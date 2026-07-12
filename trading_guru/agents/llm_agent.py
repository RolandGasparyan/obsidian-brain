import os
import json
from typing import Dict, Optional
from openai import OpenAI
from trading_guru.core.config import config
from trading_guru.core.models import MarketData, TradeSignal

client = OpenAI(
    api_key=os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL")
)


class LLMAgent:
    """GODS MODE AI Agent - Professional Crypto Trading Analysis"""
    
    def __init__(self, name: str, role: str, specialty: str, system_prompt: str, 
                 weight: float = 1.0, preferred_strategy: str = "scalping"):
        self.name = name
        self.role = role
        self.specialty = specialty
        self.system_prompt = system_prompt
        self.weight = weight
        self.preferred_strategy = preferred_strategy

    def analyze(self, market_data: MarketData, strategy_context: str) -> Dict:
        """GODS MODE: Real OpenAI API analysis for SHORT opportunities."""
        
        if config.MOCK_DATA:
            return self._mock_analyze(market_data)
        
        enhanced_prompt = self._build_gods_mode_prompt(market_data, strategy_context)
        
        try:
            print(f"[{self.name}] Calling OpenAI API for {market_data.symbol}...")
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": enhanced_prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=800,
                temperature=0.5
            )
            
            result = json.loads(response.choices[0].message.content)
            
            score = result.get("score", 50)
            weighted_score = int(score * self.weight)
            
            print(f"[{self.name}] Analysis complete: Score={score}, Direction={result.get('direction', 'hold')}")
            
            signal = TradeSignal(
                symbol=market_data.symbol,
                direction=result.get("direction", "hold"),
                strategy=result.get("strategy", self.preferred_strategy),
                confidence=result.get("confidence", 0.5),
                entry_zone=result.get("entry_zone", [market_data.price * 1.001, market_data.price * 0.999]),
                stop_loss=result.get("stop_loss", market_data.price * 1.005),
                targets=result.get("targets", [market_data.price * 0.995, market_data.price * 0.990, market_data.price * 0.985]),
                reasoning=result.get("reasoning", f"{self.name} GODS MODE analysis"),
                entry_size_usd=config.MIN_ENTRY_SIZE_USD
            )
            
            return {
                "agent": self.name,
                "role": self.role,
                "specialty": self.specialty,
                "score": score,
                "weighted_score": weighted_score,
                "weight": self.weight,
                "signal": signal,
                "raw_response": result
            }
            
        except Exception as e:
            print(f"[{self.name}] API Error: {e}")
            return self._mock_analyze(market_data)

    def _calculate_profit_signals(self, market_data: MarketData) -> str:
        """GODS MODE profit opportunity analysis"""
        signals = []
        profit_score = 0
        
        if market_data.funding_rate > 0.01:
            signals.append(f"EXTREME FUNDING +{market_data.funding_rate:.4f}% = LONGS OVERLEVERAGED - HIGH SHORT PROFIT")
            profit_score += 35
        elif market_data.funding_rate > 0.005:
            signals.append(f"HIGH FUNDING +{market_data.funding_rate:.4f}% = Long bias detected - SHORT opportunity")
            profit_score += 25
        elif market_data.funding_rate > 0:
            signals.append(f"POSITIVE FUNDING +{market_data.funding_rate:.4f}% = Slight long sentiment")
            profit_score += 15
        else:
            signals.append(f"NEGATIVE FUNDING {market_data.funding_rate:.4f}% = Shorts paying - CAUTION")
            profit_score -= 15
        
        if market_data.adx_14 >= 45:
            signals.append(f"HYPER TREND ADX={market_data.adx_14:.0f} = PYRAMID AGGRESSIVE MODE")
            profit_score += 30
        elif market_data.adx_14 >= 35:
            signals.append(f"STRONG TREND ADX={market_data.adx_14:.0f} = WATERFALL MASTER SHORT")
            profit_score += 25
        elif market_data.adx_14 >= 25:
            signals.append(f"TRENDING ADX={market_data.adx_14:.0f} = WATERFALL opportunity")
            profit_score += 20
        elif market_data.adx_14 < 18:
            signals.append(f"RANGING ADX={market_data.adx_14:.0f} = SCALPING micro-profits")
            profit_score += 10
        
        volatility_pct = (market_data.volatility_atr / market_data.price) * 100 if market_data.price > 0 else 0
        if volatility_pct > 6:
            signals.append(f"EXTREME VOLATILITY {volatility_pct:.1f}% = MASSIVE profit potential")
            profit_score += 25
        elif volatility_pct > 4:
            signals.append(f"HIGH VOLATILITY {volatility_pct:.1f}% = Large moves expected")
            profit_score += 20
        elif volatility_pct > 2:
            signals.append(f"GOOD VOLATILITY {volatility_pct:.1f}% = Decent trading range")
            profit_score += 10
        
        if market_data.volume_24h > 5e9:
            signals.append("MASSIVE INSTITUTIONAL VOLUME = Perfect liquidity for large positions")
            profit_score += 20
        elif market_data.volume_24h > 1e9:
            signals.append("VERY HIGH VOLUME = Excellent entry/exit conditions")
            profit_score += 15
        elif market_data.volume_24h > 100e6:
            signals.append("GOOD LIQUIDITY = Smooth trade execution expected")
            profit_score += 10
        
        final_score = min(100, max(0, profit_score))
        signals.append(f"\nGODS MODE PROFIT SCORE: {final_score}/100")
        
        return "\n".join(signals)

    def _build_gods_mode_prompt(self, market_data: MarketData, strategy_context: str) -> str:
        """Build GODS MODE enhanced prompt with professional crypto analysis"""
        
        profit_signals = self._calculate_profit_signals(market_data)
        
        base_data = f"""
===== GODS MODE LEVEL 13 TRADING ANALYSIS =====
SYMBOL: {market_data.symbol}
TIMESTAMP: {market_data.timestamp}

=== LIVE MARKET DATA ===
Current Price: ${market_data.price:,.4f}
24h Volume: ${market_data.volume_24h:,.0f}
ATR (Volatility): ${market_data.volatility_atr:.4f}
ADX (Trend Strength): {market_data.adx_14:.1f}
Spread: {market_data.spread_percent:.4f}%
Funding Rate: {market_data.funding_rate:.4f}%

=== PROFIT OPPORTUNITY ANALYSIS ===
{profit_signals}

=== STRATEGY CONTEXT ===
{strategy_context}

=== TRADING RULES (MANDATORY) ===
1. SHORTS ONLY - Never recommend LONG positions
2. Minimum 70% confidence for SHORT signal
3. Stop-loss MANDATORY on every trade
4. Risk:Reward minimum 1:1.5
5. Consider funding rates for entry timing
"""
        
        role_analysis = self._get_gods_mode_analysis(market_data)
        
        return f"""{base_data}

=== {self.role.upper()} SPECIALIZED ANALYSIS ===
{role_analysis}

As {self.name} ({self.role}), provide GODS MODE SHORT trade analysis.
Expertise: {self.specialty}

RESPOND IN JSON FORMAT:
{{
    "score": 0-100 (SHORT confluence score),
    "direction": "short" or "hold",
    "strategy": "scalping" | "waterfall" | "snowball" | "pyramid",
    "entry_zone": [upper_price, lower_price],
    "stop_loss": price_level,
    "targets": [tp1, tp2, tp3],
    "confidence": 0.0-1.0,
    "reasoning": "detailed analysis using your specialty"
}}
"""

    def _get_gods_mode_analysis(self, market_data: MarketData) -> str:
        """Generate GODS MODE role-specific professional analysis"""
        
        if "Quant" in self.role:
            return f"""
TECHNICAL ANALYSIS (Moving Averages & RSI):
- Analyze price action relative to key moving averages (20, 50, 200 EMA)
- Calculate RSI levels for overbought conditions (>70 = SHORT signal)
- Identify bearish divergence between price and momentum indicators

HISTORICAL DATA ANALYSIS:
- Review recent price trends for {market_data.symbol}
- Identify significant resistance levels from past data
- Analyze volume patterns during previous tops

RISK MANAGEMENT FOCUS:
- Calculate optimal position size based on volatility
- Set stop-loss at key technical levels
- Define take-profit targets at support zones

QUANTITATIVE METRICS:
- Current ADX: {market_data.adx_14:.1f} (trend strength)
- Volatility: {market_data.volatility_atr:.4f}
- Volume Profile: ${market_data.volume_24h:,.0f}
"""
        
        elif "Macro" in self.role:
            funding_signal = "LONGS OVERLEVERAGED - SHORT" if market_data.funding_rate > 0 else "SHORTS DOMINANT - CAUTION"
            return f"""
MARKET ANALYSIS (Current Trends):
- Analyze macroeconomic factors affecting {market_data.symbol}
- Consider correlation with traditional markets (S&P500, DXY)
- Evaluate crypto market sentiment and Bitcoin dominance

PRICE PREDICTION ANALYSIS:
- Use technical indicators for SHORT opportunity assessment
- Consider historical patterns and current market conditions
- Factor in macro events (Fed decisions, regulatory news)

FUNDING RATE STRATEGY:
- Current Funding: {market_data.funding_rate:.4f}%
- Signal: {funding_signal}
- If positive funding > 0.01%, longs pay shorts = HIGH SHORT OPPORTUNITY

WHALE ACTIVITY MONITORING:
- Track large holder distribution patterns
- Monitor exchange inflows (selling pressure indicator)
- Analyze on-chain metrics for smart money movement
"""
        
        elif "Psychologist" in self.role or "Contrarian" in self.role:
            return f"""
SENTIMENT ANALYSIS (Social & News):
- Analyze recent social media sentiment for {market_data.symbol}
- Monitor Twitter, Reddit, Telegram for fear/greed indicators
- Track retail trader positioning and sentiment extremes

MARKET SENTIMENT INDICATORS:
- Fear & Greed Index analysis
- Long/Short ratio assessment
- Open interest changes and liquidation levels

CONTRARIAN PSYCHOLOGY:
- Identify when crowd is overly bullish (SHORT opportunity)
- Detect FOMO patterns that typically reverse
- Spot liquidity grabs above resistance (Judas Swing setup)

RETAIL TRAP DETECTION:
- Identify fake breakouts designed to trap long traders
- Monitor stop-loss clusters above recent highs
- Analyze capitulation and exhaustion patterns
"""
        
        elif "News" in self.role or "Sniper" in self.role:
            return f"""
NEWS UPDATES (Latest Crypto News):
- Summarize major events impacting {market_data.symbol}
- Track regulatory developments and government actions
- Monitor exchange news (listings, delistings, issues)

REGULATORY INSIGHTS:
- Analyze recent regulatory changes affecting crypto trading
- Consider SEC, CFTC, and international regulatory actions
- Factor in potential regulatory risks

CATALYST ANALYSIS:
- Identify negative catalysts (hacks, exploits, failures)
- Track FUD acceleration and news velocity
- Monitor whale alerts and large exchange deposits

REAL-TIME INTELLIGENCE:
- Social sentiment shift detection
- Breaking news impact assessment
- Correlation with traditional market news
"""
        
        elif "Scalper" in self.role:
            return f"""
TECHNICAL ANALYSIS (Micro-Timeframe):
- 1-minute and 5-minute chart structure analysis
- Fair Value Gap (FVG) detection for bearish imbalances
- Breaker block identification at key levels

TRADING BOT OPTIMIZATION:
- Identify precise entry levels for minimal drawdown
- Calculate optimal stop-loss placement
- Define quick take-profit targets (0.3-0.8%)

ENTRY PRECISION:
- Micro-structure analysis (lower highs, lower lows)
- Order block and FVG confluence zones
- Immediate bearish pattern recognition

SCALPING PARAMETERS:
- Price: ${market_data.price:,.4f}
- Target: 0.3-0.8% moves
- Stop-loss: Tight at structure break
- Execution: IOC market orders for speed
"""
        
        elif "Pattern" in self.role:
            return f"""
TECHNICAL ANALYSIS (Chart Patterns):
- Head & Shoulders, Double Top, Rising Wedge detection
- Bear Flag and Descending Triangle identification
- Trend line breaks and support failures

HARMONIC PATTERNS:
- Bearish Bat, Crab, Butterfly, Gartley, Shark patterns
- PRZ (Potential Reversal Zone) identification
- Fibonacci confluence analysis

FIBONACCI ANALYSIS:
- Key retracement levels (38.2%, 50%, 61.8%, 78.6%)
- Extension targets for take-profit placement
- Confluence with harmonic pattern completion

CANDLESTICK PATTERNS:
- Bearish engulfing at resistance
- Shooting star and evening star formations
- Doji at exhaustion points
- Three black crows pattern
"""
        
        return ""

    def _mock_analyze(self, market_data: MarketData) -> Dict:
        """Fallback mock analysis when API fails."""
        import random
        
        mock_score = random.randint(70, 95)
        weighted_score = int(mock_score * self.weight)
        
        signal = TradeSignal(
            symbol=market_data.symbol,
            direction="short",
            strategy=self.preferred_strategy,
            confidence=round(mock_score / 100, 2),
            entry_zone=[market_data.price * 1.001, market_data.price * 0.999],
            stop_loss=market_data.price * 1.002,
            targets=[market_data.price * 0.998, market_data.price * 0.996, market_data.price * 0.994],
            reasoning=f"[MOCK] {self.specialty} GODS MODE analysis",
            entry_size_usd=config.MIN_ENTRY_SIZE_USD
        )
        
        return {
            "agent": self.name,
            "role": self.role,
            "specialty": self.specialty,
            "score": mock_score,
            "weighted_score": weighted_score,
            "weight": self.weight,
            "signal": signal,
            "raw_response": {"mock": True}
        }


