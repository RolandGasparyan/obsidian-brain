// ═══════════════════════════════════════════════════════════════════════════════
// ULTIMATE GODS LEVEL STRATEGY - MAXIMUM POWER EDITION
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// 7 MARKET REGIMES - Advanced Market Classification
// ═══════════════════════════════════════════════════════════════════════════════
export type MarketRegime = 
  | "STRONG_TRENDING_UP" 
  | "TRENDING_UP" 
  | "RANGING" 
  | "TRENDING_DOWN" 
  | "STRONG_TRENDING_DOWN" 
  | "HIGH_VOLATILITY" 
  | "LOW_VOLATILITY";

// ═══════════════════════════════════════════════════════════════════════════════
// 5 TRADING MODES - Edge-based Dynamic Selection
// ═══════════════════════════════════════════════════════════════════════════════
export type TradingMode = "ULTRA_SAFE" | "SAFE" | "NORMAL" | "AGGRESSIVE" | "ULTRA_AGGRESSIVE";

// ═══════════════════════════════════════════════════════════════════════════════
// 6 BALANCE TIERS - Dynamic Scaling Up to 50x Leverage
// ═══════════════════════════════════════════════════════════════════════════════
export interface GodsBalanceTier {
  min: number;
  max: number;
  tradeFrequency: number;
  positionMultiplier: number;
  tierName: string;
  maxLeverage: number;
  atrMultiplier: number;
  riskPerTrade: number;
}

export const GODS_BALANCE_TIERS: GodsBalanceTier[] = [
  { min: 0, max: 100, tradeFrequency: 300, positionMultiplier: 1.0, tierName: "Base", maxLeverage: 10, atrMultiplier: 2.0, riskPerTrade: 0.01 },
  { min: 100, max: 500, tradeFrequency: 180, positionMultiplier: 1.3, tierName: "Growth", maxLeverage: 15, atrMultiplier: 1.8, riskPerTrade: 0.015 },
  { min: 500, max: 2500, tradeFrequency: 120, positionMultiplier: 1.6, tierName: "Accelerated", maxLeverage: 20, atrMultiplier: 1.5, riskPerTrade: 0.02 },
  { min: 2500, max: 10000, tradeFrequency: 90, positionMultiplier: 2.0, tierName: "Elite", maxLeverage: 25, atrMultiplier: 1.3, riskPerTrade: 0.025 },
  { min: 10000, max: 50000, tradeFrequency: 60, positionMultiplier: 2.5, tierName: "Gods", maxLeverage: 30, atrMultiplier: 1.2, riskPerTrade: 0.03 },
  { min: 50000, max: Infinity, tradeFrequency: 30, positionMultiplier: 3.0, tierName: "Titan", maxLeverage: 50, atrMultiplier: 1.0, riskPerTrade: 0.035 }
];

// ═══════════════════════════════════════════════════════════════════════════════
// 5 TRADING MODES CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════
export interface TradingModeConfig {
  minEdge: number;
  leverageMin: number;
  leverageMax: number;
  positionPctMin: number;
  positionPctMax: number;
  atrStopMultiplier: number;
  atrTakeProfitMultiplier: number;
}

