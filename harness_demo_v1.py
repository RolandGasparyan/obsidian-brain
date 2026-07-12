"""
harness_demo_v1.py — re-run V1 (VWAP-gap mean-rev) through the harness.

Purpose: regression test. The harness must produce the SAME 11th-NULL
verdict that the ad-hoc `v1_vwap_gap.py` runner produced. If the harness
output disagrees materially with the prior runner, the harness has a bug.

This script does NOT introduce new factor research. V1 is already row 11
of NULL_REGISTRY.md. The harness re-tests it strictly to validate that
the harness itself reproduces the canonical NULL verdict mechanically.
"""
from __future__ import annotations

import os
import statistics
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from factor_research_harness import (
    FactorResearchHarness,
    FactorSpec,
    FactorResearchHarnessError,
)
from basis_extended_runner import fetch_4h_paginated_perp


VWAP_LOOKBACK_BARS = 6
Z_LOOKBACK_BARS = 180
Z_THRESHOLD = 2.0
HORIZON_BARS = 18  # 3d at 4h


def _rolling_vwap(closes, volumes, lookback):
    out: List[Optional[float]] = [None] * len(closes)
    for i in range(lookback, len(closes)):
        denom = sum(volumes[i - lookback:i])
        if denom <= 0:
            continue
        out[i] = sum(c * v for c, v in zip(
            closes[i - lookback:i], volumes[i - lookback:i])) / denom
    return out


def _gap_bps(closes, vwap):
    out: List[Optional[float]] = [None] * len(closes)
    for i, (c, v) in enumerate(zip(closes, vwap)):
        if v is not None and v > 0:
            out[i] = (c - v) / v * 10000.0
    return out


def _rolling_z(series, lookback):
    out: List[Optional[float]] = [None] * len(series)
    for i in range(lookback, len(series)):
        w = [x for x in series[i - lookback:i] if x is not None]
        if len(w) < lookback // 2:
            continue
        mu = statistics.mean(w)
        sd = statistics.pstdev(w)
        if sd <= 0 or series[i] is None:
            continue
        out[i] = (series[i] - mu) / sd
    return out


def _regime(closes, i, lookback=180):
    if i < lookback or closes[i - lookback] <= 0:
        return 'unknown'
    ret = (closes[i] - closes[i - lookback]) / closes[i - lookback] * 100
    if ret > 10: return 'bull'
    if ret < -10: return 'bear'
    return 'range'


def signal_builder(bars):
    closes = [b['c'] for b in bars]
    volumes = [b['v'] for b in bars]
    vwap = _rolling_vwap(closes, volumes, VWAP_LOOKBACK_BARS)
    gap = _gap_bps(closes, vwap)
    z = _rolling_z(gap, Z_LOOKBACK_BARS)

    n = len(bars)
    mask = [False] * n
    directions: List[Optional[int]] = [None] * n
    for i, zv in enumerate(z):
        if zv is None:
            continue
        if zv > Z_THRESHOLD:
            mask[i] = True
            directions[i] = -1   # short — mean-rev
        elif zv < -Z_THRESHOLD:
            mask[i] = True
            directions[i] = +1   # long — mean-rev

    fwd: Dict[str, List[Optional[float]]] = {}
    for h in (HORIZON_BARS, 30, 42):
        arr: List[Optional[float]] = [None] * n
        for i in range(n - h):
            if closes[i] > 0:
                arr[i] = (closes[i + h] - closes[i]) / closes[i] * 100
        fwd[str(h)] = arr

    regimes = [_regime(closes, i) for i in range(n)]
    return mask, z, fwd, regimes, directions


def main():
    spec = FactorSpec(
        name='V1_VWAP_GAP_MEAN_REV_HARNESS_REGRESSION',
        hypothesis='4h close-to-VWAP_24h gap z-score reverts to mean — '
                   'large positive gap predicts negative forward return.',
        mechanism='mechanical',
        decision_rule='mean_rev_long_q1_short_q5',
        is_signed=True,
        horizon_bars=HORIZON_BARS,
        pairs=['ETH_USDT', 'SOL_USDT', 'XRP_USDT'],
        earliest_ts=1672531200,
        null_registry_distinction=(
            'Distinct from V1 row 11 only by execution path: same hypothesis '
            'and decision rule, run through harness as regression test.'
        ),
        cross_pair_min_share_sign=2,
    )
    harness = FactorResearchHarness(
        spec, output_dir=os.path.dirname(os.path.abspath(__file__))
    )
    harness.register_signal_builder(signal_builder)
    harness.register_data_fetcher(fetch_4h_paginated_perp)

    try:
        out = harness.run()
    except FactorResearchHarnessError as e:
        print(f"\n  HARNESS REFUSED TO RUN:\n{e}")
        return

    # Regression assertion: this must produce a NULL — V1 is already in registry.
    assert out['verdict'] == 'NULL', (
        f"REGRESSION FAILURE — harness produced {out['verdict']} for V1 "
        f"which is canonically NULL. Harness has a bug or methodology drift."
    )
    print("\n  ✅ Regression assertion: harness reproduced V1's NULL verdict.")
    print("  Harness validated. Future factor research can use it directly.")


if __name__ == '__main__':
    main()
