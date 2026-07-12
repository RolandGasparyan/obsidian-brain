#!/bin/bash
# rollback_deploy.sh — manual rollback for the live battle.
#
# Restores the most recent pre-deploy snapshot, stops canary-battle.service,
# engages L99 halt, writes a CRITICAL audit event. Use when:
#   - A deploy succeeded but the resulting live state is misbehaving and
#     you want to revert to the previous keys/config without doing a new
#     deploy.
#   - The automatic rollback in setup_live_battle.sh didn't fire (e.g. the
#     SSH session died mid-deploy) and the VPS is in an inconsistent state.
#
# Usage:
#   /root/tradingguru-empire/canary/rollback_deploy.sh [reason]
#
# Arguments:
#   reason  — short string for the audit event. Default OPERATOR_MANUAL.
#
# Reads:
#   /root/canary/backups/.latest-deploy-backup → path of the snapshot dir
#
# Exits non-zero if:
#   - the pointer file does not exist (no snapshot to roll back to)
#   - the snapshot directory does not exist
#   - the safety module raises a DeploySafetyError

set -euo pipefail

CANARY_DIR=/root/canary
BACKUP_ROOT=$CANARY_DIR/backups
AUDIT_DIR=$CANARY_DIR/audit
L99_HALT=/root/.l99/protection_halt.json
REPO_DIR=/root/tradingguru-empire
PY="$CANARY_DIR/venv/bin/python3"

REASON="${1:-OPERATOR_MANUAL}"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
WORKFLOW_RUN_ID="manual-$(date +%s)"

POINTER=$BACKUP_ROOT/.latest-deploy-backup
if [ ! -f "$POINTER" ]; then
  echo "::error::No snapshot pointer at $POINTER. Has a deploy ever run?" >&2
  exit 1
fi
BACKUP_DIR=$(cat "$POINTER")
if [ ! -d "$BACKUP_DIR" ]; then
  echo "::error::Snapshot directory $BACKUP_DIR (from pointer) does not exist" >&2
  exit 1
fi

echo "════════════════════════════════════════════════════════════════"
echo "  🛑 MANUAL ROLLBACK"
echo "  reason:    $REASON"
echo "  ts:        $TS"
echo "  backup:    $BACKUP_DIR"
echo "  audit_dir: $AUDIT_DIR"
echo "════════════════════════════════════════════════════════════════"

# Stop the service BEFORE restoring files so the executor doesn't try to
# read mid-restore. If it's already stopped, this is a no-op.
systemctl stop canary-battle.service 2>&1 | head -3 || true

"$PY" - "$REASON" "$WORKFLOW_RUN_ID" "$BACKUP_DIR" <<PY
import sys
sys.path.insert(0, "$REPO_DIR/canary")
from deploy_safety import rollback, DeploySafetyError
from pathlib import Path

reason, run_id, backup_dir = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    result = rollback(
        backup_dir=Path(backup_dir),
        canary_dir=Path("$CANARY_DIR"),
        audit_dir=Path("$AUDIT_DIR"),
        workflow_run_id=run_id,
        failure_reason=reason,
        l99_halt_path=Path("$L99_HALT"),
    )
except DeploySafetyError as e:
    print(f"::error::{e}")
    sys.exit(e.exit_code if hasattr(e, "exit_code") else 1)
print()
print("─── ROLLBACK SUMMARY ───")
print(f"Files restored:                 {result['files_restored']}")
print(f"Files skipped (no .bak in snap): {result['files_skipped_missing_in_backup']}")
print(f"L99 halt engaged:               {result['l99_halt_engaged']}")
PY

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  POST-ROLLBACK CHECKLIST"
echo "════════════════════════════════════════════════════════════════"
echo "  1. Verify no open positions are stranded on Gate.io (UI check)"
echo "  2. Read the audit event at $AUDIT_DIR/rollback-$WORKFLOW_RUN_ID.json"
echo "  3. Decide whether to re-deploy (will refuse until L99 is explicitly"
echo "     cleared by passing CONFIRM_CLEAR_L99=YES to the next deploy)"
echo "  4. Service is STOPPED — do not assume it's running"
echo "════════════════════════════════════════════════════════════════"
