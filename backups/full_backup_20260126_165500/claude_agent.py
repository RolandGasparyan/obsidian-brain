"""
Trading Guru - Claude Opus Agent
The Contrarian Psychologist: Nuance & Psychological Profiling
"""

from typing import Dict, Any
from .base_agent import BaseAgent
from ..core.config import AgentConfig


class ClaudeAgent(BaseAgent):
    """
    Claude Opus - The Contrarian Psychologist
    
    Strength: Nuance & Psychological Profiling
    Role: The "Psychologist" - Predicts when retail traders are excessively 
    greedy/fearful and about to be trapped.
    """
    
    def get_system_prompt(self) -> str:
        return """# MISSION: BEHAVIORAL & SENTIMENT ANALYSIS (CLAUDE)

Act as a Behavioral Finance Expert specializing in "Max Pain" theories and crowd psychology. Your mission is to identify moments of peak euphoria or panic that precede major market reversals.

## CORE PHILOSOPHY:
1. **Contrarian Edge:** The crowd is usually wrong at extremes. Peak euphoria = sell signal. Peak fear = buy signal.
2. **Liquidity Engineering:** Smart money needs retail liquidity to fill orders. They engineer emotions to create it.
3. **The Trap is the Trade:** Identify who is being trapped and position accordingly.

## PSYCHOLOGICAL PROFILING FRAMEWORK:

### 1. Sentiment Phase Identification
- **Disbelief:** Early trend, most are skeptical (opportunity phase)
- **Hope:** Trend gaining recognition, early adopters entering
- **Optimism:** Trend confirmed, mainstream entering
- **Euphoria:** "This time is different" - DANGER ZONE for longs
- **Anxiety:** First significant pullback, "buy the dip" mentality
- **Denial:** Trend breaking, but bulls refuse to accept
- **Panic:** Capitulation, forced selling - OPPORTUNITY for longs
- **Depression:** Bottom formation, no one cares anymore

### 2. Trap Identification
- **Bull Trap:** Price breaks above resistance with low volume, then reverses
  - Breakout traders get trapped long
  - Their stop losses become fuel for the dump
- **Bear Trap:** Price breaks below support, then reverses sharply
  - Breakdown traders get trapped short
  - Their stop losses become fuel for the pump
- **Inducement:** False moves designed to lure traders into wrong positions

### 3. Max Pain Analysis
- Where would price need to go to cause maximum financial pain?
- Where are the largest clusters of stop losses?
- What price action would liquidate the most leveraged positions?

### 4. Sentiment Indicators
- Fear & Greed Index interpretation
- Social media sentiment analysis
- Influencer positioning (are they hedging their public stance?)

## OUTPUT FORMAT (STRICT JSON):
{
    "signal": "short" | "long" | "neutral",
    "confidence": 0.0-1.0,
    "sentiment_phase": "disbelief" | "hope" | "optimism" | "euphoria" | "anxiety" | "denial" | "panic" | "depression",
    "retail_sentiment": "euphoric" | "greedy" | "neutral" | "fearful" | "capitulating",
    "trap_identified": "bull_trap" | "bear_trap" | "inducement" | "none",
    "trap_description": "Who is being trapped and how",
    "max_pain_level": <price where max pain occurs>,
    "execution_trigger": "Specific condition to enter the trade",
    "reasoning": "Psychological analysis",
    "key_findings": ["finding1", "finding2", ...]
}

Reply: "CLAUDE PSYCH OPS ONLINE." then await data."""
    
    def format_analysis_prompt(self, market_data: dict, **kwargs) -> str:
        from ..utils.market_utils import format_market_data_for_prompt
        
        sentiment_data = kwargs.get('sentiment_data', {})
        
        # Analyze sentiment phase
        fear_greed = sentiment_data.get('fear_greed_index', 50) if sentiment_data else 50
        rsi = market_data.get('rsi', 50)
        price_change = market_data.get('price_change_24h', 0)
        funding_rate = market_data.get('funding_rate', 0)
        
        # Determine sentiment phase
        if fear_greed > 80 and price_change > 5:
            sentiment_phase = "EUPHORIA - Extreme greed, potential top"
        elif fear_greed > 65 and price_change > 2:
            sentiment_phase = "OPTIMISM - Bullish but watch for exhaustion"
        elif fear_greed > 50:
            sentiment_phase = "HOPE - Trend developing"
        elif fear_greed > 35:
            sentiment_phase = "ANXIETY - Uncertainty, potential reversal zone"
        elif fear_greed > 20:
            sentiment_phase = "DENIAL/PANIC - Fear increasing"
        else:
            sentiment_phase = "DEPRESSION/CAPITULATION - Extreme fear, potential bottom"
        
        # Trap analysis
        trap_analysis = "NO CLEAR TRAP IDENTIFIED"
        if price_change > 3 and funding_rate > 0.01:
            trap_analysis = "POTENTIAL BULL TRAP - Breakout with overleveraged longs"
        elif price_change < -3 and funding_rate < -0.01:
            trap_analysis = "POTENTIAL BEAR TRAP - Breakdown with overleveraged shorts"
        elif abs(price_change) < 1 and abs(funding_rate) > 0.005:
            trap_analysis = "INDUCEMENT ZONE - Price consolidating while leverage builds"
        
        prompt = f"""
CLAUDE PSYCH OPS ONLINE. Analyzing market psychology...

{format_market_data_for_prompt(market_data, sentiment_data=sentiment_data)}

## PSYCHOLOGICAL ANALYSIS (Pre-computed):

### Current Sentiment Phase: {sentiment_phase}
- Fear & Greed Index: {fear_greed}
- RSI: {rsi}
- 24h Price Change: {price_change:+.2f}%

### Trap Analysis: {trap_analysis}
- Funding Rate: {funding_rate:.4%}
- Long/Short Ratio: {market_data.get('long_short_ratio', 'N/A')}

### Social Sentiment:
{f"- Twitter Sentiment Score: {sentiment_data.get('twitter_sentiment', 'N/A')}" if sentiment_data else "- No social data available"}
{f"- Trending Keywords: {', '.join(sentiment_data.get('trending_keywords', []))}" if sentiment_data else ""}
{f"- Bullish Influencers: {sentiment_data.get('bullish_influencers', 0)} | Bearish: {sentiment_data.get('bearish_influencers', 0)}" if sentiment_data else ""}

### Leverage Analysis:
- Open Interest: ${market_data.get('open_interest', 0):,.2f}
- Funding Rate Signal: {"LONGS PAYING" if funding_rate > 0 else "SHORTS PAYING" if funding_rate < 0 else "NEUTRAL"}

## TASK:
As a Behavioral Finance Expert, analyze this data to determine:
1. What is the current psychological phase of the market?
2. Is there a trap being set? Who is about to get trapped?
3. Where is the "Max Pain" level - the price that would cause maximum liquidations?
4. What is the contrarian trade here?

Provide your analysis in the specified JSON format.
"""
        return prompt
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the Claude response into structured data."""
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
            result["entry_price"] = json_data.get("max_pain_level")
            
            result["metadata"] = {
                "sentiment_phase": json_data.get("sentiment_phase"),
                "retail_sentiment": json_data.get("retail_sentiment"),
                "trap_identified": json_data.get("trap_identified"),
                "trap_description": json_data.get("trap_description"),
                "execution_trigger": json_data.get("execution_trigger")
            }
        else:
            # Fallback parsing
            response_lower = response.lower()
            
            # Check for euphoria/greed signals (bearish)
            if any(x in response_lower for x in ["euphoria", "extreme greed", "bull trap"]):
                result["signal"] = "short"
                result["confidence"] = 0.65
            # Check for panic/fear signals (bullish)
            elif any(x in response_lower for x in ["capitulation", "extreme fear", "bear trap"]):
                result["signal"] = "long"
                result["confidence"] = 0.65
            
            result["reasoning"] = response[:500]
            result["entry_price"] = self._extract_price_from_text(response, "max pain")
        
        return result


def create_claude_agent(agent_config: AgentConfig = None) -> ClaudeAgent:
    """Factory function to create a Claude agent."""
    if agent_config is None:
        from ..core.config import DEFAULT_AGENTS
        agent_config = DEFAULT_AGENTS["claude"]
    
    return ClaudeAgent(agent_config)
