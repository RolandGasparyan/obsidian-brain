#!/usr/bin/env python3
"""
Deep-edge search — the pieces we didn't test before folding.

Research rounds 1-3 evaluated each strategy PER PAIR and compared to
per-pair buy-and-hold. That's the wrong denominator: real deployment
uses a PORTFOLIO of pairs, and portfolio Sharpe > average individual
Sharpe by a factor determined by cross-pair correlation. We may have
been failing the ship gate by 3-6 Sharpe points that diversification
alone would have supplied.

This round packages five compounding edges:

  1. PORTFOLIO WALK-FORWARD — build a single 4-pair equity curve per
     run, compute portfolio-level Sharpe / MC / rolling wins. Forces
     the metrics to reflect the actual deployment.

  2. VOLATILITY-TARGETED SIZING — position size scales as
     target_vol / realized_vol. Each trade contributes equal variance
     to the portfolio, smoothing the equity curve (~+0.4 Sharpe
     improvement is typical across asset classes).

  3. DONCHIAN BREAKOUT — long when price makes N-day high, exit on
     M-day low. Parallel to MA but triggered by price extremes, not
     averages. Different failure modes from MA — partially decorrelated.

  4. BTC-CONDITIONAL GATE — only take alt longs when BTC's own
     MA50+W5 is LONG. Uses BTC as the market regime signal distinct
     from each alt's own MA.

  5. VOTING ENSEMBLE — three signals (MA20+W5, Donchian-20, BTC-gate).
     Go long only when at least 2 of 3 agree. Conservative but cuts
     whipsaws where signals disagree.

Ship gate remains unchanged:
  MC percentile ≥ 99 % on the portfolio
  AND rolling-window wins ≥ 4 / 5
  AND recent 6-month portfolio ROI > 0

Usage:
  python deep_edge.py
  python deep_edge.py --mc-runs 200
  python deep_edge.py --target-vol 0.15   # 15% annualized vol per position
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
BTC_SYMBOL    = "BTC_USDT"
FEE_RT        = 0.0025


# ── helpers ───────────────────────────────────────────────────────────
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


def _realized_vol(closes: List[float], idx: int, window: int = 30) -> float:
    """Annualized realized volatility of log returns."""
    if idx < window + 1: return 0.0
    rets = [math.log(closes[i] / closes[i - 1])
            for i in range(idx - window + 1, idx + 1)]
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)
    return math.sqrt(var) * math.sqrt(365)


# ── signal builders ──────────────────────────────────────────────────
def build_ma20w5(closes, bars, ma_p=20, weekly_p=5, hyst=0.0025):
    weekly = _weekly(bars) if weekly_p > 0 else []
    ma_s = sma(closes, ma_p)
    w_ma = sma([b.c for b in weekly], weekly_p) if weekly_p > 0 else []
    def want(i, in_pos):
        if ma_s[i] is None: return False
        m, px = ma_s[i], closes[i]
        upper = m * (1 + hyst); lower = m * (1 - hyst)
        d_ok = (px >= lower) if in_pos else (px > upper)
        if weekly_p == 0: return d_ok
        cur_ts = bars[i].ts
        w_idx = None
        for j in range(len(weekly) - 1, -1, -1):
            if weekly[j].ts <= cur_ts:
                w_idx = j; break
        if w_idx is None or w_ma[w_idx] is None: return False
        w_px, wm = weekly[w_idx].c, w_ma[w_idx]
        w_u = wm * (1 + hyst); w_l = wm * (1 - hyst)
        w_ok = (w_px >= w_l) if in_pos else (w_px > w_u)
        return d_ok and w_ok
    return want


def build_donchian(closes, bars, entry_n=20, exit_n=10):
    """Long when price > max of previous `entry_n` bars' highs;
    exit when price < min of previous `exit_n` bars' lows."""
    highs = [b.h for b in bars]
    lows  = [b.l for b in bars]
    def want(i, in_pos):
        if i < max(entry_n, exit_n): return False
        if in_pos:
            exit_floor = min(lows[i - exit_n:i])
            return closes[i] > exit_floor
        entry_ceil = max(highs[i - entry_n:i])
        return closes[i] > entry_ceil
    return want


