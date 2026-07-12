"""Unit tests for canary/deploy_safety.py.

Covers the safety invariants required by PR #50 (Atomic Deploy Rollback Safety):

  • Snapshot captures every deploy-mutable file (or records its absence).
  • Rollback restores files + re-engages L99 + writes a CRITICAL audit event.
  • L99 halt clearing requires explicit operator confirmation.
  • Keyfile format is validated BEFORE any disk write.
  • Each failure-mode listed in the PR command has a corresponding test.

Run via pytest:
    pytest canary/tests/test_deploy_safety.py

Or standalone:
    python3 canary/tests/test_deploy_safety.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SAFETY_FILE = HERE.parent / "deploy_safety.py"


def _import_safety():
    spec = importlib.util.spec_from_file_location("deploy_safety", SAFETY_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SAFETY_FILE}")
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules BEFORE exec — dataclass introspection
    # looks up the module from sys.modules at decorator time.
    sys.modules["deploy_safety"] = mod
    spec.loader.exec_module(mod)
    return mod


ds = _import_safety()


# ── Fixtures ─────────────────────────────────────────────────────────────


def _make_canary_dir(tmp: Path, *, with_arm: bool = True, with_keys: bool = True) -> Path:
    """Build a fake /root/canary tree under tmp/."""
    canary = tmp / "canary"
    canary.mkdir(parents=True, exist_ok=True)
    (canary / "runtime").mkdir(exist_ok=True)
    if with_arm:
        (canary / "canary_arm.json").write_text(
            json.dumps(
                {
                    "armed_by": "test",
                    "armed_at": "2026-05-20T00:00:00Z",
                    "paper_preflight_passed": True,
                }
            )
        )
    if with_keys:
        # Realistic-shaped values: 32-hex KEY + 64-hex SECRET
        k = "a" * 32
        s = "b" * 64
        for acc in ("main", "sub1", "sub2"):
            (canary / f".api_key_{acc}").write_text(f"{k}:{s}")
            (canary / f".api_key_{acc}").chmod(0o600)
    # Touch executor + config so they're captured by snapshot
    (canary / "canary_executor.py").write_text("# pretend executor\n")
    (canary / "canary_config.json").write_text('{"accounts": {}}')
    return canary


def _make_l99(tmp: Path, halted: bool = True) -> Path:
    """Build a fake /root/.l99/protection_halt.json under tmp/."""
    l99_dir = tmp / "l99"
    l99_dir.mkdir(exist_ok=True)
    p = l99_dir / "protection_halt.json"
    p.write_text(
        json.dumps(
            {
                "halted": halted,
                "engaged_at": "2026-05-12T06:51:00Z",
                "reason": "OPERATOR_EMERGENCY_STOP_2026-05-12",
            }
        )
    )
    return p


# ── Snapshot tests ──────────────────────────────────────────────────────


def test_snapshot_captures_all_files_when_present(tmp_path: Path) -> None:
    canary = _make_canary_dir(tmp_path)
    l99 = _make_l99(tmp_path, halted=True)
    backup_root = tmp_path / "backups"

    snap = ds.snapshot(
        canary_dir=canary,
        backup_root=backup_root,
        workflow_run_id="test-run-1",
        ts="20260520T000000Z",
        l99_halt_path=l99,
    )

    # Every snapshot file present in canary should be captured
    for rel in ds.SNAPSHOT_FILES:
        assert snap.captured[rel] is True, f"missed: {rel}"
        assert (snap.backup_dir / f"{rel}.bak").is_file()
    # L99 captured separately
    assert snap.captured["protection_halt.json"] is True
    assert (snap.backup_dir / "protection_halt.json.bak").is_file()
    # Pointer file exists
    pointer = backup_root / ".latest-deploy-backup"
    assert pointer.is_file()
    assert pointer.read_text() == str(snap.backup_dir)
    # Manifest exists
    manifest = json.loads((snap.backup_dir / "manifest.json").read_text())
    assert manifest["workflow_run_id"] == "test-run-1"
    assert manifest["backup_dir"] == str(snap.backup_dir)


def test_snapshot_records_absence_of_missing_files(tmp_path: Path) -> None:
    """A first-time deploy has no arm/halt/keys yet. Snapshot must record
    that fact, not invent placeholder files."""
    canary = _make_canary_dir(tmp_path, with_arm=False, with_keys=False)
    (canary / "canary_executor.py").unlink()  # also remove this
    backup_root = tmp_path / "backups"
    l99 = tmp_path / "l99" / "no_such_file.json"  # explicitly missing

    snap = ds.snapshot(
        canary_dir=canary,
        backup_root=backup_root,
        workflow_run_id="test-run-2",
        l99_halt_path=l99,
    )

    assert snap.captured["canary_arm.json"] is False
    assert snap.captured[".api_key_main"] is False
    assert snap.captured["canary_executor.py"] is False
    assert snap.captured["protection_halt.json"] is False
    # No .bak files were created for missing inputs
    assert not (snap.backup_dir / "canary_arm.json.bak").exists()


def test_snapshot_pointer_updates_on_subsequent_snapshots(tmp_path: Path) -> None:
    canary = _make_canary_dir(tmp_path)
    backup_root = tmp_path / "backups"
    l99 = _make_l99(tmp_path, halted=False)

    s1 = ds.snapshot(canary, backup_root, "run-1", ts="20260520T100000Z", l99_halt_path=l99)
    s2 = ds.snapshot(canary, backup_root, "run-2", ts="20260520T110000Z", l99_halt_path=l99)

    assert s1.backup_dir != s2.backup_dir
    assert (backup_root / ".latest-deploy-backup").read_text() == str(s2.backup_dir)
    # First snapshot still preserved on disk for forensic value
    assert s1.backup_dir.is_dir()


# ── L99 governance tests ────────────────────────────────────────────────


def test_l99_clear_refused_without_confirmation(tmp_path: Path) -> None:
    """SIMULATES: operator triggers deploy while L99 is engaged but forgot
    to pass CONFIRM_CLEAR_L99=YES. Must refuse, no mutation."""
    l99 = _make_l99(tmp_path, halted=True)
    audit_dir = tmp_path / "audit"

    try:
        ds.validate_l99_clear(
            confirm_token=None,
            workflow_run_id="run-no-confirm",
            audit_dir=audit_dir,
            l99_halt_path=l99,
        )
    except ds.DeploySafetyError as e:
        assert e.exit_code == ds.EXIT_L99_REFUSED
    else:
        raise AssertionError("expected DeploySafetyError when L99 engaged without confirm")

    # File unchanged
    data = json.loads(l99.read_text())
    assert data["halted"] is True
    # No audit event written
    assert not audit_dir.exists() or not any(audit_dir.iterdir())


def test_l99_clear_refused_with_wrong_token(tmp_path: Path) -> None:
    l99 = _make_l99(tmp_path, halted=True)
    audit_dir = tmp_path / "audit"

    for token in ("yes", "Y", "YEs", "1", "true"):
        try:
            ds.validate_l99_clear(
                confirm_token=token,
                workflow_run_id=f"run-{token}",
                audit_dir=audit_dir,
                l99_halt_path=l99,
            )
        except ds.DeploySafetyError as e:
            assert e.exit_code == ds.EXIT_L99_REFUSED, f"token={token!r}"
        else:
            raise AssertionError(f"expected refusal for token={token!r}")
    assert json.loads(l99.read_text())["halted"] is True  # unchanged


def test_l99_clear_succeeds_with_explicit_yes(tmp_path: Path) -> None:
    l99 = _make_l99(tmp_path, halted=True)
    audit_dir = tmp_path / "audit"

    ds.validate_l99_clear(
        confirm_token="YES",
        workflow_run_id="run-explicit-yes",
        audit_dir=audit_dir,
        l99_halt_path=l99,
        now_iso="2026-05-20T19:00:00Z",
    )

    data = json.loads(l99.read_text())
    assert data["halted"] is False
    assert "cleared_history" in data
    assert len(data["cleared_history"]) == 1
    entry = data["cleared_history"][0]
    assert entry["cleared_by_workflow_run_id"] == "run-explicit-yes"
    assert entry["cleared_at"] == "2026-05-20T19:00:00Z"
    assert entry["reason_at_engage"] == "OPERATOR_EMERGENCY_STOP_2026-05-12"

    # Audit event written
    audit_files = list(audit_dir.glob("l99-cleared-*.json"))
    assert len(audit_files) == 1
    event = json.loads(audit_files[0].read_text())
    assert event["event"] == "l99_halt_cleared"
    assert event["explicit_operator_confirmation"] is True


def test_l99_clear_noop_when_not_engaged(tmp_path: Path) -> None:
    l99 = _make_l99(tmp_path, halted=False)
    audit_dir = tmp_path / "audit"

    # No token required when nothing is engaged
    ds.validate_l99_clear(
        confirm_token=None,
        workflow_run_id="run-noop",
        audit_dir=audit_dir,
        l99_halt_path=l99,
    )
    data = json.loads(l99.read_text())
    assert data["halted"] is False  # unchanged
    assert "cleared_history" not in data  # noop, not a clearing event


def test_l99_clear_noop_when_file_missing(tmp_path: Path) -> None:
    l99 = tmp_path / "no_such_file.json"
    audit_dir = tmp_path / "audit"

    ds.validate_l99_clear(
        confirm_token=None,
        workflow_run_id="run-no-file",
        audit_dir=audit_dir,
        l99_halt_path=l99,
    )
    assert not l99.exists()


# ── Keyfile validation tests ────────────────────────────────────────────


def test_keyfile_validation_accepts_correct_format() -> None:
    ds.validate_keyfile_format("MAIN", "a" * 32, "b" * 64)  # no raise
    ds.validate_keyfile_format("SUB1", "0" * 32, "f" * 64)
    ds.validate_keyfile_format("SUB2", "ABCDEF" + "0" * 26, "0123456789" + "a" * 54)


def test_keyfile_validation_rejects_short_key() -> None:
    """SIMULATES: invalid API secret — short key from paste truncation."""
    try:
        ds.validate_keyfile_format("MAIN", "a" * 31, "b" * 64)
    except ds.DeploySafetyError as e:
        assert "KEY length 31" in str(e)
    else:
        raise AssertionError("expected DeploySafetyError for short KEY")


def test_keyfile_validation_rejects_long_key() -> None:
    try:
        ds.validate_keyfile_format("SUB2", "a" * 33, "b" * 64)
    except ds.DeploySafetyError as e:
        assert "KEY length 33" in str(e)
    else:
        raise AssertionError("expected DeploySafetyError for long KEY")


def test_keyfile_validation_rejects_short_secret() -> None:
    try:
        ds.validate_keyfile_format("MAIN", "a" * 32, "b" * 63)
    except ds.DeploySafetyError as e:
        assert "SECRET length 63" in str(e)
    else:
        raise AssertionError("expected DeploySafetyError for short SECRET")


def test_keyfile_validation_rejects_non_hex() -> None:
    """SIMULATES: paste error introduced a non-hex character."""
    try:
        ds.validate_keyfile_format("MAIN", "z" + "a" * 31, "b" * 64)
    except ds.DeploySafetyError as e:
        assert "non-hex" in str(e).lower()
    else:
        raise AssertionError("expected DeploySafetyError for non-hex KEY")

    try:
        ds.validate_keyfile_format("SUB1", "a" * 32, "Q" + "b" * 63)
    except ds.DeploySafetyError as e:
        assert "non-hex" in str(e).lower()
    else:
        raise AssertionError("expected DeploySafetyError for non-hex SECRET")


# ── Rollback tests ──────────────────────────────────────────────────────


def test_rollback_restores_all_captured_files(tmp_path: Path) -> None:
    canary = _make_canary_dir(tmp_path)
    l99 = _make_l99(tmp_path, halted=True)
    backup_root = tmp_path / "backups"
    audit_dir = tmp_path / "audit"

    snap = ds.snapshot(canary, backup_root, "run-rollback", l99_halt_path=l99)

    # Simulate a destructive partial deploy: overwrite arm + a keyfile
    (canary / "canary_arm.json").write_text('{"corrupted": true}')
    (canary / ".api_key_main").write_text("BROKEN")

    result = ds.rollback(
        backup_dir=snap.backup_dir,
        canary_dir=canary,
        audit_dir=audit_dir,
        workflow_run_id="run-rollback",
        failure_reason="simulated_partial_deploy",
        l99_halt_path=l99,
        now_iso="2026-05-20T19:30:00Z",
    )

    # Files restored
    assert "canary_arm.json" in result["files_restored"]
    assert ".api_key_main" in result["files_restored"]
    # Arm content matches original
    arm = json.loads((canary / "canary_arm.json").read_text())
    assert arm["armed_by"] == "test"
    # Keyfile content + permissions restored
    keyfile = canary / ".api_key_main"
    assert keyfile.read_text() == "a" * 32 + ":" + "b" * 64
    assert (keyfile.stat().st_mode & 0o777) == 0o600


def test_rollback_engages_l99_after_restore(tmp_path: Path) -> None:
    canary = _make_canary_dir(tmp_path)
    l99 = _make_l99(tmp_path, halted=False)  # not engaged at snapshot time
    backup_root = tmp_path / "backups"
    audit_dir = tmp_path / "audit"

    snap = ds.snapshot(canary, backup_root, "run-engages-l99", l99_halt_path=l99)
    ds.rollback(
        backup_dir=snap.backup_dir,
        canary_dir=canary,
        audit_dir=audit_dir,
        workflow_run_id="run-engages-l99",
        failure_reason="service_failed_to_start",
        l99_halt_path=l99,
    )

    # L99 is forcibly engaged regardless of pre-snapshot state
    data = json.loads(l99.read_text())
    assert data["halted"] is True
    assert data["engaged_by"] == "deploy_rollback"
    assert "DEPLOY_ROLLBACK_run-engages-l99" in data["reason"]


def test_rollback_writes_critical_audit_event(tmp_path: Path) -> None:
    canary = _make_canary_dir(tmp_path)
    l99 = _make_l99(tmp_path, halted=True)
    backup_root = tmp_path / "backups"
    audit_dir = tmp_path / "audit"

    snap = ds.snapshot(canary, backup_root, "run-audit", l99_halt_path=l99)
    result = ds.rollback(
        backup_dir=snap.backup_dir,
        canary_dir=canary,
        audit_dir=audit_dir,
        workflow_run_id="run-audit",
        failure_reason="auth_check_failed_MAIN",
        l99_halt_path=l99,
        now_iso="2026-05-20T19:45:00Z",
    )

    assert result["severity"] == "CRITICAL"
    assert result["operator_action_required"] is True
    assert result["l99_halt_engaged"] is True

    event_file = audit_dir / "rollback-run-audit.json"
    assert event_file.is_file()
    event = json.loads(event_file.read_text())
    assert event["event"] == "deploy_failed_rolled_back"
    assert event["severity"] == "CRITICAL"
    assert event["failure_reason"] == "auth_check_failed_MAIN"


def test_rollback_removes_destinations_for_files_missing_in_backup(tmp_path: Path) -> None:
    """If a file didn't exist at snapshot time but exists now (e.g. a
    partial write created it), rollback must remove it — otherwise the
    rollback leaves a partial state behind."""
    canary = _make_canary_dir(tmp_path, with_arm=False)
    l99 = _make_l99(tmp_path, halted=False)
    backup_root = tmp_path / "backups"
    audit_dir = tmp_path / "audit"

    snap = ds.snapshot(canary, backup_root, "run-no-arm", l99_halt_path=l99)
    assert snap.captured["canary_arm.json"] is False

    # Now simulate the deploy creating a partial arm file
    (canary / "canary_arm.json").write_text('{"partial": "deploy"}')
    assert (canary / "canary_arm.json").is_file()

    ds.rollback(
        backup_dir=snap.backup_dir,
        canary_dir=canary,
        audit_dir=audit_dir,
        workflow_run_id="run-no-arm-rollback",
        failure_reason="restart_failed",
        l99_halt_path=l99,
    )

    # Partial arm file is gone — no partial state survives rollback
    assert not (canary / "canary_arm.json").exists()


def test_rollback_raises_on_missing_backup(tmp_path: Path) -> None:
    canary = _make_canary_dir(tmp_path)
    l99 = _make_l99(tmp_path)
    audit_dir = tmp_path / "audit"

    try:
        ds.rollback(
            backup_dir=tmp_path / "no_such_backup",
            canary_dir=canary,
            audit_dir=audit_dir,
            workflow_run_id="run-bad-backup",
            failure_reason="test",
            l99_halt_path=l99,
        )
    except ds.DeploySafetyError as e:
        assert "not found" in str(e).lower()
    else:
        raise AssertionError("expected DeploySafetyError for missing backup")


# ── End-to-end failure-mode tests (PR command lists these explicitly) ────


def test_simulated_invalid_api_secret_blocks_before_disk_write(tmp_path: Path) -> None:
    """PR command failure mode: 'invalid API secret'.

    Validates that validate_keyfile_format() catches it BEFORE the keyfile
    is written. The disk write would have followed validation in
    setup_live_battle.sh."""
    bad_secret = "b" * 63  # one char short
    try:
        ds.validate_keyfile_format("MAIN", "a" * 32, bad_secret)
    except ds.DeploySafetyError:
        pass  # expected — disk write never happens
    else:
        raise AssertionError("invalid secret should have raised")


def test_simulated_partial_secret_write_recovers_via_rollback(tmp_path: Path) -> None:
    """PR command failure mode: 'partial secret write'.

    Snapshot captures the old key, deploy starts overwriting, fails on
    SUB2, rollback restores all 3 to pre-deploy state."""
    canary = _make_canary_dir(tmp_path)
    original_sub2 = (canary / ".api_key_sub2").read_text()
    l99 = _make_l99(tmp_path, halted=False)
    backup_root = tmp_path / "backups"
    audit_dir = tmp_path / "audit"

    snap = ds.snapshot(canary, backup_root, "run-partial", l99_halt_path=l99)

    # Simulate: MAIN + SUB1 written successfully, SUB2 write got garbage
    (canary / ".api_key_main").write_text("c" * 32 + ":" + "d" * 64)
    (canary / ".api_key_sub1").write_text("e" * 32 + ":" + "f" * 64)
    (canary / ".api_key_sub2").write_text("PARTIAL_WRITE_GARBAGE")

    ds.rollback(
        backup_dir=snap.backup_dir,
        canary_dir=canary,
        audit_dir=audit_dir,
        workflow_run_id="run-partial",
        failure_reason="partial_secret_write",
        l99_halt_path=l99,
    )

    # All 3 restored to pre-deploy state
    assert (canary / ".api_key_main").read_text() == "a" * 32 + ":" + "b" * 64
    assert (canary / ".api_key_sub1").read_text() == "a" * 32 + ":" + "b" * 64
    assert (canary / ".api_key_sub2").read_text() == original_sub2


def test_simulated_restart_failure_engages_l99(tmp_path: Path) -> None:
    """PR command failure mode: 'restart failure'.

    Rollback after a restart failure must engage L99 so the operator must
    consciously re-clear it before another deploy attempts."""
    canary = _make_canary_dir(tmp_path)
    l99 = _make_l99(tmp_path, halted=False)  # not engaged before deploy
    backup_root = tmp_path / "backups"
    audit_dir = tmp_path / "audit"

    snap = ds.snapshot(canary, backup_root, "run-restart-fail", l99_halt_path=l99)
    ds.rollback(
        backup_dir=snap.backup_dir,
        canary_dir=canary,
        audit_dir=audit_dir,
        workflow_run_id="run-restart-fail",
        failure_reason="systemctl_restart_failed",
        l99_halt_path=l99,
    )
    # L99 now engaged — next deploy must explicitly clear
    assert json.loads(l99.read_text())["halted"] is True


def test_simulated_auth_failure_full_recovery(tmp_path: Path) -> None:
    """PR command failure mode: 'auth failure' + 'rollback recovery'.

    End-to-end: snapshot → partial deploy → simulated auth fail → rollback →
    confirm everything is back."""
    canary = _make_canary_dir(tmp_path)
    l99 = _make_l99(tmp_path, halted=True)  # was engaged before deploy
    backup_root = tmp_path / "backups"
    audit_dir = tmp_path / "audit"

    original_arm = (canary / "canary_arm.json").read_text()
    original_keyfile_main = (canary / ".api_key_main").read_text()

    snap = ds.snapshot(canary, backup_root, "run-auth-fail", l99_halt_path=l99)

    # operator cleared L99
    ds.validate_l99_clear(
        confirm_token="YES",
        workflow_run_id="run-auth-fail",
        audit_dir=audit_dir,
        l99_halt_path=l99,
    )
    assert json.loads(l99.read_text())["halted"] is False

    # deploy proceeded, wrote keyfiles, then auth check failed
    (canary / "canary_arm.json").write_text('{"new_arm": "true"}')
    (canary / ".api_key_main").write_text("z" * 32 + ":" + "y" * 64)

    # rollback fires
    ds.rollback(
        backup_dir=snap.backup_dir,
        canary_dir=canary,
        audit_dir=audit_dir,
        workflow_run_id="run-auth-fail",
        failure_reason="post_deploy_auth_check_MAIN_failed",
        l99_halt_path=l99,
    )

    # Arm + keyfile restored to pre-deploy values
    assert (canary / "canary_arm.json").read_text() == original_arm
    assert (canary / ".api_key_main").read_text() == original_keyfile_main
    # L99 re-engaged
    assert json.loads(l99.read_text())["halted"] is True
    # CRITICAL audit event written
    assert (audit_dir / "rollback-run-auth-fail.json").is_file()


# ── setup_live_battle.sh structural invariant (regression test for TEST A bug) ────


def test_setup_script_runs_l99_check_before_trap_install() -> None:
    """REGRESSION (TEST A bug): The L99 governance check must run BEFORE the
    bash `trap rollback_on_error ERR INT TERM` is installed. Otherwise an
    L99 refusal triggers the rollback trap → service is stopped → audit
    log shows CRITICAL rollback even though no mutation occurred.

    The refusal path must be PURE: no snapshot, no trap, no service stop,
    no rollback. This test enforces that by reading the bash script and
    asserting the line order.
    """
    repo_root = HERE.parent.parent
    script = (repo_root / "canary" / "setup_live_battle.sh").read_text()
    lines = script.splitlines()

    # Find the line numbers of:
    #   • the `validate_l99_clear(` call (governance gate)
    #   • the `trap rollback_on_error` install
    #   • the `from deploy_safety import snapshot` (snapshot import inside heredoc)
    l99_line = next(
        (i for i, line in enumerate(lines) if "validate_l99_clear(" in line),
        None,
    )
    trap_line = next(
        (i for i, line in enumerate(lines)
         if line.strip().startswith("trap rollback_on_error")),
        None,
    )
    snapshot_line = next(
        (i for i, line in enumerate(lines)
         if "from deploy_safety import snapshot" in line),
        None,
    )

    assert l99_line is not None, "validate_l99_clear() call not found in setup_live_battle.sh"
    assert trap_line is not None, "trap rollback_on_error not found in setup_live_battle.sh"
    assert snapshot_line is not None, "snapshot import not found in setup_live_battle.sh"

    # The invariant: L99 check happens BEFORE both the snapshot and the trap.
    assert l99_line < snapshot_line, (
        f"L99 check (line {l99_line + 1}) must run BEFORE snapshot "
        f"(line {snapshot_line + 1}). A refusal path that mutates "
        f"runtime state is a governance violation."
    )
    assert l99_line < trap_line, (
        f"L99 check (line {l99_line + 1}) must run BEFORE trap "
        f"(line {trap_line + 1}). Otherwise an L99 refusal triggers "
        f"the rollback trap unnecessarily — TEST A regression."
    )


def test_setup_script_l99_phase_is_numbered_first() -> None:
    """The phase marker for the L99 check must read [1/8], not [2/8].
    This is a documentation invariant — operators reading the run output
    should see governance as the first gate, not the second."""
    repo_root = HERE.parent.parent
    script = (repo_root / "canary" / "setup_live_battle.sh").read_text()
    lines = script.splitlines()

    l99_phase = next(
        (line for line in lines
         if "L99 governance" in line and "echo " in line and "[" in line),
        None,
    )
    assert l99_phase is not None, "L99 phase echo not found"
    assert "[1/8]" in l99_phase, (
        f"L99 phase must be [1/8] (gate first), got: {l99_phase.strip()}"
    )


# ── Audit event helper ──────────────────────────────────────────────────


# ── canary_executor exit-code semantics (auto-restart correctness) ──────


def _import_executor():
    """Import canary_executor without running main() — used to test the
    signal-received tracking + exit-code-decision logic in isolation."""
    import importlib.util
    import sys as _sys
    exec_path = HERE.parent / "canary_executor.py"
    spec = importlib.util.spec_from_file_location("canary_executor", exec_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {exec_path}")
    mod = importlib.util.module_from_spec(spec)
    _sys.modules["canary_executor"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_executor_defaults_to_signal_not_received() -> None:
    """Fresh import: _signal_received must default False so the exit-99
    path fires unless a SIGTERM/SIGINT actually flipped the flag."""
    ex = _import_executor()
    assert ex._signal_received is False


def test_signal_handler_flips_received_flag() -> None:
    """Calling _sig (the SIGTERM/SIGINT handler) must set _signal_received
    True so main()'s exit decision goes to exit 0 (clean operator stop)."""
    ex = _import_executor()
    # Reset state in case the module is cached
    ex._signal_received = False
    ex._shutdown.clear()
    assert ex._signal_received is False
    ex._sig(None, None)
    assert ex._signal_received is True
    assert ex._shutdown.is_set() is True


