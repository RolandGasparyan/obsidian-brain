#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# manus_sync.sh — Manus Sandbox ↔ GitHub ↔ VPS sync helper
# ═══════════════════════════════════════════════════════════════════════
#
# Usage:
#   ./manus_sync.sh pull          Pull latest from GitHub origin/main
#   ./manus_sync.sh push <msg>    Stage + commit + push to GitHub
#   ./manus_sync.sh status        Show local git state
#   ./manus_sync.sh log           Show last 10 commits
#
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REMOTE="origin"
BRANCH="main"

cmd="${1:-status}"
shift || true

case "$cmd" in
  pull)
    cd "$REPO_DIR"
    echo "→ Fetching latest from $REMOTE/$BRANCH..."
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
    echo "✓ Pull complete — now at: $(git log --oneline -1)"
    ;;

  push)
    msg="${1:-MANUS SYNC: $(date '+%Y%m%d_%H%M%S')}"
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
      echo "✓ Push complete — $(git log --oneline -1)"
    fi
    ;;

  status)
    echo "═══ SANDBOX GIT STATUS ═══"
    cd "$REPO_DIR"
    echo "Branch: $(git branch --show-current)"
    echo "Latest: $(git log --oneline -1)"
    echo "Remote: $(git remote get-url origin)"
    echo ""
    git status --short --branch | head -20
    echo ""
    echo "═══ RECENT COMMITS ═══"
    git log --oneline -5
    ;;

  log)
    cd "$REPO_DIR"
    git log --oneline -10
    ;;

  *)
    echo "Usage: $0 {pull|push [msg]|status|log}"
    exit 1
    ;;
esac
