#!/usr/bin/env python3
"""
Microstructure signal-nature investigation.

After the 6-filter battery showed XRP_USDT spread_pct@1800s with
IC=+0.475 / CI95=[+0.407, +0.538] / vol-adj +0.483, the question
shifts from "is it real?" to "what does it mean economically?"

Spearman ρ tells us rank correlation. It does NOT tell us:
  - Magnitude of the effect in basis points
  - Whether the relationship is monotonic across quintiles
  - Whether it's symmetric (does Q5 produce as much positive as Q1
    produces negative?)
  - Whether the effect is driven by the tails or the body

This script answers those by binning each surviving feature into
quintiles and reporting the conditional mean of forward returns.
A signal that's economically interpretable should:
  1. Have a monotonic Q1 → Q5 relationship (not noise)
  2. Show meaningful spread between top and bottom quintiles
     (Q5_mean - Q1_mean > a few bps for it to matter post-fees)
  3. Be roughly symmetric (otherwise we're learning a one-sided effect)

If the relationship is messy or driven entirely by the tails, the
high IC is a Spearman artifact of a few outliers — and we should
NOT bet capital on it even if all other filters passed.

Usage:
  python microstructure_signal_nature.py
  python microstructure_signal_nature.py --feature spread_pct --horizon 1800
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd


# Top survivors from D6_DRYRUN_6FILTER.txt that we want to characterize
DEFAULT_CELLS = [
    ("XRP_USDT",  "spread_pct",       1800),
    ("ETH_USDT",  "spread_pct",       1800),
    ("BTC_USDT",  "spread_pct",       1800),
    ("SOL_USDT",  "spread_pct",       1800),
    ("XRP_USDT",  "basis_pct",         120),
    ("BTC_USDT",  "depth_imbalance",    60),
    ("XRP_USDT",  "book_slope_bid",    300),
    ("SOL_USDT",  "funding_rate_8h",  1800),
    ("AVAX_USDT", "funding_rate_8h",  1800),
]


def load(data_dir: Path, pair: str) -> pd.DataFrame:
    files = list(data_dir.rglob(f"{pair}.parquet"))
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in sorted(files)],
                   ignore_index=True)
    return df.sort_values("ts_ms").drop_duplicates("ts_ms").reset_index(drop=True)


def add_fwd_ret(df: pd.DataFrame, T: int) -> pd.DataFrame:
    df = df.copy()
    df["ts_s"] = df["ts_ms"] // 1000
    fut = df[["ts_s", "mid"]].rename(columns={"ts_s": "ts_future",
                                                "mid":  "mid_future"})
    merged = pd.merge_asof(
        df.assign(ts_lookup=df["ts_s"] + T).sort_values("ts_lookup"),
        fut.sort_values("ts_future"),
        left_on="ts_lookup", right_on="ts_future",
        tolerance=2, direction="forward",
    ).sort_values("ts_ms")
    df[f"fwd_ret_{T}s"] = np.log(merged["mid_future"].values
                                   / df["mid"].values)
    return df


def quintile_table(df: pd.DataFrame, feat: str, T: int) -> pd.DataFrame:
    col = f"fwd_ret_{T}s"
    if col not in df.columns or feat not in df.columns:
        return pd.DataFrame()
    sub = df[[feat, col]].dropna()
    if len(sub) < 500:
        return pd.DataFrame()
    # duplicates='drop' may produce fewer than 5 bins for highly-discrete
    # features (e.g. funding_rate_8h with sparse non-zero values). Don't
    # pre-label — let pandas auto-name and rename surviving bins after.
    try:
        sub["q"] = pd.qcut(sub[feat], q=5, duplicates="drop")
    except ValueError:
        return pd.DataFrame()
    if sub["q"].nunique(dropna=True) < 5:
        return pd.DataFrame()
    # Re-label surviving bins Q1..Q5 (only if we got 5 distinct ones)
    sub["q"] = pd.qcut(sub[feat], q=5,
                        labels=["Q1", "Q2", "Q3", "Q4", "Q5"],
                        duplicates="drop")
    grp = sub.groupby("q", observed=True)
    out = grp[col].agg(["count", "mean", "std", "median"])
    out.columns = ["n", "mean_ret", "std_ret", "median_ret"]
    # Convert to bps (1 log return × 10000 ≈ basis points)
    out["mean_bps"] = out["mean_ret"] * 10000
    out["median_bps"] = out["median_ret"] * 10000
    out["std_bps"] = out["std_ret"] * 10000
    out["t_stat"]   = out["mean_ret"] / (out["std_ret"] / np.sqrt(out["n"]))
    feat_means = grp[feat].mean()
    out["feat_mean"] = feat_means
    return out[["n", "feat_mean", "mean_bps", "median_bps", "std_bps", "t_stat"]]


def monotonicity_score(qt: pd.DataFrame) -> float:
    """Spearman ρ between quintile rank (1..5) and mean_bps. +1 perfectly
    monotonic increasing; -1 perfectly monotonic decreasing; 0 = noise."""
    if qt.empty: return float("nan")
    ranks = np.arange(1, len(qt) + 1)
    means = qt["mean_bps"].values
    if np.std(means) == 0: return 0.0
    return float(np.corrcoef(ranks, means)[0, 1])


def symmetry_score(qt: pd.DataFrame) -> float:
    """How symmetric is the Q1 vs Q5 effect?  ratio = -Q1_bps / Q5_bps.
    1.0 = perfectly symmetric. >1 means Q1 effect bigger than Q5.
    0 = one-sided.  Returns inf if Q5 mean is zero."""
    if qt.empty or len(qt) < 5: return float("nan")
    q1 = qt.iloc[0]["mean_bps"]
    q5 = qt.iloc[-1]["mean_bps"]
    if q5 == 0: return float("inf")
    return float(-q1 / q5)   # positive when monotonic increasing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/var/log/microstructure")
    ap.add_argument("--cells", default=None,
                    help="Comma-separated triplets PAIR:FEATURE:HORIZON")
    ap.add_argument("--fee-bps-rt", type=float, nargs="+",
                    default=[10.0, 20.0, 30.0, 40.0],
                    help="Round-trip fee scenarios in bps (Gate.io: maker≈10, taker≈30)")
    args = ap.parse_args()

    if args.cells:
        cells = [tuple(c.split(":")) for c in args.cells.split(",")]
        cells = [(p, f, int(T)) for p, f, T in cells]
    else:
        cells = DEFAULT_CELLS

    print("═" * 100)
    print("  MICROSTRUCTURE SIGNAL-NATURE INVESTIGATION")
    print("  (quintile binning of feature vs forward return — economic interpretation)")
    print("═" * 100)

    data_dir = Path(args.data_dir)
    cache: dict = {}
    summary_rows = []

    for pair, feat, T in cells:
        if pair not in cache:
            cache[pair] = load(data_dir, pair)
            if cache[pair].empty:
                print(f"  {pair}: no parquet data in {data_dir}")
                continue
        df = cache[pair]
        if f"fwd_ret_{T}s" not in df.columns:
            df = add_fwd_ret(df, T)
            cache[pair] = df

        print("\n" + "─" * 100)
        print(f"  {pair} · {feat} @ H={T}s   (n_total = {len(df):,d})")
        print("─" * 100)

        qt = quintile_table(df, feat, T)
        if qt.empty:
            print("    insufficient data")
            continue

        # Header
        print(f"    {'quintile':<10}{'n':>8}{'feat_mean':>14}"
              f"{'fwd_mean(bps)':>16}{'fwd_med(bps)':>14}"
              f"{'fwd_std(bps)':>14}{'t-stat':>9}")
        for q, row in qt.iterrows():
            print(f"    {q:<10}{row['n']:>8.0f}{row['feat_mean']:>14.4f}"
                  f"{row['mean_bps']:>+15.2f} "
                  f"{row['median_bps']:>+13.2f} "
                  f"{row['std_bps']:>+13.2f}{row['t_stat']:>+9.2f}")

        mono = monotonicity_score(qt)
        sym  = symmetry_score(qt)
        spread_q5_q1 = qt.iloc[-1]["mean_bps"] - qt.iloc[0]["mean_bps"]
        print(f"\n    Q5 - Q1 spread = {spread_q5_q1:+.2f} bps "
              f"(post 0.30% RT fee = {spread_q5_q1 - 30:+.2f} bps net)")
        print(f"    Monotonicity ρ = {mono:+.3f}   (≥+0.8 or ≤-0.8 = clean)")
        print(f"    Symmetry      = {sym:+.2f}    (1.0 = symmetric, 0 = one-sided)")
        # Verdict
        clean_mono = abs(mono) >= 0.8
        meaningful_spread = abs(spread_q5_q1) >= 30   # ≥30 bps = beats spot RT fee
        symmetric = 0.3 <= abs(sym) <= 3.0 if not math.isinf(sym) else False
        verdict = "✅ economically interpretable" if (
            clean_mono and meaningful_spread and symmetric) else (
            "⚠ questionable" if clean_mono or meaningful_spread else
            "🛑 noise/artifact — high IC despite no clean structure")
        print(f"    VERDICT       = {verdict}")

        summary_rows.append({
            "pair": pair, "feature": feat, "horizon": T,
            "Q5-Q1_bps":   spread_q5_q1,
            "monotonicity": mono,
            "symmetry":     sym,
            "verdict":      verdict,
        })

    # Final summary table
    print("\n" + "═" * 100)
    print("  SUMMARY — economic-interpretation verdict per cell")
    print("═" * 100)
    print(f"  {'pair':<10}{'feature':<18}{'H':>6}{'Q5-Q1 (bps)':>13}"
          f"{'mono ρ':>9}{'sym':>7}  verdict")
    print("  " + "-" * 90)
    for r in summary_rows:
        sym_str = f"{r['symmetry']:+.2f}" if not math.isinf(r["symmetry"]) else "  inf"
        print(f"  {r['pair']:<10}{r['feature']:<18}{r['horizon']:>5}s"
              f"{r['Q5-Q1_bps']:>+12.2f} {r['monotonicity']:>+8.3f}{sym_str:>7}  "
              f"{r['verdict']}")
    print("═" * 100)

    # ── Fee-scenario sensitivity table ──────────────────────────
    if not summary_rows:
        return
    print("\n" + "═" * 100)
    print(f"  FEE-SCENARIO SENSITIVITY — does any signal survive at lower fee tiers?")
    print(f"  (Gate.io reference: maker ≈ 10 bps RT · taker ≈ 30 bps RT)")
    print("═" * 100)
    fee_cols = " ".join(f"{f:>5.0f}bps" for f in args.fee_bps_rt)
    print(f"  {'pair':<10}{'feature':<18}{'H':>6}{'Q5-Q1':>9}  {fee_cols}")
    print("  " + "-" * 90)
    for r in summary_rows:
        gross = r["Q5-Q1_bps"]
        cells = []
        for fee in args.fee_bps_rt:
            net = abs(gross) - fee
            mark = "✅" if net >= 5 else ("⚠ " if net >= 0 else "🛑")
            cells.append(f"{mark}{net:+5.1f}")
        print(f"  {r['pair']:<10}{r['feature']:<18}{r['horizon']:>5}s"
              f"{gross:>+8.2f}  " + " ".join(c.rjust(8) for c in cells))
    print()
    print("  ✅ = ≥ 5 bps net edge   ⚠ = barely positive   🛑 = unprofitable")
    print("═" * 100)


if __name__ == "__main__":
    main()