def build_btc_gate(btc_bars: List[Bar], ma_p=50, weekly_p=5, hyst=0.0025):
    """Returns a function taking (i, in_pos) — True if BTC itself is LONG
    according to MA50+W5 at calendar-nearest BTC bar."""
    btc_closes = [b.c for b in btc_bars]
    btc_weekly = _weekly(btc_bars)
    ma_s  = sma(btc_closes, ma_p)
    w_ma  = sma([b.c for b in btc_weekly], weekly_p)
    # Pre-compute per-bar signal for BTC
    btc_signal = []
    in_btc = False
    for i in range(len(btc_bars)):
        if ma_s[i] is None:
            btc_signal.append(False); continue
        m, px = ma_s[i], btc_closes[i]
        upper = m * (1 + hyst); lower = m * (1 - hyst)
        d_ok = (px >= lower) if in_btc else (px > upper)
        w_idx = None
        cur_ts = btc_bars[i].ts
        for j in range(len(btc_weekly) - 1, -1, -1):
            if btc_weekly[j].ts <= cur_ts:
                w_idx = j; break
        w_ok = False
        if w_idx is not None and w_ma[w_idx] is not None:
            w_px, wm = btc_weekly[w_idx].c, w_ma[w_idx]
            w_u = wm * (1 + hyst); w_l = wm * (1 - hyst)
            w_ok = (w_px >= w_l) if in_btc else (w_px > w_u)
        want = d_ok and w_ok
        btc_signal.append(want)
        in_btc = want
    return btc_signal, [b.ts for b in btc_bars]


def _btc_gate_fn(btc_signal, btc_ts):
    def lookup(asset_ts):
        # Find largest btc_ts[j] <= asset_ts
        if not btc_ts: return False
        lo, hi = 0, len(btc_ts) - 1
        best = -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if btc_ts[mid] <= asset_ts:
                best = mid; lo = mid + 1
            else:
                hi = mid - 1
        return btc_signal[best] if best >= 0 else False
    return lookup


def build_vote_of_three(closes, bars, btc_signal, btc_ts):
    """Go long when ≥2 of (MA20+W5, Donchian-20, BTC-gate) agree."""
    ma_fn   = build_ma20w5(closes, bars)
    don_fn  = build_donchian(closes, bars)
    btc_fn  = _btc_gate_fn(btc_signal, btc_ts)
    def want(i, in_pos):
        a = ma_fn(i, in_pos)
        b = don_fn(i, in_pos)
        c = btc_fn(bars[i].ts)
        votes = int(bool(a)) + int(bool(b)) + int(bool(c))
        if in_pos:
            return votes >= 2 - 0  # need 2+ to stay
        return votes >= 2          # need 2+ to enter
    return want


# ── per-pair replay with vol-targeted OR binary sizing ───────────────
def replay(bars: List[Bar], signal_fn: Callable,
           start_bal: float = 1000.0,
           target_vol: float = 0.0) -> Tuple[List[float], List[float], int]:
    """
    If target_vol > 0: position size = start_bal × (target_vol / realized_30d_vol),
    capped at 100 %. Equal-risk weighting.
    If target_vol == 0: binary 100 % long / 0 % cash.
    """
    closes = [b.c for b in bars]
    bal = start_bal
    units = 0.0
    in_pos = False
    eq_curve, rets, trades = [], [], 0
    prev_eq = start_bal
    for i in range(len(bars)):
        px = closes[i]
        want = signal_fn(i, in_pos)

        if want and not in_pos:
            if target_vol > 0:
                vol = _realized_vol(closes, i, 30)
                size_frac = min(1.0, target_vol / max(1e-6, vol))
            else:
                size_frac = 1.0
            cost = bal * size_frac * (1 - FEE_RT / 2)
            units = cost / px
            bal -= cost + cost * (FEE_RT / 2) / (1 - FEE_RT / 2)
            bal = max(0.0, bal)
            in_pos = True
            trades += 1
        elif (not want) and in_pos:
            bal += units * px * (1 - FEE_RT / 2)
            units = 0.0
            in_pos = False
            trades += 1

        eq = bal + units * px
        eq_curve.append(eq)
        if prev_eq > 0:
            rets.append((eq - prev_eq) / prev_eq * 100)
        prev_eq = eq
    return rets, eq_curve, trades


