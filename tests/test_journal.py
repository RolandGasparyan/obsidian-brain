"""Tests for champion.journal — viability-gate enforcement."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from champion.journal import (JournalRecord, TradeJournal,
                               ViabilityThresholds)


def _rec(pnl_R, t_ns=None, engine="aegis_alpha", pair="ETH_USDT"):
    return JournalRecord(
        t_close_ns=t_ns or time.time_ns(),
        engine=engine, pair=pair, direction="LONG",
        entry_price=100.0, exit_price=100.0 + pnl_R,
        units=1.0,
        pnl_usd=pnl_R, pnl_pct=pnl_R / 100, pnl_R=pnl_R,
        held_seconds=3600,
        close_reason="TEST",
    )


class TestJournal:
    def test_record_appends_to_file_and_memory(self, tmp_path):
        path = tmp_path / "journal.jsonl"
        j = TradeJournal(path)
        j.record(_rec(2.5))
        j.record(_rec(-1.0))
        j.close()
        # File has two lines
        lines = path.read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["pnl_R"] == 2.5
        assert json.loads(lines[1])["pnl_R"] == -1.0

    def test_metrics_with_zero_trades(self, tmp_path):
        j = TradeJournal(tmp_path / "journal.jsonl")
        m = j.compute_metrics(window=50)
        assert m.n_trades == 0
        assert not m.is_viable
        j.close()

    def test_viable_metrics_pass_gate(self, tmp_path):
        j = TradeJournal(tmp_path / "journal.jsonl")
        # 50 trades: 30 wins @ +2.5R, 20 losses @ -1R, INTERLEAVED so
        # max consec losses ≤ 8 threshold. Pattern: 3W, 2L, repeat (10 cycles)
        # → 30W, 20L, max_consec_loss=2.
        for _ in range(10):
            for _ in range(3): j.record(_rec(2.5))
            for _ in range(2): j.record(_rec(-1.0))
        m = j.compute_metrics(window=50)
        assert m.n_trades == 50
        assert m.win_rate == pytest.approx(0.60)
        assert m.avg_r_per_win == pytest.approx(2.5)
        assert m.avg_r_per_loss == pytest.approx(-1.0)
        # EV = (30*2.5 + 20*-1.0) / 50 = (75 - 20) / 50 = 1.1R
        assert m.ev_per_trade == pytest.approx(1.1)
        # Profit factor = 75 / 20 = 3.75
        assert m.profit_factor == pytest.approx(3.75)
        assert m.is_viable
        j.close()

    def test_low_winrate_fails_gate(self, tmp_path):
        j = TradeJournal(tmp_path / "journal.jsonl")
        # 50 trades: 20 wins @ 2.5R, 30 losses @ -1R → 40% win rate < 48%
        for _ in range(20): j.record(_rec(2.5))
        for _ in range(30): j.record(_rec(-1.0))
        m = j.compute_metrics(window=50)
        assert m.win_rate == pytest.approx(0.40)
        assert not m.is_viable
        assert any("win_rate" in r for r in m.fail_reasons)
        j.close()

    def test_engine_filter(self, tmp_path):
        j = TradeJournal(tmp_path / "journal.jsonl")
        for _ in range(10): j.record(_rec(2.0, engine="aegis_alpha"))
        for _ in range(40): j.record(_rec(-1.0, engine="godmode"))
        m_alpha = j.compute_metrics(window=50, engine="aegis_alpha")
        m_god   = j.compute_metrics(window=50, engine="godmode")
        assert m_alpha.n_trades == 10
        assert m_god.n_trades == 40
        # Only the godmode subset has 100% loss rate
        assert m_god.win_rate == 0.0
        j.close()

    def test_max_consec_losses_tracked(self, tmp_path):
        j = TradeJournal(tmp_path / "journal.jsonl")
        # 1W, then 9L, then 1W
        j.record(_rec(2.0))
        for _ in range(9): j.record(_rec(-1.0))
        j.record(_rec(2.0))
        m = j.compute_metrics(window=50)
        assert m.max_consec_losses == 9
        # 9 > 8 threshold → not viable
        assert not m.is_viable
        j.close()

    def test_journal_rehydrates_from_file(self, tmp_path):
        path = tmp_path / "journal.jsonl"
        j1 = TradeJournal(path)
        for _ in range(5): j1.record(_rec(1.5))
        j1.close()
        # New instance should re-read history
        j2 = TradeJournal(path)
        m = j2.compute_metrics(window=50)
        assert m.n_trades == 5
        j2.close()
