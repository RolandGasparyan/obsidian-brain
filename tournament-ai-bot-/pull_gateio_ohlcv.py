from __future__ import annotations
import argparse, csv, json, sys, time
from pathlib import Path
from urllib import request, parse

GATEIO_BASE = "https://api.gateio.ws/api/v4"
CANDLES_ENDPOINT = "/spot/candlesticks"
PAGE_LIMIT = 1000

INTERVAL_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "8h": 28800,
    "1d": 86400,
}

def fetch_page(pair, end_ts, interval):
    step = INTERVAL_SECONDS[interval]
    start_ts = end_ts - (PAGE_LIMIT - 1) * step
    params = {
        "currency_pair": pair,
        "interval": interval,
        "from": start_ts,
        "to": end_ts,
    }
    url = f"{GATEIO_BASE}{CANDLES_ENDPOINT}?{parse.urlencode(params)}"
    req = request.Request(url, headers={"Accept": "application/json"})
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def pull_pair(pair, days, interval, outdir):
    if interval not in INTERVAL_SECONDS:
        print(f"Unsupported interval: {interval}")
        return

    step = INTERVAL_SECONDS[interval]
    now = int(time.time())
    oldest = now - days * 24 * 3600
    candles = []
    cursor = now

    while cursor > oldest:
        batch = fetch_page(pair, cursor, interval)
        if not batch:
            break
        candles.extend(batch)
        cursor = int(batch[0][0]) - 1
        time.sleep(0.4)

    seen = {}
    for c in candles:
        ts = int(c[0])
        if ts >= oldest:
            seen[ts] = c

    rows = sorted(seen.values(), key=lambda x: int(x[0]))

    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{pair}_{interval}_{days}d.csv"

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for r in rows:
            w.writerow([r[0], r[5], r[3], r[4], r[2], r[6]])

    print(f"Wrote {len(rows)} rows to {path}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", default="BTC_USDT")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--interval", default="1m")
    p.add_argument("--outdir", default="./calib_data")
    args = p.parse_args()

    outdir = Path(args.outdir)
    for pair in args.pairs.split(","):
        pull_pair(pair.strip(), args.days, args.interval, outdir)

if __name__ == "__main__":
    main()
