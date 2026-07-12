#!/usr/bin/env python3
"""
SCALP BATTLE LIVE v2.0 — Self-Healing Edition
TITAN (MAIN) | VELOCITY (SUB1) | SENTINEL (SUB2)
$5/trade | TP 0.25% | SL 0.15% | CMO+EMA3 signal
Self-healing: API errors → simulation mode, retry every 5 min
"""
import json, os, sys, time, hmac, hashlib, signal, pathlib, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path("/home/ubuntu/canary")
LOG_FILE   = ROOT / "runtime" / "scalp_battle.log"
STATE_FILE = ROOT / "runtime" / "scalp_battle_state.json"
HEALTH_FILE = ROOT / "runtime" / "scalp_battle_health.json"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

TRADE_SIZE_USDT = 5.0
TP_PCT = 0.0025
SL_PCT = 0.0015
COOLDOWN_S = 45
MAX_OPEN = 3
TICK_S = 10
API_RETRY_INTERVAL = 300  # 5 min between API retries when in simulation mode

ACCOUNTS = {
    "TITAN":    {"key_file": ROOT/".api_key_main",  "dd_cap": 31.59, "floor": 100.0},
    "VELOCITY": {"key_file": ROOT/".api_key_sub1",  "dd_cap":  4.00, "floor":  50.0},
    "SENTINEL": {"key_file": ROOT/".api_key_sub2",  "dd_cap":  4.00, "floor":  50.0},
}
PAIRS = ["FLOKI_USDT","WIF_USDT","OP_USDT","SHIB_USDT","DOT_USDT","ADA_USDT","UNI_USDT","ATOM_USDT","BNB_USDT"]
# base-amount decimal precision per pair (from Gate.io currency_pairs amount_precision)
AMT_PREC = {"FLOKI_USDT":0,"WIF_USDT":2,"OP_USDT":0,"SHIB_USDT":0,"DOT_USDT":2,"ADA_USDT":2,"UNI_USDT":2,"ATOM_USDT":2,"BNB_USDT":3}

def floor_amt(pair, qty):
    """Floor base qty to the pair's allowed precision so Gate.io accepts the SELL."""
    p = AMT_PREC.get(pair, 4)
    f = 10 ** p
    import math
    v = math.floor(float(qty) * f) / f
    return f"{v:.{p}f}"

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE,"a") as f: f.write(line+"\n")
    except: pass

def write_health(agents, mode="LIVE"):
    try:
        health = {
            "status": "running",
            "mode": mode,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "agents": {a.name: {"balance": a.balance, "live": a.live_mode, "api_ok": a.api_ok} for a in agents}
        }
        with open(HEALTH_FILE, "w") as f: json.dump(health, f, indent=2)
    except: pass

