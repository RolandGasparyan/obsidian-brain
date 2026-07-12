#!/usr/bin/env python3
"""
ensemble_edge_sweep.py — multi-feature alignment ensemble research.

THE THESIS
==========
The 7-filter battery + Bayesian single-feature sweep both confirmed that
no individual microstructure feature on Gate.io spot has Q5−Q1 magnitude
above the 30 bps round-trip taker fee. Each surviving cell has IC ≈ +0.1
to +0.3 with magnitude 14 bps gross.

The hypothesis this script tests: when MULTIPLE independent features all
agree on direction simultaneously, the per-trade signal-to-noise ratio is
higher even if each feature is individually weak. Trade fewer times, but
each trade has a stronger edge.

Concretely: enter LONG only when ≥ K of N features simultaneously fire
their bullish-quintile threshold. K is the alignment requirement.

POSSIBLE OUTCOMES
=================
- ✅ alignment > sum-of-parts: per-trade edge ≥ 30 bps, infrequent but real
  → Phase B B.2.1 candidate; walk-forward validate, gate at D6
- 🛑 alignment ≈ noise: features are correlated enough that "agreement"
  doesn't reduce noise OR alignment is too rare to be tradeable
  → confirms Phase B must look elsewhere (maker exec, on-chain B1)

Both outcomes are useful. Both stay on this feature branch.

METHODOLOGY
===========
1. For each pair, take the cells that survived the 7-filter battery.
2. Build per-pair feature signal: for each feature, compute its rolling
   percentile rank (Q5 = top 20%, Q1 = bottom 20%).
3. Define alignment score = number of features whose rank is in the
   bullish-direction quintile (Q5 for positive-IC features, Q1 for
   negative-IC features).
4. Strategy: enter LONG when alignment_score ≥ K. Exit on horizon OR
   hard_stop OR profit_target.
5. Backtest with realistic 30 bps RT taker fee.
6. Bayesian-optimize K, lookback_bars, horizon_bars, hard_stop_pct,
   profit_target_pct.
7. Honest report.

NOT INTEGRATED INTO PRODUCTION. Research code on feat/ensemble-edge-sweep,
NOT merged to main. ADR-003 still in force until D7 (May 1).
"""
from __future__ import annotations

import argparse
import math
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path("/var/log/microstructure")

# Cells from D6 7-filter survivor list at 86.7h, grouped by pair.
# (feature, sign): sign=+1 means high-feature → bullish (Q5 entry),
#                  sign=-1 means low-feature → bullish (Q1 entry)
PAIR_FEATURES: Dict[str, List[Tuple[str, int]]] = {
    "XRP_USDT": [
        ("basis_pct",         +1),
        ("depth_imbalance",   +1),
        ("book_slope_bid",    -1),
        ("book_slope_ask",    +1),
        ("ofi_30s",           +1),
    ],
    "ETH_USDT": [
        ("depth_imbalance",   +1),
        ("book_slope_bid",    +1),
        ("book_slope_ask",    -1),
    ],
    "BTC_USDT": [
        ("depth_imbalance",   +1),
        ("book_slope_bid",    +1),
        ("book_slope_ask",    -1),
    ],
}


def load_resampled(pair: str, data_dir: Path,
                    bar_freq: str = "1min") -> pd.DataFrame:
    files = sorted(data_dir.rglob(f"{pair}.parquet"))
    if not files:
        return pd.DataFrame()
    raw = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    raw = raw.sort_values("ts_ms").drop_duplicates("ts_ms").reset_index(drop=True)
    raw["ts"] = pd.to_datetime(raw["ts_ms"], unit="ms", utc=True)
    raw = raw.set_index("ts")

    feat_cols = [c for c in raw.columns
                 if c not in ("ts_ms", "pair", "market", "regime_label",
                              "regime_layer1", "regime_layer2",
                              "regime_layer3", "regime_layer4")
                 and pd.api.types.is_numeric_dtype(raw[c])]

    ohlc = raw["mid"].resample(bar_freq).agg(["first", "max", "min", "last"])
    ohlc.columns = ["Open", "High", "Low", "Close"]
    ohlc["Volume"] = 1.0
    for c in feat_cols:
        if c == "mid": continue
        ohlc[c] = raw[c].resample(bar_freq).mean()
    return ohlc.dropna(subset=["Close"])


