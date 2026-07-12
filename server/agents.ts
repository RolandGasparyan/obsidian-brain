import OpenAI from "openai";
import { DEFAULT_AGENTS, type AgentConfig, type AgentAnalysis, type MarketData, type SignalType } from "@shared/schema";

const openai = new OpenAI({
  apiKey: process.env.AI_INTEGRATIONS_OPENAI_API_KEY,
  baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
});

function generateMockMarketData(symbol: string): MarketData {
  const basePrices: Record<string, number> = {
    "BTC/USDT": 97500,
    "ETH/USDT": 3450,
    "SOL/USDT": 185,
    "XRP/USDT": 2.15,
    "DOGE/USDT": 0.32,
  };
  
  const basePrice = basePrices[symbol] || 100;
  const volatility = 0.02;
  const change = (Math.random() - 0.5) * volatility * basePrice;
  const currentPrice = basePrice + change;
  
  return {
    symbol,
    currentPrice: parseFloat(currentPrice.toFixed(2)),
    priceChange24h: parseFloat(((Math.random() - 0.5) * 8).toFixed(2)),
    volume24h: parseFloat((Math.random() * 5000000000 + 1000000000).toFixed(0)),
    high24h: parseFloat((currentPrice * 1.03).toFixed(2)),
    low24h: parseFloat((currentPrice * 0.97).toFixed(2)),
    vwap: parseFloat((currentPrice * 0.995).toFixed(2)),
    rsi: parseFloat((Math.random() * 40 + 30).toFixed(1)),
    macd: {
      macd: parseFloat(((Math.random() - 0.5) * 100).toFixed(2)),
      signal: parseFloat(((Math.random() - 0.5) * 80).toFixed(2)),
      histogram: parseFloat(((Math.random() - 0.5) * 50).toFixed(2)),
    },
    bollingerBands: {
      upper: parseFloat((currentPrice * 1.02).toFixed(2)),
      middle: currentPrice,
      lower: parseFloat((currentPrice * 0.98).toFixed(2)),
    },
    fundingRate: parseFloat(((Math.random() - 0.5) * 0.001).toFixed(6)),
    predictedFundingRate: parseFloat(((Math.random() - 0.5) * 0.0015).toFixed(6)),
    openInterest: parseFloat((Math.random() * 10000000000 + 5000000000).toFixed(0)),
    longShortRatio: parseFloat((Math.random() * 0.6 + 0.7).toFixed(2)),
    orderBookImbalance: parseFloat(((Math.random() - 0.5) * 0.4).toFixed(4)),
    bidAskSpread: parseFloat((Math.random() * 0.001).toFixed(6)),
    markPrice: parseFloat((currentPrice * (1 + (Math.random() - 0.5) * 0.001)).toFixed(2)),
    indexPrice: parseFloat((currentPrice * (1 + (Math.random() - 0.5) * 0.0005)).toFixed(2)),
    liquidations24h: {
      longLiquidations: parseFloat((Math.random() * 50000000).toFixed(0)),
      shortLiquidations: parseFloat((Math.random() * 50000000).toFixed(0)),
      totalLiquidations: parseFloat((Math.random() * 100000000).toFixed(0)),
    },
    timestamp: new Date().toISOString(),
    dataSource: "simulated" as const,
  };
}

// UNIVERSAL AI MASTER PROMPT - All 8 models use the SAME prompt for FAIR competition
// They compete on: execution timing, pattern recognition, risk management, decision-making

