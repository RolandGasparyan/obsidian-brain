#!/bin/bash
# fix_singleengine_do.sh — enforce SINGLE live engine on DigitalOcean.
# Stops + MASKS canary-battle (and siblings) and disables any cron/watchdog
# that keeps reviving them, so ONLY champion-battle + coach trade.
# Run as root on DO:  bash fix_singleengine_do.sh
set -u
echo "================================================================"
echo " TRADING GURU — DO SINGLE-ENGINE ENFORCE (mask revivers)"
echo " $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================================"

# 1. Find & neutralise any cron line that restarts canary/scalp engines
echo "--- [1] Scanning root crontab for engine revivers ---"
CRON_TMP="$(mktemp)"
crontab -l 2>/dev/null > "$CRON_TMP" || true
if grep -qE 'canary|scalp|hourly_monitor|watchdog' "$CRON_TMP"; then
  grep -nE 'canary|scalp|hourly_monitor|watchdog' "$CRON_TMP" | sed 's/^/   FOUND: /'
  sed -i -E 's#^([^#].*(canary|scalp|hourly_monitor|watchdog).*)#\# DISABLED-single-engine \1#' "$CRON_TMP"
  crontab "$CRON_TMP"
  echo "   -> commented out reviver cron lines"
else
  echo "   (no reviver cron lines found)"
fi
rm -f "$CRON_TMP"

# 2. Stop + mask the OLD real-money engines (mask = cannot start, even manually)
echo "--- [2] Stopping + masking old engines ---"
for svc in canary-battle scalp-battle-live canary-watchdog; do
  sudo systemctl stop "$svc" 2>/dev/null
  sudo systemctl disable "$svc" 2>/dev/null
  sudo systemctl mask "$svc" 2>/dev/null
  printf "   %-20s " "$svc"; systemctl is-active "$svc" 2>/dev/null
done

# 3. Kill any lingering canary_executor / scalp process (graceful)
echo "--- [3] Killing lingering old engine processes ---"
for pat in canary_executor.py scalp_battle_live.py; do
  pids=$(pgrep -f "$pat" || true)
  if [ -n "$pids" ]; then echo "   killing $pat: $pids"; sudo kill $pids 2>/dev/null; fi
done
sleep 2

# 4. Ensure the TEAM is the only live engine
echo "--- [4] Team engines (should be active) ---"
for svc in coach champion-battle; do
  printf "   %-20s " "$svc"; systemctl is-active "$svc" 2>/dev/null
done

echo "--- [5] Real-money processes now (should be coach + champion only) ---"
ps -eo pid,cmd | grep -E 'canary_executor|scalp_battle|champion_battle|coach\.py' | grep -v grep \
  || echo "   (none)"

echo "================================================================"
echo " DONE — if [2]=inactive(masked), [4]=active, [5]=coach+champion only"
echo " => DigitalOcean is now truly SINGLE-ENGINE (no conflict)."
echo "================================================================"
