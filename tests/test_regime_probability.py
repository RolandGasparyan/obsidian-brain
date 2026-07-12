"""
Unit tests for champion.regime_probability (Layer 2 §1-§5).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.regime_probability import (
    RegimeFeatures,
    RegimeProbabilities,
    RegimeProbabilityConfig,
    RegimeProbabilityEstimator,
    RegimeWeights,
)


# ─────────────────────────────────────────────
# Feature input validation
# ─────────────────────────────────────────────

class TestRegimeFeaturesValidation:
    def test_all_in_unit_interval_ok(self):
        f = RegimeFeatures(
            vol_percentile=0.5, volume_percentile=0.5,
            atr_expansion=0.5, spread_stability=0.5,
            btc_trend=0.5, market_breadth=0.5,
            delta_intensity=0.5, liquidity_stability=0.5,
        )
        assert f.vol_percentile == 0.5

    def test_value_above_1_rejected(self):
        with pytest.raises(ValueError):
            RegimeFeatures(vol_percentile=1.5)

    def test_value_below_0_rejected(self):
        with pytest.raises(ValueError):
            RegimeFeatures(market_breadth=-0.1)

    def test_zero_and_one_boundary_ok(self):
        # Boundary values are allowed.
        f = RegimeFeatures(vol_percentile=0.0, volume_percentile=1.0)
        assert f.vol_percentile == 0.0
        assert f.volume_percentile == 1.0


# ─────────────────────────────────────────────
# Probability estimation
# ─────────────────────────────────────────────

class TestEstimateProbabilities:
    def test_probs_sum_to_one(self):
        est = RegimeProbabilityEstimator()
        f = RegimeFeatures(
            vol_percentile=0.7, volume_percentile=0.6,
            atr_expansion=0.5, spread_stability=0.4,
            btc_trend=0.5, market_breadth=0.6,
            delta_intensity=0.3, liquidity_stability=0.5,
        )
        p = est.estimate(f)
        total = p.p_dead + p.p_normal + p.p_expansion + p.p_high_impulse
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_all_zero_input_dead_dominates(self):
        est = RegimeProbabilityEstimator()
        # All-zero features: low everything → DEAD wins
        f = RegimeFeatures()
        p = est.estimate(f)
        assert p.most_likely == "DEAD"
        assert p.p_dead > 0.5

    def test_balanced_mid_vol_normal_wins(self):
        # vol=0.5 (mid), spread_stability=1, others mid → NORMAL should dominate
        est = RegimeProbabilityEstimator()
        f = RegimeFeatures(
            vol_percentile=0.5, volume_percentile=0.5,
            spread_stability=1.0, atr_expansion=0.3,
            btc_trend=0.3, market_breadth=0.5,
            delta_intensity=0.3, liquidity_stability=0.7,
        )
        p = est.estimate(f)
        assert p.most_likely == "NORMAL"

    def test_high_vol_volume_atr_btc_expansion_wins(self):
        est = RegimeProbabilityEstimator()
        f = RegimeFeatures(
            vol_percentile=0.85, volume_percentile=0.9,
            atr_expansion=0.85, spread_stability=0.6,
            btc_trend=0.85, market_breadth=0.7,
            delta_intensity=0.4, liquidity_stability=0.6,
        )
        p = est.estimate(f)
        assert p.most_likely == "EXPANSION"

    def test_extreme_vol_delta_breadth_high_impulse_wins(self):
        est = RegimeProbabilityEstimator()
        f = RegimeFeatures(
            vol_percentile=0.95, volume_percentile=0.85,
            atr_expansion=0.95, spread_stability=0.5,
            btc_trend=0.7, market_breadth=0.95,
            delta_intensity=0.95, liquidity_stability=0.5,
        )
        p = est.estimate(f)
        assert p.most_likely == "HIGH_IMPULSE"


# ─────────────────────────────────────────────
# Exposure multiplier (Section 4)
# ─────────────────────────────────────────────

class TestExposureMultiplier:
    def test_spec_example(self):
        # From L99_REGIME_PROBABILITY §4 worked example:
        # P(R1)=0.1, P(R2)=0.3, P(R3)=0.4, P(R4)=0.2
        # Multiplier = 0×0.1 + 0.5×0.3 + 1.0×0.4 + 1.2×0.2 = 0.79
        est = RegimeProbabilityEstimator()
        probs = RegimeProbabilities(
            p_dead=0.1, p_normal=0.3, p_expansion=0.4, p_high_impulse=0.2
        )
        m = est.exposure_multiplier(probs)
        assert m == pytest.approx(0.79)

    def test_pure_dead_gives_zero(self):
        est = RegimeProbabilityEstimator()
        probs = RegimeProbabilities(p_dead=1.0, p_normal=0, p_expansion=0, p_high_impulse=0)
        assert est.exposure_multiplier(probs) == 0.0

    def test_pure_high_impulse_gives_max(self):
        est = RegimeProbabilityEstimator()
        probs = RegimeProbabilities(p_dead=0, p_normal=0, p_expansion=0, p_high_impulse=1.0)
        assert est.exposure_multiplier(probs) == 1.2


# ─────────────────────────────────────────────
# Effective expectancy (Section 5)
# ─────────────────────────────────────────────

class TestEffectiveExpectancy:
    def test_basic_weighted_sum(self):
        probs = RegimeProbabilities(
            p_dead=0.2, p_normal=0.3, p_expansion=0.4, p_high_impulse=0.1
        )
        e_per_regime = {
            "DEAD": -0.5, "NORMAL": 0.1, "EXPANSION": 0.5, "HIGH_IMPULSE": 0.8
        }
        # E_total = 0.2*-0.5 + 0.3*0.1 + 0.4*0.5 + 0.1*0.8 = -0.1+0.03+0.2+0.08 = 0.21
        e = RegimeProbabilityEstimator.effective_expectancy(probs, e_per_regime)
        assert e == pytest.approx(0.21)

    def test_missing_regime_treated_as_zero(self):
        probs = RegimeProbabilities(
            p_dead=0.5, p_normal=0.5, p_expansion=0, p_high_impulse=0
        )
        # Only NORMAL specified; others missing → 0 contribution
        e = RegimeProbabilityEstimator.effective_expectancy(
            probs, {"NORMAL": 0.4}
        )
        assert e == pytest.approx(0.5 * 0.4)

    def test_negative_e_total_when_all_regimes_negative(self):
        probs = RegimeProbabilities(
            p_dead=0.4, p_normal=0.3, p_expansion=0.2, p_high_impulse=0.1
        )
        e_per_regime = {"DEAD": -1.0, "NORMAL": -0.5, "EXPANSION": -0.2, "HIGH_IMPULSE": -0.1}
        e = RegimeProbabilityEstimator.effective_expectancy(probs, e_per_regime)
        assert e < 0


# ─────────────────────────────────────────────
# Most-likely accessor
# ─────────────────────────────────────────────

class TestMostLikely:
    def test_picks_max_probability(self):
        p = RegimeProbabilities(p_dead=0.1, p_normal=0.2, p_expansion=0.6, p_high_impulse=0.1)
        assert p.most_likely == "EXPANSION"

    def test_dead_dominant(self):
        p = RegimeProbabilities(p_dead=0.9, p_normal=0.05, p_expansion=0.03, p_high_impulse=0.02)
        assert p.most_likely == "DEAD"


# ─────────────────────────────────────────────
# Custom config
# ─────────────────────────────────────────────

class TestCustomConfig:
    def test_custom_weights_change_outcome(self):
        # Build a config where DEAD has positive bias and EXPANSION has -inf bias.
        cfg = RegimeProbabilityConfig(
            weights_dead=RegimeWeights(bias=10.0),
            weights_normal=RegimeWeights(bias=0.0),
            weights_expansion=RegimeWeights(bias=-50.0),
            weights_high_impulse=RegimeWeights(bias=-50.0),
        )
        est = RegimeProbabilityEstimator(cfg)
        # Even with high_vol/expansion-y features, DEAD should dominate.
        f = RegimeFeatures(vol_percentile=0.9, volume_percentile=0.9, btc_trend=0.9)
        p = est.estimate(f)
        assert p.most_likely == "DEAD"
        assert p.p_dead > 0.99

    def test_custom_multipliers(self):
        cfg = RegimeProbabilityConfig(
            mul_dead=0.0, mul_normal=0.25, mul_expansion=2.0, mul_high_impulse=3.0
        )
        est = RegimeProbabilityEstimator(cfg)
        probs = RegimeProbabilities(p_dead=0, p_normal=0.5, p_expansion=0.5, p_high_impulse=0)
        # 0.25*0.5 + 2.0*0.5 = 0.125 + 1.0 = 1.125
        assert est.exposure_multiplier(probs) == pytest.approx(1.125)
