#!/bin/bash
# diag_revive_do.sh — find WHAT keeps reviving canary-battle on DigitalOcean.
# Run as root on DO:  bash diag_revive_do.sh
echo "================================================================"
echo " CANARY-BATTLE REVIVER DIAGNOSTIC  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================================"

echo "--- [A] Is canary-battle masked? unit file state ---"
systemctl is-active canary-battle; systemctl is-enabled canary-battle 2>&1
systemctl show canary-battle -p UnitFileState,LoadState,ActiveState,FragmentPath,TriggeredBy,WantedBy,RequiredBy 2>&1

echo "--- [B] WHO started current canary_executor? (recent journal) ---"
journalctl -u canary-battle --no-pager -n 20 2>/dev/null | tail -20

echo "--- [C] All systemd units mentioning canary (incl. path/timer/target) ---"
systemctl list-units --all 2>/dev/null | grep -i canary
echo "--- path units / timers ---"
systemctl list-unit-files 2>/dev/null | grep -iE 'canary|scalp|battle|watchdog|revive|guard'

echo "--- [D] What is canary-api doing? does it spawn executor? ---"
systemctl is-active canary-api 2>/dev/null
systemctl cat canary-api 2>/dev/null | grep -iE 'ExecStart|WorkingDirectory'
grep -rIl --include=*.py -e 'systemctl' -e 'canary-battle' -e 'canary_executor' /root/canary 2>/dev/null | head -20

echo "--- [E] ALL cron (root + system) referencing engines ---"
echo "[root crontab]"; crontab -l 2>/dev/null | grep -niE 'canary|scalp|battle|watchdog|systemctl' || echo "  none"
echo "[/etc/cron.d + cron.* ]"; grep -rniE 'canary|scalp|battle|watchdog' /etc/cron.d /etc/crontab /etc/cron.hourly /etc/cron.daily 2>/dev/null || echo "  none"

echo "--- [F] Any *.timer that could trigger it ---"
systemctl list-timers --all 2>/dev/null | grep -iE 'canary|battle|scalp|watchdog' || echo "  none"

echo "--- [G] Process tree of current canary_executor (who is its parent?) ---"
for pid in $(pgrep -f canary_executor.py); do
  echo "executor PID=$pid  PPID info:"; ps -o pid,ppid,etime,cmd -p "$pid" 2>/dev/null
  ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
  echo "  parent:"; ps -o pid,ppid,cmd -p "$ppid" 2>/dev/null
done

echo "================================================================"
echo " Look at [A] (should be masked), [B] (who triggered), [C]/[F] (hidden unit/timer), [G] (parent process)"
echo "================================================================"
