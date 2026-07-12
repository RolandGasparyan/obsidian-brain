"""
champion.anti_overcompounding — Layer 4 §4 Anti-overcompounding law.

Implements Section 4 of L99_COMPOUNDING_VELOCITY.md.

Edge-independent. Pure state machine. NO exchange wiring.

Operator spec §4:

    If 3 consecutive losses at elevated risk
       OR daily loss > 3R
       OR weekly loss > 6R
    Immediate: reduce risk to baseline; disable acceleration for 10 trades.

    Capital protection overrides velocity.

This module tracks consecutive-loss streaks, daily/weekly R accumulators,
and a cooldown countdown. After any trigger fires, it requires
`cooldown_trades` subsequent trades before `can_accelerate()` returns True
again.

API:
  - register_trade(r_multiple, was_at_elevated_risk) → trigger?
  - is_in_cooldown() → bool
  - can_accelerate() → bool (= no cooldown active)
  - reset() → clear all state

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class AntiOvercompoundingConfig:
    """Operator-spec defaults from L99_COMPOUNDING_VELOCITY §4."""

    consecutive_loss_threshold: int = 3        # 3 consec losses at elevated risk → trigger
    daily_loss_r_threshold: float = 3.0        # daily R cumulative loss limit
    weekly_loss_r_threshold: float = 6.0       # weekly R cumulative loss limit
    cooldown_trades: int = 10                  # trades to wait after trigger

    def __post_init__(self) -> None:
        if self.consecutive_loss_threshold < 1:
            raise ValueError("consecutive_loss_threshold must be >= 1")
        if self.daily_loss_r_threshold <= 0:
            raise ValueError("daily_loss_r_threshold must be > 0")
        if self.weekly_loss_r_threshold <= 0:
            raise ValueError("weekly_loss_r_threshold must be > 0")
        if self.cooldown_trades < 0:
            raise ValueError("cooldown_trades must be >= 0")


# ─────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────

@dataclass
class AntiOvercompoundingState:
    consecutive_losses_at_elevated_risk: int = 0
    daily_r: float = 0.0
    weekly_r: float = 0.0
    cooldown_remaining: int = 0
    last_trigger_reason: Optional[str] = None
    last_daily_reset: datetime = field(default_factory=datetime.utcnow)
    last_weekly_reset: datetime = field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# MONITOR
# ─────────────────────────────────────────────

class AntiOvercompoundingMonitor:

    def __init__(self, config: Optional[AntiOvercompoundingConfig] = None):
        self.config = config or AntiOvercompoundingConfig()
        self.state = AntiOvercompoundingState()

    # ─────────────────────────────────────────

    def register_trade(
        self,
        r_multiple: float,
        was_at_elevated_risk: bool,
    ) -> Optional[str]:
        """Record a closed trade. Returns the trigger reason if a new
        anti-overcompounding trigger fired, else None.

        `was_at_elevated_risk` should be True when the trade was sized
        above baseline (i.e., during ACCELERATION mode). Consecutive-loss
        tracking only counts losses while at elevated risk per spec.
        """
        self._reset_if_needed()

        # Decrement cooldown FIRST so the just-registered trade counts
        # toward the cooldown countdown.
        if self.state.cooldown_remaining > 0:
            self.state.cooldown_remaining -= 1

        # Daily / weekly R accumulators
        self.state.daily_r += r_multiple
        self.state.weekly_r += r_multiple

        # Consecutive-loss tracking
        if r_multiple < 0 and was_at_elevated_risk:
            self.state.consecutive_losses_at_elevated_risk += 1
        elif r_multiple > 0:
            # A win breaks the consec-loss streak
            self.state.consecutive_losses_at_elevated_risk = 0
        # r_multiple == 0 (flat): no change to streak

        # Check triggers in spec priority order
        cfg = self.config

        if (
            self.state.consecutive_losses_at_elevated_risk
            >= cfg.consecutive_loss_threshold
        ):
            return self._trigger("consecutive_losses_at_elevated_risk")

        if self.state.daily_r <= -cfg.daily_loss_r_threshold:
            return self._trigger("daily_loss_exceeded")

        if self.state.weekly_r <= -cfg.weekly_loss_r_threshold:
            return self._trigger("weekly_loss_exceeded")

        return None

    # ─────────────────────────────────────────

    def _trigger(self, reason: str) -> str:
        """Activate the cooldown and reset all accumulators so the same
        trigger doesn't keep firing on subsequent trades while the
        accumulator is still beyond the threshold (e.g., daily_r=-3.5
        would otherwise re-fire on every next trade until 24h elapses).

        The 10-trade cooldown IS the punishment per spec §4; resetting
        accumulators on trigger is the operationally-correct way to
        avoid an infinite re-trigger loop.
        """
        self.state.cooldown_remaining = self.config.cooldown_trades
        self.state.last_trigger_reason = reason
        self.state.consecutive_losses_at_elevated_risk = 0
        self.state.daily_r = 0.0
        self.state.weekly_r = 0.0
        return reason

    # ─────────────────────────────────────────

    def is_in_cooldown(self) -> bool:
        return self.state.cooldown_remaining > 0

    def can_accelerate(self) -> bool:
        """True if no cooldown is active (i.e., ACCELERATION mode is
        permitted by this monitor)."""
        return not self.is_in_cooldown()

    # ─────────────────────────────────────────

    def _reset_if_needed(self) -> None:
        """Roll daily/weekly accumulators on elapsed-window expiry."""
        now = datetime.utcnow()
        if now - self.state.last_daily_reset > timedelta(days=1):
            self.state.daily_r = 0.0
            self.state.last_daily_reset = now
        if now - self.state.last_weekly_reset > timedelta(days=7):
            self.state.weekly_r = 0.0
            self.state.last_weekly_reset = now

    # ─────────────────────────────────────────

    def reset(self) -> None:
        """Manually clear all state. Useful for tests + post-cooldown hard
        resets."""
        self.state = AntiOvercompoundingState()
