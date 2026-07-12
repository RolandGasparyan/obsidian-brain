#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trading_guru'))

from core.engine import TimeDecayScalpingEngine

if __name__ == "__main__":
    engine = TimeDecayScalpingEngine()
    engine.run()
