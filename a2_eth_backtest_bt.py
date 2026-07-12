"""
A2 — Stablecoin Supply Impulse on ETH/USDT — full backtest via backtesting.py.

WHY THIS SCRIPT EXISTS
======================
Per operator instruction "backtesting ara yev yntri amboxch patmutyan testing
amena ashxatogh tarberaly" — across 9 NULL verdicts + 1 candidate (A2):

  * D6, C2_4H, C1, NATIVE D2, B1, B2, B3 → all NULL via L99 battery
  * A2 (Stablecoin Supply Impulse, ETH 3d) → only variant that passed any
    L99 combinations in the apparent-pass scan (PR #26)

So "amena ashxatogh tarberaly" = unambiguously **A2 ETH 3d**.
This script wires that signal into backtesting.py end-to-end.

CRITICAL HONESTY DISCLAIMER
===========================
The companion validation suite (`a2_validation_suite.py`,
`a2_validation_results.json`) ALREADY showed:

  * Walk-forward: 2/8 yearly folds pass full L99 battery
    - 2024 BTC+ETH passed, 2023/2025/2026 fail (PF<1, Q5-Q1<0, sign-flip)
  * Lag-shift ±1 day: BTC fails Q5-Q1 at every lag; ETH passes at every lag
  * Regime-conditional: 0/6 single-regime sub-tests survive full battery

→ A2 is a CANDIDATE (per L99_ALPHA_VALIDATION §1.6) but FAILED the §3
robustness gates. It is NOT deployable.

This script therefore runs the backtest as a **research artifact only**.
The "best variant" exists numerically; it will be visualised honestly,
including its OOS collapse. NOTHING is wired into a live config.
Position remains 100% USDT.

CONFIG INTEGRATION
==================
Per discipline framework + memory rule `feedback_drift_pattern.md`:

    NO live config integration is performed.
    NO l99/config.py override is committed.
    NO TRADING_MODE flag is flipped.

If/when A2 graduates §3 Stage 1 (60-day paper, 50+ trades), parameters
documented here can be promoted via a separate operator-approved PR.

WHAT THIS SCRIPT DOES
=====================
  1. Re-fetches DefiLlama USDT+USDC daily supply (cache-friendly)
  2. Re-fetches Gate.io ETH_USDT 4h perp candles
  3. Computes 30-day rolling z-score of 7-day supply % change
  4. Builds entry signal: when daily z > 1.5 at bar timestamp
  5. Implements `A2StablecoinImpulse(Strategy)`:
       - Enter long on signal fire (one position at a time)
       - Hold for 18 bars (3 days at 4h)
       - Exit at close after 18 bars
       - Uses backtesting.py's commission for realistic fees
  6. Runs full backtest 2023-01 → now
  7. Runs OOS yearly folds (2023, 2024, 2025, 2026)
  8. Saves bokeh equity-curve HTML + stats JSON
  9. Prints honest synthesis vs validation suite verdict
"""
from __future__ import annotations

import bisect
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a2_stablecoin_runner import (
    DEFILLAMA_STABLECOIN_IDS,
    EARLIEST_TS,
    fetch_perp_4h_paginated,
    fetch_stablecoin_history,
    n_day_change,
    rolling_zscore,
    GROWTH_LOOKBACK_7D,
    Z_LOOKBACK,
    Z_THRESHOLD,
)

# ──────────────────────────────────────────────────────────────────
# Strategy parameters
# ──────────────────────────────────────────────────────────────────

PAIR = 'ETH_USDT'                  # historically best per validation suite
HOLD_BARS = 18                     # 3 days at 4h cadence (HORIZONS["3d"])
ENTRY_FRACTION = 0.95              # of equity per trade (one at a time)

# Three fee tiers from the spec
FEE_SCENARIOS = {
    'A_VIP0_taker':       0.00125,  # 12.5 bps per side  (25 bps RT)
    'B_VIP1_GT_discount': 0.00090,  # 9 bps per side     (18 bps RT)
    'C_VIP1_maker_only':  0.00070,  # 7 bps per side     (14 bps RT)
}

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ──────────────────────────────────────────────────────────────────
# Data preparation
# ──────────────────────────────────────────────────────────────────

