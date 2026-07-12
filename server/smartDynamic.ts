/**
 * 🧠 SMART-DYNAMIC TRADING SYSTEM
 * Intelligent Trader's Protocol with Tier Progression & Ranking
 * 
 * Features:
 * 1. Trading Modes (AGGRESSIVE, NORMAL, SAFE, NO_TRADE)
 * 2. Balance Tiers with Dynamic Scaling
 * 3. Ranking Score & Level System
 * 4. Self-Preservation Protocol
 * 5. Strategy Arsenal
 */

// ============================================
// 💰 BALANCE TIER SYSTEM
// ============================================

export interface BalanceTier {
  min: number;
  max: number;
  tradeFrequency: number; // seconds between trades
  positionSizeMultiplier: number;
  tierName: string;
  description: string;
}

export const BALANCE_TIERS: BalanceTier[] = [
  { min: 0, max: 10000, tradeFrequency: 300, positionSizeMultiplier: 1.0, tierName: "Base", description: "Standard trading frequency" },
  { min: 10001, max: 25000, tradeFrequency: 180, positionSizeMultiplier: 1.2, tierName: "Growth", description: "+20% position size, faster trades" },
  { min: 25001, max: 50000, tradeFrequency: 120, positionSizeMultiplier: 1.4, tierName: "Accelerated", description: "+40% position size, 2-min trades" },
  { min: 50001, max: 100000, tradeFrequency: 90, positionSizeMultiplier: 1.6, tierName: "Elite", description: "+60% position size, 90-sec trades" },
  { min: 100001, max: Infinity, tradeFrequency: 60, positionSizeMultiplier: 2.0, tierName: "Gods", description: "+100% position size, 60-sec trades" },
];

export function getBalanceTier(balance: number): BalanceTier {
  return BALANCE_TIERS.find(tier => balance >= tier.min && balance <= tier.max) || BALANCE_TIERS[0];
}

export function calculateEffectivePositionSize(baseSize: number, balance: number): number {
  const tier = getBalanceTier(balance);
  return baseSize * tier.positionSizeMultiplier;
}

export function getTradeFrequency(balance: number): number {
  const tier = getBalanceTier(balance);
  return tier.tradeFrequency;
}

// ============================================
// 🏆 RANKING & TIER SYSTEM
// ============================================

export interface AIModelStats {
  name: string;
  totalProfit: number;
  startingBalance: number;
  currentBalance: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  maxDrawdown: number;
  dailyPnl: number;
  dailyLossLimit: number;
  isActive: boolean;
  deactivationReason?: string;
}

export interface RankingResult {
  rankingScore: number;
  tier: string;
  level: number;
  breakdown: {
    normalizedPnL: number;
    winRate: number;
    tradeCountFactor: number;
    consistencyFactor: number;
  };
  nextTierAt: number;
  progressToNextTier: number;
}

export function calculateRankingScore(stats: AIModelStats): RankingResult {
  // Normalized P&L (0-100 scale)
  const normalizedPnL = Math.max(0, (stats.totalProfit / stats.startingBalance) * 100);
  
  // Win Rate (0-100 scale)
  const winRate = stats.totalTrades > 0 
    ? (stats.winningTrades / stats.totalTrades) * 100 
    : 0;
  
  // Trade Count Factor (0-100 scale, capped at 100 trades)
  const tradeCountFactor = Math.min(stats.totalTrades / 100, 1) * 100;
  
  // Consistency Factor (0-100 scale)
  const consistencyFactor = stats.totalProfit > 0
    ? Math.max(0, (1 - (stats.maxDrawdown / stats.totalProfit)) * 100)
    : 50; // Default if no profit yet
  
  // Weighted score
  const rankingScore = 
    (normalizedPnL * 0.4) +
    (winRate * 0.3) +
    (tradeCountFactor * 0.2) +
    (consistencyFactor * 0.1);

  const tier = getTierFromScore(rankingScore);
  const level = getLevelFromScore(rankingScore);
  const { nextTierAt, progressToNextTier } = getProgressToNextTier(rankingScore);
  
  return {
    rankingScore: Math.max(0, rankingScore),
    tier,
    level,
    breakdown: {
      normalizedPnL,
      winRate,
      tradeCountFactor,
      consistencyFactor
    },
    nextTierAt,
    progressToNextTier
  };
}

