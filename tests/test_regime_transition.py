"""
Unit tests for champion.regime_transition.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.regime_probability import RegimeProbabilities
from champion.regime_transition import (
    RegimeTransitionConfig,
    RegimeTransitionTracker,
    RegimeVelocity,
)


def probs(d: float, n: float, e: float, h: float) -> RegimeProbabilities:
    """Build RegimeProbabilities; values must sum to 1 for realism but
    the tracker doesn't enforce that — it just diff's them."""
    return RegimeProbabilities(p_dead=d, p_normal=n, p_expansion=e, p_high_impulse=h)


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

class TestConfig:
    def test_defaults(self):
        cfg = RegimeTransitionConfig()
        assert cfg.window == 12
        assert cfg.rapid_shift_threshold == 0.30

    def test_invalid_window_rejected(self):
        with pytest.raises(ValueError):
            RegimeTransitionConfig(window=1)

    def test_invalid_threshold_rejected(self):
        with pytest.raises(ValueError):
            RegimeTransitionConfig(rapid_shift_threshold=0.0)
        with pytest.raises(ValueError):
            RegimeTransitionConfig(rapid_shift_threshold=1.5)


# ─────────────────────────────────────────────
# Empty / single observation
# ─────────────────────────────────────────────

class TestEmptyAndSingle:
    def test_empty_returns_zero_velocity(self):
        tracker = RegimeTransitionTracker()
        v = tracker.compute_velocity()
        assert v.delta_dead == 0.0
        assert v.delta_normal == 0.0
        assert v.delta_expansion == 0.0
        assert v.delta_high_impulse == 0.0
        assert v.rapid_shift is False
        assert v.n_observations == 0

    def test_single_observation_zero_velocity(self):
        tracker = RegimeTransitionTracker()
        tracker.add_observation(probs(0.4, 0.3, 0.2, 0.1))
        v = tracker.compute_velocity()
        assert v.n_observations == 1
        assert v.rapid_shift is False
        assert v.delta_expansion == 0.0


# ─────────────────────────────────────────────
# Velocity computation
# ─────────────────────────────────────────────

class TestVelocity:
    def test_simple_delta(self):
        tracker = RegimeTransitionTracker()
        tracker.add_observation(probs(0.7, 0.2, 0.05, 0.05))
        tracker.add_observation(probs(0.4, 0.3, 0.2, 0.1))
        v = tracker.compute_velocity()
        assert v.delta_dead == pytest.approx(-0.3)
        assert v.delta_normal == pytest.approx(0.1)
        assert v.delta_expansion == pytest.approx(0.15)
        assert v.delta_high_impulse == pytest.approx(0.05)

    def test_rapid_shift_triggers_above_threshold(self):
        tracker = RegimeTransitionTracker(
            RegimeTransitionConfig(window=12, rapid_shift_threshold=0.30)
        )
        tracker.add_observation(probs(0.7, 0.2, 0.05, 0.05))
        tracker.add_observation(probs(0.3, 0.2, 0.4, 0.1))  # P(EXPANSION) +0.35
        v = tracker.compute_velocity()
        assert v.rapid_shift is True

    def test_no_rapid_shift_below_threshold(self):
        tracker = RegimeTransitionTracker(
            RegimeTransitionConfig(window=12, rapid_shift_threshold=0.30)
        )
        tracker.add_observation(probs(0.5, 0.3, 0.15, 0.05))
        tracker.add_observation(probs(0.4, 0.3, 0.25, 0.05))  # max delta 0.10
        v = tracker.compute_velocity()
        assert v.rapid_shift is False

    def test_rapid_shift_on_negative_delta(self):
        tracker = RegimeTransitionTracker(
            RegimeTransitionConfig(window=12, rapid_shift_threshold=0.30)
        )
        tracker.add_observation(probs(0.1, 0.1, 0.7, 0.1))  # high EXPANSION
        tracker.add_observation(probs(0.5, 0.3, 0.15, 0.05))  # P(EXPANSION) -0.55
        v = tracker.compute_velocity()
        assert v.rapid_shift is True
        assert v.delta_expansion < -0.5


# ─────────────────────────────────────────────
# Window eviction
# ─────────────────────────────────────────────

class TestWindowEviction:
    def test_old_observations_evicted(self):
        tracker = RegimeTransitionTracker(
            RegimeTransitionConfig(window=3, rapid_shift_threshold=0.30)
        )
        # Big swing in the FIRST observation — should evict by the time we add
        # 4 more.
        tracker.add_observation(probs(0.9, 0.05, 0.03, 0.02))   # eventually evicted
        tracker.add_observation(probs(0.45, 0.2, 0.25, 0.1))
        tracker.add_observation(probs(0.45, 0.2, 0.25, 0.1))
        tracker.add_observation(probs(0.45, 0.2, 0.25, 0.1))
        # Window now contains the last 3 (all identical) — velocity ≈ 0.
        v = tracker.compute_velocity()
        assert abs(v.delta_dead) < 1e-9
        assert abs(v.delta_expansion) < 1e-9


# ─────────────────────────────────────────────
# Reset
# ─────────────────────────────────────────────

class TestReset:
    def test_reset_clears_history(self):
        tracker = RegimeTransitionTracker()
        tracker.add_observation(probs(0.7, 0.2, 0.05, 0.05))
        tracker.add_observation(probs(0.3, 0.2, 0.4, 0.1))
        tracker.reset()
        assert tracker.n_observations() == 0
        v = tracker.compute_velocity()
        assert v.rapid_shift is False
        assert v.n_observations == 0
