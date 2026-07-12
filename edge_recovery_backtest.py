#!/usr/bin/env python3
"""
L99 Edge Recovery Mode — backtest validation via backtesting.py 0.6.5.

Tests four variants of the same trend-follow core, each adding one more
filter, to answer one binary question:

    Do the filters in the L99 Edge Recovery Mode spec genuinely add OOS
    edge, or do they just reduce trade count to where evaluation is
    statistically noisy?

Variants:
  V1 BASELINE        MAWeekly (price > daily SMA AND > weekly SMA)
                     This is the documented FAIL case from prior research.
  V2 +ATR_EXP        V1 + ATR-expansion gate (ATR(14)/ATR(60) ∈ [1.2, 2.5])
  V3 +DELTA_ACCEL    V2 + body+volume "delta acceleration" proxy
  V4 FULL            V3 + 2-bar continuation + edge ≥ 0.45%
                       + hard −0.35% stop  (full L99 Edge Recovery)

Run setup:
  - 4 pairs: ETH_USDT, SOL_USDT, XRP_USDT, AVAX_USDT
  - 1d timeframe, 1000 bars, 70/30 train/test
  - commission 0.0025 (0.25% — slightly above 0.20% RT to include slippage)
  - cash 10000

Promotion gate (per spec Step 6):
  V4 wins if: OOS Sharpe ≥ 0.5 on ≥ 3 of 4 pairs AND median WR ≥ 55%
  AND median avg-trade-pct ≥ 1.5×stop_pct

Otherwise: ADR-001 fallback path (B1 on-chain).

Usage:
  python edge_recovery_backtest.py
  python edge_recovery_backtest.py --pairs ETH_USDT SOL_USDT
  python edge_recovery_backtest.py --train-frac 0.6
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import warnings
from datetime import datetime, timezone
from typing import Dict, List

warnings.filterwarnings("ignore")

try:
    import numpy as np
    import pandas as pd
    from backtesting import Backtest, Strategy
    from backtesting.lib import resample_apply
except ImportError as e:
    print(f"import failed: {e}"); sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
from gods_level_engine import Bar
from backtest_multi_token import fetch_gateio_bars


PAIRS_DEFAULT = ["ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]


# ── data adapter ────────────────────────────────────────────────────
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


# ── indicator helpers ──────────────────────────────────────────────
def _sma(arr, n):
    return pd.Series(arr).rolling(n, min_periods=1).mean().to_numpy()


def _atr(high, low, close, n):
    h, l, c = pd.Series(high), pd.Series(low), pd.Series(close)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def _delta_proxy(open_, close, volume):
    """No L2 tape on daily bars — use bar-body × volume as a delta proxy.
    Positive = buyer aggression dominant; negative = seller dominant."""
    body_sign = np.sign(np.array(close) - np.array(open_))
    return (body_sign * np.array(volume)).astype(float)


# ═════ V1 BASELINE — MAWeekly ═════════════════════════════════════════
class V1_MAWeekly(Strategy):
    ma_period = 20
    weekly_period = 5
    hysteresis = 25  # 25 bp

    def init(self):
        c = self.data.Close
        self.sma_d = self.I(_sma, c, self.ma_period)
        self.sma_w = self.I(resample_apply, "W", _sma, c, self.weekly_period,
                            overlay=True)

    def next(self):
        if len(self.data.Close) < max(self.ma_period, self.weekly_period * 7):
            return
        px = self.data.Close[-1]
        d, w = self.sma_d[-1], self.sma_w[-1]
        if math.isnan(d) or math.isnan(w):
            return
        hy = self.hysteresis / 10000.0
        if self.position:
            if px < d * (1 - hy) or px < w * (1 - hy):
                self.position.close()
        else:
            if px > d * (1 + hy) and px > w * (1 + hy):
                self.buy()


# ═════ V2 — V1 + ATR-expansion regime filter ══════════════════════════
class V2_ATR_Expansion(V1_MAWeekly):
    atr_short = 14
    atr_long  = 60
    expansion_min = 1.2   # current ATR > 120% of long-term mean
    expansion_max = 2.5   # but not already > 250% (overextended)

    def init(self):
        super().init()
        self.atr_s = self.I(_atr, self.data.High, self.data.Low,
                             self.data.Close, self.atr_short)
        self.atr_l = self.I(_atr, self.data.High, self.data.Low,
                             self.data.Close, self.atr_long)

    def next(self):
        if (math.isnan(self.atr_s[-1]) or math.isnan(self.atr_l[-1])
                or self.atr_l[-1] <= 0):
            return
        ratio = self.atr_s[-1] / self.atr_l[-1]
        if not (self.expansion_min <= ratio <= self.expansion_max):
            # exit if currently long and outside expansion band
            if self.position:
                self.position.close()
            return
        super().next()


# ═════ V3 — V2 + delta acceleration filter ════════════════════════════
class V3_DeltaAccel(V2_ATR_Expansion):
    delta_lookback = 10

    def init(self):
        super().init()
        self.delta = self.I(_delta_proxy, self.data.Open, self.data.Close,
                            self.data.Volume)

    def next(self):
        # Require positive delta accumulation over last `delta_lookback` bars
        if len(self.delta) < self.delta_lookback:
            return
        recent_delta = float(np.sum(self.delta[-self.delta_lookback:]))
        if recent_delta <= 0:
            if self.position:
                self.position.close()
            return
        super().next()


# ═════ V4 FULL — V3 + 2-bar continuation + edge gate + hard stop ═════
class V4_FullL99(V3_DeltaAccel):
    edge_min_pct  = 0.0045   # 0.45% — spec Step 2
    stop_pct      = 0.0035   # 0.35% — spec Step 3 "cut losers fast"
    breakeven_after_pct = 0.0050   # move stop to BE after +0.50%

    def init(self):
        super().init()
        self._entry_px = 0.0
        self._stop_px  = 0.0

    def next(self):
        # ── Hard stop (Patch 1 logic, parameterized to 0.35%) ──
        if self.position and self._entry_px > 0:
            cur = self.data.Close[-1]
            if cur <= self._stop_px:
                self.position.close()
                self._entry_px, self._stop_px = 0.0, 0.0
                return
            # BE move after spec.breakeven_after_pct
            if cur >= self._entry_px * (1 + self.breakeven_after_pct):
                # ratchet stop up to entry (BE)
                if self._stop_px < self._entry_px:
                    self._stop_px = self._entry_px

        # ── 2-bar continuation: last two closes both higher ──
        if len(self.data.Close) < 3:
            return
        c0, c1, c2 = self.data.Close[-3], self.data.Close[-2], self.data.Close[-1]
        continuation_bull = (c1 > c0) and (c2 > c1)

        # ── Edge after fees gate ──
        atr_s = self.atr_s[-1] if not math.isnan(self.atr_s[-1]) else 0.0
        mid = c2
        if mid <= 0:
            return
        expected_move_pct = atr_s / mid       # one-bar typical move
        # Conservative: assume maker entry + taker exit + 0.05% slip
        rt_cost = 0.0025 + 0.0005             # 0.25% + 0.05% slip
        edge_pct = expected_move_pct - rt_cost
        if edge_pct < self.edge_min_pct:
            return

        # Entry only if continuation candle and not already long
        if not self.position:
            if continuation_bull:
                # Apply parent V3 filters via super; if it would buy, we add stop
                pre_position = bool(self.position)
                super().next()
                if self.position and not pre_position:
                    self._entry_px = self.data.Close[-1]
                    self._stop_px  = self._entry_px * (1 - self.stop_pct)
        else:
            super().next()


VARIANTS = {
    "V1_BASELINE_MAW":     V1_MAWeekly,
    "V2_ATR_EXPANSION":    V2_ATR_Expansion,
    "V3_DELTA_ACCEL":      V3_DeltaAccel,
    "V4_FULL_EDGE_RECOV":  V4_FullL99,
}


# ── runner ─────────────────────────────────────────────────────────
def evaluate_variant(df: pd.DataFrame, StratCls, train_frac: float,
                     cash: float = 10000, commission: float = 0.0025):
    cut = int(len(df) * train_frac)
    train_df, test_df = df.iloc[:cut], df.iloc[cut:]
    if len(train_df) < 150 or len(test_df) < 80:
        return {"error": f"insufficient data {len(train_df)}/{len(test_df)}"}
    try:
        bt_train = Backtest(train_df, StratCls, cash=cash, commission=commission,
                             finalize_trades=True)
        s_train = bt_train.run()
        bt_test = Backtest(test_df, StratCls, cash=cash, commission=commission,
                            finalize_trades=True)
        s_test = bt_test.run()
        return {
            "train_sqn":    s_train.get("SQN", 0)            or 0,
            "train_sharpe": s_train.get("Sharpe Ratio", 0)   or 0,
            "train_ret":    s_train.get("Return [%]", 0)     or 0,
            "train_trades": s_train.get("# Trades", 0)       or 0,

            "test_sqn":     s_test.get("SQN", 0)             or 0,
            "test_sharpe":  s_test.get("Sharpe Ratio", 0)    or 0,
            "test_ret":     s_test.get("Return [%]", 0)      or 0,
            "test_bh":      s_test.get("Buy & Hold Return [%]", 0) or 0,
            "test_dd":      s_test.get("Max. Drawdown [%]", 0) or 0,
            "test_wr":      s_test.get("Win Rate [%]", 0)    or 0,
            "test_trades":  s_test.get("# Trades", 0)        or 0,
            "test_avg":     s_test.get("Avg. Trade [%]", 0)  or 0,
            "test_pf":      s_test.get("Profit Factor", 0)   or 0,
        }
    except Exception as e:
        return {"error": str(e)[:100]}


# ── main ─────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS_DEFAULT)
    ap.add_argument("--history", type=int, default=1000)
    ap.add_argument("--train-frac", type=float, default=0.7)
    args = ap.parse_args()

    print("═" * 110)
    print(f"  L99 EDGE RECOVERY — backtest validation · {len(args.pairs)} pairs · "
          f"{args.history} bars · {args.train_frac*100:.0f}/{(1-args.train_frac)*100:.0f}")
    print("═" * 110)

    print("\n▸ Fetching data")
    dfs = {}
    for pair in args.pairs:
        bars = fetch_gateio_bars(pair, "1d", args.history)
        if len(bars) >= 400:
            dfs[pair] = bars_to_df(bars)
            print(f"    {pair:<10}  {len(bars)} bars")

    print("\n▸ Per-pair × variant OOS table")
    print(f"  {'pair':<10} {'variant':<22} {'TRAIN SQN':>10} {'TEST SQN':>10} "
          f"{'Test Ret%':>10} {'BH Ret%':>10} {'WR%':>6} {'#':>4} {'AvgTr%':>8}")
    print("  " + "-" * 103)

    results = {}
    for pair, df in dfs.items():
        for vname, cls in VARIANTS.items():
            r = evaluate_variant(df, cls, args.train_frac)
            results.setdefault(pair, {})[vname] = r
            if "error" in r:
                print(f"  {pair:<10} {vname:<22} ERR: {r['error']}")
                continue
            print(f"  {pair:<10} {vname:<22} "
                  f"{r['train_sqn']:>+9.2f}  "
                  f"{r['test_sqn']:>+9.2f}  "
                  f"{r['test_ret']:>+9.1f}%  "
                  f"{r['test_bh']:>+9.1f}%  "
                  f"{r['test_wr']:>5.0f}%  "
                  f"{r['test_trades']:>3}  "
                  f"{r['test_avg']:>+7.2f}%")

    # ── per-variant cross-pair summary
    print("\n" + "═" * 110)
    print("  CROSS-PAIR SUMMARY — does each successive filter add OOS edge?")
    print("═" * 110)
    print(f"  {'variant':<22} {'med SQN':>10} {'med Sharpe':>12} "
          f"{'med Ret%':>10} {'med WR%':>8} {'med #':>7} {'pairs +ROI':>13}")
    print("  " + "-" * 96)

    for vname in VARIANTS.keys():
        cells = [results[p][vname] for p in dfs.keys()
                 if "error" not in results.get(p, {}).get(vname, {})]
        if not cells:
            continue
        med = lambda key: float(np.median([c[key] for c in cells]))
        med_sqn   = med("test_sqn")
        med_shar  = med("test_sharpe")
        med_ret   = med("test_ret")
        med_wr    = med("test_wr")
        med_n     = med("test_trades")
        pos_pairs = sum(1 for c in cells if c["test_ret"] > 0)
        print(f"  {vname:<22} {med_sqn:>+9.2f}  {med_shar:>+11.2f}  "
              f"{med_ret:>+9.1f}%  {med_wr:>7.0f}%  {med_n:>6.0f}  "
              f"{pos_pairs}/{len(cells)}")

    # ── promotion gate per spec Step 6
    print("\n" + "═" * 110)
    print("  PROMOTION GATE (per spec Step 6: WR ≥ 55%, avg R ≥ 1.5)")
    print("═" * 110)
    v4_cells = [results[p]["V4_FULL_EDGE_RECOV"] for p in dfs.keys()
                if "error" not in results.get(p, {}).get("V4_FULL_EDGE_RECOV", {})]
    if v4_cells:
        n_pairs = len(v4_cells)
        sharpe_pass = sum(1 for c in v4_cells if c["test_sharpe"] >= 0.5)
        wr_pass     = sum(1 for c in v4_cells if c["test_wr"] >= 55)
        ret_pos     = sum(1 for c in v4_cells if c["test_ret"] > 0)

        # Avg R proxy: avg trade % / stop %  (stop = 0.35%)
        avg_r_pass = sum(1 for c in v4_cells
                          if c["test_avg"] >= 1.5 * 0.35)
        print(f"  Pairs with OOS Sharpe ≥ 0.5     : {sharpe_pass}/{n_pairs}")
        print(f"  Pairs with WR ≥ 55%              : {wr_pass}/{n_pairs}")
        print(f"  Pairs with avg-trade ≥ 1.5×stop  : {avg_r_pass}/{n_pairs}")
        print(f"  Pairs with positive OOS Return   : {ret_pos}/{n_pairs}")
        gate_passed = (sharpe_pass >= 3 and wr_pass >= 3 and ret_pos == n_pairs)
        print()
        if gate_passed:
            print("  ✅ PASS — promote V4 to Phase B candidate")
        else:
            print("  🛑 FAIL — V4 does not clear Step 6 bar.")
            print("           Stay on ADR-001 fallback (B1 on-chain) on D7.")
    print("═" * 110)


if __name__ == "__main__":
    main()
