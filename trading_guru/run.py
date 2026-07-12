#!/usr/bin/env python3
"""
Trading Guru - Quick Start Runner
Starts the One Dollar Sniper bot with 8 AI Models
"""

import subprocess
import sys
import os

def main():
    print("🚀 Starting Trading Guru - One Dollar Sniper")
    print("=" * 50)
    
    bot_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "one_dollar_sniper.py")
    
    if os.path.exists(bot_path):
        print(f"📍 Running: {bot_path}")
        subprocess.run([sys.executable, "-u", bot_path])
    else:
        print(f"❌ Bot not found at: {bot_path}")
        print("   Try running directly: python one_dollar_sniper.py")

if __name__ == "__main__":
    main()
