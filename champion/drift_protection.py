"""
champion.drift_protection — Layer 5 §7 Drift Protection Engine.

Implements operator's 2026-05-01 paste of the Drift Protection Engine.

Edge-independent. Consumes trade-journal-derived statistics only.
NO exchange wiring. Pure statistical gate.

Design philosophy (operator's words):

    Capital protection (Governor) protects money.
    Drift Protection protects truth.

Authoritative principle:

    If edge weakens → auto-disable.

API:
  - evaluate(**metrics) → bool (True = engine remains ENABLED, False = DISABLED)
  - reset()             → clear disabled flag and last reason

The engine is "sticky" once tripped: `state.disabled` and `state.last_disable_reason`
remain set across subsequent `evaluate()` calls. The return value of `evaluate()`
reflects the current call's verdict; callers that want pause-and-revalidate
semantics per L99_ALPHA_VALIDATION §2.7 should treat any False return as
terminal until manual `reset()`.

Per ADR-001 + ADR-003 (D7 expired): library only. Wiring into a live
executor requires validated edge first.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class DriftProtectionConfig:
    """Operator-spec defaults from L99_HYBRID_PORTFOLIO_GOD_MODE §7
    + L99_ALPHA_VALIDATION §2.7."""

    min_trades_required: int = 30          # below this → "not enough evidence yet"
    min_win_rate: float = 0.45             # < 0.45 → disable
    min_profit_factor: float = 1.1         # < 1.1  → disable
    min_expectancy_r: float = 0.0          # ≤ 0    → disable (non-positive)
    min_information_coefficient: float = 0.02   # < 0.02 → disable
    max_consecutive_losses: int = 8        # > 8   → disable
    max_drawdown_pct: float = 0.20         # > 20% → disable


# ─────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────

@dataclass
class DriftProtectionState:
    trades_observed: int = 0
    disabled: bool = False
    last_disable_reason: Optional[str] = None


# ─────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────

class DriftProtectionEngine:
    """Stateful drift detector; one instance per strategy engine."""

    def __init__(self, config: DriftProtectionConfig):
        self.config = config
        self.state = DriftProtectionState()

    # ─────────────────────────────────────────

    def evaluate(
        self,
        trades: int,
        win_rate: float,
        profit_factor: float,
        expectancy_r: float,
        information_coefficient: float,
        max_consecutive_losses: int,
        drawdown_pct: float,
    ) -> bool:
        """Returns True if engine remains ENABLED, False if disabled.

        Disable order matches L99_ALPHA_VALIDATION §2.7 priority:
        win_rate → profit_factor → expectancy → IC → consecutive losses → drawdown.

        First check: if trades < min_trades_required, return True (not enough
        evidence to disable). This prevents premature disable on a tiny sample
        where statistics are noise-dominated.
        """
        self.state.trades_observed = trades

        if trades < self.config.min_trades_required:
            return True  # Not enough evidence yet

        if win_rate < self.config.min_win_rate:
            return self._disable("win_rate_below_threshold")

        if profit_factor < self.config.min_profit_factor:
            return self._disable("profit_factor_below_threshold")

        if expectancy_r <= self.config.min_expectancy_r:
            return self._disable("non_positive_expectancy")

        if information_coefficient < self.config.min_information_coefficient:
            return self._disable("weak_information_coefficient")

        if max_consecutive_losses > self.config.max_consecutive_losses:
            return self._disable("excess_consecutive_losses")

        if drawdown_pct > self.config.max_drawdown_pct:
            return self._disable("excess_drawdown")

        return True

    # ─────────────────────────────────────────

    def _disable(self, reason: str) -> bool:
        self.state.disabled = True
        self.state.last_disable_reason = reason
        return False

    # ─────────────────────────────────────────

    def reset(self) -> None:
        """Clear disabled flag and last reason. Caller must have determined
        the underlying drift cause is resolved (i.e., revalidation passed)."""
        self.state.disabled = False
        self.state.last_disable_reason = None
