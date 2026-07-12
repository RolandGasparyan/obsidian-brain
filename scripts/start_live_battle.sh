#!/bin/bash
# ============================================================
# TRADING GURU — 3-ACCOUNT LIVE BATTLE ENGINE
# Reads Gate.io keys from /root/canary/ and starts the battle
# Run as root on VPS: bash /root/tradingguru-empire/scripts/start_live_battle.sh
# ============================================================
set -euo pipefail

REPO_DIR="/root/tradingguru-empire"
CANARY_DIR="/root/canary"
LOG_DIR="/var/log/trading-guru"
SERVICE_NAME="trading-guru-battle"
VENV_DIR="${REPO_DIR}/venv"
# Metaworld API — heartbeat endpoint (update with your published domain)
METAWORLD_URL="${METAWORLD_URL:-https://trading-guru-metaworld.manus.space}"
HEARTBEAT_URL="${METAWORLD_URL}/api/trpc/battle.heartbeat"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   TRADING GURU — LIVE BATTLE ENGINE DEPLOYER        ║"
echo "║   3 Gate.io Accounts · SHORT-ONLY · GODS LEVEL      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Verify canary key files exist ──────────────────────────────────────────
echo "▸ [1/7] Checking Gate.io key files..."
for acc in main sub1 sub2; do
    KEY_FILE="${CANARY_DIR}/.api_key_${acc}"
    if [[ ! -f "$KEY_FILE" ]]; then
        echo "  ✗ MISSING: ${KEY_FILE}"
        echo "  Run: printf 'YOUR_API_KEY\nYOUR_API_SECRET\n' > ${KEY_FILE}"
        exit 1
    fi
    LINES=$(wc -l < "$KEY_FILE" | tr -d ' ')
    if [[ "$LINES" -lt 2 ]]; then
        echo "  ✗ INVALID: ${KEY_FILE} must have 2 lines (key + secret)"
        exit 1
    fi
    echo "  ✓ ${acc}: ${KEY_FILE} (${LINES} lines)"
done

# ── 2. Read keys into env vars ─────────────────────────────────────────────────
echo ""
echo "▸ [2/7] Loading credentials..."
export GATE_MAIN_API_KEY=$(sed -n '1p' "${CANARY_DIR}/.api_key_main" | tr -d '[:space:]')
export GATE_MAIN_API_SECRET=$(sed -n '2p' "${CANARY_DIR}/.api_key_main" | tr -d '[:space:]')
export GATE_SUB1_API_KEY=$(sed -n '1p' "${CANARY_DIR}/.api_key_sub1" | tr -d '[:space:]')
export GATE_SUB1_API_SECRET=$(sed -n '2p' "${CANARY_DIR}/.api_key_sub1" | tr -d '[:space:]')
export GATE_SUB2_API_KEY=$(sed -n '1p' "${CANARY_DIR}/.api_key_sub2" | tr -d '[:space:]')
export GATE_SUB2_API_SECRET=$(sed -n '2p' "${CANARY_DIR}/.api_key_sub2" | tr -d '[:space:]')

# Validate keys are not placeholder
for VAR in GATE_MAIN_API_KEY GATE_MAIN_API_SECRET GATE_SUB1_API_KEY GATE_SUB1_API_SECRET GATE_SUB2_API_KEY GATE_SUB2_API_SECRET; do
    VAL="${!VAR}"
    if [[ "$VAL" == "YOUR_"* ]] || [[ -z "$VAL" ]]; then
        echo "  ✗ ${VAR} is still a placeholder or empty. Please set real Gate.io credentials."
        exit 1
    fi
    echo "  ✓ ${VAR}: ${VAL:0:8}... (${#VAL} chars)"
done

# ── 3. Setup Python venv ───────────────────────────────────────────────────────
echo ""
echo "▸ [3/7] Setting up Python environment..."
cd "$REPO_DIR"
if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    echo "  ✓ Created venv at ${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
pip install -q ccxt openai requests python-dotenv 2>&1 | tail -3
echo "  ✓ Dependencies installed"

# ── 4. Create log directory ────────────────────────────────────────────────────
echo ""
echo "▸ [4/7] Setting up log directory..."
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"
echo "  ✓ Logs will be written to ${LOG_DIR}"

# ── 5. Write heartbeat sidecar script ─────────────────────────────────────────
echo ""
echo "▸ [5/7] Installing heartbeat sidecar..."
cat > "/usr/local/bin/trading-guru-heartbeat.sh" << 'HEARTBEAT_EOF'
#!/bin/bash
# Sends a heartbeat ping to the Metaworld API every 30 seconds
METAWORLD_URL="${METAWORLD_URL:-https://trading-guru-metaworld.manus.space}"
HEARTBEAT_URL="${METAWORLD_URL}/api/trpc/battle.heartbeat"
SERVICE_NAME="trading-guru-battle"

