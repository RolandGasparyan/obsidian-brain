#!/usr/bin/env python3
"""
Mean-reversion strategies + ensemble with MA20+W5.

Path-A result: plain MA20+W5 is our best trend rule but fails the ship
bar (MC 93–97%, rolling 2–3/5). Path-B hypothesis: mean-reversion and
trend-follow have *mechanically decorrelated* failure modes. MR works
in chop; trend works in trends. Ensembling them may produce a combined
P&L whose drawdowns partially cancel, lifting the MC percentile above
99 and the rolling wins above 4/5.

Strategies tested:

  RSI2     — Connors-style: buy when RSI(2) < 10, sell when RSI(2) > 70.
             Fast-snap mean reversion, many small trades.

  BB_FADE  — Bollinger bounce: buy when close < lower band (20d SMA -
             2σ), exit when close crosses above the 20d SMA. Patient
             mean reversion, fewer trades, slightly larger moves.

  ENSEMBLE — 50/50 capital split: half runs MA20+W5, half runs the best
             MR strategy. Each half independently long or in cash.

Ship gate is the same:
  MC percentile ≥ 99 on ≥ 3 pairs
  AND rolling wins ≥ 4/5 on ≥ 3 pairs
  AND recent 6-month ROI > 0 on all 4 pairs

Usage:
  python mean_reversion.py
  python mean_reversion.py --mc-runs 200
  python mean_reversion.py --pairs ETH_USDT SOL_USDT
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from typing import Callable, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar
from backtest_multi_token import fetch_gateio_bars
from backtest_ma import buy_and_hold, sma


PAIRS_DEFAULT = ["ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]
FEE_RT         = 0.0025


# ── helpers ──────────────────────────────────────────────────────────
def _sharpe(rets, ann=math.sqrt(365)):
    if not rets: return 0.0
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)
    sd = math.sqrt(var)
    return (mu / sd) * ann if sd else 0.0


def _weekly(bars, per=7):
    out = []
    for i in range(0, len(bars), per):
        c = bars[i:i + per]
        if not c: continue
        out.append(Bar(c[0].ts, c[0].o, max(x.h for x in c),
                       min(x.l for x in c), c[-1].c, sum(x.v for x in c)))
    return out


def _rsi(closes: List[float], period: int) -> List[float]:
    """Wilder's RSI. Returns None-padded list of same length."""
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        if d > 0: gains += d
        else:     losses -= d
    avg_g = gains / period
    avg_l = losses / period
    if avg_l == 0:
        out[period] = 100.0
    else:
        rs = avg_g / avg_l
        out[period] = 100.0 - 100.0 / (1 + rs)
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        g = max(0.0, d)
        l = max(0.0, -d)
        avg_g = (avg_g * (period - 1) + g) / period
        avg_l = (avg_l * (period - 1) + l) / period
        if avg_l == 0:
            out[i] = 100.0
        else:
            rs = avg_g / avg_l
            out[i] = 100.0 - 100.0 / (1 + rs)
    return out


def _stdev(closes: List[float], idx: int, window: int) -> float:
    if idx < window - 1:
        return 0.0
    w = closes[idx - window + 1:idx + 1]
    mu = sum(w) / len(w)
    v  = sum((x - mu) ** 2 for x in w) / max(1, len(w) - 1)
    return math.sqrt(v)


# ── signal builders ─────────────────────────────────────────────────
def signal_rsi2(closes: List[float],
                bars: List[Bar],
                lower: float = 10.0,
                upper: float = 70.0) -> Callable[[int, bool], bool]:
    rsi = _rsi(closes, 2)
    def want(i: int, in_pos: bool) -> bool:
        r = rsi[i]
        if r is None: return in_pos  # hold current state
        if in_pos:
            return r < upper   # exit above upper threshold
        return r < lower       # enter below lower threshold
    return want


def signal_bb_fade(closes: List[float],
                   bars: List[Bar],
                   ma_period: int = 20,
                   k: float = 2.0) -> Callable[[int, bool], bool]:
    ma = sma(closes, ma_period)
    def want(i: int, in_pos: bool) -> bool:
        if ma[i] is None: return in_pos
        sd = _stdev(closes, i, ma_period)
        lower_band = ma[i] - k * sd
        if in_pos:
            return closes[i] < ma[i]   # exit when back above mean
        return closes[i] < lower_band  # enter when at/below lower band
    return want


