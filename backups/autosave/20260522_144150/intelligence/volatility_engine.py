#!/usr/bin/env python3

import json
import time
import random
from pathlib import Path
from datetime import datetime

STATE = Path("intelligence/runtime/volatility_state.json")
LOG = Path("intelligence/logs/volatility_engine.log")

def log(msg):

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{ts}] [VOL] {msg}"

    print(line)

    with open(LOG, "a") as f:
        f.write(line + "\n")

while True:

    try:

        level = random.randint(1,100)

        if level >= 80:
            state = "EXTREME"

        elif level >= 60:
            state = "HIGH"

        elif level >= 40:
            state = "MEDIUM"

        else:
            state = "LOW"

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "volatility": level,
            "state": state
        }

        STATE.write_text(json.dumps(data, indent=2))

        log(f"VOL={level} STATE={state}")

    except Exception as e:
        log(f"ERROR {e}")

    time.sleep(15)

