#!/usr/bin/env python3
"""
UNCRISHABLE Trading Engine - Main Entry Point
24/7 Production-Grade AI Trading System
"""

import asyncio
import signal
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.ai_manager import AIManager
from engine.auto_withdraw import AutoWithdrawSystem
from monitor.watchdog import Watchdog
from storage.config_manager import ConfigManager
from api.gate_api import GateIOAPI
from api.telegram_bot import TelegramBot

class TradingEngine:
    def __init__(self):
        self.running = False
        self.config_manager = ConfigManager()
        self.gate_api = GateIOAPI()
        self.telegram = TelegramBot()
        self.ai_manager = None
        self.auto_withdraw = None
        self.watchdog = None
        
    async def initialize(self):
        print("=" * 60)
        print("🚀 UNCRISHABLE TRADING ENGINE v1.0")
        print("=" * 60)
        
        config = self.config_manager.load_config()
        print(f"✅ Config Manager initialized")
        
        self.auto_withdraw = AutoWithdrawSystem(self.gate_api, config)
        print(f"✅ Auto-Withdraw System initialized")
        print(f"   Cold Wallet: {config.get('cold_wallet', 'Not set')}")
        print(f"   Threshold: ${config.get('withdraw_threshold', 100)}")
        
        self.ai_manager = AIManager(self.gate_api, config)
        print(f"✅ AI Manager initialized with 8 AI GODS")
        print(f"   Trading Mode: {config.get('trading_mode', 'FUTURES')}")
        print(f"   Max Leverage: {config.get('max_leverage', 10)}x")
        
        self.watchdog = Watchdog(self, self.telegram)
        print(f"✅ Health Monitor initialized")
        print("=" * 60)
        
    async def start(self):
        await self.initialize()
        self.running = True
        await self.telegram.send_alert("🚀 Trading Engine Started!")
        asyncio.create_task(self.watchdog.start())
        asyncio.create_task(self.auto_withdraw.start())
        await self.ai_manager.start_competition()
        
    async def stop(self):
        print("\n⏹️ Stopping trading engine...")
        self.running = False
        if self.ai_manager:
            await self.ai_manager.stop()
        if self.auto_withdraw:
            await self.auto_withdraw.stop()
        if self.watchdog:
            await self.watchdog.stop()
        self.config_manager.save_config()
        await self.telegram.send_alert("⏹️ Trading Engine Stopped")
        print("✅ Engine stopped gracefully")
        
    def health_check(self) -> dict:
        return {
            "running": self.running,
            "ai_manager": self.ai_manager.get_status() if self.ai_manager else None,
            "auto_withdraw": self.auto_withdraw.get_status() if self.auto_withdraw else None,
            "timestamp": datetime.now().isoformat()
        }

async def main():
    engine = TradingEngine()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(engine.stop()))
    try:
        await engine.start()
        while engine.running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await engine.stop()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        await engine.telegram.send_alert(f"❌ FATAL ERROR: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