def build_daily_z(stablecoin_ids: Dict[str, int]) -> Dict[int, float]:
    """Reuse a2_stablecoin_runner methodology: combined USDT+USDC supply."""
    print("  fetching DefiLlama supply ...")
    histories = {sym: fetch_stablecoin_history(cid) for sym, cid in stablecoin_ids.items()}

    # Align by date — combined supply per day
    by_day: Dict[int, float] = {}
    for sym, hist in histories.items():
        for ts, v in hist:
            day_ts = (ts // 86400) * 86400
            by_day[day_ts] = by_day.get(day_ts, 0.0) + v

    if not by_day:
        raise RuntimeError("no daily supply history fetched from DefiLlama")

    sorted_days = sorted(by_day.keys())
    series = [by_day[d] for d in sorted_days]
    growth = n_day_change(series, GROWTH_LOOKBACK_7D)
    growth_clean = [g if g is not None else 0.0 for g in growth]
    z = rolling_zscore(growth_clean, Z_LOOKBACK)

    out: Dict[int, float] = {}
    for d, zv in zip(sorted_days, z):
        if zv is not None and d >= EARLIEST_TS:
            out[d] = zv
    print(f"  daily z-scores: {len(out)}")
    return out


def build_perp_df(pair: str) -> pd.DataFrame:
    print(f"  fetching {pair} 4h perp candles ...")
    bars = fetch_perp_4h_paginated(pair)
    print(f"  {pair}: {len(bars)} bars")
    if not bars:
        raise RuntimeError(f"no perp data for {pair}")
    df = pd.DataFrame(bars).rename(columns={
        'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume',
    })
    df['Datetime'] = pd.to_datetime(df['ts'], unit='s', utc=True)
    df = df.set_index('Datetime').drop(columns=['ts'])
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]


def build_entry_series(df: pd.DataFrame, daily_z: Dict[int, float]) -> pd.Series:
    """For each bar, latest available daily z (lookahead-clean: bisect_right - 1)."""
    sorted_ts = sorted(daily_z.keys())
    z_per_bar: List[float] = []
    for dt in df.index:
        bar_ts = int(dt.timestamp())
        idx = bisect.bisect_right(sorted_ts, bar_ts) - 1
        z_per_bar.append(daily_z[sorted_ts[idx]] if idx >= 0 else float('nan'))
    return pd.Series(z_per_bar, index=df.index, name='z')


# ──────────────────────────────────────────────────────────────────
# Strategy
# ──────────────────────────────────────────────────────────────────

class A2StablecoinImpulse(Strategy):
    """
    Long-only impulse strategy.

    Entry  : when bar's latest daily-supply z-score crosses above Z_THRESHOLD
             AND we are flat AND no entry in last HOLD_BARS bars
    Exit   : after HOLD_BARS bars (forced close)

    Uses backtesting.py's commission for realistic fee accounting.
    """

    z_threshold = Z_THRESHOLD
    hold_bars = HOLD_BARS

    def init(self):
        # Pre-supplied via data; pull from auxiliary column
        self.z = self.I(lambda: self.data.df['z'].values, name='z', overlay=False)
        self._entry_bar: Optional[int] = None

    def next(self):
        i = len(self.data) - 1
        z_now = self.z[-1]

        # Force exit after hold window
        if self.position and self._entry_bar is not None:
            held = i - self._entry_bar
            if held >= self.hold_bars:
                self.position.close()
                self._entry_bar = None
                return  # one decision per bar

        # Crossover entry: previous z below, current z above
        if not self.position and len(self.data) >= 2:
            prev_z = self.z[-2]
            if (
                np.isfinite(prev_z) and np.isfinite(z_now)
                and prev_z <= self.z_threshold
                and z_now > self.z_threshold
            ):
                self.buy(size=ENTRY_FRACTION)
                self._entry_bar = i


# ──────────────────────────────────────────────────────────────────
# Runners
# ──────────────────────────────────────────────────────────────────

