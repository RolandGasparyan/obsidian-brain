"""
Unit tests for champion.regime_validation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.regime_probability import RegimeProbabilities
from champion.regime_validation import (
    RegimeValidationResult,
    RegimeValidator,
    RegimeValidatorConfig,
)


def probs(d: float, n: float, e: float, h: float) -> RegimeProbabilities:
    return RegimeProbabilities(p_dead=d, p_normal=n, p_expansion=e, p_high_impulse=h)


# ─────────────────────────────────────────────
# Insufficient data
# ─────────────────────────────────────────────

class TestInsufficientData:
    def test_empty_returns_insufficient_data(self):
        v = RegimeValidator()
        r = v.validate()
        assert r.verdict == "insufficient_data"
        assert r.n_observations == 0

    def test_below_min_obs_returns_insufficient(self):
        v = RegimeValidator(RegimeValidatorConfig(min_observations=100))
        for i in range(50):
            v.add_observation(probs(0.4, 0.3, 0.2, 0.1), forward_return=0.01, forward_volatility=0.01)
        assert v.validate().verdict == "insufficient_data"


# ─────────────────────────────────────────────
# Strong-correlation accept
# ─────────────────────────────────────────────

class TestStrongCorrelation:
    def test_perfect_expansion_vol_correlation_accepts(self):
        # Build samples where P(EXPANSION) and forward_vol are perfectly aligned.
        # Use min_observations=10 for fast tests.
        v = RegimeValidator(RegimeValidatorConfig(
            min_observations=10, min_vol_ic_threshold=0.5,
            min_regime_expectancy=0.0,
        ))
        for i in range(20):
            p_exp = i / 20.0
            v.add_observation(
                probs(0.0, 1.0 - p_exp, p_exp, 0.0),
                forward_return=p_exp,    # also positive when expansion high → +E
                forward_volatility=p_exp,
            )
        result = v.validate()
        assert result.verdict == "accept"
        assert result.expansion_vol_ic > 0.95


# ─────────────────────────────────────────────
# Reject scenarios
# ─────────────────────────────────────────────

class TestRejection:
    def test_no_correlation_rejects(self):
        v = RegimeValidator(RegimeValidatorConfig(
            min_observations=10, min_vol_ic_threshold=0.5,
            min_regime_expectancy=0.0,
        ))
        # P(EXPANSION) sweeps 0..1; forward_vol stays constant → IC = 0
        for i in range(20):
            p_exp = i / 20.0
            v.add_observation(
                probs(0.0, 1.0 - p_exp, p_exp, 0.0),
                forward_return=0.0,
                forward_volatility=0.5,  # constant
            )
        result = v.validate()
        assert result.verdict == "reject"
        assert any("expansion_vol_ic" in r for r in result.rejection_reasons)

    def test_negative_best_regime_expectancy_rejects(self):
        v = RegimeValidator(RegimeValidatorConfig(
            min_observations=10, min_vol_ic_threshold=-1.0,  # vol IC won't reject
            min_regime_expectancy=0.0,
        ))
        # Set up observations where every regime has negative expectancy.
        for i in range(20):
            p_exp = i / 20.0
            v.add_observation(
                probs(0.0, 1.0 - p_exp, p_exp, 0.0),
                forward_return=-0.1,  # always negative
                forward_volatility=p_exp,
            )
        result = v.validate()
        assert result.verdict == "reject"
        assert any("best_regime_expectancy" in r for r in result.rejection_reasons)

    def test_negative_forward_vol_rejected_at_input(self):
        v = RegimeValidator()
        with pytest.raises(ValueError):
            v.add_observation(probs(0.4, 0.3, 0.2, 0.1), forward_return=0.0, forward_volatility=-0.1)


# ─────────────────────────────────────────────
# Per-regime expectancy
# ─────────────────────────────────────────────

class TestRegimeExpectancy:
    def test_buckets_by_most_likely(self):
        v = RegimeValidator(RegimeValidatorConfig(
            min_observations=4, min_vol_ic_threshold=-1.0,
            min_regime_expectancy=-1.0,
        ))
        # Two DEAD-dominant observations with -0.5 returns
        v.add_observation(probs(0.7, 0.1, 0.1, 0.1), 0.0, 0.1)
        v.add_observation(probs(0.7, 0.1, 0.1, 0.1), -1.0, 0.1)
        # Two EXPANSION-dominant observations with +0.5 returns
        v.add_observation(probs(0.1, 0.1, 0.7, 0.1), 0.5, 0.5)
        v.add_observation(probs(0.1, 0.1, 0.7, 0.1), 0.5, 0.5)

        r = v.validate()
        assert r.regime_counts["DEAD"] == 2
        assert r.regime_counts["EXPANSION"] == 2
        assert r.regime_expectancies["DEAD"] == pytest.approx(-0.5)
        assert r.regime_expectancies["EXPANSION"] == pytest.approx(0.5)


# ─────────────────────────────────────────────
# Reset
# ─────────────────────────────────────────────

class TestReset:
    def test_reset_clears_records(self):
        v = RegimeValidator()
        v.add_observation(probs(0.4, 0.3, 0.2, 0.1), 0.01, 0.5)
        v.reset()
        assert v.n_observations() == 0
        assert v.validate().verdict == "insufficient_data"