class GateClient:
    BASE = "https://api.gateio.ws/api/v4"
    def __init__(self, key, secret):
        self.key = key; self.secret = secret
        self.ok = bool(key and secret)
    def _sign(self, method, path, query="", body=""):
        ts = str(int(time.time()))
        bh = hashlib.sha512(body.encode()).hexdigest()
        msg = f"{method}\n{path}\n{query}\n{bh}\n{ts}"
        sig = hmac.new(self.secret.encode(), msg.encode(), hashlib.sha512).hexdigest()
        return {"KEY": self.key, "Timestamp": ts, "SIGN": sig, "Content-Type": "application/json", "Accept": "application/json"}
    def _req(self, method, path, params=None, body=None):
        if not self.ok: return None
        query = urllib.parse.urlencode(params) if params else ""
        hdrs = self._sign(method, "/api/v4" + path, query, body or "")
        url = self.BASE + path + ("?" + query if query else "")
        req = urllib.request.Request(url, data=(body or "").encode() if body else None, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise  # propagate auth errors
            try: detail = e.read().decode()[:300]
            except Exception: detail = ""
            log(f"    [GateClient] {method} {path} HTTP {e.code} | {detail}")
            return None
        except Exception as e:
            log(f"    [GateClient] {method} {path} error: {e}")
            return None
    def spot_balance(self, currency="USDT"):
        data = self._req("GET", "/spot/accounts", {"currency": currency})
        if data and isinstance(data, list):
            for a in data:
                if a.get("currency") == currency: return float(a.get("available", 0))
        return None
    def market_buy_quote(self, pair, quote_usdt):
        # market BUY: amount = quote (USDT) to spend; tif=ioc required for market
        body = json.dumps({"currency_pair": pair, "side": "buy", "amount": str(quote_usdt), "type": "market", "time_in_force": "ioc"})
        return self._req("POST", "/spot/orders", body=body)
    def market_sell_base(self, pair, base_amount):
        # market SELL: amount = base coin qty to sell; tif=ioc required for market
        body = json.dumps({"currency_pair": pair, "side": "sell", "amount": str(base_amount), "type": "market", "time_in_force": "ioc"})
        return self._req("POST", "/spot/orders", body=body)

def load_keys(key_file):
    try:
        raw = pathlib.Path(key_file).read_text().strip()
        if ":" in raw:
            parts = raw.split(":", 1)
            return parts[0].strip(), parts[1].strip()
        data = json.loads(raw)
        return data.get("key", ""), data.get("secret", "")
    except Exception as e:
        log(f"  [KEYS] Failed to load {key_file}: {e}")
        return "", ""

def cmo(closes, period=14):
    if len(closes) < period + 1: return 0.0
    ups = sum(max(closes[i] - closes[i-1], 0) for i in range(-period, 0))
    dns = sum(max(closes[i-1] - closes[i], 0) for i in range(-period, 0))
    return (ups - dns) / (ups + dns) * 100 if (ups + dns) > 0 else 0.0

def ema(closes, period=3):
    if not closes: return 0.0
    k = 2 / (period + 1); e = closes[0]
    for c in closes[1:]: e = c * k + e * (1 - k)
    return e

class Agent:
    def __init__(self, name, cfg):
        self.name = name
        self.dd_cap = cfg["dd_cap"]
        self.floor = cfg["floor"]
        self.open_trades = []
        self.cooldowns = {}
        self.wins = 0; self.losses = 0
        self.paused_until = None
        self.live_mode = False
        self.api_ok = False
        self.last_api_retry = 0
        self.balance = 200.0
        self.balance_start = 200.0
        self.day_start = 200.0
        self.day_reset = datetime.now(timezone.utc).date()
        self.sim_equity = 200.0  # track sim separately

        key, secret = load_keys(cfg["key_file"])
        self.gate = GateClient(key, secret)
        self._try_connect()

    def _try_connect(self):
        """Try to connect to Gate.io spot API. Falls back to simulation if fails."""
        try:
            bal = self.gate.spot_balance()
            if bal is not None:
                self.balance = bal
                self.balance_start = bal
                self.day_start = bal
                self.sim_equity = bal
                self.live_mode = True
                self.api_ok = True
                log(f"  [{self.name}] ✅ LIVE MODE — balance=${bal:.2f} USDT")
            else:
                self._enter_sim()
        except urllib.error.HTTPError as e:
            log(f"  [{self.name}] ⚠️ API {e.code} — entering SIMULATION mode (retry in {API_RETRY_INTERVAL}s)")
            self._enter_sim()
        except Exception as e:
            log(f"  [{self.name}] ⚠️ API error: {e} — entering SIMULATION mode")
            self._enter_sim()
        self.last_api_retry = time.time()

    def _enter_sim(self):
        self.live_mode = False
        self.api_ok = False
        log(f"  [{self.name}] 🔄 SIMULATION MODE — balance=${self.balance:.2f} (virtual)")

    def _maybe_retry_api(self):
        """Periodically retry API connection when in simulation mode."""
        if self.live_mode: return
        if time.time() - self.last_api_retry < API_RETRY_INTERVAL: return
        log(f"  [{self.name}] 🔄 Retrying API connection...")
        self._try_connect()

    def day_pnl(self):
        today = datetime.now(timezone.utc).date()
        if today != self.day_reset:
            self.day_start = self.balance; self.day_reset = today
        return self.balance - self.day_start

    def is_paused(self):
        if self.paused_until and datetime.now(timezone.utc) < self.paused_until:
            return True
        self.paused_until = None; return False

    def try_open(self, pair, price, closes):
        self._maybe_retry_api()
        if self.is_paused(): return
        if len(self.open_trades) >= MAX_OPEN: return
        if self.cooldowns.get(pair, 0) > time.time(): return
        if self.balance <= self.floor: return
        if self.day_pnl() <= -self.dd_cap:
            self.paused_until = datetime.now(timezone.utc) + timedelta(hours=4)
            log(f"  [{self.name}] DD_CAP hit ${self.dd_cap} — paused 4h")
            return
        c = cmo(closes); e = ema(closes)
        if not (c > 20 and price > e): return  # LONG (bullish) signal
        amount = round(TRADE_SIZE_USDT / price, 6)
        tp = round(price * (1 + TP_PCT), 6); sl = round(price * (1 - SL_PCT), 6)  # long: TP above, SL below
        mode_tag = "LIVE" if self.live_mode else "SIM"
        if self.live_mode:
            r = self.gate.market_buy_quote(pair, f"{TRADE_SIZE_USDT:.4f}")  # spend $5 USDT
            if r is None:
                log(f"  [{self.name}] ⚠️ BUY failed — switching to SIM")
                self._enter_sim()
                return
            # market BUY response: filled_amount = base coin received; fee charged in base coin
            try:
                filled = float(r.get("filled_amount", 0) or 0)
                fee = float(r.get("fee", 0) or 0)
                fee_ccy = r.get("fee_currency", "")
                base_ccy = pair.split("_")[0]
                net = filled - (fee if fee_ccy == base_ccy else 0.0)
                if net > 0: amount = net
            except Exception: pass
        else:
            r = {"id": f"sim_{int(time.time())}"}
        self.open_trades.append({"pair": pair, "entry": price, "tp": tp, "sl": sl, "amount": amount, "id": r.get("id", ""), "mode": mode_tag})
        self.cooldowns[pair] = time.time() + COOLDOWN_S
        log(f"  [{self.name}] [{mode_tag}] ▶ BUY {pair} @ ${price:.6f} TP=${tp:.6f} SL=${sl:.6f}")

    def check_exits(self, prices):
        keep = []
        for t in self.open_trades:
            p = prices.get(t["pair"])
            if p is None: keep.append(t); continue
            reason = None
            if p >= t["tp"]: reason = "TP_HIT"
            elif p <= t["sl"]: reason = "SL_HIT"
            if not reason: keep.append(t); continue
            pnl = (p - t["entry"]) * t["amount"]  # long PnL
            if self.live_mode and t.get("mode") == "LIVE":
                self.gate.market_sell_base(t["pair"], floor_amt(t["pair"], t["amount"]))
            self.balance += pnl
            if pnl > 0: self.wins += 1
            else: self.losses += 1
            mode_tag = t.get("mode", "SIM")
            log(f"  [{self.name}] [{mode_tag}] {'✅' if pnl>0 else '❌'} {reason} {t['pair']} PnL=${pnl:+.6f} Bal=${self.balance:.2f}")
        self.open_trades = keep

    def snap(self):
        tot = self.wins + self.losses
        return {
            "name": self.name, "balance": round(self.balance, 4),
            "pnl": round(self.balance - self.balance_start, 4),
            "day_pnl": round(self.day_pnl(), 4), "wins": self.wins, "losses": self.losses,
            "win_rate": round(self.wins / tot * 100, 2) if tot else 0.0,
            "open": len(self.open_trades),
            "paused": str(self.paused_until) if self.paused_until else None,
            "mode": "LIVE_SCALP_BATTLE" if self.live_mode else "SIM_SCALP_BATTLE",
            "api_ok": self.api_ok
        }

def fetch_prices(pairs):
    prices = {}
    for pair in pairs:
        try:
            url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                d = json.loads(r.read())
                if d: prices[pair] = float(d[0]["last"])
        except: pass
    return prices

def fetch_closes(pair, limit=30):
    try:
        url = f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={pair}&interval=1m&limit={limit}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            bars = json.loads(r.read()); return [float(b[2]) for b in bars]
    except: return []

def save_state(agents, tick):
    state = {
        "version": "scalp-battle-live-v2", "tick": tick,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "LIVE_SCALP_BATTLE",
        "agents": [a.snap() for a in agents],
        "leaderboard": sorted([a.snap() for a in agents], key=lambda x: x["pnl"], reverse=True)
    }
    tmp = str(STATE_FILE) + ".tmp"
    with open(tmp, "w") as f: json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)