while true; do
    STATUS=$(systemctl is-active "${SERVICE_NAME}" 2>/dev/null || echo "stopped")
    if [[ "$STATUS" == "active" ]]; then
        HB_STATUS="running"
        MSG="Battle engine active — $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    else
        HB_STATUS="stopped"
        MSG="Battle engine stopped — systemd status: ${STATUS}"
    fi

    curl -s -X POST "${HEARTBEAT_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"json\":{\"serviceId\":\"trading-guru-battle\",\"status\":\"${HB_STATUS}\",\"message\":\"${MSG}\"}}" \
        --max-time 10 \
        --retry 2 \
        -o /dev/null 2>/dev/null || true

    sleep 30
done
HEARTBEAT_EOF
chmod +x "/usr/local/bin/trading-guru-heartbeat.sh"

# Install heartbeat as a systemd service
cat > "/etc/systemd/system/trading-guru-heartbeat.service" << EOF
[Unit]
Description=Trading Guru — Metaworld Heartbeat Sidecar
After=network-online.target ${SERVICE_NAME}.service
Wants=network-online.target

[Service]
Type=simple
User=root
Environment=METAWORLD_URL=${METAWORLD_URL}
ExecStart=/usr/local/bin/trading-guru-heartbeat.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "trading-guru-heartbeat"
echo "  ✓ Heartbeat sidecar installed (pings Metaworld every 30s)"

# ── 6. Write battle engine systemd service ────────────────────────────────────
echo ""
echo "▸ [6/7] Installing battle engine systemd service..."

cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Trading Guru — 3-Account Live Battle Engine
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${REPO_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=GATE_MAIN_API_KEY=${GATE_MAIN_API_KEY}
Environment=GATE_MAIN_API_SECRET=${GATE_MAIN_API_SECRET}
Environment=GATE_SUB1_API_KEY=${GATE_SUB1_API_KEY}
Environment=GATE_SUB1_API_SECRET=${GATE_SUB1_API_SECRET}
Environment=GATE_SUB2_API_KEY=${GATE_SUB2_API_KEY}
Environment=GATE_SUB2_API_SECRET=${GATE_SUB2_API_SECRET}
ExecStart=${VENV_DIR}/bin/python ${REPO_DIR}/run_championship.py --mode live --accounts main,sub1,sub2
StandardOutput=append:${LOG_DIR}/battle.log
StandardError=append:${LOG_DIR}/battle-error.log
Restart=always
RestartSec=15
MemoryMax=1G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
echo "  ✓ Battle engine service installed and enabled"

# ── 7. Start both services ─────────────────────────────────────────────────────
echo ""
echo "▸ [7/7] Starting live battle + heartbeat sidecar..."
systemctl restart "${SERVICE_NAME}"
systemctl restart "trading-guru-heartbeat"
sleep 3

BATTLE_STATUS=$(systemctl is-active "${SERVICE_NAME}" 2>/dev/null || echo "unknown")
HB_STATUS=$(systemctl is-active "trading-guru-heartbeat" 2>/dev/null || echo "unknown")

if [[ "$BATTLE_STATUS" == "active" ]]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║   ✅  LIVE BATTLE STARTED SUCCESSFULLY!             ║"
    echo "║                                                      ║"
    echo "║   Battle engine:  ACTIVE                            ║"
    echo "║   Heartbeat:      ${HB_STATUS}                      ║"
    echo "║   Metaworld:      ${METAWORLD_URL}                  ║"
    echo "║   Logs:           ${LOG_DIR}/battle.log             ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    echo "  Monitor battle:    journalctl -u ${SERVICE_NAME} -f"
    echo "  Monitor heartbeat: journalctl -u trading-guru-heartbeat -f"
    echo "  Stop battle:       systemctl stop ${SERVICE_NAME}"
    echo "  View logs:         tail -f ${LOG_DIR}/battle.log"
    echo ""
    echo "  The Metaworld Arena will show BATTLE ENGINE: RUNNING within 30s."
    echo "  URL: ${METAWORLD_URL}"

    # Send immediate first heartbeat
    curl -s -X POST "${HEARTBEAT_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"json\":{\"serviceId\":\"trading-guru-battle\",\"status\":\"running\",\"message\":\"Battle engine started successfully — 3 accounts active\"}}" \
        --max-time 10 -o /dev/null 2>/dev/null && echo "  ✓ Initial heartbeat sent to Metaworld" || echo "  ⚠ Could not send initial heartbeat (will retry in 30s)"
else
    echo ""
    echo "  ⚠ Battle engine status: ${BATTLE_STATUS}"
    echo "  Check logs: journalctl -u ${SERVICE_NAME} -n 30"
    journalctl -u "${SERVICE_NAME}" -n 20 --no-pager 2>/dev/null || true

    # Send degraded heartbeat
    curl -s -X POST "${HEARTBEAT_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"json\":{\"serviceId\":\"trading-guru-battle\",\"status\":\"degraded\",\"message\":\"Battle engine failed to start — status: ${BATTLE_STATUS}\"}}" \
        --max-time 10 -o /dev/null 2>/dev/null || true
fi
