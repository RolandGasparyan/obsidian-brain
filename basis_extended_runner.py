"""
B3 — Basis Compression (extended history via pagination).

Per /L99_NATIVE_ONLY_MODE Native B3:
  Hypothesis: Perp - Spot basis collapses (negative z-score) → expect expansion (vol).
  Mechanism: Compressed basis = arb closure → next move likely directional.
  Forward signal: |48h price change| (vol expansion proxy)

L99 thresholds INTACT post-2026-05-05 corrections.

Hard rules honored:
  - No live deployment
  - No threshold tweaking
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

EARLIEST_TS = 1672531200  # 2023-01-01 UTC (spot+perp candles support full range per B1 paginator)
NOW_TS = int(time.time())

FEE_SCENARIOS = {
    'A_VIP0_taker':       0.0025,
    'B_VIP1_GT_discount': 0.0018,
    'C_VIP1_maker_only':  0.0014,
}

BASIS_LOOKBACK = 30
BASIS_Z_THRESHOLD = -1.5  # compression = below normal
HORIZON_BARS_4H = 12  # 48h forward at 4h cadence (vol proxy)


# ─────────────────────────────────────────────
# DATA FETCH (paginated)
# ─────────────────────────────────────────────

def http_get(url: str, timeout: int = 25):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_4h_paginated_spot(pair: str) -> List[Dict[str, float]]:
    """Paginate spot 4h candles. Spot endpoint: /spot/candlesticks."""
    all_bars: List[Dict[str, float]] = []
    seen = set()
    cursor = EARLIEST_TS
    iterations = 0
    while cursor < NOW_TS and iterations < 30:
        iterations += 1
        url = (
            f"https://api.gateio.ws/api/v4/spot/candlesticks"
            f"?currency_pair={pair}&interval=4h&from={cursor}&limit=1000"
        )
        try:
            raw = http_get(url)
        except Exception as e:
            print(f"    {pair} spot 4h err from {cursor}: {e}")
            break
        if not raw:
            break
        new_count = 0
        last_ts = cursor
        for r in raw:
            if r[7] != 'true':
                continue
            ts = int(r[0])
            if ts > last_ts:
                last_ts = ts
            if ts in seen:
                continue
            seen.add(ts)
            all_bars.append({
                'ts': ts,
                'o': float(r[5]), 'h': float(r[3]), 'l': float(r[4]),
                'c': float(r[2]), 'v': float(r[6]),
            })
            new_count += 1
        if new_count == 0:
            break
        cursor = last_ts + 4 * 3600
        time.sleep(0.5)
    all_bars.sort(key=lambda b: b['ts'])
    return all_bars


def fetch_4h_paginated_perp(contract: str) -> List[Dict[str, float]]:
    """Paginate perp 4h candles. Futures endpoint: /futures/usdt/candlesticks."""
    all_bars: List[Dict[str, float]] = []
    seen = set()
    cursor = EARLIEST_TS
    iterations = 0
    while cursor < NOW_TS and iterations < 30:
        iterations += 1
        url = (
            f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks"
            f"?contract={contract}&interval=4h&from={cursor}&limit=1000"
        )
        try:
            raw = http_get(url)
        except Exception as e:
            print(f"    {contract} perp 4h err from {cursor}: {e}")
            break
        if not raw:
            break
        new_count = 0
        last_ts = cursor
        for r in raw:
            ts = int(r['t'])
            if ts > last_ts:
                last_ts = ts
            if ts in seen:
                continue
            seen.add(ts)
            all_bars.append({
                'ts': ts,
                'o': float(r['o']), 'h': float(r['h']), 'l': float(r['l']),
                'c': float(r['c']), 'v': float(r['v']),
            })
            new_count += 1
        if new_count == 0:
            break
        cursor = last_ts + 4 * 3600
        time.sleep(0.5)
    all_bars.sort(key=lambda b: b['ts'])
    return all_bars


# ─────────────────────────────────────────────
# CORE STATS
# ─────────────────────────────────────────────

def rolling_zscore(series: List[float], lookback: int) -> List[Optional[float]]:
    n = len(series)
    out: List[Optional[float]] = [None] * n
    for i in range(lookback, n):
        w = series[i - lookback:i]
        mu = sum(w) / lookback
        var = sum((x - mu) ** 2 for x in w) / lookback
        sd = math.sqrt(var) if var > 0 else 1e-9
        out[i] = (series[i] - mu) / sd if sd > 0 else 0.0
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
# B3 FACTOR
# ─────────────────────────────────────────────

def b3_extended(spot_bars: List[Dict[str, float]],
                perp_bars: List[Dict[str, float]],
                diag: Dict[str, int]) -> Tuple[List[bool], List[Optional[float]],
                                                List[Optional[float]], List[str]]:
    """B3 factor: basis (perp - spot) Z-score below threshold = compression.
    Forward signal = |48h price change| (vol expansion proxy)."""
    diag.setdefault('total', 0)
    diag.setdefault('compressed', 0)

    spot_by_ts = {b['ts']: b for b in spot_bars}
    aligned = [(b, spot_by_ts[b['ts']]) for b in perp_bars if b['ts'] in spot_by_ts]
    n = len(aligned)
    perps = [a[0] for a in aligned]
    spots = [a[1] for a in aligned]

    basis_bps = []
    for p, s in aligned:
        if s['c'] > 0:
            basis_bps.append((p['c'] - s['c']) / s['c'] * 10000)
        else:
            basis_bps.append(0)

    z = rolling_zscore(basis_bps, BASIS_LOOKBACK)
    closes = [p['c'] for p in perps]

    fwd_abs: List[Optional[float]] = [None] * n
    for i in range(n - HORIZON_BARS_4H):
        if closes[i] > 0:
            fwd_abs[i] = abs((closes[i + HORIZON_BARS_4H] - closes[i]) / closes[i] * 100)

    regimes = [regime_label(closes, i) for i in range(n)]

    mask = [False] * n
    for i in range(n):
        diag['total'] += 1
        if z[i] is None:
            continue
        if z[i] < BASIS_Z_THRESHOLD:
            diag['compressed'] += 1
            mask[i] = True

    return mask, z, fwd_abs, regimes


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
    print("  B3 — Basis Compression (extended history via pagination)")
    print(f"  Universe: {', '.join(PAIRS)}")
    print(f"  Range: {datetime.fromtimestamp(EARLIEST_TS, timezone.utc).strftime('%Y-%m-%d')} → now")
    print("  L99 thresholds: INTACT (post-2026-05-05 corrections)")
    print("═" * 74)
    print()

    print("  ── Paginated spot + perp 4h (parallel per pair) ──")
    spot_data: Dict[str, List[Dict[str, float]]] = {}
    perp_data: Dict[str, List[Dict[str, float]]] = {}
    for pair in PAIRS:
        try:
            spot_data[pair] = fetch_4h_paginated_spot(pair)
            perp_data[pair] = fetch_4h_paginated_perp(pair)
            print(f"    {pair}: spot4h={len(spot_data[pair])}  perp4h={len(perp_data[pair])}")
        except Exception as e:
            print(f"    {pair}: FAILED — {e}")
            spot_data[pair] = []
            perp_data[pair] = []
    print()

    print("  ── Running B3 battery × 3 fee scenarios per pair + universe ──")
    all_results: Dict[str, Dict] = {}
    diag_master: Dict[str, Dict[str, int]] = {}

    pooled_factor: List[Optional[float]] = []
    pooled_fwd: List[Optional[float]] = []
    pooled_regimes: List[str] = []
    pooled_mask: List[bool] = []

    for pair in PAIRS:
        if not spot_data[pair] or not perp_data[pair]:
            continue
        diag = {}
        mask, fac, fwd, reg = b3_extended(spot_data[pair], perp_data[pair], diag)
        diag_master[f'B3_{pair}'] = diag

        for scenario, fee_rt in FEE_SCENARIOS.items():
            res = battery(f'B3_{pair}_{scenario}', fac, fwd, reg, mask, fee_rt)
            all_results[res['name']] = res

        pooled_factor.extend(fac)
        pooled_fwd.extend(fwd)
        pooled_regimes.extend(reg)
        pooled_mask.extend(mask)

    for scenario, fee_rt in FEE_SCENARIOS.items():
        res = battery(f'B3_UNIVERSE_{scenario}', pooled_factor, pooled_fwd,
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
        'mode': 'B3_BASIS_COMPRESSION_EXTENDED',
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
            'BASIS_LOOKBACK': BASIS_LOOKBACK,
            'BASIS_Z_THRESHOLD': BASIS_Z_THRESHOLD,
        },
        'signal_funnels': diag_master,
        'spot_bars_per_pair': {p: len(spot_data.get(p, [])) for p in PAIRS},
        'perp_bars_per_pair': {p: len(perp_data.get(p, [])) for p in PAIRS},
        'passing_count': len(passing),
        'insufficient_count': len(insufficient),
        'failing_count': len(failing),
        'results': all_results,
    }
    with open('b3_extended_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print()
    print(f"  Results: b3_extended_results.json")
    print("═" * 74)
    return summary


if __name__ == '__main__':
    main()
