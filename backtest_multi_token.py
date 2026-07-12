#!/usr/bin/env python3
"""
Multi-token MA strategy backtest — fetches daily bars from Gate.io public API
and runs MA50, MA50+W10, MA50+W20, and buy-and-hold on each token.

Gate.io free public API gives up to 1000 daily bars per pair (~2.7 years).

Usage:
  python backtest_multi_token.py
  python backtest_multi_token.py --pairs BTC_USDT ETH_USDT SOL_USDT
  python backtest_multi_token.py --balance 5000 --interval 1d
"""
import argparse
import os
import sys
import time
from typing import List

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar
from backtest_ma import (
    aggregate,
    buy_and_hold,
    make_signal_above_sma,
    make_signal_ma_with_weekly_filter,
    run_strategy,
    TF_MIN,
)


DEFAULT_PAIRS = [
    "BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT",
    "XRP_USDT", "ADA_USDT", "DOGE_USDT", "AVAX_USDT",
    "LINK_USDT", "DOT_USDT",
]


def fetch_gateio_bars(pair: str, interval: str = "1d", limit: int = 1000) -> List[Bar]:
    """
    Gate.io returns: [[ts, volume_quote, close, high, low, open, volume_base, finalized], ...]
    Returns a list of Bar objects sorted oldest → newest.
    """
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {"currency_pair": pair, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    raw = r.json()
    bars = []
    for row in raw:
        try:
            bars.append(Bar(
                ts=int(row[0]),
                o=float(row[5]), h=float(row[3]),
                l=float(row[4]), c=float(row[2]),
                v=float(row[6]),
            ))
        except (IndexError, ValueError):
            continue
    bars.sort(key=lambda b: b.ts)
    return bars


def backtest_one(pair: str, bars: List[Bar], balance: float = 1000.0, fee_rt: float = 0.0025):
    """Run MA suite on one token's bars and return a list of result dicts."""
    closes = [b.c for b in bars]
    # For 1d input we still want a weekly aggregation; build synthetic weekly
    # by grouping 7 daily bars into 1 weekly OHLC.
    def aggregate_daily_to_weekly(dbars):
        out = []
        for i in range(0, len(dbars), 7):
            chunk = dbars[i:i + 7]
            if not chunk:
                continue
            out.append(Bar(
                ts=chunk[0].ts,
                o=chunk[0].o,
                h=max(x.h for x in chunk),
                l=min(x.l for x in chunk),
                c=chunk[-1].c,
                v=sum(x.v for x in chunk),
            ))
        return out
    weekly_bars = aggregate_daily_to_weekly(bars)

    results = []
    results.append({"pair": pair, **buy_and_hold(bars, balance, fee_rt)})
    if len(bars) >= 50:
        results.append({"pair": pair, **run_strategy(
            "MA50_direct", bars, make_signal_above_sma(50, closes),
            fee_rt=fee_rt, balance=balance)})
    if len(bars) >= 100:
        results.append({"pair": pair, **run_strategy(
            "MA100_direct", bars, make_signal_above_sma(100, closes),
            fee_rt=fee_rt, balance=balance)})
    if len(bars) >= 50 and len(weekly_bars) >= 12:
        results.append({"pair": pair, **run_strategy(
            "MA50_W10", bars,
            make_signal_ma_with_weekly_filter(50, 10, closes, weekly_bars),
            fee_rt=fee_rt, balance=balance)})
        results.append({"pair": pair, **run_strategy(
            "MA50_W20", bars,
            make_signal_ma_with_weekly_filter(50, 20, closes, weekly_bars),
            fee_rt=fee_rt, balance=balance)})
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=DEFAULT_PAIRS,
                    help="Gate.io pairs, e.g. BTC_USDT ETH_USDT")
    ap.add_argument("--interval", default="1d", choices=["1d", "4h", "1h"])
    ap.add_argument("--limit", type=int, default=1000, help="bars per pair (max 1000)")
    ap.add_argument("--balance", type=float, default=1000.0)
    args = ap.parse_args()

    print("═" * 100)
    print(f"  MULTI-TOKEN BACKTEST · {args.interval} · {args.limit} bars · ${args.balance:.0f} start · 0.25% RT fees")
    print("═" * 100)

    all_rows = []
    for pair in args.pairs:
        try:
            print(f"  → fetching {pair} …", end=" ", flush=True)
            bars = fetch_gateio_bars(pair, args.interval, args.limit)
            if not bars or len(bars) < 50:
                print(f"SKIP (only {len(bars)} bars)")
                continue
            span_days = (bars[-1].ts - bars[0].ts) / 86400
            print(f"{len(bars)} bars, {span_days:.0f} days, ${bars[0].c:.2f} → ${bars[-1].c:.2f}")
            rows = backtest_one(pair, bars, args.balance)
            all_rows.extend(rows)
            time.sleep(0.25)   # polite to the public API
        except Exception as e:
            print(f"ERR: {e}")

    if not all_rows:
        print("No results.")
        return

    # ─ per-token table
    print()
    print("═" * 100)
    print(f"  {'PAIR':<12}  {'STRATEGY':<16}  {'TRADES':>6}  {'WR':>6}  {'AVG/T':>8}  {'ROI':>10}  {'END $':>12}")
    print("─" * 100)
    last_pair = None
    for r in all_rows:
        if last_pair and last_pair != r['pair']:
            print("  " + "·" * 96)
        print(f"  {r['pair']:<12}  {r['name']:<16}  {r['trades']:>6}  "
              f"{r['wr']:>5.1f}%  {r['avg_pct']:>+7.2f}%  {r['roi']:>+9.2f}%  ${r['end_bal']:>10.2f}")
        last_pair = r['pair']

    # ─ MA50+W10 leaderboard
    w10 = [r for r in all_rows if r['name'] == 'MA50_W10']
    bh  = [r for r in all_rows if r['name'] == 'BUY_AND_HOLD']
    if w10:
        print()
        print("═" * 100)
        print("  MA50 + W10  VS  BUY & HOLD")
        print("═" * 100)
        print(f"  {'PAIR':<12}  {'MA50+W10 ROI':>14}  {'B&H ROI':>12}  {'Δ (MA - B&H)':>14}  WINNER")
        print("─" * 100)
        by_pair_bh = {r['pair']: r for r in bh}
        for r in sorted(w10, key=lambda x: -x['roi']):
            b = by_pair_bh.get(r['pair'], {})
            b_roi = b.get('roi', 0.0)
            delta = r['roi'] - b_roi
            winner = "MA50+W10 ✓" if delta > 0 else "B&H"
            print(f"  {r['pair']:<12}  {r['roi']:>+12.2f}%  {b_roi:>+10.2f}%  "
                  f"{delta:>+12.2f}%  {winner}")
        # aggregate
        avg_ma = sum(r['roi'] for r in w10) / len(w10)
        avg_bh = sum(r['roi'] for r in bh) / len(bh) if bh else 0.0
        print("─" * 100)
        print(f"  {'AVG':<12}  {avg_ma:>+12.2f}%  {avg_bh:>+10.2f}%  "
              f"{avg_ma - avg_bh:>+12.2f}%")
        print("═" * 100)


if __name__ == "__main__":
    main()
