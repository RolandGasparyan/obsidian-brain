"""
loss_cluster_breaker.py
-----------------------
Fast-reaction circuit breaker tuned for tournament-mode early-phase bleeding.

The existing TournamentRiskController has a simple streak cooldown:
    3 losses -> 15min cooldown.

That's fine for MID phase. For EARLY phase it's too slow - by the time you
hit 3 consecutive losses in aggressive mode, you may have bled 4-5% of
equity. This module adds:

1. Phase-aware streak triggers (EARLY: 2 losses -> 5min, MID: 3/15min, ENDGAME: 2/30min).
2. Loss *rate* detection: N losses within T minutes, regardless of streak
   (catches alternating win-loss-loss patterns that don't hit streak trigger).
3. Loss *magnitude* detection: cumulative PnL in last window below threshold.
4. Automatic cooldown extension if cluster repeats during cooldown.

Output: BreakerDecision with cooldown_seconds (0 = no break) and reason.
brain.py should short-circuit entry evaluation when cooldown_seconds > 0.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Deque, Optional

from .capital_phase_manager import Phase
from .usdt_domination_core import TradeEvent


class BreakerState(str, Enum):
    OPEN = "OPEN"           # breaker closed, trading allowed
    TRIPPED = "TRIPPED"     # breaker open, no new entries
    EXTENDED = "EXTENDED"   # cluster repeated during cooldown


@dataclass(frozen=True)
class _BreakerConfig:
    # Streak trigger
    streak_losses: int
    streak_cooldown_seconds: float
    # Rate trigger
    rate_losses: int
    rate_window_seconds: float
    rate_cooldown_seconds: float
    # Magnitude trigger (cumulative loss as fraction of equity over window)
    magnitude_pct: float
    magnitude_window_seconds: float
    magnitude_cooldown_seconds: float
    # Extension policy
    extension_multiplier: float  # if cluster during cooldown, extend by this


_CONFIGS = {
    Phase.EARLY: _BreakerConfig(
        streak_losses=2,
        streak_cooldown_seconds=5 * 60,
        rate_losses=3,
        rate_window_seconds=10 * 60,
        rate_cooldown_seconds=8 * 60,
        magnitude_pct=0.025,       # 2.5% equity lost triggers break
        magnitude_window_seconds=15 * 60,
        magnitude_cooldown_seconds=12 * 60,
        extension_multiplier=1.5,
    ),
    Phase.MID: _BreakerConfig(
        streak_losses=3,
        streak_cooldown_seconds=15 * 60,
        rate_losses=4,
        rate_window_seconds=20 * 60,
        rate_cooldown_seconds=18 * 60,
        magnitude_pct=0.020,
        magnitude_window_seconds=30 * 60,
        magnitude_cooldown_seconds=20 * 60,
        extension_multiplier=1.75,
    ),
    Phase.ENDGAME: _BreakerConfig(
        streak_losses=2,
        streak_cooldown_seconds=30 * 60,
        rate_losses=3,
        rate_window_seconds=30 * 60,
        rate_cooldown_seconds=45 * 60,
        magnitude_pct=0.010,       # tighter, protect the lead
        magnitude_window_seconds=45 * 60,
        magnitude_cooldown_seconds=60 * 60,
        extension_multiplier=2.0,
    ),
}


@dataclass
class BreakerDecision:
    state: BreakerState
    cooldown_seconds: float
    trigger: str
    cooldown_until_ts: float


@dataclass
class BreakerTelemetry:
    state: BreakerState
    cooldown_remaining_seconds: float
    current_streak: int
    losses_in_rate_window: int
    loss_magnitude_in_window: float
    last_trigger: str
    trips_last_24h: int


class LossClusterBreaker:
    """Thread-safe. Call on_close() for every closed trade, ask allow() before entry."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._events: Deque[TradeEvent] = deque(maxlen=500)
        self._cooldown_until: float = 0.0
        self._last_trigger: str = ""
        self._state: BreakerState = BreakerState.OPEN
        self._trip_history: Deque[float] = deque(maxlen=100)  # trip timestamps

    def on_close(self, event: TradeEvent, equity_usdt: float, phase: Phase) -> BreakerDecision:
        """Record the closed trade and re-evaluate breaker state."""
        with self._lock:
            self._events.append(event)
            cfg = _CONFIGS[phase]
            now = time.time()

            # If currently tripped and another loss happened - extend cooldown
            already_tripped = now < self._cooldown_until
            triggered = False
            trigger_reason = ""

            # Check streak (only consecutive losses from the tail)
            streak = self._current_loss_streak_locked()
            if streak >= cfg.streak_losses:
                triggered = True
                trigger_reason = f"streak_{streak}"
                cooldown = cfg.streak_cooldown_seconds

            # Check rate
            if not triggered:
                rate_losses = self._losses_in_window_locked(cfg.rate_window_seconds)
                if rate_losses >= cfg.rate_losses:
                    triggered = True
                    trigger_reason = f"rate_{rate_losses}_in_{int(cfg.rate_window_seconds/60)}m"
                    cooldown = cfg.rate_cooldown_seconds

            # Check magnitude
            if not triggered:
                mag_pct, mag_window_losses = self._loss_magnitude_locked(
                    cfg.magnitude_window_seconds, equity_usdt)
                if mag_pct >= cfg.magnitude_pct:
                    triggered = True
                    trigger_reason = f"magnitude_{mag_pct:.2%}"
                    cooldown = cfg.magnitude_cooldown_seconds

            if triggered:
                if already_tripped:
                    # extension
                    remaining = self._cooldown_until - now
                    extended_cooldown = max(cooldown, remaining) * cfg.extension_multiplier
                    self._cooldown_until = now + extended_cooldown
                    self._state = BreakerState.EXTENDED
                    self._last_trigger = f"{trigger_reason}_EXTENDED"
                else:
                    self._cooldown_until = now + cooldown
                    self._state = BreakerState.TRIPPED
                    self._last_trigger = trigger_reason
                    self._trip_history.append(now)

                return BreakerDecision(
                    state=self._state,
                    cooldown_seconds=self._cooldown_until - now,
                    trigger=self._last_trigger,
                    cooldown_until_ts=self._cooldown_until,
                )

            # No new trigger - if cooldown expired, reset state
            if now >= self._cooldown_until and self._state != BreakerState.OPEN:
                self._state = BreakerState.OPEN

            return BreakerDecision(
                state=self._state,
                cooldown_seconds=max(0.0, self._cooldown_until - now),
                trigger="none",
                cooldown_until_ts=self._cooldown_until,
            )

    def allow(self) -> bool:
        """Fast path called before entry evaluation. No mutation."""
        with self._lock:
            now = time.time()
            if now >= self._cooldown_until:
                # lazy state reset
                if self._state != BreakerState.OPEN:
                    self._state = BreakerState.OPEN
                return True
            return False

    def cooldown_remaining(self) -> float:
        with self._lock:
            return max(0.0, self._cooldown_until - time.time())

    def force_reset(self) -> None:
        """Manual reset hook for ops. Not called automatically."""
        with self._lock:
            self._cooldown_until = 0.0
            self._state = BreakerState.OPEN
            self._last_trigger = "manual_reset"

    # ---- internal helpers (caller holds lock) ----

    def _current_loss_streak_locked(self) -> int:
        streak = 0
        for e in reversed(self._events):
            if e.realized_pnl_usdt < 0:
                streak += 1
            else:
                break
        return streak

    def _losses_in_window_locked(self, window_seconds: float) -> int:
        cutoff = time.time() - window_seconds
        return sum(1 for e in self._events
                   if e.closed_ts >= cutoff and e.realized_pnl_usdt < 0)

    def _loss_magnitude_locked(
        self, window_seconds: float, equity_usdt: float,
    ) -> tuple[float, int]:
        cutoff = time.time() - window_seconds
        losses = [e.realized_pnl_usdt for e in self._events
                  if e.closed_ts >= cutoff and e.realized_pnl_usdt < 0]
        if not losses or equity_usdt <= 0:
            return 0.0, 0
        total_loss = abs(sum(losses))
        return total_loss / equity_usdt, len(losses)

    def telemetry(self, phase: Phase, equity_usdt: float) -> BreakerTelemetry:
        with self._lock:
            cfg = _CONFIGS[phase]
            now = time.time()
            trips_24h = sum(1 for ts in self._trip_history if ts >= now - 86400)
            streak = self._current_loss_streak_locked()
            rate = self._losses_in_window_locked(cfg.rate_window_seconds)
            mag, _ = self._loss_magnitude_locked(cfg.magnitude_window_seconds, equity_usdt)
            return BreakerTelemetry(
                state=self._state,
                cooldown_remaining_seconds=max(0.0, self._cooldown_until - now),
                current_streak=streak,
                losses_in_rate_window=rate,
                loss_magnitude_in_window=round(mag, 4),
                last_trigger=self._last_trigger,
                trips_last_24h=trips_24h,
            )
