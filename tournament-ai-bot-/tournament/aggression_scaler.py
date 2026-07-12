"""
aggression_scaler.py
--------------------
Velocity-tied adaptive aggression multiplier.

The phase manager gives you a phase-level risk multiplier (e.g., EARLY=1.25).
This module gives you a *dynamic* multiplier on top, driven by recent
compounding rate and rotation velocity.

Intuition: when the system is compounding hot (growth multiple climbing fast,
positive rotation velocity), lean in. When it's stalled or bleeding, fall back
to baseline. This is pro-cyclical by design - tournament mode is not portfolio
management, it's punching through a growth window.

Outputs: a multiplier in [floor, ceiling] that brain.py applies on top of
phase.risk_multiplier * risk.risk_multiplier. Capped hard to prevent runaway.

Safety: the scaler NEVER goes above 1.0 in ENDGAME. It NEVER goes below floor
even after a drawdown (that's the risk controller's job, not this one).
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Deque, Optional

from .capital_phase_manager import Phase


class AggressionMode(str, Enum):
    HOT = "HOT"
    WARM = "WARM"
    STEADY = "STEADY"
    COOL = "COOL"


@dataclass
class AggressionReading:
    multiplier: float
    mode: AggressionMode
    growth_velocity_per_hour: float   # d(growth_multiple)/dt in units/hour
    rotation_velocity: float          # from UsdtCore
    rationale: str


@dataclass(frozen=True)
class _PhaseAggressionConfig:
    floor: float          # minimum multiplier this module will apply
    ceiling: float        # maximum multiplier this module will apply
    hot_threshold: float  # growth velocity per hour above which we go HOT
    warm_threshold: float
    cool_threshold: float # below this (usually 0 or negative), go COOL


_PHASE_CONFIG = {
    # EARLY: lean in hard when hot, but don't go cold — early is for punching.
    Phase.EARLY: _PhaseAggressionConfig(
        floor=0.85, ceiling=1.35,
        hot_threshold=0.015,   # 1.5% equity/hour
        warm_threshold=0.005,  # 0.5% equity/hour
        cool_threshold=-0.003, # -0.3% equity/hour
    ),
    # MID: symmetric, modest range.
    Phase.MID: _PhaseAggressionConfig(
        floor=0.75, ceiling=1.15,
        hot_threshold=0.010,
        warm_threshold=0.003,
        cool_threshold=-0.002,
    ),
    # ENDGAME: asymmetric - ceiling is 1.0 flat. Cooling scales down aggressively.
    Phase.ENDGAME: _PhaseAggressionConfig(
        floor=0.50, ceiling=1.00,
        hot_threshold=0.008,
        warm_threshold=0.002,
        cool_threshold=-0.001,
    ),
}


@dataclass(frozen=True)
class _Sample:
    ts: float
    growth_multiple: float


class AggressionScaler:
    """Rolling growth velocity estimator + aggression mapper.

    Thread-safe. Feed it growth multiple samples periodically (e.g. every
    minute from launch.py's telemetry tick). It windows them to compute
    velocity over the last N minutes.
    """

    def __init__(
        self,
        window_minutes: float = 30.0,
        min_samples_for_velocity: int = 5,
    ) -> None:
        self._lock = RLock()
        self._window_seconds = window_minutes * 60.0
        self._min_samples = min_samples_for_velocity
        self._samples: Deque[_Sample] = deque(maxlen=500)

    def sample(self, growth_multiple: float) -> None:
        now = time.time()
        with self._lock:
            self._samples.append(_Sample(ts=now, growth_multiple=growth_multiple))
            # prune anything older than window
            cutoff = now - self._window_seconds
            while self._samples and self._samples[0].ts < cutoff:
                self._samples.popleft()

    def _growth_velocity_per_hour(self) -> float:
        with self._lock:
            if len(self._samples) < self._min_samples:
                return 0.0
            first = self._samples[0]
            last = self._samples[-1]
            dt_seconds = last.ts - first.ts
            # require at least 60 seconds of spread to compute velocity
            # (otherwise rapid back-to-back samples produce meaningless extremes)
            if dt_seconds < 60.0:
                return 0.0
            dt_hours = dt_seconds / 3600.0
            return (last.growth_multiple - first.growth_multiple) / dt_hours

    def read(
        self,
        phase: Phase,
        rotation_velocity: float,
    ) -> AggressionReading:
        cfg = _PHASE_CONFIG[phase]
        growth_vel = self._growth_velocity_per_hour()

        # Primary signal: growth velocity. Secondary: rotation velocity sign.
        # If growth velocity is insufficient sample, fall back to rotation.
        if growth_vel >= cfg.hot_threshold:
            mode = AggressionMode.HOT
            # scale multiplier linearly between warm and hot, capped at ceiling
            frac = min(1.0, (growth_vel - cfg.warm_threshold) /
                       max(cfg.hot_threshold - cfg.warm_threshold, 1e-9))
            mult = 1.0 + frac * (cfg.ceiling - 1.0)
        elif growth_vel >= cfg.warm_threshold:
            mode = AggressionMode.WARM
            frac = (growth_vel - cfg.warm_threshold) / max(
                cfg.hot_threshold - cfg.warm_threshold, 1e-9)
            mult = 1.0 + frac * (cfg.ceiling - 1.0) * 0.5
        elif growth_vel >= cfg.cool_threshold:
            mode = AggressionMode.STEADY
            mult = 1.0
        else:
            mode = AggressionMode.COOL
            # scale down toward floor as velocity goes more negative
            frac = min(1.0, (cfg.cool_threshold - growth_vel) / 0.01)
            mult = 1.0 - frac * (1.0 - cfg.floor)

        # Clamp to phase config
        mult = max(cfg.floor, min(cfg.ceiling, mult))

        # Rotation velocity tiebreaker: if growth_vel is ~0 but rotation_velocity
        # is positive, nudge up a little (system is making money without showing
        # on equity yet, possibly due to fees/slippage drag). Conservative +2%.
        if mode == AggressionMode.STEADY and rotation_velocity > 0.001:
            mult = min(cfg.ceiling, mult * 1.02)

        return AggressionReading(
            multiplier=round(mult, 3),
            mode=mode,
            growth_velocity_per_hour=round(growth_vel, 5),
            rotation_velocity=round(rotation_velocity, 5),
            rationale=(
                f"phase={phase.value} mode={mode.value} "
                f"growth_vel={growth_vel:.4f}/hr rot_vel={rotation_velocity:.4f}"
            ),
        )
