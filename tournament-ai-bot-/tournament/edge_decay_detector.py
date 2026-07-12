"""
edge_decay_detector.py
----------------------
Detects when the strategy's edge is decaying statistically, before drawdown
forces a stop. Uses a segmented comparison: recent-half expectancy vs
prior-half expectancy, with a Welch's t-test style check on PnL distributions.

Returns EdgeStatus with verdict in:
    HEALTHY   - recent edge stable or improving
    SOFT_DECAY - recent expectancy below prior, not yet significant
    HARD_DECAY - recent expectancy significantly worse (p < 0.05 and delta large)

HARD_DECAY should trigger:
    - score threshold tightening (handled by performance_oracle)
    - pair re-ranking (pair_scorer can be flagged)
    - optional mode rotation (spot_champion -> tighter filters)
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from .usdt_domination_core import TradeEvent


class DecayVerdict(str, Enum):
    HEALTHY = "HEALTHY"
    SOFT_DECAY = "SOFT_DECAY"
    HARD_DECAY = "HARD_DECAY"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass
class EdgeStatus:
    verdict: DecayVerdict
    prior_expectancy: float
    recent_expectancy: float
    delta: float
    t_stat: float
    approx_p: float
    sample_size: int
    note: str


def _welch_t(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    """Welch's t-statistic and two-sided approx p via normal approximation.
    Good enough for n >= 15 per side; we don't need scipy in the hot path."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0, 1.0
    ma, mb = statistics.mean(a), statistics.mean(b)
    va = statistics.variance(a) if na > 1 else 0.0
    vb = statistics.variance(b) if nb > 1 else 0.0
    denom = math.sqrt(va / na + vb / nb)
    if denom == 0:
        return 0.0, 1.0
    t = (ma - mb) / denom
    # two-sided p via normal approx (|t| ~ z for large n)
    # erfc(|z|/sqrt(2)) gives two-sided p for standard normal
    z = abs(t)
    p = math.erfc(z / math.sqrt(2.0))
    return t, p


class EdgeDecayDetector:
    """Stateless - consumes a list of TradeEvent, returns a status."""

    def __init__(
        self,
        min_total_sample: int = 40,
        p_threshold_hard: float = 0.05,
        min_delta_r: float = 0.25,
    ) -> None:
        self._min_total = min_total_sample
        self._p_hard = p_threshold_hard
        self._min_delta = min_delta_r

    def evaluate(self, events: Sequence[TradeEvent]) -> EdgeStatus:
        n = len(events)
        if n < self._min_total:
            return EdgeStatus(
                DecayVerdict.INSUFFICIENT, 0.0, 0.0, 0.0, 0.0, 1.0, n,
                f"need {self._min_total}, have {n}",
            )

        # split in half by time (events assumed chronological; sort to be safe)
        ordered = sorted(events, key=lambda e: e.closed_ts)
        mid = n // 2
        prior = [e.realized_pnl_usdt for e in ordered[:mid]]
        recent = [e.realized_pnl_usdt for e in ordered[mid:]]

        prior_exp = statistics.mean(prior)
        recent_exp = statistics.mean(recent)
        delta = recent_exp - prior_exp

        t, p = _welch_t(recent, prior)  # positive t = recent better

        # express delta in R using avg loss magnitude across full sample
        losses = [x for x in prior + recent if x < 0]
        avg_loss_abs = abs(statistics.mean(losses)) if losses else 1.0
        delta_r = delta / avg_loss_abs if avg_loss_abs > 0 else 0.0

        if t >= 0:
            return EdgeStatus(
                DecayVerdict.HEALTHY, prior_exp, recent_exp, delta, t, p, n,
                "recent >= prior",
            )

        # recent is worse
        if p < self._p_hard and abs(delta_r) >= self._min_delta:
            verdict = DecayVerdict.HARD_DECAY
            note = f"p={p:.4f}, delta_r={delta_r:.3f}"
        else:
            verdict = DecayVerdict.SOFT_DECAY
            note = f"p={p:.4f}, delta_r={delta_r:.3f}"

        return EdgeStatus(
            verdict=verdict,
            prior_expectancy=round(prior_exp, 4),
            recent_expectancy=round(recent_exp, 4),
            delta=round(delta, 4),
            t_stat=round(t, 3),
            approx_p=round(p, 4),
            sample_size=n,
            note=note,
        )