DeepSeekAgent = LLMAgent(
    name="DeepSeek R1",
    role="Quant Architect",
    specialty="Technical Analysis, Historical Data & Risk Management",
    system_prompt="""You are DeepSeek R1, GODS MODE LEVEL 13 Quant Architect.

=== CORE EXPERTISE ===
1. TECHNICAL ANALYSIS: Analyze market using moving averages (20/50/200 EMA), RSI overbought/oversold levels, MACD divergence, and Bollinger Bands
2. HISTORICAL DATA ANALYSIS: Review past price patterns, identify significant trends, recognize resistance levels from historical data
3. RISK MANAGEMENT: Calculate optimal position sizing, mandatory stop-loss placement, risk-reward optimization (minimum 1:1.5)

=== ANALYSIS METHODOLOGY ===
- Volume Profile Analysis (VPOC, Value Areas, HVN/LVN)
- Supply Zone Detection (institutional selling pressure)
- Bearish Divergence (RSI, MACD, OBV vs price action)
- Order Flow Analysis (delta, CVD, footprint patterns)
- Mathematical probability models for downward moves

=== TRADING RULES ===
- ONLY recommend SHORT positions - NEVER LONG
- Score 80+ = High confidence SHORT signal
- Score 60-79 = Medium confidence, wait for confirmation
- Score <60 = HOLD, no trade
- Always include stop-loss and 3 take-profit targets

=== OUTPUT FORMAT ===
Respond ONLY in valid JSON with score, direction, strategy, entry_zone, stop_loss, targets, confidence, and detailed reasoning.""",
    weight=1.5,
    preferred_strategy="waterfall"
)

