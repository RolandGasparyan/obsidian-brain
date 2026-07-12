#!/usr/bin/env python3
"""
MA50+W10 — independent validation harness.

Re-implements the MA50 + weekly-SMA10 rule that CLAUDE.md / MA_STRATEGY.md
claims returned +74.9% over 24 months and +3,427% across a 7.5-year regime
chain. Measures it on real daily BTC closes with a fee sweep, walk-forward,
Monte-Carlo permutation, and a claim-consistency note.

Strategy (verbatim from MA_STRATEGY.md):
  Hold 100% BTC when daily close > 50-day SMA AND weekly close > 10-week SMA;
  else 100% USDT. Flips state on signal change only. Fees applied per flip.

DATA: 100 real daily BTC-USDT closes from Binance (a fresh-fetched window,
embedded for reproducibility). NOT enough history for a 24-month verdict —
this is a method-level demo. The script also supports --live for a full
1000-bar run on the VPS via fetch_gateio_bars.

NO LIVE TRADING. This script only reads numbers and prints metrics.
"""
from __future__ import annotations

import argparse
import random
from dataclasses import dataclass

# ── 100 real daily BTC-USDT closes (Binance, fetched 2026-05-29) ────────
# One close per line, oldest first.
CLOSES_CSV = """
67003.73
68020.01
67975.93
67643.40
64656.02
64058.15
67988.04
67485.18
65872.10
66973.26
65776.47
68830.06
68338.00
72666.77
70890.72
68114.02
67262.91
65971.20
68432.16
69948.63
70191.86
70541.34
70930.00
71211.95
72815.24
74884.67
73909.36
71246.54
69930.00
70510.73
68918.12
67859.00
70906.45
70556.74
71336.53
68820.31
66407.28
66377.03
66010.93
66797.37
68284.48
68113.92
66901.99
66964.30
67300.42
69034.18
68853.66
71924.22
71069.93
71787.97
72962.70
73043.16
70740.98
74417.99
74131.55
74809.99
75154.29
77072.00
75691.76
73801.79
75840.97
76336.15
78178.23
78257.48
77437.13
77625.00
78657.55
77371.32
76342.77
75780.00
76346.57
78231.13
78686.85
78568.57
79861.01
80905.52
81447.01
80006.00
80193.17
80678.40
82210.07
81745.65
80504.47
79313.61
81089.99
79113.21
78148.05
77457.67
77001.87
76834.36
77552.23
77615.52
75539.50
76752.01
77064.96
77322.01
75930.01
74449.30
73617.51
72926.00
"""

DAILY_SECS = 86400
WEEKLY_SECS = 7 * DAILY_SECS
DAILY_SMA = 50
WEEKLY_SMA = 10
DEFAULT_BASE_TS = 1771459200       # 2026-02-18 (first bar in embedded window)


@dataclass
class Bar:
    ts: int
    c: float


def parse_closes(block):
    return [float(x) for x in block.strip().splitlines()]


def make_bars(closes, base_ts=DEFAULT_BASE_TS):
    return [Bar(base_ts + i * DAILY_SECS, c) for i, c in enumerate(closes)]


def aggregate_weekly(daily):
    """Group consecutive 7 daily bars; weekly close = last daily close in week."""
    out, cur = [], []
    for b in daily:
        cur.append(b)
        if len(cur) == 7:
            out.append(Bar(cur[0].ts, cur[-1].c))
            cur = []
    if cur:
        out.append(Bar(cur[0].ts, cur[-1].c))
    return out


def sma(values, period):
    out = [None] * len(values)
    for i in range(period - 1, len(values)):
        out[i] = sum(values[i - period + 1:i + 1]) / period
    return out


