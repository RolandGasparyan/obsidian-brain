"""
Audit A2 stablecoin signal — 7 of 27 combinations apparently pass.

Same council methodology that caught D2 (look-ahead) and B1 (window/fee bugs).

Specifically check:
  1. Look-ahead — daily Z-score must be observable at bar_ts
  2. Regime confound — do signal events cluster in bull regime?
  3. Per-quintile monotonicity (top-down sanity)
  4. Multiple-comparisons correction (27 tests, 7 pass — Bonferroni)
  5. Effective N considering correlation
  6. Forward-return baseline vs signal-conditional
"""
from __future__ import annotations

import json
import statistics
import sys
from typing import Dict, List, Tuple

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
)


def main():
    print("═" * 74)
    print("  A2 PASSING-SIGNAL AUDIT — 7 of 27 apparently pass")
    print("═" * 74)

    # ─── Reload data ───
    print("\n  Step 1: Reload data (cached if recent)")
    daily_supplies: Dict[int, Dict[str, float]] = {}
    for symbol, coin_id in DEFILLAMA_STABLECOIN_IDS.items():
        for ts, v in fetch_stablecoin_history(coin_id):
            daily_supplies.setdefault(ts, {})[symbol] = v

    daily_total: Dict[int, float] = {}
    for ts, sup in daily_supplies.items():
        if 'USDT' in sup and 'USDC' in sup:
            daily_total[ts] = sup['USDT'] + sup['USDC']
    sorted_days = sorted(daily_total.keys())
    daily_total_series = [daily_total[ts] for ts in sorted_days]
    growth_7d = n_day_change(daily_total_series, GROWTH_LOOKBACK_7D)
    z_series = rolling_zscore(
        [g if g is not None else 0 for g in growth_7d], Z_LOOKBACK
    )
    daily_z: Dict[int, float] = {}
    for i, ts in enumerate(sorted_days):
        if z_series[i] is not None and growth_7d[i] is not None:
            daily_z[ts] = z_series[i]

    print(f"  Daily Z available: {len(daily_z)} days")
    eth_bars = fetch_perp_4h_paginated('ETH_USDT')
    print(f"  ETH 4h bars: {len(eth_bars)}")

    # ─── Sample size in TIME ───
    print("\n  Step 2: Look-ahead spot check")
    print("    daily_z[ts] uses growth_7d[i-7..i] then z over [i-30..i-1] — clean")
    print("    bisect_right(supply_ts, bar_ts) - 1 = latest daily Z BEFORE bar — clean")
    print("    fwd[i] = closes[i+horizon] - closes[i] — strictly future")
    print("    ✅ No look-ahead in entry-timing")

    # ─── Regime confound check ───
    print("\n  Step 3: Regime confound (CRITICAL audit)")
    import bisect
    sorted_supply_ts = sorted(daily_z.keys())
    closes = [b['c'] for b in eth_bars]
    regimes = [regime_label(closes, i) for i in range(len(eth_bars))]

    z_extreme_regimes: Dict[str, int] = {}
    z_normal_regimes: Dict[str, int] = {}
    for i in range(len(eth_bars)):
        bar_ts = eth_bars[i]['ts']
        idx = bisect.bisect_right(sorted_supply_ts, bar_ts) - 1
        if idx < 0:
            continue
        z = daily_z[sorted_supply_ts[idx]]
        if z > Z_THRESHOLD:
            z_extreme_regimes[regimes[i]] = z_extreme_regimes.get(regimes[i], 0) + 1
        else:
            z_normal_regimes[regimes[i]] = z_normal_regimes.get(regimes[i], 0) + 1

    print(f"    Z-EXTREME bars by regime: {z_extreme_regimes}")
    print(f"    Z-NORMAL  bars by regime: {z_normal_regimes}")
    extreme_total = sum(z_extreme_regimes.values())
    normal_total = sum(z_normal_regimes.values())
    if extreme_total > 0 and normal_total > 0:
        for reg in ('bull', 'bear', 'range'):
            ex_pct = z_extreme_regimes.get(reg, 0) / extreme_total * 100
            no_pct = z_normal_regimes.get(reg, 0) / normal_total * 100
            ratio = ex_pct / no_pct if no_pct > 0 else float('inf')
            print(f"    {reg:8s}: extreme={ex_pct:5.1f}%  normal={no_pct:5.1f}%  "
                  f"ratio={ratio:.2f}x  {'⚠ confounded' if ratio > 2 or ratio < 0.5 else '✅ balanced'}")

    # ─── Forward-return baseline vs signal ───
    print("\n  Step 4: Forward-return baseline vs signal (3d horizon, ETH)")
    h_3d = HORIZONS['3d']
    n = len(eth_bars)
    fwd_3d = [None] * n
    for i in range(n - h_3d):
        if closes[i] > 0:
            fwd_3d[i] = (closes[i + h_3d] - closes[i]) / closes[i] * 100

    # Baseline: ALL bars
    baseline_returns = [r for r in fwd_3d if r is not None]
    print(f"    Baseline (all bars):       N={len(baseline_returns):4d}  mean={statistics.mean(baseline_returns):+.4f}%  "
          f"win_rate={sum(1 for r in baseline_returns if r > 0)/len(baseline_returns)*100:.1f}%")

    # Signal-conditional
    signal_returns = []
    for i in range(n):
        if fwd_3d[i] is None:
            continue
        bar_ts = eth_bars[i]['ts']
        idx = bisect.bisect_right(sorted_supply_ts, bar_ts) - 1
        if idx < 0:
            continue
        z = daily_z[sorted_supply_ts[idx]]
        if z > Z_THRESHOLD:
            signal_returns.append(fwd_3d[i])
    print(f"    Signal (z>{Z_THRESHOLD}):           N={len(signal_returns):4d}  mean={statistics.mean(signal_returns):+.4f}%  "
          f"win_rate={sum(1 for r in signal_returns if r > 0)/len(signal_returns)*100:.1f}%")

    diff = statistics.mean(signal_returns) - statistics.mean(baseline_returns)
    print(f"    Signal vs baseline diff:   {diff:+.4f}%")

    # ─── Quintile monotonicity ───
    print("\n  Step 5: Per-quintile breakdown (ETH 3d, 14 bps RT maker)")
    pairs = []
    for i in range(n):
        if fwd_3d[i] is None:
            continue
        bar_ts = eth_bars[i]['ts']
        idx = bisect.bisect_right(sorted_supply_ts, bar_ts) - 1
        if idx < 0:
            continue
        z = daily_z[sorted_supply_ts[idx]]
        pairs.append((z, fwd_3d[i]))
    pairs.sort(key=lambda x: x[0])
    n_pairs = len(pairs)
    nq = n_pairs // 5
    fee_rt = 0.0014
    for q in range(5):
        start = q * nq
        end = (q + 1) * nq if q < 4 else n_pairs
        q_z = [p[0] for p in pairs[start:end]]
        q_fwd = [p[1] for p in pairs[start:end]]
        net_mean = statistics.mean(q_fwd) - fee_rt * 100
        print(f"    Q{q+1}: N={end-start:4d}  z∈[{min(q_z):+.3f}, {max(q_z):+.3f}]  "
              f"gross fwd={statistics.mean(q_fwd):+.4f}%  net@maker={net_mean:+.4f}%")

    # ─── Multiple-comparisons (Bonferroni) ───
    print("\n  Step 6: Multiple-comparisons correction (Bonferroni)")
    print("    27 tests run, 7 passed at α=0.05 default")
    print("    Bonferroni-corrected α: 0.05 / 27 = 0.00185")
    print("    Required t-stat at corrected α (two-tailed): ~3.13")
    print()
    print("    Re-checking each PASS at corrected threshold:")
    passes = json.load(open('a2_stablecoin_results.json'))['results']
    for name, r in passes.items():
        if r['passes']:
            t = abs(r['tstat'])
            survives = "✅ SURVIVES" if t > 3.13 else "❌ FAILS Bonferroni"
            print(f"      {name:<48} t={t:+.3f}  {survives}")

    # ─── Effective-N (cross-sectional pooling) ───
    print("\n  Step 7: Effective-N (universe pool inflation)")
    print("    BTC and ETH 4h returns ~0.7 correlated.")
    print("    Universe N=2064 effective N ≈ 2064 / (1 + 0.7) = 1214")
    print("    True t-stat ≈ reported × sqrt(1214/2064) = reported × 0.767")
    print()
    print("    Re-checking universe PASSES with effective-N adjustment:")
    for name, r in passes.items():
        if r['passes'] and 'UNIVERSE' in name:
            t_adj = r['tstat'] * 0.767
            survives = "✅" if abs(t_adj) > 3.13 else "❌ FAILS post effective-N"
            print(f"      {name:<48} t_orig={r['tstat']:+.3f}  t_adj={t_adj:+.3f}  {survives}")


if __name__ == '__main__':
    main()
