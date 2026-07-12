"""
Layer 2 regime-probability composition integration tests.

Verifies the 5 Layer 2 modules compose end-to-end:

    OHLCV / orderbook stream
        ↓
    MarketBreadthCalculator   (feature 6)
    LiquidityStabilityCalculator (feature 8)
        ↓ (subset of) RegimeFeatures
    RegimeProbabilityEstimator
        ↓ RegimeProbabilities
    RegimeTransitionTracker  (velocity / rapid_shift flag)
    RegimeValidator          (calibration diagnostics over time)

Plus bridge to Layer 5: regime probabilities → exposure_multiplier →
PortfolioRiskGovernor.regime_multiplier (replaces orchestrator's binary
exposure decision).

NO live exchange wiring. Pure-Python composition.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.regime_breadth import MarketBreadthCalculator, MarketBreadthConfig
from champion.regime_liquidity import LiquidityStabilityCalculator, LiquidityStabilityConfig
from champion.regime_probability import (
    RegimeFeatures,
    RegimeProbabilityEstimator,
)
from champion.regime_transition import RegimeTransitionTracker
from champion.regime_validation import RegimeValidator, RegimeValidatorConfig

from champion.portfolio_risk_governor import (
    PortfolioRiskConfig,
    PortfolioRiskGovernor,
)


# ─────────────────────────────────────────────
# Feature engineering → estimator
# ─────────────────────────────────────────────

class TestFeatureEngineeringChain:
    def test_breadth_and_liquidity_feed_estimator(self):
        # Step 1: build breadth from synthetic pair closes
        breadth = MarketBreadthCalculator(MarketBreadthConfig(ma_window=5, min_history_bars=5))
        # 3 pairs, 5 bars each, all rising → breadth = 1.0
        for sym in ("BTC_USDT", "ETH_USDT", "SOL_USDT"):
            for i in range(1, 6):
                breadth.update_pair_close(sym, float(i))
        breadth_score = breadth.compute_breadth()
        assert breadth_score == 1.0

        # Step 2: build liquidity from synthetic spreads/depths
        liq = LiquidityStabilityCalculator(LiquidityStabilityConfig(window=20, min_observations=10))
        for _ in range(20):
            liq.update(spread_bps=10.0, depth_usdt=50_000.0)
        liq_score = liq.compute_stability()
        assert liq_score == pytest.approx(1.0)

        # Step 3: feed estimator
        f = RegimeFeatures(
            vol_percentile=0.85, volume_percentile=0.9,
            atr_expansion=0.85, spread_stability=0.7,
            btc_trend=0.85, market_breadth=breadth_score,
            delta_intensity=0.4, liquidity_stability=liq_score,
        )
        est = RegimeProbabilityEstimator()
        p = est.estimate(f)
        assert p.most_likely == "EXPANSION"


# ─────────────────────────────────────────────
# Estimator → transition tracker
# ─────────────────────────────────────────────

class TestEstimatorToTransition:
    def test_regime_shift_detected(self):
        est = RegimeProbabilityEstimator()
        tracker = RegimeTransitionTracker()

        # Time t1: DEAD-dominant input (low everything)
        f1 = RegimeFeatures()
        p1 = est.estimate(f1)
        tracker.add_observation(p1)

        # Time t2: EXPANSION-dominant input
        f2 = RegimeFeatures(
            vol_percentile=0.85, volume_percentile=0.9,
            atr_expansion=0.85, btc_trend=0.85,
        )
        p2 = est.estimate(f2)
        tracker.add_observation(p2)

        v = tracker.compute_velocity()
        # Should be a rapid shift (DEAD→EXPANSION)
        assert v.rapid_shift is True
        assert v.delta_dead < 0       # DEAD probability dropped
        assert v.delta_expansion > 0  # EXPANSION probability rose


# ─────────────────────────────────────────────
# Estimator → validator
# ─────────────────────────────────────────────

class TestEstimatorToValidator:
    def test_validator_accumulates_then_validates(self):
        est = RegimeProbabilityEstimator()
        validator = RegimeValidator(RegimeValidatorConfig(
            min_observations=20, min_vol_ic_threshold=0.5,
            min_regime_expectancy=0.0,
        ))

        # Synthesize a stream: when vol_pct is high, both EXPANSION prob AND
        # forward_volatility are high. Validator should detect the alignment
        # and accept the model.
        for i in range(40):
            vp = i / 40.0
            f = RegimeFeatures(
                vol_percentile=vp, volume_percentile=vp,
                atr_expansion=vp, btc_trend=vp,
            )
            p = est.estimate(f)
            validator.add_observation(
                probs=p,
                forward_return=vp * 0.01,        # small positive when expansion high
                forward_volatility=vp,
            )

        result = validator.validate()
        assert result.verdict == "accept"
        assert result.expansion_vol_ic > 0.5


# ─────────────────────────────────────────────
# Bridge to Layer 5 governor
# ─────────────────────────────────────────────

class TestBridgeToGovernor:
    def test_exposure_multiplier_feeds_governor(self):
        est = RegimeProbabilityEstimator()
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), starting_equity=10_000)

        # EXPANSION-dominant features → multiplier ≈ 1.0
        f = RegimeFeatures(
            vol_percentile=0.85, volume_percentile=0.9,
            atr_expansion=0.85, btc_trend=0.85,
        )
        p = est.estimate(f)
        mul = est.exposure_multiplier(p)
        assert 0.9 <= mul <= 1.2

        # Wire as governor's regime_multiplier; approve a small position.
        gov.config.regime_multiplier = mul
        assert gov.approve_new_position("BTC_USDT", 0.005) is True

    def test_dead_dominant_yields_low_multiplier(self):
        est = RegimeProbabilityEstimator()
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), starting_equity=10_000)

        # DEAD-dominant features (all zero) → multiplier near 0
        p = est.estimate(RegimeFeatures())
        mul = est.exposure_multiplier(p)
        assert mul < 0.5  # DEAD has multiplier 0; NORMAL has 0.5

        gov.config.regime_multiplier = mul
        # Request 0.012 (max single cap); effective = 0.012 × small mul
        # Since multiplier is small, effective fraction stays well under cap
        assert gov.approve_new_position("BTC_USDT", 0.012) is True