export function getTierFromScore(score: number): string {
  if (score >= 1000) return "Gods Mode";
  if (score >= 751) return "Legend";
  if (score >= 501) return "Master";
  if (score >= 251) return "Expert";
  if (score >= 101) return "Intermediate";
  return "Novice";
}

export function getLevelFromScore(score: number): number {
  return Math.min(Math.floor(score / 10) + 1, 100);
}

function getProgressToNextTier(score: number): { nextTierAt: number; progressToNextTier: number } {
  const tiers = [
    { name: "Novice", min: 0 },
    { name: "Intermediate", min: 101 },
    { name: "Expert", min: 251 },
    { name: "Master", min: 501 },
    { name: "Legend", min: 751 },
    { name: "Gods Mode", min: 1000 }
  ];

  for (let i = 0; i < tiers.length - 1; i++) {
    if (score < tiers[i + 1].min) {
      const nextTierAt = tiers[i + 1].min;
      const tierStart = tiers[i].min;
      const progressToNextTier = ((score - tierStart) / (nextTierAt - tierStart)) * 100;
      return { nextTierAt, progressToNextTier: Math.max(0, Math.min(100, progressToNextTier)) };
    }
  }
  
  return { nextTierAt: 1000, progressToNextTier: 100 };
}

// ============================================
// 🎯 TRADING MODE SYSTEM
// ============================================

export type TradingMode = 'AGGRESSIVE' | 'NORMAL' | 'SAFE' | 'NO_TRADE';

export interface TradingModeConfig {
  mode: TradingMode;
  minConfidence: number;
  maxConfidence: number;
  leverageRange: { min: number; max: number };
  positionSizeRange: { min: number; max: number }; // % of balance
  philosophy: string;
}

export const TRADING_MODES: TradingModeConfig[] = [
  {
    mode: 'AGGRESSIVE',
    minConfidence: 90,
    maxConfidence: 100,
    leverageRange: { min: 15, max: 20 },
    positionSizeRange: { min: 2, max: 3 },
    philosophy: "Near-certainty. Strike with maximum force to maximize profit."
  },
  {
    mode: 'NORMAL',
    minConfidence: 75,
    maxConfidence: 89,
    leverageRange: { min: 5, max: 10 },
    positionSizeRange: { min: 1, max: 2 },
    philosophy: "Odds strongly in favor. Standard, professional trade."
  },
  {
    mode: 'SAFE',
    minConfidence: 50,
    maxConfidence: 74,
    leverageRange: { min: 2, max: 5 },
    positionSizeRange: { min: 0.5, max: 1 },
    philosophy: "Potential opportunity with notable risks. Small, calculated risk."
  },
  {
    mode: 'NO_TRADE',
    minConfidence: 0,
    maxConfidence: 49,
    leverageRange: { min: 0, max: 0 },
    positionSizeRange: { min: 0, max: 0 },
    philosophy: "Uncertainty too high. Wait for better opportunity."
  }
];

export function getTradingMode(confidence: number): TradingModeConfig {
  for (const mode of TRADING_MODES) {
    if (confidence >= mode.minConfidence && confidence <= mode.maxConfidence) {
      return mode;
    }
  }
  return TRADING_MODES[3]; // NO_TRADE
}

// ============================================
// 🛡️ SELF-PRESERVATION PROTOCOL
// ============================================

