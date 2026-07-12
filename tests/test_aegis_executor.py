"""
Tests for aegis_alpha entry/exit logic per CHAMPION_MODE.md §3.2-3.3.

Covers:
    - check_entry: each gate independently (score/close/vol/resistance/
                    spread/BTC/chase)
    - compute_stop: 0.2× ATR buffer, 2% hard cap
    - AlphaTrade TP ladder (standard & god-tier), trailing stop
                    activation, hard stop, time exits, BTC kill,
                    breakout reclaim, volume collapse
    - AlphaExecutor: refuses double-open, routes through sizer,
                    reports R correctly to sizer.record_trade
"""
from __future__ import annotations

import math
import time
from pathlib import Path

import pytest

from aegis_alpha.scanner  import TokenScore, FactorScore
from aegis_alpha.executor import (check_entry, compute_stop,
                                   AlphaExecutor, EntryConfirmation,
                                   STOP_ATR_BUFFER, HARD_MAX_STOP_PCT)
from aegis_alpha.trade    import (AlphaTrade, CloseReason, TPLevel,
                                   STANDARD_TP_LADDER, GOD_TIER_TP_LADDER,
                                   NS_PER_HOUR)
from champion             import (CapitalStageTracker, PositionSizer,
                                   RiskLaws)


# ── helpers ──────────────────────────────────────────────────────────
def _mk_token_score(total=80.0, god=False, spread=0.05) -> TokenScore:
    return TokenScore(
        pair="ETH_USDT", total=total,
        factors=[FactorScore("liquidity", 25, 25, {})],
        qualified=total >= 72, god_tier=god, disqualify_reason="",
        snapshot_data={"last": 3000.0, "spread_pct": spread,
                        "vol_24h_usd": 1e8, "ret_24h_pct": 8.0},
    )


def _mk_candles(n: int, last_close: float, last_volume: float,
                avg_volume: float = 1.0,
                breakout_high: float = None) -> list:
    """Build n 4H candle rows. Last close = last_close, last vol = last_volume.
    Prior 20 closes form the breakout wall at breakout_high (default
    last_close − 1%)."""
    if breakout_high is None:
        breakout_high = last_close * 0.99
    rows = []
    for i in range(n - 1):
        c = breakout_high * (0.99 + (i % 5) * 0.001)
        rows.append([1_000_000_000 * (i + 1),     # ts
                      avg_volume,                   # quote_vol
                      c,                            # close
                      c * 1.002, c * 0.998, c,      # high low open
                      avg_volume / c])              # base_vol
    rows.append([1_000_000_000 * n,
                 last_volume, last_close,
                 last_close * 1.002, last_close * 0.998, last_close,
                 last_volume / last_close])
    return rows


def _now(): return time.time_ns()


