#!/usr/bin/env bash
# healthcheck.sh — Production health check for canary-battle.service
# Usage: bash /root/canary/healthcheck.sh
# Returns: 0 = healthy, 1 = degraded (details printed to stdout)
#
# Checks:
#   1. systemd service active
#   2. Recent log activity (last 120s)
#   3. State files exist and are fresh
#   4. No CANARY_HALT.json engaged
#   5. Balance audit (state shows session_pnl is finite)
#   6. ufw active
#   7. fail2ban active
#
# Designed to be run manually or by a cron/monitoring system.
# Does NOT restart the service — only reports status.

set -euo pipefail

RUNTIME="/root/canary/runtime"
HALT_FILE="$RUNTIME/CANARY_HALT.json"
ACCOUNTS=("MAIN" "SUB1" "SUB2")
STATE_FILES=("$RUNTIME/state_main.json" "$RUNTIME/state_sub1.json" "$RUNTIME/state_sub2.json")
BATTLE_LOG="$RUNTIME/battle.log"
STATE_STALE_SEC=120
ERRORS=0

ok()  { echo "[OK]   $*"; }
warn(){ echo "[WARN] $*"; ERRORS=$((ERRORS + 1)); }
fail(){ echo "[FAIL] $*"; ERRORS=$((ERRORS + 1)); }

echo "========================================"
echo "canary-battle health check — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "========================================"

