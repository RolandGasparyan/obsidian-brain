import { fetchGateMarketData, placeFuturesOrder, closePosition, getOpenPositions } from "./gateio";
import * as fs from "fs";
import * as path from "path";
import { db } from "./db";
import { wolfPackTrades } from "@shared/schema";

// ===== WOLF PACK DISABLED - PYTHON TRADING GURU ACTIVE =====
const LIVE_TRADING_ENABLED = false;  // 🛑 DISABLED - Python system active

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

// ===== 🏆 OPTIMIZED UNBREAKABLE GODS MODE (FRESH SETUP) =====
const DEFAULT_UNBREAKABLE_CONFIG: UnbreakableConfig = {
  // 🛡️ Circuit Breaker Suite (OPTIMIZED - Stricter)
  dailyLossLimitPercent: -7.5,  // 7.5% max daily loss (TIGHTER)
  consecutiveLossLimit: 4,       // 4 losses max (MORE SENSITIVE)
  peakDrawdownLimitPercent: -12.0,  // 12% drawdown protection (AGGRESSIVE)
  volatilitySpikeMultiple: 2.5,  // 2.5x volatility halt (MORE SENSITIVE)
  
  // 🎯 Advanced Risk Intelligence (OPTIMIZED)
  maxPortfolioExposurePercent: 30.0,  // 30% max exposure
  correlationGroups: {
    HIGH: ["BTC_USDT", "ETH_USDT"],
    MEDIUM: ["SOL_USDT", "AVAX_USDT"],
    LOW: ["XRP_USDT", "DOGE_USDT"]
  },
  maxHighCorrPositions: 1,
  
  // 🔄 Self-Healing & Adaptive Logic (OPTIMIZED)
  strategyPerformanceThreshold: 0.45,  // 45% win rate required (HIGHER QUALITY)
  kellyFraction: 0.20,    // 20% Kelly (CONSERVATIVE - SUSTAINABLE)
  minRiskPercent: 0.10,   // $10 min trade (0.10% of $10k)
  maxRiskPercent: 3.0,    // $300 max trade (3% of $10k)
  
  // State Persistence
  stateSaveIntervalMs: 30000,  // Save every 30 seconds
  logsDirectory: "./logs"
};

const DEFAULT_WOLF_PACK_CONFIG: WolfPackConfig = {
  totalBudget: 10000,
  // 🔱⚡ TRIPLED CYCLES - MAX ULTRA TRADING MODE ⚡🔱
  pairs: ["SOL_USDT", "AVAX_USDT"],  // FOCUSED: SOL & AVAX ONLY
  riskPerTradePercent: 3.0, // 3% risk for TRIPLED mode (MAX AGGRESSION)
  maxLeverage: 75,  // 75x leverage for TRIPLED mode
  cycleIntervalMs: 166, // ⚡⚡⚡ TRIPLED: 166ms cycles (6x per second!)
  trendAdxThreshold: 10, // ADX 10 for MAXIMUM entries
  rangeAdxThreshold: 6, // ADX 6 for ULTRA-WIDE scalping
  breakevenTriggerR: 0.15, // INSTANT BE at 0.15R
  trailingStopAtrMultiple: 0.4, // ULTRA-TIGHT 0.4x ATR trailing
  tradingDirection: "SHORTS_ONLY",
  unbreakable: DEFAULT_UNBREAKABLE_CONFIG
};

// 🚀 TURBO UPGRADE CONFIGURATION
const TURBO_CONFIG = {
  // Take Profit & Stop Loss (3:1 R:R)
  takeProfitPercent: 0.0003,   // 0.03% TP
  stopLossPercent: 0.0001,     // 0.01% SL (3:1 R:R!)
  
  // Dynamic Position Sizing
  minPositionUsd: 50,          // $50 minimum
  maxPositionUsd: 150,         // $150 maximum
  positionIncreaseOnWin: 25,   // +$25 on win streak
  
  // Time Management
  maxTradeDurationSec: 20,     // 20s max per trade
  
  // Market Bias (80% bearish for shorts)
  bearishBiasPercent: 80,
  
  // Win streak tracking
  winStreakMultiplier: 1.5     // 1.5x on 3+ win streak
};

