"""deploy_safety.py — atomic snapshot + rollback for live-battle deploys.

Used by canary/setup_live_battle.sh + canary/rollback_deploy.sh. Lives as a
Python module instead of inline bash so each function is unit-testable
without touching /root/canary or any systemd state.

CONTRACT:
  • snapshot()      — copy every deploy-mutable file into backups/pre-deploy-<ts>/.
                      Idempotent: missing source files are recorded as such, not
                      created.
  • validate_l99_clear() — refuses unless an explicit operator confirmation
                      token is provided. Records an audit event when allowed.
  • validate_keyfile_format() — refuses keys/secrets that don't match the
                      exact 32-hex / 64-hex Gate.io format.
  • rollback()      — restore every file from a backup directory, re-engage
                      L99 protection_halt, write a CRITICAL audit event.

No file in this module mutates canary_strategy.py, canary_config.json risk
caps, or the SHA256 lock. No new live agents introduced. No autonomous
behavior — every action is operator-initiated.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── File set covered by snapshot/rollback ────────────────────────────────
# Tuples of (relative_path, optional_dest_override).
# Each path is relative to the canary root (default /root/canary).
SNAPSHOT_FILES: tuple[str, ...] = (
    "canary_arm.json",
    ".api_key_main",
    ".api_key_sub1",
    ".api_key_sub2",
    "canary_executor.py",
    "canary_config.json",
)
# Files outside the canary root that need separate handling.
L99_HALT_PATH = Path("/root/.l99/protection_halt.json")
# Confirmation token required to clear the L99 halt.
# Not a password — a UI confirmation string typed by the operator into the
# workflow_dispatch form. Documented in DEPLOY_LIVE_BATTLE_AUDIT.md §5.
L99_CONFIRM_TOKEN = "YES"  # nosec B105 — confirmation token, not credential

# Exit codes used by setup_live_battle.sh — matched in tests.
EXIT_OK = 0
EXIT_MISSING_ENV = 64
EXIT_L99_REFUSED = 65
EXIT_PREFLIGHT_FAILED = 66
EXIT_SERVICE_FAILED = 67
EXIT_TELEMETRY_FAILED = 68


class DeploySafetyError(Exception):
    """Raised when a safety invariant is violated."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


# ── Helpers ──────────────────────────────────────────────────────────────


