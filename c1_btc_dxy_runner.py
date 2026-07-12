"""
C1 — BTC–DXY Divergence Break runner.

Per L99_ULTRA_AGGRESSIVE_ALPHA_BLUEPRINT.md factor C1 (priority queue #7,
fully unblocked):

    Hypothesis:
      BTC up while DXY up → unsustainable divergence → expect correction.

    Factor:
      Rolling_30d_corr(BTC, DXY) < -0.3
      AND BTC_3d_return > 3%
      AND DXY_3d_return > 1%

    Test:
      3–5 day correction probability.

Data sources:
  BTC: Gate.io public REST `/spot/candlesticks` interval=1d (no auth)
  DXY: FRED DTWEXBGS — "Nominal Broad U.S. Dollar Index" (daily, no auth)

DOCUMENTED SUBSTITUTION:
  ICE DXY (6 fixed currencies) is not freely available without auth.
  FRED DTWEXBGS uses ~26 trade-weighted currencies — broader basket but
  >95% correlated with ICE DXY in practice. Operationally equivalent for
  USD-strength signals. Substitution documented in structural report.

Signal direction:
  Per spec, C1 signal predicts BEARISH BTC forward (correction). Forward
  returns are flipped to short-side: short_return = -btc_forward_return.

Hard rules honored (same as C2_4H runner):
  - No live deployment
  - No L99 threshold drift (IC≥0.04, t≥2.0, PF≥1.3, Q5−Q1≥60bps,
    MC≥80%, Regimes≥2, N≥100)
  - No factor additions (only C1)
  - No N reduction
  - No daily-timeframe revival of micro intent
  - Capital remains 100% USDT
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '.')
from l99_battery import L99, ic, tstat, profit_factor, monte_carlo  # noqa: F401

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

PAIR = 'BTC_USDT'
INTERVAL = '1d'
LIMIT_BTC = 1000  # ~2.7 years of daily bars

DXY_FRED_SERIES = 'DTWEXBGS'
DXY_START = '2022-01-01'

# Forward horizons (in trading days). 3d/5d/7d.
HORIZONS = {'3d': 3, '5d': 5, '7d': 7}

# Fee scenarios
FEE_SCENARIOS = {
    'A_VIP0_taker':       0.0025,
    'B_VIP1_GT_discount': 0.0018,
    'C_VIP1_maker_only':  0.0014,
}

# Spec thresholds (do NOT modify per "no parameter drift")
CORR_WINDOW = 30          # rolling 30-day Pearson correlation
CORR_THRESHOLD = -0.3     # spec: corr < -0.3 (typical inverse relationship)
BTC_3D_THRESHOLD = 3.0    # spec: BTC 3d return > 3%
DXY_3D_THRESHOLD = 1.0    # spec: DXY 3d return > 1%


# ─────────────────────────────────────────────
# DATA FETCHERS
# ─────────────────────────────────────────────

def fetch_btc_1d() -> List[Dict[str, float]]:
    """Fetch BTC_USDT daily bars from Gate.io public REST."""
    url = (
        f"https://api.gateio.ws/api/v4/spot/candlesticks"
        f"?currency_pair={PAIR}&interval={INTERVAL}&limit={LIMIT_BTC}"
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        raw = json.loads(r.read())
    bars: List[Dict[str, float]] = []
    for row in raw:
        if row[7] != 'true':
            continue
        bars.append({
            'date': datetime.fromtimestamp(int(row[0]), timezone.utc).strftime('%Y-%m-%d'),
            'ts': int(row[0]),
            'c': float(row[2]),
            'h': float(row[3]),
            'l': float(row[4]),
            'o': float(row[5]),
            'v': float(row[6]),
        })
    bars.sort(key=lambda b: b['date'])
    return bars


def fetch_dxy_proxy() -> List[Dict[str, float]]:
    """Fetch FRED DTWEXBGS — Nominal Broad U.S. Dollar Index (daily)."""
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={DXY_FRED_SERIES}&cosd={DXY_START}"
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        text = r.read().decode('utf-8')
    rows: List[Dict[str, float]] = []
    for line in text.splitlines()[1:]:  # skip header
        parts = line.split(',')
        if len(parts) < 2 or parts[1] in ('', '.'):
            continue
        try:
            rows.append({
                'date': parts[0],
                'c': float(parts[1]),
            })
        except ValueError:
            continue
    rows.sort(key=lambda r: r['date'])
    return rows


# ─────────────────────────────────────────────
# ALIGNMENT + FACTOR
# ─────────────────────────────────────────────

def align_btc_dxy(btc: List[Dict[str, float]],
                  dxy: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """Inner-join BTC and DXY by date. DXY is weekday-only; intersect dates."""
    dxy_by_date = {r['date']: r['c'] for r in dxy}
    aligned: List[Dict[str, float]] = []
    for b in btc:
        if b['date'] in dxy_by_date:
            aligned.append({
                'date': b['date'],
                'btc_close': b['c'],
                'dxy_close': dxy_by_date[b['date']],
            })
    return aligned


def rolling_pearson(x: List[float], y: List[float], w: int) -> List[Optional[float]]:
    """Pearson correlation over rolling window of size w."""
    n = len(x)
    out: List[Optional[float]] = [None] * n
    for i in range(w - 1, n):
        wx = x[i - w + 1:i + 1]
        wy = y[i - w + 1:i + 1]
        mx = sum(wx) / w
        my = sum(wy) / w
        num = sum((a - mx) * (b - my) for a, b in zip(wx, wy))
        dx = math.sqrt(sum((a - mx) ** 2 for a in wx))
        dy = math.sqrt(sum((b - my) ** 2 for b in wy))
        out[i] = num / (dx * dy) if dx * dy > 0 else 0.0
    return out


def n_day_return(closes: List[float], n: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(closes)
    for i in range(n, len(closes)):
        if closes[i - n] > 0:
            out[i] = (closes[i] - closes[i - n]) / closes[i - n] * 100
    return out


def c1_signal_mask(aligned: List[Dict[str, float]],
                   diag: Optional[Dict[str, int]] = None) -> Tuple[List[bool], List[Optional[float]]]:
    """Compute C1 signal mask + the factor score (correlation)."""
    n = len(aligned)
    if diag is None:
        diag = {}
    diag.setdefault('total_evaluable', 0)
    diag.setdefault('corr_below_neg03', 0)
    diag.setdefault('btc_3d_above_3', 0)
    diag.setdefault('dxy_3d_above_1', 0)
    diag.setdefault('all_passed', 0)

    btc_closes = [r['btc_close'] for r in aligned]
    dxy_closes = [r['dxy_close'] for r in aligned]

    corr = rolling_pearson(btc_closes, dxy_closes, CORR_WINDOW)
    btc_3d = n_day_return(btc_closes, 3)
    dxy_3d = n_day_return(dxy_closes, 3)

    mask = [False] * n
    for i in range(CORR_WINDOW, n):
        if corr[i] is None or btc_3d[i] is None or dxy_3d[i] is None:
            continue
        diag['total_evaluable'] += 1

        if corr[i] >= CORR_THRESHOLD:  # corr should be < -0.3
            continue
        diag['corr_below_neg03'] += 1

        if btc_3d[i] <= BTC_3D_THRESHOLD:
            continue
        diag['btc_3d_above_3'] += 1

        if dxy_3d[i] <= DXY_3D_THRESHOLD:
            continue
        diag['dxy_3d_above_1'] += 1

        mask[i] = True
        diag['all_passed'] += 1

    return mask, corr


def forward_returns(closes: List[float], horizon_days: int) -> List[Optional[float]]:
    """Forward % return from close[i] to close[i+horizon]."""
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    for i in range(n - horizon_days):
        if closes[i] > 0:
            out[i] = (closes[i + horizon_days] - closes[i]) / closes[i] * 100
    return out


def regime_labels(btc_closes: List[float]) -> List[str]:
    """Label each day's regime from 30-day trailing return."""
    n = len(btc_closes)
    labels = ['unknown'] * n
    for i in range(30, n):
        ret = (btc_closes[i] - btc_closes[i - 30]) / btc_closes[i - 30] * 100 if btc_closes[i - 30] > 0 else 0
        if ret > 10:
            labels[i] = 'bull'
        elif ret < -10:
            labels[i] = 'bear'
        else:
            labels[i] = 'range'
    return labels


