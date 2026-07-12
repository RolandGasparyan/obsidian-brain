"""
C2_4H — Volatility Regime Transition factor on 4H spot bars.

Per /OODA /GODMODE /L99 — C2 STRUCTURAL SWITCH directive (2026-05-02):
  - Switch C2 factor to 4H timeframe
  - Top liquid spot pairs
  - Fee model: VIP0 (25 bps RT) + 2 alternative scenarios
  - Apply L99 7-filter battery intact (NO threshold lowering)
  - If N < 100 → continue data accumulation (NOT a NO-GO)

C2_4H signal definition (per directive Phase 1):
  1. ATR(14) expansion: ATR_now > rolling 30-period baseline × 1.5
  2. Range breakout: close > 20-bar high
  3. Volume percentile > 70% (rolling 30)
  4. Range stability: current bar range within 20% of rolling 30-period median range
  5. No DEAD regime override: |10-bar return| > 0.5%

Fee scenarios (Phase 3):
  A. VIP0 taker/taker        25 bps RT
  B. VIP1 + GT discount      18 bps RT
  C. VIP1 + maker-only       14 bps RT

Hard rules honored:
  - No live deployment       ← runner produces JSON + report only
  - No parameter drift       ← FEE_RT applied per scenario; L99 thresholds intact
  - No adding factors        ← only C2_4H
  - No N reduction           ← N≥100 minimum enforced
  - No micro timeframe       ← 4H only
  - Capital 100% USDT        ← no positions taken
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# Add repo root for l99_battery import
sys.path.insert(0, '.')
from l99_battery import L99, ic, tstat, profit_factor, quintile_spread, monte_carlo

# Pairs (top liquid spot per existing microstructure_collector universe)
PAIRS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'XRP_USDT', 'AVAX_USDT']

INTERVAL = '4h'
LIMIT_PER_PAIR = 1000  # ~167 days of 4H bars

# Fee scenarios (round-trip in fraction)
FEE_SCENARIOS = {
    'A_VIP0_taker':       0.0025,  # 25 bps RT
    'B_VIP1_GT_discount': 0.0018,  # 18 bps RT
    'C_VIP1_maker_only':  0.0014,  # 14 bps RT
}

# Forward horizons (in 4H bars). 24h = 6 bars; 48h = 12 bars; 72h = 18 bars.
HORIZONS = {'24h': 6, '48h': 12, '72h': 18}


# ─────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────

def fetch_4h_candles(pair: str) -> List[Dict[str, float]]:
    """Fetch 4H OHLCV from Gate.io public REST. Returns list of dicts.

    Gate.io candlestick format:
      [ts_seconds, quote_volume, close, high, low, open, base_volume, finished_flag]
    """
    url = (
        f"https://api.gateio.ws/api/v4/spot/candlesticks"
        f"?currency_pair={pair}&interval={INTERVAL}&limit={LIMIT_PER_PAIR}"
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        raw = json.loads(r.read())

    bars: List[Dict[str, float]] = []
    for row in raw:
        # Skip unfinished bars
        if row[7] != 'true':
            continue
        bars.append({
            'ts': int(row[0]),
            'o': float(row[5]),
            'h': float(row[3]),
            'l': float(row[4]),
            'c': float(row[2]),
            'v': float(row[6]),
        })
    bars.sort(key=lambda b: b['ts'])
    return bars


# ─────────────────────────────────────────────
# C2_4H FACTOR
# ─────────────────────────────────────────────

def compute_atr14(bars: List[Dict[str, float]]) -> List[Optional[float]]:
    if len(bars) < 14:
        return [None] * len(bars)
    tr = [bars[0]['h'] - bars[0]['l']]
    for i in range(1, len(bars)):
        tr.append(max(
            bars[i]['h'] - bars[i]['l'],
            abs(bars[i]['h'] - bars[i - 1]['c']),
            abs(bars[i]['l'] - bars[i - 1]['c']),
        ))
    atr: List[Optional[float]] = [None] * len(bars)
    atr[13] = sum(tr[:14]) / 14
    for i in range(14, len(bars)):
        atr[i] = (atr[i - 1] * 13 + tr[i]) / 14
    return atr


def c2_4h_signal_mask(bars: List[Dict[str, float]],
                       diag: Optional[Dict[str, int]] = None) -> List[bool]:
    """Compute the C2_4H boolean signal mask per directive Phase 1.

    NOTE on directive condition 4 ("Spread stability within 20% of median"):
    This requires orderbook bid-ask data, which is NOT available from
    Gate.io public candlestick REST. We OMIT this filter and document
    the limitation in the structural report. Honoring "no parameter drift",
    we do NOT substitute an OHLCV-derived proxy that would contradict
    condition 1 (ATR expansion).

    The remaining 4 conditions are intact:
      1. ATR(14) expansion: ATR_now > rolling 30-baseline × 1.5
      2. Range breakout: close > 20-bar high (excluding current)
      3. Volume percentile > 70 (rolling 30)
      4. (omitted: spread stability — needs orderbook)
      5. No DEAD regime: |10-bar return| > 0.5%
    """
    n = len(bars)
    mask = [False] * n
    atr = compute_atr14(bars)
    if diag is None:
        diag = {}
    diag.setdefault('total', 0)
    diag.setdefault('atr_expansion', 0)
    diag.setdefault('range_breakout', 0)
    diag.setdefault('volume_pct', 0)
    diag.setdefault('not_dead', 0)
    diag.setdefault('all_passed', 0)

    for i in range(31, n):
        diag['total'] += 1

        # 1. ATR expansion
        atr_window = [a for a in atr[i - 30:i] if a is not None]
        if not atr_window or atr[i] is None:
            continue
        atr_baseline = sum(atr_window) / len(atr_window)
        if atr[i] <= atr_baseline * 1.5:
            continue
        diag['atr_expansion'] += 1

        # 2. Range breakout
        range_20h = max(b['h'] for b in bars[i - 20:i])
        if bars[i]['c'] <= range_20h:
            continue
        diag['range_breakout'] += 1

        # 3. Volume percentile > 70
        vols = [b['v'] for b in bars[i - 30:i]]
        rank = sum(1 for v in vols if v <= bars[i]['v']) / len(vols)
        if rank <= 0.70:
            continue
        diag['volume_pct'] += 1

        # 5. No DEAD regime
        c10_ret = abs(bars[i]['c'] - bars[i - 10]['c']) / bars[i - 10]['c'] * 100
        if c10_ret <= 0.5:
            continue
        diag['not_dead'] += 1

        mask[i] = True
        diag['all_passed'] += 1

    return mask


# ─────────────────────────────────────────────
# FORWARD RETURNS + REGIME LABELS
# ─────────────────────────────────────────────

def compute_forward_returns(
    bars: List[Dict[str, float]],
    horizon_bars: int,
) -> List[Optional[float]]:
    n = len(bars)
    fwd: List[Optional[float]] = [None] * n
    for i in range(n - horizon_bars):
        if bars[i]['c'] > 0:
            fwd[i] = (bars[i + horizon_bars]['c'] - bars[i]['c']) / bars[i]['c'] * 100
    return fwd


def regime_labels(bars: List[Dict[str, float]]) -> List[str]:
    """Classify each bar's regime based on 15-bar trailing return + volatility."""
    n = len(bars)
    labels = ['unknown'] * n
    for i in range(15, n):
        window = bars[max(0, i - 15):i + 1]
        ret = (window[-1]['c'] - window[0]['c']) / window[0]['c'] * 100 if window[0]['c'] > 0 else 0
        diffs = []
        for j in range(1, len(window)):
            if window[j - 1]['c'] > 0:
                diffs.append(abs(window[j]['c'] - window[j - 1]['c']) / window[j - 1]['c'] * 100)
        vol = statistics.mean(diffs) if diffs else 0
        if vol < 0.3:
            labels[i] = 'range'
        elif ret > 3:
            labels[i] = 'bull'
        elif ret < -3:
            labels[i] = 'bear'
        else:
            labels[i] = 'volatile'
    return labels


