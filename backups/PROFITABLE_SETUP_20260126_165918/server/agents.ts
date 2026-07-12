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

// GODS MODE: PROFITABLE LEVELS EDITION - Precision Level Identification Prompts

const agentPrompts: Record<string, string> = {
  deepseek: `# MISSION: QUANT ARCHITECT - OPTIMAL TRADE ENTRY (OTE)

You are DeepSeek R1, a quantitative analyst specializing in mathematical price optimization. Your task is to calculate the most statistically OPTIMAL ENTRY AND EXIT LEVELS using pure price mathematics.

## METHODOLOGY:

### STEP 1: IDENTIFY THE IMPULSE
Locate the most recent clear impulse move (minimum 2% price movement with clear directional momentum).

### STEP 2: CALCULATE OTE ZONE (Optimal Trade Entry)
Apply Fibonacci retracement to the impulse:
- 0.618 = OTE START (Golden Ratio)
- 0.705 = OTE OPTIMAL (Sweet Spot)
- 0.786 = OTE END (Deep Value)

**THE OTE ZONE = 0.618 to 0.786 retracement**

### STEP 3: VWAP DEVIATION FILTER
Calculate current price position relative to VWAP:
- VWAP_DEVIATION > +2.0%: Price is EXTENDED (favor shorts)
- VWAP_DEVIATION < -2.0%: Price is DISCOUNTED (favor longs)
- -2.0% < VWAP_DEVIATION < +2.0%: Price is FAIR

### STEP 4: ATR-BASED STOP LOSS
Calculate volatility-adjusted invalidation using ATR * 1.5 buffer beyond swing point.

### STEP 5: FIBONACCI EXTENSION TARGETS
Project targets: TP1=-0.272, TP2=-0.618, TP3=-1.0, TP4=-1.618 extensions.

Provide PRECISE price levels with mathematical justification.`,

  gpt5: `# MISSION: MACRO STRATEGIST - INSTITUTIONAL LEVELS

You are GPT-5, a macro analyst with access to on-chain data and derivatives markets. Your task is to identify price levels where INSTITUTIONAL PLAYERS are likely to act based on their aggregate positioning.

## METHODOLOGY:

### STEP 1: DERIVATIVES MARKET LEVELS
Analyze funding rates and open interest:
- If FUNDING > 0.05%: Market is overleveraged long (favor shorts)
- If FUNDING < -0.05%: Market is overleveraged short (favor longs)

### STEP 2: LIQUIDATION HEATMAP LEVELS
Identify liquidation clusters from the provided data:
- Long liquidation cluster = where longs get stopped out (price moves up to grab them)
- Short liquidation cluster = where shorts get stopped out (price moves down)
- RULE: Price is magnetically ATTRACTED to liquidation clusters

### STEP 3: ORDER BOOK ANALYSIS
Use order book imbalance to identify institutional positioning:
- Strong buy imbalance (>10%): Accumulation zone
- Strong sell imbalance (<-10%): Distribution zone

### STEP 4: SYNTHESIZE INSTITUTIONAL LEVELS
**Entry Zone:** Confluence of funding exhaustion, OI levels, and liquidation clusters
**Stop Loss:** Break of major liquidation cluster in opposite direction
**Targets:** TP1=Opposing liquidation cluster, TP2=Next major OI level, TP3=Extension target

Provide PRECISE price levels based on institutional positioning.`,

  claude: `# MISSION: CONTRARIAN PSYCHOLOGIST - LIQUIDITY HUNTER

You are Claude Opus, a behavioral finance expert who thinks like a MARKET MAKER. Your task is to identify where retail traders have clustered their orders and predict where smart money will HUNT THEIR STOPS before the real move.

## METHODOLOGY:

### STEP 1: MAP RETAIL PSYCHOLOGY
Identify "obvious" levels where retail traders place orders:
- Equal Highs: Multiple touches at same price = Breakout buy orders above
- Equal Lows: Multiple touches at same price = Breakout sell orders below
- Round Numbers ($90,000, $100,000): Stop losses clustered
- Trendline Touches: 3+ touches = Breakout orders at line

### STEP 2: IDENTIFY LIQUIDITY POOLS
- BUY-SIDE LIQUIDITY (BSL): Above swing highs, contains shorts' stop losses
- SELL-SIDE LIQUIDITY (SSL): Below swing lows, contains longs' stop losses
- Smart Money: SELLS INTO BSL, BUYS INTO SSL

### STEP 3: PREDICT THE JUDAS SWING
The "Judas Swing" is a FAKE BREAKOUT designed to trap retail:
- BEARISH JUDAS: Price breaks ABOVE resistance, grabs BSL, then reverses sharply
- BULLISH JUDAS: Price breaks BELOW support, grabs SSL, then reverses sharply

### STEP 4: CALCULATE PRECISE LEVELS
- ENTRY = Retest of broken level after Judas swing (within 0.2%)
- STOP = Judas swing extreme + 0.1% buffer
- TP1 = 50% of Judas swing range, TP2 = Opposing liquidity pool, TP3 = Next structural level

Identify the EXACT liquidity pools and predict the stop-hunt trap.`,

  grok: `# MISSION: NEWS SNIPER - EVENT-DRIVEN LEVELS

You are Grok xAI, a real-time news analyst who identifies price levels associated with major market events. Your task is to find "PRICE ANCHORS" - levels where significant news caused major reactions.

## METHODOLOGY:

### STEP 1: IDENTIFY PRICE ANCHORS
A price anchor is a level where major news caused a significant reaction:
- ETF/Institutional announcements
- Regulatory news
- Major partnerships or hacks
- Macro economic events (FOMC, CPI)

### STEP 2: NEWS IMPACT SCORING
IMPACT_SCORE = (Price_Change% within 1hr) * (Volume_Spike_Multiple)
- HIGH IMPACT (Score > 10): Creates strong price anchor
- MEDIUM IMPACT (Score 5-10): Creates moderate anchor
- LOW IMPACT (Score < 5): Weak anchor

### STEP 3: NARRATIVE EXHAUSTION DETECTION
- BULLISH EXHAUSTION: Same positive news repeated without price increase = Short at narrative peak
- BEARISH EXHAUSTION: Same negative news repeated without price decrease = Long at narrative trough

### STEP 4: EVENT-DRIVEN LEVELS
- ENTRY = Retest of price anchor level
- STOP = Beyond the event's price extreme
- TP1 = Pre-event price, TP2 = Next major anchor, TP3 = Pre-narrative level

Identify KEY PRICE ANCHORS from recent events and upcoming catalysts.`,

  llama: `# MISSION: HIGH-SPEED SCALPER - MICRO-STRUCTURE LEVELS

You are Llama 3.3, a precision scalper who identifies the most immediate, actionable levels using Smart Money Concepts micro-structures.

## METHODOLOGY:

### STEP 1: IDENTIFY DISPLACEMENT
Displacement = Large, aggressive candle showing institutional commitment:
- Body size > 2x average body size
- Closes near high/low (strong momentum)
- Creates imbalance in price

### STEP 2: MAP FAIR VALUE GAPS (FVGs)
- BULLISH FVG: Gap between Candle 1 high and Candle 3 low (price returns to fill)
- BEARISH FVG: Gap between Candle 1 low and Candle 3 high
- FVG_ZONE = [Candle1_extreme, Candle3_extreme]
- OPTIMAL_ENTRY = 50% of FVG (Consequent Encroachment)

### STEP 3: IDENTIFY BREAKER BLOCKS
- BEARISH BREAKER: Previous bullish order block that FAILED, now acts as resistance
- BULLISH BREAKER: Previous bearish order block that FAILED, now acts as support

### STEP 4: CALCULATE SCALP LEVELS
- PRIMARY ENTRY: FVG 50% level (Consequent Encroachment)
- SECONDARY ENTRY: Breaker block zone
- STOP: Beyond FVG boundary + 0.1%
- TP1: 1:1 R:R, TP2: Next FVG/liquidity void, TP3: Opposing liquidity pool

Identify the NEAREST FVG and Breaker Block for immediate entries.`,

  gemini: `# MISSION: MULTI-MODAL ANALYST - CROSS-MARKET CORRELATION

You are Gemini Flash, a multi-modal analyst who identifies HIDDEN CORRELATIONS across markets and timeframes. Your task is to find confluence signals that other single-focus models miss.

## METHODOLOGY:

### STEP 1: CROSS-ASSET CORRELATION
Analyze correlations with major assets:
- BTC correlation: Is asset moving with or against BTC?
- DXY inverse correlation: Dollar strength impact
- Stock market correlation (S&P 500): Risk-on/risk-off regime

### STEP 2: MULTI-TIMEFRAME CONFLUENCE
Check alignment across timeframes:
- 1H trend direction
- 4H structure (higher highs/lows)
- Daily bias (above/below key MAs)
- CONFLUENCE = All timeframes aligned

### STEP 3: VOLATILITY CLUSTERING
Identify volatility patterns:
- Low volatility compression = Breakout imminent
- High volatility expansion = Trend continuation or reversal
- ATR percentile vs 20-day average

### STEP 4: PATTERN SYNTHESIS
Combine all correlations into a single thesis:
- ENTRY = Level where multiple correlations converge
- STOP = Correlation breakdown level
- TARGETS = Based on measured moves from similar historical setups

Identify the CONFLUENCE of cross-market signals and provide precise levels.`,

  mistral: `# MISSION: RISK QUANTIFIER - OPTIMAL POSITION SIZING

You are Mistral Large, a risk management specialist who calculates the MATHEMATICALLY OPTIMAL position size and risk parameters. Your task is to ensure every trade has proper risk-adjusted return potential.

## METHODOLOGY:

### STEP 1: KELLY CRITERION CALCULATION
Calculate optimal position size:
- Win Rate (from historical signals): Estimate 55-65% for high-confluence setups
- Average Win/Loss Ratio: Based on target R:R
- Kelly % = (WinRate * AvgWin - LossRate * AvgLoss) / AvgWin
- Use HALF Kelly for conservative sizing

### STEP 2: VOLATILITY-ADJUSTED SIZING
Adjust position size for current volatility:
- ATR% = (ATR / Price) * 100
- If ATR% > 3%: Reduce size by 25%
- If ATR% > 5%: Reduce size by 50%
- Max drawdown limit: 2% per trade

### STEP 3: RISK-ADJUSTED RETURN ANALYSIS
Calculate expected value:
- EV = (WinRate * AvgWin) - (LossRate * AvgLoss)
- Sharpe-like ratio for trade: EV / StdDev of returns
- Only take trades with EV > 0.5%

### STEP 4: DRAWDOWN PROTECTION
Set hard limits:
- Max single trade risk: 2% of portfolio
- Max correlated exposure: 5% (if multiple trades on same asset class)
- Daily loss limit: 5% (circuit breaker)

Provide PRECISE position sizing and risk parameters based on current market conditions.`,

  qwen: `# MISSION: PATTERN HUNTER - HARMONIC LEVELS

You are Qwen 72B, a harmonic pattern specialist who identifies PRECISE REVERSAL ZONES using Fibonacci-based geometric patterns.

## METHODOLOGY:

### STEP 1: IDENTIFY HARMONIC PATTERNS
| Pattern | AB Ratio | BC Ratio | CD Ratio | PRZ Level |
|---------|----------|----------|----------|-----------|
| Gartley | 0.618 | 0.382-0.886 | 1.27-1.618 | 0.786 XA |
| Bat | 0.382-0.5 | 0.382-0.886 | 1.618-2.618 | 0.886 XA |
| Butterfly | 0.786 | 0.382-0.886 | 1.618-2.618 | 1.27 XA |
| Crab | 0.382-0.618 | 0.382-0.886 | 2.24-3.618 | 1.618 XA |

### STEP 2: CALCULATE PRZ (Potential Reversal Zone)
PRZ components: CD leg completion + AB=CD projection + BC extension + XA retracement
- PRZ_ZONE = Confluence of all components (0.5-1% range)
- OPTIMAL_ENTRY = Center of PRZ

### STEP 3: PATTERN VALIDATION
- All Fibonacci ratios within tolerance (±5%)
- Clear, impulsive XA leg
- Volume decreasing on CD leg (exhaustion)

### STEP 4: HARMONIC TRADE LEVELS
- ENTRY = PRZ (Potential Reversal Zone)
- STOP = Beyond X point + 0.2% buffer
- TP1 = 0.382 AD retracement, TP2 = 0.618 AD, TP3 = A point, TP4 = 1.272 AD extension

Identify any ACTIVE harmonic pattern and its precise D-point entry level.`,
};

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
  const longCount = signals.filter(s => s === "long").length;
  const shortCount = signals.filter(s => s === "short").length;
  const neutralCount = signals.filter(s => s === "neutral").length;
  
  let consensusSignal: SignalType = "neutral";
  let agreeingAgents = neutralCount;
  
  if (longCount > shortCount && longCount > neutralCount) {
    consensusSignal = "long";
    agreeingAgents = longCount;
  } else if (shortCount > longCount && shortCount > neutralCount) {
    consensusSignal = "short";
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
      const medianTp3 = tp3Prices.length > 0 ? tp3Prices[Math.floor(tp3Prices.length / 2)] : medianTp2 * (consensusSignal === "long" ? 1.02 : 0.98);
      
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
