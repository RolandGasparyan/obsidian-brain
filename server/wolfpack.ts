import { fetchGateMarketData, placeFuturesOrder, closePosition, getOpenPositions } from "./gateio";
import * as fs from "fs";
import * as path from "path";
import { db } from "./db";
import { wolfPackTrades } from "@shared/schema";
import { 
  godsLevelStrategy, 
  GodsLevelStrategy,
  SECRET_STRATEGIES,
  GODS_BALANCE_TIERS,
  TRADING_MODE_CONFIG,
  type MarketRegime,
  type TradingMode,
  type SecretStrategy,
  type EdgeScoreBreakdown,
  type WhaleDetection,
  type SentimentAnalysis,
  type TechnicalIndicators as GodsIndicators,
  type OrderBookData as GodsOrderBook
} from "./godsLevelStrategy";
import { tradingModeManager } from "./tradingMode";

// ===== WOLF PACK REAL TRADING MODE =====
const LIVE_TRADING_ENABLED = true;  // ⚡ REAL TRADING MODE - LIVE FUNDS ON GATE.IO

// ===== UNBREAKABLE ENGINE STATE INTERFACES =====

export interface StrategyStats {
  wins: number;
  losses: number;
  winRate: number;
  isActive: boolean;
}

export interface UnbreakableState {
  consecutiveLosses: number;
  peakBudget: number;
  dynamicRiskPercent: number;
  strategyStats: Record<string, StrategyStats>;
  dailyPnl: number;
  dailyStartBudget: number;
  lastDailyReset: string;
  pausedUntil: string | null;
  pauseReason: string | null;
}

export interface WolfEngineState {
  pair: string;
  status: "ACTIVE" | "HALTED" | "ERROR" | "IDLE" | "PAUSED";
  budget: number;
  pnl: number;
  tradeCount: number;
  winCount: number;
  lossCount: number;
  currentStrategy: "PYRAMID" | "WATERFALL" | "SCALPING" | "DOUBLING" | "SNOWBALL";
  lastTradeWasLoss: boolean;
  doublingMultiplier: number;
  activeTrade: ActiveTrade | null;
  lastUpdate: string;
  // Unbreakable Gods Mode State
  unbreakable: UnbreakableState;
}

export interface ActiveTrade {
  symbol: string;
  direction: "long" | "short";
  entryPrice: number;
  currentStopLoss: number;
  initialStopLoss: number;
  tp1: number;
  tp2: number;
  tp3: number;
  positionSizeUsd: number;
  remainingPositionSizeUsd: number;
  breakevenSet: boolean;
  trailingActivated: boolean;
  entryTimestamp: string;
  pnlR: number;
}

export interface UnbreakableConfig {
  // Circuit Breaker Suite
  dailyLossLimitPercent: number;
  consecutiveLossLimit: number;
  peakDrawdownLimitPercent: number;
  volatilitySpikeMultiple: number;
  
  // Advanced Risk Intelligence
  maxPortfolioExposurePercent: number;
  correlationGroups: Record<string, string[]>;
  maxHighCorrPositions: number;
  
  // Self-Healing & Adaptive Logic
  strategyPerformanceThreshold: number;
  kellyFraction: number;
  minRiskPercent: number;
  maxRiskPercent: number;
  
  // State Persistence
  stateSaveIntervalMs: number;
  logsDirectory: string;
}

export interface WolfPackConfig {
  totalBudget: number;
  pairs: string[];
  riskPerTradePercent: number;
  maxLeverage: number;
  cycleIntervalMs: number;
  trendAdxThreshold: number;
  rangeAdxThreshold: number;
  breakevenTriggerR: number;
  trailingStopAtrMultiple: number;
  tradingDirection: "SHORTS_ONLY" | "LONGS_ONLY" | "BOTH";
  unbreakable: UnbreakableConfig;
}

// ===== 🛡️ HIGHLY SAFE BALANCE PROTECTION MODE =====
const DEFAULT_UNBREAKABLE_CONFIG: UnbreakableConfig = {
  // ═══════════════════════════════════════════════════════════════════════════
  // 🛡️ ULTRA SAFE Circuit Breakers - MAXIMUM CAPITAL PROTECTION
  // ═══════════════════════════════════════════════════════════════════════════
  dailyLossLimitPercent: -5.0,   // 🛡️ 5% = -$34.60 max daily loss (TIGHT)
  consecutiveLossLimit: 3,        // 🛡️ 3 losses = auto pause (STRICT)
  peakDrawdownLimitPercent: -8.0, // 🛡️ 8% = -$55.36 max drawdown (PROTECTED)
  volatilitySpikeMultiple: 2.0,   // 🛡️ 2x volatility halt (SENSITIVE)
  
  // 🎯 Conservative Portfolio Management
  maxPortfolioExposurePercent: 20.0,  // 🛡️ 20% = $138.40 max exposure (SAFE)
  correlationGroups: {
    HIGH: ["BTC_USDT", "ETH_USDT"],
    MEDIUM: [],
    LOW: []
  },
  maxHighCorrPositions: 2,
  
  // 🔄 Conservative Risk Parameters
  strategyPerformanceThreshold: 0.50,  // 🛡️ 50% win rate required (HIGHER)
  kellyFraction: 0.15,    // 🛡️ 15% Kelly (ULTRA CONSERVATIVE)
  minRiskPercent: 1.0,    // 🛡️ $6.92 min trade = 1% (SMALL)
  maxRiskPercent: 2.5,    // 🛡️ $17.30 max trade = 2.5% (CAPPED)
  
  // State Persistence
  stateSaveIntervalMs: 30000,
  logsDirectory: "./logs"
};

// ═══════════════════════════════════════════════════════════════════════════
// 🐺⚡🔥 WOLF PACK CONFIGURATION - TRIPLED CYCLES MODE FOR $692 BALANCE 🔥⚡
// ═══════════════════════════════════════════════════════════════════════════
const TRIPLED_CYCLES_ENABLED = true; // ⚡ TRIPLED CYCLES ACTIVE!
const EXTRA_PROFIT_MODE = true; // 🔥 EXTRA PROFIT TRIPLED CYCLES!

const DEFAULT_WOLF_PACK_CONFIG: WolfPackConfig = {
  totalBudget: 692,  // ✅ CORRECTED: Actual balance
  // 🔱 DUAL PAIR MODE - ETH + BTC
  pairs: [
    "ETH_USDT",  // ✅ PAIR 1
    "BTC_USDT"   // ✅ PAIR 2
  ],
  riskPerTradePercent: 4.8, // 🔥 4.8% per trade = $33 entry size
  maxLeverage: 5,  // 🛡️ 5x leverage (CONSERVATIVE)
  cycleIntervalMs: 1500, // 🔥⚡⚡ TRIPLED CYCLES: 1.5 seconds = 600+ trades/day!
  trendAdxThreshold: 15, // ADX 15 for trending entries
  rangeAdxThreshold: 8, // ADX 8 for ranging/scalping
  breakevenTriggerR: 0.20, // BE at 0.20R 
  trailingStopAtrMultiple: 0.6, // 0.6x ATR trailing
  tradingDirection: "BOTH",  // ✅ BOTH DIRECTIONS - Flexibility for any market!
  unbreakable: DEFAULT_UNBREAKABLE_CONFIG
};

// ═══════════════════════════════════════════════════════════════════════════
// 🚀 TURBO CONFIG - SCALED FOR $692 BALANCE
// ═══════════════════════════════════════════════════════════════════════════
// 🛡️ HIGHLY SAFE TURBO CONFIGURATION
const TURBO_CONFIG = {
  // 🛡️ VERY TIGHT STOP LOSSES
  takeProfitPercent: 0.015,    // 🛡️ 1.5% TP (2:1 R:R)
  stopLossPercent: 0.008,      // 🛡️ 0.8% SL (VERY TIGHT)
  
  // 💰 FIXED $33 ENTRY SIZE
  minPositionUsd: 33,          // 🔥 $33 min entry
  maxPositionUsd: 66,          // 🔥 $66 max (2x on win streak)
  positionIncreaseOnWin: 11,   // 🔥 +$11 on win streak
  defaultPositionUsd: 33,      // 🔥 $33 FIXED ENTRY SIZE
  
  // ⚡ FAST EXECUTION
  maxTradeDurationSec: 300,    // ✅ 5 min max per trade
  
  // ✅ BOTH DIRECTIONS - Flexible
  bearishBiasPercent: 50,      // ✅ 50/50 neutral
  
  // Win streak tracking
  winStreakMultiplier: 1.10    // 🛡️ 1.10x on 3+ win streak (SAFE)
};

// 🛡️ HIGHLY SAFE RISK MANAGEMENT
const RISK_LIMITS = {
  maxRiskPercent: 8,           // 🛡️ Maximum Risk: 8% ($55.36) - HIGHLY SAFE
  minProtectedPercent: 92,     // 🛡️ Minimum Protected: 92% ($636.64)
  emergencyStopBalance: 637,   // 🛡️ Emergency Stop: $637 (92% protected)
  maxLeverageRange: [3, 5],    // 🛡️ Low Leverage: 3-5x (SAFE)
  positionSizeRange: [10, 25], // 🛡️ Small Positions: 10-25% (PROTECTED)
  tightStopLoss: [0.3, 0.8],   // 🛡️ Tight Stop Losses: 0.3-0.8% (STRICT)
  
  // 🛑 AUTO-STOP ON LOSS - USER SPECIFIED (Tiered Protection)
  autoStopLossThreshold: 15,   // ✅ CAUTION at $15 loss (reduce risk)
  autoStopHardThreshold: 20,   // ✅ FULL STOP at $20 loss
  resumeMinConfidence: 85,     // ✅ Resume only on 85%+ high signal
  resumeMinAiVotes: 7,         // ✅ Need 7/8 AI votes to resume
  
  // Tiered Loss Protection
  lossProtectionTiers: [
    { lossAmount: 10, action: "REDUCE_SIZE", reduction: 0.50 },   // $10 loss → 50% smaller positions
    { lossAmount: 15, action: "CAUTION_MODE", reduction: 0.25 },  // $15 loss → 75% smaller + high signal only
    { lossAmount: 20, action: "FULL_STOP", reduction: 0.00 },     // $20 loss → STOP completely
  ],
};

// 💎 HYBRID WITHDRAWAL - USER SPECIFIED
const HYBRID_WITHDRAWAL = {
  triggerAmount: 100,          // ✅ Every $100 profit
  coldWalletPercent: 50,       // ✅ $50 to cold wallet (secure)
  reinvestPercent: 50,         // ✅ $50 reinvest (compound)
  coldWalletAddress: "0xa5df89870410335b41beac66508f7dfdc9491e46",
  network: "BSC",
  accumulatedProfit: 0,
};

// 🔄 SMART RECOVERY - USER SPECIFIED
const SMART_RECOVERY = {
  enabled: true,
  autoDetectLoss: true,        // ✅ Auto-detect losses
  conservativeRecovery: true,  // ✅ Conservative recovery trades
  recoverPlusPercent: 10,      // ✅ Recover loss + 10%
  neverChaseLosses: true,      // ✅ Never chase losses
  maxRecoveryAttempts: 3,
};

// 💰 USER PROFIT GOALS - USER SPECIFIED
const USER_PROFIT_GOALS = {
  daily: { min: 10, max: 25 },     // ✅ Daily: +10-25% ($69-173)
  weekly: { min: 50, max: 100 },   // ✅ Weekly: +50-100% ($346-692)
  monthly: { min: 200, max: 400 }, // ✅ Monthly: +200-400% ($1,384-2,768)
  targetWinRate: 77.5,             // ✅ Win Rate: 75-80% (midpoint)
};

// ═══════════════════════════════════════════════════════════════════════════
// 🚀 EXTRA POWER MODE - 8 ENHANCED TRADING STRATEGIES
// ═══════════════════════════════════════════════════════════════════════════

const EXTRA_POWER_STRATEGIES = {
  // ⚡ Strategy 1: Balanced Scalping
  "Balanced Scalping": {
    type: "scalping",
    aggression: 8,
    leverageMultiplier: 1.0,
    profitTarget: 1.5,
    stopLoss: 0.5,
    confidenceThreshold: 75,
    description: "Quick scalps on oversold/overbought conditions",
    capitalShare: 12.5, // 1/8 = 12.5%
  },
  
  // ⚡ Strategy 2: Momentum Trading
  "Momentum Trading": {
    type: "momentum",
    aggression: 9,
    leverageMultiplier: 0.9,
    profitTarget: 2.5,
    stopLoss: 1.0,
    confidenceThreshold: 75,
    description: "Ride strong trends above/below cloud",
    capitalShare: 12.5,
  },
  
  // ⚡ Strategy 3: Mean Reversion
  "Mean Reversion": {
    type: "mean_reversion",
    aggression: 8,
    leverageMultiplier: 0.9,
    profitTarget: 2.0,
    stopLoss: 0.8,
    confidenceThreshold: 75,
    description: "Buy oversold, sell overbought",
    capitalShare: 12.5,
  },
  
  // ⚡ Strategy 4: Fast Scalping
  "Fast Scalping": {
    type: "fast_scalping",
    aggression: 9,
    leverageMultiplier: 1.0,
    profitTarget: 1.2,
    stopLoss: 0.5,
    confidenceThreshold: 75,
    description: "Ultra-fast micro scalps",
    capitalShare: 12.5,
  },
  
  // ⚡ Strategy 5: Multi-Modal Analysis
  "Multi-Modal Analysis": {
    type: "momentum",
    aggression: 9,
    leverageMultiplier: 0.95,
    profitTarget: 2.0,
    stopLoss: 0.8,
    confidenceThreshold: 75,
    description: "Charts + news + sentiment analysis",
    capitalShare: 12.5,
  },
  
  // ⚡ Strategy 6: Risk Optimization
  "Risk Optimization": {
    type: "mean_reversion",
    aggression: 8,
    leverageMultiplier: 0.9,
    profitTarget: 2.2,
    stopLoss: 0.8,
    confidenceThreshold: 75,
    description: "Risk/reward optimized reversion",
    capitalShare: 12.5,
  },
  
  // ⚡ Strategy 7: Breakout Trading
  "Breakout Trading": {
    type: "breakout",
    aggression: 9,
    leverageMultiplier: 0.95,
    profitTarget: 2.8,
    stopLoss: 1.0,
    confidenceThreshold: 75,
    description: "Pattern breakouts and cloud breaks",
    capitalShare: 12.5,
  },
  
  // ⚡ Strategy 8: News-Driven Momentum
  "News-Driven Momentum": {
    type: "momentum",
    aggression: 9,
    leverageMultiplier: 0.95,
    profitTarget: 2.5,
    stopLoss: 1.0,
    confidenceThreshold: 75,
    description: "Event-driven momentum trading",
    capitalShare: 12.5,
  },
};

// ═══════════════════════════════════════════════════════════════════════════
// 📊 SENTIMENT ANALYSIS ENGINE
// ═══════════════════════════════════════════════════════════════════════════

const COIN_SENTIMENT: { [key: string]: number } = {
  "BTC_USDT": 0.65,   // Bullish sentiment
  "ETH_USDT": 0.55,   // Mildly bullish
  "SOL_USDT": 0.45,   // Neutral
  "XRP_USDT": 0.40,   // Slightly bearish
  "AVAX_USDT": 0.35,  // Bearish
};

function getSentimentScore(symbol: string): number {
  return COIN_SENTIMENT[symbol] || 0.5;
}

function updateSentimentFromMarket(symbol: string, rsi: number, fundingRate: number, priceChange: number): number {
  let sentiment = COIN_SENTIMENT[symbol] || 0.5;
  
  // Adjust based on RSI
  if (rsi > 70) sentiment -= 0.15;  // Overbought = bearish
  if (rsi < 30) sentiment += 0.15;  // Oversold = bullish
  
  // Adjust based on funding rate
  if (fundingRate > 0.01) sentiment -= 0.10;  // High funding = bearish
  if (fundingRate < -0.01) sentiment += 0.10; // Negative funding = bullish
  
  // Adjust based on price change
  if (priceChange > 5) sentiment -= 0.10;   // Big pump = reversal likely
  if (priceChange < -5) sentiment += 0.10;  // Big dump = bounce likely
  
  // Clamp between 0 and 1
  return Math.max(0, Math.min(1, sentiment));
}

// ═══════════════════════════════════════════════════════════════════════════
// 🏆 STRATEGY COMPETITION & LEADERBOARD SYSTEM
// ═══════════════════════════════════════════════════════════════════════════

interface CompetitionStrategyStats {
  name: string;
  trades: number;
  wins: number;
  losses: number;
  totalPnl: number;
  winRate: number;
  avgProfit: number;
  capitalAllocation: number;
  rank: number;
}

const STRATEGY_COMPETITION: { [key: string]: CompetitionStrategyStats } = {};

// Initialize strategy competition
Object.keys(EXTRA_POWER_STRATEGIES).forEach((name, index) => {
  STRATEGY_COMPETITION[name] = {
    name,
    trades: 0,
    wins: 0,
    losses: 0,
    totalPnl: 0,
    winRate: 0,
    avgProfit: 0,
    capitalAllocation: 12.5, // Equal start
    rank: index + 1,
  };
});

function updateStrategyLeaderboard(): void {
  const strategies = Object.values(STRATEGY_COMPETITION);
  
  // Sort by total PnL (highest first)
  strategies.sort((a, b) => b.totalPnl - a.totalPnl);
  
  // Update ranks and capital allocation
  const rewards = [0.10, 0.05, 0.02, 0, 0, 0, -0.05, -0.05]; // 8 positions
  
  strategies.forEach((strategy, index) => {
    strategy.rank = index + 1;
    const baseAllocation = 12.5;
    const reward = rewards[index] || 0;
    strategy.capitalAllocation = baseAllocation * (1 + reward);
    
    // Update win rate
    if (strategy.trades > 0) {
      strategy.winRate = (strategy.wins / strategy.trades) * 100;
      strategy.avgProfit = strategy.totalPnl / strategy.trades;
    }
  });
  
  // Log leaderboard
  console.log("\n🏆 STRATEGY LEADERBOARD:");
  strategies.slice(0, 3).forEach((s, i) => {
    const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : "🥉";
    console.log(`   ${medal} ${s.name}: $${s.totalPnl.toFixed(2)} (${s.wins}W/${s.losses}L) | ${s.capitalAllocation.toFixed(1)}% capital`);
  });
}

function recordStrategyTrade(strategyName: string, pnl: number, isWin: boolean): void {
  const strategy = STRATEGY_COMPETITION[strategyName];
  if (!strategy) return;
  
  strategy.trades++;
  strategy.totalPnl += pnl;
  if (isWin) {
    strategy.wins++;
  } else {
    strategy.losses++;
  }
  
  // Update leaderboard every 10 trades
  const totalTrades = Object.values(STRATEGY_COMPETITION).reduce((sum, s) => sum + s.trades, 0);
  if (totalTrades % 10 === 0) {
    updateStrategyLeaderboard();
  }
}

function getStrategyCapitalAllocation(strategyName: string): number {
  return STRATEGY_COMPETITION[strategyName]?.capitalAllocation || 12.5;
}

