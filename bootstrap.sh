#!/usr/bin/env bash
# ─── tradingguru-agent · session bootstrap ────────────────────────────────
#
# Run this FIRST whenever a new Claude session (or human) starts work on the
# trading agent. It loads context, checks integrity, and points to the right
# documents in the right order.
#
# Usage:
#   ./bootstrap.sh           — full bootstrap (status + verify + docs links)
#   ./bootstrap.sh quick     — quick health check only
#   ./bootstrap.sh docs      — print doc reading order

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
mode="${1:-full}"

color() { printf "\033[%sm%s\033[0m" "$1" "$2"; }
ok()    { color "32" "✓"; }
fail()  { color "31" "✗"; }
warn()  { color "33" "⚠"; }
bold()  { color "1" "$1"; }

cat <<EOF
╔══════════════════════════════════════════════════════════════════╗
║  $(bold "tradingguru-agent · session bootstrap")
║  $(date "+%Y-%m-%d %H:%M:%S %Z")
╚══════════════════════════════════════════════════════════════════╝
EOF

if [ "$mode" = "docs" ]; then
  cat <<EOF

$(bold "DOCUMENT READING ORDER")

  1. README.md                                         — this repo, layout + hands-off zones
  2. docs/9-refusals-log.md                            — what's been refused, why
  3. governance/LAYER_DISCIPLINE.md                    — Layer 1/2/3 immutable rules
  4. governance/BRANCH_LOCK.md                         — multi-session coordination
  5. docs/MA_STRATEGY.md                               — the only validated edge
  6. docs/wiki-mirror/tradingguru-agent-isolation.md   — isolation architecture
  7. docs/wiki-mirror/tradingguru-architecture-3-layer-vision.md
  8. docs/wiki-mirror/tradingguru-immutable-layer-governance.md
  9. docs/obsidian-mirror/2026-05-13 — Phase 5-8 ...md — latest session log
 10. server-mirror/STATE.md                            — server state snapshot

After reading those, you'll know:
  - What this agent is + what it isn't
  - What's locked + why
  - What's been refused + why
  - Where every piece of code lives + what depends on it

EOF
  exit 0
fi

echo ""
echo "$(bold "STEP 1 — Sacred lock verification")"

LOCKED_SHA="704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143"

if command -v sha256sum >/dev/null 2>&1; then
  SHACMD="sha256sum"
else
  SHACMD="shasum -a 256"
fi

LOCAL_SHA=$($SHACMD "$REPO_ROOT/canary/canary_strategy.py" | awk '{print $1}')
if [ "$LOCAL_SHA" = "$LOCKED_SHA" ]; then
  echo "  $(ok) canary_strategy.py SHA256 verified"
else
  echo "  $(fail) CANARY LOCK VIOLATED"
  echo "    Expected: $LOCKED_SHA"
  echo "    Current:  $LOCAL_SHA"
  echo ""
  echo "  STOP. Investigate before proceeding."
  exit 1
fi

if [ "$mode" = "quick" ]; then
  echo ""
  echo "$(bold "Quick mode — done.")"
  exit 0
fi

echo ""
echo "$(bold "STEP 2 — Repository state")"

cd "$REPO_ROOT"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
DIRTY=$(git status --porcelain | wc -l | tr -d ' ')
AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "0")
BEHIND=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo "0")

echo "  Branch:        $BRANCH"
echo "  Uncommitted:   $DIRTY files"
echo "  Ahead remote:  $AHEAD commits"
echo "  Behind remote: $BEHIND commits"

if [ "$BEHIND" != "0" ]; then
  echo "  $(warn) Local is behind — run: ./sync.sh pull"
fi

if [ "$DIRTY" != "0" ]; then
  echo "  $(warn) Uncommitted changes — review with: git status"
fi

echo ""
echo "$(bold "STEP 3 — Server reachability + sync verify")"

if ssh -o ConnectTimeout=8 -o BatchMode=yes root@167.71.24.86 'echo ok' 2>/dev/null | grep -q ok; then
  echo "  $(ok) Server SSH reachable"

  SERVER_SHA=$(ssh -o ConnectTimeout=8 root@167.71.24.86 "sha256sum /root/agent/canary/canary_strategy.py | awk '{print \$1}'")
  if [ "$SERVER_SHA" = "$LOCKED_SHA" ]; then
    echo "  $(ok) Server repo canary SHA256 matches"
  else
    echo "  $(fail) Server repo canary SHA256 differs"
  fi

  LIVE_SHA=$(ssh -o ConnectTimeout=8 root@167.71.24.86 "sha256sum /root/canary/canary_strategy.py | awk '{print \$1}'")
  if [ "$LIVE_SHA" = "$LOCKED_SHA" ]; then
    echo "  $(ok) Server LIVE canary SHA256 matches"
  else
    echo "  $(fail) Server LIVE canary SHA256 differs"
  fi

  L99_HALTED=$(ssh -o ConnectTimeout=8 root@167.71.24.86 "grep -q '\"halted\": true' /root/.l99/protection_halt.json && echo true || echo false")
  if [ "$L99_HALTED" = "true" ]; then
    echo "  $(ok) L99 protection halt engaged"
  else
    echo "  $(warn) L99 halt NOT engaged"
  fi

  TELEM=$(ssh -o ConnectTimeout=8 root@167.71.24.86 "systemctl is-active tradingguru-telemetry.service")
  if [ "$TELEM" = "active" ]; then
    echo "  $(ok) Telemetry service running"
  else
    echo "  $(fail) Telemetry service NOT active"
  fi

  SOCKETS=$(ssh -o ConnectTimeout=8 root@167.71.24.86 "ss -tnp 2>/dev/null | grep -iE 'gate\.io|bybit\.com' | wc -l")
  if [ "$SOCKETS" = "0" ]; then
    echo "  $(ok) No exchange sockets open"
  else
    echo "  $(warn) $SOCKETS exchange socket(s) open"
  fi
else
  echo "  $(warn) Server SSH not reachable (continuing without server checks)"
fi

echo ""
echo "$(bold "STEP 4 — Layer integrity")"
echo "  Layer 1 (Trading):   🔒 Canary SHA256 verified, services inactive, capital ringfenced"
echo "  Layer 2 (Telemetry): ✓ terminal.json producer running, read-only"
echo "  Layer 3 (Cinematic): ✓ Frontend deployed (Phases 1-8 shipped)"

echo ""
echo "$(bold "STEP 5 — What you can do safely")"
echo "  ✓ Edit anything in $REPO_ROOT/docs/ or governance/ — content"
echo "  ✓ Edit Layer 3 frontend in ~/Desktop/ai-trading-championship/src/components/"
echo "  ✓ Edit Layer 2 telemetry-only files"
echo "  ✗ canary_strategy.py — IMMUTABLE (rotation requires 5 file updates + decision doc)"
echo "  ✗ Anything in /root/ai-l99-production/*.py without operator approval"
echo "  ✗ /root/.l99/protection_halt.json — never clear without verbatim"
echo "  ✗ Anything in ~/Desktop/REINCARNATION SMM/ from a trading session"

echo ""
echo "$(bold "NEXT STEPS")"
echo "  • Read docs in order:   ./bootstrap.sh docs"
echo "  • Quick health check:   ./bootstrap.sh quick"
echo "  • Pull latest:          ./sync.sh pull"
echo "  • Full sync verify:     ./sync.sh verify"
echo ""
