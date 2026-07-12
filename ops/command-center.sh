#!/usr/bin/env bash
# ops/command-center.sh — TRADINGGURU.AI operator command center
#
# Verify-only by default. Destructive subcommands (halt, unhalt, stop, start,
# rollback) refuse to run unless CONFIRM=YES is set in the environment.
#
# Enforces:
#   - NO-DRIFT LAW (verify-only by default)
#   - SHA256-locked strategy (MA50W10) — same code on TITAN / VELOCITY / SENTINEL
#   - Governance is the source of truth; this script does not bypass it
#
# Operator runs this on the live host. It will NOT execute live trading,
# mutate strategy, or alter governance.
#
# Zone model:
#
#   SAFE ZONE
#   ─────────
#     read-only · verify-only · telemetry only
#     status, service, tail, champions, pnl, exec, failclosed, invalidkey,
#     rollback-log, governance, halt-state, processes, restart-policy,
#     watch, dashboard, frontend, request
#
#   GUARDED ZONE
#   ────────────
#     state mutation · requires explicit CONFIRM=YES
#     isolated from monitoring layer (operator-only, no automation path)
#     halt, unhalt, stop, start, rollback
#
# Safety properties (audited):
#   - set -euo pipefail
#   - All variable expansions quoted; braces used for explicitness
#   - GUARDED ZONE actions require CONFIRM=YES (refuse with exit 2 otherwise)
#   - Each GUARDED ZONE action prints an explicit "about to execute" banner
#     after the gate and before any side effect
#   - rm targets are validated: regular file, not symlink, expected basename
#   - Rollback script must be a regular non-symlink executable located under
#     CANARY_REPO_DIR (resolved via readlink -f), with expected basename
#   - GUARDED ZONE does NOT auto-create production paths — refuses if the
#     runtime dir does not already exist
#   - main() runs only when the file is executed directly, not when sourced
#     (prevents accidental execution via `source ops/command-center.sh`)

set -euo pipefail

# ── Core state (cinematic labels only; strategy is shared) ───────────────
export SYSTEM_MODE="${SYSTEM_MODE:-VERIFY_ONLY}"
export CHAMPIONSHIP_MODE="${CHAMPIONSHIP_MODE:-ACTIVE}"
export STRATEGY_NAME="${STRATEGY_NAME:-MA50W10}"
# Fingerprint prefix of the locked strategy snapshot (truncated for display).
export STRATEGY_SHA256_PREFIX="${STRATEGY_SHA256_PREFIX:-704dd5725a909fe3f6}"

export MAIN_LABEL="${MAIN_LABEL:-TITAN}"
export SUB1_LABEL="${SUB1_LABEL:-VELOCITY}"
export SUB2_LABEL="${SUB2_LABEL:-SENTINEL}"

# Full SHA256 lock of the strategy file. The `battle` subcommand verifies
# the on-disk file against this value before printing "lock intact".
STRATEGY_SHA256_LOCK="${STRATEGY_SHA256_LOCK:-704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143}"

# ── Paths (overridable for non-prod hosts) ───────────────────────────────
CANARY_RUNTIME_DIR="${CANARY_RUNTIME_DIR:-/root/canary/runtime}"
CANARY_REPO_DIR="${CANARY_REPO_DIR:-/root/tradingguru-empire}"
STRATEGY_FILE="${STRATEGY_FILE:-${CANARY_REPO_DIR}/canary/canary_strategy.py}"
PROTECTION_HALT="${PROTECTION_HALT:-/root/.l99/protection_halt.json}"
OPERATOR_REQUESTS_DIR="${OPERATOR_REQUESTS_DIR:-/root/canary/operator_requests}"

BATTLE_LOG="${BATTLE_LOG:-${CANARY_RUNTIME_DIR}/battle.log}"
CANARY_HALT_FILE="${CANARY_HALT_FILE:-${CANARY_RUNTIME_DIR}/CANARY_HALT.json}"
SERVICE_NAME="${SERVICE_NAME:-canary-battle.service}"
ROLLBACK_SCRIPT="${ROLLBACK_SCRIPT:-${CANARY_REPO_DIR}/canary/rollback_deploy.sh}"

# Expected basenames — defends against env mis-pointing.
EXPECTED_HALT_BASENAME="CANARY_HALT.json"
EXPECTED_ROLLBACK_BASENAME="rollback_deploy.sh"

