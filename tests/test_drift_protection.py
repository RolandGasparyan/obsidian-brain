"""
Unit tests for champion.drift_protection.

Includes the 8 tests provided verbatim by the operator on 2026-05-01,
plus defensive tests for: default config, initial state, reset(),
disable-reason persistence, and the priority order of disable triggers.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.drift_protection import (
    DriftProtectionEngine,
    DriftProtectionConfig,
)


# ─────────────────────────────────────────────
# Helpers (operator-provided)
# ─────────────────────────────────────────────

def create_engine() -> DriftProtectionEngine:
    return DriftProtectionEngine(DriftProtectionConfig())


def valid_metrics() -> dict:
    return dict(
        trades=50,
        win_rate=0.52,
        profit_factor=1.4,
        expectancy_r=0.6,
        information_coefficient=0.05,
        max_consecutive_losses=4,
        drawdown_pct=0.10,
    )


# ─────────────────────────────────────────────
# Operator-provided tests (verbatim semantics)
# ─────────────────────────────────────────────

def test_not_enough_trades():
    engine = create_engine()
    metrics = valid_metrics()
    metrics["trades"] = 10
    assert engine.evaluate(**metrics) is True


def test_disable_low_win_rate():
    engine = create_engine()
    metrics = valid_metrics()
    metrics["win_rate"] = 0.40
    assert engine.evaluate(**metrics) is False
    assert engine.state.last_disable_reason == "win_rate_below_threshold"


def test_disable_low_profit_factor():
    engine = create_engine()
    metrics = valid_metrics()
    metrics["profit_factor"] = 1.05
    assert engine.evaluate(**metrics) is False


def test_disable_negative_expectancy():
    engine = create_engine()
    metrics = valid_metrics()
    metrics["expectancy_r"] = -0.01
    assert engine.evaluate(**metrics) is False


def test_disable_low_ic():
    engine = create_engine()
    metrics = valid_metrics()
    metrics["information_coefficient"] = 0.01
    assert engine.evaluate(**metrics) is False


def test_disable_consecutive_losses():
    engine = create_engine()
    metrics = valid_metrics()
    metrics["max_consecutive_losses"] = 12
    assert engine.evaluate(**metrics) is False


def test_disable_drawdown():
    engine = create_engine()
    metrics = valid_metrics()
    metrics["drawdown_pct"] = 0.30
    assert engine.evaluate(**metrics) is False


def test_valid_case_remains_enabled():
    engine = create_engine()
    metrics = valid_metrics()
    assert engine.evaluate(**metrics) is True
    assert engine.state.disabled is False


# ─────────────────────────────────────────────
# Additional defensive tests
# ─────────────────────────────────────────────

class TestConfigDefaults:
    def test_defaults_match_spec(self):
        cfg = DriftProtectionConfig()
        assert cfg.min_trades_required == 30
        assert cfg.min_win_rate == 0.45
        assert cfg.min_profit_factor == 1.1
        assert cfg.min_expectancy_r == 0.0
        assert cfg.min_information_coefficient == 0.02
        assert cfg.max_consecutive_losses == 8
        assert cfg.max_drawdown_pct == 0.20

    def test_overrides_independent(self):
        cfg = DriftProtectionConfig(min_win_rate=0.50, max_drawdown_pct=0.10)
        assert cfg.min_win_rate == 0.50
        assert cfg.max_drawdown_pct == 0.10
        assert cfg.min_profit_factor == 1.1  # untouched


class TestInitialState:
    def test_initial_state_clean(self):
        engine = create_engine()
        assert engine.state.disabled is False
        assert engine.state.last_disable_reason is None
        assert engine.state.trades_observed == 0

    def test_trades_observed_updates_each_call(self):
        engine = create_engine()
        engine.evaluate(**valid_metrics())
        assert engine.state.trades_observed == 50
        engine.evaluate(**{**valid_metrics(), "trades": 75})
        assert engine.state.trades_observed == 75


class TestExpectancyBoundary:
    def test_expectancy_zero_triggers_disable(self):
        # Boundary: <=0 triggers, so exactly 0 should disable.
        engine = create_engine()
        metrics = valid_metrics()
        metrics["expectancy_r"] = 0.0
        assert engine.evaluate(**metrics) is False
        assert engine.state.last_disable_reason == "non_positive_expectancy"

    def test_expectancy_just_above_zero_passes(self):
        engine = create_engine()
        metrics = valid_metrics()
        metrics["expectancy_r"] = 0.001
        assert engine.evaluate(**metrics) is True


class TestReset:
    def test_reset_clears_disabled_flag(self):
        engine = create_engine()
        metrics = valid_metrics()
        metrics["win_rate"] = 0.30  # trigger disable
        engine.evaluate(**metrics)
        assert engine.state.disabled is True
        engine.reset()
        assert engine.state.disabled is False

    def test_reset_clears_disable_reason(self):
        engine = create_engine()
        metrics = valid_metrics()
        metrics["profit_factor"] = 0.9
        engine.evaluate(**metrics)
        assert engine.state.last_disable_reason == "profit_factor_below_threshold"
        engine.reset()
        assert engine.state.last_disable_reason is None

    def test_after_reset_can_evaluate_again(self):
        engine = create_engine()
        metrics = valid_metrics()
        metrics["win_rate"] = 0.30
        engine.evaluate(**metrics)
        engine.reset()
        # Now with valid metrics, returns True.
        assert engine.evaluate(**valid_metrics()) is True


class TestDisablePriorityOrder:
    """Verify the order of checks: when multiple thresholds are violated,
    the FIRST violated check (per spec order) wins the reason field."""

    def test_win_rate_wins_over_profit_factor(self):
        engine = create_engine()
        metrics = valid_metrics()
        metrics["win_rate"] = 0.30  # violates
        metrics["profit_factor"] = 0.5  # also violates, but checked later
        engine.evaluate(**metrics)
        assert engine.state.last_disable_reason == "win_rate_below_threshold"

    def test_profit_factor_wins_over_expectancy(self):
        engine = create_engine()
        metrics = valid_metrics()
        metrics["profit_factor"] = 0.5
        metrics["expectancy_r"] = -1.0  # also violates
        engine.evaluate(**metrics)
        assert engine.state.last_disable_reason == "profit_factor_below_threshold"

    def test_expectancy_wins_over_ic(self):
        engine = create_engine()
        metrics = valid_metrics()
        metrics["expectancy_r"] = -0.5
        metrics["information_coefficient"] = -0.1  # also violates
        engine.evaluate(**metrics)
        assert engine.state.last_disable_reason == "non_positive_expectancy"

    def test_ic_wins_over_consec_losses(self):
        engine = create_engine()
        metrics = valid_metrics()
        metrics["information_coefficient"] = 0.0
        metrics["max_consecutive_losses"] = 20
        engine.evaluate(**metrics)
        assert engine.state.last_disable_reason == "weak_information_coefficient"

    def test_consec_losses_wins_over_drawdown(self):
        engine = create_engine()
        metrics = valid_metrics()
        metrics["max_consecutive_losses"] = 20
        metrics["drawdown_pct"] = 0.50
        engine.evaluate(**metrics)
        assert engine.state.last_disable_reason == "excess_consecutive_losses"
