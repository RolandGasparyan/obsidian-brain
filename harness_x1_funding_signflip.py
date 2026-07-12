"""
X1 — Funding rate sign-flip events (event-study, NOT continuous factor)

GENUINELY DISTINCT FROM B1 (NULL_REGISTRY row 7)
==================================================
B1 used continuous funding magnitude / mean-extreme as factor. X1 is an
EVENT STUDY: only the discrete moments when 8h funding rate crosses
zero. Different research geometry — sparse catalysts, not continuous
mean-reversion.

HYPOTHESIS
==========
When 8h funding rate flips sign:
  * +  → −  (longs were paying, now shorts pay): the previously-stressed
            long side has been forced out via funding payments. Expected
            mean-reversion: bounce upward → LONG entry.
  * −  → +  (shorts were paying, now longs pay): the previously-stressed
            short side has been forced out. Expected continuation /
            mean-reversion downward → SHORT entry.

Mechanism: flow + reflexive. Funding pays the dominant side of the book;
extended pressure leads to liquidations and forced unwinds; the moment
of sign-flip marks the "stress relief" inflection.

DISTINCT FROM 11 PRIOR NULLS
============================
  Row 7 (B1)  — used continuous funding mean. X1 uses sign-flip events only.
  Row 8 (B2)  — OI + flat-price; no funding signal.
  Row 9 (B3)  — basis z-score; no funding signal.
  Row 10 (A2) — stablecoin supply; no funding signal.
  Row 11 (V1) — VWAP gap; no funding signal.

FIRST USE OF THE HARNESS FOR REAL FACTOR PROPOSAL
=================================================
This script is the first non-regression use of `factor_research_harness.py`.
If it produces a NULL, the harness has done its job by mechanically
applying the 11 lessons. If it produces a CANDIDATE, operator must
review for §3 Stage 1 paper validation.

EXPECTED OUTCOME (honest)
=========================
Probably a 12th NULL given 11-prior empirical signal. The interesting
result either way is whether the harness output matches the analytical
expectation.

DISCIPLINE
==========
  - No live config integration regardless of result
  - Position 100% USDT throughout
  - 17 L99 modules dormant
"""
from __future__ import annotations

import bisect
import os
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from factor_research_harness import (
    FactorResearchHarness,
    FactorSpec,
    FactorResearchHarnessError,
)
from basis_extended_runner import fetch_4h_paginated_perp
from funding_extended_runner import fetch_funding_paginated


HORIZON_BARS = 18  # 3d at 4h cadence
REGIME_LOOKBACK_BARS = 180


def data_fetcher(contract: str) -> List[Dict[str, float]]:
    """Fetch 4h perp candles + 8h funding history; attach funding to each bar
    via lookahead-clean bisect (Rule 4 / look-ahead audit)."""
    bars = fetch_4h_paginated_perp(contract)
    if not bars:
        return []
    funding_hist = fetch_funding_paginated(contract)
    if not funding_hist:
        for b in bars:
            b['funding'] = None
        return bars

    funding_hist.sort(key=lambda x: x['ts'])
    funding_ts = [int(f['ts']) for f in funding_hist]
    funding_r = [float(f['r']) for f in funding_hist]

    for b in bars:
        bar_ts = int(b['ts'])
        idx = bisect.bisect_right(funding_ts, bar_ts) - 1
        b['funding'] = funding_r[idx] if idx >= 0 else None

    n_with_funding = sum(1 for b in bars if b['funding'] is not None)
    print(f"    {contract}: bars={len(bars)} bars_with_funding={n_with_funding} "
          f"funding_obs={len(funding_hist)}")
    return bars


