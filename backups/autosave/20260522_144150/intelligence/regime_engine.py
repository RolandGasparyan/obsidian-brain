#!/usr/bin/env python3

import json
import time
import random
from pathlib import Path
from datetime import datetime

RUNTIME = Path("intelligence/runtime")
REPORTS = Path("intelligence/reports")
LOGS = Path("intelligence/logs")

STATE_FILE = RUNTIME / "regime_state.json"
REPORT_FILE = REPORTS / "regime_report.md"
LOG_FILE = LOGS / "regime_engine.log"

REGIMES = [
    "BULL_TREND",
    "BEAR_TREND",
    "SIDEWAYS",
    "PANIC",
    "VOLATILITY_EXPANSION",
    "MOMENTUM_BREAKOUT",
    "LOW_LIQUIDITY"
]

def log(msg):

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{ts}] [REGIME] {msg}"

    print(line)

    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def detect_regime():

    regime = random.choice(REGIMES)

    strength = random.randint(40, 100)

    volatility = random.randint(20, 100)

    momentum = random.randint(20, 100)

    liquidity = random.randint(20, 100)

    aggression = 1.0

    if regime == "BULL_TREND":
        aggression = 1.5

    elif regime == "MOMENTUM_BREAKOUT":
        aggression = 1.7

    elif regime == "SIDEWAYS":
        aggression = 0.7

    elif regime == "PANIC":
        aggression = 0.2

    elif regime == "LOW_LIQUIDITY":
        aggression = 0.4

    elif regime == "VOLATILITY_EXPANSION":
        aggression = 0.6

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "regime": regime,
        "strength": strength,
        "volatility": volatility,
        "momentum": momentum,
        "liquidity": liquidity,
        "aggression_multiplier": aggression
    }

while True:

    try:

        state = detect_regime()

        STATE_FILE.write_text(json.dumps(state, indent=2))

        REPORT_FILE.write_text(f"""
# REGIME ENGINE REPORT

## Timestamp
{state["timestamp"]}

## Current Regime
{state["regime"]}

## Strength
{state["strength"]}/100

## Volatility
{state["volatility"]}/100

## Momentum
{state["momentum"]}/100

## Liquidity
{state["liquidity"]}/100

## Aggression Multiplier
{state["aggression_multiplier"]}

""")

        log(
            f'REGIME={state["regime"]} | '
            f'STRENGTH={state["strength"]} | '
            f'VOL={state["volatility"]} | '
            f'AGGR={state["aggression_multiplier"]}'
        )

    except Exception as e:
        log(f"ERROR: {e}")

    time.sleep(15)

