#!/usr/bin/env python3
"""
Regime-gated MA strategy — walk-forward validated.

The plain MA20+W5 rule fails the ship gate because it trades every
regime indiscriminately. Wins in trending markets, loses in chop and
bear. Hypothesis: **only activate the trend rule when the macro
regime favors trend-following; otherwise stay in USDT.**

This script tests 5 regime gates on the best MA combo (MA20+W5) from
the parameter sweep:

  G1  "slope"   — 200d SMA slope > 0 over the last 10 bars
  G2  "above"   — price > 200d SMA (simpler version of slope)
  G3  "hi-vol"  — 30d realized vol > 3% (trend-follow needs movement)
  G4  "combo"   — slope>0 AND vol>2% (both must hold)
  G5  "strict"  — slope>0 AND price>200d MA AND vol>2%

Each gated variant runs through the same Monte Carlo + rolling-window
harness as walk_forward.py. The ship gate is unchanged:

  MC percentile ≥ 99 on ≥ 3 pairs
  AND rolling wins ≥ 4 / 5 on ≥ 3 pairs
  AND recent 6-month ROI > 0 on all 4 pairs

One-line verdict per gate: does it clear the bar?

Usage:
  python regime_gated_ma.py
  python regime_gated_ma.py --ma 20 --weekly 5
  python regime_gated_ma.py --mc-runs 200
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


# ── helpers ───────────────────────────────────────────────────────────
def _sharpe(rets, ann=math.sqrt(365)):
    if not rets: return 0.0
    mu = sum(rets)/len(rets)
    var = sum((r-mu)**2 for r in rets)/max(1, len(rets)-1)
    sd = math.sqrt(var)
    return (mu/sd)*ann if sd else 0.0


def _weekly(bars, per=7):
    out = []
    for i in range(0, len(bars), per):
        c = bars[i:i+per]
        if not c: continue
        out.append(Bar(c[0].ts, c[0].o, max(x.h for x in c),
                       min(x.l for x in c), c[-1].c, sum(x.v for x in c)))
    return out


def _slope(series: List[float], idx: int, lookback: int = 10) -> float:
    """Linear slope (% per bar) of a series over the last `lookback` bars."""
    if idx < lookback or series[idx] is None or series[idx - lookback] is None:
        return 0.0
    return (series[idx] - series[idx - lookback]) / series[idx - lookback] / lookback


def _vol(closes: List[float], idx: int, window: int = 30) -> float:
    """Annualized realized vol of log returns over the last `window` bars."""
    if idx < window + 1: return 0.0
    rets = [math.log(closes[i] / closes[i - 1])
            for i in range(idx - window + 1, idx + 1)]
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)
    return math.sqrt(var) * math.sqrt(365)


# ── regime gates — each returns (name, gate_fn(closes, ma200, idx)) ──
# gate_fn returns True if regime favorable → allow the trend rule,
# False if not → force USDT regardless of MA signal.
def gate_always_on(closes, ma200, idx):
    return True


def gate_slope(closes, ma200, idx):
    return _slope(ma200, idx, lookback=10) > 0


def gate_above(closes, ma200, idx):
    return ma200[idx] is not None and closes[idx] > ma200[idx]


def gate_hivol(closes, ma200, idx):
    return _vol(closes, idx, window=30) > 1.00   # 100% annualized = ~5.2% daily


def gate_combo(closes, ma200, idx):
    return gate_slope(closes, ma200, idx) and _vol(closes, idx, 30) > 0.80


def gate_strict(closes, ma200, idx):
    return (gate_slope(closes, ma200, idx)
            and gate_above(closes, ma200, idx)
            and _vol(closes, idx, 30) > 0.80)


GATES = {
    "none":   gate_always_on,
    "slope":  gate_slope,
    "above":  gate_above,
    "hivol":  gate_hivol,
    "combo":  gate_combo,
    "strict": gate_strict,
}


# ── core replay with regime gate ─────────────────────────────────────
def _replay(bars: List[Bar], ma_p: int, weekly_p: int,
            hyst: float, gate_fn: Callable,
            fee_rt: float = 0.0025,
            start_bal: float = 1000.0):
    closes = [b.c for b in bars]
    weekly = _weekly(bars) if weekly_p > 0 else []
    ma_series = sma(closes, ma_p)
    ma200     = sma(closes, 200)
    w_ma      = sma([b.c for b in weekly], weekly_p) if weekly_p > 0 else []

    bal, units, in_pos = start_bal, 0.0, False
    equity, rets, trades = [], [], 0
    prev_eq = start_bal
    for i in range(len(bars)):
        px = closes[i]

        # Regime gate first — if off, force USDT
        if not gate_fn(closes, ma200, i):
            if in_pos:
                bal = units * px * (1 - fee_rt / 2)
                units, in_pos = 0.0, False
                trades += 1
        else:
            # MA + weekly signal with hysteresis
            m = ma_series[i]
            if m is None:
                pass
            else:
                upper = m * (1 + hyst)
                lower = m * (1 - hyst)
                d_ok = (px >= lower) if in_pos else (px > upper)

                weekly_ok = True
                if weekly_p > 0:
                    cur_ts = bars[i].ts
                    w_idx = None
                    for j in range(len(weekly) - 1, -1, -1):
                        if weekly[j].ts <= cur_ts:
                            w_idx = j; break
                    if w_idx is None or w_ma[w_idx] is None:
                        weekly_ok = False
                    else:
                        w_px = weekly[w_idx].c
                        wm   = w_ma[w_idx]
                        w_u  = wm * (1 + hyst)
                        w_l  = wm * (1 - hyst)
                        weekly_ok = (w_px >= w_l) if in_pos else (w_px > w_u)

                want = d_ok and weekly_ok
                if want and not in_pos:
                    units = bal * (1 - fee_rt / 2) / px
                    bal, in_pos = 0.0, True
                    trades += 1
                elif (not want) and in_pos:
                    bal = units * px * (1 - fee_rt / 2)
                    units, in_pos = 0.0, False
                    trades += 1

        eq = bal + units * px
        equity.append(eq)
        if prev_eq > 0:
            rets.append((eq - prev_eq) / prev_eq * 100)
        prev_eq = eq
    return rets, equity, trades


# ── evaluation primitives ────────────────────────────────────────────
def mc_significance(bars, ma_p, weekly_p, hyst, gate_fn, n_runs, seed=42):
    rng = random.Random(seed)
    real_r, _, _ = _replay(bars, ma_p, weekly_p, hyst, gate_fn)
    real_s = _sharpe(real_r)
    base = [b.c for b in bars]
    log_r = [math.log(base[i]/base[i-1]) for i in range(1, len(base))]
    wins = 0
    for _ in range(n_runs):
        sh = list(log_r); rng.shuffle(sh)
        px = [base[0]]
        for r in sh:
            px.append(px[-1] * math.exp(r))
        synth = [Bar(bars[i].ts, c, c, c, c, 1.0) for i, c in enumerate(px)]
        sr, _, _ = _replay(synth, ma_p, weekly_p, hyst, gate_fn)
        if real_s > _sharpe(sr):
            wins += 1
    return wins / n_runs * 100.0


def rolling_wins(bars, ma_p, weekly_p, hyst, gate_fn, n_windows=5):
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
        _, eq, _ = _replay(test, ma_p, weekly_p, hyst, gate_fn)
        ma_roi = (eq[-1]-eq[0])/eq[0]*100 if eq else 0
        bh_roi = buy_and_hold(test)["roi"]
        if ma_roi > bh_roi: wins += 1
        total += 1
    return wins, total


def recent_roi(bars, ma_p, weekly_p, hyst, gate_fn, tail=176):
    if len(bars) < tail + max(ma_p, 200):
        return 0.0
    _, eq, _ = _replay(bars[-tail:], ma_p, weekly_p, hyst, gate_fn)
    if not eq: return 0.0
    return (eq[-1] - eq[0])/eq[0] * 100


# ── main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS_DEFAULT)
    ap.add_argument("--ma", type=int, default=20)
    ap.add_argument("--weekly", type=int, default=5)
    ap.add_argument("--hyst", type=float, default=0.0025)
    ap.add_argument("--mc-runs", type=int, default=100)
    args = ap.parse_args()

    print("═" * 114)
    print(f"  REGIME-GATED MA{args.ma}+W{args.weekly} · hyst={args.hyst*100:.2f}% · "
          f"{len(args.pairs)} pairs × {len(GATES)} gates = {len(args.pairs)*len(GATES)} runs")
    print("═" * 114)

    bars_by_pair = {}
    for p in args.pairs:
        b = fetch_gateio_bars(p, "1d", 1000)
        if len(b) >= 400:
            bars_by_pair[p] = b

    # For each pair × gate
    cells = {}   # gate -> pair -> metrics
    for gate_name, gate_fn in GATES.items():
        print(f"\n▸ GATE: {gate_name}")
        print("-" * 114)
        for pair, bars in bars_by_pair.items():
            t0 = time.time()
            rets, eq, trades = _replay(bars, args.ma, args.weekly, args.hyst, gate_fn)
            sharpe = _sharpe(rets)
            full_roi = (eq[-1]-eq[0])/eq[0]*100 if eq else 0
            mc = mc_significance(bars, args.ma, args.weekly, args.hyst, gate_fn, args.mc_runs)
            wins, total = rolling_wins(bars, args.ma, args.weekly, args.hyst, gate_fn)
            rroi = recent_roi(bars, args.ma, args.weekly, args.hyst, gate_fn)
            cells.setdefault(gate_name, {})[pair] = {
                "sharpe": sharpe, "roi": full_roi, "mc": mc,
                "wins": wins, "total": total,
                "recent": rroi, "trades": trades,
            }
            dt = time.time() - t0
            print(f"  {pair:<10}  ROI {full_roi:>+8.1f}%  "
                  f"Sharpe {sharpe:>5.2f}  MC {mc:>5.1f}%  "
                  f"roll {wins}/{total}  recent {rroi:>+6.1f}%  "
                  f"trades {trades:>3}  ({dt:.1f}s)")

    # ── summary per gate
    print("\n" + "═" * 114)
    print(f"  SHIP-GATE CROSS-PAIR SCORECARD")
    print("═" * 114)
    print(f"  {'gate':<10}  {'MC≥99':>10}  {'rolling≥4/5':>14}  "
          f"{'recent>0':>12}  {'avg Sharpe':>12}  {'avg MC%':>10}  PASSES")
    print("  " + "-" * 108)

    scored = []
    for gate_name, pp in cells.items():
        mc99  = sum(1 for m in pp.values() if m["mc"] >= 99)
        r45   = sum(1 for m in pp.values() if m["total"] > 0
                    and m["wins"] / m["total"] >= 4/5)
        recent_p = sum(1 for m in pp.values() if m["recent"] > 0)
        n  = len(pp)
        avg_sharpe = sum(m["sharpe"] for m in pp.values())/n
        avg_mc     = sum(m["mc"] for m in pp.values())/n
        passes = mc99 >= 3 and r45 >= 3 and recent_p == n
        mark = "✅ SHIP" if passes else ""
        scored.append((avg_mc + 20*mc99 + 15*r45 + 10*recent_p, gate_name, pp, passes))
        print(f"  {gate_name:<10}  {mc99:>4}/{n:<6}  {r45:>4}/{n:<10}  "
              f"{recent_p:>4}/{n:<8}  {avg_sharpe:>+11.2f}  {avg_mc:>9.1f}%  {mark}")

    # Verdict
    scored.sort(reverse=True)
    winners = [s for s in scored if s[3]]
    print("\n" + "═" * 114)
    if winners:
        _, gname, pp, _ = winners[0]
        print(f"  ✅ SHIP CANDIDATE — gate '{gname}' with MA{args.ma}+W{args.weekly}")
        print()
        for p, m in pp.items():
            print(f"    {p:<10}  ROI {m['roi']:>+8.1f}%  Sharpe {m['sharpe']:>5.2f}  "
                  f"MC {m['mc']:>5.1f}%  rolling {m['wins']}/{m['total']}  "
                  f"recent {m['recent']:>+6.1f}%  trades {m['trades']}")
        print()
        print(f"  Deploy: --strategy ma{args.ma}w{args.weekly} with gate='{gname}' enabled.")
    else:
        _, best_gname, _, _ = scored[0]
        print(f"  🛑 NO regime gate clears the ship bar. Best: '{best_gname}'.")
        print(f"  The MA trend-follow family is structurally exhausted on this data.")
        print(f"  Pivot to: mean-reversion (Bollinger / RSI-2) or breakout (Donchian).")
    print("═" * 114)


if __name__ == "__main__":
    main()