def backtest(daily, weekly, daily_period, weekly_period, fee_rt):
    """Long-only BTC vs USDT flip on daily MA + weekly MA filter.
    Returns (roi_pct, num_flips, num_in_market_days, trades_list)."""
    if len(daily) < daily_period or len(weekly) < weekly_period:
        return None
    d_closes = [b.c for b in daily]
    w_closes = [b.c for b in weekly]
    d_ma = sma(d_closes, daily_period)
    w_ma = sma(w_closes, weekly_period)

    balance = 1000.0
    units = 0.0
    in_pos = False
    entry_px = 0.0
    trades = []
    in_market = 0

    for i, b in enumerate(daily):
        if d_ma[i] is None:
            continue
        # find latest weekly bar at or before this daily ts
        w_idx = None
        for j in range(len(weekly) - 1, -1, -1):
            if weekly[j].ts <= b.ts:
                w_idx = j
                break
        if w_idx is None or w_ma[w_idx] is None:
            continue
        daily_ok = b.c > d_ma[i]
        weekly_ok = weekly[w_idx].c > w_ma[w_idx]
        want_long = daily_ok and weekly_ok

        if want_long and not in_pos:
            entry_px = b.c
            cost = balance * (1 - fee_rt / 2)
            units = cost / b.c
            balance = 0.0
            in_pos = True
        elif (not want_long) and in_pos:
            balance = units * b.c * (1 - fee_rt / 2)
            pnl_pct = (b.c - entry_px) / entry_px * 100 - fee_rt * 100
            trades.append(pnl_pct)
            units = 0.0
            in_pos = False
        if in_pos:
            in_market += 1

    if in_pos:
        last = daily[-1].c
        balance = units * last * (1 - fee_rt / 2)
        pnl_pct = (last - entry_px) / entry_px * 100 - fee_rt * 100
        trades.append(pnl_pct)
    roi = (balance - 1000.0) / 1000.0 * 100
    return roi, len(trades), in_market, trades


def buy_and_hold(daily, fee_rt):
    entry = daily[0].c
    exit_ = daily[-1].c
    units = 1000.0 * (1 - fee_rt / 2) / entry
    final = units * exit_ * (1 - fee_rt / 2)
    return (final - 1000.0) / 1000.0 * 100


def walk_forward(daily, weekly, n_seg=3, fee_rt=0.0025):
    out = []
    for s in range(n_seg):
        L = len(daily)
        a, b_ = L * s // n_seg, L * (s + 1) // n_seg
        seg = daily[a:b_]
        seg_w = [w for w in weekly if w.ts <= seg[-1].ts] if seg else []
        r = backtest(seg, seg_w, DAILY_SMA, WEEKLY_SMA, fee_rt)
        bh = buy_and_hold(seg, fee_rt) if seg else 0
        out.append((r, bh, len(seg)))
    return out


def monte_carlo(daily, weekly, n_runs=200, fee_rt=0.0025, seed=42):
    """Shuffle daily closes (preserving the marginal price distribution but
    destroying any trend). Re-aggregate weeklies from the shuffled dailies
    and re-run. Real ROI in the top 5% => SIGNIFICANT."""
    rng = random.Random(seed)
    real = backtest(daily, weekly, DAILY_SMA, WEEKLY_SMA, fee_rt)
    real_roi = real[0] if real else 0
    closes = [b.c for b in daily]
    base_ts = daily[0].ts
    mc = []
    for _ in range(n_runs):
        shuffled = closes.copy()
        rng.shuffle(shuffled)
        sd = [Bar(base_ts + i * DAILY_SECS, c) for i, c in enumerate(shuffled)]
        sw = aggregate_weekly(sd)
        r = backtest(sd, sw, DAILY_SMA, WEEKLY_SMA, fee_rt)
        mc.append(r[0] if r else 0)
    mc.sort()
    beats = sum(1 for v in mc if real_roi > v)
    pct = beats / len(mc) * 100 if mc else 0
    return {"real": real_roi, "mc_mean": sum(mc) / len(mc) if mc else 0,
            "mc_p95": mc[int(len(mc) * 0.95)] if mc else 0,
            "percentile": pct,
            "verdict": "SIGNIFICANT" if pct >= 95 else
                       "MARGINAL" if pct >= 80 else "INDISTINGUISHABLE FROM NOISE"}


