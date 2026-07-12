#!/usr/bin/env python3
"""
LIQUIDATE TO USDT — Championship Rule Enforcer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sells ALL non-USDT tokens back to USDT on all 3 accounts.
Championship rule: agents must end holding only USDT.

- Skips USDT itself
- Skips dust below MIN_VALUE_USDT (unsellable, would just error)
- Uses market sell with time_in_force=ioc
- Respects Gate.io min order size by checking value first
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import pathlib, urllib.request, urllib.parse, hmac, hashlib, json, time

ROOT = pathlib.Path("/home/ubuntu/canary")
BASE = "https://api.gateio.ws/api/v4"
MIN_VALUE_USDT = 1.0   # only sell holdings worth >= $1 (Gate.io min order ~$1-3)

ACCOUNTS = [
    (".api_key_main", "TITAN"),
    (".api_key_sub1", "VELOCITY"),
    (".api_key_sub2", "SENTINEL"),
]

def sign(key, secret, method, path, query="", body=""):
    ts = str(int(time.time()))
    bh = hashlib.sha512(body.encode()).hexdigest()
    msg = f"{method}\n/api/v4{path}\n{query}\n{bh}\n{ts}"
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha512).hexdigest()
    return {"KEY": key, "Timestamp": ts, "SIGN": sig,
            "Content-Type": "application/json", "Accept": "application/json"}

def api(key, secret, method, path, params=None, body=None):
    query = urllib.parse.urlencode(params) if params else ""
    hdrs = sign(key, secret, method, path, query, body or "")
    url = BASE + path + ("?" + query if query else "")
    req = urllib.request.Request(url, data=(body or "").encode() if body else None,
                                 headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def public_price(pair):
    try:
        url = f"{BASE}/spot/tickers?currency_pair={pair}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read())
            if d and isinstance(d, list):
                return float(d[0].get("last", 0))
    except Exception:
        pass
    return 0.0

def get_min_amount(pair):
    """Get min base amount + precision for a spot pair."""
    try:
        url = f"{BASE}/spot/currency_pairs/{pair}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read())
            return {
                "min_base": float(d.get("min_base_amount", 0) or 0),
                "amount_precision": int(d.get("amount_precision", 6) or 6),
                "tradable": d.get("trade_status") == "tradable",
            }
    except Exception:
        return {"min_base": 0, "amount_precision": 6, "tradable": True}

def liquidate_account(key, secret, label):
    print(f"\n{'='*50}\n {label}\n{'='*50}")
    accts = api(key, secret, "GET", "/spot/accounts")
    total_recovered = 0.0
    for a in accts:
        cur = a.get("currency")
        avail = float(a.get("available", 0))
        if cur == "USDT" or avail <= 0:
            continue
        pair = f"{cur}_USDT"
        price = public_price(pair)
        if price <= 0:
            print(f"  SKIP {cur}: no USDT market / price unavailable")
            continue
        value = avail * price
        if value < MIN_VALUE_USDT:
            print(f"  SKIP {cur}: ${value:.4f} below ${MIN_VALUE_USDT} min (dust)")
            continue
        info = get_min_amount(pair)
        if not info["tradable"]:
            print(f"  SKIP {cur}: pair not tradable")
            continue
        # Round qty DOWN to amount precision
        prec = info["amount_precision"]
        qty = int(avail * (10 ** prec)) / (10 ** prec)
        if info["min_base"] > 0 and qty < info["min_base"]:
            print(f"  SKIP {cur}: qty {qty} below min_base {info['min_base']}")
            continue
        body = json.dumps({"currency_pair": pair, "side": "sell",
                           "amount": str(qty), "type": "market",
                           "time_in_force": "ioc"})
        try:
            res = api(key, secret, "POST", "/spot/orders", body=body)
            filled = float(res.get("filled_total", 0) or 0)
            total_recovered += filled
            print(f"  SOLD {cur}: {qty} @ ~{price:.8f} → +{filled:.4f} USDT  [{res.get('status')}]")
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:140]
            print(f"  FAIL {cur}: HTTP {e.code} {err}")
        time.sleep(0.3)
    # final USDT
    accts2 = api(key, secret, "GET", "/spot/accounts")
    usdt = next((float(x["available"]) for x in accts2 if x["currency"] == "USDT"), 0.0)
    print(f"  → {label} recovered ~${total_recovered:.2f}, USDT now = ${usdt:.2f}")
    return total_recovered, usdt

if __name__ == "__main__":
    print("LIQUIDATE TO USDT — Championship Rule Enforcer")
    grand = 0.0
    for f, label in ACCOUNTS:
        raw = (ROOT/f).read_text().strip()
        key, secret = raw.split(":", 1)
        rec, usdt = liquidate_account(key.strip(), secret.strip(), label)
        grand += rec
    print(f"\n{'='*50}\n TOTAL RECOVERED: ~${grand:.2f} USDT\n{'='*50}")
