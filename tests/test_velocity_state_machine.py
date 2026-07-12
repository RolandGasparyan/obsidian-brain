"""
Unit tests for champion.velocity_state_machine (Layer 4 §2).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.velocity_state_machine import (
    VelocityState,
    VelocityStateMachine,
    VelocityStateMachineConfig,
)


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

class TestConfig:
    def test_defaults_match_spec(self):
        cfg = VelocityStateMachineConfig()
        assert cfg.conservative_pf_max == 1.3
        assert cfg.conservative_dd_max == 0.10
        assert cfg.baseline_pf_min == 1.3
        assert cfg.baseline_pf_max == 1.5
        assert cfg.baseline_dd_max == 0.10
        assert cfg.acceleration_pf_min == 1.6
        assert cfg.acceleration_dd_max == 0.08
        assert cfg.acceleration_min_trades == 200
        assert cfg.conservative_risk_r == 0.5
        assert cfg.baseline_risk_r == 1.0
        assert cfg.acceleration_risk_r_cap == 1.25

    def test_invalid_pf_ordering_rejected(self):
        with pytest.raises(ValueError):
            VelocityStateMachineConfig(baseline_pf_min=1.7, baseline_pf_max=1.6)

    def test_invalid_dd_ordering_rejected(self):
        with pytest.raises(ValueError):
            VelocityStateMachineConfig(
                acceleration_dd_max=0.15, baseline_dd_max=0.10
            )


# ─────────────────────────────────────────────
# Initial state
# ─────────────────────────────────────────────

class TestInitialState:
    def test_initial_state_is_conservative(self):
        sm = VelocityStateMachine()
        assert sm.current_state == VelocityState.CONSERVATIVE


# ─────────────────────────────────────────────
# CONSERVATIVE
# ─────────────────────────────────────────────

class TestConservative:
    def test_low_pf_triggers_conservative(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(profit_factor=1.1, rolling_dd=0.05, trades_count=100)
        assert d.state == VelocityState.CONSERVATIVE
        assert d.risk_r == 0.5

    def test_high_dd_triggers_conservative(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(profit_factor=1.4, rolling_dd=0.15, trades_count=100)
        assert d.state == VelocityState.CONSERVATIVE

    def test_low_trades_triggers_conservative(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(profit_factor=1.4, rolling_dd=0.05, trades_count=20)
        assert d.state == VelocityState.CONSERVATIVE
        assert "trades=20" in d.reason


# ─────────────────────────────────────────────
# BASELINE
# ─────────────────────────────────────────────

class TestBaseline:
    def test_in_band_triggers_baseline(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(
            profit_factor=1.4, rolling_dd=0.05,
            trades_count=100, ic_stable=False, regime_is_expansion=False,
        )
        assert d.state == VelocityState.BASELINE
        assert d.risk_r == 1.0

    def test_pf_at_lower_boundary(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(
            profit_factor=1.3, rolling_dd=0.05, trades_count=100,
        )
        # PF=1.3 is inclusive on the baseline lower bound
        assert d.state == VelocityState.BASELINE

    def test_pf_at_upper_boundary(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(
            profit_factor=1.5, rolling_dd=0.05, trades_count=100,
        )
        # PF=1.5 inclusive on baseline upper
        assert d.state == VelocityState.BASELINE


# ─────────────────────────────────────────────
# ACCELERATION
# ─────────────────────────────────────────────

class TestAcceleration:
    def test_all_gates_pass_acceleration(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(
            profit_factor=1.7, rolling_dd=0.05, trades_count=200,
            ic_stable=True, regime_is_expansion=True,
        )
        assert d.state == VelocityState.ACCELERATION
        assert d.risk_r == 1.25

    def test_missing_ic_stability_falls_to_lower_tier(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(
            profit_factor=1.7, rolling_dd=0.05, trades_count=200,
            ic_stable=False, regime_is_expansion=True,
        )
        # PF=1.7 > baseline_pf_max=1.5 → not BASELINE either
        # Falls to CONSERVATIVE (no higher tier passes)
        assert d.state == VelocityState.CONSERVATIVE

    def test_missing_expansion_falls_to_lower_tier(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(
            profit_factor=1.7, rolling_dd=0.05, trades_count=200,
            ic_stable=True, regime_is_expansion=False,
        )
        assert d.state == VelocityState.CONSERVATIVE

    def test_dd_too_high_falls_to_lower_tier(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(
            profit_factor=1.7, rolling_dd=0.09, trades_count=200,
            ic_stable=True, regime_is_expansion=True,
        )
        # DD 0.09 > 0.08 → ACCELERATION blocked; PF 1.7 > baseline max → CONSERVATIVE
        assert d.state == VelocityState.CONSERVATIVE

    def test_too_few_trades_falls_to_lower_tier(self):
        sm = VelocityStateMachine()
        d = sm.evaluate(
            profit_factor=1.7, rolling_dd=0.05, trades_count=150,
            ic_stable=True, regime_is_expansion=True,
        )
        # trades < 200 → ACCELERATION blocked
        assert d.state == VelocityState.CONSERVATIVE

    def test_acceleration_without_expansion_when_disabled(self):
        cfg = VelocityStateMachineConfig(acceleration_requires_expansion=False)
        sm = VelocityStateMachine(cfg)
        d = sm.evaluate(
            profit_factor=1.7, rolling_dd=0.05, trades_count=200,
            ic_stable=True, regime_is_expansion=False,
        )
        assert d.state == VelocityState.ACCELERATION


# ─────────────────────────────────────────────
# State persistence
# ─────────────────────────────────────────────

class TestStatePersistence:
    def test_state_updates_per_call(self):
        sm = VelocityStateMachine()

        sm.evaluate(profit_factor=1.0, rolling_dd=0.05, trades_count=100)
        assert sm.current_state == VelocityState.CONSERVATIVE

        sm.evaluate(profit_factor=1.4, rolling_dd=0.05, trades_count=100)
        assert sm.current_state == VelocityState.BASELINE

        sm.evaluate(
            profit_factor=1.7, rolling_dd=0.05, trades_count=200,
            ic_stable=True, regime_is_expansion=True,
        )
        assert sm.current_state == VelocityState.ACCELERATION
