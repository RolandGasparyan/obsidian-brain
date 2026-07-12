#!/usr/bin/env python3
"""
Signal alert — fires only when the validated setup CHANGES state
(CASH -> BTC = buy, BTC -> CASH = exit). Reads forward_test.json each loop,
compares to the last seen state, and on a flip writes an alert + (optionally)
pushes to Telegram. Idempotent: no flip => no alert. Judges only; no trading.

Telegram is OPT-IN via env (YOU set these; never stored here):
  TG_BOT_TOKEN, TG_CHAT_ID
"""
import os, json, time, urllib.parse, urllib.request

OUT = os.environ.get("FWD_OUT", os.path.join(os.path.dirname(__file__), "results"))
STATE = os.path.join(OUT, "alert_state.json")
fwd = json.load(open(os.path.join(OUT, "forward_test.json")))
cur = fwd["current_state"]                      # IN_BTC or IN_CASH
prev = None
try: prev = json.load(open(STATE)).get("state")
except Exception: pass

def notify(msg):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  {msg}"
    with open(os.path.join(OUT, "alerts.log"), "a") as f: f.write(line + "\n")
    open(os.path.join(OUT, "latest_alert.md"), "w").write(f"# ⚠️ SIGNAL\n\n{line}\n")
    tok, chat = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
    if tok and chat:
        try:
            url = f"https://api.telegram.org/bot{tok}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
            urllib.request.urlopen(url, data=data, timeout=10)
            print("  telegram: sent")
        except Exception as e:
            print(f"  telegram: failed ({e})")

if prev is None:
    print(f"alert baseline set: {cur} (no alert on first run)")
elif cur != prev:
    arrow = "🟢 BUY: CASH -> BTC" if cur == "IN_BTC" else "⚪️ EXIT: BTC -> CASH"
    msg = f"{arrow}  | MA50W10/{fwd['pair']} | close {fwd['last_close']:,.0f} | paper {fwd['paper_return_pct']:+.0f}%"
    notify(msg)
    print(f"ALERT FIRED: {msg}")
else:
    print(f"no change: still {cur}")

json.dump({"state": cur, "updated": time.time()}, open(STATE, "w"))
