#!/usr/bin/env python3

import json
import time
import random
from pathlib import Path
from datetime import datetime

RUNTIME = Path("intelligence/runtime")
REPORTS = Path("intelligence/reports")
LOGS = Path("intelligence/logs")

STATE_FILE = RUNTIME / "triple_state.json"
REPORT_FILE = REPORTS / "triple_engine_report.md"
LOG_FILE = LOGS / "triple_engine.log"

MAX_LEVEL = 3

BASE_RISK = 1.0

def log(msg):

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{ts}] [TRIPLE] {msg}"

    print(line)

    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def compute():

    balance = 1500 + random.randint(-100, 300)

    confidence = random.randint(40, 100)

    volatility = random.randint(10, 100)

    loss_streak = random.randint(0, 5)

    multiplier = 1.0

    mode = "NORMAL"

    if loss_streak == 1:
        multiplier = 1.5

    elif loss_streak == 2:
        multiplier = 2.2

    elif loss_streak == 3:
        multiplier = 3.0

    elif loss_streak >= 4:
        multiplier = 0.5
        mode = "SAFE_MODE"

    if volatility >= 80:
        multiplier *= 0.5
        mode = "VOLATILITY_DEFENSE"

    if confidence <= 50:
        multiplier *= 0.7

    risk = BASE_RISK * multiplier

    trade_size = round(balance * (risk / 100), 2)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "balance": balance,
        "confidence": confidence,
        "volatility": volatility,
        "loss_streak": loss_streak,
        "multiplier": round(multiplier,2),
        "risk_percent": round(risk,2),
        "recommended_trade_size": trade_size,
        "mode": mode
    }

while True:

    try:

        state = compute()

        STATE_FILE.write_text(json.dumps(state, indent=2))

        REPORT_FILE.write_text(f"""
# SMART TRIPLE ENGINE

## Timestamp
{state["timestamp"]}

## Balance
${state["balance"]}

## Confidence
{state["confidence"]}

## Volatility
{state["volatility"]}

## Loss Streak
{state["loss_streak"]}

## Multiplier
{state["multiplier"]}x

## Risk
{state["risk_percent"]}%

## Recommended Size
${state["recommended_trade_size"]}

## Mode
{state["mode"]}

""")

        log(
            f'STREAK={state["loss_streak"]} | '
            f'MULT={state["multiplier"]}x | '
            f'RISK={state["risk_percent"]}% | '
            f'SIZE=${state["recommended_trade_size"]} | '
            f'MODE={state["mode"]}'
        )

    except Exception as e:
        log(f"ERROR {e}")

    time.sleep(15)

