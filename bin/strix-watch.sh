#!/bin/bash
# bin/strix-watch.sh — SAFE ZONE security audit loop
#
# Runs `strix scan` against the operator's repos in read-only / no-destructive
# mode on a scheduled interval. Writes JSON reports per repo. Does NOT touch:
#   - canary-battle.service or any trading runtime
#   - canary/canary_strategy.py SHA256 lock (704dd5725a909fe3f6…)
#   - Gate.io API keys or keyfiles
#   - governance docs, refusals, caps
#
# Tier classification (per two-tier model):
#   SAFE ZONE — read-only · verify-only · telemetry only · auto-runs OK
#
# Usage:
#   bin/strix-watch.sh                  # default: scan every 3600s
#   SCAN_INTERVAL=600 bin/strix-watch.sh # override interval
#   REPO1=/path/to/repo bin/strix-watch.sh
#
# Exit codes:
#   0 — clean exit on SIGINT/SIGTERM
#   2 — `strix` not installed
#   3 — target repo directory missing
#
# Dependencies:
#   - strix (security scanner — operator-installed; verify with `which strix`)
#   - bash 4+
#   - standard POSIX utilities (date, mkdir, sleep)

set -euo pipefail
IFS=$'\n\t'

# ── Config (env-overridable) ─────────────────────────────────────────
STRIX_MODE="${STRIX_MODE:-SECURITY_RESEARCH}"
STRIX_SCOPE="${STRIX_SCOPE:-SAFE_AUDIT_ONLY}"
REPO1="${REPO1:-$HOME/tradingguru-empire}"
REPO2="${REPO2:-$HOME/reincarnation-smm}"
SCAN_INTERVAL="${SCAN_INTERVAL:-3600}"

# ── Pre-flight ───────────────────────────────────────────────────────
command -v strix >/dev/null || {
  echo "::error::strix not installed (no \`strix\` binary on PATH)"
  exit 2
}

for repo_var in REPO1 REPO2; do
  repo_path="${!repo_var}"
  if [ ! -d "$repo_path" ]; then
    echo "::error::missing repo dir: $repo_var=$repo_path"
    exit 3
  fi
done

mkdir -p "$REPO1/reports" "$REPO2/reports"

# ── Signal handling ──────────────────────────────────────────────────
cleanup() {
  echo
  echo "── interrupted at $(date -u +%Y-%m-%dT%H:%M:%SZ) — exiting cleanly"
  exit 0
}
trap cleanup INT TERM

# ── Single-repo scan (failures don't kill the loop) ──────────────────
scan_repo() {
  local repo="$1" name="$2"
  echo
  echo "🔍 scanning $name ($repo) …"
  if (cd "$repo" && strix scan . \
        --mode safe \
        --no-destructive \
        --report "reports/${name}-report.json"); then
    echo "✓ $name scan complete"
  else
    echo "::warning::strix failed on $name — continuing loop"
  fi
}

# ── Main loop ────────────────────────────────────────────────────────
echo "=================================================="
echo "🛡️  STRIX SECURITY WATCH"
echo "=================================================="
echo "mode:           $STRIX_MODE"
echo "scope:          $STRIX_SCOPE"
echo "interval:       ${SCAN_INTERVAL}s"
echo "repo1:          $REPO1"
echo "repo2:          $REPO2"
echo "tier:           SAFE ZONE — read-only · no-destructive"
echo "=================================================="

while true; do
  echo
  echo "── pass started $(date -u +%Y-%m-%dT%H:%M:%SZ) ──"
  scan_repo "$REPO1" tradingguru
  scan_repo "$REPO2" reincarnation
  echo
  echo "── pass complete · sleeping ${SCAN_INTERVAL}s ──"
  sleep "$SCAN_INTERVAL"
done