const UNIVERSAL_MASTER_PROMPT = `# ELITE AI TRADING AGENT - GODS LEVEL UNIVERSAL KNOWLEDGE BASE

You are an Elite AI Trading Agent competing against 7 other AI models in a 24/7 trading competition.
All AIs have IDENTICAL knowledge and strategies. You compete on EXECUTION QUALITY, timing, and decision-making.

Mission: Dominate the 24/7 AI trading competition. Rank #1.
Goal: Maximum profit with 70-90% win rate using Gods Level intelligence.

## COMPLETE TRADING ARSENAL (50+ Methods)

### 1. FIBONACCI MASTERY (30% of Edge)
- OTE Zones: 0.618-0.786 (Golden Pocket = highest probability)
- Extensions: 1.272, 1.618, 2.618 for targets
- Time Zones: Predict reversal timing
- Entry: Wait for 0.618-0.786, confirm with volume
- Stop: Beyond 0.886 or swing low/high
- Target: 1.272 (conservative), 1.618 (aggressive)

### 2. VWAP INTELLIGENCE
- Deviation Bands: +/-1σ (68%), +/-2σ (95%), +/-3σ (99.7%)
- Mean Reversion: Price > VWAP+2σ = SHORT, Price < VWAP-2σ = LONG
- Breakout: Beyond +/-2σ with volume = strong trend
- Institutional: Large players use VWAP for execution
- Slope: Upward = bullish bias, Downward = bearish bias

### 3. SMART MONEY CONCEPTS (30% of Edge)
- Fair Value Gaps (FVG): Imbalance between candles
  * Bullish FVG: Gap below = support
  * Bearish FVG: Gap above = resistance
  * Entry: 50% fill (consequent encroachment)
- Order Blocks: Last opposite candle before strong move
- Breaker Blocks: Failed order blocks (role reversal)
- Liquidity Pools: BSL (above highs), SSL (below lows)
- Liquidity Grab: Spike to trigger stops → reversal
- Market Structure: BOS (continuation), CHoCH (reversal)

### 4. ORDER FLOW & VOLUME (30% of Edge)
- Order Book: Bid/ask walls, depth imbalance
  * Bid/Ask > 1.5 = bullish pressure
  * Bid/Ask < 0.67 = bearish pressure
- Volume Profile: POC (magnet), Value Area (70% volume)
- Whale Detection: Orders > 15% avg volume
- Liquidation Heatmaps: Cluster zones (fade into them)

### 5. DERIVATIVES ANALYSIS (20% of Edge)
- Funding Rate:
  * > +0.15% = overleveraged longs → SHORT
  * < -0.15% = overleveraged shorts → LONG
- Open Interest:
  * Rising OI + Rising Price = bullish
  * Rising OI + Falling Price = bearish
- Long/Short Ratio:
  * > 2.0 = too many longs → reversal down
  * < 0.5 = too many shorts → reversal up

### 6. HARMONIC PATTERNS (10% of Edge)
- Gartley: D at 0.786 XA (70-80% win rate)
- Bat: D at 0.886 XA (75% win rate - higher accuracy)
- Butterfly: D at 1.27-1.618 XA (80% win rate)
- Crab: D at 1.618 XA (85% win rate - most aggressive)
- Entry: Point D with RSI divergence
- Target: 0.382 AD, 0.618 AD

### 7. TECHNICAL INDICATORS
- EMA: 9 (scalp), 21 (day), 50 (swing), 200 (trend)
- RSI: <30 oversold, >70 overbought, divergence = reversal
- MACD: Signal cross, zero cross, histogram, divergence
- Bollinger Bands: Squeeze (breakout coming), walk the band
- ATR: Volatility measure, stop loss = 1.5x ATR
- Stochastic RSI: <20 buy, >80 sell, crossovers

### 8. ADVANCED STRATEGIES (10% of Edge)
- Wyckoff: Accumulation (Spring), Distribution (Upthrust)
- Elliott Wave: 5-wave impulse, 3-wave correction
- Ichimoku: Cloud, Tenkan/Kijun crosses
- Kelly Criterion: Position size = (Win%×AvgWin - Loss%×AvgLoss)/AvgWin

### 9. MARKET REGIME DETECTION (7 Types)
- STRONG_TRENDING_UP (ADX > 35): Aggressive longs, pyramiding
- TRENDING_UP (ADX > 25): Trend following longs
- RANGING (ADX < 20): Mean reversion, fade extremes
- TRENDING_DOWN (ADX > 25): Trend following shorts
- STRONG_TRENDING_DOWN (ADX > 35): Aggressive shorts
- HIGH_VOLATILITY (ATR > 150% avg): Scalping, wider stops
- LOW_VOLATILITY (ATR < 70% avg): Wait for breakout

### 10. NEWS & CATALYSTS
- High Impact: Fed, CPI, Employment, GDP
- Crypto: Listings, upgrades, regulation, whale moves
- Strategy: Wait 5-15min after event, then trade new trend

## DECISION FRAMEWORK (70 seconds total)

STEP 1: MARKET ANALYSIS (30 sec)
- Regime? (Trending/Ranging/Volatile)
- Trend? (Bullish/Bearish/Neutral on higher TF)
- Key Levels? (VWAP, EMAs, Support/Resistance)
- Order Book? (Bid/ask imbalance)
- Sentiment? (Funding, Long/Short ratio)

STEP 2: OPPORTUNITY SCAN (20 sec)
- FVG, Order Block, or Liquidity Pool?
- Harmonic Pattern completing?
- Technical Signal? (RSI, MACD, etc.)
- Whale Activity? (Large orders)
- News Catalyst?

STEP 3: EDGE SCORE CALCULATION (10 sec)
Technical Score (0-100):
- Fibonacci alignment: +20
- VWAP position: +15
- EMA alignment: +15
- RSI/MACD signal: +20
- Bollinger position: +10
- ATR confirmation: +10
- Multi-timeframe: +10

Order Flow Score (0-100):
- Bid/ask imbalance: +30
- Volume surge: +20
- Order book walls: +20
- Liquidation zones: +15
- Volume profile: +15

Sentiment Score (0-100):
- Funding rate: +40
- Open interest: +30
- Long/Short ratio: +30

Strategy Score (0-100):
- FVG present: +25
- Order block: +25
- Harmonic pattern: +25
- Liquidity pool: +25

Whale Score (0-100):
- Large order detected: +50
- Repeated accumulation: +30
- Whale direction: +20

FINAL EDGE SCORE:
Edge = (Technical×30%) + (OrderFlow×30%) + (Sentiment×20%) + (Strategy×10%) + (Whale×10%)

MINIMUM: 60% (do not trade below this)
OPTIMAL: 80%+ (85-90% win rate)

STEP 4: MODE SELECTION (5 sec)
Edge >= 90: ULTRA_AGGRESSIVE (15-20x leverage, 2.5-3% position)
Edge >= 80: AGGRESSIVE (10-15x leverage, 2-2.5% position)
Edge >= 70: NORMAL (5-10x leverage, 1.5-2% position)
Edge >= 60: SAFE (3-5x leverage, 1-1.5% position)
Edge < 60: NO TRADE

STEP 5: EXECUTION (5 sec)
- Position Size: Balance × Position% × Leverage
- Entry: Current price or limit order
- Stop Loss: Entry +/- (1.5 × ATR) or beyond structure
- Take Profit 1 (50%): 1:2 R/R
- Take Profit 2 (30%): 1:3 R/R
- Take Profit 3 (20%): 1:5 R/R

## CONSENSUS LEVELS (8 AI AGREEMENT):
- 7-8 agents agree: GODLIKE (90%+ win probability)
- 6 agents agree: ELITE (85% win probability)
- 5 agents agree: STRONG (80% win probability)
- 3-4 agents agree: MODERATE (70% win probability)
- <3 agents agree: WEAK (skip trade)

## COMPETITION RANKING:
Ranking = (Total_PnL × 40%) + (Win_Rate × 30%) + (Trade_Count × 20%) + (Consistency × 10%)

TIERS:
- Gods Mode: Score > 1000
- Legend: 750-1000
- Elite: 500-750
- Master: 300-500
- Expert: 150-300
- Intermediate: 50-150
- Novice: 0-50

## SELF-PRESERVATION:
- Daily Loss Limit: 5% of starting balance
- If hit: Auto-deactivate until 00:00 UTC reset
- Protects capital, prevents revenge trading

## WINNING STRATEGIES:
1. Quality > Quantity: Edge 80+ = 85%+ win rate
2. Confluence is King: More signals = higher edge
3. Risk Management: Never >3% per trade
4. Adapt to Regime: Different strategies for different markets
5. Follow Whales: Large players often know more
6. Respect Structure: HH/HL or LH/LL is your guide
7. Patience: Wait for edge > 60, don't force trades
8. Compound: As balance grows, so do position sizes

## YOUR MISSION:
You have the SAME knowledge as 7 other AIs.
Your edge comes from:
- Better execution (timing, entry)
- Better risk management (stops, sizing)
- Better pattern recognition (seeing more confluences)
- Better decisions (higher edge scores)

TRADE SMART. TRADE WITH EDGE. DOMINATE THE LEADERBOARD.
`;

