"""
Unit tests for champion.growth_projector (Layer 3 §3.2 + §3.4).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.growth_projector import (
    GrowthProjector,
    GrowthProjectorConfig,
    ProjectionResult,
)


# ─────────────────────────────────────────────
# Config validation
# ─────────────────────────────────────────────

class TestConfig:
    def test_defaults(self):
        cfg = GrowthProjectorConfig()
        assert cfg.variance_haircut == 0.40
        assert cfg.target_band_min == 0.06
        assert cfg.target_band_max == 0.10
        assert cfg.aggressive_max == 0.15
        assert cfg.overfitting_warn_threshold == 0.20

    def test_invalid_haircut_rejected(self):
        with pytest.raises(ValueError):
            GrowthProjectorConfig(variance_haircut=1.0)
        with pytest.raises(ValueError):
            GrowthProjectorConfig(variance_haircut=-0.1)

    def test_band_ordering_required(self):
        with pytest.raises(ValueError):
            GrowthProjectorConfig(target_band_min=0.10, target_band_max=0.05)


# ─────────────────────────────────────────────
# Spec example (§3.2)
# ─────────────────────────────────────────────

class TestSpecExample:
    def test_spec_example(self):
        # From L99_CAPITAL_MATHEMATICS §3.2:
        # E = +0.5R, Trades/month = 30, Risk = 1%
        # Raw monthly = 0.5 × 30 × 0.01 = 15%
        # Adjusted (40% haircut) = 9%
        proj = GrowthProjector()
        result = proj.project(
            expectancy_r=0.5, trades_per_month=30, risk_per_trade=0.01
        )
        assert result.raw_monthly == pytest.approx(0.15)
        assert result.adjusted_monthly == pytest.approx(0.09)
        # 9% falls in moderate band (6-10%)
        assert result.classification == "moderate"
        assert result.overfitting_warning is False


# ─────────────────────────────────────────────
# Classification bands
# ─────────────────────────────────────────────

class TestClassification:
    def test_below_band(self):
        proj = GrowthProjector()
        # E=0, raw=0, adj=0 → below_band
        result = proj.project(0.0, 30, 0.01)
        assert result.classification == "below_band"

    def test_negative_expectancy_below_band(self):
        proj = GrowthProjector()
        result = proj.project(-0.5, 30, 0.01)
        assert result.adjusted_monthly < 0
        assert result.classification == "below_band"

    def test_conservative_band(self):
        # Raw=0.05, adj=0.03 → between 3% and 6% → conservative
        proj = GrowthProjector()
        result = proj.project(expectancy_r=0.05, trades_per_month=100, risk_per_trade=0.01)
        # raw=0.05, adj=0.03
        assert result.adjusted_monthly == pytest.approx(0.03)
        assert result.classification == "conservative"

    def test_moderate_band(self):
        # Spec example
        proj = GrowthProjector()
        result = proj.project(0.5, 30, 0.01)
        assert result.classification == "moderate"

    def test_aggressive_sustainable_band(self):
        # Raw=0.25, adj=0.15 → at aggressive_max boundary (inclusive)
        proj = GrowthProjector()
        result = proj.project(expectancy_r=1.0, trades_per_month=25, risk_per_trade=0.01)
        # raw = 0.25, adj = 0.15
        assert result.raw_monthly == pytest.approx(0.25)
        assert result.adjusted_monthly == pytest.approx(0.15)
        assert result.classification == "aggressive_sustainable"

    def test_above_band_classification(self):
        # Raw=0.30, adj=0.18 → above 0.15 → above_band
        proj = GrowthProjector()
        result = proj.project(expectancy_r=2.0, trades_per_month=15, risk_per_trade=0.01)
        # raw = 0.30, adj = 0.18
        assert result.adjusted_monthly == pytest.approx(0.18)
        assert result.classification == "above_band"


# ─────────────────────────────────────────────
# Overfitting warning (§3.4)
# ─────────────────────────────────────────────

class TestOverfittingWarning:
    def test_raw_above_20pct_triggers_warning(self):
        proj = GrowthProjector()
        # Raw = 0.5 * 50 * 0.01 = 0.25 > 0.20 threshold
        result = proj.project(0.5, 50, 0.01)
        assert result.overfitting_warning is True

    def test_raw_at_or_below_20pct_no_warning(self):
        proj = GrowthProjector()
        # Raw = 0.5 * 30 * 0.01 = 0.15 < 0.20
        result = proj.project(0.5, 30, 0.01)
        assert result.overfitting_warning is False

    def test_warning_uses_raw_not_adjusted(self):
        # Raw = 0.21 (just above 0.20), adjusted = 0.126 (well below 0.20)
        # Warning should fire on raw
        proj = GrowthProjector()
        result = proj.project(expectancy_r=0.7, trades_per_month=30, risk_per_trade=0.01)
        # raw = 0.21
        assert result.raw_monthly == pytest.approx(0.21)
        assert result.overfitting_warning is True


# ─────────────────────────────────────────────
# Input validation
# ─────────────────────────────────────────────

class TestInputValidation:
    def test_negative_trades_raises(self):
        proj = GrowthProjector()
        with pytest.raises(ValueError):
            proj.project(0.5, -10, 0.01)

    def test_invalid_risk_raises(self):
        proj = GrowthProjector()
        with pytest.raises(ValueError):
            proj.project(0.5, 30, 1.5)
        with pytest.raises(ValueError):
            proj.project(0.5, 30, -0.1)

    def test_zero_trades_returns_zero(self):
        proj = GrowthProjector()
        result = proj.project(0.5, 0, 0.01)
        assert result.raw_monthly == 0
        assert result.adjusted_monthly == 0
        assert result.classification == "below_band"


# ─────────────────────────────────────────────
# Result dataclass shape
# ─────────────────────────────────────────────

class TestResultShape:
    def test_returns_ProjectionResult(self):
        result = GrowthProjector().project(0.5, 30, 0.01)
        assert isinstance(result, ProjectionResult)
        assert hasattr(result, "raw_monthly")
        assert hasattr(result, "adjusted_monthly")
        assert hasattr(result, "classification")
        assert hasattr(result, "overfitting_warning")
