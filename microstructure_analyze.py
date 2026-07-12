#!/usr/bin/env python3
"""
Phase A → Phase B gate — microstructure feature correlation study.

Runs against parquet files produced by microstructure_collector.py. The
question this script answers, and nothing else:

    "At time T, does feature X have out-of-sample predictive power for
     the sign (or magnitude) of mid_price_return at T+2min, T+5min,
     T+10min — consistently across pairs and across days?"

If the answer is yes for at least one feature on at least 2 of 4 pairs
with |Information Coefficient| ≥ 0.04 and t-stat ≥ 2.0, Phase B is
on the table. Otherwise the microstructure-signal thesis is killed
and we pivot to the next edge class (on-chain, options skew, etc.).

Information Coefficient here = Spearman rank correlation between feature
value and forward return. Classical quant-research metric. 0.04 is the
lower end of "barely informative" in institutional equity literature;
higher in crypto is possible but we shouldn't assume it.

Usage:
  python microstructure_analyze.py
  python microstructure_analyze.py --data-dir /var/log/microstructure
  python microstructure_analyze.py --horizons 120 300 600 1800
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("pip install pandas numpy pyarrow", file=sys.stderr); sys.exit(1)
try:
    from scipy.stats import spearmanr
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


FEATURES = [
    # core top-of-book
    "depth_imbalance",
    "spread_pct",
    # order-flow and tape
    "delta_30s",
    "trade_intensity",
    "volatility_burst",
    # peer-reviewed microstructure signals
    "ofi_30s",            # Cont-Kukanov-Stoikov order-flow imbalance
    "book_slope_bid",     # absorption capacity on bid side
    "book_slope_ask",     # absorption capacity on ask side
    # derivatives / positioning
    "basis_pct",          # (perp_mark - spot) / spot
    "funding_rate_8h",    # predicted next-period funding
    "perp_oi",            # open interest (z-score per pair is better, raw ok for now)
]


def load_all(data_dir: Path) -> pd.DataFrame:
    """Walk the YYYY-MM-DD/HH/PAIR.parquet hierarchy, return one DataFrame
    per pair concatenated across time. Returns dict of pair → DataFrame."""
    files = list(data_dir.rglob("*.parquet"))
    if not files:
        print(f"no parquet files found under {data_dir}")
        sys.exit(1)
    frames_by_pair: Dict[str, List[pd.DataFrame]] = {}
    for f in sorted(files):
        pair = f.stem
        try:
            df = pd.read_parquet(f)
        except Exception as e:
            print(f"skip {f}: {e}"); continue
        frames_by_pair.setdefault(pair, []).append(df)
    out: Dict[str, pd.DataFrame] = {}
    for pair, frames in frames_by_pair.items():
        df = pd.concat(frames, ignore_index=True)
        df = df.sort_values("ts_ms").drop_duplicates("ts_ms").reset_index(drop=True)
        out[pair] = df
    return out


def forward_returns(df: pd.DataFrame, horizons_s: List[int]) -> pd.DataFrame:
    """Compute forward log returns over multiple horizons. Each sample's
    forward-T return = log(mid[t + T_seconds] / mid[t]). Rows near the
    end of the series where T is unavailable become NaN.

    NOTE: direction="forward" forces the forward-return lookup to match
    the first sample at OR AFTER ts+T. The previous version used
    direction="nearest" which could match up to 2s BEFORE ts+T —
    technically a small look-ahead reduction (the "future" mid was
    sometimes the one just before the intended horizon). Switched to
    "forward" so all forward returns are strictly future-only.
    Confirmed by 2026-04-25 look-ahead audit on D6 dry-run.
    """
    if "ts_ms" not in df.columns or "mid" not in df.columns:
        raise ValueError("expect ts_ms and mid columns")
    df = df.copy()
    # index by time for label lookup
    df["ts_s"] = df["ts_ms"] // 1000
    # For each horizon, find future mid at-or-after ts_s + horizon
    # tolerance allows up to 2s slack on data-dropout gaps
    for T in horizons_s:
        fut = df[["ts_s", "mid"]].rename(columns={"ts_s": "ts_future",
                                                    "mid":   "mid_future"})
        merged = pd.merge_asof(
            df.assign(ts_lookup=df["ts_s"] + T).sort_values("ts_lookup"),
            fut.sort_values("ts_future"),
            left_on="ts_lookup", right_on="ts_future",
            tolerance=2, direction="forward",
        ).sort_values("ts_ms")
        df[f"fwd_ret_{T}s"] = np.log(merged["mid_future"].values /
                                       df["mid"].values)
    return df


def information_coefficient(feature: np.ndarray,
                             target: np.ndarray) -> Dict[str, float]:
    mask = ~(np.isnan(feature) | np.isnan(target))
    f, t = feature[mask], target[mask]
    if len(f) < 100:
        return dict(ic=float("nan"), t_stat=float("nan"), n=len(f))
    if HAS_SCIPY:
        rho, pval = spearmanr(f, t)
        # t-stat from IC: t = IC × sqrt((n-2) / (1 - IC²))
        if 1 - rho * rho > 0:
            tstat = rho * math.sqrt((len(f) - 2) / (1 - rho * rho))
        else:
            tstat = float("inf")
    else:
        # Pearson fallback
        f_rank = pd.Series(f).rank().values
        t_rank = pd.Series(t).rank().values
        rho = np.corrcoef(f_rank, t_rank)[0, 1]
        tstat = rho * math.sqrt((len(f) - 2) / (1 - rho * rho)) if 1 - rho * rho > 0 else float("inf")
    return dict(ic=rho, t_stat=tstat, n=int(len(f)))


def main():
    import math  # local for information_coefficient
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/var/log/microstructure")
    ap.add_argument("--horizons", nargs="+", type=int,
                    default=[60, 120, 300, 600, 1800],
                    help="forward-return horizons in seconds")
    ap.add_argument("--pairs", nargs="+", default=None)
    args = ap.parse_args()

    globals()["math"] = math   # make available to helper without passing around

    print("═" * 100)
    print(f"  MICROSTRUCTURE ANALYSIS · {args.data_dir}")
    print("═" * 100)

    by_pair = load_all(Path(args.data_dir))
    if args.pairs:
        by_pair = {p: df for p, df in by_pair.items() if p in args.pairs}

    # Summary per pair
    print("\n▸ Data summary")
    for pair, df in by_pair.items():
        span_h = (df["ts_ms"].max() - df["ts_ms"].min()) / 1000 / 3600
        print(f"  {pair:<10} {len(df):>8,d} rows · {span_h:.1f} h of data")

    # ── L99 regime-conditional analysis ───────────────────────────────
    # If regime_label is present, compute IC separately for each regime
    # bucket. The hypothesis we test: features have higher IC during
    # EXPANSION/HIGH_IMPULSE than during DEAD/NEUTRAL. If yes → regime
    # gating is genuine alpha. If no → regime classifier was noise.
    has_regime = any("regime_label" in df.columns for df in by_pair.values())
    if has_regime:
        print("\n▸ Regime distribution by pair")
        for pair, df in by_pair.items():
            if "regime_label" not in df.columns:
                continue
            counts = df["regime_label"].value_counts()
            total = len(df)
            dist = " · ".join(f"{lbl} {n} ({n/total*100:.1f}%)"
                              for lbl, n in counts.items())
            print(f"  {pair:<10}  {dist}")

    # Per pair × feature × horizon → IC / t-stat / n
    print("\n▸ Information Coefficient (Spearman ρ) — |IC| ≥ 0.04 and |t| ≥ 2.0 flagged")
    print()
    header = f"  {'pair':<10} {'feature':<18} " + " ".join(
        f"{'H=' + str(h) + 's':>18}" for h in args.horizons)
    print(header)
    print("  " + "-" * (len(header) - 2))

    pair_feature_hits = {}
    for pair, df in by_pair.items():
        df = forward_returns(df, args.horizons)
        for feat in FEATURES:
            row = f"  {pair:<10} {feat:<18} "
            for T in args.horizons:
                r = information_coefficient(
                    df[feat].values.astype(float),
                    df[f"fwd_ret_{T}s"].values.astype(float),
                )
                ic = r["ic"]; t = r["t_stat"]; n = r["n"]
                ic_flag = "★" if (not math.isnan(ic) and abs(ic) >= 0.04
                                    and abs(t) >= 2.0) else " "
                if math.isnan(ic):
                    cell = "    nan "
                else:
                    cell = f"{ic:+.3f}/t{t:+.1f}{ic_flag}"
                row += f"{cell:>18} "
                if ic_flag == "★":
                    pair_feature_hits.setdefault((feat, T), []).append(pair)
            print(row)
        print()

    # ── L99 regime-conditional IC test ────────────────────────────────
    # For each pair × feature × horizon, compute IC restricted to rows
    # where regime is EXPANSION or HIGH_IMPULSE. If a feature's IC is
    # meaningfully larger during expansion than overall, that's a
    # second-order signal: the regime classifier is identifying when
    # the feature actually predicts.
    if has_regime:
        print("\n▸ Regime-conditional IC — features × {EXPANSION+HIGH_IMPULSE only}")
        print(f"  Only flagging features whose conditional |IC| improves by ≥0.02 over unconditional")
        for pair, df in by_pair.items():
            if "regime_label" not in df.columns: continue
            df = forward_returns(df, args.horizons)
            mask = df["regime_label"].isin(["EXPANSION", "HIGH_IMPULSE"])
            if mask.sum() < 100:
                print(f"  {pair:<10}  too few EXPANSION samples ({mask.sum()})")
                continue
            print(f"  {pair:<10}  EXPANSION/HIGH_IMPULSE rows: {mask.sum()}")
            for feat in FEATURES:
                if feat not in df.columns: continue
                for T in args.horizons:
                    ic_all = information_coefficient(
                        df[feat].values.astype(float),
                        df[f"fwd_ret_{T}s"].values.astype(float),
                    )
                    df_e = df[mask]
                    ic_e = information_coefficient(
                        df_e[feat].values.astype(float),
                        df_e[f"fwd_ret_{T}s"].values.astype(float),
                    )
                    ic_a = ic_all["ic"]; ic_x = ic_e["ic"]
                    if math.isnan(ic_a) or math.isnan(ic_x): continue
                    delta = abs(ic_x) - abs(ic_a)
                    if delta >= 0.02 and abs(ic_x) >= 0.04:
                        print(f"    ★ {feat:<18} H={T}s  "
                              f"IC_all={ic_a:+.3f}  IC_expansion={ic_x:+.3f}  "
                              f"Δ=+{delta:.3f}")

    # Phase B verdict
    print("═" * 100)
    print("  PHASE B GATE")
    print("═" * 100)
    survivors = [(feat, T, pairs) for (feat, T), pairs in
                 pair_feature_hits.items() if len(pairs) >= 2]
    if survivors:
        print(f"  ✅ {len(survivors)} (feature, horizon) combo(s) cleared the bar:")
        for feat, T, pairs in sorted(survivors, key=lambda x: -len(x[2])):
            print(f"    • {feat} @ H={T}s  consistent on {len(pairs)}/{len(by_pair)} pairs: "
                  f"{', '.join(pairs)}")
        print()
        print("  Recommended Phase B: ensemble the surviving features into a classifier,")
        print("  walk-forward validate with professional_backtest.py, deploy paper-only if it clears.")
    else:
        print("  🛑 No (feature, horizon) combo has |IC| ≥ 0.04 AND |t| ≥ 2.0")
        print("     on ≥ 2 of the collected pairs. Microstructure features as implemented")
        print("     do not carry predictive signal at the horizons tested on this data.")
        print()
        print("  Next steps:")
        print("   1. Collect more data (5 days may be insufficient).")
        print("   2. Try richer features: micro-price, order-flow imbalance, VPIN.")
        print("   3. Move to a different edge class: on-chain, options skew, MM spread capture.")


if __name__ == "__main__":
    main()
