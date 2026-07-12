from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class MarketData:
    symbol: str
    price: float
    volume_24h: float
    volatility_atr: float
    adx_14: float
    spread_percent: float
    funding_rate: float
    timestamp: str

@dataclass
class TradeSignal:
    symbol: str
    direction: str
    strategy: str
    confidence: float
    entry_zone: List[float]
    stop_loss: float
    targets: List[float]
    reasoning: str
    entry_size_usd: float

@dataclass
class PairScore:
    symbol: str
    total_score: int
    scores: Dict[str, int]
    recommended_strategy: str
    signal: Optional[TradeSignal] = None

@dataclass
class OrchestratorState:
    timestamp: str
    active_pairs: List[str]
    pair_scores: List[PairScore]
    active_trades: List[Any]
    daily_pnl: float
    risk_level: str