// AI Personality traits that subtly influence decision-making
const AI_PERSONALITIES: Record<string, { trait: string; edgeModifier: string }> = {
  deepseek: { trait: "Analytical and precise", edgeModifier: "Slightly favors mathematical precision and Fibonacci levels" },
  gpt5: { trait: "Strategic and calculated", edgeModifier: "Slightly favors institutional flow and derivatives data" },
  claude: { trait: "Contrarian and patient", edgeModifier: "Slightly favors liquidity hunting and stop hunt setups" },
  grok: { trait: "Fast and reactive", edgeModifier: "Slightly favors news catalysts and momentum plays" },
  llama: { trait: "Aggressive and opportunistic", edgeModifier: "Slightly favors FVG and microstructure scalping" },
  gemini: { trait: "Adaptive and flexible", edgeModifier: "Slightly favors cross-market correlation and multi-timeframe" },
  mistral: { trait: "Conservative and risk-aware", edgeModifier: "Slightly favors risk-adjusted sizing and drawdown protection" },
  qwen: { trait: "Pattern-focused and methodical", edgeModifier: "Slightly favors harmonic patterns and PRZ entries" },
};

// All 8 AI models use the SAME universal prompt with personality context
const agentPrompts: Record<string, string> = {
  deepseek: UNIVERSAL_MASTER_PROMPT + `

## YOUR PERSONALITY: Analytical and Precise
You excel at mathematical precision. When multiple setups are equal, you slightly favor:
- Fibonacci OTE zones with exact 0.618-0.786 calculations
- VWAP deviation with precise measurement
- Kelly Criterion position sizing
Focus on QUANTITATIVE EDGE and statistical probability.`,

  gpt5: UNIVERSAL_MASTER_PROMPT + `

## YOUR PERSONALITY: Strategic and Calculated
You excel at institutional analysis. When multiple setups are equal, you slightly favor:
- Derivatives data (funding rate extremes, OI divergence)
- Liquidation heatmaps and cascade zones
- Order book imbalance and institutional flow
Focus on FOLLOWING SMART MONEY and fading retail.`,

  claude: UNIVERSAL_MASTER_PROMPT + `

## YOUR PERSONALITY: Contrarian and Patient
You excel at liquidity hunting. When multiple setups are equal, you slightly favor:
- BSL/SSL liquidity pool setups
- Judas swing and stop hunt opportunities
- Contrarian plays when sentiment is extreme
Focus on THINKING LIKE A MARKET MAKER, not retail.`,

  grok: UNIVERSAL_MASTER_PROMPT + `

## YOUR PERSONALITY: Fast and Reactive
You excel at catalyst trading. When multiple setups are equal, you slightly favor:
- News and event-driven opportunities
- Sentiment extremes and narrative exhaustion
- Momentum plays with strong catalysts
Focus on SPEED and reacting to information before others.`,

  llama: UNIVERSAL_MASTER_PROMPT + `

## YOUR PERSONALITY: Aggressive and Opportunistic
You excel at microstructure scalping. When multiple setups are equal, you slightly favor:
- Fair Value Gap (FVG) entries at 50% fill
- Breaker blocks and displacement candles
- High-frequency scalping opportunities
Focus on QUICK EXECUTION and capturing small moves frequently.`,

  gemini: UNIVERSAL_MASTER_PROMPT + `

## YOUR PERSONALITY: Adaptive and Flexible
You excel at cross-market analysis. When multiple setups are equal, you slightly favor:
- Cross-asset correlations (BTC vs S&P, DXY, Gold)
- Multi-timeframe confluence (10+ timeframes)
- Volatility clustering and regime changes
Focus on SEEING THE BIG PICTURE across all markets.`,

  mistral: UNIVERSAL_MASTER_PROMPT + `

## YOUR PERSONALITY: Conservative and Risk-Aware
You excel at risk management. When multiple setups are equal, you slightly favor:
- Kelly Criterion optimal position sizing
- Volatility-adjusted trade sizing
- Drawdown protection and capital preservation
Focus on MAXIMIZING RISK-ADJUSTED RETURNS with Sharpe >2.0.`,

  qwen: UNIVERSAL_MASTER_PROMPT + `

## YOUR PERSONALITY: Pattern-Focused and Methodical
You excel at harmonic patterns. When multiple setups are equal, you slightly favor:
- Harmonic patterns (Gartley, Bat, Butterfly, Crab)
- PRZ (Potential Reversal Zone) with 3+ Fib confluences
- RSI divergence confirmation at pattern completion
Focus on HIGH-PROBABILITY REVERSALS with 1:5+ R:R.`,
};