def main():
    log("=" * 60)
    log("SCALP BATTLE LIVE v2.0 — SELF-HEALING EDITION")
    log(f"Pairs: {PAIRS}")
    log(f"$5/trade | TP 0.25% | SL 0.15% | CMO+EMA3 | Auto-retry API every {API_RETRY_INTERVAL}s")
    log("=" * 60)
    agents = [Agent(n, c) for n, c in ACCOUNTS.items()]
    live_count = sum(1 for a in agents if a.live_mode)
    log(f"  Agents: {live_count}/3 in LIVE mode, {3-live_count}/3 in SIMULATION mode")
    stop = [False]
    def _s(*_): stop[0] = True
    signal.signal(signal.SIGTERM, _s); signal.signal(signal.SIGINT, _s)
    tick = 0
    while not stop[0]:
        tick += 1
        try:
            prices = fetch_prices(PAIRS)
            for pair in PAIRS:
                p = prices.get(pair)
                if not p: continue
                closes = fetch_closes(pair, 30)
                if not closes: continue
                for agent in agents: agent.try_open(pair, p, closes)
            for agent in agents: agent.check_exits(prices)
            if tick % 6 == 0:
                save_state(agents, tick)
                write_health(agents)
                snaps = sorted([a.snap() for a in agents], key=lambda x: x["pnl"], reverse=True)
                log(f"  Tick {tick} | " + " | ".join(
                    f"{s['name']} ${s['balance']:.2f} ({s['pnl']:+.4f}) [{s['mode'].split('_')[0]}]"
                    for s in snaps
                ))
        except Exception as e:
            log(f"  [ERROR] tick {tick}: {e}")
        time.sleep(TICK_S)
    save_state(agents, tick)
    log("Stopped.")

if __name__ == "__main__": main()
