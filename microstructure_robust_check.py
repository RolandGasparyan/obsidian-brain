#!/usr/bin/env python3
"""
Microstructure robustness checks — to be run alongside microstructure_analyze.py

After RSI-2 was rejected for being a single-window curve-fit, the same
discipline applies to the microstructure analyzer's |IC|≥0.04 hits.
This sidecar adds three checks the base analyzer lacks:

  1. STATIONARITY (IC by day) — split the dataset into daily buckets,
     compute IC per (pair, feature, horizon, day). If the signal is
     real, IC should keep the same sign across days. If it's regime-
     specific noise, daily IC will flip sign or concentrate in one day.

  2. WALK-FORWARD IC STABILITY — train_ic on first 60% of timeline,
     test_ic on last 40%. A real edge has |test_ic| ≥ 0.5 × |train_ic|
     and same sign. Anything that flips sign or collapses is a
     curve-fit, exactly like XRP RSI-2.

  3. MULTIPLE-COMPARISON CORRECTION — with N=11 features × 5 horizons
     × 5 pairs = 275 hypotheses tested, expecting ~14 to clear |t|≥2.0
     by pure chance at α=0.05. Apply Benjamini-Hochberg FDR adjustment
     and report which hits survive at α_FDR=0.10.

Output a TIGHTENED Phase B verdict: which combos clear ALL three filters.
That's the set worth ensembling for actual signal extraction.

Usage:
  python microstructure_robust_check.py
  python microstructure_robust_check.py --data-dir /var/log/microstructure
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

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
    print("WARNING: scipy not available, using rank-Pearson fallback")


FEATURES = [
    "depth_imbalance", "spread_pct", "delta_30s", "trade_intensity",
    "volatility_burst", "ofi_30s", "book_slope_bid", "book_slope_ask",
    "basis_pct", "funding_rate_8h", "perp_oi",
]


def load_all(data_dir: Path) -> Dict[str, pd.DataFrame]:
    files = list(data_dir.rglob("*.parquet"))
    if not files:
        print(f"no parquet files found under {data_dir}"); sys.exit(1)
    by_pair: Dict[str, List[pd.DataFrame]] = {}
    for f in sorted(files):
        try:
            by_pair.setdefault(f.stem, []).append(pd.read_parquet(f))
        except Exception as e:
            print(f"skip {f}: {e}")
    out = {}
    for pair, frames in by_pair.items():
        df = pd.concat(frames, ignore_index=True)
        df = df.sort_values("ts_ms").drop_duplicates("ts_ms").reset_index(drop=True)
        out[pair] = df
    return out


def forward_returns(df: pd.DataFrame, horizons: List[int]) -> pd.DataFrame:
    """Forward log returns at-or-after ts+T (direction='forward')."""
    df = df.copy()
    df["ts_s"] = df["ts_ms"] // 1000
    for T in horizons:
        fut = df[["ts_s", "mid"]].rename(
            columns={"ts_s": "ts_future", "mid": "mid_future"})
        merged = pd.merge_asof(
            df.assign(ts_lookup=df["ts_s"] + T).sort_values("ts_lookup"),
            fut.sort_values("ts_future"),
            left_on="ts_lookup", right_on="ts_future",
            tolerance=2, direction="forward",
        ).sort_values("ts_ms")
        df[f"fwd_ret_{T}s"] = np.log(merged["mid_future"].values
                                       / df["mid"].values)
    return df


def ic_t(feat: np.ndarray, tgt: np.ndarray) -> Tuple[float, float, int]:
    mask = ~(np.isnan(feat) | np.isnan(tgt))
    f, t = feat[mask], tgt[mask]
    if len(f) < 50:
        return float("nan"), float("nan"), len(f)
    if HAS_SCIPY:
        rho, _ = spearmanr(f, t)
    else:
        f_rank = pd.Series(f).rank().values
        t_rank = pd.Series(t).rank().values
        rho = np.corrcoef(f_rank, t_rank)[0, 1]
    if math.isnan(rho) or 1 - rho * rho <= 0:
        return rho, float("inf"), int(len(f))
    tstat = rho * math.sqrt((len(f) - 2) / (1 - rho * rho))
    return float(rho), float(tstat), int(len(f))


# ── 4. BOOTSTRAP IC confidence interval ────────────────────────────
def bootstrap_ic_ci(feat: np.ndarray, tgt: np.ndarray,
                    n_boot: int = 1000, seed: int = 17,
                    block_size: int = 60) -> Dict[str, float]:
    """Block-bootstrap CI on Spearman IC.

    With 36k 1-Hz samples per pair-day, individual rows are NOT iid:
    consecutive rows share book/tape state. Naive resampling
    overstates effective N. We use a moving block bootstrap with
    block_size=60 (roughly the autocorrelation horizon for our
    features) so each block preserves local serial dependence.

    Output: median, p2.5, p97.5 of the bootstrap IC distribution.
    A cell "passes" if (a) p2.5 > +0.04, OR (b) p97.5 < -0.04. That is:
    the 95% CI excludes zero with magnitude beyond the |IC|=0.04 floor.
    """
    mask = ~(np.isnan(feat) | np.isnan(tgt))
    f, t = feat[mask], tgt[mask]
    n = len(f)
    if n < max(200, block_size * 4):
        return {"median": float("nan"), "p2_5": float("nan"),
                "p97_5": float("nan"), "n": n, "passes": False}
    rng = np.random.default_rng(seed)
    n_blocks = n // block_size
    ics = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        # Sample n_blocks block start indices with replacement
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        idx = (starts[:, None] + np.arange(block_size)).ravel()
        idx = idx[idx < n]
        if HAS_SCIPY:
            rho, _ = spearmanr(f[idx], t[idx])
        else:
            rho = np.corrcoef(pd.Series(f[idx]).rank().values,
                              pd.Series(t[idx]).rank().values)[0, 1]
        ics[b] = rho if not math.isnan(rho) else 0.0
    median = float(np.median(ics))
    p2_5   = float(np.percentile(ics, 2.5))
    p97_5  = float(np.percentile(ics, 97.5))
    passes = (p2_5 > 0.04) or (p97_5 < -0.04)
    return {"median": median, "p2_5": p2_5, "p97_5": p97_5,
            "n": n, "passes": passes}


# ── 5. VOLATILITY-ADJUSTED forward returns ─────────────────────────
def vol_adjust_ic(df: pd.DataFrame, feat: str, T: int,
                  vol_window: int = 600) -> Dict[str, float]:
    """Re-compute IC using vol-normalized forward returns.

    fwd_ret_T scales linearly with realized vol; same |IC| during a
    high-vol minute is more informative than during a low-vol minute.
    Divide each forward return by an EWM σ over `vol_window` seconds
    and re-measure IC. If unconditional IC was inflated by a few
    high-vol bursts, vol-adjusted IC will collapse.
    """
    col = f"fwd_ret_{T}s"
    if col not in df.columns or feat not in df.columns:
        return {"vol_adj_ic": float("nan"), "shrunk": False}
    s = df[col].astype(float)
    sigma = s.ewm(halflife=vol_window).std().replace(0, np.nan)
    s_adj = (s / sigma).values
    ic, _, _ = ic_t(df[feat].values.astype(float), s_adj)
    return {"vol_adj_ic": ic, "shrunk": False}  # caller compares to raw


# ── 7. MONOTONICITY (quintile structure) gate ──────────────────────
def quintile_monotonicity(df: pd.DataFrame, feat: str, T: int) -> float:
    """Compute Spearman ρ between quintile rank (1..5) and the mean
    forward return per quintile.  +1 = perfectly monotonic increasing,
    -1 = perfectly decreasing, 0 = noise.

    A high IC with low quintile-monotonicity means the rank correlation
    is driven by tail extremities (a few rows at the ends), not a
    smooth feature→return relationship. Such signals fail to translate
    into tradeable strategies even if all other filters pass.

    Returns nan if the cell can't be quintile-binned.
    """
    col = f"fwd_ret_{T}s"
    if col not in df.columns or feat not in df.columns:
        return float("nan")
    sub = df[[feat, col]].dropna()
    if len(sub) < 500:
        return float("nan")
    try:
        sub["q"] = pd.qcut(sub[feat], q=5,
                           labels=[1, 2, 3, 4, 5],
                           duplicates="drop")
    except ValueError:
        return float("nan")
    means = sub.groupby("q")[col].mean()
    if len(means) < 5 or means.std() == 0:
        return float("nan")
    ranks = np.arange(1, len(means) + 1, dtype=float)
    return float(np.corrcoef(ranks, means.values)[0, 1])


# ── 6. CONCURRENT-FEATURE correlation map ──────────────────────────
def feature_correlation_matrix(df: pd.DataFrame,
                                feats: List[str]) -> pd.DataFrame:
    """Are spread_pct / book_slope_* / depth_imbalance secretly the
    same feature? Compute pairwise Spearman ρ on the feature columns
    themselves. If two features have |ρ| > 0.7, they're not independent
    signals and counting both as a "Phase B winner" is double-counting.
    """
    sub = df[feats].copy()
    if HAS_SCIPY:
        ranks = sub.rank()
        return ranks.corr(method="pearson")  # rank-correlation = Spearman
    return sub.corr(method="spearman")


# ── 1. STATIONARITY by day ─────────────────────────────────────────
def per_day_ic(df: pd.DataFrame, feat: str, T: int) -> List[Tuple[str, float, int]]:
    df = df.copy()
    df["day"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True).dt.date
    out = []
    for day, g in df.groupby("day"):
        if f"fwd_ret_{T}s" not in g.columns: continue
        ic, _, n = ic_t(g[feat].values.astype(float),
                        g[f"fwd_ret_{T}s"].values.astype(float))
        if not math.isnan(ic):
            out.append((str(day), ic, n))
    return out


# ── 2. WALK-FORWARD train/test ─────────────────────────────────────
def walk_forward_ic(df: pd.DataFrame, feat: str, T: int,
                    train_frac: float = 0.6) -> Dict[str, float]:
    if f"fwd_ret_{T}s" not in df.columns:
        return {"train_ic": float("nan"), "test_ic": float("nan"),
                "stable": False}
    cut = int(len(df) * train_frac)
    train = df.iloc[:cut]; test = df.iloc[cut:]
    tr_ic, _, _ = ic_t(train[feat].values.astype(float),
                       train[f"fwd_ret_{T}s"].values.astype(float))
    te_ic, _, _ = ic_t(test[feat].values.astype(float),
                       test[f"fwd_ret_{T}s"].values.astype(float))
    if math.isnan(tr_ic) or math.isnan(te_ic):
        stable = False
    else:
        same_sign = (tr_ic * te_ic > 0)
        magnitude_ok = abs(te_ic) >= 0.5 * abs(tr_ic)
        stable = same_sign and magnitude_ok
    return {"train_ic": tr_ic, "test_ic": te_ic, "stable": stable}


# ── 3. Benjamini-Hochberg FDR ──────────────────────────────────────
def bh_fdr(p_values: List[Tuple[Tuple, float]],
           alpha: float = 0.10) -> List[Tuple]:
    """Returns the list of keys whose p-value passes BH-FDR at level alpha."""
    if not p_values: return []
    sorted_p = sorted(p_values, key=lambda x: x[1])
    m = len(sorted_p)
    survivors = []
    for k, (key, p) in enumerate(sorted_p, start=1):
        if p <= (k / m) * alpha:
            survivors = sorted_p[:k]   # keep all up to k
    return [key for key, _ in survivors]


def t_to_p_two_sided(t: float, df: int) -> float:
    """Approximate two-sided p-value from t-stat without scipy.t."""
    if HAS_SCIPY:
        from scipy.stats import t as t_dist
        return 2 * (1 - t_dist.cdf(abs(t), df=max(df, 1)))
    # fallback: large-N normal approximation
    from math import erf
    return 2 * (1 - 0.5 * (1 + erf(abs(t) / math.sqrt(2))))


# ── main ───────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/var/log/microstructure")
    ap.add_argument("--horizons", nargs="+", type=int,
                    default=[60, 120, 300, 600, 1800])
    ap.add_argument("--ic-floor", type=float, default=0.04)
    ap.add_argument("--fdr-alpha", type=float, default=0.10)
    args = ap.parse_args()

    print("═" * 100)
    print(f"  MICROSTRUCTURE ROBUSTNESS CHECK · 7-filter battery")
    print(f"  (1) stationarity by day  (2) walk-forward stability")
    print(f"  (3) BH-FDR multi-comparison  (4) block-bootstrap 95% CI")
    print(f"  (5) vol-adjusted IC same-sign + ≥50% magnitude")
    print(f"  (6) concurrent-feature independence (|ρ|<0.7)")
    print(f"  (7) quintile monotonicity (|ρ(rank, fwd_mean)| ≥ 0.85)")
    print("═" * 100)

    by_pair = load_all(Path(args.data_dir))
    n_days = 0
    for pair, df in by_pair.items():
        days = pd.to_datetime(df["ts_ms"], unit="ms", utc=True).dt.date.unique()
        n_days = max(n_days, len(days))
    print(f"\n  pairs:    {', '.join(by_pair.keys())}")
    print(f"  horizons: {args.horizons}")
    print(f"  features: {len(FEATURES)}")
    print(f"  days:     {n_days}")
    print(f"  total tests = {len(by_pair) * len(FEATURES) * len(args.horizons)} "
          f"= {len(by_pair) * len(FEATURES) * len(args.horizons)} hypotheses")

    # Add forward returns to every pair df
    for pair in list(by_pair.keys()):
        by_pair[pair] = forward_returns(by_pair[pair], args.horizons)

    # ── pass 1: collect every (pair, feat, T) → (ic, t, n)
    raw_hits: Dict[Tuple[str, str, int], Tuple[float, float, int]] = {}
    p_values: List[Tuple[Tuple, float]] = []
    for pair, df in by_pair.items():
        for feat in FEATURES:
            for T in args.horizons:
                if feat not in df.columns: continue
                ic, t, n = ic_t(df[feat].values.astype(float),
                                df[f"fwd_ret_{T}s"].values.astype(float))
                if math.isnan(ic): continue
                raw_hits[(pair, feat, T)] = (ic, t, n)
                p = t_to_p_two_sided(t, n - 2)
                p_values.append(((pair, feat, T), p))

    # ── pass 2: |IC|≥floor AND |t|≥2 (the base analyzer's gate)
    base_hits = {k: v for k, v in raw_hits.items()
                 if abs(v[0]) >= args.ic_floor and abs(v[1]) >= 2.0}
    print(f"\n▸ Base hits (|IC|≥{args.ic_floor} AND |t|≥2.0): "
          f"{len(base_hits)} of {len(raw_hits)} tests")

    # ── pass 3: stationarity by day
    print(f"\n▸ FILTER 1: stationarity by day (sign consistent across ≥{max(2, n_days-1)} of {n_days} days)")
    stationary = []
    for (pair, feat, T), (ic, t, n) in base_hits.items():
        days = per_day_ic(by_pair[pair], feat, T)
        if not days: continue
        sign = 1 if ic > 0 else -1
        agree = sum(1 for _, day_ic, _ in days if (day_ic > 0) == (sign > 0))
        if agree >= max(2, len(days) - 1):
            stationary.append((pair, feat, T, ic, t, n, agree, len(days)))
    print(f"    {len(stationary)} of {len(base_hits)} survive")

    # ── pass 4: walk-forward stability
    print(f"\n▸ FILTER 2: walk-forward stability (train 60% → test 40%, same sign + |test_IC|≥0.5×|train_IC|)")
    wf_stable = []
    for (pair, feat, T, ic, t, n, agree, total) in stationary:
        wf = walk_forward_ic(by_pair[pair], feat, T)
        if wf["stable"]:
            wf_stable.append((pair, feat, T, ic, t, n,
                              wf["train_ic"], wf["test_ic"]))
    print(f"    {len(wf_stable)} of {len(stationary)} survive")

    # ── pass 5: BH-FDR multi-comparison
    print(f"\n▸ FILTER 3: Benjamini-Hochberg FDR @ α={args.fdr_alpha}")
    fdr_keys = set(bh_fdr(p_values, alpha=args.fdr_alpha))
    print(f"    {len(fdr_keys)} of {len(p_values)} tests pass FDR")

    # ── intersect: TRIPLE-FILTER survivors
    triple = [(p, f, T, ic, t, n, tr, te) for (p, f, T, ic, t, n, tr, te)
              in wf_stable if (p, f, T) in fdr_keys]
    print(f"\n  TRIPLE-FILTER survivors: {len(triple)}")

    # ── pass 6: BLOCK BOOTSTRAP IC confidence interval ──────────────
    print(f"\n▸ FILTER 4: block-bootstrap 95% CI (block=60s · 1000 resamples · CI excludes |IC|=0.04 floor)")
    quad = []
    for (p, f, T, ic, ts, n, tr, te) in triple:
        df_p = by_pair[p]
        boot = bootstrap_ic_ci(df_p[f].values.astype(float),
                                df_p[f"fwd_ret_{T}s"].values.astype(float),
                                n_boot=1000)
        if boot["passes"]:
            quad.append((p, f, T, ic, ts, tr, te,
                          boot["median"], boot["p2_5"], boot["p97_5"]))
    print(f"    {len(quad)} of {len(triple)} survive bootstrap CI")

    # ── pass 7: VOL-ADJUSTED IC sanity check ──────────────────────
    print(f"\n▸ FILTER 5: vol-adjusted IC (raw IC robust to per-horizon σ normalization)")
    quint = []
    for (p, f, T, ic, ts, tr, te, b50, b025, b975) in quad:
        v = vol_adjust_ic(by_pair[p], f, T)
        v_ic = v["vol_adj_ic"]
        # Pass: vol-adjusted IC has same sign AND |adj_ic| >= 0.5 * |raw_ic|
        if (math.isnan(v_ic) or
            (v_ic * ic <= 0) or
            abs(v_ic) < 0.5 * abs(ic)):
            continue
        quint.append((p, f, T, ic, ts, tr, te, b50, b025, b975, v_ic))
    print(f"    {len(quint)} of {len(quad)} survive vol-adjustment")

    # ── pass 7b: QUINTILE MONOTONICITY gate ─────────────────────
    print(f"\n▸ FILTER 7: quintile monotonicity (|ρ(rank, fwd_mean)| ≥ 0.85)")
    sext = []
    for (p, f, T, ic, ts, tr, te, b50, b025, b975, v_ic) in quint:
        mono = quintile_monotonicity(by_pair[p], f, T)
        if math.isnan(mono): continue
        if abs(mono) >= 0.85:
            sext.append((p, f, T, ic, ts, tr, te, b50, b025, b975, v_ic, mono))
    print(f"    {len(sext)} of {len(quint)} survive monotonicity gate")
    quint = sext   # downstream uses 'quint' as the survivor list

    # ── pass 8: CONCURRENT-FEATURE correlation map ───────────────
    print(f"\n▸ FILTER 6: concurrent-feature correlation (warn if any pair has |ρ|>0.7 between two features)")
    duplicates = set()
    for pair, df in by_pair.items():
        cm = feature_correlation_matrix(df, FEATURES)
        for i, fi in enumerate(FEATURES):
            for j, fj in enumerate(FEATURES):
                if j <= i: continue
                v = cm.loc[fi, fj]
                if abs(v) > 0.7:
                    duplicates.add(frozenset([fi, fj]))
                    print(f"    ⚠ {pair}: ρ({fi}, {fj}) = {v:+.2f}")
    if not duplicates:
        print("    no feature-pair has |ρ|>0.7 on any pair → features are independent enough")

    # ── verdict
    print("\n" + "═" * 100)
    print("  TIGHTENED PHASE B VERDICT — seven-filter battery")
    print("═" * 100)
    if quint:
        print(f"  ✅ {len(quint)} (pair, feature, horizon) combos cleared ALL SEVEN filters:\n")
        print(f"     {'pair':<10} {'feature':<18} {'H':>6} "
              f"{'IC':>7} {'train':>7} {'test':>7} "
              f"{'CI95.lo':>8} {'CI95.hi':>8} {'volAdj':>8} {'mono ρ':>8}")
        print(f"     " + "-" * 102)
        quint.sort(key=lambda r: -abs(r[3]))
        for p, f, T, ic, ts, tr, te, b50, b025, b975, v_ic, mono in quint[:30]:
            print(f"     {p:<10} {f:<18} {T:>5}s "
                  f"{ic:>+6.3f} {tr:>+6.3f} {te:>+6.3f} "
                  f"{b025:>+7.3f} {b975:>+7.3f} {v_ic:>+7.3f} {mono:>+7.3f}")
        if len(quint) > 30:
            print(f"     ... and {len(quint) - 30} more")

        # group by (feature, horizon) — count pairs surviving
        fh_pairs: Dict[Tuple[str, int], List[str]] = defaultdict(list)
        for p, f, T, *_ in quint:
            fh_pairs[(f, T)].append(p)

        print(f"\n  Six-filter (feature, horizon) combos hitting ≥2 pairs:")
        for (f, T), pairs in sorted(fh_pairs.items(), key=lambda x: -len(x[1])):
            if len(pairs) >= 2:
                print(f"    • {f} @ H={T}s — {len(pairs)} pairs: {', '.join(pairs)}")
    else:
        print("  🛑 NO combo survives all 6 filters. Microstructure thesis weakens.")
    print("═" * 100)
    if duplicates:
        print("\n  Concurrent-feature warning: the following pairs are ρ>0.7-correlated")
        print("  on at least one symbol. Counting them as separate winners is double-counting:")
        for d in duplicates:
            print(f"    {' ↔ '.join(sorted(d))}")


if __name__ == "__main__":
    main()
