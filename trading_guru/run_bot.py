#!/usr/bin/env python3
"""
Quick launcher for Trading Guru Bot - REAL TRADING MODE
SHORTS ONLY with AI-powered 6-agent consensus
"""

import sys
import os

sys.path.insert(0, '/home/runner/workspace')
os.chdir('/home/runner/workspace')

from trading_guru.bot.trading_bot import run_bot

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TRADING GURU BOT - REAL TRADING MODE LAUNCHER")
    print("=" * 80)
    print("Direction: SHORTS ONLY")
    print("Strategies: Grid + Scalping + Martingale")
    print("AI: 6-Agent Consensus (Real OpenAI API)")
    print("=" * 80 + "\n")
    
    run_bot()