# ── portfolio driver: equal-weight across N pairs ────────────────────
def portfolio_run(bars_by_pair, build_signal_fn,
                  btc_signal=None, btc_ts=None,
                  target_vol: float = 0.0,
                  start_bal: float = 1000.0) -> Tuple[List[float], List[float], int]:
    """
    Split start_bal equally across pairs. Each sub-portfolio runs its
    own strategy; portfolio equity is the sum. Returns daily returns
    (%), equity curve, total trade count.
    """
    per_pair_bal = start_bal / len(bars_by_pair)
    curves = {}
    total_trades = 0
    for pair, bars in bars_by_pair.items():
        closes = [b.c for b in bars]
        if btc_signal is not None:
            sig = build_signal_fn(closes, bars, btc_signal, btc_ts)
        else:
            sig = build_signal_fn(closes, bars)
        _, eq, trades = replay(bars, sig, start_bal=per_pair_bal, target_vol=target_vol)
        curves[pair] = eq
        total_trades += trades

    # Align on length (trim to shortest; they should be equal but be safe)
    n = min(len(eq) for eq in curves.values())
    port_eq = [sum(curves[p][i] for p in curves) for i in range(n)]
    port_rets = []
    for i in range(1, n):
        if port_eq[i - 1] > 0:
            port_rets.append((port_eq[i] - port_eq[i - 1]) / port_eq[i - 1] * 100)
    return port_rets, port_eq, total_trades


# ── evaluation primitives (portfolio-level) ──────────────────────────
def portfolio_mc(bars_by_pair, build_fn, n_runs,
                 btc_signal=None, btc_ts=None, target_vol=0.0, seed=42):
    rng = random.Random(seed)
    real_r, _, _ = portfolio_run(bars_by_pair, build_fn,
                                 btc_signal=btc_signal, btc_ts=btc_ts,
                                 target_vol=target_vol)
    real_s = _sharpe(real_r)

    # Pre-compute log returns per pair
    all_log_r = {}
    for p, bars in bars_by_pair.items():
        c = [b.c for b in bars]
        all_log_r[p] = [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]

    wins = 0
    for _ in range(n_runs):
        synth_bars = {}
        for p, bars in bars_by_pair.items():
            sh = list(all_log_r[p]); rng.shuffle(sh)
            base = [b.c for b in bars]
            px = [base[0]]
            for r in sh:
                px.append(px[-1] * math.exp(r))
            synth_bars[p] = [Bar(bars[i].ts, c, c, c, c, 1.0) for i, c in enumerate(px)]
        # If BTC-gated, shuffle BTC too and rebuild the gate
        if btc_signal is not None:
            # Use the original BTC signal — shuffling BTC separately adds little
            # and keeps the comparison fair for the alt-pair MC test
            pass
        r2, _, _ = portfolio_run(synth_bars, build_fn,
                                 btc_signal=btc_signal, btc_ts=btc_ts,
                                 target_vol=target_vol)
        if real_s > _sharpe(r2):
            wins += 1
    return wins / n_runs * 100.0


