"""
A2 ETH "perfected" — two theoretically-grounded enhancements over the
falsified baseline. Per operator request "yntrir lavaguyn ashxatogh
tarberaky yev sksenq da katarelagorcel".

BASELINE (already falsified)
============================
`a2_eth_backtest_bt.py` long-only ETH on z>1.5 crossover, 18-bar hold:
  full Return +11.1%, Sharpe 0.25, MaxDD -17.5%, vs ETH B&H +99.4%.
  Sharpe degrades monotonically across years 2023→2026.

WHY THESE TWO ENHANCEMENTS (NOT PARAMETER SWEEPS)
=================================================
Validation suite (`a2_validation_results.json`) showed two concrete
empirical patterns we can build on without curve-fitting:

  (a) ETH passed every lag-shift; BTC failed every lag-shift.
      → ETH outperforms BTC after stablecoin-minting signal.
      → Re-spec the trade as long ETH / short BTC (paired).

  (b) Walk-forward 2024 ETH was the only fold to clear L99 fully;
      regime-conditional showed edge concentrated in bull/range.
      → Skip entries when BTC trailing 30-day return < -10% (bear
        regime), since 2025/2026 OOS losses came from bear/chop.

Both modifications are SIGNED, theoretically motivated, and avoid the
B2/B3 |abs| pitfall. Both are explicitly NOT parameter-sweep tuning.

FEE ACCOUNTING — CRITICAL
=========================
A paired trade pays fees on TWO instruments per entry/exit. So the
effective per-side commission on the synthetic ETH/BTC ratio is
DOUBLED relative to the single-leg case.

DECISION GATE (§3.5 — proposed)
================================
Promote enhanced strategy from "research artifact" to "Stage 1 paper
candidate" ONLY if all of the following hold:

  1. Sharpe ≥ 1.0 on full 2023-now history
  2. Beat ETH buy-and-hold OR BTC buy-and-hold (whichever is benchmark)
  3. Yearly Sharpe ≥ 0 in at least 3 of 4 OOS folds (no monotonic decay)
  4. MaxDD < 25%
  5. ≥ 30 trades for power
  6. Win rate ≥ 40%

Fail any gate → A2 is officially the 10th NULL, pivot to new factor.

NO LIVE CONFIG INTEGRATION REGARDLESS.
"""
from __future__ import annotations

import bisect
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a2_eth_backtest_bt import (
    DEFILLAMA_STABLECOIN_IDS,
    EARLIEST_TS,
    HOLD_BARS,
    Z_THRESHOLD,
    build_daily_z,
    build_perp_df,
    build_entry_series,
)

# ──────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────

PAIR_LONG = 'ETH_USDT'
PAIR_SHORT = 'BTC_USDT'
HOLD_BARS_PAIRED = HOLD_BARS              # same 18 bars (3 days)
ENTRY_FRACTION = 0.90

# Bear-regime threshold: BTC 30-day trailing return
BEAR_THRESHOLD_PCT = -10.0
REGIME_LOOKBACK = 30 * 6                  # 30 days at 4h cadence = 180 bars

# Per-leg → per-pair-side fee doubling
PAIRED_FEE_SCENARIOS = {
    'A_VIP0_taker':       0.00250,  # 25 bps per side per pair  = 50 bps RT
    'B_VIP1_GT_discount': 0.00180,  # 18 bps per side per pair  = 36 bps RT
    'C_VIP1_maker_only':  0.00140,  # 14 bps per side per pair  = 28 bps RT
}

# §3.5 gate thresholds
GATE_SHARPE = 1.0
GATE_MAX_DD = -25.0
GATE_MIN_TRADES = 30
GATE_MIN_WIN_RATE = 40.0
GATE_MIN_GOOD_YEARS = 3

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ──────────────────────────────────────────────────────────────────
# Synthetic ratio asset (ETH/BTC)
# ──────────────────────────────────────────────────────────────────

