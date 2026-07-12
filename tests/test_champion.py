"""
Unit tests for the Champion Mode position sizer + stage tracker + risk laws.

Covers the math from CHAMPION_MODE.md §1.3, §4.1, §V. Every test maps
to a specific doctrine clause; if a test fails, the doctrine is being
violated.
"""
from __future__ import annotations

import time

import pytest

from champion import (
    CapitalStageTracker, Stage,
    PositionSizer, SizeRecommendation, TradeOutcome,
    RiskLaws, RiskState,
)


# ── stage tracker ───────────────────────────────────────────────────
class TestStageTracker:
    def test_initial_stage_is_1_at_3k(self):
        t = CapitalStageTracker(starting_equity=3_000)
        assert t.stage is Stage.STAGE_1
        assert t.base_risk_pct == 0.015
        assert t.max_risk_pct  == 0.020
        assert t.min_risk_pct  == 0.005

    def test_stage_boundaries_match_doctrine(self):
        """§1.3 — stages: $3k–$20k, $20k–$150k, $150k–$500k, $500k+."""
        # Just below each boundary
        for eq, expected in [(19_999, Stage.STAGE_1),
                             (149_999, Stage.STAGE_2),
                             (499_999, Stage.STAGE_3),
                             (1_000_000, Stage.STAGE_4)]:
            t = CapitalStageTracker(starting_equity=eq)
            assert t.stage is expected, f"{eq} → expected {expected}"

    def test_promotion_requires_buffer(self):
        """Doctrine: promotion only with 1% buffer beyond ceiling
        (no thrash on boundary chops)."""
        t = CapitalStageTracker(starting_equity=19_500)
        assert t.stage is Stage.STAGE_1
        # Cross to 20_001 — natural stage is 2 but no 1% buffer past 20k
        t.update_equity(20_001)
        assert t.stage is Stage.STAGE_1, "Promotion without buffer should not occur"
        # Comfortably past
        t.update_equity(20_300)  # > 20_000 * 1.01
        assert t.stage is Stage.STAGE_2

    def test_regression_is_immediate(self):
        """Doctrine §V Layer 4 — regression is immediate, no buffer."""
        t = CapitalStageTracker(starting_equity=25_000)
        assert t.stage is Stage.STAGE_2
        # Drop to 19_500
        t.update_equity(19_500)
        assert t.stage is Stage.STAGE_1
        # Risk envelope must immediately reflect Stage 1
        assert t.base_risk_pct == 0.015
        assert t.max_risk_pct  == 0.020

    def test_risk_envelope_per_stage(self):
        """§4.1 — base / max / min risk per stage."""
        cases = [
            (15_000, Stage.STAGE_1, 0.015, 0.020, 0.005),
            (50_000, Stage.STAGE_2, 0.010, 0.015, 0.004),
            (200_000, Stage.STAGE_3, 0.0075, 0.010, 0.003),
            (700_000, Stage.STAGE_4, 0.005, 0.0075, 0.0025),
        ]
        for eq, stg, base, mx, mn in cases:
            t = CapitalStageTracker(starting_equity=eq)
            assert t.stage is stg
            assert t.base_risk_pct == base
            assert t.max_risk_pct  == mx
            assert t.min_risk_pct  == mn

    def test_doublings_to_target(self):
        """8.4 doublings = $1M from $3k (per §1.1)."""
        t = CapitalStageTracker(starting_equity=3_000)
        t.update_equity(1_000_000)
        # log2(1_000_000/3_000) ≈ 8.38
        assert 8.3 <= t.doublings_achieved() <= 8.5


