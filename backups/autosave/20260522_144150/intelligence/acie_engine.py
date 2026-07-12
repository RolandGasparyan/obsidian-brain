#!/usr/bin/env python3

import json
import time
from datetime import datetime
from pathlib import Path

RUNTIME = Path("intelligence/runtime")
REPORTS = Path("intelligence/reports")
LOGS = Path("intelligence/logs")

STATE_FILE = RUNTIME / "acie_state.json"
REPORT_FILE = REPORTS / "acie_report.md"
LOG_FILE = LOGS / "acie_engine.log"

START_BALANCE = 1500.0

def log(msg):

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{ts}] [ACIE] {msg}"

    print(line)

    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def calculate():

    current_balance = 1500 + (__import__("random").randint(-150, 300))

    pnl = current_balance - START_BALANCE

    confidence = __import__("random").randint(40, 95)

    volatility = __import__("random").randint(20, 100)

    drawdown = max(0, START_BALANCE - current_balance)

    risk = 2.0

    if confidence >= 85:
        risk += 2.0

    elif confidence >= 70:
        risk += 1.0

    if volatility >= 80:
        risk *= 0.5

    if drawdown >= 100:
        risk *= 0.5

    if drawdown >= 200:
        risk *= 0.3

    recommended_size = round(current_balance * (risk / 100), 2)

    if drawdown > 200:
        mode = "SURVIVAL"

    elif volatility > 80:
        mode = "DEFENSIVE"

    elif confidence > 85:
        mode = "ATTACK"

    else:
        mode = "BALANCED"

    return {
        "balance": current_balance,
        "pnl": pnl,
        "confidence": confidence,
        "volatility": volatility,
        "drawdown": drawdown,
        "risk_percent": round(risk, 2),
        "recommended_trade_size": recommended_size,
        "mode": mode
    }

while True:

    try:

        state = calculate()

        STATE_FILE.write_text(json.dumps(state, indent=2))

        REPORT_FILE.write_text(f"""
# ACIE ENGINE REPORT

## Timestamp
{datetime.utcnow().isoformat()}

## Balance
${state["balance"]}

## PnL
${state["pnl"]}

## Confidence
{state["confidence"]}/100

## Volatility
{state["volatility"]}/100

## Drawdown
${state["drawdown"]}

## Risk %
{state["risk_percent"]}%

## Recommended Trade Size
${state["recommended_trade_size"]}

## Current Mode
{state["mode"]}

""")

        log(
            f'MODE={state["mode"]} | '
            f'BALANCE=${state["balance"]} | '
            f'RISK={state["risk_percent"]}% | '
            f'SIZE=${state["recommended_trade_size"]}'
        )

    except Exception as e:
        log(f"ERROR: {e}")

    time.sleep(15)

