"""
Unit tests for champion.portfolio_risk_governor.

These tests exercise the L99_HYBRID_PORTFOLIO_GOD_MODE §6 governor:
  - default config matches operator spec
  - equity peak tracking + drawdown kill
  - position approval cap (single / total / sector)
  - daily / weekly R circuit breakers
  - rolling-window resets
  - manual kill / reset
  - status snapshot

No network, no parquet, no subprocess. Pure-Python; runs in <50ms.
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from champion.portfolio_risk_governor import (
    PortfolioRiskConfig,
    PortfolioRiskGovernor,
    PortfolioRiskState,
)


# ──────────────────────────────────────────────────────────────
# Config / construction
# ──────────────────────────────────────────────────────────────

class TestConfigDefaults:
    def test_defaults_match_l99_hybrid_section_6(self):
        cfg = PortfolioRiskConfig()
        assert cfg.max_total_exposure == 0.08
        assert cfg.max_single_position == 0.012
        assert cfg.max_sector_exposure == 0.04
        assert cfg.daily_loss_limit_r == 3.0
        assert cfg.weekly_loss_limit_r == 6.0
        assert cfg.max_drawdown_pct == 0.25
        assert cfg.regime_multiplier == 1.0

    def test_overrides(self):
        cfg = PortfolioRiskConfig(
            max_total_exposure=0.05,
            max_drawdown_pct=0.10,
        )
        assert cfg.max_total_exposure == 0.05
        assert cfg.max_drawdown_pct == 0.10
        # Untouched defaults preserved.
        assert cfg.max_single_position == 0.012


class TestConstruction:
    def test_starting_equity_initializes_state(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), starting_equity=10_000)
        assert gov.state.equity_current == 10_000
        assert gov.state.equity_peak == 10_000
        assert gov.state.open_positions == {}
        assert gov.state.sector_map == {}
        assert gov.state.realized_r_today == 0.0
        assert gov.state.realized_r_week == 0.0
        assert gov.state.kill_switch is False

    def test_zero_equity_rejected(self):
        with pytest.raises(ValueError):
            PortfolioRiskGovernor(PortfolioRiskConfig(), starting_equity=0)

    def test_negative_equity_rejected(self):
        with pytest.raises(ValueError):
            PortfolioRiskGovernor(PortfolioRiskConfig(), starting_equity=-1)


# ──────────────────────────────────────────────────────────────
# Equity / drawdown
# ──────────────────────────────────────────────────────────────

class TestEquityTracking:
    def test_update_to_higher_equity_raises_peak(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.update_equity(11_000)
        assert gov.state.equity_peak == 11_000
        assert gov.state.equity_current == 11_000

    def test_drawdown_does_not_lower_peak(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.update_equity(11_000)
        gov.update_equity(9_500)
        assert gov.state.equity_peak == 11_000
        assert gov.state.equity_current == 9_500

    def test_drawdown_below_threshold_does_not_kill(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(max_drawdown_pct=0.25), 10_000)
        # 20% DD < 25% threshold
        gov.update_equity(8_000)
        assert gov.state.kill_switch is False

    def test_drawdown_at_threshold_triggers_kill(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(max_drawdown_pct=0.25), 10_000)
        # exactly 25% DD
        gov.update_equity(7_500)
        assert gov.state.kill_switch is True

    def test_drawdown_beyond_threshold_triggers_kill(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(max_drawdown_pct=0.25), 10_000)
        gov.update_equity(7_000)
        assert gov.state.kill_switch is True


# ──────────────────────────────────────────────────────────────
# Trade-result accounting + circuit breakers
# ──────────────────────────────────────────────────────────────

class TestTradeResultAccumulation:
    def test_loss_accumulates(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.register_trade_result(-1.0)
        assert gov.state.realized_r_today == -1.0
        assert gov.state.realized_r_week == -1.0

    def test_win_accumulates(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.register_trade_result(2.5)
        assert gov.state.realized_r_today == 2.5
        assert gov.state.realized_r_week == 2.5

    def test_mixed_results(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        for r in (-1.0, 2.0, -0.5, 1.0):
            gov.register_trade_result(r)
        assert gov.state.realized_r_today == pytest.approx(1.5)
        assert gov.state.realized_r_week == pytest.approx(1.5)


class TestCircuitBreakers:
    def test_daily_loss_3R_triggers_kill(self):
        gov = PortfolioRiskGovernor(
            PortfolioRiskConfig(daily_loss_limit_r=3.0), 10_000
        )
        gov.register_trade_result(-1.0)
        gov.register_trade_result(-1.5)
        assert gov.state.kill_switch is False
        gov.register_trade_result(-0.6)  # cumulative -3.1
        assert gov.state.kill_switch is True

    def test_daily_loss_at_exactly_3R_triggers_kill(self):
        gov = PortfolioRiskGovernor(
            PortfolioRiskConfig(daily_loss_limit_r=3.0), 10_000
        )
        gov.register_trade_result(-3.0)
        assert gov.state.kill_switch is True

    def test_weekly_loss_6R_triggers_kill(self):
        # Use a high daily limit so the daily breaker doesn't fire first.
        gov = PortfolioRiskGovernor(
            PortfolioRiskConfig(daily_loss_limit_r=100.0, weekly_loss_limit_r=6.0),
            10_000,
        )
        for _ in range(6):
            gov.register_trade_result(-1.0)
        assert gov.state.kill_switch is True

    def test_winning_does_not_trigger_kill(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        for _ in range(20):
            gov.register_trade_result(2.0)
        assert gov.state.kill_switch is False


class TestRollingResets:
    def test_daily_resets_after_24h_elapsed(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.register_trade_result(-2.0)
        # Backdate the last_reset_day to >24h ago.
        gov.state.last_reset_day = datetime.utcnow() - timedelta(days=1, seconds=10)
        gov.register_trade_result(-0.5)
        # Only the new -0.5 remains in today; yesterday's -2.0 zeroed.
        assert gov.state.realized_r_today == pytest.approx(-0.5)
        # Weekly is independent and still has both.
        assert gov.state.realized_r_week == pytest.approx(-2.5)

    def test_weekly_resets_after_7d_elapsed(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.register_trade_result(-2.0)
        gov.state.last_reset_week = datetime.utcnow() - timedelta(days=7, seconds=10)
        # Also backdate daily to avoid daily reset noise.
        gov.state.last_reset_day = datetime.utcnow() - timedelta(hours=1)
        gov.register_trade_result(-0.5)
        # Weekly reset; only the new -0.5 remains.
        assert gov.state.realized_r_week == pytest.approx(-0.5)


# ──────────────────────────────────────────────────────────────
# Position approval
# ──────────────────────────────────────────────────────────────

class TestApprovePosition:
    def _gov(self):
        return PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)

    def test_position_within_all_caps_approved(self):
        gov = self._gov()
        assert gov.approve_new_position("BTC_USDT", 0.01) is True

    def test_position_exceeding_single_cap_rejected(self):
        gov = self._gov()
        # default single-cap = 0.012, request 0.02
        assert gov.approve_new_position("BTC_USDT", 0.02) is False

    def test_single_cap_at_exact_threshold_approved(self):
        gov = self._gov()
        assert gov.approve_new_position("BTC_USDT", 0.012) is True

    def test_total_exposure_cap_blocks_new_position(self):
        gov = self._gov()
        # Fill up to near total cap.
        gov.open_position("ETH_USDT", 0.012)
        gov.open_position("SOL_USDT", 0.012)
        gov.open_position("XRP_USDT", 0.012)
        gov.open_position("AVAX_USDT", 0.012)
        gov.open_position("BTC_USDT", 0.012)
        gov.open_position("ADA_USDT", 0.012)
        # 6 × 0.012 = 0.072. New 0.012 would push to 0.084 > 0.08 cap.
        assert gov.approve_new_position("DOT_USDT", 0.012) is False

    def test_total_exposure_at_exact_cap_approves(self):
        gov = self._gov()
        for sym in ("ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT", "BTC_USDT", "ADA_USDT"):
            gov.open_position(sym, 0.012)
        # 6 × 0.012 = 0.072. Adding 0.008 → 0.080 = exact cap.
        assert gov.approve_new_position("DOT_USDT", 0.008) is True

    def test_kill_switch_blocks_all_new_positions(self):
        gov = self._gov()
        gov.force_kill()
        assert gov.approve_new_position("BTC_USDT", 0.001) is False

    def test_sector_cap_blocks_correlated_position(self):
        gov = self._gov()
        gov.set_sector("BTC_USDT", "L1_majors")
        gov.set_sector("ETH_USDT", "L1_majors")
        gov.set_sector("SOL_USDT", "L1_majors")
        gov.open_position("BTC_USDT", 0.012)
        gov.open_position("ETH_USDT", 0.012)
        gov.open_position("SOL_USDT", 0.012)
        # 3 × 0.012 = 0.036 in sector. Adding another 0.012 → 0.048 > 0.04 cap.
        gov.set_sector("AVAX_USDT", "L1_majors")
        assert gov.approve_new_position("AVAX_USDT", 0.012) is False

    def test_sector_cap_allows_uncorrelated_position(self):
        gov = self._gov()
        gov.set_sector("BTC_USDT", "L1_majors")
        gov.set_sector("ETH_USDT", "L1_majors")
        gov.set_sector("SOL_USDT", "L1_majors")
        gov.open_position("BTC_USDT", 0.012)
        gov.open_position("ETH_USDT", 0.012)
        gov.open_position("SOL_USDT", 0.012)
        # XRP in different sector, sector exposure for "alts_payments" = 0.
        gov.set_sector("XRP_USDT", "alts_payments")
        assert gov.approve_new_position("XRP_USDT", 0.012) is True

    def test_no_sector_set_skips_sector_check(self):
        gov = self._gov()
        gov.open_position("BTC_USDT", 0.012)
        gov.open_position("ETH_USDT", 0.012)
        # No sector set on the new symbol → no sector check.
        assert gov.approve_new_position("DOGE_USDT", 0.012) is True

    def test_regime_multiplier_amplifies_size(self):
        # Risk = 0.008 × multiplier 2.0 = 0.016, which exceeds single-cap 0.012.
        gov = PortfolioRiskGovernor(
            PortfolioRiskConfig(regime_multiplier=2.0), 10_000
        )
        assert gov.approve_new_position("BTC_USDT", 0.008) is False

    def test_regime_multiplier_dampens_size(self):
        # Multiplier 0.5 lets a normally-too-big request fit.
        gov = PortfolioRiskGovernor(
            PortfolioRiskConfig(regime_multiplier=0.5), 10_000
        )
        assert gov.approve_new_position("BTC_USDT", 0.020) is True  # 0.020 × 0.5 = 0.010 ≤ 0.012


# ──────────────────────────────────────────────────────────────
# Position lifecycle
# ──────────────────────────────────────────────────────────────

class TestPositionLifecycle:
    def test_open_records_position(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.open_position("BTC_USDT", 0.012)
        assert gov.state.open_positions == {"BTC_USDT": 0.012}

    def test_close_removes_position(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.open_position("BTC_USDT", 0.012)
        gov.close_position("BTC_USDT")
        assert gov.state.open_positions == {}

    def test_close_unknown_symbol_is_noop(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.close_position("NEVER_OPENED")  # must not raise
        assert gov.state.open_positions == {}

    def test_set_sector_records_mapping(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.set_sector("BTC_USDT", "L1_majors")
        assert gov.state.sector_map["BTC_USDT"] == "L1_majors"


# ──────────────────────────────────────────────────────────────
# Manual kill controls
# ──────────────────────────────────────────────────────────────

class TestManualKillControls:
    def test_force_kill_sets_flag(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.force_kill()
        assert gov.state.kill_switch is True

    def test_reset_kill_clears_flag(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.force_kill()
        gov.reset_kill()
        assert gov.state.kill_switch is False

    def test_reset_kill_re_enables_position_approval(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.force_kill()
        assert gov.approve_new_position("BTC_USDT", 0.001) is False
        gov.reset_kill()
        assert gov.approve_new_position("BTC_USDT", 0.001) is True


# ──────────────────────────────────────────────────────────────
# Status snapshot
# ──────────────────────────────────────────────────────────────

class TestStatus:
    def test_status_contains_all_keys(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        s = gov.status()
        for key in (
            "equity_current",
            "equity_peak",
            "drawdown_pct",
            "open_positions",
            "total_exposure",
            "realized_r_today",
            "realized_r_week",
            "kill_switch",
        ):
            assert key in s, f"missing key: {key}"

    def test_status_drawdown_zero_at_start(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        assert gov.status()["drawdown_pct"] == 0.0

    def test_status_drawdown_after_loss(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.update_equity(8_500)  # 15% DD
        assert gov.status()["drawdown_pct"] == pytest.approx(0.15)

    def test_status_total_exposure_sum(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.open_position("BTC_USDT", 0.01)
        gov.open_position("ETH_USDT", 0.012)
        assert gov.status()["total_exposure"] == pytest.approx(0.022)

    def test_status_open_positions_returns_copy(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)
        gov.open_position("BTC_USDT", 0.01)
        s = gov.status()
        s["open_positions"]["MUTATED"] = 99.0
        # The internal state must NOT be mutated by external snapshot edits.
        assert "MUTATED" not in gov.state.open_positions


# ──────────────────────────────────────────────────────────────
# Integration scenario
# ──────────────────────────────────────────────────────────────

class TestIntegrationScenario:
    """Walk a multi-step sequence to verify the governor as a whole."""

    def test_normal_day_through_drawdown_kill(self):
        gov = PortfolioRiskGovernor(PortfolioRiskConfig(), 10_000)

        # 1. Approve + open a normal position.
        assert gov.approve_new_position("BTC_USDT", 0.01) is True
        gov.open_position("BTC_USDT", 0.01)

        # 2. Equity climbs to 10_500; peak updates.
        gov.update_equity(10_500)
        assert gov.state.equity_peak == 10_500

        # 3. Trade closes at -0.5R; equity drops to 9_950.
        gov.register_trade_result(-0.5)
        gov.update_equity(9_950)
        gov.close_position("BTC_USDT")

        # No kill triggered yet (DD 5.2% < 25%, R-budget healthy).
        assert gov.state.kill_switch is False

        # 4. Catastrophic equity drop → 25% DD from 10_500 peak = 7_875.
        gov.update_equity(7_500)
        assert gov.state.kill_switch is True

        # 5. Any new position request blocked.
        assert gov.approve_new_position("ETH_USDT", 0.001) is False

    def test_daily_breaker_does_not_trigger_weekly(self):
        gov = PortfolioRiskGovernor(
            PortfolioRiskConfig(daily_loss_limit_r=3.0, weekly_loss_limit_r=6.0),
            10_000,
        )
        gov.register_trade_result(-3.0)  # daily kill
        assert gov.state.kill_switch is True
        # Weekly accumulator at -3.0, well above -6.0.
        assert gov.state.realized_r_week == -3.0