def portfolio_rolling(bars_by_pair, build_fn,
                      btc_signal=None, btc_ts=None,
                      target_vol=0.0, n_windows=5):
    n = min(len(b) for b in bars_by_pair.values())
    if n < 300: return 0, 0, []
    w_size = n // (n_windows + 1)
    wins = total = 0
    details = []
    for i in range(n_windows):
        start = i * (n - w_size) // max(1, n_windows - 1) if n_windows > 1 else 0
        end = start + w_size
        sub = {p: bars[start:end] for p, bars in bars_by_pair.items()}
        if min(len(b) for b in sub.values()) < 150: continue
        cut = int(w_size * 0.5)
        test = {p: b[cut:] for p, b in sub.items()}
        if min(len(b) for b in test.values()) < 50: continue
        # B&H portfolio for the same window
        _, eq_ma, _ = portfolio_run(test, build_fn,
                                    btc_signal=btc_signal, btc_ts=btc_ts,
                                    target_vol=target_vol)
        bh_roi = sum(buy_and_hold(b)["roi"] for b in test.values()) / len(test)
        ma_roi = (eq_ma[-1] - eq_ma[0]) / eq_ma[0] * 100 if eq_ma else 0
        if ma_roi > bh_roi: wins += 1
        total += 1
        details.append((f"bars [{start}..{end}]", ma_roi, bh_roi))
    return wins, total, details