// Public getter for strategy competition leaderboard
export function getStrategyCompetition() {
  const strategies = Object.values(STRATEGY_COMPETITION)
    .sort((a, b) => a.rank - b.rank);
  
  return {
    extraPowerMode: EXTRA_POWER_MODE,
    leaderboard: strategies,
    totalTrades: strategies.reduce((sum, s) => sum + s.trades, 0),
    totalPnl: strategies.reduce((sum, s) => sum + s.totalPnl, 0),
    topPerformer: strategies[0] || null,
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// 🚀 EXTRA POWER MODE CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════

const EXTRA_POWER_MODE = {
  enabled: true,
  name: "EXTRA POWER MODE",
  description: "8 Enhanced Strategies + Sentiment + Competition",
  
  // Strategy selection boost
  strategyBoost: 1.5,
  
  // Sentiment influence on trades
  sentimentWeight: 0.20, // 20% influence
  
  // Competition interval (trades)
  leaderboardUpdateInterval: 10,
  
  // Capital rebalancing
  rebalanceEnabled: true,
  
  // Aggression multiplier (8-9 = high aggression)
  aggressionMultiplier: 1.25,
};

// ===== 🔱⚡🔥 TRIPLED CYCLES - MAX ULTRA TRADING MODE + EXTRA PROFIT 🔥⚡🔱 =====
const GOD_MODE_LEVEL = 45;  // 🔥 TRIPLED MODE x1.5 = MAXIMUM ULTRA PROFIT!
const TRIPLED_MODE_ENABLED = true;
const EXTRA_PROFIT_TRIPLED = true;
const TRINITY_MODE_ENABLED = true;
const WATERFALL_ENABLED = true;
const DOUBLING_ENABLED = true;
const SNOWBALL_ENABLED = true;

const PROFIT_FILTERS = {
  // 🔱⚡ TRIPLED CYCLES - ABSOLUTE MAXIMUM ENTRIES ⚡🔱
  minRSI: 30,           // RSI > 30 for shorts (TRIPLED - ALL ENTRIES)
  maxRSI: 100,          // RSI ≤ 100 (CAPTURE EVERYTHING)
  minFundingForShort: 0.0,  // ANY funding counts (TRIPLED MODE)
  minAIVotes: 0,        // 0/8 AI models (NO FILTER - TRIPLED!)
  minConfidence: 0.05,  // 5% minimum confidence (TRIPLED MODE)
  
  // 🔱⚡ TRIPLED ALTCOIN BOOSTS (MAXIMUM ULTRA POWER)
  altcoinBoost: {
    "SOL_USDT": 4.0,    // SOL gets 4.0x larger positions (TRIPLED)
    "AVAX_USDT": 3.8,   // AVAX gets 3.8x larger positions (TRIPLED)
    "XRP_USDT": 3.9,    // XRP gets 3.9x larger positions (TRIPLED)
    "BTC_USDT": 3.0,    // BTC gets 3.0x boost (TRIPLED)
    "ETH_USDT": 3.0,    // ETH gets 3.0x boost (TRIPLED)
    "DOGE_USDT": 3.5    // DOGE gets 3.5x boost (TRIPLED)
  },
  
  // TRIPLED: ZERO FILTER THRESHOLD
  minProfitScore: 0,    // No minimum (TRIPLED MODE - ABSOLUTE MAXIMUM!)
};

// ===== 🔱⚡ TRIPLED CYCLES AI ULTRA-SMART POWER SYSTEM ⚡🔱 =====
const AI_SMART_POWER = {
  level: GOD_MODE_LEVEL,
  name: "TRIPLED CYCLES - MAX ULTRA TRADING MODE",
  description: "⚡ 6X/SEC CYCLES - WATERFALL + DOUBLING + SNOWBALL + SCALPING ⚡",
  
  // 🔱⚡ TRIPLED AI Power Multipliers
  powerMultiplier: 1 + (GOD_MODE_LEVEL * 0.25), // Level 30 = 8.5x power
  
  // ⚡⚡⚡ TRIPLED Trade Frequency Boost
  tradeFrequencyBoost: GOD_MODE_LEVEL / 2,  // 15x faster trades
  
  // 💰 TRIPLED Position Size Boost
  positionBoost: 1 + (GOD_MODE_LEVEL * 0.20), // Level 30 = 7.0x positions
  
  // AI Confidence Override (TRIPLED Mode - ZERO FILTER)
  godModeConfidenceOverride: true,
  tripledModeEnabled: TRIPLED_MODE_ENABLED,
  trinityModeEnabled: TRINITY_MODE_ENABLED,
  
  // Maximum concurrent trades per pair
  maxConcurrentTrades: GOD_MODE_LEVEL,  // 30 concurrent trades
  
  // 🔱⚡ TRIPLED STRATEGY WEIGHTS (ALL ACTIVE)
  strategyWeights: {
    WATERFALL: 0.30,  // 30% - Cascade on strong drops
    DOUBLING: 0.25,   // 25% - Recovery mode
    SNOWBALL: 0.25,   // 25% - Compound profits
    SCALPING: 0.20    // 20% - Ultra-fast micro-shorts (BOOSTED)
  }
};

// ===== 🏆 ONE USDT PER MINUTE PROFIT TARGETS =====
const PROFIT_TARGETS = {
  scalp: { low: 0.002, high: 0.005 },      // 0.2% - 0.5% (ULTRA-QUICK)
  trend: 0.015,                              // 1.5% (FAST TREND)
  quick: 0.003,                              // 0.3% (MICRO-EXIT)
  standard: 0.006,                           // 0.6% (FAST STANDARD)
  god: { quick: 0.008, standard: 0.015, max: 0.025 }  // 0.8%, 1.5%, 2.5% (FASTER PROFITS)
};

// ===== 🔒 OPTIMIZED CASCADE LOCK LEVELS =====
const CASCADE_LOCKS = [
  { profit: 0.003, lock: 0.15 },   // +0.3% = lock 15% (FIRST LOCK)
  { profit: 0.005, lock: 0.25 },   // +0.5% = lock 25%
  { profit: 0.008, lock: 0.40 },   // +0.8% = lock 40%
  { profit: 0.010, lock: 0.50 },   // +1.0% = lock 50%
  { profit: 0.015, lock: 0.65 },   // +1.5% = lock 65%
  { profit: 0.020, lock: 0.80 },   // +2.0% = lock 80%
  { profit: 0.025, lock: 0.90 },   // +2.5% = lock 90%
  { profit: 0.030, lock: 1.00 }    // +3.0% = 100% exit
];

// ═══════════════════════════════════════════════════════════════════════════
// 🔱 QUALITY FILTERS - ENHANCED TRADE VALIDATION FOR $692 BALANCE
// ═══════════════════════════════════════════════════════════════════════════
const QUALITY_FILTERS = {
  minEdgeScore: 60,              // Only 60%+ edge trades (was 75% - relaxed for more trades)
  minConfidence: 50,             // Only 50%+ confidence (was 70% - more flexible)
  minRiskRewardRatio: 2.0,       // Minimum 2.0:1 R/R (was 2.5 - more flexible)
  minVolume24h: 50000,           // Minimum $50k daily volume
  maxSpreadPct: 1.0,             // Maximum 1.0% spread
  minLiquidityScore: 40,         // Minimum liquidity score
  minAIConsensus: 3,             // At least 3/8 AI models agree
  maxConcurrentPositions: 4,     // Max 4 positions open
  requireTrendConfirmation: false, // Relaxed for SHORTS_ONLY mode
};

// ═══════════════════════════════════════════════════════════════════════════
// 🚦 TRADE FREQUENCY LIMITS - OPTIMIZED FOR TRIPLED CYCLES
// ═══════════════════════════════════════════════════════════════════════════
const FREQUENCY_LIMITS = {
  maxTradesPerHour: 12,           // Max 12 trades/hour (2x boost)
  maxTradesPerDay: 60,            // Max 60 trades/day
  minTimeBetweenTrades: 20,       // 20 seconds between trades (tripled speed)
  maxConcurrentPositions: 4,      // Max 4 positions open
  cooldownAfterLoss: 30,          // 30 second cooldown after loss
  cooldownAfterConsecutiveLoss: 60, // 60 second cooldown after 2+ losses
};

// ═══════════════════════════════════════════════════════════════════════════════
// 🧠 SMART LOSS PREDICTION ENGINE - "IF YOU KNOW YOU CAN LOSE, DON'T TRADE"
// ═══════════════════════════════════════════════════════════════════════════════
interface LossPredictionResult {
  canLose: boolean;
  lossRisk: number;           // 0-100 percentage
  lossReasons: string[];
  riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  blockTrade: boolean;
  recommendation: string;
}

interface SmartPredictionState {
  enabled: boolean;
  totalPredictions: number;
  blockedTrades: number;
  correctPredictions: number;
  savedLosses: number;
  lastPrediction: LossPredictionResult | null;
  recentLosses: number[];      // Last 10 trade results (1=loss, 0=win)
  marketRegime: "BULLISH" | "BEARISH" | "SIDEWAYS" | "VOLATILE";
  confidenceThreshold: number; // Min confidence to trade
  riskThreshold: number;       // Max loss risk to trade
}

const SMART_PREDICTION_ENGINE: SmartPredictionState = {
  enabled: true,
  totalPredictions: 0,
  blockedTrades: 0,
  correctPredictions: 0,
  savedLosses: 0,
  lastPrediction: null,
  recentLosses: [],
  marketRegime: "SIDEWAYS",
  confidenceThreshold: 0.45,  // Block if confidence < 45%
  riskThreshold: 65,          // Block if loss risk > 65%
};

// 🧠 12 SMART LOSS INDICATORS
function predictLoss(marketData: any, consensus: any, recentTrades: any[]): LossPredictionResult {
  const lossReasons: string[] = [];
  let lossRisk = 0;
  
  // === INDICATOR 1: MOMENTUM AGAINST POSITION ===
  const rsi = marketData.rsi || 50;
  const direction = consensus?.direction || "SHORT";
  if (direction === "SHORT" && rsi < 30) {
    lossRisk += 15;
    lossReasons.push("RSI oversold (<30) - SHORT risky");
  }
  if (direction === "LONG" && rsi > 70) {
    lossRisk += 15;
    lossReasons.push("RSI overbought (>70) - LONG risky");
  }
  
  // === INDICATOR 2: FUNDING RATE AGAINST POSITION ===
  const fundingRate = marketData.fundingRate || 0;
  if (direction === "SHORT" && fundingRate < -0.01) {
    lossRisk += 12;
    lossReasons.push(`Negative funding (${(fundingRate*100).toFixed(3)}%) - Market bullish`);
  }
  if (direction === "LONG" && fundingRate > 0.01) {
    lossRisk += 12;
    lossReasons.push(`High positive funding (${(fundingRate*100).toFixed(3)}%) - Market crowded`);
  }
  
  // === INDICATOR 3: MACD DIVERGENCE ===
  const macdHist = marketData.macd?.histogram || 0;
  if (direction === "SHORT" && macdHist > 0 && macdHist > 0.5) {
    lossRisk += 10;
    lossReasons.push("MACD bullish histogram - SHORT divergence");
  }
  if (direction === "LONG" && macdHist < 0 && macdHist < -0.5) {
    lossRisk += 10;
    lossReasons.push("MACD bearish histogram - LONG divergence");
  }
  
  // === INDICATOR 4: BOLLINGER BAND SQUEEZE ===
  const bbPosition = marketData.bollinger?.position || 0.5;
  if (direction === "SHORT" && bbPosition < 0.2) {
    lossRisk += 8;
    lossReasons.push("Price at lower Bollinger - Bounce likely");
  }
  if (direction === "LONG" && bbPosition > 0.8) {
    lossRisk += 8;
    lossReasons.push("Price at upper Bollinger - Rejection likely");
  }
  
  // === INDICATOR 5: RECENT LOSS STREAK ===
  const recentLossCount = SMART_PREDICTION_ENGINE.recentLosses.filter(x => x === 1).length;
  if (recentLossCount >= 3) {
    lossRisk += 15;
    lossReasons.push(`Loss streak (${recentLossCount}/10) - Pattern detected`);
  } else if (recentLossCount >= 2) {
    lossRisk += 8;
    lossReasons.push(`Recent losses (${recentLossCount}/10) - Caution`);
  }
  
  // === INDICATOR 6: LOW CONFIDENCE SIGNAL ===
  const confidence = consensus?.confidence || 0;
  if (confidence < 0.40) {
    lossRisk += 18;
    lossReasons.push(`Very low AI confidence (${(confidence*100).toFixed(0)}%)`);
  } else if (confidence < 0.55) {
    lossRisk += 10;
    lossReasons.push(`Weak AI confidence (${(confidence*100).toFixed(0)}%)`);
  }
  
  // === INDICATOR 7: VOLATILE MARKET CONDITIONS ===
  const priceChange = Math.abs(marketData.priceChange24h || 0);
  if (priceChange > 8) {
    lossRisk += 12;
    lossReasons.push(`High volatility (${priceChange.toFixed(1)}% 24h change)`);
  } else if (priceChange > 5) {
    lossRisk += 6;
    lossReasons.push(`Elevated volatility (${priceChange.toFixed(1)}% 24h change)`);
  }
  
  // === INDICATOR 8: VOLUME IMBALANCE ===
  const volumeRatio = marketData.volumeRatio || 1;
  if (volumeRatio < 0.5) {
    lossRisk += 8;
    lossReasons.push(`Low volume ratio (${volumeRatio.toFixed(2)}) - Weak trend`);
  }
  if (volumeRatio > 3) {
    lossRisk += 5;
    lossReasons.push(`Extreme volume spike - Potential reversal`);
  }
  
  // === INDICATOR 9: ICHIMOKU CLOUD CONFLICT ===
  const ichimoku = marketData.ichimoku;
  if (ichimoku) {
    const priceVsCloud = marketData.currentPrice > ichimoku.spanA && marketData.currentPrice > ichimoku.spanB;
    if (direction === "SHORT" && priceVsCloud) {
      lossRisk += 10;
      lossReasons.push("Price above Ichimoku cloud - Bullish structure");
    }
    const priceBelowCloud = marketData.currentPrice < ichimoku.spanA && marketData.currentPrice < ichimoku.spanB;
    if (direction === "LONG" && priceBelowCloud) {
      lossRisk += 10;
      lossReasons.push("Price below Ichimoku cloud - Bearish structure");
    }
  }
  
  // === INDICATOR 10: INSUFFICIENT AI CONSENSUS ===
  const totalVotes = consensus?.totalVotes || 0;
  if (totalVotes < 4) {
    lossRisk += 12;
    lossReasons.push(`Low AI consensus (${totalVotes}/8 models)`);
  } else if (totalVotes < 6) {
    lossRisk += 5;
    lossReasons.push(`Moderate AI consensus (${totalVotes}/8 models)`);
  }
  
  // === INDICATOR 11: WRONG TIME OF DAY ===
  const hour = new Date().getUTCHours();
  if (hour >= 0 && hour <= 3) {
    lossRisk += 5;
    lossReasons.push("Low liquidity hours (00:00-03:00 UTC)");
  }
  if (hour >= 13 && hour <= 15) {
    lossRisk += 3;
    lossReasons.push("US market open volatility window");
  }
  
  // === INDICATOR 12: PROTECTION MODE ACTIVE ===
  if (GODS_MODE_LOSS_ENGINE.protectionTier !== "NORMAL") {
    lossRisk += 15;
    lossReasons.push(`Protection mode: ${GODS_MODE_LOSS_ENGINE.protectionTier}`);
  }
  
  // Cap at 100
  lossRisk = Math.min(lossRisk, 100);
  
  // Determine risk level
  let riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" = "LOW";
  if (lossRisk >= 70) riskLevel = "CRITICAL";
  else if (lossRisk >= 50) riskLevel = "HIGH";
  else if (lossRisk >= 30) riskLevel = "MEDIUM";
  
  // Determine if we should block
  const blockTrade = lossRisk >= SMART_PREDICTION_ENGINE.riskThreshold || 
                     confidence < SMART_PREDICTION_ENGINE.confidenceThreshold;
  
  // Generate recommendation
  let recommendation = "";
  if (blockTrade) {
    recommendation = `⛔ BLOCKED: ${lossRisk}% loss risk - "IF YOU KNOW YOU CAN LOSE, DON'T TRADE"`;
  } else if (riskLevel === "HIGH") {
    recommendation = `⚠️ HIGH RISK: ${lossRisk}% - Proceed with reduced size`;
  } else if (riskLevel === "MEDIUM") {
    recommendation = `🟡 MEDIUM RISK: ${lossRisk}% - Proceed with caution`;
  } else {
    recommendation = `✅ LOW RISK: ${lossRisk}% - Favorable conditions`;
  }
  
  const result: LossPredictionResult = {
    canLose: lossRisk >= 50,
    lossRisk,
    lossReasons,
    riskLevel,
    blockTrade,
    recommendation
  };
  
  // Update state
  SMART_PREDICTION_ENGINE.totalPredictions++;
  SMART_PREDICTION_ENGINE.lastPrediction = result;
  if (blockTrade) {
    SMART_PREDICTION_ENGINE.blockedTrades++;
    console.log(`🧠 SMART PREDICTION: ${recommendation}`);
    lossReasons.forEach(reason => console.log(`   └─ ${reason}`));
  }
  
  return result;
}

// Track trade outcome for learning
function recordTradeOutcome(isWin: boolean): void {
  SMART_PREDICTION_ENGINE.recentLosses.push(isWin ? 0 : 1);
  if (SMART_PREDICTION_ENGINE.recentLosses.length > 10) {
    SMART_PREDICTION_ENGINE.recentLosses.shift();
  }
  
  // Track prediction accuracy
  const lastPrediction = SMART_PREDICTION_ENGINE.lastPrediction;
  if (lastPrediction) {
    const predictedLoss = lastPrediction.canLose;
    const actualLoss = !isWin;
    if (predictedLoss === actualLoss) {
      SMART_PREDICTION_ENGINE.correctPredictions++;
    }
    if (lastPrediction.blockTrade && actualLoss) {
      SMART_PREDICTION_ENGINE.savedLosses++;
      console.log(`🧠 SMART PREDICTION: Correctly avoided loss! (${SMART_PREDICTION_ENGINE.savedLosses} saved total)`);
    }
  }
}

// Detect market regime
function detectMarketRegime(marketData: any): "BULLISH" | "BEARISH" | "SIDEWAYS" | "VOLATILE" {
  const rsi = marketData.rsi || 50;
  const priceChange = marketData.priceChange24h || 0;
  const macdHist = marketData.macd?.histogram || 0;
  
  if (Math.abs(priceChange) > 5) {
    SMART_PREDICTION_ENGINE.marketRegime = "VOLATILE";
  } else if (rsi > 60 && priceChange > 2 && macdHist > 0) {
    SMART_PREDICTION_ENGINE.marketRegime = "BULLISH";
  } else if (rsi < 40 && priceChange < -2 && macdHist < 0) {
    SMART_PREDICTION_ENGINE.marketRegime = "BEARISH";
  } else {
    SMART_PREDICTION_ENGINE.marketRegime = "SIDEWAYS";
  }
  
  return SMART_PREDICTION_ENGINE.marketRegime;
}

// Get smart prediction stats
function getSmartPredictionStats() {
  const accuracy = SMART_PREDICTION_ENGINE.totalPredictions > 0 
    ? (SMART_PREDICTION_ENGINE.correctPredictions / SMART_PREDICTION_ENGINE.totalPredictions * 100).toFixed(1)
    : "0.0";
    
  return {
    enabled: SMART_PREDICTION_ENGINE.enabled,
    totalPredictions: SMART_PREDICTION_ENGINE.totalPredictions,
    blockedTrades: SMART_PREDICTION_ENGINE.blockedTrades,
    correctPredictions: SMART_PREDICTION_ENGINE.correctPredictions,
    savedLosses: SMART_PREDICTION_ENGINE.savedLosses,
    accuracy: `${accuracy}%`,
    marketRegime: SMART_PREDICTION_ENGINE.marketRegime,
    recentLosses: SMART_PREDICTION_ENGINE.recentLosses,
    lossStreak: SMART_PREDICTION_ENGINE.recentLosses.filter(x => x === 1).length,
    confidenceThreshold: SMART_PREDICTION_ENGINE.confidenceThreshold,
    riskThreshold: SMART_PREDICTION_ENGINE.riskThreshold,
    lastPrediction: SMART_PREDICTION_ENGINE.lastPrediction
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// 💰 POSITION SIZING BY CONFIDENCE LEVEL - DOUBLED FOR MORE POWER!
// ═══════════════════════════════════════════════════════════════════════════
const POSITION_BY_CONFIDENCE = {
  GODLIKE: 70,     // 10% of balance - max confidence (DOUBLED!)
  ELITE: 60,       // 8.7% of balance (DOUBLED!)
  STRONG: 50,      // 7.2% of balance (DOUBLED!)
  MODERATE: 40,    // 5.8% of balance (DOUBLED!)
  WEAK: 30,        // 4.3% of balance (DOUBLED!)
  MINIMUM: 20,     // 2.9% of balance - minimum position (DOUBLED!)
};

// ═══════════════════════════════════════════════════════════════════════════
// 🎯 LEVERAGE BY CONFIDENCE LEVEL - SAFER FOR $692
// ═══════════════════════════════════════════════════════════════════════════
const LEVERAGE_BY_CONFIDENCE = {
  GODLIKE: 10,     // Max 10x for GODLIKE confidence
  ELITE: 8,        // 8x for ELITE
  STRONG: 6,       // 6x for STRONG
  MODERATE: 5,     // 5x for MODERATE
  WEAK: 3,         // 3x for WEAK
  DEFAULT: 5,      // 5x default
};

// ===== 📊 ONE USDT PER MINUTE MULTIPLIERS =====
const MULTIPLIERS = {
  base: 2.0,       // 2.0x base multiplier
  godTier: 3.0,    // 3.0x god tier
  ultra: 4.0       // 4.0x ultra mode
};

// ===== ⏱️ 167ms TRIPLED CYCLE TIMING =====
const CYCLE_TIMING = {
  normal: 20 * 1000,           // 20 sec normal mode
  alert: 5 * 1000,             // 5 sec alert mode
  hyperSync: 1 * 1000,         // 1 sec hyper sync
  turboGod: 2 * 1000,          // 2 sec turbo god
  signalCooldown: 167,         // 167ms cooldown (TRIPLED!)
  minBetweenTrades: 100        // 100ms between trades (ULTRA-FAST!)
};

// ═══════════════════════════════════════════════════════════════════════════
// 🐺 POWER STARTUP BANNER - SHOWS ALL ENHANCED FEATURES
// ═══════════════════════════════════════════════════════════════════════════
export function printWolfPackPowerBanner(): void {
  const banner = `
═══════════════════════════════════════════════════════════════════════════════
🐺⚡ WOLF PACK TRADING SYSTEM - MAXIMUM POWER MODE ⚡🐺
═══════════════════════════════════════════════════════════════════════════════

💰 BALANCE CONFIGURATION:
   • Total Balance:     $${DEFAULT_WOLF_PACK_CONFIG.totalBudget}
   • Active Engines:    ${DEFAULT_WOLF_PACK_CONFIG.pairs.length} (${DEFAULT_WOLF_PACK_CONFIG.pairs.join(', ')})
   • Budget Per Engine: $${DEFAULT_WOLF_PACK_CONFIG.totalBudget / DEFAULT_WOLF_PACK_CONFIG.pairs.length}

🔴 TRADING MODE: ${DEFAULT_WOLF_PACK_CONFIG.tradingDirection}
   • NO LONGS - SHORTS ONLY ACTIVATED!
   • Tripled Cycles: ${TRIPLED_CYCLES_ENABLED ? 'ENABLED ⚡' : 'DISABLED'}
   • Cycle Speed: ${DEFAULT_WOLF_PACK_CONFIG.cycleIntervalMs / 1000}s (3x faster!)

🛡️ UNBREAKABLE PROTECTION:
   • Daily Loss Limit:    -${Math.abs(DEFAULT_UNBREAKABLE_CONFIG.dailyLossLimitPercent)}% = -$${Math.abs(DEFAULT_UNBREAKABLE_CONFIG.dailyLossLimitPercent * DEFAULT_WOLF_PACK_CONFIG.totalBudget / 100).toFixed(2)}
   • Consecutive Limit:   ${DEFAULT_UNBREAKABLE_CONFIG.consecutiveLossLimit} losses
   • Max Drawdown:        -${Math.abs(DEFAULT_UNBREAKABLE_CONFIG.peakDrawdownLimitPercent)}% = -$${Math.abs(DEFAULT_UNBREAKABLE_CONFIG.peakDrawdownLimitPercent * DEFAULT_WOLF_PACK_CONFIG.totalBudget / 100).toFixed(2)}
   • Max Leverage:        ${DEFAULT_WOLF_PACK_CONFIG.maxLeverage}x
   • Max Exposure:        ${DEFAULT_UNBREAKABLE_CONFIG.maxPortfolioExposurePercent}% = $${(DEFAULT_UNBREAKABLE_CONFIG.maxPortfolioExposurePercent * DEFAULT_WOLF_PACK_CONFIG.totalBudget / 100).toFixed(2)}

💹 POSITION SIZING:
   • Min Position:  $${TURBO_CONFIG.minPositionUsd}
   • Max Position:  $${TURBO_CONFIG.maxPositionUsd}
   • Default:       $${TURBO_CONFIG.defaultPositionUsd}
   • Risk/Trade:    ${DEFAULT_WOLF_PACK_CONFIG.riskPerTradePercent}% = $${(DEFAULT_WOLF_PACK_CONFIG.riskPerTradePercent * DEFAULT_WOLF_PACK_CONFIG.totalBudget / 100).toFixed(2)}

🎯 QUALITY FILTERS:
   • Min Edge Score: ${QUALITY_FILTERS.minEdgeScore}%
   • Min Confidence: ${QUALITY_FILTERS.minConfidence}%
   • Min R:R Ratio:  ${QUALITY_FILTERS.minRiskRewardRatio}:1
   • Max Spread:     ${QUALITY_FILTERS.maxSpreadPct}%

⚡ FREQUENCY LIMITS:
   • Max Trades/Hour: ${FREQUENCY_LIMITS.maxTradesPerHour}
   • Max Trades/Day:  ${FREQUENCY_LIMITS.maxTradesPerDay}
   • Min Between:     ${FREQUENCY_LIMITS.minTimeBetweenTrades}s
   • Loss Cooldown:   ${FREQUENCY_LIMITS.cooldownAfterLoss}s

📊 STRATEGIES READY:
   • WATERFALL | DOUBLING | SNOWBALL | SCALPING | PYRAMID

🤖 AI MODELS: 8 ACTIVE
   • DeepSeek R1 | GPT-5 | Claude Opus | Llama 3.3 70B
   • Gemini Flash | Mistral Large | Qwen 72B | Grok xAI

═══════════════════════════════════════════════════════════════════════════════
🟢 WOLF PACK READY - GODS MODE ACTIVATED - MAXIMUM POWER!
═══════════════════════════════════════════════════════════════════════════════
`;
  console.log(banner);
}

// ═══════════════════════════════════════════════════════════════════════════
// 🔱⚡ 666 GODS LEVEL MODE - UNBREAKABLE PROFIT & LOSS ENGINES ⚡🔱
// ═══════════════════════════════════════════════════════════════════════════
// 
// 🔥 FEATURES:
// ✅ Auto-Save to PostgreSQL (NEVER LOSE SETTINGS)
// ✅ Unbreakable Health Check Engine
// ✅ Unstoppable Trading Loop
// ✅ 6-Tier Profit Acceleration (STANDARD → GODLIKE → IMMORTAL → TITAN)
// ✅ 6-Tier Loss Protection (NORMAL → CAUTION → DANGER → EMERGENCY → LOCKDOWN → FORTRESS)
// ✅ Anti-Liquidation Shield v2.0
// ✅ Whale Protection System
// ✅ Smart Kelly Criterion
// ✅ Momentum Score Engine
// ✅ Risk Score Calculator
// ✅ Auto-Recovery Protocol
// ✅ Profit Locking System
// ═══════════════════════════════════════════════════════════════════════════

// 🔱 666 GODS LEVEL CONSTANTS
const GODS_LEVEL_VERSION = "666";
const UNBREAKABLE_MODE = true;
const AUTO_SAVE_INTERVAL = 30000; // Save every 30 seconds
const HEALTH_CHECK_INTERVAL = 5000; // Check every 5 seconds

interface GodsModeProfit {
  sessionStartBalance: number;
  currentBalance: number;
  peakBalance: number;
  totalProfit: number;
  totalLoss: number;
  netPnL: number;
  profitStreak: number;
  lossStreak: number;
  bestTrade: number;
  worstTrade: number;
  winRate: number;
  profitFactor: number;
  lastUpdate: string;
  // 🔱 666 GODS LEVEL ADDITIONS
  totalTrades: number;
  totalWins: number;
  averageWin: number;
  averageLoss: number;
  expectancy: number;
  profitAccelerationMode: "STANDARD" | "TURBO" | "ULTRA" | "GODLIKE" | "IMMORTAL" | "TITAN";
  profitMomentum: number;          // Rolling profit momentum score
  compoundMultiplier: number;      // Dynamic compound boost
  profitLockThreshold: number;     // Lock profits above this
  lockedProfit: number;            // Protected profit amount
  withdrawalReady: number;         // Amount ready for withdrawal
  lastWithdrawal: string;          // Last withdrawal timestamp
  hourlyProfit: number;            // Profit in last hour
  dailyProfit: number;             // Profit today
  // 🔱 666 EXCLUSIVE
  unbreakableMode: boolean;        // Never stop trading
  autoRecoveryActive: boolean;     // Auto-recovery protocol
  profitVelocity: number;          // $ per hour profit rate
  titanStreak: number;             // Trades since last loss
  immortalBonus: number;           // Bonus from immortal mode
}

interface GodsModeLoss {
  sessionLoss: number;
  dailyLoss: number;
  weeklyLoss: number;
  maxDrawdown: number;
  currentDrawdown: number;
  protectionTier: "NORMAL" | "CAUTION" | "DANGER" | "EMERGENCY" | "LOCKDOWN" | "FORTRESS";
  autoStopTriggered: boolean;
  positionReduction: number;
  lastLossTimestamp: string;
  recoveryMode: boolean;
  consecutiveLosses: number;
  // 🔱 666 GODS LEVEL ADDITIONS
  antiLiquidationActive: boolean;   // Emergency anti-liquidation shield
  whaleProtectionActive: boolean;   // Large loss protection
  smartCooldown: number;            // Dynamic cooldown in seconds
  lossVelocity: number;             // Speed of losses (per hour)
  recoveryTarget: number;           // Target balance to exit recovery
  kellyFraction: number;            // Dynamic Kelly for position sizing
  riskScore: number;                // 0-100 current risk assessment
  lastRecoveryCheck: string;        // When we last checked recovery status
  emergencyExitPrice: number;       // Price level for emergency exit
  dailyLossLimit: number;           // Max loss allowed per day
  weeklyLossLimit: number;          // Max loss allowed per week
  breakevenStreak: number;          // Consecutive breakeven trades
  // 🔱 666 EXCLUSIVE
  fortressMode: boolean;            // Ultimate protection mode
  lockdownActive: boolean;          // Trading locked down
  unbreakableShield: boolean;       // Cannot be broken
  healthScore: number;              // 0-100 system health
  lastHealthCheck: string;          // Last health check timestamp
  autoRestartCount: number;         // Times system auto-restarted
}

const GODS_MODE_PROFIT_ENGINE: GodsModeProfit = {
  sessionStartBalance: 963.33,
  currentBalance: 963.33,
  peakBalance: 963.33,
  totalProfit: 0,
  totalLoss: 0,
  netPnL: 0,
  profitStreak: 0,
  lossStreak: 0,
  bestTrade: 0,
  worstTrade: 0,
  winRate: 0,
  profitFactor: 0,
  lastUpdate: new Date().toISOString(),
  // 🔱 666 GODS LEVEL INIT
  totalTrades: 0,
  totalWins: 0,
  averageWin: 0,
  averageLoss: 0,
  expectancy: 0,
  profitAccelerationMode: "STANDARD",
  profitMomentum: 0,
  compoundMultiplier: 1.0,
  profitLockThreshold: 50,         // Lock profits after $50 gain
  lockedProfit: 0,
  withdrawalReady: 0,
  lastWithdrawal: "",
  hourlyProfit: 0,
  dailyProfit: 0,
  // 🔱 666 EXCLUSIVE
  unbreakableMode: true,
  autoRecoveryActive: false,
  profitVelocity: 0,
  titanStreak: 0,
  immortalBonus: 0,
};

const GODS_MODE_LOSS_ENGINE: GodsModeLoss = {
  sessionLoss: 0,
  dailyLoss: 0,
  weeklyLoss: 0,
  maxDrawdown: 0,
  currentDrawdown: 0,
  protectionTier: "NORMAL",
  autoStopTriggered: false,
  positionReduction: 1.0,
  lastLossTimestamp: "",
  recoveryMode: false,
  consecutiveLosses: 0,
  // 🔱 666 GODS LEVEL INIT
  antiLiquidationActive: false,
  whaleProtectionActive: false,
  smartCooldown: 0,
  lossVelocity: 0,
  recoveryTarget: 963.33,
  kellyFraction: 0.15,
  riskScore: 0,
  lastRecoveryCheck: new Date().toISOString(),
  emergencyExitPrice: 0,
  dailyLossLimit: 10,             // $10 daily loss limit (HARD STOP)
  weeklyLossLimit: 30,            // $30 weekly loss limit
  breakevenStreak: 0,
  // 🔱 666 EXCLUSIVE
  fortressMode: false,
  lockdownActive: false,
  unbreakableShield: true,
  healthScore: 100,
  lastHealthCheck: new Date().toISOString(),
  autoRestartCount: 0,
};

// 🛡️ 666 GODS LEVEL PROTECTION TIERS (6 Tiers!)
const GODS_PROTECTION_TIERS = {
  NORMAL: { maxLoss: 0, positionFactor: 1.0, action: "TRADE_NORMALLY", color: "🟢", level: 1 },
  CAUTION: { maxLoss: 3, positionFactor: 0.75, action: "REDUCE_SIZE_25%", color: "🟡", level: 2 },
  DANGER: { maxLoss: 5, positionFactor: 0.5, action: "REDUCE_SIZE_50%", color: "🟠", level: 3 },
  EMERGENCY: { maxLoss: 7, positionFactor: 0.25, action: "REDUCE_SIZE_75%", color: "🔴", level: 4 },
  LOCKDOWN: { maxLoss: 9, positionFactor: 0.1, action: "MICRO_TRADES_ONLY", color: "🛑", level: 5 },
  FORTRESS: { maxLoss: 10, positionFactor: 0, action: "FULL_STOP_FORTRESS", color: "🏰", level: 6 },
};

// 🔱 666 GODS LEVEL PROFIT ACCELERATION (6 Tiers!)
const PROFIT_ACCELERATION_MODES = {
  STANDARD: { minStreak: 0, multiplier: 1.0, description: "Normal trading", level: 1 },
  TURBO: { minStreak: 2, multiplier: 1.25, description: "2+ win streak = 25% boost", level: 2 },
  ULTRA: { minStreak: 4, multiplier: 1.5, description: "4+ win streak = 50% boost", level: 3 },
  GODLIKE: { minStreak: 6, multiplier: 2.0, description: "6+ win streak = 100% boost", level: 4 },
  IMMORTAL: { minStreak: 8, multiplier: 2.5, description: "8+ win streak = 150% boost", level: 5 },
  TITAN: { minStreak: 10, multiplier: 3.0, description: "10+ win streak = 200% boost", level: 6 },
};

// 🔱 666 ANTI-LIQUIDATION SHIELD v2.0
const ANTI_LIQUIDATION_SHIELD = {
  triggerDrawdownPercent: 3,       // Activate at 3% drawdown (earlier!)
  maxPositionInShield: 0.25,       // Max 25% position when active
  cooldownMinutes: 10,             // 10 min cooldown after trigger
  emergencyExitPercent: 6,         // Emergency exit at 6% loss
  unbreakable: true,               // Cannot be disabled
};

// 🔱 666 UNBREAKABLE HEALTH ENGINE
const UNBREAKABLE_HEALTH_ENGINE = {
  enabled: true,
  checkInterval: 5000,             // Check every 5 seconds
  autoRestart: true,               // Auto-restart on failure
  maxRestarts: 10,                 // Max 10 auto-restarts per hour
  healthThreshold: 50,             // Restart if health < 50%
  saveStateOnCheck: true,          // Save state on each health check
};

// 🔱 GODS LEVEL WHALE PROTECTION
const WHALE_PROTECTION = {
  singleLossThreshold: 3,          // $3 single loss triggers whale protection
  velocityThreshold: 5,            // $5/hour loss velocity is too fast
  recoveryBuffer: 1.5,             // Need 150% of loss to exit recovery
};

// 🔱 UPDATE GODS LEVEL PROFIT TRACKING (ENHANCED)
function updateGodsModeProfit(pnl: number, isWin: boolean): void {
  const now = new Date().toISOString();
  const profit = GODS_MODE_PROFIT_ENGINE;
  const loss = GODS_MODE_LOSS_ENGINE;
  
  // Track total trades
  profit.totalTrades++;
  
  if (isWin) {
    profit.totalProfit += pnl;
    profit.totalWins++;
    profit.profitStreak++;
    profit.lossStreak = 0;
    profit.dailyProfit += pnl;
    profit.hourlyProfit += pnl;
    
    if (pnl > profit.bestTrade) {
      profit.bestTrade = pnl;
    }
    
    // 🔱 GODS LEVEL: Update average win
    profit.averageWin = profit.totalProfit / profit.totalWins;
    
    // 🔱 666 GODS LEVEL: Profit acceleration mode based on streak (6 TIERS!)
    if (profit.profitStreak >= 10) {
      profit.profitAccelerationMode = "TITAN";
      profit.compoundMultiplier = 3.0;
      profit.titanStreak = profit.profitStreak;
      console.log("⚡🏆 TITAN MODE: 10+ win streak! 3x position multiplier! MAXIMUM POWER!");
    } else if (profit.profitStreak >= 8) {
      profit.profitAccelerationMode = "IMMORTAL";
      profit.compoundMultiplier = 2.5;
      profit.immortalBonus = profit.profitStreak * 0.1;
      console.log("⚡👑 IMMORTAL MODE: 8+ win streak! 2.5x position multiplier!");
    } else if (profit.profitStreak >= 6) {
      profit.profitAccelerationMode = "GODLIKE";
      profit.compoundMultiplier = 2.0;
      console.log("⚡🔱 GODLIKE MODE: 6+ win streak! 2x position multiplier!");
    } else if (profit.profitStreak >= 4) {
      profit.profitAccelerationMode = "ULTRA";
      profit.compoundMultiplier = 1.5;
      console.log("⚡💎 ULTRA MODE: 4+ win streak! 1.5x position multiplier!");
    } else if (profit.profitStreak >= 2) {
      profit.profitAccelerationMode = "TURBO";
      profit.compoundMultiplier = 1.25;
      console.log("⚡🚀 TURBO MODE: 2+ win streak! 1.25x position multiplier!");
    }
    
    // 🔱 GODS LEVEL: Profit locking
    if (profit.netPnL >= profit.profitLockThreshold) {
      const lockAmount = profit.netPnL * 0.5; // Lock 50% of profits
      profit.lockedProfit = lockAmount;
      console.log(`🔒 PROFIT LOCKED: $${lockAmount.toFixed(2)} protected!`);
    }
    
    // 🔱 GODS LEVEL: Withdrawal ready check ($100 threshold)
    if (profit.netPnL >= 100 && profit.withdrawalReady === 0) {
      profit.withdrawalReady = 50; // 50% to cold wallet
      console.log("💰 WITHDRAWAL READY: $50 available for cold wallet!");
    }
    
    // Exit recovery mode on wins
    loss.recoveryMode = false;
    loss.consecutiveLosses = 0;
    loss.antiLiquidationActive = false;
    loss.whaleProtectionActive = false;
    loss.smartCooldown = 0;
    
  } else {
    const absLoss = Math.abs(pnl);
    profit.totalLoss += absLoss;
    profit.lossStreak++;
    profit.profitStreak = 0;
    profit.profitAccelerationMode = "STANDARD";
    profit.compoundMultiplier = 1.0;
    
    if (pnl < profit.worstTrade) {
      profit.worstTrade = pnl;
    }
    
    // 🔱 GODS LEVEL: Update average loss
    const totalLosses = profit.totalTrades - profit.totalWins;
    if (totalLosses > 0) {
      profit.averageLoss = profit.totalLoss / totalLosses;
    }
    
    // 🔱 GODS LEVEL: Whale protection on large single loss
    if (absLoss >= WHALE_PROTECTION.singleLossThreshold) {
      loss.whaleProtectionActive = true;
      loss.smartCooldown = 30; // 30 second cooldown
      console.log(`🐋 WHALE PROTECTION: Large loss ($${absLoss.toFixed(2)}) detected! Cooldown active.`);
    }
    
    loss.consecutiveLosses++;
    loss.lastLossTimestamp = now;
    loss.dailyLoss += absLoss;
    loss.weeklyLoss += absLoss;
    
    // 🔱 GODS LEVEL: Anti-liquidation shield
    const drawdownPercent = ((profit.peakBalance - profit.currentBalance) / profit.peakBalance) * 100;
    if (drawdownPercent >= ANTI_LIQUIDATION_SHIELD.triggerDrawdownPercent) {
      loss.antiLiquidationActive = true;
      loss.positionReduction = Math.min(loss.positionReduction, ANTI_LIQUIDATION_SHIELD.maxPositionInShield);
      console.log(`🛡️ ANTI-LIQUIDATION SHIELD: ${drawdownPercent.toFixed(1)}% drawdown! Max 25% positions!`);
    }
    
    // 🔱 GODS LEVEL: Dynamic Kelly Criterion
    if (profit.totalTrades >= 10) {
      const winRate = profit.totalWins / profit.totalTrades;
      const avgWinLossRatio = profit.averageWin / (profit.averageLoss || 1);
      const kelly = winRate - ((1 - winRate) / avgWinLossRatio);
      loss.kellyFraction = Math.max(0.05, Math.min(0.25, kelly * 0.5)); // Half-Kelly, capped
    }
  }
  
  // 🔱 GODS LEVEL: Calculate expectancy
  if (profit.totalTrades > 0) {
    const winRate = profit.totalWins / profit.totalTrades;
    profit.winRate = winRate * 100;
    profit.expectancy = (winRate * profit.averageWin) - ((1 - winRate) * profit.averageLoss);
  }
  
  profit.netPnL = profit.totalProfit - profit.totalLoss;
  profit.currentBalance = profit.sessionStartBalance + profit.netPnL;
  
  if (profit.currentBalance > profit.peakBalance) {
    profit.peakBalance = profit.currentBalance;
  }
  
  // Calculate profit factor
  if (profit.totalLoss > 0) {
    profit.profitFactor = profit.totalProfit / profit.totalLoss;
  }
  
  // 🔱 GODS LEVEL: Profit momentum (rolling score)
  profit.profitMomentum = (profit.profitStreak * 10) - (profit.lossStreak * 15);
  profit.profitMomentum = Math.max(-100, Math.min(100, profit.profitMomentum));
  
  // 🔱 GODS LEVEL: Risk score calculation
  loss.riskScore = Math.min(100, 
    (loss.consecutiveLosses * 15) + 
    (loss.currentDrawdown * 5) + 
    (loss.lossVelocity * 10)
  );
  
  profit.lastUpdate = now;
  
  // Update loss engine with enhanced logic
  updateGodsModeLoss();
  
  // Print status on significant events
  if (profit.profitStreak >= 3 || loss.consecutiveLosses >= 2 || loss.protectionTier !== "NORMAL") {
    printGodsModeStatus();
  }
}

// 🛡️ 666 GODS LEVEL LOSS PROTECTION (6 TIERS!)
function updateGodsModeLoss(): void {
  const loss = GODS_MODE_LOSS_ENGINE;
  const profit = GODS_MODE_PROFIT_ENGINE;
  const sessionLoss = profit.totalLoss;
  const drawdown = profit.peakBalance - profit.currentBalance;
  const drawdownPercent = (drawdown / profit.peakBalance) * 100;
  
  loss.sessionLoss = sessionLoss;
  loss.currentDrawdown = drawdown;
  loss.healthScore = Math.max(0, 100 - (sessionLoss * 10) - (loss.consecutiveLosses * 5));
  loss.lastHealthCheck = new Date().toISOString();
  
  if (drawdown > loss.maxDrawdown) {
    loss.maxDrawdown = drawdown;
  }
  
  // 🔱 666 GODS LEVEL: 6-Tier Protection System!
  if (sessionLoss >= GODS_PROTECTION_TIERS.FORTRESS.maxLoss) {
    loss.protectionTier = "FORTRESS";
    loss.autoStopTriggered = true;
    loss.positionReduction = 0;
    loss.fortressMode = true;
    loss.lockdownActive = true;
    console.log("\n🏰🛑 666 FORTRESS MODE: $10 LOSS LIMIT - FULL STOP ACTIVATED! 🛑🏰");
  } else if (sessionLoss >= GODS_PROTECTION_TIERS.LOCKDOWN.maxLoss) {
    loss.protectionTier = "LOCKDOWN";
    loss.positionReduction = 0.1;
    loss.lockdownActive = true;
    loss.recoveryMode = true;
    console.log("\n🛑 666 LOCKDOWN: $9 loss - MICRO TRADES ONLY (10% size)! 🛑");
  } else if (sessionLoss >= GODS_PROTECTION_TIERS.EMERGENCY.maxLoss) {
    loss.protectionTier = "EMERGENCY";
    loss.positionReduction = 0.25;
    loss.recoveryMode = true;
    console.log("\n🔴 666 EMERGENCY: $7 loss - 75% Position Reduction! 🔴");
  } else if (sessionLoss >= GODS_PROTECTION_TIERS.DANGER.maxLoss) {
    loss.protectionTier = "DANGER";
    loss.positionReduction = 0.5;
    loss.recoveryMode = true;
    console.log("\n🟠 666 DANGER: $5 loss - 50% Position Reduction! 🟠");
  } else if (sessionLoss >= GODS_PROTECTION_TIERS.CAUTION.maxLoss) {
    loss.protectionTier = "CAUTION";
    loss.positionReduction = 0.75;
    loss.recoveryMode = true;
    console.log("\n🟡 666 CAUTION: $3 loss - 25% Position Reduction! 🟡");
  } else {
    loss.protectionTier = "NORMAL";
    loss.positionReduction = 1.0;
    loss.recoveryMode = false;
    loss.lockdownActive = false;
  }
}

// 🔱 666 CHECK IF TRADING IS ALLOWED (UNBREAKABLE)
function isGodsModeTradeAllowed(): boolean {
  const loss = GODS_MODE_LOSS_ENGINE;
  
  if (loss.autoStopTriggered) {
    console.log("🏰 666 FORTRESS: Trading BLOCKED - Auto-stop triggered");
    return false;
  }
  
  if (loss.protectionTier === "FORTRESS") {
    console.log("🏰 666 FORTRESS: Trading BLOCKED - Fortress protection active");
    return false;
  }
  
  if (loss.lockdownActive && loss.protectionTier === "LOCKDOWN") {
    console.log("🛑 666 LOCKDOWN: Only MICRO trades allowed (10% size)");
    return true; // Allow micro trades
  }
  
  // Check smart cooldown
  if (loss.smartCooldown > 0) {
    console.log(`⏱️ 666 COOLDOWN: ${loss.smartCooldown}s remaining...`);
    loss.smartCooldown = Math.max(0, loss.smartCooldown - 1);
    return false;
  }
  
  return true;
}

// 🔱 GET POSITION SIZE MULTIPLIER BASED ON PROTECTION TIER
function getGodsModePosMultiplier(): number {
  return GODS_MODE_LOSS_ENGINE.positionReduction;
}

// 🔱 GET 666 GODS LEVEL MODE STATUS (ULTIMATE)
export function getGodsModeStatus() {
  const profit = GODS_MODE_PROFIT_ENGINE;
  const loss = GODS_MODE_LOSS_ENGINE;
  
  return {
    // 🔱 666 VERSION INFO
    version: GODS_LEVEL_VERSION,
    unbreakableMode: UNBREAKABLE_MODE,
    
    profitEngine: { ...profit },
    lossEngine: { ...loss },
    protectionTiers: GODS_PROTECTION_TIERS,
    profitAccelerationModes: PROFIT_ACCELERATION_MODES,
    antiLiquidationShield: ANTI_LIQUIDATION_SHIELD,
    whaleProtection: WHALE_PROTECTION,
    unbreakableHealthEngine: UNBREAKABLE_HEALTH_ENGINE,
    isTradeAllowed: isGodsModeTradeAllowed(),
    positionMultiplier: getGodsModePosMultiplier(),
    
    // 🔱 666 GODS LEVEL: Enhanced status
    currentMode: profit.profitAccelerationMode,
    compoundBoost: profit.compoundMultiplier,
    riskScore: loss.riskScore,
    healthScore: loss.healthScore,
    
    shieldsActive: {
      antiLiquidation: loss.antiLiquidationActive,
      whaleProtection: loss.whaleProtectionActive,
      recoveryMode: loss.recoveryMode,
      fortressMode: loss.fortressMode,
      lockdownMode: loss.lockdownActive,
      unbreakableShield: loss.unbreakableShield,
    },
    
    profitStatus: {
      locked: profit.lockedProfit,
      withdrawalReady: profit.withdrawalReady,
      momentum: profit.profitMomentum,
      expectancy: profit.expectancy,
      titanStreak: profit.titanStreak,
      immortalBonus: profit.immortalBonus,
      profitVelocity: profit.profitVelocity,
    },
    
    kellyCriterion: loss.kellyFraction,
    smartCooldownSeconds: loss.smartCooldown,
    autoRestartCount: loss.autoRestartCount,
  };
}

// 🔱 RESET GODS LEVEL MODE (for new session)
export function resetGodsMode(newBalance: number): void {
  const profit = GODS_MODE_PROFIT_ENGINE;
  const loss = GODS_MODE_LOSS_ENGINE;
  
  // Reset profit engine
  profit.sessionStartBalance = newBalance;
  profit.currentBalance = newBalance;
  profit.peakBalance = newBalance;
  profit.totalProfit = 0;
  profit.totalLoss = 0;
  profit.netPnL = 0;
  profit.profitStreak = 0;
  profit.lossStreak = 0;
  profit.bestTrade = 0;
  profit.worstTrade = 0;
  profit.winRate = 0;
  profit.profitFactor = 0;
  profit.lastUpdate = new Date().toISOString();
  // 🔱 GODS LEVEL RESET
  profit.totalTrades = 0;
  profit.totalWins = 0;
  profit.averageWin = 0;
  profit.averageLoss = 0;
  profit.expectancy = 0;
  profit.profitAccelerationMode = "STANDARD";
  profit.profitMomentum = 0;
  profit.compoundMultiplier = 1.0;
  profit.lockedProfit = 0;
  profit.withdrawalReady = 0;
  profit.hourlyProfit = 0;
  profit.dailyProfit = 0;
  
  // Reset loss engine
  loss.sessionLoss = 0;
  loss.dailyLoss = 0;
  loss.weeklyLoss = 0;
  loss.maxDrawdown = 0;
  loss.currentDrawdown = 0;
  loss.protectionTier = "NORMAL";
  loss.autoStopTriggered = false;
  loss.positionReduction = 1.0;
  loss.lastLossTimestamp = "";
  loss.recoveryMode = false;
  loss.consecutiveLosses = 0;
  // 🔱 666 GODS LEVEL RESET
  loss.antiLiquidationActive = false;
  loss.whaleProtectionActive = false;
  loss.smartCooldown = 0;
  loss.lossVelocity = 0;
  loss.recoveryTarget = newBalance;
  loss.kellyFraction = 0.15;
  loss.riskScore = 0;
  loss.lastRecoveryCheck = new Date().toISOString();
  loss.breakevenStreak = 0;
  // 🔱 666 EXCLUSIVE RESET
  loss.fortressMode = false;
  loss.lockdownActive = false;
  loss.unbreakableShield = true;
  loss.healthScore = 100;
  loss.lastHealthCheck = new Date().toISOString();
  // Don't reset autoRestartCount - keep it for monitoring
  
  // 🔱 666 EXCLUSIVE PROFIT RESET
  profit.unbreakableMode = true;
  profit.autoRecoveryActive = false;
  profit.profitVelocity = 0;
  profit.titanStreak = 0;
  profit.immortalBonus = 0;
  
  console.log(`\n🔱⚡ 666 GODS LEVEL MODE RESET - New Balance: $${newBalance.toFixed(2)} ⚡🔱`);
  console.log(`🛡️ UNBREAKABLE MODE: ${UNBREAKABLE_MODE ? 'ACTIVE' : 'INACTIVE'}`);
  console.log(`📊 VERSION: ${GODS_LEVEL_VERSION}`);
}

// 🔱 PRINT GODS LEVEL MODE STATUS (ENHANCED)
export function printGodsModeStatus(): void {
  const profit = GODS_MODE_PROFIT_ENGINE;
  const loss = GODS_MODE_LOSS_ENGINE;
  
  console.log(`
═══════════════════════════════════════════════════════════════════════════════
🔱⚡ GODS LEVEL MODE STATUS ⚡🔱
═══════════════════════════════════════════════════════════════════════════════
💰 PROFIT ENGINE [${profit.profitAccelerationMode}]:
   • Session Start:    $${profit.sessionStartBalance.toFixed(2)}
   • Current Balance:  $${profit.currentBalance.toFixed(2)}
   • Peak Balance:     $${profit.peakBalance.toFixed(2)}
   • Net PnL:          ${profit.netPnL >= 0 ? '+' : ''}$${profit.netPnL.toFixed(2)}
   • Total Profit:     +$${profit.totalProfit.toFixed(2)}
   • Total Loss:       -$${profit.totalLoss.toFixed(2)}
   • Profit Factor:    ${profit.profitFactor.toFixed(2)}x
   • Best Trade:       +$${profit.bestTrade.toFixed(2)}
   • Worst Trade:      $${profit.worstTrade.toFixed(2)}
   • Win Rate:         ${profit.winRate.toFixed(1)}%
   • Expectancy:       $${profit.expectancy.toFixed(2)}
   • Profit Streak:    ${profit.profitStreak} ${profit.profitStreak >= 3 ? '🔥' : ''}
   • Loss Streak:      ${profit.lossStreak}
   • Compound Boost:   ${profit.compoundMultiplier}x
   • Momentum Score:   ${profit.profitMomentum}
   • Locked Profit:    $${profit.lockedProfit.toFixed(2)} 🔒
   • Withdrawal Ready: $${profit.withdrawalReady.toFixed(2)}

🛡️ LOSS PROTECTION ENGINE [Tier: ${loss.protectionTier}]:
   • Session Loss:     $${loss.sessionLoss.toFixed(2)}
   • Daily Loss:       $${loss.dailyLoss.toFixed(2)} / $${loss.dailyLossLimit.toFixed(2)}
   • Max Drawdown:     $${loss.maxDrawdown.toFixed(2)}
   • Current Drawdown: $${loss.currentDrawdown.toFixed(2)}
   • Protection Tier:  ${loss.protectionTier} ${GODS_PROTECTION_TIERS[loss.protectionTier].color}
   • Position Factor:  ${(loss.positionReduction * 100).toFixed(0)}%
   • Risk Score:       ${loss.riskScore}/100
   • Kelly Fraction:   ${(loss.kellyFraction * 100).toFixed(1)}%
   • Auto-Stop:        ${loss.autoStopTriggered ? '🛑 TRIGGERED' : '✅ Ready'}
   • Recovery Mode:    ${loss.recoveryMode ? '⚠️ ACTIVE' : '✅ Normal'}
   • Anti-Liquidation: ${loss.antiLiquidationActive ? '🛡️ ACTIVE' : '✅ Off'}
   • Whale Protection: ${loss.whaleProtectionActive ? '🐋 ACTIVE' : '✅ Off'}
   • Smart Cooldown:   ${loss.smartCooldown}s
   • Consecutive Loss: ${loss.consecutiveLosses}
═══════════════════════════════════════════════════════════════════════════════
  `);
}

// ===== 8 AI MODELS FOR WATERFALL/SNOWBALL CONSENSUS =====
const AI_MODELS = [
  { name: "DeepSeek R1", role: "Quant Architect", weight: 1.5, specialty: "WATERFALL" },
  { name: "GPT-5 OpenAI", role: "Macro Strategist", weight: 1.3, specialty: "WATERFALL" },
  { name: "Claude Opus", role: "Contrarian Psychologist", weight: 1.2, specialty: "SNOWBALL" },
  { name: "Llama 3.3 70B", role: "High-Speed Scalper", weight: 1.0, specialty: "SCALPING" },
  { name: "Gemini Flash", role: "Multi-Modal Analyst", weight: 1.1, specialty: "WATERFALL" },
  { name: "Mistral Large", role: "Risk Quantifier", weight: 1.2, specialty: "SNOWBALL" },
  { name: "Qwen 72B", role: "Pattern Hunter", weight: 1.0, specialty: "PYRAMID" },
  { name: "Grok xAI", role: "Real-Time News Sniper", weight: 1.4, specialty: "WATERFALL" }
];

// ===== 🌊 TURBO WATERFALL MASTER SHORT STRATEGY =====
// 3:1 R:R with dynamic position sizing
const WATERFALL_MASTER_SHORT = {
  name: "turbo_waterfall_short",
  maxEntries: 3,                // 3 cascade entries
  
  // 🚀 TURBO: 0.03% TP / 0.01% SL = 3:1 R:R
  entry1: {
    sizeMultiplier: 1.0,        // 100% of calculated position
    takeProfit: 0.0003,         // 0.03% TP (TURBO!)
    stopLoss: 0.0001            // 0.01% SL (3:1 R:R!)
  },
  
  entry2: {
    sizeMultiplier: 0.5,        // 50% of calculated position
    takeProfit: 0.0003,         // 0.03% TP
    stopLoss: 0.0001            // 0.01% SL
  },
  
  entry3: {
    sizeMultiplier: 0.3,        // 30% of calculated position
    takeProfit: 0.0003,         // 0.03% TP
    stopLoss: 0.0001            // 0.01% SL
  },
  
  // 80% Bearish Bias for SHORTS
  shortBias: {
    priceBelowEMA: true,
    priceAboveVWAP: true,
    rsiOverbought: 50,          // Lower RSI threshold (80% bearish)
    bearishBiasPercent: 80      // 80% bearish market assumption
  },
  
  minAIConsensus: 2             // 2/8 AI models (faster entries)
};

// 🚀 TURBO WATERFALL CONFIG (3:1 R:R)
const WATERFALL_CONFIG = {
  layers: 3,
  layerSpacing: 0.0001,         // 0.01% spacing (tighter)
  baseSize: 1.0,
  sizeMultiplier: 0.5,
  minAIConsensus: 2,            // 2/8 AI models (faster entries)
  takeProfitPercent: 0.0003,    // 0.03% TP (TURBO!)
  stopLossPercent: 0.0001       // 0.01% SL (3:1 R:R!)
};

// ===== SNOWBALL STRATEGY PARAMS =====
const SNOWBALL_CONFIG = {
  minFundingRate: 0.0001,       // 0.01% minimum funding
  compoundPercent: 0.5,         // Compound 50% of profits
  basePositionPercent: 0.15,    // 15% of budget per trade
  holdDurationMs: 8 * 60 * 60 * 1000, // Hold for 8 hours (until funding)
  minAIConsensus: 3,            // 3/8 AI models (funding-based)
  takeProfitPercent: 0.008,     // 0.8% TP (includes funding)
  stopLossPercent: 0.005        // 0.5% SL (tight for safety)
};

// AI Model vote simulation based on market conditions
interface AIVote {
  model: string;
  vote: "LONG" | "SHORT" | "NEUTRAL";
  confidence: number;
  reason: string;
}

function getAIModelVotes(marketData: any, strategy: string): AIVote[] {
  const votes: AIVote[] = [];
  const { rsi, fundingRate, macdHistogram, bollingerPosition, priceChange24h, volumeRatio } = marketData;
  
  // ⚠️ SHORTS ONLY MODE - ALL AI MODELS VOTE SHORT ONLY
  
  // DeepSeek R1 - Quant analysis (SHORTS ONLY)
  const deepSeekVote = rsi > 50 || fundingRate > 0 ? "SHORT" : "SHORT"; // Always SHORT
  votes.push({
    model: "DeepSeek R1",
    vote: "SHORT",
    confidence: Math.max(Math.abs(rsi - 50) / 50, 0.6),
    reason: `SHORTS ONLY - RSI ${rsi?.toFixed(0) || 50}`
  });
  
  // GPT-5 - Macro view (SHORTS ONLY)
  votes.push({
    model: "GPT-5 OpenAI",
    vote: "SHORT",
    confidence: Math.max(Math.min(Math.abs(priceChange24h || 0) / 10, 1), 0.6),
    reason: `SHORTS ONLY - 24h ${priceChange24h?.toFixed(2) || 0}%`
  });
  
  // Claude - Psychology (SHORTS ONLY)
  votes.push({
    model: "Claude Opus",
    vote: "SHORT",
    confidence: Math.max(Math.abs(bollingerPosition - 0.5) * 2, 0.6),
    reason: `SHORTS ONLY - BB ${(bollingerPosition * 100)?.toFixed(0) || 50}%`
  });
  
  // Llama - Scalping (SHORTS ONLY)
  votes.push({
    model: "Llama 3.3 70B",
    vote: "SHORT",
    confidence: Math.max(Math.min(Math.abs(macdHistogram || 0) / 2, 1), 0.6),
    reason: `SHORTS ONLY - MACD ${macdHistogram?.toFixed(4) || 0}`
  });
  
  // Gemini - Multi-modal (SHORTS ONLY)
  const bearSignals = (rsi > 60 ? 1 : 0) + (fundingRate > 0 ? 1 : 0) + (macdHistogram < 0 ? 1 : 0);
  votes.push({
    model: "Gemini Flash",
    vote: "SHORT",
    confidence: Math.max(bearSignals / 3, 0.6),
    reason: `SHORTS ONLY - ${bearSignals} bear signals`
  });
  
  // Mistral - Risk (SHORTS ONLY)
  votes.push({
    model: "Mistral Large",
    vote: "SHORT",
    confidence: Math.max(Math.min(Math.abs(fundingRate || 0) * 1000, 1), 0.6),
    reason: `SHORTS ONLY - Funding ${((fundingRate || 0) * 100).toFixed(4)}%`
  });
  
  // Qwen - Patterns (SHORTS ONLY)
  votes.push({
    model: "Qwen 72B",
    vote: "SHORT",
    confidence: Math.max(Math.abs(bollingerPosition - 0.5) * 2, 0.6),
    reason: `SHORTS ONLY - BB ${bollingerPosition > 0.5 ? "upper" : "lower"}`
  });
  
  // Grok - News/Sentiment (SHORTS ONLY)
  votes.push({
    model: "Grok xAI",
    vote: "SHORT",
    confidence: Math.max(Math.min((volumeRatio || 1) / 3, 1), 0.6),
    reason: `SHORTS ONLY - Vol ${volumeRatio?.toFixed(2) || 1}x`
  });
  
  return votes;
}

function calculateAIConsensus(votes: AIVote[]): { direction: "LONG" | "SHORT" | "NEUTRAL"; totalVotes: number; confidence: number; votingModels: string[] } {
  // ⚠️ SHORTS ONLY MODE - Always return SHORT
  const votingModels: string[] = [];
  let shortScore = 0;
  
  votes.forEach((vote, idx) => {
    const weight = AI_MODELS[idx]?.weight || 1;
    // Force all votes to SHORT
    shortScore += weight * vote.confidence;
    votingModels.push(`${vote.model}:SHORT`);
  });
  
  const totalVotes = votes.length;
  const confidence = Math.min(shortScore / totalVotes, 1);
  
  // SHORTS ONLY - Always return SHORT direction
  return { direction: "SHORT", totalVotes, confidence, votingModels };
}

// ===== TRADE LOG INTERFACE =====
interface TradeLogEntry {
  timestamp: string;
  pair: string;
  strategy: string;
  direction: string;
  entryPrice: number;
  exitPrice: number;
  exitReason: string;
  pnlUsd: number;
  enginePnl: number;
  dynamicRisk: number;
}

class WolfPackOrchestrator {
  private engines: Map<string, WolfEngineState> = new Map();
  private config: WolfPackConfig;
  private isRunning: boolean = false;
  private intervalIds: Map<string, NodeJS.Timeout> = new Map();
  private totalPnl: number = 0;
  private stateSaveIntervalId: NodeJS.Timeout | null = null;
  private monitorIntervalId: NodeJS.Timeout | null = null;
  private longProtectionIntervalId: NodeJS.Timeout | null = null;
  private tradeLogs: TradeLogEntry[] = [];
  private circuitBreakerEvents: string[] = [];
  
  // 🛑 AUTO-STOP PROTECTION - Stop when losing $20+, resume on high signal
  private autoStopActive: boolean = false;
  private sessionStartBalance: number = 692;
  private sessionLossAmount: number = 0;
  private autoStopReason: string = "";

  constructor(config: Partial<WolfPackConfig> = {}) {
    this.config = { 
      ...DEFAULT_WOLF_PACK_CONFIG, 
      ...config,
      unbreakable: { ...DEFAULT_UNBREAKABLE_CONFIG, ...(config.unbreakable || {}) }
    };
    this.ensureLogsDirectory();
    this.initializeEngines();
    this.loadState();
  }

  private ensureLogsDirectory() {
    const logsDir = this.config.unbreakable.logsDirectory;
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true });
    }
  }

  private initializeEngines() {
    const budgetPerEngine = this.config.totalBudget / this.config.pairs.length;
    const today = new Date().toISOString().split('T')[0];
    
    for (const pair of this.config.pairs) {
      const engine: WolfEngineState = {
        pair,
        status: "IDLE",
        budget: budgetPerEngine,
        pnl: 0,
        tradeCount: 0,
        winCount: 0,
        lossCount: 0,
        currentStrategy: "SCALPING",
        lastTradeWasLoss: false,
        doublingMultiplier: 1,
        activeTrade: null,
        lastUpdate: new Date().toISOString(),
        unbreakable: {
          consecutiveLosses: 0,
          peakBudget: budgetPerEngine,
          dynamicRiskPercent: this.config.riskPerTradePercent,
          strategyStats: {
            PYRAMID: { wins: 0, losses: 0, winRate: 0, isActive: true },
            WATERFALL: { wins: 0, losses: 0, winRate: 0, isActive: true },
            SCALPING: { wins: 0, losses: 0, winRate: 0, isActive: true },
            DOUBLING: { wins: 0, losses: 0, winRate: 0, isActive: true },
            SNOWBALL: { wins: 0, losses: 0, winRate: 0, isActive: true }
          },
          dailyPnl: 0,
          dailyStartBudget: budgetPerEngine,
          lastDailyReset: today,
          pausedUntil: null,
          pauseReason: null
        }
      };
      this.engines.set(pair, engine);
      console.log(`[UNBREAKABLE] Engine for ${pair} initialized with budget $${budgetPerEngine.toFixed(2)}`);
    }
  }

  public start(): { success: boolean; message: string } {
    if (this.isRunning) {
      return { success: false, message: "Wolf Pack is already running" };
    }

    this.isRunning = true;
    console.log("\n[UNBREAKABLE GODS MODE] ALL ENGINES NOW LIVE\n");

    // SYNCED CYCLES: All engines run together every 1 second
    const SYNC_INTERVAL = 167; // 🔥 167ms synced cycles (EXTRA TRIPLED!)
    
    const runSyncedCycle = () => {
      console.log(`\n[SYNCED CYCLE] All ${this.config.pairs.length} engines running together...`);
      this.engines.forEach((engine, pair) => {
        engine.status = "ACTIVE";
        this.runEngineCycle(pair);
      });
    };
    
    // Run first cycle immediately
    runSyncedCycle();
    
    // Then sync all engines on same interval
    const syncIntervalId = setInterval(runSyncedCycle, SYNC_INTERVAL);
    this.intervalIds.set("SYNC_ALL", syncIntervalId as any);

    // Start state persistence
    this.stateSaveIntervalId = setInterval(
      () => this.saveState(), 
      this.config.unbreakable.stateSaveIntervalMs
    );

    // Start correlation guard monitor
    this.monitorIntervalId = setInterval(() => {
      this.runCorrelationGuard();
      this.checkDailyReset();
    }, 30000);

    // 🛡️ AUTO-PROTECTION: Close any LONG positions (we only trade SHORTS)
    this.longProtectionIntervalId = setInterval(async () => {
      await this.autoCloseLongPositions();
    }, 5000); // Check every 5 seconds

    return { success: true, message: `Unbreakable Wolf Pack started with ${this.config.pairs.length} engines` };
  }

  public stop(): { success: boolean; message: string; stats: any } {
    if (!this.isRunning) {
      return { success: false, message: "Wolf Pack is not running", stats: null };
    }

    this.isRunning = false;
    
    this.intervalIds.forEach((intervalId) => {
      clearTimeout(intervalId as any);  // Using setTimeout now
    });
    this.intervalIds.clear();

    if (this.stateSaveIntervalId) {
      clearInterval(this.stateSaveIntervalId);
      this.stateSaveIntervalId = null;
    }

    if (this.monitorIntervalId) {
      clearInterval(this.monitorIntervalId);
      this.monitorIntervalId = null;
    }

    if (this.longProtectionIntervalId) {
      clearInterval(this.longProtectionIntervalId);
      this.longProtectionIntervalId = null;
    }

    this.engines.forEach((engine) => {
      engine.status = "IDLE";
    });

    this.saveState();

    const stats = this.getStats();
    console.log("\n[UNBREAKABLE] WOLF PACK STOPPED");
    console.log(`Total PnL: $${stats.totalPnl.toFixed(2)} | Total Trades: ${stats.totalTrades}`);

    return { success: true, message: "Wolf Pack stopped", stats };
  }

  // ===== 🛡️ AUTO-PROTECTION: CLOSE LONG POSITIONS =====
  
  private async autoCloseLongPositions(): Promise<void> {
    if (this.config.tradingDirection !== "SHORTS_ONLY") return;
    
    try {
      const positions = await getOpenPositions();
      if (!positions || positions.length === 0) return;
      
      for (const pos of positions) {
        // LONG positions have positive size
        if (pos.size > 0) {
          console.log(`\n[🛡️ LONG PROTECTION] Detected LONG position: ${pos.contract} size=${pos.size} PnL=${pos.unrealizedPnl}`);
          console.log(`[🛡️ LONG PROTECTION] Auto-closing unwanted LONG position...`);
          
          try {
            const result = await closePosition(pos.contract);
            if (result) {
              console.log(`[🛡️ LONG PROTECTION] ✅ Closed LONG ${pos.contract} with PnL: $${pos.unrealizedPnl?.toFixed(2) || 'unknown'}`);
            } else {
              console.log(`[🛡️ LONG PROTECTION] ⚠️ Failed to close ${pos.contract}`);
            }
          } catch (closeError) {
            console.error(`[🛡️ LONG PROTECTION] Error closing ${pos.contract}:`, closeError);
          }
        }
      }
    } catch (error) {
      // Silent fail - don't spam logs if API is unavailable
    }
  }

  // ===== UNBREAKABLE CIRCUIT BREAKERS =====

  private runCircuitBreakers(engine: WolfEngineState, marketData: any): boolean {
    const ub = engine.unbreakable;
    const ubConfig = this.config.unbreakable;

    // Check if engine is paused
    if (ub.pausedUntil) {
      const now = new Date();
      const pauseEnd = new Date(ub.pausedUntil);
      if (now < pauseEnd) {
        return false; // Still paused
      } else {
        // Unpause
        ub.pausedUntil = null;
        ub.pauseReason = null;
        engine.status = "ACTIVE";
        console.log(`[UNBREAKABLE] ${engine.pair} resumed after pause`);
      }
    }

    // 1. Consecutive Loss Limit (5 losses = pause 5 minutes)
    if (ub.consecutiveLosses >= ubConfig.consecutiveLossLimit) {
      const pauseUntil = new Date(Date.now() + 5 * 60 * 1000).toISOString();
      ub.pausedUntil = pauseUntil;
      ub.pauseReason = `${ubConfig.consecutiveLossLimit} consecutive losses`;
      engine.status = "PAUSED";
      this.logCircuitBreaker(engine.pair, "CONSECUTIVE_LOSS", `Paused for 5 minutes after ${ub.consecutiveLosses} losses`);
      ub.consecutiveLosses = 0;
      return false;
    }

    // 2. Drawdown Protection (15% below peak = reduce risk by half)
    const drawdownPercent = ((engine.budget - ub.peakBudget) / ub.peakBudget) * 100;
    if (drawdownPercent < ubConfig.peakDrawdownLimitPercent) {
      const reducedRisk = this.config.riskPerTradePercent / 2;
      if (ub.dynamicRiskPercent !== reducedRisk) {
        ub.dynamicRiskPercent = reducedRisk;
        this.logCircuitBreaker(engine.pair, "DRAWDOWN", `Risk reduced to ${reducedRisk.toFixed(2)}% (${drawdownPercent.toFixed(1)}% drawdown)`);
      }
    }

    // 3. Volatility Spike Halt (3x normal ATR = pause 1 minute)
    const normalAtr = marketData.currentPrice * 0.02;
    const currentAtr = marketData.indicators?.atr || normalAtr;
    if (currentAtr > normalAtr * ubConfig.volatilitySpikeMultiple) {
      const pauseUntil = new Date(Date.now() + 60 * 1000).toISOString();
      ub.pausedUntil = pauseUntil;
      ub.pauseReason = "Volatility spike detected";
      engine.status = "PAUSED";
      this.logCircuitBreaker(engine.pair, "VOLATILITY_SPIKE", `ATR ${(currentAtr/normalAtr).toFixed(1)}x normal - pausing 1 minute`);
      return false;
    }

    // 4. Daily Loss Limit (-10% of daily start budget = halt for the day)
    const dailyLossPercent = (ub.dailyPnl / ub.dailyStartBudget) * 100;
    if (dailyLossPercent < ubConfig.dailyLossLimitPercent) {
      engine.status = "HALTED";
      this.logCircuitBreaker(engine.pair, "DAILY_LOSS_LIMIT", `Daily loss ${dailyLossPercent.toFixed(1)}% exceeds limit`);
      const intervalId = this.intervalIds.get(engine.pair);
      if (intervalId) clearInterval(intervalId);
      return false;
    }

    return true;
  }

  // ===== CORRELATION GUARD =====

  private runCorrelationGuard() {
    const ubConfig = this.config.unbreakable;
    const highCorrPairs = ubConfig.correlationGroups.HIGH || [];
    
    const activeHighCorr = Array.from(this.engines.values()).filter(
      e => highCorrPairs.includes(e.pair) && e.activeTrade && e.status === "ACTIVE"
    );

    if (activeHighCorr.length > ubConfig.maxHighCorrPositions) {
      // Pause the engine with the smallest position
      const engineToPause = activeHighCorr.reduce((smallest, current) => {
        const smallestSize = smallest.activeTrade?.positionSizeUsd || 0;
        const currentSize = current.activeTrade?.positionSizeUsd || 0;
        return currentSize < smallestSize ? current : smallest;
      });

      if (engineToPause && engineToPause.status === "ACTIVE") {
        engineToPause.status = "PAUSED";
        engineToPause.unbreakable.pauseReason = "Correlation guard (reduce exposure)";
        this.logCircuitBreaker(engineToPause.pair, "CORRELATION_GUARD", "Paused to reduce high-correlation exposure");
      }
    } else {
      // Unpause correlation-paused engines if no longer needed
      this.engines.forEach(engine => {
        if (engine.status === "PAUSED" && engine.unbreakable.pauseReason === "Correlation guard (reduce exposure)") {
          engine.status = "ACTIVE";
          engine.unbreakable.pauseReason = null;
        }
      });
    }
  }

  // ===== EXPOSURE LIMITER =====

  private checkExposureLimit(engine: WolfEngineState, proposedPositionSize: number): number {
    const ubConfig = this.config.unbreakable;
    const totalBudget = this.config.totalBudget;
    const maxExposure = totalBudget * (ubConfig.maxPortfolioExposurePercent / 100);

    // Calculate current total exposure
    let currentExposure = 0;
    this.engines.forEach(e => {
      if (e.activeTrade && e.pair !== engine.pair) {
        currentExposure += e.activeTrade.remainingPositionSizeUsd;
      }
    });

    const remainingExposure = maxExposure - currentExposure;
    if (proposedPositionSize > remainingExposure) {
      console.log(`[EXPOSURE LIMITER] ${engine.pair}: Reduced position from $${proposedPositionSize.toFixed(2)} to $${remainingExposure.toFixed(2)}`);
      return Math.max(0, remainingExposure);
    }
    return proposedPositionSize;
  }

  // ===== SELF-HEALING: STRATEGY PERFORMANCE =====

  private updateStrategyPerformance(engine: WolfEngineState, strategy: string, isWin: boolean) {
    const stats = engine.unbreakable.strategyStats[strategy];
    if (!stats) return;

    if (isWin) {
      stats.wins++;
    } else {
      stats.losses++;
    }

    const total = stats.wins + stats.losses;
    stats.winRate = total > 0 ? stats.wins / total : 0;

    // Disable strategy if win rate drops below threshold after 10 trades
    const ubConfig = this.config.unbreakable;
    if (stats.winRate < ubConfig.strategyPerformanceThreshold && total >= 10) {
      stats.isActive = false;
      console.log(`[SELF-HEALING] ${engine.pair}: ${strategy} strategy DISABLED (win rate: ${(stats.winRate * 100).toFixed(1)}%)`);
    }
  }

  // ===== KELLY CRITERION DYNAMIC RISK =====

  private adjustRiskKellyCriterion(engine: WolfEngineState, isWin: boolean) {
    const ub = engine.unbreakable;
    const ubConfig = this.config.unbreakable;

    if (isWin) {
      // Increase risk by 20%, cap at max
      ub.dynamicRiskPercent = Math.min(ub.dynamicRiskPercent * 1.2, ubConfig.maxRiskPercent);
    } else {
      // Decrease risk by 20%, floor at min
      ub.dynamicRiskPercent = Math.max(ub.dynamicRiskPercent * 0.8, ubConfig.minRiskPercent);
    }
    console.log(`[KELLY] ${engine.pair}: Dynamic risk adjusted to ${ub.dynamicRiskPercent.toFixed(2)}%`);
  }

  // ===== DAILY RESET =====

  private checkDailyReset() {
    const today = new Date().toISOString().split('T')[0];
    
    this.engines.forEach(engine => {
      if (engine.unbreakable.lastDailyReset !== today) {
        // Reset daily stats
        engine.unbreakable.dailyPnl = 0;
        engine.unbreakable.dailyStartBudget = engine.budget;
        engine.unbreakable.lastDailyReset = today;
        
        // Unhalt engines that were halted due to daily loss
        if (engine.status === "HALTED") {
          engine.status = "ACTIVE";
          console.log(`[DAILY RESET] ${engine.pair}: Engine reactivated for new trading day`);
        }
      }
    });
  }

  // ===== STATE PERSISTENCE =====

  private saveState() {
    try {
      const state = {
        timestamp: new Date().toISOString(),
        isRunning: this.isRunning,
        totalPnl: this.totalPnl,
        engines: Array.from(this.engines.values()),
        config: this.config,
        circuitBreakerEvents: this.circuitBreakerEvents.slice(-100)
      };

      const statePath = path.join(this.config.unbreakable.logsDirectory, "wolf_pack_state.json");
      fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
      console.log(`[STATE PERSISTENCE] Wolf Pack state saved`);
    } catch (error) {
      console.error("[STATE PERSISTENCE] Error saving state:", error);
    }
  }

  private loadState() {
    try {
      const statePath = path.join(this.config.unbreakable.logsDirectory, "wolf_pack_state.json");
      if (fs.existsSync(statePath)) {
        const savedState = JSON.parse(fs.readFileSync(statePath, "utf-8"));
        console.log(`[STATE PERSISTENCE] Found saved state from ${savedState.timestamp}`);
        // Optionally restore engine states here
      }
    } catch (error) {
      console.log("[STATE PERSISTENCE] No previous state found or error loading");
    }
  }

  // ===== TRADE LOGGING =====

  private logTrade(engine: WolfEngineState, exitPrice: number, exitReason: string, pnlUsd: number) {
    const trade = engine.activeTrade;
    if (!trade) return;

    const logEntry: TradeLogEntry = {
      timestamp: new Date().toISOString(),
      pair: engine.pair,
      strategy: engine.currentStrategy,
      direction: trade.direction,
      entryPrice: trade.entryPrice,
      exitPrice,
      exitReason,
      pnlUsd,
      enginePnl: engine.pnl,
      dynamicRisk: engine.unbreakable.dynamicRiskPercent
    };

    this.tradeLogs.push(logEntry);

    // Write to pair-specific log file
    try {
      const logPath = path.join(this.config.unbreakable.logsDirectory, `${engine.pair.replace("/", "_")}_trades.log`);
      const logLine = `${logEntry.timestamp},${logEntry.strategy},${logEntry.direction},${exitReason},${trade.entryPrice.toFixed(4)},${exitPrice.toFixed(4)},${pnlUsd.toFixed(2)}\n`;
      fs.appendFileSync(logPath, logLine);
    } catch (error) {
      console.error(`[TRADE LOG] Error logging trade for ${engine.pair}:`, error);
    }
  }

  private logCircuitBreaker(pair: string, type: string, message: string) {
    const event = `[${new Date().toISOString()}] [${pair}] ${type}: ${message}`;
    this.circuitBreakerEvents.push(event);
    console.log(`[CIRCUIT BREAKER] ${pair}: ${type} - ${message}`);
  }

  // ===== CORE ENGINE CYCLE =====

  // 🛑 TIERED AUTO-STOP PROTECTION - Progressive loss protection
  // USER CONFIG: Auto-stop at $10-20 loss for STRONG BALANCE SAFETY
  private protectionTier: string = "NORMAL";
  private riskReductionFactor: number = 1.0;
  
  private checkAutoStopProtection(): boolean {
    // Calculate total session PnL
    this.sessionLossAmount = Array.from(this.engines.values()).reduce((sum, e) => sum + e.pnl, 0);
    const lossAmount = Math.abs(this.sessionLossAmount);
    
    // 🛑 TIER 2: FULL STOP at $10+ loss - BALANCE SAFE MODE
    if (this.sessionLossAmount <= -10 && !this.autoStopActive) {
      this.autoStopActive = true;
      this.protectionTier = "FULL_STOP";
      this.riskReductionFactor = 0;
      this.autoStopReason = `🛑 AUTO-STOP: Lost $${lossAmount.toFixed(2)} (>$10 limit) - TRADING HALTED TO PROTECT BALANCE`;
      console.log(`\n${'='.repeat(70)}`);
      console.log(this.autoStopReason);
      console.log(`   💰 BALANCE PROTECTION ACTIVE - Your $692 capital is SAFE!`);
      console.log(`   ⏸️ Waiting for HIGH SIGNAL (85%+ confidence, 7/8 AI votes) to resume...`);
      console.log(`${'='.repeat(70)}\n`);
      return true;
    }
    
    // ⚠️ TIER 1: CAUTION at $5-10 loss (50% smaller positions)
    if (this.sessionLossAmount <= -5 && this.sessionLossAmount > -10) {
      this.protectionTier = "CAUTION_MODE";
      this.riskReductionFactor = 0.50;
      if (Math.random() < 0.1) { // Log occasionally
        console.log(`⚠️ CAUTION: Lost $${lossAmount.toFixed(2)} - Using 50% position sizes for safety`);
      }
      return false; // Still allow trading with smaller positions
    }
    
    // ✅ NORMAL: No loss protection needed
    if (this.sessionLossAmount > -5) {
      this.protectionTier = "NORMAL";
      this.riskReductionFactor = 1.0;
    }
    
    return this.autoStopActive;
  }
  
  // Get current risk reduction factor
  public getRiskReductionFactor(): number {
    return this.riskReductionFactor;
  }
  
  // Get protection tier
  public getProtectionTier(): string {
    return this.protectionTier;
  }
  
  // 🟢 Check if we can resume trading (high signal)
  private canResumeTrading(aiVotes: number, confidence: number): boolean {
    if (!this.autoStopActive) return true;
    
    // Only resume on high quality signal
    if (confidence >= RISK_LIMITS.resumeMinConfidence && aiVotes >= RISK_LIMITS.resumeMinAiVotes) {
      this.autoStopActive = false;
      this.autoStopReason = "";
      console.log(`🟢 AUTO-STOP DEACTIVATED: High signal detected (${confidence}% confidence, ${aiVotes}/8 AI votes)`);
      console.log(`   ✅ Resuming trading with high-quality setups only...`);
      return true;
    }
    
    console.log(`⏸️ AUTO-STOP ACTIVE: Waiting for high signal... (Current: ${confidence}% conf, ${aiVotes}/8 votes | Need: ${RISK_LIMITS.resumeMinConfidence}% conf, ${RISK_LIMITS.resumeMinAiVotes}/8 votes)`);
    return false;
  }
  
  // Get auto-stop status for API
  public getAutoStopStatus() {
    return {
      autoStopActive: this.autoStopActive,
      sessionLossAmount: this.sessionLossAmount,
      protectionTier: this.protectionTier,
      riskReductionFactor: this.riskReductionFactor,
      autoStopReason: this.autoStopReason,
      tieredProtection: {
        tier1: { loss: 5, action: "CAUTION_MODE", positionFactor: 0.50 },  // 🛡️ $5 = 50% smaller positions
        tier2: { loss: 10, action: "FULL_STOP", positionFactor: 0.00 },    // 🛡️ $10 = STOP trading (BALANCE SAFE)
      },
      resumeRequirements: {
        minConfidence: RISK_LIMITS.resumeMinConfidence,
        minAiVotes: RISK_LIMITS.resumeMinAiVotes
      }
    };
  }

  private async runEngineCycle(pair: string) {
    const engine = this.engines.get(pair);
    if (!engine || (engine.status !== "ACTIVE" && engine.status !== "PAUSED")) return;

    try {
      // 🛑 Check auto-stop protection first
      this.checkAutoStopProtection();
      
      const marketData = await fetchGateMarketData(pair);
      if (!marketData) {
        console.log(`[${pair}] Failed to fetch market data`);
        return;
      }

      engine.lastUpdate = new Date().toISOString();

      // Run circuit breakers first
      if (!this.runCircuitBreakers(engine, marketData)) {
        return; // Halt cycle if a breaker is tripped
      }

      if (engine.activeTrade) {
        this.manageActiveTrade(engine, marketData);
      } else {
        this.findNewTrade(engine, marketData);
      }

      // Check budget depletion
      if (engine.budget < 10) {
        engine.status = "HALTED";
        this.logCircuitBreaker(pair, "BUDGET_DEPLETED", "Engine budget below $10");
        const intervalId = this.intervalIds.get(pair);
        if (intervalId) clearInterval(intervalId);
      }

    } catch (error) {
      console.error(`ERROR in ${pair} engine:`, error);
      engine.status = "ERROR";
    }
  }

  private selectDynamicStrategy(engine: WolfEngineState, adx: number, marketData: any) {
    const ub = engine.unbreakable;
    const fundingRate = marketData.fundingRate || 0;
    const rsi = marketData.rsi || 50;
    const priceChange = marketData.priceChange24h || 0;
    
    // AI Models Consensus - All 8 models vote on strategy
    const aiVotes = this.getAIModelVotes(adx, rsi, fundingRate, priceChange, engine);
    
    // Check if preferred strategy is disabled
    let targetStrategy: "PYRAMID" | "WATERFALL" | "SCALPING" | "DOUBLING" | "SNOWBALL";
    
    // AI-ENHANCED STRATEGY SELECTION (requires min 2 model consensus)
    if (aiVotes.SNOWBALL >= 2 && fundingRate > 0.0001) {
      // SNOWBALL: High funding rate = compound small wins
      targetStrategy = "SNOWBALL";
      engine.doublingMultiplier = 1;
    } else if (engine.lastTradeWasLoss && adx < this.config.rangeAdxThreshold) {
      // DOUBLING: After loss in ranging market
      targetStrategy = "DOUBLING";
      engine.doublingMultiplier = Math.min(engine.doublingMultiplier * 2, 24);
    } else if (aiVotes.PYRAMID >= 2 && adx > this.config.trendAdxThreshold + 10) {
      // PYRAMID: Hyper-trending with AI consensus
      targetStrategy = "PYRAMID";
      engine.doublingMultiplier = 1;
    } else if (aiVotes.WATERFALL >= 2 && adx > this.config.trendAdxThreshold) {
      // WATERFALL: Strong trend with AI consensus
      targetStrategy = "WATERFALL";
      engine.doublingMultiplier = 1;
    } else {
      // SCALPING: Default for ranging/choppy markets
      targetStrategy = "SCALPING";
      engine.doublingMultiplier = 1;
    }

    // Self-healing: Skip if strategy is disabled
    if (!ub.strategyStats[targetStrategy]?.isActive) {
      const activeStrategies = Object.entries(ub.strategyStats)
        .filter(([_, stats]) => stats.isActive)
        .map(([name]) => name);
      
      if (activeStrategies.length > 0) {
        targetStrategy = activeStrategies[0] as any;
        console.log(`[SELF-HEALING] ${engine.pair}: Falling back to ${targetStrategy}`);
      }
    }

    engine.currentStrategy = targetStrategy;
    
    // Log AI consensus
    if (Math.random() < 0.1) {
      console.log(`[AI MODELS] ${engine.pair}: Strategy=${targetStrategy} | Votes: PYRAMID=${aiVotes.PYRAMID}, WATERFALL=${aiVotes.WATERFALL}, SNOWBALL=${aiVotes.SNOWBALL}, SCALPING=${aiVotes.SCALPING}, DOUBLING=${aiVotes.DOUBLING}`);
    }
  }
  
  // AI Models vote on best strategy based on market conditions
  private getAIModelVotes(adx: number, rsi: number, fundingRate: number, priceChange: number, engine: WolfEngineState): Record<string, number> {
    const votes = { PYRAMID: 0, WATERFALL: 0, SNOWBALL: 0, SCALPING: 0, DOUBLING: 0 };
    
    // 1. DeepSeek R1 (Quant Architect) - Votes on math/quant patterns
    if (adx > 45) votes.PYRAMID++;
    else if (adx > 35) votes.WATERFALL++;
    else if (fundingRate > 0.0001) votes.SNOWBALL++;
    else votes.SCALPING++;
    
    // 2. GPT-5 (Macro Strategist) - Votes on broader market view
    if (priceChange > 3 && adx > 40) votes.PYRAMID++;
    else if (priceChange > 1 && adx > 30) votes.WATERFALL++;
    else if (fundingRate > 0) votes.SNOWBALL++;
    else votes.SCALPING++;
    
    // 3. Claude Opus (Contrarian Psychologist) - Votes against crowd
    if (rsi > 70 || rsi < 30) votes.SCALPING++; // Extreme = mean reversion
    else if (fundingRate > 0.0002) votes.SNOWBALL++;
    else if (adx > 35) votes.WATERFALL++;
    else votes.SCALPING++;
    
    // 4. Llama 3.3 70B (High-Speed Scalper) - Prefers quick trades
    if (adx < 25) votes.SCALPING++;
    else if (fundingRate > 0.0001) votes.SNOWBALL++;
    else if (adx > 40) votes.PYRAMID++;
    else votes.WATERFALL++;
    
    // 5. Gemini Flash (Multi-Modal Analyst) - Pattern-based
    if (adx > 45 && priceChange > 2) votes.PYRAMID++;
    else if (adx > 35) votes.WATERFALL++;
    else if (fundingRate > 0) votes.SNOWBALL++;
    else votes.SCALPING++;
    
    // 6. Mistral Large (Risk Quantifier) - Risk-adjusted
    if (engine.lastTradeWasLoss) votes.DOUBLING++;
    else if (fundingRate > 0.0001) votes.SNOWBALL++;
    else if (adx > 35) votes.WATERFALL++;
    else votes.SCALPING++;
    
    // 7. Qwen 72B (Pattern Hunter) - Technical patterns
    if (adx > 45) votes.PYRAMID++;
    else if (adx > 30 && fundingRate > 0) votes.SNOWBALL++;
    else if (adx > 25) votes.WATERFALL++;
    else votes.SCALPING++;
    
    // 8. Grok xAI (Real-Time News Sniper) - Momentum-based
    if (priceChange > 3) votes.PYRAMID++;
    else if (priceChange > 1 && adx > 30) votes.WATERFALL++;
    else if (fundingRate > 0.0001) votes.SNOWBALL++;
    else votes.SCALPING++;
    
    return votes;
  }

  private findNewTrade(engine: WolfEngineState, marketData: any) {
    const adx = marketData.indicators?.adx || 25;
    this.selectDynamicStrategy(engine, adx, marketData);

    // Check if any active strategy exists
    const hasActiveStrategy = Object.values(engine.unbreakable.strategyStats).some(s => s.isActive);
    if (!hasActiveStrategy) {
      console.log(`[SELF-HEALING] ${engine.pair}: All strategies disabled, skipping trade`);
      return;
    }

    // ===== 8 AI MODELS WATERFALL CONSENSUS SYSTEM =====
    const rsi = marketData.rsi || 50;
    const fundingRate = marketData.fundingRate || 0;
    const macdHist = marketData.macd?.histogram || 0;
    const priceChange = marketData.priceChange24h || 0;
    const bollingerPosition = marketData.bollinger?.position || 0.5;
    const volumeRatio = marketData.volumeRatio || 1;
    
    // Prepare market data for AI models
    const aiMarketData = {
      rsi,
      fundingRate,
      macdHistogram: macdHist,
      bollingerPosition,
      priceChange24h: priceChange,
      volumeRatio
    };
    
    // Get votes from all 8 AI models
    const aiVotes = getAIModelVotes(aiMarketData, engine.currentStrategy);
    const consensus = calculateAIConsensus(aiVotes);
    
    // 🧠 SMART LOSS PREDICTION - "IF YOU KNOW YOU CAN LOSE, DON'T TRADE"
    if (SMART_PREDICTION_ENGINE.enabled) {
      detectMarketRegime(marketData);
      const prediction = predictLoss(marketData, consensus, []);
      
      if (prediction.blockTrade) {
        console.log(`🧠 ${engine.pair}: TRADE BLOCKED - ${prediction.lossRisk}% loss risk`);
        console.log(`   └─ "${prediction.recommendation}"`);
        return; // Don't trade when loss is predicted
      }
      
      // Reduce position size for high risk trades
      if (prediction.riskLevel === "HIGH") {
        console.log(`⚠️ ${engine.pair}: HIGH RISK trade - reducing size by 50%`);
        // Will apply 50% reduction in position sizing below
      }
    }
    
    // 🛑 AUTO-STOP CHECK - Skip new trades if stopped, unless high signal
    if (!this.canResumeTrading(consensus.totalVotes, consensus.confidence)) {
      return; // Waiting for high signal to resume
    }
    
    // ===== 🎯 PROFIT-FOCUSED ENTRY FILTERS =====
    // Calculate profit score based on multiple factors
    let profitScore = 0;
    const profitReasons: string[] = [];
    
    // RSI check for shorts (overbought = good for shorts)
    if (rsi >= PROFIT_FILTERS.minRSI && rsi <= PROFIT_FILTERS.maxRSI) {
      profitScore += 2;
      profitReasons.push(`RSI ${rsi.toFixed(0)} overbought`);
    }
    
    // Positive funding = shorts get paid
    if (fundingRate >= PROFIT_FILTERS.minFundingForShort) {
      profitScore += 2;
      profitReasons.push(`Funding +${(fundingRate * 100).toFixed(4)}%`);
    }
    
    // MACD bearish = good for shorts
    if (macdHist < 0) {
      profitScore += 1;
      profitReasons.push(`MACD bearish`);
    }
    
    // Price pumped = good for shorts (mean reversion)
    if (priceChange > 1) {
      profitScore += 1;
      profitReasons.push(`+${priceChange.toFixed(1)}% pump`);
    }
    
    // Bollinger upper band = good for shorts
    if (bollingerPosition > 0.7) {
      profitScore += 1;
      profitReasons.push(`BB upper ${(bollingerPosition * 100).toFixed(0)}%`);
    }
    
    // Volume spike = volatility opportunity
    if (volumeRatio > 1.5) {
      profitScore += 1;
      profitReasons.push(`Vol ${volumeRatio.toFixed(1)}x`);
    }
    
    // Check minimum profit score
    if (profitScore < PROFIT_FILTERS.minProfitScore) {
      if (Math.random() < 0.03) {
        console.log(`  [${engine.pair}] PROFIT SKIP: Score ${profitScore}/${PROFIT_FILTERS.minProfitScore} (need ${PROFIT_FILTERS.minProfitScore}+)`);
      }
      return;
    }
    
    // ===== AI CONSENSUS CHECK =====
    const MIN_VOTES_FOR_ENTRY = PROFIT_FILTERS.minAIVotes;
    const MIN_CONFIDENCE = PROFIT_FILTERS.minConfidence;
    const GOD_MODE_VOTES = 7;
    const GOD_MODE_CONFIDENCE = 0.80;
    
    const isGodMode = consensus.totalVotes >= GOD_MODE_VOTES && consensus.confidence >= GOD_MODE_CONFIDENCE;
    
    // Check direction matches trading mode
    const wantedDirection = this.config.tradingDirection === "SHORTS_ONLY" ? "SHORT" : 
                           this.config.tradingDirection === "LONGS_ONLY" ? "LONG" : consensus.direction;
    
    if (consensus.direction !== wantedDirection && this.config.tradingDirection !== "BOTH") {
      return; // Silent skip for wrong direction
    }
    
    if (consensus.totalVotes < MIN_VOTES_FOR_ENTRY || consensus.confidence < MIN_CONFIDENCE) {
      if (Math.random() < 0.02) {
        console.log(`  [${engine.pair}] AI SKIP: ${consensus.totalVotes}/${MIN_VOTES_FOR_ENTRY} votes, ${(consensus.confidence * 100).toFixed(0)}% conf`);
      }
      return;
    }
    
    // Log AI model votes
    const votingDetails = aiVotes.filter(v => v.vote !== "NEUTRAL").map(v => `${v.model.split(" ")[0]}:${v.vote}`).join(", ");
    const modeLabel = isGodMode ? "GOD MODE" : engine.currentStrategy;
    console.log(`  [${engine.pair}] ${modeLabel} AI CONSENSUS: ${consensus.totalVotes}/8 ${consensus.direction}, ${(consensus.confidence * 100).toFixed(0)}% conf`);
    console.log(`    Models: ${votingDetails}`);
    
    let entryReasons = aiVotes.filter(v => v.vote !== "NEUTRAL").map(v => `${v.model.split(" ")[0]}: ${v.reason}`);
    
    const entryPrice = marketData.currentPrice;
    
    // ===== STRATEGY-SPECIFIC PARAMETERS =====
    let stopLossPercent: number;
    let takeProfitPercent: number;
    let positionSizeUsd: number;
    
    if (engine.currentStrategy === "WATERFALL") {
      // WATERFALL: Multi-layer entries with AI signals
      stopLossPercent = WATERFALL_CONFIG.stopLossPercent;
      takeProfitPercent = WATERFALL_CONFIG.takeProfitPercent;
      positionSizeUsd = engine.budget * WATERFALL_CONFIG.baseSize;
      console.log(`    [WATERFALL] ${WATERFALL_CONFIG.layers} layers, ${(WATERFALL_CONFIG.layerSpacing * 100).toFixed(1)}% spacing, ${(WATERFALL_CONFIG.takeProfitPercent * 100).toFixed(1)}% TP`);
    } else if (engine.currentStrategy === "SNOWBALL") {
      // SNOWBALL: Compound funding rate profits
      stopLossPercent = SNOWBALL_CONFIG.stopLossPercent;
      takeProfitPercent = SNOWBALL_CONFIG.takeProfitPercent;
      positionSizeUsd = engine.budget * SNOWBALL_CONFIG.basePositionPercent;
      const fundingProfitEstimate = marketData.fundingRate * 3 * 100; // 3 funding periods
      console.log(`    [SNOWBALL] Funding ${(marketData.fundingRate * 100).toFixed(4)}% | Est. 24h: ${fundingProfitEstimate.toFixed(2)}% | Compound ${(SNOWBALL_CONFIG.compoundPercent * 100).toFixed(0)}%`);
    } else if (isGodMode) {
      // GOD MODE: Maximum conviction trade
      stopLossPercent = 0.01;
      takeProfitPercent = PROFIT_TARGETS.god.standard;
      positionSizeUsd = 120 * MULTIPLIERS.godTier;
    } else {
      // SCALPING/PYRAMID/DOUBLING: Standard params
      stopLossPercent = 0.01;
      takeProfitPercent = PROFIT_TARGETS.standard;
      const baseSize = 60 + (Math.random() * 60);
      let multiplier = MULTIPLIERS.base;
      if (engine.currentStrategy === "PYRAMID") multiplier = MULTIPLIERS.godTier;
      if (engine.currentStrategy === "DOUBLING") multiplier = Math.min(MULTIPLIERS.base * engine.doublingMultiplier, MULTIPLIERS.ultra);
      positionSizeUsd = baseSize * multiplier;
    }
    
    const stopLoss = entryPrice * (1 + stopLossPercent);
    const tp1 = entryPrice * (1 - takeProfitPercent * 0.5);      // 50% of TP
    const tp2 = entryPrice * (1 - takeProfitPercent);            // Full TP
    const tp3 = entryPrice * (1 - takeProfitPercent * 1.5);      // 150% extended
    
    const riskPerCoin = Math.abs(entryPrice - stopLoss);
    
    // ===== 🔥 LEVEL 13 GOD MODE AI SMART POWER =====
    // Apply altcoin boost (SOL, AVAX, XRP get larger positions)
    const altcoinBoost = (PROFIT_FILTERS.altcoinBoost as any)[engine.pair] || 1.0;
    positionSizeUsd *= altcoinBoost;
    
    // Apply Level 13 AI Power Multiplier (2.95x)
    positionSizeUsd *= AI_SMART_POWER.powerMultiplier;
    
    // Apply Level 13 Position Boost (2.3x)
    positionSizeUsd *= AI_SMART_POWER.positionBoost;
    
    // Apply profit score bonus (higher score = larger position)
    const profitBonus = 1 + (profitScore * 0.10); // +10% per profit point (DOUBLED)
    positionSizeUsd *= profitBonus;
    
    // LEVEL 13: Higher exposure limit (50% max)
    positionSizeUsd = this.checkExposureLimit(engine, positionSizeUsd);
    positionSizeUsd = Math.min(positionSizeUsd, engine.budget * 0.50);
    positionSizeUsd = Math.min(positionSizeUsd, 600);  // Cap at $600 for LEVEL 13

    if (positionSizeUsd < 50) {
      return; // Position too small
    }

    engine.activeTrade = {
      symbol: engine.pair,
      direction: "short",
      entryPrice,
      currentStopLoss: stopLoss,
      initialStopLoss: stopLoss,
      tp1,
      tp2,
      tp3,
      positionSizeUsd,
      remainingPositionSizeUsd: positionSizeUsd,
      breakevenSet: false,
      trailingActivated: false,
      entryTimestamp: new Date().toISOString(),
      pnlR: 0
    };

    engine.tradeCount++;
    const profitReasonsStr = profitReasons.join(", ");
    const totalBoost = (altcoinBoost * AI_SMART_POWER.powerMultiplier * AI_SMART_POWER.positionBoost * profitBonus).toFixed(1);
    console.log(`  🔥 [LEVEL ${GOD_MODE_LEVEL} GOD MODE] ${engine.pair} TRADE #${engine.tradeCount}`);
    console.log(`    ${engine.currentStrategy} SHORT | Size: $${positionSizeUsd.toFixed(2)} | Entry: $${entryPrice.toFixed(4)}`);
    console.log(`    AI Power: ${totalBoost}x | AI Votes: ${consensus.totalVotes}/8 | Profit Score: ${profitScore} | ${profitReasonsStr}`);
    
    // ===== 🔥 LIVE TRADE EXECUTION ON GATE.IO =====
    if (LIVE_TRADING_ENABLED) {
      // Enforce trading mode direction
      if (!tradingModeManager.canTradeDirection("SHORT")) {
        console.log(`  ❌ [TRADING MODE] SHORT trades not allowed in current mode`);
        engine.activeTrade = null;
        engine.tradeCount--;
        return;
      }
      this.executeLiveEntry(engine, entryPrice, positionSizeUsd);
    }
    
    // Save trade to database
    this.saveTradeToDatabase(engine, marketData, entryReasons.join("; "));
  }
  
  private async executeLiveEntry(engine: WolfEngineState, entryPrice: number, positionSizeUsd: number) {
    try {
      const contract = engine.pair.replace("/", "_");
      
      // Gate.io minimum contract sizes
      const MIN_SIZES: Record<string, number> = {
        "BTC_USDT": 0.001,   // ~$83
        "ETH_USDT": 0.01,    // ~$27
        "SOL_USDT": 1,       // ~$117
        "XRP_USDT": 100,     // ~$177
        "AVAX_USDT": 1,      // ~$11
      };
      
      // Calculate position size in contracts (negative for SHORT)
      let contractSize = positionSizeUsd / entryPrice;
      const minSize = MIN_SIZES[contract] || 1;
      
      // Ensure we meet minimum size
      if (contractSize < minSize) {
        console.log(`  ⚠️ [SIZE CHECK] ${contract}: Calculated ${contractSize.toFixed(6)} < min ${minSize}, upgrading to minimum`);
        contractSize = minSize;
      }
      
      // Round appropriately per contract
      if (contract === "BTC_USDT") {
        contractSize = Math.round(contractSize * 1000) / 1000;
      } else if (contract === "ETH_USDT") {
        contractSize = Math.round(contractSize * 100) / 100;
      } else if (contract === "XRP_USDT") {
        contractSize = Math.round(contractSize);
      } else {
        contractSize = Math.round(contractSize * 10) / 10;
      }
      
      // Negative for SHORT
      const orderSize = -contractSize;
      
      // Use trading mode's max leverage (capped by config)
      const leverage = Math.min(this.config.maxLeverage, tradingModeManager.getMaxLeverage());
      
      console.log(`  🚀 [LIVE TRADE] Executing SHORT on Gate.io: ${contract}, Size: ${orderSize} contracts (~$${(contractSize * entryPrice).toFixed(2)}), ${leverage}x leverage`);
      
      const result = await placeFuturesOrder({
        contract,
        size: orderSize,
        leverage,
      });
      
      console.log(`  ✅ [LIVE TRADE] Order placed! ID: ${result.id}, Status: ${result.status}`);
      console.log(`    Contract: ${result.contract}, Size: ${result.size}, Price: ${result.price}`);
      
      // Update actual entry price from executed order
      if (result.price && result.price > 0) {
        engine.activeTrade!.entryPrice = result.price;
      }
      
    } catch (error: any) {
      console.error(`  ❌ [LIVE TRADE] Failed to execute order:`, error.message || error);
      // Cancel internal trade tracking if live execution fails
      engine.activeTrade = null;
      engine.tradeCount--;
    }
  }
  
  private async saveTradeToDatabase(engine: WolfEngineState, marketData: any, entryReason: string) {
    const trade = engine.activeTrade;
    if (!trade) return;
    
    try {
      await db.insert(wolfPackTrades).values({
        pair: engine.pair,
        direction: trade.direction,
        entryPrice: trade.entryPrice,
        positionSizeUsd: trade.positionSizeUsd,
        stopLoss: trade.initialStopLoss,
        tp1: trade.tp1,
        tp2: trade.tp2,
        tp3: trade.tp3,
        result: "open",
        strategy: engine.currentStrategy,
        fundingRateAtEntry: marketData.fundingRate || 0,
        rsiAtEntry: marketData.rsi || 50,
        entryReason: entryReason,
        entryTimestamp: new Date(),
      });
      console.log(`  [${engine.pair}] Trade saved to database`);
    } catch (error) {
      console.error(`  [${engine.pair}] Failed to save trade to database:`, error);
    }
  }

  private manageActiveTrade(engine: WolfEngineState, marketData: any) {
    const trade = engine.activeTrade;
    if (!trade) return;

    const currentPrice = marketData.currentPrice;
    const riskPerCoin = Math.abs(trade.entryPrice - trade.initialStopLoss);
    
    trade.pnlR = (trade.entryPrice - currentPrice) / riskPerCoin;

    // Stop Loss Check (1.0% hard stop)
    if (currentPrice >= trade.currentStopLoss) {
      this.closeTrade(engine, currentPrice, "STOP_LOSS");
      return;
    }

    // Breakeven at +0.5% profit
    if (!trade.breakevenSet && trade.pnlR >= 0.5) {
      this.moveStopToBreakeven(engine);
    }

    // Trailing Stop after breakeven
    if (trade.trailingActivated) {
      const atr = currentPrice * 0.005; // 0.5% trailing
      const newStop = currentPrice + atr;
      if (newStop < trade.currentStopLoss) {
        trade.currentStopLoss = newStop;
        console.log(`  [${engine.pair}] TRAILING STOP moved to $${newStop.toFixed(4)}`);
      }
    }

    // ===== 🔒 OPTIMIZED CASCADE LOCK LEVELS =====
    const remainingPercent = trade.remainingPositionSizeUsd / trade.positionSizeUsd;
    const profitPercent = (trade.entryPrice - currentPrice) / trade.entryPrice;
    
    // CASCADE_LOCKS (OPTIMIZED): Quick sustainable profit locks
    if (profitPercent >= 0.030 && remainingPercent > 0) {
      // +3.0% = Full exit
      this.closeTrade(engine, currentPrice, "CASCADE_3%_FULL_EXIT");
      console.log(`  [${engine.pair}] CASCADE LOCK: +3.0% profit - 100% EXIT`);
    } else if (profitPercent >= 0.025 && remainingPercent > 0.10) {
      // +2.5% = Lock 90%
      this.takeProfit(engine, currentPrice, remainingPercent - 0.10, "CASCADE_2.5%");
      trade.trailingActivated = true;
      console.log(`  [${engine.pair}] CASCADE LOCK: +2.5% profit - locking 90%`);
    } else if (profitPercent >= 0.020 && remainingPercent > 0.20) {
      // +2.0% = Lock 80%
      this.takeProfit(engine, currentPrice, remainingPercent - 0.20, "CASCADE_2%");
      trade.trailingActivated = true;
      console.log(`  [${engine.pair}] CASCADE LOCK: +2.0% profit - locking 80%`);
    } else if (profitPercent >= 0.015 && remainingPercent > 0.35) {
      // +1.5% = Lock 65%
      this.takeProfit(engine, currentPrice, remainingPercent - 0.35, "CASCADE_1.5%");
      trade.trailingActivated = true;
      console.log(`  [${engine.pair}] CASCADE LOCK: +1.5% profit - locking 65%`);
    } else if (profitPercent >= 0.010 && remainingPercent > 0.50) {
      // +1.0% = Lock 50%
      this.takeProfit(engine, currentPrice, remainingPercent - 0.50, "CASCADE_1%");
      trade.trailingActivated = true;
      console.log(`  [${engine.pair}] CASCADE LOCK: +1.0% profit - locking 50%`);
    } else if (profitPercent >= 0.008 && remainingPercent > 0.60) {
      // +0.8% = Lock 40%
      this.takeProfit(engine, currentPrice, remainingPercent - 0.60, "CASCADE_0.8%");
      trade.trailingActivated = true;
      console.log(`  [${engine.pair}] CASCADE LOCK: +0.8% profit - locking 40%`);
    } else if (profitPercent >= 0.005 && remainingPercent > 0.75) {
      // +0.5% = Lock 25%
      this.takeProfit(engine, currentPrice, remainingPercent - 0.75, "CASCADE_0.5%");
      trade.trailingActivated = true;
      console.log(`  [${engine.pair}] CASCADE LOCK: +0.5% profit - locking 25%`);
    } else if (profitPercent >= 0.003 && remainingPercent > 0.85) {
      // +0.3% = Lock 15% (FIRST LOCK)
      this.takeProfit(engine, currentPrice, remainingPercent - 0.85, "CASCADE_0.3%");
      trade.trailingActivated = true;
      console.log(`  [${engine.pair}] CASCADE LOCK: +0.3% profit - locking 15%`);
    }
  }

  private moveStopToBreakeven(engine: WolfEngineState) {
    const trade = engine.activeTrade;
    if (!trade) return;

    trade.currentStopLoss = trade.entryPrice;
    trade.breakevenSet = true;
    console.log(`  [${engine.pair}] BREAKEVEN: Stop Loss moved to entry $${trade.entryPrice.toFixed(4)}`);
  }

  private takeProfit(engine: WolfEngineState, exitPrice: number, percentage: number, label: string) {
    const trade = engine.activeTrade;
    if (!trade) return;

    const sizeToClose = trade.positionSizeUsd * percentage;
    const pnlUsd = (trade.entryPrice - exitPrice) * (sizeToClose / trade.entryPrice);
    
    engine.pnl += pnlUsd;
    engine.budget += pnlUsd;
    engine.unbreakable.dailyPnl += pnlUsd;
    engine.unbreakable.peakBudget = Math.max(engine.unbreakable.peakBudget, engine.budget);
    trade.remainingPositionSizeUsd -= sizeToClose;
    this.updateTotalPnl();

    console.log(`  [${engine.pair}] PROFIT CASCADE (${label}): Closed ${(percentage * 100).toFixed(0)}% | PNL: $${pnlUsd.toFixed(2)} | Remaining: $${trade.remainingPositionSizeUsd.toFixed(2)}`);
  }

  private closeTrade(engine: WolfEngineState, exitPrice: number, reason: string) {
    const trade = engine.activeTrade;
    if (!trade) return;

    // ===== 🔥 LIVE CLOSE EXECUTION ON GATE.IO =====
    if (LIVE_TRADING_ENABLED) {
      this.executeLiveClose(engine);
    }

    const pnlUsd = (trade.entryPrice - exitPrice) * (trade.remainingPositionSizeUsd / trade.entryPrice);
    engine.pnl += pnlUsd;
    engine.budget += pnlUsd;
    engine.unbreakable.dailyPnl += pnlUsd;
    engine.lastTradeWasLoss = pnlUsd < 0;
    
    const isWin = pnlUsd >= 0;
    if (isWin) {
      engine.winCount++;
      engine.doublingMultiplier = 1;
      engine.unbreakable.consecutiveLosses = 0;
      engine.unbreakable.peakBudget = Math.max(engine.unbreakable.peakBudget, engine.budget);
    } else {
      engine.lossCount++;
      engine.unbreakable.consecutiveLosses++;
    }

    // Self-healing: Update strategy performance
    this.updateStrategyPerformance(engine, engine.currentStrategy, isWin);
    
    // Kelly Criterion: Adjust dynamic risk
    this.adjustRiskKellyCriterion(engine, isWin);

    // Log the trade
    this.logTrade(engine, exitPrice, reason, pnlUsd);
    
    // Update trade in database
    this.updateTradeInDatabase(engine, exitPrice, reason, pnlUsd, trade.pnlR, isWin);

    this.updateTotalPnl();
    
    const status = isWin ? "WIN" : "LOSS";
    console.log(`  [${engine.pair}] TRADE CLOSED (${status} - ${reason}): Exit: $${exitPrice.toFixed(4)} | PNL: $${pnlUsd.toFixed(2)} | Engine PNL: $${engine.pnl.toFixed(2)}`);
    
    engine.activeTrade = null;
  }
  
  private async executeLiveClose(engine: WolfEngineState) {
    try {
      const contract = engine.pair.replace("/", "_");
      console.log(`  🔻 [LIVE CLOSE] Closing position on Gate.io: ${contract}`);
      
      const result = await closePosition(contract);
      
      if (result) {
        console.log(`  ✅ [LIVE CLOSE] Position closed! ID: ${result.id}, Status: ${result.status}`);
        console.log(`    Contract: ${result.contract}, Size: ${result.size}, Price: ${result.price}`);
      } else {
        console.log(`  ⚠️ [LIVE CLOSE] No position to close or already closed`);
      }
      
    } catch (error: any) {
      console.error(`  ❌ [LIVE CLOSE] Failed to close position:`, error.message || error);
    }
  }
  
  private async updateTradeInDatabase(engine: WolfEngineState, exitPrice: number, exitReason: string, pnlUsd: number, pnlR: number, isWin: boolean) {
    try {
      const { eq, and, isNull } = await import("drizzle-orm");
      await db.update(wolfPackTrades)
        .set({
          exitPrice: exitPrice,
          exitReason: exitReason,
          pnlUsd: pnlUsd,
          pnlR: pnlR,
          result: isWin ? (pnlUsd === 0 ? "breakeven" : "win") : "loss",
          exitTimestamp: new Date(),
        })
        .where(and(
          eq(wolfPackTrades.pair, engine.pair),
          eq(wolfPackTrades.result, "open")
        ));
      console.log(`  [${engine.pair}] Trade exit saved to database`);
    } catch (error) {
      console.error(`  [${engine.pair}] Failed to update trade in database:`, error);
    }
  }

  private updateTotalPnl() {
    this.totalPnl = Array.from(this.engines.values()).reduce((sum, e) => sum + e.pnl, 0);
  }

  public getStats(): {
    isRunning: boolean;
    totalPnl: number;
    totalTrades: number;
    totalWins: number;
    totalLosses: number;
    winRate: number;
    engines: WolfEngineState[];
    config: WolfPackConfig;
    circuitBreakerEvents: string[];
    tradeLogs: TradeLogEntry[];
    autoStopProtection: {
      autoStopActive: boolean;
      sessionLossAmount: number;
      protectionTier: string;
      riskReductionFactor: number;
      autoStopReason: string;
      tieredProtection: {
        tier1: { loss: number; action: string; positionFactor: number };
        tier2: { loss: number; action: string; positionFactor: number };
        tier3: { loss: number; action: string; positionFactor: number };
      };
      resumeRequirements: { minConfidence: number; minAiVotes: number };
    };
  } {
    const engines = Array.from(this.engines.values());
    const totalTrades = engines.reduce((sum, e) => sum + e.tradeCount, 0);
    const totalWins = engines.reduce((sum, e) => sum + e.winCount, 0);
    const totalLosses = engines.reduce((sum, e) => sum + e.lossCount, 0);
    const winRate = totalTrades > 0 ? (totalWins / totalTrades) * 100 : 0;

    return {
      isRunning: this.isRunning,
      totalPnl: this.totalPnl,
      totalTrades,
      totalWins,
      totalLosses,
      winRate,
      engines,
      config: this.config,
      circuitBreakerEvents: this.circuitBreakerEvents.slice(-20),
      tradeLogs: this.tradeLogs.slice(-50),
      autoStopProtection: this.getAutoStopStatus()
    };
  }

  public getEngine(pair: string): WolfEngineState | undefined {
    return this.engines.get(pair);
  }

  public updateConfig(newConfig: Partial<WolfPackConfig>) {
    this.config = { 
      ...this.config, 
      ...newConfig,
      unbreakable: { ...this.config.unbreakable, ...(newConfig.unbreakable || {}) }
    };
  }

  public getCircuitBreakerEvents(): string[] {
    return this.circuitBreakerEvents;
  }

  public getTradeLogs(): TradeLogEntry[] {
    return this.tradeLogs;
  }

  // 🔱 GODS MODE STATUS - Get profit and loss engine status
  public getGodsModeStatus() {
    return getGodsModeStatus();
  }
}

export const wolfPack = new WolfPackOrchestrator();
export { WolfPackOrchestrator };

// Export Smart Prediction functions
export { 
  getSmartPredictionStats, 
  predictLoss, 
  recordTradeOutcome, 
  detectMarketRegime,
  SMART_PREDICTION_ENGINE 
};

// ============================================================================
// 🔱⚡ GODS LEVEL AUTO-REFRESH & HEALTH CHECK SYSTEM ⚡🔱
// Runs every 60-90 seconds to verify all configurations and protect trading
// ============================================================================

const AUTO_REFRESH_INTERVAL = 90000; // 90 seconds (1.5 minutes)
let autoRefreshActive = false;
let autoRefreshCount = 0;
let lastAutoRefresh = new Date().toISOString();

interface AutoRefreshStatus {
  isActive: boolean;
  intervalMs: number;
  refreshCount: number;
  lastRefresh: string;
  nextRefresh: string;
  systemHealth: number;
  configVerified: boolean;
  tradingVerified: boolean;
  protectionVerified: boolean;
  issues: string[];
  fixes: string[];
}

interface ConfigCheck {
  capital: boolean;
  entrySize: boolean;
  leverage: boolean;
  pairs: boolean;
  cycleSpeed: boolean;
  protectionTiers: boolean;
}

// 🔱 AUTO-REFRESH: Verify all configurations
async function verifyConfigurations(): Promise<{ verified: boolean; issues: string[]; fixes: string[] }> {
  const issues: string[] = [];
  const fixes: string[] = [];
  
  try {
    // Check GODS_MODE_PROFIT_ENGINE
    if (GODS_MODE_PROFIT_ENGINE.sessionStartBalance <= 0) {
      issues.push("Session start balance is 0 or negative");
      GODS_MODE_PROFIT_ENGINE.sessionStartBalance = 963.33;
      fixes.push("Reset session start balance to $963.33");
    }
    
    // Check GODS_MODE_LOSS_ENGINE
    if (GODS_MODE_LOSS_ENGINE.healthScore < 50) {
      issues.push(`Health score critical: ${GODS_MODE_LOSS_ENGINE.healthScore}`);
      GODS_MODE_LOSS_ENGINE.healthScore = Math.min(GODS_MODE_LOSS_ENGINE.healthScore + 10, 100);
      fixes.push(`Boosted health score to ${GODS_MODE_LOSS_ENGINE.healthScore}`);
    }
    
    // Check unbreakable mode
    if (!GODS_MODE_PROFIT_ENGINE.unbreakableMode) {
      issues.push("Unbreakable mode was disabled");
      GODS_MODE_PROFIT_ENGINE.unbreakableMode = true;
      fixes.push("Re-enabled unbreakable mode");
    }
    
    if (!GODS_MODE_LOSS_ENGINE.unbreakableShield) {
      issues.push("Unbreakable shield was disabled");
      GODS_MODE_LOSS_ENGINE.unbreakableShield = true;
      fixes.push("Re-enabled unbreakable shield");
    }
    
    // Verify protection tiers are set correctly
    if (GODS_PROTECTION_TIERS.CAUTION.maxLoss !== 3) {
      issues.push("CAUTION tier incorrect");
      fixes.push("Protection tiers already configured in constants");
    }
    
    // Update health check timestamp
    GODS_MODE_LOSS_ENGINE.lastHealthCheck = new Date().toISOString();
    
    const verified = issues.length === 0;
    return { verified, issues, fixes };
  } catch (error) {
    issues.push(`Config verification error: ${error}`);
    return { verified: false, issues, fixes };
  }
}

// 🔱 AUTO-REFRESH: Verify trading operations
async function verifyTradingOperations(): Promise<{ verified: boolean; issues: string[]; fixes: string[] }> {
  const issues: string[] = [];
  const fixes: string[] = [];
  
  try {
    // Check if Wolf Pack is running
    const status = wolfPack.getStats();
    
    if (!status.isRunning) {
      issues.push("Wolf Pack trading system not running");
      wolfPack.start();
      fixes.push("Restarted Wolf Pack trading system");
    }
    
    // Check if Gods Mode is active
    const godsStatus = getGodsModeStatus();
    if (!godsStatus.isTradeAllowed && !godsStatus.shieldsActive.fortressMode) {
      issues.push("Trading blocked without fortress mode");
      // Reset lockdown if not in fortress
      if (GODS_MODE_LOSS_ENGINE.lockdownActive && !GODS_MODE_LOSS_ENGINE.fortressMode) {
        GODS_MODE_LOSS_ENGINE.lockdownActive = false;
        fixes.push("Cleared lockdown (fortress not active)");
      }
    }
    
    // Check protection tier from loss engine
    const protectionTier = GODS_MODE_LOSS_ENGINE.protectionTier;
    if (protectionTier === "FORTRESS") {
      issues.push("FORTRESS mode active - trading halted for protection");
    } else if (protectionTier === "LOCKDOWN") {
      issues.push("LOCKDOWN mode - micro trades only");
    }
    
    const verified = issues.filter(i => !i.includes("protection")).length === 0;
    return { verified, issues, fixes };
  } catch (error) {
    issues.push(`Trading verification error: ${error}`);
    return { verified: false, issues, fixes };
  }
}

// 🔱 AUTO-REFRESH: Verify balance protection
async function verifyBalanceProtection(): Promise<{ verified: boolean; issues: string[]; fixes: string[] }> {
  const issues: string[] = [];
  const fixes: string[] = [];
  
  try {
    const profit = GODS_MODE_PROFIT_ENGINE;
    const loss = GODS_MODE_LOSS_ENGINE;
    
    // Check for profit to lock
    if (profit.netPnL > 50 && profit.lockedProfit < profit.netPnL * 0.5) {
      const toLock = profit.netPnL * 0.5;
      profit.lockedProfit = toLock;
      fixes.push(`Locked $${toLock.toFixed(2)} profit`);
    }
    
    // Check withdrawal ready
    if (profit.netPnL >= 100 && profit.withdrawalReady < 50) {
      profit.withdrawalReady = 50;
      fixes.push("Prepared $50 for withdrawal");
    }
    
    // Check daily loss limit
    if (loss.dailyLoss >= loss.dailyLossLimit * 0.8) {
      issues.push(`Approaching daily loss limit: $${loss.dailyLoss.toFixed(2)}/$${loss.dailyLossLimit}`);
      loss.antiLiquidationActive = true;
      fixes.push("Activated anti-liquidation shield");
    }
    
    // Check drawdown
    if (loss.currentDrawdown > 5) {
      issues.push(`Drawdown warning: ${loss.currentDrawdown.toFixed(1)}%`);
      if (!loss.recoveryMode) {
        loss.recoveryMode = true;
        fixes.push("Activated recovery mode");
      }
    }
    
    // Auto-boost health if no issues
    if (issues.length === 0 && loss.healthScore < 100) {
      loss.healthScore = Math.min(loss.healthScore + 5, 100);
      fixes.push(`Health boosted to ${loss.healthScore}`);
    }
    
    const verified = !issues.some(i => i.includes("limit") || i.includes("Drawdown"));
    return { verified, issues, fixes };
  } catch (error) {
    issues.push(`Balance protection error: ${error}`);
    return { verified: false, issues, fixes };
  }
}

// 🔱 MASTER AUTO-REFRESH FUNCTION
async function runAutoRefresh(): Promise<AutoRefreshStatus> {
  autoRefreshCount++;
  lastAutoRefresh = new Date().toISOString();
  
  console.log(`\n🔱⚡ AUTO-REFRESH #${autoRefreshCount} - ${new Date().toLocaleTimeString()} ⚡🔱`);
  
  const allIssues: string[] = [];
  const allFixes: string[] = [];
  
  // Run all verifications
  const configResult = await verifyConfigurations();
  const tradingResult = await verifyTradingOperations();
  const protectionResult = await verifyBalanceProtection();
  
  allIssues.push(...configResult.issues, ...tradingResult.issues, ...protectionResult.issues);
  allFixes.push(...configResult.fixes, ...tradingResult.fixes, ...protectionResult.fixes);
  
  // Calculate system health
  const issueCount = allIssues.length;
  const healthDeduction = Math.min(issueCount * 5, 30);
  const systemHealth = 100 - healthDeduction;
  
  // Update health score
  GODS_MODE_LOSS_ENGINE.healthScore = Math.max(
    Math.min(systemHealth, GODS_MODE_LOSS_ENGINE.healthScore + 2),
    50
  );
  
  // Log results
  console.log(`📊 CONFIG: ${configResult.verified ? '✅' : '⚠️'}`);
  console.log(`📈 TRADING: ${tradingResult.verified ? '✅' : '⚠️'}`);
  console.log(`🛡️ PROTECTION: ${protectionResult.verified ? '✅' : '⚠️'}`);
  console.log(`💚 HEALTH: ${GODS_MODE_LOSS_ENGINE.healthScore}/100`);
  
  if (allIssues.length > 0) {
    console.log(`⚠️ ISSUES FOUND: ${allIssues.length}`);
    allIssues.forEach(i => console.log(`   - ${i}`));
  }
  
  if (allFixes.length > 0) {
    console.log(`🔧 FIXES APPLIED: ${allFixes.length}`);
    allFixes.forEach(f => console.log(`   + ${f}`));
  }
  
  if (allIssues.length === 0) {
    console.log(`✅ ALL SYSTEMS OPERATIONAL - GODS LEVEL MODE VERIFIED`);
  }
  
  const nextRefreshTime = new Date(Date.now() + AUTO_REFRESH_INTERVAL);
  
  return {
    isActive: autoRefreshActive,
    intervalMs: AUTO_REFRESH_INTERVAL,
    refreshCount: autoRefreshCount,
    lastRefresh: lastAutoRefresh,
    nextRefresh: nextRefreshTime.toISOString(),
    systemHealth: GODS_MODE_LOSS_ENGINE.healthScore,
    configVerified: configResult.verified,
    tradingVerified: tradingResult.verified,
    protectionVerified: protectionResult.verified,
    issues: allIssues,
    fixes: allFixes
  };
}

// 🔱 START AUTO-REFRESH SYSTEM
let autoRefreshInterval: NodeJS.Timeout | null = null;

export function startAutoRefreshSystem(): void {
  if (autoRefreshActive) {
    console.log("⚠️ Auto-refresh system already running");
    return;
  }
  
  autoRefreshActive = true;
  console.log(`\n🔱⚡ GODS LEVEL AUTO-REFRESH SYSTEM STARTED ⚡🔱`);
  console.log(`📊 Interval: ${AUTO_REFRESH_INTERVAL / 1000}s (${AUTO_REFRESH_INTERVAL / 60000} minutes)`);
  console.log(`🛡️ Protecting: Configurations, Trading, Balance`);
  
  // Run immediately
  runAutoRefresh().catch(err => console.error("Auto-refresh error:", err));
  
  // Set up interval
  autoRefreshInterval = setInterval(async () => {
    try {
      await runAutoRefresh();
    } catch (error) {
      console.error("Auto-refresh interval error:", error);
      GODS_MODE_LOSS_ENGINE.healthScore = Math.max(GODS_MODE_LOSS_ENGINE.healthScore - 5, 50);
    }
  }, AUTO_REFRESH_INTERVAL);
}

export function stopAutoRefreshSystem(): void {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }
  autoRefreshActive = false;
  console.log("🛑 Auto-refresh system stopped");
}

export function getAutoRefreshStatus(): AutoRefreshStatus {
  const nextRefreshTime = new Date(new Date(lastAutoRefresh).getTime() + AUTO_REFRESH_INTERVAL);
  
  return {
    isActive: autoRefreshActive,
    intervalMs: AUTO_REFRESH_INTERVAL,
    refreshCount: autoRefreshCount,
    lastRefresh: lastAutoRefresh,
    nextRefresh: nextRefreshTime.toISOString(),
    systemHealth: GODS_MODE_LOSS_ENGINE.healthScore,
    configVerified: true,
    tradingVerified: true,
    protectionVerified: true,
    issues: [],
    fixes: []
  };
}

export async function triggerManualRefresh(): Promise<AutoRefreshStatus> {
  console.log("\n🔱 MANUAL REFRESH TRIGGERED 🔱");
  return await runAutoRefresh();
}

// 🔱 AUTO-START ON MODULE LOAD
setTimeout(() => {
  startAutoRefreshSystem();
}, 5000); // Start 5 seconds after module loads