def test_executor_signal_received_is_module_level_global() -> None:
    """The flag must be a module-level Python global (not e.g. a per-
    thread or per-function variable), so the signal handler running on
    the main thread and the exit-decision at end of main() see the same
    value. Defensive — catches regressions where someone refactors it
    into a nested scope by accident."""
    ex = _import_executor()
    assert "_signal_received" in vars(ex), \
        "_signal_received must live at module scope of canary_executor"
    # It must also be tracked by the signal handler — not just read.
    import inspect
    src = inspect.getsource(ex._sig)
    assert "global _signal_received" in src, \
        "_sig must declare `global _signal_received` to mutate the flag"
    assert "_signal_received = True" in src, \
        "_sig must set _signal_received to True on signal receipt"


def test_executor_main_exits_99_when_no_signal_received() -> None:
    """Static structural test: the main() function's exit decision must
    call sys.exit(99) when _signal_received is False. Catches regressions
    where someone removes the auto-restart trigger."""
    exec_text = (HERE.parent / "canary_executor.py").read_text()
    # The exit-99 line must appear in main() after the join loop.
    assert "sys.exit(99)" in exec_text, \
        "main() must call sys.exit(99) on halt-induced shutdown"
    # And it must be guarded by `if not _signal_received:` so that
    # operator-initiated SIGTERM still exits cleanly with code 0.
    assert "if not _signal_received:" in exec_text, \
        "exit(99) must be guarded by `if not _signal_received:`"