# ── risk laws ───────────────────────────────────────────────────────
class TestRiskLaws:
    def _t(self, day_offset_h: float = 0) -> int:
        """Deterministic UTC time anchor for tests: 2026-01-01T00:00:00Z."""
        return 1_767_225_600 * 1_000_000_000 + int(day_offset_h * 3600 * 1e9)

    def test_no_pause_initially(self):
        r = RiskLaws()
        r.update_equity(3_000, self._t(0))
        d = r.decision(self._t(0))
        assert d["allowed"] is True
        assert d["size_scaler"] == 1.0
        assert d["state"] is RiskState.NORMAL

    def test_daily_dd_5pct_halts_today(self):
        """§V Layer 2 — 5% daily DD → no more trades today."""
        r = RiskLaws()
        r.update_equity(10_000, self._t(0))
        # Drop to -5% intraday
        r.update_equity(9_500, self._t(2))
        d = r.decision(self._t(2))
        assert not d["allowed"]
        assert d["state"] is RiskState.PAUSED_DAILY

    def test_peak_dd_15pct_minimum_size(self):
        """§V Layer 3 — −15% from peak → minimum size only.
        Sequence walks four UTC days so daily-DD halt clears before we
        check the peak-DD scaler (the two halts overlap if checked the
        same day)."""
        r = RiskLaws()
        # Day 0: open at 10k, holds at 10.5k peak
        r.update_equity(10_000, self._t(0))
        r.update_equity(10_500, self._t(2))
        # Day 1: small flat day — keeps peak, no DD trigger
        r.update_equity(10_400, self._t(25))
        # Day 2: small flat continues
        r.update_equity(10_400, self._t(49))
        # Day 3: large drop ⇒ peak_dd ≈ 16% (well above 15% threshold).
        # Daily DD ≈ 15% intraday triggers PAUSED_DAILY for THAT day.
        r.update_equity(8_800, self._t(73))
        # Day 4: small recovery — daily halt expired, peak DD still 16.2%
        # → MIN_SIZE_DD15 should engage.
        r.update_equity(8_810, self._t(97))
        d = r.decision(self._t(97))
        assert d["allowed"] is True
        assert d["state"] is RiskState.MIN_SIZE_DD15
        assert d["size_scaler"] == 0.5

    def test_systemic_btc_drop_halts_all(self):
        """§V Layer 5 — BTC drops > 20% in 7d → halt."""
        r = RiskLaws()
        r.update_equity(10_000, self._t(0))
        r.update_btc_price(70_000, self._t(0))
        r.update_btc_price(50_000, self._t(50))   # -28.6% over 2d
        d = r.decision(self._t(50))
        assert not d["allowed"]
        assert d["state"] is RiskState.HALTED_SYSTEMIC