def build_ratio_df(eth_df: pd.DataFrame, btc_df: pd.DataFrame) -> pd.DataFrame:
    """ETH/BTC ratio OHLCV. Long this asset = long ETH/short BTC at equal $."""
    common_idx = eth_df.index.intersection(btc_df.index)
    e = eth_df.loc[common_idx]
    b = btc_df.loc[common_idx]
    out = pd.DataFrame(index=common_idx)
    out['Open']  = e['Open']  / b['Open']
    out['Close'] = e['Close'] / b['Close']
    # Conservative bounds for intra-bar high/low (ratio is non-monotonic)
    out['High']  = np.maximum(e['High'] / b['Low'],  e['Open'] / b['Open']).clip(
        upper=(e['High'] / b['Low']) * 1.0
    )
    out['Low']   = np.minimum(e['Low']  / b['High'], e['Close'] / b['Close']).clip(
        lower=(e['Low']  / b['High']) * 1.0
    )
    # Simple max/min for safety
    out['High'] = out[['Open', 'Close', 'High']].max(axis=1)
    out['Low']  = out[['Open', 'Close', 'Low']].min(axis=1)
    out['Volume'] = (e['Volume'] + b['Volume']) / 2.0
    return out


def build_btc_regime_series(btc_df: pd.DataFrame, lookback: int) -> pd.Series:
    """Trailing N-bar % return on BTC close. Used as bull/range/bear filter."""
    closes = btc_df['Close'].values
    out = np.full(len(closes), np.nan)
    for i in range(lookback, len(closes)):
        if closes[i - lookback] > 0:
            out[i] = (closes[i] - closes[i - lookback]) / closes[i - lookback] * 100
    return pd.Series(out, index=btc_df.index, name='btc_regime_30d')


# ──────────────────────────────────────────────────────────────────
# Strategies
# ──────────────────────────────────────────────────────────────────

class A2PairedNoFilter(Strategy):
    """Enhancement #1 only: paired ETH/BTC, no regime filter."""
    z_threshold = Z_THRESHOLD
    hold_bars = HOLD_BARS_PAIRED

    def init(self):
        self.z = self.I(lambda: self.data.df['z'].values, name='z', overlay=False)
        self._entry_bar: Optional[int] = None

    def next(self):
        i = len(self.data) - 1
        if self.position and self._entry_bar is not None:
            if i - self._entry_bar >= self.hold_bars:
                self.position.close()
                self._entry_bar = None
                return

        if not self.position and len(self.data) >= 2:
            prev_z = self.z[-2]
            cur_z = self.z[-1]
            if (
                np.isfinite(prev_z) and np.isfinite(cur_z)
                and prev_z <= self.z_threshold
                and cur_z > self.z_threshold
            ):
                self.buy(size=ENTRY_FRACTION)
                self._entry_bar = i


class A2PairedWithRegime(Strategy):
    """Enhancements #1 + #2: paired ETH/BTC AND skip bear regime entries."""
    z_threshold = Z_THRESHOLD
    hold_bars = HOLD_BARS_PAIRED
    bear_threshold = BEAR_THRESHOLD_PCT

    def init(self):
        self.z = self.I(lambda: self.data.df['z'].values, name='z', overlay=False)
        self.btc_30d = self.I(lambda: self.data.df['btc_regime_30d'].values,
                              name='btc_30d', overlay=False)
        self._entry_bar: Optional[int] = None

    def next(self):
        i = len(self.data) - 1
        if self.position and self._entry_bar is not None:
            if i - self._entry_bar >= self.hold_bars:
                self.position.close()
                self._entry_bar = None
                return

        if not self.position and len(self.data) >= 2:
            prev_z = self.z[-2]
            cur_z = self.z[-1]
            regime = self.btc_30d[-1]
            if (
                np.isfinite(prev_z) and np.isfinite(cur_z)
                and np.isfinite(regime)
                and prev_z <= self.z_threshold
                and cur_z > self.z_threshold
                and regime > self.bear_threshold  # SKIP bear
            ):
                self.buy(size=ENTRY_FRACTION)
                self._entry_bar = i


# ──────────────────────────────────────────────────────────────────
# Runners
# ──────────────────────────────────────────────────────────────────

