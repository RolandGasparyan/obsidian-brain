"""
Unit tests for champion.stair_step_compounder (Layer 4 §7).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.stair_step_compounder import (
    StairStepCompounder,
    StairStepConfig,
)


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

class TestConfig:
    def test_default_threshold(self):
        cfg = StairStepConfig()
        assert cfg.step_threshold_pct == 0.10

    def test_invalid_threshold_rejected(self):
        with pytest.raises(ValueError):
            StairStepConfig(step_threshold_pct=0)


# ─────────────────────────────────────────────
# Construction
# ─────────────────────────────────────────────

class TestConstruction:
    def test_initial_state(self):
        c = StairStepCompounder(starting_equity=10_000)
        assert c.state.initial_equity == 10_000
        assert c.state.current_baseline == 10_000
        assert c.state.n_steps == 0

    def test_zero_equity_rejected(self):
        with pytest.raises(ValueError):
            StairStepCompounder(starting_equity=0)

    def test_negative_equity_rejected(self):
        with pytest.raises(ValueError):
            StairStepCompounder(starting_equity=-1)


# ─────────────────────────────────────────────
# Update behavior
# ─────────────────────────────────────────────

class TestUpdate:
    def test_below_threshold_no_step(self):
        c = StairStepCompounder(starting_equity=10_000)
        d = c.update(10_900)  # 9% growth, below 10%
        assert d.new_step_locked is False
        assert d.current_baseline == 10_000
        assert d.n_steps == 0

    def test_at_exactly_10pct_locks_step(self):
        c = StairStepCompounder(starting_equity=10_000)
        d = c.update(11_000)  # exactly 10% → step locked
        assert d.new_step_locked is True
        assert d.current_baseline == 11_000
        assert d.n_steps == 1

    def test_below_baseline_does_not_unlock(self):
        c = StairStepCompounder(starting_equity=10_000)
        c.update(11_000)  # lock first step at 11_000
        d = c.update(9_500)  # equity drops below baseline
        # n_steps remains; growth is negative
        assert d.new_step_locked is False
        assert d.n_steps == 1
        assert d.current_baseline == 11_000
        assert d.growth_since_baseline_pct < 0

    def test_multiple_steps_locked_in_one_update(self):
        c = StairStepCompounder(starting_equity=10_000)
        # Equity goes from 10_000 to 14_000 in a single update.
        # 10_000 → 11_000 → 12_100 → 13_310 → 14_641 (4 steps)
        # 14_000 < 14_641 → only 3 steps lock, baseline = 13_310
        d = c.update(14_000)
        assert d.new_step_locked is True
        assert d.n_steps == 3
        assert d.current_baseline == pytest.approx(10_000 * (1.10 ** 3))

    def test_zero_equity_in_update_rejected(self):
        c = StairStepCompounder(starting_equity=10_000)
        with pytest.raises(ValueError):
            c.update(0)


# ─────────────────────────────────────────────
# Sequential updates
# ─────────────────────────────────────────────

class TestSequentialUpdates:
    def test_step_then_grow_more(self):
        c = StairStepCompounder(starting_equity=10_000)
        d1 = c.update(11_000)
        assert d1.n_steps == 1
        # After locking baseline at 11_000, growth to 11_500 is +4.5% (no step)
        d2 = c.update(11_500)
        assert d2.new_step_locked is False
        assert d2.n_steps == 1
        # Growth to 12_100 from 11_000 is exactly +10% → step
        d3 = c.update(12_100)
        assert d3.new_step_locked is True
        assert d3.n_steps == 2


# ─────────────────────────────────────────────
# Reset
# ─────────────────────────────────────────────

class TestReset:
    def test_reset_default_uses_initial_equity(self):
        c = StairStepCompounder(starting_equity=10_000)
        c.update(15_000)  # locks several steps
        c.reset()
        assert c.state.initial_equity == 10_000
        assert c.state.current_baseline == 10_000
        assert c.state.n_steps == 0

    def test_reset_with_new_starting_equity(self):
        c = StairStepCompounder(starting_equity=10_000)
        c.reset(starting_equity=20_000)
        assert c.state.initial_equity == 20_000
        assert c.state.current_baseline == 20_000

    def test_reset_negative_rejected(self):
        c = StairStepCompounder(starting_equity=10_000)
        with pytest.raises(ValueError):
            c.reset(starting_equity=-1)
