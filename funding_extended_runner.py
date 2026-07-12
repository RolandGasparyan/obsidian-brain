"""
B1 — Funding Extreme Mean Reversion (extended history via pagination).

Per /L99_NATIVE_ONLY_MODE — exchange-native only. Previous run hit Gate.io's
default 90-record cap on funding_rate endpoint (~30 days). This runner uses
the `from`/`to` parameter trick to paginate and pull ~3 years of funding
history per pair, sufficient to clear N≥100 even with strict |z|>2.5 threshold.

L99 thresholds INTACT (no parameter drift):
  IC ≥ 0.04, t ≥ 2.0, PF ≥ 1.3, Q5−Q1 ≥ 60bps, MC ≥ 80%, Regimes ≥ 2, N ≥ 100

Spec:
  Hypothesis: Funding extreme (|z|>2.5) → 24h mean reversion (opposite direction)
  Mechanism:  Longs paying high funding = crowded long → short squeeze potential
              and inverse for shorts; structural reflexive flow
  Failure:    IC sign flip OOS, Q5−Q1 < 60bps after fees, regime fragility

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

# Pagination depth: ~3 years = ~94M seconds
EARLIEST_TS = 1672531200  # 2023-01-01 UTC
NOW_TS = int(time.time())
CHUNK_SIZE_SEC = 333 * 86400  # 333 days per chunk (limit=1000 × 8h funding)

FEE_SCENARIOS = {
    'A_VIP0_taker':       0.0025,
    'B_VIP1_GT_discount': 0.0018,
    'C_VIP1_maker_only':  0.0014,
}

# Per spec hypothesis: |z|>2.5 → expect mean reversion in 24h
Z_THRESHOLD = 2.5
HORIZON_BARS_4H = 6  # 24h forward at 4h cadence


# ─────────────────────────────────────────────
# DATA FETCH (paginated)
# ─────────────────────────────────────────────

def http_get(url: str, timeout: int = 25):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_funding_paginated(contract: str) -> List[Dict[str, float]]:
    """Paginate funding_rate from EARLIEST_TS to NOW_TS in 333-day chunks."""
    all_rows: List[Dict[str, float]] = []
    seen_ts = set()
    cursor = EARLIEST_TS
    while cursor < NOW_TS:
        end = min(cursor + CHUNK_SIZE_SEC, NOW_TS)
        url = (
            f"https://api.gateio.ws/api/v4/futures/usdt/funding_rate"
            f"?contract={contract}&from={cursor}&to={end}&limit=1000"
        )
        try:
            raw = http_get(url)
        except Exception as e:
            print(f"    {contract} fetch error in {cursor}-{end}: {e}")
            cursor = end
            continue
        new_count = 0
        for r in raw:
            ts = int(r['t'])
            if ts in seen_ts:
                continue
            seen_ts.add(ts)
            all_rows.append({'ts': ts, 'r': float(r['r'])})
            new_count += 1
        # Rate limit: ~10/min default; pace conservatively
        time.sleep(0.5)
        cursor = end
    all_rows.sort(key=lambda r: r['ts'])
    return all_rows


def fetch_futures_4h(contract: str, limit: int = 1000) -> List[Dict[str, float]]:
    """Single-call fetch (last `limit` bars). Use fetch_futures_4h_paginated
    for full historical span matching funding history."""
    raw = http_get(
        f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks"
        f"?contract={contract}&interval=4h&limit={limit}"
    )
    bars = []
    for r in raw:
        bars.append({
            'ts': int(r['t']),
            'o': float(r['o']), 'h': float(r['h']), 'l': float(r['l']),
            'c': float(r['c']), 'v': float(r['v']),
        })
    bars.sort(key=lambda b: b['ts'])
    return bars


def fetch_futures_4h_paginated(contract: str) -> List[Dict[str, float]]:
    """Paginate 4h futures candlesticks from EARLIEST_TS to NOW using
    `from=<ts>&limit=1000` (returns 1000 bars going forward from ts).
    Iterates until reaching NOW_TS. Required to match funding history span.

    Fix 2026-05-05: futures candlestick endpoint does NOT support from/to
    pair like funding does — returns HTTP 400. Must use from=<ts>&limit=1000
    and advance cursor by last-bar-ts + 1 each iteration.
    """
    all_bars: List[Dict[str, float]] = []
    seen_ts = set()
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
            print(f"    {contract} 4h fetch error from {cursor}: {e}")
            break
        if not raw:
            break
        new_count = 0
        last_ts = cursor
        for r in raw:
            ts = int(r['t'])
            if ts > last_ts:
                last_ts = ts
            if ts in seen_ts:
                continue
            seen_ts.add(ts)
            all_bars.append({
                'ts': ts,
                'o': float(r['o']), 'h': float(r['h']), 'l': float(r['l']),
                'c': float(r['c']), 'v': float(r['v']),
            })
            new_count += 1
        if new_count == 0:
            break
        # Advance cursor past last received bar
        cursor = last_ts + 4 * 3600  # +4h to next bar
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


def quintile_spread(factor: List[Optional[float]],
                    forward: List[Optional[float]],
                    fee_rt: float) -> float:
    """Q5-Q1 spread in BPS NET of fees.

    Per-leg fee accounting (fix 2026-05-05 per council Model QA M3):
    A Q5−Q1 trade = LONG Q5 + SHORT Q1 = 2 separate trades, each pays
    its own round-trip fee. fee_rt is decimal fraction (e.g., 0.0025).
    Convert to bps via × 10000, then × 2 for two-leg spread.

    Previous bug (now fixed): fee_rt * 100 * 2 = 0.5 (interpreted as
    0.5 bps), 100× too small — fees were effectively not deducted.
    """
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
# B1 FACTOR (extended history)
# ─────────────────────────────────────────────

def b1_extended(funding: List[Dict[str, float]],
                bars: List[Dict[str, float]],
                diag: Dict[str, int]) -> Tuple[List[bool], List[Optional[float]],
                                                List[Optional[float]], List[str]]:
    """B1 factor on extended funding history.

    Aligns each 4h bar to its preceding funding settlement (8h cadence).
    Computes rolling 30-record (10-day) z-score. Signal = |z| > 2.5.
    Forward return = -bar's 24h forward return when z>0 (long-pay, expect down)
                   or +bar's 24h forward return when z<0 (short-pay, expect up)
    """
    diag.setdefault('total_bars', 0)
    diag.setdefault('aligned_bars', 0)
    diag.setdefault('extreme_z', 0)

    f_series = [f['r'] for f in funding]
    z_series = rolling_zscore(f_series, 30)
    z_by_ts = {funding[i]['ts']: z_series[i] for i in range(len(funding))
               if z_series[i] is not None}
    sorted_funding_ts = sorted(z_by_ts.keys())

    n = len(bars)
    mask = [False] * n
    factor: List[Optional[float]] = [None] * n
    closes = [b['c'] for b in bars]
    fwd_24h: List[Optional[float]] = [None] * n
    for i in range(n - HORIZON_BARS_4H):
        if closes[i] > 0:
            fwd_24h[i] = (closes[i + HORIZON_BARS_4H] - closes[i]) / closes[i] * 100
    regimes = [regime_label(closes, i) for i in range(n)]

    # Binary-search latest funding settlement ≤ bar_ts
    import bisect
    for i in range(n):
        diag['total_bars'] += 1
        bar_ts = bars[i]['ts']
        idx = bisect.bisect_right(sorted_funding_ts, bar_ts) - 1
        if idx < 0:
            continue
        z = z_by_ts[sorted_funding_ts[idx]]
        factor[i] = z
        diag['aligned_bars'] += 1
        if abs(z) > Z_THRESHOLD:
            diag['extreme_z'] += 1
            mask[i] = True

    # Direction: high z (longs paying) → expect down → short_return = -fwd
    fwd_directional: List[Optional[float]] = [None] * n
    for i in range(n):
        if fwd_24h[i] is None or factor[i] is None:
            continue
        if factor[i] > 0:
            fwd_directional[i] = -fwd_24h[i]
        else:
            fwd_directional[i] = fwd_24h[i]

    return mask, factor, fwd_directional, regimes


# ─────────────────────────────────────────────
# BATTERY (parameterized by fee)
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

    qs_v = quintile_spread(factor_vals, forward, fee_rt)

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
    print("  B1 — Funding Extreme Mean Reversion (extended history via pagination)")
    print(f"  Universe: {', '.join(PAIRS)}")
    print(f"  History range: {datetime.fromtimestamp(EARLIEST_TS, timezone.utc).strftime('%Y-%m-%d')} → now")
    print("  L99 thresholds: INTACT (no parameter drift)")
    print("═" * 74)
    print()

    print("  ── Paginated funding + paginated price fetch (3-year span match) ──")
    funding_data: Dict[str, List[Dict[str, float]]] = {}
    perp_4h: Dict[str, List[Dict[str, float]]] = {}
    for pair in PAIRS:
        try:
            funding_data[pair] = fetch_funding_paginated(pair)
            perp_4h[pair] = fetch_futures_4h_paginated(pair)  # H1 fix per council 2026-05-05
            t0 = datetime.fromtimestamp(funding_data[pair][0]['ts'], timezone.utc).strftime('%Y-%m-%d') if funding_data[pair] else "n/a"
            t1 = datetime.fromtimestamp(funding_data[pair][-1]['ts'], timezone.utc).strftime('%Y-%m-%d') if funding_data[pair] else "n/a"
            print(f"    {pair}: funding={len(funding_data[pair])}  perp4h={len(perp_4h[pair])}  [{t0} → {t1}]")
        except Exception as e:
            print(f"    {pair}: FAILED — {e}")
            funding_data[pair] = []
            perp_4h[pair] = []
    print()

    # Run B1 per-pair + universe-aggregated
    print("  ── Running B1 battery × 3 fee scenarios per pair ──")
    all_results: Dict[str, Dict] = {}
    diag_master: Dict[str, Dict[str, int]] = {}

    pooled_factor: List[Optional[float]] = []
    pooled_fwd: List[Optional[float]] = []
    pooled_regimes: List[str] = []
    pooled_mask: List[bool] = []

    for pair in PAIRS:
        if not funding_data[pair] or not perp_4h[pair]:
            continue
        diag = {}
        mask, fac, fwd, reg = b1_extended(funding_data[pair], perp_4h[pair], diag)
        diag_master[f'B1_{pair}'] = diag

        for scenario, fee_rt in FEE_SCENARIOS.items():
            res = battery(f'B1_{pair}_{scenario}', fac, fwd, reg, mask, fee_rt)
            all_results[res['name']] = res

        pooled_factor.extend(fac)
        pooled_fwd.extend(fwd)
        pooled_regimes.extend(reg)
        pooled_mask.extend(mask)

    # Universe-aggregated
    print("  ── B1 universe-aggregated (cross-sectional pooling) ──")
    for scenario, fee_rt in FEE_SCENARIOS.items():
        res = battery(f'B1_UNIVERSE_{scenario}', pooled_factor, pooled_fwd,
                      pooled_regimes, pooled_mask, fee_rt)
        all_results[res['name']] = res

    # Print
    print()
    print(f"  {'Factor':<40} {'N':>6} {'IC':>8} {'t':>8} {'PF':>6} {'Q-bps':>8} {'MC%':>5} {'Reg':>4}  Status")
    print("  " + "─" * 100)
    passing = []
    insufficient = []
    failing = []
    for name, r in all_results.items():
        st = "✅ PASS" if r['passes'] else "❌"
        n_part = ('N<100' if any('< 100' in k for k in r['killed_by']) else 'KILL')
        status_str = f"{st} {n_part}" if not r['passes'] else st
        print(f"  {name:<40} {r['n']:>6} {r['ic']:>+8.4f} {r['tstat']:>+8.3f} "
              f"{r['pf']:>6.2f} {r['q_bps']:>+8.2f} {r['mc']*100:>5.1f} "
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
        'mode': 'B1_FUNDING_EXTREME_EXTENDED',
        'pagination_range': f"{datetime.fromtimestamp(EARLIEST_TS, timezone.utc).strftime('%Y-%m-%d')} → now",
        'pairs': PAIRS,
        'L99_thresholds': {
            'IC_MIN': L99.IC_MIN, 'TSTAT_MIN': L99.TSTAT_MIN,
            'PF_MIN': L99.PF_MIN, 'QUINTILE_MIN_bps': L99.QUINTILE_MIN,
            'MC_STABILITY': L99.MC_STABILITY, 'REGIME_MIN': L99.REGIME_MIN,
            'MIN_OBS': L99.MIN_OBS,
        },
        'fee_scenarios': {k: f"{v * 10000} bps RT" for k, v in FEE_SCENARIOS.items()},
        'z_threshold': Z_THRESHOLD,
        'horizon': '24h',
        'signal_funnels': diag_master,
        'funding_records_per_pair': {p: len(funding_data.get(p, [])) for p in PAIRS},
        'passing_count': len(passing),
        'insufficient_count': len(insufficient),
        'failing_count': len(failing),
        'results': all_results,
    }
    with open('b1_extended_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print()
    print(f"  Results: b1_extended_results.json")
    print("═" * 74)
    return summary


if __name__ == '__main__':
    main()