# ── Helpers ──────────────────────────────────────────────────────────────
hr() { printf '%s\n' "=================================================="; }

die() {
  echo "REFUSED: $*" >&2
  exit 1
}

require_confirm() {
  if [[ "${CONFIRM:-}" != "YES" ]]; then
    hr
    echo "REFUSED: '$1' is a danger-zone action."
    echo "Re-run with CONFIRM=YES to acknowledge:"
    echo "  CONFIRM=YES $0 $1 ${*:2}"
    hr
    exit 2
  fi
}

danger_banner() {
  hr
  echo "⚠️  DANGER-ZONE EXECUTION"
  echo "⚠️  action : $1"
  echo "⚠️  target : $2"
  echo "⚠️  host   : $(hostname 2>/dev/null || echo unknown)"
  echo "⚠️  user   : ${USER:-unknown}"
  echo "⚠️  time   : $(date)"
  echo "⚠️  Governance is still enforced. NO-DRIFT LAW applies."
  hr
}

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "missing: $1" >&2
    return 1
  fi
}

# Refuse if path is a symlink, dir, or basename mismatch. Used before rm.
validate_rm_target() {
  local target="$1" expected_basename="$2"
  [[ -L "${target}" ]]                            && die "${target} is a symlink"
  [[ -d "${target}" ]]                            && die "${target} is a directory"
  [[ -e "${target}" && ! -f "${target}" ]]        && die "${target} is not a regular file"
  [[ "$(basename -- "${target}")" == "${expected_basename}" ]] \
    || die "basename mismatch: $(basename -- "${target}") != ${expected_basename}"
}

