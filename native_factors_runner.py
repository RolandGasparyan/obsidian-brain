"""
L99_NATIVE_ONLY_MODE — Exchange-native factor battery (Gate.io only).

Per /L99_NATIVE_ONLY_MODE directive (2026-05-02):
  - NO CryptoQuant, Glassnode, Whale Alert
  - NO external macro
  - Gate.io spot + futures + funding + OI + liquidations only

Factors tested (per directive Phase 1):
  B1 — Funding extreme divergence:    |funding_z| > 2.5 → expect 3-5d mean reversion
  B2 — OI spike + flat price:         OI_3d_change > 90th pct AND |Δprice|<1% → squeeze breakout
  B3 — Basis compression:             |basis_z| > some threshold → expect expansion
  D1 — Volatility contraction → expansion:  ATR percentile crosses low→high
  D2 — Failed breakout trap:          price breaks 20-bar high, reverses below within 3 bars
  D3 — Liquidity vacuum burst:        SKIPPED — needs L2 orderbook history (not in public REST)

L99 thresholds INTACT (no parameter drift):
  IC ≥ 0.04, t ≥ 2.0, PF ≥ 1.3, Q5−Q1 ≥ 60bps, MC ≥ 80%, Regimes ≥ 2, N ≥ 100

Hard rules honored:
  - No live deployment
  - No threshold tweaking
  - No factor additions beyond the 5 implementable
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
from l99_battery import L99, ic, tstat


PAIRS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'XRP_USDT', 'AVAX_USDT']
LIMIT = 1000  # ~2.7 years daily, ~167 days 4h, ~42 days 1h

# Timeframes per factor type
TF_DAILY = '1d'
TF_4H = '4h'

FEE_SCENARIOS = {
    'A_VIP0_taker':       0.0025,
    'B_VIP1_GT_discount': 0.0018,
    'C_VIP1_maker_only':  0.0014,
}

# Forward horizons in BARS (multiplied by timeframe)
HORIZONS_DAILY = {'3d': 3, '5d': 5, '7d': 7}
HORIZONS_4H = {'24h': 6, '48h': 12, '72h': 18}


# ─────────────────────────────────────────────
# DATA FETCHERS (Gate.io public REST, no auth)
# ─────────────────────────────────────────────

def http_get(url: str, timeout: int = 25):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_spot_ohlcv(pair: str, interval: str, limit: int = LIMIT) -> List[Dict[str, float]]:
    raw = http_get(
        f"https://api.gateio.ws/api/v4/spot/candlesticks"
        f"?currency_pair={pair}&interval={interval}&limit={limit}"
    )
    bars = []
    for r in raw:
        if r[7] != 'true':
            continue
        bars.append({
            'ts': int(r[0]),
            'o': float(r[5]), 'h': float(r[3]), 'l': float(r[4]),
            'c': float(r[2]), 'v': float(r[6]),
        })
    bars.sort(key=lambda b: b['ts'])
    return bars


def fetch_futures_ohlcv(contract: str, interval: str, limit: int = LIMIT) -> List[Dict[str, float]]:
    raw = http_get(
        f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks"
        f"?contract={contract}&interval={interval}&limit={limit}"
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


def fetch_funding_rates(contract: str, limit: int = LIMIT) -> List[Dict[str, float]]:
    """Returns funding rate history (most-recent-first per Gate.io)."""
    raw = http_get(
        f"https://api.gateio.ws/api/v4/futures/usdt/funding_rate"
        f"?contract={contract}&limit={limit}"
    )
    rows = [{'ts': int(r['t']), 'r': float(r['r'])} for r in raw]
    rows.sort(key=lambda r: r['ts'])
    return rows


def fetch_contract_stats(contract: str, limit: int = LIMIT, interval: str = '1h') -> List[Dict[str, float]]:
    """Returns OI / mark_price / LSR / liq_summary history (per `interval`)."""
    raw = http_get(
        f"https://api.gateio.ws/api/v4/futures/usdt/contract_stats"
        f"?contract={contract}&limit={limit}&interval={interval}"
    )
    rows = []
    for x in raw:
        try:
            rows.append({
                'ts': int(x['time']),
                'oi_usd': float(x.get('open_interest_usd', 0) or 0),
                'mp': float(x.get('mark_price', 0) or 0),
                'lsr_taker': float(x.get('lsr_taker', 0) or 0),
                'liq_long_usd': float(x.get('long_liq_usd_new', 0) or 0),
                'liq_short_usd': float(x.get('short_liq_usd_new', 0) or 0),
            })
        except (KeyError, ValueError, TypeError):
            continue
    rows.sort(key=lambda r: r['ts'])
    return rows


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


def rolling_percentile(series: List[float], lookback: int) -> List[Optional[float]]:
    n = len(series)
    out: List[Optional[float]] = [None] * n
    for i in range(lookback, n):
        w = series[i - lookback:i]
        rank = sum(1 for x in w if x <= series[i])
        out[i] = rank / lookback
    return out


def compute_atr(bars: List[Dict[str, float]], p: int = 14) -> List[Optional[float]]:
    if len(bars) < p:
        return [None] * len(bars)
    tr = [bars[0]['h'] - bars[0]['l']]
    for i in range(1, len(bars)):
        tr.append(max(
            bars[i]['h'] - bars[i]['l'],
            abs(bars[i]['h'] - bars[i - 1]['c']),
            abs(bars[i]['l'] - bars[i - 1]['c']),
        ))
    atr: List[Optional[float]] = [None] * len(tr)
    atr[p - 1] = sum(tr[:p]) / p
    for i in range(p, len(tr)):
        atr[i] = (atr[i - 1] * (p - 1) + tr[i]) / p
    return atr


def forward_return(closes: List[float], horizon: int) -> List[Optional[float]]:
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    for i in range(n - horizon):
        if closes[i] > 0:
            out[i] = (closes[i + horizon] - closes[i]) / closes[i] * 100
    return out


def regime_label_simple(closes: List[float], i: int, lookback: int = 30) -> str:
    if i < lookback or closes[i - lookback] <= 0:
        return 'unknown'
    ret = (closes[i] - closes[i - lookback]) / closes[i - lookback] * 100
    if ret > 10:
        return 'bull'
    if ret < -10:
        return 'bear'
    return 'range'


# ─────────────────────────────────────────────
# BATTERY
# ─────────────────────────────────────────────

def quintile_spread(factor: List[Optional[float]],
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
    # Fix 2026-05-05 per council M3: per-leg fee, decimal→bps via *10000.
    return (statistics.mean(q5) - statistics.mean(q1)) * 100 - fee_rt * 10000 * 2


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
# FACTORS
# ─────────────────────────────────────────────

def b1_funding_extreme(funding: List[Dict[str, float]],
                       perp_bars: List[Dict[str, float]],
                       diag: Dict[str, int]) -> Tuple[List[bool], List[Optional[float]], List[Optional[float]], List[str]]:
    """B1 — |funding_z| > 2.5 → expect 3-5d mean reversion.

    Aligns funding settlements (8h) with perp 4h bars. Returns mask + factor +
    forward return + regime, all on perp_bars index.
    """
    diag.setdefault('b1_total', 0)
    diag.setdefault('b1_z_extreme', 0)
    diag.setdefault('b1_aligned', 0)

    # Build funding lookup: ts → r
    f_lookup = {f['ts']: f['r'] for f in funding}
    f_series = [f['r'] for f in funding]
    z_series = rolling_zscore(f_series, 30)
    z_by_ts = {funding[i]['ts']: z_series[i] for i in range(len(funding)) if z_series[i] is not None}

    n = len(perp_bars)
    mask = [False] * n
    factor: List[Optional[float]] = [None] * n
    closes = [b['c'] for b in perp_bars]
    fwd = forward_return(closes, 6)  # 24h forward at 4h bars
    regimes = [regime_label_simple(closes, i) for i in range(n)]

    for i in range(n):
        diag['b1_total'] += 1
        # Find latest funding settlement ≤ this bar's ts
        bar_ts = perp_bars[i]['ts']
        nearest_ts = None
        for ts in sorted(z_by_ts.keys()):
            if ts <= bar_ts and (nearest_ts is None or ts > nearest_ts):
                nearest_ts = ts
        if nearest_ts is None:
            continue
        z = z_by_ts[nearest_ts]
        factor[i] = z
        diag['b1_aligned'] += 1
        if abs(z) > 2.5:
            diag['b1_z_extreme'] += 1
            # Mean reversion: short-side return (flip sign for high z = short signal)
            mask[i] = True

    # For high-z (positive funding extreme = longs paying), expect short → flip
    # We use abs(z) for signal magnitude; direction baked into forward
    fwd_directional: List[Optional[float]] = [None] * n
    for i in range(n):
        if fwd[i] is None or factor[i] is None:
            continue
        # If z > 0 (longs paying high funding) expect down → short return = -fwd
        if factor[i] > 0:
            fwd_directional[i] = -fwd[i]
        else:
            fwd_directional[i] = fwd[i]
    return mask, factor, fwd_directional, regimes


def b2_oi_spike_flat_price(stats: List[Dict[str, float]],
                           diag: Dict[str, int]) -> Tuple[List[bool], List[Optional[float]], List[Optional[float]], List[str]]:
    """B2 — OI 3d change > 90th percentile AND |price 24h change| < 1% → squeeze breakout."""
    diag.setdefault('b2_total', 0)
    diag.setdefault('b2_oi_spike', 0)
    diag.setdefault('b2_flat_price', 0)

    n = len(stats)
    closes = [s['mp'] for s in stats]
    oi_series = [s['oi_usd'] for s in stats]

    # 3d change in OI (assuming 1h cadence, 3d = 72 bars)
    horizon_3d_bars = 72
    horizon_24h_bars = 24
    oi_3d_change = [None] * n
    price_24h_change = [None] * n
    for i in range(horizon_3d_bars, n):
        if oi_series[i - horizon_3d_bars] > 0:
            oi_3d_change[i] = (oi_series[i] - oi_series[i - horizon_3d_bars]) / oi_series[i - horizon_3d_bars]
    for i in range(horizon_24h_bars, n):
        if closes[i - horizon_24h_bars] > 0:
            price_24h_change[i] = (closes[i] - closes[i - horizon_24h_bars]) / closes[i - horizon_24h_bars] * 100

    # 90th percentile of OI 3d change (rolling 30-day = 720 hourly bars)
    oi_3d_clean = [v for v in oi_3d_change if v is not None]
    oi_3d_pct = rolling_percentile(
        [v if v is not None else 0 for v in oi_3d_change], min(720, len(oi_3d_change) - 1)
    )

    fwd = forward_return(closes, 48)  # 48h forward (squeeze breakout window)
    regimes = [regime_label_simple(closes, i) for i in range(n)]

    mask = [False] * n
    factor = oi_3d_change[:]
    for i in range(n):
        diag['b2_total'] += 1
        if oi_3d_pct[i] is None or price_24h_change[i] is None or oi_3d_change[i] is None:
            continue
        if oi_3d_pct[i] > 0.90:
            diag['b2_oi_spike'] += 1
            if abs(price_24h_change[i]) < 1.0:
                diag['b2_flat_price'] += 1
                mask[i] = True

    return mask, factor, fwd, regimes


def b3_basis_compression(spot_bars: List[Dict[str, float]],
                         perp_bars: List[Dict[str, float]],
                         diag: Dict[str, int]) -> Tuple[List[bool], List[Optional[float]], List[Optional[float]], List[str]]:
    """B3 — Basis Z-score < threshold → expect expansion (vol).

    Per spec "Perp - Spot basis collapses → Expect expansion".
    Compute basis = (perp_close - spot_close) / spot_close in basis points.
    """
    diag.setdefault('b3_total', 0)
    diag.setdefault('b3_compressed', 0)

    # Align spot + perp by timestamp
    spot_by_ts = {b['ts']: b for b in spot_bars}
    aligned = [(b, spot_by_ts[b['ts']]) for b in perp_bars if b['ts'] in spot_by_ts]
    n = len(aligned)
    perps = [a[0] for a in aligned]
    spots = [a[1] for a in aligned]

    basis_bps = []
    for p, s in aligned:
        if s['c'] > 0:
            basis_bps.append((p['c'] - s['c']) / s['c'] * 10000)  # bps
        else:
            basis_bps.append(0)

    z = rolling_zscore(basis_bps, 30)
    closes = [p['c'] for p in perps]
    fwd_abs = [None] * n
    fwd_raw = forward_return(closes, 6)
    # B3 expects EXPANSION (vol increase) — measure absolute forward return as vol proxy
    for i in range(n):
        if fwd_raw[i] is not None:
            fwd_abs[i] = abs(fwd_raw[i])

    regimes = [regime_label_simple(closes, i) for i in range(n)]

    mask = [False] * n
    for i in range(n):
        diag['b3_total'] += 1
        if z[i] is None:
            continue
        if z[i] < -1.5:  # basis compressed (below normal)
            diag['b3_compressed'] += 1
            mask[i] = True

    return mask, z, fwd_abs, regimes


def d1_vol_contraction_expansion(bars: List[Dict[str, float]],
                                 diag: Dict[str, int]) -> Tuple[List[bool], List[Optional[float]], List[Optional[float]], List[str]]:
    """D1 — Volatility contraction → expansion.

    ATR percentile in low quintile (≤30%) followed by expansion (>70% in
    next bar). Forward return on direction of expansion bar.
    """
    diag.setdefault('d1_total', 0)
    diag.setdefault('d1_contraction', 0)
    diag.setdefault('d1_then_expansion', 0)

    n = len(bars)
    atr = compute_atr(bars, 14)
    atr_pct = [None] * n
    lookback = 60
    for i in range(lookback, n):
        if atr[i] is None:
            continue
        w = [a for a in atr[i - lookback:i] if a is not None]
        if not w:
            continue
        atr_pct[i] = sum(1 for a in w if a <= atr[i]) / len(w)

    closes = [b['c'] for b in bars]
    fwd = forward_return(closes, 6)
    regimes = [regime_label_simple(closes, i) for i in range(n)]

    mask = [False] * n
    factor = atr_pct[:]
    for i in range(1, n):
        diag['d1_total'] += 1
        if atr_pct[i] is None or atr_pct[i - 1] is None:
            continue
        if atr_pct[i - 1] <= 0.30:
            diag['d1_contraction'] += 1
            if atr_pct[i] >= 0.70:
                diag['d1_then_expansion'] += 1
                mask[i] = True

    return mask, factor, fwd, regimes


def d2_failed_breakout(bars: List[Dict[str, float]],
                       diag: Dict[str, int]) -> Tuple[List[bool], List[Optional[float]], List[Optional[float]], List[str]]:
    """D2 — Failed breakout trap.

    Price breaks 20-bar high (bar i), then closes back below within 3 bars
    (bar j ∈ {i+1, i+2, i+3}). LOOK-AHEAD-FREE entry at bar j (the bar where
    failure IS observable in real time). Factor = breakout magnitude
    (computed at i, known at j). Forward return computed FROM bar j (not from i).
    """
    diag.setdefault('d2_total', 0)
    diag.setdefault('d2_breakouts', 0)
    diag.setdefault('d2_failed', 0)

    n = len(bars)
    closes = [b['c'] for b in bars]
    highs = [b['h'] for b in bars]
    fwd_from_each_bar = forward_return(closes, 6)  # 6 bars forward from index
    regimes = [regime_label_simple(closes, i) for i in range(n)]

    mask = [False] * n
    factor: List[Optional[float]] = [None] * n
    fwd_at_entry: List[Optional[float]] = [None] * n  # forward return from entry bar j

    for i in range(20, n - 3):
        diag['d2_total'] += 1
        prior_high = max(highs[i - 20:i])
        if highs[i] <= prior_high:
            continue
        diag['d2_breakouts'] += 1
        breakout_pct = (highs[i] - prior_high) / prior_high * 100

        # Find first bar j in [i+1, i+3] where close < prior_high (failure)
        for j in range(i + 1, min(i + 4, n)):
            if closes[j] < prior_high:
                diag['d2_failed'] += 1
                # Entry is bar j (when failure first observable)
                mask[j] = True
                factor[j] = breakout_pct
                # Forward return from bar j (not from i)
                fwd_at_entry[j] = fwd_from_each_bar[j]
                break

    # Short signal: flip forward return sign (we expect down-move after fakeout)
    fwd_short = [(-r if r is not None else None) for r in fwd_at_entry]
    return mask, factor, fwd_short, regimes


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print()
    print("═" * 74)
    print("  L99_NATIVE_ONLY_MODE — Exchange-native factor battery (Gate.io only)")
    print("  Universe: " + ", ".join(PAIRS))
    print("  L99 thresholds: INTACT")
    print("═" * 74)
    print()

    print("  ── Fetching native data ──")
    spot_4h: Dict[str, List] = {}
    perp_4h: Dict[str, List] = {}
    spot_1d: Dict[str, List] = {}
    perp_1d: Dict[str, List] = {}
    funding: Dict[str, List] = {}
    stats: Dict[str, List] = {}

    for pair in PAIRS:
        try:
            spot_4h[pair] = fetch_spot_ohlcv(pair, TF_4H, LIMIT)
            perp_4h[pair] = fetch_futures_ohlcv(pair, TF_4H, LIMIT)
            spot_1d[pair] = fetch_spot_ohlcv(pair, TF_DAILY, LIMIT)
            perp_1d[pair] = fetch_futures_ohlcv(pair, TF_DAILY, LIMIT)
            funding[pair] = fetch_funding_rates(pair, LIMIT)
            stats[pair] = fetch_contract_stats(pair, LIMIT, '1h')
            print(f"    {pair}: spot4h={len(spot_4h[pair])} perp4h={len(perp_4h[pair])} "
                  f"funding={len(funding[pair])} stats={len(stats[pair])}")
        except Exception as e:
            print(f"    {pair}: FETCH FAILED — {e}")
            spot_4h[pair] = perp_4h[pair] = spot_1d[pair] = perp_1d[pair] = []
            funding[pair] = stats[pair] = []
    print()

    print("  ── Running factors × battery × 3 fee scenarios ──")
    all_results: Dict[str, Dict] = {}
    diag_master: Dict[str, Dict[str, int]] = {}

    for pair in PAIRS:
        if not perp_4h[pair]:
            continue

        # B1 funding extreme
        diag_b = {}
        mask, fac, fwd, reg = b1_funding_extreme(funding[pair], perp_4h[pair], diag_b)
        diag_master[f'B1_{pair}'] = diag_b
        for scenario, fee_rt in FEE_SCENARIOS.items():
            res = battery(f'B1_{pair}_{scenario}', fac, fwd, reg, mask, fee_rt)
            all_results[res['name']] = res

        # B2 OI spike + flat price
        if stats[pair]:
            diag_b = {}
            mask, fac, fwd, reg = b2_oi_spike_flat_price(stats[pair], diag_b)
            diag_master[f'B2_{pair}'] = diag_b
            for scenario, fee_rt in FEE_SCENARIOS.items():
                res = battery(f'B2_{pair}_{scenario}', fac, fwd, reg, mask, fee_rt)
                all_results[res['name']] = res

        # B3 basis compression
        if spot_4h[pair] and perp_4h[pair]:
            diag_b = {}
            mask, fac, fwd, reg = b3_basis_compression(spot_4h[pair], perp_4h[pair], diag_b)
            diag_master[f'B3_{pair}'] = diag_b
            for scenario, fee_rt in FEE_SCENARIOS.items():
                res = battery(f'B3_{pair}_{scenario}', fac, fwd, reg, mask, fee_rt)
                all_results[res['name']] = res

        # D1 vol contraction → expansion
        diag_b = {}
        mask, fac, fwd, reg = d1_vol_contraction_expansion(perp_4h[pair], diag_b)
        diag_master[f'D1_{pair}'] = diag_b
        for scenario, fee_rt in FEE_SCENARIOS.items():
            res = battery(f'D1_{pair}_{scenario}', fac, fwd, reg, mask, fee_rt)
            all_results[res['name']] = res

        # D2 failed breakout
        diag_b = {}
        mask, fac, fwd, reg = d2_failed_breakout(perp_4h[pair], diag_b)
        diag_master[f'D2_{pair}'] = diag_b
        for scenario, fee_rt in FEE_SCENARIOS.items():
            res = battery(f'D2_{pair}_{scenario}', fac, fwd, reg, mask, fee_rt)
            all_results[res['name']] = res

    # Print
    # Universe-aggregated runs for B3 + D2 (most-firing factors per-pair)
    # Cross-sectional factor pooling: same factor formula, observations
    # aggregated across the 5-pair universe. NOT a new factor — standard
    # factor-model methodology.
    print()
    print("  ── Universe-aggregated pool (cross-sectional pooling, not new factors) ──")
    for fac_name, fac_fn, data_key in [
        ('B3_UNIVERSE', lambda p: b3_basis_compression(spot_4h[p], perp_4h[p], {})
                              if spot_4h[p] and perp_4h[p] else None,
         'spot+perp'),
        ('D2_UNIVERSE', lambda p: d2_failed_breakout(perp_4h[p], {}) if perp_4h[p] else None,
         'perp'),
    ]:
        pooled_factor: List[Optional[float]] = []
        pooled_fwd: List[Optional[float]] = []
        pooled_regimes: List[str] = []
        pooled_mask: List[bool] = []
        for pair in PAIRS:
            t = fac_fn(pair)
            if t is None:
                continue
            mask, fac, fwd, reg = t
            pooled_mask.extend(mask)
            pooled_factor.extend(fac)
            pooled_fwd.extend(fwd)
            pooled_regimes.extend(reg)
        for scenario, fee_rt in FEE_SCENARIOS.items():
            res = battery(f'{fac_name}_{scenario}', pooled_factor, pooled_fwd,
                          pooled_regimes, pooled_mask, fee_rt)
            all_results[res['name']] = res

    print()
    print(f"  {'Factor':<48} {'N':>5} {'IC':>8} {'t':>8} {'PF':>6} {'Q-bps':>8} {'MC%':>5} {'Reg':>4}  Status")
    print("  " + "─" * 100)
    passing = []
    insufficient = []
    failing = []
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
            failing.append(name)

    print()
    print(f"  Total combinations:  {len(all_results)}")
    print(f"  ✅ Passing:           {len(passing)}")
    print(f"  🟡 N<100:             {len(insufficient)}")
    print(f"  🛑 Killed after N:   {len(failing)}")

    summary = {
        'run_time': datetime.now(timezone.utc).isoformat(),
        'mode': 'L99_NATIVE_ONLY_MODE',
        'data_sources': 'Gate.io public REST only (spot, futures, funding, contract_stats)',
        'pairs': PAIRS,
        'L99_thresholds': {
            'IC_MIN': L99.IC_MIN, 'TSTAT_MIN': L99.TSTAT_MIN,
            'PF_MIN': L99.PF_MIN, 'QUINTILE_MIN_bps': L99.QUINTILE_MIN,
            'MC_STABILITY': L99.MC_STABILITY, 'REGIME_MIN': L99.REGIME_MIN,
            'MIN_OBS': L99.MIN_OBS,
        },
        'fee_scenarios': {k: f"{v * 10000} bps RT" for k, v in FEE_SCENARIOS.items()},
        'passing_count': len(passing),
        'insufficient_count': len(insufficient),
        'failing_count': len(failing),
        'total_combinations': len(all_results),
        'signal_funnels': diag_master,
        'results': all_results,
    }
    with open('native_factors_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print()
    print(f"  Results: native_factors_results.json")
    print("═" * 74)
    return summary


if __name__ == '__main__':
    main()