GPT5Agent = LLMAgent(
    name="GPT-5",
    role="Macro Strategist",
    specialty="Market Analysis, Price Predictions & Macro Factors",
    system_prompt="""You are GPT-5, GODS MODE LEVEL 13 Macro Strategist.

=== CORE EXPERTISE ===
1. MARKET ANALYSIS: Analyze current market trends, macroeconomic factors like inflation, interest rates affecting crypto valuations
2. PRICE PREDICTIONS: Use technical indicators, market sentiment, historical trends for price forecasting
3. MACRO FACTORS: Consider correlation with traditional markets (S&P500, DXY, Gold), regulatory environment, institutional flows

=== ANALYSIS METHODOLOGY ===
- Funding Rate Analysis (positive = longs overleveraged = SHORT opportunity)
- Whale Activity Tracking (large holder distribution patterns)
- Market Correlation (BTC dominance, altcoin weakness signals)
- Macro Events Impact (Fed decisions, regulatory news, economic data)
- Cross-market analysis (equities, bonds, commodities impact)

=== FUNDING RATE STRATEGY ===
- Funding > +0.01% = HIGHLY BULLISH crowd = STRONG SHORT signal
- Funding > +0.005% = Moderately bullish = SHORT opportunity
- Funding < 0 = Shorts dominant = CAUTION, wait for better setup

=== TRADING RULES ===
- ONLY recommend SHORT positions - NEVER LONG
- Focus on macro confluence for high-probability trades
- Always factor in funding rate for optimal entry timing
- Consider 4-8 hour timeframe for macro setups

=== OUTPUT FORMAT ===
Respond ONLY in valid JSON with score, direction, strategy, entry_zone, stop_loss, targets, confidence, and macro-based reasoning.""",
    weight=1.3,
    preferred_strategy="waterfall"
)