export interface DailyStats {
  startingBalance: number;
  currentBalance: number;
  dailyPnL: number;
  dailyLossLimitPercent: number;
  dailyLossLimit: number;
  isActive: boolean;
  deactivationReason?: string;
  tradesExecuted: number;
  consecutiveLosses: number;
  maxConsecutiveLosses: number;
}

export class SelfPreservationProtocol {
  private dailyStats: Map<string, DailyStats> = new Map();
  private dailyLossLimitPercent: number = 5; // -5% daily loss limit
  private maxConsecutiveLosses: number = 5;

  initializeAI(aiId: string, startingBalance: number): void {
    const dailyLossLimit = startingBalance * (this.dailyLossLimitPercent / 100);
    
    this.dailyStats.set(aiId, {
      startingBalance,
      currentBalance: startingBalance,
      dailyPnL: 0,
      dailyLossLimitPercent: this.dailyLossLimitPercent,
      dailyLossLimit,
      isActive: true,
      tradesExecuted: 0,
      consecutiveLosses: 0,
      maxConsecutiveLosses: this.maxConsecutiveLosses
    });
  }

  recordTrade(aiId: string, pnl: number, currentBalance: number): {
    isActive: boolean;
    reason?: string;
  } {
    const stats = this.dailyStats.get(aiId);
    if (!stats) {
      this.initializeAI(aiId, currentBalance);
      return { isActive: true };
    }

    stats.dailyPnL += pnl;
    stats.currentBalance = currentBalance;
    stats.tradesExecuted++;

    // Track consecutive losses
    if (pnl < 0) {
      stats.consecutiveLosses++;
    } else {
      stats.consecutiveLosses = 0;
    }

    // Check daily loss limit
    if (stats.dailyPnL <= -stats.dailyLossLimit) {
      stats.isActive = false;
      stats.deactivationReason = `Daily loss limit of -$${stats.dailyLossLimit.toFixed(2)} breached. Current daily P&L: $${stats.dailyPnL.toFixed(2)}`;
      console.log(`🛡️ [SELF-PRESERVATION] ${aiId}: ${stats.deactivationReason}`);
      return { isActive: false, reason: stats.deactivationReason };
    }

    // Check consecutive losses
    if (stats.consecutiveLosses >= stats.maxConsecutiveLosses) {
      stats.isActive = false;
      stats.deactivationReason = `${stats.consecutiveLosses} consecutive losses. Taking a break to reassess.`;
      console.log(`🛡️ [SELF-PRESERVATION] ${aiId}: ${stats.deactivationReason}`);
      return { isActive: false, reason: stats.deactivationReason };
    }

    return { isActive: true };
  }

  canTrade(aiId: string): { canTrade: boolean; reason?: string } {
    const stats = this.dailyStats.get(aiId);
    if (!stats) return { canTrade: true };
    
    if (!stats.isActive) {
      return { canTrade: false, reason: stats.deactivationReason };
    }
    
    return { canTrade: true };
  }

  reactivateAI(aiId: string): void {
    const stats = this.dailyStats.get(aiId);
    if (stats) {
      stats.isActive = true;
      stats.deactivationReason = undefined;
      stats.consecutiveLosses = 0;
      console.log(`✅ [SELF-PRESERVATION] ${aiId} reactivated`);
    }
  }

  resetDaily(): void {
    Array.from(this.dailyStats.entries()).forEach(([aiId, stats]) => {
      stats.dailyPnL = 0;
      stats.tradesExecuted = 0;
      stats.isActive = true;
      stats.deactivationReason = undefined;
      stats.consecutiveLosses = 0;
      stats.dailyLossLimit = stats.currentBalance * (this.dailyLossLimitPercent / 100);
      stats.startingBalance = stats.currentBalance;
    });
    console.log(`🔄 [SELF-PRESERVATION] Daily stats reset for all AIs`);
  }

  getStats(aiId: string): DailyStats | undefined {
    return this.dailyStats.get(aiId);
  }

  getAllStats(): Map<string, DailyStats> {
    return this.dailyStats;
  }
}

