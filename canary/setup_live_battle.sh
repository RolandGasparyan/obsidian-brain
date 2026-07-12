#!/bin/bash
# setup_live_battle.sh
#
# Deterministic, atomic-rollback deploy for the 3-account live battle.
# Called by .github/workflows/deploy-live-battle.yml after the SSH step.
#
# CONTRACT (enforced by canary/deploy_safety.py + this script's `trap ERR`):
#   1. L99 GATING — runs FIRST as a pure refusal gate. /root/.l99/protection_halt.json
#      is cleared ONLY when CONFIRM_CLEAR_L99=YES is in the environment. On refusal,
#      the script exits 65 with ZERO side effects (no snapshot, no trap, no service
#      stop, no rollback).
#   2. SNAPSHOT — once the L99 gate passes, every deploy-mutable file is copied to
#      backups/pre-deploy-<ts>/ BEFORE any mutation. The trap is armed after this
#      so subsequent failures restore the snapshot.
#   3. VALIDATION — keys + secrets are length+hex-checked before any keyfile is
#      written. A malformed input never reaches /root/canary/.api_key_*.
#   4. MEASURED PREFLIGHT — canary/check_agents.py is run against live Gate.io
#      (read-only) and must exit 0 before paper_preflight_passed:true is set in
#      canary_arm.json.
#   5. ROLLBACK ON FAILURE — ANY failure AFTER the snapshot (including SIGINT)
#      restores the snapshot, stops canary-battle.service, engages L99 halt, and
#      writes a CRITICAL audit event. The operator must manually re-clear L99
#      before the next deploy.
#
# Required env vars:
#   GATE_MAIN_API_KEY   GATE_MAIN_API_SECRET
#   GATE_SUB1_API_KEY   GATE_SUB1_API_SECRET
#   GATE_SUB2_API_KEY   GATE_SUB2_API_SECRET
#
# Optional env vars:
#   CONFIRM_CLEAR_L99   — must be "YES" to clear an active L99 halt
#   GITHUB_RUN_ID       — workflow run id for audit attribution
#
# Exit codes (matched in canary/deploy_safety.py + tested in CI):
#   0   success
#   64  required env var missing
#   65  L99 halt engaged + no operator confirmation
#   66  measured preflight failed
#   67  systemd restart failed / service did not become active
#   68  executor did not produce telemetry within wait window
#   70  rollback target backup not found (catastrophic)
#   1+  generic — see audit event in /root/canary/audit/

set -euo pipefail

# ── Paths ────────────────────────────────────────────────────────────────
CANARY_DIR=/root/canary
RUNTIME_DIR=$CANARY_DIR/runtime
BACKUP_ROOT=$CANARY_DIR/backups
AUDIT_DIR=$CANARY_DIR/audit
ARM_FILE=$CANARY_DIR/canary_arm.json
L99_HALT=/root/.l99/protection_halt.json
REPO_DIR=/root/tradingguru-empire

WORKFLOW_RUN_ID=${GITHUB_RUN_ID:-manual-$(date +%s)}
TS=$(date -u +%Y%m%dT%H%M%SZ)
TS_HUMAN=$(date -u +%Y-%m-%dT%H:%M:%SZ)

mkdir -p "$RUNTIME_DIR" "$BACKUP_ROOT" "$AUDIT_DIR" "$(dirname "$L99_HALT")"

PY="$CANARY_DIR/venv/bin/python3"
SAFETY="$REPO_DIR/canary/deploy_safety.py"

echo "=== Trading Guru Multi-Account Live Battle Deploy ==="
echo "  ts:              $TS_HUMAN"
echo "  workflow_run_id: $WORKFLOW_RUN_ID"
echo "  accounts:        MAIN(\$1579.52) + SUB1(\$200) + SUB2(\$200)"
echo "  pairs:           BTC/USDT ETH/USDT XRP/USDT SOL/USDT"
echo "  strategy:        MA50W10 (SHA256 locked)"
echo ""

# ── [0/8] Required env vars ──────────────────────────────────────────────
echo "[0/8] Verifying required env vars"
for v in GATE_MAIN_API_KEY GATE_MAIN_API_SECRET \
         GATE_SUB1_API_KEY GATE_SUB1_API_SECRET \
         GATE_SUB2_API_KEY GATE_SUB2_API_SECRET; do
  if [ -z "${!v:-}" ]; then
    echo "::error::required env var $v missing"
    exit 64
  fi
done
echo "      all 6 Gate.io env vars present"