// Export the universal prompt for use elsewhere
export const getUniversalPrompt = () => UNIVERSAL_MASTER_PROMPT;
export const getAIPersonalities = () => AI_PERSONALITIES;

export async function analyzeWithAgent(
  agent: AgentConfig,
  marketData: MarketData
): Promise<AgentAnalysis> {
  const systemPrompt = agentPrompts[agent.id] || "You are a trading analyst.";
  
  const liquidationsInfo = marketData.liquidations24h 
    ? `- 24h Long Liquidations: $${(marketData.liquidations24h.longLiquidations / 1e6).toFixed(2)}M
- 24h Short Liquidations: $${(marketData.liquidations24h.shortLiquidations / 1e6).toFixed(2)}M
- 24h Total Liquidations: $${(marketData.liquidations24h.totalLiquidations / 1e6).toFixed(2)}M`
    : "";

  const orderBookInfo = marketData.orderBookImbalance !== undefined
    ? `- Order Book Imbalance: ${(marketData.orderBookImbalance * 100).toFixed(2)}% (${marketData.orderBookImbalance > 0 ? 'Buy pressure' : 'Sell pressure'})
- Bid/Ask Spread: ${(marketData.bidAskSpread || 0).toFixed(4)}%`
    : "";

  const futuresInfo = marketData.markPrice !== undefined
    ? `- Mark Price: $${marketData.markPrice.toLocaleString()}
- Index Price: $${marketData.indexPrice?.toLocaleString() || 'N/A'}
- Predicted Funding: ${marketData.predictedFundingRate !== undefined ? (marketData.predictedFundingRate * 100).toFixed(4) + '%' : 'N/A'}`
    : "";

  const userPrompt = `Market Data for ${marketData.symbol} (${marketData.dataSource.toUpperCase()} DATA):

=== SPOT DATA ===
- Current Price: $${marketData.currentPrice.toLocaleString()}
- 24h Change: ${marketData.priceChange24h}%
- 24h Volume: $${(marketData.volume24h / 1e9).toFixed(2)}B
- 24h High: $${marketData.high24h.toLocaleString()}
- 24h Low: $${marketData.low24h.toLocaleString()}

=== TECHNICAL INDICATORS ===
- VWAP: $${marketData.vwap.toLocaleString()} (${marketData.currentPrice > marketData.vwap ? 'Above' : 'Below'} VWAP)
- RSI (14): ${marketData.rsi} (${marketData.rsi > 70 ? 'Overbought' : marketData.rsi < 30 ? 'Oversold' : 'Neutral'})
- MACD: ${marketData.macd.macd.toFixed(2)} (Signal: ${marketData.macd.signal.toFixed(2)}, Histogram: ${marketData.macd.histogram.toFixed(2)})
- Bollinger Bands: Upper $${marketData.bollingerBands.upper.toLocaleString()}, Middle $${marketData.bollingerBands.middle.toLocaleString()}, Lower $${marketData.bollingerBands.lower.toLocaleString()}

=== DERIVATIVES DATA ===
- Funding Rate: ${(marketData.fundingRate * 100).toFixed(4)}% (${marketData.fundingRate > 0 ? 'Longs pay shorts' : 'Shorts pay longs'})
- Open Interest: $${(marketData.openInterest / 1e9).toFixed(2)}B
- Long/Short Ratio: ${marketData.longShortRatio} (${marketData.longShortRatio > 1 ? 'More longs' : 'More shorts'})
${futuresInfo}

=== ORDER FLOW ===
${orderBookInfo}
${liquidationsInfo}

Based on your specialized GODS MODE analysis, identify PRECISE TRADING LEVELS.

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{
  "signal": "long" | "short" | "neutral",
  "confidence": 0.0-1.0,
  "reasoning": "Your specialized analysis summary",
  "keyFindings": ["Finding 1", "Finding 2", "Finding 3"],
  "entryZone": {
    "high": <exact price number>,
    "low": <exact price number>,
    "optimal": <exact price number>,
    "type": "OTE|FVG|Liquidity|Harmonic|Institutional"
  },
  "stopLoss": {
    "price": <exact price number>,
    "reason": "structural invalidation reason"
  },
  "targets": {
    "tp1": {"price": <number>, "type": "1:1 RR or description"},
    "tp2": {"price": <number>, "type": "primary target description"},
    "tp3": {"price": <number>, "type": "runner target description"}
  },
  "levelConfluence": ["list of confluent factors at entry level"]
}`;

  try {
    // Retry logic for more reliable AI responses
    let content: string | null = null;
    let lastError: Error | null = null;
    
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const response = await openai.chat.completions.create({
          model: "gpt-4o-mini", // Use reliable model
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt },
          ],
          response_format: { type: "json_object" },
          max_tokens: 800,
        });
        
        content = response.choices[0]?.message?.content;
        if (content) break;
      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err));
        console.log(`Agent ${agent.id} attempt ${attempt} failed:`, lastError.message);
        if (attempt < 3) await new Promise(r => setTimeout(r, 1000)); // Wait 1s before retry
      }
    }
    
    if (!content) {
      throw lastError || new Error("No response from AI after 3 attempts");
    }

    const parsed = JSON.parse(content);
    
    // Extract Gods Mode structured levels
    const entryZone = parsed.entryZone || {};
    const stopLossData = parsed.stopLoss || {};
    const targets = parsed.targets || {};
    
    return {
      agentId: agent.id,
      agentName: agent.name,
      agentRole: agent.role,
      signal: parsed.signal || "neutral",
      confidence: Math.min(1, Math.max(0, parsed.confidence || 0.5)),
      reasoning: parsed.reasoning || "Analysis complete",
      keyFindings: parsed.keyFindings || [],
      // Gods Mode: Precise Level Data
      entryZone: entryZone.optimal ? {
        high: entryZone.high,
        low: entryZone.low,
        optimal: entryZone.optimal,
        type: entryZone.type || "general"
      } : undefined,
      stopLoss: stopLossData.price,
      stopLossReason: stopLossData.reason,
      targets: targets.tp1 ? {
        tp1: targets.tp1,
        tp2: targets.tp2,
        tp3: targets.tp3
      } : undefined,
      levelConfluence: parsed.levelConfluence || [],
      // Legacy fields for backward compatibility
      entryPrice: entryZone.optimal || parsed.entryPrice,
      target1: targets.tp1?.price || parsed.target1,
      target2: targets.tp2?.price || parsed.target2,
      metadata: {},
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    console.error(`Agent ${agent.id} error:`, error);
    
    return {
      agentId: agent.id,
      agentName: agent.name,
      agentRole: agent.role,
      signal: "neutral",
      confidence: 0.3,
      reasoning: "Analysis encountered an issue - defaulting to neutral stance",
      keyFindings: ["Unable to complete full analysis"],
      metadata: { error: error instanceof Error ? error.message : "Unknown error" },
      timestamp: new Date().toISOString(),
    };
  }
}

