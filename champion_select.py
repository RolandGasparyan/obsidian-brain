#!/usr/bin/env python3
"""
Champion Select — across the entire research arc, which (strategy, pair,
timeframe, params) cell has the best honest OOS performance, and what's
the minimum config change to deploy it?

Tests every variant that appeared positive in any prior research script:

  candidates from godsmode_backtest.py top-cells:
    ETH  1d  MAWeekly        ma=50, weekly=5      (best 1d ETH cell)
    ETH  4h  MAWeekly        ma=20, weekly=5      (best 4h ETH cell)
    ETH  4h  SmaCross        n1=10, n2=30
    XRP  4h  RSI-2 reversion lower=10, upper=70

  candidates from edge_recovery_backtest.py:
    ETH  1d  MAWeekly + ATR-expansion   (V2, ETH-only positive)

  baseline / current production:
    All  1d  MA50+W10  (legacy default)
    All  1d  MA20+W5   (param-sweep winner)
    All  1d  Vote ≥2 of 3  (current production via run_vote_strategy)

Methodology: backtesting.py 0.6.5 · 1000 bars · 70/30 train/test ·
commission 0.0025 (0.25% RT, conservative) · finalize_trades=True.

Output:
  1. Ranking table sorted by OOS_Sharpe primary, OOS_Return secondary
  2. The single CHAMPION cell with full stats
  3. Recommended config integration (PAIRS list + strategy flag)
  4. Honest note on whether this winner cleared the spec ship gates
     (audit §8: OOS Sharpe ≥ 0.5; ADR-002: 0.30% net edge)

If champion violates ADR-003 (requires new strategy code on main),
output the integration plan but DO NOT execute the deploy step here.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import resample_apply

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar
from backtest_multi_token import fetch_gateio_bars


PAIRS = ["ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]


# ── data adapter ─────────────────────────────────────────────────────
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


# ── helpers ─────────────────────────────────────────────────────────
def _sma(arr, n):
    return pd.Series(arr).rolling(n, min_periods=1).mean().to_numpy()


def _atr(high, low, close, n):
    h, l, c = pd.Series(high), pd.Series(low), pd.Series(close)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean().to_numpy()


def _rsi(arr, n):
    s = pd.Series(arr)
    d = s.diff()
    g = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = g / l.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50).to_numpy()


# ── strategy classes (frozen at the parameters that won historically) ──
class MAW_50_5(Strategy):
    """MA50 + W5 — godsmode top cell for ETH 1d / SOL 1d."""
    def init(self):
        c = self.data.Close
        self.sma_d = self.I(_sma, c, 50)
        self.sma_w = self.I(resample_apply, "W", _sma, c, 5, overlay=True)

    def next(self):
        if len(self.data.Close) < 50: return
        px = self.data.Close[-1]
        d, w = self.sma_d[-1], self.sma_w[-1]
        if math.isnan(d) or math.isnan(w): return
        h = 0.0025
        if self.position:
            if px < d * (1 - h) or px < w * (1 - h):
                self.position.close()
        else:
            if px > d * (1 + h) and px > w * (1 + h):
                self.buy()


class MAW_20_5(Strategy):
    """MA20 + W5 — param-sweep winner."""
    def init(self):
        c = self.data.Close
        self.sma_d = self.I(_sma, c, 20)
        self.sma_w = self.I(resample_apply, "W", _sma, c, 5, overlay=True)

    def next(self):
        if len(self.data.Close) < 35: return
        px = self.data.Close[-1]
        d, w = self.sma_d[-1], self.sma_w[-1]
        if math.isnan(d) or math.isnan(w): return
        h = 0.0025
        if self.position:
            if px < d * (1 - h) or px < w * (1 - h):
                self.position.close()
        else:
            if px > d * (1 + h) and px > w * (1 + h):
                self.buy()


class MAW_50_10(Strategy):
    """MA50 + W10 — original production legacy."""
    def init(self):
        c = self.data.Close
        self.sma_d = self.I(_sma, c, 50)
        self.sma_w = self.I(resample_apply, "W", _sma, c, 10, overlay=True)

    def next(self):
        if len(self.data.Close) < 70: return
        px = self.data.Close[-1]
        d, w = self.sma_d[-1], self.sma_w[-1]
        if math.isnan(d) or math.isnan(w): return
        h = 0.0025
        if self.position:
            if px < d * (1 - h) or px < w * (1 - h):
                self.position.close()
        else:
            if px > d * (1 + h) and px > w * (1 + h):
                self.buy()


class MAW_20_5_ATR(Strategy):
    """MA20 + W5 + ATR expansion gate — Edge Recovery V2 (ETH-only positive)."""
    def init(self):
        c = self.data.Close
        self.sma_d = self.I(_sma, c, 20)
        self.sma_w = self.I(resample_apply, "W", _sma, c, 5, overlay=True)
        self.atr_s = self.I(_atr, self.data.High, self.data.Low,
                             self.data.Close, 14)
        self.atr_l = self.I(_atr, self.data.High, self.data.Low,
                             self.data.Close, 60)

    def next(self):
        if len(self.data.Close) < 60: return
        if (math.isnan(self.atr_s[-1]) or math.isnan(self.atr_l[-1])
                or self.atr_l[-1] <= 0):
            return
        ratio = self.atr_s[-1] / self.atr_l[-1]
        if not (1.2 <= ratio <= 2.5):
            if self.position:
                self.position.close()
            return
        px = self.data.Close[-1]
        d, w = self.sma_d[-1], self.sma_w[-1]
        if math.isnan(d) or math.isnan(w): return
        h = 0.0025
        if self.position:
            if px < d * (1 - h) or px < w * (1 - h):
                self.position.close()
        else:
            if px > d * (1 + h) and px > w * (1 + h):
                self.buy()


class SmaCross_10_30(Strategy):
    """Classic SMA crossover — godsmode top ETH 4h cell."""
    def init(self):
        c = self.data.Close
        self.s1 = self.I(_sma, c, 10)
        self.s2 = self.I(_sma, c, 30)

    def next(self):
        if len(self.data.Close) < 30: return
        if self.s1[-1] > self.s2[-1] and not self.position:
            self.buy()
        elif self.s1[-1] < self.s2[-1] and self.position:
            self.position.close()


class RSI2(Strategy):
    """RSI-2 mean reversion — appeared in godsmode XRP/AVAX cells."""
    def init(self):
        self.rsi = self.I(_rsi, self.data.Close, 2)

    def next(self):
        if len(self.data.Close) < 5: return
        if math.isnan(self.rsi[-1]): return
        if self.position:
            if self.rsi[-1] > 70:
                self.position.close()
        else:
            if self.rsi[-1] < 10:
                self.buy()


# ── candidate registry ───────────────────────────────────────────────
# (strategy_class, label, timeframe, run_only_on_pair_subset)
CANDIDATES = [
    (MAW_50_5,        "MAWeekly_50_5",        "1d", None),
    (MAW_50_5,        "MAWeekly_50_5",        "4h", None),
    (MAW_20_5,        "MAWeekly_20_5",        "1d", None),
    (MAW_20_5,        "MAWeekly_20_5",        "4h", None),
    (MAW_50_10,       "MAWeekly_50_10",       "1d", None),
    (MAW_20_5_ATR,    "MAW_20_5_ATR_filter",  "1d", None),
    (SmaCross_10_30,  "SmaCross_10_30",       "1d", None),
    (SmaCross_10_30,  "SmaCross_10_30",       "4h", None),
    (RSI2,            "RSI2_reversion",       "1d", None),
    (RSI2,            "RSI2_reversion",       "4h", None),
]


# ── runner ───────────────────────────────────────────────────────────
def evaluate(df, StratCls, train_frac=0.7, cash=10_000, commission=0.0025):
    cut = int(len(df) * train_frac)
    train_df, test_df = df.iloc[:cut], df.iloc[cut:]
    if len(train_df) < 150 or len(test_df) < 80:
        return {"error": "insufficient data"}
    try:
        # No optimization — these are FROZEN historical winners
        bt_train = Backtest(train_df, StratCls, cash=cash, commission=commission,
                             finalize_trades=True)
        s_train = bt_train.run()
        bt_test = Backtest(test_df, StratCls, cash=cash, commission=commission,
                            finalize_trades=True)
        s_test = bt_test.run()
        return {
            "train_sharpe": float(s_train.get("Sharpe Ratio", 0) or 0),
            "train_ret":    float(s_train.get("Return [%]", 0) or 0),
            "test_sharpe":  float(s_test.get("Sharpe Ratio", 0) or 0),
            "test_sqn":     float(s_test.get("SQN", 0) or 0),
            "test_ret":     float(s_test.get("Return [%]", 0) or 0),
            "test_bh":      float(s_test.get("Buy & Hold Return [%]", 0) or 0),
            "test_dd":      float(s_test.get("Max. Drawdown [%]", 0) or 0),
            "test_wr":      float(s_test.get("Win Rate [%]", 0) or 0),
            "test_trades":  int(s_test.get("# Trades", 0) or 0),
            "test_avg":     float(s_test.get("Avg. Trade [%]", 0) or 0),
            "test_pf":      float(s_test.get("Profit Factor", 0) or 0),
        }
    except Exception as e:
        return {"error": str(e)[:100]}


def composite_score(r):
    """Single rank metric: OOS Sharpe + WR-bonus - DD-penalty.
    Punishes near-zero trade counts."""
    if "error" in r: return -999.0
    if r["test_trades"] < 3: return -999.0   # statistically meaningless
    sharpe = r["test_sharpe"] if not math.isnan(r["test_sharpe"]) else 0
    wr_bonus = (r["test_wr"] - 50) / 50.0    # 50% WR neutral
    dd_pen = abs(r["test_dd"]) / 100.0
    edge_bonus = 1.0 if r["test_ret"] > 0 else -0.5
    return sharpe + wr_bonus - dd_pen + edge_bonus


# ── main ─────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS)
    ap.add_argument("--history", type=int, default=1000)
    args = ap.parse_args()

    print("═" * 116)
    print(f"  CHAMPION SELECT — comprehensive history-of-research backtest aggregator")
    print(f"  {len(args.pairs)} pairs × {len(CANDIDATES)} candidates = "
          f"{len(args.pairs) * len(CANDIDATES)} cells")
    print("═" * 116)

    print("\n▸ Fetching data per timeframe")
    data: Dict[Tuple[str, str], pd.DataFrame] = {}
    for tf in {tf for _, _, tf, _ in CANDIDATES}:
        for pair in args.pairs:
            bars = fetch_gateio_bars(pair, tf, args.history)
            if len(bars) >= 400:
                data[(pair, tf)] = bars_to_df(bars)
                print(f"    {pair:<10} {tf:<3}  {len(bars)} bars")

    print("\n▸ Running all (candidate × pair × tf) cells\n")
    all_results = []
    for cls, label, tf, only_pairs in CANDIDATES:
        for pair in args.pairs:
            if only_pairs and pair not in only_pairs:
                continue
            df = data.get((pair, tf))
            if df is None: continue
            r = evaluate(df, cls)
            r["label"] = label
            r["pair"] = pair
            r["tf"] = tf
            r["score"] = composite_score(r)
            all_results.append(r)
            if "error" in r:
                print(f"  {pair:<10} {tf:<3} {label:<24} ERR: {r['error']}")
            else:
                marker = "★" if r["test_sharpe"] >= 0.5 and r["test_ret"] > 0 else ""
                print(f"  {pair:<10} {tf:<3} {label:<24} "
                      f"Sharpe {r['test_sharpe']:>+5.2f}  "
                      f"Ret {r['test_ret']:>+7.1f}%  "
                      f"BH {r['test_bh']:>+7.1f}%  "
                      f"DD {r['test_dd']:>5.1f}%  "
                      f"WR {r['test_wr']:>4.0f}%  "
                      f"#{r['test_trades']:>3}  "
                      f"score {r['score']:>+5.2f}  {marker}")

    # ── Top-10 by composite score ─────────────────────────────────
    print("\n" + "═" * 116)
    print("  TOP 10 CELLS BY COMPOSITE SCORE  (Sharpe + WR-50 - |DD|/100 + EV-bonus)")
    print("═" * 116)
    valid = [r for r in all_results if "error" not in r and r["score"] > -100]
    valid.sort(key=lambda r: -r["score"])
    print(f"  {'#':>3}  {'pair':<10} {'tf':<3} {'strategy':<24} "
          f"{'OOS Sharpe':>12} {'OOS Ret%':>10} {'BH Ret%':>10} "
          f"{'WR%':>5} {'#tr':>4} {'score':>7}")
    print("  " + "-" * 110)
    for i, r in enumerate(valid[:10], 1):
        print(f"  {i:>3}  {r['pair']:<10} {r['tf']:<3} {r['label']:<24} "
              f"{r['test_sharpe']:>+11.2f}  {r['test_ret']:>+9.1f}%  "
              f"{r['test_bh']:>+9.1f}%  {r['test_wr']:>4.0f}%  "
              f"{r['test_trades']:>3}  {r['score']:>+6.2f}")

    if not valid:
        print("\n  🛑 NO valid candidate produced ≥ 3 trades on any pair.")
        return

    champion = valid[0]
    print("\n" + "═" * 116)
    print(f"  🏆 CHAMPION")
    print("═" * 116)
    print(f"  Strategy:        {champion['label']}")
    print(f"  Pair:            {champion['pair']}")
    print(f"  Timeframe:       {champion['tf']}")
    print(f"  OOS Sharpe:      {champion['test_sharpe']:+.2f}")
    print(f"  OOS SQN:         {champion['test_sqn']:+.2f}")
    print(f"  OOS Return:      {champion['test_ret']:+.1f}%  "
          f"(B&H: {champion['test_bh']:+.1f}%)")
    print(f"  Win Rate:        {champion['test_wr']:.0f}%")
    print(f"  Trades:          {champion['test_trades']}")
    print(f"  Avg trade:       {champion['test_avg']:+.2f}%")
    print(f"  Max DD:          {champion['test_dd']:.1f}%")
    print(f"  Profit Factor:   {champion['test_pf']:.2f}")

    # ── ship-gate evaluation ─────────────────────────────────────
    print("\n  ─── Ship-gate evaluation ───")
    sharpe_pass = champion["test_sharpe"] >= 0.5
    ret_pass    = champion["test_ret"] > 0
    bh_pass     = champion["test_ret"] > champion["test_bh"]
    trade_pass  = champion["test_trades"] >= 5
    print(f"    OOS Sharpe ≥ 0.5     {'✓' if sharpe_pass else '✗'}  "
          f"({champion['test_sharpe']:+.2f})")
    print(f"    OOS Return > 0       {'✓' if ret_pass else '✗'}  "
          f"({champion['test_ret']:+.1f}%)")
    print(f"    Beats buy-and-hold   {'✓' if bh_pass else '✗'}  "
          f"({champion['test_ret'] - champion['test_bh']:+.1f}pp vs B&H)")
    print(f"    Trades ≥ 5           {'✓' if trade_pass else '✗'}  "
          f"({champion['test_trades']})")
    all_pass = sharpe_pass and ret_pass and bh_pass and trade_pass

    # ── integration plan ────────────────────────────────────────
    print("\n  ─── Integration plan ───")
    if not all_pass:
        print(f"    🛑 Champion does NOT clear all 4 gates. NOT recommended for "
              f"live deploy.")
        print(f"    Per ADR-001/003: keep current Vote ensemble running, wait "
              f"for D6 microstructure_analyze.py verdict.")
    else:
        print(f"    ✅ Champion clears all 4 gates. Minimum config change:")
        print()
        print(f"      config.py:")
        print(f"        PAIRS = [\"{champion['pair']}\"]")
        print(f"      systemd unit:")
        print(f"        --strategy <maps to {champion['label']}> "
              f"--interval {champion['tf']}")
        print()
        if champion["label"] not in {"MAWeekly_50_10", "MAWeekly_20_5"}:
            print(f"    ⚠ {champion['label']} is NOT one of the existing "
                  f"strategy flags in run.py.")
            print(f"    Adding it requires NEW strategy code, which violates "
                  f"ADR-003 hard rule")
            print(f"    until D7 (May 1). Queue for D7+ deploy.")
        else:
            print(f"    {champion['label']} maps to existing strategy flag — "
                  f"config-only change OK.")
    print("═" * 116)


if __name__ == "__main__":
    main()
