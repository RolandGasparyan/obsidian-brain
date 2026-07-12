"""
Trading Guru Market Utilities
Functions for fetching market data and performing technical analysis.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import random

# Note: In production, these would use actual exchange APIs
# For demonstration, we'll create mock data generators


def calculate_vwap(candles: List[dict]) -> float:
    """Calculate Volume Weighted Average Price."""
    if not candles:
        return 0.0
    
    cumulative_tp_vol = 0.0
    cumulative_vol = 0.0
    
    for candle in candles:
        typical_price = (candle['high'] + candle['low'] + candle['close']) / 3
        cumulative_tp_vol += typical_price * candle['volume']
        cumulative_vol += candle['volume']
    
    return cumulative_tp_vol / cumulative_vol if cumulative_vol > 0 else 0.0


def calculate_rsi(closes: List[float], period: int = 14) -> float:
    """Calculate Relative Strength Index."""
    if len(closes) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


def calculate_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
    """Calculate MACD indicator."""
    if len(closes) < slow:
        return {"macd": 0, "signal": 0, "histogram": 0}
    
    def ema(data: List[float], period: int) -> float:
        if len(data) < period:
            return sum(data) / len(data)
        multiplier = 2 / (period + 1)
        ema_val = sum(data[:period]) / period
        for price in data[period:]:
            ema_val = (price - ema_val) * multiplier + ema_val
        return ema_val
    
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = ema_fast - ema_slow
    
    # Simplified signal line calculation
    signal_line = macd_line * 0.9  # Approximation
    histogram = macd_line - signal_line
    
    return {
        "macd": round(macd_line, 4),
        "signal": round(signal_line, 4),
        "histogram": round(histogram, 4)
    }


def calculate_bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, float]:
    """Calculate Bollinger Bands."""
    if len(closes) < period:
        return {"upper": 0, "middle": 0, "lower": 0}
    
    recent_closes = closes[-period:]
    middle = sum(recent_closes) / period
    
    variance = sum((x - middle) ** 2 for x in recent_closes) / period
    std = variance ** 0.5
    
    return {
        "upper": round(middle + (std_dev * std), 2),
        "middle": round(middle, 2),
        "lower": round(middle - (std_dev * std), 2)
    }


def identify_swing_points(candles: List[dict], lookback: int = 5) -> Tuple[List[dict], List[dict]]:
    """Identify swing highs and swing lows."""
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, len(candles) - lookback):
        # Check for swing high
        is_swing_high = all(
            candles[i]['high'] > candles[j]['high']
            for j in range(i - lookback, i + lookback + 1)
            if j != i
        )
        
        # Check for swing low
        is_swing_low = all(
            candles[i]['low'] < candles[j]['low']
            for j in range(i - lookback, i + lookback + 1)
            if j != i
        )
        
        if is_swing_high:
            swing_highs.append({
                "price": candles[i]['high'],
                "timestamp": candles[i]['timestamp'],
                "index": i
            })
        
        if is_swing_low:
            swing_lows.append({
                "price": candles[i]['low'],
                "timestamp": candles[i]['timestamp'],
                "index": i
            })
    
    return swing_highs, swing_lows


def identify_fair_value_gaps(candles: List[dict]) -> List[dict]:
    """Identify Fair Value Gaps (FVGs)."""
    fvgs = []
    
    for i in range(2, len(candles)):
        prev_candle = candles[i-2]
        curr_candle = candles[i]
        
        # Bullish FVG: Gap between candle 1 high and candle 3 low
        if curr_candle['low'] > prev_candle['high']:
            fvgs.append({
                "type": "bullish",
                "high": curr_candle['low'],
                "low": prev_candle['high'],
                "timestamp": candles[i-1]['timestamp'],
                "filled": False
            })
        
        # Bearish FVG: Gap between candle 1 low and candle 3 high
        if curr_candle['high'] < prev_candle['low']:
            fvgs.append({
                "type": "bearish",
                "high": prev_candle['low'],
                "low": curr_candle['high'],
                "timestamp": candles[i-1]['timestamp'],
                "filled": False
            })
    
    return fvgs


def identify_order_blocks(candles: List[dict]) -> List[dict]:
    """Identify Order Blocks."""
    order_blocks = []
    
    for i in range(1, len(candles) - 1):
        curr = candles[i]
        next_candle = candles[i + 1]
        
        # Bullish Order Block: Last bearish candle before a strong bullish move
        if curr['close'] < curr['open']:  # Bearish candle
            if next_candle['close'] > next_candle['open']:  # Followed by bullish
                body_size = abs(next_candle['close'] - next_candle['open'])
                avg_body = sum(abs(c['close'] - c['open']) for c in candles[max(0, i-10):i]) / min(10, i) if i > 0 else body_size
                
                if body_size > avg_body * 1.5:  # Strong move
                    order_blocks.append({
                        "type": "bullish",
                        "high": curr['high'],
                        "low": curr['low'],
                        "timestamp": curr['timestamp'],
                        "mitigated": False
                    })
        
        # Bearish Order Block: Last bullish candle before a strong bearish move
        if curr['close'] > curr['open']:  # Bullish candle
            if next_candle['close'] < next_candle['open']:  # Followed by bearish
                body_size = abs(next_candle['close'] - next_candle['open'])
                avg_body = sum(abs(c['close'] - c['open']) for c in candles[max(0, i-10):i]) / min(10, i) if i > 0 else body_size
                
                if body_size > avg_body * 1.5:  # Strong move
                    order_blocks.append({
                        "type": "bearish",
                        "high": curr['high'],
                        "low": curr['low'],
                        "timestamp": curr['timestamp'],
                        "mitigated": False
                    })
    
    return order_blocks


def determine_market_structure(candles: List[dict]) -> str:
    """Determine current market structure."""
    if len(candles) < 20:
        return "unknown"
    
    swing_highs, swing_lows = identify_swing_points(candles)
    
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "ranging"
    
    # Check for higher highs and higher lows (bullish)
    recent_highs = swing_highs[-3:]
    recent_lows = swing_lows[-3:]
    
    if len(recent_highs) >= 2 and len(recent_lows) >= 2:
        hh = recent_highs[-1]['price'] > recent_highs[-2]['price']
        hl = recent_lows[-1]['price'] > recent_lows[-2]['price']
        
        if hh and hl:
            return "bullish"
        
        lh = recent_highs[-1]['price'] < recent_highs[-2]['price']
        ll = recent_lows[-1]['price'] < recent_lows[-2]['price']
        
        if lh and ll:
            return "bearish"
    
    return "ranging"


def calculate_standard_deviation_from_vwap(current_price: float, vwap: float, candles: List[dict]) -> float:
    """Calculate how many standard deviations price is from VWAP."""
    if not candles or vwap == 0:
        return 0.0
    
    closes = [c['close'] for c in candles[-20:]]
    mean = sum(closes) / len(closes)
    variance = sum((x - mean) ** 2 for x in closes) / len(closes)
    std = variance ** 0.5
    
    if std == 0:
        return 0.0
    
    return (current_price - vwap) / std


def generate_mock_market_data(symbol: str = "BTC/USDT", timeframe: str = "1h", num_candles: int = 100) -> dict:
    """Generate mock market data for testing."""
    base_price = 95000 if "BTC" in symbol else 3500 if "ETH" in symbol else 150
    
    candles = []
    current_price = base_price
    
    for i in range(num_candles):
        change_pct = random.uniform(-0.02, 0.02)
        open_price = current_price
        close_price = current_price * (1 + change_pct)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
        volume = random.uniform(1000, 10000) * base_price / 1000
        
        candles.append({
            "timestamp": (datetime.now() - timedelta(hours=num_candles - i)).isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": round(volume, 2)
        })
        
        current_price = close_price
    
    closes = [c['close'] for c in candles]
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": candles,
        "current_price": round(current_price, 2),
        "bid": round(current_price * 0.9999, 2),
        "ask": round(current_price * 1.0001, 2),
        "volume_24h": round(sum(c['volume'] for c in candles[-24:]), 2),
        "price_change_24h": round((candles[-1]['close'] / candles[-24]['close'] - 1) * 100, 2),
        "vwap": round(calculate_vwap(candles[-24:]), 2),
        "rsi": calculate_rsi(closes),
        "macd": calculate_macd(closes),
        "bollinger_bands": calculate_bollinger_bands(closes),
        "funding_rate": round(random.uniform(-0.01, 0.03), 4),
        "open_interest": round(random.uniform(1000000, 5000000), 2),
        "long_short_ratio": round(random.uniform(0.8, 1.5), 2)
    }


def generate_mock_onchain_data(symbol: str = "BTC") -> dict:
    """Generate mock on-chain data for testing."""
    return {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "exchange_inflow": round(random.uniform(1000, 5000), 2),
        "exchange_outflow": round(random.uniform(1000, 5000), 2),
        "net_flow": round(random.uniform(-2000, 2000), 2),
        "whale_transactions": random.randint(50, 200),
        "large_tx_volume": round(random.uniform(10000, 100000), 2),
        "sopr": round(random.uniform(0.95, 1.05), 4),
        "nupl": round(random.uniform(-0.2, 0.6), 4),
        "active_addresses": random.randint(500000, 1000000),
        "transaction_count": random.randint(200000, 400000)
    }


def generate_mock_sentiment_data(symbol: str = "BTC") -> dict:
    """Generate mock sentiment data for testing."""
    fear_greed = random.randint(20, 85)
    
    if fear_greed < 25:
        label = "extreme_fear"
    elif fear_greed < 45:
        label = "fear"
    elif fear_greed < 55:
        label = "neutral"
    elif fear_greed < 75:
        label = "greed"
    else:
        label = "extreme_greed"
    
    return {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "fear_greed_index": fear_greed,
        "fear_greed_label": label,
        "twitter_sentiment": round(random.uniform(-0.5, 0.8), 2),
        "twitter_volume": random.randint(10000, 100000),
        "trending_keywords": random.sample(
            ["moon", "pump", "dump", "bullish", "bearish", "hodl", "buy", "sell", "dip", "ath"],
            k=3
        ),
        "bullish_influencers": random.randint(5, 20),
        "bearish_influencers": random.randint(2, 15)
    }


def format_market_data_for_prompt(market_data: dict, onchain_data: dict = None, sentiment_data: dict = None) -> str:
    """Format market data into a string for LLM prompts."""
    output = f"""