// ============================================
// ⚔️ STRATEGY ARSENAL
// ============================================

export interface TradingStrategy {
  id: string;
  name: string;
  whenToUse: string;
  objective: string;
  typicalDuration: string;
  targetProfit: string;
  confidence: number; // base confidence for this strategy
}

export const STRATEGY_ARSENAL: TradingStrategy[] = [
  {
    id: 'SCALPING',
    name: 'Scalping & Liquidity Grabs',
    whenToUse: 'High volatility, tight spreads, strong order book',
    objective: 'Quick profits from micro-movements',
    typicalDuration: '30 seconds - 5 minutes',
    targetProfit: '0.3% - 1%',
    confidence: 75
  },
  {
    id: 'MOMENTUM',
    name: 'Momentum & Trend Following',
    whenToUse: 'Clear trend established, increasing volume',
    objective: 'Ride the wave of market momentum',
    typicalDuration: '15 minutes - 2 hours',
    targetProfit: '2% - 5%',
    confidence: 80
  },
  {
    id: 'BREAKOUT',
    name: 'Breakout & Volatility Expansion',
    whenToUse: 'Price consolidation, Bollinger Bands squeezing',
    objective: 'Capture explosive breakout moves',
    typicalDuration: '5 minutes - 1 hour',
    targetProfit: '3% - 8%',
    confidence: 70
  },
  {
    id: 'MEAN_REVERSION',
    name: 'Mean Reversion & Swing Failures',
    whenToUse: 'Extreme RSI, price deviation from moving averages',
    objective: 'Profit from price returning to mean',
    typicalDuration: '30 minutes - 4 hours',
    targetProfit: '1.5% - 4%',
    confidence: 72
  },
  {
    id: 'ORDER_FLOW',
    name: 'Order Flow & Whale Tracking',
    whenToUse: 'Large order book imbalances, whale activity detected',
    objective: 'Front-run large market participants',
    typicalDuration: 'Real-time - 30 minutes',
    targetProfit: '1% - 5%',
    confidence: 85
  },
  {
    id: 'FUNDING_ARBITRAGE',
    name: 'Funding Rate Arbitrage',
    whenToUse: 'Extreme funding rates (>0.1% or <-0.1%)',
    objective: 'Collect funding fees while hedging',
    typicalDuration: '8 hours (funding interval)',
    targetProfit: 'Funding rate + spread',
    confidence: 90
  },
  {
    id: 'NEWS_EVENT',
    name: 'News & Event Trading',
    whenToUse: 'Major announcements, economic data releases',
    objective: 'Capitalize on market reactions',
    typicalDuration: 'Instant - 1 hour',
    targetProfit: '2% - 10%',
    confidence: 65
  }
];

export function selectBestStrategy(marketConditions: {
  volatility: number;
  trendStrength: number;
  orderBookImbalance: number;
  fundingRate: number;
  rsi: number;
}): TradingStrategy {
  const { volatility, trendStrength, orderBookImbalance, fundingRate, rsi } = marketConditions;

  // Funding arbitrage if extreme
  if (Math.abs(fundingRate) > 0.001) {
    return STRATEGY_ARSENAL.find(s => s.id === 'FUNDING_ARBITRAGE')!;
  }

  // Order flow if whale activity
  if (Math.abs(orderBookImbalance) > 1.5) {
    return STRATEGY_ARSENAL.find(s => s.id === 'ORDER_FLOW')!;
  }

  // Mean reversion if extreme RSI
  if (rsi < 25 || rsi > 75) {
    return STRATEGY_ARSENAL.find(s => s.id === 'MEAN_REVERSION')!;
  }

  // Momentum if strong trend
  if (trendStrength > 40) {
    return STRATEGY_ARSENAL.find(s => s.id === 'MOMENTUM')!;
  }

  // Breakout if low volatility (squeeze)
  if (volatility < 0.02) {
    return STRATEGY_ARSENAL.find(s => s.id === 'BREAKOUT')!;
  }

  // Default to scalping
  return STRATEGY_ARSENAL.find(s => s.id === 'SCALPING')!;
}