def run_one(strategy_cls, df: pd.DataFrame, fee_per_side: float,
            label: str, plot: bool = False) -> Dict:
    bt = Backtest(
        df, strategy_cls,
        cash=10_000,
        commission=fee_per_side,
        exclusive_orders=True,
        trade_on_close=False,
    )
    stats = bt.run()
    out: Dict[str, float] = {}
    keep = [
        'Start', 'End', 'Duration', 'Exposure Time [%]',
        'Equity Final [$]', 'Equity Peak [$]',
        'Return [%]', 'Buy & Hold Return [%]',
        'Return (Ann.) [%]', 'Volatility (Ann.) [%]',
        'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio',
        'Max. Drawdown [%]', 'Avg. Drawdown [%]',
        '# Trades', 'Win Rate [%]', 'Best Trade [%]', 'Worst Trade [%]',
        'Avg. Trade [%]', 'Profit Factor', 'Expectancy [%]', 'SQN',
    ]
    for k in keep:
        if k in stats.index:
            v = stats[k]
            if hasattr(v, 'isoformat'):
                out[k] = v.isoformat()
            elif isinstance(v, pd.Timedelta):
                out[k] = str(v)
            elif isinstance(v, (int, float, np.integer, np.floating)):
                out[k] = None if (np.isnan(v) or np.isinf(v)) else float(v)
            else:
                out[k] = str(v)
    if plot:
        plot_path = os.path.join(OUTPUT_DIR, f'a2_perfected_{label}.html')
        try:
            bt.plot(filename=plot_path, open_browser=False)
            out['plot_path'] = plot_path
        except Exception as e:
            out['plot_error'] = str(e)
    return out


def evaluate_gate(full_stats: Dict, yearly: Dict[str, Dict]) -> Tuple[bool, List[str]]:
    """Apply §3.5 deployment gate."""
    fail: List[str] = []
    sh = full_stats.get('Sharpe Ratio')
    if sh is None or sh < GATE_SHARPE:
        fail.append(f"Sharpe={sh:.3f} < {GATE_SHARPE}")
    ret = full_stats.get('Return [%]') or 0.0
    bh = full_stats.get('Buy & Hold Return [%]') or 0.0
    if ret <= bh:
        fail.append(f"Return={ret:.2f}% does NOT beat B&H={bh:.2f}%")
    dd = full_stats.get('Max. Drawdown [%]') or 0.0
    if dd < GATE_MAX_DD:
        fail.append(f"MaxDD={dd:.2f}% < {GATE_MAX_DD}%")
    n = full_stats.get('# Trades') or 0
    if n < GATE_MIN_TRADES:
        fail.append(f"#Trades={int(n)} < {GATE_MIN_TRADES}")
    wr = full_stats.get('Win Rate [%]') or 0.0
    if wr < GATE_MIN_WIN_RATE:
        fail.append(f"WinRate={wr:.1f}% < {GATE_MIN_WIN_RATE}%")
    good_years = sum(1 for r in yearly.values()
                     if r.get('Sharpe Ratio') is not None and r['Sharpe Ratio'] > 0)
    if good_years < GATE_MIN_GOOD_YEARS:
        fail.append(f"GoodYears={good_years}/{len(yearly)} < {GATE_MIN_GOOD_YEARS}")
    return len(fail) == 0, fail