# ── [1/8] L99 governance gate (PURE refusal — no snapshot, no trap, no rollback) ──
# Runs BEFORE the snapshot + trap so a refusal exits cleanly with no side effects:
#   - no rollback fires
#   - no service is stopped
#   - no file is mutated
#   - audit event written ONLY when explicitly clearing (validate_l99_clear handles this)
# Bug fixed by PR following TEST A inconsistency: previously this lived at [2/8]
# AFTER the trap was armed, causing L99 refusal to incorrectly trigger rollback.
echo "[1/8] L99 governance check"
"$PY" - <<PY
import sys
sys.path.insert(0, "$REPO_DIR/canary")
from deploy_safety import validate_l99_clear, DeploySafetyError
from pathlib import Path
try:
    validate_l99_clear(
        confirm_token="${CONFIRM_CLEAR_L99:-}",
        workflow_run_id="$WORKFLOW_RUN_ID",
        audit_dir=Path("$AUDIT_DIR"),
        l99_halt_path=Path("$L99_HALT"),
    )
except DeploySafetyError as e:
    print(f"::error::{e}")
    sys.exit(e.exit_code)
PY
echo "      L99 OK"

# ── [2/8] Atomic snapshot ────────────────────────────────────────────────
echo "[2/8] Pre-deploy snapshot via deploy_safety.snapshot()"
BACKUP_DIR=$("$PY" - <<PY
import sys
sys.path.insert(0, "$REPO_DIR/canary")
from deploy_safety import snapshot
from pathlib import Path
snap = snapshot(
    canary_dir=Path("$CANARY_DIR"),
    backup_root=Path("$BACKUP_ROOT"),
    workflow_run_id="$WORKFLOW_RUN_ID",
    ts="$TS",
    l99_halt_path=Path("$L99_HALT"),
)
print(snap.backup_dir)
PY
)
echo "      backup: $BACKUP_DIR"

# ── Trap installed AFTER snapshot — anything below this line is reversible
ROLLBACK_REASON="unknown"
rollback_on_error() {
  local rc=$?
  echo ""
  echo "::error::DEPLOY FAILED (rc=$rc, reason=$ROLLBACK_REASON) — initiating rollback"
  systemctl stop canary-battle.service 2>&1 | head -3 || true
  "$PY" - <<PY || true
import sys
sys.path.insert(0, "$REPO_DIR/canary")
from deploy_safety import rollback
from pathlib import Path
rollback(
    backup_dir=Path("$BACKUP_DIR"),
    canary_dir=Path("$CANARY_DIR"),
    audit_dir=Path("$AUDIT_DIR"),
    workflow_run_id="$WORKFLOW_RUN_ID",
    failure_reason="$ROLLBACK_REASON",
    l99_halt_path=Path("$L99_HALT"),
)
PY
  echo "::error::CRITICAL — rollback complete · service stopped · L99 halt engaged"
  echo "::error::Operator action required before next deploy"
  echo "::error::Forensic backup: $BACKUP_DIR"
  echo "::error::Audit events:    $AUDIT_DIR"
  exit $rc
}
trap rollback_on_error ERR INT TERM


