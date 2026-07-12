"""
L99 — FACTOR VALIDATION BATTERY

Operator-pasted 2026-05-02. Runs full 7-condition validation on real Gate.io data.
Every factor that fails any condition is killed immediately.

Priority order per blueprint: B2 → B1 → C2

Per ADR-001 + discipline framework: this module is a validation/diagnostic tool.
NOT wired to any live executor. Run with `python3 l99_battery.py`.

Required input file: `l99_raw_data.json` with structure:
    {
      "funding": {"BTC_USDT": [{"t": ..., "r": ...}, ...], ...},
      "spot":    {"BTC_USDT": [[ts, vol, close, high, low, open, ...], ...], ...},
      "stats":   {"BTC_USDT": [{"time": ..., "open_interest": ..., "mark_price": ...}, ...], ...}
    }

If `l99_raw_data.json` is missing, the script will fail with FileNotFoundError;
this is the documented blocker — operator must collect data before battery runs.
"""
from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════
# VALIDATION THRESHOLDS (from L99 blueprint)
# ═══════════════════════════════════════════════════════════════
class L99:
    IC_MIN = 0.04        # |Information Coefficient| ≥ 0.04
    TSTAT_MIN = 2.0      # t-statistic ≥ 2.0
    PF_MIN = 1.30        # Profit Factor ≥ 1.3
    QUINTILE_MIN = 60.0  # Q5−Q1 ≥ 60 bps after fees (was 0.60 — unit-inconsistent bug; fixed 2026-05-05)
    MC_STABILITY = 0.80  # 80% of MC runs must be profitable
    REGIME_MIN = 2       # must survive in ≥2 regimes
    FEE_RT = 0.0025      # 0.25% round-trip
    MIN_OBS = 100        # minimum observations for statistical validity


# ═══════════════════════════════════════════════════════════════
# CORE STATISTICS
# ═══════════════════════════════════════════════════════════════

def zscore(series: List[float], lookback: int = 30) -> List[Optional[float]]:
    """Rolling z-score over lookback window."""
    n = len(series)
    result: List[Optional[float]] = [None] * n
    for i in range(lookback, n):
        window = series[i - lookback:i]
        mu = statistics.mean(window)
        sd = statistics.stdev(window) if len(window) > 1 else 1e-9
        result[i] = (series[i] - mu) / sd if sd > 0 else 0.0
    return result


def rolling_mean(series: List[float], n: int) -> List[Optional[float]]:
    result: List[Optional[float]] = [None] * len(series)
    for i in range(n - 1, len(series)):
        result[i] = sum(series[i - n + 1:i + 1]) / n
    return result


def rolling_corr(x: List[float], y: List[float], n: int) -> List[Optional[float]]:
    """Pearson correlation over rolling window."""
    assert len(x) == len(y)
    result: List[Optional[float]] = [None] * len(x)
    for i in range(n - 1, len(x)):
        wx = x[i - n + 1:i + 1]
        wy = y[i - n + 1:i + 1]
        mx = statistics.mean(wx)
        my = statistics.mean(wy)
        num = sum((a - mx) * (b - my) for a, b in zip(wx, wy))
        dx = math.sqrt(sum((a - mx) ** 2 for a in wx))
        dy = math.sqrt(sum((b - my) ** 2 for b in wy))
        result[i] = num / (dx * dy) if dx * dy > 0 else 0.0
    return result


def tstat(values: List[float]) -> float:
    """One-sample t-statistic against H0: mean = 0."""
    if len(values) < 2:
        return 0.0
    mu = statistics.mean(values)
    se = statistics.stdev(values) / math.sqrt(len(values))
    return mu / se if se > 0 else 0.0


def ic(factor: List[float], forward: List[float]) -> float:
    """Rank IC (Spearman) between factor scores and forward returns."""
    pairs = [(f, r) for f, r in zip(factor, forward)
             if f is not None and r is not None]
    if len(pairs) < 10:
        return 0.0

    def rank(vals):
        s = sorted(enumerate(vals), key=lambda x: x[1])
        r = [0] * len(vals)
        for rank_i, (orig_i, _) in enumerate(s):
            r[orig_i] = rank_i + 1
        return r

    fs, rs = zip(*pairs)
    rf = rank(list(fs))
    rr = rank(list(rs))
    mf = statistics.mean(rf)
    mr = statistics.mean(rr)
    num = sum((a - mf) * (b - mr) for a, b in zip(rf, rr))
    df = math.sqrt(sum((a - mf) ** 2 for a in rf))
    dr = math.sqrt(sum((b - mr) ** 2 for b in rr))
    return num / (df * dr) if df * dr > 0 else 0.0


