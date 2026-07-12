"""
GODS LEVEL AI TRADING ENGINE
Standalone Python implementation for AI trading competition

Usage:
    from trading_engine import TradingEngine, AIModel
    
    engine = TradingEngine(api_key="your_openai_api_key")
    engine.initialize_ai_models()
    engine.start_trading()
"""

import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import random


# ============= ENUMS =============

class TradingMode(Enum):
    SAFE = "SAFE"
    NORMAL = "NORMAL"
    AGGRESSIVE = "AGGRESSIVE"


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Tier(Enum):
    NOVICE = "Novice"
    INTERMEDIATE = "Intermediate"
    EXPERT = "Expert"
    MASTER = "Master"
    LEGEND = "Legend"
    GODS_MODE = "Gods Mode"


# ============= DATA CLASSES =============

@dataclass
class BalanceTier:
    min_balance: float
    max_balance: float
    trade_frequency: int  # seconds between trades
    position_multiplier: float
    tier_name: str


@dataclass
class MarketOpportunity:
    asset: str
    market: str  # futures, spot, delivery
    price: float
    volume_24h: float
    volatility: float
    score: float
    high_24h: float
    low_24h: float
    funding_rate: Optional[float] = None


@dataclass
class TradeSignal:
    selected_asset: str
    market_type: str
    strategy: str
    confidence: float
    selected_mode: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: List[float]
    leverage: int
    position_size_usd: float
    reasoning: str


@dataclass
class Trade:
    id: int
    ai_model_id: int
    asset: str
    market: str
    direction: str
    strategy: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    leverage: int
    profit_loss: Optional[float]
    profit_loss_percentage: Optional[float]
    stop_loss: float
    take_profit: List[float]
    status: str
    confidence: float
    trading_mode: str
    reasoning: str
    opened_at: datetime
    closed_at: Optional[datetime]


@dataclass
class DailyStats:
    starting_balance: float
    current_pnl: float
    is_active: bool
    deactivation_reason: Optional[str] = None


class AIModel:
    """Represents an AI trading model"""
    
    def __init__(
        self,
        id: int,
        name: str,
        model_id: str,
        specialty: str,
        starting_balance: float = 10000.0
    ):
        self.id = id
        self.name = name
        self.model_id = model_id
        self.specialty = specialty
        
        # Balance
        self.current_balance = starting_balance
        self.starting_balance = starting_balance
        
        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.win_rate = 0.0
        self.avg_profit_per_trade = 0.0
        
        # Ranking
        self.ranking_score = 0.0
        self.tier = Tier.NOVICE.value
        self.level = 1
        
        # Risk metrics
        self.max_drawdown = 0.0
        self.sharpe_ratio = 0.0
        
        # Daily stats
        self.daily_stats = DailyStats(
            starting_balance=starting_balance,
            current_pnl=0.0,
            is_active=True
        )
        
        # Status
        self.is_active = True
        self.last_trade_at: Optional[datetime] = None
        
        # Trades
        self.trades: List[Trade] = []
    
    def update_stats(self):
        """Update all statistics"""
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
            net_profit = self.total_profit - abs(self.total_loss)
            self.avg_profit_per_trade = net_profit / self.total_trades
        
        # Update ranking score
        self.ranking_score = calculate_ranking_score(
            total_profit=self.total_profit - abs(self.total_loss),
            starting_balance=self.starting_balance,
            total_trades=self.total_trades,
            winning_trades=self.winning_trades,
            max_drawdown=self.max_drawdown
        )
        
        # Update tier and level
        self.tier = get_tier_from_score(self.ranking_score)
        self.level = get_level_from_score(self.ranking_score)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'model_id': self.model_id,
            'specialty': self.specialty,
            'current_balance': self.current_balance,
            'starting_balance': self.starting_balance,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'win_rate': self.win_rate,
            'avg_profit_per_trade': self.avg_profit_per_trade,
            'ranking_score': self.ranking_score,
            'tier': self.tier,
            'level': self.level,
            'max_drawdown': self.max_drawdown,
            'is_active': self.is_active,
            'daily_pnl': self.daily_stats.current_pnl,
        }