def run_one(df: pd.DataFrame, fee_per_side: float, label: str,
            plot: bool = False) -> Dict:
    bt = Backtest(
        df,
        A2StablecoinImpulse,
        cash=10_000,
        commission=fee_per_side,
        exclusive_orders=True,
        trade_on_close=False,  # next-bar fill — no look-ahead
    )
    stats = bt.run()
    out: Dict[str, float] = {}
    keep = [
        'Start', 'End', 'Duration', 'Exposure Time [%]',
        'Equity Final [$]', 'Equity Peak [$]',
        'Return [%]', 'Buy & Hold Return [%]',
        'Return (Ann.) [%]', 'Volatility (Ann.) [%]',
        'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio',
        'Max. Drawdown [%]', 'Avg. Drawdown [%]', 'Max. Drawdown Duration',
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
                if np.isnan(v) or np.isinf(v):
                    out[k] = None
                else:
                    out[k] = float(v)
            else:
                out[k] = str(v)
    if plot:
        plot_path = os.path.join(OUTPUT_DIR, f'a2_eth_equity_{label}.html')
        try:
            bt.plot(filename=plot_path, open_browser=False)
            out['plot_path'] = plot_path
        except Exception as e:
            out['plot_error'] = str(e)
    return out


def main():
    print("═" * 74)
    print("  A2 ETH/USDT — backtesting.py end-to-end (research artifact)")
    print("═" * 74)
    print()

    # Step 1: data
    daily_z = build_daily_z(DEFILLAMA_STABLECOIN_IDS)
    df = build_perp_df(PAIR)

    # Filter to EARLIEST_TS bound
    df = df[df.index >= pd.Timestamp(EARLIEST_TS, unit='s', tz='UTC')]
    z_series = build_entry_series(df, daily_z)
    df = df.assign(z=z_series.values)
    df = df.dropna(subset=['z'])

    n_signal = int(((df['z'].shift(1) <= Z_THRESHOLD) & (df['z'] > Z_THRESHOLD)).sum())
    print(f"  Bars after alignment: {len(df)}")
    print(f"  Crossover entries (z↑>{Z_THRESHOLD}): {n_signal}")
    print()

    # Step 2: full-history backtest at three fee tiers
    print("── Full-history backtest (2023-01 → now) ──")
    full_results = {}
    for tier_label, fee_per_side in FEE_SCENARIOS.items():
        print(f"  Running tier {tier_label} (fee={fee_per_side*10000:.1f} bps/side) ...")
        full_results[tier_label] = run_one(
            df, fee_per_side,
            label=f'full_{tier_label}',
            plot=(tier_label == 'C_VIP1_maker_only'),  # only one HTML to save space
        )
    print()

    # Step 3: yearly OOS folds (matches validation suite folds)
    print("── Yearly OOS folds (matches a2_validation_suite.py) ──")
    yearly_results: Dict[str, Dict[str, Dict]] = {}
    for year in [2023, 2024, 2025, 2026]:
        start = pd.Timestamp(f'{year}-01-01', tz='UTC')
        end = pd.Timestamp(f'{year+1}-01-01', tz='UTC')
        sub = df[(df.index >= start) & (df.index < end)]
        if len(sub) < 200:
            print(f"  {year}: skipped (only {len(sub)} bars)")
            continue
        yearly_results[str(year)] = {}
        for tier_label, fee_per_side in FEE_SCENARIOS.items():
            r = run_one(sub, fee_per_side, label=f'{year}_{tier_label}', plot=False)
            yearly_results[str(year)][tier_label] = r
            print(f"  {year} {tier_label}: "
                  f"Return={r.get('Return [%]', float('nan')):+7.2f}%  "
                  f"Sharpe={r.get('Sharpe Ratio', float('nan')):+5.2f}  "
                  f"MaxDD={r.get('Max. Drawdown [%]', float('nan')):+6.2f}%  "
                  f"Trades={int(r.get('# Trades', 0))}")
    print()

    # Step 4: write artifact
    out = {
        'run_time': datetime.now(timezone.utc).isoformat(),
        'mode': 'A2_ETH_BACKTEST_VIA_BACKTESTING_PY',
        'pair': PAIR,
        'hold_bars': HOLD_BARS,
        'z_threshold': Z_THRESHOLD,
        'fee_scenarios_per_side': FEE_SCENARIOS,
        'full_history': full_results,
        'yearly_folds': yearly_results,
        'caveats': [
            'A2 is a candidate per L99_ALPHA_VALIDATION §1.6.',
            'Not deployable per §3 (paper-validation gate not passed).',
            'Walk-forward already showed 2/8 yearly folds pass L99 battery.',
            'Lag-shift ±1d showed BTC failure across all shifts.',
            'Regime-conditional showed 0/6 single-regime sub-tests survive.',
            'Backtest run as research artifact only. NOT integrated into live config.',
            'Position remains 100% USDT.',
        ],
    }
    out_path = os.path.join(OUTPUT_DIR, 'a2_eth_backtest_bt_results.json')
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"  → results: {out_path}")
    print()

    # Step 5: synthesis
    print("═" * 74)
    print("  SYNTHESIS — full-history vs yearly OOS")
    print("═" * 74)
    for tier_label in FEE_SCENARIOS:
        full_ret = full_results[tier_label].get('Return [%]')
        full_sharpe = full_results[tier_label].get('Sharpe Ratio')
        full_dd = full_results[tier_label].get('Max. Drawdown [%]')
        full_n = full_results[tier_label].get('# Trades')
        bh = full_results[tier_label].get('Buy & Hold Return [%]')
        print(f"  {tier_label:22s}: full Return={full_ret:+7.2f}%  "
              f"Sharpe={full_sharpe:+5.2f}  MaxDD={full_dd:+6.2f}%  "
              f"Trades={int(full_n) if full_n else 0}  vs B&H {bh:+7.2f}%")
    print()
    print("  Yearly Sharpe instability (maker tier):")
    for year, by_tier in yearly_results.items():
        sh = by_tier.get('C_VIP1_maker_only', {}).get('Sharpe Ratio')
        rt = by_tier.get('C_VIP1_maker_only', {}).get('Return [%]')
        print(f"     {year}: Sharpe={sh if sh is not None else 'nan':>6}  Return={rt}")
    print()
    print("  Decision: NOT integrated into l99/config.py. Position = 100% USDT.")
    print("  Backtest stands as research artifact next to validation_suite.")
    print("═" * 74)


if __name__ == '__main__':
    main()
