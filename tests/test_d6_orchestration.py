#!/usr/bin/env python3
"""
Tests for the D6 orchestration layer added in Step 1 of the L99 path.

Three modules under test:
  - d6_final_run.py            verdict synthesis (regex parsers + sanity)
  - d6_autotrigger.py          binding-run trigger (verdict summary parser)
  - production_monitor.py      state-transition alert logic

These are pure-Python tests — no network calls, no parquet I/O,
no subprocess. The qcut crash that took a full re-run cycle to
discover is exactly the kind of bug a small unit-test layer prevents.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import d6_final_run as d6
import d6_autotrigger as d6t
import production_monitor as pm


# ── d6_final_run.parse_robust_survivors ─────────────────────────────
class TestParseRobustSurvivors:
    """Survivor table extraction from microstructure_robust_check.py output."""

    def test_extracts_full_table(self):
        sample = """
  TIGHTENED PHASE B VERDICT — seven-filter battery
══════════════════════════════════════════════════════════════════════
  ✅ 3 (pair, feature, horizon) combos cleared ALL SEVEN filters:

     pair       feature                 H      IC   train   test
     -------------------------------------------------------------
     XRP_USDT   spread_pct          1800s +0.475 +0.588 +0.375
     ETH_USDT   basis_pct            120s +0.378 +0.382 +0.388
     BTC_USDT   ofi_30s               60s +0.157 +0.147 +0.171

  Robust (feature, horizon) combos hitting >=2 pairs:
"""
        out = d6.parse_robust_survivors(sample)
        assert len(out) == 3
        assert out[0] == {"pair": "XRP_USDT", "feature": "spread_pct",
                          "horizon": 1800, "ic": 0.475}
        assert out[1]["feature"] == "basis_pct"
        assert out[2]["ic"] == pytest.approx(0.157)

    def test_handles_negative_ic(self):
        sample = """
  TIGHTENED PHASE B VERDICT — seven-filter battery
     pair       feature              H      IC
     -----------------------------------------
     XRP_USDT   book_slope_bid     300s -0.286 -0.243 -0.357
"""
        out = d6.parse_robust_survivors(sample)
        assert len(out) == 1
        assert out[0]["ic"] == pytest.approx(-0.286)

    def test_empty_when_no_table(self):
        assert d6.parse_robust_survivors("nothing here") == []

    def test_empty_when_zero_survivors(self):
        sample = """
  TIGHTENED PHASE B VERDICT — seven-filter battery
  🛑 NO combo survives all 6 filters.
"""
        assert d6.parse_robust_survivors(sample) == []


# ── d6_final_run.parse_nature_fee_verdicts ──────────────────────────
class TestParseNatureFeeVerdicts:
    """Fee-scenario sensitivity row parser from signal_nature output."""

    def test_extracts_winner(self):
        sample = """
  FEE-SCENARIO SENSITIVITY — does any signal survive at lower fee tiers?
  pair      feature                H    Q5-Q1     10bps    20bps    30bps    40bps
  ----------------------------------------------------------------------------
  AVAX_USDT funding_rate_8h    1800s  -17.46    ✅ +7.5   🛑 -2.5  🛑-12.5  🛑-22.5

═══
"""
        out = d6.parse_nature_fee_verdicts(sample)
        assert len(out) == 1
        row = out[0]
        assert row["pair"] == "AVAX_USDT"
        assert row["feature"] == "funding_rate_8h"
        assert row["horizon"] == 1800
        assert row["gross_bps"] == pytest.approx(-17.46)
        assert row["maker_verdict"] == "✅"
        assert row["maker_net_bps"] == pytest.approx(7.5)

    def test_extracts_borderline(self):
        sample = """
  FEE-SCENARIO SENSITIVITY
  pair       feature             H    Q5-Q1     10bps
  ---------------------------------------------------
  XRP_USDT   spread_pct       1800s   +14.23   ⚠ +4.2

═══
"""
        out = d6.parse_nature_fee_verdicts(sample)
        assert len(out) == 1
        assert out[0]["maker_verdict"] == "⚠"
        assert out[0]["maker_net_bps"] == pytest.approx(4.2)

    def test_extracts_unprofitable(self):
        sample = """
  FEE-SCENARIO SENSITIVITY
  BTC_USDT   depth_imbalance     60s   +1.21    🛑 -8.8

═══
"""
        out = d6.parse_nature_fee_verdicts(sample)
        assert len(out) == 1
        assert out[0]["maker_verdict"] == "🛑"
        assert out[0]["maker_net_bps"] == pytest.approx(-8.8)


# ── d6_autotrigger.parse_verdict_summary ────────────────────────────
class TestVerdictSummaryParser:
    """Extract the Phase B verdict paragraph from D6_FINAL_VERDICT.md."""

    def test_extracts_go_section(self, tmp_path):
        md = tmp_path / "verdict.md"
        md.write_text("""# D6 FINAL VERDICT

## 1. Pre-flight sanity
✅ ok

## 4. Phase B promotion verdict
### 🟢 GO — Phase B candidate identified

**Lead cell:** `XRP · spread_pct @ H=1800s`

## 5. Audit trail
""")
        out = d6t.parse_verdict_summary(md)
        assert "🟢 GO" in out
        assert "Lead cell" in out
        assert "spread_pct" in out
        assert "Audit trail" not in out  # stops at next section

    def test_extracts_no_go_section(self, tmp_path):
        md = tmp_path / "verdict.md"
        md.write_text("""## 4. Phase B promotion verdict
### 🛑 NO-GO — no cell clears the maker-fee gate

ADR-002 fallback recommended.