def signal_ma20w5(closes: List[float],
                  bars: List[Bar],
                  ma_p: int = 20,
                  weekly_p: int = 5,
                  hyst: float = 0.0025) -> Callable[[int, bool], bool]:
    weekly = _weekly(bars) if weekly_p > 0 else []
    ma_series = sma(closes, ma_p)
    w_ma      = sma([b.c for b in weekly], weekly_p) if weekly_p > 0 else []
    def want(i: int, in_pos: bool) -> bool:
        if ma_series[i] is None: return False
        m = ma_series[i]
        px = closes[i]
        upper = m * (1 + hyst); lower = m * (1 - hyst)
        d_ok = (px >= lower) if in_pos else (px > upper)
        if weekly_p == 0: return d_ok
        cur_ts = bars[i].ts
        w_idx = None
        for j in range(len(weekly) - 1, -1, -1):
            if weekly[j].ts <= cur_ts:
                w_idx = j; break
        if w_idx is None or w_ma[w_idx] is None: return False
        w_px = weekly[w_idx].c; wm = w_ma[w_idx]
        w_u = wm * (1 + hyst); w_l = wm * (1 - hyst)
        w_ok = (w_px >= w_l) if in_pos else (w_px > w_u)
        return d_ok and w_ok
    return want


# ── generic replayer ────────────────────────────────────────────────
def replay(bars: List[Bar],
           signal_fn: Callable[[int, bool], bool],
           start_bal: float = 1000.0) -> Tuple[List[float], List[float], int]:
    bal, units, in_pos = start_bal, 0.0, False
    eq_curve, rets, trades = [], [], 0
    prev_eq = start_bal
    for i in range(len(bars)):
        px = bars[i].c
        want = signal_fn(i, in_pos)
        if want and not in_pos:
            units = bal * (1 - FEE_RT / 2) / px
            bal, in_pos = 0.0, True
            trades += 1
        elif (not want) and in_pos:
            bal = units * px * (1 - FEE_RT / 2)
            units, in_pos = 0.0, False
            trades += 1
        eq = bal + units * px
        eq_curve.append(eq)
        if prev_eq > 0:
            rets.append((eq - prev_eq) / prev_eq * 100)
        prev_eq = eq
    return rets, eq_curve, trades


def replay_ensemble(bars: List[Bar],
                    signal_fn_a: Callable,
                    signal_fn_b: Callable,
                    start_bal: float = 1000.0,
                    split: float = 0.5) -> Tuple[List[float], List[float], int]:
    """
    50/50 capital split — each half runs independently. Return the
    combined equity curve and total trade count.
    """
    bal_a = start_bal * split
    bal_b = start_bal * (1 - split)
    units_a = units_b = 0.0
    in_a = in_b = False
    eq_curve, rets, trades = [], [], 0
    prev_eq = start_bal
    for i in range(len(bars)):
        px = bars[i].c
        # Half A
        want_a = signal_fn_a(i, in_a)
        if want_a and not in_a:
            units_a = bal_a * (1 - FEE_RT / 2) / px
            bal_a, in_a = 0.0, True
            trades += 1
        elif (not want_a) and in_a:
            bal_a = units_a * px * (1 - FEE_RT / 2)
            units_a, in_a = 0.0, False
            trades += 1
        # Half B
        want_b = signal_fn_b(i, in_b)
        if want_b and not in_b:
            units_b = bal_b * (1 - FEE_RT / 2) / px
            bal_b, in_b = 0.0, True
            trades += 1
        elif (not want_b) and in_b:
            bal_b = units_b * px * (1 - FEE_RT / 2)
            units_b, in_b = 0.0, False
            trades += 1
        eq = bal_a + units_a * px + bal_b + units_b * px
        eq_curve.append(eq)
        if prev_eq > 0:
            rets.append((eq - prev_eq) / prev_eq * 100)
        prev_eq = eq
    return rets, eq_curve, trades


# ── harness metrics (same bar as walk_forward.py) ────────────────────
def mc_percentile(bars: List[Bar], build_signal_fn: Callable,
                  n_runs: int, seed: int = 42) -> float:
    rng = random.Random(seed)
    closes = [b.c for b in bars]
    sig = build_signal_fn(closes, bars)
    real_r, _, _ = replay(bars, sig)
    real_s = _sharpe(real_r)
    log_r = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    wins = 0
    for _ in range(n_runs):
        sh = list(log_r); rng.shuffle(sh)
        px = [closes[0]]
        for r in sh:
            px.append(px[-1] * math.exp(r))
        synth_bars   = [Bar(bars[i].ts, c, c, c, c, 1.0) for i, c in enumerate(px)]
        synth_closes = px
        s2 = build_signal_fn(synth_closes, synth_bars)
        r2, _, _ = replay(synth_bars, s2)
        if real_s > _sharpe(r2):
            wins += 1
    return wins / n_runs * 100.0


