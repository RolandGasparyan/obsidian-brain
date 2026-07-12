"""
Trading Guru - Llama 3.3 70B Agent
The High-Speed Scalper: Efficiency & Speed
"""

from typing import Dict, Any
from .base_agent import BaseAgent
from ..core.config import AgentConfig


class LlamaAgent(BaseAgent):
    """
    Llama 3.3 70B - The High-Speed Scalper
    
    Strength: Efficiency & Speed
    Role: The "Scalper" - Looks for quick, 5-15 minute timeframe setups 
    for rapid profit.
    """
    
    def get_system_prompt(self) -> str:
        return """# MISSION: 15-MINUTE CHART ANALYSIS (LLAMA)

You are a high-frequency scalping bot focused on the 15-minute timeframe. Your purpose is to identify the earliest signs of potential trend reversals and quick profit opportunities. We do not care about the long term. We care about the next 3-5 candles.

## CORE PHILOSOPHY:
1. **Speed Over Depth:** Quick analysis, quick execution, quick profits.
2. **Tight Risk Management:** Small stops, defined targets, no hoping.
3. **Structure is Everything:** Trade the structure, not the story.

## SCALPING FRAMEWORK:

### 1. Displacement Detection
- Find the most recent high-volume candle that broke structure
- Bullish Displacement: Large green candle breaking above resistance
- Bearish Displacement: Large red candle breaking below support
- Displacement creates Fair Value Gaps (FVGs) - these are our entry zones

### 2. Breaker Block Identification
- **Bearish Breaker:** Previous support that broke and now acts as resistance
  - Price breaks below support → Retests from below → SHORT ENTRY
- **Bullish Breaker:** Previous resistance that broke and now acts as support
  - Price breaks above resistance → Retests from above → LONG ENTRY

### 3. The Retest Setup
- Wait for price to retrace into the displacement zone (FVG or Breaker)
- Entry on the retest, not the initial move
- This gives better risk:reward and confirmation

### 4. Quick Profit Targets
- Target 1: Recent swing low/high (conservative)
- Target 2: Next liquidity zone (aggressive)
- Never hold through major support/resistance

## BEARISH SCALP SETUP:
1. **Displacement:** Big red candle breaks support
2. **FVG Created:** Gap between candle bodies
3. **Retest:** Price wicks back into FVG or Breaker Block
4. **Entry:** Short on rejection from FVG/Breaker
5. **Stop:** Above the wick high
6. **Target:** Recent swing low

## BULLISH SCALP SETUP:
1. **Displacement:** Big green candle breaks resistance
2. **FVG Created:** Gap between candle bodies
3. **Retest:** Price wicks back into FVG or Breaker Block
4. **Entry:** Long on bounce from FVG/Breaker
5. **Stop:** Below the wick low
6. **Target:** Recent swing high

## OUTPUT FORMAT (STRICT JSON):
{
    "signal": "short" | "long" | "wait",
    "confidence": 0.0-1.0,
    "setup_type": "displacement_retest" | "breaker_block" | "fvg_fill" | "none",
    "entry_price": <exact entry price>,
    "stop_loss": <tight stop above/below wick>,
    "target_1": <recent swing>,
    "target_2": <next liquidity zone>,
    "risk_reward": <calculated R:R ratio>,
    "timeframe": "15m",
    "candles_to_target": <estimated candles to reach target>,
    "reasoning": "Quick scalp analysis",
    "key_findings": ["finding1", "finding2", ...]
}

Reply: "LLAMA SCALPER READY." then await data."""
    
    def format_analysis_prompt(self, market_data: dict, **kwargs) -> str:
        from ..utils.market_utils import (
            identify_fair_value_gaps,
            identify_order_blocks,
            identify_swing_points,
            format_market_data_for_prompt
        )
        
        candles = market_data.get('candles', [])
        
        # Get recent candles for scalping analysis (last 20)
        recent_candles = candles[-20:] if len(candles) >= 20 else candles
        
        # Identify structures
        fvgs = identify_fair_value_gaps(recent_candles) if recent_candles else []
        order_blocks = identify_order_blocks(recent_candles) if recent_candles else []
        swing_highs, swing_lows = identify_swing_points(recent_candles, lookback=3) if recent_candles else ([], [])
        
        # Find displacement (large candles)
        displacements = []
        if len(recent_candles) >= 2:
            avg_body = sum(abs(c['close'] - c['open']) for c in recent_candles[:-1]) / (len(recent_candles) - 1)
            
            for i, candle in enumerate(recent_candles[-5:], start=len(recent_candles)-5):
                body = abs(candle['close'] - candle['open'])
                if body > avg_body * 2:  # Significant candle
                    direction = "BULLISH" if candle['close'] > candle['open'] else "BEARISH"
                    displacements.append({
                        "index": i,
                        "direction": direction,
                        "open": candle['open'],
                        "close": candle['close'],
                        "high": candle['high'],
                        "low": candle['low']
                    })
        
        # Current price position
        current_price = market_data.get('current_price', 0)
        
        # Find nearest levels
        nearest_swing_high = min([sh['price'] for sh in swing_highs if sh['price'] > current_price], default=None)
        nearest_swing_low = max([sl['price'] for sl in swing_lows if sl['price'] < current_price], default=None)
        
        prompt = f"""
LLAMA SCALPER READY. Analyzing 15-minute structure...

## CURRENT PRICE: ${current_price:,.2f}

### Recent Candle Data (Last 5):
{chr(10).join([f"- O: ${c['open']:,.2f} | H: ${c['high']:,.2f} | L: ${c['low']:,.2f} | C: ${c['close']:,.2f} | {'🟢' if c['close'] > c['open'] else '🔴'}" for c in recent_candles[-5:]]) if recent_candles else "No candle data"}

### Technical Indicators:
- RSI (14): {market_data.get('rsi', 'N/A')}
- VWAP: ${market_data.get('vwap', 0):,.2f}
- Price vs VWAP: {"ABOVE ⬆️" if current_price > market_data.get('vwap', 0) else "BELOW ⬇️"}

### Displacement Candles Detected:
{chr(10).join([f"- {d['direction']} displacement: ${d['low']:,.2f} - ${d['high']:,.2f}" for d in displacements]) if displacements else "- No significant displacement detected"}

### Fair Value Gaps (FVGs):
{chr(10).join([f"- {fvg['type'].upper()}: ${fvg['low']:,.2f} - ${fvg['high']:,.2f}" for fvg in fvgs[-3:]]) if fvgs else "- No FVGs detected"}

### Breaker Blocks / Order Blocks:
{chr(10).join([f"- {ob['type'].upper()}: ${ob['low']:,.2f} - ${ob['high']:,.2f}" for ob in order_blocks[-3:]]) if order_blocks else "- No Order Blocks detected"}

### Key Levels:
- Nearest Swing High: {f'${nearest_swing_high:,.2f}' if nearest_swing_high else 'N/A'}
- Nearest Swing Low: {f'${nearest_swing_low:,.2f}' if nearest_swing_low else 'N/A'}

## TASK:
As a High-Speed Scalper, analyze this 15-minute data to find:
1. Is there a valid scalping setup forming?
2. If yes, what type (displacement retest, breaker block, FVG fill)?
3. Provide exact entry, stop loss, and target levels
4. Calculate the risk:reward ratio
5. If no setup, signal "wait"

Provide your analysis in the specified JSON format. Be precise with levels!
"""
        return prompt
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the Llama response into structured data."""
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
            signal = json_data.get("signal", "neutral").lower()
            # Convert "wait" to "neutral"
            result["signal"] = "neutral" if signal == "wait" else signal
            result["confidence"] = float(json_data.get("confidence", 0.5))
            result["reasoning"] = json_data.get("reasoning", "")
            result["key_findings"] = json_data.get("key_findings", [])
            result["entry_price"] = json_data.get("entry_price")
            result["stop_loss"] = json_data.get("stop_loss")
            result["target_1"] = json_data.get("target_1")
            result["target_2"] = json_data.get("target_2")
            
            result["metadata"] = {
                "setup_type": json_data.get("setup_type"),
                "risk_reward": json_data.get("risk_reward"),
                "timeframe": json_data.get("timeframe", "15m"),
                "candles_to_target": json_data.get("candles_to_target")
            }
        else:
            # Fallback parsing
            response_lower = response.lower()
            
            if "short" in response_lower and ("entry" in response_lower or "setup" in response_lower):
                result["signal"] = "short"
                result["confidence"] = 0.6
            elif "long" in response_lower and ("entry" in response_lower or "setup" in response_lower):
                result["signal"] = "long"
                result["confidence"] = 0.6
            
            result["reasoning"] = response[:500]
            result["entry_price"] = self._extract_price_from_text(response, "entry")
            result["stop_loss"] = self._extract_price_from_text(response, "stop")
            result["target_1"] = self._extract_price_from_text(response, "target")
        
        return result


def create_llama_agent(agent_config: AgentConfig = None) -> LlamaAgent:
    """Factory function to create a Llama agent."""
    if agent_config is None:
        from ..core.config import DEFAULT_AGENTS
        agent_config = DEFAULT_AGENTS["llama"]
    
    return LlamaAgent(agent_config)