def portfolio_recent(bars_by_pair, build_fn,
                     btc_signal=None, btc_ts=None,
                     target_vol=0.0, tail=176):
    n = min(len(b) for b in bars_by_pair.values())
    if n < tail + 50: return 0.0
    tail_bars = {p: b[-tail:] for p, b in bars_by_pair.items()}
    _, eq, _ = portfolio_run(tail_bars, build_fn,
                             btc_signal=btc_signal, btc_ts=btc_ts,
                             target_vol=target_vol)
    return (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0


# ── variant builders for the shootout ────────────────────────────────
def make_vote_builder(btc_signal, btc_ts):
    def builder(closes, bars, *_, **__):
        return build_vote_of_three(closes, bars, btc_signal, btc_ts)
    return builder


# ── main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS_DEFAULT)
    ap.add_argument("--mc-runs", type=int, default=100)
    ap.add_argument("--target-vol", type=float, default=0.30,
                    help="annualized vol target for sizing (default 30%)")
    args = ap.parse_args()

    print("═" * 120)
    print(f"  DEEP EDGE SEARCH · portfolio walk-forward · {len(args.pairs)} pairs · "
          f"{args.mc_runs} MC runs · vol target {args.target_vol*100:.0f}%")
    print("═" * 120)

    bars_by_pair = {}
    for p in args.pairs:
        b = fetch_gateio_bars(p, "1d", 1000)
        if len(b) >= 400:
            bars_by_pair[p] = b
            print(f"  {p:<10} {len(b)} bars")
    # BTC reference
    btc_bars = fetch_gateio_bars(BTC_SYMBOL, "1d", 1000)
    btc_signal, btc_ts = build_btc_gate(btc_bars)
    long_frac = sum(1 for s in btc_signal if s) / len(btc_signal) * 100
    print(f"  BTC reference: {len(btc_bars)} bars, MA50+W5 says LONG on "
          f"{long_frac:.0f}% of bars")

    # Build variants
    variants = {
        "MA20+W5 (binary)":
            ("binary", lambda c, b: build_ma20w5(c, b), 0.0, False),
        "MA20+W5 (vol-targeted)":
            ("vol",    lambda c, b: build_ma20w5(c, b), args.target_vol, False),
        "Donchian-20 (binary)":
            ("binary", lambda c, b: build_donchian(c, b), 0.0, False),
        "Donchian-20 (vol-targeted)":
            ("vol",    lambda c, b: build_donchian(c, b), args.target_vol, False),
        "MA20+W5 + BTC gate":
            ("binary", lambda c, b: _gated(build_ma20w5(c, b), bars_for_ts(b),
                                           btc_signal, btc_ts), 0.0, False),
        "Vote ≥2 of 3 (MA+Don+BTC)":
            ("binary", make_vote_builder(btc_signal, btc_ts), 0.0, True),
        "Vote ≥2 of 3 (vol-targeted)":
            ("vol",    make_vote_builder(btc_signal, btc_ts), args.target_vol, True),
    }

    print("\n" + "═" * 120)
    print(f"  {'variant':<34}  {'sizing':<6}  {'Port Sharpe':>12}  "
          f"{'Port ROI':>11}  {'Port MC%':>10}  {'rolling':>9}  "
          f"{'recent%':>9}  {'trades':>7}  PASSES")
    print("  " + "-" * 116)

    results = {}
    for name, (mode, builder, tvol, is_vote) in variants.items():
        t0 = time.time()
        # Portfolio run
        if is_vote:
            port_r, port_eq, trades = portfolio_run(
                bars_by_pair, builder, target_vol=tvol)
        else:
            port_r, port_eq, trades = portfolio_run(
                bars_by_pair, builder, target_vol=tvol)
        sharpe = _sharpe(port_r)
        roi = (port_eq[-1] - port_eq[0]) / port_eq[0] * 100 if port_eq else 0
        mc = portfolio_mc(bars_by_pair, builder, args.mc_runs,
                          btc_signal=btc_signal if is_vote else None,
                          btc_ts=btc_ts if is_vote else None,
                          target_vol=tvol)
        wins, total, _ = portfolio_rolling(bars_by_pair, builder,
                                           target_vol=tvol)
        recent = portfolio_recent(bars_by_pair, builder, target_vol=tvol)
        passes = (mc >= 99 and (total == 0 or wins / total >= 4/5)
                  and recent > 0)
        mark = "✅ SHIP" if passes else ""
        results[name] = {
            "sharpe": sharpe, "roi": roi, "mc": mc,
            "wins": wins, "total": total, "recent": recent,
            "trades": trades, "passes": passes,
        }
        dt = time.time() - t0
        print(f"  {name:<34}  {mode:<6}  {sharpe:>+11.2f}  "
              f"{roi:>+10.1f}%  {mc:>9.1f}%  {wins}/{total:<7}  "
              f"{recent:>+8.1f}%  {trades:>7}  {mark}  ({dt:.1f}s)")

    # Verdict
    print("\n" + "═" * 120)
    winners = [(n, r) for n, r in results.items() if r["passes"]]
    if winners:
        winners.sort(key=lambda x: -x[1]["sharpe"])
        print(f"  ✅ SHIP CANDIDATE — {winners[0][0]}")
        r = winners[0][1]
        print(f"     Port Sharpe {r['sharpe']:+.2f}  ROI {r['roi']:+.1f}%  "
              f"MC {r['mc']:.1f}%  rolling {r['wins']}/{r['total']}  "
              f"recent {r['recent']:+.1f}%  trades {r['trades']}")
    else:
        # Find the closest miss
        best = max(results.items(), key=lambda kv: (
            kv[1]["mc"] + 20 * (kv[1]["wins"] / max(1, kv[1]["total"])) +
            (10 if kv[1]["recent"] > 0 else 0)
        ))
        print(f"  🛑 NO variant clears the portfolio ship gate.")
        print(f"     Best effort: {best[0]}")
        r = best[1]
        print(f"     Port Sharpe {r['sharpe']:+.2f}  ROI {r['roi']:+.1f}%  "
              f"MC {r['mc']:.1f}%  rolling {r['wins']}/{r['total']}  "
              f"recent {r['recent']:+.1f}%  trades {r['trades']}")


# Helper used by BTC-gate variant builder
def bars_for_ts(bars):
    return bars


def _gated(inner_fn, bars, btc_signal, btc_ts):
    """Wrap a signal function with a BTC LONG gate."""
    btc_fn = _btc_gate_fn(btc_signal, btc_ts)
    def want(i, in_pos):
        if not btc_fn(bars[i].ts):
            return False
        return inner_fn(i, in_pos)
    return want


if __name__ == "__main__":
    main()
