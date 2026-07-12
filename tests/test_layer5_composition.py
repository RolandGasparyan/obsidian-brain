"""
Layer 5 composition integration tests.

Verifies the four Layer 5 modules compose end-to-end:

    TradeRecord
        ↓
    RollingMetricsAggregator
        ↓ (RollingMetrics)
    DriftProtectionEngine.evaluate(...)
        ↓ (drift_enabled: bool)
    MasterRegimeOrchestrator.evaluate(drift_enabled, vol_pct, trend)
        ↓ (OrchestratorDecision)
    PortfolioRiskGovernor.approve_new_position(...)
        ↓ (approve: bool)

These tests assemble the full pipeline (with the governor's regime_multiplier
hook fed by the orchestrator's exposure_multiplier) and walk synthetic trade
sequences through it.

NO live exchange wiring. NO real strategy code. Pure-Python composition.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.drift_protection import DriftProtectionConfig, DriftProtectionEngine
from champion.master_regime_orchestrator import MasterRegimeOrchestrator
from champion.portfolio_risk_governor import (
    PortfolioRiskConfig,
    PortfolioRiskGovernor,
)
from champion.rolling_metrics import (
    RollingMetricsAggregator,
    TradeRecord,
)


def build_layer5_stack(starting_equity: float = 10_000.0):
    """Construct a fresh Layer 5 stack ready to consume trades."""
    aggregator = RollingMetricsAggregator(window_size=50)
    drift = DriftProtectionEngine(DriftProtectionConfig())
    orchestrator = MasterRegimeOrchestrator()
    governor = PortfolioRiskGovernor(PortfolioRiskConfig(), starting_equity)
    return aggregator, drift, orchestrator, governor


def feed_trade(
    aggregator: RollingMetricsAggregator,
    governor: PortfolioRiskGovernor,
    trade: TradeRecord,
) -> None:
    """Helper: register a trade into both aggregator (for stats) and
    governor (for live equity tracking)."""
    aggregator.add_trade(trade)
    governor.update_equity(trade.equity)
    governor.register_trade_result(trade.r_multiple)


# ─────────────────────────────────────────────
# Composition tests
# ─────────────────────────────────────────────

class TestHealthyEdgePipeline:
    """When all metrics are healthy and regime is normal, the pipeline
    should approve a sane new position."""

    def test_healthy_metrics_approve_position(self):
        agg, drift, orch, gov = build_layer5_stack()

        # Synthesize 50 healthy trades: 60% win rate, 1.5R wins, -1R losses.
        equity = 10_000.0
        for i in range(50):
            r = 1.5 if (i % 5) < 3 else -1.0   # 30 wins, 20 losses
            equity += r * 100
            agg.add_trade(TradeRecord(
                r_multiple=r,
                equity=equity,
                prediction=float(i),
                outcome=float(i) + (0.5 if r > 0 else -0.5),  # IC ~ positive
            ))

        # Update governor equity to match.
        gov.update_equity(equity)

        metrics = agg.compute()
        drift_enabled = drift.evaluate(
            trades=metrics.trades,
            win_rate=metrics.win_rate,
            profit_factor=metrics.profit_factor,
            expectancy_r=metrics.expectancy_r,
            information_coefficient=metrics.information_coefficient,
            max_consecutive_losses=metrics.max_consecutive_losses,
            drawdown_pct=metrics.drawdown_pct,
        )
        assert drift_enabled is True

        decision = orch.evaluate(
            drift_enabled=drift_enabled,
            regime_volatility_percentile=0.50,  # normal
            regime_trend_score=0.50,            # not trending
        )
        assert decision.engine_enabled is True
        assert decision.regime_label == "NORMAL"
        assert decision.exposure_multiplier == 1.0

        # Update governor's regime multiplier per orchestrator output.
        gov.config.regime_multiplier = decision.exposure_multiplier
        approve = gov.approve_new_position("BTC_USDT", risk_fraction=0.01)
        assert approve is True


class TestDriftDisablesPipeline:
    """When drift fires, downstream multipliers and approvals should all
    cascade to a no-trade outcome."""

    def test_low_win_rate_disables_pipeline(self):
        agg, drift, orch, gov = build_layer5_stack()

        # 30 trades with 30% win rate.
        equity = 10_000.0
        for i in range(30):
            r = 1.0 if (i % 10) < 3 else -1.0  # 9 wins, 21 losses
            equity += r * 100
            agg.add_trade(TradeRecord(
                r_multiple=r, equity=equity,
                prediction=float(i), outcome=float(i),
            ))

        metrics = agg.compute()
        drift_enabled = drift.evaluate(
            trades=metrics.trades,
            win_rate=metrics.win_rate,                    # ~0.30 < 0.45 → disable
            profit_factor=metrics.profit_factor,
            expectancy_r=metrics.expectancy_r,
            information_coefficient=metrics.information_coefficient,
            max_consecutive_losses=metrics.max_consecutive_losses,
            drawdown_pct=metrics.drawdown_pct,
        )
        assert drift_enabled is False
        assert drift.state.last_disable_reason == "win_rate_below_threshold"

        decision = orch.evaluate(
            drift_enabled=drift_enabled,
            regime_volatility_percentile=0.50,
            regime_trend_score=0.50,
        )
        assert decision.engine_enabled is False
        assert decision.exposure_multiplier == 0.0
        assert decision.regime_label == "DISABLED_BY_DRIFT"

        # With multiplier 0.0, governor would size position to 0 → reject.
        gov.config.regime_multiplier = decision.exposure_multiplier
        approve = gov.approve_new_position("BTC_USDT", risk_fraction=0.01)
        # The governor's effective_fraction = 0.01 × 0.0 = 0.0; that's
        # ≤ max_single_position 0.012, ≤ total cap, ≤ sector cap. So the
        # APPROVAL gate passes (a zero-size position is technically
        # approvable). The downstream caller is responsible for not
        # placing a zero-size order — exposure_multiplier=0.0 is the
        # explicit "do not trade" signal from the orchestrator.
        assert approve is True
        # However, sizing the trade with multiplier 0 yields 0 risk:
        effective_risk = 0.01 * decision.exposure_multiplier
        assert effective_risk == 0.0


class TestHighVolDampensSizing:
    """In HIGH_VOL regime, the orchestrator's 0.5 multiplier should make
    a normally-too-big request fit within governor caps."""

    def test_high_vol_multiplier_makes_oversize_position_fit(self):
        agg, drift, orch, gov = build_layer5_stack()

        # 50 healthy trades to skip drift.
        equity = 10_000.0
        for i in range(50):
            r = 1.5 if (i % 5) < 3 else -1.0
            equity += r * 100
            agg.add_trade(TradeRecord(
                r_multiple=r, equity=equity,
                prediction=float(i), outcome=float(i) + (0.5 if r > 0 else -0.5),
            ))
        gov.update_equity(equity)

        metrics = agg.compute()
        drift_enabled = drift.evaluate(
            trades=metrics.trades, win_rate=metrics.win_rate,
            profit_factor=metrics.profit_factor, expectancy_r=metrics.expectancy_r,
            information_coefficient=metrics.information_coefficient,
            max_consecutive_losses=metrics.max_consecutive_losses,
            drawdown_pct=metrics.drawdown_pct,
        )
        assert drift_enabled is True

        decision = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.95,  # HIGH_VOL
            regime_trend_score=0.50,
        )
        assert decision.regime_label == "HIGH_VOL"
        assert decision.exposure_multiplier == 0.5

        gov.config.regime_multiplier = decision.exposure_multiplier
        # Request 0.020 (above 0.012 single cap normally), but × 0.5 → 0.010.
        approve = gov.approve_new_position("BTC_USDT", risk_fraction=0.020)
        assert approve is True


class TestKillSwitchHardOverride:
    """Once the governor's drawdown kill switch trips, no orchestrator
    multiplier and no drift approval can re-enable trading."""

    def test_drawdown_kill_overrides_everything(self):
        agg, drift, orch, gov = build_layer5_stack()

        # Force a 30% equity drop → hits 25% kill threshold.
        gov.update_equity(7_000.0)
        assert gov.state.kill_switch is True

        # Even with drift_enabled and TRENDING regime, governor still rejects.
        decision = orch.evaluate(
            drift_enabled=True,
            regime_volatility_percentile=0.50,
            regime_trend_score=0.85,
        )
        assert decision.regime_label == "TRENDING"
        assert decision.exposure_multiplier == 1.2

        gov.config.regime_multiplier = decision.exposure_multiplier
        approve = gov.approve_new_position("BTC_USDT", risk_fraction=0.001)
        assert approve is False  # kill switch rejects unconditionally
