"""run_paper_bot.py - Multi-pair paper trading bot for tournament qualification.

Runs a historical replay over OHLCV CSV data, emitting ENTRY signals whenever
VolatilityExpansionDetector sees a COMPRESSED state.

Usage:
    # BTC (default)
    python run_paper_bot.py

    # Single pair
    python run_paper_bot.py --pair ETH_USDT

    # All tournament pairs sequentially
    python run_paper_bot.py --all

    # Custom CSV path
    python run_paper_bot.py --pair SOL_USDT --csv ./calib_15m/SOL_USDT_15m_90d.csv

    # All pairs, 1-min candles
    python run_paper_bot.py --all --interval 1m --indir ./calib_15m
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from tournament.volatility_expansion_detector import VolatilityExpansionDetector

# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------
TOURNAMENT_PAIRS = [
    "BTC_USDT",
    "ETH_USDT",
    "SOL_USDT",
    "BNB_USDT",
]
DEFAULT_INTERVAL = "15m"
DEFAULT_INDIR = "./calib_15m"
DEFAULT_DAYS = 90


# ---------------------------------------------------------------------------
# ATR helper
# ---------------------------------------------------------------------------
def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df = df.copy()
    df["ATR"] = tr.rolling(period).mean()
    return df


# ---------------------------------------------------------------------------
# Single-pair paper replay
# ---------------------------------------------------------------------------
def run_pair(pair: str, csv_path: Path, interval: str) -> dict:
    """Replay one pair CSV and print entry signals. Returns summary stats."""
    if not csv_path.exists():
        print(f"  [SKIP] {pair}: CSV not found at {csv_path}")
        return {"pair": pair, "signals": 0, "skipped": True}

    print(f"\n{'='*50}")
    print(f"PAPER BOT  |  {pair}  |  {interval}")
    print(f"CSV: {csv_path}")
    print(f"{'='*50}")

    df = pd.read_csv(csv_path)
    df = compute_atr(df)

    detector = VolatilityExpansionDetector()
    signals = 0

    for i in range(50, len(df)):
        window = df.iloc[:i]
        current = window.iloc[-1]

        reading = detector.read(
            pair,
            window["high"].values,
            window["low"].values,
            window["close"].values,
            window["volume"].values,
        )

        state = getattr(reading, "state", None)

        if state == "COMPRESSED":
            atr = current["ATR"]
            price = current["close"]

            if np.isnan(atr):
                continue

            stop = price - atr
            target = price + (2 * atr)
            r_risk = atr
            r_reward = 2 * atr

            signals += 1
            print(f"[ENTRY #{signals}] {pair}  {interval}")
            print(f"  Price : {price:.4f}  ATR : {atr:.4f}")
            print(f"  SL    : {stop:.4f}  TP  : {target:.4f}")
            print(f"  Risk  : {r_risk:.4f}  Reward: {r_reward:.4f}  (2R)")
            print("-" * 40)

        time.sleep(0.01)  # slight throttle; remove for max speed

    print(f"\n[DONE] {pair}: {signals} entry signals found in {len(df)} candles")
    return {"pair": pair, "signals": signals, "candles": len(df), "skipped": False}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_csv_path(pair: str, interval: str, days: int, indir: Path) -> Path:
    return indir / f"{pair}_{interval}_{days}d.csv"


def main() -> None:
    p = argparse.ArgumentParser(description="Tournament paper-trading replay bot")
    p.add_argument(
        "--pair",
        default="BTC_USDT",
        help="Single pair to run (e.g. ETH_USDT). Ignored if --all is set.",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Run all TOURNAMENT_PAIRS sequentially.",
    )
    p.add_argument("--interval", default=DEFAULT_INTERVAL, help="Candle interval (e.g. 15m, 1h)")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS, help="Lookback days used when naming CSV")
    p.add_argument(
        "--indir",
        default=DEFAULT_INDIR,
        help="Directory containing OHLCV CSVs",
    )
    p.add_argument(
        "--csv",
        default=None,
        help="Explicit CSV path (overrides --indir naming convention). Only for single --pair.",
    )
    args = p.parse_args()

    indir = Path(args.indir)
    pairs = TOURNAMENT_PAIRS if args.all else [args.pair]

    results = []
    for pair in pairs:
        if args.csv and not args.all:
            csv_path = Path(args.csv)
        else:
            csv_path = build_csv_path(pair, args.interval, args.days, indir)
        results.append(run_pair(pair, csv_path, args.interval))

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for r in results:
        if r.get("skipped"):
            print(f"  {r['pair']:<12}  SKIPPED (CSV missing)")
        else:
            print(f"  {r['pair']:<12}  {r['signals']:>4} signals / {r['candles']} candles")


if __name__ == "__main__":
    main()