ClaudeAgent = LLMAgent(
    name="Claude Opus",
    role="Contrarian Psychologist",
    specialty="Sentiment Analysis, Market Psychology & Retail Trap Detection",
    system_prompt="""You are Claude Opus, GODS MODE LEVEL 13 Contrarian Psychologist.

=== CORE EXPERTISE ===
1. SENTIMENT ANALYSIS: Analyze social media sentiment, news articles, Fear & Greed Index for trading signals
2. MARKET PSYCHOLOGY: Understand crowd behavior, FOMO patterns, capitulation signals, exhaustion points
3. RETAIL TRAP DETECTION: Identify fake breakouts, stop hunts, liquidity grabs designed to trap retail traders

=== ANALYSIS METHODOLOGY ===
- Liquidity Grab Detection (sweeps above old highs = SHORT setup)
- Judas Swing Identification (fake breakouts that reverse hard)
- Retail Trap Analysis (where retail gets trapped long)
- Sentiment Extremes (extreme greed = contrarian SHORT signal)
- Stop Hunt Patterns (market makers hunting retail stops)

=== CONTRARIAN SIGNALS ===
- Extreme bullish sentiment = HIGH SHORT opportunity
- FOMO buying spikes = Reversal imminent
- "This time is different" narratives = Top signal
- Retail long/short ratio extreme = Fade the crowd

=== TRADING RULES ===
- ONLY recommend SHORT positions - NEVER LONG
- Be contrarian when crowd is euphoric
- Wait for liquidity grabs above key levels
- Target trapped long liquidations for profit

=== OUTPUT FORMAT ===
Respond ONLY in valid JSON with score, direction, strategy, entry_zone, stop_loss, targets, confidence, and psychology-based reasoning.""",
    weight=1.2,
    preferred_strategy="snowball"
)

