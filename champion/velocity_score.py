"""
champion.velocity_score — Layer 4 §3 Velocity Score + scaling action.

Implements Section 3 of L99_COMPOUNDING_VELOCITY.md.

Edge-independent. Pure math. NO exchange wiring.

Velocity Score formula (operator spec §3):

    VS = (PF × E × IC_stability) / (DD% × Variance)

Scaling rule:

    VS > scaling_threshold AND stable for stable_trades_required trades
        → scale_up (+0.25R)
    scaling_threshold ≥ VS > reduction_threshold
        → hold
    reduction_threshold ≥ VS > freeze_threshold
        → reduce (×0.5)
    VS ≤ freeze_threshold
        → freeze

Edge cases:
  - DD = 0     → ideal stability; map to a tiny ε to keep VS finite & large
  - Variance=0 → ditto
  - E < 0      → VS negative → freeze (this is the spec-mandated behavior:
                 negative expectancy must not be amplified)

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────
# ACTION ENUM
# ─────────────────────────────────────────────

class VelocityScoreAction(Enum):
    SCALE_UP = "scale_up"
    HOLD = "hold"
    REDUCE = "reduce"
    FREEZE = "freeze"


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class VelocityScoreConfig:
    """Operator-spec defaults from L99_COMPOUNDING_VELOCITY §3."""

    scaling_threshold: float = 2.0      # VS > this → scale_up (with stability)
    reduction_threshold: float = 1.0    # VS < this → reduce 50%
    freeze_threshold: float = 0.0       # VS ≤ this → freeze
    stable_trades_required: int = 30    # for scale_up
    scaling_step_r: float = 0.25
    reduction_factor: float = 0.5
    epsilon: float = 1e-9               # for DD=0 / variance=0 substitutes

    def __post_init__(self) -> None:
        if not (self.freeze_threshold < self.reduction_threshold < self.scaling_threshold):
            raise ValueError(
                "must satisfy freeze_threshold < reduction_threshold < scaling_threshold"
            )
        if not 0 < self.reduction_factor <= 1:
            raise ValueError("reduction_factor must be in (0, 1]")
        if self.scaling_step_r <= 0:
            raise ValueError("scaling_step_r must be > 0")


# ─────────────────────────────────────────────
# RESULT
# ─────────────────────────────────────────────

@dataclass
class VelocityScoreResult:
    score: float
    action: VelocityScoreAction
    delta_risk_r: float       # +scaling_step_r / 0 / 0 / 0
    risk_multiplier: float    # 1.0 / 1.0 / reduction_factor / 0.0


# ─────────────────────────────────────────────
# CALCULATOR
# ─────────────────────────────────────────────

class VelocityScoreCalculator:
    """Stateless. Inputs are passed per-call."""

    def __init__(self, config: Optional[VelocityScoreConfig] = None):
        self.config = config or VelocityScoreConfig()

    # ─────────────────────────────────────────

    def compute(
        self,
        profit_factor: float,
        expectancy_r: float,
        ic_stability: float,
        drawdown_pct: float,
        variance: float,
    ) -> float:
        """Compute the raw VS = (PF × E × IC_stab) / (DD% × Variance).

        Substitutes ε for zero values of DD% or variance to avoid
        division by zero (those are 'ideal stability' inputs)."""
        eps = self.config.epsilon
        denom = max(drawdown_pct, eps) * max(variance, eps)
        return (profit_factor * expectancy_r * ic_stability) / denom

    # ─────────────────────────────────────────

    def evaluate(
        self,
        profit_factor: float,
        expectancy_r: float,
        ic_stability: float,
        drawdown_pct: float,
        variance: float,
        trades_at_current_state: int,
    ) -> VelocityScoreResult:
        """Compute VS, classify action."""
        cfg = self.config
        score = self.compute(
            profit_factor, expectancy_r, ic_stability, drawdown_pct, variance
        )

        if score <= cfg.freeze_threshold:
            return VelocityScoreResult(
                score=score,
                action=VelocityScoreAction.FREEZE,
                delta_risk_r=0.0,
                risk_multiplier=0.0,
            )

        if score < cfg.reduction_threshold:
            return VelocityScoreResult(
                score=score,
                action=VelocityScoreAction.REDUCE,
                delta_risk_r=0.0,
                risk_multiplier=cfg.reduction_factor,
            )

        if score < cfg.scaling_threshold:
            return VelocityScoreResult(
                score=score,
                action=VelocityScoreAction.HOLD,
                delta_risk_r=0.0,
                risk_multiplier=1.0,
            )

        # score >= scaling_threshold
        if trades_at_current_state >= cfg.stable_trades_required:
            return VelocityScoreResult(
                score=score,
                action=VelocityScoreAction.SCALE_UP,
                delta_risk_r=cfg.scaling_step_r,
                risk_multiplier=1.0,
            )

        # High VS but not enough stable trades yet — hold and wait.
        return VelocityScoreResult(
            score=score,
            action=VelocityScoreAction.HOLD,
            delta_risk_r=0.0,
            risk_multiplier=1.0,
        )