# ── check_entry ──────────────────────────────────────────────────────
class TestCheckEntry:
    def test_all_pass(self):
        score = _mk_token_score(total=80.0, spread=0.05)
        candles = _mk_candles(30, last_close=3030.0, last_volume=2000.0,
                               avg_volume=1000.0,
                               breakout_high=3010.0)
        c = check_entry(score, candles,
                        btc_ema20=70_000, btc_ema50=68_000)
        assert c.passes, f"expected pass, fail reasons: {c.fail_reasons}"

    def test_fails_when_score_below_72(self):
        score = _mk_token_score(total=70.0)
        candles = _mk_candles(30, 3030, 2000, 1000, 3010)
        c = check_entry(score, candles, btc_ema20=70_000, btc_ema50=68_000)
        assert not c.passes
        assert "score < 72" in c.fail_reasons

    def test_fails_when_close_at_or_below_breakout(self):
        """Build prior candles so max prior close is exactly 3050 — last
        close at 3050 means we're AT the breakout, not above. close_ok=False."""
        score = _mk_token_score(total=80)
        # Hand-craft so prior 20 closes max out at 3050 (one tall bar)
        rows = []
        for i in range(29):
            c = 3000.0 if i != 10 else 3050.0     # one tall bar = 3050 max
            rows.append([1_000_000_000 * (i + 1), 1000,
                          c, c * 1.002, c * 0.998, c, 1000 / c])
        # Last bar: closes EXACTLY at 3050 — equal to prior max → close_ok False
        rows.append([1_000_000_000 * 30, 2000, 3050.0,
                      3050.0 * 1.002, 3050.0 * 0.998, 3050.0, 2000 / 3050.0])
        c = check_entry(score, rows, btc_ema20=70_000, btc_ema50=68_000)
        assert not c.close_ok

    def test_fails_when_volume_under_150pct(self):
        score = _mk_token_score(total=80)
        candles = _mk_candles(30, 3030, last_volume=1100,  # 1.1× avg
                               avg_volume=1000.0, breakout_high=3010.0)
        c = check_entry(score, candles, btc_ema20=70_000, btc_ema50=68_000)
        assert not c.volume_ok

    def test_fails_on_wide_spread(self):
        score = _mk_token_score(total=80, spread=0.15)
        candles = _mk_candles(30, 3030, 2000, 1000, 3010)
        c = check_entry(score, candles, btc_ema20=70_000, btc_ema50=68_000)
        assert not c.spread_ok

    def test_fails_when_btc_in_downtrend(self):
        score = _mk_token_score(total=80)
        candles = _mk_candles(30, 3030, 2000, 1000, 3010)
        c = check_entry(score, candles, btc_ema20=68_000, btc_ema50=70_000)
        assert not c.btc_ok

    def test_chase_blocks_when_more_than_2pct_above(self):
        score = _mk_token_score(total=80)
        candles = _mk_candles(30, last_close=3100.0, last_volume=2000.0,
                               avg_volume=1000.0, breakout_high=3000.0)
        # +3.33% past breakout — chase
        c = check_entry(score, candles, btc_ema20=70_000, btc_ema50=68_000)
        assert not c.chase_ok


# ── compute_stop ─────────────────────────────────────────────────────
class TestComputeStop:
    def test_atr_buffer(self):
        # entry 3000, breakout_low 2980, atr_4h 50
        # raw_stop = 2980 - 0.2*50 = 2970
        # 2% floor = 2940 → max picks 2970
        s = compute_stop(entry_price=3000.0,
                         breakout_candle_low=2980.0, atr_4h=50.0)
        assert s == pytest.approx(2970.0, rel=1e-3)

    def test_2pct_hard_cap_when_atr_huge(self):
        # entry 3000, breakout_low 2500, atr 1000
        # raw_stop = 2500 - 200 = 2300
        # 2% floor = 2940 → max picks 2940 (the floor wins)
        s = compute_stop(entry_price=3000.0,
                         breakout_candle_low=2500.0, atr_4h=1000.0)
        assert s == pytest.approx(2940.0, rel=1e-3)


