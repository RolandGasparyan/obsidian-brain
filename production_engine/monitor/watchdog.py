"""
Watchdog - Health monitoring and auto-restart
"""

import asyncio
import psutil
from datetime import datetime
from typing import Any, Dict

class Watchdog:
    def __init__(self, engine, telegram):
        self.engine = engine
        self.telegram = telegram
        self.running = False
        
        self.check_interval = 60
        self.max_restart_attempts = 3
        self.restart_count = 0
        self.last_check = None
        self.start_time = datetime.now()
        
        self.health_history = []
        
    async def start(self):
        """Start health monitoring"""
        self.running = True
        print(f"🔍 Watchdog started (checking every {self.check_interval}s)")
        
        while self.running:
            try:
                health = await self._check_health()
                self._log_health(health)
                
                if not health["is_healthy"]:
                    await self._handle_unhealthy(health)
                    
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ Watchdog error: {e}")
                await asyncio.sleep(10)
    
    async def _check_health(self) -> Dict[str, Any]:
        """Perform health check"""
        self.last_check = datetime.now()
        
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        engine_status = self.engine.health_check()
        
        is_healthy = (
            engine_status.get("running", False) and
            cpu_percent < 90 and
            memory.percent < 90
        )
        
        return {
            "is_healthy": is_healthy,
            "timestamp": self.last_check.isoformat(),
            "engine_running": engine_status.get("running", False),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "restart_count": self.restart_count
        }
    
    def _log_health(self, health: Dict):
        """Log health check result"""
        self.health_history.append(health)
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-500:]
        
        status = "🟢" if health["is_healthy"] else "🔴"
        print(f"{status} Health check: CPU {health['cpu_percent']:.1f}%, MEM {health['memory_percent']:.1f}%")
    
    async def _handle_unhealthy(self, health: Dict):
        """Handle unhealthy state"""
        self.restart_count += 1
        
        message = f"⚠️ Health check failed!\n"
        message += f"CPU: {health['cpu_percent']:.1f}%\n"
        message += f"Memory: {health['memory_percent']:.1f}%\n"
        message += f"Engine: {'Running' if health['engine_running'] else 'STOPPED'}\n"
        message += f"Restart attempt: {self.restart_count}/{self.max_restart_attempts}"
        
        await self.telegram.send_alert(message)
        
        if self.restart_count >= self.max_restart_attempts:
            await self.telegram.send_alert("❌ Max restart attempts reached. Manual intervention required!")
            self.running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get watchdog status"""
        return {
            "running": self.running,
            "check_interval": self.check_interval,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "restart_count": self.restart_count,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "health_checks_count": len(self.health_history)
        }
    
    async def stop(self):
        """Stop the watchdog"""
        self.running = False
        print("🔍 Watchdog stopped")
