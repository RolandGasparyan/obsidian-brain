"""
Edge-case + stress tests for canary_executor.py pure functions.

These tests exercise the executor's safety-critical helpers (arm/halt/clock
gates, credential loader, state I/O, round arithmetic) under failure modes
that would normally only surface in production:

  • corrupt JSON in canary_arm.json / state_*.json / halt file
  • malformed keyfile (no colon, empty side, wrong permissions)
  • missing files
  • lifetime-cap boundary
  • round-id computation at session-start and far in the future

No network. No ccxt. No live executor invocation. All tests patch the
filesystem to a tmp_path and call the helper functions directly.

Compatible with `pytest` (auto-discovered by CI) AND standalone via
`python3 canary/tests/test_executor_edge_cases.py`.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

try:
    import pytest  # noqa: F401
except ImportError:
    pytest = None

HERE = Path(__file__).resolve().parent
EXECUTOR = HERE.parent / "canary_executor.py"


def _import_executor():
    """Import canary_executor without running main()."""
    spec = importlib.util.spec_from_file_location("canary_executor", EXECUTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXECUTOR}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_keyfile(path: Path, content: str, mode: int = 0o600) -> Path:
    path.write_text(content)
    os.chmod(path, mode)
    return path


def _expect_fail_closed(ex, callable_, *args, **kwargs):
    """Assert that calling `callable_(*args, **kwargs)` triggers fail_closed()
    (which calls sys.exit(1)). Returns the captured log error string."""
    captured: list[str] = []
    orig = ex.fail_closed

    def _capture(reason):
        captured.append(str(reason))
        raise SystemExit(1)

    with patch.object(ex, "fail_closed", side_effect=_capture):
        try:
            callable_(*args, **kwargs)
        except SystemExit:
            pass
    assert captured, "fail_closed was not called when failure was expected"
    return captured[0]


# ---- arm gate ------------------------------------------------------------

def test_check_arm_missing_file_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        arm_path = Path(td) / "canary_arm.json"  # does not exist
        with patch.object(ex, "ARM_FILE", arm_path):
            reason = _expect_fail_closed(ex, ex.check_arm)
        assert "arm file missing" in reason


def test_check_arm_unparseable_json_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        arm_path = Path(td) / "canary_arm.json"
        arm_path.write_text("{not valid json{")
        with patch.object(ex, "ARM_FILE", arm_path):
            reason = _expect_fail_closed(ex, ex.check_arm)
        assert "arm unreadable" in reason


def test_check_arm_missing_required_key_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        arm_path = Path(td) / "canary_arm.json"
        # Missing paper_preflight_passed
        arm_path.write_text(json.dumps({
            "armed_by": "test", "armed_at": "2026-05-19T00:00:00+00:00",
            "ack_max_loss_usd": 4.0, "ack_time_cap_hours": 720,
        }))
        with patch.object(ex, "ARM_FILE", arm_path):
            reason = _expect_fail_closed(ex, ex.check_arm)
        assert "missing key" in reason


def test_check_arm_paper_preflight_false_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        arm_path = Path(td) / "canary_arm.json"
        arm_path.write_text(json.dumps({
            "armed_by": "test", "armed_at": "2026-05-19T00:00:00+00:00",
            "ack_max_loss_usd": 4.0, "ack_time_cap_hours": 720,
            "paper_preflight_passed": False,
        }))
        with patch.object(ex, "ARM_FILE", arm_path):
            reason = _expect_fail_closed(ex, ex.check_arm)
        assert "paper preflight not passed" in reason


def test_check_arm_happy_path_returns_arm():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        arm_path = Path(td) / "canary_arm.json"
        arm = {
            "armed_by": "test", "armed_at": "2026-05-19T00:00:00+00:00",
            "ack_max_loss_usd": 4.0, "ack_time_cap_hours": 720,
            "paper_preflight_passed": True,
        }
        arm_path.write_text(json.dumps(arm))
        with patch.object(ex, "ARM_FILE", arm_path):
            result = ex.check_arm()
        assert result == arm


# ---- halt gate -----------------------------------------------------------

def test_check_halts_active_l99_halt_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        l99 = Path(td) / "l99.json"
        l99.write_text(json.dumps({"halted": True, "reason": "test"}))
        halt = Path(td) / "halt.json"  # does not exist
        with patch.object(ex, "L99_HALT", l99), patch.object(ex, "HALT_FILE", halt):
            reason = _expect_fail_closed(ex, ex.check_halts)
        assert "halt active" in reason


def test_check_halts_unparseable_halt_file_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        l99 = Path(td) / "l99.json"  # does not exist
        halt = Path(td) / "halt.json"
        halt.write_text("{not json{")
        with patch.object(ex, "L99_HALT", l99), patch.object(ex, "HALT_FILE", halt):
            reason = _expect_fail_closed(ex, ex.check_halts)
        assert "halt unparseable" in reason


def test_check_halts_inactive_no_action():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        l99 = Path(td) / "l99.json"
        l99.write_text(json.dumps({"halted": False}))
        halt = Path(td) / "halt.json"  # does not exist
        # Should NOT fail_closed. We assert by completing without raising.
        with patch.object(ex, "L99_HALT", l99), patch.object(ex, "HALT_FILE", halt):
            ex.check_halts()  # ← if this raises, the test fails


# ---- clock gate ----------------------------------------------------------

def test_check_clock_lifetime_exceeded_fail_closed():
    ex = _import_executor()
    # arm.armed_at = MAX_LIFETIME_HOURS + 1h ago
    past = datetime.now(timezone.utc) - timedelta(hours=ex.MAX_LIFETIME_HOURS + 1)
    arm = {"armed_at": past.isoformat()}
    reason = _expect_fail_closed(ex, ex.check_clock, arm)
    assert "lifetime cap" in reason


def test_check_clock_fresh_arm_passes():
    ex = _import_executor()
    arm = {"armed_at": datetime.now(timezone.utc).isoformat()}
    # No raise, no fail_closed.
    ex.check_clock(arm)


# ---- credential loader ---------------------------------------------------

def test_load_creds_missing_file_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        kf = Path(td) / "absent_key"
        reason = _expect_fail_closed(ex, ex.load_creds, kf)
        assert "key file missing" in reason


def test_load_creds_wrong_perms_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        kf = _write_keyfile(Path(td) / "key", "k:s", mode=0o644)
        reason = _expect_fail_closed(ex, ex.load_creds, kf)
        assert "perms" in reason


def test_load_creds_no_colon_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        kf = _write_keyfile(Path(td) / "key", "no_separator_here")
        reason = _expect_fail_closed(ex, ex.load_creds, kf)
        assert "need KEY:SECRET" in reason


def test_load_creds_empty_secret_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        kf = _write_keyfile(Path(td) / "key", "thekey:")
        reason = _expect_fail_closed(ex, ex.load_creds, kf)
        assert "malformed" in reason or "empty" in reason


def test_load_creds_empty_key_fail_closed():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        kf = _write_keyfile(Path(td) / "key", ":thesecret")
        reason = _expect_fail_closed(ex, ex.load_creds, kf)
        assert "malformed" in reason or "empty" in reason


def test_load_creds_strips_whitespace_inside_value():
    """A single trailing space on the API key produces INVALID_SIGNATURE
    at Gate.io with no other clue. load_creds strips each side after
    splitting on ':' to defend against that."""
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        kf = _write_keyfile(Path(td) / "key", "  thekey  :  thesecret  \n")
        k, s = ex.load_creds(kf)
        assert k == "thekey"
        assert s == "thesecret"


# ---- state I/O round-trip ------------------------------------------------

def test_init_state_has_required_fields():
    ex = _import_executor()
    s = ex.init_state(ex.ACCOUNTS[0])
    for field in (
        "account_id", "positions", "trades_today", "current_date",
        "session_pnl", "session_start", "daily_dd_usd", "consec_api_fails",
        "last_exit_ts", "round_anchors", "last_seen_round_id",
    ):
        assert field in s, f"init_state missing {field}"
    assert s["account_id"] == "MAIN"
    assert s["positions"] == {}
    assert s["trades_today"] == 0
    assert s["session_pnl"] == 0.0
    assert s["round_anchors"] == {}
    assert s["last_seen_round_id"] == 0


def test_load_state_returns_init_state_when_file_absent():
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        acc = dict(ex.ACCOUNTS[0])
        acc["state_file"] = Path(td) / "state_missing.json"
        s = ex.load_state(acc)
        assert s["account_id"] == acc["id"]
        assert s["trades_today"] == 0


def test_load_state_recovers_from_corrupt_json():
    """If state_*.json is corrupt (truncated write, etc.), load_state
    must return a fresh init_state — not crash the thread on every poll."""
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        acc = dict(ex.ACCOUNTS[0])
        sf = Path(td) / "state_corrupt.json"
        sf.write_text("{not valid json{")
        acc["state_file"] = sf
        s = ex.load_state(acc)
        # Should recover gracefully — not raise
        assert s["account_id"] == acc["id"]
        assert s["trades_today"] == 0


def test_load_state_migrates_old_state_without_round_fields():
    """Earlier state files (pre PR #28) lack round_anchors / last_seen_round_id.
    load_state must backfill them with safe defaults instead of crashing
    publish_status's round logic."""
    ex = _import_executor()
    with tempfile.TemporaryDirectory() as td:
        acc = dict(ex.ACCOUNTS[0])
        sf = Path(td) / "state_old.json"
        sf.write_text(json.dumps({
            "account_id": "MAIN", "positions": {}, "trades_today": 3,
            "current_date": "2026-05-19", "session_pnl": 1.50,
            "session_start": "2026-05-19T00:00:00+00:00",
            "daily_dd_usd": 0.0, "consec_api_fails": 0, "last_exit_ts": {},
            # NOTE: no round_anchors, no last_seen_round_id
        }))
        acc["state_file"] = sf
        s = ex.load_state(acc)
        assert s["trades_today"] == 3, "existing fields preserved"
        assert s["round_anchors"] == {}, "round_anchors backfilled"
        assert s["last_seen_round_id"] == 0, "last_seen_round_id backfilled"


# ---- round arithmetic ----------------------------------------------------

def test_round_id_now_at_arm_time_is_round_1():
    ex = _import_executor()
    arm = {"armed_at": datetime.now(timezone.utc).isoformat()}
    assert ex.round_id_now(arm) == 1


def test_round_id_now_after_2h_is_round_3():
    ex = _import_executor()
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2, seconds=1)
    arm = {"armed_at": two_hours_ago.isoformat()}
    # 0-60min = round 1, 60-120min = round 2, 120min+ = round 3
    assert ex.round_id_now(arm) == 3