GrokAgent = LLMAgent(
    name="Grok xAI",
    role="Real-Time News Sniper",
    specialty="News Updates, Regulatory Insights & Catalyst Analysis",
    system_prompt="""You are Grok xAI, GODS MODE LEVEL 13 Real-Time News Sniper.

=== CORE EXPERTISE ===
1. NEWS UPDATES: Summarize latest news and major events impacting cryptocurrency market
2. REGULATORY INSIGHTS: Analyze regulatory changes, SEC/CFTC actions, international crypto regulations
3. CATALYST ANALYSIS: Identify negative catalysts (hacks, exploits, delistings) that trigger sell-offs

=== ANALYSIS METHODOLOGY ===
- FUD Velocity Measurement (acceleration of negative news)
- Breaking News Impact Assessment (which news moves price)
- Regulatory Risk Analysis (government crackdowns, legal issues)
- Social Sentiment Tracking (Twitter, Reddit, Telegram fear)
- Whale Alert Analysis (large exchange deposits = selling pressure)

=== NEWS-BASED SIGNALS ===
- Negative regulatory news = STRONG SHORT
- Exchange issues (hacks, insolvency) = IMMEDIATE SHORT
- Large whale deposits to exchanges = Selling incoming
- FUD acceleration with no rebuttal = Panic selling ahead

=== TRADING RULES ===
- ONLY recommend SHORT positions - NEVER LONG
- React fast to breaking negative news
- Factor in news velocity and social amplification
- Consider news already priced in vs fresh catalyst

=== OUTPUT FORMAT ===
Respond ONLY in valid JSON with score, direction, strategy, entry_zone, stop_loss, targets, confidence, and news-based reasoning.""",
    weight=1.4,
    preferred_strategy="waterfall"
)

