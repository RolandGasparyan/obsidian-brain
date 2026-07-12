#!/bin/bash
# deploy_team_do.sh — Deploy the Champion+Coach TEAM setup on DigitalOcean
# (167.71.24.86) as the SINGLE live engine.
#
# This script:
#   1. STOPS + DISABLES every OTHER real-money engine (single-engine rule)
#   2. Installs champion_battle.py + coach.py + rank_setups.py + liquidate_to_usdt.py
#   3. Installs + starts champion-battle.service + coach.service
#   4. Verifies all 3 Gate.io accounts authenticate from this VPS IP
#
# Run as root on the DigitalOcean VPS:
#   sudo bash deploy_team_do.sh
set -euo pipefail

CANARY=/root/canary
RUNTIME=$CANARY/runtime
REPO=/root/tradingguru-empire
mkdir -p "$RUNTIME"

echo "================================================================"
echo " TRADING GURU — DigitalOcean SINGLE-ENGINE TEAM DEPLOY"
echo " $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================================"

# ── 1. STOP + DISABLE all other real-money engines (single-engine rule) ──────
echo "[1/5] Stopping all OTHER real-money engines (single-engine rule)..."
for svc in canary-battle scalp-battle-live canary-watchdog; do
  systemctl stop    "$svc" 2>/dev/null || true
  systemctl disable "$svc" 2>/dev/null || true
  echo "   stopped+disabled: $svc"
done
# kill any stragglers
pkill -f canary_executor.py   2>/dev/null || true
pkill -f scalp_battle_live.py 2>/dev/null || true
sleep 2

# ── 2. Install code (prefer repo copy, fall back to local files) ─────────────
echo "[2/5] Installing team code into $CANARY ..."
for f in champion_battle.py coach.py rank_setups.py liquidate_to_usdt.py; do
  if [ -f "$REPO/canary/$f" ]; then
    cp -a "$REPO/canary/$f" "$CANARY/$f"
    echo "   installed from repo: $f"
  elif [ -f "./$f" ]; then
    cp -a "./$f" "$CANARY/$f"
    echo "   installed from cwd:  $f"
  else
    echo "   WARNING: $f not found in repo or cwd"
  fi
done

# ── 3. Install systemd units ─────────────────────────────────────────────────
echo "[3/5] Installing systemd services..."
for unit in champion-battle.service coach.service; do
  if [ -f "$REPO/canary/$unit" ]; then
    cp -a "$REPO/canary/$unit" "/etc/systemd/system/$unit"
  elif [ -f "./$unit" ]; then
    cp -a "./$unit" "/etc/systemd/system/$unit"
  fi
  echo "   installed: $unit"
done
systemctl daemon-reload

# ── 4. Verify Gate.io auth from THIS VPS IP ──────────────────────────────────
echo "[4/5] Verifying Gate.io auth for all 3 accounts from this VPS..."
PY=/root/canary/venv/bin/python3
[ -x "$PY" ] || PY=/usr/bin/python3
$PY - <<'PYEOF'
import ccxt
from pathlib import Path
all_ok = True
for acc in ["main", "sub1", "sub2"]:
    kf = Path(f"/root/canary/.api_key_{acc}")
    if not kf.exists():
        print(f"[{acc.upper()}] keyfile MISSING"); all_ok = False; continue
    raw = kf.read_text().strip().split(":", 1)
    if len(raw) != 2:
        print(f"[{acc.upper()}] keyfile malformed"); all_ok = False; continue
    k, s = raw[0].strip(), raw[1].strip()
    ex = ccxt.gate({"apiKey": k, "secret": s, "enableRateLimit": True,
                    "timeout": 15000, "options": {"defaultType": "spot"}})
    try:
        bal = ex.fetch_balance()
        usdt = float(bal.get("USDT", {}).get("free", 0))
        print(f"[{acc.upper()}] PASS  USDT free=${usdt:.2f}")
    except Exception as e:
        all_ok = False
        print(f"[{acc.upper()}] FAIL  {type(e).__name__}: {e}")
print("=== RESULT: ALL 3 ACCOUNTS AUTHENTICATED ===" if all_ok
      else "=== RESULT: AT LEAST ONE ACCOUNT FAILED AUTH (check IP whitelist 167.71.24.86) ===")
PYEOF

# ── 5. Start the team ────────────────────────────────────────────────────────
echo "[5/5] Starting coach + champion-battle..."
systemctl enable coach.service champion-battle.service >/dev/null 2>&1 || true
systemctl restart coach.service
sleep 3
systemctl restart champion-battle.service
sleep 5

echo "----------------------------------------------------------------"
for svc in coach champion-battle; do
  printf "   %-18s " "$svc"; systemctl is-active "$svc"
done
echo "----------------------------------------------------------------"
echo "Coach signals:"
cat "$RUNTIME/coach_signals.json" 2>/dev/null | head -40 || echo "(not written yet)"
echo "----------------------------------------------------------------"
echo "Champion log (last 15 lines):"
tail -15 "$RUNTIME/champion_battle.log" 2>/dev/null || echo "(no log yet)"
echo "================================================================"
echo " DEPLOY COMPLETE — single live engine = champion-battle + coach"
echo "================================================================"
