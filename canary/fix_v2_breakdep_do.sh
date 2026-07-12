#!/bin/bash
# fix_v2_breakdep_do.sh — DEFINITIVE single-engine fix for DigitalOcean.
# Root cause: canary-battle.service has WantedBy=canary-api.service, so every
# time canary-api starts it drags canary-battle back up. We break that link,
# then mask canary-battle so it can NEVER start (not even as a dependency).
# canary-api (dashboard, port 8765) is kept running.
# Run as root on DO:  bash fix_v2_breakdep_do.sh
set -u
echo "================================================================"
echo " TRADING GURU — DO SINGLE-ENGINE FIX v2 (break api->battle dep)"
echo " $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================================"

BATTLE_UNIT=/etc/systemd/system/canary-battle.service

# 1. Show the offending Install/WantedBy lines
echo "--- [1] Current canary-battle [Install] section ---"
grep -nE 'WantedBy|RequiredBy|\[Install\]' "$BATTLE_UNIT" 2>/dev/null || echo "  (none / unit not found)"

# 2. Stop canary-battle + siblings
echo "--- [2] Stopping old engines ---"
for svc in canary-battle scalp-battle-live canary-watchdog scalp-godmode-engine; do
  sudo systemctl stop "$svc" 2>/dev/null
done

# 3. Remove the WantedBy=canary-api dependency from the unit file (comment it out)
echo "--- [3] Removing WantedBy=canary-api dependency ---"
if [ -f "$BATTLE_UNIT" ]; then
  sudo cp "$BATTLE_UNIT" "${BATTLE_UNIT}.bak.$(date +%s)"
  sudo sed -i -E 's#^(WantedBy=.*canary-api.*)#\# removed-single-engine \1#I' "$BATTLE_UNIT"
  sudo sed -i -E 's#^(RequiredBy=.*canary-api.*)#\# removed-single-engine \1#I' "$BATTLE_UNIT"
  echo "   patched (backup saved)"
fi

# 3b. Also drop any Wants=/Requires= on canary-api side pointing to canary-battle
API_UNIT=/etc/systemd/system/canary-api.service
if [ -f "$API_UNIT" ]; then
  if grep -qiE '(Wants|Requires|BindsTo)=.*canary-battle' "$API_UNIT"; then
    sudo cp "$API_UNIT" "${API_UNIT}.bak.$(date +%s)"
    sudo sed -i -E 's#^((Wants|Requires|BindsTo)=.*canary-battle.*)#\# removed-single-engine \1#I' "$API_UNIT"
    echo "   patched canary-api (removed Wants/Requires canary-battle)"
  else
    echo "   canary-api has no direct Wants/Requires on canary-battle (good)"
  fi
fi

# 4. Reload, disable + MASK canary-battle (mask wins over any WantedBy)
echo "--- [4] daemon-reload + disable + MASK old engines ---"
sudo systemctl daemon-reload
for svc in canary-battle scalp-battle-live canary-watchdog scalp-godmode-engine; do
  sudo systemctl disable "$svc" 2>/dev/null
  sudo systemctl mask "$svc" 2>/dev/null
done

# 5. Restart canary-api so it re-reads deps (dashboard stays up, no battle dragged in)
echo "--- [5] Restarting canary-api (dashboard) WITHOUT battle ---"
sudo systemctl restart canary-api 2>/dev/null
sleep 3

# 6. Kill any executor that may still be lingering
echo "--- [6] Killing lingering canary_executor ---"
pids=$(pgrep -f canary_executor.py || true)
if [ -n "$pids" ]; then echo "   killing: $pids"; sudo kill $pids 2>/dev/null; sleep 2; fi
pids=$(pgrep -f canary_executor.py || true)
if [ -n "$pids" ]; then echo "   force kill: $pids"; sudo kill -9 $pids 2>/dev/null; fi

# 7. Final state
echo "--- [7] FINAL STATE ---"
for svc in canary-battle scalp-battle-live canary-watchdog canary-api coach champion-battle; do
  printf "   %-20s active=%-10s state=%s\n" "$svc" "$(systemctl is-active $svc 2>/dev/null)" "$(systemctl is-enabled $svc 2>/dev/null)"
done
echo "--- real-money processes (should be coach + champion ONLY) ---"
ps -eo pid,cmd | grep -E 'canary_executor|scalp_battle|champion_battle|coach\.py' | grep -v grep || echo "   (none)"
echo "================================================================"
echo " EXPECT: canary-battle active=inactive state=masked ;"
echo "         canary-api active=active ; coach/champion active=active ;"
echo "         processes = coach.py + champion_battle.py ONLY."
echo " If executor reappears within 2 min, run: systemctl status canary-battle"
echo "================================================================"
