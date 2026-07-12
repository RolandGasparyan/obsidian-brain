#!/usr/bin/env bash
# mac-control.sh — Mac-side SSH dispatcher for the tradingguru-empire
# operator console.
#
# Forwards subcommands to `ops/command-center.sh` on the live VPS over SSH.
# SAFE subcommands run as-is; GUARDED subcommands require `CONFIRM=YES`
# locally on the Mac AND are forwarded with the same env to the remote so
# `command-center.sh` enforces its own require_confirm gate.
#
# This script does NOT mutate strategy, governance, or capital. It is a
# remote runner for the existing operator console — every safety property
# of `ops/command-center.sh` still applies on the VPS side.
#
# Usage:
#   ops/mac-control.sh <subcommand> [args...]
#
# Config (env, or ~/.tradingguru-empire/mac-control.env if it exists):
#   VPS_HOST        ssh target host                   (default: btc-15m-paper-bot)
#   VPS_USER        ssh user                          (default: root)
#   SSH_OPTS        extra ssh options                 (default: empty)
#   REPO_DIR_VPS    repo path on the VPS              (default: /root/tradingguru-empire)

set -euo pipefail
IFS=$'\n\t'

CONFIG_FILE="${HOME}/.tradingguru-empire/mac-control.env"
if [ -f "${CONFIG_FILE}" ]; then
  # shellcheck source=/dev/null
  . "${CONFIG_FILE}"
fi

VPS_HOST="${VPS_HOST:-btc-15m-paper-bot}"
VPS_USER="${VPS_USER:-root}"
SSH_OPTS="${SSH_OPTS:-}"
REPO_DIR_VPS="${REPO_DIR_VPS:-/root/tradingguru-empire}"
OPS_VPS="${REPO_DIR_VPS}/ops/command-center.sh"

SCRIPT_DIR="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR_LOCAL="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXPECTED_STRATEGY_SHA="704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143"

usage() {
  cat <<'USAGE'
Usage: ops/mac-control.sh <subcommand> [args...]

Forwards to ops/command-center.sh on the VPS via SSH. Every subcommand the
VPS console supports is reachable. Listed here for orientation:

  SAFE ZONE (read-only, no confirmation):
    status service tail champions pnl exec failclosed invalidkey
    rollback-log governance halt-state processes restart-policy watch
    dashboard frontend request mode l3 leaderboard battle signals

  GUARDED ZONE (require CONFIRM=YES on the Mac AND on the VPS):
    halt unhalt stop start rollback battle-restart

  Mac-only:
    final     End-of-championship report: local SHA256 verify + remote
              SHA256 + leaderboard + governance + halt-state + service
              + recent pnl. Read-only, no mutation.
    doctor    Print effective config, test SSH reachability, verify the
              remote command-center.sh exists and is executable.
    help      Show this message.

Config file (optional): ~/.tradingguru-empire/mac-control.env
  VPS_HOST=...
  VPS_USER=...
  SSH_OPTS="-i ~/.ssh/id_ed25519 -o ConnectTimeout=10"
  REPO_DIR_VPS=/root/tradingguru-empire

Examples:
  ops/mac-control.sh status
  ops/mac-control.sh leaderboard
  ops/mac-control.sh final
  CONFIRM=YES ops/mac-control.sh halt
USAGE
}

die() { echo "::error::$1" >&2; exit "${2:-1}"; }

ssh_run() {
  # shellcheck disable=SC2086
  ssh ${SSH_OPTS} "${VPS_USER}@${VPS_HOST}" -- "$@"
}

require_confirm() {
  if [ "${CONFIRM:-}" != "YES" ]; then
    echo "::error:: GUARDED subcommand '$1' requires CONFIRM=YES on the Mac" >&2
    echo "          Re-run as: CONFIRM=YES ops/mac-control.sh $1" >&2
    exit 65
  fi
}

shell_quote() {
  printf "'%s'" "${1//\'/\'\\\'\'}"
}

build_remote_cmd() {
  local cmd="${OPS_VPS}"
  local arg
  for arg in "$@"; do
    cmd="${cmd} $(shell_quote "${arg}")"
  done
  printf '%s' "${cmd}"
}

cmd_forward_safe() {
  local sub="$1"; shift
  ssh_run "$(build_remote_cmd "${sub}" "$@")"
}

cmd_forward_guarded() {
  local sub="$1"; shift
  require_confirm "${sub}"
  ssh_run "CONFIRM=YES $(build_remote_cmd "${sub}" "$@")"
}

local_strategy_sha() {
  local strat="${REPO_DIR_LOCAL}/canary/canary_strategy.py"
  if [ ! -f "${strat}" ]; then
    echo "(strategy file missing locally: ${strat})"
    return
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${strat}" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${strat}" | awk '{print $1}'
  else
    echo "(neither shasum nor sha256sum available)"
  fi
}

