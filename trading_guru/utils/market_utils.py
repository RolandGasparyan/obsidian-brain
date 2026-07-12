import random
import time
from typing import List
from trading_guru.core.models import MarketData

def get_mock_market_data(symbol: str) -> MarketData:
    """Generates mock market data for a given symbol, favoring short setups."""
    
    if symbol in ["BTC/USDT", "ETH/USDT", "SOL/USDT"]:
        price = round(random.uniform(20000, 70000) if symbol == "BTC/USDT" else random.uniform(1000, 4000), 2)
        volatility_atr = round(price * random.uniform(0.03, 0.06), 2)
        volume_24h = random.uniform(2e9, 6e9)
        adx_14 = random.uniform(40, 60)
        spread_percent = random.uniform(0.001, 0.005)
        funding_rate = random.uniform(0.10, 0.30)
    else:
        price = round(random.uniform(1, 100), 4)
        volatility_atr = round(price * random.uniform(0.005, 0.015), 4)
        volume_24h = random.uniform(1e6, 1e8)
        adx_14 = random.uniform(15, 30)
        spread_percent = random.uniform(0.02, 0.05)
        funding_rate = random.uniform(-0.005, 0.05)

    return MarketData(
        symbol=symbol,
        price=price,
        volume_24h=volume_24h,
        volatility_atr=volatility_atr,
        adx_14=adx_14,
        spread_percent=spread_percent,
        funding_rate=funding_rate,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
    )

def get_all_mock_pairs() -> List[str]:
    """Returns a list of mock trading pairs."""
    return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "SHIB/USDT"]

def calculate_pair_score(data: MarketData) -> int:
    """Calculates a score, heavily favoring short conditions."""
    score = 0
    
    atr_percent = (data.volatility_atr / data.price) * 100
    if atr_percent > 5: score += 25
    elif atr_percent > 3: score += 20
    else: score += 10
    
    if data.volume_24h > 2e9: score += 25
    elif data.volume_24h > 1e9: score += 20
    else: score += 10
    
    if data.adx_14 > 50: score += 25
    elif data.adx_14 > 40: score += 20
    else: score += 10
    
    if data.spread_percent < 0.005: score += 25
    elif data.spread_percent < 0.01: score += 20
    else: score += 10
    
    if data.funding_rate > 0.20: score += 30
    elif data.funding_rate > 0.10: score += 20
    
    return score

def get_recommended_strategy(score: int, data: MarketData) -> str:
    """Determines the best strategy based on score and market data."""
    if data.adx_14 > 50 and data.funding_rate > 0.15:
        return "waterfall"
    elif data.spread_percent < 0.005:
        return "scalping"
    elif data.funding_rate > 0.20:
        return "snowball"
    else:
        return "doubling"
