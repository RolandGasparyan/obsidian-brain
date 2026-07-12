#!/usr/bin/env bash
# ============================================================
# SCALP BATTLE LIVE — One-shot installer for DO VPS (root)
# Paste this entire script into your DO VPS root shell.
# ============================================================
set -e
echo "=== SCALP BATTLE LIVE INSTALLER ==="

# 1. Directories
mkdir -p /root/canary/runtime

# 2. Write scalp_battle_live.py
cat > /root/canary/scalp_battle_live.py << 'PYEOF'
#!/usr/bin/env python3
"""
SCALP BATTLE LIVE — 3 Agents, Real Gate.io Spot Orders
TITAN (MAIN) | VELOCITY (SUB1) | SENTINEL (SUB2)
$5/trade | TP 0.25% | SL 0.15% | CMO+EMA3 signal
Championship rules: SHORT-only, DD caps, cold wallet floor
"""
import json, os, sys, time, hmac, hashlib, signal, pathlib, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path("/root/canary")
LOG_FILE  = ROOT / "runtime" / "scalp_battle.log"
STATE_FILE = ROOT / "runtime" / "scalp_battle_state.json"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

TRADE_SIZE_USDT = 5.0
TP_PCT = 0.0025
SL_PCT = 0.0015
COOLDOWN_S = 45
MAX_OPEN = 3
TICK_S = 10

ACCOUNTS = {
    "TITAN":    {"key_file": ROOT/".api_key_main",  "dd_cap": 31.59, "floor": 100.0},
    "VELOCITY": {"key_file": ROOT/".api_key_sub1",  "dd_cap":  4.00, "floor":  50.0},
    "SENTINEL": {"key_file": ROOT/".api_key_sub2",  "dd_cap":  4.00, "floor":  50.0},
}
PAIRS = ["FLOKI_USDT","WIF_USDT","OP_USDT","SHIB_USDT","DOT_USDT","ADA_USDT","UNI_USDT","ATOM_USDT","BNB_USDT"]

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        open(LOG_FILE,"a").write(line+"\n")
    except: pass

class GateClient:
    BASE = "https://api.gateio.ws/api/v4"
    def __init__(self,key,secret):
        self.key=key; self.secret=secret
    def _sign(self,method,path,query="",body=""):
        ts=str(int(time.time()))
        bh=hashlib.sha512(body.encode()).hexdigest()
        msg=f"{method}\n{path}\n{query}\n{bh}\n{ts}"
        sig=hmac.new(self.secret.encode(),msg.encode(),hashlib.sha512).hexdigest()
        return {"KEY":self.key,"Timestamp":ts,"SIGN":sig,"Content-Type":"application/json","Accept":"application/json"}
    def get(self,path,params=None):
        q=urllib.parse.urlencode(params or {})
        url=f"{self.BASE}{path}"+(f"?{q}" if q else "")
        req=urllib.request.Request(url,headers=self._sign("GET",path,q))
        with urllib.request.urlopen(req,timeout=8) as r: return json.loads(r.read())
    def post(self,path,body):
        raw=json.dumps(body)
        req=urllib.request.Request(f"{self.BASE}{path}",data=raw.encode(),headers=self._sign("POST",path,"",raw),method="POST")
        with urllib.request.urlopen(req,timeout=10) as r: return json.loads(r.read())
    def spot_balance(self):
        try:
            for a in self.get("/spot/accounts"):
                if a.get("currency")=="USDT": return float(a.get("available",0))
        except Exception as e: log(f"  [warn] balance: {e}")
        return 0.0
    def place_sell(self,pair,amount):
        try: return self.post("/spot/orders",{"currency_pair":pair,"side":"sell","amount":amount,"type":"market","time_in_force":"ioc","account":"spot"})
        except Exception as e: log(f"  [warn] sell {pair}: {e}"); return None
    def place_buy(self,pair,amount):
        try: return self.post("/spot/orders",{"currency_pair":pair,"side":"buy","amount":amount,"type":"market","time_in_force":"ioc","account":"spot"})
        except Exception as e: log(f"  [warn] buy {pair}: {e}"); return None

