"""
champion.kelly_sizer — Layer 3 §1 Constrained Kelly Sizing.

Implements Sections 1.1, 1.2, 1.3 of L99_CAPITAL_MATHEMATICS.md.

Edge-independent. Pure math. NO exchange wiring. NO strategy dependency.

Classic Kelly:

    f* = (b·p - q) / b

where b = AvgWin/AvgLoss (reward-to-risk), p = win rate, q = 1 - p.

Constrained Kelly (Section 1.2):

    risk_per_trade = min(fractional_kelly, max_risk_per_trade)

where fractional_kelly is full / half / quarter Kelly per config.

Volatility-adjusted Kelly (Section 1.3):
  - If rolling drawdown > dd_reduction_threshold → multiply by dd_reduction_factor
  - If current rolling expectancy < baseline expectancy → freeze (return 0.0)

Classic Kelly is too volatile (Section 1.1 quote: "Full Kelly is too
volatile"). Operator-spec default uses Quarter Kelly with a hard 1%
absolute cap, matching Layer 5 §6 portfolio_risk_governor's
max_single_position threshold.

Per ADR-001 + ADR-003 (D7 expired): library only. Wiring into
gateio_executor.py requires validated edge first.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

# Valid fraction modes per Section 1.2
_FRACTION_MULTIPLIERS = {
    "full": 1.0,
    "half": 0.5,
    "quarter": 0.25,
}


@dataclass
class KellySizerConfig:
    """Operator-spec defaults from L99_CAPITAL_MATHEMATICS §1.2 + §1.3."""

    fraction_mode: str = "quarter"           # "full" | "half" | "quarter"
    max_risk_per_trade: float = 0.01         # 1% absolute hard cap
    dd_reduction_threshold: float = 0.10     # if rolling DD > this → halve Kelly
    dd_reduction_factor: float = 0.5         # the halving factor (Section 1.3)
    freeze_on_expectancy_decline: bool = True  # freeze if current E < baseline E

    def __post_init__(self) -> None:
        if self.fraction_mode not in _FRACTION_MULTIPLIERS:
            raise ValueError(
                f"fraction_mode must be one of {list(_FRACTION_MULTIPLIERS)}, "
                f"got {self.fraction_mode!r}"
            )
        if self.max_risk_per_trade <= 0 or self.max_risk_per_trade > 1:
            raise ValueError("max_risk_per_trade must be in (0, 1]")
        if not (0.0 <= self.dd_reduction_threshold <= 1.0):
            raise ValueError("dd_reduction_threshold must be in [0, 1]")
        if not (0.0 < self.dd_reduction_factor <= 1.0):
            raise ValueError("dd_reduction_factor must be in (0, 1]")


# ─────────────────────────────────────────────
# SIZER
# ─────────────────────────────────────────────

class KellySizer:
    """Stateless Kelly sizer. Inputs are passed per-call; no internal
    state to manage."""

    def __init__(self, config: Optional[KellySizerConfig] = None):
        self.config = config or KellySizerConfig()

    # ─────────────────────────────────────────

    @staticmethod
    def classic_kelly(win_rate: float, avg_win_r: float, avg_loss_r: float) -> float:
        """Classic Kelly formula. Returns the raw f* fraction.

        avg_loss_r is treated as an absolute magnitude (positive number).
        Returns can be:
          > 0  → positive expectancy; trade
          0    → break-even or undefined; do not trade
          < 0  → negative expectancy; do not trade (caller should clamp to 0)
        """
        if not 0.0 <= win_rate <= 1.0:
            raise ValueError("win_rate must be in [0, 1]")
        if avg_win_r < 0:
            raise ValueError("avg_win_r must be >= 0")
        if avg_loss_r <= 0:
            raise ValueError("avg_loss_r must be > 0")

        b = avg_win_r / avg_loss_r
        p = win_rate
        q = 1.0 - p
        if b == 0:
            # No reward → Kelly undefined; caller must not trade.
            return 0.0
        return (b * p - q) / b

    # ─────────────────────────────────────────

    def compute(
        self,
        win_rate: float,
        avg_win_r: float,
        avg_loss_r: float,
        rolling_dd: float = 0.0,
        baseline_expectancy: Optional[float] = None,
        current_expectancy: Optional[float] = None,
    ) -> float:
        """Return the recommended risk-per-trade fraction (constrained, capped).

        Returns 0.0 in any of:
          - Negative or zero raw Kelly (no edge)
          - Frozen by Section 1.3 (current_expectancy < baseline_expectancy
            and freeze_on_expectancy_decline=True)

        Otherwise:
          - Apply fraction_mode multiplier (full/half/quarter)
          - If rolling_dd > dd_reduction_threshold → multiply by dd_reduction_factor
          - Cap at max_risk_per_trade
        """
        # Section 1.3 expectancy freeze
        if (
            self.config.freeze_on_expectancy_decline
            and baseline_expectancy is not None
            and current_expectancy is not None
            and current_expectancy < baseline_expectancy
        ):
            return 0.0

        raw = self.classic_kelly(win_rate, avg_win_r, avg_loss_r)
        if raw <= 0:
            return 0.0

        # Section 1.2: fractional Kelly
        fractional = raw * _FRACTION_MULTIPLIERS[self.config.fraction_mode]

        # Section 1.3: vol-adjusted reduction on elevated DD
        if rolling_dd > self.config.dd_reduction_threshold:
            fractional *= self.config.dd_reduction_factor

        # Section 1.2: hard absolute cap
        return min(fractional, self.config.max_risk_per_trade)