# Refuse if rollback script is anything other than a regular, non-symlink,
# executable file living under CANARY_REPO_DIR (resolved).
validate_rollback_script() {
  local script="$1"
  [[ -L "${script}" ]] && die "rollback script is a symlink: ${script}"
  [[ -f "${script}" ]] || die "rollback script is not a regular file: ${script}"
  [[ -x "${script}" ]] || die "rollback script is not executable: ${script}"
  [[ "$(basename -- "${script}")" == "${EXPECTED_ROLLBACK_BASENAME}" ]] \
    || die "rollback basename mismatch: $(basename -- "${script}")"
  local script_abs repo_abs
  script_abs="$(readlink -f -- "${script}")"
  repo_abs="$(readlink -f -- "${CANARY_REPO_DIR}" 2>/dev/null || true)"
  [[ -n "${repo_abs}" ]] || die "CANARY_REPO_DIR does not resolve: ${CANARY_REPO_DIR}"
  case "${script_abs}" in
    "${repo_abs}"/*) : ;;
    *) die "rollback script outside repo dir: ${script_abs} (repo: ${repo_abs})" ;;
  esac
}

log_grep() {
  # Safe grep against the battle log; tolerate missing file.
  if [[ ! -f "${BATTLE_LOG}" ]]; then
    echo "(no battle log at ${BATTLE_LOG})"
    return 0
  fi
  grep -E "$1" "${BATTLE_LOG}" | tail -"${2:-50}" || true
}

# Compute SHA256 of $1 using whichever tool is available. Prints the hex
# digest on stdout. Returns non-zero if no tool is found or the file is
# missing.
strategy_sha256() {
  local f="$1"
  [[ -f "${f}" ]] || { echo "(strategy file missing: ${f})" >&2; return 1; }
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -- "${f}" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -- "${f}" | awk '{print $1}'
  else
    echo "(no sha256sum/shasum available)" >&2
    return 1
  fi
}

# Verify the on-disk strategy file against ${STRATEGY_SHA256_LOCK}.
# Prints expected/actual. Returns 0 on match, 1 on mismatch, 2 on tool error.
# Pure verifier — does NOT mutate state.
verify_strategy_lock() {
  local actual
  if ! actual="$(strategy_sha256 "${STRATEGY_FILE}")"; then
    echo "✗ STRATEGY LOCK CHECK FAILED — could not compute SHA256"
    return 2
  fi
  printf 'expected: %s\n' "${STRATEGY_SHA256_LOCK}"
  printf 'actual:   %s\n' "${actual}"
  if [[ "${actual}" == "${STRATEGY_SHA256_LOCK}" ]]; then
    echo "✓ STRATEGY LOCK INTACT (${STRATEGY_NAME})"
    return 0
  fi
  echo "✗ STRATEGY LOCK MISMATCH — drift detected; DO NOT deploy"
  return 1
}

disclosure() {
  hr
  echo "Cinematic display labels only."
  echo "All live accounts execute the same"
  echo "SHA256-locked ${STRATEGY_NAME} strategy"
  echo "under shared governance."
  hr
}

banner() {
  echo "⚔️ REAL MONEY CHAMPIONSHIP ACTIVE"
  echo "👑 MAIN   ↔ ${MAIN_LABEL}"
  echo "🔥 SUB1   ↔ ${SUB1_LABEL}"
  echo "🛡️ SUB2   ↔ ${SUB2_LABEL}"
  echo ""
  echo "🟢 ${SYSTEM_MODE} MODE ACTIVE"
  echo "🟢 NO-DRIFT LAW ENFORCED"
  echo "🟢 GOVERNANCE ACTIVE"
  echo "🟢 SAFETY STACK ACTIVE"
}

no_drift_footer() {
  hr
  echo "NO-DRIFT LAW ENFORCED"
  echo "VERIFY-ONLY MODE DEFAULT"
  echo "NO GODMODE EXECUTION"
  echo "NO AUTONOMOUS EVOLUTION"
  echo "NO STRATEGY MUTATION"
  echo "NO GOVERNANCE BYPASS"
  hr
}

usage() {
  cat <<'EOF'
Usage: ops/command-center.sh <subcommand>

Verify-only (safe, read-only):
  status         Disclosure + live banner + service state
  service        systemctl status of canary-battle.service
  tail           Live telemetry stream (tail -F battle.log)
  champions      Last 50 MAIN/SUB1/SUB2 lines
  pnl            Last 50 PnL / DD / Sharpe / balance lines
  exec           Last 50 BUY / SELL / LONG / SHORT lines
  failclosed     Last 20 FAIL-CLOSED events
  invalidkey     Last 20 INVALID_KEY events
  rollback-log   Last 20 ROLLBACK events
  governance     Cat protection_halt.json
  halt-state     Show CANARY_HALT.json state (does not modify)
  processes      pgrep for canary processes
  restart-policy systemctl show Restart=*
  watch          Live dashboard refresh (Ctrl-C to exit)
  dashboard      Trigger dashboard.yml workflow (gh required)
  frontend       Trigger frontend-check.yml workflow (gh required)
  request        Log a manual operator request (interactive)
  mode <NAME>    Switch runtime profile banner/env
                 (SAFE | AGGRESSIVE_MONITOR | SHADOW_ARENA | OPS | WARROOM | LIVE)
                 Env only persists if the script is sourced.
  l3             Print L3 championship layer config (cinematic, SAFE ZONE)
  leaderboard    Cinematic placeholder leaderboard feed (NOT live data)
  battle         Aggressive-monitoring init: real SHA256 verify +
                 governance + service + snapshot + hand-off to watch.
                 Skip the watch loop with BATTLE_SKIP_WATCH=1.
  signals        Wider read-only view: UTC ts + entry/exit/signal grep +
                 canary_executor.py process check.

Danger-zone (require CONFIRM=YES):
  halt             Write soft-halt file CANARY_HALT.json (graceful stop)
  unhalt           Remove soft-halt file
  stop             systemctl stop canary-battle.service
  start            systemctl start canary-battle.service
  rollback         Run canary/rollback_deploy.sh MANUAL_ABORT
  battle-restart   systemctl restart canary-battle.service (gated, no prompt)

Examples:
  ops/command-center.sh status
  ops/command-center.sh battle
  ops/command-center.sh pnl
  CONFIRM=YES ops/command-center.sh halt
  CONFIRM=YES ops/command-center.sh battle-restart
EOF
}

# ─────────────────────────────────────────────────────────────────────────
# SAFE ZONE — read-only · verify-only · telemetry only
# ─────────────────────────────────────────────────────────────────────────
cmd_status() {
  disclosure
  banner
  echo ""
  local active="unknown"
  active="$(systemctl is-active "${SERVICE_NAME}" 2>/dev/null || echo unknown)"
  echo "service: ${active}"
  no_drift_footer
}

cmd_service() {
  systemctl status "${SERVICE_NAME}" --no-pager
}

cmd_tail() {
  require_file "${BATTLE_LOG}"
  tail -F "${BATTLE_LOG}"
}

cmd_champions()   { log_grep "MAIN|SUB1|SUB2" 50; }
cmd_pnl()         { log_grep "PnL|Sharpe|DD|balance OK" 50; }
cmd_exec()        { log_grep "BUY|SELL|LONG|SHORT" 50; }
cmd_failclosed()  { log_grep "FAIL-CLOSED" 20; }
cmd_invalidkey()  { log_grep "INVALID_KEY" 20; }
cmd_rollbacklog() { log_grep "ROLLBACK" 20; }

cmd_governance() {
  if [[ ! -f "${PROTECTION_HALT}" ]]; then
    echo "(no protection_halt.json at ${PROTECTION_HALT})"
    return 0
  fi
  cat "${PROTECTION_HALT}"
}

cmd_halt_state() {
  if [[ -e "${CANARY_HALT_FILE}" ]]; then
    echo "SOFT HALT ACTIVE:"
    ls -la "${CANARY_HALT_FILE}"
    echo "---"
    cat "${CANARY_HALT_FILE}"
  else
    echo "no soft halt file at ${CANARY_HALT_FILE}"
  fi
}

cmd_processes() {
  # pgrep -a prints "pid cmdline"; tolerate no-match (exit 1) cleanly.
  if ! pgrep -a canary; then
    echo "(no canary processes found)"
  fi
}

cmd_restart_policy() {
  systemctl show "${SERVICE_NAME}" | grep -E "^Restart"
}

cmd_watch() {
  if ! command -v watch >/dev/null 2>&1; then
    echo "watch(1) not installed" >&2
    return 1
  fi
  # Variables are interpolated into the inner shell snippet by the heredoc;
  # they are operator-controlled trusted paths, not user-supplied input.
  local inner
  inner="$(cat <<INNER
echo "=================================================="
echo "⚔️ FINAL LIVE ARENA"
echo "=================================================="
echo
echo "=== SERVICE ==="
systemctl is-active ${SERVICE_NAME}
echo
echo "=== PNL / DD / SHARPE ==="
grep -E 'PnL|Sharpe|DD' ${BATTLE_LOG} 2>/dev/null | tail -10
echo
echo "=== EXECUTIONS ==="
grep -E 'BUY|SELL|LONG|SHORT' ${BATTLE_LOG} 2>/dev/null | tail -10
echo
echo "=== FAIL-CLOSED ==="
grep 'FAIL-CLOSED' ${BATTLE_LOG} 2>/dev/null | tail -5
echo
echo "=== ROLLBACK ==="
grep 'ROLLBACK' ${BATTLE_LOG} 2>/dev/null | tail -5
echo
echo "=================================================="
echo "🟢 FINAL LIVE SYSTEM RUNNING"
echo "=================================================="
INNER
)"
  watch -n 3 "${inner}"
}

cmd_dashboard() {
  if ! command -v gh >/dev/null 2>&1; then
    echo "gh CLI not installed; skipping workflow trigger" >&2
    return 1
  fi
  gh workflow run dashboard.yml
}

# cmd_signals — wider read-only signals view than `exec` (which only matches
# BUY/SELL/LONG/SHORT). Adds ENTRY|SIGNAL|EXECUTED|filled tokens and a
# process check so the operator gets entry-side activity and executor liveness
# in one pass. Pure SAFE ZONE — read-only.
cmd_signals() {
  date -u
  echo ""
  echo "=== LIVE SIGNALS ==="
  if [[ -f "${BATTLE_LOG}" ]]; then
    grep -Ei "BUY|SELL|ENTRY|SIGNAL|EXECUTED|filled" "${BATTLE_LOG}" | tail -30 || true
  else
    echo "(no battle log at ${BATTLE_LOG})"
  fi
  echo ""
  echo "=== ENGINE ==="
  pgrep -af canary_executor.py || echo "(no canary_executor.py process found)"
}

cmd_frontend() {
  if ! command -v gh >/dev/null 2>&1; then
    echo "gh CLI not installed; skipping workflow trigger" >&2
    return 1
  fi
  gh workflow run frontend-check.yml
}

cmd_request() {
  mkdir -p "${OPERATOR_REQUESTS_DIR}"
  hr
  echo "⚠️ MANUAL OPERATOR REQUEST"
  hr
  local req="" reason=""
  read -r -p "Request: " req || true
  read -r -p "Reason:  " reason || true
  local out
  out="${OPERATOR_REQUESTS_DIR}/request-$(date +%s).log"
  {
    printf 'TIME=%s\n' "$(date)"
    printf 'USER=%s\n' "${USER:-unknown}"
    printf 'HOST=%s\n' "$(hostname 2>/dev/null || echo unknown)"
    printf 'REQUEST=%s\n' "${req}"
    printf 'REASON=%s\n'  "${reason}"
    printf 'MODE=MANUAL_OPERATOR_REQUEST\n'
  } >"${out}"
  echo "✅ Logged: ${out}"
  echo "⚠️ Logging ≠ authorization"
  echo "⚠️ Governance still enforced"
}

# switch_mode — runtime profile switcher. Pure SAFE ZONE: only sets env
# vars and prints a banner. Does NOT grant any new execution power; the
# GUARDED ZONE is gated by CONFIRM=YES regardless of which mode is active.
#
# Persistence: when invoked via `./command-center.sh mode SAFE`, the env
# exports only live in the subshell — they do not propagate to the parent.
# To set the operator's interactive shell profile, source the script and
# call the function directly:
#
#     source ops/command-center.sh
#     switch_mode SAFE
switch_mode() {
  local mode="${1:-}"
  echo ""
  hr
  echo "⚔️ TRADINGGURU.AI MODE SWITCH"
  hr
  echo "Requested Mode: ${mode}"
  hr
  echo ""
  case "${mode}" in
    SAFE)
      export SYSTEM_MODE="VERIFY_ONLY"
      export WATCH_INTERVAL=10
      export TELEMETRY_LEVEL="NORMAL"
      echo "🟢 SAFE MODE ACTIVE"
      echo "Read-only monitoring enabled"
      ;;
    AGGRESSIVE_MONITOR)
      export SYSTEM_MODE="VERIFY_ONLY"
      export WATCH_INTERVAL=1
      export TELEMETRY_LEVEL="HIGH"
      echo "🔥 AGGRESSIVE MONITOR MODE ACTIVE"
      echo "Fast telemetry refresh enabled"
      echo "No runtime mutation allowed"
      ;;
    SHADOW_ARENA)
      export SYSTEM_MODE="VERIFY_ONLY"
      export CHAMPIONSHIP_OVERLAY=1
      export LIVE_SCOREBOARD=1
      export TELEMETRY_LEVEL="MAX"
      echo "⚔️ SHADOW ARENA ACTIVE"
      echo "👑 ${MAIN_LABEL} online"
      echo "🔥 ${SUB1_LABEL} online"
      echo "🛡️ ${SUB2_LABEL} online"
      echo ""
      echo "Cinematic labels only."
      echo "All accounts still execute"
      echo "the same SHA256-locked strategy."
      ;;
    OPS)
      # OPS only signals operator intent; CONFIRM=YES is still the sole
      # gate for GUARDED ZONE actions. ENABLE_GUARDED_ZONE is informational.
      export SYSTEM_MODE="OPERATOR"
      export ENABLE_GUARDED_ZONE=1
      echo "🛠️ OPERATOR MODE ACTIVE"
      echo "Guarded zone available"
      echo "CONFIRM=YES still required"
      ;;
    WARROOM)
      export SYSTEM_MODE="WARROOM"
      export WATCH_INTERVAL=1
      export LIVE_WATCH=1
      export TELEMETRY_LEVEL="MAX"
      echo "🚀 WARROOM ACTIVE"
      echo "Realtime telemetry streaming enabled"
      echo "Governance unchanged"
      ;;
    LIVE)
      # LIVE = operator-console live-watch posture. Pure SAFE ZONE.
      # The accounts have been live (real capital) throughout; this mode
      # does NOT change the trading state, the SHA256-locked strategy,
      # or any per-account caps. It only sets operator-side env vars and
      # raises the cinematic banner. CONFIRM=YES is still the sole gate
      # for every GUARDED ZONE action.
      export SYSTEM_MODE="LIVE"
      export WATCH_INTERVAL=2
      export TELEMETRY_LEVEL="MAX"
      export LIVE_BANNER=1
      echo "👑 LIVE MODE ACTIVE"
      echo "Operator console: live-watch posture"
      echo "Telemetry: MAX  ·  Watch interval: 2s"
      echo ""
      echo "Strategy SHA256 lock: UNCHANGED"
      echo "Per-account caps:     UNCHANGED"
      echo "Governance:           ENFORCED"
      echo "CONFIRM=YES still required for every GUARDED action."
      ;;
    ""|*)
      echo "❌ UNKNOWN MODE: ${mode:-<empty>}"
      echo ""
      echo "Available modes:"
      echo "  SAFE"
      echo "  AGGRESSIVE_MONITOR"
      echo "  SHADOW_ARENA"
      echo "  OPS"
      echo "  WARROOM"
      echo "  LIVE"
      return 1
      ;;
  esac
  echo ""
  hr
  echo "🟢 MODE SWITCH COMPLETE"
  echo "🟢 NO-DRIFT LAW ENFORCED"
  echo "🟢 STRATEGY SHA256 UNCHANGED"
  echo "🟢 GOVERNANCE ACTIVE"
  hr
  echo ""
}

cmd_mode() {
  switch_mode "${1:-}"
}

# enable_l3_battle — SAFE ZONE: sets L3 scoring engine env vars only.
# Does NOT enable execution, mutation, or per-account strategy variants.
# The L3 layer is a *cinematic* competition overlay; underlying strategy
# is the same SHA256-locked MA50W10 on every account.
enable_l3_battle() {
  export ENABLE_L3_BATTLE=1
  export SCORE_PNL=1
  export SCORE_SHARPE=1
  export SCORE_STABILITY=1
  export SCORE_SURVIVAL=1
  export SCORE_EXECUTION=1
  export SCORE_RECOVERY=1
  export TITLE_PNL_KING="MONEY EMPEROR"
  export TITLE_SHARPE="PRECISION KING"
  export TITLE_SURVIVAL="SURVIVAL TITAN"
  export TITLE_SPEED="MOMENTUM HUNTER"
  export MICRO_ROUND_MIN=15
  export BATTLE_ROUND_MIN=60
  export WAR_ROUND_HOURS=6
}

# cmd_l3 — print the L3 configuration banner. Sets the env vars only in
# this subshell unless the file is sourced (see switch_mode docs).
cmd_l3() {
  enable_l3_battle
  hr
  echo "👑 L3 CHAMPIONSHIP LAYER"
  hr
  echo "rounds:  micro=${MICRO_ROUND_MIN}m  battle=${BATTLE_ROUND_MIN}m  war=${WAR_ROUND_HOURS}h"
  echo "scores:  pnl=${SCORE_PNL} sharpe=${SCORE_SHARPE} stability=${SCORE_STABILITY}"
  echo "         survival=${SCORE_SURVIVAL} execution=${SCORE_EXECUTION} recovery=${SCORE_RECOVERY}"
  echo "titles:  pnl=${TITLE_PNL_KING}"
  echo "         sharpe=${TITLE_SHARPE}"
  echo "         survival=${TITLE_SURVIVAL}"
  echo "         speed=${TITLE_SPEED}"
  hr
  echo "Cinematic competition layer only."
  echo "All accounts execute the same SHA256-locked ${STRATEGY_NAME} strategy."
  hr
}

# cmd_leaderboard — real per-account leaderboard parsed from battle.log
# by ops/scoring.py. If python3 is unavailable or the scorer fails, falls
# back to a clearly-labelled cinematic placeholder. Disclosure is printed
# top and bottom regardless of branch.
cmd_leaderboard() {
  local scorer
  scorer="$(dirname -- "${BASH_SOURCE[0]}")/scoring.py"
  # MAIN_LABEL/SUB*/STRATEGY_NAME are already exported globally above, so
  # the scorer inherits them. BATTLE_LOG is passed explicitly.
  if command -v python3 >/dev/null 2>&1 && [[ -f "${scorer}" ]]; then
    if python3 "${scorer}" --battle-log "${BATTLE_LOG}"; then
      return 0
    fi
    echo "(scorer failed — falling back to cinematic placeholder)" >&2
  else
    echo "(python3 or scoring.py missing — cinematic placeholder)" >&2
  fi
  hr
  echo "⚠️  CINEMATIC COMPETITION LAYER — placeholder feed"
  echo "⚠️  These lines are illustrative templates, NOT live telemetry."
  echo "⚠️  Use 'pnl', 'champions', 'exec' for actual log-sourced data."
  hr
  echo ""
  echo "⚔️ ${MAIN_LABEL} dominates Sharpe leaderboard"
  echo "🔥 ${SUB1_LABEL} captures momentum breakout"
  echo "🛡️ ${SUB2_LABEL} survives volatility collapse"
  echo "👑 ${MAIN_LABEL} secures first place"
  echo "📈 ${SUB1_LABEL} gains +2 battle points"
  echo "🏆 ${SUB2_LABEL} wins survival round"
  echo ""
  echo "🏆 LIVE CHAMPIONSHIP"
  echo "1. ${MAIN_LABEL}"
  echo "2. ${SUB1_LABEL}"
  echo "3. ${SUB2_LABEL}"
  echo ""
  hr
  echo "Cinematic competition layer only."
  echo "All accounts execute the same"
  echo "SHA256-locked ${STRATEGY_NAME} strategy."
  hr
}

