"""
champion.velocity_state_machine — Layer 4 §2 Velocity States.

Implements Section 2 of L99_COMPOUNDING_VELOCITY.md.

Edge-independent. Pure logic state machine. NO exchange wiring. NO strategy
dependency.

Three velocity states with falsifiable transition rules per spec:

    STATE 1 — CONSERVATIVE
        Conditions: PF < 1.3 OR rolling-50 barely passes OR DD > 10%
        Risk:       0.5R
        Scaling:    NONE
        Purpose:    Stabilize capital

    STATE 2 — BASELINE
        Conditions: PF in [1.3, 1.5], stable IC, DD < 10%
        Risk:       0.75–1R
        Scaling:    Slow compounding allowed
        Purpose:    Controlled growth

    STATE 3 — ACCELERATION
        Conditions: PF ≥ 1.6, rolling-200 stable, IC consistent, DD < 8%,
                    regime = EXPANSION
        Risk:       Up to 1.25R (+0.25R steps)
        Purpose:    Maximize geometric growth during edge dominance

Decision priority:
  ACCELERATION (most-restrictive gates) → BASELINE → CONSERVATIVE.

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────
# STATE ENUM
# ─────────────────────────────────────────────

class VelocityState(Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BASELINE = "BASELINE"
    ACCELERATION = "ACCELERATION"


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class VelocityStateMachineConfig:
    """Operator-spec defaults from L99_COMPOUNDING_VELOCITY §2."""

    # CONSERVATIVE entry gate
    conservative_pf_max: float = 1.3        # PF < this → CONSERVATIVE
    conservative_dd_max: float = 0.10       # DD > this → CONSERVATIVE
    conservative_min_trades: int = 50       # below this → "rolling 50 barely passes"

    # BASELINE band
    baseline_pf_min: float = 1.3
    baseline_pf_max: float = 1.5            # exceeded → ACCELERATION (if other gates pass)
    baseline_dd_max: float = 0.10

    # ACCELERATION gates
    acceleration_pf_min: float = 1.6
    acceleration_dd_max: float = 0.08
    acceleration_min_trades: int = 200      # rolling-200 stable
    acceleration_requires_expansion: bool = True

    # Risk fractions per state (in R)
    conservative_risk_r: float = 0.5
    baseline_risk_r: float = 1.0            # default mid-band; caller may use 0.75-1
    acceleration_risk_r_cap: float = 1.25

    def __post_init__(self) -> None:
        if not (
            0 < self.conservative_pf_max
            <= self.baseline_pf_min
            <= self.baseline_pf_max
            < self.acceleration_pf_min
        ):
            raise ValueError(
                "PF thresholds must satisfy: "
                "conservative_pf_max <= baseline_pf_min <= baseline_pf_max < acceleration_pf_min"
            )
        if not (0 <= self.acceleration_dd_max < self.baseline_dd_max <= 1):
            raise ValueError(
                "DD thresholds must satisfy: acceleration_dd_max < baseline_dd_max"
            )


# ─────────────────────────────────────────────
# DECISION OUTPUT
# ─────────────────────────────────────────────

@dataclass
class VelocityStateDecision:
    state: VelocityState
    risk_r: float
    reason: str


# ─────────────────────────────────────────────
# STATE MACHINE
# ─────────────────────────────────────────────

class VelocityStateMachine:
    """Stateful velocity tier classifier. `current_state` reflects the most
    recent `evaluate()` outcome and is exposed for monitoring."""

    def __init__(self, config: Optional[VelocityStateMachineConfig] = None):
        self.config = config or VelocityStateMachineConfig()
        self.current_state: VelocityState = VelocityState.CONSERVATIVE

    # ─────────────────────────────────────────

    def evaluate(
        self,
        profit_factor: float,
        rolling_dd: float,
        trades_count: int,
        ic_stable: bool = False,
        regime_is_expansion: bool = False,
    ) -> VelocityStateDecision:
        """Pick the highest-tier state whose gates are satisfied. Defaults to
        CONSERVATIVE."""
        cfg = self.config

        # Tier 3: ACCELERATION
        accel_ok = (
            profit_factor >= cfg.acceleration_pf_min
            and rolling_dd < cfg.acceleration_dd_max
            and trades_count >= cfg.acceleration_min_trades
            and ic_stable
            and (regime_is_expansion or not cfg.acceleration_requires_expansion)
        )
        if accel_ok:
            self.current_state = VelocityState.ACCELERATION
            return VelocityStateDecision(
                state=VelocityState.ACCELERATION,
                risk_r=cfg.acceleration_risk_r_cap,
                reason="all_acceleration_gates_passed",
            )

        # Tier 2: BASELINE
        baseline_ok = (
            cfg.baseline_pf_min <= profit_factor <= cfg.baseline_pf_max
            and rolling_dd < cfg.baseline_dd_max
            and trades_count >= cfg.conservative_min_trades
        )
        if baseline_ok:
            self.current_state = VelocityState.BASELINE
            return VelocityStateDecision(
                state=VelocityState.BASELINE,
                risk_r=cfg.baseline_risk_r,
                reason="baseline_band",
            )

        # Tier 1: CONSERVATIVE (default fallback)
        reasons = []
        if profit_factor < cfg.conservative_pf_max:
            reasons.append(f"pf={profit_factor:.3f}<{cfg.conservative_pf_max}")
        if rolling_dd > cfg.conservative_dd_max:
            reasons.append(f"dd={rolling_dd:.3f}>{cfg.conservative_dd_max}")
        if trades_count < cfg.conservative_min_trades:
            reasons.append(f"trades={trades_count}<{cfg.conservative_min_trades}")

        reason = "; ".join(reasons) if reasons else "no_higher_tier_gate_passed"
        self.current_state = VelocityState.CONSERVATIVE
        return VelocityStateDecision(
            state=VelocityState.CONSERVATIVE,
            risk_r=cfg.conservative_risk_r,
            reason=reason,
        )