def mc_percentile_ensemble(bars, build_a, build_b, n_runs, seed=42):
    rng = random.Random(seed)
    closes = [b.c for b in bars]
    sa = build_a(closes, bars)
    sb = build_b(closes, bars)
    real_r, _, _ = replay_ensemble(bars, sa, sb)
    real_s = _sharpe(real_r)
    log_r = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    wins = 0
    for _ in range(n_runs):
        sh = list(log_r); rng.shuffle(sh)
        px = [closes[0]]
        for r in sh:
            px.append(px[-1] * math.exp(r))
        synth_bars   = [Bar(bars[i].ts, c, c, c, c, 1.0) for i, c in enumerate(px)]
        synth_closes = px
        sa2 = build_a(synth_closes, synth_bars)
        sb2 = build_b(synth_closes, synth_bars)
        r2, _, _ = replay_ensemble(synth_bars, sa2, sb2)
        if real_s > _sharpe(r2): wins += 1
    return wins / n_runs * 100.0


def rolling_wins(bars, build_signal_fn, n_windows=5):
    n = len(bars)
    if n < 300: return 0, 0
    w_size = n // (n_windows + 1)
    wins = total = 0
    for i in range(n_windows):
        start = i * (n - w_size) // max(1, n_windows - 1) if n_windows > 1 else 0
        end = start + w_size
        window = bars[start:end]
        if len(window) < 150: continue
        cut = int(len(window) * 0.5)
        test = window[cut:]
        if len(test) < 50: continue
        closes = [b.c for b in test]
        sig = build_signal_fn(closes, test)
        _, eq, _ = replay(test, sig)
        ma_roi = (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0
        bh_roi = buy_and_hold(test)["roi"]
        if ma_roi > bh_roi: wins += 1
        total += 1
    return wins, total


def rolling_wins_ensemble(bars, build_a, build_b, n_windows=5):
    n = len(bars)
    if n < 300: return 0, 0
    w_size = n // (n_windows + 1)
    wins = total = 0
    for i in range(n_windows):
        start = i * (n - w_size) // max(1, n_windows - 1) if n_windows > 1 else 0
        end = start + w_size
        window = bars[start:end]
        if len(window) < 150: continue
        cut = int(len(window) * 0.5)
        test = window[cut:]
        if len(test) < 50: continue
        closes = [b.c for b in test]
        sa = build_a(closes, test); sb = build_b(closes, test)
        _, eq, _ = replay_ensemble(test, sa, sb)
        roi = (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0
        bh_roi = buy_and_hold(test)["roi"]
        if roi > bh_roi: wins += 1
        total += 1
    return wins, total


def recent_roi(bars, build_signal_fn, tail=176):
    if len(bars) < tail + 50: return 0.0
    tail_bars = bars[-tail:]
    closes = [b.c for b in tail_bars]
    sig = build_signal_fn(closes, tail_bars)
    _, eq, _ = replay(tail_bars, sig)
    return (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0


def recent_roi_ensemble(bars, build_a, build_b, tail=176):
    if len(bars) < tail + 50: return 0.0
    tail_bars = bars[-tail:]
    closes = [b.c for b in tail_bars]
    sa = build_a(closes, tail_bars); sb = build_b(closes, tail_bars)
    _, eq, _ = replay_ensemble(tail_bars, sa, sb)
    return (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0


# ── strategy builders (match the build_signal_fn shape) ─────────────
def build_rsi2(closes, bars):      return signal_rsi2(closes, bars)
def build_bb_fade(closes, bars):   return signal_bb_fade(closes, bars)
def build_ma20w5(closes, bars):    return signal_ma20w5(closes, bars)


STRATEGIES = {
    "MA20+W5":  build_ma20w5,
    "RSI2":     build_rsi2,
    "BB_FADE":  build_bb_fade,
}


# ── main ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS_DEFAULT)
    ap.add_argument("--mc-runs", type=int, default=100)
    args = ap.parse_args()

    print("═" * 114)
    print(f"  MEAN-REVERSION + ENSEMBLE · {len(args.pairs)} pairs · "
          f"{args.mc_runs} MC runs each")
    print("═" * 114)

    # Cache bars
    bars_by_pair = {}
    for p in args.pairs:
        b = fetch_gateio_bars(p, "1d", 1000)
        if len(b) >= 400:
            bars_by_pair[p] = b

    # Per-strategy table
    results = {}   # strategy_name -> pair -> metrics
    for name, build_fn in STRATEGIES.items():
        print(f"\n▸ STRATEGY: {name}")
        print("-" * 114)
        results[name] = {}
        for pair, bars in bars_by_pair.items():
            t0 = time.time()
            closes = [b.c for b in bars]
            sig = build_fn(closes, bars)
            rets, eq, trades = replay(bars, sig)
            sharpe = _sharpe(rets)
            full_roi = (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0
            mc = mc_percentile(bars, build_fn, args.mc_runs)
            wins, total = rolling_wins(bars, build_fn)
            rroi = recent_roi(bars, build_fn)
            results[name][pair] = {
                "sharpe": sharpe, "roi": full_roi, "mc": mc,
                "wins": wins, "total": total, "recent": rroi,
                "trades": trades,
            }
            dt = time.time() - t0
            print(f"  {pair:<10}  ROI {full_roi:>+8.1f}%  Sharpe {sharpe:>5.2f}  "
                  f"MC {mc:>5.1f}%  roll {wins}/{total}  recent {rroi:>+6.1f}%  "
                  f"trades {trades:>3}  ({dt:.1f}s)")

    # Ensemble: MA20+W5 + best MR (we'll auto-pick based on avg Sharpe)
    mr_rank = sorted(["RSI2", "BB_FADE"],
                     key=lambda n: -sum(m["sharpe"] for m in results[n].values()))
    best_mr = mr_rank[0]
    print(f"\n▸ ENSEMBLE: MA20+W5 ⊕ {best_mr}  (50/50 capital split)")
    print("-" * 114)
    results[f"ENS:MA+{best_mr}"] = {}
    for pair, bars in bars_by_pair.items():
        t0 = time.time()
        closes = [b.c for b in bars]
        sa = build_ma20w5(closes, bars)
        sb = STRATEGIES[best_mr](closes, bars)
        rets, eq, trades = replay_ensemble(bars, sa, sb)
        sharpe = _sharpe(rets)
        full_roi = (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0
        mc = mc_percentile_ensemble(bars, build_ma20w5, STRATEGIES[best_mr], args.mc_runs)
        wins, total = rolling_wins_ensemble(bars, build_ma20w5, STRATEGIES[best_mr])
        rroi = recent_roi_ensemble(bars, build_ma20w5, STRATEGIES[best_mr])
        results[f"ENS:MA+{best_mr}"][pair] = {
            "sharpe": sharpe, "roi": full_roi, "mc": mc,
            "wins": wins, "total": total, "recent": rroi,
            "trades": trades,
        }
        dt = time.time() - t0
        print(f"  {pair:<10}  ROI {full_roi:>+8.1f}%  Sharpe {sharpe:>5.2f}  "
              f"MC {mc:>5.1f}%  roll {wins}/{total}  recent {rroi:>+6.1f}%  "
              f"trades {trades:>3}  ({dt:.1f}s)")

    # Scorecard
    print("\n" + "═" * 114)
    print("  CROSS-STRATEGY SHIP-GATE SCORECARD")
    print("═" * 114)
    print(f"  {'strategy':<22}  {'MC≥99':>8}  {'roll≥4/5':>10}  {'recent>0':>10}  "
          f"{'avg Sharpe':>12}  {'avg MC%':>10}  PASSES")
    print("  " + "-" * 106)
    for name, per_pair in results.items():
        mc99 = sum(1 for m in per_pair.values() if m["mc"] >= 99)
        r45  = sum(1 for m in per_pair.values() if m["total"] > 0
                   and m["wins"] / m["total"] >= 4/5)
        rp   = sum(1 for m in per_pair.values() if m["recent"] > 0)
        n    = len(per_pair)
        avg_s  = sum(m["sharpe"] for m in per_pair.values()) / n
        avg_mc = sum(m["mc"] for m in per_pair.values()) / n
        passes = mc99 >= 3 and r45 >= 3 and rp == n
        mark = "✅ SHIP" if passes else ""
        print(f"  {name:<22}  {mc99}/{n:<6}  {r45}/{n:<8}  {rp}/{n:<8}  "
              f"{avg_s:>+11.2f}  {avg_mc:>9.1f}%  {mark}")


if __name__ == "__main__":
    main()