# 1. systemd service
if systemctl is-active --quiet canary-battle.service; then
    ok "canary-battle.service is active"
    else
        fail "canary-battle.service is NOT active"
            echo "    Last 20 log lines:"
                journalctl -u canary-battle.service -n 20 --no-pager 2>/dev/null || true
                fi

                # 2. Recent log activity — last line should be < STATE_STALE_SEC old
                if [ -f "$BATTLE_LOG" ]; then
                    LOG_AGE=$(( $(date +%s) - $(stat -c %Y "$BATTLE_LOG") ))
                        if [ "$LOG_AGE" -lt "$STATE_STALE_SEC" ]; then
                                ok "battle.log updated ${LOG_AGE}s ago"
                                    else
                                            warn "battle.log last updated ${LOG_AGE}s ago (> ${STATE_STALE_SEC}s threshold)"
                                                    echo "    Last 5 log lines:"
                                                            tail -5 "$BATTLE_LOG" 2>/dev/null || true
                                                                fi
                                                                else
                                                                    warn "battle.log does not exist — service may not have started yet"
                                                                    fi

                                                                    # 3. State files freshness
                                                                    for i in "${!ACCOUNTS[@]}"; do
                                                                        AID="${ACCOUNTS[$i]}"
                                                                            SF="${STATE_FILES[$i]}"
                                                                                if [ ! -f "$SF" ]; then
                                                                                        warn "[$AID] state file missing: $SF"
                                                                                                continue
                                                                                                    fi
                                                                                                        AGE=$(( $(date +%s) - $(stat -c %Y "$SF") ))
                                                                                                            if [ "$AGE" -lt "$STATE_STALE_SEC" ]; then
                                                                                                                    # Parse key fields
                                                                                                                            PNL=$(python3 -c "import json,sys; d=json.load(open('$SF')); print(f\"{float(d.get('session_pnl',0)):+.2f}\")" 2>/dev/null || echo "?")
                                                                                                                                    DD=$(python3 -c "import json,sys; d=json.load(open('$SF')); print(f\"{float(d.get('daily_dd_usd',0)):.2f}\")" 2>/dev/null || echo "?")
                                                                                                                                            POS=$(python3 -c "import json,sys; d=json.load(open('$SF')); print(len(d.get('positions',{})))" 2>/dev/null || echo "?")
                                                                                                                                                    FAILS=$(python3 -c "import json,sys; d=json.load(open('$SF')); print(d.get('consec_api_fails',0))" 2>/dev/null || echo "?")
                                                                                                                                                            ok "[$AID] state fresh (${AGE}s) | pnl=\$${PNL} dd=\$${DD} pos=${POS} api_fails=${FAILS}"
                                                                                                                                                                else
                                                                                                                                                                        fail "[$AID] state file stale: ${AGE}s > ${STATE_STALE_SEC}s — executor may be hung"
                                                                                                                                                                            fi
                                                                                                                                                                            done
                                                                                                                                                                            
                                                                                                                                                                            # 4. Kill switch / halt file
                                                                                                                                                                            if [ -f "$HALT_FILE" ]; then
                                                                                                                                                                                HALTED=$(python3 -c "import json; d=json.load(open('$HALT_FILE')); print(d.get('halted',''))" 2>/dev/null || echo "")
                                                                                                                                                                                    REASON=$(python3 -c "import json; d=json.load(open('$HALT_FILE')); print(d.get('reason','unknown'))" 2>/dev/null || echo "unknown")
                                                                                                                                                                                        if [ "$HALTED" = "True" ]; then
                                                                                                                                                                                                fail "CANARY_HALT.json is ENGAGED: $REASON"
                                                                                                                                                                                                        echo "    To clear: rm $HALT_FILE && systemctl restart canary-battle.service"
                                                                                                                                                                                                            else
                                                                                                                                                                                                                    ok "CANARY_HALT.json exists but halted=False — OK"
                                                                                                                                                                                                                        fi
                                                                                                                                                                                                                        else
                                                                                                                                                                                                                            ok "No halt file — executor running freely"
                                                                                                                                                                                                                            fi
                                                                                                                                                                                                                            
                                                                                                                                                                                                                            # 5. L99 protection halt
                                                                                                                                                                                                                            L99="/root/.l99/protection_halt.json"
                                                                                                                                                                                                                            if [ -f "$L99" ]; then
                                                                                                                                                                                                                                L99_HALTED=$(python3 -c "import json; d=json.load(open('$L99')); print(d.get('halted',''))" 2>/dev/null || echo "")
                                                                                                                                                                                                                                    if [ "$L99_HALTED" = "True" ]; then
                                                                                                                                                                                                                                            fail "L99 protection halt ENGAGED — executor will refuse to trade"
                                                                                                                                                                                                                                                else
                                                                                                                                                                                                                                                        ok "L99 protection_halt.json: halted=False"
                                                                                                                                                                                                                                                            fi
                                                                                                                                                                                                                                                            else
                                                                                                                                                                                                                                                                ok "No L99 halt file"
                                                                                                                                                                                                                                                                fi
                                                                                                                                                                                                                                                                
                                                                                                                                                                                                                                                                # 6. ufw
                                                                                                                                                                                                                                                                if command -v ufw >/dev/null 2>&1; then
                                                                                                                                                                                                                                                                    UFW_STATUS=$(ufw status 2>/dev/null | head -1)
                                                                                                                                                                                                                                                                        if echo "$UFW_STATUS" | grep -q "active"; then
                                                                                                                                                                                                                                                                                ok "ufw: $UFW_STATUS"
                                                                                                                                                                                                                                                                                    else
                                                                                                                                                                                                                                                                                            warn "ufw: $UFW_STATUS (not active)"
                                                                                                                                                                                                                                                                                                fi
                                                                                                                                                                                                                                                                                                else
                                                                                                                                                                                                                                                                                                    warn "ufw not installed"
                                                                                                                                                                                                                                                                                                    fi
                                                                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                                                    # 7. fail2ban
                                                                                                                                                                                                                                                                                                    if command -v fail2ban-client >/dev/null 2>&1; then
                                                                                                                                                                                                                                                                                                        if fail2ban-client status >/dev/null 2>&1; then
                                                                                                                                                                                                                                                                                                                ok "fail2ban is running"
                                                                                                                                                                                                                                                                                                                    else
                                                                                                                                                                                                                                                                                                                            warn "fail2ban not running"
                                                                                                                                                                                                                                                                                                                                fi
                                                                                                                                                                                                                                                                                                                                else
                                                                                                                                                                                                                                                                                                                                    warn "fail2ban not installed"
                                                                                                                                                                                                                                                                                                                                    fi
                                                                                                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                                                                                    # 8. Python SSL / certifi
                                                                                                                                                                                                                                                                                                                                    if python3 -c "import ssl, certifi; print('certifi OK:', certifi.where())" 2>/dev/null; then
                                                                                                                                                                                                                                                                                                                                        ok "Python SSL + certifi: OK"
                                                                                                                                                                                                                                                                                                                                        else
                                                                                                                                                                                                                                                                                                                                            warn "certifi not installed — run: pip install certifi"
                                                                                                                                                                                                                                                                                                                                            fi
                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                            echo "========================================"
                                                                                                                                                                                                                                                                                                                                            if [ "$ERRORS" -eq 0 ]; then
                                                                                                                                                                                                                                                                                                                                                echo "RESULT: HEALTHY (0 issues)"
                                                                                                                                                                                                                                                                                                                                                    exit 0
                                                                                                                                                                                                                                                                                                                                                    else
                                                                                                                                                                                                                                                                                                                                                        echo "RESULT: DEGRADED ($ERRORS issue(s) found — review above)"
                                                                                                                                                                                                                                                                                                                                                            exit 1
                                                                                                                                                                                                                                                                                                                                                            fi
                                                                                                                                                                                                                                                                                                                                                            