// Gods Mode: Kill Zone Synthesis - Calculate high-confluence entry zone from all agent levels
export function calculateConsensus(
  symbol: string,
  marketData: MarketData,
  analyses: AgentAnalysis[]
) {
  const signals = analyses.map(a => a.signal);
  // ⚠️ SHORTS ONLY - Convert all long signals to short
  const shortCount = signals.filter(s => s === "short" || s === "long").length; // Count both as short
  const neutralCount = signals.filter(s => s === "neutral").length;
  
  // SHORTS ONLY - Always output short signal when there's consensus
  let consensusSignal: SignalType = "neutral";
  let agreeingAgents = neutralCount;
  
  // ⚠️ SHORTS ONLY MODE - Force SHORT consensus, never LONG
  if (shortCount > neutralCount) {
    consensusSignal = "short"; // Always SHORT, never long
    agreeingAgents = shortCount;
  }
  
  const avgConfidence = analyses.reduce((sum, a) => sum + a.confidence, 0) / analyses.length;
  const agreementRatio = agreeingAgents / analyses.length;
  const confluenceScore = avgConfidence * agreementRatio;
  
  // Gods Mode: Confluence Level Classification (8 agents)
  type ConfluenceLevel = "GODLIKE" | "ELITE" | "STRONG" | "MODERATE" | "WEAK";
  let confluenceLevel: ConfluenceLevel = "WEAK";
  if (agreeingAgents >= 7) confluenceLevel = "GODLIKE";
  else if (agreeingAgents === 6) confluenceLevel = "ELITE";
  else if (agreeingAgents === 5) confluenceLevel = "STRONG";
  else if (agreeingAgents >= 3) confluenceLevel = "MODERATE";
  
  // Gods Mode: Kill Zone Synthesis from Agent Entry Zones
  const entryZones = analyses
    .filter(a => a.entryZone && a.signal === consensusSignal)
    .map(a => a.entryZone!);
  
  const stopLosses = analyses
    .filter(a => a.stopLoss && a.signal === consensusSignal)
    .map(a => a.stopLoss!);
  
  const allTargets = analyses
    .filter(a => a.targets && a.signal === consensusSignal)
    .map(a => a.targets!);
  
  let killZone: { high: number; low: number; optimal: number; widthPercent: number } | undefined;
  let invalidation: { price: number; reason: string } | undefined;
  let targets: {
    tp1: { price: number; exitPercent: number; type: string };
    tp2: { price: number; exitPercent: number; type: string };
    tp3: { price: number; exitPercent: number; type: string };
  } | undefined;
  let riskReward: { toTp1: number; toTp2: number; toTp3: number } | undefined;
  
  const price = marketData.currentPrice;
  
  if (entryZones.length >= 2) {
    // Calculate Kill Zone using MEDIAN of agent zones
    const sortedHighs = entryZones.map(z => z.high).sort((a, b) => a - b);
    const sortedLows = entryZones.map(z => z.low).sort((a, b) => a - b);
    const sortedOptimals = entryZones.map(z => z.optimal).sort((a, b) => a - b);
    
    const medianIndex = Math.floor(sortedHighs.length / 2);
    const killZoneHigh = sortedHighs[medianIndex];
    const killZoneLow = sortedLows[medianIndex];
    const killZoneOptimal = sortedOptimals[medianIndex];
    const widthPercent = ((killZoneHigh - killZoneLow) / price) * 100;
    
    killZone = {
      high: parseFloat(killZoneHigh.toFixed(2)),
      low: parseFloat(killZoneLow.toFixed(2)),
      optimal: parseFloat(killZoneOptimal.toFixed(2)),
      widthPercent: parseFloat(widthPercent.toFixed(3))
    };
  } else {
    // Fallback: Calculate from current price
    const volatilityFactor = 0.005;
    killZone = {
      high: parseFloat((price * (1 + volatilityFactor)).toFixed(2)),
      low: parseFloat((price * (1 - volatilityFactor)).toFixed(2)),
      optimal: parseFloat(price.toFixed(2)),
      widthPercent: parseFloat((volatilityFactor * 200).toFixed(3))
    };
  }
  
  // Gods Mode: Master Invalidation (worst-case stop from all agents + buffer)
  if (stopLosses.length > 0) {
    const stopPrice = consensusSignal === "short" 
      ? Math.max(...stopLosses) * 1.001 // Add 0.1% buffer above highest stop for shorts
      : Math.min(...stopLosses) * 0.999; // Subtract 0.1% buffer below lowest stop for longs
    
    const stopReason = analyses.find(a => a.stopLossReason && a.signal === consensusSignal)?.stopLossReason;
    
    invalidation = {
      price: parseFloat(stopPrice.toFixed(2)),
      reason: stopReason || `Structural break ${consensusSignal === "short" ? "above" : "below"} agent stop levels`
    };
  }
  
  // Gods Mode: Layer Profit Targets from agent consensus
  if (allTargets.length > 0) {
    const tp1Prices = allTargets.filter(t => t.tp1?.price).map(t => t.tp1!.price).sort((a, b) => a - b);
    const tp2Prices = allTargets.filter(t => t.tp2?.price).map(t => t.tp2!.price).sort((a, b) => a - b);
    const tp3Prices = allTargets.filter(t => t.tp3?.price).map(t => t.tp3!.price).sort((a, b) => a - b);
    
    if (tp1Prices.length > 0 && tp2Prices.length > 0) {
      const medianTp1 = tp1Prices[Math.floor(tp1Prices.length / 2)];
      const medianTp2 = tp2Prices[Math.floor(tp2Prices.length / 2)];
      // SHORTS ONLY - Always use short calculation for TP3
      const medianTp3 = tp3Prices.length > 0 ? tp3Prices[Math.floor(tp3Prices.length / 2)] : medianTp2 * 0.98;
      
      targets = {
        tp1: { price: parseFloat(medianTp1.toFixed(2)), exitPercent: 25, type: "scout" },
        tp2: { price: parseFloat(medianTp2.toFixed(2)), exitPercent: 50, type: "primary" },
        tp3: { price: parseFloat(medianTp3.toFixed(2)), exitPercent: 25, type: "runner" }
      };
      
      // Calculate Risk:Reward ratios
      if (invalidation && killZone) {
        const entry = killZone.optimal;
        const risk = Math.abs(entry - invalidation.price);
        
        riskReward = {
          toTp1: parseFloat((Math.abs(targets.tp1.price - entry) / risk).toFixed(2)),
          toTp2: parseFloat((Math.abs(targets.tp2.price - entry) / risk).toFixed(2)),
          toTp3: parseFloat((Math.abs(targets.tp3.price - entry) / risk).toFixed(2))
        };
      }
    }
  }
  
  // Gods Mode: Verdict determination
  type Verdict = "EXECUTE" | "WAIT" | "NO_TRADE";
  let verdict: Verdict = "NO_TRADE";
  const isKillZoneValid = killZone && killZone.widthPercent <= 0.5;
  const hasGoodRR = riskReward && riskReward.toTp2 >= 2.5;
  
  if (confluenceLevel === "GODLIKE" && isKillZoneValid && hasGoodRR) {
    verdict = "EXECUTE";
  } else if ((confluenceLevel === "ELITE" || confluenceLevel === "STRONG") && isKillZoneValid) {
    verdict = "EXECUTE";
  } else if (confluenceLevel === "MODERATE" && hasGoodRR) {
    verdict = "WAIT";
  }
  
  const isActionable = verdict === "EXECUTE";
  
  // Position size based on confluence
  const positionSizeMap: Record<ConfluenceLevel, number> = {
    "GODLIKE": 100,
    "ELITE": 80,
    "STRONG": 60,
    "MODERATE": 40,
    "WEAK": 0
  };
  
  return {
    symbol,
    totalAgents: analyses.length,
    agreeingAgents,
    consensusSignal,
    confluenceScore: parseFloat(confluenceScore.toFixed(3)),
    confluenceLevel,
    agentAnalyses: analyses,
    // Gods Mode: Kill Zone
    killZone,
    invalidation,
    targets,
    riskReward,
    verdict,
    // Legacy fields for backward compatibility
    entryZoneLow: killZone?.low,
    entryZoneHigh: killZone?.high,
    invalidationLevel: invalidation?.price,
    primaryTarget: targets?.tp2.price,
    secondaryTarget: targets?.tp3.price,
    riskRewardRatio: riskReward?.toTp2,
    positionSizeRecommendation: positionSizeMap[confluenceLevel],
    isActionable,
    timestamp: new Date().toISOString(),
  };
}

