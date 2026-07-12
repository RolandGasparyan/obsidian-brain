"""
V1 — VWAP-gap mean-reversion (z-score conditional)

NEW FACTOR FAMILY pivot after A2's 3-round falsification.

ORTHOGONALITY TO 10 PRIOR NULLS
================================
  Prior NULLs hit:                      V1 uses:
  D6  tick microstructure               4h bar OHLCV (different timescale)
  C2  4h volatility regime              price-VWAP gap (different signal)
  C1  BTC-DXY joint                     single-asset within universe
  NATIVE D2 look-ahead                  strict bisect_right - 1 alignment
  B1  funding mean                      no funding dependence
  B2  OI spike + flat price             no OI dependence
  B3  basis |z|                         price gap z (signed, mean-rev)
  A2  stablecoin supply                 no on-chain dependence
  Old "VWAPSniper" (Apr-24)             z-conditional, not proximity-bounce
                                        L99 battery, not pattern-match

HYPOTHESIS
==========
Across 4h timeframe, instantaneous price extremes vs the rolling 24h
volume-weighted average price (VWAP) revert. Specifically:

  factor    = (close - vwap_24h) / vwap_24h * 10000   (bps gap)
  z         = (factor - rolling_mean_30d) / rolling_std_30d
  signal    = |z| > 2.0
  direction = SHORT if z > +2.0, LONG if z < -2.0   (mean-reversion)
  hold      = 18 bars (3d) — same as A2 for cross-comparison
  forward   = SIGNED return per pair, oriented to the trade direction

Mean-reversion IC convention: NEGATIVE IC between z and forward-return
indicates edge (high gap → negative fwd return on a short). We score
the absolute value against L99.IC_MIN.

§3.5 GATE BUILT-IN FROM DAY 1
==============================
A genuine pass requires ALL of:

  L99 battery (existing):
    IC ≥ 0.04, |t| ≥ 2.0, PF ≥ 1.3, Q5−Q1 NET ≥ 60 bps,
    MC stability ≥ 80%, ≥ 2 regimes, N ≥ 100

  + §3.5 backtest gate (new, day-1 mandatory):
    Sharpe ≥ 1.0 on full history
    Beat per-pair B&H (long-only benchmark)
    ≥ 3 of 4 yearly OOS folds with Sharpe > 0
    MaxDD > -25%
    ≥ 30 trades for power
    Win Rate ≥ 40%

Failing ANY gate → 11th NULL, document, pivot again. No threshold tuning.

DISCIPLINE
==========
  - Position remains 100% USDT
  - 17 L99 modules dormant
  - No live config integration regardless of result
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from basis_extended_runner import fetch_4h_paginated_perp as fetch_perp_4h_paginated  # reuse
from l99_battery import L99, ic, tstat


# ──────────────────────────────────────────────────────────────────
# Config — locked at day-1; no tuning permitted
# ──────────────────────────────────────────────────────────────────

PAIRS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'XRP_USDT', 'AVAX_USDT']
EARLIEST_TS = 1672531200  # 2023-01-01 UTC

VWAP_LOOKBACK_BARS = 6      # 24 hours at 4h cadence
Z_LOOKBACK_BARS = 180       # 30 days at 4h cadence
Z_THRESHOLD = 2.0
HOLD_BARS = 18              # 3 days at 4h
HORIZONS = {'3d': 18, '5d': 30, '7d': 42}

FEE_SCENARIOS = {
    'A_VIP0_taker':       0.00125,  # 12.5 bps per side
    'B_VIP1_GT_discount': 0.00090,
    'C_VIP1_maker_only':  0.00070,
}

# §3.5 gate (day-1 mandatory)
GATE_SHARPE = 1.0
GATE_MAX_DD = -25.0
GATE_MIN_TRADES = 30
GATE_MIN_WIN_RATE = 40.0
GATE_MIN_GOOD_YEARS = 3

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ──────────────────────────────────────────────────────────────────
# Factor construction
# ──────────────────────────────────────────────────────────────────

def rolling_vwap(closes: List[float], volumes: List[float], lookback: int) -> List[Optional[float]]:
    """Rolling volume-weighted average price."""
    out: List[Optional[float]] = [None] * len(closes)
    for i in range(lookback, len(closes)):
        w_close = closes[i - lookback:i]
        w_vol = volumes[i - lookback:i]
        denom = sum(w_vol)
        if denom <= 0:
            continue
        out[i] = sum(c * v for c, v in zip(w_close, w_vol)) / denom
    return out


def gap_bps(closes: List[float], vwap: List[Optional[float]]) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(closes)
    for i, (c, v) in enumerate(zip(closes, vwap)):
        if v is not None and v > 0:
            out[i] = (c - v) / v * 10000.0
    return out


def rolling_zscore(series: List[Optional[float]], lookback: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(series)
    for i in range(lookback, len(series)):
        w = [x for x in series[i - lookback:i] if x is not None]
        if len(w) < lookback // 2:
            continue
        mu = statistics.mean(w)
        sd = statistics.pstdev(w)
        if sd <= 0 or series[i] is None:
            continue
        out[i] = (series[i] - mu) / sd
    return out


def regime_label(closes: List[float], i: int, lookback: int = 30 * 6) -> str:
    if i < lookback or closes[i - lookback] <= 0:
        return 'unknown'
    ret = (closes[i] - closes[i - lookback]) / closes[i - lookback] * 100
    if ret > 10:
        return 'bull'
    if ret < -10:
        return 'bear'
    return 'range'


def quintile_spread_bps_signed(factor: List[Optional[float]],
                                forward: List[Optional[float]],
                                fee_rt: float,
                                mean_rev: bool = True) -> float:
    """For mean-reversion: edge = mean(Q1.fwd) - mean(Q5.fwd) (low-z forward >> high-z forward).
    NET via per-leg fee math (×10000 ×2)."""
    pairs = [(f, r) for f, r in zip(factor, forward)
             if f is not None and r is not None]
    if len(pairs) < 20:
        return 0.0
    pairs.sort(key=lambda x: x[0])
    nq = max(1, len(pairs) // 5)
    q1 = [p[1] for p in pairs[:nq]]
    q5 = [p[1] for p in pairs[-nq:]]
    raw = (statistics.mean(q1) - statistics.mean(q5)) if mean_rev \
          else (statistics.mean(q5) - statistics.mean(q1))
    return raw * 100 - fee_rt * 10000 * 2


def battery(name: str,
            factor_vals: List[Optional[float]],
            forward: List[Optional[float]],
            regimes: List[str],
            mask: List[bool],
            directions: List[Optional[int]],   # +1=long, -1=short, None=skip
            fee_rt: float) -> Dict:
    """Battery with SIGNED, direction-oriented forward returns.
    For each masked entry, the realized return is direction[i] * forward[i]."""
    indices = [i for i in range(len(mask))
               if mask[i] and factor_vals[i] is not None
               and forward[i] is not None and directions[i] in (-1, 1)]
    n = len(indices)
    killed: List[str] = []
    if n < L99.MIN_OBS:
        return {'name': name, 'fee_rt_bps': fee_rt * 10000, 'n': n,
                'passes': False, 'killed_by': [f'N={n}<{L99.MIN_OBS}'],
                'ic': 0, 'tstat': 0, 'pf': 0, 'q_bps': 0, 'mc': 0,
                'regime_count': 0}

    sig_factor = [factor_vals[i] for i in indices]
    raw_fwd = [forward[i] for i in indices]
    direction_oriented = [directions[i] * forward[i] for i in indices]
    net_returns = [r - fee_rt * 100 for r in direction_oriented]

    # IC against UN-oriented forward — mean-rev expected NEGATIVE
    ic_v = ic(sig_factor, raw_fwd)
    ts_v = tstat(net_returns)

    wins = [r for r in net_returns if r > 0]
    losses = [r for r in net_returns if r <= 0]
    pf_v = (sum(wins) / abs(sum(losses))) if (wins and losses) else (
        999.0 if not losses else 0.0
    )

    qs_v = quintile_spread_bps_signed(factor_vals, forward, fee_rt, mean_rev=True)

    import random
    rng = random.Random(42)
    mc_wins = 0
    for _ in range(500):
        sample = [rng.choice(net_returns) for _ in range(n)]
        if sum(sample) > 0:
            mc_wins += 1
    mc_v = mc_wins / 500.0

    sig_regimes = [regimes[i] for i in indices]
    regime_ret: Dict[str, List[float]] = {}
    for r_lab, ret in zip(sig_regimes, net_returns):
        regime_ret.setdefault(r_lab, []).append(ret)
    reg_count = sum(1 for rets in regime_ret.values()
                    if len(rets) >= 5 and statistics.mean(rets) > 0)

    if abs(ic_v) < L99.IC_MIN:
        killed.append(f"IC={ic_v:+.4f}")
    if abs(ts_v) < L99.TSTAT_MIN:
        killed.append(f"t={ts_v:+.4f}")
    if pf_v < L99.PF_MIN:
        killed.append(f"PF={pf_v:.4f}")
    if qs_v < L99.QUINTILE_MIN:
        killed.append(f"Q5-Q1={qs_v:+.2f}")
    if mc_v < L99.MC_STABILITY:
        killed.append(f"MC={mc_v*100:.1f}%")
    if reg_count < L99.REGIME_MIN:
        killed.append(f"Reg={reg_count}")

    return {'name': name, 'fee_rt_bps': fee_rt * 10000, 'n': n,
            'passes': len(killed) == 0, 'killed_by': killed,
            'ic': ic_v, 'tstat': ts_v, 'pf': pf_v, 'q_bps': qs_v,
            'mc': mc_v, 'regime_count': reg_count,
            'gross_expectancy': statistics.mean(direction_oriented),
            'net_expectancy': statistics.mean(net_returns)}


# ──────────────────────────────────────────────────────────────────
# Per-pair pipeline
# ──────────────────────────────────────────────────────────────────

def build_pair(contract: str) -> Optional[Dict]:
    bars = fetch_perp_4h_paginated(contract)
    if len(bars) < 1000:
        print(f"  {contract}: too few bars ({len(bars)})")
        return None
    closes = [b['c'] for b in bars]
    volumes = [b['v'] for b in bars]
    vwap = rolling_vwap(closes, volumes, VWAP_LOOKBACK_BARS)
    gap = gap_bps(closes, vwap)
    z = rolling_zscore(gap, Z_LOOKBACK_BARS)

    n = len(bars)
    mask = [False] * n
    directions: List[Optional[int]] = [None] * n
    for i, zv in enumerate(z):
        if zv is None:
            continue
        if zv > Z_THRESHOLD:
            mask[i] = True
            directions[i] = -1   # short the high gap
        elif zv < -Z_THRESHOLD:
            mask[i] = True
            directions[i] = +1   # long the low gap

    fwd: Dict[str, List[Optional[float]]] = {}
    for label, h in HORIZONS.items():
        fwd[label] = [None] * n
        for i in range(n - h):
            if closes[i] > 0:
                fwd[label][i] = (closes[i + h] - closes[i]) / closes[i] * 100

    regimes = [regime_label(closes, i) for i in range(n)]
    return {
        'contract': contract, 'bars': bars, 'closes': closes, 'volumes': volumes,
        'vwap': vwap, 'gap': gap, 'z': z, 'mask': mask, 'directions': directions,
        'fwd': fwd, 'regimes': regimes,
        'n_signal': sum(mask),
    }


# ──────────────────────────────────────────────────────────────────
# Backtesting.py harness
# ──────────────────────────────────────────────────────────────────

def to_df(d: Dict) -> pd.DataFrame:
    out = pd.DataFrame(d['bars']).rename(columns={
        'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume',
    })
    out['Datetime'] = pd.to_datetime(out['ts'], unit='s', utc=True)
    out = out.set_index('Datetime').drop(columns=['ts'])
    out = out[['Open', 'High', 'Low', 'Close', 'Volume']]
    out['z'] = d['z']
    out['direction'] = [x if x is not None else 0 for x in d['directions']]
    return out.dropna(subset=['z'])


class V1VwapGapMeanRev(Strategy):
    z_threshold = Z_THRESHOLD
    hold_bars = HOLD_BARS

    def init(self):
        self.z = self.I(lambda: self.data.df['z'].values, name='z', overlay=False)
        self.dir = self.I(lambda: self.data.df['direction'].values, name='dir', overlay=False)
        self._entry_bar: Optional[int] = None
        self._entry_dir: int = 0

    def next(self):
        i = len(self.data) - 1
        if self.position and self._entry_bar is not None:
            if i - self._entry_bar >= self.hold_bars:
                self.position.close()
                self._entry_bar = None
                self._entry_dir = 0
                return

        if not self.position and len(self.data) >= 2:
            prev_z = self.z[-2]
            cur_z = self.z[-1]
            cur_d = int(self.dir[-1])
            # Crossing into extreme zone (z prev was inside band, now outside)
            cross_short = (
                np.isfinite(prev_z) and np.isfinite(cur_z)
                and prev_z <= self.z_threshold < cur_z
                and cur_d == -1
            )
            cross_long = (
                np.isfinite(prev_z) and np.isfinite(cur_z)
                and prev_z >= -self.z_threshold > cur_z
                and cur_d == +1
            )
            if cross_long:
                self.buy(size=0.90)
                self._entry_bar = i
                self._entry_dir = +1
            elif cross_short:
                self.sell(size=0.90)
                self._entry_bar = i
                self._entry_dir = -1


def run_bt(df: pd.DataFrame, fee_per_side: float, label: str,
           plot: bool = False) -> Dict:
    bt = Backtest(df, V1VwapGapMeanRev, cash=10_000,
                  commission=fee_per_side, exclusive_orders=True,
                  trade_on_close=False, margin=1.0, hedging=False)
    stats = bt.run()
    out: Dict = {}
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
        path = os.path.join(OUTPUT_DIR, f'v1_{label}.html')
        try:
            bt.plot(filename=path, open_browser=False)
            out['plot_path'] = path
        except Exception as e:
            out['plot_error'] = str(e)
    return out


def gate(full: Dict, yearly: Dict[str, Dict]) -> Tuple[bool, List[str]]:
    fail: List[str] = []
    sh = full.get('Sharpe Ratio')
    if sh is None or sh < GATE_SHARPE:
        fail.append(f"Sharpe={sh} < {GATE_SHARPE}")
    ret = full.get('Return [%]') or 0.0
    bh = full.get('Buy & Hold Return [%]') or 0.0
    if ret <= bh:
        fail.append(f"Return={ret:.2f}% does NOT beat B&H={bh:.2f}%")
    dd = full.get('Max. Drawdown [%]') or 0.0
    if dd < GATE_MAX_DD:
        fail.append(f"MaxDD={dd:.2f}% < {GATE_MAX_DD}%")
    n = full.get('# Trades') or 0
    if n < GATE_MIN_TRADES:
        fail.append(f"#Trades={int(n)} < {GATE_MIN_TRADES}")
    wr = full.get('Win Rate [%]') or 0.0
    if wr < GATE_MIN_WIN_RATE:
        fail.append(f"WinRate={wr:.1f}% < {GATE_MIN_WIN_RATE}%")
    good = sum(1 for r in yearly.values()
               if r.get('Sharpe Ratio') is not None and r['Sharpe Ratio'] > 0)
    if good < GATE_MIN_GOOD_YEARS:
        fail.append(f"GoodYears={good}/{len(yearly)} < {GATE_MIN_GOOD_YEARS}")
    return len(fail) == 0, fail


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────

def main():
    print("═" * 74)
    print("  V1 — VWAP-gap mean-reversion (z-conditional)")
    print("  NEW factor family pivot. §3.5 gate built-in from day 1.")
    print("═" * 74)

    pair_data: Dict[str, Dict] = {}
    print("\n  Step 1 — fetch + compute factor per pair ...")
    for p in PAIRS:
        print(f"    {p} ...", flush=True)
        d = build_pair(p)
        if d is not None:
            pair_data[p] = d
            print(f"       n_bars={len(d['bars'])}  n_signal={d['n_signal']}")
    if not pair_data:
        print("  ❌ no pair data — abort.")
        return

    output: Dict = {
        'run_time': datetime.now(timezone.utc).isoformat(),
        'mode': 'V1_VWAP_GAP_MEAN_REVERSION',
        'pairs_attempted': PAIRS,
        'pairs_loaded': list(pair_data.keys()),
        'config': {
            'vwap_lookback_bars': VWAP_LOOKBACK_BARS,
            'z_lookback_bars': Z_LOOKBACK_BARS,
            'z_threshold': Z_THRESHOLD,
            'hold_bars': HOLD_BARS,
        },
        'gate_thresholds': {
            'sharpe_min': GATE_SHARPE, 'max_dd_min': GATE_MAX_DD,
            'trades_min': GATE_MIN_TRADES, 'win_rate_min': GATE_MIN_WIN_RATE,
            'good_years_min': GATE_MIN_GOOD_YEARS,
        },
    }

    # ─── L99 battery (per-pair, all horizons, 3 fee tiers) ───
    print("\n  Step 2 — L99 battery (per-pair) ...")
    battery_out: Dict = {}
    for pair, d in pair_data.items():
        for horizon, _h_bars in HORIZONS.items():
            for tier_label, fee in FEE_SCENARIOS.items():
                fee_rt = fee * 2
                name = f"V1_{pair}_{horizon}_{tier_label}"
                r = battery(name, d['z'], d['fwd'][horizon], d['regimes'],
                            d['mask'], d['directions'], fee_rt)
                battery_out[name] = r
                if r['passes']:
                    print(f"    ✅ {name}: IC={r['ic']:+.4f} t={r['tstat']:+.2f} "
                          f"PF={r['pf']:.2f} Q={r['q_bps']:+.1f} N={r['n']}")
    n_pass = sum(1 for r in battery_out.values() if r['passes'])
    print(f"  L99 battery passes: {n_pass} of {len(battery_out)}")
    output['battery'] = battery_out

    # ─── §3.5 backtesting.py — per pair, full history ───
    print("\n  Step 3 — backtesting.py per-pair (§3.5 gate) ...")
    bt_out: Dict = {}
    for pair, d in pair_data.items():
        df = to_df(d)
        df = df[df.index >= pd.Timestamp(EARLIEST_TS, unit='s', tz='UTC')]
        if len(df) < 500:
            continue
        bt_out[pair] = {'full_history': {}, 'yearly_folds': {}}
        for tier_label, fee in FEE_SCENARIOS.items():
            r = run_bt(df, fee, label=f'{pair}_full_{tier_label}',
                       plot=(tier_label == 'C_VIP1_maker_only'))
            bt_out[pair]['full_history'][tier_label] = r
            print(f"    {pair} {tier_label}: "
                  f"Return={r.get('Return [%]', float('nan')):+7.2f}%  "
                  f"Sharpe={r.get('Sharpe Ratio') or 0:+5.2f}  "
                  f"MaxDD={r.get('Max. Drawdown [%]', float('nan')):+6.2f}%  "
                  f"Trades={int(r.get('# Trades', 0))}  "
                  f"vs B&H {r.get('Buy & Hold Return [%]', float('nan')):+7.2f}%")

        # Yearly folds at maker tier
        fee = FEE_SCENARIOS['C_VIP1_maker_only']
        for year in [2023, 2024, 2025, 2026]:
            start = pd.Timestamp(f'{year}-01-01', tz='UTC')
            end = pd.Timestamp(f'{year+1}-01-01', tz='UTC')
            sub = df[(df.index >= start) & (df.index < end)]
            if len(sub) < 200:
                continue
            r = run_bt(sub, fee, label=f'{pair}_{year}', plot=False)
            bt_out[pair]['yearly_folds'][str(year)] = r

        # §3.5 gate
        gp, gf = gate(bt_out[pair]['full_history']['C_VIP1_maker_only'],
                      bt_out[pair]['yearly_folds'])
        bt_out[pair]['gate_pass'] = gp
        bt_out[pair]['gate_failures'] = gf
        print(f"    §3.5 gate ({pair}): {'✅ PASS' if gp else '❌ FAIL'}")
        for f in gf:
            print(f"       - {f}")
    output['backtest'] = bt_out

    # ─── Final synthesis ───
    out_path = os.path.join(OUTPUT_DIR, 'v1_vwap_gap_results.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  → {out_path}")

    print("\n" + "═" * 74)
    print("  FINAL VERDICT")
    print("═" * 74)
    pairs_passing = [p for p, r in bt_out.items() if r.get('gate_pass')]
    l99_passing = [n for n, r in battery_out.items() if r['passes']]
    print(f"  L99 battery passes:        {len(l99_passing)} of {len(battery_out)}")
    print(f"  §3.5 backtest gate passes: {len(pairs_passing)} of {len(bt_out)}")
    if l99_passing and pairs_passing:
        print(f"  → CANDIDATE on pairs: {pairs_passing}")
        print(f"  → Operator must approve for Stage 1 paper validation.")
    else:
        print("  → 11th NULL. V1 falsified. Pivot to next factor family.")
    print("  → Position remains 100% USDT.")
    print("═" * 74)


if __name__ == '__main__':
    main()
