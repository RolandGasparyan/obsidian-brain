#!/usr/bin/env python3
"""
Unit tests for onchain_collector.py — buffer + z-scorer + parquet flush.

Pure-Python: no API calls, no parquet I/O dependencies on actual disk.
Tests the deterministic computation logic only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import onchain_collector as oc


class TestWhaleTxBuffer:
    """Rolling 1h window of large transactions."""

    def test_empty_buffer(self):
        buf = oc.WhaleTxBuffer()
        s = buf.stats_for_symbol("btc", now_s=1_000_000)
        assert s == {
            "whale_tx_count_1h": 0.0,
            "whale_tx_volume_1h": 0.0,
            "whale_tx_to_exchange": 0.0,
            "whale_tx_from_exchange": 0.0,
        }

    def test_single_tx(self):
        buf = oc.WhaleTxBuffer()
        buf.add(ts_s=1_000_000, symbol="btc",
                amount_usd=2_000_000.0,
                from_owner="unknown", to_owner="exchange")
        s = buf.stats_for_symbol("btc", now_s=1_000_000)
        assert s["whale_tx_count_1h"] == 1.0
        assert s["whale_tx_volume_1h"] == 2_000_000.0
        assert s["whale_tx_to_exchange"] == 1.0
        assert s["whale_tx_from_exchange"] == 0.0

    def test_window_eviction(self):
        buf = oc.WhaleTxBuffer()
        # Old tx (>1h ago) should be evicted
        buf.add(ts_s=1_000_000, symbol="btc", amount_usd=1e6,
                from_owner="exchange", to_owner="unknown")
        # New tx
        buf.add(ts_s=1_000_000 + 3700,   # 1h + 100 sec later
                symbol="btc", amount_usd=2e6,
                from_owner="unknown", to_owner="exchange")
        s = buf.stats_for_symbol("btc", now_s=1_000_000 + 3700)
        # Old one evicted, only the new $2M tx counts
        assert s["whale_tx_count_1h"] == 1.0
        assert s["whale_tx_volume_1h"] == 2_000_000.0
        assert s["whale_tx_to_exchange"] == 1.0
        assert s["whale_tx_from_exchange"] == 0.0

    def test_symbol_filter(self):
        buf = oc.WhaleTxBuffer()
        buf.add(1_000_000, "btc", 1e6, "u", "u")
        buf.add(1_000_000, "eth", 1e6, "u", "u")
        buf.add(1_000_000, "btc", 2e6, "u", "u")
        s_btc = buf.stats_for_symbol("btc", 1_000_000)
        s_eth = buf.stats_for_symbol("eth", 1_000_000)
        assert s_btc["whale_tx_count_1h"] == 2.0
        assert s_eth["whale_tx_count_1h"] == 1.0
        assert s_btc["whale_tx_volume_1h"] == 3_000_000.0
        assert s_eth["whale_tx_volume_1h"] == 1_000_000.0

    def test_symbol_case_insensitive(self):
        buf = oc.WhaleTxBuffer()
        buf.add(1_000_000, "BTC", 1e6, "u", "u")
        s = buf.stats_for_symbol("btc", 1_000_000)
        assert s["whale_tx_count_1h"] == 1.0


class TestFlowZScorer:
    """30-day rolling z-score for flow metrics."""

    def test_first_few_samples_return_none(self):
        z = oc.FlowZScorer()
        # Less than 10 samples → returns None (not enough data)
        for i in range(5):
            assert z.push(ts_s=1_000_000 + i, value=float(i)) is None

    def test_z_score_computes_after_threshold(self):
        z = oc.FlowZScorer()
        # Push 10 identical values — std = 0 → z returns 0.0
        for i in range(10):
            z.push(ts_s=1_000_000 + i, value=100.0)
        assert z.push(ts_s=1_000_010, value=100.0) == 0.0

    def test_outlier_detection(self):
        z = oc.FlowZScorer()
        # 10 samples around 100, then a clear outlier
        for i in range(10):
            z.push(1_000_000 + i, 100.0 + (i % 2))   # values 100,101,100,101,...
        # Add an outlier at +500
        result = z.push(1_000_010, 500.0)
        # Should have positive z (above mean)
        assert result is not None
        assert result > 1.0   # at least 1 sigma above mean

    def test_window_eviction_over_30_days(self):
        z = oc.FlowZScorer(window_sec=30 * 24 * 3600)
        # Push old samples
        for i in range(10):
            z.push(ts_s=1_000_000 + i, value=100.0)
        # Push current sample 31 days later — old samples should be evicted
        future_ts = 1_000_000 + 31 * 24 * 3600
        z.push(ts_s=future_ts, value=100.0)
        # Buffer now has only the most recent sample — too few for z-score
        result = z.push(ts_s=future_ts + 1, value=200.0)
        assert result is None   # only 2 samples in window, < 10


class TestPairStateAndPath:
    def test_pair_state_init(self):
        st = oc.PairState(pair="BTC_USDT", asset="btc")
        assert st.pair == "BTC_USDT"
        assert st.asset == "btc"
        assert st.buffer == []
        assert isinstance(st.netflow_z, oc.FlowZScorer)
        assert isinstance(st.miner_z, oc.FlowZScorer)

    def test_hour_stamp_format(self):
        # _hour_stamp returns YYYY-MM-DD/HH for parquet path
        stamp = oc._hour_stamp()
        # Format: 4-2-2/2  = 13 chars including the slash
        parts = stamp.split("/")
        assert len(parts) == 2
        date_part, hour_part = parts
        assert len(date_part) == 10   # YYYY-MM-DD
        assert len(hour_part) == 2    # HH
        # All digits and dashes
        assert date_part.replace("-", "").isdigit()
        assert hour_part.isdigit()
        assert 0 <= int(hour_part) <= 23


class TestPairToAssetMapping:
    def test_btc_eth_mapped(self):
        assert oc.PAIR_TO_ASSET["BTC_USDT"] == "btc"
        assert oc.PAIR_TO_ASSET["ETH_USDT"] == "eth"

    def test_other_pairs_not_in_default(self):
        # Reminder: SOL/XRP/AVAX not yet mapped (free tiers may not cover)
        assert "SOL_USDT" not in oc.PAIR_TO_ASSET
        assert "XRP_USDT" not in oc.PAIR_TO_ASSET


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
