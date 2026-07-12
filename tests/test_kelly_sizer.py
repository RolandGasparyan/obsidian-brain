"""
Unit tests for champion.kelly_sizer (Layer 3 §1).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.kelly_sizer import KellySizer, KellySizerConfig


# ─────────────────────────────────────────────
# Config validation
# ─────────────────────────────────────────────

class TestConfig:
    def test_default_is_quarter_kelly(self):
        cfg = KellySizerConfig()
        assert cfg.fraction_mode == "quarter"
        assert cfg.max_risk_per_trade == 0.01
        assert cfg.dd_reduction_threshold == 0.10
        assert cfg.dd_reduction_factor == 0.5
        assert cfg.freeze_on_expectancy_decline is True

    def test_invalid_fraction_mode_rejected(self):
        with pytest.raises(ValueError):
            KellySizerConfig(fraction_mode="eighth")

    def test_invalid_max_risk_rejected(self):
        with pytest.raises(ValueError):
            KellySizerConfig(max_risk_per_trade=0.0)
        with pytest.raises(ValueError):
            KellySizerConfig(max_risk_per_trade=1.5)

    def test_invalid_dd_threshold_rejected(self):
        with pytest.raises(ValueError):
            KellySizerConfig(dd_reduction_threshold=-0.1)

    def test_invalid_dd_factor_rejected(self):
        with pytest.raises(ValueError):
            KellySizerConfig(dd_reduction_factor=0.0)
        with pytest.raises(ValueError):
            KellySizerConfig(dd_reduction_factor=1.5)


# ─────────────────────────────────────────────
# Classic Kelly formula
# ─────────────────────────────────────────────

class TestClassicKelly:
    def test_spec_example(self):
        # From L99_CAPITAL_MATHEMATICS §1.1:
        # WR=0.5, AvgWin=2, AvgLoss=1 → f* = 0.25
        f = KellySizer.classic_kelly(win_rate=0.5, avg_win_r=2.0, avg_loss_r=1.0)
        assert f == pytest.approx(0.25)

    def test_zero_win_rate_returns_negative(self):
        # No wins → all loss → strongly negative
        f = KellySizer.classic_kelly(win_rate=0.0, avg_win_r=2.0, avg_loss_r=1.0)
        assert f < 0

    def test_high_b_high_p_returns_high_kelly(self):
        # b=3, p=0.7 → b*p - q = 2.1 - 0.3 = 1.8; f* = 1.8/3 = 0.6
        f = KellySizer.classic_kelly(win_rate=0.7, avg_win_r=3.0, avg_loss_r=1.0)
        assert f == pytest.approx(0.6)

    def test_invalid_win_rate_raises(self):
        with pytest.raises(ValueError):
            KellySizer.classic_kelly(win_rate=1.5, avg_win_r=2.0, avg_loss_r=1.0)
        with pytest.raises(ValueError):
            KellySizer.classic_kelly(win_rate=-0.1, avg_win_r=2.0, avg_loss_r=1.0)

    def test_zero_avg_loss_raises(self):
        with pytest.raises(ValueError):
            KellySizer.classic_kelly(win_rate=0.5, avg_win_r=2.0, avg_loss_r=0.0)

    def test_negative_avg_loss_raises(self):
        with pytest.raises(ValueError):
            KellySizer.classic_kelly(win_rate=0.5, avg_win_r=2.0, avg_loss_r=-1.0)


# ─────────────────────────────────────────────
# Compute (constrained Kelly)
# ─────────────────────────────────────────────

class TestComputeQuarterKelly:
    def test_quarter_kelly_capped_by_1pct(self):
        # raw = 0.25 → quarter = 0.0625 → capped at 0.01
        sizer = KellySizer()  # quarter, 1% cap
        f = sizer.compute(win_rate=0.5, avg_win_r=2.0, avg_loss_r=1.0)
        assert f == pytest.approx(0.01)

    def test_quarter_kelly_below_cap(self):
        # Need a small edge so quarter Kelly < 1% cap.
        # WR=0.51, AvgWin=1.02, AvgLoss=1.0:
        #   b = 1.02
        #   raw = (1.02*0.51 - 0.49)/1.02 = 0.0302/1.02 ≈ 0.02961
        #   quarter = 0.02961 * 0.25 ≈ 0.00740 (below 0.01 cap)
        sizer = KellySizer()
        f = sizer.compute(win_rate=0.51, avg_win_r=1.02, avg_loss_r=1.0)
        assert 0 < f < 0.01
        assert f == pytest.approx(0.00740, abs=1e-4)

    def test_negative_kelly_returns_zero(self):
        # Bad edge: WR=0.3, b=1.0 → negative Kelly
        sizer = KellySizer()
        f = sizer.compute(win_rate=0.3, avg_win_r=1.0, avg_loss_r=1.0)
        assert f == 0.0

    def test_zero_kelly_returns_zero(self):
        # Break-even: WR=0.5, b=1.0 → b*p - q = 0.0; f* = 0
        sizer = KellySizer()
        f = sizer.compute(win_rate=0.5, avg_win_r=1.0, avg_loss_r=1.0)
        assert f == 0.0


class TestDrawdownReduction:
    def test_dd_below_threshold_no_reduction(self):
        sizer = KellySizer()
        normal = sizer.compute(0.55, 1.5, 1.0, rolling_dd=0.05)
        # 5% DD below 10% threshold → no halving
        # Should equal compute with rolling_dd=0
        baseline = sizer.compute(0.55, 1.5, 1.0, rolling_dd=0.0)
        assert normal == baseline

    def test_dd_above_threshold_halves(self):
        # Need an edge small enough that BOTH normal and reduced are below
        # the 1% cap, so we can verify the halving cleanly.
        # WR=0.51, AvgWin=1.02, AvgLoss=1.0 → quarter Kelly ≈ 0.0074
        # normal (DD 5% < 10%):  0.0074
        # reduced (DD 15% > 10%): 0.0074 * 0.5 = 0.0037
        sizer = KellySizer()
        normal = sizer.compute(0.51, 1.02, 1.0, rolling_dd=0.05)
        reduced = sizer.compute(0.51, 1.02, 1.0, rolling_dd=0.15)
        assert 0 < reduced < normal < 0.01  # both below cap
        assert reduced == pytest.approx(normal * 0.5, abs=1e-6)


class TestFractionMode:
    def test_full_kelly_capped(self):
        cfg = KellySizerConfig(fraction_mode="full")
        sizer = KellySizer(cfg)
        # raw = 0.25 → full = 0.25 → capped at 0.01
        f = sizer.compute(0.5, 2.0, 1.0)
        assert f == pytest.approx(0.01)

    def test_half_kelly_capped(self):
        cfg = KellySizerConfig(fraction_mode="half")
        sizer = KellySizer(cfg)
        # raw = 0.25 → half = 0.125 → capped at 0.01
        f = sizer.compute(0.5, 2.0, 1.0)
        assert f == pytest.approx(0.01)


class TestExpectancyFreeze:
    def test_current_below_baseline_freezes(self):
        sizer = KellySizer()
        f = sizer.compute(
            win_rate=0.55, avg_win_r=2.0, avg_loss_r=1.0,
            baseline_expectancy=0.5, current_expectancy=0.3,
        )
        assert f == 0.0

    def test_current_above_baseline_does_not_freeze(self):
        sizer = KellySizer()
        f = sizer.compute(
            win_rate=0.55, avg_win_r=2.0, avg_loss_r=1.0,
            baseline_expectancy=0.3, current_expectancy=0.5,
        )
        assert f > 0

    def test_current_equal_baseline_does_not_freeze(self):
        # Strict less-than, so equality passes
        sizer = KellySizer()
        f = sizer.compute(
            win_rate=0.55, avg_win_r=2.0, avg_loss_r=1.0,
            baseline_expectancy=0.5, current_expectancy=0.5,
        )
        assert f > 0

    def test_freeze_disabled_via_config(self):
        cfg = KellySizerConfig(freeze_on_expectancy_decline=False)
        sizer = KellySizer(cfg)
        f = sizer.compute(
            win_rate=0.55, avg_win_r=2.0, avg_loss_r=1.0,
            baseline_expectancy=0.5, current_expectancy=0.3,
        )
        assert f > 0

    def test_freeze_inactive_when_baseline_none(self):
        sizer = KellySizer()
        f = sizer.compute(
            win_rate=0.55, avg_win_r=2.0, avg_loss_r=1.0,
            baseline_expectancy=None, current_expectancy=None,
        )
        assert f > 0