## 5. Audit trail
""")
        out = d6t.parse_verdict_summary(md)
        assert "NO-GO" in out
        assert "ADR-002" in out

    def test_returns_message_on_missing_file(self, tmp_path):
        out = d6t.parse_verdict_summary(tmp_path / "nope.md")
        assert "not found" in out


# ── production_monitor.detect_transitions ───────────────────────────
class TestDetectTransitions:
    """Alert state-machine — fires Telegram, must be tight."""

    def _bot(self, pair="ETH_USDT", state="active", restarts=0,
             roi_pct=0.0) -> dict:
        return {"pair": pair, "state": state, "restarts": restarts,
                "roi_pct": roi_pct}

    def test_steady_state_emits_nothing(self):
        curr = [self._bot(roi_pct=-1.0)]
        prev = {"ETH_USDT": self._bot(roi_pct=-1.0)}
        out = pm.detect_transitions(curr, prev, collector_age_s=300,
                                     prev_collector_alert=False,
                                     disk_pct=20.0, prev_disk_alert=False)
        assert out == []

    def test_state_active_to_inactive(self):
        curr = [self._bot(state="failed")]
        prev = {"ETH_USDT": self._bot(state="active")}
        out = pm.detect_transitions(curr, prev, 300, False, 20.0, False)
        assert any("state = 'failed'" in a["msg"] for a in out)
        assert any(a["severity"] == "urgent" for a in out)

    def test_restart_count_increases(self):
        curr = [self._bot(restarts=2)]
        prev = {"ETH_USDT": self._bot(restarts=1)}
        out = pm.detect_transitions(curr, prev, 300, False, 20.0, False)
        assert len(out) == 1
        assert out[0]["severity"] == "urgent"
        assert "restarted" in out[0]["msg"]

    def test_dd_crosses_warn_threshold(self):
        curr = [self._bot(roi_pct=-3.5)]
        prev = {"ETH_USDT": self._bot(roi_pct=-1.0)}  # was healthy
        out = pm.detect_transitions(curr, prev, 300, False, 20.0, False)
        assert len(out) == 1
        assert out[0]["severity"] == "warn"
        assert "-3" in out[0]["msg"]

    def test_dd_crosses_urgent_threshold(self):
        curr = [self._bot(roi_pct=-6.0)]
        prev = {"ETH_USDT": self._bot(roi_pct=-1.0)}
        out = pm.detect_transitions(curr, prev, 300, False, 20.0, False)
        # Should fire ONE alert at urgent level (not also warn)
        urgent_msgs = [a for a in out if a["severity"] == "urgent"]
        warn_msgs = [a for a in out if a["severity"] == "warn"]
        assert len(urgent_msgs) == 1
        assert len(warn_msgs) == 0
        assert "Patch 3 hard limit" in urgent_msgs[0]["msg"]

    def test_dd_recovery(self):
        curr = [self._bot(roi_pct=-1.0)]
        prev = {"ETH_USDT": self._bot(roi_pct=-4.0)}
        out = pm.detect_transitions(curr, prev, 300, False, 20.0, False)
        assert len(out) == 1
        assert out[0]["severity"] == "info"
        assert "recovered" in out[0]["msg"]

    def test_dd_persistent_below_threshold_no_repeat(self):
        # Both runs at -4% — already past threshold, NO new alert (state-transition only)
        curr = [self._bot(roi_pct=-4.0)]
        prev = {"ETH_USDT": self._bot(roi_pct=-4.0)}
        out = pm.detect_transitions(curr, prev, 300, False, 20.0, False)
        assert out == []

    def test_collector_goes_stale(self):
        curr = [self._bot()]
        prev = {"ETH_USDT": self._bot()}
        out = pm.detect_transitions(curr, prev,
                                     collector_age_s=8000,  # >2h
                                     prev_collector_alert=False,
                                     disk_pct=20.0, prev_disk_alert=False)
        assert len(out) == 1
        assert out[0]["severity"] == "urgent"
        assert "Collector stale" in out[0]["msg"]

    def test_collector_no_files_at_all(self):
        out = pm.detect_transitions([], {},
                                     collector_age_s=None,
                                     prev_collector_alert=False,
                                     disk_pct=20.0, prev_disk_alert=False)
        assert any(a["severity"] == "urgent" and "stale" in a["msg"]
                   for a in out)

    def test_collector_resumed(self):
        out = pm.detect_transitions([self._bot()], {"ETH_USDT": self._bot()},
                                     collector_age_s=120,
                                     prev_collector_alert=True,
                                     disk_pct=20.0, prev_disk_alert=False)
        assert any(a["severity"] == "info" and "resumed" in a["msg"]
                   for a in out)

    def test_disk_pressure_alert(self):
        out = pm.detect_transitions([self._bot()], {"ETH_USDT": self._bot()},
                                     collector_age_s=300,
                                     prev_collector_alert=False,
                                     disk_pct=92.0, prev_disk_alert=False)
        assert any(a["severity"] == "warn" and "Disk usage" in a["msg"]
                   for a in out)

    def test_multi_bot_independent_alerts(self):
        # ETH crosses -3%, SOL fine — only one alert
        curr = [self._bot("ETH_USDT", roi_pct=-3.5),
                self._bot("SOL_USDT", roi_pct=-1.0)]
        prev = {"ETH_USDT": self._bot("ETH_USDT", roi_pct=-1.0),
                "SOL_USDT": self._bot("SOL_USDT", roi_pct=-1.0)}
        out = pm.detect_transitions(curr, prev, 300, False, 20.0, False)
        assert len(out) == 1
        assert "ETH_USDT" in out[0]["msg"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
