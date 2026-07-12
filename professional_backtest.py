#!/usr/bin/env python3
"""
Professional backtest using kernc/backtesting.py (the battle-tested
framework).

Our hand-rolled harness got us institutional-grade rigor (walk-forward,
MC permutation, portfolio metrics) but misses several things the
established library does for free:

  * SQN (System Quality Number) — Van Tharp's noise-adjusted metric
  * Kelly Criterion from the trade distribution (not theoretical)
  * Calmar Ratio (CAGR / Max DD)
  * Profit Factor
  * Per-trade attribution (entry/exit bar, holding time)
  * Built-in grid + Bayesian optimizer with constraint support
  * Proper HL fills (not just close-to-close)

Pipeline:
  1. Fetch 2500 daily bars per pair from Gate.io.
  2. Split 70/30 TRAIN/TEST (strict out-of-sample holdout).
  3. For each strategy × pair:
        a) Optimize parameters on TRAIN, maximize SQN.
        b) Apply frozen optimal params to TEST — report OOS stats.
  4. Rank strategies by OOS SQN × OOS Sharpe (both must be positive
     to be considered deployable).
  5. Winner is the strategy with the best OOS performance that beats
     our current production Vote ≥2 of 3.

Usage:
  python professional_backtest.py
  python professional_backtest.py --pairs ETH_USDT SOL_USDT
  python professional_backtest.py --train-frac 0.6
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

try:
    import pandas as pd
except ImportError:
    print("pandas missing — pip install pandas"); sys.exit(1)

try:
    from backtesting import Backtest, Strategy
    from backtesting.lib import crossover, resample_apply
except ImportError as e:
    print(f"backtesting import failed: {e}"); sys.exit(1)

# SMA is no longer exported from backtesting.lib in 0.6.5 — define here
def SMA(values, n):
    """Simple moving average — array-compatible with self.I()."""
    return pd.Series(values).rolling(n).mean()

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar
from backtest_multi_token import fetch_gateio_bars


PAIRS_DEFAULT = ["ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]


# ── data adapter: Bar → pandas OHLCV DataFrame ───────────────────────
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


# ── Strategy 1: MA+W (our current research winner) ────────────────────
class MAWeekly(Strategy):
    """Daily SMA + weekly SMA trend filter with hysteresis band."""
    ma_period     = 20
    weekly_period = 5
    hysteresis    = 25  # in basis points (25 = 0.25%)

    def init(self):
        close = self.data.Close
        self.sma_d = self.I(SMA, close, self.ma_period, name="SMA_d")
        # Weekly SMA — resample daily closes to weekly, compute SMA
        self.sma_w = self.I(
            resample_apply, "W", SMA, close, self.weekly_period,
            name="SMA_w", overlay=True,
        )

    def next(self):
        if len(self.data.Close) < max(self.ma_period, self.weekly_period * 7):
            return
        px = self.data.Close[-1]
        d_ma = self.sma_d[-1]
        w_ma = self.sma_w[-1]
        if math.isnan(d_ma) or math.isnan(w_ma):
            return
        hy = self.hysteresis / 10000.0
        upper_d = d_ma * (1 + hy); lower_d = d_ma * (1 - hy)
        upper_w = w_ma * (1 + hy); lower_w = w_ma * (1 - hy)

        if self.position:
            # exit if price drops clearly below either MA
            if px < lower_d or px < lower_w:
                self.position.close()
        else:
            if px > upper_d and px > upper_w:
                self.buy()


# ── Strategy 2: Donchian breakout ─────────────────────────────────────
class Donchian(Strategy):
    entry_n = 20
    exit_n  = 10

    def init(self):
        self.entry_high = self.I(lambda x, n: pd.Series(x).rolling(n).max(),
                                 self.data.High, self.entry_n,
                                 name="entry_high")
        self.exit_low   = self.I(lambda x, n: pd.Series(x).rolling(n).min(),
                                 self.data.Low, self.exit_n,
                                 name="exit_low")

    def next(self):
        if math.isnan(self.entry_high[-2]) or math.isnan(self.exit_low[-2]):
            return
        px = self.data.Close[-1]
        if self.position:
            if px < self.exit_low[-2]:
                self.position.close()
        else:
            if px > self.entry_high[-2]:
                self.buy()


# ── Strategy 3: Classic SMA crossover (control) ───────────────────────
class SmaCross(Strategy):
    n1 = 10
    n2 = 30

    def init(self):
        close = self.data.Close
        self.sma1 = self.I(SMA, close, self.n1)
        self.sma2 = self.I(SMA, close, self.n2)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.buy()
        elif crossover(self.sma2, self.sma1) and self.position:
            self.position.close()


# ── Strategy 4: BTC-gated MA+W ────────────────────────────────────────
# Requires a module-level BTC signal injected at runtime.
_BTC_GATE_DF: pd.DataFrame | None = None

def _btc_is_long_on(ts):
    if _BTC_GATE_DF is None or len(_BTC_GATE_DF) == 0:
        return False
    # find last BTC row at or before ts
    try:
        idx = _BTC_GATE_DF.index.get_indexer([ts], method="pad")[0]
    except Exception:
        return False
    if idx < 0: return False
    return bool(_BTC_GATE_DF.iloc[idx].long)


class MAWeeklyBTCGated(Strategy):
    ma_period     = 20
    weekly_period = 5
    hysteresis    = 25

    def init(self):
        close = self.data.Close
        self.sma_d = self.I(SMA, close, self.ma_period, name="SMA_d")
        self.sma_w = self.I(resample_apply, "W", SMA, close, self.weekly_period,
                            name="SMA_w", overlay=True)

    def next(self):
        if len(self.data.Close) < max(self.ma_period, self.weekly_period * 7):
            return
        ts = self.data.index[-1]
        # BTC gate filter
        if not _btc_is_long_on(ts):
            if self.position:
                self.position.close()
            return
        px = self.data.Close[-1]
        d_ma = self.sma_d[-1]
        w_ma = self.sma_w[-1]
        if math.isnan(d_ma) or math.isnan(w_ma):
            return
        hy = self.hysteresis / 10000.0
        if self.position:
            if px < d_ma * (1 - hy) or px < w_ma * (1 - hy):
                self.position.close()
        else:
            if px > d_ma * (1 + hy) and px > w_ma * (1 + hy):
                self.buy()


# ── BTC gate precomputation ───────────────────────────────────────────
def compute_btc_gate_df(history_bars: int = 2500) -> pd.DataFrame:
    global _BTC_GATE_DF
    bars = fetch_gateio_bars("BTC_USDT", "1d", history_bars)
    df = bars_to_df(bars)
    # Use MA50+W5 to determine BTC regime
    close = df["Close"]
    sma_d = close.rolling(50).mean()
    weekly = close.resample("W").last()
    sma_w = weekly.rolling(5).mean().reindex(df.index, method="ffill")
    long = (close > sma_d * 1.0025) & (close > sma_w * 1.0025)
    _BTC_GATE_DF = pd.DataFrame({"long": long})
    return _BTC_GATE_DF


# ── run helper: fit on train, report OOS on test ─────────────────────
def fit_eval(pair: str, df: pd.DataFrame, StrategyCls,
             param_grid: Dict, maximize: str = "SQN",
             train_frac: float = 0.7,
             cash: float = 10_000, commission: float = 0.0025) -> Dict:
    cut = int(len(df) * train_frac)
    train_df, test_df = df.iloc[:cut], df.iloc[cut:]
    if len(train_df) < 150 or len(test_df) < 80:
        return {"error": f"insufficient data ({len(train_df)}/{len(test_df)})"}

    # Optimize on TRAIN
    bt_train = Backtest(train_df, StrategyCls, cash=cash, commission=commission)
    try:
        if param_grid:
            stats_train = bt_train.optimize(
                **param_grid, maximize=maximize, method="grid",
                return_heatmap=False,
            )
        else:
            stats_train = bt_train.run()
    except Exception as e:
        return {"error": str(e)}

    strat_obj = stats_train._strategy
    # Read back the optimized params
    params = {k: getattr(strat_obj, k) for k in param_grid.keys()} if param_grid else {}

    # Apply to TEST (OOS)
    bt_test = Backtest(test_df, StrategyCls, cash=cash, commission=commission)
    stats_test = bt_test.run(**params) if params else bt_test.run()

    return {
        "train_sqn":     stats_train.get("SQN", 0) or 0,
        "train_sharpe":  stats_train.get("Sharpe Ratio", 0) or 0,
        "train_return":  stats_train.get("Return [%]", 0) or 0,
        "train_trades":  stats_train.get("# Trades", 0) or 0,

        "test_sqn":      stats_test.get("SQN", 0) or 0,
        "test_sharpe":   stats_test.get("Sharpe Ratio", 0) or 0,
        "test_sortino":  stats_test.get("Sortino Ratio", 0) or 0,
        "test_calmar":   stats_test.get("Calmar Ratio", 0) or 0,
        "test_return":   stats_test.get("Return [%]", 0) or 0,
        "test_bh":       stats_test.get("Buy & Hold Return [%]", 0) or 0,
        "test_dd":       stats_test.get("Max. Drawdown [%]", 0) or 0,
        "test_winrate":  stats_test.get("Win Rate [%]", 0) or 0,
        "test_trades":   stats_test.get("# Trades", 0) or 0,
        "test_pf":       stats_test.get("Profit Factor", 0) or 0,
        "test_kelly":    stats_test.get("Kelly Criterion", 0) or 0,

        "params":        params,
    }


# ── main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS_DEFAULT)
    ap.add_argument("--history", type=int, default=1000)
    ap.add_argument("--train-frac", type=float, default=0.7)
    args = ap.parse_args()

    print("═" * 115)
    print(f"  PROFESSIONAL BACKTEST (backtesting.py 0.6.5) · "
          f"{len(args.pairs)} pairs · {args.history} bars · "
          f"train/test {args.train_frac*100:.0f}/{(1-args.train_frac)*100:.0f}")
    print("═" * 115)

    # Pre-fetch BTC gate
    print("\n  Fetching BTC reference for gate strategy …")
    compute_btc_gate_df(args.history)
    print(f"  BTC gate df length: {len(_BTC_GATE_DF)} · "
          f"LONG on {_BTC_GATE_DF.long.sum()} bars "
          f"({_BTC_GATE_DF.long.mean()*100:.0f}% of history)")

    # Fetch pair data
    print("\n  Fetching pair data …")
    dfs = {}
    for pair in args.pairs:
        bars = fetch_gateio_bars(pair, "1d", args.history)
        if len(bars) >= 400:
            dfs[pair] = bars_to_df(bars)
            print(f"    {pair:<10}  {len(bars)} bars")
        else:
            print(f"    {pair:<10}  skip ({len(bars)} bars)")

    # Strategies + grids
    strategies = {
        "MA+W": (MAWeekly, {
            "ma_period":     range(10, 61, 10),
            "weekly_period": [3, 5, 10, 20],
            "hysteresis":    [15, 25, 50],
        }),
        "MA+W + BTC gate": (MAWeeklyBTCGated, {
            "ma_period":     range(10, 61, 10),
            "weekly_period": [3, 5, 10, 20],
            "hysteresis":    [15, 25, 50],
        }),
        "Donchian": (Donchian, {
            "entry_n": range(10, 51, 5),
            "exit_n":  range(5, 26, 5),
        }),
        "SmaCross": (SmaCross, {
            "n1": range(5, 21, 5),
            "n2": range(20, 61, 10),
        }),
    }

    results = {}
    for pair, df in dfs.items():
        print(f"\n▸ {pair}")
        print("-" * 115)
        for name, (cls, grid) in strategies.items():
            t0 = time.time()
            try:
                # For cross, add constraint n1 < n2
                res = fit_eval(pair, df, cls, grid,
                               train_frac=args.train_frac)
            except Exception as e:
                res = {"error": str(e)[:80]}
            results.setdefault(pair, {})[name] = res
            if "error" in res:
                print(f"  {name:<18} ERROR: {res['error']}  ({time.time()-t0:.1f}s)")
            else:
                print(f"  {name:<18}  TRAIN SQN {res['train_sqn']:>5.2f}  "
                      f"Sharpe {res['train_sharpe']:>5.2f}  "
                      f"Ret {res['train_return']:>+8.1f}%  |  "
                      f"TEST SQN {res['test_sqn']:>5.2f}  "
                      f"Sharpe {res['test_sharpe']:>5.2f}  "
                      f"Ret {res['test_return']:>+8.1f}% (B&H {res['test_bh']:>+7.1f}%)  "
                      f"DD {res['test_dd']:>5.1f}%  WR {res['test_winrate']:>4.1f}%  "
                      f"#{res['test_trades']:>3}  ({time.time()-t0:.1f}s)")

    # ── cross-pair ranking: mean OOS SQN + mean OOS Sharpe where both > 0
    print("\n" + "═" * 115)
    print("  CROSS-PAIR OOS RANKING (train-optimized params applied to held-out test)")
    print("═" * 115)
    print(f"  {'strategy':<20}  {'avg OOS SQN':>13}  {'avg OOS Sharpe':>15}  "
          f"{'avg OOS Ret%':>13}  {'pairs positive':>16}  {'pairs SQN>2':>12}")
    print("  " + "-" * 111)

    scored = []
    for strat_name in strategies:
        cells = [r for pair, pair_res in results.items()
                 for sn, r in pair_res.items() if sn == strat_name and "error" not in r]
        if not cells:
            continue
        avg_sqn    = sum(c["test_sqn"] for c in cells) / len(cells)
        avg_sharpe = sum(c["test_sharpe"] for c in cells) / len(cells)
        avg_ret    = sum(c["test_return"] for c in cells) / len(cells)
        pos = sum(1 for c in cells if c["test_return"] > 0)
        sqn2 = sum(1 for c in cells if c["test_sqn"] >= 2.0)
        scored.append((avg_sqn + avg_sharpe, strat_name, avg_sqn, avg_sharpe,
                       avg_ret, pos, len(cells), sqn2))

    scored.sort(reverse=True)
    for _, name, sqn, sharpe, ret, pos, n, sqn2 in scored:
        print(f"  {name:<20}  {sqn:>+12.2f}  {sharpe:>+14.2f}  "
              f"{ret:>+12.1f}%  {pos:>6}/{n:<9}  {sqn2:>5}/{n:<6}")

    # Winner
    print("\n" + "═" * 115)
    if scored:
        winner_combined, winner_name = scored[0][0], scored[0][1]
        print(f"  🏆 OOS WINNER — {winner_name}")
        print(f"\n  Per-pair optimal parameters (from TRAIN half):")
        for pair, pair_res in results.items():
            r = pair_res.get(winner_name)
            if r and "error" not in r:
                p = r["params"]
                param_str = " ".join(f"{k}={v}" for k, v in p.items())
                print(f"    {pair:<10}  {param_str}  "
                      f"→ OOS SQN {r['test_sqn']:+.2f}  Sharpe {r['test_sharpe']:+.2f}  "
                      f"Ret {r['test_return']:+.1f}%  DD {r['test_dd']:.1f}%")

        # Interpretation
        _, _, avg_sqn, avg_sharpe, avg_ret, pos, n, sqn2 = scored[0]
        print()
        if avg_sqn >= 2.0 and pos == n and avg_sharpe > 1.0:
            print("  ✅ DEPLOYABLE: average OOS SQN ≥ 2.0, all pairs positive, Sharpe > 1.")
        elif avg_sqn >= 1.0 and pos >= n * 0.75:
            print("  ⚠  MARGINAL: positive edge on most pairs, but SQN < 2 means "
                  "the signal-to-noise is not strong. Small-size deployment only.")
        else:
            print("  🛑 NOT SHIP-READY: negative or near-zero edge OOS.")
    print("═" * 115)


if __name__ == "__main__":
    main()
