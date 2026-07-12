"""
AI Manager - Manages the competition between 8 AI GODS
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any

from engine.ai_config import AI_GODS, TRADING_PAIRS, MARKET_CONDITIONS, RISK_CONFIG
from engine.ai_trader import AITrader

class AIManager:
    def __init__(self, gate_api, config: dict):
        self.gate_api = gate_api
        self.config = config
        self.running = False
        
        self.total_balance = config.get("starting_balance", 692)
        self.budget_per_ai = self.total_balance / 8
        self.protected_balance = self.total_balance * (RISK_CONFIG["protected_balance_pct"] / 100)
        
        self.ai_traders: Dict[str, AITrader] = {}
        self.market_condition = "RANGING"
        self.last_rebalance = datetime.now()
        self.rebalance_interval = timedelta(hours=4)
        self.total_rebalances = 0
        
        self._initialize_traders()
    
    def _initialize_traders(self):
        """Initialize all 8 AI traders"""
        ai_config = {
            "budget_per_ai": self.budget_per_ai,
            "consecutive_loss_limit": RISK_CONFIG["consecutive_loss_limit"]
        }
        
        for ai_id, config in AI_GODS.items():
            self.ai_traders[ai_id] = AITrader(ai_id, config, self.gate_api, ai_config)
            print(f"   🤖 {config['name']} initialized (${self.budget_per_ai:.2f})")
    
    async def start_competition(self):
        """Start the AI competition"""
        self.running = True
        print("\n🏆 AI GODS COMPETITION STARTED!")
        print(f"   Total Budget: ${self.total_balance:.2f}")
        print(f"   Budget per AI: ${self.budget_per_ai:.2f}")
        print(f"   Protected Balance: ${self.protected_balance:.2f}")
        print(f"   Trading Pairs: {', '.join(TRADING_PAIRS)}")
        print(f"   Rebalancing: Every 4 hours\n")
        
        while self.running:
            try:
                await self._run_trading_cycle()
                await self._check_rebalance()
                await asyncio.sleep(30)
            except Exception as e:
                print(f"❌ Cycle error: {e}")
                await asyncio.sleep(10)
    
    async def _run_trading_cycle(self):
        """Run one trading cycle for all AIs"""
        current_balance = await self._get_total_balance()
        
        if current_balance < self.protected_balance:
            print(f"⚠️ Balance ${current_balance:.2f} below protected ${self.protected_balance:.2f} - PAUSING")
            return
        
        self.market_condition = await self._detect_market_condition()
        
        for symbol in TRADING_PAIRS:
            for ai_id, trader in self.ai_traders.items():
                if trader.is_paused:
                    continue
                
                if not self._strategy_matches_condition(trader.config["strategy"]):
                    continue
                
                analysis = await trader.analyze_market(symbol)
                
                if analysis["action"] in ["LONG", "SHORT"]:
                    if self.config.get("direction") == "SHORTS_ONLY" and analysis["action"] == "LONG":
                        continue
                    
                    size_usd = trader.current_budget * analysis["size_pct"]
                    if size_usd >= 5:
                        print(f"🔥 [{trader.config['name']}] {analysis['action']} {symbol} - {analysis['reason']}")
                        await trader.execute_trade(symbol, analysis["action"], size_usd)
    
    def _strategy_matches_condition(self, strategy: str) -> bool:
        """Check if strategy is active for current market condition"""
        allocation = MARKET_CONDITIONS.get(self.market_condition, {})
        return allocation.get(strategy, 0) > 0
    
    async def _detect_market_condition(self) -> str:
        """Detect current market condition"""
        try:
            btc = await self.gate_api.get_ticker("BTC_USDT")
            if btc:
                change = float(btc.get("change_percentage", 0))
                if change > 3:
                    return "TRENDING_UP"
                elif change < -3:
                    return "TRENDING_DOWN"
                elif abs(change) > 5:
                    return "VOLATILE"
            return "RANGING"
        except:
            return "RANGING"
    
    async def _check_rebalance(self):
        """Check if it's time to rebalance capital"""
        if datetime.now() - self.last_rebalance > self.rebalance_interval:
            await self._rebalance_capital()
            self.last_rebalance = datetime.now()
            self.total_rebalances += 1
    
    async def _rebalance_capital(self):
        """Rebalance capital - winners get more, losers get less"""
        print("\n💰 CAPITAL REBALANCING...")
        
        sorted_ais = sorted(
            self.ai_traders.values(),
            key=lambda x: x.total_profit,
            reverse=True
        )
        
        total_budget = sum(t.current_budget for t in sorted_ais)
        
        for i, trader in enumerate(sorted_ais):
            if i < 2:
                new_budget = trader.current_budget * 1.5
                print(f"   🥇 {trader.config['name']}: +50% (${new_budget:.2f})")
            elif i >= 6:
                new_budget = trader.current_budget * 0.5
                print(f"   📉 {trader.config['name']}: -50% (${new_budget:.2f})")
            else:
                new_budget = trader.current_budget
                
            trader.current_budget = new_budget
        
        print(f"   Rebalance #{self.total_rebalances + 1} complete\n")
    
    async def _get_total_balance(self) -> float:
        """Get total balance from Gate.io"""
        try:
            balance = await self.gate_api.get_balance()
            return float(balance.get("available", 0))
        except:
            return self.total_balance
    
    def get_leaderboard(self) -> List[Dict]:
        """Get current leaderboard"""
        sorted_ais = sorted(
            self.ai_traders.values(),
            key=lambda x: x.total_profit,
            reverse=True
        )
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        
        return [
            {**trader.get_stats(), "rank": i + 1, "medal": medals[i]}
            for i, trader in enumerate(sorted_ais)
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """Get competition status"""
        return {
            "running": self.running,
            "market_condition": self.market_condition,
            "total_balance": self.total_balance,
            "protected_balance": self.protected_balance,
            "active_ais": sum(1 for t in self.ai_traders.values() if not t.is_paused),
            "paused_ais": sum(1 for t in self.ai_traders.values() if t.is_paused),
            "total_rebalances": self.total_rebalances,
            "next_rebalance": (self.last_rebalance + self.rebalance_interval).isoformat(),
            "leaderboard": self.get_leaderboard()
        }
    
    async def stop(self):
        """Stop the competition"""
        self.running = False
        print("🏁 Competition stopped")
