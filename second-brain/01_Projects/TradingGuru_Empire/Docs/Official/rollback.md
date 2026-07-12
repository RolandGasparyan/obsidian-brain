# Rollback Procedure — canary-battle.service

Last updated: 2026-05-23 (P3b remediation)

This document contains the **exact literal commands** to stop the live battle,
restore a prior known-good state, and restart the service safely.

> **Capital at risk: $1,979.52 USDT (MAIN $1,579.52 + SUB1 $200 + SUB2 $200)**
> Do not rush. Read each step before executing.

---

## When to use this

- Service is in a halt loop and won't restart cleanly
- State files are corrupted
- Unexpected balance discrepancy detected
- `healthcheck.sh` reports DEGRADED on multiple consecutive runs
- Manual operator decision to pause trading

---

## Step 1 — Stop the service

```bash
# Stop canary-battle (and watchdog if running)
systemctl stop canary-battle.service
systemctl stop canary-watchdog.service 2>/dev/null || true

# Verify stopped
systemctl is-active canary-battle.service  # should print "inactive"
```

---

## Step 2 — Snapshot current state

```bash
# Timestamp for this rollback
TS=$(date +%Y%m%d_%H%M%S)

# Backup current state files
cp /root/canary/runtime/state_main.json /root/canary/runtime/state_main.json.bak.$TS
cp /root/canary/runtime/state_sub1.json /root/canary/runtime/state_sub1.json.bak.$TS
cp /root/canary/runtime/state_sub2.json /root/canary/runtime/state_sub2.json.bak.$TS

# Backup arm file
cp /root/canary/canary_arm.json /root/canary/canary_arm.json.bak.$TS

# Backup battle log
cp /root/canary/runtime/battle.log /root/canary/runtime/battle.log.bak.$TS 2>/dev/null || true

echo "Snapshot complete: $TS"
```

---

## Step 3 — Inspect open positions

Before doing anything further, verify what positions are open on the exchange:

```bash
# Check state files for open positions
python3 -c "
import json
for acct, sf in [('MAIN', 'state_main'), ('SUB1', 'state_sub1'), ('SUB2', 'state_sub2')]:
    try:
            d = json.load(open(f'/root/canary/runtime/{sf}.json'))
                    pos = d.get('positions', {})
                            pnl = d.get('session_pnl', 0)
                                    dd  = d.get('daily_dd_usd', 0)
                                            print(f'[{acct}] pnl=\${pnl:+.2f} dd=\${dd:.2f} open={list(pos.keys())}')
                                                except Exception as e:
                                                        print(f'[{acct}] ERROR: {e}')
                                                        "
                                                        ```

                                                        **If positions are open on the exchange but NOT in the state file:**
                                                        Manually close them via Gate.io web UI before proceeding.

                                                        **If positions are in the state file but already closed on exchange:**
                                                        Proceed — the next service start will reconcile via `check_bal`.

                                                        ---

                                                        ## Step 4 — Clear any halt file

                                                        ```bash
                                                        # Check if a halt is engaged
                                                        if [ -f /root/canary/runtime/CANARY_HALT.json ]; then
                                                            echo "Halt reason: $(python3 -c 'import json; print(json.load(open("/root/canary/runtime/CANARY_HALT.json")).get("reason", "?"))')"
                                                                # Only clear if you are ready to resume trading
                                                                    read -p "Clear halt file? (yes/no): " CONFIRM
                                                                        [ "$CONFIRM" = "yes" ] && rm /root/canary/runtime/CANARY_HALT.json && echo "Halt cleared"
                                                                        fi

                                                                        # Check L99 protection halt
                                                                        if [ -f /root/.l99/protection_halt.json ]; then
                                                                            echo "L99 halt active — do NOT clear without operator approval"
                                                                            fi
                                                                            ```

                                                                            ---

                                                                            ## Step 5 — Restore prior state (if needed)

                                                                            Only if the current state files are corrupted or show impossible values:

                                                                            ```bash
                                                                            # List available backups
                                                                            ls -lt /root/canary/runtime/state_main.json.bak.* 2>/dev/null | head -5

                                                                            # Restore from a specific backup (replace TIMESTAMP)
                                                                            TIMESTAMP=20260523_140000  # example — use the timestamp from Step 2
                                                                            cp /root/canary/runtime/state_main.json.bak.$TIMESTAMP /root/canary/runtime/state_main.json
                                                                            cp /root/canary/runtime/state_sub1.json.bak.$TIMESTAMP /root/canary/runtime/state_sub1.json
                                                                            cp /root/canary/runtime/state_sub2.json.bak.$TIMESTAMP /root/canary/runtime/state_sub2.json
                                                                            echo "State restored from $TIMESTAMP"
                                                                            ```

                                                                            ---

                                                                            ## Step 6 — Update code from git (if deploying a fix)

                                                                            ```bash
                                                                            cd /root/canary
                                                                            git fetch origin
                                                                            git pull origin main  # or 'Godmode' if testing that branch

                                                                            # If requirements changed
                                                                            source venv/bin/activate
                                                                            pip install -r requirements.txt
                                                                            deactivate
                                                                            ```

                                                                            ---

                                                                            ## Step 7 — Run pre-restart health check

                                                                            ```bash
                                                                            bash /root/canary/healthcheck.sh
                                                                            ```

                                                                            Only proceed to Step 8 if the output shows HEALTHY or only minor warnings.

                                                                            ---

                                                                            ## Step 8 — Restart service

                                                                            ```bash
                                                                            # Reload systemd config (needed if service file changed)
                                                                            systemctl daemon-reload

                                                                            # Start service
                                                                            systemctl start canary-battle.service

                                                                            # Verify startup
                                                                            journalctl -u canary-battle.service -f -n 30
                                                                            # Look for: "Safety gates passed. Starting 3-account live battle..."
                                                                            # Ctrl+C to exit follow mode
                                                                            ```

                                                                            ---

                                                                            ## Step 9 — Verify post-restart

                                                                            ```bash
                                                                            # Service status
                                                                            systemctl status canary-battle.service

                                                                            # State files updated?
                                                                            sleep 60
                                                                            bash /root/canary/healthcheck.sh

                                                                            # Optional: tail the log
                                                                            tail -f /root/canary/runtime/battle.log
                                                                            ```

                                                                            ---

                                                                            ## Emergency stop (fastest path)

                                                                            If you need to halt trading immediately with no other action:

                                                                            ```bash
                                                                            # Method 1: Stop service (executor exits cleanly)
                                                                            systemctl stop canary-battle.service

                                                                            # Method 2: Write halt file manually (executor stops on next loop tick ~30s)
                                                                            python3 -c "
                                                                            import json, time
                                                                            from datetime import datetime, timezone
                                                                            payload = {'halted': True, 'reason': 'OPERATOR_MANUAL_HALT', 'ts': time.time(), 'iso': datetime.now(timezone.utc).isoformat()}
                                                                            open('/root/canary/runtime/CANARY_HALT.json', 'w').write(json.dumps(payload, indent=2))
                                                                            print('Halt file written')
                                                                            "

                                                                            # Method 3: Use the kill script (most immediate)
                                                                            bash /root/canary/kill.sh
                                                                            ```

                                                                            ---

                                                                            ## Rollback decision checklist

                                                                            Before restarting after a rollback:

                                                                            - [ ] Open positions on exchange match state files (or manually resolved)
                                                                            - [ ] No halt files engaged (or consciously cleared)
                                                                            - [ ] `healthcheck.sh` returns HEALTHY
                                                                            - [ ] `canary_arm.json` still valid and `paper_preflight_passed: true`
                                                                            - [ ] Lifetime cap not exceeded (`armed_at` + 720h > now)
                                                                            - [ ] L99 protection halt NOT engaged

                                                                            ---

                                                                            *Maintained under docs/rollback.md on the Godmode branch.*
                                                                            *P3b remediation — 2026-05-23*
                                                                            