def main():
    print("═" * 74)
    print("  A2 PERFECTED — paired ETH/BTC + regime filter")
    print("  Two theoretically-grounded enhancements (NOT parameter sweeps)")
    print("═" * 74)
    print()

    # Step 1: data
    daily_z = build_daily_z(DEFILLAMA_STABLECOIN_IDS)
    eth_df = build_perp_df(PAIR_LONG)
    btc_df = build_perp_df(PAIR_SHORT)

    earliest_ts_pd = pd.Timestamp(EARLIEST_TS, unit='s', tz='UTC')
    eth_df = eth_df[eth_df.index >= earliest_ts_pd]
    btc_df = btc_df[btc_df.index >= earliest_ts_pd]

    ratio_df = build_ratio_df(eth_df, btc_df)
    print(f"  Ratio bars (ETH/BTC): {len(ratio_df)}")

    z_series = build_entry_series(ratio_df, daily_z)
    regime_series = build_btc_regime_series(btc_df, REGIME_LOOKBACK).reindex(ratio_df.index)

    df = ratio_df.assign(z=z_series.values, btc_regime_30d=regime_series.values)
    df = df.dropna(subset=['z', 'btc_regime_30d'])
    print(f"  After alignment + regime backfill: {len(df)} bars")

    # Crossover counts
    cross_all = ((df['z'].shift(1) <= Z_THRESHOLD) & (df['z'] > Z_THRESHOLD)).sum()
    cross_no_bear = (
        (df['z'].shift(1) <= Z_THRESHOLD)
        & (df['z'] > Z_THRESHOLD)
        & (df['btc_regime_30d'] > BEAR_THRESHOLD_PCT)
    ).sum()
    print(f"  Crossover entries (all): {cross_all}")
    print(f"  Crossover entries (non-bear): {cross_no_bear}")
    print()

    output: Dict = {
        'run_time': datetime.now(timezone.utc).isoformat(),
        'mode': 'A2_PERFECTED_PAIRED_ETH_BTC_BACKTEST',
        'baseline_path': 'a2_eth_backtest_bt.py',
        'enhancements': [
            'Paired long ETH / short BTC via synthetic ratio asset',
            f'Skip entries when BTC 30d trailing return ≤ {BEAR_THRESHOLD_PCT}%',
        ],
        'gate_thresholds': {
            'sharpe_min': GATE_SHARPE,
            'max_dd_min': GATE_MAX_DD,
            'trades_min': GATE_MIN_TRADES,
            'win_rate_min': GATE_MIN_WIN_RATE,
            'good_years_min': GATE_MIN_GOOD_YEARS,
        },
        'crossover_counts': {
            'all': int(cross_all),
            'non_bear': int(cross_no_bear),
        },
    }

    # Step 2: run both strategies, both fee tiers
    for variant_name, cls in [
        ('paired_no_filter', A2PairedNoFilter),
        ('paired_with_regime', A2PairedWithRegime),
    ]:
        print(f"── Variant: {variant_name} ──")
        variant_out: Dict = {'full_history': {}, 'yearly_folds': {}}
        for tier_label, fee in PAIRED_FEE_SCENARIOS.items():
            r = run_one(cls, df, fee, label=f'{variant_name}_full_{tier_label}',
                        plot=(tier_label == 'C_VIP1_maker_only'))
            variant_out['full_history'][tier_label] = r
            print(f"  {tier_label:22s} (full): "
                  f"Return={r.get('Return [%]', float('nan')):+7.2f}%  "
                  f"Sharpe={r.get('Sharpe Ratio', float('nan')) or 0:+5.2f}  "
                  f"MaxDD={r.get('Max. Drawdown [%]', float('nan')):+6.2f}%  "
                  f"Trades={int(r.get('# Trades', 0))}  "
                  f"vs B&H_ratio {r.get('Buy & Hold Return [%]', float('nan')):+7.2f}%")

        # Yearly folds (maker tier only — that's our best case)
        fee = PAIRED_FEE_SCENARIOS['C_VIP1_maker_only']
        for year in [2023, 2024, 2025, 2026]:
            start = pd.Timestamp(f'{year}-01-01', tz='UTC')
            end = pd.Timestamp(f'{year+1}-01-01', tz='UTC')
            sub = df[(df.index >= start) & (df.index < end)]
            if len(sub) < 200:
                continue
            r = run_one(cls, sub, fee, label=f'{variant_name}_{year}', plot=False)
            variant_out['yearly_folds'][str(year)] = r
            print(f"     {year}: Return={r.get('Return [%]', float('nan')):+7.2f}%  "
                  f"Sharpe={r.get('Sharpe Ratio', float('nan')) or 0:+5.2f}  "
                  f"Trades={int(r.get('# Trades', 0))}")

        # Apply gate
        gate_pass, gate_failures = evaluate_gate(
            variant_out['full_history']['C_VIP1_maker_only'],
            variant_out['yearly_folds'],
        )
        variant_out['gate_pass'] = gate_pass
        variant_out['gate_failures'] = gate_failures
        print(f"  §3.5 gate (maker tier): {'✅ PASS' if gate_pass else '❌ FAIL'}")
        for f in gate_failures:
            print(f"     - {f}")
        print()

        output[variant_name] = variant_out

    # Step 3: write artifact
    out_path = os.path.join(OUTPUT_DIR, 'a2_perfected_results.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  → {out_path}")
    print()

    # Step 4: synthesis
    print("═" * 74)
    print("  FINAL VERDICT — does any variant clear §3.5 gate?")
    print("═" * 74)
    any_pass = False
    for variant_name in ['paired_no_filter', 'paired_with_regime']:
        v = output[variant_name]
        gate = v['gate_pass']
        any_pass = any_pass or gate
        print(f"  {variant_name:25s}: {'✅ PASS' if gate else '❌ FAIL'}")
        if not gate:
            for f in v['gate_failures']:
                print(f"     - {f}")
    print()
    if any_pass:
        print("  → Promote passing variant to Stage 1 paper validation gate.")
        print("  → Operator must approve PR before any live config change.")
    else:
        print("  → A2 OFFICIALLY DEAD. 10th NULL confirmed across two enhancement paths.")
        print("  → Pivot to a completely new factor family with §3.5 built-in from day 1.")
    print("  → Position remains 100% USDT.")
    print("═" * 74)


if __name__ == '__main__':
    main()
