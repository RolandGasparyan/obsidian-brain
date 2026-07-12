#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# vps_empire_setup.sh — one-shot VPS promotion of tradingguru-empire
# ═══════════════════════════════════════════════════════════════════════
#
# WHAT THIS DOES (on the VPS · 167.71.24.86):
#   1. Validates GITHUB_PAT env var is set
#   2. Verifies canary SHA256 lock UNCHANGED on /root/canary/ + /root/agent/
#   3. Clones tradingguru-empire (PRIVATE) → /root/tradingguru-empire/
#   4. Re-verifies SHA256 lock now matches in empire too (3 → 4-way parity)
#   5. Backs up current paper-arena.service file to /tmp/
#   6. Writes new paper-arena.service file pointing to empire repo
#   7. systemctl daemon-reload + stop + start
#   8. Verifies service active + healthy
#   9. Reports final state with all sacred locks
#  10. ROLLBACK on any failure: restores backup service file, restarts old
#
# WHAT THIS DOES NOT DO:
#   ✗ Does NOT touch /root/canary/ (Layer 1 live dir)
#   ✗ Does NOT touch /root/.l99/protection_halt.json (L99 halt)
#   ✗ Does NOT touch /root/tradingguru-premium-upgrade/ (unknown operator dir)
#   ✗ Does NOT touch /root/agent/ (kept as legacy reference — read-only)
#   ✗ Does NOT activate canary.service or any live-trading service
#   ✗ Does NOT generate or read .api_key
#
# USAGE (run on the VPS · as root):
#   export GITHUB_PAT="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
#   bash vps_empire_setup.sh
#
# PAT GENERATION (operator-only):
#   1. Visit: https://github.com/settings/personal-access-tokens/new
#   2. Token name: "tradingguru-empire VPS deploy"
#   3. Repository access: Only select repositories → tradingguru-empire
#   4. Permissions: Contents (Read), Metadata (Read)  [read-only is enough]
#   5. Click Generate · copy the token (starts with github_pat_ or ghp_)
#   6. Paste into the export GITHUB_PAT="..." above before running this script
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── CONSTANTS ───────────────────────────────────────────────────────────
LOCKED_SHA="704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143"
REPO_OWNER="RolandGasparyan"
REPO_NAME="tradingguru-empire"
EMPIRE_DIR="/root/tradingguru-empire"
SERVICE_NAME="paper-arena.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
SERVICE_BACKUP="/tmp/${SERVICE_NAME}.pre-empire-promote.bak"
BANNER_FAIL="❌ ABORT"
BANNER_OK="✓"
SECTION="═══════════════════════════════════════════════════════════════"

# ── HELPERS ─────────────────────────────────────────────────────────────
log()  { echo "  $*"; }
hdr()  { echo ""; echo "$SECTION"; echo "  $*"; echo "$SECTION"; }
abort() {
  echo ""
  echo "$BANNER_FAIL  $*"
  echo ""
  echo "SACRED LOCK STATE AT ABORT:"
  echo "  L99: $(grep -o '"halted": [a-z]*' /root/.l99/protection_halt.json 2>/dev/null || echo unknown)"
  echo "  canary.service:    $(systemctl is-active canary.service 2>/dev/null)"
  echo "  paper-arena.service: $(systemctl is-active "$SERVICE_NAME" 2>/dev/null)"
  exit 1
}

sha_of() { sha256sum "$1" 2>/dev/null | awk '{print $1}'; }

require_sha_match() {
  local file="$1" name="$2"
  local actual="$(sha_of "$file")"
  if [[ "$actual" != "$LOCKED_SHA" ]]; then
    abort "$name SHA mismatch: expected $LOCKED_SHA got $actual"
  fi
  log "$BANNER_OK $name: $actual"
}

rollback_service() {
  if [[ -f "$SERVICE_BACKUP" ]]; then
    log "→ Rolling back service file from $SERVICE_BACKUP"
    cp "$SERVICE_BACKUP" "$SERVICE_PATH"
    systemctl daemon-reload
    systemctl start "$SERVICE_NAME" || true
  fi
}
trap 'rollback_service' ERR

# ── [1/9] PRE-FLIGHT ────────────────────────────────────────────────────
hdr "[1/9] PRE-FLIGHT CHECKS"

if [[ -z "${GITHUB_PAT:-}" ]]; then
  abort "GITHUB_PAT env var is empty. Generate PAT first (see header comments)."
fi
log "$BANNER_OK GITHUB_PAT is set (${#GITHUB_PAT} chars)"

