#!/usr/bin/env python3
"""
GODS MODE LEVEL 13 - RUNNER
Runs the trading bot continuously with auto-restart
"""

import subprocess
import time
import sys
import os

def main():
    print("=" * 60)
    print("⚡ GODS MODE LEVEL 13 - STARTING REAL TRADING ⚡")
    print("=" * 60)
    print("Direction: SHORTS ONLY")
    print("Pairs: BTC, ETH, SOL, XRP, AVAX")
    print("Leverage: 3x")
    print("AI Agents: 6 Gods")
    print("=" * 60)
    
    os.makedirs('logs', exist_ok=True)
    
    while True:
        try:
            print("\n🚀 Starting GODS MODE bot...")
            process = subprocess.run(
                [sys.executable, "gods_mode_level_13.py"],
                cwd="/home/runner/workspace"
            )
            
            if process.returncode != 0:
                print(f"Bot exited with code {process.returncode}, restarting in 5s...")
                time.sleep(5)
            else:
                break
                
        except KeyboardInterrupt:
            print("\n👋 Shutdown requested, exiting...")
            break
        except Exception as e:
            print(f"Error: {e}, restarting in 10s...")
            time.sleep(10)

if __name__ == "__main__":
    main()