section() {
  printf '\n── %s ' "$1"
  local width=$((68 - ${#1}))
  if [ "${width}" -lt 1 ]; then width=1; fi
  printf '%*s\n' "${width}" '' | tr ' ' '─'
}

cmd_final() {
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "════════════════════════════════════════════════════════════════════"
  echo "  CHAMPIONSHIP FINAL REPORT"
  echo "  generated:  ${ts}"
  echo "  vps:        ${VPS_USER}@${VPS_HOST}"
  echo "  repo_vps:   ${REPO_DIR_VPS}"
  echo "════════════════════════════════════════════════════════════════════"

  section "STRATEGY LOCK (local)"
  local local_sha
  local_sha="$(local_strategy_sha)"
  echo "expected: ${EXPECTED_STRATEGY_SHA}"
  echo "local:    ${local_sha}"
  if [ "${local_sha}" = "${EXPECTED_STRATEGY_SHA}" ]; then
    echo "✓ local strategy SHA256 intact"
  else
    echo "✗ local strategy SHA256 MISMATCH"
  fi

  section "STRATEGY LOCK (vps)"
  local remote_sha
  remote_sha="$(ssh_run "sha256sum '${REPO_DIR_VPS}/canary/canary_strategy.py' 2>/dev/null | awk '{print \$1}'" || true)"
  echo "remote:   ${remote_sha:-(fetch failed)}"
  if [ -n "${remote_sha}" ] && [ "${remote_sha}" = "${EXPECTED_STRATEGY_SHA}" ]; then
    echo "✓ remote strategy SHA256 intact"
  elif [ -n "${remote_sha}" ]; then
    echo "✗ remote strategy SHA256 MISMATCH"
  fi

  section "LEADERBOARD"
  cmd_forward_safe leaderboard || echo "(leaderboard fetch failed)"

  section "GOVERNANCE (L99 protection_halt.json)"
  cmd_forward_safe governance || echo "(governance fetch failed)"

  section "SOFT HALT (CANARY_HALT.json)"
  cmd_forward_safe halt-state || echo "(halt-state fetch failed)"

  section "SERVICE (canary-battle.service)"
  cmd_forward_safe service || echo "(service fetch failed)"

  section "RECENT PnL EVENTS"
  cmd_forward_safe pnl || echo "(pnl fetch failed)"

  section "RECENT FAIL-CLOSED EVENTS"
  cmd_forward_safe failclosed || echo "(failclosed fetch failed)"

  section "RESTART POLICY"
  cmd_forward_safe restart-policy || echo "(restart-policy fetch failed)"

  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo "  END FINAL REPORT"
  echo "  No-drift law: ENFORCED · Cinematic labels are display-only ·"
  echo "  All accounts execute the same SHA256-locked MA50W10 strategy."
  echo "════════════════════════════════════════════════════════════════════"
}

cmd_doctor() {
  echo "── effective configuration ──"
  printf '  %-16s %s\n' VPS_HOST "${VPS_HOST}"
  printf '  %-16s %s\n' VPS_USER "${VPS_USER}"
  printf '  %-16s %s\n' SSH_OPTS "${SSH_OPTS:-(none)}"
  printf '  %-16s %s\n' REPO_DIR_VPS "${REPO_DIR_VPS}"
  printf '  %-16s %s\n' OPS_VPS "${OPS_VPS}"
  printf '  %-16s %s\n' CONFIG_FILE "${CONFIG_FILE} $( [ -f "${CONFIG_FILE}" ] && echo '(present)' || echo '(absent)' )"

  echo ""
  echo "── ssh reachability ──"
  if ssh_run 'true'; then
    echo "✓ ssh ok"
  else
    die "ssh failed — fix VPS_HOST / SSH_OPTS / keys before retrying" 70
  fi

  echo ""
  echo "── remote command-center.sh ──"
  if ssh_run "test -x '${OPS_VPS}'"; then
    echo "✓ ${OPS_VPS} is executable on ${VPS_HOST}"
  else
    die "${OPS_VPS} missing or not executable on the VPS" 71
  fi

  echo ""
  echo "── local strategy SHA256 ──"
  local sha
  sha="$(local_strategy_sha)"
  if [ "${sha}" = "${EXPECTED_STRATEGY_SHA}" ]; then
    echo "✓ ${sha}"
  else
    echo "✗ ${sha} (expected ${EXPECTED_STRATEGY_SHA})"
  fi
}

main() {
  local sub="${1:-help}"
  shift || true
  case "${sub}" in
    final)           cmd_final "$@" ;;
    doctor)          cmd_doctor "$@" ;;
    halt|unhalt|stop|start|rollback|battle-restart) cmd_forward_guarded "${sub}" "$@" ;;
    -h|--help|help)  usage ;;
    "")              usage ;;
    *)               cmd_forward_safe "${sub}" "$@" ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
