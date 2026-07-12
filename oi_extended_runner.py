"""
B2 — OI Spike + Flat Price (extended history via pagination).

Per /L99_NATIVE_ONLY_MODE Native B2:
  Hypothesis: OI 3d-change > 90th percentile AND |price 24h change| < 1%
              → expect volatility expansion/breakout in 48h
  Mechanism: Leverage builds while price stays flat → cascade probability
             on either directional break

L99 thresholds INTACT post-2026-05-05 corrections:
  IC ≥ 0.04, t ≥ 2.0, PF ≥ 1.3, Q5−Q1 ≥ 60bps net, MC ≥ 80%, Regimes ≥ 2, N ≥ 100
  L99.QUINTILE_MIN now 60.0 (bps) not 0.60 — proper threshold
  quintile_spread fee math now * 10000 * 2 (proper per-leg RT) not * 100 * 2

Hard rules honored:
  - No live deployment
  - No threshold tweaking
  - No factor additions
  - Capital remains 100% USDT
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '.')
from l99_battery import L99, ic, tstat


PAIRS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'XRP_USDT', 'AVAX_USDT']

EARLIEST_TS = 1700000000  # 2023-11-14 UTC (contract_stats endpoint depth limit)
NOW_TS = int(time.time())

FEE_SCENARIOS = {
    'A_VIP0_taker':       0.0025,
    'B_VIP1_GT_discount': 0.0018,
    'C_VIP1_maker_only':  0.0014,
}

# Per-spec thresholds (do NOT modify per "no parameter drift")
OI_LOOKBACK_3D = 72       # 3 days × 24h cadence (in 1h bars)
OI_PERCENTILE_THRESHOLD = 0.90
PRICE_FLAT_THRESHOLD_PCT = 1.0  # |24h price change| < 1%
PRICE_LOOKBACK_24H = 24


# ─────────────────────────────────────────────
# DATA FETCH (paginated)
# ─────────────────────────────────────────────

def http_get(url: str, timeout: int = 25):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_contract_stats_paginated(contract: str) -> List[Dict[str, float]]:
    """Paginate /futures/usdt/contract_stats from EARLIEST_TS to NOW.
    1h interval × limit=2000 per chunk = ~83 days per chunk.
    """
    all_rows: List[Dict[str, float]] = []
    seen_ts = set()
    cursor = EARLIEST_TS
    iterations = 0
    while cursor < NOW_TS and iterations < 30:
        iterations += 1
        url = (
            f"https://api.gateio.ws/api/v4/futures/usdt/contract_stats"
            f"?contract={contract}&interval=1h&from={cursor}&limit=2000"
        )
        try:
            raw = http_get(url)
        except Exception as e:
            print(f"    {contract} OI fetch error from {cursor}: {e}")
            break
        if not raw:
            break
        new_count = 0
        last_ts = cursor
        for x in raw:
            ts = int(x['time'])
            if ts > last_ts:
                last_ts = ts
            if ts in seen_ts:
                continue
            seen_ts.add(ts)
            try:
                all_rows.append({
                    'ts': ts,
                    'oi_usd': float(x.get('open_interest_usd', 0) or 0),
                    'mp': float(x.get('mark_price', 0) or 0),
                })
                new_count += 1
            except (KeyError, ValueError, TypeError):
                continue
        if new_count == 0:
            break
        cursor = last_ts + 3600  # advance +1h
        time.sleep(0.5)
    all_rows.sort(key=lambda r: r['ts'])
    return all_rows


# ─────────────────────────────────────────────
# CORE STATS
# ─────────────────────────────────────────────

def rolling_percentile(series: List[float], lookback: int) -> List[Optional[float]]:
    n = len(series)
    out: List[Optional[float]] = [None] * n
    for i in range(lookback, n):
        w = series[i - lookback:i]
        rank = sum(1 for x in w if x <= series[i])
        out[i] = rank / lookback
    return out


def regime_label(closes: List[float], i: int, lookback: int = 30) -> str:
    if i < lookback or closes[i - lookback] <= 0:
        return 'unknown'
    ret = (closes[i] - closes[i - lookback]) / closes[i - lookback] * 100
    if ret > 10:
        return 'bull'
    if ret < -10:
        return 'bear'
    return 'range'


def quintile_spread_bps(factor: List[Optional[float]],
                       forward: List[Optional[float]],
                       fee_rt: float) -> float:
    """Q5-Q1 spread in BPS NET of fees (post-2026-05-05 corrections)."""
    pairs = [(f, r) for f, r in zip(factor, forward)
             if f is not None and r is not None]
    if len(pairs) < 20:
        return 0.0
    pairs.sort(key=lambda x: x[0])
    nq = max(1, len(pairs) // 5)
    q1 = [p[1] for p in pairs[:nq]]
    q5 = [p[1] for p in pairs[-nq:]]
    return (statistics.mean(q5) - statistics.mean(q1)) * 100 - fee_rt * 10000 * 2


# ─────────────────────────────────────────────
# B2 FACTOR
# ─────────────────────────────────────────────

def b2_extended(stats: List[Dict[str, float]],
                diag: Dict[str, int]) -> Tuple[List[bool], List[Optional[float]],
                                                List[Optional[float]], List[str]]:
    """B2 factor: OI 3d-change > 90th percentile AND |24h price change| < 1%.
    Forward return = absolute |48h price change| (volatility expansion proxy)."""
    diag.setdefault('total', 0)
    diag.setdefault('oi_spike', 0)
    diag.setdefault('flat_price', 0)
    diag.setdefault('both', 0)

    n = len(stats)
    closes = [s['mp'] for s in stats]
    oi_series = [s['oi_usd'] for s in stats]

    # OI 3-day change in percent (3 days = 72 hourly bars)
    oi_3d_change: List[Optional[float]] = [None] * n
    for i in range(OI_LOOKBACK_3D, n):
        if oi_series[i - OI_LOOKBACK_3D] > 0:
            oi_3d_change[i] = (oi_series[i] - oi_series[i - OI_LOOKBACK_3D]) / oi_series[i - OI_LOOKBACK_3D]

    # 24h price change
    price_24h_change: List[Optional[float]] = [None] * n
    for i in range(PRICE_LOOKBACK_24H, n):
        if closes[i - PRICE_LOOKBACK_24H] > 0:
            price_24h_change[i] = (closes[i] - closes[i - PRICE_LOOKBACK_24H]) / closes[i - PRICE_LOOKBACK_24H] * 100

    # Rolling 30-day percentile of OI 3d change (~720 hourly bars)
    pct_lookback = min(720, max(100, n // 4))
    oi_3d_pct = rolling_percentile(
        [v if v is not None else 0 for v in oi_3d_change], pct_lookback
    )

    # Forward returns: 48h absolute (vol expansion proxy)
    fwd_48h: List[Optional[float]] = [None] * n
    for i in range(n - 48):
        if closes[i] > 0:
            fwd_48h[i] = abs((closes[i + 48] - closes[i]) / closes[i] * 100)

    regimes = [regime_label(closes, i) for i in range(n)]

    mask = [False] * n
    factor_vals: List[Optional[float]] = oi_3d_change[:]

    for i in range(n):
        diag['total'] += 1
        if oi_3d_pct[i] is None or price_24h_change[i] is None or oi_3d_change[i] is None:
            continue
        oi_spike_now = oi_3d_pct[i] > OI_PERCENTILE_THRESHOLD
        flat_now = abs(price_24h_change[i]) < PRICE_FLAT_THRESHOLD_PCT
        if oi_spike_now:
            diag['oi_spike'] += 1
        if flat_now:
            diag['flat_price'] += 1
        if oi_spike_now and flat_now:
            diag['both'] += 1
            mask[i] = True

    return mask, factor_vals, fwd_48h, regimes


# ─────────────────────────────────────────────
# BATTERY
# ─────────────────────────────────────────────

def battery(name: str,
            factor_vals: List[Optional[float]],
            forward: List[Optional[float]],
            regimes: List[str],
            mask: List[bool],
            fee_rt: float) -> Dict:
    indices = [i for i in range(len(mask))
               if mask[i] and factor_vals[i] is not None and forward[i] is not None]
    n = len(indices)
    killed_by: List[str] = []

    if n < L99.MIN_OBS:
        return {
            'name': name, 'fee_rt_bps': fee_rt * 10000, 'n': n,
            'passes': False, 'killed_by': [f'N={n} < {L99.MIN_OBS}'],
            'ic': 0, 'tstat': 0, 'pf': 0, 'q_bps': 0, 'mc': 0,
            'regime_count': 0, 'gross_expectancy': 0, 'net_expectancy': 0,
        }

    sig_factor = [factor_vals[i] for i in indices]
    sig_returns = [forward[i] for i in indices]
    gross_exp = statistics.mean(sig_returns)
    net_returns = [r - fee_rt * 100 for r in sig_returns]
    net_exp = statistics.mean(net_returns)

    ic_v = ic(sig_factor, sig_returns)
    ts_v = tstat(net_returns)

    wins = [r for r in net_returns if r > 0]
    losses = [r for r in net_returns if r <= 0]
    if wins and losses:
        pf_v = sum(wins) / abs(sum(losses))
    elif not losses:
        pf_v = 999.0
    else:
        pf_v = 0.0

    qs_v = quintile_spread_bps(factor_vals, forward, fee_rt)

    import random
    rng = random.Random(42)
    mc_wins = 0
    for _ in range(500):
        sample = [rng.choice(net_returns) for _ in range(n)]
        if sum(sample) > 0:
            mc_wins += 1
    mc_v = mc_wins / 500

    sig_regimes = [regimes[i] for i in indices]
    regime_ret: Dict[str, List[float]] = {}
    for r_label, ret in zip(sig_regimes, net_returns):
        regime_ret.setdefault(r_label, []).append(ret)
    reg_count = sum(1 for rets in regime_ret.values()
                    if len(rets) >= 5 and statistics.mean(rets) > 0)

    if abs(ic_v) < L99.IC_MIN:
        killed_by.append(f"IC={ic_v:+.4f}")
    if abs(ts_v) < L99.TSTAT_MIN:
        killed_by.append(f"t={ts_v:+.4f}")
    if pf_v < L99.PF_MIN:
        killed_by.append(f"PF={pf_v:.4f}")
    if qs_v < L99.QUINTILE_MIN:
        killed_by.append(f"Q5-Q1={qs_v:+.2f}")
    if mc_v < L99.MC_STABILITY:
        killed_by.append(f"MC={mc_v*100:.1f}%")
    if reg_count < L99.REGIME_MIN:
        killed_by.append(f"Reg={reg_count}")

    return {
        'name': name, 'fee_rt_bps': fee_rt * 10000, 'n': n,
        'passes': len(killed_by) == 0,
        'killed_by': killed_by,
        'ic': ic_v, 'tstat': ts_v, 'pf': pf_v, 'q_bps': qs_v,
        'mc': mc_v, 'regime_count': reg_count,
        'gross_expectancy': gross_exp, 'net_expectancy': net_exp,
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print()
    print("═" * 74)
    print("  B2 — OI Spike + Flat Price (extended history via pagination)")
    print(f"  Universe: {', '.join(PAIRS)}")
    print(f"  Range: {datetime.fromtimestamp(EARLIEST_TS, timezone.utc).strftime('%Y-%m-%d')} → now")
    print("  L99 thresholds: INTACT (post-2026-05-05 corrections)")
    print("═" * 74)
    print()

    print("  ── Paginated contract_stats fetch (1h cadence) ──")
    stats_data: Dict[str, List[Dict[str, float]]] = {}
    for pair in PAIRS:
        try:
            stats_data[pair] = fetch_contract_stats_paginated(pair)
            t0 = datetime.fromtimestamp(stats_data[pair][0]['ts'], timezone.utc).strftime('%Y-%m-%d') if stats_data[pair] else "n/a"
            t1 = datetime.fromtimestamp(stats_data[pair][-1]['ts'], timezone.utc).strftime('%Y-%m-%d') if stats_data[pair] else "n/a"
            print(f"    {pair}: stats={len(stats_data[pair])}  [{t0} → {t1}]")
        except Exception as e:
            print(f"    {pair}: FAILED — {e}")
            stats_data[pair] = []
    print()

    print("  ── Running B2 battery × 3 fee scenarios per pair + universe ──")
    all_results: Dict[str, Dict] = {}
    diag_master: Dict[str, Dict[str, int]] = {}

    pooled_factor: List[Optional[float]] = []
    pooled_fwd: List[Optional[float]] = []
    pooled_regimes: List[str] = []
    pooled_mask: List[bool] = []

    for pair in PAIRS:
        if not stats_data[pair]:
            continue
        diag = {}
        mask, fac, fwd, reg = b2_extended(stats_data[pair], diag)
        diag_master[f'B2_{pair}'] = diag

        for scenario, fee_rt in FEE_SCENARIOS.items():
            res = battery(f'B2_{pair}_{scenario}', fac, fwd, reg, mask, fee_rt)
            all_results[res['name']] = res

        pooled_factor.extend(fac)
        pooled_fwd.extend(fwd)
        pooled_regimes.extend(reg)
        pooled_mask.extend(mask)

    for scenario, fee_rt in FEE_SCENARIOS.items():
        res = battery(f'B2_UNIVERSE_{scenario}', pooled_factor, pooled_fwd,
                      pooled_regimes, pooled_mask, fee_rt)
        all_results[res['name']] = res

    print()
    print(f"  {'Factor':<40} {'N':>6} {'IC':>8} {'t':>8} {'PF':>6} {'Q-bps':>9} {'MC%':>5} {'Reg':>4}  Status")
    print("  " + "─" * 100)
    passing = []
    insufficient = []
    failing = []
    for name, r in all_results.items():
        st = "✅ PASS" if r['passes'] else "❌"
        n_part = ('N<100' if any('< 100' in k for k in r['killed_by']) else 'KILL')
        status_str = f"{st} {n_part}" if not r['passes'] else st
        print(f"  {name:<40} {r['n']:>6} {r['ic']:>+8.4f} {r['tstat']:>+8.3f} "
              f"{r['pf']:>6.2f} {r['q_bps']:>+9.2f} {r['mc']*100:>5.1f} "
              f"{r['regime_count']:>4}  {status_str}")
        if r['passes']:
            passing.append(name)
        elif any('< 100' in k for k in r['killed_by']):
            insufficient.append(name)
        else:
            failing.append(name)

    print()
    print(f"  Total combinations:  {len(all_results)}")
    print(f"  ✅ Passing:           {len(passing)}")
    print(f"  🟡 N<100:             {len(insufficient)}")
    print(f"  🛑 Killed after N:   {len(failing)}")

    summary = {
        'run_time': datetime.now(timezone.utc).isoformat(),
        'mode': 'B2_OI_SPIKE_EXTENDED',
        'pagination_range': f"{datetime.fromtimestamp(EARLIEST_TS, timezone.utc).strftime('%Y-%m-%d')} → now",
        'pairs': PAIRS,
        'L99_thresholds': {
            'IC_MIN': L99.IC_MIN, 'TSTAT_MIN': L99.TSTAT_MIN,
            'PF_MIN': L99.PF_MIN, 'QUINTILE_MIN_bps': L99.QUINTILE_MIN,
            'MC_STABILITY': L99.MC_STABILITY, 'REGIME_MIN': L99.REGIME_MIN,
            'MIN_OBS': L99.MIN_OBS,
        },
        'fee_scenarios': {k: f"{v * 10000} bps RT" for k, v in FEE_SCENARIOS.items()},
        'spec_thresholds': {
            'OI_LOOKBACK_3D': OI_LOOKBACK_3D,
            'OI_PERCENTILE_THRESHOLD': OI_PERCENTILE_THRESHOLD,
            'PRICE_FLAT_THRESHOLD_PCT': PRICE_FLAT_THRESHOLD_PCT,
        },
        'signal_funnels': diag_master,
        'stats_records_per_pair': {p: len(stats_data.get(p, [])) for p in PAIRS},
        'passing_count': len(passing),
        'insufficient_count': len(insufficient),
        'failing_count': len(failing),
        'results': all_results,
    }
    with open('b2_extended_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print()
    print(f"  Results: b2_extended_results.json")
    print("═" * 74)
    return summary


if __name__ == '__main__':
    main()
