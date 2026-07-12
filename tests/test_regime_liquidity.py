"""
Unit tests for champion.regime_liquidity.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.regime_liquidity import (
    LiquidityStabilityCalculator,
    LiquidityStabilityConfig,
)


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

class TestConfig:
    def test_defaults(self):
        cfg = LiquidityStabilityConfig()
        assert cfg.window == 60
        assert cfg.min_observations == 10
        assert cfg.cov_normalize_pivot == 0.5

    def test_invalid_window_rejected(self):
        with pytest.raises(ValueError):
            LiquidityStabilityConfig(window=1)

    def test_invalid_min_obs_rejected(self):
        with pytest.raises(ValueError):
            LiquidityStabilityConfig(min_observations=1)

    def test_invalid_pivot_rejected(self):
        with pytest.raises(ValueError):
            LiquidityStabilityConfig(cov_normalize_pivot=0)


# ─────────────────────────────────────────────
# Empty / insufficient
# ─────────────────────────────────────────────

class TestEmpty:
    def test_empty_returns_neutral(self):
        calc = LiquidityStabilityCalculator()
        assert calc.compute_stability() == 0.5

    def test_below_min_obs_returns_neutral(self):
        calc = LiquidityStabilityCalculator(
            LiquidityStabilityConfig(window=20, min_observations=10)
        )
        for _ in range(5):
            calc.update(spread_bps=10.0, depth_usdt=10_000.0)
        assert calc.compute_stability() == 0.5


# ─────────────────────────────────────────────
# Stability scoring
# ─────────────────────────────────────────────

class TestStabilityScoring:
    def test_perfect_steady_high_score(self):
        calc = LiquidityStabilityCalculator(
            LiquidityStabilityConfig(window=20, min_observations=10)
        )
        for _ in range(20):
            calc.update(spread_bps=10.0, depth_usdt=10_000.0)
        # CoV = 0 → score = 1.0
        assert calc.compute_stability() == pytest.approx(1.0)

    def test_high_variability_low_score(self):
        calc = LiquidityStabilityCalculator(
            LiquidityStabilityConfig(window=20, min_observations=10)
        )
        # Wildly varying spread AND depth — realistic "thinning liquidity" scenario
        for i in range(20):
            spread = 1.0 if i % 2 == 0 else 100.0
            depth = 50_000.0 if i % 2 == 0 else 1_000.0
            calc.update(spread_bps=spread, depth_usdt=depth)
        # Both components erratic → composite well below 0.5
        s = calc.compute_stability()
        assert s < 0.5
        assert s > 0  # but not zero

    def test_negative_inputs_raise(self):
        calc = LiquidityStabilityCalculator()
        with pytest.raises(ValueError):
            calc.update(spread_bps=-1.0, depth_usdt=100.0)
        with pytest.raises(ValueError):
            calc.update(spread_bps=10.0, depth_usdt=-100.0)

    def test_zero_mean_returns_neutral_per_component(self):
        # If mean is zero (all zeros), the helper returns 0.5 for that component.
        calc = LiquidityStabilityCalculator(
            LiquidityStabilityConfig(window=20, min_observations=10)
        )
        for _ in range(20):
            calc.update(spread_bps=0.0, depth_usdt=0.0)
        # Both spread and depth zero-mean → both 0.5 → composite 0.5
        assert calc.compute_stability() == 0.5


# ─────────────────────────────────────────────
# Reset + window eviction
# ─────────────────────────────────────────────

class TestResetAndEviction:
    def test_reset_returns_to_neutral(self):
        calc = LiquidityStabilityCalculator(
            LiquidityStabilityConfig(window=20, min_observations=10)
        )
        for _ in range(20):
            calc.update(spread_bps=10.0, depth_usdt=10_000.0)
        calc.reset()
        assert calc.compute_stability() == 0.5

    def test_window_eviction_keeps_recent_only(self):
        calc = LiquidityStabilityCalculator(
            LiquidityStabilityConfig(window=10, min_observations=10)
        )
        # First 10 erratic, next 10 stable → buffer has only stable ones.
        for i in range(10):
            calc.update(spread_bps=(1.0 if i % 2 == 0 else 100.0), depth_usdt=10_000.0)
        for _ in range(10):
            calc.update(spread_bps=10.0, depth_usdt=10_000.0)
        # Buffer now contains only the steady period → high stability.
        s = calc.compute_stability()
        assert s > 0.95
