#!/usr/bin/env bash
# stop_shadow_round.sh — stops a running shadow round via SIGTERM (clean shutdown).
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PID_FILE="${SCRIPT_DIR}/runtime/shadow_round.pid"

if [[ ! -f "${PID_FILE}" ]]; then
  echo "ℹ no pid file at ${PID_FILE} — nothing to stop"
  exit 0
fi

PID="$(cat "${PID_FILE}")"
if ! kill -0 "${PID}" 2>/dev/null; then
  echo "ℹ pid ${PID} not running — removing stale pid file"
  rm -f "${PID_FILE}"
  exit 0
fi

echo "→ sending SIGTERM to shadow_round pid ${PID}"
kill -TERM "${PID}"
for i in $(seq 1 20); do
  if ! kill -0 "${PID}" 2>/dev/null; then
    echo "✓ stopped cleanly"
    rm -f "${PID_FILE}"
    exit 0
  fi
  sleep 0.5
done

echo "⚠ pid ${PID} did not exit after 10s — sending SIGKILL"
kill -KILL "${PID}" 2>/dev/null || true
rm -f "${PID_FILE}"
echo "✓ killed"
