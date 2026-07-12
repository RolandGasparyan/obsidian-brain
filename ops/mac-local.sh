#!/usr/bin/env bash
# mac-local.sh — Mac-side offline tools for tradingguru-empire.
#
# Read-only utilities that do NOT require VPS access. Useful when working
# from the Mac without SSH (or when the VPS is unreachable):
#
#   verify     — check canary_strategy.py SHA256 against the lock
#   frontend   — open https://tradingguru.ai in the default browser
#   ticker     — curl Gate.io public spot ticker (no API key)
#   strix      — run bin/strix-watch.sh locally (security audit loop)
#   sync       — git pull origin main (fast-forward only)
#   refusals   — print docs/9-refusals-log.md
#   adrs       — list governance/ADR-*.md and refused proposals
#
# Pure SAFE ZONE — no state mutation, no governance bypass, no remote calls.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
EXPECTED_STRATEGY_SHA="704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143"

die() { echo "::error::$1" >&2; exit "${2:-1}"; }

sha_tool() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$@"
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$@"
  else
    die "neither shasum nor sha256sum available" 70
  fi
}

cmd_verify() {
  local strat="${REPO_DIR}/canary/canary_strategy.py"
  [ -f "${strat}" ] || die "strategy missing: ${strat}" 66
  local actual
  actual="$(sha_tool "${strat}" | awk '{print $1}')"
  printf 'expected: %s\n' "${EXPECTED_STRATEGY_SHA}"
  printf 'actual:   %s\n' "${actual}"
  if [ "${actual}" = "${EXPECTED_STRATEGY_SHA}" ]; then
    echo "✓ strategy SHA256 lock intact"
  else
    echo "✗ MISMATCH — strategy has drifted; do NOT deploy" >&2
    exit 64
  fi
}

cmd_frontend() {
  local url="${1:-https://tradingguru.ai/}"
  echo "opening ${url}"
  if command -v open >/dev/null 2>&1; then
    open "${url}"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${url}"
  else
    echo "(no browser launcher found — visit ${url} manually)"
  fi
}

cmd_ticker() {
  local pair="${1:-BTC_USDT}"
  command -v curl >/dev/null 2>&1 || die "curl not found" 70
  echo "── Gate.io public spot ticker: ${pair} ──"
  local resp
  resp="$(curl -sS --max-time 10 "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=${pair}" || true)"
  if [ -z "${resp}" ]; then
    die "empty response from Gate.io (network?)" 71
  fi
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "${resp}" | python3 -m json.tool
  else
    printf '%s\n' "${resp}"
  fi
}

cmd_strix() {
  local strix_script="${REPO_DIR}/bin/strix-watch.sh"
  [ -x "${strix_script}" ] || die "missing or not executable: ${strix_script}" 66
  exec "${strix_script}" "$@"
}

cmd_sync() {
  ( cd "${REPO_DIR}" && git fetch origin main && git pull --ff-only origin main )
}

cmd_refusals() {
  local log="${REPO_DIR}/docs/9-refusals-log.md"
  if [ -f "${log}" ]; then
    cat -- "${log}"
  else
    echo "(refusals log missing: ${log})"
  fi
}

cmd_adrs() {
  local gov="${REPO_DIR}/governance"
  if [ ! -d "${gov}" ]; then
    echo "(governance dir missing: ${gov})"
    return
  fi
  echo "── ADRs ──"
  ( cd "${gov}" && ls -1 -- ADR-*.md 2>/dev/null || echo "  (none)" )
  echo ""
  echo "── refused proposals ──"
  if [ -d "${gov}/refused_proposals" ]; then
    ( cd "${gov}/refused_proposals" && ls -1 -- ./*.md 2>/dev/null || echo "  (none)" )
  else
    echo "  (refused_proposals/ missing)"
  fi
}

usage() {
  cat <<'USAGE'
Usage: ops/mac-local.sh <subcommand> [args]

  verify              check canary_strategy.py SHA256 against the lock
  frontend [URL]      open https://tradingguru.ai (or given URL)
  ticker [PAIR]       curl Gate.io public spot ticker (default BTC_USDT)
  strix [args...]     run bin/strix-watch.sh locally
  sync                git pull origin main --ff-only
  refusals            print docs/9-refusals-log.md
  adrs                list governance/ADR-*.md and refused_proposals/
  help                show this message

Environment:
  REPO_DIR            override repo path (auto-detected from script location)

No remote calls, no state mutation. Pure SAFE ZONE.
USAGE
}

main() {
  local sub="${1:-help}"
  shift || true
  case "${sub}" in
    verify)   cmd_verify "$@" ;;
    frontend) cmd_frontend "$@" ;;
    ticker)   cmd_ticker "$@" ;;
    strix)    cmd_strix "$@" ;;
    sync)     cmd_sync "$@" ;;
    refusals) cmd_refusals "$@" ;;
    adrs)     cmd_adrs "$@" ;;
    -h|--help|help) usage ;;
    *) echo "unknown subcommand: ${sub}" >&2; echo ""; usage; exit 64 ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