def test_round_started_at_offsets_by_interval():
    ex = _import_executor()
    base = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
    arm = {"armed_at": base.isoformat()}
    # Round 1 starts at arm.armed_at
    assert ex.round_started_at(arm, 1).startswith("2026-05-19T12:00:00")
    # Round 4 starts at arm.armed_at + 3 * 60min
    assert ex.round_started_at(arm, 4).startswith("2026-05-19T15:00:00")


# ---- ccxt absence guard --------------------------------------------------

def test_make_ex_without_ccxt_fail_closed():
    ex = _import_executor()
    with patch.object(ex, "ccxt", None):
        reason = _expect_fail_closed(ex, ex.make_ex, ex.ACCOUNTS[0])
        assert "ccxt not installed" in reason


def test_make_ex_public_without_ccxt_fail_closed():
    ex = _import_executor()
    with patch.object(ex, "ccxt", None):
        reason = _expect_fail_closed(ex, ex.make_ex_public)
        assert "ccxt not installed" in reason


# ---- standalone runner ---------------------------------------------------

def _main():
    """Standalone runner: no pytest, no fixtures."""
    tests = [
        ("check_arm: missing file", test_check_arm_missing_file_fail_closed),
        ("check_arm: unparseable JSON", test_check_arm_unparseable_json_fail_closed),
        ("check_arm: missing required key", test_check_arm_missing_required_key_fail_closed),
        ("check_arm: paper_preflight=False", test_check_arm_paper_preflight_false_fail_closed),
        ("check_arm: happy path returns arm", test_check_arm_happy_path_returns_arm),
        ("check_halts: active L99", test_check_halts_active_l99_halt_fail_closed),
        ("check_halts: unparseable halt", test_check_halts_unparseable_halt_file_fail_closed),
        ("check_halts: inactive — passes", test_check_halts_inactive_no_action),
        ("check_clock: lifetime exceeded", test_check_clock_lifetime_exceeded_fail_closed),
        ("check_clock: fresh arm passes", test_check_clock_fresh_arm_passes),
        ("load_creds: missing file", test_load_creds_missing_file_fail_closed),
        ("load_creds: wrong perms", test_load_creds_wrong_perms_fail_closed),
        ("load_creds: no colon", test_load_creds_no_colon_fail_closed),
        ("load_creds: empty secret", test_load_creds_empty_secret_fail_closed),
        ("load_creds: empty key", test_load_creds_empty_key_fail_closed),
        ("load_creds: strips inner whitespace", test_load_creds_strips_whitespace_inside_value),
        ("init_state: required fields", test_init_state_has_required_fields),
        ("load_state: absent file → init", test_load_state_returns_init_state_when_file_absent),
        ("load_state: corrupt JSON recovers", test_load_state_recovers_from_corrupt_json),
        ("load_state: old state migrates", test_load_state_migrates_old_state_without_round_fields),
        ("round_id_now: at arm time = 1", test_round_id_now_at_arm_time_is_round_1),
        ("round_id_now: after 2h = 3", test_round_id_now_after_2h_is_round_3),
        ("round_started_at: offset arithmetic", test_round_started_at_offsets_by_interval),
        ("make_ex: missing ccxt", test_make_ex_without_ccxt_fail_closed),
        ("make_ex_public: missing ccxt", test_make_ex_public_without_ccxt_fail_closed),
    ]
    passes = 0
    fails = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passes += 1
        except AssertionError as e:
            print(f"  FAIL  {name} — {e}")
            fails += 1
        except Exception as e:
            print(f"  ERROR {name} — {type(e).__name__}: {e}")
            fails += 1
    print(f"\nRESULT: {passes}/{passes + fails} passed · {fails} failed")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    _main()
