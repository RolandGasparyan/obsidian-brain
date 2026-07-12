#!/usr/bin/env bash
# install_balances_api.sh — Deploy the canary balances API on the DO VPS.
#
# WHAT IT DOES (idempotent):
#   1. Drops balances_api.py into /root/canary/
#   2. Installs flask via pip if missing
#   3. Creates systemd unit `canary-balances-api`
#   4. Opens UFW port 8090
#   5. Enables + starts the service and verifies /healthz + /api/balances
#
# RUN ON THE DO VPS (167.71.24.86):
#     curl -fsSL "https://...balances_api.py-url..." -o /root/canary/balances_api.py
#     curl -fsSL "https://...install_balances_api.sh-url..." | sudo bash
# OR (recommended) scp both files first, then `sudo bash install_balances_api.sh`.
set -euo pipefail

PORT="${BALANCES_PORT:-8090}"
DEST="/root/canary"
SCRIPT="${DEST}/balances_api.py"
UNIT="/etc/systemd/system/canary-balances-api.service"

if [[ $EUID -ne 0 ]]; then
  echo "This installer must run as root (sudo bash install_balances_api.sh)." >&2
  exit 1
fi

if [[ ! -f "${SCRIPT}" ]]; then
  echo "Expected balances_api.py at ${SCRIPT} — copy it there first." >&2
  exit 2
fi

echo "[1/5] Ensuring Python + Flask are present"
python3 -m pip install --quiet --upgrade flask >/dev/null 2>&1 || \
  python3 -m pip install --quiet --upgrade --break-system-packages flask >/dev/null

echo "[2/5] Verifying canary key files exist"
for f in .api_key_main .api_key_sub1 .api_key_sub2; do
  if [[ ! -s "${DEST}/${f}" ]]; then
    echo "Missing or empty key file: ${DEST}/${f}" >&2
    exit 3
  fi
  chmod 600 "${DEST}/${f}"
done

echo "[3/5] Writing systemd unit ${UNIT}"
cat > "${UNIT}" <<UNIT
[Unit]
Description=Canary Balances API (TITAN/VELOCITY/SENTINEL real-time USDT)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${DEST}
Environment=BALANCES_PORT=${PORT}
Environment=CANARY_KEY_DIR=${DEST}
ExecStart=/usr/bin/python3 -u ${SCRIPT}
Restart=always
RestartSec=5
# Read-only deployment — the service only signs requests, never writes anything.
ProtectSystem=full
NoNewPrivileges=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now canary-balances-api

echo "[4/5] Opening UFW port ${PORT}/tcp"
if command -v ufw >/dev/null 2>&1; then
  ufw allow ${PORT}/tcp >/dev/null || true
fi

echo "[5/5] Smoke test"
sleep 2
echo -n "  /healthz       -> "
curl -fsS -m 5 "http://127.0.0.1:${PORT}/healthz" | head -c 80 ; echo
echo -n "  /api/balances  -> "
curl -fsS -m 8 "http://127.0.0.1:${PORT}/api/balances" | head -c 240 ; echo

echo
echo "Done. Public endpoint: http://167.71.24.86:${PORT}/api/balances"
echo "If you do not want this endpoint to be publicly reachable, restrict UFW"
echo "to allow only the GCP VPS IP (34.139.162.200) instead of all of 0.0.0.0/0."