// Trinity of Profit: Calculate Pair Score for Ultra-Profitable Selection
export function calculatePairScore(marketData: MarketData): {
  totalScore: number;
  scores: {
    volatility: number;
    volume: number;
    liquidity: number;
    momentum: number;
    fundingBonus: number;
  };
  recommendedStrategy: "WATERFALL" | "DOUBLING" | "SNOWBALL" | "SCALPING";
} {
  const price = marketData.currentPrice;
  const scores = {
    volatility: 0,
    volume: 0,
    liquidity: 0,
    momentum: 0,
    fundingBonus: 0
  };
  
  // 1. Volatility Score (0-25) - Based on price range
  const priceRange = marketData.high24h - marketData.low24h;
  const volatilityPercent = (priceRange / price) * 100;
  if (volatilityPercent > 5) scores.volatility = 25;
  else if (volatilityPercent > 3) scores.volatility = 20;
  else if (volatilityPercent > 2) scores.volatility = 15;
  else if (volatilityPercent > 1) scores.volatility = 10;
  else scores.volatility = 5;
  
  // 2. Volume Score (0-25) - Based on 24h volume
  const volumeB = marketData.volume24h / 1e9;
  if (volumeB > 5) scores.volume = 25;
  else if (volumeB > 2) scores.volume = 20;
  else if (volumeB > 1) scores.volume = 15;
  else if (volumeB > 0.5) scores.volume = 10;
  else scores.volume = 5;
  
  // 3. Liquidity Score (0-25) - Based on spread
  const spreadPercent = (marketData.bidAskSpread || 0.001) * 100;
  if (spreadPercent < 0.005) scores.liquidity = 25;
  else if (spreadPercent < 0.02) scores.liquidity = 20;
  else if (spreadPercent < 0.05) scores.liquidity = 15;
  else if (spreadPercent < 0.1) scores.liquidity = 10;
  else scores.liquidity = 5;
  
  // 4. Momentum Score (0-25) - Based on RSI
  const rsi = marketData.rsi;
  if (rsi > 70 || rsi < 30) scores.momentum = 25; // Strong trend
  else if (rsi > 60 || rsi < 40) scores.momentum = 20;
  else scores.momentum = 15;
  
  // 5. Funding Rate Bonus (0-30) - Huge bonus for shorting with high positive funding
  const fundingPercent = marketData.fundingRate * 100;
  if (fundingPercent > 0.20) scores.fundingBonus = 30;
  else if (fundingPercent > 0.10) scores.fundingBonus = 20;
  else if (fundingPercent > 0.05) scores.fundingBonus = 10;
  else if (fundingPercent < -0.10) scores.fundingBonus = 20; // Bonus for longing with negative funding
  else scores.fundingBonus = 0;
  
  const totalScore = scores.volatility + scores.volume + scores.liquidity + scores.momentum + scores.fundingBonus;
  
  // Trinity of Profit: Strategy Selection Matrix
  let recommendedStrategy: "WATERFALL" | "DOUBLING" | "SNOWBALL" | "SCALPING" = "SCALPING";
  
  if (scores.momentum >= 20 && fundingPercent > 0.15) {
    recommendedStrategy = "WATERFALL"; // Strong trend + high funding = layer into position
  } else if (scores.liquidity >= 25 && spreadPercent < 0.005) {
    recommendedStrategy = "SCALPING"; // Ultra-tight spread = hyper-scalp
  } else if (scores.fundingBonus >= 20) {
    recommendedStrategy = "SNOWBALL"; // High funding = compound small wins
  } else {
    recommendedStrategy = "DOUBLING"; // Default for choppy markets
  }
  
  return { totalScore, scores, recommendedStrategy };
}

