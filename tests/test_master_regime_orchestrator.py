"""
Unit tests for champion.master_regime_orchestrator.

Covers all 5 regime branches (DISABLED_BY_DRIFT, HIGH_VOL, TRENDING,
LOW_VOL, NORMAL) plus priority ordering and state persistence.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.master_regime_orchestrator import (
    MasterRegimeOrchestrator,
    OrchestratorDecision,
)


def make() -> MasterRegimeOrchestrator:
    return MasterRegimeOrchestrator()


# ─────────────────────────────────────────────
# Initial state
# ─────────────────────────────────────────────

class TestInitialState:
    def test_initial_regime_is_normal(self):
        orch = make()
        assert orch.current_regime == "NORMAL"


# ─────────────────────────────────────────────
# Drift override (highest priority)
# ─────────────────────────────────────────────

class TestDriftOverride:
    def test_drift_disabled_returns_disabled(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=False,
            regime_volatility_percentile=0.50,
            regime_trend_score=0.50,
        )
        assert d.engine_enabled is False
        assert d.exposure_multiplier == 0.0
        assert d.regime_label == "DISABLED_BY_DRIFT"

    def test_drift_disabled_overrides_high_vol(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=False,
            regime_volatility_percentile=0.95,  # would be HIGH_VOL
            regime_trend_score=0.50,
        )
        assert d.regime_label == "DISABLED_BY_DRIFT"
        assert d.exposure_multiplier == 0.0

    def test_drift_disabled_overrides_trending(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=False,
            regime_volatility_percentile=0.50,
            regime_trend_score=0.95,  # would be TRENDING
        )
        assert d.regime_label == "DISABLED_BY_DRIFT"
        assert d.exposure_multiplier == 0.0


# ─────────────────────────────────────────────
# Regime classification (when drift_enabled=True)
# ─────────────────────────────────────────────

class TestHighVolatility:
    def test_high_volatility_classification(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.85,
            regime_trend_score=0.50,
        )
        assert d.regime_label == "HIGH_VOL"
        assert d.exposure_multiplier == 0.5
        assert d.engine_enabled is True

    def test_high_vol_takes_precedence_over_trending(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.85,  # HIGH_VOL signal
            regime_trend_score=0.95,            # also TRENDING signal
        )
        # HIGH_VOL fires first → defensive sizing wins
        assert d.regime_label == "HIGH_VOL"
        assert d.exposure_multiplier == 0.5

    def test_high_vol_threshold_boundary(self):
        # Strictly > 0.80 triggers HIGH_VOL.
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.81,
            regime_trend_score=0.50,
        )
        assert d.regime_label == "HIGH_VOL"

        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.80,  # NOT strictly greater
            regime_trend_score=0.50,
        )
        assert d.regime_label == "NORMAL"


class TestTrending:
    def test_trending_classification(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.50,
            regime_trend_score=0.80,
        )
        assert d.regime_label == "TRENDING"
        assert d.exposure_multiplier == 1.2

    def test_trending_takes_precedence_over_low_vol(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.10,  # LOW_VOL signal
            regime_trend_score=0.85,            # also TRENDING signal
        )
        # TRENDING fires before LOW_VOL → opportunity sizing
        assert d.regime_label == "TRENDING"
        assert d.exposure_multiplier == 1.2

    def test_trending_threshold_boundary(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.50,
            regime_trend_score=0.71,
        )
        assert d.regime_label == "TRENDING"

        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.50,
            regime_trend_score=0.70,  # NOT strictly greater
        )
        assert d.regime_label == "NORMAL"


class TestLowVolatility:
    def test_low_volatility_classification(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.10,
            regime_trend_score=0.50,
        )
        assert d.regime_label == "LOW_VOL"
        assert d.exposure_multiplier == 0.7

    def test_low_vol_threshold_boundary(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.19,
            regime_trend_score=0.50,
        )
        assert d.regime_label == "LOW_VOL"

        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.20,  # NOT strictly less
            regime_trend_score=0.50,
        )
        assert d.regime_label == "NORMAL"


class TestNormal:
    def test_normal_classification(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.50,
            regime_trend_score=0.50,
        )
        assert d.regime_label == "NORMAL"
        assert d.exposure_multiplier == 1.0

    def test_normal_at_inner_boundaries(self):
        orch = make()
        d = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.20,  # not low, not high
            regime_trend_score=0.70,            # not trending
        )
        assert d.regime_label == "NORMAL"
        assert d.exposure_multiplier == 1.0


# ─────────────────────────────────────────────
# State persistence across calls
# ─────────────────────────────────────────────

class TestStatePersistence:
    def test_current_regime_updates_each_call(self):
        orch = make()

        orch.evaluate(drift_enabled=True, regime_volatility_percentile=0.85, regime_trend_score=0.0)
        assert orch.current_regime == "HIGH_VOL"

        orch.evaluate(drift_enabled=True, regime_volatility_percentile=0.50, regime_trend_score=0.85)
        assert orch.current_regime == "TRENDING"

        orch.evaluate(drift_enabled=True, regime_volatility_percentile=0.10, regime_trend_score=0.0)
        assert orch.current_regime == "LOW_VOL"

        orch.evaluate(drift_enabled=False, regime_volatility_percentile=0.50, regime_trend_score=0.50)
        assert orch.current_regime == "DISABLED_BY_DRIFT"

        orch.evaluate(drift_enabled=True, regime_volatility_percentile=0.50, regime_trend_score=0.50)
        assert orch.current_regime == "NORMAL"


# ─────────────────────────────────────────────
# Decision dataclass shape
# ─────────────────────────────────────────────

class TestDecisionDataclass:
    def test_decision_has_three_fields(self):
        orch = make()
        d = orch.evaluate(drift_enabled=True, regime_volatility_percentile=0.5, regime_trend_score=0.5)
        assert isinstance(d, OrchestratorDecision)
        assert hasattr(d, "engine_enabled")
        assert hasattr(d, "exposure_multiplier")
        assert hasattr(d, "regime_label")

    def test_disabled_decision_multiplier_is_zero(self):
        orch = make()
        d = orch.evaluate(drift_enabled=False, regime_volatility_percentile=0.5, regime_trend_score=0.5)
        assert d.exposure_multiplier == 0.0
