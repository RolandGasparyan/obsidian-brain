"""
Trading Guru Configuration Module
Centralized configuration for all trading parameters and API settings.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class TradingMode(Enum):
    """Trading mode enumeration."""
    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"


class SignalType(Enum):
    """Signal type enumeration."""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class Timeframe(Enum):
    """Supported timeframes."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


@dataclass
class APIConfig:
    """API Configuration for different services."""
    # OpenAI Compatible API (for all LLM agents)
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    
    # Exchange APIs (for market data and trading)
    exchange_api_key: str = field(default_factory=lambda: os.getenv("EXCHANGE_API_KEY", ""))
    exchange_api_secret: str = field(default_factory=lambda: os.getenv("EXCHANGE_API_SECRET", ""))
    exchange_name: str = "binance"
    
    # On-Chain Data APIs
    glassnode_api_key: str = field(default_factory=lambda: os.getenv("GLASSNODE_API_KEY", ""))
    cryptoquant_api_key: str = field(default_factory=lambda: os.getenv("CRYPTOQUANT_API_KEY", ""))
    
    # Social Sentiment APIs
    twitter_bearer_token: str = field(default_factory=lambda: os.getenv("TWITTER_BEARER_TOKEN", ""))


@dataclass
class AgentConfig:
    """Configuration for individual AI agents."""
    name: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    role: str = ""
    enabled: bool = True


@dataclass
class TradingConfig:
    """Trading parameters configuration."""
    mode: TradingMode = TradingMode.PAPER
    default_symbol: str = "BTC/USDT"
    watchlist: List[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    
    # Risk Management
    max_position_size_pct: float = 5.0  # Max 5% of portfolio per trade
    max_drawdown_pct: float = 10.0  # Max 10% drawdown before stopping
    risk_reward_ratio: float = 3.0  # Minimum 1:3 risk-reward
    
    # Consensus Requirements
    min_consensus_agents: int = 4  # Minimum agents agreeing for trade execution
    confluence_threshold: float = 0.7  # 70% confidence threshold
    
    # Timeframes
    primary_timeframe: Timeframe = Timeframe.H1
    scalping_timeframe: Timeframe = Timeframe.M15
    macro_timeframe: Timeframe = Timeframe.D1


# Default Agent Configurations
DEFAULT_AGENTS: Dict[str, AgentConfig] = {
    "deepseek": AgentConfig(
        name="DeepSeek R1",
        model="gpt-4.1-mini",  # Can be replaced with actual DeepSeek model
        temperature=0.3,
        max_tokens=2500,
        role="Quant Architect"
    ),
    "gpt5": AgentConfig(
        name="GPT-5",
        model="gpt-4.1-mini",
        temperature=0.5,
        max_tokens=2500,
        role="Macro Strategist"
    ),
    "claude": AgentConfig(
        name="Claude Opus",
        model="gpt-4.1-mini",  # Can be replaced with Claude API
        temperature=0.6,
        max_tokens=2500,
        role="Contrarian Psychologist"
    ),
    "grok": AgentConfig(
        name="Grok xAI",
        model="gpt-4.1-mini",  # Can be replaced with Grok API
        temperature=0.7,
        max_tokens=2000,
        role="Real-Time News Sniper"
    ),
    "llama": AgentConfig(
        name="Llama 3.3 70B",
        model="gpt-4.1-mini",  # Can be replaced with Llama API
        temperature=0.4,
        max_tokens=1500,
        role="High-Speed Scalper"
    ),
    "qwen": AgentConfig(
        name="Qwen 72B",
        model="gpt-4.1-mini",  # Can be replaced with Qwen API
        temperature=0.4,
        max_tokens=2000,
        role="Pattern Hunter"
    ),
}


class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.api = APIConfig()
        self.trading = TradingConfig()
        self.agents = DEFAULT_AGENTS.copy()
    
    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """Get configuration for a specific agent."""
        return self.agents.get(agent_name)
    
    def update_agent_model(self, agent_name: str, model: str):
        """Update the model for a specific agent."""
        if agent_name in self.agents:
            self.agents[agent_name].model = model
    
    def set_trading_mode(self, mode: TradingMode):
        """Set the trading mode."""
        self.trading.mode = mode
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "api": {
                "exchange": self.api.exchange_name,
                "openai_configured": bool(self.api.openai_api_key),
            },
            "trading": {
                "mode": self.trading.mode.value,
                "symbol": self.trading.default_symbol,
                "watchlist": self.trading.watchlist,
                "risk_reward_ratio": self.trading.risk_reward_ratio,
            },
            "agents": {
                name: {"name": cfg.name, "model": cfg.model, "enabled": cfg.enabled}
                for name, cfg in self.agents.items()
            }
        }


# Global configuration instance
config = Config()