# ─────────────────────────────────────────────
# BATTERY (parameterized by fee)
# ─────────────────────────────────────────────

def quintile_spread_full(factor_vals: List[Optional[float]],
                         forward: List[Optional[float]],
                         fee_rt: float) -> float:
    """Q5-Q1 spread in bps after fees. Computed across the full series, not
    just signal hits, so the factor's overall predictive structure is
    measured even when N at the signal mask is below 100."""
    pairs = [(f, r) for f, r in zip(factor_vals, forward)
             if f is not None and r is not None]
    if len(pairs) < 20:
        return 0.0
    pairs.sort(key=lambda x: x[0])
    nq = max(1, len(pairs) // 5)
    q1 = [p[1] for p in pairs[:nq]]
    q5 = [p[1] for p in pairs[-nq:]]
    # Fix 2026-05-05 per council M3: per-leg fee, decimal→bps via *10000.
    return (statistics.mean(q5) - statistics.mean(q1)) * 100 - fee_rt * 10000 * 2


def run_battery_at_fee(name: str,
                        factor_vals: List[Optional[float]],
                        forward_short: List[Optional[float]],
                        regime_labels_list: List[str],
                        signal_mask: List[bool],
                        fee_rt: float) -> Dict:
    """Run all 7 L99 conditions on a factor at a specific fee rate."""
    # Filter to bars with all data present
    indices = [i for i in range(len(signal_mask))
               if signal_mask[i]
               and factor_vals[i] is not None
               and forward_short[i] is not None]
    n = len(indices)

    killed_by: List[str] = []
    if n < L99.MIN_OBS:
        return {
            'name': name, 'fee_rt_bps': fee_rt * 10000, 'n': n,
            'passes': False, 'killed_by': [f'N={n} < {L99.MIN_OBS} minimum'],
            'ic': 0, 'tstat': 0, 'pf': 0, 'q_bps': 0, 'mc': 0,
            'regime_count': 0, 'gross_expectancy': 0, 'net_expectancy': 0,
        }

    sig_factor = [factor_vals[i] for i in indices]
    sig_returns = [forward_short[i] for i in indices]
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

    qs_v = quintile_spread_full(factor_vals, forward_short, fee_rt)

    import random
    rng = random.Random(42)
    mc_wins = 0
    for _ in range(500):
        sample = [rng.choice(net_returns) for _ in range(n)]
        if sum(sample) > 0:
            mc_wins += 1
    mc_v = mc_wins / 500

    sig_regimes = [regime_labels_list[i] for i in indices]
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
        killed_by.append(f"Q5-Q1={qs_v:+.2f}bps")
    if mc_v < L99.MC_STABILITY:
        killed_by.append(f"MC={mc_v * 100:.1f}%")
    if reg_count < L99.REGIME_MIN:
        killed_by.append(f"Regimes={reg_count}")

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
    print("  C1 — BTC-DXY DIVERGENCE BREAK RUNNER")
    print("  Pair: BTC_USDT (Gate.io)  |  DXY proxy: FRED DTWEXBGS")
    print("  L99 thresholds: INTACT (no parameter drift)")
    print("═" * 74)
    print()

    print("  ── Fetching daily bars ──")
    try:
        btc = fetch_btc_1d()
        print(f"    BTC: {len(btc)} bars  [{btc[0]['date']} → {btc[-1]['date']}]")
    except Exception as e:
        print(f"    BTC fetch FAILED: {e}")
        return None

    try:
        dxy = fetch_dxy_proxy()
        print(f"    DXY (DTWEXBGS): {len(dxy)} bars  [{dxy[0]['date']} → {dxy[-1]['date']}]")
    except Exception as e:
        print(f"    DXY fetch FAILED: {e}")
        return None

    aligned = align_btc_dxy(btc, dxy)
    print(f"    Aligned (intersection): {len(aligned)} bars")
    if aligned:
        print(f"      [{aligned[0]['date']} → {aligned[-1]['date']}]")
    print()

    if len(aligned) < CORR_WINDOW + 30:
        print(f"  ⚠ Aligned series too short ({len(aligned)} < {CORR_WINDOW + 30}). Aborting.")
        return None

    # Compute signal
    print("  ── Computing C1 signal mask ──")
    diag: Dict[str, int] = {}
    mask, corr = c1_signal_mask(aligned, diag)
    n_signals = sum(mask)
    print(f"    Total evaluable bars (after CORR_WINDOW=30): {diag['total_evaluable']}")
    print(f"    corr<{CORR_THRESHOLD} pass:               {diag['corr_below_neg03']}")
    print(f"    + BTC_3d>{BTC_3D_THRESHOLD}% pass:          {diag['btc_3d_above_3']}")
    print(f"    + DXY_3d>{DXY_3D_THRESHOLD}% pass:          {diag['dxy_3d_above_1']}")
    print(f"    Final signals fired:                          {n_signals}")
    print()

    btc_closes = [r['btc_close'] for r in aligned]
    regimes = regime_labels(btc_closes)

    print("  ── Running battery × 3 horizons × 3 fee scenarios ──")
    all_results: Dict[str, Dict] = {}
    for hlabel, hdays in HORIZONS.items():
        # Forward BTC return at horizon
        fwd_btc = forward_returns(btc_closes, hdays)
        # Spec C1 expects bearish forward → short-side return
        fwd_short = [(-r if r is not None else None) for r in fwd_btc]
        for scenario, fee_rt in FEE_SCENARIOS.items():
            name = f"C1_BTC_DXY_{hlabel}_{scenario}"
            result = run_battery_at_fee(
                name=name,
                factor_vals=corr,
                forward_short=fwd_short,
                regime_labels_list=regimes,
                signal_mask=mask,
                fee_rt=fee_rt,
            )
            all_results[name] = result

    # Print results
    print()
    print(f"  {'Factor':<48} {'N':>5} {'IC':>8} {'t':>8} {'PF':>6} {'Q-bps':>8} {'MC%':>5} {'Reg':>4}  Status")
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

    print()
    print(f"  Total combinations:  {len(all_results)}")
    print(f"  Passing:             {len(passing)}")
    print(f"  Killed by N<100:     {len(insufficient)}")
    print(f"  Killed after N gate: {len(failing_after_n)}")

    summary = {
        'run_time': datetime.now(timezone.utc).isoformat(),
        'pair': PAIR,
        'dxy_source': f"FRED {DXY_FRED_SERIES} (DXY proxy — broad trade-weighted USD)",
        'btc_bars': len(btc),
        'dxy_bars': len(dxy),
        'aligned_bars': len(aligned),
        'signal_funnel': diag,
        'n_signals_fired': n_signals,
        'L99_thresholds': {
            'IC_MIN': L99.IC_MIN, 'TSTAT_MIN': L99.TSTAT_MIN,
            'PF_MIN': L99.PF_MIN, 'QUINTILE_MIN_bps': L99.QUINTILE_MIN,
            'MC_STABILITY': L99.MC_STABILITY, 'REGIME_MIN': L99.REGIME_MIN,
            'MIN_OBS': L99.MIN_OBS,
        },
        'spec_thresholds': {
            'CORR_WINDOW': CORR_WINDOW,
            'CORR_THRESHOLD': CORR_THRESHOLD,
            'BTC_3D_THRESHOLD': BTC_3D_THRESHOLD,
            'DXY_3D_THRESHOLD': DXY_3D_THRESHOLD,
        },
        'fee_scenarios': {k: f"{v * 10000} bps RT" for k, v in FEE_SCENARIOS.items()},
        'horizons': HORIZONS,
        'passing_count': len(passing),
        'insufficient_data_count': len(insufficient),
        'failing_after_n_count': len(failing_after_n),
        'total_combinations': len(all_results),
        'results': all_results,
    }
    with open('c1_btc_dxy_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print()
    print(f"  Results: c1_btc_dxy_results.json")
    print("═" * 74)
    return summary


if __name__ == '__main__':
    main()
