#!/bin/bash
# verify_team_do.sh — confirm the DigitalOcean team setup is the SINGLE live
# engine, with no conflicting real-money engines running.
# Run as root on DO:  bash verify_team_do.sh
echo "================================================================"
echo " TRADING GURU — DigitalOcean SINGLE-ENGINE VERIFY"
echo " $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================================"

echo "--- [1] LIVE team services (should be ACTIVE) ---"
for svc in coach champion-battle; do
  printf "   %-18s " "$svc"; systemctl is-active "$svc" 2>/dev/null
done

echo "--- [2] OLD engines (should all be INACTIVE — no conflict) ---"
for svc in canary-battle scalp-battle-live canary-watchdog; do
  printf "   %-18s " "$svc"; systemctl is-active "$svc" 2>/dev/null
done

echo "--- [3] Real-money python processes running ---"
ps -eo pid,cmd | grep -E 'champion_battle|coach\.py|canary_executor|scalp_battle' | grep -v grep \
  || echo "   (none besides team)"

echo "--- [4] Coach assignments (one pair per agent, no overlap) ---"
python3 - <<'PY'
import json, pathlib
f = pathlib.Path("/root/canary/runtime/coach_signals.json")
try:
    d = json.loads(f.read_text())
    a = d.get("assignments", {})
    pairs = []
    for agent, v in a.items():
        print(f"   {agent:9s} -> {v.get('strategy','?')[:26]:26s} @ {v.get('pair','?'):11s} PF={v.get('profit_factor','?')}")
        pairs.append(v.get("pair"))
    print("   OVERLAP CHECK:", "OK (all distinct)" if len(pairs)==len(set(pairs)) else "WARNING duplicate pairs")
except Exception as e:
    print("   coach_signals.json not ready:", e)
PY

echo "--- [5] Champion battle — last 12 log lines ---"
tail -12 /root/canary/runtime/champion_battle.log 2>/dev/null || echo "   (no log yet)"

echo "--- [6] Gate.io balances (all should end in USDT) ---"
python3 - <<'PY'
import ccxt, pathlib
ROOT = pathlib.Path("/root/canary")
for f,l in [(".api_key_main","TITAN"),(".api_key_sub1","VELOCITY"),(".api_key_sub2","SENTINEL")]:
    try:
        k,s = (ROOT/f).read_text().strip().split(":",1)
        ex = ccxt.gate({"apiKey":k.strip(),"secret":s.strip(),"enableRateLimit":True,"options":{"defaultType":"spot"}})
        bal = ex.fetch_balance()
        usdt = float(bal.get("USDT",{}).get("free",0))
        # list any non-USDT, non-dust holdings (token accumulation check)
        toks = {c:float(v.get("free",0)) for c,v in bal.items() if isinstance(v,dict) and c!="USDT" and float(v.get("free",0))>0}
        toks = {c:round(a,4) for c,a in toks.items() if a>0}
        print(f"   {l:9s} USDT=${usdt:8.2f}  tokens={toks if toks else 'NONE (clean)'}")
    except Exception as e:
        print(f"   {l:9s} ERROR {type(e).__name__}: {e}")
PY
echo "================================================================"
echo " If [1]=active, [2]=inactive, [4]=distinct pairs, [6]=USDT only"
echo " => SINGLE-ENGINE TEAM is LIVE on DigitalOcean, no conflict."
echo "================================================================"
