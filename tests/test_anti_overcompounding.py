"""
Unit tests for champion.anti_overcompounding (Layer 4 §4).
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.anti_overcompounding import (
    AntiOvercompoundingConfig,
    AntiOvercompoundingMonitor,
)


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

class TestConfig:
    def test_defaults_match_spec(self):
        cfg = AntiOvercompoundingConfig()
        assert cfg.consecutive_loss_threshold == 3
        assert cfg.daily_loss_r_threshold == 3.0
        assert cfg.weekly_loss_r_threshold == 6.0
        assert cfg.cooldown_trades == 10

    def test_invalid_consec_threshold_rejected(self):
        with pytest.raises(ValueError):
            AntiOvercompoundingConfig(consecutive_loss_threshold=0)

    def test_invalid_daily_threshold_rejected(self):
        with pytest.raises(ValueError):
            AntiOvercompoundingConfig(daily_loss_r_threshold=0)

    def test_invalid_weekly_threshold_rejected(self):
        with pytest.raises(ValueError):
            AntiOvercompoundingConfig(weekly_loss_r_threshold=-1)

    def test_invalid_cooldown_rejected(self):
        with pytest.raises(ValueError):
            AntiOvercompoundingConfig(cooldown_trades=-1)


# ─────────────────────────────────────────────
# Initial state
# ─────────────────────────────────────────────

class TestInitialState:
    def test_initial_state_clean(self):
        m = AntiOvercompoundingMonitor()
        assert m.is_in_cooldown() is False
        assert m.can_accelerate() is True
        assert m.state.consecutive_losses_at_elevated_risk == 0
        assert m.state.daily_r == 0.0
        assert m.state.weekly_r == 0.0
        assert m.state.last_trigger_reason is None


# ─────────────────────────────────────────────
# Consecutive loss trigger
# ─────────────────────────────────────────────

class TestConsecutiveLossTrigger:
    def test_3_consec_at_elevated_risk_triggers(self):
        m = AntiOvercompoundingMonitor()
        assert m.register_trade(-1.0, was_at_elevated_risk=True) is None
        assert m.register_trade(-1.0, was_at_elevated_risk=True) is None
        reason = m.register_trade(-1.0, was_at_elevated_risk=True)
        assert reason == "consecutive_losses_at_elevated_risk"
        assert m.is_in_cooldown() is True

    def test_3_consec_NOT_at_elevated_risk_does_not_trigger(self):
        m = AntiOvercompoundingMonitor()
        # Default daily limit is 3R; -0.5R × 3 = -1.5R → daily not triggered
        for _ in range(3):
            assert m.register_trade(-0.5, was_at_elevated_risk=False) is None
        assert m.is_in_cooldown() is False

    def test_win_breaks_consec_streak(self):
        m = AntiOvercompoundingMonitor()
        m.register_trade(-1.0, was_at_elevated_risk=True)
        m.register_trade(-1.0, was_at_elevated_risk=True)
        m.register_trade(0.5, was_at_elevated_risk=True)  # win breaks streak
        # Now 2 more losses should NOT trigger (streak was reset to 0)
        reason = m.register_trade(-0.3, was_at_elevated_risk=True)
        assert reason is None
        reason = m.register_trade(-0.3, was_at_elevated_risk=True)
        assert reason is None
        assert m.is_in_cooldown() is False


# ─────────────────────────────────────────────
# Daily loss trigger
# ─────────────────────────────────────────────

class TestDailyLossTrigger:
    def test_daily_loss_3R_triggers(self):
        m = AntiOvercompoundingMonitor()
        m.register_trade(-1.0, was_at_elevated_risk=False)
        m.register_trade(-1.0, was_at_elevated_risk=False)
        # Cumulative -2R; one more -1.5R → -3.5R triggers
        reason = m.register_trade(-1.5, was_at_elevated_risk=False)
        assert reason == "daily_loss_exceeded"
        assert m.is_in_cooldown() is True

    def test_daily_below_3R_does_not_trigger(self):
        m = AntiOvercompoundingMonitor()
        m.register_trade(-1.0, was_at_elevated_risk=False)
        m.register_trade(-1.5, was_at_elevated_risk=False)
        # -2.5R total, below 3R limit
        assert m.is_in_cooldown() is False


# ─────────────────────────────────────────────
# Weekly loss trigger
# ─────────────────────────────────────────────

class TestWeeklyLossTrigger:
    def test_weekly_loss_6R_triggers(self):
        # Use a high daily limit so daily breaker doesn't fire first.
        cfg = AntiOvercompoundingConfig(
            consecutive_loss_threshold=100,
            daily_loss_r_threshold=100.0,
            weekly_loss_r_threshold=6.0,
        )
        m = AntiOvercompoundingMonitor(cfg)
        for _ in range(6):
            m.register_trade(-1.0, was_at_elevated_risk=False)
        assert m.state.last_trigger_reason == "weekly_loss_exceeded"
        assert m.is_in_cooldown() is True


# ─────────────────────────────────────────────
# Cooldown countdown
# ─────────────────────────────────────────────

class TestCooldown:
    def test_cooldown_decrements_per_trade(self):
        cfg = AntiOvercompoundingConfig(cooldown_trades=3)
        m = AntiOvercompoundingMonitor(cfg)
        # Trigger via daily loss
        m.register_trade(-3.5, was_at_elevated_risk=False)
        assert m.state.cooldown_remaining == 3
        # Each subsequent trade decrements
        m.register_trade(0.1, was_at_elevated_risk=False)
        assert m.state.cooldown_remaining == 2
        m.register_trade(0.1, was_at_elevated_risk=False)
        assert m.state.cooldown_remaining == 1
        m.register_trade(0.1, was_at_elevated_risk=False)
        assert m.state.cooldown_remaining == 0
        # Now cooldown is over
        assert m.can_accelerate() is True

    def test_can_accelerate_during_cooldown_false(self):
        m = AntiOvercompoundingMonitor()
        m.register_trade(-3.5, was_at_elevated_risk=False)
        assert m.can_accelerate() is False


# ─────────────────────────────────────────────
# Rolling window resets
# ─────────────────────────────────────────────

class TestRollingResets:
    def test_daily_resets_after_24h(self):
        m = AntiOvercompoundingMonitor()
        m.register_trade(-1.0, was_at_elevated_risk=False)
        # Backdate the last_daily_reset to >24h ago
        m.state.last_daily_reset = datetime.utcnow() - timedelta(days=1, seconds=10)
        # Next register_trade should reset daily accumulator first
        m.register_trade(-0.5, was_at_elevated_risk=False)
        assert m.state.daily_r == pytest.approx(-0.5)

    def test_weekly_resets_after_7d(self):
        m = AntiOvercompoundingMonitor()
        m.register_trade(-2.0, was_at_elevated_risk=False)
        m.state.last_weekly_reset = datetime.utcnow() - timedelta(days=7, seconds=10)
        # Backdate daily too so the daily accumulator resets independently
        m.state.last_daily_reset = datetime.utcnow() - timedelta(hours=2)
        m.register_trade(-0.5, was_at_elevated_risk=False)
        # Weekly reset; only the new -0.5 should remain
        assert m.state.weekly_r == pytest.approx(-0.5)


# ─────────────────────────────────────────────
# Manual reset
# ─────────────────────────────────────────────

class TestManualReset:
    def test_reset_clears_all_state(self):
        m = AntiOvercompoundingMonitor()
        m.register_trade(-3.5, was_at_elevated_risk=True)
        m.register_trade(-1.0, was_at_elevated_risk=True)
        m.reset()
        assert m.state.consecutive_losses_at_elevated_risk == 0
        assert m.state.daily_r == 0.0
        assert m.state.weekly_r == 0.0
        assert m.state.cooldown_remaining == 0
        assert m.state.last_trigger_reason is None
