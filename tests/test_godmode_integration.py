"""
Integration smoke: confirm that when the godmode arbiter votes ENTER,
the champion PositionSizer is the authority deciding actual position
size — and that risk laws / stage envelope are respected.

We don't replay real ticks here; we directly drive the arbiter with
synthetic StreamOutputs and the sizer with manual equity updates.
"""
from __future__ import annotations

import time

import pytest

from godmode.arbiter   import ConfluenceArbiter
from godmode.streams   import StreamOutput
from godmode.runtime   import compute_stop_price, STOP_DIST_MIN_FRAC
from champion          import (CapitalStageTracker, PositionSizer,
                                RiskLaws, TradeOutcome)


def _outputs_for_strong_long(net_edge: float = 0.0020) -> dict:
    """Build StreamOutputs that pass arbiter (multiplicative score ≥78).
    Score is product of magnitudes/100; with 7 factors we need ~0.97
    each (0.97^7 ≈ 0.81 × 100 ≈ 81)."""
    return {
        "microstructure": StreamOutput(
            "microstructure", directional=+97.0, magnitude=97.0,
            confidence=0.9, data={"dir": 2.5, "std_z": 2.1}),
        "volatility": StreamOutput(
            "volatility", magnitude=97.0, confidence=0.9,
            data={"expansion": 1.4}),
        "absorption": StreamOutput(
            "absorption", magnitude=97.0, confidence=0.9),
        "structural": StreamOutput(
            "structural", magnitude=97.0, confidence=0.9),
        "fee_edge": StreamOutput(
            "fee_edge", magnitude=97.0, confidence=0.9,
            data={"net_edge": net_edge, "expected_move": 0.0030}),
        "execution": StreamOutput(
            "execution", magnitude=97.0, confidence=0.9),
        "risk": StreamOutput(
            "risk", magnitude=100.0, confidence=1.0,
            data={"state": "NORMAL"}),
    }


class TestArbiterPlusSizer:
    def test_enter_routes_through_sizer(self):
        """End-to-end: arbiter says BUY, sizer returns a real position size."""
        arbiter = ConfluenceArbiter()
        decision = arbiter.vote(_outputs_for_strong_long())
        assert decision.action == "BUY"
        assert decision.final_score >= arbiter.ENTER_SCORE

        # Now size it. Stage 1, $3k, no risk-throttles.
        tr = CapitalStageTracker(starting_equity=3_000)
        rl = RiskLaws()
        rl.update_equity(3_000, time.time_ns())
        sz = PositionSizer(tr, rl)

        entry = 67_400.0
        stop  = compute_stop_price("BUY", entry, atr_1m=80.0, mid=entry)
        rec   = sz.compute_size(entry, stop, t_ns=time.time_ns(),
                                vol_percentile=0.5,
                                god_tier=decision.aggressive)
        assert rec.blocked is False
        assert rec.risk_pct  == pytest.approx(0.015, abs=1e-6)
        assert rec.risk_amount == pytest.approx(45.0, abs=0.01)
        # Stop distance: 0.7 × 80 = 56, clamped above 0.05% × 67400 = 33.7 → 56 wins
        assert rec.stop_distance_pct == pytest.approx(56.0 / 67_400, rel=1e-3)

    def test_below_score_holds(self):
        outputs = _outputs_for_strong_long()
        # Cripple the volatility magnitude → score should fall under 78
        outputs["volatility"] = StreamOutput(
            "volatility", magnitude=10.0, confidence=0.7,
            data={"expansion": 1.05})
        decision = ConfluenceArbiter().vote(outputs)
        assert decision.action == "HOLD"

    def test_aggressive_god_tier_caps_at_max_risk(self):
        """Score ≥88 + edge ≥0.25% → arbiter sets aggressive=True →
        sizer uses god_tier 2× capped at max_risk (Stage 1 = 2.0%).
        Multiplicative score with 7 factors: need geometric-mean ≥0.983
        → all at 99 gives 0.99^7 ≈ 0.93 → score 93."""
        outputs = _outputs_for_strong_long(net_edge=0.0030)
        for k in ("microstructure", "volatility", "absorption", "structural",
                  "execution"):
            base = outputs[k]
            outputs[k] = StreamOutput(
                k, directional=+99.0 if k == "microstructure" else 0.0,
                magnitude=99.0, confidence=1.0, data=base.data)
        outputs["fee_edge"] = StreamOutput(
            "fee_edge", magnitude=100.0, confidence=1.0,
            data={"net_edge": 0.0030})
        outputs["risk"] = StreamOutput(
            "risk", magnitude=100.0, confidence=1.0,
            data={"state": "NORMAL"})
        decision = ConfluenceArbiter().vote(outputs)
        assert decision.action == "BUY"
        assert decision.aggressive is True

        tr = CapitalStageTracker(starting_equity=3_000)
        rl = RiskLaws(); rl.update_equity(3_000, time.time_ns())
        sz = PositionSizer(tr, rl)
        rec = sz.compute_size(67_400.0, 67_350.0, t_ns=time.time_ns(),
                              god_tier=decision.aggressive)
        # 0.015 × 2 = 0.030 → clipped to max 0.020
        assert rec.risk_pct == pytest.approx(0.020, abs=1e-6)
        assert rec.god_tier is True

    def test_loss_throttle_blocks_after_3_losses(self):
        """Even a clean ENTER decision must be blocked when the sizer
        has been throttled by 3 consecutive losses."""
        tr = CapitalStageTracker(starting_equity=3_000)
        rl = RiskLaws(); rl.update_equity(3_000, time.time_ns())
        sz = PositionSizer(tr, rl)
        now = time.time_ns()
        for _ in range(3):
            sz.record_trade(TradeOutcome(-0.01, -1.0, now))
        # 1 minute later — pause still active
        rec = sz.compute_size(67_400.0, 67_350.0,
                              t_ns=now + 60 * 1_000_000_000,
                              god_tier=True)
        assert rec.blocked
        assert "Loss-streak pause" in rec.block_reason

    def test_compute_stop_floors_to_min_frac(self):
        """Stop must always be ≥ 0.05% of price even with tiny ATR."""
        entry = 67_400.0
        stop = compute_stop_price("BUY", entry, atr_1m=0.0, mid=entry)
        dist = abs(entry - stop)
        assert dist == pytest.approx(entry * STOP_DIST_MIN_FRAC, rel=1e-6)
        # SELL side
        stop_s = compute_stop_price("SELL", entry, atr_1m=0.0, mid=entry)
        dist_s = abs(stop_s - entry)
        assert dist_s == pytest.approx(entry * STOP_DIST_MIN_FRAC, rel=1e-6)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
