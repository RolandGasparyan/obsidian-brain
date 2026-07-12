# Canary Rollback — When Things Go Wrong

## TL;DR — single command stops everything

```bash
sudo /root/canary/kill.sh "your_reason"
```

That's it. Everything else in this file is detail for post-incident review.

---

## Scenarios and responses

### Scenario A — Canary loss approaching $2

**Indicator:** `journalctl -u canary.service` shows `pnl=-1.50` or similar
**Action:** Wait for automatic killswitch (fires at -$2) OR pull the trigger early:
```bash
sudo /root/canary/kill.sh "DD_PREEMPTIVE"
```

### Scenario B — Bot stuck (no logs for >2 minutes)

**Indicator:** `journalctl -u canary.service` tail is silent
**Likely cause:** API rate limit, network hiccup, or Python deadlock
**Action:** Watchdog will detect this within 90s via state-staleness check and halt. If you want faster:
```bash
sudo /root/canary/kill.sh "BOT_HUNG"
```

### Scenario C — Watchdog stopped working

**Indicator:** `systemctl is-active canary-killswitch.service` returns inactive
**Risk:** Canary now has no DD safety. Stop it.
```bash
sudo /root/canary/kill.sh "WATCHDOG_DOWN"
```

### Scenario D — Suspicious behavior (wrong symbol, wrong size, multiple positions)

**Indicator:** Position shown in `canary_status.json` has unexpected fields
**Action:**
```bash
sudo /root/canary/kill.sh "ANOMALY"
# Then dump everything for forensic review:
cp /root/canary/canary_state.json /root/canary/snapshots/state_$(date +%s).json
cp /root/canary/runtime/trades.log /root/canary/snapshots/trades_$(date +%s).log
```

### Scenario E — Open position when kill.sh runs

**State after kill:** Bot stopped. Position may still be on Gate.io.

The executor has emergency-exit logic that fires when DD cap hits, but it only runs while the bot is alive. If `kill.sh` SIGTERMs the bot mid-cycle, the position may NOT have been closed.

**Recovery:**
1. Check `canary_state.json` → look for `"position": {...}` non-null
2. Check Gate.io sub-account → confirm position
3. Close manually via Gate.io UI:
   - Spot Trading → Open Orders → cancel all
   - Holdings → Sell all BTC to USDT
4. Verify sub-account is back to ~$100 USDT (minus realized P&L)

### Scenario F — Multiple positions detected

**Indicator:** Gate.io shows >1 open order on canary sub-account
**Risk:** This violates the design (single-position-at-a-time mutex)
**Action:**
1. `sudo /root/canary/kill.sh "MULTI_POSITION_VIOLATION"`
2. Cancel ALL orders manually on Gate.io
3. **Do NOT re-arm** until root cause identified
4. Investigate: `/root/canary/runtime/trades.log`, `POSITION.lock` mtime, `canary_state.json` history

### Scenario G — API key compromised / unauthorized trade

**Indicator:** Trade in `trades.log` that you didn't expect (wrong size, wrong symbol if BTC/USDT somehow bypassed)
**Action immediate:**
1. Log into Gate.io
2. Revoke the canary sub-account API key
3. `sudo /root/canary/kill.sh "API_COMPROMISE"`
4. Cancel all orders, transfer balance back to main account
5. Forensic review

---

## How to re-arm after a stop

If you stopped for an issue and want to resume:

1. **Resolve the root cause first** — don't re-arm with the same bug
2. Review logs, fix whatever caused the stop
3. Dismiss halt artifact:
   ```bash
   rm /root/canary/runtime/CANARY_HALT.json
   ```
4. Recreate arm file with a NEW timestamp (the wall-clock cap is from `armed_at`):
   ```bash
   cat > /root/canary/canary_arm.json <<EOF
   {
     "armed_by": "Roland Gasparyan",
     "armed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
     "ack_max_loss_usd": 2.00,
     "ack_time_cap_hours": 48,
     "paper_preflight_passed": true
   }
   EOF
   ```
5. Start as in DEPLOY.md Step 8 (watchdog FIRST, then canary)

---

## How to fully decommission

If you want to remove the canary permanently:

```bash
# Stop services
sudo systemctl stop canary.service canary-killswitch.service

# Remove unit files
sudo rm /etc/systemd/system/canary.service /etc/systemd/system/canary-killswitch.service
sudo systemctl daemon-reload

# Cancel any Gate.io orders, transfer sub-account USDT back to main
# (manual on Gate.io UI)

# Revoke API key on Gate.io
# (manual on Gate.io UI)

# Archive the canary directory (don't delete — keep for forensics)
mv /root/canary /root/canary.archived_$(date -u +%Y%m%d)
```

---

## Indicators that you should kill RIGHT NOW

- `session_pnl_usd` between -$1.50 and -$2.00 (DD cap imminent)
- Multiple BUY entries in trades.log within < 30 min
- Position size mismatch (executor logs $30 but Gate.io shows different)
- Any SELL on a non-BTC/USDT pair
- Watchdog log silent for > 2 min
- API balance check returns balance > $200 (sub-account isolation broken)
- Any reference to leverage/margin in Gate.io account status

When in doubt → `sudo /root/canary/kill.sh "PRECAUTION"`. The DD cost of an unnecessary stop is $0. The DD cost of a missed stop can be the full $100.