def signal_builder(bars):
    """Detect funding sign-flips. mask=True at flip events.
    factor = current funding rate at flip moment.
    direction = +1 (LONG) on +→− flip, −1 (SHORT) on −→+ flip."""
    n = len(bars)
    closes = [b['c'] for b in bars]
    funding = [b.get('funding') for b in bars]

    mask = [False] * n
    directions: List[Optional[int]] = [None] * n
    factor: List[Optional[float]] = [None] * n

    for i in range(1, n):
        f_now = funding[i]
        f_prev = funding[i - 1]
        if f_now is None or f_prev is None:
            continue
        # Sign change requires actual crossing — equality on either side excluded
        if f_prev > 0 and f_now < 0:
            mask[i] = True
            directions[i] = +1
            factor[i] = f_now    # negative — places into Q1 quintile
        elif f_prev < 0 and f_now > 0:
            mask[i] = True
            directions[i] = -1
            factor[i] = f_now    # positive — places into Q5 quintile

    # SIGNED forward returns (Rule 1)
    fwd: Dict[str, List[Optional[float]]] = {}
    for h in (HORIZON_BARS, 30, 42):
        arr: List[Optional[float]] = [None] * n
        for i in range(n - h):
            if closes[i] > 0:
                arr[i] = (closes[i + h] - closes[i]) / closes[i] * 100
        fwd[str(h)] = arr

    # Regime label (180-bar trailing return)
    regimes: List[str] = []
    for i in range(n):
        if i < REGIME_LOOKBACK_BARS or closes[i - REGIME_LOOKBACK_BARS] <= 0:
            regimes.append('unknown')
        else:
            r = (closes[i] - closes[i - REGIME_LOOKBACK_BARS]) / \
                closes[i - REGIME_LOOKBACK_BARS] * 100
            if r > 10:
                regimes.append('bull')
            elif r < -10:
                regimes.append('bear')
            else:
                regimes.append('range')

    return mask, factor, fwd, regimes, directions


def main():
    spec = FactorSpec(
        name='X1_FUNDING_SIGNFLIP_EVENT',
        hypothesis=(
            'When 8h funding rate flips sign, the previously-stressed side has '
            'been forced out via funding payments; expected mean-reversion. '
            '+→− flip → LONG (longs cleared, bounce up); −→+ flip → SHORT.'
        ),
        mechanism='flow',
        decision_rule='mean_rev_long_q1_short_q5',
        is_signed=True,
        horizon_bars=HORIZON_BARS,
        pairs=['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'XRP_USDT', 'AVAX_USDT'],
        earliest_ts=1672531200,
        null_registry_distinction=(
            'Distinct from B1 (row 7): B1 used continuous funding magnitude as '
            'factor; X1 is event-study geometry — only discrete moments where '
            '8h funding crosses zero. Different signal cadence (sparse events '
            'vs continuous values) and different decision rule (paired '
            'long-on-+-flip / short-on-minus-flip vs Q5-Q1 spread on funding '
            'extremes).'
        ),
        cross_pair_min_share_sign=3,   # 3 of 5 — funding is mostly per-pair
    )

    harness = FactorResearchHarness(
        spec, output_dir=os.path.dirname(os.path.abspath(__file__))
    )
    harness.register_signal_builder(signal_builder)
    harness.register_data_fetcher(data_fetcher)

    try:
        out = harness.run()
    except FactorResearchHarnessError as e:
        print(f"\n  HARNESS REFUSED TO RUN:\n{e}")
        return

    print("\n  ── X1 FINAL ──")
    print(f"    Verdict: {out['verdict']}")
    print(f"    L99: {out['l99_passes']}/{out['l99_total']}")
    print(f"    §3.5: {out['gate_3_5_passes']}/{out['gate_3_5_total']} pairs")
    print(f"    Cross-pair sign share: {out['cross_pair_sign_share']}")
    print(f"    Position: 100% USDT (unchanged)")
    if out['verdict'] == 'NULL':
        print("\n  → Honest 12th NULL via the harness. Add row to NULL_REGISTRY.md.")
    else:
        print("\n  → CANDIDATE. Operator review required for §3 Stage 1 promotion.")


if __name__ == '__main__':
    main()