# cmd_battle — SAFE ZONE aggressive-monitoring init.
#
# Does a real SHA256 verification (not just a printed prefix), prints
# governance state, service status, banner + disclosure, recent log lines,
# then hands off to cmd_watch for the live refresh loop. NO state mutation.
# Service restart is a separate GUARDED subcommand (battle-restart).
cmd_battle() {
  hr
  echo "👑 FINAL LIVE DEPLOY"
  echo "   mode: SAFE ZONE (read-only verify + live watch)"
  echo "   time: $(date)"
  hr
  echo ""

  echo "── STRATEGY LOCK ──"
  verify_strategy_lock || {
    local rc=$?
    echo ""
    echo "::warning:: strategy lock check returned non-zero ($rc)."
    echo "::warning:: continuing in observe-only mode — no mutation will follow."
  }
  echo ""

  echo "── GOVERNANCE (L99) ──"
  if [[ -f "${PROTECTION_HALT}" ]]; then
    cat -- "${PROTECTION_HALT}"
  else
    echo "(no protection_halt.json at ${PROTECTION_HALT})"
  fi
  echo ""

  echo "── SERVICE ──"
  local active="unknown"
  active="$(systemctl is-active "${SERVICE_NAME}" 2>/dev/null || echo unknown)"
  echo "${SERVICE_NAME}: ${active}"
  echo ""

  disclosure
  banner
  echo ""

  echo "── LIVE SNAPSHOT (last 30 lines) ──"
  if [[ -f "${BATTLE_LOG}" ]]; then
    tail -n 30 -- "${BATTLE_LOG}" || true
  else
    echo "(no battle log at ${BATTLE_LOG})"
  fi
  echo ""

  if [[ "${BATTLE_SKIP_WATCH:-0}" == "1" ]]; then
    echo "(BATTLE_SKIP_WATCH=1 — skipping cmd_watch hand-off)"
    return 0
  fi

  hr
  echo "📡 handing off to live watch — Ctrl-C to exit"
  echo "   restart is a SEPARATE command: CONFIRM=YES $0 battle-restart"
  hr
  cmd_watch
}

