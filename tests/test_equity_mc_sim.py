"""
Unit tests for champion.equity_mc_sim (Layer 3 §3.3 + §4).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.equity_mc_sim import (
    EquityMonteCarloSimulator,
    McSimConfig,
    McSimResult,
    _percentile,
)


# ─────────────────────────────────────────────
# Config validation
# ─────────────────────────────────────────────

class TestConfig:
    def test_defaults(self):
        cfg = McSimConfig()
        assert cfg.n_simulations == 1000
        assert cfg.starting_equity == 10_000.0
        assert cfg.risk_per_trade == 0.01
        assert cfg.ruin_threshold == 0.50
        assert cfg.dd_threshold == 0.30

    def test_invalid_n_sims_rejected(self):
        with pytest.raises(ValueError):
            McSimConfig(n_simulations=0)

    def test_invalid_starting_equity_rejected(self):
        with pytest.raises(ValueError):
            McSimConfig(starting_equity=0)

    def test_invalid_risk_rejected(self):
        with pytest.raises(ValueError):
            McSimConfig(risk_per_trade=0)
        with pytest.raises(ValueError):
            McSimConfig(risk_per_trade=1.5)


# ─────────────────────────────────────────────
# Determinism with seed
# ─────────────────────────────────────────────

class TestDeterminism:
    def test_same_seed_same_result(self):
        cfg = McSimConfig(n_simulations=100, seed=42)
        sim_a = EquityMonteCarloSimulator(cfg)
        sim_b = EquityMonteCarloSimulator(cfg)
        outcomes = [1.0, -0.5, 1.5, -0.8, 2.0, -1.0] * 10
        a = sim_a.simulate(outcomes)
        b = sim_b.simulate(outcomes)
        assert a.median_final_equity == b.median_final_equity
        assert a.prob_ruin == b.prob_ruin
        assert a.prob_dd_threshold == b.prob_dd_threshold

    def test_different_seeds_different_paths(self):
        # Multiplicative compounding is commutative — final equity is
        # invariant under reordering of the same R-outcome list. So
        # final-equity statistics will be identical regardless of seed.
        # However, drawdown and time-to-recovery DO depend on order, so
        # they must differ between seeds.
        outcomes = [1.0, -0.5, 1.5, -0.8] * 25
        a = EquityMonteCarloSimulator(McSimConfig(n_simulations=200, seed=1)).simulate(outcomes)
        b = EquityMonteCarloSimulator(McSimConfig(n_simulations=200, seed=2)).simulate(outcomes)
        # Drawdown is order-dependent → different seeds → different DD distributions
        assert a.median_max_drawdown != b.median_max_drawdown
        assert a.p95_max_drawdown != b.p95_max_drawdown


# ─────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_outcomes_raises(self):
        sim = EquityMonteCarloSimulator(McSimConfig(seed=1))
        with pytest.raises(ValueError):
            sim.simulate([])

    def test_all_wins_no_drawdown(self):
        sim = EquityMonteCarloSimulator(McSimConfig(n_simulations=50, seed=1))
        result = sim.simulate([1.0] * 30)
        assert result.median_max_drawdown == 0.0
        assert result.prob_ruin == 0.0
        assert result.prob_dd_threshold == 0.0
        assert result.median_final_equity > 10_000

    def test_all_losses_negative_growth(self):
        sim = EquityMonteCarloSimulator(McSimConfig(n_simulations=50, seed=1))
        result = sim.simulate([-1.0] * 30)
        # 30 × -1R × 1% risk → multiplicative ~ 0.99^30 ≈ 0.74
        # That's ~26% DD across all sims (no randomness needed since all same).
        assert result.median_final_equity < 10_000


# ─────────────────────────────────────────────
# Realistic edge scenario
# ─────────────────────────────────────────────

class TestRealisticScenarios:
    def test_positive_edge_grows_equity(self):
        # 50% WR, 2R wins, 1R losses → +0.5R expectancy
        outcomes = [2.0, -1.0] * 25
        sim = EquityMonteCarloSimulator(McSimConfig(n_simulations=200, seed=1))
        result = sim.simulate(outcomes)
        assert result.median_final_equity > 10_000

    def test_higher_risk_increases_ruin_prob(self):
        # Same outcomes, but at 5% risk vs 1% → ruin probability much higher
        outcomes = [-2.0] * 20 + [1.0] * 20  # bad edge
        low_risk = EquityMonteCarloSimulator(
            McSimConfig(n_simulations=200, risk_per_trade=0.01, seed=1)
        ).simulate(outcomes)
        high_risk = EquityMonteCarloSimulator(
            McSimConfig(n_simulations=200, risk_per_trade=0.05, seed=1)
        ).simulate(outcomes)
        assert high_risk.prob_ruin >= low_risk.prob_ruin
        assert high_risk.median_max_drawdown >= low_risk.median_max_drawdown


# ─────────────────────────────────────────────
# Result dataclass shape
# ─────────────────────────────────────────────

class TestResultShape:
    def test_all_fields_present(self):
        sim = EquityMonteCarloSimulator(McSimConfig(n_simulations=10, seed=1))
        result = sim.simulate([1.0, -0.5] * 10)
        assert isinstance(result, McSimResult)
        for field in (
            "n_simulations", "median_final_equity", "p5_final_equity",
            "p95_final_equity", "median_max_drawdown", "p95_max_drawdown",
            "prob_ruin", "prob_dd_threshold", "median_time_to_recovery",
        ):
            assert hasattr(result, field)

    def test_n_simulations_matches_config(self):
        sim = EquityMonteCarloSimulator(McSimConfig(n_simulations=42, seed=1))
        result = sim.simulate([1.0, -0.5] * 10)
        assert result.n_simulations == 42


# ─────────────────────────────────────────────
# Percentile helper
# ─────────────────────────────────────────────

class TestPercentile:
    def test_empty_returns_zero(self):
        assert _percentile([], 0.5) == 0.0

    def test_single_value(self):
        assert _percentile([5.0], 0.0) == 5.0
        assert _percentile([5.0], 0.5) == 5.0
        assert _percentile([5.0], 1.0) == 5.0

    def test_median_of_three(self):
        assert _percentile([1.0, 2.0, 3.0], 0.5) == pytest.approx(2.0)

    def test_5th_and_95th(self):
        sorted_vals = list(range(1, 101))  # 1..100
        assert _percentile(sorted_vals, 0.05) == pytest.approx(5.95, abs=0.5)
        assert _percentile(sorted_vals, 0.95) == pytest.approx(95.05, abs=0.5)
