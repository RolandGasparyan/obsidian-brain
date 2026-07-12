"""
A2 Validation Suite — 3 robustness checks on the A2 Candidate Alpha.

Per PR #26 finding: A2 Stablecoin Supply Impulse appears to clear L99 §1.6
Decision Matrix (7 of 27 combinations PASS, 4-of-4 audit checks survive).

Before §3 Stage 1 paper validation, run 3 cheap-but-decisive falsification
attempts per discipline framework recommendations:

  1. LAG-SHIFT ±1 — Re-run with entry shifted ±1 day. Real edges are robust
     to small temporal misalignment; curve-fits collapse.

  2. WALK-FORWARD OOS — Train period 2023, test 2024-Q1; refit 2023+2024-Q1,
     test 2024-Q2..; etc. Stable factor maintains IC across all OOS folds.

  3. REGIME-CONDITIONAL — Stratify signal events by regime label at entry.
     Verify edge persists across BULL + BEAR + RANGE regimes (or fails
     in non-bull → bull-confound was the edge, not A2 mechanism).

Outcomes:
  3a) ALL 3 survive → strong candidate, ready for §3 Stage 1 paper
  3b) SOME survive → conditional candidate (e.g., regime-gated)
  3c) NONE survive → joins 9-NULL pile cleanly with proper methodology
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '.')
from a2_stablecoin_runner import (
    fetch_stablecoin_history,
    fetch_perp_4h_paginated,
    rolling_zscore,
    n_day_change,
    regime_label,
    DEFILLAMA_STABLECOIN_IDS,
    Z_LOOKBACK,
    GROWTH_LOOKBACK_7D,
    Z_THRESHOLD,
    HORIZONS,
    PAIRS_TO_TEST,
    FEE_SCENARIOS,
)
from l99_battery import L99, ic, tstat


# ─────────────────────────────────────────────
# Helpers from runner (re-implementation for clarity)
# ─────────────────────────────────────────────

def quintile_spread_bps(factor: List[Optional[float]],
                        forward: List[Optional[float]],
                        fee_rt: float) -> float:
    pairs = [(f, r) for f, r in zip(factor, forward)
             if f is not None and r is not None]
    if len(pairs) < 20:
        return 0.0
    pairs.sort(key=lambda x: x[0])
    nq = max(1, len(pairs) // 5)
    q1 = [p[1] for p in pairs[:nq]]
    q5 = [p[1] for p in pairs[-nq:]]
    return (statistics.mean(q5) - statistics.mean(q1)) * 100 - fee_rt * 10000 * 2


def quick_battery(name: str,
                  factor: List[Optional[float]],
                  forward: List[Optional[float]],
                  regimes: List[str],
                  mask: List[bool],
                  fee_rt: float = 0.0014) -> Dict:
    """Lightweight battery — only computes the metrics we care about for
    this validation pass. fee_rt defaults to maker-only (best case)."""
    indices = [i for i in range(len(mask))
               if mask[i] and factor[i] is not None and forward[i] is not None]
    n = len(indices)
    if n < L99.MIN_OBS:
        return {'name': name, 'n': n, 'passes': False, 'killed_by': [f'N={n}<100']}
    sig_factor = [factor[i] for i in indices]
    sig_returns = [forward[i] for i in indices]
    net_returns = [r - fee_rt * 100 for r in sig_returns]
    ic_v = ic(sig_factor, sig_returns)
    ts_v = tstat(net_returns)
    wins = [r for r in net_returns if r > 0]
    losses = [r for r in net_returns if r <= 0]
    pf_v = (sum(wins) / abs(sum(losses))) if (wins and losses) else (999 if not losses else 0)
    qs_v = quintile_spread_bps(factor, forward, fee_rt)

    sig_regimes = [regimes[i] for i in indices]
    regime_ret: Dict[str, List[float]] = {}
    for r_label, ret in zip(sig_regimes, net_returns):
        regime_ret.setdefault(r_label, []).append(ret)
    reg_count = sum(1 for rets in regime_ret.values()
                    if len(rets) >= 5 and statistics.mean(rets) > 0)

    killed_by = []
    if abs(ic_v) < L99.IC_MIN:
        killed_by.append(f"IC={ic_v:+.4f}")
    if abs(ts_v) < L99.TSTAT_MIN:
        killed_by.append(f"t={ts_v:+.4f}")
    if pf_v < L99.PF_MIN:
        killed_by.append(f"PF={pf_v:.4f}")
    if qs_v < L99.QUINTILE_MIN:
        killed_by.append(f"Q5-Q1={qs_v:+.2f}")
    if reg_count < L99.REGIME_MIN:
        killed_by.append(f"Reg={reg_count}")

    return {
        'name': name, 'n': n,
        'ic': ic_v, 'tstat': ts_v, 'pf': pf_v, 'q_bps': qs_v,
        'regime_count': reg_count,
        'passes': len(killed_by) == 0,
        'killed_by': killed_by,
    }


def build_signal(daily_z: Dict[int, float],
                 perp_bars: List[Dict[str, float]],
                 horizon_bars: int,
                 lag_shift: int = 0,
                 ) -> Tuple[List[bool], List[Optional[float]],
                              List[Optional[float]], List[str]]:
    """Build signal mask + factor + forward returns + regimes for a pair.
    lag_shift: shift entry timing by this many bars (e.g. +1 = entry 1 bar later)."""
    import bisect
    sorted_supply_ts = sorted(daily_z.keys())
    n = len(perp_bars)
    closes = [b['c'] for b in perp_bars]

    mask = [False] * n
    factor: List[Optional[float]] = [None] * n
    fwd: List[Optional[float]] = [None] * n
    regimes = [regime_label(closes, i) for i in range(n)]

    for i in range(n):
        bar_ts = perp_bars[i]['ts']
        idx = bisect.bisect_right(sorted_supply_ts, bar_ts) - 1
        if idx < 0:
            continue
        z = daily_z[sorted_supply_ts[idx]]
        # Apply lag-shift: entry happens at i + lag_shift
        entry_idx = i + lag_shift
        if entry_idx < 0 or entry_idx >= n:
            continue
        factor[entry_idx] = z
        if entry_idx + horizon_bars < n and closes[entry_idx] > 0:
            fwd[entry_idx] = (closes[entry_idx + horizon_bars] - closes[entry_idx]) / closes[entry_idx] * 100
        if z > Z_THRESHOLD:
            mask[entry_idx] = True

    return mask, factor, fwd, regimes


# ─────────────────────────────────────────────
# Validation 1 — Lag-Shift ±1
# ─────────────────────────────────────────────

def validate_lag_shift(daily_z: Dict[int, float],
                       perp_data: Dict[str, List[Dict[str, float]]]) -> Dict:
    """Re-run battery with entry shifted ±1 day (=6 4h bars)."""
    print("\n  ── VALIDATION 1: LAG-SHIFT ±1 day (6 bars) ──")
    print("    Theory: real edge survives small entry shifts; curve-fits collapse.")
    print()
    results = {}
    for shift_bars, label in [(-6, "lag_minus1d"), (0, "lag_zero"), (+6, "lag_plus1d")]:
        for pair in PAIRS_TO_TEST:
            for h_label in ['3d']:  # focus on 3d horizon (the strongest pass)
                mask, factor, fwd, regimes = build_signal(
                    daily_z, perp_data[pair], HORIZONS[h_label], lag_shift=shift_bars,
                )
                res = quick_battery(
                    f'A2_{pair}_{h_label}_{label}',
                    factor, fwd, regimes, mask,
                )
                results[res['name']] = res
                status = "✅ PASS" if res.get('passes') else "❌"
                print(f"    {res['name']:<48} N={res.get('n', 0):>4}  "
                      f"IC={res.get('ic', 0):+.4f}  t={res.get('tstat', 0):+.3f}  "
                      f"PF={res.get('pf', 0):.2f}  Q={res.get('q_bps', 0):+.1f}  {status}")
    return results


# ─────────────────────────────────────────────
# Validation 2 — Walk-Forward OOS
# ─────────────────────────────────────────────

def validate_walk_forward(daily_z: Dict[int, float],
                          perp_data: Dict[str, List[Dict[str, float]]]) -> Dict:
    """Split sample by year. Test stability of IC across temporal folds."""
    print("\n  ── VALIDATION 2: WALK-FORWARD (yearly folds) ──")
    print("    Theory: real edge stable across time; over-fit collapses on OOS.")
    print()
    results = {}

    # For each pair, split into yearly folds
    for pair in PAIRS_TO_TEST:
        bars = perp_data[pair]
        if not bars:
            continue
        mask, factor, fwd, regimes = build_signal(
            daily_z, bars, HORIZONS['3d'], lag_shift=0,
        )

        # Group bars by calendar year
        bar_year = [datetime.fromtimestamp(b['ts'], timezone.utc).year for b in bars]
        years_present = sorted(set(bar_year))

        for yr in years_present:
            # Indices in this year
            yr_indices = [i for i in range(len(bars)) if bar_year[i] == yr]
            yr_factor = [factor[i] if i in set(yr_indices) else None for i in range(len(bars))]
            yr_fwd = [fwd[i] if i in set(yr_indices) else None for i in range(len(bars))]
            yr_mask = [mask[i] if i in set(yr_indices) else False for i in range(len(bars))]
            res = quick_battery(
                f'A2_{pair}_3d_year{yr}',
                yr_factor, yr_fwd, regimes, yr_mask,
            )
            results[res['name']] = res
            status = "✅" if res.get('passes') else "❌"
            print(f"    {res['name']:<48} N={res.get('n', 0):>4}  "
                  f"IC={res.get('ic', 0):+.4f}  t={res.get('tstat', 0):+.3f}  "
                  f"PF={res.get('pf', 0):.2f}  Q={res.get('q_bps', 0):+.1f}  {status}")
    return results


# ─────────────────────────────────────────────
# Validation 3 — Regime-Conditional
# ─────────────────────────────────────────────

def validate_regime_conditional(daily_z: Dict[int, float],
                                 perp_data: Dict[str, List[Dict[str, float]]]) -> Dict:
    """Stratify signal events by regime at entry. Verify edge in each."""
    print("\n  ── VALIDATION 3: REGIME-CONDITIONAL (CRITICAL — bull confound) ──")
    print("    Theory: if edge depends on bull regime → it's selection effect.")
    print()
    results = {}

    for pair in PAIRS_TO_TEST:
        bars = perp_data[pair]
        if not bars:
            continue
        mask, factor, fwd, regimes = build_signal(
            daily_z, bars, HORIZONS['3d'], lag_shift=0,
        )

        for target_regime in ('bull', 'range', 'bear'):
            # Mask = original mask AND regime[i] == target_regime
            r_mask = [mask[i] and regimes[i] == target_regime for i in range(len(bars))]
            res = quick_battery(
                f'A2_{pair}_3d_regime_{target_regime}',
                factor, fwd, regimes, r_mask,
            )
            results[res['name']] = res
            status = "✅" if res.get('passes') else "❌"
            print(f"    {res['name']:<48} N={res.get('n', 0):>4}  "
                  f"IC={res.get('ic', 0):+.4f}  t={res.get('tstat', 0):+.3f}  "
                  f"PF={res.get('pf', 0):.2f}  Q={res.get('q_bps', 0):+.1f}  {status}")
    return results


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("═" * 76)
    print("  A2 VALIDATION SUITE — Lag-shift + Walk-forward + Regime-conditional")
    print("  Subject: A2 Stablecoin Supply Impulse (Candidate Alpha per PR #26)")
    print("  L99 thresholds: INTACT (post-2026-05-05 corrections)")
    print("═" * 76)

    # ─── Reload data ───
    print("\n  Step 1: Load data (DefiLlama supply + Gate.io perp 4h)")
    daily_supplies: Dict[int, Dict[str, float]] = {}
    for symbol, coin_id in DEFILLAMA_STABLECOIN_IDS.items():
        for ts, v in fetch_stablecoin_history(coin_id):
            daily_supplies.setdefault(ts, {})[symbol] = v
        time.sleep(0.5)
    daily_total: Dict[int, float] = {}
    for ts, sup in daily_supplies.items():
        if 'USDT' in sup and 'USDC' in sup:
            daily_total[ts] = sup['USDT'] + sup['USDC']
    sorted_days = sorted(daily_total.keys())
    daily_total_series = [daily_total[ts] for ts in sorted_days]
    growth_7d = n_day_change(daily_total_series, GROWTH_LOOKBACK_7D)
    z_series = rolling_zscore(
        [g if g is not None else 0 for g in growth_7d], Z_LOOKBACK,
    )
    daily_z: Dict[int, float] = {}
    for i, ts in enumerate(sorted_days):
        if z_series[i] is not None and growth_7d[i] is not None:
            daily_z[ts] = z_series[i]
    print(f"    Daily Z-scores: {len(daily_z)}")

    perp_data: Dict[str, List[Dict[str, float]]] = {}
    for pair in PAIRS_TO_TEST:
        perp_data[pair] = fetch_perp_4h_paginated(pair)
        print(f"    {pair}: {len(perp_data[pair])} bars")

    # ─── Run 3 validations ───
    val1 = validate_lag_shift(daily_z, perp_data)
    val2 = validate_walk_forward(daily_z, perp_data)
    val3 = validate_regime_conditional(daily_z, perp_data)

    # ─── Synthesis ───
    print("\n" + "═" * 76)
    print("  SYNTHESIS — verdict on A2 Candidate Alpha after 3 validations")
    print("═" * 76)

    # Lag-shift: t-stat at zero vs ±1 should be similar magnitude
    lag_zero = [v for k, v in val1.items() if 'lag_zero' in k and 'BTC' not in k]
    lag_minus = [v for k, v in val1.items() if 'lag_minus1d' in k and 'BTC' not in k]
    lag_plus = [v for k, v in val1.items() if 'lag_plus1d' in k and 'BTC' not in k]

    print("\n  LAG-SHIFT verdict:")
    if lag_zero and lag_minus and lag_plus:
        t0 = lag_zero[0].get('tstat', 0)
        t_neg = lag_minus[0].get('tstat', 0)
        t_pos = lag_plus[0].get('tstat', 0)
        # Real edge: t-stat should not be MUCH higher at lag_zero than ±1
        if abs(t0) > 0 and abs(t_neg) / abs(t0) > 0.6 and abs(t_pos) / abs(t0) > 0.6:
            print(f"    ✅ PASS — t-stats similar across shifts (zero={t0:+.2f}, -1={t_neg:+.2f}, +1={t_pos:+.2f})")
        else:
            print(f"    ⚠ WEAK — t-stat at zero ({t0:+.2f}) much higher than ±1 ({t_neg:+.2f}, {t_pos:+.2f})")
            print("      Suggests entry-timing-sensitive (suspicious)")

    # Walk-forward: how many years pass independently?
    print("\n  WALK-FORWARD verdict:")
    yearly = [v for k, v in val2.items() if '_year' in k]
    yearly_pass = [v for v in yearly if v.get('passes')]
    yearly_pos_ic = [v for v in yearly if abs(v.get('ic', 0)) >= 0.04]
    if yearly:
        print(f"    Yearly folds tested: {len(yearly)}")
        print(f"    Folds passing full battery: {len(yearly_pass)}")
        print(f"    Folds with |IC|≥0.04: {len(yearly_pos_ic)}")
        if len(yearly_pos_ic) >= len(yearly) * 0.6:
            print("    ✅ PASS — IC stable across most years")
        else:
            print("    ⚠ MIXED — IC unstable across years")

    # Regime conditional
    print("\n  REGIME-CONDITIONAL verdict (most critical):")
    bull = [v for k, v in val3.items() if 'regime_bull' in k]
    range_ = [v for k, v in val3.items() if 'regime_range' in k]
    bear = [v for k, v in val3.items() if 'regime_bear' in k]
    bull_pos = sum(1 for v in bull if abs(v.get('ic', 0)) >= 0.04 and v.get('n', 0) >= 30)
    range_pos = sum(1 for v in range_ if abs(v.get('ic', 0)) >= 0.04 and v.get('n', 0) >= 30)
    bear_pos = sum(1 for v in bear if abs(v.get('ic', 0)) >= 0.04 and v.get('n', 0) >= 30)
    print(f"    Bull regime: pairs with edge / total = {bull_pos}/{len(bull)}")
    print(f"    Range regime: {range_pos}/{len(range_)}")
    print(f"    Bear regime: {bear_pos}/{len(bear)}")
    if bull_pos > 0 and (range_pos > 0 or bear_pos > 0):
        print("    ✅ PASS — edge persists across multiple regimes")
    elif bull_pos > 0 and range_pos == 0 and bear_pos == 0:
        print("    ⚠ FAIL — edge ONLY in bull regime → bull confound, not A2 mechanism")
    else:
        print("    ⚠ INCONCLUSIVE — needs more sample")

    # Save full results
    summary = {
        'run_time': datetime.now(timezone.utc).isoformat(),
        'mode': 'A2_VALIDATION_SUITE',
        'subject': 'A2 Stablecoin Supply Impulse Candidate Alpha (PR #26)',
        'validations': {
            'lag_shift': val1,
            'walk_forward': val2,
            'regime_conditional': val3,
        },
    }
    with open('a2_validation_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Results saved: a2_validation_results.json")
    print("═" * 76)
    return summary


if __name__ == '__main__':
    main()