// Trinity of Profit: Get Strategy Parameters
export function getStrategyParams(
  strategy: "WATERFALL" | "DOUBLING" | "SNOWBALL" | "SCALPING",
  price: number,
  direction: "long" | "short" | "neutral"
): {
  strategy: "WATERFALL" | "DOUBLING" | "SNOWBALL" | "SCALPING";
  leverage: number;
  entrySize: number;
  riskPercent: number;
  targetPercent: number;
  stopLossPercent: number;
  layers?: number;
  maxDoubles?: number;
  description: string;
} {
  // For neutral signals, return conservative DOUBLING parameters for recovery
  if (direction === "neutral") {
    return {
      strategy: "DOUBLING",
      leverage: 5,
      entrySize: 5,
      riskPercent: 0.1,
      targetPercent: 0.2,
      stopLossPercent: 0.1,
      maxDoubles: 3,
      description: "Conservative mode: Wait for clearer signal direction"
    };
  }
  
  const isShort = direction === "short";
  
  switch (strategy) {
    case "WATERFALL":
      return {
        strategy: "WATERFALL",
        leverage: 20,
        entrySize: 10,
        riskPercent: 0.2,
        targetPercent: 0.5,
        stopLossPercent: 0.2,
        layers: 10,
        description: "Layer into position: 10 entries at 0.1% spacing, tight stops"
      };
    
    case "DOUBLING":
      return {
        strategy: "DOUBLING",
        leverage: 10,
        entrySize: 5,
        riskPercent: 0.15,
        targetPercent: 0.3,
        stopLossPercent: 0.15,
        maxDoubles: 5,
        description: "Recovery mode: Double size after loss, reset after win"
      };
    
    case "SNOWBALL":
      return {
        strategy: "SNOWBALL",
        leverage: 10,
        entrySize: 5,
        riskPercent: 0.1,
        targetPercent: 0.2,
        stopLossPercent: 0.1,
        description: "Compound mode: Roll profits into next trade"
      };
    
    case "SCALPING":
    default:
      return {
        strategy: "SCALPING",
        leverage: 50,
        entrySize: 3,
        riskPercent: 0.075,
        targetPercent: 0.15,
        stopLossPercent: 0.075,
        description: "Hyper-speed: 50x leverage, micro-targets, 60s max hold"
      };
  }
}

export { generateMockMarketData, DEFAULT_AGENTS };
