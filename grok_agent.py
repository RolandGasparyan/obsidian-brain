"""
Trading Guru - Grok xAI Agent
The Real-Time News Sniper: Real-Time Access to Social Data
"""

from typing import Dict, Any
from .base_agent import BaseAgent
from ..core.config import AgentConfig


class GrokAgent(BaseAgent):
    """
    Grok xAI - The Real-Time News Sniper
    
    Strength: Real-Time Access to X (Twitter) Data
    Role: The "News Arbitrageur" - Detects when a pump is fake news or 
    when the crowd turns bearish instantly.
    """
    
    def get_system_prompt(self) -> str:
        return """# MISSION: REAL-TIME SENTIMENT ARBITRAGE (GROK)

You are a real-time sentiment algorithm with a direct feed from social media and news sources. Your job is to detect immediate shifts in market narrative and sentiment that precede price movements.

## CORE PHILOSOPHY:
1. **News Moves Markets:** But only temporarily. Identify when the news effect is exhausted.
2. **Sentiment Velocity:** It's not just what people are saying, but how fast sentiment is changing.
3. **Narrative Exhaustion:** When everyone is bullish and price stops going up, the narrative is exhausted.

## REAL-TIME ANALYSIS FRAMEWORK:

### 1. "Sell the News" Detection
- Major bullish event occurs but price fails to break resistance = DISTRIBUTION
- Price pumps on news but immediately rejects = SMART MONEY SELLING INTO NEWS
- Positive news + Negative price action = BEARISH DIVERGENCE

### 2. FUD Velocity Tracking
- Monitor velocity of bearish keywords: "scam," "rug," "dump," "crash"
- Sudden spike in negative sentiment while price holds = EARLY WARNING
- FUD spreading while price rises = POTENTIAL TOP

### 3. Influencer Divergence
- Are major influencers becoming quiet after pumping?
- Are they hedging their public bullish stance?
- Influencer silence after hype = DISTRIBUTION PHASE

### 4. Bot Activity Detection
- Are bots spamming bullish posts while price stagnates?
- Artificial sentiment inflation = MANIPULATION
- Real organic sentiment vs manufactured sentiment

### 5. Narrative Exhaustion Signals
- Same bullish talking points recycled without new catalysts
- Decreasing engagement on bullish posts
- "Why isn't it pumping?" sentiment emerging

## TRIGGER CONDITIONS FOR SHORTS:
1. **"Sell the News":** Major event + price rejection = SHORT
2. **Viral Fear:** FUD trending + price at resistance = SHORT
3. **Fake Pump:** Bot activity + stagnant price = SHORT
4. **Influencer Exit:** Silence from previously vocal bulls = SHORT

## OUTPUT FORMAT (STRICT JSON):
{
    "signal": "short" | "long" | "hold",
    "confidence": 0.0-1.0,
    "sentiment_velocity": "accelerating_bullish" | "decelerating_bullish" | "neutral" | "accelerating_bearish" | "decelerating_bearish",
    "narrative_status": "fresh" | "mature" | "exhausted" | "reversing",
    "fud_trigger_level": <price where panic selling begins>,
    "fomo_trigger_level": <price where FOMO buying begins>,
    "news_impact": "positive" | "negative" | "neutral" | "fading",
    "bot_activity": "low" | "moderate" | "high" | "extreme",
    "reasoning": "Real-time sentiment analysis",
    "key_findings": ["finding1", "finding2", ...],
    "trending_narratives": ["narrative1", "narrative2", ...],
    "alert_level": "green" | "yellow" | "orange" | "red"
}

Reply: "GROK REAL-TIME FEED ACTIVE." then await data."""
    
    def format_analysis_prompt(self, market_data: dict, **kwargs) -> str:
        from ..utils.market_utils import format_market_data_for_prompt
        
        sentiment_data = kwargs.get('sentiment_data', {})
        news_data = kwargs.get('news_data', [])
        
        # Analyze sentiment velocity
        twitter_sentiment = sentiment_data.get('twitter_sentiment', 0) if sentiment_data else 0
        twitter_volume = sentiment_data.get('twitter_volume', 0) if sentiment_data else 0
        trending_keywords = sentiment_data.get('trending_keywords', []) if sentiment_data else []
        
        # Determine sentiment velocity
        if twitter_sentiment > 0.5 and twitter_volume > 50000:
            sentiment_velocity = "ACCELERATING BULLISH - High positive sentiment with high volume"
        elif twitter_sentiment > 0.3:
            sentiment_velocity = "MODERATELY BULLISH"
        elif twitter_sentiment < -0.3 and twitter_volume > 50000:
            sentiment_velocity = "ACCELERATING BEARISH - Negative sentiment spreading fast"
        elif twitter_sentiment < -0.1:
            sentiment_velocity = "MODERATELY BEARISH"
        else:
            sentiment_velocity = "NEUTRAL - No strong directional sentiment"
        
        # Check for narrative exhaustion
        price_change = market_data.get('price_change_24h', 0)
        if twitter_sentiment > 0.3 and price_change < 0:
            narrative_status = "DIVERGENCE - Bullish sentiment but bearish price action"
        elif twitter_sentiment < -0.3 and price_change > 0:
            narrative_status = "DIVERGENCE - Bearish sentiment but bullish price action"
        elif twitter_sentiment > 0.5 and price_change < 2:
            narrative_status = "POTENTIAL EXHAUSTION - High bullish sentiment, weak price response"
        else:
            narrative_status = "ALIGNED - Sentiment matches price action"
        
        # Check for FUD keywords
        fud_keywords = ["scam", "rug", "dump", "crash", "sell"]
        bullish_keywords = ["moon", "pump", "buy", "hodl", "bullish"]
        
        fud_count = sum(1 for kw in trending_keywords if any(f in kw.lower() for f in fud_keywords))
        bull_count = sum(1 for kw in trending_keywords if any(b in kw.lower() for b in bullish_keywords))
        
        prompt = f"""
GROK REAL-TIME FEED ACTIVE. Scanning sentiment streams...

{format_market_data_for_prompt(market_data, sentiment_data=sentiment_data)}

## REAL-TIME SENTIMENT ANALYSIS:

### Sentiment Velocity: {sentiment_velocity}
- Twitter Sentiment Score: {twitter_sentiment:+.2f}
- Twitter Volume: {twitter_volume:,} mentions
- 24h Price Change: {price_change:+.2f}%

### Narrative Status: {narrative_status}

### Keyword Analysis:
- Trending Keywords: {', '.join(trending_keywords) if trending_keywords else 'None detected'}
- FUD Keywords Detected: {fud_count}
- Bullish Keywords Detected: {bull_count}
- Sentiment Ratio: {"BULLISH DOMINATED" if bull_count > fud_count else "FUD DOMINATED" if fud_count > bull_count else "BALANCED"}

### Influencer Activity:
{f"- Bullish Influencers Active: {sentiment_data.get('bullish_influencers', 0)}" if sentiment_data else "- No influencer data"}
{f"- Bearish Influencers Active: {sentiment_data.get('bearish_influencers', 0)}" if sentiment_data else ""}

### Recent News Impact:
{chr(10).join([f"- {news}" for news in news_data[:5]]) if news_data else "- No significant news detected"}

## TASK:
As a Real-Time Sentiment Analyst, determine:
1. Is the current sentiment sustainable or showing signs of exhaustion?
2. Are there any "Sell the News" or "Buy the Rumor" setups?
3. What is the FUD trigger level - where will panic selling begin?
4. What is the FOMO trigger level - where will FOMO buying begin?
5. Is this a HOLD or SHORT/LONG opportunity based on sentiment?

Provide your analysis in the specified JSON format.
"""
        return prompt
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the Grok response into structured data."""
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
            # Convert "hold" to "neutral" for consistency
            result["signal"] = "neutral" if signal == "hold" else signal
            result["confidence"] = float(json_data.get("confidence", 0.5))
            result["reasoning"] = json_data.get("reasoning", "")
            result["key_findings"] = json_data.get("key_findings", [])
            result["entry_price"] = json_data.get("fud_trigger_level") if result["signal"] == "short" else json_data.get("fomo_trigger_level")
            
            result["metadata"] = {
                "sentiment_velocity": json_data.get("sentiment_velocity"),
                "narrative_status": json_data.get("narrative_status"),
                "fud_trigger_level": json_data.get("fud_trigger_level"),
                "fomo_trigger_level": json_data.get("fomo_trigger_level"),
                "news_impact": json_data.get("news_impact"),
                "bot_activity": json_data.get("bot_activity"),
                "trending_narratives": json_data.get("trending_narratives", []),
                "alert_level": json_data.get("alert_level")
            }
        else:
            # Fallback parsing
            response_lower = response.lower()
            
            if any(x in response_lower for x in ["sell the news", "narrative exhaustion", "fud spreading"]):
                result["signal"] = "short"
                result["confidence"] = 0.6
            elif any(x in response_lower for x in ["fomo", "bullish momentum", "positive catalyst"]):
                result["signal"] = "long"
                result["confidence"] = 0.6
            
            result["reasoning"] = response[:500]
            result["entry_price"] = self._extract_price_from_text(response, "trigger")
        
        return result


def create_grok_agent(agent_config: AgentConfig = None) -> GrokAgent:
    """Factory function to create a Grok agent."""
    if agent_config is None:
        from ..core.config import DEFAULT_AGENTS
        agent_config = DEFAULT_AGENTS["grok"]
    
    return GrokAgent(agent_config)
