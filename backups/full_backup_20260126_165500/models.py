"""
Trading Guru Data Models
Pydantic models for market data, signals, and trade analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class MarketStructure(Enum):
    """Market structure types."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"
    UNKNOWN = "unknown"


class SentimentLevel(Enum):
    """Market sentiment levels."""
    EXTREME_FEAR = "extreme_fear"
    FEAR = "fear"
    NEUTRAL = "neutral"
    GREED = "greed"
    EXTREME_GREED = "extreme_greed"
    EUPHORIC = "euphoric"


class PatternType(Enum):
    """Chart pattern types."""
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    INVERSE_HEAD_AND_SHOULDERS = "inverse_head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    BEARISH_BAT = "bearish_bat"
    BULLISH_BAT = "bullish_bat"
    BEARISH_GARTLEY = "bearish_gartley"
    BULLISH_GARTLEY = "bullish_gartley"
    BEARISH_CRAB = "bearish_crab"
    BULLISH_CRAB = "bullish_crab"
    NONE = "none"


@dataclass
class OHLCV:
    """OHLCV candle data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open
    
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


@dataclass
class MarketData:
    """Comprehensive market data structure."""
    symbol: str
    timeframe: str
    candles: List[OHLCV]
    current_price: float
    bid: float
    ask: float
    volume_24h: float
    price_change_24h: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Technical Indicators
    vwap: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[Dict[str, float]] = None
    bollinger_bands: Optional[Dict[str, float]] = None
    
    # Derivatives Data
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    long_short_ratio: Optional[float] = None


@dataclass
class OnChainData:
    """On-chain metrics data."""
    symbol: str
    timestamp: datetime
    
    # Exchange Flows
    exchange_inflow: Optional[float] = None
    exchange_outflow: Optional[float] = None
    net_flow: Optional[float] = None
    
    # Whale Activity
    whale_transactions: Optional[int] = None
    large_tx_volume: Optional[float] = None
    
    # Profitability Metrics
    sopr: Optional[float] = None  # Spent Output Profit Ratio
    nupl: Optional[float] = None  # Net Unrealized Profit/Loss
    
    # Network Activity
    active_addresses: Optional[int] = None
    transaction_count: Optional[int] = None


@dataclass
class SentimentData:
    """Social sentiment data."""
    symbol: str
    timestamp: datetime
    
    # Fear & Greed
    fear_greed_index: Optional[int] = None
    fear_greed_label: Optional[SentimentLevel] = None
    
    # Social Metrics
    twitter_sentiment: Optional[float] = None  # -1 to 1
    twitter_volume: Optional[int] = None
    trending_keywords: List[str] = field(default_factory=list)
    
    # Influencer Activity
    bullish_influencers: int = 0
    bearish_influencers: int = 0


@dataclass
class LiquidityZone:
    """Liquidity zone identification."""
    price_level: float
    zone_type: str  # "swing_high", "swing_low", "equal_highs", "equal_lows"
    strength: float  # 0-1 strength rating
    touched_count: int = 0
    last_touched: Optional[datetime] = None


@dataclass
class FairValueGap:
    """Fair Value Gap (FVG) identification."""
    high: float
    low: float
    direction: str  # "bullish" or "bearish"
    timestamp: datetime
    filled: bool = False
    fill_percentage: float = 0.0


@dataclass
class OrderBlock:
    """Order Block identification."""
    high: float
    low: float
    direction: str  # "bullish" or "bearish"
    timestamp: datetime
    mitigated: bool = False
    strength: float = 1.0


@dataclass
class AgentAnalysis:
    """Analysis output from an individual agent."""
    agent_name: str
    agent_role: str
    timestamp: datetime
    
    # Signal
    signal: str  # "short", "long", "neutral"
    confidence: float  # 0-1
    
    # Analysis Details
    reasoning: str
    key_findings: List[str]
    
    # Trade Levels (optional, depending on agent)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    
    # Agent-Specific Data
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    """Consensus result from all agents."""
    timestamp: datetime
    symbol: str
    
    # Consensus Metrics
    total_agents: int
    agreeing_agents: int
    consensus_signal: str  # "short", "long", "neutral"
    confluence_score: float  # 0-1
    
    # Individual Analyses
    agent_analyses: List[AgentAnalysis]
    
    # Aggregated Trade Levels
    entry_zone_high: Optional[float] = None
    entry_zone_low: Optional[float] = None
    invalidation_level: Optional[float] = None
    primary_target: Optional[float] = None
    secondary_target: Optional[float] = None
    
    # Risk Metrics
    risk_reward_ratio: Optional[float] = None
    position_size_recommendation: Optional[float] = None
    
    @property
    def is_actionable(self) -> bool:
        """Check if the consensus is actionable."""
        return self.agreeing_agents >= 4 and self.confluence_score >= 0.7
    
    @property
    def consensus_percentage(self) -> float:
        """Get consensus percentage."""
        return (self.agreeing_agents / self.total_agents) * 100 if self.total_agents > 0 else 0


@dataclass
class TradeSignal:
    """Final trade signal for execution."""
    signal_id: str
    timestamp: datetime
    symbol: str
    
    # Trade Direction
    direction: str  # "short" or "long"
    
    # Entry
    entry_price: float
    entry_zone_high: float
    entry_zone_low: float
    
    # Risk Management
    stop_loss: float
    take_profit_1: float
    
    # Position Sizing
    position_size_pct: float
    
    # Metadata
    confluence_score: float
    consensus_agents: int
    reasoning: str
    
    # Optional fields with defaults
    take_profit_2: Optional[float] = None
    leverage: int = 1
    
    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk-reward ratio."""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit_1 - self.entry_price)
        return reward / risk if risk > 0 else 0


@dataclass
class TradeExecution:
    """Trade execution record."""
    trade_id: str
    signal_id: str
    timestamp: datetime
    symbol: str
    
    # Execution Details
    direction: str
    entry_price: float
    quantity: float
    leverage: int
    
    # Status
    status: str  # "open", "closed", "cancelled"
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    
    # P&L
    realized_pnl: Optional[float] = None
    realized_pnl_pct: Optional[float] = None
    
    # Notes
    notes: str = ""
