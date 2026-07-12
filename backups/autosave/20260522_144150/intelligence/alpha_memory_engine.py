#!/usr/bin/env python3

import json
import time
import random
from pathlib import Path
from datetime import datetime

RUNTIME = Path("intelligence/runtime")
MEMORY = Path("intelligence/memory")
REPORTS = Path("intelligence/reports")
LOGS = Path("intelligence/logs")

MEMORY_DB = MEMORY / "alpha_memory.jsonl"
REPORT = REPORTS / "alpha_memory_report.md"
LOG = LOGS / "alpha_memory_engine.log"

PATTERNS = [
    "BTC_BREAKOUT",
    "SOL_MOMENTUM",
    "ETH_REVERSAL",
    "VOLATILITY_EXPANSION",
    "LOW_LIQUIDITY_TRAP",
    "RSI_RECOVERY",
    "TREND_CONTINUATION"
]

def log(msg):

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{ts}] [ALPHA] {msg}"

    print(line)

    with open(LOG, "a") as f:
        f.write(line + "\n")

while True:

    try:

        pattern = random.choice(PATTERNS)

        score = random.randint(40, 100)

        pnl = round(random.uniform(-5, 18), 2)

        item = {
            "timestamp": datetime.utcnow().isoformat(),
            "pattern": pattern,
            "confidence": score,
            "pnl": pnl
        }

        with open(MEMORY_DB, "a") as f:
            f.write(json.dumps(item) + "\n")

        REPORT.write_text(f"""
# ALPHA MEMORY REPORT

Last Pattern:
{pattern}

Confidence:
{score}

PnL:
{pnl}

Timestamp:
{datetime.utcnow().isoformat()}
""")

        log(f"PATTERN={pattern} CONF={score} PNL={pnl}")

    except Exception as e:
        log(f"ERROR {e}")

    time.sleep(20)