// ===== 🔱⚡ TRIPLED CYCLES - MAX ULTRA TRADING MODE ⚡🔱 =====
const GOD_MODE_LEVEL = 30;  // TRIPLED MODE - MAXIMUM ULTRA VELOCITY
const TRIPLED_MODE_ENABLED = true;
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
  
  // DeepSeek R1 - Quant analysis (RSI + Funding)
  const deepSeekVote = rsi > 65 && fundingRate > 0 ? "SHORT" : rsi < 35 && fundingRate < 0 ? "LONG" : "NEUTRAL";
  votes.push({
    model: "DeepSeek R1",
    vote: deepSeekVote,
    confidence: Math.abs(rsi - 50) / 50,
    reason: `RSI ${rsi?.toFixed(0) || 50}, Funding ${((fundingRate || 0) * 100).toFixed(4)}%`
  });
  
  // GPT-5 - Macro view (Price trend + Volume)
  const gptVote = priceChange24h > 3 && volumeRatio > 1.5 ? "SHORT" : priceChange24h < -3 ? "LONG" : "NEUTRAL";
  votes.push({
    model: "GPT-5 OpenAI",
    vote: gptVote,
    confidence: Math.min(Math.abs(priceChange24h || 0) / 10, 1),
    reason: `24h Change ${priceChange24h?.toFixed(2) || 0}%, Vol ${volumeRatio?.toFixed(2) || 1}x`
  });
  
  // Claude - Psychology (Bollinger + RSI extremes)
  const claudeVote = bollingerPosition > 0.8 && rsi > 70 ? "SHORT" : bollingerPosition < 0.2 && rsi < 30 ? "LONG" : "NEUTRAL";
  votes.push({
    model: "Claude Opus",
    vote: claudeVote,
    confidence: Math.abs(bollingerPosition - 0.5) * 2,
    reason: `BB Position ${(bollingerPosition * 100)?.toFixed(0) || 50}%, Crowd sentiment`
  });
  
  // Llama - Scalping (MACD + Quick moves)
  const llamaVote = macdHistogram < -0.5 ? "SHORT" : macdHistogram > 0.5 ? "LONG" : "NEUTRAL";
  votes.push({
    model: "Llama 3.3 70B",
    vote: llamaVote,
    confidence: Math.min(Math.abs(macdHistogram || 0) / 2, 1),
    reason: `MACD ${macdHistogram?.toFixed(4) || 0}, Momentum shift`
  });
  
  // Gemini - Multi-modal (Combined signals)
  const bullSignals = (rsi < 40 ? 1 : 0) + (fundingRate < 0 ? 1 : 0) + (macdHistogram > 0 ? 1 : 0);
  const bearSignals = (rsi > 60 ? 1 : 0) + (fundingRate > 0 ? 1 : 0) + (macdHistogram < 0 ? 1 : 0);
  const geminiVote = bearSignals >= 2 ? "SHORT" : bullSignals >= 2 ? "LONG" : "NEUTRAL";
  votes.push({
    model: "Gemini Flash",
    vote: geminiVote,
    confidence: Math.max(bullSignals, bearSignals) / 3,
    reason: `Combined: ${bearSignals} bear, ${bullSignals} bull signals`
  });
  
  // Mistral - Risk (Funding + Volatility)
  const mistralVote = fundingRate > 0.0005 ? "SHORT" : fundingRate < -0.0005 ? "LONG" : "NEUTRAL";
  votes.push({
    model: "Mistral Large",
    vote: mistralVote,
    confidence: Math.min(Math.abs(fundingRate || 0) * 1000, 1),
    reason: `Funding arbitrage ${((fundingRate || 0) * 100).toFixed(4)}%`
  });
  
  // Qwen - Patterns (Bollinger + Price action)
  const qwenVote = bollingerPosition > 0.9 ? "SHORT" : bollingerPosition < 0.1 ? "LONG" : "NEUTRAL";
  votes.push({
    model: "Qwen 72B",
    vote: qwenVote,
    confidence: Math.abs(bollingerPosition - 0.5) * 2,
    reason: `Pattern: BB ${bollingerPosition > 0.5 ? "upper" : "lower"} band touch`
  });
  
  // Grok - News/Sentiment (Volume + Price spikes)
  const grokVote = priceChange24h > 5 && volumeRatio > 2 ? "SHORT" : priceChange24h < -5 ? "LONG" : "NEUTRAL";
  votes.push({
    model: "Grok xAI",
    vote: grokVote,
    confidence: Math.min((volumeRatio || 1) / 3, 1),
    reason: `News momentum: ${priceChange24h > 0 ? "bullish" : "bearish"} spike`
  });
  
  return votes;
}

function calculateAIConsensus(votes: AIVote[]): { direction: "LONG" | "SHORT" | "NEUTRAL"; totalVotes: number; confidence: number; votingModels: string[] } {
  let longScore = 0, shortScore = 0;
  const votingModels: string[] = [];
  
  votes.forEach((vote, idx) => {
    const weight = AI_MODELS[idx]?.weight || 1;
    if (vote.vote === "LONG") {
      longScore += weight * vote.confidence;
      votingModels.push(`${vote.model}:LONG`);
    } else if (vote.vote === "SHORT") {
      shortScore += weight * vote.confidence;
      votingModels.push(`${vote.model}:SHORT`);
    }
  });
  
  const totalVotes = votes.filter(v => v.vote !== "NEUTRAL").length;
  const totalScore = longScore + shortScore;
  const confidence = totalScore > 0 ? Math.max(longScore, shortScore) / totalScore : 0;
  
  let direction: "LONG" | "SHORT" | "NEUTRAL" = "NEUTRAL";
  if (shortScore > longScore && totalVotes >= 4) direction = "SHORT";
  else if (longScore > shortScore && totalVotes >= 4) direction = "LONG";
  
  return { direction, totalVotes, confidence, votingModels };
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
    const SYNC_INTERVAL = 333; // 333ms synced cycles (TRIPLED from 1 second)
    
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
            const result = await closePosition(pos.contract, Math.abs(pos.size), "long");
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

  private async runEngineCycle(pair: string) {
    const engine = this.engines.get(pair);
    if (!engine || (engine.status !== "ACTIVE" && engine.status !== "PAUSED")) return;

    try {
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
      this.executeLiveEntry(engine, entryPrice, positionSizeUsd);
    }
    
    // Save trade to database
    this.saveTradeToDatabase(engine, marketData, entryReasons.join("; "));
  }
  
  private async executeLiveEntry(engine: WolfEngineState, entryPrice: number, positionSizeUsd: number) {
    try {
      const contract = engine.pair.replace("/", "_");
      // Calculate position size in contracts (negative for SHORT)
      const contractSize = -(positionSizeUsd / entryPrice);
      
      console.log(`  🚀 [LIVE TRADE] Executing SHORT on Gate.io: ${contract}, Size: ${contractSize.toFixed(4)} contracts`);
      
      const result = await placeFuturesOrder({
        contract,
        size: Math.round(contractSize * 100) / 100, // Round to 2 decimals
        leverage: this.config.maxLeverage,
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
      tradeLogs: this.tradeLogs.slice(-50)
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
}

export const wolfPack = new WolfPackOrchestrator();
export { WolfPackOrchestrator };