def compute_alignment_score(df: pd.DataFrame,
                             feats: List[Tuple[str, int]],
                             entry_q_pct: float,
                             lookback_bars: int) -> np.ndarray:
    """For each bar, count how many features are in their bullish quintile.
    Uses ROLLING percentile rank (no look-ahead)."""
    score = np.zeros(len(df), dtype=int)
    for feat, sign in feats:
        if feat not in df.columns: continue
        s = df[feat]
        # Rolling rank of current value within trailing window (0..1)
        rolling_rank = s.rolling(lookback_bars, min_periods=60).apply(
            lambda x: (x.iloc[-1] > x).sum() / len(x), raw=False)
        if sign > 0:
            # Bullish when rank > entry_q_pct/100 (e.g. >0.80 = top 20%)
            in_quintile = (rolling_rank > entry_q_pct / 100.0).astype(int)
        else:
            # Bullish when rank < (1 - entry_q_pct/100) (e.g. <0.20 = bottom 20%)
            in_quintile = (rolling_rank < (1 - entry_q_pct / 100.0)).astype(int)
        score += in_quintile.fillna(0).astype(int).values
    return score


class EnsembleAlignmentStrategy(Strategy):
    pair: str = "XRP_USDT"
    feats: tuple = ()
    K: int = 3
    entry_q_pct: int = 80
    lookback_bars: int = 240
    horizon_bars: int = 30
    hard_stop_pct: float = 0.025
    profit_target_pct: float = 0.020

    def init(self):
        # Compute alignment score once at init (uses rolling, no look-ahead)
        align = compute_alignment_score(
            self.data.df, list(self.feats),
            self.entry_q_pct, self.lookback_bars)
        self.align = self.I(lambda: align, name="align", overlay=False)
        self._entry_bar = -1

    def next(self):
        i = len(self.data) - 1
        if math.isnan(self.align[-1]): return

        if self.position:
            bars_held = i - self._entry_bar
            if bars_held >= self.horizon_bars:
                self.position.close()
                self._entry_bar = -1
                return

        if not self.position and self.align[-1] >= self.K:
            px = self.data.Close[-1]
            self.buy(sl=px * (1 - self.hard_stop_pct),
                     tp=px * (1 + self.profit_target_pct))
            self._entry_bar = i


