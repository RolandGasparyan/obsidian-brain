"""
champion.regime_liquidity — Layer 2 §2 input feature #8: Liquidity Stability.

Implements input feature 8 of L99_REGIME_PROBABILITY.md §2:
"Liquidity Stability Score".

Edge-independent. Pure math. NO exchange wiring.

Composite liquidity-quality metric in [0, 1] derived from:
  - Spread stability     (low coefficient-of-variation of bid/ask spread)
  - Depth stability      (low coefficient-of-variation of top-of-book depth)

Operator spec §7 ("Volatility Shock Filter"):

    "If volatility spike detected but spread widens / liquidity thins,
     reduce HIGH IMPULSE probability artificially.
     Impulse without liquidity = trap."

This module gives the regime probability estimator the liquidity-stability
signal it needs to compute that filter via its `liquidity_stability`
feature input.

Score interpretation:
  1.0 → spread + depth perfectly steady (high stability)
  0.0 → spread + depth wildly varying (thin/erratic — execution trap)
  0.5 → mixed / insufficient data

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class LiquidityStabilityConfig:
    window: int = 60                 # observations to keep in rolling buffer
    min_observations: int = 10       # require this many before producing non-neutral score
    cov_normalize_pivot: float = 0.5 # CoV value mapped to score 0.5 (calibration)

    def __post_init__(self) -> None:
        if self.window < 2:
            raise ValueError("window must be >= 2")
        if self.min_observations < 2:
            raise ValueError("min_observations must be >= 2")
        if self.cov_normalize_pivot <= 0:
            raise ValueError("cov_normalize_pivot must be > 0")


# ─────────────────────────────────────────────
# CALCULATOR
# ─────────────────────────────────────────────

class LiquidityStabilityCalculator:
    """Rolling spread + depth observer; produces a [0, 1] stability score.

    `update(spread_bps, depth_usdt)` is called per microstructure observation
    (e.g. 1Hz). `compute_stability()` returns the current composite score.
    """

    def __init__(self, config: Optional[LiquidityStabilityConfig] = None):
        self.config = config or LiquidityStabilityConfig()
        self._spreads: Deque[float] = deque(maxlen=self.config.window)
        self._depths: Deque[float] = deque(maxlen=self.config.window)

    # ─────────────────────────────────────────

    def update(self, spread_bps: float, depth_usdt: float) -> None:
        """Record one observation. Inputs must be non-negative."""
        if spread_bps < 0:
            raise ValueError("spread_bps must be >= 0")
        if depth_usdt < 0:
            raise ValueError("depth_usdt must be >= 0")
        self._spreads.append(spread_bps)
        self._depths.append(depth_usdt)

    # ─────────────────────────────────────────

    def reset(self) -> None:
        self._spreads.clear()
        self._depths.clear()

    # ─────────────────────────────────────────

    def compute_stability(self) -> float:
        """Composite liquidity-stability score in [0, 1].

        score = 0.5 × spread_stability + 0.5 × depth_stability

        where each component is mapped from coefficient-of-variation (CoV)
        through `1 / (1 + cov / pivot)`. Lower CoV → score closer to 1.
        """
        cfg = self.config
        if len(self._spreads) < cfg.min_observations:
            return 0.5

        spread_score = _stability_from_cov(self._spreads, cfg.cov_normalize_pivot)
        depth_score = _stability_from_cov(self._depths, cfg.cov_normalize_pivot)
        return 0.5 * spread_score + 0.5 * depth_score


# ─────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────

def _stability_from_cov(values: Deque[float], pivot: float) -> float:
    """Map coefficient-of-variation to a stability score in [0, 1].

    score = 1 / (1 + cov / pivot)

    - cov = 0    → score = 1.0   (perfectly steady)
    - cov = pivot → score = 0.5   (operator-defined "neutral" CoV)
    - cov → ∞    → score → 0.0   (wildly erratic)
    """
    if len(values) < 2:
        return 0.5
    mean = sum(values) / len(values)
    if mean == 0:
        # All zeros → perfectly steady at zero (or no data); call it neutral.
        return 0.5
    var = sum((v - mean) ** 2 for v in values) / len(values)
    sd = math.sqrt(var)
    cov = sd / abs(mean)
    return 1.0 / (1.0 + cov / pivot)