# ── audit history ───────────────────────────────────────────────────────


def test_write_audit_event_preserves_history(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    p1 = ds.write_audit_event(audit_dir, "deploy_success", workflow_run_id="run-1")
    p2 = ds.write_audit_event(audit_dir, "deploy_success", workflow_run_id="run-2")
    p3 = ds.write_audit_event(audit_dir, "deploy_success", workflow_run_id="run-3")

    assert p1 == audit_dir / "deploy_success.json"
    assert p2 == audit_dir / "deploy_success.1.json"
    assert p3 == audit_dir / "deploy_success.2.json"
    assert json.loads(p1.read_text())["workflow_run_id"] == "run-1"
    assert json.loads(p3.read_text())["workflow_run_id"] == "run-3"


# ── Standalone runner ──────────────────────────────────────────────────


def _main() -> int:
    tests = [
        # snapshot
        test_snapshot_captures_all_files_when_present,
        test_snapshot_records_absence_of_missing_files,
        test_snapshot_pointer_updates_on_subsequent_snapshots,
        # L99 governance
        test_l99_clear_refused_without_confirmation,
        test_l99_clear_refused_with_wrong_token,
        test_l99_clear_succeeds_with_explicit_yes,
        test_l99_clear_noop_when_not_engaged,
        test_l99_clear_noop_when_file_missing,
        # keyfile validation
        test_keyfile_validation_accepts_correct_format,
        test_keyfile_validation_rejects_short_key,
        test_keyfile_validation_rejects_long_key,
        test_keyfile_validation_rejects_short_secret,
        test_keyfile_validation_rejects_non_hex,
        # rollback
        test_rollback_restores_all_captured_files,
        test_rollback_engages_l99_after_restore,
        test_rollback_writes_critical_audit_event,
        test_rollback_removes_destinations_for_files_missing_in_backup,
        test_rollback_raises_on_missing_backup,
        # simulated PR-listed failure modes
        test_simulated_invalid_api_secret_blocks_before_disk_write,
        test_simulated_partial_secret_write_recovers_via_rollback,
        test_simulated_restart_failure_engages_l99,
        test_simulated_auth_failure_full_recovery,
        # script structural invariants (TEST A regression)
        test_setup_script_runs_l99_check_before_trap_install,
        test_setup_script_l99_phase_is_numbered_first,
        # executor exit-code semantics (auto-restart correctness)
        test_executor_defaults_to_signal_not_received,
        test_signal_handler_flips_received_flag,
        test_executor_signal_received_is_module_level_global,
        test_executor_main_exits_99_when_no_signal_received,
        # audit
        test_write_audit_event_preserves_history,
    ]
    passes = fails = 0
    for fn in tests:
        sig_params = fn.__code__.co_varnames[: fn.__code__.co_argcount]
        with tempfile.TemporaryDirectory() as td:
            try:
                if "tmp_path" in sig_params:
                    fn(Path(td))
                else:
                    fn()
                print(f"  PASS  {fn.__name__}")
                passes += 1
            except AssertionError as e:
                print(f"  FAIL  {fn.__name__} — {e}")
                fails += 1
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR {fn.__name__} — {type(e).__name__}: {e}")
                fails += 1
    print(f"\nRESULT: {passes}/{passes + fails} passed · {fails} failed")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(_main())
