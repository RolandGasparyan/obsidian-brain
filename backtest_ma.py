#!/usr/bin/env python3
"""
Simple trend-following strategies on real BTC/USD data.

Hypothesis tested by this script: a dumb moving-average rule (long above
MA → USDT below MA) beats the 9-agent consensus engine on both regimes.

Variants:
  MA50_direct   — long if close > 50d SMA, else USDT
  MA200_direct  — long if close > 200d SMA, else USDT
  MA50x200      — long if 50d SMA > 200d SMA (golden/death cross)
  MA20x50       — faster cross version
  BUY_AND_HOLD  — sanity baseline

Usage:
  python backtest_ma.py --csv data/btcusd_1min_latest.csv
  python backtest_ma.py --csv data/btcusd_1min_bull2024.csv
"""
import os, sys, csv, argparse
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar, T, C


TF_MIN = {"1d": 1440, "4h": 240, "1h": 60, "1w": 10080}


def load_1m(path):
    bars = []
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            bars.append(Bar(
                ts=int(row["timestamp"]),
                o=float(row["open"]), h=float(row["high"]),
                l=float(row["low"]),  c=float(row["close"]),
                v=float(row["volume"])))
    return bars


def aggregate(bars_1m, minutes):
    if minutes == 1: return bars_1m
    out, cur, bk = [], [], None
    for b in bars_1m:
        k = b.ts // (minutes * 60)
        if bk is None: bk = k
        if k != bk:
            if cur:
                out.append(Bar(cur[0].ts, cur[0].o,
                               max(x.h for x in cur), min(x.l for x in cur),
                               cur[-1].c, sum(x.v for x in cur)))
            cur = [b]; bk = k
        else:
            cur.append(b)
    if cur:
        out.append(Bar(cur[0].ts, cur[0].o,
                       max(x.h for x in cur), min(x.l for x in cur),
                       cur[-1].c, sum(x.v for x in cur)))
    return out


def sma(closes, period):
    out = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        out[i] = sum(closes[i - period + 1:i + 1]) / period
    return out


@dataclass
class TradeMA:
    entry_ts: int
    entry_px: float
    exit_ts:  int = 0
    exit_px:  float = 0.0
    pnl_pct:  float = 0.0
    reason:   str = ""


def run_strategy(name, bars, signal_fn, fee_rt=0.0025, balance=1000.0):
    """
    signal_fn(bars_so_far) -> True (want to be long) or False (want USDT).
    Enters/exits only on state changes. Fills at bar close.
    """
    in_pos = False
    entry_px = 0.0
    entry_ts = 0
    bal = balance
    units = 0.0
    trades = []

    for i in range(len(bars)):
        bars_so_far = bars[:i + 1]
        want_long = signal_fn(bars_so_far)
        if want_long is None:    # not enough history yet
            continue
        px = bars[i].c
        ts = bars[i].ts

        if want_long and not in_pos:
            # Enter: spend balance on BTC, pay fee
            entry_px = px
            entry_ts = ts
            cost = bal * (1 - fee_rt / 2)
            units = cost / px
            bal = 0.0
            in_pos = True
        elif (not want_long) and in_pos:
            # Exit: sell BTC for USDT, pay fee
            gross = units * px
            bal = gross * (1 - fee_rt / 2)
            pnl_pct = (px - entry_px) / entry_px * 100 - fee_rt * 100
            trades.append(TradeMA(entry_ts, entry_px, ts, px, pnl_pct, "MA_FLIP"))
            units = 0.0
            in_pos = False

    # Close any remaining position at last bar
    if in_pos:
        px = bars[-1].c
        bal = units * px * (1 - fee_rt / 2)
        pnl_pct = (px - entry_px) / entry_px * 100 - fee_rt * 100
        trades.append(TradeMA(entry_ts, entry_px, bars[-1].ts, px, pnl_pct, "END"))

    wins = [t for t in trades if t.pnl_pct > 0]
    wr   = len(wins) / len(trades) * 100 if trades else 0
    pnl_pct_sum = sum(t.pnl_pct for t in trades)
    roi = (bal - balance) / balance * 100
    return {"name": name, "trades": len(trades), "wr": wr,
            "roi": roi, "end_bal": bal, "wins": len(wins),
            "avg_pct": pnl_pct_sum / len(trades) if trades else 0.0}


def make_signal_above_sma(period, closes):
    ma = sma(closes, period)
    def f(bars_so_far):
        idx = len(bars_so_far) - 1
        if ma[idx] is None: return None
        return bars_so_far[-1].c > ma[idx]
    return f


def make_signal_ma_cross(fast, slow, closes):
    fast_ma = sma(closes, fast)
    slow_ma = sma(closes, slow)
    def f(bars_so_far):
        idx = len(bars_so_far) - 1
        if fast_ma[idx] is None or slow_ma[idx] is None: return None
        return fast_ma[idx] > slow_ma[idx]
    return f


