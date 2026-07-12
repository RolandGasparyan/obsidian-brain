#!/usr/bin/env python3
"""
Fetch fresh DAILY BTC (and optionally ETH) OHLCV via ccxt public API (Gate, then
Binance fallback) and write lab_data/<PAIR>.csv in the lab's schema:
    timestamp,open,high,low,close,volume
No API keys (public OHLCV only). Keeps the VPS forward record advancing daily.
Read-only market data; never places orders.
"""
import os, sys, csv
DATA = os.environ.get("LAB_DATA", os.path.join(os.path.dirname(__file__), "lab_data"))
PAIRS = os.environ.get("FETCH_PAIRS", "BTC,ETH").split(",")
LIMIT = int(os.environ.get("FETCH_LIMIT", "1000"))
os.makedirs(DATA, exist_ok=True)

try:
    import ccxt
except Exception as e:
    print(f"fetch_btc: ccxt not available ({e}); leaving existing CSVs"); sys.exit(0)

def fetch(symbol):
    for name in ("gateio", "binance", "kucoin"):
        try:
            ex = getattr(ccxt, name)({"enableRateLimit": True})
            o = ex.fetch_ohlcv(symbol, timeframe="1d", limit=LIMIT)
            if o and len(o) > 60:
                return name, o
        except Exception as e:
            print(f"  {name} {symbol} failed: {e}")
    return None, None

ok = 0
for p in PAIRS:
    p = p.strip().upper()
    if not p:
        continue
    src, rows = fetch(f"{p}/USDT")
    if not rows:
        print(f"fetch_btc: no data for {p}; keeping existing CSV")
        continue
    out = os.path.join(DATA, f"{p}.csv")
    import datetime as dt
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for ms, o_, h, l, c, v in rows:
            ds = dt.datetime.utcfromtimestamp(ms/1000).strftime("%Y-%m-%d")
            w.writerow([ds, o_, h, l, c, v])
    last = rows[-1]
    last_d = dt.datetime.utcfromtimestamp(last[0]/1000).strftime("%Y-%m-%d")
    print(f"fetch_btc: {p} <- {src}  {len(rows)} daily bars, last {last_d} close {last[4]:,.2f}")
    ok += 1

sys.exit(0 if ok else 0)  # never hard-fail the loop