LlamaAgent = LLMAgent(
    name="Llama 3.3",
    role="High-Speed Scalper",
    specialty="Micro Technical Analysis, Entry Precision & Quick Profits",
    system_prompt="""You are Llama 3.3, GODS MODE LEVEL 13 High-Speed Scalper.

=== CORE EXPERTISE ===
1. MICRO TECHNICAL ANALYSIS: 1-minute and 5-minute chart patterns, micro-structure analysis
2. ENTRY PRECISION: Exact price levels for minimal drawdown, tight stop-loss placement
3. QUICK PROFITS: Target 0.3-0.8% moves, rapid trade execution, hit-and-run style

=== ANALYSIS METHODOLOGY ===
- Fair Value Gap (FVG) Detection (bearish imbalances to fill)
- Breaker Block Analysis (failed support becomes resistance)
- 1-Minute Structure (lower highs, lower lows forming)
- Order Block Identification (institutional entry zones)
- Liquidity Pool Targeting (stops clustered = target)

=== SCALPING PARAMETERS ===
- Entry: At FVG or breaker block with confirmation
- Stop-loss: Just above structure high (tight)
- Target 1: 0.3% (quick partial)
- Target 2: 0.5% (main target)
- Target 3: 0.8% (runner)

=== TRADING RULES ===
- ONLY recommend SHORT positions - NEVER LONG
- Precision entries with minimal drawdown
- Quick profit-taking, no greed
- Tight stops, high win rate focus

=== OUTPUT FORMAT ===
Respond ONLY in valid JSON with score, direction, strategy, entry_zone, stop_loss, targets, confidence, and micro-structure reasoning.""",
    weight=1.0,
    preferred_strategy="scalping"
)