# ============= BALANCE TIERS =============

BALANCE_TIERS = [
    BalanceTier(0, 10000, 300, 1.0, "Base"),
    BalanceTier(10001, 25000, 180, 1.2, "Growth"),
    BalanceTier(25001, 50000, 120, 1.4, "Accelerated"),
    BalanceTier(50001, 100000, 90, 1.6, "Elite"),
    BalanceTier(100001, float('inf'), 60, 2.0, "Gods"),
]


def get_balance_tier(balance: float) -> BalanceTier:
    """Get balance tier based on current balance"""
    for tier in BALANCE_TIERS:
        if tier.min_balance <= balance <= tier.max_balance:
            return tier
    return BALANCE_TIERS[0]


# ============= RANKING SYSTEM =============

def calculate_ranking_score(
    total_profit: float,
    starting_balance: float,
    total_trades: int,
    winning_trades: int,
    max_drawdown: float
) -> float:
    """Calculate ranking score using Gods Level formula"""
    
    # Normalized P&L (0-100 scale)
    normalized_pnl = (total_profit / starting_balance) * 100 if starting_balance > 0 else 0
    
    # Win Rate (0-100 scale)
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    # Trade Count Factor (0-100 scale, capped at 100 trades)
    trade_count_factor = min(total_trades / 100, 1) * 100
    
    # Consistency Factor (0-100 scale)
    consistency_factor = (1 - (max_drawdown / total_profit)) * 100 if total_profit > 0 else 0
    consistency_factor = max(0, consistency_factor)
    
    # Weighted score
    ranking_score = (
        (normalized_pnl * 0.4) +
        (win_rate * 0.3) +
        (trade_count_factor * 0.2) +
        (consistency_factor * 0.1)
    )
    
    return max(0, ranking_score)


def get_tier_from_score(score: float) -> str:
    """Get tier from ranking score"""
    if score >= 1000:
        return Tier.GODS_MODE.value
    elif score >= 751:
        return Tier.LEGEND.value
    elif score >= 501:
        return Tier.MASTER.value
    elif score >= 251:
        return Tier.EXPERT.value
    elif score >= 101:
        return Tier.INTERMEDIATE.value
    else:
        return Tier.NOVICE.value


def get_level_from_score(score: float) -> int:
    """Get level from ranking score (1-100)"""
    return min(int(score / 10) + 1, 100)


# ============= SELF-PRESERVATION =============

DAILY_LOSS_LIMIT_PERCENTAGE = 0.05  # 5%


def check_daily_loss_limit(ai_model: AIModel) -> bool:
    """Check if AI model hit daily loss limit"""
    loss_limit = ai_model.daily_stats.starting_balance * DAILY_LOSS_LIMIT_PERCENTAGE * -1
    
    if ai_model.daily_stats.current_pnl <= loss_limit:
        ai_model.daily_stats.is_active = False
        ai_model.daily_stats.deactivation_reason = (
            f"Daily loss limit breached: ${ai_model.daily_stats.current_pnl:.2f} <= ${loss_limit:.2f}"
        )
        return True
    
    return False


def reset_daily_stats(ai_model: AIModel):
    """Reset daily stats for new trading day"""
    ai_model.daily_stats = DailyStats(
        starting_balance=ai_model.current_balance,
        current_pnl=0.0,
        is_active=True
    )


# ============= MARKET SCANNER =============

