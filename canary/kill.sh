#!/bin/bash
#
# kill.sh — One-button safe stop for canary.
# Usage: sudo /root/canary/kill.sh [reason]
#
# Action sequence:
#   1. Write CANARY_HALT.json with reason + ts
#   2. Stop systemd services (executor first to prevent re-trade, then watchdog)
#   3. Print final state snapshot
#   4. Show next-step guidance
#
# This script does NOT close open positions on Gate.io.
# If a position is open, the executor's emergency exit logic will try to close
# it on its next cycle (before noticing the halt file). If that fails, operator
# must close via Gate.io UI manually.

set -e

REASON="${1:-OPERATOR_KILL}"
TS=$(date +%s)
ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

HALT_FILE=/root/canary/runtime/CANARY_HALT.json
STATE_FILE=/root/canary/canary_state.json
STATUS_FILE=/root/canary/runtime/canary_status.json

echo "════════════════════════════════════════════════════════════════"
echo "  🛑 CANARY KILL SWITCH"
echo "  reason: $REASON"
echo "  ts:     $ISO"
echo "════════════════════════════════════════════════════════════════"

# 1. Write halt file FIRST (so even if systemctl fails, canary self-halts next cycle)
mkdir -p /root/canary/runtime
cat > "$HALT_FILE" <<EOF
{
  "halted": true,
  "reason": "$REASON",
  "triggered_by": "kill.sh",
  "ts": $TS,
  "iso": "$ISO"
}
EOF
echo "✓ halt file written: $HALT_FILE"

# 2. Stop executor first (prevent new trades), then watchdog
systemctl stop canary.service 2>&1 | head -3
echo "✓ canary.service stop attempted"
sleep 1
systemctl stop canary-killswitch.service 2>&1 | head -3
echo "✓ canary-killswitch.service stop attempted"

# 3. Verify stopped
sleep 1
echo ""
echo "── service status ──"
systemctl is-active canary.service canary-killswitch.service 2>&1 || true

# 4. Final state snapshot
echo ""
echo "── final state snapshot ──"
if [ -f "$STATE_FILE" ]; then
  cat "$STATE_FILE"
else
  echo "  (no state file)"
fi
echo ""
echo "── latest telemetry ──"
if [ -f "$STATUS_FILE" ]; then
  cat "$STATUS_FILE"
else
  echo "  (no status file)"
fi

# 5. Guidance
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  POST-KILL CHECKLIST FOR OPERATOR"
echo "════════════════════════════════════════════════════════════════"
echo "  1. Check Gate.io sub-account: any open orders to cancel?"
echo "  2. Check Gate.io sub-account: any non-USDT holdings to convert back?"
echo "  3. Review canary_state.json above for final session_pnl_usd"
echo "  4. Review /root/canary/runtime/trades.log for full trade history"
echo "  5. To re-arm canary: review + recreate /root/canary/canary_arm.json"
echo "  6. To dismiss halt: rm $HALT_FILE  (only after issues resolved)"
echo "════════════════════════════════════════════════════════════════"
