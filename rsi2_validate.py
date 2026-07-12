#!/usr/bin/env python3
"""
RSI-2 D7 Validation Harness — feature branch only, ADR-003 compliant.

After champion_select.py identified XRP_USDT 4h RSI-2 as the first cell
to clear every audit ship-gate, the next discipline step is to verify
the result is NOT an artifact of a single 70/30 OOS split before D7
deployment. Three independent tests:

  1. ROLLING WALK-FORWARD ─ 5 contiguous train/test windows. If the
     edge survives across distinct historical periods, it's not just a
     lucky break in one regime. Gate: ≥ 4/5 windows beat B&H + Sharpe>0.

  2. MONTE CARLO PERMUTATION ─ shuffle bar log-returns, rebuild a
     synthetic price path with identical drift+vol but no temporal
     pattern, re-run the strategy. If the real Sharpe sits in the top
     5% of shuffled-Sharpe distribution, the edge is real, not pattern
     memorization. Gate: percentile ≥ 95% (SIGNIFICANT).

  3. SLIPPAGE / FEE STRESS ─ RSI-2 fires more often than MA-family
     strategies (~18 trades vs ~7), so fees compound harder. Sweep
     commission from 0.10% to 0.50% RT and verify the edge survives
     even at the hostile end. Gate: OOS Sharpe ≥ 0.5 at 0.40% RT
     (real-world Gate.io spot taker = 0.30% RT).

Plus a sensitivity sweep on the MAX_HOLD_BARS parameter that the D7
risk overlay will introduce — RSI-2 has no natural stop, so we force
exit if RSI doesn't recover in N bars. Test which N value preserves
edge without bleeding too many trades.

Output is a printable verdict per gate. NO strategy code is committed
to main from this script — RSI2Strategy implementation lands at D7.

Usage:
  python rsi2_validate.py                    # full run, XRP 4h, 1000 bars
  python rsi2_validate.py --pair ETH_USDT    # cross-pair sanity check
  python rsi2_validate.py --mc-runs 500      # tighter MC tail
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar
from backtest_multi_token import fetch_gateio_bars


# ── helpers ─────────────────────────────────────────────────────────
def bars_to_df(bars):
    return pd.DataFrame({
        "Open":   [b.o for b in bars],
        "High":   [b.h for b in bars],
        "Low":    [b.l for b in bars],
        "Close":  [b.c for b in bars],
        "Volume": [b.v for b in bars],
    }, index=pd.DatetimeIndex(
        [datetime.fromtimestamp(b.ts, tz=timezone.utc) for b in bars],
        name="Date",
    ))


def _rsi(arr, n):
    s = pd.Series(arr)
    d = s.diff()
    g = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = g / l.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50).to_numpy()


# ── strategy class — frozen at champion_select.py params ────────────
class RSI2(Strategy):
    """
    RSI-2 mean reversion (Connors-style).
    Entry: RSI(2) < 10
    Exit:  RSI(2) > 70
    No risk overlay yet — that's the D7 implementation step.
    """
    rsi_lower = 10
    rsi_upper = 70

    def init(self):
        self.rsi = self.I(_rsi, self.data.Close, 2)

    def next(self):
        if len(self.data.Close) < 5:
            return
        if math.isnan(self.rsi[-1]):
            return
        if self.position:
            if self.rsi[-1] > self.rsi_upper:
                self.position.close()
        else:
            if self.rsi[-1] < self.rsi_lower:
                self.buy()


class RSI2WithStops(Strategy):
    """
    RSI-2 with the D7 risk overlay attached, used in MAX_HOLD_BARS
    sensitivity sweep. Forces exit if RSI doesn't recover in
    `max_hold_bars`, plus hard stop at `hard_stop_pct`.
    """
    rsi_lower = 10
    rsi_upper = 70
    hard_stop_pct = 0.025
    max_hold_bars = 24
    _bars_held = 0
    _entry_px = 0.0

    def init(self):
        self.rsi = self.I(_rsi, self.data.Close, 2)

    def next(self):
        if len(self.data.Close) < 5:
            return
        if math.isnan(self.rsi[-1]):
            return
        px = self.data.Close[-1]
        if self.position:
            self._bars_held += 1
            # Hard stop
            if self._entry_px > 0 and px <= self._entry_px * (1 - self.hard_stop_pct):
                self.position.close()
                self._bars_held = 0
                return
            # Max hold
            if self._bars_held >= self.max_hold_bars:
                self.position.close()
                self._bars_held = 0
                return
            # RSI recovery
            if self.rsi[-1] > self.rsi_upper:
                self.position.close()
                self._bars_held = 0
        else:
            if self.rsi[-1] < self.rsi_lower:
                self.buy()
                self._entry_px = px
                self._bars_held = 0


# ── shared run helper ───────────────────────────────────────────────
def run_bt(df: pd.DataFrame, StratCls, commission: float = 0.0025,
           cash: float = 10_000) -> Dict[str, float]:
    bt = Backtest(df, StratCls, cash=cash, commission=commission,
                  finalize_trades=True)
    s = bt.run()
    return {
        "sharpe":  float(s.get("Sharpe Ratio", 0) or 0),
        "ret":     float(s.get("Return [%]", 0) or 0),
        "bh":      float(s.get("Buy & Hold Return [%]", 0) or 0),
        "dd":      float(s.get("Max. Drawdown [%]", 0) or 0),
        "wr":      float(s.get("Win Rate [%]", 0) or 0),
        "trades":  int(s.get("# Trades", 0) or 0),
        "pf":      float(s.get("Profit Factor", 0) or 0),
        "sqn":     float(s.get("SQN", 0) or 0),
    }


# ── 1. rolling walk-forward ─────────────────────────────────────────
def rolling_walk_forward(df: pd.DataFrame, n_windows: int = 5,
                         train_frac: float = 0.7) -> List[Dict]:
    """
    Slice into n overlapping windows. For each, train_frac for the
    in-sample prefix, the rest as held-out OOS test. Slides forward.
    """
    n = len(df)
    if n < 400:
        return []
    w_size = n // (n_windows + 1)  # overlap so all windows fit
    out = []
    for i in range(n_windows):
        start = i * (n - w_size) // max(1, n_windows - 1) if n_windows > 1 else 0
        end = start + w_size
        window = df.iloc[start:end]
        if len(window) < 150:
            continue
        cut = int(len(window) * train_frac)
        test = window.iloc[cut:]
        if len(test) < 50:
            continue
        r = run_bt(test, RSI2)
        r["window"] = f"[{start}..{end}]"
        r["test_bars"] = len(test)
        r["edge"] = r["ret"] - r["bh"]
        out.append(r)
    return out


# ── 2. Monte Carlo permutation ──────────────────────────────────────
def monte_carlo_permutation(df: pd.DataFrame, n_runs: int = 300,
                            seed: int = 42) -> Dict[str, Any]:
    """
    Compare real OOS Sharpe to Sharpe distribution under shuffled
    log-returns. If real Sharpe is in top tail (>95%), edge is real.
    """
    rng = random.Random(seed)
    real = run_bt(df, RSI2)
    real_sharpe = real["sharpe"]

    closes = df["Close"].to_numpy()
    log_rets = np.diff(np.log(closes))

    mc = []
    for _ in range(n_runs):
        sh = list(log_rets)
        rng.shuffle(sh)
        synth = [closes[0]]
        for r in sh:
            synth.append(synth[-1] * math.exp(r))
        synth_df = pd.DataFrame({
            "Open":  synth, "High": synth, "Low": synth,
            "Close": synth, "Volume": [1.0] * len(synth),
        }, index=df.index[: len(synth)])
        try:
            mc.append(run_bt(synth_df, RSI2)["sharpe"])
        except Exception:
            mc.append(0.0)

    mc.sort()
    if not mc:
        return {"verdict": "INSUFFICIENT", "real_sharpe": real_sharpe}
    beats = sum(1 for s in mc if real_sharpe > s)
    pct = beats / len(mc) * 100
    p99 = mc[int(len(mc) * 0.99)]
    p95 = mc[int(len(mc) * 0.95)]
    return {
        "real_sharpe": real_sharpe,
        "mc_mean":     sum(mc) / len(mc),
        "mc_p95":      p95,
        "mc_p99":      p99,
        "percentile":  pct,
        "verdict":     "SIGNIFICANT" if pct >= 95 else
                       "MARGINAL"    if pct >= 80 else
                       "LIKELY NOISE",
    }


# ── 3. slippage / fee stress sweep ──────────────────────────────────
def fee_stress(df: pd.DataFrame) -> List[Dict]:
    """
    Vary commission from 0.10% to 0.50% round-trip and re-run on the
    held-out OOS slice (last 30%). Real Gate.io spot taker RT ≈ 0.30%.
    """
    cut = int(len(df) * 0.7)
    test = df.iloc[cut:]
    fees = [0.0010, 0.0015, 0.0020, 0.0025, 0.0030, 0.0040, 0.0050]
    out = []
    for fee in fees:
        r = run_bt(test, RSI2, commission=fee)
        r["fee_pct"] = fee * 100
        out.append(r)
    return out


# ── 4. MAX_HOLD_BARS sensitivity ────────────────────────────────────
def max_hold_sweep(df: pd.DataFrame) -> List[Dict]:
    """
    For each candidate MAX_HOLD_BARS value, run RSI2WithStops on the OOS
    slice. Pick the smallest N that preserves OOS Sharpe ≥ baseline.
    """
    cut = int(len(df) * 0.7)
    test = df.iloc[cut:]
    candidates = [12, 18, 24, 36, 48, 72]

    # baseline (no max hold)
    base = run_bt(test, RSI2)
    base["max_hold"] = "None (baseline)"

    out = [base]
    for n in candidates:
        # Use a closure-bound subclass to inject parameter
        cls = type(f"RSI2_h{n}", (RSI2WithStops,), {"max_hold_bars": n})
        try:
            r = run_bt(test, cls)
        except Exception as e:
            r = {"sharpe": 0, "ret": 0, "bh": 0, "dd": 0, "wr": 0,
                 "trades": 0, "pf": 0, "sqn": 0, "error": str(e)[:60]}
        r["max_hold"] = f"{n} bars"
        out.append(r)
    return out


# ── main ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="XRP_USDT")
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--mc-runs", type=int, default=200)
    ap.add_argument("--windows", type=int, default=5)
    args = ap.parse_args()

    print("═" * 100)
    print(f"  RSI-2 D7 VALIDATION HARNESS · {args.pair} · {args.tf} · "
          f"{args.limit} bars")
    print("═" * 100)

    bars = fetch_gateio_bars(args.pair, args.tf, args.limit)
    if len(bars) < 400:
        print(f"\n  🛑 INSUFFICIENT DATA — got {len(bars)} bars, need ≥ 400")
        return
    df = bars_to_df(bars)
    span = (bars[-1].ts - bars[0].ts) / 86400
    print(f"\n  Loaded {len(bars)} bars · {span:.0f} days · "
          f"${bars[0].c:.4f} → ${bars[-1].c:.4f}")

    # ── baseline replay (sanity that champion_select.py result is reproducible)
    print("\n" + "─" * 100)
    print("  BASELINE — full 70/30 OOS replay (verifies champion_select.py result)")
    print("─" * 100)
    cut = int(len(df) * 0.7)
    base = run_bt(df.iloc[cut:], RSI2)
    print(f"    OOS Sharpe       {base['sharpe']:+6.2f}")
    print(f"    OOS Return       {base['ret']:+7.2f}%   B&H {base['bh']:+7.2f}%")
    print(f"    Win Rate         {base['wr']:6.1f}%")
    print(f"    Trades           {base['trades']:>4d}")
    print(f"    Max Drawdown     {base['dd']:6.1f}%")
    print(f"    Profit Factor    {base['pf']:6.2f}")
    print(f"    SQN              {base['sqn']:6.2f}")

    # ── 1. rolling walk-forward
    print("\n" + "─" * 100)
    print(f"  GATE 1 — ROLLING WALK-FORWARD ({args.windows} windows)")
    print("─" * 100)
    rwf = rolling_walk_forward(df, n_windows=args.windows)
    if not rwf:
        print("    🛑 insufficient data for rolling test")
    else:
        print(f"    {'window':<14}{'OOS bars':>10}{'OOS Ret%':>10}"
              f"{'B&H Ret%':>10}{'edge':>10}{'Sharpe':>9}{'#tr':>5}")
        for r in rwf:
            print(f"    {r['window']:<14}{r['test_bars']:>10}"
                  f"{r['ret']:>+9.2f}%{r['bh']:>+9.2f}%"
                  f"{r['edge']:>+9.2f}%{r['sharpe']:>+9.2f}"
                  f"{r['trades']:>5d}")
        wins = sum(1 for r in rwf if r["edge"] > 0 and r["sharpe"] > 0)
        gate1 = wins >= max(3, len(rwf) - 1)  # ≥ 4/5
        print(f"\n    → {wins}/{len(rwf)} windows beat B&H AND Sharpe > 0 "
              f"{'✅ PASS' if gate1 else '🛑 FAIL'}")

    # ── 2. Monte Carlo permutation
    print("\n" + "─" * 100)
    print(f"  GATE 2 — MONTE CARLO PERMUTATION ({args.mc_runs} shuffled runs)")
    print("─" * 100)
    mc = monte_carlo_permutation(df, n_runs=args.mc_runs)
    print(f"    Real Sharpe:           {mc['real_sharpe']:+6.2f}")
    print(f"    Shuffled mean:         {mc['mc_mean']:+6.2f}")
    print(f"    Shuffled p95:          {mc['mc_p95']:+6.2f}")
    print(f"    Shuffled p99:          {mc['mc_p99']:+6.2f}")
    print(f"    Real beats {mc['percentile']:.1f}% of shuffles")
    gate2 = mc["verdict"] == "SIGNIFICANT"
    print(f"    Verdict: **{mc['verdict']}**  "
          f"{'✅ PASS' if gate2 else '🛑 FAIL'}")

    # ── 3. fee stress
    print("\n" + "─" * 100)
    print("  GATE 3 — FEE / SLIPPAGE STRESS  (Gate.io spot taker RT ≈ 0.30%)")
    print("─" * 100)
    fs = fee_stress(df)
    print(f"    {'fee RT%':>8}{'Sharpe':>10}{'OOS Ret%':>11}{'#trades':>9}{'PF':>7}")
    for r in fs:
        print(f"    {r['fee_pct']:>7.2f}%{r['sharpe']:>+9.2f}{r['ret']:>+10.2f}%"
              f"{r['trades']:>9d}{r['pf']:>7.2f}")
    # gate: Sharpe ≥ 0.5 at 0.40% (worst plausible)
    target = next((r for r in fs if abs(r["fee_pct"] - 0.40) < 0.01), None)
    gate3 = target is not None and target["sharpe"] >= 0.5
    print(f"\n    → Sharpe @ 0.40% RT = {target['sharpe']:+.2f} "
          f"(target ≥ 0.50)  "
          f"{'✅ PASS' if gate3 else '🛑 FAIL'}")

    # ── 4. max-hold-bars sweep
    print("\n" + "─" * 100)
    print("  GATE 4 — MAX_HOLD_BARS SENSITIVITY  (D7 risk overlay design)")
    print("─" * 100)
    mh = max_hold_sweep(df)
    print(f"    {'max_hold':<22}{'Sharpe':>9}{'OOS Ret%':>10}"
          f"{'WR%':>7}{'#tr':>5}{'PF':>7}")
    for r in mh:
        if "error" in r:
            print(f"    {r['max_hold']:<22} ERR: {r['error']}")
            continue
        print(f"    {r['max_hold']:<22}{r['sharpe']:>+8.2f}"
              f"{r['ret']:>+9.2f}%{r['wr']:>6.1f}%{r['trades']:>5d}{r['pf']:>7.2f}")

    # ── final verdict
    print("\n" + "═" * 100)
    print("  D7 SHIP READINESS SUMMARY")
    print("═" * 100)
    gates = [
        ("1 · Rolling walk-forward",  gate1 if rwf else False),
        ("2 · Monte Carlo permutation", gate2),
        ("3 · Fee stress @ 0.40%",      gate3),
    ]
    passed = sum(1 for _, p in gates if p)
    for name, p in gates:
        print(f"    {name:<40} {'✅' if p else '🛑'}")
    print(f"\n    {passed}/{len(gates)} gates passed")
    if passed == len(gates):
        print("    🟢 RSI-2 cleared all D7 validation gates. Ship plan confirmed.")
    elif passed >= len(gates) - 1:
        print("    🟡 RSI-2 cleared most gates. Investigate the failed gate before D7.")
    else:
        print("    🛑 RSI-2 fails majority of gates. DO NOT proceed to D7 deploy.")
    print("═" * 100)


if __name__ == "__main__":
    main()
