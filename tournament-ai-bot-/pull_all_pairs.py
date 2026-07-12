"""pull_all_pairs.py - Batch 15m OHLCV pull for all tournament pairs.

Usage:
    python pull_all_pairs.py
    python pull_all_pairs.py --days 30 --interval 1m
    python pull_all_pairs.py --pairs BTC_USDT,ETH_USDT --days 14

Output goes to ./calib_15m/ by default.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from pull_gateio_ohlcv import pull_pair

TOURNAMENT_PAIRS = [
    "BTC_USDT",
    "ETH_USDT",
    "SOL_USDT",
    "BNB_USDT",
]


def main() -> None:
    p = argparse.ArgumentParser(
        description="Pull OHLCV data for all tournament pairs from Gate.io"
    )
    p.add_argument("--pairs", default=",".join(TOURNAMENT_PAIRS))
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--interval", default="15m")
    p.add_argument("--outdir", default="./calib_15m")
    args = p.parse_args()

    pairs = [s.strip() for s in args.pairs.split(",") if s.strip()]
    outdir = Path(args.outdir)

    print(f"Pulling {args.days}d {args.interval} for {len(pairs)} pairs -> {outdir}")

    for pair in pairs:
        print(f"  {pair}...")
        pull_pair(pair, args.days, args.interval, outdir)

    print("Done. Run calibration next:")
    for pair in pairs:
        csv = outdir / f"{pair}_{args.interval}_{args.days}d.csv"
        print(f"  python -m tournament.calibrate_volatility --pair {pair} --csv {csv}")


if __name__ == "__main__":
    main()