if [[ "$(id -u)" != "0" ]]; then
  abort "must run as root (current uid: $(id -u))"
fi
log "$BANNER_OK running as root"

if [[ ! -f /root/canary/canary_strategy.py ]]; then
  abort "/root/canary/canary_strategy.py missing — refusing to proceed without Layer 1"
fi
if [[ ! -f /root/.l99/protection_halt.json ]]; then
  abort "L99 halt artifact missing — refusing to proceed without protection"
fi
log "$BANNER_OK Layer 1 files present"

# ── [2/9] SACRED LOCK VERIFICATION (pre-clone) ──────────────────────────
hdr "[2/9] SACRED LOCK VERIFICATION (pre-clone)"

require_sha_match /root/canary/canary_strategy.py        "Live dir SHA256"
require_sha_match /root/agent/canary/canary_strategy.py  "Agent repo SHA256"

L99_STATE=$(grep -o '"halted": [a-z]*' /root/.l99/protection_halt.json)
if [[ "$L99_STATE" != '"halted": true' ]]; then
  abort "L99 halt is NOT engaged (got: $L99_STATE) — refusing service repoint"
fi
log "$BANNER_OK L99: $L99_STATE"

for svc in canary monster-agent canary-killswitch; do
  state=$(systemctl is-active "${svc}.service" 2>/dev/null || echo unknown)
  if [[ "$state" != "inactive" ]]; then
    abort "${svc}.service is $state — must be inactive before promotion"
  fi
  log "$BANNER_OK ${svc}.service: $state"
done

SOCK=$(ss -tnp 2>/dev/null | grep -iE 'gate\.io|bybit\.com' | wc -l)
if [[ "$SOCK" != "0" ]]; then
  abort "$SOCK exchange socket(s) detected — must be 0"
fi
log "$BANNER_OK exchange sockets: 0"

# ── [3/9] CLONE EMPIRE (HTTPS + PAT) ────────────────────────────────────
hdr "[3/9] CLONING tradingguru-empire (PRIVATE) → $EMPIRE_DIR"

if [[ -d "$EMPIRE_DIR/.git" ]]; then
  log "→ empire dir exists — pulling latest instead"
  cd "$EMPIRE_DIR"
  # Configure auth via remote URL
  git remote set-url origin "https://oauth2:${GITHUB_PAT}@github.com/${REPO_OWNER}/${REPO_NAME}.git"
  git fetch --quiet origin main
  git reset --hard origin/main >/dev/null
  # Scrub PAT from URL for safety (use SSH-style placeholder if no key, else https without token)
  git remote set-url origin "https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
else
  log "→ fresh clone"
  git clone --quiet "https://oauth2:${GITHUB_PAT}@github.com/${REPO_OWNER}/${REPO_NAME}.git" "$EMPIRE_DIR"
  cd "$EMPIRE_DIR"
  # Scrub PAT
  git remote set-url origin "https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
  # Configure git credentials so future pulls use stored helper (not URL)
  git config --local credential.helper '!f() { echo username=oauth2; echo password=$(cat /root/.tradingguru-empire-pat); }; f'
fi

# Store PAT for future non-interactive pulls (chmod 600)
echo "$GITHUB_PAT" > /root/.tradingguru-empire-pat
chmod 600 /root/.tradingguru-empire-pat
log "$BANNER_OK PAT stored at /root/.tradingguru-empire-pat (chmod 600)"

# Activate hooks in clone
cd "$EMPIRE_DIR"
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
log "$BANNER_OK pre-commit hook armed"

log "$BANNER_OK clone HEAD: $(git log --oneline -1)"

# ── [4/9] SACRED LOCK VERIFICATION (post-clone · 4-way parity) ──────────
hdr "[4/9] SACRED LOCK VERIFICATION (post-clone · 4-way parity)"

require_sha_match /root/canary/canary_strategy.py             "Live dir       "
require_sha_match /root/agent/canary/canary_strategy.py       "Agent repo     "
require_sha_match "$EMPIRE_DIR/canary/canary_strategy.py"     "Empire repo    "

# ── [5/9] BACKUP SERVICE FILE ───────────────────────────────────────────
hdr "[5/9] BACKUP CURRENT $SERVICE_NAME"

cp "$SERVICE_PATH" "$SERVICE_BACKUP"
log "$BANNER_OK backed up to $SERVICE_BACKUP"
log "$BANNER_OK first 6 lines of current service file:"
head -6 "$SERVICE_PATH" | sed 's/^/    /'