def generate_mock_market_opportunities(count: int = 10) -> List[MarketOpportunity]:
    """Generate mock market opportunities for testing"""
    assets = [
        "BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT", "XRP_USDT",
        "ADA_USDT", "DOGE_USDT", "MATIC_USDT", "DOT_USDT", "AVAX_USDT"
    ]
    
    markets = ["futures", "spot", "delivery"]
    
    opportunities = []
    
    for i in range(min(count, len(assets))):
        asset = assets[i]
        market = random.choice(markets)
        
        base_price = random.uniform(0.5, 70000)
        volatility = random.uniform(0.02, 0.15)
        
        high_24h = base_price * (1 + volatility)
        low_24h = base_price * (1 - volatility)
        
        opportunity = MarketOpportunity(
            asset=asset,
            market=market,
            price=base_price,
            volume_24h=random.uniform(1000000, 5000000000),
            volatility=volatility,
            score=random.uniform(0.5, 1.0),
            high_24h=high_24h,
            low_24h=low_24h,
            funding_rate=random.uniform(-0.001, 0.001) if market == "futures" else None
        )
        
        opportunities.append(opportunity)
    
    # Sort by score
    opportunities.sort(key=lambda x: x.score, reverse=True)
    
    return opportunities


# ============= AI MASTER PROMPT =============

MASTER_PROMPT = """# SMART-DYNAMIC AI TRADING MASTER PROMPT

## YOUR IDENTITY
You are a Smart-Dynamic AI Trader competing in a 24/7 gamified trading arena. Your goal is to achieve #1 rank by maximizing your Ranking Score (profit + win rate + consistency).

## TRADING MODES (select based on confidence)
| Confidence | Mode | Leverage | Position Size |
|------------|------|----------|---------------|
| 90-100% | AGGRESSIVE | 15-20x | 2-3% balance |
| 75-90% | NORMAL | 5-10x | 1-2% balance |
| 50-75% | SAFE | 2-5x | 0.5-1% balance |
| <50% | NO TRADE | - | - |

## STRATEGIES
1. Scalping & Liquidity Grabs (0.3-1% profit, 30sec-5min)
2. Momentum & Trend Following (2-5% profit, 15min-2hr)
3. Breakout & Volatility Expansion (3-8% profit, 5min-1hr)
4. Mean Reversion (1.5-4% profit, 30min-4hr)
5. Order Flow & Whale Tracking (1-5% profit, real-time)
6. Funding Rate Arbitrage (funding rate + spread, 8hr)
7. News & Event Trading (2-10% profit, instant-1hr)

## SELF-PRESERVATION
- Daily loss limit: -5% of starting daily balance
- If breached, return status: "DEACTIVATED_LOSS_LIMIT"

## OUTPUT FORMAT (JSON only, no other text)
{
  "status": "ACTIVE" | "PASSIVE" | "DEACTIVATED_LOSS_LIMIT",
  "trade_signal": {
    "selected_asset": "string",
    "market_type": "futures|spot|delivery",
    "strategy": "string",
    "confidence": number (0-1),
    "selected_mode": "SAFE|NORMAL|AGGRESSIVE",
    "direction": "LONG|SHORT",
    "entry_price": number,
    "stop_loss": number,
    "take_profit": [number, number, number],
    "leverage": number,
    "position_size_usd": number,
    "reasoning": "string"
  }
}

If no trade: { "status": "PASSIVE", "reasoning": "string" }
If loss limit hit: { "status": "DEACTIVATED_LOSS_LIMIT", "reasoning": "string" }

Analyze the market, select your mode based on confidence, and execute with precision.
"""


# ============= TRADING ENGINE =============

