#!/bin/bash
# watch_strategy_integrity.sh — polls canary_strategy.py SHA256 every 30s.
# Alerts + exits if the file is modified outside an approved snapshot.
# Run via: nohup ./watch_strategy_integrity.sh > runtime/integrity.log 2>&1 &
set -u
cd /root/canary || exit 1
mkdir -p runtime strategy_snapshots

LATEST_SNAPSHOT=strategy_snapshots/ma50w10_locked_20260512_161050.sha256
if [ -z "" ]; then
  echo "[2026-05-12T16:10:50Z] FATAL: no snapshot to compare against"
  exit 2
fi

BASE_HASH=
echo "[2026-05-12T16:10:50Z] integrity watcher started · baseline= · snapshot="

while true; do
  CUR_HASH=704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143
  if [ -z "" ]; then
    echo "[2026-05-12T16:10:50Z] ALERT: canary_strategy.py unreadable"
    exit 3
  fi
  if [ "" != "" ]; then
    echo ""
    echo "🚨 [2026-05-12T16:10:50Z] STRATEGY FILE MODIFIED"
    echo "    baseline:  "
    echo "    current:   "
    echo "    snapshot:  "
    echo ""
    diff -u ".py" canary_strategy.py | head -60 || true
    echo ""
    echo "Exiting watcher. Operator must investigate before re-arming canary."
    exit 1
  fi
  sleep 30
done