def profit_factor(returns: List[float], fee: float = L99.FEE_RT) -> float:
    net = [r - fee * 100 for r in returns]
    wins = [r for r in net if r > 0]
    losses = [r for r in net if r <= 0]
    if not wins or not losses:
        return 0.0
    return sum(wins) / abs(sum(losses))


def quintile_spread(factor: List[Optional[float]],
                    forward: List[float]) -> float:
    """Q5-Q1 spread in BPS after fees (fixed 2026-05-05).

    A Q5−Q1 trade is TWO trades (long Q5 + short Q1), each paying its own
    round-trip fee. So the spread net of fees deducts 2× round-trip.

    Units: forward returns are in PERCENT (e.g., 0.50 = 0.50%). To convert
    spread in percent → bps, multiply by 100. To convert FEE_RT (decimal
    fraction, e.g., 0.0025) → bps, multiply by 10000. Then × 2 for the
    two-leg spread trade.

    Previous bug: deducted `FEE_RT * 100 * 2 = 0.5` (interpreted as 0.5 bps),
    which was 100× too small — fees were effectively not deducted.
    """
    pairs = [(f, r) for f, r in zip(factor, forward)
             if f is not None and r is not None]
    if len(pairs) < 20:
        return 0.0
    pairs.sort(key=lambda x: x[0])
    n = len(pairs)
    q = max(1, n // 5)
    q1_ret = [p[1] for p in pairs[:q]]
    q5_ret = [p[1] for p in pairs[-q:]]
    spread_pct = statistics.mean(q5_ret) - statistics.mean(q1_ret)
    spread_bps = spread_pct * 100 - L99.FEE_RT * 10000 * 2
    return spread_bps


def monte_carlo(returns: List[float], n_sim: int = 500,
                seed: int = 42) -> float:
    """Fraction of bootstrap runs that are profitable after fees."""
    import random
    rng = random.Random(seed)
    net = [r - L99.FEE_RT * 100 for r in returns]
    wins = 0
    for _ in range(n_sim):
        sample = [rng.choice(net) for _ in range(len(net))]
        if sum(sample) > 0:
            wins += 1
    return wins / n_sim


# ═══════════════════════════════════════════════════════════════
# DATA LOADER
# ═══════════════════════════════════════════════════════════════

def load() -> dict:
    with open('l99_raw_data.json') as f:
        return json.load(f)


def align_funding_to_price(funding_list: List[Dict],
                           spot_bars: List[List]) -> List[Dict]:
    """Align 8h funding settlements to 8h spot candles."""
    price_rows = []
    for row in spot_bars:
        ts = int(row[0])
        c = float(row[2])
        price_rows.append((ts, c))
    price_rows.sort()

    price_map = {ts: c for ts, c in price_rows}
    price_sorted = [ts for ts, _ in price_rows]

    funding_map: Dict[int, float] = {}
    for x in funding_list:
        t = int(x['t'])
        t_norm = (t // (8 * 3600)) * (8 * 3600)
        funding_map[t_norm] = float(x['r'])

    aligned = []
    for i in range(len(price_sorted) - 3):
        ts = price_sorted[i]
        ts_norm = (ts // (8 * 3600)) * (8 * 3600)
        if ts_norm not in funding_map:
            continue
        c = price_map[ts]
        c_1 = price_map.get(price_sorted[i + 1], c)
        c_3 = price_map.get(price_sorted[i + 3], c)
        aligned.append({
            'ts': ts,
            'funding': funding_map[ts_norm],
            'close': c,
            'fwd_8h': (c_1 - c) / c * 100,
            'fwd_24h': (c_3 - c) / c * 100,
        })
    return aligned


# ═══════════════════════════════════════════════════════════════
# FACTOR TESTS
# ═══════════════════════════════════════════════════════════════

@dataclass
class FactorResult:
    name: str
    n: int
    ic_val: float
    tstat_val: float
    pf_val: float
    quintile_bps: float
    mc_stability: float
    regime_count: int
    passes: bool
    killed_by: List[str]
    signal_returns: List[float] = field(default_factory=list)
    notes: str = ""

    def print(self):
        status = "✅ PASS" if self.passes else "❌ KILL"
        print(f"\n  {status} — {self.name}")
        print(f"  {'─' * 60}")
        ic_ok = "✅" if abs(self.ic_val) >= L99.IC_MIN else "❌"
        ts_ok = "✅" if abs(self.tstat_val) >= L99.TSTAT_MIN else "❌"
        pf_ok = "✅" if self.pf_val >= L99.PF_MIN else "❌"
        q_ok = "✅" if self.quintile_bps >= L99.QUINTILE_MIN else "❌"
        mc_ok = "✅" if self.mc_stability >= L99.MC_STABILITY else "❌"
        reg_ok = "✅" if self.regime_count >= L99.REGIME_MIN else "❌"
        print(f"  {ic_ok} IC:              {self.ic_val:+.4f}  (need |IC| ≥ {L99.IC_MIN})")
        print(f"  {ts_ok} t-stat:          {self.tstat_val:+.4f}  (need |t| ≥ {L99.TSTAT_MIN})")
        print(f"  {pf_ok} Profit Factor:   {self.pf_val:.4f}   (need PF ≥ {L99.PF_MIN})")
        print(f"  {q_ok} Q5−Q1 (bps):     {self.quintile_bps:+.2f}    (need ≥ {L99.QUINTILE_MIN} bps)")
        print(f"  {mc_ok} MC stability:    {self.mc_stability * 100:.1f}%     (need ≥ {L99.MC_STABILITY * 100:.0f}%)")
        print(f"  {reg_ok} Regime count:   {self.regime_count}         (need ≥ {L99.REGIME_MIN})")
        print(f"  N signals: {self.n}")
        if self.killed_by:
            print(f"  Killed by: {', '.join(self.killed_by)}")
        if self.notes:
            print(f"  Notes: {self.notes}")


def run_battery(name: str, factor_vals: List[Optional[float]],
                forward_8h: List[float], forward_24h: List[float],
                regime_labels: List[str],
                signal_mask: List[bool]) -> FactorResult:
    """Run all L99 conditions on a factor."""
    sig_ret_8h = [forward_8h[i] for i in range(len(signal_mask)) if signal_mask[i]]
    sig_ret_24h = [forward_24h[i] for i in range(len(signal_mask)) if signal_mask[i]]
    n = len(sig_ret_8h)

    killed_by: List[str] = []

    if n < L99.MIN_OBS:
        return FactorResult(
            name=name, n=n, ic_val=0, tstat_val=0, pf_val=0,
            quintile_bps=0, mc_stability=0, regime_count=0,
            passes=False, killed_by=[f"N={n} < {L99.MIN_OBS} minimum"],
            notes=f"Need {L99.MIN_OBS - n} more observations"
        )

    ic_v = ic(
        [factor_vals[i] for i in range(len(signal_mask)) if signal_mask[i]],
        sig_ret_24h,
    )
    ts_v = tstat(sig_ret_24h)
    pf_v = profit_factor(sig_ret_24h)
    qs_v = quintile_spread(factor_vals, forward_24h)
    mc_v = monte_carlo(sig_ret_24h) if sig_ret_24h else 0.0

    sig_regimes = [regime_labels[i] for i in range(len(signal_mask)) if signal_mask[i]]
    regime_ret: Dict[str, List[float]] = {}
    for r_label, ret in zip(sig_regimes, sig_ret_24h):
        regime_ret.setdefault(r_label, []).append(ret)
    reg_pos = sum(1 for rets in regime_ret.values()
                  if len(rets) >= 5 and statistics.mean(rets) > L99.FEE_RT * 100)
    reg_count = reg_pos

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

    passes = len(killed_by) == 0

    return FactorResult(
        name=name, n=n, ic_val=ic_v, tstat_val=ts_v,
        pf_val=pf_v, quintile_bps=qs_v, mc_stability=mc_v,
        regime_count=reg_count, passes=passes,
        killed_by=killed_by, signal_returns=sig_ret_24h
    )


# ═══════════════════════════════════════════════════════════════
# FACTOR IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════

def classify_regime(returns_window: List[float]) -> str:
    if len(returns_window) < 5:
        return 'unknown'
    total = sum(returns_window)
    vol = statistics.stdev(returns_window) if len(returns_window) > 1 else 0
    if total > 2.0:
        return 'bull'
    if total < -2.0:
        return 'bear'
    if vol < 0.5:
        return 'range'
    return 'volatile'


def test_B2_funding_extreme(data: dict) -> List[FactorResult]:
    """B2 — Funding Extreme Mean Reversion"""
    print("\n  ── B2: Funding Extreme Mean Reversion ──")
    results: List[FactorResult] = []
    for sym in ['BTC_USDT', 'ETH_USDT', 'SOL_USDT']:
        funding_list = data['funding'].get(sym, [])
        spot_list = data['spot'].get(sym, [])
        if not funding_list or not spot_list:
            print(f"  {sym}: no data")
            continue

        aligned = align_funding_to_price(funding_list, spot_list)
        if len(aligned) < 20:
            print(f"  {sym}: only {len(aligned)} aligned obs")
            continue

        funding_series = [x['funding'] for x in aligned]
        fwd_8h = [x['fwd_8h'] for x in aligned]
        fwd_24h = [x['fwd_24h'] for x in aligned]

        zs = zscore(funding_series, lookback=min(21, len(funding_series) // 4))

        regimes = []
        for i in range(len(aligned)):
            window = [x['fwd_8h'] for x in aligned[max(0, i - 10):i + 1]]
            regimes.append(classify_regime(window))

        for threshold, direction, label in [
            (2.0, -1, f"B2_{sym}_pos2sig_reversal"),
            (-2.0, +1, f"B2_{sym}_neg2sig_reversal"),
            (1.5, -1, f"B2_{sym}_pos1.5sig_reversal"),
            (-1.5, +1, f"B2_{sym}_neg1.5sig_reversal"),
        ]:
            mask = []
            for i, z in enumerate(zs):
                if z is None:
                    mask.append(False)
                elif direction == -1:
                    mask.append(z >= threshold)
                else:
                    mask.append(z <= threshold)

            fwd_use = [direction * r for r in fwd_24h]
            result = run_battery(label, zs, fwd_8h, fwd_use, regimes, mask)
            results.append(result)

    return results


def test_B1_oi_flat_price(data: dict) -> List[FactorResult]:
    """B1 — OI + Flat Price Divergence"""
    print("\n  ── B1: OI + Flat Price Divergence ──")
    results: List[FactorResult] = []

    for sym in ['BTC_USDT', 'ETH_USDT']:
        stats_list = data['stats'].get(sym, [])
        spot_list = data['spot'].get(sym, [])
        if not stats_list or not spot_list:
            continue

        oi_rows = []
        for x in stats_list:
            try:
                oi_rows.append({
                    'ts': int(x['time']),
                    'oi': float(x.get('open_interest', 0) or 0),
                    'mp': float(x.get('mark_price', 0) or 0),
                    'liq_long': float(x.get('long_liq_usd_new', 0) or 0),
                    'liq_short': float(x.get('short_liq_usd_new', 0) or 0),
                    'lsr': float(x.get('lsr_taker', 0) or 0),
                })
            except Exception:
                continue
        oi_rows.sort(key=lambda x: x['ts'])

        if len(oi_rows) < 30:
            continue

        oi_series = [x['oi'] for x in oi_rows]
        mp_series = [x['mp'] for x in oi_rows]
        lsr_series = [x['lsr'] for x in oi_rows]

        oi_z = zscore(oi_series, lookback=min(30, len(oi_series) // 3))

        mp_chg: List[Optional[float]] = [None] * 3
        for i in range(3, len(mp_series)):
            if mp_series[i - 3] > 0:
                mp_chg.append((mp_series[i] - mp_series[i - 3]) / mp_series[i - 3] * 100)
            else:
                mp_chg.append(None)

        fwd_24h: List[Optional[float]] = [None] * len(mp_series)
        for i in range(len(mp_series) - 3):
            if mp_series[i] > 0:
                fwd_24h[i] = (mp_series[i + 3] - mp_series[i]) / mp_series[i] * 100

        fwd_48h: List[Optional[float]] = [None] * len(mp_series)
        for i in range(len(mp_series) - 6):
            if mp_series[i] > 0:
                fwd_48h[i] = abs((mp_series[i + 6] - mp_series[i]) / mp_series[i] * 100)

        regimes = []
        for i in range(len(oi_rows)):
            window = [mp_series[j] for j in range(max(0, i - 10), i + 1)]
            if len(window) > 2:
                chg = (window[-1] - window[0]) / window[0] * 100 if window[0] > 0 else 0
                regimes.append('bull' if chg > 2 else 'bear' if chg < -2 else 'range')
            else:
                regimes.append('unknown')

        mask_b1 = [
            (oi_z[i] is not None and oi_z[i] > 2.0
             and mp_chg[i] is not None and abs(mp_chg[i]) < 1.0)
            for i in range(len(oi_rows))
        ]

        fwd_clean = [r if r is not None else 0 for r in fwd_48h]
        result = run_battery(
            f"B1_{sym}_OI_flat_volatility", oi_z,
            fwd_clean, fwd_clean, regimes, mask_b1,
        )
        results.append(result)

        lsr_z = zscore(lsr_series, lookback=min(21, len(lsr_series) // 3))
        fwd_dir = [r if r is not None else 0 for r in fwd_24h]
        mask_lsr = [lsr_z[i] is not None and lsr_z[i] > 1.5 for i in range(len(lsr_z))]
        fwd_lsr = [-r for r in fwd_dir]
        result_lsr = run_battery(
            f"B1_{sym}_LSR_extreme", lsr_z, fwd_dir, fwd_lsr, regimes, mask_lsr,
        )
        results.append(result_lsr)

    return results


def test_C2_vol_regime(data: dict) -> List[FactorResult]:
    """C2 — Volatility Regime Transition"""
    print("\n  ── C2: Volatility Regime Transition ──")
    results: List[FactorResult] = []

    for sym in ['BTC_USDT']:
        spot_list = data['spot'].get(sym, [])
        if not spot_list:
            continue

        bars = sorted(spot_list, key=lambda x: int(x[0]))
        closes = [float(x[2]) for x in bars]
        highs = [float(x[3]) for x in bars]
        lows = [float(x[4]) for x in bars]

        tr = [highs[0] - lows[0]]
        for i in range(1, len(bars)):
            tr.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            ))

        atr14: List[Optional[float]] = [None] * len(tr)
        if len(tr) >= 14:
            atr14[13] = sum(tr[:14]) / 14
            for i in range(14, len(tr)):
                atr14[i] = (atr14[i - 1] * 13 + tr[i]) / 14

        atr_pct: List[Optional[float]] = [None] * len(atr14)
        for i in range(42, len(atr14)):
            if atr14[i] is None:
                continue
            window = [v for v in atr14[i - 42:i] if v is not None]
            if not window:
                continue
            rank = sum(1 for v in window if v <= atr14[i])
            atr_pct[i] = rank / len(window) * 100

        regime_cross = [False] * len(atr_pct)
        for i in range(1, len(atr_pct)):
            if (atr_pct[i] is not None and atr_pct[i - 1] is not None
                    and atr_pct[i - 1] < 30 and atr_pct[i] > 70):
                regime_cross[i] = True

        fwd_24h: List[Optional[float]] = [None] * len(closes)
        fwd_48h: List[Optional[float]] = [None] * len(closes)
        for i in range(len(closes) - 3):
            if closes[i] > 0:
                fwd_24h[i] = (closes[i + 3] - closes[i]) / closes[i] * 100
                if i + 6 < len(closes):
                    fwd_48h[i] = (closes[i + 6] - closes[i]) / closes[i] * 100

        regimes = []
        for i in range(len(bars)):
            w = closes[max(0, i - 15):i + 1]
            if len(w) > 2:
                c = (w[-1] - w[0]) / w[0] * 100 if w[0] > 0 else 0
                regimes.append('bull' if c > 3 else 'bear' if c < -3 else 'range')
            else:
                regimes.append('unknown')

        fwd_abs = [abs(r) if r is not None else 0 for r in fwd_48h]
        result = run_battery(
            f"C2_{sym}_vol_expansion", atr_pct,
            [r or 0 for r in fwd_24h], fwd_abs, regimes, regime_cross,
        )
        results.append(result)

        mask_high = [p is not None and p > 80 for p in atr_pct]
        fwd_rev = [-(r or 0) for r in fwd_24h]
        result2 = run_battery(
            f"C2_{sym}_high_vol_reversion", atr_pct,
            [r or 0 for r in fwd_24h], fwd_rev, regimes, mask_high,
        )
        results.append(result2)

    return results


# ═══════════════════════════════════════════════════════════════
# MAIN RUN
# ═══════════════════════════════════════════════════════════════

def main():
    print()
    print("╔" + "═" * 72 + "╗")
    print("║  L99 — FACTOR VALIDATION BATTERY                                      ║")
    print("║  Priority: B2 → B1 → C2  |  Kill any that fail any condition          ║")
    print("╚" + "═" * 72 + "╝")

    try:
        data = load()
    except FileNotFoundError:
        print("\n  🛑 l99_raw_data.json NOT FOUND")
        print()
        print("  This script requires real Gate.io data. Run a collector first:")
        print("    - Spot OHLCV bars (8h)")
        print("    - Funding rates (per 8h settlement)")
        print("    - Stats (open interest, mark price, LSR)")
        print()
        print("  Expected JSON structure:")
        print('    {"funding": {...}, "spot": {...}, "stats": {...}}')
        print()
        print("  Until then: POSITION = 100% USDT.")
        return [], []

    print(f"\n  Data loaded:")
    for sym in ['BTC_USDT', 'ETH_USDT', 'SOL_USDT']:
        nf = len(data['funding'].get(sym, []))
        ns = len(data['spot'].get(sym, []))
        nst = len(data['stats'].get(sym, []))
        print(f"    {sym}: funding={nf} spot={ns} stats={nst}")

    print(f"\n  L99 Kill thresholds:")
    print(f"    |IC| ≥ {L99.IC_MIN} | t-stat ≥ {L99.TSTAT_MIN} | PF ≥ {L99.PF_MIN}")
    print(f"    Q5-Q1 ≥ {L99.QUINTILE_MIN}bps | MC ≥ {L99.MC_STABILITY * 100:.0f}% | Regimes ≥ {L99.REGIME_MIN}")
    print(f"    Min observations: {L99.MIN_OBS}")

    b2 = test_B2_funding_extreme(data)
    b1 = test_B1_oi_flat_price(data)
    c2 = test_C2_vol_regime(data)
    all_results = b2 + b1 + c2

    print("\n\n" + "═" * 74)
    print("  BATTERY RESULTS")
    print("═" * 74)

    passed = [r for r in all_results if r.passes]
    failed = [r for r in all_results if not r.passes]

    for r in all_results:
        r.print()

    print("\n\n" + "─" * 74)
    print(f"  {'Factor':<38} {'N':>5} {'IC':>7} {'t':>7} {'PF':>6} {'Q5-Q1':>7} {'MC%':>6} {'Status'}")
    print("  " + "─" * 72)
    for r in all_results:
        st = "✅ PASS" if r.passes else "❌ KILL"
        print(f"  {r.name:<38} {r.n:>5} "
              f"{r.ic_val:>+7.4f} {r.tstat_val:>+7.3f} "
              f"{r.pf_val:>6.3f} {r.quintile_bps:>+7.2f} "
              f"{r.mc_stability * 100:>5.1f}% {st}")

    print()
    print(f"  PASSED: {len(passed)}/{len(all_results)}")
    print()

    if passed:
        print("  SURVIVING SIGNALS:")
        for r in passed:
            print(f"    → {r.name}  Kelly-eligible: YES")
    else:
        print("  NO SIGNALS PASS THE L99 BATTERY")
        print()
        print("  FINDING DETAILS:")
        kill_counts: Dict[str, int] = {}
        for r in failed:
            for k in r.killed_by:
                for filt in ['IC', 't=', 'PF', 'Q5', 'MC', 'Regime', 'N=']:
                    if filt in k:
                        kill_counts[filt] = kill_counts.get(filt, 0) + 1
        for filt, count in sorted(kill_counts.items(), key=lambda x: -x[1]):
            print(f"    Killed by {filt:12}: {count} signals")
        print()
        print("  POSITION: 100% USDT — no validated edge on available data.")

    summary = {
        'run_time': datetime.now(timezone.utc).isoformat(),
        'passed': len(passed),
        'total': len(all_results),
        'position': 'TRADE' if passed else 'USDT',
        'factors': [
            {
                'name': r.name, 'n': r.n, 'ic': r.ic_val, 'tstat': r.tstat_val,
                'pf': r.pf_val, 'q_bps': r.quintile_bps, 'mc': r.mc_stability,
                'passes': r.passes, 'killed_by': r.killed_by,
            }
            for r in all_results
        ],
    }
    with open('l99_battery_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Results saved: l99_battery_results.json")
    print("═" * 74)

    return passed, failed


if __name__ == '__main__':
    main()
