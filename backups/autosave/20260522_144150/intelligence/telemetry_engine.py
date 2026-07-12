#!/usr/bin/env python3

import time
from pathlib import Path
from datetime import datetime

LOG = Path("intelligence/logs/telemetry_engine.log")

while True:

    try:

        line = f"[{datetime.utcnow()}] TELEMETRY_OK\n"

        with open(LOG, "a") as f:
            f.write(line)

        print(line)

    except:
        pass

    time.sleep(30)

