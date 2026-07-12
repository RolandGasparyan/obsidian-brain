"""
Trading Guru - DeepSeek R1 Agent
The Quant Architect: Complex Reasoning & Code Logic
"""

import re
from typing import Dict, Any
from .base_agent import BaseAgent
from ..core.config import AgentConfig


class DeepSeekAgent(BaseAgent):
    """
    DeepSeek R1 - The Quant Architect
    
    Strength: Complex Reasoning & Code Logic
    Role: The "Math Engine" - Calculates probability of market moves based on 
    mathematical structure and quantitative analysis.
    """
    
    def get_system_prompt(self) -> str:
        return """# MISSION: QUANTITATIVE EXECUTION (DEEPSEEK R1)

Act as a High-Frequency Quantitative Analyst. Your focus is exclusively on mathematical and logical price analysis. Ignore all narratives and sentiment. You are the "Math Engine" of a sophisticated trading system.

## CORE PRINCIPLES:
1. **Pure Logic:** Emotions and narratives are noise. Only price, volume, and mathematical relationships matter.
2. **Probability-Based:** Every trade is a probability game. Calculate the odds before recommending action.
3. **Precision:** Provide exact price levels, not ranges or approximations.

## ANALYSIS FRAMEWORK:

### 1. Market Structure Mapping
- Identify the current market structure (uptrend, downtrend, or range)
- Has there been a recent Break of Structure (BOS) to the downside?
- Map Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), Lower Lows (LL)

### 2. Liquidity Analysis
- Pinpoint key liquidity zones: swing highs/lows and equal highs/lows
- Identify where stop-losses are likely clustered
- Calculate the "liquidity magnet" effect

### 3. Inefficiency Scan
- Identify Fair Value Gaps (FVGs) that could act as magnets or resistance
- Locate Order Blocks (OBs) where institutional orders were placed
- Determine if price is likely to return to fill these inefficiencies

### 4. Volume Profile Analysis
- Identify High Volume Nodes (HVNs) - price rejection zones
- Identify Low Volume Nodes (LVNs) - price acceleration zones
- Point of Control (POC) analysis

### 5. Statistical Analysis
- Is price > 2 Standard Deviations from the 20-period VWAP?
- Mean reversion probability calculation
- Volatility regime assessment

## OUTPUT FORMAT (STRICT JSON):
You MUST respond with a JSON object containing:
{
    "signal": "short" | "long" | "neutral",
    "confidence": 0.0-1.0,
    "logic_chain": "Step-by-step reasoning",
    "market_structure": "bullish" | "bearish" | "ranging",
    "entry_price": <number>,
    "stop_loss": <number>,
    "target_1": <number>,
    "target_2": <number>,
    "key_findings": ["finding1", "finding2", ...],
    "invalidation_reason": "What would invalidate this setup"
}

Reply: "DEEPSEEK QUANT SYSTEM ONLINE." then await data."""
    
    def format_analysis_prompt(self, market_data: dict, **kwargs) -> str:
        from ..utils.market_utils import (
            identify_swing_points, 
            identify_fair_value_gaps,
            identify_order_blocks,
            determine_market_structure,
            calculate_standard_deviation_from_vwap,
            format_market_data_for_prompt
        )
        
        candles = market_data.get('candles', [])
        
        # Perform technical analysis
        swing_highs, swing_lows = identify_swing_points(candles) if candles else ([], [])
        fvgs = identify_fair_value_gaps(candles) if candles else []
        order_blocks = identify_order_blocks(candles) if candles else []
        market_structure = determine_market_structure(candles) if candles else "unknown"
        
        std_from_vwap = calculate_standard_deviation_from_vwap(
            market_data.get('current_price', 0),
            market_data.get('vwap', 0),
            candles
        ) if candles else 0
        
        # Format recent swing points
        recent_highs = swing_highs[-5:] if swing_highs else []
        recent_lows = swing_lows[-5:] if swing_lows else []
        
        prompt = f"""
DEEPSEEK QUANT SYSTEM ONLINE. Analyzing market data...

{format_market_data_for_prompt(market_data)}

## STRUCTURAL ANALYSIS (Pre-computed):

### Market Structure: {market_structure.upper()}

### Recent Swing Highs:
{chr(10).join([f"- ${sh['price']:,.2f}" for sh in recent_highs]) if recent_highs else "- No significant swing highs identified"}

### Recent Swing Lows:
{chr(10).join([f"- ${sl['price']:,.2f}" for sl in recent_lows]) if recent_lows else "- No significant swing lows identified"}

### Fair Value Gaps (FVGs):
{chr(10).join([f"- {fvg['type'].upper()} FVG: ${fvg['low']:,.2f} - ${fvg['high']:,.2f}" for fvg in fvgs[-5:]]) if fvgs else "- No significant FVGs identified"}

### Order Blocks:
{chr(10).join([f"- {ob['type'].upper()} OB: ${ob['low']:,.2f} - ${ob['high']:,.2f}" for ob in order_blocks[-5:]]) if order_blocks else "- No significant Order Blocks identified"}

### Statistical Position:
- **Standard Deviations from VWAP:** {std_from_vwap:.2f}
- **Mean Reversion Signal:** {"HIGH" if abs(std_from_vwap) > 2 else "MODERATE" if abs(std_from_vwap) > 1 else "LOW"}

## TASK:
Analyze this data using your quantitative framework. Provide your analysis in the specified JSON format.
Focus on identifying the highest probability SHORT setup if bearish conditions exist, or LONG setup if bullish conditions exist.
If no clear setup exists, signal "neutral".
"""
        return prompt
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the DeepSeek response into structured data."""
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
            result["reasoning"] = json_data.get("logic_chain", "")
            result["key_findings"] = json_data.get("key_findings", [])
            result["entry_price"] = json_data.get("entry_price")
            result["stop_loss"] = json_data.get("stop_loss")
            result["target_1"] = json_data.get("target_1")
            result["target_2"] = json_data.get("target_2")
            result["metadata"] = {
                "market_structure": json_data.get("market_structure"),
                "invalidation_reason": json_data.get("invalidation_reason")
            }
        else:
            # Fallback: Parse text response
            response_lower = response.lower()
            
            if "short" in response_lower and "signal" in response_lower:
                result["signal"] = "short"
                result["confidence"] = 0.6
            elif "long" in response_lower and "signal" in response_lower:
                result["signal"] = "long"
                result["confidence"] = 0.6
            
            result["reasoning"] = response[:500]
            
            # Try to extract prices
            result["entry_price"] = self._extract_price_from_text(response, "entry")
            result["stop_loss"] = self._extract_price_from_text(response, "stop")
            result["target_1"] = self._extract_price_from_text(response, "target")
        
        return result


def create_deepseek_agent(agent_config: AgentConfig = None) -> DeepSeekAgent:
    """Factory function to create a DeepSeek agent."""
    if agent_config is None:
        from ..core.config import DEFAULT_AGENTS
        agent_config = DEFAULT_AGENTS["deepseek"]
    
    return DeepSeekAgent(agent_config)
