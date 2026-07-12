"""
Individual AI Trader - Each AI God operates independently
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

class AITrader:
    def __init__(self, ai_id: str, config: dict, gate_api, global_config: dict):
        self.ai_id = ai_id
        self.config = config
        self.gate_api = gate_api
        self.global_config = global_config
        
        self.starting_budget = global_config.get("budget_per_ai", 86.5)
        self.current_budget = self.starting_budget
        self.total_profit = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.current_streak = 0
        self.best_streak = 0
        self.is_paused = False
        self.pause_reason = ""
        self.current_position = None
        self.last_trade_time = None
        
    async def analyze_market(self, symbol: str) -> Dict[str, Any]:
        """Analyze market and decide on trade"""
        try:
            ticker = await self.gate_api.get_ticker(symbol)
            if not ticker:
                return {"action": "HOLD", "reason": "No market data"}
            
            price = float(ticker.get("last", 0))
            change_24h = float(ticker.get("change_percentage", 0))
            
            signal = self._generate_signal(price, change_24h)
            
            return {
                "action": signal["action"],
                "confidence": signal["confidence"],
                "price": price,
                "reason": signal["reason"],
                "leverage": self.config["leverage"],
                "size_pct": self._calculate_position_size()
            }
        except Exception as e:
            return {"action": "HOLD", "reason": f"Error: {e}"}
    
    def _generate_signal(self, price: float, change_24h: float) -> Dict[str, Any]:
        """Generate trading signal based on AI personality"""
        strategy = self.config["strategy"]
        aggression = self.config["aggression"]
        
        if strategy == "scalping":
            if abs(change_24h) > 0.5:
                return {
                    "action": "SHORT" if change_24h > 0 else "LONG",
                    "confidence": min(90, 60 + aggression * 3),
                    "reason": f"Scalp reversal on {change_24h:.2f}% move"
                }
        elif strategy == "momentum":
            if abs(change_24h) > 2:
                return {
                    "action": "SHORT" if change_24h < -2 else "LONG",
                    "confidence": min(85, 55 + aggression * 3),
                    "reason": f"Momentum continuation on {change_24h:.2f}%"
                }
        elif strategy == "mean_reversion":
            if abs(change_24h) > 3:
                return {
                    "action": "LONG" if change_24h < -3 else "SHORT",
                    "confidence": min(80, 50 + aggression * 3),
                    "reason": f"Mean reversion on {change_24h:.2f}% move"
                }
        elif strategy == "breakout":
            if abs(change_24h) > 5:
                return {
                    "action": "SHORT" if change_24h < 0 else "LONG",
                    "confidence": min(85, 60 + aggression * 2),
                    "reason": f"Breakout on {change_24h:.2f}%"
                }
        
        return {"action": "HOLD", "confidence": 0, "reason": "No signal"}
    
    def _calculate_position_size(self) -> float:
        """Calculate position size based on risk and streak"""
        base_size = 0.05
        streak_bonus = min(0.02, self.current_streak * 0.005)
        return min(0.15, base_size + streak_bonus)
    
    async def execute_trade(self, symbol: str, action: str, size_usd: float) -> Optional[Dict]:
        """Execute a trade on Gate.io"""
        if self.is_paused:
            return None
            
        try:
            result = await self.gate_api.create_order(
                symbol=symbol,
                side=action.lower(),
                size=size_usd,
                leverage=self.config["leverage"]
            )
            
            if result:
                self.current_position = {
                    "symbol": symbol,
                    "side": action,
                    "entry_price": result.get("price"),
                    "size": size_usd,
                    "entry_time": datetime.now()
                }
                self.last_trade_time = datetime.now()
                self.total_trades += 1
                
            return result
        except Exception as e:
            print(f"[{self.ai_id}] Trade error: {e}")
            return None
    
    def record_result(self, pnl: float):
        """Record trade result and update stats"""
        self.total_profit += pnl
        self.current_budget += pnl
        
        if pnl > 0:
            self.winning_trades += 1
            self.current_streak = max(1, self.current_streak + 1)
            self.best_streak = max(self.best_streak, self.current_streak)
        else:
            self.losing_trades += 1
            self.current_streak = min(-1, self.current_streak - 1)
            
            if abs(self.current_streak) >= self.global_config.get("consecutive_loss_limit", 4):
                self.is_paused = True
                self.pause_reason = f"{abs(self.current_streak)} consecutive losses"
        
        self.current_position = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current AI stats"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        roi = (self.total_profit / self.starting_budget * 100) if self.starting_budget > 0 else 0
        
        return {
            "id": self.ai_id,
            "name": self.config["name"],
            "budget": self.current_budget,
            "starting_budget": self.starting_budget,
            "total_profit": self.total_profit,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": win_rate,
            "roi": roi,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "is_paused": self.is_paused,
            "pause_reason": self.pause_reason,
            "current_position": self.current_position,
            "strategy": self.config["strategy"],
            "leverage": self.config["leverage"]
        }
    
    def unpause(self):
        """Unpause the AI trader"""
        self.is_paused = False
        self.pause_reason = ""
        self.current_streak = 0
