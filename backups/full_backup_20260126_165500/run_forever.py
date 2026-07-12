#!/usr/bin/env python3
"""
Trading Guru - 24/7 Continuous Runner
Runs all trading systems on loop forever without stopping
"""

import subprocess
import time
import signal
import sys
import os
from datetime import datetime

os.chdir('/home/runner/workspace')
sys.path.insert(0, '/home/runner/workspace')

RESTART_DELAY = 5  # Seconds between restarts
LOG_INTERVAL = 60  # Log status every 60 seconds

print("=" * 60)
print("TRADING GURU - 24/7 CONTINUOUS LOOP")
print("=" * 60)
print(f"Started: {datetime.now()}")
print("Mode: SHORTS ONLY - Never stops")
print("=" * 60)

running = True

def signal_handler(sig, frame):
    global running
    print("\nShutdown signal received...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Import SAFE bot
from trading_guru_optimal import SafeTradingBot, SafeConfig

restart_count = 0

while running:
    restart_count += 1
    print(f"\n[{datetime.now()}] Starting SAFE bot (Run #{restart_count})")
    
    try:
        config = SafeConfig()
        bot = SafeTradingBot(config)
        bot.run()
    except KeyboardInterrupt:
        print("Manual stop requested")
        running = False
    except Exception as e:
        print(f"[ERROR] Bot crashed: {e}")
        print(f"Restarting in {RESTART_DELAY} seconds...")
        time.sleep(RESTART_DELAY)

print("\n" + "=" * 60)
print("TRADING GURU STOPPED")
print(f"Total runs: {restart_count}")
print("=" * 60)
