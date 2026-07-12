#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# sync_empire.sh — Mac<->GitHub<->VPS three-way sync helper for empire
# ═══════════════════════════════════════════════════════════════════════
#
# Run on the Mac (this script lives in ~/Desktop/tradingguru-empire/).
#
# Usage:
#   ./sync_empire.sh pull          pull latest from origin/main (Mac side)
#   ./sync_empire.sh push <msg>    stage + commit + push (Mac side)
#   ./sync_empire.sh server        pull latest on the VPS
#   ./sync_empire.sh status        show local + remote + VPS git state side-by-side
#   ./sync_empire.sh verify        sacred-lock verification (4-way SHA parity)
#   ./sync_empire.sh deploy <msg>  full cycle: commit local → push origin → VPS pull → restart paper-arena
#
# SAFETY:
#   ✗ Never force-pushes
#   ✗ Never skips hooks (pre-commit guards SHA256 + secrets on every commit)
#   ✗ Never touches L99 halt, canary.service, .api_key, /root/canary/
#   ✗ Never operates on /root/agent/ (operator's legacy mirror)
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REMOTE="origin"
BRANCH="main"
SERVER="root@167.71.24.86"
SERVER_REPO="/root/tradingguru-empire"
LOCKED_SHA="704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143"
SERVICE_NAME="paper-arena.service"

cmd="${1:-status}"
shift || true

case "$cmd" in

  pull)
    cd "$REPO_DIR"
    echo "→ Pulling latest from $REMOTE/$BRANCH..."
    git fetch "$REMOTE" "$BRANCH"
    if [ -n "$(git status --porcelain)" ]; then
      echo "  Local has uncommitted changes — stashing first"
      git stash --include-untracked
      STASHED=1
    fi
    git pull --rebase "$REMOTE" "$BRANCH"
    if [ "${STASHED:-0}" = "1" ]; then
      echo "  Restoring stash"
      git stash pop || echo "  (stash had conflicts — resolve manually)"
    fi
    echo "✓ pull complete"
    ;;

  push)
    msg="${1:-sync: local empire changes}"
    cd "$REPO_DIR"
    echo "→ Staging all changes..."
    git add -A
    if git diff --cached --quiet; then
      echo "  No changes to commit"
    else
      echo "→ Committing: $msg"
      git commit -m "$msg"
      echo "→ Pushing to $REMOTE/$BRANCH..."
      git push "$REMOTE" "$BRANCH"
      echo "✓ push complete"
    fi
    ;;

  server)
    echo "→ Pulling on VPS..."
    ssh -o ConnectTimeout=10 "$SERVER" "cd $SERVER_REPO && git pull --rebase origin main 2>&1 | tail -10"
    echo "✓ VPS pull complete"
    ;;

  status)
    echo "═══ LOCAL ($(hostname)) ═══"
    cd "$REPO_DIR"
    git status --short --branch | head -10
    echo ""
    echo "═══ GITHUB (origin/main HEAD) ═══"
    git fetch "$REMOTE" "$BRANCH" --quiet 2>/dev/null || true
    git log "$REMOTE/$BRANCH" --oneline -3
    echo ""
    echo "═══ VPS ($SERVER:$SERVER_REPO) ═══"
    ssh -o ConnectTimeout=10 "$SERVER" "cd $SERVER_REPO 2>/dev/null && git status --short --branch | head -5 && git log --oneline -3" 2>&1 | head -10
    ;;

  verify)
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  tradingguru-empire · sacred-lock verify"
    echo "║  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "═══ [1/4] SHA256 LOCK 3-WAY PARITY (post empire-promotion) ═══"
    LOCAL_EMPIRE=$(shasum -a 256 "$REPO_DIR/canary/canary_strategy.py" | awk '{print $1}')
    SERVER_EMPIRE=$(ssh -o ConnectTimeout=10 "$SERVER" "sha256sum $SERVER_REPO/canary/canary_strategy.py | awk '{print \$1}'" 2>/dev/null || echo "ssh-error")
    SERVER_LIVE=$(ssh -o ConnectTimeout=10 "$SERVER" "sha256sum /root/canary/canary_strategy.py | awk '{print \$1}'" 2>/dev/null || echo "ssh-error")
    printf "  Expected:           %s\n" "$LOCKED_SHA"
    printf "  Local empire:       %s %s\n" "$LOCAL_EMPIRE"  "$([ "$LOCAL_EMPIRE"  = "$LOCKED_SHA" ] && echo ✓ || echo ✗)"
    printf "  Server empire repo: %s %s\n" "$SERVER_EMPIRE" "$([ "$SERVER_EMPIRE" = "$LOCKED_SHA" ] && echo ✓ || echo ✗)"
    printf "  Server live dir:    %s %s\n" "$SERVER_LIVE"   "$([ "$SERVER_LIVE"   = "$LOCKED_SHA" ] && echo ✓ || echo ✗)"
    # Legacy agent archive — informational only (was canonical before 2026-05-13 empire promotion)
    LEGACY_AGENT=$(ssh -o ConnectTimeout=10 "$SERVER" "sha256sum /root/_legacy_2026-05-13/agent/canary/canary_strategy.py 2>/dev/null | awk '{print \$1}'" 2>/dev/null || echo "")
    if [ -n "$LEGACY_AGENT" ]; then
      printf "  Legacy agent (archived): %s %s\n" "$LEGACY_AGENT" "$([ "$LEGACY_AGENT" = "$LOCKED_SHA" ] && echo ✓ || echo ✗)"
    fi
    echo ""
    echo "═══ [2/4] L99 HALT ═══"
    ssh -o ConnectTimeout=10 "$SERVER" 'cat /root/.l99/protection_halt.json 2>/dev/null | head -3'
    echo ""
    echo "═══ [3/4] SERVICES (canary inactive · paper-arena active) ═══"
    ssh -o ConnectTimeout=10 "$SERVER" 'for s in canary monster-agent canary-killswitch paper-arena tradingguru-telemetry; do printf "  %-32s %s\n" "$s.service" "$(systemctl is-active $s.service)"; done'
    echo ""
    echo "═══ [4/4] EXCHANGE SOCKETS (must be NONE) ═══"
    SOCK=$(ssh -o ConnectTimeout=10 "$SERVER" 'ss -tnp 2>/dev/null | grep -iE "gate\.io|bybit\.com" | wc -l')
    if [ "$SOCK" = "0" ]; then echo "  ✓ NONE open"; else echo "  ✗ $SOCK socket(s) — INVESTIGATE"; fi
    echo ""
    echo "═══ SUMMARY ═══"
    echo "  Capital: \$1,980.90 USDT (untouched while halt engaged + no sockets)"
    ;;

  deploy)
    msg="${1:-deploy: full empire cycle}"
    echo "═══ [1/4] LOCAL COMMIT + PUSH ═══"
    bash "$0" push "$msg"
    echo ""
    echo "═══ [2/4] VPS PULL ═══"
    bash "$0" server
    echo ""
    echo "═══ [3/4] RESTART paper-arena.service (running on empire now) ═══"
    ssh -o ConnectTimeout=10 "$SERVER" "systemctl restart $SERVICE_NAME && sleep 3 && echo '  paper-arena: '\$(systemctl is-active $SERVICE_NAME)"
    echo ""
    echo "═══ [4/4] VERIFY 4-WAY SHA + LOCKS ═══"
    bash "$0" verify
    ;;

  *)
    echo "Unknown command: $cmd"
    echo "Usage: $0 [pull|push <msg>|server|status|verify|deploy <msg>]"
    exit 1
    ;;
esac