// ============================================
// 🧠 SMART-DYNAMIC ORCHESTRATOR
// ============================================

export interface TradeSignal {
  status: 'ACTIVE' | 'PASSIVE' | 'DEACTIVATED_LOSS_LIMIT';
  trade_signal?: {
    selected_asset: string;
    market_type: string;
    strategy: string;
    confidence: number;
    selected_mode: TradingMode;
    direction: 'SHORT'; // SHORTS ONLY
    entry_price: number;
    stop_loss: number;
    take_profit: number[];
    leverage: number;
    position_size_usd: number;
    reasoning: string;
  };
  reasoning?: string;
}

export class SmartDynamicOrchestrator {
  private selfPreservation: SelfPreservationProtocol;
  private aiStats: Map<string, AIModelStats> = new Map();

  constructor() {
    this.selfPreservation = new SelfPreservationProtocol();
  }

  initializeAI(aiId: string, startingBalance: number): void {
    this.selfPreservation.initializeAI(aiId, startingBalance);
    
    this.aiStats.set(aiId, {
      name: aiId,
      totalProfit: 0,
      startingBalance,
      currentBalance: startingBalance,
      totalTrades: 0,
      winningTrades: 0,
      losingTrades: 0,
      maxDrawdown: 0,
      dailyPnl: 0,
      dailyLossLimit: startingBalance * 0.05,
      isActive: true
    });
  }

  recordTradeResult(aiId: string, pnl: number, currentBalance: number): void {
    const stats = this.aiStats.get(aiId);
    if (!stats) return;

    stats.totalProfit += pnl;
    stats.currentBalance = currentBalance;
    stats.totalTrades++;
    stats.dailyPnl += pnl;

    if (pnl > 0) {
      stats.winningTrades++;
    } else {
      stats.losingTrades++;
    }

    // Track max drawdown
    const drawdown = stats.startingBalance - currentBalance;
    if (drawdown > stats.maxDrawdown) {
      stats.maxDrawdown = drawdown;
    }

    // Self-preservation check
    const result = this.selfPreservation.recordTrade(aiId, pnl, currentBalance);
    stats.isActive = result.isActive;
  }

