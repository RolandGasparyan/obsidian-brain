"""
Smoke tests for canary_executor.publish_status output shape.

The frontend pages read terminal.json + live_battle.json. The fields these
files must contain were established empirically over multiple deploys
(see PRs #10, #24). If anyone refactors publish_status and breaks the
field set, these tests catch it at CI time instead of after a frontend
page silently goes blank.

Compatible with `pytest` (auto-discovered by the CI workflow) AND
standalone via `python3 canary/tests/test_publish_shape.py`.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

try:
    import pytest  # noqa: F401  pytest fixtures used below if available
except ImportError:
    pytest = None  # standalone runner mode (no pytest required)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
EXECUTOR = HERE.parent / "canary_executor.py"


def _import_executor():
    """Import canary_executor without running main()."""
    spec = importlib.util.spec_from_file_location("canary_executor", EXECUTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXECUTOR}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_state(account_id: str, has_position: bool = False) -> dict:
    base = {
        "account_id": account_id,
        "positions": {},
        "trades_today": 0,
        "current_date": "2026-05-19",
        "session_pnl": 0.0,
        "session_start": "2026-05-19T00:00:00+00:00",
        "daily_dd_usd": 0.0,
        "consec_api_fails": 0,
        "last_exit_ts": {},
    }
    if has_position:
        base["positions"] = {
            "BTC/USDT": {
                "side": "long", "entry_price": 77050.10,
                "size_usdt": 18.0, "size_base": 0.0002336,
                "entry_ts": 1779188634.0,
            }
        }
        base["trades_today"] = 1
    return base


class _AliveThread:
    def is_alive(self) -> bool:
        return True


class _DeadThread:
    def is_alive(self) -> bool:
        return False


# pytest fixtures (only used when pytest is importing this file)
if pytest is not None:
    @pytest.fixture
    def ex():
        return _import_executor()


def _publish_into(ex, tmp_path: Path, states: list, threads_by_id=None, arm=None):
    """Helper: patch the three output paths to tmp_path and call publish_status."""
    with patch.object(ex, "STATUS_FILE", tmp_path / "status.json"), \
         patch.object(ex, "FRONTEND_PUB", tmp_path / "live_battle.json"), \
         patch.object(ex, "TERMINAL_PUB", tmp_path / "terminal.json"):
        ex.publish_status(states, ex.ALL_PAIRS, threads_by_id, arm=arm)
    return (
        json.loads((tmp_path / "status.json").read_text()),
        json.loads((tmp_path / "live_battle.json").read_text()),
        json.loads((tmp_path / "terminal.json").read_text()),
    )


# ---- tests ----------------------------------------------------------------

def test_terminal_json_has_required_top_level_keys(ex=None, tmp_path=None):
    if ex is None:
        ex = _import_executor()
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    states = [_make_state(a["id"]) for a in ex.ACCOUNTS]
    threads = {a["id"]: _AliveThread() for a in ex.ACCOUNTS}
    _, _, term = _publish_into(ex, tmp_path, states, threads)
    # legacy frontend fields
    for key in ("mode", "disclaimer", "real_capital_usd", "layer1_locked",
                "layer1_l99_halted", "accounts", "pairs", "strategy",
                "agents", "bot", "timestamp"):
        assert key in term, f"terminal.json missing legacy key: {key}"
    # Schema version contract — frontends pin to a min version
    assert term.get("schema_version") == "2.0", \
        f"terminal.json schema_version expected '2.0', got {term.get('schema_version')!r}"
    # live fields added by publish_status
    assert "pairs_ranked" in term, "terminal.json missing pairs_ranked"
    assert "live" in term, "terminal.json missing live aggregate"
    for k in ("aggregate_session_pnl_usd", "aggregate_trades_today",
              "alive_accounts", "total_accounts"):
        assert k in term["live"], f"terminal.json live.{k} missing"


def test_terminal_accounts_have_per_account_live_data(ex=None, tmp_path=None):
    if ex is None:
        ex = _import_executor()
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    states = [
        _make_state("MAIN"),
        _make_state("SUB1", has_position=True),
        _make_state("SUB2"),
    ]
    threads = {"MAIN": _DeadThread(), "SUB1": _AliveThread(), "SUB2": _AliveThread()}
    _, _, term = _publish_into(ex, tmp_path, states, threads)
    for aid in ("MAIN", "SUB1", "SUB2"):
        acc = term["accounts"][aid]
        for key in ("agent_label", "capital_usd", "status", "trades_today",
                    "session_pnl_usd", "daily_dd_usd",
                    "open_positions", "positions"):
            assert key in acc, f"accounts.{aid} missing {key}"
    # DEAD MAIN should show status: DEAD
    assert term["accounts"]["MAIN"]["status"] == "DEAD"
    # SUB1 with open position
    assert term["accounts"]["SUB1"]["open_positions"] == 1
    assert "BTC/USDT" in term["accounts"]["SUB1"]["positions"]
    # Cinematic agent labels surfaced on every account — canonical IDs
    # remain MAIN/SUB1/SUB2 (used for keyfile lookup, halt/restore, logs);
    # agent_label is frontend-only ornament.
    assert term["accounts"]["MAIN"]["agent_label"] == "TITAN"
    assert term["accounts"]["SUB1"]["agent_label"] == "VELOCITY"
    assert term["accounts"]["SUB2"]["agent_label"] == "SENTINEL"


def test_live_battle_json_matches_status_file(ex=None, tmp_path=None):
    if ex is None:
        ex = _import_executor()
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    states = [_make_state(a["id"]) for a in ex.ACCOUNTS]
    status, live, _ = _publish_into(ex, tmp_path, states, None)
    # timestamps may differ only by microseconds — overwrite for comparison
    live["timestamp"] = status["timestamp"]
    assert live == status, "live_battle.json and multi_battle_status.json must match"


def test_pairs_match_config(ex=None, tmp_path=None):
    if ex is None:
        ex = _import_executor()
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    states = [_make_state(a["id"]) for a in ex.ACCOUNTS]
    _, _, term = _publish_into(ex, tmp_path, states, None)
    # CMO_CHANDE v2 pairs: FLOKI/WIF/OP/SHIB/DOT/ADA/UNI/ATOM/BNB
    assert term["pairs"] == ex.ALL_PAIRS
    assert "FLOKI/USDT" in ex.ALL_PAIRS, "CMO_CHANDE v2 must include FLOKI/USDT (PF=4.43)"


def test_aggregate_live_pnl_sums_states(ex=None, tmp_path=None):
    if ex is None:
        ex = _import_executor()
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    states = [_make_state(a["id"]) for a in ex.ACCOUNTS]
    states[0]["session_pnl"] = 1.5
    states[1]["session_pnl"] = -0.25
    states[2]["session_pnl"] = 0.75
    _, _, term = _publish_into(ex, tmp_path, states, None)
    assert abs(term["live"]["aggregate_session_pnl_usd"] - 2.0) < 1e-9


def test_championship_rounds_crown_top_earner(ex=None, tmp_path=None):
    """60-min championship: build_rounds_view ranks champions per round and
    names the winner. Top session_pnl gain over the round wins."""
    if ex is None:
        ex = _import_executor()
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    # Stub arm: armed 90 min ago → current round = 2
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    arm_at = (_dt.now(_tz.utc) - _td(minutes=90)).isoformat()
    arm = {"armed_at": arm_at}

    # 3 accounts. Round 1 (anchors at start): MAIN=0, SUB1=0, SUB2=0
    #                                  end:    MAIN=1.5, SUB1=0.5, SUB2=-0.3
    # Round 2 (in progress): SUB1 = +0.4 from its anchor, others flat
    states = [_make_state(a["id"]) for a in ex.ACCOUNTS]
    states[0]["round_anchors"] = {"1": {"started_at": arm_at, "session_pnl_at_start": 0.0},
                                  "2": {"started_at": arm_at, "session_pnl_at_start": 1.5}}
    states[0]["session_pnl"] = 1.5  # round 2 in progress: 0 delta
    states[1]["round_anchors"] = {"1": {"started_at": arm_at, "session_pnl_at_start": 0.0},
                                  "2": {"started_at": arm_at, "session_pnl_at_start": 0.5}}
    states[1]["session_pnl"] = 0.9  # round 2 in progress: +0.4 delta — SUB1 leads
    states[2]["round_anchors"] = {"1": {"started_at": arm_at, "session_pnl_at_start": 0.0},
                                  "2": {"started_at": arm_at, "session_pnl_at_start": -0.3}}
    states[2]["session_pnl"] = -0.3

    _, _, term = _publish_into(ex, tmp_path, states, None, arm=arm)
    champ = term["championship"]
    assert champ["current_round_id"] == 2, f"current_round_id={champ['current_round_id']}"
    # Round 1 should be present (completed). MAIN should be its winner with +1.5
    round1 = next((r for r in champ["rounds"] if r["round_id"] == 1), None)
    assert round1 is not None, "round 1 missing from view"
    assert round1["in_progress"] is False
    assert round1["winner_account_id"] == "MAIN", f"round 1 winner: {round1['winner_account_id']}"
    # Round 2 (in progress): SUB1 leading at +0.4 delta
    round2 = next((r for r in champ["rounds"] if r["round_id"] == 2), None)
    assert round2 is not None
    assert round2["in_progress"] is True
    assert round2["winner_account_id"] == "SUB1", f"round 2 winner: {round2['winner_account_id']}"
    assert champ["current_round_leader"] == "SUB1"


# ---- standalone runner (also reachable via `python3 -m canary.tests...`) -

def _main():
    """Standalone runner: no pytest, no fixtures. Used by manual `python3 ...`."""
    ex = _import_executor()
    tests = [
        ("terminal_json top-level keys", test_terminal_json_has_required_top_level_keys),
        ("terminal_json per-account live data", test_terminal_accounts_have_per_account_live_data),
        ("live_battle.json matches status_file", test_live_battle_json_matches_status_file),
        ("pairs match ALL_PAIRS", test_pairs_match_config),
        ("aggregate live PnL sums states", test_aggregate_live_pnl_sums_states),
        ("championship rounds crown top earner", test_championship_rounds_crown_top_earner),
    ]
    passes = 0
    fails = 0
    for name, fn in tests:
        with tempfile.TemporaryDirectory() as td:
            try:
                fn(ex=ex, tmp_path=Path(td))
                print(f"  PASS  {name}")
                passes += 1
            except AssertionError as e:
                print(f"  FAIL  {name} — {e}")
                fails += 1
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR {name} — {type(e).__name__}: {e}")
                fails += 1
    print(f"\nRESULT: {passes}/{passes + fails} passed · {fails} failed")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    _main()
