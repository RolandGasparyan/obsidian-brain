#!/usr/bin/env python3

import json
import time
from datetime import datetime
from pathlib import Path

RUNTIME = Path("intelligence/runtime")
LOGS = Path("intelligence/logs")
REPORTS = Path("intelligence/reports")

STATE_FILE = RUNTIME / "fib_state.json"
LOG_FILE = LOGS / "fib_engine.log"

PAIR = "BTC/USDT"

def log(msg):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [FIB_ENGINE] {msg}"
    print(line)

    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def fib_levels(high, low):

    diff = high - low

    return {
        "0.236": round(high - diff * 0.236, 2),
        "0.382": round(high - diff * 0.382, 2),
        "0.5": round(high - diff * 0.5, 2),
        "0.618": round(high - diff * 0.618, 2),
        "0.786": round(high - diff * 0.786, 2),
    }

def classify_zone(price, levels):

    if price >= levels["0.236"]:
        return "EXTREME_BULLISH"

    elif price >= levels["0.382"]:
        return "BULLISH"

    elif price >= levels["0.5"]:
        return "MID_PULLBACK"

    elif price >= levels["0.618"]:
        return "DEEP_PULLBACK"

    elif price >= levels["0.786"]:
        return "SNIPER_ZONE"

    else:
        return "HIGH_RISK"

while True:

    try:

        # DEMO MARKET SNAPSHOT
        # later connect real exchange data

        swing_high = 110000
        swing_low = 100000
        current_price = 104500

        levels = fib_levels(swing_high, swing_low)

        zone = classify_zone(current_price, levels)

        report = {
            "pair": PAIR,
            "timestamp": datetime.utcnow().isoformat(),
            "swing_high": swing_high,
            "swing_low": swing_low,
            "current_price": current_price,
            "zone": zone,
            "fib_levels": levels,
            "recommended_action":
                "WATCH_LONGS" if zone in [
                    "SNIPER_ZONE",
                    "DEEP_PULLBACK",
                    "MID_PULLBACK"
                ] else "WAIT"
        }

        STATE_FILE.write_text(json.dumps(report, indent=2))

        md = REPORTS / "fib_report.md"

        md.write_text(
f'''
# Fibonacci God Engine

## Pair
{PAIR}

## Market State
{zone}

## Current Price
{current_price}

## Swing High
{swing_high}

## Swing Low
{swing_low}

## Fibonacci Levels

- 0.236 → {levels["0.236"]}
- 0.382 → {levels["0.382"]}
- 0.5   → {levels["0.5"]}
- 0.618 → {levels["0.618"]}
- 0.786 → {levels["0.786"]}

## Recommended Action
{report["recommended_action"]}

'''
        )

        log(f"{PAIR} | zone={zone} | action={report['recommended_action']}")

    except Exception as e:
        log(f"ERROR: {e}")

    time.sleep(15)

