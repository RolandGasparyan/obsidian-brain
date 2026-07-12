#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSE BATTLE — DigitalOcean VPS (167.71.24.86)
# One-command health check for the Trading Guru champion battle.
# Answers: Are the agents actually trading? Why no profit / no competition?
# Run on the VPS:  bash diagnose_battle_do.sh
# ─────────────────────────────────────────────────────────────────────────────
set +e
ROOT="/root/canary"
[ -d "$ROOT" ] || ROOT="/home/ubuntu/canary"
RT="$ROOT/runtime"
echo "════════════════════════════════════════════════════════════"
echo " TRADING GURU — BATTLE DIAGNOSTIC   $(date -u '+%Y-%m-%d %H:%M:%SZ')"
echo " ROOT=$ROOT"
echo "════════════════════════════════════════════════════════════"

echo; echo "── 1) WHICH ENGINES ARE RUNNING (systemd) ──"
systemctl list-units --type=service --state=running 2>/dev/null | grep -Ei 'champion|coach|canary|battle|scalp|paper|micro' || echo "  (none matched)"

echo; echo "── 2) champion-battle + coach status ──"
for s in champion-battle coach; do
  printf "  %-16s : %s\n" "$s" "$(systemctl is-active $s 2>/dev/null) / enabled=$(systemctl is-enabled $s 2>/dev/null)"
done

echo; echo "── 3) PYTHON PROCESSES (what is actually executing) ──"
ps -eo pid,etime,cmd 2>/dev/null | grep -Ei 'python.*(champion_battle|coach|canary|scalp|executor)' | grep -v grep || echo "  (no matching python processes)"

echo; echo "── 4) champion_battle.log — last 40 lines ──"
tail -n 40 "$RT/champion_battle.log" 2>/dev/null || echo "  (no champion_battle.log)"

echo; echo "── 5) Trade activity in champion log (BUY/SELL/TP/SL counts) ──"
if [ -f "$RT/champion_battle.log" ]; then
  echo "  BUY  lines: $(grep -c 'BUY'  "$RT/champion_battle.log" 2>/dev/null)"
  echo "  SELL/exit : $(grep -Ec 'SELL|TP|SL|MAXHOLD' "$RT/champion_battle.log" 2>/dev/null)"
  echo "  ERRORs    : $(grep -c 'ERROR\|❌\|error' "$RT/champion_battle.log" 2>/dev/null)"
  echo "  last 5 trade-ish lines:"
  grep -E 'BUY|SELL|TP|SL|MAXHOLD|ROUND' "$RT/champion_battle.log" 2>/dev/null | tail -n 5 | sed 's/^/    /'
else echo "  (no log)"; fi

echo; echo "── 6) coach_signals.json (agent → pair/strategy assignments) ──"
if [ -f "$RT/coach_signals.json" ]; then
  python3 - "$RT/coach_signals.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print("  updated_at:", d.get("updated_at"))
for a,v in (d.get("assignments") or {}).items():
    print(f"   {a:9s} -> {v.get('pair'):12s} | {v.get('strategy','')[:22]:22s} | PF {v.get('profit_factor')}")
print("  bench:", d.get("bench"))
PY
else echo "  (no coach_signals.json — coach may not be writing!)"; fi

echo; echo "── 7) battle_rounds.json (completed rounds + winners) ──"
if [ -f "$RT/battle_rounds.json" ]; then
  python3 - "$RT/battle_rounds.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
h=d.get("history",[])
print("  completed rounds:", len(h))
for r in h[-3:]:
    res=" | ".join(f"{x['agent']} {x['round_pnl_usd']:+.4f}" for x in r.get("results",[]))
    print(f"   R{r.get('round_id')}: winner={r.get('winner')} :: {res}")
PY
else echo "  (no battle_rounds.json — no round has completed yet)"; fi

echo; echo "── 8) LIVE Gate.io balances (3 accounts) ──"
python3 - <<'PY'
import pathlib
try:
    import ccxt
except Exception as e:
    print("  ccxt not available:", e); raise SystemExit
ROOT=None
for c in ("/root/canary","/home/ubuntu/canary"):
    if pathlib.Path(c).exists(): ROOT=pathlib.Path(c); break
if not ROOT: print("  canary root not found"); raise SystemExit
for f,l in [(".api_key_main","TITAN"),(".api_key_sub1","VELOCITY"),(".api_key_sub2","SENTINEL")]:
    try:
        k,s=(ROOT/f).read_text().strip().split(":")
        ex=ccxt.gate({"apiKey":k,"secret":s,"enableRateLimit":True,"options":{"defaultType":"spot"}})
        b=ex.fetch_balance()
        usdt=float(b.get("USDT",{}).get("free",0) or 0)
        # list any non-USDT tokens left over (stuck positions)
        leftovers={c:v for c,v in (b.get("total") or {}).items() if c!="USDT" and v and v>0}
        print(f"  {l:9s}: ${usdt:.2f} USDT free | leftover tokens: {leftovers if leftovers else 'none'}")
    except Exception as e:
        print(f"  {l:9s}: ERROR {e}")
PY

echo; echo "── 9) Gate.io FUTURES permission probe (TITAN main key) ──"
python3 - <<'PY'
import pathlib
try: import ccxt
except Exception: raise SystemExit
ROOT=None
for c in ("/root/canary","/home/ubuntu/canary"):
    if pathlib.Path(c).exists(): ROOT=pathlib.Path(c); break
if not ROOT: raise SystemExit
try:
    k,s=(ROOT/".api_key_main").read_text().strip().split(":")
    ex=ccxt.gate({"apiKey":k,"secret":s,"enableRateLimit":True,"options":{"defaultType":"swap"}})
    bal=ex.fetch_balance()
    print("  FUTURES/swap balance reachable:", {kk:vv for kk,vv in (bal.get("USDT") or {}).items()})
except Exception as e:
    print("  FUTURES not enabled / error:", str(e)[:160])
PY

echo; echo "════════════════════════════════════════════════════════════"
echo " DIAGNOSTIC COMPLETE — copy ALL output above back to Manus."
echo "════════════════════════════════════════════════════════════"
