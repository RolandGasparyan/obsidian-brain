#!/usr/bin/env python3

import json
import time
import random
from datetime import datetime
from pathlib import Path

RUNTIME = Path("intelligence/runtime")
LOGS = Path("intelligence/logs")
REPORTS = Path("intelligence/reports")

STATE_FILE = RUNTIME / "confidence_state.json"
LOG_FILE = LOGS / "confidence_engine.log"

PAIR = "BTC/USDT"

def log(msg):

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{ts}] [CONFIDENCE_ENGINE] {msg}"

    print(line)

    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def score_market():

    trend_strength = random.randint(50, 100)
    volume_strength = random.randint(40, 100)
    momentum = random.randint(40, 100)
    volatility = random.randint(20, 100)

    confidence = int(
        (
            trend_strength * 0.35 +
            volume_strength * 0.25 +
            momentum * 0.25 +
            (100 - volatility) * 0.15
        )
    )

    if confidence >= 85:
        mode = "ULTRA_BULLISH"

    elif confidence >= 70:
        mode = "BULLISH"

    elif confidence >= 55:
        mode = "NEUTRAL"

    elif confidence >= 40:
        mode = "DEFENSIVE"

    else:
        mode = "HIGH_RISK"

    return {
        "trend_strength": trend_strength,
        "volume_strength": volume_strength,
        "momentum": momentum,
        "volatility": volatility,
        "confidence": confidence,
        "market_mode": mode
    }

while True:

    try:

        data = score_market()

        recommendation = "WAIT"

        if data["confidence"] >= 85:
            recommendation = "FULL_ATTACK"

        elif data["confidence"] >= 70:
            recommendation = "SMART_LONGS"

        elif data["confidence"] >= 55:
            recommendation = "LIGHT_TRADING"

        elif data["confidence"] >= 40:
            recommendation = "REDUCE_SIZE"

        else:
            recommendation = "AVOID_MARKET"

        report = {
            "pair": PAIR,
            "timestamp": datetime.utcnow().isoformat(),
            "market_mode": data["market_mode"],
            "confidence": data["confidence"],
            "trend_strength": data["trend_strength"],
            "volume_strength": data["volume_strength"],
            "momentum": data["momentum"],
            "volatility": data["volatility"],
            "recommended_action": recommendation
        }

        STATE_FILE.write_text(json.dumps(report, indent=2))

        md = REPORTS / "confidence_report.md"

        md.write_text(
f'''
# Confidence Engine

## Pair
{PAIR}

## Market Mode
{data["market_mode"]}

## Confidence
{data["confidence"]}/100

## Metrics

- Trend Strength → {data["trend_strength"]}
- Volume Strength → {data["volume_strength"]}
- Momentum → {data["momentum"]}
- Volatility → {data["volatility"]}

## Recommended Action
{recommendation}

'''
        )

        log(
            f'{PAIR} | '
            f'confidence={data["confidence"]} | '
            f'mode={data["market_mode"]} | '
            f'action={recommendation}'
        )

    except Exception as e:
        log(f"ERROR: {e}")

    time.sleep(15)

