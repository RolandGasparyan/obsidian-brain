"""
Unit tests for champion.regime_breadth.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.regime_breadth import MarketBreadthCalculator, MarketBreadthConfig


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

class TestConfig:
    def test_defaults(self):
        cfg = MarketBreadthConfig()
        assert cfg.ma_window == 20
        assert cfg.min_history_bars == 20

    def test_invalid_ma_window_rejected(self):
        with pytest.raises(ValueError):
            MarketBreadthConfig(ma_window=1)

    def test_min_history_below_ma_rejected(self):
        with pytest.raises(ValueError):
            MarketBreadthConfig(ma_window=20, min_history_bars=10)


# ─────────────────────────────────────────────
# Empty / insufficient history
# ─────────────────────────────────────────────

class TestEmptyAndInsufficient:
    def test_empty_returns_neutral(self):
        calc = MarketBreadthCalculator()
        assert calc.compute_breadth() == 0.5

    def test_insufficient_history_returns_neutral(self):
        calc = MarketBreadthCalculator(MarketBreadthConfig(ma_window=20, min_history_bars=20))
        for _ in range(5):
            calc.update_pair_close("BTC_USDT", 50_000.0)
        assert calc.compute_breadth() == 0.5
        assert calc.n_eligible_pairs() == 0


# ─────────────────────────────────────────────
# Above / below MA
# ─────────────────────────────────────────────

class TestBreadthMath:
    def test_all_above_ma_returns_one(self):
        # Use small window for fast tests
        calc = MarketBreadthCalculator(MarketBreadthConfig(ma_window=5, min_history_bars=5))
        # Closes 1,2,3,4,5 → MA=3.0, last close 5 > 3.0 → above
        for i in range(1, 6):
            calc.update_pair_close("BTC_USDT", float(i))
        for i in range(1, 6):
            calc.update_pair_close("ETH_USDT", float(i) * 10)
        assert calc.compute_breadth() == 1.0

    def test_all_below_ma_returns_zero(self):
        calc = MarketBreadthCalculator(MarketBreadthConfig(ma_window=5, min_history_bars=5))
        # Closes 5,4,3,2,1 → MA=3.0, last close 1 < 3.0 → below
        for i in (5, 4, 3, 2, 1):
            calc.update_pair_close("BTC_USDT", float(i))
        for i in (50, 40, 30, 20, 10):
            calc.update_pair_close("ETH_USDT", float(i))
        assert calc.compute_breadth() == 0.0

    def test_50_50_split(self):
        calc = MarketBreadthCalculator(MarketBreadthConfig(ma_window=5, min_history_bars=5))
        # Pair 1 above MA
        for i in range(1, 6):
            calc.update_pair_close("BTC_USDT", float(i))
        # Pair 2 below MA
        for i in (5, 4, 3, 2, 1):
            calc.update_pair_close("ETH_USDT", float(i))
        assert calc.compute_breadth() == 0.5


# ─────────────────────────────────────────────
# Mixed eligibility
# ─────────────────────────────────────────────

class TestMixedEligibility:
    def test_excludes_undersample_pairs(self):
        calc = MarketBreadthCalculator(MarketBreadthConfig(ma_window=5, min_history_bars=5))
        # 5-bar pair, eligible
        for i in range(1, 6):
            calc.update_pair_close("BTC_USDT", float(i))
        # 2-bar pair, NOT eligible
        for i in (10, 20):
            calc.update_pair_close("ETH_USDT", float(i))

        assert calc.n_eligible_pairs() == 1
        # Only BTC contributes; it's above MA → breadth = 1.0
        assert calc.compute_breadth() == 1.0


# ─────────────────────────────────────────────
# Reset
# ─────────────────────────────────────────────

class TestReset:
    def test_reset_clears_history(self):
        calc = MarketBreadthCalculator(MarketBreadthConfig(ma_window=5, min_history_bars=5))
        for i in range(1, 6):
            calc.update_pair_close("BTC_USDT", float(i))
        calc.reset()
        assert calc.compute_breadth() == 0.5
        assert calc.n_eligible_pairs() == 0


# ─────────────────────────────────────────────
# Window eviction
# ─────────────────────────────────────────────

class TestWindowEviction:
    def test_old_closes_evict(self):
        calc = MarketBreadthCalculator(MarketBreadthConfig(ma_window=3, min_history_bars=3))
        # Add 5 closes; only last 3 retained
        for i in (1, 2, 3, 100, 200):
            calc.update_pair_close("BTC_USDT", float(i))
        # Window now has [3, 100, 200]; MA=101; last=200 > 101 → above
        assert calc.compute_breadth() == 1.0