def claim_check(real_roi, span_days, bh_roi):
    """MA_STRATEGY.md claims +74.9% over 24 months. This window is much
    shorter; just check (a) does the strategy beat buy-and-hold? and (b)
    flag if the window is too short for a deployment-grade verdict."""
    notes = []
    notes.append(("beats buy-and-hold", real_roi > bh_roi,
                  f"strategy {real_roi:+.2f}% vs B&H {bh_roi:+.2f}%"))
    notes.append(("window >= 24 months", span_days >= 720,
                  f"have {span_days} days ({span_days/30:.1f} months)"))
    return notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="pull 1000 real daily BTC bars from Gate.io (VPS only)")
    args = ap.parse_args()

    if args.live:
        from backtest_multi_token import fetch_gateio_bars
        raw = fetch_gateio_bars("BTC_USDT", "1d", 1000)
        daily = [Bar(b.ts, b.c) for b in raw]
        note = f"LIVE Gate.io 1d · {len(daily)} bars"
    else:
        closes = parse_closes(CLOSES_CSV)
        daily = make_bars(closes)
        note = f"embedded sample · {len(daily)} bars"

    weekly = aggregate_weekly(daily)
    span_days = (daily[-1].ts - daily[0].ts) // DAILY_SECS

    print("=" * 78)
    print("  MA50 + W10 — independent validation on real daily BTC closes")
    print(f"  {note}  |  span {span_days} days  |  weekly bars {len(weekly)}")
    print("=" * 78)

    # Fee sweep
    print(f"\n  {'fee RT':>7} {'trades':>7} {'in-mkt':>7} "
          f"{'ROI%':>8} {'B&H%':>8} {'edge%':>8}")
    print("  " + "-" * 55)
    headline = None
    for fee in (0.0, 0.0010, 0.0025, 0.0050):
        r = backtest(daily, weekly, DAILY_SMA, WEEKLY_SMA, fee)
        bh = buy_and_hold(daily, fee)
        if r is None:
            print(f"  {fee*100:>6.2f}%   insufficient history")
            continue
        roi, ntr, in_mkt, _ = r
        edge = roi - bh
        print(f"  {fee*100:>6.2f}% {ntr:>7} {in_mkt:>7} "
              f"{roi:>+7.2f}% {bh:>+7.2f}% {edge:>+7.2f}%")
        if fee == 0.0025:
            headline = (roi, bh)

    # Walk-forward
    print("\n  GATE A — WALK-FORWARD (3 segments, fee 0.25% RT)")
    wf = walk_forward(daily, weekly, n_seg=3, fee_rt=0.0025)
    wins = 0
    for i, (r, bh, n) in enumerate(wf, 1):
        if r is None:
            print(f"    seg {i}: {n} bars — insufficient history for MA50")
            continue
        roi, ntr, _, _ = r
        edge = roi - bh
        if edge > 0:
            wins += 1
        print(f"    seg {i}: {n} bars  ROI {roi:+6.2f}%  "
              f"B&H {bh:+6.2f}%  edge {edge:+6.2f}%  trades {ntr}")
    print(f"    -> {wins}/{len(wf)} segments beat B&H")

    # Monte-Carlo permutation
    print("\n  GATE B — MONTE-CARLO PERMUTATION (200 shuffles, fee 0.25% RT)")
    mc = monte_carlo(daily, weekly)
    print(f"    real ROI:           {mc['real']:+.2f}%")
    print(f"    shuffled mean:      {mc['mc_mean']:+.2f}%")
    print(f"    shuffled p95:       {mc['mc_p95']:+.2f}%")
    print(f"    real beats {mc['percentile']:.1f}% of shuffles")
    print(f"    Verdict: **{mc['verdict']}**")

    # Claim consistency
    print("\n  GATE C — CLAIM CONSISTENCY (MA_STRATEGY.md)")
    if headline:
        cc = claim_check(headline[0], span_days, headline[1])
        for name, ok, detail in cc:
            print(f"    [{'OK ' if ok else 'FAIL'}] {name:<25} {detail}")

    # Consolidated verdict
    print("\n  " + "=" * 64)
    print("  CONSOLIDATED VERDICT")
    edge_at_real_fees = (headline[0] - headline[1]) if headline else 0
    if headline is None or span_days < 720:
        print(f"  - Sample too small for a deployment verdict "
              f"({span_days} days vs 720 needed for 24m claim).")
        print("  - For a real verdict run:  python ma50w10_validate.py --live")
    if headline:
        print(f"  - On this window: ROI {headline[0]:+.2f}% vs B&H "
              f"{headline[1]:+.2f}% (edge {edge_at_real_fees:+.2f}%)")
    print(f"  - Walk-forward:  {wins}/{len(wf)} segments beat B&H")
    print(f"  - Monte-Carlo:   {mc['verdict']}")
    print("=" * 78)


if __name__ == "__main__":
    main()