# ─────────────────────────────────────────────────────────────────────────
# GUARDED ZONE — state mutation · CONFIRM=YES required
# isolated from monitoring layer (operator-only, no automation path)
# ─────────────────────────────────────────────────────────────────────────
# Each guarded function:
#   1) require_confirm — refuse without CONFIRM=YES (exit 2)
#   2) validate inputs (paths, basenames, repo containment, runtime exists)
#   3) print a danger_banner describing the action
#   4) perform the action

cmd_halt() {
  require_confirm halt
  # Refuse to auto-create runtime dir in danger-zone — operator must ensure
  # it already exists.
  [[ -d "${CANARY_RUNTIME_DIR}" ]] \
    || die "CANARY_RUNTIME_DIR does not exist: ${CANARY_RUNTIME_DIR}"
  [[ "$(basename -- "${CANARY_HALT_FILE}")" == "${EXPECTED_HALT_BASENAME}" ]] \
    || die "halt basename mismatch: $(basename -- "${CANARY_HALT_FILE}")"
  # If something is already there, validate it's the expected regular file
  # before overwriting.
  if [[ -e "${CANARY_HALT_FILE}" ]]; then
    validate_rm_target "${CANARY_HALT_FILE}" "${EXPECTED_HALT_BASENAME}"
  fi
  danger_banner "halt (write soft-halt file)" "${CANARY_HALT_FILE}"
  printf '{"halted": true, "reason": "MANUAL_OPERATOR_STOP", "ts": %s}\n' \
    "$(date +%s)" >"${CANARY_HALT_FILE}"
  echo "soft halt written: ${CANARY_HALT_FILE}"
}

