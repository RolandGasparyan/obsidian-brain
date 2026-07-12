"""
8 AI GODS Configuration
Each AI has unique personality, strategy preferences, and risk profile
"""

AI_GODS = {
    "DeepSeek_R1": {
        "name": "DeepSeek R1 - Quant God",
        "aggression": 10,
        "strategy": "scalping",
        "leverage": 15,
        "profit_target": 1.5,
        "stop_loss": 0.5,
        "description": "Ultra-fast quant trading, mathematical precision"
    },
    "GPT_5": {
        "name": "GPT-5 - Macro God",
        "aggression": 9,
        "strategy": "momentum",
        "leverage": 12,
        "profit_target": 8.0,
        "stop_loss": 2.5,
        "description": "Macro analysis, trend following"
    },
    "Claude_Opus": {
        "name": "Claude Opus - Contrarian God",
        "aggression": 8,
        "strategy": "mean_reversion",
        "leverage": 10,
        "profit_target": 5.0,
        "stop_loss": 2.0,
        "description": "Contrarian plays, mean reversion"
    },
    "Llama_33": {
        "name": "Llama 3.3 - Speed God",
        "aggression": 10,
        "strategy": "scalping",
        "leverage": 10,
        "profit_target": 0.8,
        "stop_loss": 0.3,
        "description": "High-frequency scalping"
    },
    "Gemini_Flash": {
        "name": "Gemini Flash - Multi-Modal God",
        "aggression": 9,
        "strategy": "momentum",
        "leverage": 11,
        "profit_target": 7.0,
        "stop_loss": 2.0,
        "description": "Multi-factor momentum"
    },
    "Mistral_Large": {
        "name": "Mistral Large - Risk God",
        "aggression": 8,
        "strategy": "mean_reversion",
        "leverage": 10,
        "profit_target": 5.5,
        "stop_loss": 2.0,
        "description": "Risk-adjusted mean reversion"
    },
    "Qwen_72B": {
        "name": "Qwen 72B - Pattern God",
        "aggression": 9,
        "strategy": "breakout",
        "leverage": 12,
        "profit_target": 12.0,
        "stop_loss": 3.0,
        "description": "Pattern recognition, breakouts"
    },
    "Grok_xAI": {
        "name": "Grok xAI - News God",
        "aggression": 10,
        "strategy": "news",
        "leverage": 13,
        "profit_target": 10.0,
        "stop_loss": 3.0,
        "description": "News sentiment trading"
    }
}

TRADING_PAIRS = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]

MARKET_CONDITIONS = {
    "TRENDING_UP": {"momentum": 60, "scalping": 20, "breakout": 20},
    "TRENDING_DOWN": {"momentum": 60, "scalping": 20, "breakout": 20},
    "RANGING": {"mean_reversion": 40, "scalping": 30, "grid": 30},
    "VOLATILE": {"scalping": 50, "momentum": 20, "mean_reversion": 20, "breakout": 10},
    "BREAKOUT": {"momentum": 50, "breakout": 40, "scalping": 10},
    "REVERSAL": {"mean_reversion": 60, "scalping": 20, "grid": 20}
}

RISK_CONFIG = {
    "max_daily_loss_pct": 10,
    "max_total_loss_pct": 30,
    "protected_balance_pct": 70,
    "consecutive_loss_limit": 4,
    "pause_duration_minutes": 60
}
