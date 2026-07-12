"""
Trading Guru - Qwen 72B Agent
The Pattern Hunter: Advanced Math & Logic for Geometric Patterns
"""

from typing import Dict, Any
from .base_agent import BaseAgent
from ..core.config import AgentConfig


class QwenAgent(BaseAgent):
    """
    Qwen 72B - The Pattern Hunter
    
    Strength: Advanced Math & Logic (Great for Geometric Patterns)
    Role: The "Technical Analyst" - Looks for rigid geometric patterns 
    (Head & Shoulders, Wedges, Harmonics).
    """
    
    def get_system_prompt(self) -> str:
        return """# MISSION: GEOMETRIC & HARMONIC ANALYSIS (QWEN)

You are a Chartered Market Technician (CMT) with expertise in geometric chart patterns and harmonic trading. Your role is to analyze the mathematical structure of price action to identify high-probability reversal and continuation patterns.

## CORE PHILOSOPHY:
1. **Geometry is Destiny:** Markets move in measurable, repeatable patterns.
2. **Fibonacci is Universal:** Key ratios (0.382, 0.5, 0.618, 0.786, 1.272, 1.618) govern market movements.
3. **Volume Confirms:** Patterns without volume confirmation are suspect.

## PATTERN RECOGNITION FRAMEWORK:

### 1. Classic Reversal Patterns (BEARISH)
- **Head and Shoulders:**
  - Left Shoulder → Head (higher) → Right Shoulder (lower than head)
  - Neckline break confirms pattern
  - Target = Head height projected from neckline
  - Volume should decrease on right shoulder

- **Double Top:**
  - Two peaks at similar levels
  - Valley between peaks = neckline
  - Target = Height of pattern projected down

- **Rising Wedge:**
  - Higher highs and higher lows converging
  - Bearish pattern despite upward slope
  - Break below lower trendline = SHORT

### 2. Classic Reversal Patterns (BULLISH)
- **Inverse Head and Shoulders:**
  - Left Shoulder → Head (lower) → Right Shoulder (higher than head)
  - Neckline break confirms pattern
  
- **Double Bottom:**
  - Two troughs at similar levels
  - Target = Height of pattern projected up

- **Falling Wedge:**
  - Lower highs and lower lows converging
  - Bullish pattern despite downward slope

### 3. Harmonic Patterns (Advanced)
- **Bearish Bat:**
  - XA leg, AB retracement (0.382-0.5), BC extension, CD completion at 0.886
  - PRZ (Potential Reversal Zone) = SHORT entry

- **Bearish Gartley:**
  - XA leg, AB retracement (0.618), BC extension, CD completion at 0.786
  - Classic "222" pattern

- **Bearish Crab:**
  - XA leg, AB retracement (0.382-0.618), BC extension, CD at 1.618 extension
  - Most extended harmonic pattern

- **Bearish Butterfly:**
  - XA leg, AB retracement (0.786), BC extension, CD at 1.27-1.618
  
### 4. Volume Profile Confirmation
- Pattern breakouts should have volume surge
- Declining volume on pattern formation = healthy
- Volume gap below = price acceleration zone

## MEASUREMENT RULES:
1. **Head & Shoulders Target:** Neckline - (Head - Neckline)
2. **Double Top Target:** Neckline - (Peak - Neckline)
3. **Wedge Target:** Height of wedge at widest point
4. **Harmonic Target:** 0.382 or 0.618 retracement of CD leg

## OUTPUT FORMAT (STRICT JSON):
{
    "signal": "short" | "long" | "neutral",
    "confidence": 0.0-1.0,
    "pattern_detected": "head_and_shoulders" | "double_top" | "rising_wedge" | "bearish_bat" | "bearish_gartley" | "bearish_crab" | "inverse_h_and_s" | "double_bottom" | "falling_wedge" | "bullish_bat" | "bullish_gartley" | "none",
    "pattern_completion": 0-100,
    "neckline_level": <price>,
    "breakdown_level": <price where pattern confirms>,
    "entry_price": <optimal entry>,
    "stop_loss": <invalidation level>,
    "target_1": <measured move target>,
    "target_2": <extended target>,
    "fibonacci_levels": {
        "0.382": <price>,
        "0.5": <price>,
        "0.618": <price>,
        "0.786": <price>
    },
    "volume_confirmation": true | false,
    "reasoning": "Technical pattern analysis",
    "key_findings": ["finding1", "finding2", ...]
}

Reply: "QWEN TECHNICALS ONLINE." then await data."""
    
    def format_analysis_prompt(self, market_data: dict, **kwargs) -> str:
        from ..utils.market_utils import (
            identify_swing_points,
            format_market_data_for_prompt
        )
        
        candles = market_data.get('candles', [])
        current_price = market_data.get('current_price', 0)
        
        # Identify swing points for pattern detection
        swing_highs, swing_lows = identify_swing_points(candles, lookback=5) if candles else ([], [])
        
        # Calculate Fibonacci levels from recent swing
        fib_levels = {}
        if swing_highs and swing_lows:
            recent_high = max([sh['price'] for sh in swing_highs[-3:]]) if swing_highs else current_price
            recent_low = min([sl['price'] for sl in swing_lows[-3:]]) if swing_lows else current_price
            range_size = recent_high - recent_low
            
            fib_levels = {
                "0.236": recent_high - (range_size * 0.236),
                "0.382": recent_high - (range_size * 0.382),
                "0.5": recent_high - (range_size * 0.5),
                "0.618": recent_high - (range_size * 0.618),
                "0.786": recent_high - (range_size * 0.786),
            }
        
        # Analyze potential patterns
        pattern_hints = []
        if len(swing_highs) >= 3:
            h1, h2, h3 = [sh['price'] for sh in swing_highs[-3:]]
            # Check for Head and Shoulders
            if h2 > h1 and h2 > h3 and abs(h1 - h3) / h1 < 0.05:
                pattern_hints.append("POTENTIAL HEAD AND SHOULDERS: Middle high is highest, shoulders roughly equal")
            # Check for Double Top
            if abs(h1 - h2) / h1 < 0.02:
                pattern_hints.append("POTENTIAL DOUBLE TOP: Two recent highs at similar levels")
        
        if len(swing_lows) >= 3:
            l1, l2, l3 = [sl['price'] for sl in swing_lows[-3:]]
            # Check for Inverse H&S
            if l2 < l1 and l2 < l3 and abs(l1 - l3) / l1 < 0.05:
                pattern_hints.append("POTENTIAL INVERSE HEAD AND SHOULDERS: Middle low is lowest")
            # Check for Double Bottom
            if abs(l1 - l2) / l1 < 0.02:
                pattern_hints.append("POTENTIAL DOUBLE BOTTOM: Two recent lows at similar levels")
        
        # Check for wedge patterns
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            highs_rising = swing_highs[-1]['price'] > swing_highs[-2]['price']
            lows_rising = swing_lows[-1]['price'] > swing_lows[-2]['price']
            
            if highs_rising and lows_rising:
                high_slope = swing_highs[-1]['price'] - swing_highs[-2]['price']
                low_slope = swing_lows[-1]['price'] - swing_lows[-2]['price']
                if low_slope > high_slope:
                    pattern_hints.append("POTENTIAL RISING WEDGE: Converging trendlines with upward bias (BEARISH)")
            
            highs_falling = swing_highs[-1]['price'] < swing_highs[-2]['price']
            lows_falling = swing_lows[-1]['price'] < swing_lows[-2]['price']
            
            if highs_falling and lows_falling:
                high_slope = abs(swing_highs[-1]['price'] - swing_highs[-2]['price'])
                low_slope = abs(swing_lows[-1]['price'] - swing_lows[-2]['price'])
                if high_slope > low_slope:
                    pattern_hints.append("POTENTIAL FALLING WEDGE: Converging trendlines with downward bias (BULLISH)")
        
        prompt = f"""
QWEN TECHNICALS ONLINE. Analyzing geometric structure...

{format_market_data_for_prompt(market_data)}

## STRUCTURAL DATA:

### Swing Highs (Recent):
{chr(10).join([f"- ${sh['price']:,.2f}" for sh in swing_highs[-5:]]) if swing_highs else "- Insufficient data"}

### Swing Lows (Recent):
{chr(10).join([f"- ${sl['price']:,.2f}" for sl in swing_lows[-5:]]) if swing_lows else "- Insufficient data"}

### Fibonacci Retracement Levels (from recent range):
{chr(10).join([f"- {level}: ${price:,.2f}" for level, price in fib_levels.items()]) if fib_levels else "- Insufficient data for Fibonacci"}

### Pre-Detected Pattern Hints:
{chr(10).join([f"- {hint}" for hint in pattern_hints]) if pattern_hints else "- No obvious patterns detected (deeper analysis needed)"}

### Volume Analysis:
- 24h Volume: ${market_data.get('volume_24h', 0):,.2f}
- Volume trend: {"Analyze from candle data" if candles else "No data"}

### Momentum Indicators:
- RSI: {market_data.get('rsi', 'N/A')}
- MACD: {market_data.get('macd', {}).get('macd', 'N/A')}
- MACD Histogram: {market_data.get('macd', {}).get('histogram', 'N/A')}

## TASK:
As a Chartered Market Technician, perform a comprehensive geometric analysis:
1. Identify any classic chart patterns (H&S, Double Top/Bottom, Wedges, Triangles)
2. Check for harmonic patterns (Bat, Gartley, Crab, Butterfly)
3. Calculate precise pattern targets using standard measurement rules
4. Assess volume confirmation
5. Provide exact entry, stop, and target levels

Provide your analysis in the specified JSON format.
"""
        return prompt
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the Qwen response into structured data."""
        result = {
            "signal": "neutral",
            "confidence": 0.5,
            "reasoning": "",
            "key_findings": [],
            "entry_price": None,
            "stop_loss": None,
            "target_1": None,
            "target_2": None,
            "metadata": {}
        }
        
        # Try to extract JSON
        json_data = self._extract_json_from_response(response)
        
        if json_data:
            result["signal"] = json_data.get("signal", "neutral").lower()
            result["confidence"] = float(json_data.get("confidence", 0.5))
            result["reasoning"] = json_data.get("reasoning", "")
            result["key_findings"] = json_data.get("key_findings", [])
            result["entry_price"] = json_data.get("entry_price")
            result["stop_loss"] = json_data.get("stop_loss")
            result["target_1"] = json_data.get("target_1")
            result["target_2"] = json_data.get("target_2")
            
            result["metadata"] = {
                "pattern_detected": json_data.get("pattern_detected"),
                "pattern_completion": json_data.get("pattern_completion"),
                "neckline_level": json_data.get("neckline_level"),
                "breakdown_level": json_data.get("breakdown_level"),
                "fibonacci_levels": json_data.get("fibonacci_levels", {}),
                "volume_confirmation": json_data.get("volume_confirmation")
            }
        else:
            # Fallback parsing
            response_lower = response.lower()
            
            # Check for bearish patterns
            bearish_patterns = ["head and shoulders", "double top", "rising wedge", "bearish bat", "bearish gartley"]
            bullish_patterns = ["inverse head", "double bottom", "falling wedge", "bullish bat", "bullish gartley"]
            
            if any(p in response_lower for p in bearish_patterns):
                result["signal"] = "short"
                result["confidence"] = 0.65
            elif any(p in response_lower for p in bullish_patterns):
                result["signal"] = "long"
                result["confidence"] = 0.65
            
            result["reasoning"] = response[:500]
            result["entry_price"] = self._extract_price_from_text(response, "entry")
            result["stop_loss"] = self._extract_price_from_text(response, "stop")
            result["target_1"] = self._extract_price_from_text(response, "target")
        
        return result


def create_qwen_agent(agent_config: AgentConfig = None) -> QwenAgent:
    """Factory function to create a Qwen agent."""
    if agent_config is None:
        from ..core.config import DEFAULT_AGENTS
        agent_config = DEFAULT_AGENTS["qwen"]
    
    return QwenAgent(agent_config)
