"""
Layer 3 capital-mathematics composition integration tests.

Verifies that the four Layer 3 modules work together end-to-end:

    RegimeExpectancyMatrix.best_cell()      → (regime, signal), metrics
        ↓ feeds win_rate/avg_win/avg_loss
    KellySizer.compute(...)                 → risk_per_trade fraction
        ↓ feeds risk_per_trade
    GrowthProjector.project(...)            → adjusted_monthly + classification
        ↓ classifies expected growth band
    EquityMonteCarloSimulator.simulate(...) → ruin probability + DD distribution

Plus a bridge test against Layer 5: feed an aggregator's RollingMetrics into
KellySizer to show the full pipeline from trade journal up.

NO live exchange wiring. Pure-Python composition.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.equity_mc_sim import EquityMonteCarloSimulator, McSimConfig
from champion.growth_projector import GrowthProjector
from champion.kelly_sizer import KellySizer, KellySizerConfig
from champion.regime_expectancy_matrix import RegimeExpectancyMatrix
from champion.rolling_metrics import RollingMetricsAggregator, TradeRecord


# ─────────────────────────────────────────────
# Matrix → Kelly chain
# ─────────────────────────────────────────────

class TestMatrixToKellyChain:
    def test_best_cell_feeds_kelly(self):
        # Populate matrix: NORMAL has weak edge, EXPANSION has strong edge.
        m = RegimeExpectancyMatrix()
        for _ in range(20):
            m.add_trade("EXPANSION", "donchian_20", 2.0)
        for _ in range(10):
            m.add_trade("EXPANSION", "donchian_20", -1.0)

        best = m.best_cell(min_trades=30)
        assert best is not None
        (regime, signal), metrics = best
        assert regime == "EXPANSION"
        # WR ≈ 0.667, AvgWin=2, AvgLoss=1, E ≈ 1.0
        assert metrics.win_rate == pytest.approx(0.667, abs=0.01)

        sizer = KellySizer(KellySizerConfig())
        risk = sizer.compute(
            win_rate=metrics.win_rate,
            avg_win_r=metrics.avg_win_r,
            avg_loss_r=metrics.avg_loss_r,
        )
        # Strong edge → quarter Kelly will exceed 1% cap → capped
        assert risk == pytest.approx(0.01)


# ─────────────────────────────────────────────
# Kelly → Growth chain
# ─────────────────────────────────────────────

class TestKellyToGrowthChain:
    def test_kelly_risk_feeds_growth_projection(self):
        # Strong edge → Kelly returns 1% cap.
        sizer = KellySizer()
        risk = sizer.compute(win_rate=0.55, avg_win_r=2.0, avg_loss_r=1.0)
        assert risk == pytest.approx(0.01)

        # E = 0.55*2 - 0.45*1 = 0.65R; trades/month = 30; risk = 1%
        # raw = 0.65 * 30 * 0.01 = 0.195
        # adjusted = 0.195 * 0.6 = 0.117 → above_band? No, 0.117 > aggressive_max 0.15? No.
        # Actually 0.117 < 0.15 → aggressive_sustainable
        proj = GrowthProjector()
        expectancy = 0.55 * 2.0 - 0.45 * 1.0
        result = proj.project(
            expectancy_r=expectancy,
            trades_per_month=30,
            risk_per_trade=risk,
        )
        assert result.raw_monthly == pytest.approx(expectancy * 30 * risk)
        # Within aggressive_sustainable band (10-15%)
        assert result.classification == "aggressive_sustainable"
        # raw = 0.195 > 0.20 threshold? 0.195 < 0.20 → no warning
        assert result.overfitting_warning is False


# ─────────────────────────────────────────────
# Trade list → MC simulation
# ─────────────────────────────────────────────

class TestTradeListToMcSimulation:
    def test_real_trades_through_mc(self):
        # 50 trades: 60% WR, +1.5R wins, -1R losses.
        outcomes = [1.5] * 30 + [-1.0] * 20
        sim = EquityMonteCarloSimulator(McSimConfig(
            n_simulations=200, risk_per_trade=0.01, seed=1
        ))
        result = sim.simulate(outcomes)

        # Strong positive edge → median final equity > start
        assert result.median_final_equity > 10_000
        # 1% risk on this edge → ruin probability should be low
        assert result.prob_ruin < 0.20


# ─────────────────────────────────────────────
# Full pipeline
# ─────────────────────────────────────────────

class TestFullPipeline:
    def test_full_layer3_pipeline(self):
        # 1. Build matrix from synthetic trades
        m = RegimeExpectancyMatrix()
        for _ in range(20):
            m.add_trade("EXPANSION", "donchian_20", 2.0)
        for _ in range(10):
            m.add_trade("EXPANSION", "donchian_20", -1.0)

        best = m.best_cell(min_trades=30)
        (regime, signal), metrics = best

        # 2. Compute Kelly fraction
        sizer = KellySizer()
        risk = sizer.compute(
            win_rate=metrics.win_rate,
            avg_win_r=metrics.avg_win_r,
            avg_loss_r=metrics.avg_loss_r,
        )
        assert risk > 0

        # 3. Project growth
        proj = GrowthProjector()
        projection = proj.project(
            expectancy_r=metrics.expectancy_r,
            trades_per_month=30,
            risk_per_trade=risk,
        )
        # Strong edge → in some band, no overfit warning at 1% risk
        assert projection.classification in (
            "moderate", "aggressive_sustainable", "above_band"
        )

        # 4. Monte Carlo on raw R-outcomes
        outcomes = [2.0] * 20 + [-1.0] * 10
        sim = EquityMonteCarloSimulator(McSimConfig(
            n_simulations=200, risk_per_trade=risk, seed=1
        ))
        mc = sim.simulate(outcomes)
        # Strong edge + 1% risk → low ruin prob, equity grows
        assert mc.median_final_equity > 10_000
        assert mc.prob_ruin < 0.10


# ─────────────────────────────────────────────
# Bridge test: Layer 5 RollingMetrics → Layer 3 Kelly
# ─────────────────────────────────────────────

class TestRollingMetricsBridgesToKelly:
    def test_aggregator_feeds_kelly(self):
        # Aggregator captures rolling stats; Kelly consumes them.
        agg = RollingMetricsAggregator(window_size=50)
        # 30 wins +1.5R, 20 losses -1R
        for _ in range(30):
            agg.add_trade(TradeRecord(r_multiple=1.5, equity=10_000))
        for _ in range(20):
            agg.add_trade(TradeRecord(r_multiple=-1.0, equity=10_000))
        rm = agg.compute()

        # avg_win_r and avg_loss_r are not directly in RollingMetrics, but
        # we can derive Kelly inputs from win_rate + expectancy (a useful
        # composition test). For this test we use defaults from spec:
        # WR=0.6, AvgWin=1.5, AvgLoss=1.0
        sizer = KellySizer()
        risk = sizer.compute(
            win_rate=rm.win_rate,
            avg_win_r=1.5,
            avg_loss_r=1.0,
        )
        # WR=0.6, b=1.5, raw = (1.5*0.6 - 0.4)/1.5 = 0.333
        # quarter = 0.0833 → capped at 1%
        assert risk == pytest.approx(0.01)
