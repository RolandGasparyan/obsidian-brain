"""
champion.regime_breadth — Layer 2 §2 input feature #6: Market Breadth.

Implements input feature 6 of L99_REGIME_PROBABILITY.md §2:
"Market Breadth (% pairs above MA)".

Edge-independent. Pure math. NO exchange wiring.

Computes the fraction of monitored pairs whose latest close is above
their N-period moving average. Output normalized to [0, 1] for direct
use as a `RegimeFeatures.market_breadth` input.

Insufficient-data handling: pairs without enough history to compute MA
are excluded from the calculation. If all pairs are excluded, returns 0.5
(neutral) so the regime estimator doesn't get a noisy reading from
zero-pair denominators.

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class MarketBreadthConfig:
    ma_window: int = 20         # MA period (bars)
    min_history_bars: int = 20  # require this many closes before counting a pair

    def __post_init__(self) -> None:
        if self.ma_window < 2:
            raise ValueError("ma_window must be >= 2")
        if self.min_history_bars < self.ma_window:
            raise ValueError(
                "min_history_bars must be >= ma_window (cannot compute MA "
                "with fewer bars)"
            )


# ─────────────────────────────────────────────
# CALCULATOR
# ─────────────────────────────────────────────

class MarketBreadthCalculator:
    """Per-pair close-price ring buffer + breadth aggregation.

    Caller pushes each pair's latest close as it observes a new bar.
    Internal buffers maintain the last `ma_window` closes per pair.
    """

    def __init__(self, config: Optional[MarketBreadthConfig] = None):
        self.config = config or MarketBreadthConfig()
        self._closes: Dict[str, Deque[float]] = {}

    # ─────────────────────────────────────────

    def update_pair_close(self, symbol: str, close: float) -> None:
        """Record a new close for `symbol`. Buffer is bounded by ma_window."""
        if symbol not in self._closes:
            self._closes[symbol] = deque(maxlen=self.config.ma_window)
        self._closes[symbol].append(close)

    # ─────────────────────────────────────────

    def reset(self) -> None:
        """Clear all per-pair history. Useful for tests + day-rollover resets."""
        self._closes.clear()

    # ─────────────────────────────────────────

    def compute_breadth(self) -> float:
        """Return fraction of pairs with `latest_close > MA(ma_window)`.

        Pairs with fewer than `min_history_bars` closes are excluded. If no
        pair qualifies, returns 0.5 (neutral)."""
        cfg = self.config
        eligible = 0
        above = 0

        for closes in self._closes.values():
            if len(closes) < cfg.min_history_bars:
                continue
            eligible += 1
            ma = sum(closes) / len(closes)
            if closes[-1] > ma:
                above += 1

        if eligible == 0:
            return 0.5

        return above / eligible

    # ─────────────────────────────────────────

    def n_eligible_pairs(self) -> int:
        """Diagnostic: number of pairs currently contributing to breadth."""
        return sum(
            1 for c in self._closes.values()
            if len(c) >= self.config.min_history_bars
        )
