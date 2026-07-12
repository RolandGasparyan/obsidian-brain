"""
═══════════════════════════════════════════════════════════════════════════════
GODS LEVEL STRATEGY LOGIC
Pure decision-making algorithms and dynamic balance scaling
═══════════════════════════════════════════════════════════════════════════════

This module contains the core trading logic without any database or API dependencies.
Import this into any project to use the Gods Level trading algorithms.

Usage:
    from gods_level_strategy_logic import GodsLevelStrategy
    
    strategy = GodsLevelStrategy()
    decision = strategy.make_trading_decision(
        current_balance=15000,
        starting_balance=10000,
        daily_pnl=-500,
        market_opportunities=[...]
    )
"""

import random
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS AND DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class TradingMode(Enum):
    """Trading mode based on confidence level"""
    SAFE = "SAFE"
    NORMAL = "NORMAL"
    AGGRESSIVE = "AGGRESSIVE"


class Direction(Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"


class TierLevel(Enum):
    """Ranking tier levels"""
    NOVICE = "Novice"
    INTERMEDIATE = "Intermediate"
    EXPERT = "Expert"
    MASTER = "Master"
    LEGEND = "Legend"
    GODS_MODE = "Gods Mode"


@dataclass
class BalanceTier:
    """Balance tier configuration"""
    min_balance: float
    max_balance: float
    trade_frequency_seconds: int
    position_multiplier: float
    tier_name: str
    
    def __repr__(self):
        return f"{self.tier_name} (${self.min_balance:,.0f}-${self.max_balance:,.0f})"


@dataclass
class TradingDecision:
    """Complete trading decision output"""
    status: str  # "ACTIVE", "PASSIVE", "DEACTIVATED"
    reasoning: str
    
    # Trade details (if status == "ACTIVE")
    asset: Optional[str] = None
    market_type: Optional[str] = None
    direction: Optional[Direction] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[List[float]] = None
    
    # Risk parameters
    confidence: Optional[float] = None
    trading_mode: Optional[TradingMode] = None
    leverage: Optional[int] = None
    position_size_usd: Optional[float] = None
    position_size_pct: Optional[float] = None
    
    # Strategy
    strategy: Optional[str] = None
    
    # Balance tier info
    balance_tier: Optional[BalanceTier] = None


@dataclass
class MarketOpportunity:
    """Market opportunity data"""
    asset: str
    market: str  # "futures", "spot", "delivery"
    price: float
    volume_24h: float
    volatility: float
    score: float  # 0-1, higher is better
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    funding_rate: Optional[float] = None


# ═══════════════════════════════════════════════════════════════════════════════
# GODS LEVEL STRATEGY CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class GodsLevelStrategy:
    """
    Gods Level Trading Strategy Engine
    
    Core decision-making algorithms for AI trading competition:
    - Dynamic balance scaling
    - Smart mode selection
    - Risk management
    - Self-preservation
    - Ranking system
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    BALANCE_TIERS = [
        BalanceTier(0, 10000, 300, 1.0, "Base"),
        BalanceTier(10001, 25000, 180, 1.2, "Growth"),
        BalanceTier(25001, 50000, 120, 1.4, "Accelerated"),
        BalanceTier(50001, 100000, 90, 1.6, "Elite"),
        BalanceTier(100001, float('inf'), 60, 2.0, "Gods"),
    ]
    
    DAILY_LOSS_LIMIT_PCT = 0.05  # 5%
    
    STRATEGIES = [
        "Scalping",
        "Momentum Trading",
        "Breakout",
        "Mean Reversion",
        "Order Flow",
        "Funding Arbitrage",
        "News Trading"
    ]
    
    # Mode thresholds
    AGGRESSIVE_CONFIDENCE_THRESHOLD = 0.90
    NORMAL_CONFIDENCE_THRESHOLD = 0.75
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BALANCE TIER LOGIC
    # ═══════════════════════════════════════════════════════════════════════════
    
    @classmethod
    def get_balance_tier(cls, balance: float) -> BalanceTier:
        """
        Get balance tier based on current balance
        
        Args:
            balance: Current balance in USD
            
        Returns:
            BalanceTier configuration
        """
        for tier in cls.BALANCE_TIERS:
            if tier.min_balance <= balance <= tier.max_balance:
                return tier
        return cls.BALANCE_TIERS[0]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SELF-PRESERVATION PROTOCOL
    # ═══════════════════════════════════════════════════════════════════════════
    
    @classmethod
    def check_daily_loss_limit(cls, daily_pnl: float, starting_balance: float) -> bool:
        """
        Check if daily loss limit is breached
        
        Args:
            daily_pnl: Profit/Loss for current day (negative for loss)
            starting_balance: Starting balance for the day
            
        Returns:
            True if loss limit breached, False otherwise
        """
        loss_limit = starting_balance * cls.DAILY_LOSS_LIMIT_PCT * -1
        return daily_pnl <= loss_limit
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RANKING SYSTEM
    # ═══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def calculate_ranking_score(
        total_profit: float,
        starting_balance: float,
        total_trades: int,
        winning_trades: int,
        max_drawdown: float
    ) -> float:
        """
        Calculate ranking score using Gods Level formula
        
        Formula:
            Score = (Normalized_PnL × 40%) + (Win_Rate × 30%) + 
                    (Trade_Count × 20%) + (Consistency × 10%)
        
        Args:
            total_profit: Net profit (profit - loss)
            starting_balance: Initial balance
            total_trades: Total number of trades
            winning_trades: Number of winning trades
            max_drawdown: Maximum drawdown experienced
            
        Returns:
            Ranking score (0-infinity, typically 0-2000)
        """
        # Normalized P&L (0-100 scale)
        normalized_pnl = (total_profit / starting_balance) * 100 if starting_balance > 0 else 0
        
        # Win Rate (0-100 scale)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Trade Count Factor (0-100 scale, capped at 100 trades)
        trade_count_factor = min(total_trades / 100, 1) * 100
        
        # Consistency Factor (0-100 scale)
        if total_profit != 0 and max_drawdown > 0:
            consistency_factor = (1 - (max_drawdown / abs(total_profit))) * 100
            consistency_factor = max(0, min(100, consistency_factor))
        else:
            consistency_factor = 0
        
        # Weighted score
        score = (
            (normalized_pnl * 0.4) +
            (win_rate * 0.3) +
            (trade_count_factor * 0.2) +
            (consistency_factor * 0.1)
        )
        
        return max(0, score)
    
    @staticmethod
    def get_tier_from_score(score: float) -> TierLevel:
        """Get tier level from ranking score"""
        if score >= 1000:
            return TierLevel.GODS_MODE
        elif score >= 751:
            return TierLevel.LEGEND
        elif score >= 501:
            return TierLevel.MASTER
        elif score >= 251:
            return TierLevel.EXPERT
        elif score >= 101:
            return TierLevel.INTERMEDIATE
        else:
            return TierLevel.NOVICE
    
    @staticmethod
    def get_level_from_score(score: float) -> int:
        """Get level (1-100) from ranking score"""
        return min(int(score / 10) + 1, 100)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MODE SELECTION LOGIC
    # ═══════════════════════════════════════════════════════════════════════════
    
    @classmethod
    def select_trading_mode(cls, confidence: float) -> tuple[TradingMode, int, float]:
        """
        Select trading mode based on confidence level
        
        Args:
            confidence: Confidence level (0.0-1.0)
            
        Returns:
            Tuple of (TradingMode, leverage, base_position_pct)
        """
        if confidence >= cls.AGGRESSIVE_CONFIDENCE_THRESHOLD:
            return (
                TradingMode.AGGRESSIVE,
                random.randint(15, 20),  # leverage
                random.uniform(0.02, 0.03)  # 2-3% position
            )
        elif confidence >= cls.NORMAL_CONFIDENCE_THRESHOLD:
            return (
                TradingMode.NORMAL,
                random.randint(5, 10),  # leverage
                random.uniform(0.01, 0.02)  # 1-2% position
            )
        else:
            return (
                TradingMode.SAFE,
                random.randint(2, 5),  # leverage
                random.uniform(0.005, 0.01)  # 0.5-1% position
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RISK CALCULATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def calculate_stop_loss_take_profit(
        entry_price: float,
        direction: Direction
    ) -> tuple[float, List[float]]:
        """
        Calculate stop loss and take profit levels
        
        Args:
            entry_price: Entry price
            direction: Trade direction (LONG/SHORT)
            
        Returns:
            Tuple of (stop_loss, take_profit_levels)
        """
        if direction == Direction.LONG:
            stop_loss = entry_price * 0.98  # 2% stop loss
            take_profit = [
                entry_price * 1.02,  # TP1: 2%
                entry_price * 1.04,  # TP2: 4%
                entry_price * 1.06   # TP3: 6%
            ]
        else:  # SHORT
            stop_loss = entry_price * 1.02  # 2% stop loss
            take_profit = [
                entry_price * 0.98,  # TP1: 2%
                entry_price * 0.96,  # TP2: 4%
                entry_price * 0.94   # TP3: 6%
            ]
        
        return stop_loss, take_profit
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN DECISION ENGINE
    # ═══════════════════════════════════════════════════════════════════════════
    
    @classmethod
    def make_trading_decision(
        cls,
        current_balance: float,
        starting_balance: float,
        daily_pnl: float,
        market_opportunities: List[MarketOpportunity],
        passivity_rate: float = 0.3
    ) -> TradingDecision:
        """
        Main decision-making algorithm
        
        This is the core Gods Level logic that decides:
        1. Should we trade? (Self-preservation check)
        2. Which asset to trade?
        3. What mode to use? (SAFE/NORMAL/AGGRESSIVE)
        4. Position sizing with balance tier multiplier
        5. Risk parameters (stop loss, take profit)
        
        Args:
            current_balance: Current balance in USD
            starting_balance: Starting balance for the day
            daily_pnl: Today's profit/loss
            market_opportunities: List of market opportunities
            passivity_rate: Probability of being passive (0-1)
            
        Returns:
            TradingDecision with complete trade parameters
        """
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 1: Self-Preservation Check
        # ═══════════════════════════════════════════════════════════════════════
        
        if cls.check_daily_loss_limit(daily_pnl, starting_balance):
            return TradingDecision(
                status="DEACTIVATED",
                reasoning=f"Daily loss limit breached: ${daily_pnl:.2f} (limit: {cls.DAILY_LOSS_LIMIT_PCT*100}%)"
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 2: Passivity Decision (Strategic Waiting)
        # ═══════════════════════════════════════════════════════════════════════
        
        if random.random() < passivity_rate:
            return TradingDecision(
                status="PASSIVE",
                reasoning="Waiting for better market setup"
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 3: Select Best Opportunity
        # ═══════════════════════════════════════════════════════════════════════
        
        if not market_opportunities:
            return TradingDecision(
                status="PASSIVE",
                reasoning="No market opportunities available"
            )
        
        # Select from top 5 opportunities by score
        top_opportunities = sorted(
            market_opportunities,
            key=lambda x: x.score,
            reverse=True
        )[:5]
        
        selected_opp = random.choice(top_opportunities)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 4: Generate Confidence Level
        # ═══════════════════════════════════════════════════════════════════════
        
        # Base confidence from opportunity score
        base_confidence = selected_opp.score
        
        # Add randomness (±10%)
        confidence = base_confidence + random.uniform(-0.1, 0.1)
        confidence = max(0.6, min(0.98, confidence))  # Clamp to 60-98%
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 5: Select Trading Mode
        # ═══════════════════════════════════════════════════════════════════════
        
        mode, leverage, base_position_pct = cls.select_trading_mode(confidence)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 6: Apply Balance Tier Multiplier
        # ═══════════════════════════════════════════════════════════════════════
        
        balance_tier = cls.get_balance_tier(current_balance)
        
        # Apply tier multiplier to position size
        adjusted_position_pct = base_position_pct * balance_tier.position_multiplier
        position_size_usd = current_balance * adjusted_position_pct
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 7: Determine Direction
        # ═══════════════════════════════════════════════════════════════════════
        
        direction = random.choice([Direction.LONG, Direction.SHORT])
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 8: Calculate Risk Parameters
        # ═══════════════════════════════════════════════════════════════════════
        
        entry_price = selected_opp.price
        stop_loss, take_profit = cls.calculate_stop_loss_take_profit(entry_price, direction)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 9: Select Strategy
        # ═══════════════════════════════════════════════════════════════════════
        
        strategy = random.choice(cls.STRATEGIES)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 10: Build Decision
        # ═══════════════════════════════════════════════════════════════════════
        
        reasoning = (
            f"{mode.value} {direction.value} on {selected_opp.asset} "
            f"with {confidence*100:.1f}% confidence. "
            f"Balance tier: {balance_tier.tier_name} "
            f"(multiplier: {balance_tier.position_multiplier}x)"
        )
        
        return TradingDecision(
            status="ACTIVE",
            reasoning=reasoning,
            asset=selected_opp.asset,
            market_type=selected_opp.market,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            trading_mode=mode,
            leverage=leverage,
            position_size_usd=position_size_usd,
            position_size_pct=adjusted_position_pct,
            strategy=strategy,
            balance_tier=balance_tier
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @classmethod
    def get_trade_frequency(cls, balance: float) -> int:
        """Get recommended trade frequency in seconds based on balance"""
        tier = cls.get_balance_tier(balance)
        return tier.trade_frequency_seconds
    
    @classmethod
    def format_decision(cls, decision: TradingDecision) -> str:
        """Format decision for human-readable output"""
        if decision.status != "ACTIVE":
            return f"[{decision.status}] {decision.reasoning}"
        
        return f"""
╔═══════════════════════════════════════════════════════════════════════════════
║ GODS LEVEL TRADING DECISION
╠═══════════════════════════════════════════════════════════════════════════════
║ Status: {decision.status}
║ Asset: {decision.asset}
║ Direction: {decision.direction.value}
║ Strategy: {decision.strategy}
║ 
║ CONFIDENCE & MODE:
║   Confidence: {decision.confidence*100:.1f}%
║   Mode: {decision.trading_mode.value}
║   Leverage: {decision.leverage}x
║ 
║ POSITION SIZING:
║   Balance Tier: {decision.balance_tier.tier_name}
║   Tier Multiplier: {decision.balance_tier.position_multiplier}x
║   Position Size: ${decision.position_size_usd:.2f} ({decision.position_size_pct*100:.2f}%)
║ 
║ RISK MANAGEMENT:
║   Entry: ${decision.entry_price:.2f}
║   Stop Loss: ${decision.stop_loss:.2f}
║   Take Profit 1: ${decision.take_profit[0]:.2f}
║   Take Profit 2: ${decision.take_profit[1]:.2f}
║   Take Profit 3: ${decision.take_profit[2]:.2f}
║ 
║ REASONING:
║   {decision.reasoning}
╚═══════════════════════════════════════════════════════════════════════════════
"""


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE USAGE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 80)
    print("GODS LEVEL STRATEGY LOGIC - DEMONSTRATION")
    print("═" * 80)
    print()
    
    # Create strategy instance
    strategy = GodsLevelStrategy()
    
    # Example market opportunities
    opportunities = [
        MarketOpportunity(
            asset="BTC_USDT",
            market="futures",
            price=68000.0,
            volume_24h=5000000000,
            volatility=0.08,
            score=0.92
        ),
        MarketOpportunity(
            asset="ETH_USDT",
            market="futures",
            price=3800.0,
            volume_24h=2000000000,
            volatility=0.10,
            score=0.85
        ),
        MarketOpportunity(
            asset="SOL_USDT",
            market="spot",
            price=120.0,
            volume_24h=500000000,
            volatility=0.15,
            score=0.78
        )
    ]
    
    # Simulate different balance scenarios
    scenarios = [
        {"balance": 8000, "name": "Base Tier"},
        {"balance": 15000, "name": "Growth Tier"},
        {"balance": 35000, "name": "Accelerated Tier"},
        {"balance": 75000, "name": "Elite Tier"},
        {"balance": 150000, "name": "Gods Tier"}
    ]
    
    for scenario in scenarios:
        print(f"\n{'─' * 80}")
        print(f"SCENARIO: {scenario['name']} (Balance: ${scenario['balance']:,})")
        print('─' * 80)
        
        decision = strategy.make_trading_decision(
            current_balance=scenario['balance'],
            starting_balance=10000,
            daily_pnl=0,
            market_opportunities=opportunities,
            passivity_rate=0.2  # 20% chance to be passive
        )
        
        print(strategy.format_decision(decision))
    
    # Demonstrate ranking system
    print("\n" + "═" * 80)
    print("RANKING SYSTEM DEMONSTRATION")
    print("═" * 80)
    
    test_cases = [
        {"profit": 5000, "trades": 50, "wins": 35, "drawdown": 500},
        {"profit": 15000, "trades": 150, "wins": 110, "drawdown": 1000},
        {"profit": 50000, "trades": 500, "wins": 380, "drawdown": 2000},
    ]
    
    for i, case in enumerate(test_cases, 1):
        score = strategy.calculate_ranking_score(
            total_profit=case['profit'],
            starting_balance=10000,
            total_trades=case['trades'],
            winning_trades=case['wins'],
            max_drawdown=case['drawdown']
        )
        
        tier = strategy.get_tier_from_score(score)
        level = strategy.get_level_from_score(score)
        
        print(f"\nCase {i}:")
        print(f"  Profit: ${case['profit']:,} | Trades: {case['trades']} | Wins: {case['wins']}")
        print(f"  → Score: {score:.2f} | Tier: {tier.value} | Level: {level}")
    
    print("\n" + "═" * 80)
    print("END OF DEMONSTRATION")
    print("═" * 80)
