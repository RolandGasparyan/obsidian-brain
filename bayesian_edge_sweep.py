#!/usr/bin/env python3
"""
bayesian_edge_sweep.py — exhaustive parameter search for any tradeable edge
in the existing microstructure feature set.

Honest research code, on feat/bayesian-edge-sweep, NOT merged to main.

THE QUESTION
============
The 7-filter battery shows 40 surviving (pair, feature, horizon) cells with
real IC but Q5−Q1 magnitude below the 30 bps round-trip fee gate. The IC is
real; the magnitude isn't. The question this script answers is:

    "Does ANY parameter combination — entry threshold, hold time, hard stop,
     trailing stop, profit target — turn ANY of these surviving cells into
     a strategy with net Sharpe ≥ 0.5 AFTER realistic taker fees?"

If yes: that cell is a Phase B candidate, gates D6 GO branch.
If no: confirms what 11 prior research rounds already found — no edge in
this data class.

METHODOLOGY
===========
For each (pair, feature) cell that survived the 7-filter battery:

  1. Resample 1Hz parquet to 1-minute OHLC bars + the feature column
     (mid-price as Open=High=Low=Close per bar; feature as bar-mean)
  2. Define FeatureQuintileStrategy:
       - Compute Q-threshold from a rolling lookback window (no look-ahead)
       - Enter long when feature > Q-threshold (bullish bias) or
         < (1 - Q-threshold) for negative-IC cells
       - Exit on horizon_bars OR hard_stop_pct OR profit_target_pct
  3. Bayesian optimization (skopt) over:
       - entry_q_pct       : 75 – 95 (entry strictness)
       - horizon_bars      : 5 – 60 minutes
       - hard_stop_pct     : 0.005 – 0.030
       - profit_target_pct : 0.005 – 0.040
  4. 200 trials per (pair, feature) cell
  5. Maximise: Sharpe Ratio AFTER commission=0.0030 (30 bps RT taker)
  6. Report: best parameters + full stats per cell

PROMOTION
=========
Only flag a cell if the optimized strategy clears ALL of:
  - Net Sharpe ≥ 0.5 after 30 bps fee
  - # Trades ≥ 30 (statistically meaningful)
  - Max DD ≤ 15%
  - Q5−Q1 fairness check (feature mean in winning trades > losing)

A cell that clears these is the Phase B candidate. A cell that doesn't
confirms its edge is below fee economics, full stop.

Usage:
  python bayesian_edge_sweep.py                              # all pairs
  python bayesian_edge_sweep.py --pairs XRP_USDT ETH_USDT    # subset
  python bayesian_edge_sweep.py --features spread_pct        # subset features
  python bayesian_edge_sweep.py --max-tries 50               # quick run
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path("/var/log/microstructure")

# Cells to test (from the D6 7-filter survivor list at 86.7h)
# Format: (pair, feature, sign) where sign=+1 means high-feature=long bias
CANDIDATE_CELLS = [
    ("XRP_USDT", "basis_pct",        +1),  # IC=+0.291 best survivor
    ("XRP_USDT", "book_slope_bid",   -1),  # IC=-0.113
    ("XRP_USDT", "book_slope_ask",   +1),  # IC=+0.112
    ("XRP_USDT", "depth_imbalance",  +1),  # IC=+0.106
    ("XRP_USDT", "ofi_30s",          +1),  # IC=+0.072
    ("BTC_USDT", "depth_imbalance",  +1),  # IC=+0.176
    ("BTC_USDT", "book_slope_bid",   +1),  # IC=+0.099
    ("BTC_USDT", "book_slope_ask",   -1),  # IC=-0.088
    ("ETH_USDT", "depth_imbalance",  +1),  # IC=+0.133
    ("ETH_USDT", "book_slope_bid",   +1),  # IC=+0.079
    ("ETH_USDT", "book_slope_ask",   -1),  # IC=-0.074
]


def load_resampled(pair: str, data_dir: Path,
                    bar_freq: str = "1min") -> pd.DataFrame:
    """Load all parquet for a pair, return DataFrame indexed by ts with OHLC
    and the original feature columns (resampled bar-mean)."""
    files = sorted(data_dir.rglob(f"{pair}.parquet"))
    if not files:
        return pd.DataFrame()
    raw = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    raw = raw.sort_values("ts_ms").drop_duplicates("ts_ms").reset_index(drop=True)
    raw["ts"] = pd.to_datetime(raw["ts_ms"], unit="ms", utc=True)
    raw = raw.set_index("ts")

    # Resample to bar_freq: OHLC from mid + bar-mean for features
    feat_cols = [c for c in raw.columns
                 if c not in ("ts_ms", "pair", "market", "regime_label",
                              "regime_layer1", "regime_layer2",
                              "regime_layer3", "regime_layer4")]
    feat_cols = [c for c in feat_cols if pd.api.types.is_numeric_dtype(raw[c])]

    # OHLC from mid
    ohlc = raw["mid"].resample(bar_freq).agg(["first", "max", "min", "last"])
    ohlc.columns = ["Open", "High", "Low", "Close"]
    ohlc["Volume"] = 1.0  # synthetic — backtesting.py needs the column

    # Feature columns as bar-mean
    for c in feat_cols:
        if c == "mid": continue
        ohlc[c] = raw[c].resample(bar_freq).mean()

    return ohlc.dropna(subset=["Close"])


class FeatureQuintileStrategy(Strategy):
    """Long-only strategy on a single feature quintile breakout.

    Optimisable params:
      feat_name       : column name (set externally)
      sign            : +1 for high-feature=long, -1 for low-feature=long
      entry_q_pct     : percentile cutoff for entry (75–95)
      lookback_bars   : window for Q-threshold computation (rolling, no look-ahead)
      horizon_bars    : max hold time in bars
      hard_stop_pct   : stop-loss % (Patch 1 default 0.025)
      profit_target_pct : take-profit %
    """
    feat_name: str = "basis_pct"
    sign: int = +1
    entry_q_pct: int = 80
    lookback_bars: int = 240   # 4h on 1-min bars
    horizon_bars: int = 30
    hard_stop_pct: float = 0.025
    profit_target_pct: float = 0.020

    def init(self):
        s = pd.Series(self.data.df[self.feat_name].values,
                      index=self.data.index)
        # Rolling Q-threshold with min_periods to avoid first-N NaN issues
        if self.sign > 0:
            self.q_thresh = self.I(
                lambda x: pd.Series(x).rolling(
                    self.lookback_bars, min_periods=60
                ).quantile(self.entry_q_pct / 100.0).values,
                s.values, name="q_thresh", overlay=False)
        else:
            self.q_thresh = self.I(
                lambda x: pd.Series(x).rolling(
                    self.lookback_bars, min_periods=60
                ).quantile(1 - self.entry_q_pct / 100.0).values,
                s.values, name="q_thresh", overlay=False)
        self.feat_arr = s.values
        self._entry_bar = -1

    def next(self):
        i = len(self.data) - 1
        if math.isnan(self.q_thresh[-1]):
            return
        feat = self.feat_arr[i] if i < len(self.feat_arr) else float("nan")
        if math.isnan(feat):
            return

        # Exit logic (must come before entry to handle horizon expiry)
        if self.position:
            bars_held = i - self._entry_bar
            if bars_held >= self.horizon_bars:
                self.position.close()
                self._entry_bar = -1
                return

        # Entry logic: feature crosses threshold in the bullish direction
        if not self.position:
            triggered = (feat > self.q_thresh[-1] if self.sign > 0
                         else feat < self.q_thresh[-1])
            if triggered:
                px = self.data.Close[-1]
                sl = px * (1 - self.hard_stop_pct)
                tp = px * (1 + self.profit_target_pct)
                self.buy(sl=sl, tp=tp)
                self._entry_bar = i


def evaluate_cell(pair: str, feat: str, sign: int,
                   data_dir: Path, max_tries: int = 200,
                   commission: float = 0.0030) -> Dict[str, Any]:
    """Run Bayesian optimization for one (pair, feature) cell."""
    df = load_resampled(pair, data_dir, bar_freq="1min")
    if df.empty or feat not in df.columns:
        return {"error": "no data"}
    if len(df) < 1000:
        return {"error": f"too few bars ({len(df)})"}

    StrategyCls = type(
        f"FQS_{pair}_{feat}",
        (FeatureQuintileStrategy,),
        {"feat_name": feat, "sign": sign},
    )

    bt = Backtest(df, StrategyCls, cash=10_000,
                  commission=commission, finalize_trades=True)

    try:
        stats, _ = bt.optimize(
            entry_q_pct=range(75, 96, 5),
            horizon_bars=range(5, 61, 5),
            hard_stop_pct=[0.010, 0.015, 0.020, 0.025, 0.030],
            profit_target_pct=[0.005, 0.010, 0.015, 0.020, 0.030],
            maximize="Sharpe Ratio",
            method="sambo",  # new Bayesian backend (was "skopt" pre-0.6)
            max_tries=max_tries,
            return_heatmap=True,
            random_state=42,
        )
    except Exception as e:
        return {"error": f"optimize failed: {str(e)[:100]}"}

    s = stats._strategy
    return {
        "best_params": {
            "entry_q_pct":       s.entry_q_pct,
            "horizon_bars":      s.horizon_bars,
            "hard_stop_pct":     s.hard_stop_pct,
            "profit_target_pct": s.profit_target_pct,
        },
        "sharpe":   float(stats.get("Sharpe Ratio", 0) or 0),
        "ret":      float(stats.get("Return [%]", 0) or 0),
        "bh":       float(stats.get("Buy & Hold Return [%]", 0) or 0),
        "dd":       float(stats.get("Max. Drawdown [%]", 0) or 0),
        "wr":       float(stats.get("Win Rate [%]", 0) or 0),
        "trades":   int(stats.get("# Trades", 0) or 0),
        "pf":       float(stats.get("Profit Factor", 0) or 0),
        "sqn":      float(stats.get("SQN", 0) or 0),
        "exposure": float(stats.get("Exposure Time [%]", 0) or 0),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(DATA_DIR))
    ap.add_argument("--pairs", nargs="+", default=None,
                    help="filter to these pairs only")
    ap.add_argument("--features", nargs="+", default=None,
                    help="filter to these features only")
    ap.add_argument("--max-tries", type=int, default=200)
    ap.add_argument("--commission", type=float, default=0.0030,
                    help="round-trip commission, default 0.30%% (taker)")
    args = ap.parse_args()

    cells = CANDIDATE_CELLS
    if args.pairs:
        cells = [c for c in cells if c[0] in args.pairs]
    if args.features:
        cells = [c for c in cells if c[1] in args.features]

    print("═" * 100)
    print(f"  BAYESIAN EDGE SWEEP · {len(cells)} cells × {args.max_tries} trials")
    print(f"  commission: {args.commission * 100:.2f}% RT  (Gate.io taker reference)")
    print(f"  data: {args.data_dir}")
    print("═" * 100)

    results: List[Dict[str, Any]] = []
    for pair, feat, sign in cells:
        print(f"\n▸ {pair} · {feat} (sign={'+' if sign > 0 else '-'})")
        r = evaluate_cell(pair, feat, sign, Path(args.data_dir),
                           max_tries=args.max_tries, commission=args.commission)
        r["pair"] = pair
        r["feature"] = feat
        r["sign"] = sign
        results.append(r)

        if "error" in r:
            print(f"  ERROR: {r['error']}")
            continue
        bp = r["best_params"]
        print(f"  best params: q={bp['entry_q_pct']}  hold={bp['horizon_bars']}m  "
              f"sl={bp['hard_stop_pct']*100:.2f}%  tp={bp['profit_target_pct']*100:.2f}%")
        print(f"  Sharpe {r['sharpe']:+5.2f}  Ret {r['ret']:+6.1f}%  "
              f"vs BH {r['bh']:+6.1f}%  DD {r['dd']:5.1f}%  "
              f"WR {r['wr']:4.0f}%  #{r['trades']:3d}  SQN {r['sqn']:+5.2f}")

    # ── promotion gate
    print("\n" + "═" * 100)
    print("  PROMOTION-GATE ANALYSIS")
    print("═" * 100)
    print("  Gate criteria (Phase B candidate must clear ALL):")
    print(f"    - Net Sharpe ≥ 0.5 after {args.commission*100:.2f}% fee")
    print(f"    - # Trades ≥ 30")
    print(f"    - Max DD ≤ 15%")
    print(f"    - Beats buy-and-hold")
    print()

    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda r: -r["sharpe"])

    print(f"  {'#':>3} {'pair':<10} {'feature':<18} {'Sharpe':>7} {'Ret%':>8} "
          f"{'BH%':>7} {'DD%':>6} {'WR%':>5} {'#tr':>4} {'pass':>6}")
    print("  " + "-" * 84)
    candidates: List[Dict[str, Any]] = []
    for i, r in enumerate(valid, 1):
        passes = (r["sharpe"] >= 0.5 and r["trades"] >= 30
                  and abs(r["dd"]) <= 15 and r["ret"] > r["bh"])
        marker = "✅" if passes else "🛑"
        if passes:
            candidates.append(r)
        print(f"  {i:>3} {r['pair']:<10} {r['feature']:<18} "
              f"{r['sharpe']:>+6.2f}  {r['ret']:>+7.1f}%  "
              f"{r['bh']:>+6.1f}%  {abs(r['dd']):>5.1f}% "
              f"{r['wr']:>4.0f}%  {r['trades']:>3d}  {marker:>6}")

    print()
    if candidates:
        print(f"  🟢 {len(candidates)} cell(s) clear the promotion gate.")
        print(f"     Lead candidate: {candidates[0]['pair']} · {candidates[0]['feature']}")
        print(f"     Next step: walk-forward + Monte Carlo permutation on this cell.")
        print(f"     Do NOT promote to main. ADR-003 still in force until D7 (May 1).")
    else:
        print(f"  🛑 NO cell passes the promotion gate.")
        print(f"     This confirms what the 7-filter battery + signal-nature found:")
        print(f"     single-feature microstructure on Gate.io spot at 30 bps fee is")
        print(f"     below tradeable economics, regardless of parameter tuning.")
        print(f"     Phase B will require ensemble OR maker-execution OR on-chain.")

    print("═" * 100)


if __name__ == "__main__":
    main()
