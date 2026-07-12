"""
Trading Guru - GPT-5 Agent
The Macro Strategist: Multimodal Understanding & Synthesis
"""

from typing import Dict, Any
from .base_agent import BaseAgent
from ..core.config import AgentConfig


class GPT5Agent(BaseAgent):
    """
    GPT-5 - The Macro Strategist
    
    Strength: Multimodal Understanding & Synthesis
    Role: The "Fund Manager" - Looks at the big picture combining news, 
    structure, on-chain data, and trend analysis.
    """
    
    def get_system_prompt(self) -> str:
        return """# MISSION: MACRO & ON-CHAIN ANALYSIS (GPT-5)

You are a Global Macro Hedge Fund Manager with expertise in cryptocurrency markets. Your task is to assess the broader market environment and determine if conditions support a directional trade thesis.

## CORE PHILOSOPHY:
1. **Big Picture First:** Individual candles are noise. Focus on the macro trend and structural shifts.
2. **Follow the Money:** On-chain data reveals what smart money is actually doing, not what they're saying.
3. **Narrative vs Reality:** Identify when the bullish/bearish narrative no longer matches price action.

## ANALYSIS FRAMEWORK:

### 1. On-Chain Intelligence
- **Exchange Flows:** Net inflow = potential selling pressure; Net outflow = accumulation
- **Whale Activity:** Are large wallets distributing or accumulating?
- **SOPR Analysis:** 
  - SOPR > 1: Holders selling at profit (potential top)
  - SOPR < 1: Holders selling at loss (potential capitulation)
  - SOPR rolling over from >1: Trend exhaustion signal
- **NUPL (Net Unrealized Profit/Loss):** Extreme values indicate market turning points

### 2. Derivatives Market Analysis
- **Funding Rates:**
  - Excessively positive (>0.01%): Overleveraged longs, squeeze potential
  - Excessively negative (<-0.01%): Overleveraged shorts, squeeze potential
- **Open Interest:**
  - Rising OI + Rising Price = Trend confirmation
  - Rising OI + Flat Price = Potential volatility incoming
  - Falling OI = Position unwinding
- **Long/Short Ratio:** Extreme readings indicate crowded trades

### 3. Narrative & Catalyst Analysis
- Is the recent move driven by sustainable fundamentals or fading hype?
- Are there upcoming catalysts (ETF decisions, halvings, regulatory news)?
- Is there divergence between price and narrative strength?

### 4. Structural Collapse Detection (THE "GOD" SETUP)
- **The Divergence:** Higher highs in Price but lower highs in Momentum (RSI/MACD)
- **The Catalyst:** News-driven pump that is fading
- **The Trap:** Where are retail traders "stuck" (buying breakouts of double tops, etc.)

## OUTPUT FORMAT (STRICT JSON):
{
    "signal": "short" | "long" | "neutral",
    "confidence": 0.0-1.0,
    "dump_probability": 0-100,
    "squeeze_probability": 0-100,
    "macro_bias": "bullish" | "bearish" | "neutral",
    "kill_zone": <price level for optimal entry>,
    "reasoning": "Detailed macro analysis",
    "key_findings": ["finding1", "finding2", ...],
    "on_chain_summary": "Summary of on-chain signals",
    "derivatives_summary": "Summary of derivatives signals",
    "risk_events": ["upcoming risk event 1", ...]
}

Reply: "GPT-5 MACRO DESK READY." then await data."""
    
    def format_analysis_prompt(self, market_data: dict, **kwargs) -> str:
        from ..utils.market_utils import format_market_data_for_prompt
        
        onchain_data = kwargs.get('onchain_data', {})
        sentiment_data = kwargs.get('sentiment_data', {})
        
        # Analyze derivatives signals
        funding_rate = market_data.get('funding_rate', 0)
        open_interest = market_data.get('open_interest', 0)
        long_short_ratio = market_data.get('long_short_ratio', 1)
        
        funding_signal = "NEUTRAL"
        if funding_rate > 0.01:
            funding_signal = "OVERLEVERAGED LONGS - Short squeeze risk LOW, Long squeeze risk HIGH"
        elif funding_rate < -0.01:
            funding_signal = "OVERLEVERAGED SHORTS - Short squeeze risk HIGH, Long squeeze risk LOW"
        elif funding_rate > 0.005:
            funding_signal = "MODERATELY BULLISH BIAS"
        elif funding_rate < -0.005:
            funding_signal = "MODERATELY BEARISH BIAS"
        
        # Analyze on-chain signals
        onchain_signal = "NEUTRAL"
        if onchain_data:
            net_flow = onchain_data.get('net_flow', 0)
            sopr = onchain_data.get('sopr', 1)
            
            if net_flow > 1000 and sopr > 1:
                onchain_signal = "DISTRIBUTION - Smart money potentially selling"
            elif net_flow < -1000 and sopr < 1:
                onchain_signal = "ACCUMULATION - Smart money potentially buying"
            elif net_flow > 500:
                onchain_signal = "MILD SELLING PRESSURE"
            elif net_flow < -500:
                onchain_signal = "MILD BUYING PRESSURE"
        
        prompt = f"""
GPT-5 MACRO DESK READY. Analyzing macro environment...

{format_market_data_for_prompt(market_data, onchain_data, sentiment_data)}

## PRE-ANALYZED SIGNALS:

### Derivatives Signal: {funding_signal}
- Funding Rate: {funding_rate:.4%}
- Open Interest: ${open_interest:,.2f}
- Long/Short Ratio: {long_short_ratio:.2f}

### On-Chain Signal: {onchain_signal}
{f"- Net Exchange Flow: {onchain_data.get('net_flow', 'N/A'):+,.2f}" if onchain_data else "- No on-chain data available"}
{f"- SOPR: {onchain_data.get('sopr', 'N/A')}" if onchain_data else ""}
{f"- Whale Transactions: {onchain_data.get('whale_transactions', 'N/A')}" if onchain_data else ""}

### Technical Divergence Check:
- RSI: {market_data.get('rsi', 'N/A')}
- MACD Histogram: {market_data.get('macd', {}).get('histogram', 'N/A')}
- Price vs VWAP: {"ABOVE" if market_data.get('current_price', 0) > market_data.get('vwap', 0) else "BELOW"}

## TASK:
As a Global Macro Hedge Fund Manager, synthesize all this data to determine:
1. Is the macro environment supportive of a SHORT or LONG position?
2. What is the probability of a significant dump or squeeze?
3. Where is the optimal "Kill Zone" for entry?
4. What are the key risk events to monitor?

Provide your analysis in the specified JSON format.
"""
        return prompt
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the GPT-5 response into structured data."""
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
            result["entry_price"] = json_data.get("kill_zone")
            
            result["metadata"] = {
                "dump_probability": json_data.get("dump_probability"),
                "squeeze_probability": json_data.get("squeeze_probability"),
                "macro_bias": json_data.get("macro_bias"),
                "on_chain_summary": json_data.get("on_chain_summary"),
                "derivatives_summary": json_data.get("derivatives_summary"),
                "risk_events": json_data.get("risk_events", [])
            }
        else:
            # Fallback parsing
            response_lower = response.lower()
            
            if "dump probability" in response_lower:
                if any(x in response_lower for x in ["high dump", "dump probability: 7", "dump probability: 8", "dump probability: 9"]):
                    result["signal"] = "short"
                    result["confidence"] = 0.7
            
            if "short" in response_lower and ("recommend" in response_lower or "signal" in response_lower):
                result["signal"] = "short"
                result["confidence"] = 0.6
            elif "long" in response_lower and ("recommend" in response_lower or "signal" in response_lower):
                result["signal"] = "long"
                result["confidence"] = 0.6
            
            result["reasoning"] = response[:500]
            result["entry_price"] = self._extract_price_from_text(response, "kill zone")
        
        return result


def create_gpt5_agent(agent_config: AgentConfig = None) -> GPT5Agent:
    """Factory function to create a GPT-5 agent."""
    if agent_config is None:
        from ..core.config import DEFAULT_AGENTS
        agent_config = DEFAULT_AGENTS["gpt5"]
    
    return GPT5Agent(agent_config)
