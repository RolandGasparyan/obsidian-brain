"""
Unit tests for champion.regime_expectancy_matrix (Layer 3 §2.1 + Layer 1 §1.4).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.regime_expectancy_matrix import (
    CellMetrics,
    RegimeExpectancyMatrix,
)


# ─────────────────────────────────────────────
# Empty / single
# ─────────────────────────────────────────────

class TestEmpty:
    def test_compute_empty_returns_empty_dict(self):
        m = RegimeExpectancyMatrix()
        assert m.compute() == {}

    def test_compute_cell_empty_returns_none(self):
        m = RegimeExpectancyMatrix()
        assert m.compute_cell("NORMAL", "donchian_20") is None

    def test_best_cell_empty_returns_none(self):
        m = RegimeExpectancyMatrix()
        assert m.best_cell() is None

    def test_cells_above_expectancy_empty(self):
        m = RegimeExpectancyMatrix()
        assert m.cells_above_expectancy(0.3) == []


# ─────────────────────────────────────────────
# Single cell stats
# ─────────────────────────────────────────────

class TestSingleCell:
    def _make(self):
        m = RegimeExpectancyMatrix()
        # 5 wins of +2R, 5 losses of -1R → WR=0.5, AvgWin=2, AvgLoss=1, E=0.5, PF=2
        for _ in range(5):
            m.add_trade("EXPANSION", "donchian_20", 2.0)
        for _ in range(5):
            m.add_trade("EXPANSION", "donchian_20", -1.0)
        return m

    def test_basic_metrics(self):
        m = self._make()
        c = m.compute_cell("EXPANSION", "donchian_20")
        assert c is not None
        assert c.n_trades == 10
        assert c.win_rate == 0.5
        assert c.avg_win_r == 2.0
        assert c.avg_loss_r == 1.0
        assert c.expectancy_r == pytest.approx(0.5)
        assert c.profit_factor == pytest.approx(2.0)

    def test_compute_returns_in_dict(self):
        m = self._make()
        d = m.compute()
        assert ("EXPANSION", "donchian_20") in d
        assert d[("EXPANSION", "donchian_20")].n_trades == 10


# ─────────────────────────────────────────────
# Profit factor edge cases
# ─────────────────────────────────────────────

class TestProfitFactor:
    def test_pf_inf_when_no_losses(self):
        m = RegimeExpectancyMatrix()
        for _ in range(5):
            m.add_trade("HIGH_IMPULSE", "breakout", 2.0)
        c = m.compute_cell("HIGH_IMPULSE", "breakout")
        assert c.profit_factor == float("inf")
        assert c.avg_loss_r == 0.0

    def test_pf_zero_when_no_wins(self):
        m = RegimeExpectancyMatrix()
        for _ in range(5):
            m.add_trade("DEAD", "breakout", -1.0)
        c = m.compute_cell("DEAD", "breakout")
        assert c.profit_factor == 0.0
        assert c.avg_win_r == 0.0


# ─────────────────────────────────────────────
# Multiple cells
# ─────────────────────────────────────────────

class TestMultipleCells:
    def _populate(self, m: RegimeExpectancyMatrix):
        # Cell A: NORMAL × donchian, 30 trades, modest E ≈ +0.2
        for _ in range(15):
            m.add_trade("NORMAL", "donchian_20", 1.0)
        for _ in range(15):
            m.add_trade("NORMAL", "donchian_20", -0.6)

        # Cell B: EXPANSION × donchian, 30 trades, strong E ≈ +0.8
        for _ in range(20):
            m.add_trade("EXPANSION", "donchian_20", 1.5)
        for _ in range(10):
            m.add_trade("EXPANSION", "donchian_20", -0.5)

        # Cell C: DEAD × donchian, 30 trades, negative E
        for _ in range(15):
            m.add_trade("DEAD", "donchian_20", 0.5)
        for _ in range(15):
            m.add_trade("DEAD", "donchian_20", -1.5)

    def test_all_three_cells_populated(self):
        m = RegimeExpectancyMatrix()
        self._populate(m)
        d = m.compute()
        assert len(d) == 3
        assert ("NORMAL", "donchian_20") in d
        assert ("EXPANSION", "donchian_20") in d
        assert ("DEAD", "donchian_20") in d

    def test_best_cell_is_expansion(self):
        m = RegimeExpectancyMatrix()
        self._populate(m)
        result = m.best_cell(min_trades=30)
        assert result is not None
        key, metrics = result
        assert key == ("EXPANSION", "donchian_20")
        assert metrics.expectancy_r > 0.5

    def test_cells_above_threshold_filters_correctly(self):
        m = RegimeExpectancyMatrix()
        self._populate(m)
        # E threshold = 0.3R: NORMAL ≈ 0.2 (below), EXPANSION ≈ 0.83 (above), DEAD < 0
        above = m.cells_above_expectancy(threshold=0.3, min_trades=30)
        assert len(above) == 1
        assert above[0][0] == ("EXPANSION", "donchian_20")

    def test_cells_above_threshold_zero_includes_positive(self):
        m = RegimeExpectancyMatrix()
        self._populate(m)
        # threshold=0: NORMAL (~0.2) and EXPANSION (~0.83) qualify; DEAD does not
        above = m.cells_above_expectancy(threshold=0.0, min_trades=30)
        assert len(above) == 2
        # Sorted descending by expectancy
        assert above[0][0] == ("EXPANSION", "donchian_20")
        assert above[1][0] == ("NORMAL", "donchian_20")


# ─────────────────────────────────────────────
# Min-trades filter
# ─────────────────────────────────────────────

class TestMinTradesFilter:
    def test_best_cell_excludes_undersample(self):
        m = RegimeExpectancyMatrix()
        # High-E cell with only 10 trades — excluded by min_trades=30
        for _ in range(10):
            m.add_trade("HIGH_IMPULSE", "breakout", 5.0)  # super positive
        # Lower-E cell with 30 trades — included
        for _ in range(20):
            m.add_trade("EXPANSION", "donchian_20", 1.0)
        for _ in range(10):
            m.add_trade("EXPANSION", "donchian_20", -0.5)

        # default min_trades=30
        result = m.best_cell()
        assert result is not None
        assert result[0] == ("EXPANSION", "donchian_20")

    def test_relaxed_min_trades_allows_undersample(self):
        m = RegimeExpectancyMatrix()
        for _ in range(10):
            m.add_trade("HIGH_IMPULSE", "breakout", 5.0)
        for _ in range(20):
            m.add_trade("EXPANSION", "donchian_20", 1.0)
        for _ in range(10):
            m.add_trade("EXPANSION", "donchian_20", -0.5)

        result = m.best_cell(min_trades=10)
        assert result is not None
        assert result[0] == ("HIGH_IMPULSE", "breakout")

    def test_no_cell_meets_min_trades(self):
        m = RegimeExpectancyMatrix()
        for _ in range(5):
            m.add_trade("NORMAL", "x", 1.0)
        assert m.best_cell(min_trades=30) is None
        assert m.cells_above_expectancy(0.0, min_trades=30) == []


# ─────────────────────────────────────────────
# Result shape
# ─────────────────────────────────────────────

class TestResultShape:
    def test_cell_metrics_has_all_fields(self):
        m = RegimeExpectancyMatrix()
        m.add_trade("NORMAL", "x", 1.0)
        c = m.compute_cell("NORMAL", "x")
        assert isinstance(c, CellMetrics)
        for f in ("n_trades", "win_rate", "avg_win_r", "avg_loss_r",
                  "expectancy_r", "profit_factor"):
            assert hasattr(c, f)
