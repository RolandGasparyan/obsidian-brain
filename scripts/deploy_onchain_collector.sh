#!/bin/bash
# deploy_onchain_collector.sh
#
# Single-shot VPS deployment of onchain-collector.service.
#
# Usage on VPS (after rsync of project repo):
#   sudo ./scripts/deploy_onchain_collector.sh /path/to/env-file
#
# Or interactively:
#   sudo ./scripts/deploy_onchain_collector.sh
#   (will prompt for keys if env file not given)
#
# Honors discipline:
#   - Keys saved to /etc/default/onchain-collector with mode 0600 (root-only)
#   - Service runs as dedicated unprivileged user (configured in unit file)
#   - No keys logged or printed in script output
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="/etc/default/onchain-collector"
SERVICE_NAME="onchain-collector.service"
UNIT_SRC="${REPO_ROOT}/systemd/${SERVICE_NAME}"

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: must run as root (sudo). Aborting."
    exit 1
fi

if [[ ! -f "${UNIT_SRC}" ]]; then
    echo "ERROR: ${UNIT_SRC} not found. Run from project root."
    exit 1
fi

# ─────────────────────────────────────────────
# Step 1 — env file (3 API keys)
# ─────────────────────────────────────────────

if [[ -n "${1:-}" && -f "${1}" ]]; then
    echo "Step 1: copying env file from ${1}"
    cp "${1}" "${ENV_FILE}"
else
    echo "Step 1: prompt for API keys"
    if [[ -t 0 ]]; then
        echo "Paste each key on its own line. CTRL+D when done."
        echo "Expected vars: CRYPTOQUANT_API_KEY GLASSNODE_API_KEY WHALE_ALERT_API_KEY"
        echo ""
        cat > "${ENV_FILE}.tmp"
        mv "${ENV_FILE}.tmp" "${ENV_FILE}"
    else
        echo "ERROR: no env file argument and not running in TTY. Aborting."
        exit 1
    fi
fi

# Lock down permissions
chown root:root "${ENV_FILE}"
chmod 600 "${ENV_FILE}"
echo "  Permissions: $(stat -c '%a %U:%G' "${ENV_FILE}")"

# Validate required keys present (without printing values)
for key in CRYPTOQUANT_API_KEY GLASSNODE_API_KEY WHALE_ALERT_API_KEY; do
    if grep -q "^${key}=" "${ENV_FILE}"; then
        len=$(grep "^${key}=" "${ENV_FILE}" | head -1 | cut -d= -f2- | wc -c)
        echo "  ${key}: present (${len} chars)"
    else
        echo "  ⚠ ${key}: MISSING"
    fi
done

# ─────────────────────────────────────────────
# Step 2 — install systemd unit
# ─────────────────────────────────────────────

echo ""
echo "Step 2: install systemd unit"
cp "${UNIT_SRC}" "/etc/systemd/system/${SERVICE_NAME}"
chmod 644 "/etc/systemd/system/${SERVICE_NAME}"
systemctl daemon-reload
echo "  Unit installed at /etc/systemd/system/${SERVICE_NAME}"

# ─────────────────────────────────────────────
# Step 3 — start + enable
# ─────────────────────────────────────────────

echo ""
echo "Step 3: start + enable service"
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"
sleep 3

# ─────────────────────────────────────────────
# Step 4 — health check
# ─────────────────────────────────────────────

echo ""
echo "Step 4: health check"
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo "  ✅ Service ACTIVE"
    systemctl status "${SERVICE_NAME}" --no-pager -l | head -10
else
    echo "  ❌ Service FAILED to start"
    journalctl -u "${SERVICE_NAME}" -n 20 --no-pager
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ONCHAIN-COLLECTOR DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════"
echo "  Service:  ${SERVICE_NAME}  (active)"
echo "  Env:      ${ENV_FILE}      (mode 0600)"
echo "  Logs:     journalctl -u ${SERVICE_NAME} -f"
echo "  Status:   systemctl status ${SERVICE_NAME}"
echo ""
echo "  Next: verify first parquet write within 60 minutes"
echo "    python3 verify_onchain_first_hour.py"
echo "═══════════════════════════════════════════════════"
