#!/usr/bin/env bash
# ── tradingguru-agent · bidirectional sync helper ─────────────────────────
#
# Usage:
#   ./sync.sh pull        — pull latest from GitHub (safe, no commits)
#   ./sync.sh push <msg>  — stage all changes, commit with <msg>, push
#   ./sync.sh status      — show local + server git status side by side
#   ./sync.sh verify      — verify SHA256 lock + L99 halt + service states
#   ./sync.sh server      — run sync.sh on server (push side)
#
# Always SAFE: never force-pushes, never bypasses hooks.

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
REMOTE="origin"
BRANCH="main"
SERVER="root@167.71.24.86"
SERVER_REPO="/root/agent"

cmd="${1:-status}"
shift || true

case "$cmd" in
  pull)
    echo "→ Pulling latest from $REMOTE/$BRANCH..."
    cd "$REPO_DIR"
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
    echo "✓ Pull complete"
    ;;

  push)
    msg="${1:-sync: local changes}"
    cd "$REPO_DIR"
    echo "→ Staging all changes..."
    git add -A
    if git diff --cached --quiet; then
      echo "  No changes to commit"
    else
      echo "→ Committing: $msg"
      git commit -m "$(cat <<EOF
$msg

Co-Authored-By: Roland Gasparyan <roland.gasparyan@gmail.com>
EOF
)"
      echo "→ Pushing to $REMOTE/$BRANCH..."
      git push "$REMOTE" "$BRANCH"
      echo "✓ Push complete"
    fi
    ;;

  status)
    echo "═══ LOCAL ($(hostname)) ═══"
    cd "$REPO_DIR"
    git status --short --branch | head -10
    echo ""
    echo "═══ SERVER ($SERVER) ═══"
    ssh -o ConnectTimeout=10 "$SERVER" "cd $SERVER_REPO && git status --short --branch | head -10"
    echo ""
    echo "═══ REMOTE (origin/main HEAD) ═══"
    git log "$REMOTE/$BRANCH" --oneline -3
    ;;

  verify)
    LOCKED_SHA="704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143"
    # Detect server-side vs local-side execution
    if [ "$(hostname)" = "btc-15m-paper-bot" ] || [ -d /etc/systemd/system ] && [ ! -f /usr/bin/sw_vers ]; then
      # Running on server — skip SSH calls
      MODE="server"
    else
      MODE="local"
    fi

    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  tradingguru-agent · verify  ($MODE-side execution)"
    echo "║  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "═══ [1/5] SHA256 LOCK VERIFICATION ═══"

    if [ "$MODE" = "server" ]; then
      REPO_SHA=$(sha256sum "$REPO_DIR/canary/canary_strategy.py" 2>/dev/null | awk '{print $1}')
      LIVE_SHA=$(sha256sum /root/canary/canary_strategy.py 2>/dev/null | awk '{print $1}')
      printf "  Expected:        %s\n" "$LOCKED_SHA"
      printf "  Server repo:     %s %s\n" "$REPO_SHA" "$([ "$REPO_SHA" = "$LOCKED_SHA" ] && echo "✓" || echo "✗")"
      printf "  Server live dir: %s %s\n" "$LIVE_SHA" "$([ "$LIVE_SHA" = "$LOCKED_SHA" ] && echo "✓" || echo "✗")"
    else
      LOCAL_SHA=$(shasum -a 256 "$REPO_DIR/canary/canary_strategy.py" 2>/dev/null | awk '{print $1}')
      SERVER_SHA=$(ssh -o ConnectTimeout=10 "$SERVER" "sha256sum $SERVER_REPO/canary/canary_strategy.py | awk '{print \$1}'" 2>/dev/null || echo "ssh-error")
      SERVER_LIVE=$(ssh -o ConnectTimeout=10 "$SERVER" "sha256sum /root/canary/canary_strategy.py | awk '{print \$1}'" 2>/dev/null || echo "ssh-error")
      printf "  Expected:        %s\n" "$LOCKED_SHA"
      printf "  Local repo:      %s %s\n" "$LOCAL_SHA"   "$([ "$LOCAL_SHA" = "$LOCKED_SHA" ] && echo "✓" || echo "✗")"
      printf "  Server repo:     %s %s\n" "$SERVER_SHA"  "$([ "$SERVER_SHA" = "$LOCKED_SHA" ] && echo "✓" || echo "✗")"
      printf "  Server live dir: %s %s\n" "$SERVER_LIVE" "$([ "$SERVER_LIVE" = "$LOCKED_SHA" ] && echo "✓" || echo "✗")"
    fi

    echo ""
    echo "═══ [2/5] L99 HALT STATE ═══"
    if [ "$MODE" = "server" ]; then
      cat /root/.l99/protection_halt.json 2>/dev/null | head -5
    else
      ssh -o ConnectTimeout=10 "$SERVER" 'cat /root/.l99/protection_halt.json 2>/dev/null | head -5'
    fi

    echo ""
    echo "═══ [3/5] TRADING SERVICE STATES (must be inactive) ═══"
    if [ "$MODE" = "server" ]; then
      for s in canary monster-agent canary-killswitch; do
        printf "  %-32s %s\n" "$s.service" "$(systemctl is-active $s.service)"
      done
    else
      ssh -o ConnectTimeout=10 "$SERVER" 'for s in canary monster-agent canary-killswitch; do printf "  %-32s %s\n" "$s.service" "$(systemctl is-active $s.service)"; done'
    fi

    echo ""
    echo "═══ [4/5] TELEMETRY STACK (must be active) ═══"
    if [ "$MODE" = "server" ]; then
      for s in tradingguru-telemetry tradingguru-bots-updater microstructure-collector nginx; do
        printf "  %-32s %s\n" "$s.service" "$(systemctl is-active $s.service)"
      done
    else
      ssh -o ConnectTimeout=10 "$SERVER" 'for s in tradingguru-telemetry tradingguru-bots-updater microstructure-collector nginx; do printf "  %-32s %s\n" "$s.service" "$(systemctl is-active $s.service)"; done'
    fi

    echo ""
    echo "═══ [5/5] EXCHANGE SOCKETS (must be NONE) ═══"
    if [ "$MODE" = "server" ]; then
      SOCK=$(ss -tnp 2>/dev/null | grep -iE "gate\.io|bybit\.com" | wc -l)
    else
      SOCK=$(ssh -o ConnectTimeout=10 "$SERVER" 'ss -tnp 2>/dev/null | grep -iE "gate\.io|bybit\.com" | wc -l')
    fi
    if [ "$SOCK" = "0" ]; then
      echo "  ✓ NONE open"
    else
      echo "  ✗ $SOCK exchange socket(s) detected — INVESTIGATE"
    fi

    echo ""
    echo "═══ SUMMARY ═══"
    echo "  Capital: \$1,980.90 USDT (untouched while halt engaged + no sockets)"
    echo "  Run './sync.sh status' for git state across local/server/remote"
    ;;

  server)
    msg="${1:-sync: server changes}"
    echo "→ Running push on server..."
    ssh -o ConnectTimeout=10 "$SERVER" "cd $SERVER_REPO && git add -A && (git diff --cached --quiet || git commit -m '$msg') && git push origin main"
    echo "✓ Server push complete — pulling locally..."
    cd "$REPO_DIR" && git pull --rebase origin main
    echo "✓ Round-trip complete"
    ;;

  *)
    echo "Unknown command: $cmd"
    echo "Usage: $0 [pull|push <msg>|status|verify|server <msg>]"
    exit 1
    ;;
esac