# ── AlphaTrade state machine ────────────────────────────────────────
class TestAlphaTrade:
    def _mk_trade(self, score=80, god=False, units=1.0):
        return AlphaTrade(
            pair="ETH_USDT", score=score, god_tier=god,
            open_t_ns=_now(),
            entry_price=3000.0, initial_stop_price=2940.0,  # R = 60
            breakout_level=2980.0, units_total=units,
            notional_usd=units * 3000.0,
            entry_volume=2_000_000.0,
            risk_amount_usd=units * 60.0,
            atr_4h_at_entry=50.0,
        )

    def test_R_value(self):
        t = self._mk_trade()
        assert t.R_value == pytest.approx(60.0)

    def test_standard_ladder_50_50(self):
        t = self._mk_trade(score=80, god=False, units=1.0)
        assert len(t.tp_levels) == 2
        assert t.tp_levels[0].R_multiple == 2.0
        assert t.tp_levels[0].fraction   == 0.50
        assert t.tp_levels[1].R_multiple == 3.0
        assert t.tp_levels[1].fraction   == 0.50

    def test_god_tier_ladder(self):
        t = self._mk_trade(score=92, god=True, units=1.0)
        assert len(t.tp_levels) == 3
        assert t.tp_levels[0].R_multiple == 2.0
        assert t.tp_levels[0].fraction   == 0.30
        assert t.tp_levels[1].R_multiple == 3.5
        assert t.tp_levels[1].fraction   == 0.40
        # final leg is +inf (trail-only)
        assert math.isinf(t.tp_levels[2].R_multiple)

    def test_hard_stop_closes_at_stop(self):
        t = self._mk_trade()
        ev = t.on_candle(candle_high=2960.0, candle_low=2930.0,
                          candle_close=2935.0, candle_volume=2_000_000,
                          atr_4h_now=50.0, t_ns=_now())
        assert t.closed
        assert t.close_reason == "HARD_STOP"
        # Loss should be ≈ 1R (the stop)
        assert t.realized_R == pytest.approx(-1.0, abs=1e-2)

    def test_2R_partial_then_3R_partial(self):
        t = self._mk_trade(score=80, god=False, units=1.0)
        # Bar 1: hits 2R (3120) and 3R (3180) intra-bar — both fire
        ev = t.on_candle(candle_high=3200.0, candle_low=2995.0,
                          candle_close=3150.0, candle_volume=2_000_000,
                          atr_4h_now=50.0, t_ns=_now())
        # Both TP partials should have fired
        assert t.tp_levels[0].hit
        assert t.tp_levels[1].hit
        # Standard ladder = 100% exited, trade should close as TP_LADDER_DONE
        assert t.units_remaining < 1e-9
        assert t.closed
        # +0.5×2R + 0.5×3R = 1.0 + 1.5 = 2.5R
        assert t.realized_R == pytest.approx(2.5, abs=1e-2)

    def test_trailing_stop_after_3R_for_god_tier(self):
        t = self._mk_trade(score=92, god=True, units=1.0)
        # Hit 2R partial, then 3.5R partial, then trail leg remaining
        ev = t.on_candle(candle_high=3210.0, candle_low=2995.0,   # passes 2R
                          candle_close=3200.0, candle_volume=2_000_000,
                          atr_4h_now=50.0, t_ns=_now())
        # Push price further past 3.5R
        ev = t.on_candle(candle_high=3300.0, candle_low=3150.0,
                          candle_close=3290.0, candle_volume=2_000_000,
                          atr_4h_now=50.0, t_ns=_now() + NS_PER_HOUR)
        assert t.tp_levels[0].hit
        assert t.tp_levels[1].hit
        # Trail activated since we crossed 3R
        assert t.trail.activated_trailing
        # Stop tightened above breakeven
        assert t.current_stop > t.entry_price

    def test_btc_flash_drop_kills(self):
        t = self._mk_trade()
        ev = t.on_candle(candle_high=3010, candle_low=2985,
                          candle_close=3005, candle_volume=2_000_000,
                          atr_4h_now=50.0, t_ns=_now(),
                          btc_drop_1h_pct=0.04)
        assert t.closed
        assert t.close_reason == "BTC_DROP_3PCT_1H"

    def test_breakout_reclaimed_kills(self):
        t = self._mk_trade()
        # Close back below breakout level (2980)
        ev = t.on_candle(candle_high=3010, candle_low=2950,
                          candle_close=2975, candle_volume=2_000_000,
                          atr_4h_now=50.0, t_ns=_now())
        assert t.closed
        assert t.close_reason == "BREAKOUT_RECLAIMED"

    def test_volume_collapse_kills(self):
        t = self._mk_trade()
        # candle volume at 30% of entry → triggers
        ev = t.on_candle(candle_high=3010, candle_low=2985,
                          candle_close=3005, candle_volume=600_000,
                          atr_4h_now=50.0, t_ns=_now())
        assert t.closed
        assert t.close_reason == "VOLUME_COLLAPSE"

    def test_time_exit_no_1R(self):
        t = self._mk_trade()
        future = t.open_t_ns + int(50 * NS_PER_HOUR)  # 50h
        ev = t.on_candle(candle_high=3030, candle_low=2985,
                          candle_close=3010, candle_volume=2_000_000,
                          atr_4h_now=50.0, t_ns=future)
        assert t.closed
        assert t.close_reason == "TIME_EXIT_NO_1R"

    def test_time_exit_max_72h(self):
        t = self._mk_trade()
        future = t.open_t_ns + int(75 * NS_PER_HOUR)
        ev = t.on_candle(candle_high=3060, candle_low=2985,  # hit 1R earlier
                          candle_close=3060, candle_volume=2_000_000,
                          atr_4h_now=50.0, t_ns=future)
        assert t.closed
        assert t.close_reason == "TIME_EXIT_MAX"

    def test_stop_only_tightens(self):
        t = self._mk_trade()
        # Try to widen stop → refused
        original = t.current_stop
        assert not t.tighten_stop(original - 100)
        assert t.current_stop == original
        # Tighten succeeds
        assert t.tighten_stop(original + 50)
        assert t.current_stop == original + 50


