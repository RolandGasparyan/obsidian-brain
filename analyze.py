#!/usr/bin/env python3
"""
Summarize all sim_results_*.json and backtest_results_*.json files.
Usage: python analyze.py [--dir path]
"""
import os, json, glob, argparse
from collections import defaultdict


def load_all(root: str):
    files = sorted(
        glob.glob(os.path.join(root, "sim_results_*.json"))
        + glob.glob(os.path.join(root, "backtest_results_*.json"))
    )
    return [(f, json.load(open(f))) for f in files]


def summarize(runs):
    if not runs:
        print("  No result files found.")
        return

    print("="*78)
    print(f"  {'FILE':<44} {'MODE':<22} {'ROI':>8}")
    print("="*78)
    for f, d in runs:
        name = os.path.basename(f)
        mode = d.get("mode", "?")
        roi  = d.get("roi_pct", 0.0)
        print(f"  {name:<44} {mode:<22} {roi:>+7.3f}%")

    print()
    by_mode = defaultdict(list)
    for _, d in runs: by_mode[d.get("mode","?")].append(d)

    for mode, items in by_mode.items():
        print(f"  ── {mode} ({len(items)} runs) ──")
        rois   = [d.get("roi_pct",0)   for d in items]
        wrs    = [d.get("win_rate",0)  for d in items]
        trades = [d.get("trades",0)    for d in items]
        pnls   = [d.get("pnl",0)       for d in items]
        best   = max(items, key=lambda d: d.get("roi_pct", -999))
        worst  = min(items, key=lambda d: d.get("roi_pct",  999))
        print(f"    Avg ROI:     {sum(rois)/len(rois):+.3f}%")
        print(f"    Avg WR:      {sum(wrs)/len(wrs):.1f}%")
        print(f"    Avg trades:  {sum(trades)/len(trades):.1f}")
        print(f"    Total PnL:   {sum(pnls):+.4f} USDT")
        print(f"    Best ROI:    {best.get('roi_pct',0):+.3f}% ({best.get('trades',0)} trades)")
        print(f"    Worst ROI:   {worst.get('roi_pct',0):+.3f}% ({worst.get('trades',0)} trades)")
        print()

    # Exit-type counts across everything
    exit_counts: dict = defaultdict(int)
    for _, d in runs:
        for t in d.get("history", []):
            exit_counts[t.get("why","?")] += 1
    if exit_counts:
        print("  EXIT TYPES (all runs combined):")
        for why, cnt in sorted(exit_counts.items(), key=lambda x: -x[1]):
            print(f"    {why:<20} {cnt:4d}×")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    runs = load_all(args.dir)
    summarize(runs)
