#!/usr/bin/env python3
"""
Parameter sweep for the MA trend-follow family.

Walk-forward showed MA50+W10 fails the significance bar on 3 of 4 pairs.
Before abandoning the strategy CLASS, sweep the parameter space to see
if any (ma_period, weekly_period, hysteresis) combination clears the
bar on a MAJORITY of pairs — that would suggest we had the right idea
but the wrong knobs.

For each pair × combo:
  • Full-sample Sharpe
  • Monte Carlo percentile (vs shuffled returns, 100 runs)
  • Rolling-window wins vs buy-and-hold (5 splits)
  • Recent expanding-window ROI (last 176-bar slice)

Composite score per combo (higher is better):
    score = Σ_pairs [ (mc_pct / 100) × 2
                    + (recent_roi / 10) clipped [-1, +3]
                    + (rolling_wins / 5) × 1
                    + min(sharpe, 3) / 3 × 0.5 ]

A combo that clears the ship bar on all 4 pairs:
    mc_pct ≥ 99 on ≥3 pairs AND rolling ≥4/5 on ≥3 pairs
    AND recent_roi > 0 on all 4 pairs

Usage:
  python param_sweep.py
  python param_sweep.py --mc-runs 100 --pairs ETH_USDT NEAR_USDT
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from itertools import product
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar
from backtest_multi_token import fetch_gateio_bars
from backtest_ma import buy_and_hold, make_signal_ma_with_weekly_filter, sma


# ── grid ──────────────────────────────────────────────────────────────
MA_PERIODS      = [20, 50, 100, 200]
WEEKLY_PERIODS  = [0, 5, 10, 20]             # 0 = no weekly filter
HYSTERESIS_BAND = [0.0025]                    # keep fixed; strategy-level knob
PAIRS_DEFAULT   = ["ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]


def _weekly_from_daily(bars: List[Bar], per: int = 7) -> List[Bar]:
    out = []
    for i in range(0, len(bars), per):
        chunk = bars[i:i + per]
        if not chunk:
            continue
        out.append(Bar(
            chunk[0].ts, chunk[0].o,
            max(x.h for x in chunk),
            min(x.l for x in chunk),
            chunk[-1].c,
            sum(x.v for x in chunk),
        ))
    return out


def _sharpe(rets: List[float], ann=math.sqrt(365)) -> float:
    if not rets: return 0.0
    mu  = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)
    sd  = math.sqrt(var)
    return (mu / sd) * ann if sd else 0.0


def _replay(bars: List[Bar], ma_p: int, weekly_p: int,
            hyst: float, fee_rt: float = 0.0025,
            start_bal: float = 1000.0) -> Tuple[List[float], List[float], int]:
    """Replay MA+W strategy with hysteresis. Returns (per-bar returns%, equity, trades)."""
    closes = [b.c for b in bars]
    weekly = _weekly_from_daily(bars) if weekly_p > 0 else []
    ma_series = sma(closes, ma_p)
    w_ma_series = sma([b.c for b in weekly], weekly_p) if weekly_p > 0 else []

    def want_long(i: int, in_pos: bool) -> bool:
        if ma_series[i] is None: return False
        m = ma_series[i]
        px = closes[i]
        upper = m * (1 + hyst)
        lower = m * (1 - hyst)
        d_ok = (px >= lower) if in_pos else (px > upper)

        if weekly_p > 0:
            cur_ts = bars[i].ts
            w_idx = None
            for j in range(len(weekly) - 1, -1, -1):
                if weekly[j].ts <= cur_ts:
                    w_idx = j; break
            if w_idx is None or w_ma_series[w_idx] is None:
                return False
            w_px = weekly[w_idx].c
            wm   = w_ma_series[w_idx]
            w_u  = wm * (1 + hyst)
            w_l  = wm * (1 - hyst)
            w_ok = (w_px >= w_l) if in_pos else (w_px > w_u)
            return d_ok and w_ok
        return d_ok

    bal, units, in_pos = start_bal, 0.0, False
    equity, rets, trades = [], [], 0
    prev_eq = start_bal
    for i in range(len(bars)):
        want = want_long(i, in_pos)
        px = closes[i]
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


def _mc_significance(bars: List[Bar], ma_p: int, weekly_p: int,
                     hyst: float, n_runs: int, seed: int = 42) -> float:
    """Return percentile of real Sharpe within shuffled-returns distribution."""
    rng = random.Random(seed)
    real_r, _, _ = _replay(bars, ma_p, weekly_p, hyst)
    real_sharpe = _sharpe(real_r)
    base = [b.c for b in bars]
    log_r = [math.log(base[i] / base[i - 1]) for i in range(1, len(base))]
    wins = 0
    for _ in range(n_runs):
        sh = list(log_r); rng.shuffle(sh)
        px = [base[0]]
        for r in sh:
            px.append(px[-1] * math.exp(r))
        synth = [Bar(bars[i].ts, c, c, c, c, 1.0) for i, c in enumerate(px)]
        sr, _, _ = _replay(synth, ma_p, weekly_p, hyst)
        if real_sharpe > _sharpe(sr):
            wins += 1
    return wins / n_runs * 100.0


def _rolling_wins(bars: List[Bar], ma_p: int, weekly_p: int, hyst: float,
                  n_windows: int = 5) -> Tuple[int, int]:
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
        _, eq, _ = _replay(test, ma_p, weekly_p, hyst)
        ma_roi = (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0
        bh_roi = buy_and_hold(test)["roi"]
        if ma_roi > bh_roi:
            wins += 1
        total += 1
    return wins, total


def _recent_roi(bars: List[Bar], ma_p: int, weekly_p: int, hyst: float,
                tail: int = 176) -> float:
    if len(bars) < tail + max(ma_p, 1):
        return 0.0
    _, eq, _ = _replay(bars[-tail:], ma_p, weekly_p, hyst)
    if not eq: return 0.0
    return (eq[-1] - eq[0]) / eq[0] * 100


def _score(pair_metrics: dict) -> float:
    """Composite score for one (pair, combo) cell — bigger is better."""
    s = 0.0
    s += (pair_metrics["mc"] / 100.0) * 2.0
    rr = max(-10.0, min(30.0, pair_metrics["recent_roi"]))
    s += rr / 10.0
    s += (pair_metrics["rolling_wins"] / max(1, pair_metrics["rolling_total"])) * 1.0
    s += min(3.0, max(0.0, pair_metrics["sharpe"])) / 3.0 * 0.5
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS_DEFAULT)
    ap.add_argument("--interval", default="1d")
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--mc-runs", type=int, default=100)
    args = ap.parse_args()

    combos = list(product(MA_PERIODS, WEEKLY_PERIODS, HYSTERESIS_BAND))
    print("═" * 110)
    print(f"  MA FAMILY PARAMETER SWEEP · {len(args.pairs)} pairs × "
          f"{len(combos)} combos = {len(args.pairs) * len(combos)} runs")
    print(f"  MA periods: {MA_PERIODS}  ·  Weekly: {WEEKLY_PERIODS}  ·  Hyst: {HYSTERESIS_BAND}")
    print("═" * 110)

    # Fetch bars once per pair
    bars_by_pair = {}
    for p in args.pairs:
        b = fetch_gateio_bars(p, args.interval, args.limit)
        if len(b) >= 400:
            bars_by_pair[p] = b
            print(f"  {p:<10}  {len(b)} bars")
        else:
            print(f"  {p:<10}  skip ({len(b)} bars)")

    # Sweep
    results = {}     # (ma, wk, hy) -> { pair -> metrics }
    for pair, bars in bars_by_pair.items():
        for ma_p, wk_p, hy in combos:
            t0 = time.time()
            rets, eq, trades = _replay(bars, ma_p, wk_p, hy)
            full_sharpe = _sharpe(rets)
            mc_pct = _mc_significance(bars, ma_p, wk_p, hy, args.mc_runs)
            wins, total = _rolling_wins(bars, ma_p, wk_p, hy)
            recent = _recent_roi(bars, ma_p, wk_p, hy)
            full_roi = (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0
            results.setdefault((ma_p, wk_p, hy), {})[pair] = {
                "sharpe":         full_sharpe,
                "mc":             mc_pct,
                "rolling_wins":   wins,
                "rolling_total":  total,
                "recent_roi":     recent,
                "full_roi":       full_roi,
                "trades":         trades,
            }
            dt = time.time() - t0
            print(f"  {pair:<10} MA{ma_p:<3} W{wk_p:<3}  "
                  f"ROI {full_roi:>+8.1f}%  Sharpe {full_sharpe:>5.2f}  "
                  f"MC {mc_pct:>5.1f}%  roll {wins}/{total}  "
                  f"recent {recent:>+6.1f}%  trades {trades:>3}  ({dt:.1f}s)")

    # Rank combos by cross-pair composite
    print("\n" + "═" * 110)
    print("  RANKING — combos sorted by cross-pair composite score")
    print("═" * 110)
    ranked = []
    for combo, per_pair in results.items():
        total = sum(_score(m) for m in per_pair.values())
        ranked.append((total, combo, per_pair))
    ranked.sort(reverse=True)

    print(f"  {'rank':>4}  {'combo':<14}  {'score':>7}  "
          f"{'MC ≥99 pairs':>14}  {'rolling ≥4/5 pairs':>20}  "
          f"{'recent>0 pairs':>16}  {'PASSES SHIP GATE'}")
    print("  " + "-" * 106)
    for rk, (score, (ma, wk, hy), per_pair) in enumerate(ranked[:20], 1):
        mc99 = sum(1 for m in per_pair.values() if m["mc"] >= 99)
        r45  = sum(1 for m in per_pair.values() if m["rolling_total"] > 0
                   and m["rolling_wins"] / m["rolling_total"] >= 4/5)
        rp   = sum(1 for m in per_pair.values() if m["recent_roi"] > 0)
        n    = len(per_pair)
        # ship gate: MC≥99 on ≥3 pairs AND rolling≥4/5 on ≥3 pairs AND recent>0 on all
        passes = (mc99 >= 3 and r45 >= 3 and rp == n)
        mark   = "✅ SHIP" if passes else ""
        hyst_s = f"{hy*100:.2f}%"
        print(f"  {rk:>4}  MA{ma:>3} W{wk:<3} {hyst_s:<4}  {score:>7.2f}  "
              f"{mc99:>5}/{n:<8}  {r45:>6}/{n:<12}  {rp:>5}/{n:<11}  {mark}")

    # Ship verdict
    ship = [(c, pp) for _, c, pp in ranked if
            sum(1 for m in pp.values() if m["mc"] >= 99) >= 3
            and sum(1 for m in pp.values() if m["rolling_total"] > 0
                    and m["rolling_wins"] / m["rolling_total"] >= 4/5) >= 3
            and all(m["recent_roi"] > 0 for m in pp.values())]
    print("\n" + "═" * 110)
    if ship:
        (ma, wk, hy), pp = ship[0]
        print(f"  ✅ SHIP CANDIDATE FOUND — MA{ma} + W{wk}  hyst={hy*100:.2f}%")
        print(f"  Per-pair performance:")
        for p, m in pp.items():
            print(f"    {p:<10} ROI {m['full_roi']:>+8.1f}%  Sharpe {m['sharpe']:>5.2f}  "
                  f"MC {m['mc']:>5.1f}%  rolling {m['rolling_wins']}/{m['rolling_total']}")
    else:
        print("  🛑 NO combo clears the ship gate on majority of pairs.")
        print("  The MA-family strategy class itself is the limitation on this data,")
        print("  not parameter tuning. Consider: different strategy family (breakout,")
        print("  mean-reversion), ensemble, or regime-conditional gating.")
    print("═" * 110)


if __name__ == "__main__":
    main()
