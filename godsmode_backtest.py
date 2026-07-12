#!/usr/bin/env python3
"""
GODSMODE BACKTEST — the deepest OOS sweep we've ever done.

10 strategies × 2 timeframes × 4 pairs × 80/20 OOS split = 80 runs,
each grid-optimized on TRAIN then frozen and scored on TEST.

Every family we haven't exhausted:
  1. SmaCross                — classic MA crossover (control)
  2. MAWeekly                — daily MA + weekly filter (our winner)
  3. Donchian                — breakout (20d-high / 10d-low)
  4. Bollinger Breakout      — ride upper-band breakouts (opposite of fade)
  5. MACD                    — histogram sign + signal crossover
  6. Supertrend              — ATR-based direction-flip
  7. Keltner Channel Break   — EMA ± k·ATR breakout
  8. Chandelier Exit         — trailing ATR stop with MA entry
  9. ADX-gated MA            — only trade when trend strength ADX > 25
 10. RSI-2 Reversion         — Connors fast reversion (mean-revert control)

Each strategy gets ~20–60 parameter combos via grid search. Ship gate
for the winner:

  OOS SQN     ≥ 0.5
  OOS Sharpe  ≥ 0.3
  OOS Return  > 0
  Positive on ≥ 3 of 4 pairs AND on ≥ 1 timeframe

If NO strategy clears that bar across even a majority of pairs, we have
our most definitive honest answer: the current crypto regime is not
tradeable by any standard technical rule we've tested.

Usage:
  python godsmode_backtest.py
  python godsmode_backtest.py --timeframes 1d 4h
  python godsmode_backtest.py --strategies MAWeekly Supertrend
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from typing import Dict, List, Tuple

warnings.filterwarnings("ignore")   # suppress backtesting.py open-trades warnings

try:
    import numpy as np
    import pandas as pd
    from backtesting import Backtest, Strategy
    from backtesting.lib import crossover, resample_apply
except ImportError as e:
    print(f"import failed: {e}"); sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar
from backtest_multi_token import fetch_gateio_bars


PAIRS_DEFAULT = ["ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]
TIMEFRAMES    = ["1d", "4h"]


def bars_to_df(bars: List[Bar]) -> pd.DataFrame:
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


# ── indicator helpers ────────────────────────────────────────────────
def _sma(arr, n):
    return pd.Series(arr).rolling(n, min_periods=1).mean().to_numpy()


def _ema(arr, n):
    return pd.Series(arr).ewm(span=n, adjust=False).mean().to_numpy()


def _atr(high, low, close, n):
    h, l, c = pd.Series(high), pd.Series(low), pd.Series(close)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def _stdev(arr, n):
    return pd.Series(arr).rolling(n, min_periods=1).std(ddof=0).to_numpy()


def _rsi(arr, n=14):
    s = pd.Series(arr)
    d = s.diff()
    g = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = g / l.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50).to_numpy()


def _macd(arr, fast=12, slow=26, signal=9):
    f = pd.Series(arr).ewm(span=fast, adjust=False).mean()
    s = pd.Series(arr).ewm(span=slow, adjust=False).mean()
    macd_line = f - s
    sig_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - sig_line
    return macd_line.to_numpy(), sig_line.to_numpy(), hist.to_numpy()


def _supertrend(high, low, close, period=10, mult=3.0):
    atr = _atr(high, low, close, period)
    hl2 = (pd.Series(high) + pd.Series(low)) / 2
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    trend = np.zeros(len(close)); trend[0] = 1
    st = np.zeros(len(close)); st[0] = lower.iloc[0]
    for i in range(1, len(close)):
        if close[i] > upper.iloc[i - 1]:   trend[i] = 1
        elif close[i] < lower.iloc[i - 1]: trend[i] = -1
        else:                              trend[i] = trend[i - 1]
        if trend[i] > 0:
            st[i] = max(lower.iloc[i], st[i - 1]) if trend[i - 1] > 0 else lower.iloc[i]
        else:
            st[i] = min(upper.iloc[i], st[i - 1]) if trend[i - 1] < 0 else upper.iloc[i]
    return st, trend


def _adx(high, low, close, n=14):
    h, l, c = pd.Series(high), pd.Series(low), pd.Series(close)
    up = h.diff(); dn = -l.diff()
    plus_dm  = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    atr_s = tr.ewm(alpha=1/n, adjust=False).mean()
    plus_di  = 100 * pd.Series(plus_dm).ewm(alpha=1/n, adjust=False).mean() / atr_s
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1/n, adjust=False).mean() / atr_s
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).fillna(0)
    return dx.ewm(alpha=1/n, adjust=False).mean().to_numpy()


# ── Strategies ───────────────────────────────────────────────────────
class SmaCross(Strategy):
    n1 = 10; n2 = 30
    def init(self):
        self.sma1 = self.I(_sma, self.data.Close, self.n1)
        self.sma2 = self.I(_sma, self.data.Close, self.n2)
    def next(self):
        if crossover(self.sma1, self.sma2): self.buy()
        elif crossover(self.sma2, self.sma1) and self.position: self.position.close()


class MAWeekly(Strategy):
    ma_period = 20; weekly_period = 5; hysteresis = 25
    def init(self):
        self.sma_d = self.I(_sma, self.data.Close, self.ma_period)
        self.sma_w = self.I(
            resample_apply, "W", _sma, self.data.Close, self.weekly_period,
            overlay=True,
        )
    def next(self):
        if len(self.data.Close) < max(self.ma_period, self.weekly_period * 7):
            return
        px = self.data.Close[-1]
        d, w = self.sma_d[-1], self.sma_w[-1]
        if math.isnan(d) or math.isnan(w): return
        hy = self.hysteresis / 10000.0
        if self.position:
            if px < d * (1 - hy) or px < w * (1 - hy):
                self.position.close()
        else:
            if px > d * (1 + hy) and px > w * (1 + hy):
                self.buy()


class Donchian(Strategy):
    entry_n = 20; exit_n = 10
    def init(self):
        self.eh = self.I(lambda x, n: pd.Series(x).rolling(n).max().to_numpy(),
                         self.data.High, self.entry_n)
        self.el = self.I(lambda x, n: pd.Series(x).rolling(n).min().to_numpy(),
                         self.data.Low, self.exit_n)
    def next(self):
        if math.isnan(self.eh[-2]) or math.isnan(self.el[-2]): return
        if self.position:
            if self.data.Close[-1] < self.el[-2]: self.position.close()
        else:
            if self.data.Close[-1] > self.eh[-2]: self.buy()


class BollingerBreak(Strategy):
    """Buy when close breaks above upper Bollinger band (trend ride, not fade)."""
    period = 20; k = 2
    def init(self):
        self.mid = self.I(_sma, self.data.Close, self.period)
        self.std = self.I(_stdev, self.data.Close, self.period)
    def next(self):
        if math.isnan(self.mid[-1]) or math.isnan(self.std[-1]): return
        upper = self.mid[-1] + self.k * self.std[-1]
        if self.position:
            if self.data.Close[-1] < self.mid[-1]: self.position.close()
        else:
            if self.data.Close[-1] > upper: self.buy()


class MACDSig(Strategy):
    fast = 12; slow = 26; signal_p = 9
    def init(self):
        def _fn(arr):
            m, s, h = _macd(arr, self.fast, self.slow, self.signal_p)
            return m, s
        self.macd, self.sig = self.I(_fn, self.data.Close, overlay=False)
    def next(self):
        if len(self.data) < self.slow + self.signal_p: return
        if crossover(self.macd, self.sig): self.buy()
        elif crossover(self.sig, self.macd) and self.position: self.position.close()


class SuperTrend(Strategy):
    period = 10; mult = 3.0
    def init(self):
        def _fn(h, l, c):
            st, trend = _supertrend(np.array(h), np.array(l), np.array(c),
                                     self.period, self.mult)
            return st, trend
        self.st, self.trend = self.I(
            _fn, self.data.High, self.data.Low, self.data.Close,
            overlay=True,
        )
    def next(self):
        if len(self.data) < self.period + 5: return
        if self.trend[-1] > 0 and not self.position: self.buy()
        elif self.trend[-1] < 0 and self.position:   self.position.close()


class KeltnerBreak(Strategy):
    period = 20; mult = 2.0
    def init(self):
        self.mid = self.I(_ema, self.data.Close, self.period)
        self.atr = self.I(_atr, self.data.High, self.data.Low, self.data.Close,
                          self.period)
    def next(self):
        if math.isnan(self.mid[-1]) or math.isnan(self.atr[-1]): return
        upper = self.mid[-1] + self.mult * self.atr[-1]
        if self.position:
            if self.data.Close[-1] < self.mid[-1]: self.position.close()
        else:
            if self.data.Close[-1] > upper: self.buy()


class ChandelierExit(Strategy):
    """Enter on MA-based trend, exit via ATR trailing stop (chandelier)."""
    ma_period = 20; atr_period = 14; atr_mult = 3.0
    def init(self):
        self.ma  = self.I(_sma, self.data.Close, self.ma_period)
        self.atr = self.I(_atr, self.data.High, self.data.Low, self.data.Close,
                          self.atr_period)
        self.chandelier = None
    def next(self):
        if math.isnan(self.ma[-1]) or math.isnan(self.atr[-1]): return
        px = self.data.Close[-1]
        if not self.position:
            if px > self.ma[-1]:
                self.buy()
                self.chandelier = px - self.atr_mult * self.atr[-1]
        else:
            peak = max(self.data.High[-20:]) if len(self.data.High) >= 20 else px
            ch = peak - self.atr_mult * self.atr[-1]
            self.chandelier = max(self.chandelier, ch) if self.chandelier else ch
            if px < self.chandelier:
                self.position.close()
                self.chandelier = None


class ADXGatedMA(Strategy):
    ma_period = 20; adx_period = 14; adx_min = 25
    def init(self):
        self.ma  = self.I(_sma, self.data.Close, self.ma_period)
        self.adx = self.I(_adx, self.data.High, self.data.Low, self.data.Close,
                          self.adx_period)
    def next(self):
        if math.isnan(self.ma[-1]) or math.isnan(self.adx[-1]): return
        if self.adx[-1] < self.adx_min:
            if self.position: self.position.close()
            return
        if self.position:
            if self.data.Close[-1] < self.ma[-1]: self.position.close()
        else:
            if self.data.Close[-1] > self.ma[-1]: self.buy()


class RSI2Reversion(Strategy):
    rsi_period = 2; lower = 10; upper = 70
    def init(self):
        self.rsi = self.I(_rsi, self.data.Close, self.rsi_period)
    def next(self):
        if math.isnan(self.rsi[-1]): return
        if self.position:
            if self.rsi[-1] > self.upper: self.position.close()
        else:
            if self.rsi[-1] < self.lower: self.buy()


# ── strategy registry with grids ─────────────────────────────────────
STRATEGIES: Dict[str, Tuple[type, Dict]] = {
    "SmaCross":       (SmaCross,       {"n1": [5, 10, 20], "n2": [30, 50, 100]}),
    "MAWeekly":       (MAWeekly,       {"ma_period": [10, 20, 50],
                                         "weekly_period": [3, 5, 10],
                                         "hysteresis": [15, 25, 50]}),
    "Donchian":       (Donchian,       {"entry_n": [10, 20, 40, 55],
                                         "exit_n":  [5, 10, 20]}),
    "BollingerBreak": (BollingerBreak, {"period": [10, 20, 40],
                                         "k":      [1, 2, 3]}),
    "MACDSig":        (MACDSig,        {"fast": [8, 12],
                                         "slow": [21, 26, 34],
                                         "signal_p": [7, 9, 12]}),
    "SuperTrend":     (SuperTrend,     {"period": [7, 10, 14],
                                         "mult":   [2.0, 3.0, 4.0]}),
    "KeltnerBreak":   (KeltnerBreak,   {"period": [10, 20, 40],
                                         "mult":   [1.5, 2.0, 2.5]}),
    "ChandelierExit": (ChandelierExit, {"ma_period":  [10, 20, 50],
                                         "atr_period": [10, 14, 20],
                                         "atr_mult":   [2.0, 3.0, 4.0]}),
    "ADXGatedMA":     (ADXGatedMA,     {"ma_period":  [10, 20, 50],
                                         "adx_period": [10, 14],
                                         "adx_min":    [20, 25, 30]}),
    "RSI2Reversion":  (RSI2Reversion,  {"rsi_period": [2, 4, 7],
                                         "lower":      [10, 20, 30],
                                         "upper":      [70, 80, 90]}),
}


def fit_eval(df, StratCls, grid, train_frac=0.8, cash=10000, commission=0.0025):
    cut = int(len(df) * train_frac)
    train_df, test_df = df.iloc[:cut], df.iloc[cut:]
    if len(train_df) < 100 or len(test_df) < 50:
        return None
    try:
        bt = Backtest(train_df, StratCls, cash=cash, commission=commission,
                      finalize_trades=True)
        stats = bt.optimize(**grid, maximize="SQN", method="grid",
                            return_heatmap=False)
        params = {k: getattr(stats._strategy, k) for k in grid.keys()}
        bt_t = Backtest(test_df, StratCls, cash=cash, commission=commission,
                        finalize_trades=True)
        ts = bt_t.run(**params)
        return {
            "params":       params,
            "train_sqn":    stats.get("SQN", 0) or 0,
            "train_sharpe": stats.get("Sharpe Ratio", 0) or 0,
            "train_ret":    stats.get("Return [%]", 0) or 0,
            "test_sqn":     ts.get("SQN", 0) or 0,
            "test_sharpe":  ts.get("Sharpe Ratio", 0) or 0,
            "test_sortino": ts.get("Sortino Ratio", 0) or 0,
            "test_calmar":  ts.get("Calmar Ratio", 0) or 0,
            "test_ret":     ts.get("Return [%]", 0) or 0,
            "test_bh":      ts.get("Buy & Hold Return [%]", 0) or 0,
            "test_dd":      ts.get("Max. Drawdown [%]", 0) or 0,
            "test_wr":      ts.get("Win Rate [%]", 0) or 0,
            "test_trades":  ts.get("# Trades", 0) or 0,
            "test_pf":      ts.get("Profit Factor", 0) or 0,
            "test_kelly":   ts.get("Kelly Criterion", 0) or 0,
        }
    except Exception as e:
        return {"error": str(e)[:100]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs",      nargs="+", default=PAIRS_DEFAULT)
    ap.add_argument("--timeframes", nargs="+", default=TIMEFRAMES)
    ap.add_argument("--strategies", nargs="+", default=list(STRATEGIES.keys()))
    ap.add_argument("--history",    type=int, default=1000)
    args = ap.parse_args()

    print("═" * 130)
    print(f"  GODSMODE BACKTEST · {len(args.pairs)} pairs × {len(args.timeframes)} TFs "
          f"× {len(args.strategies)} strategies = "
          f"{len(args.pairs)*len(args.timeframes)*len(args.strategies)} runs")
    print("═" * 130)

    # Fetch all data first
    data = {}   # (pair, tf) -> df
    print("\n▸ Data ingestion")
    for tf in args.timeframes:
        for p in args.pairs:
            bars = fetch_gateio_bars(p, tf, args.history)
            if len(bars) >= 250:
                data[(p, tf)] = bars_to_df(bars)
                print(f"    {p:<10} {tf:<3}  {len(bars)} bars")
            else:
                print(f"    {p:<10} {tf:<3}  SKIP ({len(bars)} bars)")

    # Run sweep
    results = []   # (pair, tf, strat_name, res)
    print("\n▸ Sweep\n")
    total = len(data) * len(args.strategies)
    done = 0
    for (pair, tf), df in data.items():
        for strat_name in args.strategies:
            done += 1
            StratCls, grid = STRATEGIES[strat_name]
            t0 = time.time()
            res = fit_eval(df, StratCls, grid)
            dt = time.time() - t0
            if res is None or "error" in res:
                err = res["error"] if res else "no data"
                print(f"  [{done:>3}/{total}] {pair:<10} {tf:<3} {strat_name:<16} ERR: {err}")
                continue
            results.append((pair, tf, strat_name, res))
            print(f"  [{done:>3}/{total}] {pair:<10} {tf:<3} {strat_name:<16} "
                  f"TRAIN SQN {res['train_sqn']:>+5.2f} → "
                  f"TEST SQN {res['test_sqn']:>+5.2f}  "
                  f"Sharpe {res['test_sharpe']:>+5.2f}  "
                  f"Ret {res['test_ret']:>+7.1f}% (BH {res['test_bh']:>+7.1f}%)  "
                  f"#{res['test_trades']:>3}  ({dt:.1f}s)")

    # Aggregate: per (strategy, timeframe) across pairs
    print("\n" + "═" * 130)
    print("  CROSS-PAIR RANKING — by mean OOS SQN (higher better)")
    print("═" * 130)
    print(f"  {'strategy':<18} {'tf':<4} "
          f"{'mean SQN':>10} {'mean Sharpe':>13} {'mean Ret%':>11} "
          f"{'mean DD%':>10} {'pairs +':>8} {'ships':>6}")
    print("  " + "-" * 126)

    grouped = {}
    for pair, tf, strat, res in results:
        key = (strat, tf)
        grouped.setdefault(key, []).append(res)

    scored = []
    for (strat, tf), rows in grouped.items():
        n = len(rows)
        if n == 0: continue
        mean_sqn    = sum(r["test_sqn"] for r in rows) / n
        mean_sharpe = sum(r["test_sharpe"] for r in rows) / n
        mean_ret    = sum(r["test_ret"] for r in rows) / n
        mean_dd     = sum(r["test_dd"] for r in rows) / n
        pos         = sum(1 for r in rows if r["test_ret"] > 0)
        ships       = sum(1 for r in rows
                          if r["test_sqn"] >= 0.5
                          and r["test_sharpe"] >= 0.3
                          and r["test_ret"] > 0)
        scored.append((mean_sqn + mean_sharpe + (ships / n),
                       strat, tf, mean_sqn, mean_sharpe, mean_ret, mean_dd,
                       pos, n, ships))
    scored.sort(reverse=True)
    for _, strat, tf, sqn, sharpe, ret, dd, pos, n, ships in scored:
        print(f"  {strat:<18} {tf:<4} {sqn:>+9.2f} {sharpe:>+12.2f} "
              f"{ret:>+10.1f}% {dd:>+9.1f}% {pos:>4}/{n:<3} {ships:>4}/{n}")

    # Ship-gate winners
    print("\n" + "═" * 130)
    ship_candidates = [(s, tf, sqn, sharpe, ret, dd, pos, n, ships, rows)
                       for (_, s, tf, sqn, sharpe, ret, dd, pos, n, ships) in scored
                       for rows in [grouped[(s, tf)]]
                       if ships >= max(1, 3 * n // 4)   # pass gate on ≥ 75% of pairs
                       and pos == n                      # ALL pairs positive
                       and sqn >= 0.5
                       and sharpe >= 0.3]
    if ship_candidates:
        ship_candidates.sort(key=lambda x: -(x[2] + x[3]))
        print(f"  ✅ SHIP-GATE PASSED — top candidate:")
        s, tf, sqn, sharpe, ret, dd, pos, n, ships, rows = ship_candidates[0]
        print(f"     {s} @ {tf}  mean SQN {sqn:+.2f}  Sharpe {sharpe:+.2f}  "
              f"Ret {ret:+.1f}%  DD {dd:+.1f}%  {pos}/{n} pairs + ({ships} pass gate)")
        print(f"\n     Per-pair optimized params (from TRAIN half):")
        # Walk back to find the pair results for the winning strategy
        for pair, tf2, strat, res in results:
            if strat == s and tf2 == tf:
                ps = " ".join(f"{k}={v}" for k, v in res["params"].items())
                print(f"       {pair:<10}  {ps:<40}  "
                      f"OOS SQN {res['test_sqn']:+.2f}  "
                      f"Sharpe {res['test_sharpe']:+.2f}  "
                      f"Ret {res['test_ret']:+.1f}%")
    else:
        print("  🛑 NO strategy × timeframe passes the ship gate on 75%+ of pairs.")
        print(f"  Best effort: {scored[0][1]} @ {scored[0][2]} — "
              f"mean SQN {scored[0][3]:+.2f}, {scored[0][-1]}/{scored[0][-2]} pairs passing.")
        print()
        print("  This is the deepest validation we have run. The negative verdict")
        print("  is robust across 10 strategy families, 2 timeframes, and 4 pairs.")
        print("  Crypto's current regime (chop + drawdown) is not tradeable with")
        print("  standard technical-signal rules. Either wait for regime change,")
        print("  or switch to a fundamentally different edge (on-chain, options,")
        print("  market-making, arbitrage).")
    print("═" * 130)


if __name__ == "__main__":
    main()