# ── AlphaExecutor ────────────────────────────────────────────────────
class TestAlphaExecutor:
    def _mk_pipeline(self, equity=3_000.0, tmp_path=None):
        tr = CapitalStageTracker(starting_equity=equity)
        rl = RiskLaws()
        rl.update_equity(equity, _now())
        sz = PositionSizer(tr, rl)
        jp = (tmp_path / "journal.jsonl") if tmp_path else None
        ex = AlphaExecutor(sz, journal_path=jp)
        return ex, sz, tr, rl

    def test_refuses_when_confirm_fails(self, tmp_path):
        ex, sz, _, _ = self._mk_pipeline(tmp_path=tmp_path)
        # Manually build a failing confirmation
        confirm = EntryConfirmation(
            pair="ETH_USDT", score=70.0, god_tier=False,
            breakout_level=2980, breakout_candle_close=3030,
            breakout_candle_volume=2_000_000, avg_volume_20p=1_000_000,
            spread_pct=0.05, btc_uptrend=True,
            distance_from_breakout_pct=1.0,
            has_resistance_within_1_5pct=False,
            score_ok=False,   # <-- fails
            close_ok=True, volume_ok=True, no_resistance_ok=True,
            spread_ok=True, btc_ok=True, chase_ok=True,
        )
        score = _mk_token_score(total=70.0)
        trade = ex.try_open(confirm, score,
                            entry_price=3030.0, atr_4h=50.0,
                            breakout_candle_low=2980.0, t_ns=_now())
        assert trade is None
        assert ex.open_count() == 0

    def test_routes_through_sizer_and_records_trade(self, tmp_path):
        ex, sz, tr, _ = self._mk_pipeline(tmp_path=tmp_path)
        score = _mk_token_score(total=80.0, god=False, spread=0.05)
        confirm = EntryConfirmation(
            pair="ETH_USDT", score=80.0, god_tier=False,
            breakout_level=2980, breakout_candle_close=3030,
            breakout_candle_volume=2_000_000, avg_volume_20p=1_000_000,
            spread_pct=0.05, btc_uptrend=True,
            distance_from_breakout_pct=1.6,
            has_resistance_within_1_5pct=False,
            score_ok=True, close_ok=True, volume_ok=True,
            no_resistance_ok=True, spread_ok=True, btc_ok=True, chase_ok=True,
        )
        trade = ex.try_open(confirm, score,
                            entry_price=3030.0, atr_4h=50.0,
                            breakout_candle_low=2980.0, t_ns=_now())
        assert trade is not None
        # Stage 1 base 1.5% on $3000 = $45 risk
        assert trade.risk_amount_usd == pytest.approx(45.0, abs=0.5)
        assert ex.open_count() == 1

    def test_double_open_blocked(self, tmp_path):
        ex, sz, _, _ = self._mk_pipeline(tmp_path=tmp_path)
        score = _mk_token_score(total=80.0)
        confirm = EntryConfirmation(
            pair="ETH_USDT", score=80.0, god_tier=False,
            breakout_level=2980, breakout_candle_close=3030,
            breakout_candle_volume=2_000_000, avg_volume_20p=1_000_000,
            spread_pct=0.05, btc_uptrend=True,
            distance_from_breakout_pct=1.6,
            has_resistance_within_1_5pct=False,
            score_ok=True, close_ok=True, volume_ok=True,
            no_resistance_ok=True, spread_ok=True, btc_ok=True, chase_ok=True,
        )
        t1 = ex.try_open(confirm, score, 3030.0, 50.0, 2980.0, _now())
        t2 = ex.try_open(confirm, score, 3030.0, 50.0, 2980.0, _now())
        assert t1 is not None
        assert t2 is None
        assert ex.open_count() == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
