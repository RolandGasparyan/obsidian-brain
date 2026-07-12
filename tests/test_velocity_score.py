"""
Unit tests for champion.velocity_score (Layer 4 §3).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.velocity_score import (
    VelocityScoreAction,
    VelocityScoreCalculator,
    VelocityScoreConfig,
)


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

class TestConfig:
    def test_defaults(self):
        cfg = VelocityScoreConfig()
        assert cfg.scaling_threshold == 2.0
        assert cfg.reduction_threshold == 1.0
        assert cfg.freeze_threshold == 0.0
        assert cfg.stable_trades_required == 30
        assert cfg.scaling_step_r == 0.25
        assert cfg.reduction_factor == 0.5

    def test_invalid_threshold_ordering_rejected(self):
        with pytest.raises(ValueError):
            VelocityScoreConfig(
                freeze_threshold=2.0, reduction_threshold=1.0, scaling_threshold=0.5
            )

    def test_invalid_reduction_factor_rejected(self):
        with pytest.raises(ValueError):
            VelocityScoreConfig(reduction_factor=0)

    def test_invalid_step_r_rejected(self):
        with pytest.raises(ValueError):
            VelocityScoreConfig(scaling_step_r=0)


# ─────────────────────────────────────────────
# Compute formula
# ─────────────────────────────────────────────

class TestCompute:
    def test_basic_formula(self):
        # VS = PF*E*IC / (DD*Var)
        # PF=1.5, E=0.5, IC=0.8, DD=0.05, Var=0.4 → VS = 0.6 / 0.02 = 30
        calc = VelocityScoreCalculator()
        s = calc.compute(profit_factor=1.5, expectancy_r=0.5,
                         ic_stability=0.8, drawdown_pct=0.05, variance=0.4)
        assert s == pytest.approx(30.0, rel=1e-6)

    def test_dd_zero_uses_epsilon(self):
        calc = VelocityScoreCalculator()
        # DD=0 → use epsilon → very large finite VS
        s = calc.compute(profit_factor=1.5, expectancy_r=0.5,
                         ic_stability=0.8, drawdown_pct=0.0, variance=0.4)
        assert s > 1e8  # tiny denominator → huge VS
        assert s != float("inf")  # but not infinite

    def test_variance_zero_uses_epsilon(self):
        calc = VelocityScoreCalculator()
        s = calc.compute(profit_factor=1.5, expectancy_r=0.5,
                         ic_stability=0.8, drawdown_pct=0.05, variance=0.0)
        assert s > 1e8

    def test_negative_expectancy_negative_score(self):
        calc = VelocityScoreCalculator()
        s = calc.compute(profit_factor=1.5, expectancy_r=-0.3,
                         ic_stability=0.8, drawdown_pct=0.05, variance=0.4)
        assert s < 0


# ─────────────────────────────────────────────
# Action classification
# ─────────────────────────────────────────────

class TestActionClassification:
    def test_freeze_on_negative_score(self):
        calc = VelocityScoreCalculator()
        r = calc.evaluate(profit_factor=1.0, expectancy_r=-0.1,
                          ic_stability=0.5, drawdown_pct=0.05, variance=0.4,
                          trades_at_current_state=50)
        assert r.action == VelocityScoreAction.FREEZE
        assert r.risk_multiplier == 0.0

    def test_reduce_when_below_reduction_threshold(self):
        # Engineer VS in (0, 1) range:
        # PF=1.0, E=0.05, IC=0.5, DD=0.10, Var=0.4
        # VS = 1.0*0.05*0.5 / (0.10*0.4) = 0.025/0.04 = 0.625
        calc = VelocityScoreCalculator()
        r = calc.evaluate(profit_factor=1.0, expectancy_r=0.05,
                          ic_stability=0.5, drawdown_pct=0.10, variance=0.4,
                          trades_at_current_state=50)
        assert 0 < r.score < 1.0
        assert r.action == VelocityScoreAction.REDUCE
        assert r.risk_multiplier == 0.5

    def test_hold_in_mid_band(self):
        # Engineer VS in [1.0, 2.0):
        # PF=1.0, E=0.06, IC=1.0, DD=0.10, Var=0.4
        # VS = 1.0*0.06*1.0 / (0.10*0.4) = 0.06/0.04 = 1.5
        calc = VelocityScoreCalculator()
        r = calc.evaluate(profit_factor=1.0, expectancy_r=0.06,
                          ic_stability=1.0, drawdown_pct=0.10, variance=0.4,
                          trades_at_current_state=50)
        assert 1.0 <= r.score < 2.0
        assert r.action == VelocityScoreAction.HOLD
        assert r.risk_multiplier == 1.0

    def test_scale_up_on_high_score_with_stable_trades(self):
        # Engineer VS > 2.0 + stable trades >= 30
        # PF=1.5, E=0.5, IC=0.8, DD=0.05, Var=0.4 → VS=30
        calc = VelocityScoreCalculator()
        r = calc.evaluate(profit_factor=1.5, expectancy_r=0.5,
                          ic_stability=0.8, drawdown_pct=0.05, variance=0.4,
                          trades_at_current_state=50)
        assert r.score > 2.0
        assert r.action == VelocityScoreAction.SCALE_UP
        assert r.delta_risk_r == 0.25

    def test_high_score_unstable_trades_holds(self):
        calc = VelocityScoreCalculator()
        r = calc.evaluate(profit_factor=1.5, expectancy_r=0.5,
                          ic_stability=0.8, drawdown_pct=0.05, variance=0.4,
                          trades_at_current_state=10)
        assert r.score > 2.0
        # Stability gate not met → HOLD even though score is high
        assert r.action == VelocityScoreAction.HOLD
        assert r.delta_risk_r == 0.0


# ─────────────────────────────────────────────
# Boundary
# ─────────────────────────────────────────────

class TestBoundaries:
    def test_score_exactly_zero_freezes(self):
        # PF*E*IC = 0 → score = 0 → freeze (≤ freeze_threshold=0)
        calc = VelocityScoreCalculator()
        r = calc.evaluate(profit_factor=0.0, expectancy_r=0.5,
                          ic_stability=0.8, drawdown_pct=0.05, variance=0.4,
                          trades_at_current_state=50)
        assert r.score == 0.0
        assert r.action == VelocityScoreAction.FREEZE