cmd_unhalt() {
  require_confirm unhalt
  if [[ ! -e "${CANARY_HALT_FILE}" ]]; then
    echo "no soft halt to remove at ${CANARY_HALT_FILE}"
    return 0
  fi
  validate_rm_target "${CANARY_HALT_FILE}" "${EXPECTED_HALT_BASENAME}"
  danger_banner "unhalt (rm soft-halt file)" "${CANARY_HALT_FILE}"
  rm -f -- "${CANARY_HALT_FILE}"
  echo "soft halt removed: ${CANARY_HALT_FILE}"
}

cmd_stop() {
  require_confirm stop
  danger_banner "stop service" "${SERVICE_NAME}"
  systemctl stop "${SERVICE_NAME}"
}

cmd_start() {
  require_confirm start
  danger_banner "start service" "${SERVICE_NAME}"
  systemctl start "${SERVICE_NAME}"
}

cmd_rollback() {
  require_confirm rollback
  validate_rollback_script "${ROLLBACK_SCRIPT}"
  danger_banner "rollback (MANUAL_ABORT)" "${ROLLBACK_SCRIPT}"
  "${ROLLBACK_SCRIPT}" MANUAL_ABORT
}

# cmd_battle_restart — GUARDED restart of the canary battle service.
#
# Replaces the interactive y/n prompt pattern: GUARDED actions must be
# gated by CONFIRM=YES (env var, not stdin) so they are explicit, scripted,
# and cannot be triggered by a stray keypress in a paste buffer.
cmd_battle_restart() {
  require_confirm battle-restart
  [[ "${SERVICE_NAME}" == "canary-battle.service" ]] \
    || die "battle-restart refused: SERVICE_NAME != canary-battle.service (${SERVICE_NAME})"
  danger_banner "battle-restart (systemctl restart)" "${SERVICE_NAME}"
  systemctl restart "${SERVICE_NAME}"
  sleep 2
  echo ""
  echo "── post-restart service state ──"
  systemctl is-active "${SERVICE_NAME}" || true
}