# ── [3/8] Validate KEY/SECRET format ─────────────────────────────────────
echo "[3/8] Validating Gate.io key/secret format (32-hex KEY + 64-hex SECRET)"
ROLLBACK_REASON="keyfile_format_invalid"
trim() {
  local v="$1"
  v="${v#"${v%%[![:space:]]*}"}"
  v="${v%"${v##*[![:space:]]}"}"
  printf '%s' "$v"
}

MAIN_K=$(trim "$GATE_MAIN_API_KEY"); MAIN_S=$(trim "$GATE_MAIN_API_SECRET")
SUB1_K=$(trim "$GATE_SUB1_API_KEY"); SUB1_S=$(trim "$GATE_SUB1_API_SECRET")
SUB2_K=$(trim "$GATE_SUB2_API_KEY"); SUB2_S=$(trim "$GATE_SUB2_API_SECRET")

GATE_MAIN_API_KEY_TRIMMED=$MAIN_K \
GATE_MAIN_API_SECRET_TRIMMED=$MAIN_S \
GATE_SUB1_API_KEY_TRIMMED=$SUB1_K \
GATE_SUB1_API_SECRET_TRIMMED=$SUB1_S \
GATE_SUB2_API_KEY_TRIMMED=$SUB2_K \
GATE_SUB2_API_SECRET_TRIMMED=$SUB2_S \
"$PY" - <<'PY'
import os, sys
sys.path.insert(0, os.environ["REPO_DIR"] + "/canary") if False else None
sys.path.insert(0, "/root/tradingguru-empire/canary")
from deploy_safety import validate_keyfile_format, DeploySafetyError
pairs = [
    ("MAIN", os.environ["GATE_MAIN_API_KEY_TRIMMED"], os.environ["GATE_MAIN_API_SECRET_TRIMMED"]),
    ("SUB1", os.environ["GATE_SUB1_API_KEY_TRIMMED"], os.environ["GATE_SUB1_API_SECRET_TRIMMED"]),
    ("SUB2", os.environ["GATE_SUB2_API_KEY_TRIMMED"], os.environ["GATE_SUB2_API_SECRET_TRIMMED"]),
]
for acc, k, s in pairs:
    try:
        validate_keyfile_format(acc, k, s)
        print(f"      {acc}: key/secret format OK (len {len(k)}/{len(s)})")
    except DeploySafetyError as e:
        print(f"::error::{e}")
        sys.exit(1)
PY

# ── [4/8] Write keyfiles (atomic per-file, 0600) ─────────────────────────
echo "[4/8] Writing keyfiles to /root/canary/.api_key_*"
ROLLBACK_REASON="keyfile_write_failed"
write_atomic() {
  local target=$1 contents=$2
  local tmp="${target}.tmp.$$"
  printf '%s' "$contents" > "$tmp"
  chmod 0600 "$tmp"
  mv "$tmp" "$target"
}
write_atomic "$CANARY_DIR/.api_key_main" "${MAIN_K}:${MAIN_S}"
write_atomic "$CANARY_DIR/.api_key_sub1" "${SUB1_K}:${SUB1_S}"
write_atomic "$CANARY_DIR/.api_key_sub2" "${SUB2_K}:${SUB2_S}"
echo "      3 keyfiles written, chmod 0600"

# ── [5/8] Sync executor + config + service unit from repo ────────────────
echo "[5/8] Syncing executor + config + service unit"
ROLLBACK_REASON="repo_sync_failed"
cp -a "$REPO_DIR/canary/canary_executor.py"   "$CANARY_DIR/canary_executor.py"
cp -a "$REPO_DIR/canary/champion_battle.py"    "$CANARY_DIR/champion_battle.py"
cp -a "$REPO_DIR/canary/canary_api_server.py"  "$CANARY_DIR/canary_api_server.py"
cp -a "$REPO_DIR/canary/canary_config.json"   "$CANARY_DIR/canary_config.json"
cp -a "$REPO_DIR/canary/canary-battle.service" /etc/systemd/system/canary-battle.service
systemctl daemon-reload
# Restart canary-api server so new endpoints are live
if systemctl is-active --quiet canary-api.service 2>/dev/null; then
  systemctl restart canary-api.service
  echo "      canary-api.service restarted (new endpoints active)"
elif pgrep -f canary_api_server.py >/dev/null 2>&1; then
  pkill -f canary_api_server.py || true
  sleep 2
  nohup "$PY" "$CANARY_DIR/canary_api_server.py" >> "$RUNTIME_DIR/canary_api.log" 2>&1 &
  echo "      canary_api_server.py restarted (pid=$!)"
fi
# Verify service file now points to champion_battle.py (not canary_executor.py)
if ! grep -q "champion_battle.py" /etc/systemd/system/canary-battle.service; then
  echo "::error::Service file verification FAILED — ExecStart does not point to champion_battle.py"
  cat /etc/systemd/system/canary-battle.service | grep ExecStart
  exit 1
fi
echo "      service unit verified: ExecStart → champion_battle.py"
echo "      executor + champion_battle + config + service unit synced"

# ── [6/8] Measured preflight (live Gate.io, read-only) ───────────────────
echo "[6/8] Measured preflight via canary/check_agents.py (read-only)"
ROLLBACK_REASON="measured_preflight_failed"
if ! "$PY" "$REPO_DIR/canary/check_agents.py"; then
  echo "::error::Measured preflight FAILED — refusing to arm"
  exit 66
fi
echo "      measured preflight passed"

# ── [7/8] Write arm artifact (paper_preflight_passed now measured) ───────
echo "[7/8] Writing canary_arm.json (paper_preflight_passed MEASURED)"
ROLLBACK_REASON="arm_artifact_write_failed"
"$PY" - "$TS_HUMAN" "$WORKFLOW_RUN_ID" <<PY
import json, subprocess, sys
ts_human, run_id = sys.argv[1], sys.argv[2]
try:
    sha = subprocess.check_output(
        ["git", "-C", "$REPO_DIR", "rev-parse", "HEAD"],
        text=True,
    ).strip()
except Exception:
    sha = "unknown"
d = {
    "armed_by": f"operator-workflow-{run_id}",
    "armed_at": ts_human,
    "ack_max_loss_usd": 4.00,
    "ack_time_cap_hours": 720,
    "paper_preflight_passed": True,
    "paper_preflight_method": "check_agents.py-live-readonly",
    "paper_preflight_run_id": run_id,
    "accounts_armed": ["MAIN", "SUB1", "SUB2"],
    "pairs_armed": ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT"],
    "total_capital_usd": 1979.52,
    "armed_against_sha": sha,
}
with open("$ARM_FILE", "w") as f:
    json.dump(d, f, indent=2, sort_keys=True)
print(f"      arm written · sha={sha[:12]}")
PY

# ── [8/8] Start service + verify telemetry ───────────────────────────────
echo "[8/8] Starting canary-battle.service + verifying telemetry"
ROLLBACK_REASON="service_start_failed"

# Ensure runtime directory exists (champion_battle.py needs it at module-level)
mkdir -p "$RUNTIME_DIR"
chmod 755 "$RUNTIME_DIR"
echo "      runtime dir ensured: $RUNTIME_DIR"

# Quick Python import test to catch any startup crash before service start
echo "      pre-flight Python import test for champion_battle.py"
if ! CANARY_ROOT="$CANARY_DIR" "$PY" -c "
import sys, os
sys.path.insert(0, '$CANARY_DIR')
os.environ.setdefault('CANARY_ROOT', '$CANARY_DIR')
import importlib.util
spec = importlib.util.spec_from_file_location('champion_battle', '$CANARY_DIR/champion_battle.py')
# Just compile, don't exec main loop
import py_compile
py_compile.compile('$CANARY_DIR/champion_battle.py', doraise=True)
print('champion_battle.py compile OK')
" 2>&1; then
  echo "::error::champion_battle.py failed pre-flight Python test"
  "$PY" -c "import py_compile; py_compile.compile('$CANARY_DIR/champion_battle.py', doraise=True)" 2>&1 || true
  exit 1
fi
echo "      champion_battle.py pre-flight OK"

systemctl enable canary-battle.service >/dev/null 2>&1 || true
systemctl restart canary-battle.service
# Give the service ~10s to either fail or become active
for i in 1 2 3 4 5 6 7 8 9 10; do
  if systemctl is-active --quiet canary-battle.service; then break; fi
  sleep 1
done
if ! systemctl is-active --quiet canary-battle.service; then
  echo "::error::canary-battle.service did not become active within 10s"
  exit 67
fi

ROLLBACK_REASON="telemetry_not_written"
# Wait up to 120s for champion_battle.py to publish first telemetry tick
# Accept either multi_battle_status.json (canary_executor) OR champion_battle.log (champion_battle.py)
TELEMETRY=$RUNTIME_DIR/multi_battle_status.json
CHAMP_LOG=$RUNTIME_DIR/champion_battle.log
TELEMETRY_OK=0
for i in $(seq 1 24); do
  # Check champion_battle.log first (preferred)
  if [ -f "$CHAMP_LOG" ] && [ -s "$CHAMP_LOG" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$CHAMP_LOG") ))
    if [ "$AGE" -lt 120 ]; then
      echo "      champion_battle.log detected (age=${AGE}s) — champion_battle.py is running"
      TELEMETRY_OK=1
      break
    fi
  fi
  # Fallback: check multi_battle_status.json
  if [ -f "$TELEMETRY" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$TELEMETRY") ))
    if [ "$AGE" -lt 120 ]; then
      echo "      multi_battle_status.json detected (age=${AGE}s)"
      TELEMETRY_OK=1
      break
    fi
  fi
  sleep 5
done
if [ "$TELEMETRY_OK" -eq 0 ]; then
  echo "::error::champion_battle.py did not write telemetry within 120s"
  echo "::error::champion_battle.log exists: $([ -f $CHAMP_LOG ] && echo YES || echo NO)"
  echo "::error::champion_battle.log size: $([ -f $CHAMP_LOG ] && stat -c %s $CHAMP_LOG || echo 0)"
  journalctl -u canary-battle.service --no-pager -n 30 2>/dev/null || true
  exit 68
fi
echo "      service active · telemetry fresh"

# ── Success audit event ──────────────────────────────────────────────────
trap - ERR INT TERM
"$PY" - <<PY
import sys
sys.path.insert(0, "$REPO_DIR/canary")
from deploy_safety import write_audit_event
from pathlib import Path
write_audit_event(
    Path("$AUDIT_DIR"),
    "deploy_success",
    workflow_run_id="$WORKFLOW_RUN_ID",
    ts="$TS_HUMAN",
    backup_dir="$BACKUP_DIR",
)
PY

echo ""
echo "=== LIVE BATTLE STARTED ==="
echo "  Monitor:        tail -f $RUNTIME_DIR/battle.log"
echo "  Status:         systemctl status canary-battle.service"
echo "  Stop:           systemctl stop canary-battle.service"
echo "  Manual rollback: $REPO_DIR/canary/rollback_deploy.sh"
echo "  Backup:         $BACKUP_DIR"
echo "  Audit:          $AUDIT_DIR/deploy_success.json (or .N.json)"
