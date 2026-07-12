#!/usr/bin/env python3
"""
Maximum edge — stack every amplifier we haven't tried yet.

Previous rounds ran on 1000 bars × 4 pairs with no per-trade risk.
Remaining honest opportunities:

  1. EXTENDED HISTORY — paginated Gate.io fetches to ~2500 daily bars
     (~7 years). More regime samples in rolling windows — may flip the
     stuck 3/5 rolling-wins bar.

  2. 10-PAIR UNIVERSE — diversification across 10 pairs (vs 4) typically
     boosts portfolio Sharpe by 1.3-1.5× due to imperfect correlation.

  3. PER-TRADE STOP-LOSS OVERLAY — hard exit at -3% below entry, capping
     left-tail drawdowns. Should help rolling windows (fewer catastrophic
     losing windows) and recent ROI (skip big drawdowns).

  4. PORTFOLIO RISK BUDGET — vol-target 20% per leg + per-trade -3%
     stop + BTC gate + 2-of-3 vote.

Ship gate unchanged:
  MC percentile ≥ 99 on portfolio
  AND rolling wins ≥ 4 / 5 (now with 7 windows, since more history)
  AND recent 6-mo ROI > 0

Usage:
  python max_edge.py
  python max_edge.py --mc-runs 200 --windows 7
  python max_edge.py --stop-pct 0.04
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from typing import Callable, List, Tuple, Dict

try:
    import requests
except ImportError:
    print("requests missing"); sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar
from backtest_ma import buy_and_hold, sma


# ── 10-pair universe (top by select_best_tokens) ─────────────────────
PAIRS_DEFAULT = [
    "ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT",
    "NEAR_USDT", "ARB_USDT", "DOGE_USDT", "LINK_USDT",
    "BNB_USDT", "DOT_USDT",
]
BTC_SYMBOL  = "BTC_USDT"
FEE_RT      = 0.0025


# ── paginated historical fetch ───────────────────────────────────────
def fetch_gateio_history(pair: str, interval: str = "1d",
                         total_bars: int = 2500) -> List[Bar]:
    """
    Gate.io limits a single /candlesticks call to 1000 bars. Paginate
    backward via `from`/`to` epoch-seconds to collect up to `total_bars`.
    Returns unfinalized bars filtered out (matches Exchange.fetch_bars).
    """
    interval_sec = {"1d": 86400, "4h": 14400, "1h": 3600}[interval]
    bars = []
    now = int(time.time())
    to = now
    while len(bars) < total_bars:
        frm = to - 999 * interval_sec
        r = requests.get("https://api.gateio.ws/api/v4/spot/candlesticks",
                         params={"currency_pair": pair,
                                 "interval": interval,
                                 "from": frm, "to": to},
                         timeout=12)
        r.raise_for_status()
        rows = r.json()
        if not rows: break
        chunk = []
        for x in rows:
            finalized = True
            if len(x) >= 8:
                f = x[7]
                finalized = (f is True) or (isinstance(f, str) and f.lower() == "true")
            if not finalized: continue
            chunk.append(Bar(int(x[0]), float(x[5]), float(x[3]),
                             float(x[4]), float(x[2]), float(x[1])))
        if not chunk: break
        # Merge unique (API may return overlap)
        have = set(b.ts for b in bars)
        chunk = [b for b in chunk if b.ts not in have]
        bars.extend(chunk)
        # Move window back just before the oldest bar we got
        oldest = min(b.ts for b in chunk)
        if oldest >= to: break
        to = oldest - 1
        time.sleep(0.15)
    bars.sort(key=lambda b: b.ts)
    return bars[-total_bars:]


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


def _realized_vol(closes, idx, window=30):
    if idx < window + 1: return 0.0
    rets = [math.log(closes[i] / closes[i - 1])
            for i in range(idx - window + 1, idx + 1)]
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)
    return math.sqrt(var) * math.sqrt(365)


# ── signal builders (same as deep_edge, factored here) ───────────────
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
    highs = [b.h for b in bars]; lows = [b.l for b in bars]
    def want(i, in_pos):
        if i < max(entry_n, exit_n): return False
        if in_pos:
            return closes[i] > min(lows[i - exit_n:i])
        return closes[i] > max(highs[i - entry_n:i])
    return want


def build_btc_signal(btc_bars):
    closes = [b.c for b in btc_bars]
    weekly = _weekly(btc_bars)
    ma_s = sma(closes, 50)
    w_ma = sma([b.c for b in weekly], 5)
    sig = []
    in_pos = False
    for i in range(len(btc_bars)):
        if ma_s[i] is None:
            sig.append(False); continue
        m, px = ma_s[i], closes[i]
        u, l = m * 1.0025, m * 0.9975
        d_ok = (px >= l) if in_pos else (px > u)
        w_idx = None; ts = btc_bars[i].ts
        for j in range(len(weekly) - 1, -1, -1):
            if weekly[j].ts <= ts: w_idx = j; break
        w_ok = False
        if w_idx is not None and w_ma[w_idx] is not None:
            wpx, wm = weekly[w_idx].c, w_ma[w_idx]
            wu, wl = wm * 1.0025, wm * 0.9975
            w_ok = (wpx >= wl) if in_pos else (wpx > wu)
        want = d_ok and w_ok
        sig.append(want); in_pos = want
    return sig, [b.ts for b in btc_bars]


def _btc_lookup(btc_signal, btc_ts):
    def fn(ts):
        if not btc_ts: return False
        lo, hi, best = 0, len(btc_ts) - 1, -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if btc_ts[mid] <= ts: best = mid; lo = mid + 1
            else: hi = mid - 1
        return btc_signal[best] if best >= 0 else False
    return fn


def build_vote_of_three(closes, bars, btc_signal, btc_ts):
    ma_fn = build_ma20w5(closes, bars)
    don_fn = build_donchian(closes, bars)
    btc_fn = _btc_lookup(btc_signal, btc_ts)
    def want(i, in_pos):
        a = ma_fn(i, in_pos); b = don_fn(i, in_pos)
        c = btc_fn(bars[i].ts)
        votes = int(a) + int(b) + int(c)
        return votes >= 2
    return want


# ── replay with vol-target + per-trade stop-loss ─────────────────────
def replay(bars, signal_fn, start_bal=1000.0,
           target_vol: float = 0.0,
           stop_loss_pct: float = 0.0):
    """
    target_vol > 0: size = target_vol / realized_30d_vol (capped at 100%)
    stop_loss_pct > 0: force exit when price falls stop_loss_pct below entry
    """
    closes = [b.c for b in bars]
    bal, units, in_pos, entry_px = start_bal, 0.0, False, 0.0
    eq_curve, rets, trades = [], [], 0
    prev_eq = start_bal

    for i in range(len(bars)):
        px = closes[i]
        want = signal_fn(i, in_pos)

        # Per-trade stop-loss overrides signal
        if in_pos and stop_loss_pct > 0 and entry_px > 0:
            if px <= entry_px * (1 - stop_loss_pct):
                want = False

        if want and not in_pos:
            if target_vol > 0:
                vol = _realized_vol(closes, i, 30)
                size_frac = min(1.0, target_vol / max(1e-6, vol))
            else:
                size_frac = 1.0
            cost = bal * size_frac * (1 - FEE_RT / 2)
            units = cost / px
            bal -= cost / (1 - FEE_RT / 2)
            bal = max(0.0, bal)
            in_pos = True
            entry_px = px
            trades += 1
        elif (not want) and in_pos:
            bal += units * px * (1 - FEE_RT / 2)
            units, in_pos, entry_px = 0.0, False, 0.0
            trades += 1

        eq = bal + units * px
        eq_curve.append(eq)
        if prev_eq > 0:
            rets.append((eq - prev_eq) / prev_eq * 100)
        prev_eq = eq
    return rets, eq_curve, trades


# ── portfolio runner ─────────────────────────────────────────────────
def portfolio_run(bars_by_pair, build_signal_fn, btc_signal, btc_ts,
                  target_vol=0.0, stop_loss_pct=0.0,
                  use_vote=True, use_btc_gate=False,
                  start_bal=1000.0):
    per_pair_bal = start_bal / len(bars_by_pair)
    curves = {}; total_trades = 0
    # align bars to common length (max 2500 or shortest)
    shortest = min(len(b) for b in bars_by_pair.values())
    for pair, bars in bars_by_pair.items():
        bars = bars[-shortest:]
        closes = [b.c for b in bars]
        if use_vote:
            sig = build_vote_of_three(closes, bars, btc_signal, btc_ts)
        else:
            inner = build_signal_fn(closes, bars)
            if use_btc_gate:
                btc_fn = _btc_lookup(btc_signal, btc_ts)
                def sig(i, in_pos, inner=inner, bars=bars):
                    if not btc_fn(bars[i].ts): return False
                    return inner(i, in_pos)
            else:
                sig = inner
        _, eq, trades = replay(bars, sig, start_bal=per_pair_bal,
                               target_vol=target_vol,
                               stop_loss_pct=stop_loss_pct)
        curves[pair] = eq
        total_trades += trades

    n = min(len(eq) for eq in curves.values())
    port_eq = [sum(curves[p][i] for p in curves) for i in range(n)]
    port_rets = []
    for i in range(1, n):
        if port_eq[i - 1] > 0:
            port_rets.append((port_eq[i] - port_eq[i - 1]) / port_eq[i - 1] * 100)
    return port_rets, port_eq, total_trades


# ── metrics ───────────────────────────────────────────────────────────
def portfolio_mc(bars_by_pair, btc_signal, btc_ts,
                 use_vote, use_btc_gate, builder,
                 target_vol, stop_loss_pct, n_runs, seed=42):
    rng = random.Random(seed)
    real_r, _, _ = portfolio_run(bars_by_pair, builder,
                                 btc_signal, btc_ts,
                                 target_vol=target_vol,
                                 stop_loss_pct=stop_loss_pct,
                                 use_vote=use_vote,
                                 use_btc_gate=use_btc_gate)
    real_s = _sharpe(real_r)
    log_r_by_pair = {}
    for p, bars in bars_by_pair.items():
        c = [b.c for b in bars]
        log_r_by_pair[p] = [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
    wins = 0
    for _ in range(n_runs):
        synth = {}
        for p, bars in bars_by_pair.items():
            sh = list(log_r_by_pair[p]); rng.shuffle(sh)
            base = [b.c for b in bars]
            px = [base[0]]
            for r in sh: px.append(px[-1] * math.exp(r))
            synth[p] = [Bar(bars[i].ts, c, c, c, c, 1.0) for i, c in enumerate(px)]
        r2, _, _ = portfolio_run(synth, builder,
                                 btc_signal, btc_ts,
                                 target_vol=target_vol,
                                 stop_loss_pct=stop_loss_pct,
                                 use_vote=use_vote,
                                 use_btc_gate=use_btc_gate)
        if real_s > _sharpe(r2): wins += 1
    return wins / n_runs * 100.0


def portfolio_rolling(bars_by_pair, btc_signal, btc_ts,
                      use_vote, use_btc_gate, builder,
                      target_vol, stop_loss_pct, n_windows):
    n = min(len(b) for b in bars_by_pair.values())
    if n < 300: return 0, 0
    w_size = n // (n_windows + 1)
    wins = total = 0
    for i in range(n_windows):
        start = i * (n - w_size) // max(1, n_windows - 1) if n_windows > 1 else 0
        end = start + w_size
        sub = {p: bars[start:end] for p, bars in bars_by_pair.items()}
        if min(len(b) for b in sub.values()) < 150: continue
        cut = int(w_size * 0.5)
        test = {p: b[cut:] for p, b in sub.items()}
        if min(len(b) for b in test.values()) < 50: continue
        _, eq, _ = portfolio_run(test, builder, btc_signal, btc_ts,
                                 target_vol=target_vol,
                                 stop_loss_pct=stop_loss_pct,
                                 use_vote=use_vote,
                                 use_btc_gate=use_btc_gate)
        ma_roi = (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0
        bh_roi = sum(buy_and_hold(b)["roi"] for b in test.values()) / len(test)
        if ma_roi > bh_roi: wins += 1
        total += 1
    return wins, total


def portfolio_recent(bars_by_pair, btc_signal, btc_ts,
                     use_vote, use_btc_gate, builder,
                     target_vol, stop_loss_pct, tail=176):
    n = min(len(b) for b in bars_by_pair.values())
    if n < tail + 50: return 0.0
    tail_bars = {p: b[-tail:] for p, b in bars_by_pair.items()}
    _, eq, _ = portfolio_run(tail_bars, builder,
                             btc_signal, btc_ts,
                             target_vol=target_vol,
                             stop_loss_pct=stop_loss_pct,
                             use_vote=use_vote,
                             use_btc_gate=use_btc_gate)
    return (eq[-1] - eq[0]) / eq[0] * 100 if eq else 0


# ── main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS_DEFAULT)
    ap.add_argument("--history", type=int, default=2500)
    ap.add_argument("--mc-runs", type=int, default=100)
    ap.add_argument("--windows", type=int, default=7)
    ap.add_argument("--target-vol", type=float, default=0.30)
    ap.add_argument("--stop-pct", type=float, default=0.04,
                    help="per-trade stop-loss as fraction (0=off)")
    args = ap.parse_args()

    print("═" * 122)
    print(f"  MAXIMUM EDGE · {len(args.pairs)} pairs · {args.history} bars history target · "
          f"{args.windows} rolling windows · MC {args.mc_runs} · "
          f"vol {args.target_vol*100:.0f}% · stop {args.stop_pct*100:.0f}%")
    print("═" * 122)

    # Paginated fetch for each pair
    print("\n  Fetching extended history …")
    bars_by_pair = {}
    for p in args.pairs:
        t0 = time.time()
        try:
            b = fetch_gateio_history(p, "1d", args.history)
        except Exception as e:
            print(f"    {p:<10}  FAIL: {e}")
            continue
        if len(b) >= 400:
            bars_by_pair[p] = b
            span = (b[-1].ts - b[0].ts) / 86400 if len(b) >= 2 else 0
            print(f"    {p:<10}  {len(b)} bars ({span:.0f} days)  "
                  f"${b[0].c:.3f} → ${b[-1].c:.3f}  ({time.time()-t0:.1f}s)")

    print(f"\n  Fetching BTC reference (for gate)...")
    btc_bars = fetch_gateio_history(BTC_SYMBOL, "1d", args.history)
    btc_signal, btc_ts = build_btc_signal(btc_bars)
    long_frac = sum(1 for s in btc_signal if s) / len(btc_signal) * 100
    print(f"    BTC: {len(btc_bars)} bars, MA50+W5 LONG on {long_frac:.0f}% of bars")

    # Variants to test
    variants = [
        ("MA20+W5 only",                      False, False, build_ma20w5, 0.0, 0.0),
        ("MA20+W5 + BTC gate",                False, True,  build_ma20w5, 0.0, 0.0),
        ("MA20+W5 + BTC gate + vol-target",   False, True,  build_ma20w5, args.target_vol, 0.0),
        ("MA20+W5 + BTC + vol + stop",        False, True,  build_ma20w5, args.target_vol, args.stop_pct),
        ("Vote ≥2 of 3 (binary)",             True,  True,  None,         0.0, 0.0),
        ("Vote ≥2 of 3 + vol-target",         True,  True,  None,         args.target_vol, 0.0),
        ("Vote ≥2 of 3 + vol + stop",         True,  True,  None,         args.target_vol, args.stop_pct),
    ]

    print("\n" + "═" * 122)
    print(f"  {'variant':<36}  {'Sharpe':>7}  {'ROI%':>11}  "
          f"{'MC%':>6}  {'rolling':>9}  {'recent%':>9}  {'trades':>7}  SHIP?")
    print("  " + "-" * 118)

    results = {}
    for name, use_vote, use_btc, builder, tvol, stop in variants:
        t0 = time.time()
        port_r, port_eq, trades = portfolio_run(
            bars_by_pair, builder, btc_signal, btc_ts,
            target_vol=tvol, stop_loss_pct=stop,
            use_vote=use_vote, use_btc_gate=use_btc)
        sharpe = _sharpe(port_r)
        roi = (port_eq[-1] - port_eq[0]) / port_eq[0] * 100 if port_eq else 0
        mc = portfolio_mc(bars_by_pair, btc_signal, btc_ts,
                          use_vote, use_btc, builder, tvol, stop, args.mc_runs)
        wins, total = portfolio_rolling(bars_by_pair, btc_signal, btc_ts,
                                        use_vote, use_btc, builder, tvol, stop,
                                        args.windows)
        recent = portfolio_recent(bars_by_pair, btc_signal, btc_ts,
                                  use_vote, use_btc, builder, tvol, stop)
        passes = (mc >= 99 and (total > 0 and wins / total >= 4/5)
                  and recent > 0)
        mark = "✅" if passes else ""
        results[name] = dict(sharpe=sharpe, roi=roi, mc=mc,
                             wins=wins, total=total, recent=recent,
                             trades=trades, passes=passes)
        print(f"  {name:<36}  {sharpe:>+6.2f}  {roi:>+10.1f}%  "
              f"{mc:>5.1f}%  {wins}/{total:<7}  {recent:>+8.1f}%  "
              f"{trades:>7}  {mark}  ({time.time()-t0:.1f}s)")

    # Verdict
    print("\n" + "═" * 122)
    winners = [(n, r) for n, r in results.items() if r["passes"]]
    if winners:
        winners.sort(key=lambda x: -x[1]["sharpe"])
        n, r = winners[0]
        print(f"  ✅ SHIP — {n}")
        print(f"     Sharpe {r['sharpe']:+.2f}  ROI {r['roi']:+.1f}%  "
              f"MC {r['mc']:.1f}%  rolling {r['wins']}/{r['total']}  "
              f"recent {r['recent']:+.1f}%  trades {r['trades']}")
    else:
        best = max(results.items(),
                   key=lambda kv: kv[1]["mc"]
                         + 15 * (kv[1]["wins"] / max(1, kv[1]["total"]))
                         + (5 if kv[1]["recent"] > 0 else 0))
        print(f"  🛑 Still no ship candidate. Best effort: {best[0]}")
        r = best[1]
        print(f"     Sharpe {r['sharpe']:+.2f}  ROI {r['roi']:+.1f}%  "
              f"MC {r['mc']:.1f}%  rolling {r['wins']}/{r['total']}  "
              f"recent {r['recent']:+.1f}%  trades {r['trades']}")


if __name__ == "__main__":
    main()