# ── Dispatch ─────────────────────────────────────────────────────────────
main() {
  local sub="${1:-status}"
  shift || true
  case "${sub}" in
    status)         cmd_status "$@" ;;
    service)        cmd_service "$@" ;;
    tail)           cmd_tail "$@" ;;
    champions)      cmd_champions "$@" ;;
    pnl)            cmd_pnl "$@" ;;
    exec)           cmd_exec "$@" ;;
    failclosed)     cmd_failclosed "$@" ;;
    invalidkey)     cmd_invalidkey "$@" ;;
    rollback-log)   cmd_rollbacklog "$@" ;;
    governance)     cmd_governance "$@" ;;
    halt-state)     cmd_halt_state "$@" ;;
    processes)      cmd_processes "$@" ;;
    restart-policy) cmd_restart_policy "$@" ;;
    watch)          cmd_watch "$@" ;;
    dashboard)      cmd_dashboard "$@" ;;
    frontend)       cmd_frontend "$@" ;;
    request)        cmd_request "$@" ;;
    mode)           cmd_mode "$@" ;;
    l3)             cmd_l3 "$@" ;;
    leaderboard)    cmd_leaderboard "$@" ;;
    battle)         cmd_battle "$@" ;;
    signals)        cmd_signals "$@" ;;
    halt)           cmd_halt "$@" ;;
    unhalt)         cmd_unhalt "$@" ;;
    stop)           cmd_stop "$@" ;;
    start)          cmd_start "$@" ;;
    rollback)       cmd_rollback "$@" ;;
    battle-restart) cmd_battle_restart "$@" ;;
    -h|--help|help) usage ;;
    *)
      echo "unknown subcommand: ${sub}" >&2
      echo ""
      usage
      exit 64
      ;;
  esac
}

# Source-guard: only run main when executed directly. Allows the file to be
# sourced for testing helpers without triggering side effects.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