# ── position sizer ──────────────────────────────────────────────────
class TestPositionSizer:
    def _setup(self, equity=3_000):
        tr = CapitalStageTracker(starting_equity=equity)
        rl = RiskLaws()
        rl.update_equity(equity, time.time_ns())
        return PositionSizer(tr, rl), tr, rl

    def test_basic_size_at_stage_1(self):
        """3000 × 1.5% = $45 risk. Stop 1% away → 0.001 × 67400 → ~0.667 units."""
        s, tr, rl = self._setup(3_000)
        rec = s.compute_size(entry_price=67_400.0, stop_price=66_726.0,
                             t_ns=time.time_ns(),
                             vol_percentile=0.5)
        assert rec.blocked is False
        assert rec.risk_pct == pytest.approx(0.015, abs=1e-6)
        assert rec.risk_amount == pytest.approx(45.0, abs=0.01)
        # Stop distance = 1% of 67400 = 674
        # position_units = 45 / 674 ≈ 0.0667
        assert rec.position_units == pytest.approx(45.0 / 674.0, rel=1e-3)

    def test_invalid_input_blocks(self):
        s, _, _ = self._setup()
        for entry, stop in [(0, 100), (100, 0), (100, 100), (-1, 50)]:
            rec = s.compute_size(entry, stop, t_ns=time.time_ns())
            assert rec.blocked, f"({entry},{stop}) should be blocked"

    def test_3w_streak_scaler(self):
        """§4.1 — 3 consecutive wins → next trade at risk × 1.25."""
        s, _, _ = self._setup(3_000)
        for _ in range(3):
            s.record_trade(TradeOutcome(pnl_pct=0.01, pnl_R=2.0,
                                         t_ns=time.time_ns()))
        rec = s.compute_size(67_400.0, 66_726.0,
                             t_ns=time.time_ns(), vol_percentile=0.5)
        # base 0.015 × 1.25 = 0.01875 (under max 0.020 → no clip)
        assert rec.risk_pct == pytest.approx(0.018_75, abs=1e-5)

    def test_5w_streak_scaler(self):
        """§4.1 — 5 consecutive wins → next trade at risk × 1.5, capped at max."""
        s, _, _ = self._setup(3_000)
        for _ in range(5):
            s.record_trade(TradeOutcome(pnl_pct=0.01, pnl_R=2.0,
                                         t_ns=time.time_ns()))
        rec = s.compute_size(67_400.0, 66_726.0,
                             t_ns=time.time_ns(), vol_percentile=0.5)
        # base 0.015 × 1.5 = 0.0225, must clip to max 0.020
        assert rec.risk_pct == pytest.approx(0.020, abs=1e-6)

    def test_2_loss_throttle(self):
        """§4.1 — 2 consec losses → next 5 trades at MIN risk."""
        s, _, _ = self._setup(3_000)
        s.record_trade(TradeOutcome(-0.01, -1.0, time.time_ns()))
        s.record_trade(TradeOutcome(-0.01, -1.0, time.time_ns()))
        rec = s.compute_size(67_400.0, 66_726.0,
                             t_ns=time.time_ns(), vol_percentile=0.5)
        assert rec.risk_pct == pytest.approx(0.005, abs=1e-6)  # min Stage 1

    def test_3_loss_pause_blocks(self):
        """§4.1 — 3 consec losses → 30-min pause."""
        s, _, _ = self._setup(3_000)
        now = time.time_ns()
        for _ in range(3):
            s.record_trade(TradeOutcome(-0.01, -1.0, now))
        rec = s.compute_size(67_400.0, 66_726.0,
                             t_ns=now + 60 * 1_000_000_000)  # 1 min later
        assert rec.blocked
        assert "Loss-streak pause" in rec.block_reason
        # 31 minutes later: pause cleared
        rec2 = s.compute_size(67_400.0, 66_726.0,
                              t_ns=now + 31 * 60 * 1_000_000_000)
        assert rec2.blocked is False or "pause" not in rec2.block_reason.lower()

    def test_5_loss_daily_halt(self):
        """§4.1 — 5 consec losses → STOP for the day.
        Use deterministic UTC-start-of-day anchor so the +4h check stays
        inside the same UTC day (otherwise the halt naturally expires)."""
        s, _, _ = self._setup(3_000)
        # 2026-01-15T00:00:00Z, deterministic
        anchor = 1_768_521_600 * 1_000_000_000
        for _ in range(5):
            s.record_trade(TradeOutcome(-0.01, -1.0, anchor))
        # Same UTC day, +4h
        rec = s.compute_size(67_400.0, 66_726.0,
                             t_ns=anchor + 4 * 3600 * 1_000_000_000)
        assert rec.blocked
        assert ("daily" in rec.block_reason.lower() or
                "halt" in rec.block_reason.lower() or
                "loss" in rec.block_reason.lower())

    def test_god_tier_doubles_size_capped(self):
        """§3.1 — god-tier scanner score → 2× size, clipped to max."""
        s, _, _ = self._setup(3_000)
        rec = s.compute_size(67_400.0, 66_726.0,
                             t_ns=time.time_ns(), vol_percentile=0.5,
                             god_tier=True)
        # 0.015 × 2 = 0.030 → clipped to max 0.020
        assert rec.risk_pct == pytest.approx(0.020, abs=1e-6)
        assert rec.god_tier is True

    def test_high_vol_scales_down(self):
        """§4.1 — high vol → ×0.7 size."""
        s, _, _ = self._setup(3_000)
        rec = s.compute_size(67_400.0, 66_726.0,
                             t_ns=time.time_ns(), vol_percentile=0.85)
        # 0.015 × 0.7 = 0.0105 (under max)
        assert rec.risk_pct == pytest.approx(0.0105, abs=1e-5)

    def test_low_vol_scales_down(self):
        """§4.1 — low vol → ×0.8 size."""
        s, _, _ = self._setup(3_000)
        rec = s.compute_size(67_400.0, 66_726.0,
                             t_ns=time.time_ns(), vol_percentile=0.10)
        # 0.015 × 0.8 = 0.012
        assert rec.risk_pct == pytest.approx(0.012, abs=1e-5)

    def test_size_grows_with_equity(self):
        """Compounding mechanism — size must scale with current equity."""
        s, tr, rl = self._setup(3_000)
        rec1 = s.compute_size(67_400.0, 66_726.0, t_ns=time.time_ns(),
                              vol_percentile=0.5)
        # Equity doubles → still Stage 1 (under $20k boundary)
        s.update_equity(6_000, time.time_ns())
        rec2 = s.compute_size(67_400.0, 66_726.0, t_ns=time.time_ns(),
                              vol_percentile=0.5)
        # Same risk_pct, but units double
        assert rec2.position_units == pytest.approx(rec1.position_units * 2, rel=1e-2)


if __name__ == "__main__":
    import sys
    raise SystemExit(pytest.main([__file__, "-v"]))