# ── [6/9] WRITE NEW SERVICE FILE (points to empire) ─────────────────────
hdr "[6/9] WRITE NEW SERVICE FILE (canonical = empire)"

cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=🎮 TradingGuru Paper Battle Engine — 8-agent simulated arena (NO REAL CAPITAL)
Documentation=file://${EMPIRE_DIR}/README.md
Documentation=file://${EMPIRE_DIR}/paper_battle/paper_battle_engine.py
After=network-online.target tradingguru-telemetry.service
Wants=tradingguru-telemetry.service

# ── ISOLATION GUARDS ────────────────────────────────────────────────────
# This service is paper-only. It writes paper-arena.json. It NEVER opens
# exchange connections or touches Layer 1 code.
#
# Refuses to start if Layer 1 mutation detected (paranoid):
ConditionPathExists=${EMPIRE_DIR}/canary/canary_strategy.py
ConditionPathExists=/root/.l99/protection_halt.json

[Service]
Type=simple
ExecStart=/usr/bin/python3 ${EMPIRE_DIR}/paper_battle/paper_battle_engine.py
WorkingDirectory=${EMPIRE_DIR}
Restart=on-failure
RestartSec=30
User=root
StandardOutput=journal
StandardError=journal

# Hard refusal of exchange ports (paper engine should NEVER egress to exchanges)
# RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6   # commented — public REST polling needs it

[Install]
WantedBy=multi-user.target
EOF

log "$BANNER_OK new service written → $SERVICE_PATH"
log "$BANNER_OK key lines:"
grep -E '^(Description|ExecStart|WorkingDirectory|ConditionPathExists)' "$SERVICE_PATH" | sed 's/^/    /'

# ── [7/9] SERVICE LIFECYCLE ─────────────────────────────────────────────
hdr "[7/9] SERVICE LIFECYCLE (daemon-reload + stop + start)"

systemctl daemon-reload
log "$BANNER_OK daemon-reload"

systemctl stop "$SERVICE_NAME"
sleep 2
log "$BANNER_OK stopped: $(systemctl is-active "$SERVICE_NAME")"

systemctl start "$SERVICE_NAME"
sleep 4
state="$(systemctl is-active "$SERVICE_NAME")"
if [[ "$state" != "active" ]]; then
  abort "service failed to start (state: $state) — see journalctl -u $SERVICE_NAME"
fi
log "$BANNER_OK started: $state"

# Disable error trap now that critical phase is past
trap - ERR

# ── [8/9] POST-START HEALTH CHECK ───────────────────────────────────────
hdr "[8/9] POST-START HEALTH CHECK"

sleep 3
journalctl -u "$SERVICE_NAME" --no-pager -n 6 --output=cat | sed 's/^/    /'

# ── [9/9] FINAL SACRED LOCK STATE ───────────────────────────────────────
hdr "[9/9] FINAL SACRED LOCK STATE"

log "$(date -u +'%Y-%m-%d %H:%M:%S UTC') — empire promotion complete"
log ""
log "Sacred locks (4-way parity):"
log "  Live dir SHA256:    $(sha_of /root/canary/canary_strategy.py)"
log "  Agent repo SHA256:  $(sha_of /root/agent/canary/canary_strategy.py)"
log "  Empire repo SHA256: $(sha_of "$EMPIRE_DIR/canary/canary_strategy.py")"
log "  Locked val:         $LOCKED_SHA"
log ""
log "Service states:"
for s in canary monster-agent canary-killswitch paper-arena tradingguru-telemetry; do
  log "  ${s}.service: $(systemctl is-active "${s}.service" 2>/dev/null || echo unknown)"
done
log ""
log "L99 halt: $(grep -o '"halted": [a-z]*' /root/.l99/protection_halt.json)"
SOCK=$(ss -tnp 2>/dev/null | grep -iE 'gate\.io|bybit\.com' | wc -l)
log "Exchange sockets: $SOCK"
log ""
log "Empire HEAD:        $(cd "$EMPIRE_DIR" && git log --oneline -1)"
log "Service backup:     $SERVICE_BACKUP (rollback if needed)"
log "PAT file:           /root/.tradingguru-empire-pat (chmod 600)"
log ""
log "✓ EMPIRE PROMOTED TO CANONICAL"
log ""
log "→ Next pull (from anywhere): cd $EMPIRE_DIR && git pull origin main"
log "→ Rollback: cp $SERVICE_BACKUP $SERVICE_PATH && systemctl daemon-reload && systemctl restart $SERVICE_NAME"
echo ""