def cmo(closes,period=9):
    if len(closes)<period+1: return 0.0
    su=sd=0.0
    for i in range(-period,0):
        d=closes[i]-closes[i-1]
        if d>0: su+=d
        else: sd+=abs(d)
    return 0.0 if su+sd==0 else 100.0*(su-sd)/(su+sd)

def ema(closes,period):
    if len(closes)<period: return closes[-1]
    k=2.0/(period+1); val=sum(closes[:period])/period
    for v in closes[period:]: val=v*k+val*(1-k)
    return val

def signal_short(closes):
    if len(closes)<20: return False
    return cmo(closes,9)>20.0 and ema(closes,3)<ema(closes,8)

class Agent:
    def __init__(self,name,cfg):
        self.name=name; self.cfg=cfg
        k,s=pathlib.Path(cfg["key_file"]).read_text().strip().split(":",1)
        self.gate=GateClient(k,s)
        self.balance=self.gate.spot_balance()
        self.balance_start=self.balance
        self.day_start=self.balance
        self.day_key=datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.open_trades=[]; self.closed=[]; self.wins=self.losses=0
        self.cooldowns={}; self.paused_until=None
        log(f"  [{name}] init — ${self.balance:.2f} USDT")
    def _roll(self):
        today=datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today!=self.day_key: self.day_key=today; self.day_start=self.balance; self.paused_until=None
    def day_pnl(self): return self.balance-self.day_start
    def paused(self):
        self._roll()
        if self.paused_until: return True
        if self.day_pnl()<=-self.cfg["dd_cap"]:
            t=(datetime.now(timezone.utc)+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
            self.paused_until=t.isoformat()
            log(f"  [{self.name}] ⛔ DD cap hit; paused until {self.paused_until}"); return True
        if self.balance<=self.cfg["floor"]:
            self.paused_until="9999-12-31"
            log(f"  [{self.name}] 🥶 floor hit; paused"); return True
        return False
    def try_open(self,pair,price,closes):
        if self.paused() or len(self.open_trades)>=MAX_OPEN: return
        if any(t["pair"]==pair for t in self.open_trades): return
        if time.time()<self.cooldowns.get(pair,0): return
        if not signal_short(closes): return
        amt=TRADE_SIZE_USDT/price; amt_s=f"{amt:.6f}"
        tp=price*(1-TP_PCT); sl=price*(1+SL_PCT)
        order=self.gate.place_sell(pair,amt_s)
        if not order: return
        self.open_trades.append({"pair":pair,"entry":price,"amount":amt,"tp":tp,"sl":sl,
            "opened_at":datetime.now(timezone.utc).isoformat(),"order_id":order.get("id","")})
        self.cooldowns[pair]=time.time()+COOLDOWN_S
        log(f"  [{self.name}] ▶ SELL {pair} @ ${price:.6f} TP=${tp:.6f} SL=${sl:.6f}")
    def check_exits(self,prices):
        keep=[]
        for t in self.open_trades:
            p=prices.get(t["pair"])
            if p is None: keep.append(t); continue
            reason=None
            if p<=t["tp"]: reason="TP_HIT"
            elif p>=t["sl"]: reason="SL_HIT"
            if not reason: keep.append(t); continue
            self.gate.place_buy(t["pair"],f"{t['amount']:.6f}")
            pnl=(t["entry"]-p)*t["amount"]; self.balance+=pnl
            if pnl>0: self.wins+=1
            else: self.losses+=1
            log(f"  [{self.name}] {'✅' if pnl>0 else '❌'} {reason} {t['pair']} PnL=${pnl:+.6f} Bal=${self.balance:.2f}")
        self.open_trades=keep
    def snap(self):
        tot=self.wins+self.losses
        return {"name":self.name,"balance":round(self.balance,4),"pnl":round(self.balance-self.balance_start,4),
            "day_pnl":round(self.day_pnl(),4),"wins":self.wins,"losses":self.losses,
            "win_rate":round(self.wins/tot*100,2) if tot else 0.0,
            "open":len(self.open_trades),"paused":self.paused_until,"mode":"LIVE_SCALP_BATTLE"}

def fetch_prices(pairs):
    prices={}
    for pair in pairs:
        try:
            url=f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}"
            req=urllib.request.Request(url,headers={"Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=5) as r:
                d=json.loads(r.read())
                if d: prices[pair]=float(d[0]["last"])
        except: pass
    return prices

def fetch_closes(pair,limit=30):
    try:
        url=f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={pair}&interval=1m&limit={limit}"
        req=urllib.request.Request(url,headers={"Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=8) as r:
            bars=json.loads(r.read()); return [float(b[2]) for b in bars]
    except: return []

def save_state(agents,tick):
    state={"version":"scalp-battle-live-v1","tick":tick,
        "updated_at":datetime.now(timezone.utc).isoformat(),"mode":"LIVE_SCALP_BATTLE",
        "agents":[a.snap() for a in agents],
        "leaderboard":sorted([a.snap() for a in agents],key=lambda x:x["pnl"],reverse=True)}
    tmp=str(STATE_FILE)+".tmp"
    with open(tmp,"w") as f: json.dump(state,f,indent=2)
    os.replace(tmp,STATE_FILE)

def main():
    log("="*60); log("SCALP BATTLE LIVE v1.0 — TITAN / VELOCITY / SENTINEL")
    log(f"Pairs: {PAIRS}"); log(f"$5/trade | TP 0.25% | SL 0.15% | CMO+EMA3"); log("="*60)
    agents=[Agent(n,c) for n,c in ACCOUNTS.items()]
    stop=[False]
    def _s(*_): stop[0]=True
    signal.signal(signal.SIGTERM,_s); signal.signal(signal.SIGINT,_s)
    tick=0
    while not stop[0]:
        tick+=1
        try:
            prices=fetch_prices(PAIRS)
            for pair in PAIRS:
                p=prices.get(pair)
                if not p: continue
                closes=fetch_closes(pair,30)
                if not closes: continue
                for agent in agents: agent.try_open(pair,p,closes)
            for agent in agents: agent.check_exits(prices)
            if tick%6==0:
                save_state(agents,tick)
                snaps=sorted([a.snap() for a in agents],key=lambda x:x["pnl"],reverse=True)
                log(f"  Tick {tick} | "+" | ".join(f"{s['name']} ${s['balance']:.2f} ({s['pnl']:+.4f})" for s in snaps))
        except Exception as e: log(f"  [ERROR] tick {tick}: {e}")
        time.sleep(TICK_S)
    save_state(agents,tick); log("Stopped.")

if __name__=="__main__": main()
PYEOF

chmod +x /root/canary/scalp_battle_live.py
echo "[1/4] Script written to /root/canary/scalp_battle_live.py"

# 3. Systemd unit
cat > /etc/systemd/system/scalp-battle-live.service << 'SVCEOF'
[Unit]
Description=Scalp Battle Live — 3 Agents Real Gate.io Spot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/canary
ExecStart=/usr/bin/python3 /root/canary/scalp_battle_live.py
Restart=always
RestartSec=15
StandardOutput=append:/root/canary/runtime/scalp_battle.log
StandardError=append:/root/canary/runtime/scalp_battle.log

[Install]
WantedBy=multi-user.target
SVCEOF

echo "[2/4] Systemd unit written"

# 4. Enable + start
systemctl daemon-reload
systemctl enable scalp-battle-live
systemctl start scalp-battle-live
echo "[3/4] Service started"

# 5. Smoke check
sleep 5
STATUS=$(systemctl is-active scalp-battle-live)
echo "[4/4] Service status: $STATUS"
if [ "$STATUS" = "active" ]; then
    echo "✅ SCALP BATTLE LIVE is running!"
    echo "   Log:   tail -f /root/canary/runtime/scalp_battle.log"
    echo "   State: cat /root/canary/runtime/scalp_battle_state.json"
    echo "   Stop:  systemctl stop scalp-battle-live"
else
    echo "❌ Service failed to start. Check: journalctl -u scalp-battle-live -n 30"
fi
