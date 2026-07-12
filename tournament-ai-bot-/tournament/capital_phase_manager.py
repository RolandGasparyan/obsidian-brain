"""
capital_phase_manager.py
------------------------
Maps current equity multiple -> capital phase -> risk/aggression directives.

Phases (defaults, override via config):
    EARLY      x < 1.5    aggressive, compounding priority
    MID        1.5 <= x < 3.0    controlled, reduce per-trade risk, keep velocity
    ENDGAME    x >= 3.0   protect the lead, elite setups only

The manager is advisory. It emits multipliers that sizer.py / guardian.py /
decision_pipeline.py already consume. It never mutates them directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Optional


class Phase(str, Enum):
    EARLY = "EARLY"
    MID = "MID"
    ENDGAME = "ENDGAME"


@dataclass(frozen=True)
class PhaseDirective:
    phase: Phase
    risk_multiplier: float           # multiply base per-trade risk % by this
    score_threshold_delta: float     # add to composite score threshold
    max_concurrent_trades: int
    daily_loss_cap_pct: float        # hard stop as % of equity
    rationale: str


DEFAULT_EARLY = PhaseDirective(
    phase=Phase.EARLY,
    risk_multiplier=1.25,
    score_threshold_delta=-2.0,
    max_concurrent_trades=2,
    daily_loss_cap_pct=0.035,
    rationale="early_phase_compound",
)

DEFAULT_MID = PhaseDirective(
    phase=Phase.MID,
    risk_multiplier=1.0,
    score_threshold_delta=0.0,
    max_concurrent_trades=2,
    daily_loss_cap_pct=0.025,
    rationale="mid_phase_controlled",
)

DEFAULT_ENDGAME = PhaseDirective(
    phase=Phase.ENDGAME,
    risk_multiplier=0.55,
    score_threshold_delta=6.0,
    max_concurrent_trades=1,
    daily_loss_cap_pct=0.015,
    rationale="endgame_protect_lead",
)


class CapitalPhaseManager:
    """Thread-safe. Re-evaluates on demand (daily cadence recommended)."""

    def __init__(
        self,
        early_max: float = 1.5,
        mid_max: float = 3.0,
        directives: Optional[dict[Phase, PhaseDirective]] = None,
        hysteresis: float = 0.05,
    ) -> None:
        self._lock = RLock()
        self._early_max = float(early_max)
        self._mid_max = float(mid_max)
        self._hysteresis = float(hysteresis)
        self._directives = directives or {
            Phase.EARLY: DEFAULT_EARLY,
            Phase.MID: DEFAULT_MID,
            Phase.ENDGAME: DEFAULT_ENDGAME,
        }
        self._current: Phase = Phase.EARLY

    def evaluate(self, growth_multiple: float) -> PhaseDirective:
        """Called by launch.py on a daily timer. Uses hysteresis to avoid flapping."""
        with self._lock:
            x = growth_multiple
            h = self._hysteresis

            # Determine target phase with hysteresis applied only at boundaries
            # we just crossed downward (prevent churn on equity wobble).
            if self._current == Phase.EARLY:
                if x >= self._early_max:
                    target = Phase.MID if x < self._mid_max else Phase.ENDGAME
                else:
                    target = Phase.EARLY
            elif self._current == Phase.MID:
                if x < self._early_max - h:
                    target = Phase.EARLY
                elif x >= self._mid_max:
                    target = Phase.ENDGAME
                else:
                    target = Phase.MID
            else:  # ENDGAME
                if x < self._mid_max - h:
                    target = Phase.MID if x >= self._early_max else Phase.EARLY
                else:
                    target = Phase.ENDGAME

            self._current = target
            return self._directives[target]

    def current(self) -> PhaseDirective:
        with self._lock:
            return self._directives[self._current]

    def override(self, phase: Phase, directive: PhaseDirective) -> None:
        with self._lock:
            self._directives[phase] = directive
