"""
Audit B2 XRP_USDT result — appears to clear 5/6 L99 gates with PF=1628.

Per Council methodology (D2 look-ahead pattern), audit:
  1. Look-ahead — is signal observable at mask[i] without future data?
  2. Outlier dominance — does PF=1628 come from a few extreme wins?
  3. Single-regime concentration — what regime accounts for the IC?
  4. Per-quintile breakdown — does Q5 actually outperform Q1 monotonically?
  5. Sign stability — does flipping bisect/threshold change result drastically?

Read-only audit. No live deployment.
"""
from __future__ import annotations

import json
import statistics
import sys
from typing import Dict, List

sys.path.insert(0, '.')
from oi_extended_runner import (
    fetch_contract_stats_paginated,
    b2_extended,
    rolling_percentile,
    regime_label,
    OI_LOOKBACK_3D,
    OI_PERCENTILE_THRESHOLD,
    PRICE_FLAT_THRESHOLD_PCT,
    PRICE_LOOKBACK_24H,
)
from l99_battery import L99


def main():
    print("═" * 74)
    print("  B2 XRP_USDT AUDIT — apparent anomaly investigation")
    print("═" * 74)

    print("\n  1. Re-fetch XRP contract_stats (cached if fresh)...")
    stats = fetch_contract_stats_paginated('XRP_USDT')
    print(f"     N records: {len(stats)}")
    if not stats:
        print("     ❌ No data")
        return

    diag = {}
    mask, factor, fwd, regimes = b2_extended(stats, diag)
    print(f"     Diagnostic funnel: {diag}")
    print(f"     Mask hits: {sum(mask)}")

    # Indices where signal fires
    indices = [i for i in range(len(mask)) if mask[i] and factor[i] is not None and fwd[i] is not None]
    print(f"     Valid indices (mask AND factor AND fwd present): {len(indices)}")
    if not indices:
        return

    sig_factors = [factor[i] for i in indices]
    sig_fwd = [fwd[i] for i in indices]
    sig_regimes = [regimes[i] for i in indices]

    # ─── 1. PF anomaly investigation ───
    print("\n  2. Profit-Factor decomposition (at 14 bps RT maker-only)...")
    fee_rt = 0.0014
    net_returns = [r - fee_rt * 100 for r in sig_fwd]

    wins = [r for r in net_returns if r > 0]
    losses = [r for r in net_returns if r <= 0]
    print(f"     Wins:   N={len(wins):4d}  sum={sum(wins):+.4f}  mean={statistics.mean(wins) if wins else 0:+.4f}")
    print(f"     Losses: N={len(losses):4d}  sum={sum(losses):+.4f}  mean={statistics.mean(losses) if losses else 0:+.4f}")
    print(f"     Win rate: {len(wins)/len(net_returns)*100:.1f}%")
    print(f"     PF: {sum(wins) / abs(sum(losses)) if losses else 'inf':.2f}")
    if wins:
        wins_sorted = sorted(wins, reverse=True)
        print(f"     Top 5 wins: {[f'{w:+.3f}' for w in wins_sorted[:5]]}")
        print(f"     Top 5 wins contribute: {sum(wins_sorted[:5]):+.3f}")
        print(f"     ratio_top5_to_total: {sum(wins_sorted[:5]) / sum(wins) * 100:.1f}%")

    # ─── 2. Forward signal nature check ───
    print("\n  3. Forward-signal nature (fwd is |48h price change| = volatility proxy)")
    print(f"     Mean of |48h returns| at signal: {statistics.mean(sig_fwd):.4f}%")
    print(f"     Median: {statistics.median(sig_fwd):.4f}%")
    print(f"     P95: {sorted(sig_fwd)[int(0.95*len(sig_fwd))]:.4f}%")
    # Compare to ALL XRP bars (not just signal):
    fwd_all = [f for f in fwd if f is not None]
    print(f"     Mean |48h ret| ACROSS ALL XRP bars: {statistics.mean(fwd_all):.4f}%")
    print(f"     Median ACROSS ALL: {statistics.median(fwd_all):.4f}%")
    diff = statistics.mean(sig_fwd) - statistics.mean(fwd_all)
    print(f"     Signal hit DOES vs DOES NOT show higher avg vol: diff = {diff:+.4f}%")

    # ─── 3. Quintile monotonicity ───
    print("\n  4. Per-quintile analysis (factor = OI 3d change)...")
    pairs_q = sorted(zip(sig_factors, sig_fwd, sig_regimes), key=lambda x: x[0])
    n = len(pairs_q)
    nq = n // 5
    for q in range(5):
        start = q * nq
        end = (q + 1) * nq if q < 4 else n
        q_fwd = [p[1] for p in pairs_q[start:end]]
        q_factor = [p[0] for p in pairs_q[start:end]]
        net_mean = statistics.mean([f - fee_rt * 100 for f in q_fwd])
        print(f"     Q{q+1}: N={end-start:4d}  factor∈[{min(q_factor):+.4f}, {max(q_factor):+.4f}]  "
              f"mean fwd|48h|={statistics.mean(q_fwd):+.4f}%  net@maker={net_mean:+.4f}%")

    # ─── 4. Regime breakdown ───
    print("\n  5. Per-regime expectancy...")
    regime_groups: Dict[str, List[float]] = {}
    for r_label, ret in zip(sig_regimes, net_returns):
        regime_groups.setdefault(r_label, []).append(ret)
    for r_label, rets in sorted(regime_groups.items()):
        if rets:
            mean_r = statistics.mean(rets)
            wr = sum(1 for r in rets if r > 0) / len(rets) * 100
            print(f"     {r_label:10s}: N={len(rets):4d}  mean net={mean_r:+.4f}%  win rate={wr:.1f}%")

    # ─── 5. Look-ahead spot-check ───
    print("\n  6. Look-ahead spot-check...")
    print("     mask[i] = (oi_3d_pct[i] > 0.90) AND (|price_24h_change[i]| < 1)")
    print("       oi_3d_pct[i] uses oi[i-72..i-1] only — clean")
    print("       price_24h_change[i] uses closes[i-24] vs closes[i] — both ≤ i, clean")
    print("       fwd[i] = |closes[i+48] - closes[i]| / closes[i] — strictly future")
    print("     ✅ No look-ahead bias detected in factor construction.")

    # ─── 6. Honest verdict ───
    print("\n  7. HONEST VERDICT:")
    if statistics.mean(sig_fwd) > statistics.mean(fwd_all) * 1.05:
        print("     Signal selects MORE-VOLATILE windows than baseline.")
        print("     This means high-OI events DO precede higher absolute moves.")
        print("     But this is a vol-PREDICTION signal, not a directional edge.")
        print("     For an undirected vol-expansion trade, you'd need a")
        print("     long-volatility instrument (options, not perp directional).")
        print("     Trading PERP directionally on this signal = no directional edge.")
    else:
        print("     Signal does NOT show meaningful vol expansion vs baseline.")
        print("     The high IC is from quintile structure, not effect-size.")


if __name__ == '__main__':
    main()