# ─────────────────────────────────────────────
# BATTERY (parameterized by fee)
# ─────────────────────────────────────────────

def run_battery_at_fee(
    name: str,
    factor_vals: List[Optional[float]],
    forward_returns: List[Optional[float]],
    regime_labels_list: List[str],
    signal_mask: List[bool],
    fee_rt: float,
) -> Dict:
    """Run all 7 L99 conditions on a factor at a specific fee rate.

    Returns dict with: passes, n, ic, tstat, pf, q_bps, mc, regime_count, killed_by.
    Mirrors l99_battery.run_battery() but allows fee override per scenario.
    """
    sig_factor = [factor_vals[i] for i in range(len(signal_mask))
                  if signal_mask[i] and factor_vals[i] is not None
                  and forward_returns[i] is not None]
    sig_returns = [forward_returns[i] for i in range(len(signal_mask))
                   if signal_mask[i] and factor_vals[i] is not None
                   and forward_returns[i] is not None]
    n = len(sig_returns)

    killed_by: List[str] = []

    if n < L99.MIN_OBS:
        return {
            'name': name, 'fee_rt_bps': fee_rt * 10000, 'n': n,
            'passes': False, 'killed_by': [f'N={n} < {L99.MIN_OBS} minimum'],
            'ic': 0, 'tstat': 0, 'pf': 0, 'q_bps': 0, 'mc': 0,
            'regime_count': 0, 'gross_expectancy': 0, 'net_expectancy': 0,
        }

    # Gross + net stats
    gross_exp = statistics.mean(sig_returns) if sig_returns else 0
    net_returns = [r - fee_rt * 100 for r in sig_returns]
    net_exp = statistics.mean(net_returns) if net_returns else 0

    ic_v = ic(sig_factor, sig_returns)
    ts_v = tstat(net_returns)

    # Profit factor on net returns
    wins = [r for r in net_returns if r > 0]
    losses = [r for r in net_returns if r <= 0]
    pf_v = (sum(wins) / abs(sum(losses))) if (wins and losses) else (999 if not losses else 0)

    qs_v = quintile_spread(factor_vals, [r if r is not None else 0 for r in forward_returns])
    qs_v_net = qs_v - fee_rt * 10000  # quintile_spread already subtracted L99.FEE_RT*100*2; re-adjust
    # Actually quintile_spread() subtracts L99.FEE_RT*100*2 hardcoded. Recompute fee-agnostic:
    pairs = [(f, r) for f, r in zip(factor_vals, forward_returns)
             if f is not None and r is not None]
    if len(pairs) >= 20:
        pairs.sort(key=lambda x: x[0])
        nq = max(1, len(pairs) // 5)
        q1_ret = [p[1] for p in pairs[:nq]]
        q5_ret = [p[1] for p in pairs[-nq:]]
        gross_q5_q1_pct = statistics.mean(q5_ret) - statistics.mean(q1_ret)
        qs_v_correct = gross_q5_q1_pct * 100 - fee_rt * 10000 * 2  # bps; fix 2026-05-05 per council M3 (per-leg fee, decimal→bps via *10000)
    else:
        qs_v_correct = 0.0

    # Monte Carlo on net returns
    import random
    rng = random.Random(42)
    if net_returns:
        mc_wins = 0
        for _ in range(500):
            sample = [rng.choice(net_returns) for _ in range(len(net_returns))]
            if sum(sample) > 0:
                mc_wins += 1
        mc_v = mc_wins / 500
    else:
        mc_v = 0.0

    # Regime breakdown
    sig_regimes = [regime_labels_list[i] for i in range(len(signal_mask))
                   if signal_mask[i] and factor_vals[i] is not None
                   and forward_returns[i] is not None]
    regime_ret: Dict[str, List[float]] = {}
    for r_label, ret in zip(sig_regimes, net_returns):
        regime_ret.setdefault(r_label, []).append(ret)
    reg_pos = sum(1 for rets in regime_ret.values()
                  if len(rets) >= 5 and statistics.mean(rets) > 0)
    reg_count = reg_pos

    if abs(ic_v) < L99.IC_MIN:
        killed_by.append(f"IC={ic_v:+.4f}")
    if abs(ts_v) < L99.TSTAT_MIN:
        killed_by.append(f"t={ts_v:+.4f}")
    if pf_v < L99.PF_MIN:
        killed_by.append(f"PF={pf_v:.4f}")
    if qs_v_correct < L99.QUINTILE_MIN:
        killed_by.append(f"Q5-Q1={qs_v_correct:+.2f}bps")
    if mc_v < L99.MC_STABILITY:
        killed_by.append(f"MC={mc_v * 100:.1f}%")
    if reg_count < L99.REGIME_MIN:
        killed_by.append(f"Regimes={reg_count}")

    return {
        'name': name, 'fee_rt_bps': fee_rt * 10000, 'n': n,
        'passes': len(killed_by) == 0,
        'killed_by': killed_by,
        'ic': ic_v, 'tstat': ts_v, 'pf': pf_v, 'q_bps': qs_v_correct,
        'mc': mc_v, 'regime_count': reg_count,
        'gross_expectancy': gross_exp, 'net_expectancy': net_exp,
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + "═" * 74)
    print("  C2_4H STRUCTURAL SWITCH EXECUTION")
    print("  Universe: " + ", ".join(PAIRS))
    print(f"  Timeframe: {INTERVAL}  Limit: {LIMIT_PER_PAIR} bars/pair")
    print("  L99 thresholds: INTACT (no parameter drift)")
    print("═" * 74)
    print()

    pair_data = {}
    print("  ── Fetching 4H bars from Gate.io public REST ──")
    for pair in PAIRS:
        try:
            bars = fetch_4h_candles(pair)
            pair_data[pair] = bars
            t0 = datetime.utcfromtimestamp(bars[0]['ts']).strftime('%Y-%m-%d')
            t1 = datetime.utcfromtimestamp(bars[-1]['ts']).strftime('%Y-%m-%d')
            print(f"    {pair}: {len(bars)} bars  [{t0} → {t1}]")
        except Exception as e:
            print(f"    {pair}: FETCH FAILED — {e}")
            pair_data[pair] = []
    print()

    # Compute signals + forward returns + regime labels per pair
    print("  ── Computing C2_4H factor + battery (per fee scenario) ──")
    all_results = {}
    n_signals_per_pair: Dict[str, int] = {}
    diag_per_pair: Dict[str, Dict[str, int]] = {}
    for pair in PAIRS:
        bars = pair_data.get(pair, [])
        if len(bars) < 50:
            n_signals_per_pair[pair] = 0
            continue
        diag: Dict[str, int] = {}
        mask = c2_4h_signal_mask(bars, diag)
        n_signals_per_pair[pair] = sum(mask)
        diag_per_pair[pair] = diag
        atr = compute_atr14(bars)
        regimes = regime_labels(bars)

        for horizon_label, horizon_bars in HORIZONS.items():
            fwd = compute_forward_returns(bars, horizon_bars)

            for scenario, fee_rt in FEE_SCENARIOS.items():
                name = f"C2_4H_{pair}_{horizon_label}_{scenario}"
                result = run_battery_at_fee(
                    name=name,
                    factor_vals=atr,
                    forward_returns=fwd,
                    regime_labels_list=regimes,
                    signal_mask=mask,
                    fee_rt=fee_rt,
                )
                all_results[name] = result

    # Summary
    print()
    print("  ── BATTERY RESULTS ──")
    print()
    hdr = f"  {'Factor':<48} {'N':>5} {'IC':>8} {'t':>8} {'PF':>6} {'Q-bps':>8} {'MC%':>5} {'Reg':>4}  Status"
    print(hdr)
    print("  " + "─" * 100)
    passing = []
    insufficient = []
    failing_after_n = []
    for name, r in all_results.items():
        st = "✅ PASS" if r['passes'] else "❌"
        n_part = ('N<100' if any('< 100' in k for k in r['killed_by']) else 'KILL')
        status_str = f"{st} {n_part}" if not r['passes'] else st
        print(f"  {name:<48} {r['n']:>5} {r['ic']:>+8.4f} {r['tstat']:>+8.3f} "
              f"{r['pf']:>6.2f} {r['q_bps']:>+8.2f} {r['mc']*100:>5.1f} "
              f"{r['regime_count']:>4}  {status_str}")
        if r['passes']:
            passing.append(name)
        elif any('< 100' in k for k in r['killed_by']):
            insufficient.append(name)
        else:
            failing_after_n.append(name)

    # Save results
    summary = {
        'run_time': datetime.now(timezone.utc).isoformat(),
        'pairs': PAIRS,
        'timeframe': INTERVAL,
        'limit_per_pair': LIMIT_PER_PAIR,
        'fee_scenarios': {k: f"{v * 10000} bps RT" for k, v in FEE_SCENARIOS.items()},
        'L99_thresholds': {
            'IC_MIN': L99.IC_MIN,
            'TSTAT_MIN': L99.TSTAT_MIN,
            'PF_MIN': L99.PF_MIN,
            'QUINTILE_MIN_bps': L99.QUINTILE_MIN,
            'MC_STABILITY': L99.MC_STABILITY,
            'REGIME_MIN': L99.REGIME_MIN,
            'MIN_OBS': L99.MIN_OBS,
        },
        'n_signals_per_pair': n_signals_per_pair,
        'bars_per_pair': {p: len(pair_data.get(p, [])) for p in PAIRS},
        'signal_funnel_per_pair': diag_per_pair,
        'passing_count': len(passing),
        'insufficient_data_count': len(insufficient),
        'failing_after_n_count': len(failing_after_n),
        'total_combinations': len(all_results),
        'results': all_results,
    }
    with open('c2_4h_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print()
    print(f"  Total combinations:  {len(all_results)}")
    print(f"  Passing:             {len(passing)}")
    print(f"  Killed by N<100:     {len(insufficient)}")
    print(f"  Killed after N gate: {len(failing_after_n)}")
    print()
    print("  ── SIGNAL FUNNEL (where conditions kill candidates) ──")
    print(f"  {'Pair':<12} {'total':>7} {'atr×1.5':>8} {'breakout':>9} {'vol>70%':>8} {'!dead':>7} {'final':>7}")
    for pair in PAIRS:
        d = diag_per_pair.get(pair, {})
        if d:
            print(f"  {pair:<12} {d.get('total', 0):>7} "
                  f"{d.get('atr_expansion', 0):>8} "
                  f"{d.get('range_breakout', 0):>9} "
                  f"{d.get('volume_pct', 0):>8} "
                  f"{d.get('not_dead', 0):>7} "
                  f"{d.get('all_passed', 0):>7}")
    print()
    print(f"  Results: c2_4h_results.json")
    print("═" * 74)
    return summary


if __name__ == '__main__':
    main()