## MARKET DATA: {market_data['symbol']}

### Price Action
- **Current Price:** ${market_data['current_price']:,.2f}
- **24h Change:** {market_data['price_change_24h']:+.2f}%
- **24h Volume:** ${market_data['volume_24h']:,.2f}
- **Bid/Ask:** ${market_data['bid']:,.2f} / ${market_data['ask']:,.2f}

### Technical Indicators
- **VWAP:** ${market_data['vwap']:,.2f}
- **RSI (14):** {market_data['rsi']}
- **MACD:** {market_data['macd']['macd']:.4f} (Signal: {market_data['macd']['signal']:.4f})
- **Bollinger Bands:** Upper: ${market_data['bollinger_bands']['upper']:,.2f} | Middle: ${market_data['bollinger_bands']['middle']:,.2f} | Lower: ${market_data['bollinger_bands']['lower']:,.2f}

### Derivatives Data
- **Funding Rate:** {market_data['funding_rate']:.4%}
- **Open Interest:** ${market_data['open_interest']:,.2f}
- **Long/Short Ratio:** {market_data['long_short_ratio']:.2f}
"""
    
    if onchain_data:
        output += f"""
### On-Chain Metrics
- **Exchange Net Flow:** {onchain_data['net_flow']:+,.2f} {onchain_data['symbol']}
- **Whale Transactions (24h):** {onchain_data['whale_transactions']}
- **SOPR:** {onchain_data['sopr']:.4f}
- **NUPL:** {onchain_data['nupl']:.4f}
- **Active Addresses:** {onchain_data['active_addresses']:,}
"""
    
    if sentiment_data:
        output += f"""
### Sentiment Data
- **Fear & Greed Index:** {sentiment_data['fear_greed_index']} ({sentiment_data['fear_greed_label']})
- **Twitter Sentiment:** {sentiment_data['twitter_sentiment']:+.2f}
- **Twitter Volume:** {sentiment_data['twitter_volume']:,} mentions
- **Trending Keywords:** {', '.join(sentiment_data['trending_keywords'])}
- **Bullish Influencers:** {sentiment_data['bullish_influencers']} | **Bearish:** {sentiment_data['bearish_influencers']}
"""
    
    return output