  generateSignal(
    aiId: string,
    asset: string,
    price: number,
    confidence: number,
    marketConditions: {
      volatility: number;
      trendStrength: number;
      orderBookImbalance: number;
      fundingRate: number;
      rsi: number;
    }
  ): TradeSignal {
    // Check if AI can trade
    const canTradeResult = this.selfPreservation.canTrade(aiId);
    if (!canTradeResult.canTrade) {
      return {
        status: 'DEACTIVATED_LOSS_LIMIT',
        reasoning: canTradeResult.reason
      };
    }

    // Get AI stats
    const stats = this.aiStats.get(aiId);
    if (!stats) {
      this.initializeAI(aiId, 692); // Default balance
    }

    // Get trading mode based on confidence
    const tradingMode = getTradingMode(confidence);

    if (tradingMode.mode === 'NO_TRADE') {
      return {
        status: 'PASSIVE',
        reasoning: `Confidence ${confidence}% below threshold. ${tradingMode.philosophy}`
      };
    }

    // Select strategy
    const strategy = selectBestStrategy(marketConditions);

    // Get balance tier for scaling
    const balanceTier = getBalanceTier(stats?.currentBalance || 692);
    
    // Calculate position size
    const basePositionPercent = (tradingMode.positionSizeRange.min + tradingMode.positionSizeRange.max) / 2;
    const effectivePositionPercent = basePositionPercent * balanceTier.positionSizeMultiplier;
    const positionSizeUsd = (stats?.currentBalance || 692) * (effectivePositionPercent / 100);

    // Calculate leverage (scale based on confidence)
    const leverageRange = tradingMode.leverageRange.max - tradingMode.leverageRange.min;
    const confidenceScale = (confidence - tradingMode.minConfidence) / (tradingMode.maxConfidence - tradingMode.minConfidence);
    const leverage = Math.round(tradingMode.leverageRange.min + leverageRange * confidenceScale);

    // Calculate stop loss and take profits
    const stopLossPercent = 0.01 + (1 - confidence / 100) * 0.02; // 1-3% based on confidence
    const takeProfitMultiplier = 2.5; // 2.5:1 R:R minimum

    const stopLoss = price * (1 + stopLossPercent); // For SHORT
    const tp1 = price * (1 - stopLossPercent * takeProfitMultiplier * 0.4);
    const tp2 = price * (1 - stopLossPercent * takeProfitMultiplier * 0.7);
    const tp3 = price * (1 - stopLossPercent * takeProfitMultiplier * 1.0);

    // Get ranking for reasoning
    const ranking = stats ? calculateRankingScore(stats) : null;

    return {
      status: 'ACTIVE',
      trade_signal: {
        selected_asset: asset,
        market_type: 'futures',
        strategy: strategy.name,
        confidence,
        selected_mode: tradingMode.mode,
        direction: 'SHORT',
        entry_price: price,
        stop_loss: stopLoss,
        take_profit: [tp1, tp2, tp3],
        leverage,
        position_size_usd: positionSizeUsd,
        reasoning: `${asset} showing ${strategy.whenToUse}. Confidence: ${confidence}%. ` +
          `${tradingMode.philosophy} Balance tier: ${balanceTier.tierName} (+${((balanceTier.positionSizeMultiplier - 1) * 100).toFixed(0)}% size). ` +
          `Strategy: ${strategy.name}. Target: ${strategy.targetProfit}. ` +
          (ranking ? `Current tier: ${ranking.tier} (Level ${ranking.level}, Score: ${ranking.rankingScore.toFixed(1)}).` : '')
      }
    };
  }

  getRanking(aiId: string): RankingResult | null {
    const stats = this.aiStats.get(aiId);
    if (!stats) return null;
    return calculateRankingScore(stats);
  }

  getLeaderboard(): Array<{ aiId: string; stats: AIModelStats; ranking: RankingResult }> {
    const leaderboard: Array<{ aiId: string; stats: AIModelStats; ranking: RankingResult }> = [];
    
    Array.from(this.aiStats.entries()).forEach(([aiId, stats]) => {
      const ranking = calculateRankingScore(stats);
      leaderboard.push({ aiId, stats, ranking });
    });

    return leaderboard.sort((a, b) => b.ranking.rankingScore - a.ranking.rankingScore);
  }

  getSelfPreservationStats(aiId: string): DailyStats | undefined {
    return this.selfPreservation.getStats(aiId);
  }

  resetDaily(): void {
    this.selfPreservation.resetDaily();
    
    // Reset daily stats for all AIs
    Array.from(this.aiStats.entries()).forEach(([aiId, stats]) => {
      stats.dailyPnl = 0;
      stats.isActive = true;
    });
  }

  reactivateAI(aiId: string): void {
    this.selfPreservation.reactivateAI(aiId);
    const stats = this.aiStats.get(aiId);
    if (stats) {
      stats.isActive = true;
    }
  }
}

// Export singleton
export const smartDynamic = new SmartDynamicOrchestrator();

// Initialize 8 AI GODS
const AI_GODS = [
  'DeepSeek_R1',
  'GPT_5',
  'Claude_Opus', 
  'Llama_3_3',
  'Gemini_Flash',
  'Mistral_Large',
  'Qwen_72B',
  'Grok_xAI'
];

AI_GODS.forEach(ai => smartDynamic.initializeAI(ai, 86.5)); // $692 / 8 = $86.50 each
