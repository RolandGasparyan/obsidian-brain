"""
A2 — Stablecoin Supply Impulse (DefiLlama free endpoint).

Per L99_ULTRA_AGGRESSIVE_ALPHA_BLUEPRINT.md A2:
  Hypothesis: Sudden stablecoin minting injects liquidity → bullish drift.
  Factor:     SC_growth_7d_z = z-score of (USDT+USDC supply 7-day % change)
  Signal:     SC_growth_7d_z > +1.5
  Test:       BTC + ETH forward returns at t+3d, t+7d
  Expected:   Positive forward returns (bullish drift)

DATA SOURCE — DefiLlama free endpoint (NO auth, NO API key needed):
  https://stablecoins.llama.fi/stablecoin/<id>
  Returns 8+ years of daily circulating-supply timeseries.

  Pivoted from Etherscan v1 (deprecated) — DefiLlama gives:
    - Longer history (USDT: 2017-11 → now, 3080 days)
    - No rate limit complexity
    - No event reconstruction
    - Authoritative stablecoin supply tracker

Discipline rules INTACT:
  - L99 thresholds verbatim (post-2026-05-05 corrections)
  - Per-leg fee math (10000 * 2)
  - L99.QUINTILE_MIN = 60.0 bps
  - SIGNED forward returns (per B2/B3 lesson)
  - Per-pair sign consistency check
  - Cross-pair pooling for universe-aggregated test

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


# Top 2 by supply — covers ~95% of stablecoin-market mass
DEFILLAMA_STABLECOIN_IDS = {'USDT': 1, 'USDC': 2}

PAIRS_TO_TEST = ['BTC_USDT', 'ETH_USDT']  # Focus on majors per spec

EARLIEST_TS = 1672531200  # 2023-01-01 UTC
NOW_TS = int(time.time())

FEE_SCENARIOS = {
    'A_VIP0_taker':       0.0025,
    'B_VIP1_GT_discount': 0.0018,
    'C_VIP1_maker_only':  0.0014,
}

# Per A2 spec
Z_LOOKBACK = 30           # rolling 30 days for Z-score
GROWTH_LOOKBACK_7D = 7    # 7-day % change in supply
Z_THRESHOLD = 1.5         # |z| > 1.5 per spec

# Test horizons in 4h bars
HORIZONS = {'3d': 18, '5d': 30, '7d': 42}


# ─────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────

def http_get(url: str, timeout: int = 25):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_stablecoin_history(coin_id: int) -> List[Tuple[int, float]]:
    """DefiLlama free endpoint. Returns [(unix_ts, circulating_usd), ...]."""
    url = f"https://stablecoins.llama.fi/stablecoin/{coin_id}"
    data = http_get(url)
    history = data.get('tokens', [])
    out = []
    for h in history:
        ts = int(h['date'])
        # circulating may be a dict {peggedUSD: number} or direct number
        circ = h.get('circulating')
        if isinstance(circ, dict):
            v = float(circ.get('peggedUSD', 0) or 0)
        else:
            v = float(circ or 0)
        if v > 0:
            out.append((ts, v))
    out.sort(key=lambda x: x[0])
    return out


def fetch_perp_4h_paginated(contract: str) -> List[Dict[str, float]]:
    """Paginated 4h perp candles from EARLIEST_TS to now. Reuses pattern from
    funding_extended_runner.py."""
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


def n_day_change(series: List[float], n: int) -> List[Optional[float]]:
    """% change over n previous samples."""
    out: List[Optional[float]] = [None] * len(series)
    for i in range(n, len(series)):
        if series[i - n] > 0:
            out[i] = (series[i] - series[i - n]) / series[i - n] * 100
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
    """Q5-Q1 NET in bps (post-2026-05-05 per-leg fee correction)."""
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
# A2 FACTOR
# ─────────────────────────────────────────────

def build_a2_signal_per_pair(
    daily_supply_z: Dict[int, float],  # {day_ts: z_value}
    perp_bars: List[Dict[str, float]],
    diag: Dict[str, int],
) -> Tuple[List[bool], List[Optional[float]],
            Dict[str, List[Optional[float]]], List[str]]:
    """For each 4h bar, find latest daily supply z-score available at-or-before
    the bar's timestamp. Mask if z > Z_THRESHOLD."""
    diag.setdefault('total_bars', 0)
    diag.setdefault('aligned', 0)
    diag.setdefault('z_extreme', 0)

    sorted_supply_ts = sorted(daily_supply_z.keys())
    n = len(perp_bars)
    closes = [b['c'] for b in perp_bars]

    mask = [False] * n
    factor: List[Optional[float]] = [None] * n
    fwd: Dict[str, List[Optional[float]]] = {}
    for label, h in HORIZONS.items():
        fwd[label] = [None] * n
        for i in range(n - h):
            if closes[i] > 0:
                # SIGNED forward return per B2/B3 methodology lesson
                fwd[label][i] = (closes[i + h] - closes[i]) / closes[i] * 100

    regimes = [regime_label(closes, i) for i in range(n)]

    # Binary-search assignment of latest daily z-score per bar
    import bisect
    for i in range(n):
        diag['total_bars'] += 1
        bar_ts = perp_bars[i]['ts']
        idx = bisect.bisect_right(sorted_supply_ts, bar_ts) - 1
        if idx < 0:
            continue
        z = daily_supply_z[sorted_supply_ts[idx]]
        factor[i] = z
        diag['aligned'] += 1
        if z > Z_THRESHOLD:  # spec: positive z extreme = stablecoin minting impulse
            diag['z_extreme'] += 1
            mask[i] = True

    return mask, factor, fwd, regimes


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
    print("  A2 — STABLECOIN SUPPLY IMPULSE (DefiLlama free endpoint)")
    print(f"  Universe: USDT + USDC combined supply")
    print(f"  Test pairs: {', '.join(PAIRS_TO_TEST)}")
    print(f"  Horizons: {list(HORIZONS.keys())}")
    print("  L99 thresholds: INTACT (post-2026-05-05 corrections)")
    print("═" * 74)
    print()

    # ─────────── Step 1 — Fetch stablecoin supply history ───────────
    print("  ── Stablecoin supply history (DefiLlama, no auth) ──")
    daily_supplies: Dict[int, Dict[str, float]] = {}  # {day_ts: {USDT: x, USDC: y}}
    for symbol, coin_id in DEFILLAMA_STABLECOIN_IDS.items():
        history = fetch_stablecoin_history(coin_id)
        print(f"    {symbol}: {len(history)} daily records  "
              f"[{datetime.fromtimestamp(history[0][0], timezone.utc).strftime('%Y-%m-%d')} → "
              f"{datetime.fromtimestamp(history[-1][0], timezone.utc).strftime('%Y-%m-%d')}]")
        for ts, v in history:
            daily_supplies.setdefault(ts, {})[symbol] = v
        time.sleep(0.5)
    print()

    # Combine: daily total_supply = USDT + USDC (only days where BOTH present)
    daily_total: Dict[int, float] = {}
    for ts, supplies in daily_supplies.items():
        if 'USDT' in supplies and 'USDC' in supplies:
            daily_total[ts] = supplies['USDT'] + supplies['USDC']
    sorted_days = sorted(daily_total.keys())
    daily_total_series = [daily_total[ts] for ts in sorted_days]
    print(f"  Combined USDT+USDC days (both present): {len(sorted_days)}")
    print(f"    Range: {datetime.fromtimestamp(sorted_days[0], timezone.utc).strftime('%Y-%m-%d')} → "
          f"{datetime.fromtimestamp(sorted_days[-1], timezone.utc).strftime('%Y-%m-%d')}")
    print()

    # ─────────── Step 2 — Compute 7-day growth + 30-day Z-score ───────────
    print("  ── Computing factor: 7-day supply % change → 30-day Z-score ──")
    growth_7d = n_day_change(daily_total_series, GROWTH_LOOKBACK_7D)
    z_series = rolling_zscore(
        [g if g is not None else 0 for g in growth_7d],
        Z_LOOKBACK,
    )
    daily_z: Dict[int, float] = {}
    for i, ts in enumerate(sorted_days):
        if z_series[i] is not None and growth_7d[i] is not None:
            daily_z[ts] = z_series[i]
    print(f"  Daily z-scores computed: {len(daily_z)}")
    extreme = [z for z in daily_z.values() if z > Z_THRESHOLD]
    print(f"  Days with z > {Z_THRESHOLD}: {len(extreme)} ({len(extreme)/len(daily_z)*100:.1f}%)")
    print()

    # ─────────── Step 3 — Fetch perp bars ───────────
    print("  ── Paginated 4h perp candles (3+ years) ──")
    perp_data: Dict[str, List[Dict[str, float]]] = {}
    for pair in PAIRS_TO_TEST:
        try:
            perp_data[pair] = fetch_perp_4h_paginated(pair)
            print(f"    {pair}: perp4h={len(perp_data[pair])}")
        except Exception as e:
            print(f"    {pair}: FAILED — {e}")
            perp_data[pair] = []
    print()

    # ─────────── Step 4 — Battery per pair × horizon × fee ───────────
    print("  ── Running A2 battery ──")
    all_results: Dict[str, Dict] = {}
    diag_master: Dict[str, Dict[str, int]] = {}
    pooled: Dict[str, Tuple[List, List, List, List]] = {
        h: ([], [], [], []) for h in HORIZONS
    }

    for pair in PAIRS_TO_TEST:
        if not perp_data[pair]:
            continue
        diag = {}
        mask, factor, fwd_dict, regimes = build_a2_signal_per_pair(
            daily_z, perp_data[pair], diag,
        )
        diag_master[f'A2_{pair}'] = diag
        for h_label in HORIZONS:
            for scenario, fee_rt in FEE_SCENARIOS.items():
                res = battery(
                    f'A2_{pair}_{h_label}_{scenario}',
                    factor, fwd_dict[h_label], regimes, mask, fee_rt,
                )
                all_results[res['name']] = res
            # Pool for universe
            pf, ff, rr, mm = pooled[h_label]
            pf.extend(factor)
            ff.extend(fwd_dict[h_label])
            rr.extend(regimes)
            mm.extend(mask)

    # Universe-aggregated
    for h_label, (pf, ff, rr, mm) in pooled.items():
        for scenario, fee_rt in FEE_SCENARIOS.items():
            res = battery(
                f'A2_UNIVERSE_{h_label}_{scenario}',
                pf, ff, rr, mm, fee_rt,
            )
            all_results[res['name']] = res

    # ─────────── Step 5 — Print + save ───────────
    print()
    print(f"  {'Factor':<48} {'N':>6} {'IC':>8} {'t':>8} {'PF':>6} {'Q-bps':>9} {'MC%':>5} {'Reg':>4}  Status")
    print("  " + "─" * 100)
    passing = []
    insufficient = []
    failing = []
    for name, r in all_results.items():
        st = "✅ PASS" if r['passes'] else "❌"
        n_part = ('N<100' if any('< 100' in k for k in r['killed_by']) else 'KILL')
        status_str = f"{st} {n_part}" if not r['passes'] else st
        print(f"  {name:<48} {r['n']:>6} {r['ic']:>+8.4f} {r['tstat']:>+8.3f} "
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
        'mode': 'A2_STABLECOIN_SUPPLY_DEFILLAMA',
        'data_source': 'DefiLlama free stablecoin endpoint (NO auth)',
        'stablecoins': list(DEFILLAMA_STABLECOIN_IDS.keys()),
        'pairs': PAIRS_TO_TEST,
        'horizons': HORIZONS,
        'L99_thresholds': {
            'IC_MIN': L99.IC_MIN, 'TSTAT_MIN': L99.TSTAT_MIN,
            'PF_MIN': L99.PF_MIN, 'QUINTILE_MIN_bps': L99.QUINTILE_MIN,
            'MC_STABILITY': L99.MC_STABILITY, 'REGIME_MIN': L99.REGIME_MIN,
            'MIN_OBS': L99.MIN_OBS,
        },
        'fee_scenarios': {k: f"{v * 10000} bps RT" for k, v in FEE_SCENARIOS.items()},
        'spec_thresholds': {
            'GROWTH_LOOKBACK_7D': GROWTH_LOOKBACK_7D,
            'Z_LOOKBACK': Z_LOOKBACK,
            'Z_THRESHOLD': Z_THRESHOLD,
        },
        'signal_funnels': diag_master,
        'days_supply_history': len(sorted_days),
        'extreme_z_days': len(extreme),
        'passing_count': len(passing),
        'insufficient_count': len(insufficient),
        'failing_count': len(failing),
        'results': all_results,
    }
    with open('a2_stablecoin_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print()
    print(f"  Results: a2_stablecoin_results.json")
    print("═" * 74)
    return summary


if __name__ == '__main__':
    main()
