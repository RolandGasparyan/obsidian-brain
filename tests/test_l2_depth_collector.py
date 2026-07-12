"""
Unit tests for l2_depth_collector — parser + buffer + cumulative depth math.

No live WebSocket connection. Tests run in <100ms.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from l2_depth_collector import (
    OrderBook,
    SnapshotBuffer,
    build_subscribe_payload,
    make_snapshot_row,
    _MISSING_DEPS,
)

# Tests that exercise the parquet flush path need pandas/pyarrow; skip
# them if the optional runtime deps aren't installed. Pure-logic tests
# (OrderBook math, snapshot row construction) still run.
requires_runtime_deps = pytest.mark.skipif(
    bool(_MISSING_DEPS),
    reason=f"requires runtime deps: {', '.join(_MISSING_DEPS)}",
)


# ─────────────────────────────────────────────
# OrderBook
# ─────────────────────────────────────────────

class TestOrderBook:
    def _sample_msg(self):
        # Simulated Gate.io spot.order_book full snapshot push.
        return {
            "channel": "spot.order_book",
            "event": "update",
            "result": {
                "bids": [["50000", "1.0"], ["49999", "2.0"], ["49000", "3.0"]],
                "asks": [["50001", "1.5"], ["50002", "2.5"], ["51000", "4.0"]],
            },
        }

    def test_apply_snapshot_basic(self):
        book = OrderBook(pair="BTC_USDT")
        book.apply_snapshot(self._sample_msg())
        assert book.best_bid() == 50000.0
        assert book.best_ask() == 50001.0
        assert book.mid() == 50000.5

    def test_apply_snapshot_sorts(self):
        book = OrderBook(pair="BTC_USDT")
        msg = {
            "channel": "spot.order_book",
            "event": "update",
            "result": {
                "bids": [["49999", "2.0"], ["50000", "1.0"], ["49998", "3.0"]],
                "asks": [["50002", "2.5"], ["50001", "1.5"], ["50003", "1.0"]],
            },
        }
        book.apply_snapshot(msg)
        # bids descending
        assert book.bids[0][0] == 50000.0
        assert book.bids[1][0] == 49999.0
        # asks ascending
        assert book.asks[0][0] == 50001.0
        assert book.asks[1][0] == 50002.0

    def test_zero_size_levels_filtered(self):
        book = OrderBook(pair="BTC_USDT")
        msg = {
            "channel": "spot.order_book",
            "event": "update",
            "result": {
                "bids": [["50000", "0"], ["49999", "1.0"]],
                "asks": [["50001", "1.0"], ["50002", "0"]],
            },
        }
        book.apply_snapshot(msg)
        assert len(book.bids) == 1
        assert len(book.asks) == 1
        assert book.bids[0][0] == 49999.0
        assert book.asks[0][0] == 50001.0

    def test_spread_bps(self):
        book = OrderBook(pair="BTC_USDT")
        book.apply_snapshot(self._sample_msg())
        # mid = 50000.5, spread = 1.0, spread_bps = 1/50000.5 * 10000 ≈ 0.1999...
        sp = book.spread_bps()
        assert sp == pytest.approx(0.19999, abs=1e-3)

    def test_empty_book(self):
        book = OrderBook(pair="BTC_USDT")
        assert book.best_bid() is None
        assert book.best_ask() is None
        assert book.mid() is None
        assert book.spread_bps() is None


class TestCumDepth:
    def test_within_1pct(self):
        # mid = 100, 1% band = [99, 101]
        # bids at 99.5 (size 1), 99.0 (size 1) → both within
        # asks at 100.5 (size 1), 101.0 (size 1) → first within, second AT cutoff
        book = OrderBook(pair="X")
        msg = {
            "channel": "spot.order_book", "event": "update",
            "result": {
                "bids": [["99.5", "1"], ["99.0", "1"], ["98.5", "1"]],
                "asks": [["100.5", "1"], ["101.0", "1"], ["101.5", "1"]],
            },
        }
        book.apply_snapshot(msg)
        # mid will be (99.5 + 100.5) / 2 = 100.0
        assert book.mid() == 100.0
        # 1% band: 99 to 101
        # bids at >= 99: 99.5 (1.0) and 99.0 (1.0). 98.5 excluded.
        # cum bid notional = 99.5 * 1 + 99.0 * 1 = 198.5
        assert book.cum_depth("bid", 1.0) == pytest.approx(198.5)
        # asks at <= 101: 100.5 (1.0) and 101.0 (1.0)
        # cum ask notional = 100.5 + 101.0 = 201.5
        assert book.cum_depth("ask", 1.0) == pytest.approx(201.5)

    def test_within_5pct_includes_more(self):
        book = OrderBook(pair="X")
        msg = {
            "channel": "spot.order_book", "event": "update",
            "result": {
                "bids": [["99", "1"], ["98", "1"], ["95", "1"], ["90", "1"]],
                "asks": [["101", "1"], ["102", "1"], ["105", "1"], ["110", "1"]],
            },
        }
        book.apply_snapshot(msg)
        # mid = 100; 5% band = [95, 105]
        # bids at 99 (1), 98 (1), 95 (1) → all within. 90 excluded.
        cum_b = book.cum_depth("bid", 5.0)
        assert cum_b == pytest.approx(99 + 98 + 95)
        # asks at 101 (1), 102 (1), 105 (1) → all within. 110 excluded.
        cum_a = book.cum_depth("ask", 5.0)
        assert cum_a == pytest.approx(101 + 102 + 105)


# ─────────────────────────────────────────────
# SnapshotBuffer
# ─────────────────────────────────────────────

class TestSnapshotBuffer:
    def test_add_and_clear(self):
        buf = SnapshotBuffer()
        buf.add({"ts_ms": 1, "pair": "BTC", "mid_price": 100.0})
        assert len(buf.rows) == 1
        # Manually clear via flush; flush requires a writable dir
        # Just verify rows accumulate.
        buf.add({"ts_ms": 2, "pair": "BTC", "mid_price": 101.0})
        assert len(buf.rows) == 2

    @requires_runtime_deps
    def test_flush_writes_parquet(self, tmp_path):
        buf = SnapshotBuffer()
        buf.add({
            "ts_ms": 1700000000000, "pair": "BTC_USDT", "mid_price": 50000.0,
            "spread_bps": 0.5, "best_bid": 49999.5, "best_ask": 50000.5,
            "bid_levels": [[49999.5, 1.0]], "ask_levels": [[50000.5, 1.0]],
            "cum_bid_depth_1pct": 100.0, "cum_ask_depth_1pct": 100.0,
            "cum_bid_depth_5pct": 100.0, "cum_ask_depth_5pct": 100.0,
        })
        dst = buf.flush(tmp_path, "BTC_USDT")
        assert dst is not None
        assert dst.exists()
        # Buffer cleared
        assert len(buf.rows) == 0
        # Re-read to verify schema
        import pandas as pd
        df = pd.read_parquet(dst)
        assert len(df) == 1
        assert df["mid_price"].iloc[0] == 50000.0

    def test_flush_empty_returns_none(self, tmp_path):
        buf = SnapshotBuffer()
        assert buf.flush(tmp_path, "BTC_USDT") is None


# ─────────────────────────────────────────────
# Subscribe payload
# ─────────────────────────────────────────────

class TestSubscribePayload:
    def test_payload_shape(self):
        p = build_subscribe_payload("BTC_USDT")
        assert p["channel"] == "spot.order_book"
        assert p["event"] == "subscribe"
        assert p["payload"] == ["BTC_USDT", "20", "100ms"]
        assert isinstance(p["time"], int)


# ─────────────────────────────────────────────
# make_snapshot_row
# ─────────────────────────────────────────────

class TestMakeSnapshotRow:
    def test_full_row(self):
        book = OrderBook(pair="BTC_USDT")
        msg = {
            "channel": "spot.order_book", "event": "update",
            "result": {
                "bids": [["50000", "1.0"], ["49999", "2.0"]],
                "asks": [["50001", "1.5"], ["50002", "2.5"]],
            },
        }
        book.apply_snapshot(msg)
        row = make_snapshot_row("BTC_USDT", book)
        assert row is not None
        assert row["pair"] == "BTC_USDT"
        assert row["mid_price"] == 50000.5
        assert row["best_bid"] == 50000.0
        assert row["best_ask"] == 50001.0
        assert len(row["bid_levels"]) == 2
        assert len(row["ask_levels"]) == 2

    def test_empty_book_returns_none(self):
        book = OrderBook(pair="BTC_USDT")
        row = make_snapshot_row("BTC_USDT", book)
        assert row is None

    def test_one_sided_book_returns_none(self):
        book = OrderBook(pair="BTC_USDT")
        msg = {
            "channel": "spot.order_book", "event": "update",
            "result": {"bids": [["50000", "1.0"]], "asks": []},
        }
        book.apply_snapshot(msg)
        row = make_snapshot_row("BTC_USDT", book)
        assert row is None
