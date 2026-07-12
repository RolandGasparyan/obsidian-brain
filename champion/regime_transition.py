"""
champion.regime_transition — Layer 2 §6 Regime transition velocity tracker.

Implements Section 6 of L99_REGIME_PROBABILITY.md.

Edge-independent. Pure math. NO exchange wiring.

Tracks the rolling history of regime probability vectors and computes
velocity = current_prob - earliest_prob_in_window for each regime. If
any regime probability shifts by more than `rapid_shift_threshold`
(default 0.30) in the window, flags `is_rapid_shift = True`.

Operator spec quote:

    Track regime velocity:
      ΔP(R3) over time
      ΔP(R4) over time
    Rapid rise → early expansion
    Rapid drop → regime decay
    If regime probability shifts > 30% in short window:
        Reduce risk until stabilized.

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from champion.regime_probability import RegimeProbabilities


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class RegimeTransitionConfig:
    window: int = 12                       # observations in the rolling window
    rapid_shift_threshold: float = 0.30    # any |Δ| above this → rapid_shift flag

    def __post_init__(self) -> None:
        if self.window < 2:
            raise ValueError("window must be >= 2")
        if not 0.0 < self.rapid_shift_threshold <= 1.0:
            raise ValueError("rapid_shift_threshold must be in (0, 1]")


# ─────────────────────────────────────────────
# RESULT
# ─────────────────────────────────────────────

@dataclass
class RegimeVelocity:
    delta_dead: float
    delta_normal: float
    delta_expansion: float
    delta_high_impulse: float
    rapid_shift: bool
    n_observations: int


# ─────────────────────────────────────────────
# TRACKER
# ─────────────────────────────────────────────

class RegimeTransitionTracker:
    """Append-only ring buffer of recent RegimeProbabilities."""

    def __init__(self, config: Optional[RegimeTransitionConfig] = None):
        self.config = config or RegimeTransitionConfig()
        self._history: Deque[RegimeProbabilities] = deque(
            maxlen=self.config.window
        )

    # ─────────────────────────────────────────

    def add_observation(self, probs: RegimeProbabilities) -> None:
        self._history.append(probs)

    # ─────────────────────────────────────────

    def reset(self) -> None:
        self._history.clear()

    # ─────────────────────────────────────────

    def n_observations(self) -> int:
        return len(self._history)

    # ─────────────────────────────────────────

    def compute_velocity(self) -> RegimeVelocity:
        """Velocity = current - earliest. With a single observation, all
        deltas are 0 and rapid_shift is False."""
        n = len(self._history)
        if n < 2:
            return RegimeVelocity(0.0, 0.0, 0.0, 0.0, False, n)

        first = self._history[0]
        last = self._history[-1]

        d_dead = last.p_dead - first.p_dead
        d_normal = last.p_normal - first.p_normal
        d_expansion = last.p_expansion - first.p_expansion
        d_high = last.p_high_impulse - first.p_high_impulse

        threshold = self.config.rapid_shift_threshold
        rapid = (
            abs(d_dead) > threshold
            or abs(d_normal) > threshold
            or abs(d_expansion) > threshold
            or abs(d_high) > threshold
        )

        return RegimeVelocity(
            delta_dead=d_dead,
            delta_normal=d_normal,
            delta_expansion=d_expansion,
            delta_high_impulse=d_high,
            rapid_shift=rapid,
            n_observations=n,
        )