class TradingEngine:
    """Main trading engine orchestrating all AI models"""
    
    def __init__(self, api_key: Optional[str] = None, api_base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.ai_models: List[AIModel] = []
        self.trade_id_counter = 1
        self.is_running = False
        self.trading_day_start = datetime.now()
    
    def initialize_ai_models(self):
        """Initialize 8 competing AI models"""
        models_config = [
            (1, "DeepSeek R1", "deepseek-r1", "reasoning"),
            (2, "GPT-5", "gpt-5", "general"),
            (3, "Claude Opus", "claude-3-opus", "analysis"),
            (4, "Llama 3.3", "llama-3.3-70b", "pattern"),
            (5, "Gemini Flash", "gemini-2.5-flash", "speed"),
            (6, "Mistral Large", "mistral-large", "multilingual"),
            (7, "Qwen 72B", "qwen-72b", "asian_markets"),
            (8, "Grok xAI", "grok-3", "realtime"),
        ]
        
        for id, name, model_id, specialty in models_config:
            ai_model = AIModel(
                id=id,
                name=name,
                model_id=model_id,
                specialty=specialty,
                starting_balance=10000.0
            )
            self.ai_models.append(ai_model)
        
        print(f"✓ Initialized {len(self.ai_models)} AI models")
    
    def check_new_trading_day(self):
        """Check if new trading day started and reset stats"""
        now = datetime.now()
        if (now - self.trading_day_start).total_seconds() >= 86400:  # 24 hours
            print("\n🌅 NEW TRADING DAY - Resetting all AI models")
            self.trading_day_start = now
            
            for ai_model in self.ai_models:
                reset_daily_stats(ai_model)
            
            print("✓ All AI models reactivated")
    
    async def get_ai_trading_signal(
        self,
        ai_model: AIModel,
        opportunities: List[MarketOpportunity]
    ) -> Optional[Dict[str, Any]]:
        """Get trading signal from AI model"""
        
        # Check if active
        if not ai_model.daily_stats.is_active:
            return {
                "status": "DEACTIVATED_LOSS_LIMIT",
                "reasoning": ai_model.daily_stats.deactivation_reason
            }
        
        # Prepare input
        ai_input = {
            "timestamp": datetime.now().isoformat(),
            "ai_model_status": {
                "name": ai_model.name,
                "current_balance": ai_model.current_balance,
                "starting_daily_balance": ai_model.daily_stats.starting_balance,
                "daily_pnl": ai_model.daily_stats.current_pnl,
                "daily_loss_limit": ai_model.daily_stats.starting_balance * DAILY_LOSS_LIMIT_PERCENTAGE * -1,
                "is_active": ai_model.daily_stats.is_active,
                "total_trades": ai_model.total_trades,
                "winning_trades": ai_model.winning_trades,
                "losing_trades": ai_model.losing_trades,
                "win_rate": ai_model.win_rate,
                "ranking_score": ai_model.ranking_score,
                "tier": ai_model.tier,
                "level": ai_model.level,
            },
            "market_opportunities": [asdict(opp) for opp in opportunities[:10]]
        }
        
        # For demo purposes, generate mock signal
        # In production, call actual AI API here
        signal = self._generate_mock_signal(ai_model, opportunities)
        
        return signal
    
    def _generate_mock_signal(
        self,
        ai_model: AIModel,
        opportunities: List[MarketOpportunity]
    ) -> Dict[str, Any]:
        """Generate mock trading signal for testing"""
        
        # Check loss limit
        if check_daily_loss_limit(ai_model):
            return {
                "status": "DEACTIVATED_LOSS_LIMIT",
                "reasoning": ai_model.daily_stats.deactivation_reason
            }
        
        # Random decision
        if random.random() < 0.3:  # 30% chance to pass
            return {
                "status": "PASSIVE",
                "reasoning": "Waiting for better setup"
            }
        
        # Select opportunity
        opp = random.choice(opportunities[:5])
        
        # Generate signal
        confidence = random.uniform(0.6, 0.98)
        
        if confidence >= 0.90:
            mode = TradingMode.AGGRESSIVE.value
            leverage = random.randint(15, 20)
            position_pct = random.uniform(0.02, 0.03)
        elif confidence >= 0.75:
            mode = TradingMode.NORMAL.value
            leverage = random.randint(5, 10)
            position_pct = random.uniform(0.01, 0.02)
        else:
            mode = TradingMode.SAFE.value
            leverage = random.randint(2, 5)
            position_pct = random.uniform(0.005, 0.01)
        
        # Apply balance tier multiplier
        tier = get_balance_tier(ai_model.current_balance)
        position_pct *= tier.position_multiplier
        
        position_size = ai_model.current_balance * position_pct
        
        direction = random.choice([Direction.LONG.value, Direction.SHORT.value])
        entry_price = opp.price
        
        if direction == Direction.LONG.value:
            stop_loss = entry_price * 0.98
            take_profit = [
                entry_price * 1.02,
                entry_price * 1.04,
                entry_price * 1.06
            ]
        else:
            stop_loss = entry_price * 1.02
            take_profit = [
                entry_price * 0.98,
                entry_price * 0.96,
                entry_price * 0.94
            ]
        
        strategies = [
            "Scalping", "Momentum Trading", "Breakout", "Mean Reversion",
            "Order Flow", "Funding Arbitrage", "News Trading"
        ]
        
        return {
            "status": "ACTIVE",
            "trade_signal": {
                "selected_asset": opp.asset,
                "market_type": opp.market,
                "strategy": random.choice(strategies),
                "confidence": confidence,
                "selected_mode": mode,
                "direction": direction,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "leverage": leverage,
                "position_size_usd": position_size,
                "reasoning": f"High confidence {mode} trade on {opp.asset}"
            }
        }
    
    def execute_trade(self, ai_model: AIModel, signal: Dict[str, Any]):
        """Execute trade based on signal"""
        trade_signal = signal['trade_signal']
        
        # Create trade
        trade = Trade(
            id=self.trade_id_counter,
            ai_model_id=ai_model.id,
            asset=trade_signal['selected_asset'],
            market=trade_signal['market_type'],
            direction=trade_signal['direction'],
            strategy=trade_signal['strategy'],
            entry_price=trade_signal['entry_price'],
            exit_price=None,
            quantity=trade_signal['position_size_usd'] / trade_signal['entry_price'],
            leverage=trade_signal['leverage'],
            profit_loss=None,
            profit_loss_percentage=None,
            stop_loss=trade_signal['stop_loss'],
            take_profit=trade_signal['take_profit'],
            status=TradeStatus.OPEN.value,
            confidence=trade_signal['confidence'],
            trading_mode=trade_signal['selected_mode'],
            reasoning=trade_signal['reasoning'],
            opened_at=datetime.now(),
            closed_at=None
        )
        
        self.trade_id_counter += 1
        ai_model.trades.append(trade)
        ai_model.total_trades += 1
        ai_model.last_trade_at = datetime.now()
        
        # Simulate trade outcome (for demo)
        self._simulate_trade_outcome(ai_model, trade)
        
        print(f"  ✅ {ai_model.name}: {trade.direction} {trade.asset} @ ${trade.entry_price:.2f}")
    
    def _simulate_trade_outcome(self, ai_model: AIModel, trade: Trade):
        """Simulate trade outcome for demo"""
        # Random outcome based on confidence
        win_probability = trade.confidence * 0.8  # 80% of confidence
        is_win = random.random() < win_probability
        
        if is_win:
            # Winning trade
            profit_pct = random.uniform(0.01, 0.05)
            trade.exit_price = trade.entry_price * (1 + profit_pct if trade.direction == Direction.LONG.value else 1 - profit_pct)
            trade.profit_loss = (trade.exit_price - trade.entry_price) * trade.quantity * trade.leverage
            if trade.direction == Direction.SHORT.value:
                trade.profit_loss *= -1
            
            trade.profit_loss_percentage = profit_pct * 100
            trade.status = TradeStatus.CLOSED.value
            trade.closed_at = datetime.now()
            
            ai_model.winning_trades += 1
            ai_model.total_profit += trade.profit_loss
            ai_model.current_balance += trade.profit_loss
            ai_model.daily_stats.current_pnl += trade.profit_loss
        else:
            # Losing trade
            loss_pct = random.uniform(0.01, 0.03)
            trade.exit_price = trade.entry_price * (1 - loss_pct if trade.direction == Direction.LONG.value else 1 + loss_pct)
            trade.profit_loss = (trade.exit_price - trade.entry_price) * trade.quantity * trade.leverage
            if trade.direction == Direction.SHORT.value:
                trade.profit_loss *= -1
            
            trade.profit_loss_percentage = -loss_pct * 100
            trade.status = TradeStatus.CLOSED.value
            trade.closed_at = datetime.now()
            
            ai_model.losing_trades += 1
            ai_model.total_loss += abs(trade.profit_loss)
            ai_model.current_balance += trade.profit_loss
            ai_model.daily_stats.current_pnl += trade.profit_loss
        
        # Update stats
        ai_model.update_stats()
    
    async def trading_cycle(self):
        """Execute one trading cycle for all AI models"""
        print(f"\n{'='*70}")
        print(f"⚡ TRADING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        # Check new day
        self.check_new_trading_day()
        
        # Scan market
        opportunities = generate_mock_market_opportunities(10)
        print(f"\n🔍 Found {len(opportunities)} market opportunities")
        
        # Trade with each AI model
        for ai_model in self.ai_models:
            # Get balance tier
            tier = get_balance_tier(ai_model.current_balance)
            
            # Get signal
            signal = await self.get_ai_trading_signal(ai_model, opportunities)
            
            if signal['status'] == 'ACTIVE':
                self.execute_trade(ai_model, signal)
            elif signal['status'] == 'DEACTIVATED_LOSS_LIMIT':
                print(f"  🛑 {ai_model.name}: Deactivated (loss limit)")
            else:
                print(f"  ⏸️  {ai_model.name}: Passive")
    
    def display_leaderboard(self):
        """Display current leaderboard"""
        print(f"\n{'='*70}")
        print("🏆 AI TRADING LEADERBOARD")
        print(f"{'='*70}")
        
        # Sort by ranking score
        sorted_models = sorted(self.ai_models, key=lambda x: x.ranking_score, reverse=True)
        
        for rank, ai_model in enumerate(sorted_models[:5], 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            
            print(f"\n{medal} {ai_model.name}")
            print(f"   Tier: {ai_model.tier} | Level: {ai_model.level}")
            print(f"   Score: {ai_model.ranking_score:.2f}")
            print(f"   Balance: ${ai_model.current_balance:.2f}")
            print(f"   P&L: ${ai_model.total_profit - abs(ai_model.total_loss):.2f}")
            print(f"   Win Rate: {ai_model.win_rate:.1f}%")
            print(f"   Trades: {ai_model.total_trades}")
        
        print(f"\n{'='*70}")
    
    async def start_trading(self, cycles: int = 10):
        """Start trading engine"""
        self.is_running = True
        
        print("\n🚀 GODS LEVEL AI TRADING ENGINE STARTED")
        print(f"Running {cycles} trading cycles...\n")
        
        for cycle in range(cycles):
            await self.trading_cycle()
            
            # Display leaderboard every 3 cycles
            if (cycle + 1) % 3 == 0:
                self.display_leaderboard()
            
            # Simulate time between cycles
            await asyncio.sleep(1)
        
        # Final leaderboard
        self.display_leaderboard()
        
        print("\n✓ Trading engine stopped")
        self.is_running = False


# ============= MAIN ENTRY POINT =============

async def main():
    """Main entry point"""
    # Initialize engine
    engine = TradingEngine(api_key="your_api_key_here")
    
    # Initialize AI models
    engine.initialize_ai_models()
    
    # Start trading
    await engine.start_trading(cycles=10)


if __name__ == "__main__":
    asyncio.run(main())