def make_signal_ma_with_weekly_filter(daily_period, weekly_period,
                                      daily_closes, weekly_bars):
    """Long if: daily close > daily SMA(N) AND weekly close > weekly SMA(M).
    `weekly_bars` are pre-aggregated 1w bars; we look up the latest weekly
    bar whose ts <= the current daily bar's ts.
    """
    daily_ma  = sma(daily_closes, daily_period)
    weekly_cl = [b.c for b in weekly_bars]
    weekly_ma = sma(weekly_cl, weekly_period)

    def f(bars_so_far):
        idx = len(bars_so_far) - 1
        if daily_ma[idx] is None: return None
        cur_ts = bars_so_far[-1].ts
        # Find the most recent weekly bar at or before cur_ts
        w_idx = None
        for i in range(len(weekly_bars) - 1, -1, -1):
            if weekly_bars[i].ts <= cur_ts:
                w_idx = i; break
        if w_idx is None or weekly_ma[w_idx] is None: return None
        daily_ok  = bars_so_far[-1].c > daily_ma[idx]
        weekly_ok = weekly_bars[w_idx].c > weekly_ma[w_idx]
        return daily_ok and weekly_ok
    return f


def buy_and_hold(bars, balance=1000.0, fee_rt=0.0025):
    if not bars: return {"name": "BUY_AND_HOLD", "trades": 1, "wr": 0, "roi": 0,
                          "end_bal": balance, "wins": 0, "avg_pct": 0}
    entry = bars[0].c
    exit_ = bars[-1].c
    units = balance * (1 - fee_rt / 2) / entry
    final = units * exit_ * (1 - fee_rt / 2)
    roi   = (final - balance) / balance * 100
    pnl   = (exit_ - entry) / entry * 100 - fee_rt * 100
    return {"name": "BUY_AND_HOLD", "trades": 1,
            "wr": 100.0 if roi > 0 else 0.0, "roi": roi,
            "end_bal": final, "wins": 1 if roi > 0 else 0, "avg_pct": pnl}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv",       required=True)
    ap.add_argument("--timeframe", default="1d", choices=list(TF_MIN.keys()))
    ap.add_argument("--balance",   type=float, default=1000.0)
    args = ap.parse_args()

    bars_1m = load_1m(args.csv)
    bars    = aggregate(bars_1m, TF_MIN[args.timeframe])
    closes  = [b.c for b in bars]
    weekly_bars = aggregate(bars_1m, TF_MIN["1w"])

    from datetime import datetime, timezone
    t0 = datetime.fromtimestamp(bars[0].ts,  tz=timezone.utc)
    t1 = datetime.fromtimestamp(bars[-1].ts, tz=timezone.utc)
    span = (bars[-1].ts - bars[0].ts) / 86400
    print("═" * 88)
    print(f"  MA STRATEGY BACKTEST — {os.path.basename(args.csv)}")
    print("═" * 88)
    print(f"  Timeframe: {args.timeframe}  |  Bars: {len(bars)}  |  Span: {span:.0f} days")
    print(f"  Range: {t0.date()} → {t1.date()}  |  ${bars[0].c:.0f} → ${bars[-1].c:.0f}")
    print(f"  Balance: ${args.balance:.2f}  |  Fees: 0.25% round-trip\n")

    results = []
    results.append(buy_and_hold(bars, args.balance))
    results.append(run_strategy("MA50_direct",
        bars, make_signal_above_sma(50, closes), balance=args.balance))
    results.append(run_strategy("MA100_direct",
        bars, make_signal_above_sma(100, closes), balance=args.balance))
    results.append(run_strategy("MA200_direct",
        bars, make_signal_above_sma(200, closes), balance=args.balance))
    results.append(run_strategy("MA50x200_cross",
        bars, make_signal_ma_cross(50, 200, closes), balance=args.balance))
    results.append(run_strategy("MA20x50_cross",
        bars, make_signal_ma_cross(20, 50, closes), balance=args.balance))
    # Weekly-filter variants
    if len(weekly_bars) >= 12:
        results.append(run_strategy("MA50_+_W10",
            bars, make_signal_ma_with_weekly_filter(50, 10, closes, weekly_bars),
            balance=args.balance))
        results.append(run_strategy("MA50_+_W20",
            bars, make_signal_ma_with_weekly_filter(50, 20, closes, weekly_bars),
            balance=args.balance))
    else:
        print(f"  (skipping weekly-filter variants: only {len(weekly_bars)} weekly bars)")

    for r in results:
        print(f"  {r['name']:<20} trades={r['trades']:>3}  wr={r['wr']:5.1f}%  "
              f"avg/trade={r['avg_pct']:+6.2f}%  ROI={r['roi']:+7.2f}%  "
              f"end=${r['end_bal']:.2f}")

    print("\n" + "═" * 88)
    print(f"  RANKING — {os.path.basename(args.csv)}")
    print("═" * 88)
    for r in sorted(results, key=lambda x: -x["roi"]):
        print(f"  {r['name']:<20} ROI {r['roi']:+8.2f}%  trades={r['trades']:>3}  "
              f"wr={r['wr']:5.1f}%")
    print("═" * 88)


if __name__ == "__main__":
    main()