def evaluate_pair(pair: str, feats: List[Tuple[str, int]],
                   data_dir: Path, max_tries: int = 50,
                   commission: float = 0.0030) -> Dict[str, Any]:
    df = load_resampled(pair, data_dir, bar_freq="1min")
    if df.empty:
        return {"error": "no data"}
    if len(df) < 1000:
        return {"error": f"too few bars ({len(df)})"}

    n_feats = len(feats)
    StrategyCls = type(
        f"EAS_{pair}",
        (EnsembleAlignmentStrategy,),
        {"pair": pair, "feats": tuple(feats)},
    )

    bt = Backtest(df, StrategyCls, cash=10_000,
                  commission=commission, finalize_trades=True)

    try:
        # K must be ≤ number of available features
        K_range = list(range(2, n_feats + 1))
        stats, _ = bt.optimize(
            K=K_range,
            entry_q_pct=range(70, 91, 5),
            lookback_bars=[120, 240, 480, 720],
            horizon_bars=range(5, 61, 10),
            hard_stop_pct=[0.010, 0.015, 0.020, 0.025, 0.030],
            profit_target_pct=[0.010, 0.020, 0.030],
            maximize="Sharpe Ratio",
            method="sambo",
            max_tries=max_tries,
            return_heatmap=True,
            random_state=42,
        )
    except Exception as e:
        return {"error": f"optimize failed: {str(e)[:120]}"}

    s = stats._strategy
    return {
        "best_params": {
            "K":                 s.K,
            "entry_q_pct":       s.entry_q_pct,
            "lookback_bars":     s.lookback_bars,
            "horizon_bars":      s.horizon_bars,
            "hard_stop_pct":     s.hard_stop_pct,
            "profit_target_pct": s.profit_target_pct,
        },
        "n_feats":  n_feats,
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
    ap.add_argument("--pairs", nargs="+", default=None)
    ap.add_argument("--max-tries", type=int, default=50)
    ap.add_argument("--commission", type=float, default=0.0030)
    args = ap.parse_args()

    pairs = args.pairs if args.pairs else list(PAIR_FEATURES.keys())

    print("═" * 100)
    print(f"  ENSEMBLE EDGE SWEEP · multi-feature alignment")
    print(f"  pairs: {pairs}")
    print(f"  fee: {args.commission*100:.2f}% RT  ·  trials per pair: {args.max_tries}")
    print("═" * 100)

    results: List[Dict[str, Any]] = []
    for pair in pairs:
        feats = PAIR_FEATURES.get(pair)
        if not feats:
            print(f"\n▸ {pair}: no feature list, skipping")
            continue
        feat_str = ', '.join(f + ('+' if s > 0 else '-') for f, s in feats)
        print(f"\n▸ {pair}  ({len(feats)} features: {feat_str})")
        r = evaluate_pair(pair, feats, Path(args.data_dir),
                           max_tries=args.max_tries,
                           commission=args.commission)
        r["pair"] = pair
        results.append(r)
        if "error" in r:
            print(f"  ERROR: {r['error']}")
            continue
        bp = r["best_params"]
        print(f"  best: K≥{bp['K']}/{r['n_feats']}  q={bp['entry_q_pct']}  "
              f"lb={bp['lookback_bars']}  hold={bp['horizon_bars']}m  "
              f"sl={bp['hard_stop_pct']*100:.1f}%  tp={bp['profit_target_pct']*100:.1f}%")
        print(f"  Sharpe {r['sharpe']:+5.2f}  Ret {r['ret']:+6.1f}%  "
              f"vs BH {r['bh']:+6.1f}%  DD {r['dd']:5.1f}%  "
              f"WR {r['wr']:4.0f}%  #{r['trades']:3d}  PF {r['pf']:4.2f}")

    # ── promotion gate
    print("\n" + "═" * 100)
    print("  ENSEMBLE PROMOTION-GATE ANALYSIS")
    print("═" * 100)
    print("  Gate criteria (all must clear):")
    print(f"    - Net Sharpe ≥ 0.5 after {args.commission*100:.2f}% fee")
    print(f"    - # Trades ≥ 20 (lower bar than single-feature; ensemble fires less)")
    print(f"    - Max DD ≤ 15%")
    print(f"    - Beats buy-and-hold")
    print()

    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda r: -r["sharpe"])

    print(f"  {'pair':<10} {'K/N':>5} {'Sharpe':>8} {'Ret%':>8} {'BH%':>7} "
          f"{'DD%':>6} {'WR%':>5} {'#tr':>4}  pass")
    print("  " + "-" * 78)
    candidates: List[Dict[str, Any]] = []
    for r in valid:
        passes = (r["sharpe"] >= 0.5 and r["trades"] >= 20
                  and abs(r["dd"]) <= 15 and r["ret"] > r["bh"])
        marker = "✅" if passes else "🛑"
        if passes:
            candidates.append(r)
        print(f"  {r['pair']:<10} {r['best_params']['K']:>2}/{r['n_feats']:<2} "
              f"{r['sharpe']:>+7.2f}  {r['ret']:>+7.1f}%  "
              f"{r['bh']:>+6.1f}%  {abs(r['dd']):>5.1f}%  "
              f"{r['wr']:>4.0f}%  {r['trades']:>3d}  {marker}")

    print()
    if candidates:
        print(f"  🟢 {len(candidates)} pair(s) clear the ensemble gate.")
        print(f"     This DOES NOT confirm a profitable strategy. Next step:")
        print(f"     - Walk-forward on rolling windows (catch regime mismatch)")
        print(f"     - Monte Carlo permutation (catch noise overfit)")
        print(f"     - Re-test on D6 full 5-day data when binding fires")
        print(f"     Do NOT promote to main. ADR-003 in force until D7.")
    else:
        print(f"  🛑 NO pair passes ensemble gate.")
        print(f"     Multi-feature alignment also doesn't beat fees on this data.")
        print(f"     Confirms Phase B must use a different signal class (maker")
        print(f"     execution discount, on-chain B1 fallback, or longer horizons).")
    print("═" * 100)


if __name__ == "__main__":
    main()
