#!/usr/bin/env bash
# ── Trading Guru — Battle Round Status ─────────────────────────────────────────
# Shows the continuous championship results: current round, round winners,
# per-agent standings, and recent round-by-round history.
# Run on DigitalOcean: bash /root/canary/battle_status.sh
set -uo pipefail

ROOT=/root/canary
[ -d "$ROOT" ] || ROOT=/home/ubuntu/canary
STATE="$ROOT/runtime/champion_state.json"
ROUNDS="$ROOT/runtime/battle_rounds.json"

echo "================================================================"
echo " TRADING GURU — BATTLE CHAMPIONSHIP STATUS  ($(date -u '+%Y-%m-%d %H:%M:%SZ'))"
echo "================================================================"

echo ""
echo "[1] Engine services"
for s in champion-battle coach; do
  printf "   %-18s %s\n" "$s" "$(systemctl is-active $s 2>&1)"
done

echo ""
echo "[2] Live championship (current round + standings)"
if [ -f "$STATE" ]; then
python3 - "$STATE" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
c = d.get("championship") or {}
print(f"   Current round : #{c.get('current_round_id','?')}  "
      f"({c.get('round_seconds_left','?')}s left of {c.get('round_interval_sec','?')}s)")
print(f"   Round leader  : {c.get('current_round_leader','?')}")
print("   Live round PnL:")
for r in c.get("current_round_live", []):
    print(f"      {r['agent']:<10} {r['round_pnl_usd']:+.4f}  ({r.get('assigned_pair')})")
rw = c.get("round_wins", {})
if rw:
    print("   Round crowns (cumulative):")
    for a, n in sorted(rw.items(), key=lambda x: -x[1]):
        print(f"      {a:<10} {n} 🏆")
else:
    print("   Round crowns  : (no completed rounds yet)")
print("\n   Session totals (since engine start):")
for a in sorted(d.get("agents", []), key=lambda x: -x.get("session_pnl",0)):
    print(f"      {a['name']:<10} bal=${a['balance']:.2f}  pnl={a['session_pnl']:+.4f}  "
          f"W/L={a['wins']}/{a['losses']}  pair={a.get('assigned_pair')}")
PY
else
  echo "   (state file not found yet — engine may still be warming up)"
fi

echo ""
echo "[3] Recent round history (most recent first)"
if [ -f "$ROUNDS" ]; then
python3 - "$ROUNDS" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
hist = list(reversed(d.get("history", [])))[:12]
if not hist:
    print("   (no completed rounds yet)")
for r in hist:
    res = " | ".join(f"{x['agent']} {x['round_pnl_usd']:+.4f}" for x in r["results"])
    print(f"   R#{r['round_id']:<4} winner={r['winner']:<10} {res}")
PY
else
  echo "   (no round history file yet — first round completes after the interval)"
fi
echo "================================================================"