def _utc_ts() -> str:
    """Returns ISO-8601 UTC timestamp like '2026-05-20T19:00:00Z'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True))


# ── Snapshot ─────────────────────────────────────────────────────────────


@dataclass
class Snapshot:
    """A point-in-time copy of every deploy-mutable file."""

    backup_dir: Path
    ts: str
    workflow_run_id: str
    captured: dict[str, bool]  # filename → True if it existed at snapshot time

    def as_dict(self) -> dict:
        return {
            "ts": self.ts,
            "workflow_run_id": self.workflow_run_id,
            "backup_dir": str(self.backup_dir),
            "captured": self.captured,
        }


def snapshot(
    canary_dir: Path,
    backup_root: Path,
    workflow_run_id: str,
    ts: Optional[str] = None,
    l99_halt_path: Path = L99_HALT_PATH,
) -> Snapshot:
    """Capture every deploy-mutable file into backup_root/pre-deploy-<ts>/.

    NEVER touches the source files. Pure copy operation.
    Returns a Snapshot record that rollback() can later replay.
    """
    ts = ts or _utc_ts().replace(":", "").replace("-", "")
    backup_dir = backup_root / f"pre-deploy-{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    captured: dict[str, bool] = {}
    for rel in SNAPSHOT_FILES:
        src = canary_dir / rel
        if src.is_file():
            shutil.copy2(src, backup_dir / f"{rel}.bak")
            captured[rel] = True
        else:
            captured[rel] = False

    if l99_halt_path.is_file():
        shutil.copy2(l99_halt_path, backup_dir / "protection_halt.json.bak")
        captured["protection_halt.json"] = True
    else:
        captured["protection_halt.json"] = False

    # Pointer file so rollback_deploy.sh can find the latest snapshot.
    pointer = backup_root / ".latest-deploy-backup"
    pointer.write_text(str(backup_dir))

    # Manifest inside the backup itself for forensic value.
    snap = Snapshot(
        backup_dir=backup_dir,
        ts=ts,
        workflow_run_id=workflow_run_id,
        captured=captured,
    )
    _write_json(backup_dir / "manifest.json", snap.as_dict())
    return snap


# ── L99 governance ───────────────────────────────────────────────────────


def is_l99_engaged(l99_halt_path: Path = L99_HALT_PATH) -> bool:
    """True iff the L99 file exists AND its `halted` flag is true.

    Defensive: a missing or unreadable file is treated as not-engaged so a
    fresh install doesn't refuse to deploy. The executor's runtime check is
    the authoritative gate; this function just informs the deploy script.
    """
    if not l99_halt_path.is_file():
        return False
    try:
        data = json.loads(l99_halt_path.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    return bool(data.get("halted") is True)


def validate_l99_clear(
    confirm_token: Optional[str],
    workflow_run_id: str,
    audit_dir: Path,
    l99_halt_path: Path = L99_HALT_PATH,
    now_iso: Optional[str] = None,
) -> None:
    """Refuse to clear the L99 halt unless explicitly confirmed.

    Raises DeploySafetyError(EXIT_L99_REFUSED) if:
      - L99 file is present with halted:true, AND
      - confirm_token != "YES"

    When confirmed, rewrites the L99 file with halted:false, appends an
    entry to cleared_history, and writes an audit event. The file is never
    deleted (history is preserved).
    """
    if not is_l99_engaged(l99_halt_path):
        return  # nothing to clear

    if confirm_token != L99_CONFIRM_TOKEN:
        raise DeploySafetyError(
            f"L99 protection_halt is ENGAGED (halted:true). "
            f"Refusing to clear without explicit CONFIRM_CLEAR_L99=YES. "
            f"Re-run the workflow with confirm_clear_l99={L99_CONFIRM_TOKEN}.",
            exit_code=EXIT_L99_REFUSED,
        )

    now_iso = now_iso or _utc_ts()
    data = json.loads(l99_halt_path.read_text())
    data["halted"] = False
    history = data.setdefault("cleared_history", [])
    history.append(
        {
            "cleared_at": now_iso,
            "cleared_by_workflow_run_id": workflow_run_id,
            "reason_at_engage": data.get("reason", ""),
        }
    )
    l99_halt_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    audit_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        audit_dir / f"l99-cleared-{workflow_run_id}.json",
        {
            "event": "l99_halt_cleared",
            "ts": now_iso,
            "workflow_run_id": workflow_run_id,
            "explicit_operator_confirmation": True,
        },
    )


# ── Key/secret validation ────────────────────────────────────────────────


_HEX32 = re.compile(r"^[0-9a-fA-F]{32}$")
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def validate_keyfile_format(account: str, key: str, secret: str) -> None:
    """Refuse keys/secrets that don't match Gate.io's exact format.

    Raises DeploySafetyError on:
      - wrong length (key != 32 chars, secret != 64 chars)
      - non-hex characters

    These checks run BEFORE any disk write, so a malformed input never
    reaches /root/canary/.api_key_*. Key-equals-secret is structurally
    impossible once length validation passes (32 != 64), so we omit it.
    """
    if len(key) != 32:
        raise DeploySafetyError(
            f"{account} KEY length {len(key)} (expected 32 hex chars)"
        )
    if len(secret) != 64:
        raise DeploySafetyError(
            f"{account} SECRET length {len(secret)} (expected 64 hex chars)"
        )
    if not _HEX32.match(key):
        raise DeploySafetyError(
            f"{account} KEY must contain only 0-9 a-f (got non-hex chars)"
        )
    if not _HEX64.match(secret):
        raise DeploySafetyError(
            f"{account} SECRET must contain only 0-9 a-f (got non-hex chars)"
        )


# ── Rollback ─────────────────────────────────────────────────────────────


def rollback(
    backup_dir: Path,
    canary_dir: Path,
    audit_dir: Path,
    workflow_run_id: str,
    failure_reason: str,
    l99_halt_path: Path = L99_HALT_PATH,
    now_iso: Optional[str] = None,
) -> dict:
    """Restore canary_dir from a backup directory + re-engage L99.

    Behaviour:
      • For every SNAPSHOT_FILES entry: if the .bak file exists in
        backup_dir, copy it back to its canary_dir location with 0600
        permissions for keyfiles.
      • L99 halt is FORCIBLY engaged after restoration so the next deploy
        must explicitly clear it (governance: no quiet re-arm).
      • A CRITICAL audit event is written so the operator has a record.

    Returns a dict describing what was restored — useful for tests and
    for the operator-visible report.
    """
    now_iso = now_iso or _utc_ts()

    if not backup_dir.is_dir():
        raise DeploySafetyError(
            f"rollback target not found: {backup_dir}", exit_code=70
        )

    restored: list[str] = []
    skipped: list[str] = []
    for rel in SNAPSHOT_FILES:
        bak = backup_dir / f"{rel}.bak"
        dst = canary_dir / rel
        if bak.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bak, dst)
            if rel.startswith(".api_key_"):
                dst.chmod(0o600)
            restored.append(rel)
        else:
            # If the original didn't exist at snapshot time, ensure the
            # destination doesn't exist now either — prevents partial state.
            if dst.exists():
                dst.unlink()
            skipped.append(rel)

    # Restore L99 halt
    l99_bak = backup_dir / "protection_halt.json.bak"
    l99_halt_path.parent.mkdir(parents=True, exist_ok=True)
    if l99_bak.is_file():
        shutil.copy2(l99_bak, l99_halt_path)
    # Then OVERWRITE with our own engagement so the next deploy must
    # explicitly clear it. Preserve any cleared_history if the bak file had it.
    engagement = {
        "halted": True,
        "engaged_at": now_iso,
        "engaged_by": "deploy_rollback",
        "reason": f"DEPLOY_ROLLBACK_{workflow_run_id}_{failure_reason}",
        "prior_state_restored_from": str(backup_dir),
    }
    if l99_bak.is_file():
        try:
            prior = json.loads(l99_bak.read_text())
            if "cleared_history" in prior:
                engagement["cleared_history_at_snapshot"] = prior["cleared_history"]
        except (json.JSONDecodeError, OSError):
            pass
    l99_halt_path.write_text(json.dumps(engagement, indent=2, sort_keys=True))

    # Write CRITICAL audit event
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_event = {
        "event": "deploy_failed_rolled_back",
        "severity": "CRITICAL",
        "ts": now_iso,
        "workflow_run_id": workflow_run_id,
        "failure_reason": failure_reason,
        "backup_dir": str(backup_dir),
        "files_restored": restored,
        "files_skipped_missing_in_backup": skipped,
        "l99_halt_engaged": True,
        "operator_action_required": True,
    }
    _write_json(audit_dir / f"rollback-{workflow_run_id}.json", audit_event)
    return audit_event


# ── Audit ────────────────────────────────────────────────────────────────


def write_audit_event(audit_dir: Path, event: str, **fields) -> Path:
    """Append-style audit event writer.

    Filename is event-name-keyed so rollback / l99-clear / deploy-success
    each get distinct files. Existing files are NOT overwritten — instead,
    a numeric suffix is appended. This preserves history.
    """
    audit_dir.mkdir(parents=True, exist_ok=True)
    base = audit_dir / f"{event}.json"
    path = base
    n = 1
    while path.exists():
        path = audit_dir / f"{event}.{n}.json"
        n += 1
    payload = {"event": event, "ts": _utc_ts(), **fields}
    _write_json(path, payload)
    return path


# ── Public API surface ──────────────────────────────────────────────────


__all__ = [
    "Snapshot",
    "snapshot",
    "is_l99_engaged",
    "validate_l99_clear",
    "validate_keyfile_format",
    "rollback",
    "write_audit_event",
    "DeploySafetyError",
    "SNAPSHOT_FILES",
    "L99_HALT_PATH",
    "L99_CONFIRM_TOKEN",
    "EXIT_OK",
    "EXIT_MISSING_ENV",
    "EXIT_L99_REFUSED",
    "EXIT_PREFLIGHT_FAILED",
    "EXIT_SERVICE_FAILED",
    "EXIT_TELEMETRY_FAILED",
]