export const TRADING_MODE_CONFIG: Record<TradingMode, TradingModeConfig> = {
  ULTRA_AGGRESSIVE: { minEdge: 0.92, leverageMin: 25, leverageMax: 50, positionPctMin: 0.04, positionPctMax: 0.05, atrStopMultiplier: 0.8, atrTakeProfitMultiplier: 3.0 },
  AGGRESSIVE: { minEdge: 0.85, leverageMin: 15, leverageMax: 25, positionPctMin: 0.03, positionPctMax: 0.04, atrStopMultiplier: 1.0, atrTakeProfitMultiplier: 2.5 },
  NORMAL: { minEdge: 0.75, leverageMin: 8, leverageMax: 15, positionPctMin: 0.02, positionPctMax: 0.03, atrStopMultiplier: 1.2, atrTakeProfitMultiplier: 2.0 },
  SAFE: { minEdge: 0.65, leverageMin: 3, leverageMax: 8, positionPctMin: 0.01, positionPctMax: 0.02, atrStopMultiplier: 1.5, atrTakeProfitMultiplier: 1.8 },
  ULTRA_SAFE: { minEdge: 0.60, leverageMin: 2, leverageMax: 3, positionPctMin: 0.005, positionPctMax: 0.01, atrStopMultiplier: 2.0, atrTakeProfitMultiplier: 1.5 }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 15 SECRET STRATEGIES - High-Edge Trading Tactics
// ═══════════════════════════════════════════════════════════════════════════════
export interface SecretStrategy {
  id: string;
  name: string;
  edge: number;
  description: string;
  minConfidence: number;
  regimes: MarketRegime[];
  signals: {
    bullish: string[];
    bearish: string[];
  };
}

export const SECRET_STRATEGIES: Record<string, SecretStrategy> = {
  liquidity_grab: { 
    id: "liquidity_grab",
    name: "Liquidity Grab", 
    edge: 0.90, 
    description: "Breaking through liquidity walls with institutional volume",
    minConfidence: 0.85,
    regimes: ["HIGH_VOLATILITY", "TRENDING_UP", "TRENDING_DOWN"],
    signals: {
      bullish: ["Large bid walls being hit", "Stop hunt recovery below support"],
      bearish: ["Large ask walls being hit", "Stop hunt recovery above resistance"]
    }
  },
  stop_hunt: { 
    id: "stop_hunt",
    name: "Stop Hunt", 
    edge: 0.88, 
    description: "Targeting stop loss clusters for reversal entries",
    minConfidence: 0.80,
    regimes: ["RANGING", "HIGH_VOLATILITY"],
    signals: {
      bullish: ["Price sweeps below previous lows, immediate recovery"],
      bearish: ["Price sweeps above previous highs, immediate rejection"]
    }
  },
  whale_following: { 
    id: "whale_following",
    name: "Whale Following", 
    edge: 0.92, 
    description: "Following institutional whale moves detected in order flow",
    minConfidence: 0.88,
    regimes: ["STRONG_TRENDING_UP", "STRONG_TRENDING_DOWN", "TRENDING_UP", "TRENDING_DOWN"],
    signals: {
      bullish: ["Large buy orders detected", "OI surge with price increase"],
      bearish: ["Large sell orders detected", "OI surge with price decrease"]
    }
  },
  order_flow_imbalance: { 
    id: "order_flow_imbalance",
    name: "Order Flow Imbalance", 
    edge: 0.82, 
    description: "Trading significant order flow pressure imbalances",
    minConfidence: 0.75,
    regimes: ["TRENDING_UP", "TRENDING_DOWN", "HIGH_VOLATILITY"],
    signals: {
      bullish: ["Bid volume > 2x Ask volume", "Aggressive buying absorption"],
      bearish: ["Ask volume > 2x Bid volume", "Aggressive selling absorption"]
    }
  },
  funding_arbitrage: { 
    id: "funding_arbitrage",
    name: "Funding Rate Arbitrage", 
    edge: 0.70, 
    description: "Exploiting extreme funding rate differentials",
    minConfidence: 0.70,
    regimes: ["RANGING", "LOW_VOLATILITY"],
    signals: {
      bullish: ["Funding rate extremely negative (-0.1%+)", "Shorts overextended"],
      bearish: ["Funding rate extremely positive (+0.1%+)", "Longs overextended"]
    }
  },
  volatility_breakout: { 
    id: "volatility_breakout",
    name: "Volatility Breakout", 
    edge: 0.75, 
    description: "Trading volatility expansion from compression zones",
    minConfidence: 0.72,
    regimes: ["LOW_VOLATILITY", "RANGING"],
    signals: {
      bullish: ["Bollinger squeeze breakout up", "ATR expansion with price rise"],
      bearish: ["Bollinger squeeze breakout down", "ATR expansion with price drop"]
    }
  },
  mean_reversion: { 
    id: "mean_reversion",
    name: "Mean Reversion", 
    edge: 0.85, 
    description: "Trading extreme RSI reversals at key levels",
    minConfidence: 0.78,
    regimes: ["RANGING", "HIGH_VOLATILITY"],
    signals: {
      bullish: ["RSI < 20 at support", "Price 3+ ATR below 20 EMA"],
      bearish: ["RSI > 80 at resistance", "Price 3+ ATR above 20 EMA"]
    }
  },
  momentum_surge: { 
    id: "momentum_surge",
    name: "Momentum Surge", 
    edge: 0.75, 
    description: "Riding strong momentum with volume confirmation",
    minConfidence: 0.73,
    regimes: ["STRONG_TRENDING_UP", "STRONG_TRENDING_DOWN", "HIGH_VOLATILITY"],
    signals: {
      bullish: ["ADX > 40 with +DI > -DI", "Volume surge with price breakout"],
      bearish: ["ADX > 40 with -DI > +DI", "Volume surge with price breakdown"]
    }
  },
  smart_money_divergence: { 
    id: "smart_money_divergence",
    name: "Smart Money Divergence", 
    edge: 0.88, 
    description: "Contrarian trading when smart money diverges from retail",
    minConfidence: 0.82,
    regimes: ["TRENDING_UP", "TRENDING_DOWN", "RANGING"],
    signals: {
      bullish: ["Price lower, OI higher (accumulation)", "Funding negative but price stable"],
      bearish: ["Price higher, OI lower (distribution)", "Funding positive but price stalling"]
    }
  },
  accumulation_distribution: { 
    id: "accumulation_distribution",
    name: "Accumulation/Distribution", 
    edge: 0.68, 
    description: "Detecting Wyckoff accumulation/distribution phases",
    minConfidence: 0.68,
    regimes: ["RANGING", "LOW_VOLATILITY"],
    signals: {
      bullish: ["Higher lows with volume increase", "Spring below support recovered"],
      bearish: ["Lower highs with volume increase", "Upthrust above resistance rejected"]
    }
  },
  wyckoff_spring: { 
    id: "wyckoff_spring",
    name: "Wyckoff Spring", 
    edge: 0.85, 
    description: "Trading Wyckoff spring and upthrust patterns",
    minConfidence: 0.80,
    regimes: ["RANGING", "LOW_VOLATILITY"],
    signals: {
      bullish: ["Sharp break below support with instant recovery", "Volume spike on recovery"],
      bearish: ["Sharp break above resistance with instant rejection", "Volume spike on rejection"]
    }
  },
  elliott_wave: { 
    id: "elliott_wave",
    name: "Elliott Wave", 
    edge: 0.72, 
    description: "Trading wave structure completion and extensions",
    minConfidence: 0.70,
    regimes: ["TRENDING_UP", "TRENDING_DOWN", "STRONG_TRENDING_UP", "STRONG_TRENDING_DOWN"],
    signals: {
      bullish: ["Wave 2/4 retracement complete (38.2-61.8%)", "Impulse wave 3/5 starting"],
      bearish: ["Corrective ABC complete", "New impulse down starting"]
    }
  },
  fibonacci_retracement: { 
    id: "fibonacci_retracement",
    name: "Fibonacci Retracement", 
    edge: 0.78, 
    description: "Trading key Fibonacci level bounces",
    minConfidence: 0.75,
    regimes: ["TRENDING_UP", "TRENDING_DOWN", "RANGING"],
    signals: {
      bullish: ["Price at 61.8% or 78.6% retracement with bullish candle"],
      bearish: ["Price at 61.8% or 78.6% retracement with bearish candle"]
    }
  },
  market_structure_break: { 
    id: "market_structure_break",
    name: "Market Structure Break", 
    edge: 0.80, 
    description: "Trading confirmed structure breaks for trend changes",
    minConfidence: 0.77,
    regimes: ["RANGING", "TRENDING_UP", "TRENDING_DOWN"],
    signals: {
      bullish: ["Break above significant swing high", "BOS followed by retest and hold"],
      bearish: ["Break below significant swing low", "BOS followed by retest and rejection"]
    }
  },
  supply_demand_zone: { 
    id: "supply_demand_zone",
    name: "Supply/Demand Zone", 
    edge: 0.72, 
    description: "Trading fresh supply/demand zones with confluence",
    minConfidence: 0.70,
    regimes: ["RANGING", "TRENDING_UP", "TRENDING_DOWN"],
    signals: {
      bullish: ["Price enters fresh demand zone", "Volume absorption at zone"],
      bearish: ["Price enters fresh supply zone", "Rejection candle at zone"]
    }
  }
};

// ═══════════════════════════════════════════════════════════════════════════════
// TECHNICAL INDICATORS INTERFACE
// ═══════════════════════════════════════════════════════════════════════════════
export interface TechnicalIndicators {
  rsi: number;
  macd: number;
  macdSignal: number;
  macdHistogram: number;
  bollingerUpper: number;
  bollingerLower: number;
  bollingerMiddle: number;
  bollingerWidth: number;
  ema9: number;
  ema21: number;
  ema50: number;
  ema200: number;
  atr: number;
  atr14: number;
  adx: number;
  plusDI: number;
  minusDI: number;
  stochasticK: number;
  stochasticD: number;
  volumeRatio: number;
  vwap: number;
  obv: number;
  mfi: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// ORDER BOOK DATA
// ═══════════════════════════════════════════════════════════════════════════════
export interface OrderBookData {
  bidVolume: number;
  askVolume: number;
  bidAskRatio: number;
  largeBidWalls: { price: number; volume: number }[];
  largeAskWalls: { price: number; volume: number }[];
  supportLevels: number[];
  resistanceLevels: number[];
  buyingPressure: number;
  orderBookImbalance: number;
  spreadPercent: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// WHALE DETECTION INTERFACE
// ═══════════════════════════════════════════════════════════════════════════════
export interface WhaleDetection {
  detected: boolean;
  direction: "BUY" | "SELL" | "NEUTRAL";
  confidence: number;
  volumeUSD: number;
  impact: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  signals: string[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// SENTIMENT ANALYSIS INTERFACE
// ═══════════════════════════════════════════════════════════════════════════════
export interface SentimentAnalysis {
  fearGreedIndex: number;
  fundingRate: number;
  openInterest: number;
  openInterestChange24h: number;
  longShortRatio: number;
  socialSentiment: number;
  sentimentScore: number;
  sentimentLabel: "EXTREME_FEAR" | "FEAR" | "NEUTRAL" | "GREED" | "EXTREME_GREED";
}

// ═══════════════════════════════════════════════════════════════════════════════
// EDGE SCORE CALCULATION
// ═══════════════════════════════════════════════════════════════════════════════
export interface EdgeScoreBreakdown {
  technicalScore: number;
  orderBookScore: number;
  sentimentScore: number;
  strategyScore: number;
  whaleScore: number;
  totalEdge: number;
  passesMinimum: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// ATR-BASED RISK MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════
export interface ATRRiskManagement {
  atr: number;
  stopLossDistance: number;
  takeProfitDistance: number;
  positionSize: number;
  riskAmount: number;
  rewardRiskRatio: number;
  stopLossPrice: number;
  takeProfitPrices: number[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// GODS LEVEL STRATEGY CLASS
// ═══════════════════════════════════════════════════════════════════════════════
export class GodsLevelStrategy {
  private static instance: GodsLevelStrategy;
  private MIN_EDGE_THRESHOLD = 0.65; // RECOVERY MODE: More selective (was 0.60)

  private constructor() {}

  static getInstance(): GodsLevelStrategy {
    if (!GodsLevelStrategy.instance) {
      GodsLevelStrategy.instance = new GodsLevelStrategy();
    }
    return GodsLevelStrategy.instance;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // MARKET REGIME DETECTION (7 TYPES)
  // ═══════════════════════════════════════════════════════════════════════════
  detectMarketRegime(indicators: TechnicalIndicators, price: number): MarketRegime {
    const { rsi, adx, plusDI, minusDI, bollingerWidth, ema21, ema50, ema200, atr } = indicators;
    
    const trendStrength = adx;
    const isBullish = plusDI > minusDI && price > ema21;
    const isBearish = minusDI > plusDI && price < ema21;
    const volatilityRatio = bollingerWidth / (atr * 2);

    if (volatilityRatio > 2.5 || bollingerWidth > 0.08) {
      return "HIGH_VOLATILITY";
    }

    if (volatilityRatio < 0.5 || bollingerWidth < 0.02) {
      return "LOW_VOLATILITY";
    }

    if (trendStrength > 40) {
      if (isBullish && price > ema50 && price > ema200) {
        return "STRONG_TRENDING_UP";
      }
      if (isBearish && price < ema50 && price < ema200) {
        return "STRONG_TRENDING_DOWN";
      }
    }

    if (trendStrength > 25) {
      if (isBullish) return "TRENDING_UP";
      if (isBearish) return "TRENDING_DOWN";
    }

    return "RANGING";
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // WHALE DETECTION
  // ═══════════════════════════════════════════════════════════════════════════
  detectWhaleActivity(orderBook: OrderBookData, volume24h: number): WhaleDetection {
    const { orderBookImbalance, largeBidWalls, largeAskWalls, bidAskRatio } = orderBook;
    const signals: string[] = [];
    
    const whaleThreshold = 0.15;
    const detected = Math.abs(orderBookImbalance) > whaleThreshold;
    
    let direction: "BUY" | "SELL" | "NEUTRAL" = "NEUTRAL";
    if (orderBookImbalance > whaleThreshold) direction = "BUY";
    if (orderBookImbalance < -whaleThreshold) direction = "SELL";

    const volumeUSD = Math.abs(orderBookImbalance) * volume24h;
    
    let impact: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" = "LOW";
    if (Math.abs(orderBookImbalance) > 0.40) impact = "CRITICAL";
    else if (Math.abs(orderBookImbalance) > 0.30) impact = "HIGH";
    else if (Math.abs(orderBookImbalance) > 0.20) impact = "MEDIUM";

    if (largeBidWalls.length > 0) signals.push(`${largeBidWalls.length} large bid walls detected`);
    if (largeAskWalls.length > 0) signals.push(`${largeAskWalls.length} large ask walls detected`);
    if (bidAskRatio > 1.5) signals.push("Strong buying pressure");
    if (bidAskRatio < 0.67) signals.push("Strong selling pressure");

    const confidence = Math.min(1.0, Math.abs(orderBookImbalance) * 2.5);

    return { detected, direction, confidence, volumeUSD, impact, signals };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SENTIMENT ANALYSIS
  // ═══════════════════════════════════════════════════════════════════════════
  analyzeSentiment(
    fundingRate: number,
    openInterest: number,
    openInterestChange: number,
    longShortRatio: number
  ): SentimentAnalysis {
    let sentimentScore = 0.5;
    
    if (fundingRate > 0.0005) sentimentScore += 0.1;
    if (fundingRate > 0.001) sentimentScore += 0.1;
    if (fundingRate < -0.0005) sentimentScore -= 0.1;
    if (fundingRate < -0.001) sentimentScore -= 0.1;

    if (openInterestChange > 0.05) sentimentScore += 0.1;
    if (openInterestChange < -0.05) sentimentScore -= 0.1;

    if (longShortRatio > 1.2) sentimentScore += 0.1;
    if (longShortRatio < 0.8) sentimentScore -= 0.1;

    sentimentScore = Math.max(0, Math.min(1, sentimentScore));

    const fearGreedIndex = sentimentScore * 100;
    
    let sentimentLabel: SentimentAnalysis["sentimentLabel"];
    if (fearGreedIndex < 20) sentimentLabel = "EXTREME_FEAR";
    else if (fearGreedIndex < 40) sentimentLabel = "FEAR";
    else if (fearGreedIndex < 60) sentimentLabel = "NEUTRAL";
    else if (fearGreedIndex < 80) sentimentLabel = "GREED";
    else sentimentLabel = "EXTREME_GREED";

    return {
      fearGreedIndex,
      fundingRate,
      openInterest,
      openInterestChange24h: openInterestChange,
      longShortRatio,
      socialSentiment: 0.5,
      sentimentScore,
      sentimentLabel
    };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // MULTI-FACTOR EDGE SCORE CALCULATION
  // ═══════════════════════════════════════════════════════════════════════════
  calculateEdgeScore(
    indicators: TechnicalIndicators,
    orderBook: OrderBookData,
    sentiment: SentimentAnalysis,
    strategy: SecretStrategy,
    whale: WhaleDetection
  ): EdgeScoreBreakdown {
    // Technical Score (30% weight)
    let technicalScore = 0.5;
    
    if (indicators.rsi > 30 && indicators.rsi < 70) technicalScore += 0.1;
    if (indicators.adx > 25) technicalScore += 0.15;
    if (indicators.volumeRatio > 1.2) technicalScore += 0.15;
    if (Math.abs(indicators.macdHistogram) > 0) technicalScore += 0.05;
    if (indicators.mfi > 20 && indicators.mfi < 80) technicalScore += 0.05;
    technicalScore = Math.min(1.0, technicalScore);

    // Order Book Score (30% weight)
    let orderBookScore = 0.5;
    
    if (orderBook.buyingPressure > 0.6 || orderBook.buyingPressure < 0.4) orderBookScore += 0.2;
    if (orderBook.largeBidWalls.length > 0) orderBookScore += 0.1;
    if (orderBook.largeAskWalls.length > 0) orderBookScore += 0.1;
    if (orderBook.spreadPercent < 0.001) orderBookScore += 0.1;
    orderBookScore = Math.min(1.0, orderBookScore);

    // Sentiment Score (20% weight)
    let sentimentScoreVal = sentiment.sentimentScore;
    
    if (sentiment.sentimentLabel === "EXTREME_FEAR" || sentiment.sentimentLabel === "EXTREME_GREED") {
      sentimentScoreVal += 0.2;
    }
    sentimentScoreVal = Math.min(1.0, sentimentScoreVal);

    // Strategy Score (10% weight)
    const strategyScore = strategy.edge;

    // Whale Score (10% weight)
    let whaleScore = 0.5;
    if (whale.detected) {
      whaleScore = whale.confidence;
      if (whale.impact === "CRITICAL") whaleScore = Math.min(1.0, whaleScore + 0.2);
      if (whale.impact === "HIGH") whaleScore = Math.min(1.0, whaleScore + 0.1);
    }

    const totalEdge = (
      technicalScore * 0.30 +
      orderBookScore * 0.30 +
      sentimentScoreVal * 0.20 +
      strategyScore * 0.10 +
      whaleScore * 0.10
    );

    return {
      technicalScore,
      orderBookScore,
      sentimentScore: sentimentScoreVal,
      strategyScore,
      whaleScore,
      totalEdge,
      passesMinimum: totalEdge >= this.MIN_EDGE_THRESHOLD
    };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SELECT TRADING MODE BASED ON EDGE SCORE
  // ═══════════════════════════════════════════════════════════════════════════
  selectTradingMode(edgeScore: number, balance: number): {
    mode: TradingMode;
    config: TradingModeConfig;
    tier: GodsBalanceTier;
  } {
    const tier = GODS_BALANCE_TIERS.find(t => balance >= t.min && balance < t.max) || GODS_BALANCE_TIERS[0];

    let mode: TradingMode;
    if (edgeScore >= TRADING_MODE_CONFIG.ULTRA_AGGRESSIVE.minEdge) {
      mode = "ULTRA_AGGRESSIVE";
    } else if (edgeScore >= TRADING_MODE_CONFIG.AGGRESSIVE.minEdge) {
      mode = "AGGRESSIVE";
    } else if (edgeScore >= TRADING_MODE_CONFIG.NORMAL.minEdge) {
      mode = "NORMAL";
    } else if (edgeScore >= TRADING_MODE_CONFIG.SAFE.minEdge) {
      mode = "SAFE";
    } else {
      mode = "ULTRA_SAFE";
    }

    const leverage = Math.min(
      tier.maxLeverage,
      TRADING_MODE_CONFIG[mode].leverageMax
    );

    return { mode, config: { ...TRADING_MODE_CONFIG[mode], leverageMax: leverage }, tier };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ATR-BASED RISK MANAGEMENT
  // ═══════════════════════════════════════════════════════════════════════════
  calculateATRRisk(
    price: number,
    atr: number,
    balance: number,
    direction: "LONG" | "SHORT",
    modeConfig: TradingModeConfig,
    tier: GodsBalanceTier
  ): ATRRiskManagement {
    const stopMultiplier = modeConfig.atrStopMultiplier * tier.atrMultiplier;
    const tpMultiplier = modeConfig.atrTakeProfitMultiplier;

    const stopLossDistance = atr * stopMultiplier;
    const takeProfitDistance = atr * tpMultiplier;

    const riskPercent = tier.riskPerTrade;
    const riskAmount = balance * riskPercent;

    const positionSize = (riskAmount / stopLossDistance) * price;

    const stopLossPrice = direction === "LONG" 
      ? price - stopLossDistance 
      : price + stopLossDistance;

    const tp1 = direction === "LONG" ? price + (takeProfitDistance * 0.5) : price - (takeProfitDistance * 0.5);
    const tp2 = direction === "LONG" ? price + (takeProfitDistance * 1.0) : price - (takeProfitDistance * 1.0);
    const tp3 = direction === "LONG" ? price + (takeProfitDistance * 1.5) : price - (takeProfitDistance * 1.5);

    const rewardRiskRatio = takeProfitDistance / stopLossDistance;

    return {
      atr,
      stopLossDistance,
      takeProfitDistance,
      positionSize,
      riskAmount,
      rewardRiskRatio,
      stopLossPrice,
      takeProfitPrices: [tp1, tp2, tp3]
    };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SELECT BEST STRATEGY FOR CURRENT REGIME
  // ═══════════════════════════════════════════════════════════════════════════
  selectBestStrategy(regime: MarketRegime, indicators: TechnicalIndicators): SecretStrategy {
    const eligibleStrategies = Object.values(SECRET_STRATEGIES).filter(
      s => s.regimes.includes(regime)
    );

    if (eligibleStrategies.length === 0) {
      return SECRET_STRATEGIES.mean_reversion;
    }

    eligibleStrategies.sort((a, b) => b.edge - a.edge);
    
    if (regime === "HIGH_VOLATILITY" && indicators.adx > 40) {
      return SECRET_STRATEGIES.momentum_surge;
    }
    if (regime === "RANGING" && indicators.rsi < 30) {
      return SECRET_STRATEGIES.mean_reversion;
    }
    if (regime === "RANGING" && indicators.rsi > 70) {
      return SECRET_STRATEGIES.mean_reversion;
    }

    return eligibleStrategies[0];
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // GENERATE TRADING SIGNAL
  // ═══════════════════════════════════════════════════════════════════════════
  generateSignal(
    price: number,
    indicators: TechnicalIndicators,
    orderBook: OrderBookData,
    sentiment: SentimentAnalysis,
    balance: number
  ): {
    shouldTrade: boolean;
    direction: "LONG" | "SHORT" | null;
    strategy: SecretStrategy;
    edgeBreakdown: EdgeScoreBreakdown;
    tradingMode: TradingMode;
    riskManagement: ATRRiskManagement | null;
    regime: MarketRegime;
    whale: WhaleDetection;
    reasoning: string[];
  } {
    const reasoning: string[] = [];

    const regime = this.detectMarketRegime(indicators, price);
    reasoning.push(`Market Regime: ${regime}`);

    const whale = this.detectWhaleActivity(orderBook, 1000000);
    if (whale.detected) {
      reasoning.push(`Whale Activity: ${whale.direction} (${whale.impact} impact)`);
    }

    const strategy = this.selectBestStrategy(regime, indicators);
    reasoning.push(`Selected Strategy: ${strategy.name} (edge: ${(strategy.edge * 100).toFixed(0)}%)`);

    const edgeBreakdown = this.calculateEdgeScore(indicators, orderBook, sentiment, strategy, whale);
    reasoning.push(`Total Edge Score: ${(edgeBreakdown.totalEdge * 100).toFixed(1)}%`);

    if (!edgeBreakdown.passesMinimum) {
      reasoning.push(`Edge below 60% minimum threshold - NO TRADE`);
      return {
        shouldTrade: false,
        direction: null,
        strategy,
        edgeBreakdown,
        tradingMode: "ULTRA_SAFE",
        riskManagement: null,
        regime,
        whale,
        reasoning
      };
    }

    const { mode, config, tier } = this.selectTradingMode(edgeBreakdown.totalEdge, balance);
    reasoning.push(`Trading Mode: ${mode} (Tier: ${tier.tierName})`);

    // ⚠️ SHORTS ONLY MODE - ALWAYS SHORT, NEVER LONG
    let direction: "LONG" | "SHORT" = "SHORT";
    
    // SHORTS ONLY - Always trade SHORT regardless of market regime
    direction = "SHORT";
    reasoning.push(`Direction: SHORT (SHORTS ONLY MODE - Never going long)`);

    // Even whale signals are ignored for SHORTS ONLY
    if (whale.detected && whale.confidence > 0.7) {
      reasoning.push(`Whale detected but SHORTS ONLY mode active - staying SHORT`);
    }

    const riskManagement = this.calculateATRRisk(price, indicators.atr, balance, direction, config, tier);
    reasoning.push(`Risk: $${riskManagement.riskAmount.toFixed(2)} | R:R ${riskManagement.rewardRiskRatio.toFixed(2)}`);

    return {
      shouldTrade: true,
      direction,
      strategy,
      edgeBreakdown,
      tradingMode: mode,
      riskManagement,
      regime,
      whale,
      reasoning
    };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // GET ALL STRATEGIES
  // ═══════════════════════════════════════════════════════════════════════════
  getAllStrategies(): SecretStrategy[] {
    return Object.values(SECRET_STRATEGIES);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // GET STRATEGY BY ID
  // ═══════════════════════════════════════════════════════════════════════════
  getStrategy(id: string): SecretStrategy | undefined {
    return SECRET_STRATEGIES[id];
  }
}

export const godsLevelStrategy = GodsLevelStrategy.getInstance();
