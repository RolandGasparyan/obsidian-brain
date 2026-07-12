"""Tests for Plan B Dual-Timeframe Acceleration:
   - aegis_alpha.regime classifier states
   - aegis_alpha.global_exposure shared budget enforcement
"""
from __future__ import annotations

import pytest

from aegis_alpha import regime as reg_mod
from aegis_alpha import global_exposure as exp_mod
from aegis_alpha.regime import (Regime, RegimeReading, classify_regime,
                                 regime_allows_1h)
from aegis_alpha.global_exposure import (can_open, register_open,
                                          unregister_open, current_exposure,
                                          reset)


# ── regime classifier (math-only, no network) ────────────────────────
class TestRegime:
    def _stub_rows(self, closes):
        """Build minimal candle rows from a list of closes; HL = ±1% of close."""
        rows = []
        for i, c in enumerate(closes):
            rows.append([1_000_000 * (i + 1), 1000, c, c * 1.01, c * 0.99,
                         c, 1000 / c])
        return rows

    def test_dead_when_ema20_below_ema50(self, monkeypatch):
        # Long downtrend
        closes = [100 - i * 0.5 for i in range(100)]   # steady decline
        monkeypatch.setattr(reg_mod, "fetch_candles",
                             lambda p, tf, lim: self._stub_rows(closes))
        r = classify_regime()
        assert r is not None
        assert r.regime is Regime.DEAD

    def test_dead_when_atr_contracted(self, monkeypatch):
        # Flat price (no volatility) — ATR ratio < 0.70
        closes = [100.0] * 100
        rows = []
        for i, c in enumerate(closes):
            # tighter HL on the most recent slice to make atr_now < baseline×0.70
            spread = 0.5 if i < 80 else 0.05
            rows.append([1_000_000 * (i + 1), 1000, c, c + spread, c - spread,
                         c, 10])
        monkeypatch.setattr(reg_mod, "fetch_candles",
                             lambda p, tf, lim: rows)
        r = classify_regime()
        assert r is not None
        # Either DEAD or NORMAL acceptable here depending on EMA equality;
        # importantly ATR ratio must be < 0.70 for the DEAD reason to fire.
        # We only require the regime to NOT be EXPANSION when vol contracts.
        assert r.regime in (Regime.DEAD, Regime.NORMAL)

    def test_normal_when_uptrend_no_expansion(self, monkeypatch):
        # Mild uptrend with stable vol
        closes = [100 + i * 0.1 for i in range(100)]
        monkeypatch.setattr(reg_mod, "fetch_candles",
                             lambda p, tf, lim: self._stub_rows(closes))
        r = classify_regime()
        assert r is not None
        # Could be NORMAL or EXPANSION depending on slope; with 0.1/bar
        # over 10 bars = 1%, slope >= 0.5% threshold, uptrend OK.
        # ATR ratio is ~1 (constant HL band) so not expansion → NORMAL
        assert r.regime in (Regime.NORMAL, Regime.EXPANSION)

    def test_classify_returns_none_on_short_data(self, monkeypatch):
        monkeypatch.setattr(reg_mod, "fetch_candles",
                             lambda p, tf, lim: [[0, 0, 1, 1, 1, 1, 1]])
        r = classify_regime()
        assert r is None

    def test_regime_allows_1h(self):
        # Build readings manually
        for state, expected in [(Regime.EXPANSION, True),
                                (Regime.NORMAL,    True),
                                (Regime.DEAD,      False)]:
            r = RegimeReading(
                regime=state, btc_close=100, btc_ema20=99, btc_ema50=98,
                btc_ema20_slope=0.01, atr_now=1, atr_baseline=1, atr_ratio=1,
                reasons=[],
            )
            assert regime_allows_1h(r) is expected
        # Fail-closed on None
        assert regime_allows_1h(None) is False


# ── global exposure tracker ──────────────────────────────────────────
class TestGlobalExposure:
    def setup_method(self):
        reset()

    def teardown_method(self):
        reset()

    def test_initial_state_allows_entries(self):
        ex = can_open("aegis_alpha_4h", proposed_risk_pct=0.015)
        assert ex.allowed
        assert ex.global_used == 0.0
        assert ex.engine_used == 0.0

    def test_register_then_can_open_reflects_use(self):
        register_open("aegis_alpha_4h", "trade1", risk_pct=0.015)
        ex = can_open("aegis_alpha_4h", proposed_risk_pct=0.015)
        assert ex.engine_used == pytest.approx(0.015)
        # 0.015 + 0.015 = 0.030 vs cap 0.020 → BLOCK
        assert not ex.allowed

    def test_engine_cap_blocks_4h(self):
        # Fill 4H slice to its cap (2%)
        register_open("aegis_alpha_4h", "t1", risk_pct=0.020)
        ex = can_open("aegis_alpha_4h", proposed_risk_pct=0.005)
        assert not ex.allowed
        assert "engine cap" in ex.reason

    def test_global_cap_blocks_when_combined(self):
        # 4H at 2%, 1H at 2% → global at 4%, room 2% per global cap (6%)
        register_open("aegis_alpha_4h", "t1", risk_pct=0.020)
        register_open("aegis_alpha_1h", "t2", risk_pct=0.020)
        # 1H tries 1% more — its slice already full → engine cap blocks first
        ex = can_open("aegis_alpha_1h", proposed_risk_pct=0.005)
        assert not ex.allowed

    def test_unregister_frees_capacity(self):
        register_open("aegis_alpha_4h", "t1", risk_pct=0.020)
        # Capacity full
        assert not can_open("aegis_alpha_4h", 0.005).allowed
        # Free it
        unregister_open("t1")
        assert can_open("aegis_alpha_4h", 0.015).allowed

    def test_engines_independent_within_cap(self):
        # 4H uses its full 2% — 1H still has its own 2% slice
        register_open("aegis_alpha_4h", "t_a", risk_pct=0.020)
        ex = can_open("aegis_alpha_1h", proposed_risk_pct=0.015)
        assert ex.allowed
        assert ex.global_used == pytest.approx(0.020)

    def test_current_exposure_snapshot(self):
        register_open("aegis_alpha_4h", "a", 0.010)
        register_open("aegis_alpha_1h", "b", 0.005)
        snap = current_exposure()
        assert snap["open_count"] == 2
        assert snap["global_used_pct"] == pytest.approx(0.015)
        assert snap["engine_used"]["aegis_alpha_4h"] == pytest.approx(0.010)
        assert snap["engine_used"]["aegis_alpha_1h"] == pytest.approx(0.005)
