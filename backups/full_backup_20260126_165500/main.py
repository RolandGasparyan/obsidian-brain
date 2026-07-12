#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/runner/workspace/trading_guru')

from core.engine import TimeDecayScalpingEngine

if __name__ == "__main__":
    engine = TimeDecayScalpingEngine()
    engine.run()
