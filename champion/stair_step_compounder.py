"""
champion.stair_step_compounder — Layer 4 §7 Stair-step compounding model.

Implements Section 7 of L99_COMPOUNDING_VELOCITY.md.

Edge-independent. Pure math. NO exchange wiring.

Operator spec §7:

    Instead of continuous compounding:
        Use staircase growth.
    Example:
        Capital grows 10%
        Lock new baseline
        Reset risk to original fraction
        Recalculate Kelly
        Resume compounding
    This prevents exponential blow-up cycles.

This module signals the "lock new baseline" event when equity grows by
`step_threshold_pct` since the most recent locked baseline. The caller
is responsible for the "reset risk fraction" + "recalculate Kelly" steps
on each step event — those are policy decisions outside the scope of
this counter.

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Float-precision tolerance for threshold comparisons. Required because
# `11_000.0 * 1.10` evaluates to 12_100.000000000002 in float-64; without
# epsilon, a current_equity of exactly 12_100 would not lock the step.
# 1e-9 is microscopic relative to any realistic equity value.
_STEP_EPSILON = 1e-9


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class StairStepConfig:
    step_threshold_pct: float = 0.10   # 10% growth from baseline triggers a step

    def __post_init__(self) -> None:
        if self.step_threshold_pct <= 0:
            raise ValueError("step_threshold_pct must be > 0")


# ─────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────

@dataclass
class StairStepState:
    initial_equity: float
    current_baseline: float    # most recently locked baseline
    n_steps: int = 0


# ─────────────────────────────────────────────
# DECISION
# ─────────────────────────────────────────────

@dataclass
class StairStepDecision:
    new_step_locked: bool
    current_baseline: float
    growth_since_baseline_pct: float
    n_steps: int


# ─────────────────────────────────────────────
# COMPOUNDER
# ─────────────────────────────────────────────

class StairStepCompounder:
    """Tracks step events as equity grows. Multiple steps can lock in a
    single `update()` call if growth has been substantial since the last
    poll (e.g., update was missed for many bars)."""

    def __init__(
        self,
        starting_equity: float,
        config: Optional[StairStepConfig] = None,
    ):
        if starting_equity <= 0:
            raise ValueError("starting_equity must be > 0")
        self.config = config or StairStepConfig()
        self.state = StairStepState(
            initial_equity=starting_equity,
            current_baseline=starting_equity,
        )

    # ─────────────────────────────────────────

    def update(self, current_equity: float) -> StairStepDecision:
        """Check if a new baseline should be locked; if so, lock it and
        return decision with `new_step_locked=True`."""
        if current_equity <= 0:
            raise ValueError("current_equity must be > 0")

        threshold = 1.0 + self.config.step_threshold_pct
        new_step_locked = False

        # If growth has been very large, lock multiple baselines in a row.
        # Caller may want to know it stepped multiple times.
        # Use epsilon tolerance for the threshold comparison (float math).
        while (
            current_equity
            >= self.state.current_baseline * threshold - _STEP_EPSILON
        ):
            self.state.current_baseline *= threshold
            self.state.n_steps += 1
            new_step_locked = True

        growth = (current_equity / self.state.current_baseline) - 1.0
        return StairStepDecision(
            new_step_locked=new_step_locked,
            current_baseline=self.state.current_baseline,
            growth_since_baseline_pct=growth,
            n_steps=self.state.n_steps,
        )

    # ─────────────────────────────────────────

    def reset(self, starting_equity: Optional[float] = None) -> None:
        """Reset state. If `starting_equity` is provided, use it as the new
        initial / baseline equity; otherwise re-use the original."""
        eq = starting_equity if starting_equity is not None else self.state.initial_equity
        if eq <= 0:
            raise ValueError("starting_equity must be > 0")
        self.state = StairStepState(initial_equity=eq, current_baseline=eq)