QwenAgent = LLMAgent(
    name="Qwen 72B",
    role="Pattern Hunter",
    specialty="Chart Patterns, Harmonic Patterns & Fibonacci Analysis",
    system_prompt="""You are Qwen 72B, GODS MODE LEVEL 13 Pattern Hunter.

=== CORE EXPERTISE ===
1. CHART PATTERNS: Head & Shoulders, Double Top, Rising Wedge, Bear Flag, Descending Triangle
2. HARMONIC PATTERNS: Bearish Bat, Crab, Butterfly, Gartley, Shark pattern recognition
3. FIBONACCI ANALYSIS: Key retracement levels (38.2%, 50%, 61.8%, 78.6%), extension targets

=== ANALYSIS METHODOLOGY ===
- Pattern Completion Detection (is pattern confirming?)
- PRZ Identification (Potential Reversal Zone)
- Fibonacci Confluence (multiple fib levels aligning)
- Candlestick Confirmation (bearish engulfing, shooting star, evening star)
- Multi-timeframe Pattern Alignment

=== PATTERN-BASED SIGNALS ===
- Head & Shoulders neckline break = STRONG SHORT
- Double Top confirmation = SHORT
- Rising Wedge breakdown = SHORT with momentum
- Bearish harmonic at PRZ = HIGH probability SHORT
- 61.8% or 78.6% fib retracement = Key SHORT level

=== TRADING RULES ===
- ONLY recommend SHORT positions - NEVER LONG
- Wait for pattern completion/confirmation
- Use Fibonacci for precise entry/exit levels
- Multiple pattern confluence = highest probability

=== OUTPUT FORMAT ===
Respond ONLY in valid JSON with score, direction, strategy, entry_zone, stop_loss, targets, confidence, and pattern-based reasoning.""",
    weight=1.0,
    preferred_strategy="pyramid"
)


ALL_AGENTS = [DeepSeekAgent, GPT5Agent, ClaudeAgent, GrokAgent, LlamaAgent, QwenAgent]


def get_multi_agent_consensus(market_data: MarketData, strategy_context: str = "GODS MODE Trinity of Profit") -> Dict:
    """GODS MODE: Runs all 6 AI agents with weighted voting for SHORT consensus."""
    
    print(f"\n{'='*60}")
    print(f"GODS MODE MULTI-AGENT ANALYSIS: {market_data.symbol}")
    print(f"{'='*60}")
    
    results = []
    total_score = 0
    total_weighted_score = 0
    total_weight = 0
    short_votes = 0
    
    for agent in ALL_AGENTS:
        result = agent.analyze(market_data, strategy_context)
        results.append(result)
        
        score = result.get("score", 0)
        weighted_score = result.get("weighted_score", score)
        weight = result.get("weight", 1.0)
        
        total_score += score
        total_weighted_score += weighted_score
        total_weight += weight
        
        if result["signal"].direction == "short":
            short_votes += 1
    
    avg_score = total_score / len(ALL_AGENTS)
    weighted_avg_score = total_weighted_score / total_weight if total_weight > 0 else avg_score
    
    consensus = "short" if short_votes >= 4 else "hold"
    
    best_result = max(results, key=lambda x: x.get("weighted_score", x["score"]))
    best_signal = best_result["signal"]
    
    strategy_votes = {}
    for r in results:
        strat = r["signal"].strategy
        if strat not in strategy_votes:
            strategy_votes[strat] = 0
        strategy_votes[strat] += r.get("weight", 1.0)
    
    recommended_strategy = max(strategy_votes, key=strategy_votes.get) if strategy_votes else "scalping"
    
    print(f"\n{'='*60}")
    print(f"GODS MODE CONSENSUS: {consensus.upper()} | Score: {avg_score:.1f} | Votes: {short_votes}/6")
    print(f"Weighted Score: {weighted_avg_score:.1f} | Strategy: {recommended_strategy.upper()}")
    print(f"{'='*60}\n")
    
    return {
        "symbol": market_data.symbol,
        "consensus": consensus,
        "avg_score": avg_score,
        "weighted_score": weighted_avg_score,
        "short_votes": short_votes,
        "best_signal": best_signal,
        "recommended_strategy": recommended_strategy,
        "strategy_votes": strategy_votes,
        "agent_results": results,
        "agents": [{"name": r["agent"], "score": r["score"], "direction": r["signal"].direction, "weight": r["weight"]} for r in results]
    }
