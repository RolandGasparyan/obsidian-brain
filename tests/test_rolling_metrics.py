"""
Unit tests for champion.rolling_metrics.

Covers: empty state, partial fill, window eviction, win-rate, profit-factor,
expectancy, max consecutive losses, window-local drawdown, Pearson IC,
zero-variance IC fallback, no-loss profit-factor inf, exact-flat trades.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.rolling_metrics import (
    RollingMetricsAggregator,
    RollingMetrics,
    TradeRecord,
)


# ─────────────────────────────────────────────
# Construction
# ─────────────────────────────────────────────

class TestConstruction:
    def test_default_window_size(self):
        agg = RollingMetricsAggregator()
        assert agg.window_size == 50

    def test_custom_window_size(self):
        agg = RollingMetricsAggregator(window_size=20)
        assert agg.window_size == 20

    def test_zero_window_rejected(self):
        with pytest.raises(ValueError):
            RollingMetricsAggregator(window_size=0)

    def test_negative_window_rejected(self):
        with pytest.raises(ValueError):
            RollingMetricsAggregator(window_size=-1)


# ─────────────────────────────────────────────
# Empty / single trade
# ─────────────────────────────────────────────

class TestEmptyAndSingle:
    def test_empty_returns_zero_metrics(self):
        m = RollingMetricsAggregator().compute()
        assert m.trades == 0
        assert m.win_rate == 0.0
        assert m.profit_factor == 0.0
        assert m.expectancy_r == 0.0
        assert m.max_consecutive_losses == 0
        assert m.drawdown_pct == 0.0
        assert m.information_coefficient == 0.0

    def test_single_winning_trade(self):
        agg = RollingMetricsAggregator()
        agg.add_trade(TradeRecord(r_multiple=2.0, equity=10_200))
        m = agg.compute()
        assert m.trades == 1
        assert m.win_rate == 1.0
        assert m.profit_factor == float("inf")  # no losses
        assert m.expectancy_r == 2.0
        assert m.max_consecutive_losses == 0
        assert m.drawdown_pct == 0.0  # only one equity point
        assert m.information_coefficient == 0.0  # n < 2

    def test_single_losing_trade(self):
        agg = RollingMetricsAggregator()
        agg.add_trade(TradeRecord(r_multiple=-1.0, equity=9_900))
        m = agg.compute()
        assert m.trades == 1
        assert m.win_rate == 0.0
        # No wins → gross_profit=0, gross_loss=1.0; PF = 0.0/1.0 = 0.0
        assert m.profit_factor == 0.0
        assert m.expectancy_r == -1.0
        assert m.max_consecutive_losses == 1


# ─────────────────────────────────────────────
# Window eviction
# ─────────────────────────────────────────────

class TestWindowEviction:
    def test_window_caps_at_size(self):
        agg = RollingMetricsAggregator(window_size=3)
        for r in range(5):  # add 5, only last 3 kept
            agg.add_trade(TradeRecord(r_multiple=float(r), equity=10_000 + r))
        m = agg.compute()
        assert m.trades == 3

    def test_old_trades_evicted_from_stats(self):
        agg = RollingMetricsAggregator(window_size=3)
        # First, 3 wins.
        for _ in range(3):
            agg.add_trade(TradeRecord(r_multiple=2.0, equity=10_500))
        m1 = agg.compute()
        assert m1.win_rate == 1.0
        # Now add 3 losses: window now contains 3 losses, the wins evicted.
        for _ in range(3):
            agg.add_trade(TradeRecord(r_multiple=-1.0, equity=9_500))
        m2 = agg.compute()
        assert m2.trades == 3
        assert m2.win_rate == 0.0


# ─────────────────────────────────────────────
# Win rate / profit factor / expectancy
# ─────────────────────────────────────────────

class TestWinRate:
    def test_50_50(self):
        agg = RollingMetricsAggregator()
        for _ in range(5):
            agg.add_trade(TradeRecord(r_multiple=2.0, equity=10_000))
        for _ in range(5):
            agg.add_trade(TradeRecord(r_multiple=-1.0, equity=10_000))
        m = agg.compute()
        assert m.win_rate == 0.5

    def test_flat_trade_not_counted_as_win(self):
        agg = RollingMetricsAggregator()
        agg.add_trade(TradeRecord(r_multiple=2.0, equity=10_000))
        agg.add_trade(TradeRecord(r_multiple=0.0, equity=10_000))  # flat
        agg.add_trade(TradeRecord(r_multiple=-1.0, equity=10_000))
        m = agg.compute()
        # Flat is neither a win nor a loss; win_rate = wins / total = 1/3.
        assert m.trades == 3
        assert m.win_rate == pytest.approx(1.0 / 3.0)


class TestProfitFactor:
    def test_pf_equals_gross_profit_over_loss(self):
        agg = RollingMetricsAggregator()
        # 2 wins of +2R, 1 loss of -1R → PF = 4 / 1 = 4.0
        agg.add_trade(TradeRecord(r_multiple=2.0, equity=10_000))
        agg.add_trade(TradeRecord(r_multiple=2.0, equity=10_000))
        agg.add_trade(TradeRecord(r_multiple=-1.0, equity=10_000))
        m = agg.compute()
        assert m.profit_factor == pytest.approx(4.0)

    def test_pf_inf_when_no_losses(self):
        agg = RollingMetricsAggregator()
        for _ in range(10):
            agg.add_trade(TradeRecord(r_multiple=1.0, equity=10_000))
        m = agg.compute()
        assert m.profit_factor == float("inf")


class TestExpectancy:
    def test_expectancy_mean_of_R(self):
        agg = RollingMetricsAggregator()
        agg.add_trade(TradeRecord(r_multiple=1.0, equity=10_000))
        agg.add_trade(TradeRecord(r_multiple=2.0, equity=10_000))
        agg.add_trade(TradeRecord(r_multiple=-1.0, equity=10_000))
        m = agg.compute()
        # (1+2-1)/3 = 0.667
        assert m.expectancy_r == pytest.approx(2.0 / 3.0)


# ─────────────────────────────────────────────
# Max consecutive losses
# ─────────────────────────────────────────────

class TestMaxConsecutiveLosses:
    def test_simple_run(self):
        agg = RollingMetricsAggregator()
        # W L L L W L L
        seq = [1.0, -1.0, -1.0, -1.0, 1.0, -1.0, -1.0]
        for r in seq:
            agg.add_trade(TradeRecord(r_multiple=r, equity=10_000))
        m = agg.compute()
        assert m.max_consecutive_losses == 3

    def test_no_consecutive_losses(self):
        agg = RollingMetricsAggregator()
        agg.add_trade(TradeRecord(r_multiple=2.0, equity=10_000))
        agg.add_trade(TradeRecord(r_multiple=-1.0, equity=10_000))
        agg.add_trade(TradeRecord(r_multiple=2.0, equity=10_000))
        m = agg.compute()
        assert m.max_consecutive_losses == 1

    def test_all_losses(self):
        agg = RollingMetricsAggregator()
        for _ in range(5):
            agg.add_trade(TradeRecord(r_multiple=-1.0, equity=10_000))
        m = agg.compute()
        assert m.max_consecutive_losses == 5


# ─────────────────────────────────────────────
# Window-local drawdown
# ─────────────────────────────────────────────

class TestDrawdown:
    def test_no_drawdown_when_monotonic(self):
        agg = RollingMetricsAggregator()
        for eq in (10_000, 10_100, 10_200, 10_300):
            agg.add_trade(TradeRecord(r_multiple=0.5, equity=eq))
        m = agg.compute()
        assert m.drawdown_pct == 0.0

    def test_drawdown_from_peak(self):
        agg = RollingMetricsAggregator()
        for eq in (10_000, 11_000, 10_450):  # peak 11_000, low 10_450 → DD = 5%
            agg.add_trade(TradeRecord(r_multiple=0.0, equity=eq))
        m = agg.compute()
        assert m.drawdown_pct == pytest.approx(0.05, abs=1e-9)

    def test_drawdown_uses_window_local_peak_only(self):
        agg = RollingMetricsAggregator(window_size=2)
        # Old peak should evict.
        for eq in (10_000, 12_000, 11_000, 10_000):
            agg.add_trade(TradeRecord(r_multiple=0.0, equity=eq))
        # Window now contains [11_000, 10_000]; peak=11_000, DD = 1 - 10_000/11_000 ≈ 0.0909.
        m = agg.compute()
        assert m.drawdown_pct == pytest.approx(1 - 10_000 / 11_000, abs=1e-9)


# ─────────────────────────────────────────────
# Information coefficient (Pearson)
# ─────────────────────────────────────────────

class TestInformationCoefficient:
    def test_perfect_positive_correlation(self):
        agg = RollingMetricsAggregator()
        for i in range(10):
            agg.add_trade(TradeRecord(
                r_multiple=0.0,
                equity=10_000,
                prediction=float(i),
                outcome=float(i) * 2.0,  # linear positive
            ))
        m = agg.compute()
        assert m.information_coefficient == pytest.approx(1.0, abs=1e-9)

    def test_perfect_negative_correlation(self):
        agg = RollingMetricsAggregator()
        for i in range(10):
            agg.add_trade(TradeRecord(
                r_multiple=0.0,
                equity=10_000,
                prediction=float(i),
                outcome=-float(i),
            ))
        m = agg.compute()
        assert m.information_coefficient == pytest.approx(-1.0, abs=1e-9)

    def test_zero_variance_returns_zero(self):
        # All predictions identical → den_x = 0 → IC = 0.0
        agg = RollingMetricsAggregator()
        for i in range(5):
            agg.add_trade(TradeRecord(
                r_multiple=0.0,
                equity=10_000,
                prediction=1.0,  # constant
                outcome=float(i),
            ))
        m = agg.compute()
        assert m.information_coefficient == 0.0


# ─────────────────────────────────────────────
# Snapshot dataclass shape
# ─────────────────────────────────────────────

class TestRollingMetricsDataclass:
    def test_compute_returns_RollingMetrics(self):
        m = RollingMetricsAggregator().compute()
        assert isinstance(m, RollingMetrics)
        for key in (
            "trades", "win_rate", "profit_factor", "expectancy_r",
            "max_consecutive_losses", "drawdown_pct", "information_coefficient",
        ):
            assert hasattr(m, key)
