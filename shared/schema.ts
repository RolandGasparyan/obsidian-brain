import { sql } from "drizzle-orm";
import { pgTable, text, varchar, serial, integer, real, timestamp, boolean, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// User table (existing)
export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

// Trading System Types
export type SignalType = "short" | "long" | "neutral";
export type AgentPhase = "sentinel" | "strategist" | "executioner";

export interface AgentConfig {
  id: string;
  name: string;
  role: string;
  phase: AgentPhase;
  icon: string;
  description: string;
  enabled: boolean;
}

export interface MarketData {
  symbol: string;
  currentPrice: number;
  priceChange24h: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  vwap: number;
  rsi: number;
  macd: {
    macd: number;
    signal: number;
    histogram: number;
  };
  bollingerBands: {
    upper: number;
    middle: number;
    lower: number;
  };
  fundingRate: number;
  predictedFundingRate?: number;
  openInterest: number;
  openInterestChange24h?: number;
  longShortRatio: number;
  topTraderLongShortRatio?: number;
  liquidations24h?: {
    longLiquidations: number;
    shortLiquidations: number;
    totalLiquidations: number;
  };
  orderBookImbalance?: number;
  bidAskSpread?: number;
  markPrice?: number;
  indexPrice?: number;
  timestamp: string;
  dataSource: "live" | "simulated";
}

// Gods Mode: Entry Zone with precise levels
export interface EntryZone {
  high: number;
  low: number;
  optimal: number;
  type: string; // OTE, FVG, Liquidity, Harmonic, Institutional
}

// Gods Mode: Target with price and type
export interface TargetLevel {
  price: number;
  type: string;
}

// Gods Mode: Multi-target structure
export interface TargetLevels {
  tp1?: TargetLevel;
  tp2?: TargetLevel;
  tp3?: TargetLevel;
}

export interface AgentAnalysis {
  agentId: string;
  agentName: string;
  agentRole: string;
  signal: SignalType;
  confidence: number;
  reasoning: string;
  keyFindings: string[];
  // Gods Mode: Precise Level Data
  entryZone?: EntryZone;
  stopLoss?: number;
  stopLossReason?: string;
  targets?: TargetLevels;
  levelConfluence?: string[];
  // Legacy fields for backward compatibility
  entryPrice?: number;
  target1?: number;
  target2?: number;
  metadata: Record<string, any>;
  timestamp: string;
}

// Gods Mode: Kill Zone (high-confluence entry zone)
export interface KillZone {
  high: number;
  low: number;
  optimal: number;
  widthPercent: number;
}

// Gods Mode: Confluence Level Classification
export type ConfluenceLevel = "GODLIKE" | "ELITE" | "STRONG" | "MODERATE" | "WEAK";

// Trinity of Profit: Pair Score for API response
export interface TrinityPairScore {
  totalScore: number;
  scores: {
    volatility: number;
    volume: number;
    liquidity: number;
    momentum: number;
    fundingBonus: number;
  };
  recommendedStrategy: TradingStrategy;
}

// Trinity of Profit: Strategy Parameters for API response
export interface TrinityStrategyParams {
  strategy: TradingStrategy;
  leverage: number;
  entrySize: number;
  riskPercent: number;
  targetPercent: number;
  stopLossPercent: number;
  layers?: number;
  maxDoubles?: number;
  description: string;
}

export interface ConsensusResult {
  symbol: string;
  totalAgents: number;
  agreeingAgents: number;
  consensusSignal: SignalType;
  confluenceScore: number;
  agentAnalyses: AgentAnalysis[];
  // Gods Mode: Kill Zone Synthesis
  killZone?: KillZone;
  confluenceLevel: ConfluenceLevel;
  invalidation?: {
    price: number;
    reason: string;
  };
  targets?: {
    tp1: { price: number; exitPercent: number; type: string };
    tp2: { price: number; exitPercent: number; type: string };
    tp3: { price: number; exitPercent: number; type: string };
  };
  riskReward?: {
    toTp1: number;
    toTp2: number;
    toTp3: number;
  };
  // Trinity of Profit: Strategy Data
  pairScore?: TrinityPairScore;
  strategyParams?: TrinityStrategyParams;
  // Legacy fields
  entryZoneHigh?: number;
  entryZoneLow?: number;
  invalidationLevel?: number;
  primaryTarget?: number;
  secondaryTarget?: number;
  riskRewardRatio?: number;
  positionSizeRecommendation?: number;
  verdict: "EXECUTE" | "WAIT" | "NO_TRADE";
  isActionable: boolean;
  timestamp: string;
}

export interface TradeSignal {
  id: string;
  symbol: string;
  direction: SignalType;
  entryPrice: number;
  entryZoneHigh: number;
  entryZoneLow: number;
  stopLoss: number;
  takeProfit1: number;
  takeProfit2?: number;
  positionSizePct: number;
  confluenceScore: number;
  consensusAgents: number;
  reasoning: string;
  timestamp: string;
}

// Analysis history table
export const analysisHistory = pgTable("analysis_history", {
  id: serial("id").primaryKey(),
  symbol: text("symbol").notNull(),
  consensusSignal: text("consensus_signal").notNull(),
  confluenceScore: real("confluence_score").notNull(),
  agreeingAgents: integer("agreeing_agents").notNull(),
  totalAgents: integer("total_agents").notNull(),
  isActionable: boolean("is_actionable").notNull(),
  entryZoneHigh: real("entry_zone_high"),
  entryZoneLow: real("entry_zone_low"),
  invalidationLevel: real("invalidation_level"),
  primaryTarget: real("primary_target"),
  secondaryTarget: real("secondary_target"),
  riskRewardRatio: real("risk_reward_ratio"),
  agentAnalyses: jsonb("agent_analyses"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

export const insertAnalysisSchema = createInsertSchema(analysisHistory).omit({
  id: true,
  createdAt: true,
});

export type InsertAnalysis = z.infer<typeof insertAnalysisSchema>;
export type AnalysisHistory = typeof analysisHistory.$inferSelect;

// Default agents configuration - 8 AI MODELS
export const DEFAULT_AGENTS: AgentConfig[] = [
  {
    id: "grok",
    name: "Grok xAI",
    role: "Real-Time News Sniper",
    phase: "sentinel",
    icon: "Zap",
    description: "Monitors social sentiment, detects narrative exhaustion, identifies 'sell the news' setups",
    enabled: true,
  },
  {
    id: "llama",
    name: "Llama 3.3 70B",
    role: "High-Speed Scalper",
    phase: "sentinel",
    icon: "Timer",
    description: "Analyzes 15-minute charts, identifies displacement, FVGs, and breaker blocks",
    enabled: true,
  },
  {
    id: "gemini",
    name: "Gemini Flash",
    role: "Multi-Modal Analyst",
    phase: "sentinel",
    icon: "Sparkles",
    description: "Cross-market correlation, pattern recognition across timeframes, volatility clustering",
    enabled: true,
  },
  {
    id: "gpt5",
    name: "GPT-5",
    role: "Macro Strategist",
    phase: "strategist",
    icon: "Globe",
    description: "On-chain analysis, derivatives data, funding rates, macro trend assessment",
    enabled: true,
  },
  {
    id: "claude",
    name: "Claude Opus",
    role: "Contrarian Psychologist",
    phase: "strategist",
    icon: "Brain",
    description: "Behavioral finance, sentiment phases, trap identification, max pain analysis",
    enabled: true,
  },
  {
    id: "mistral",
    name: "Mistral Large",
    role: "Risk Quantifier",
    phase: "strategist",
    icon: "Shield",
    description: "Position sizing, risk-adjusted returns, drawdown analysis, Kelly criterion optimization",
    enabled: true,
  },
  {
    id: "deepseek",
    name: "DeepSeek R1",
    role: "Quant Architect",
    phase: "executioner",
    icon: "Calculator",
    description: "Mathematical analysis, liquidity mapping, VWAP deviation, order blocks",
    enabled: true,
  },
  {
    id: "qwen",
    name: "Qwen 72B",
    role: "Pattern Hunter",
    phase: "executioner",
    icon: "TrendingUp",
    description: "Geometric patterns, harmonic patterns, Fibonacci analysis, volume profile",
    enabled: true,
  },
];

// Watchlist symbols
export const WATCHLIST = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"];

// Trinity of Profit: Trading Direction Modes
export type TradingMode = "LONG_ONLY" | "SHORT_ONLY" | "BOTH";

// Trinity of Profit: Strategy Types
export type TradingStrategy = "WATERFALL" | "DOUBLING" | "SNOWBALL" | "SCALPING";

// Trinity of Profit: Pair Scoring for Ultra-Profitable Selection
export interface PairScore {
  symbol: string;
  totalScore: number;
  scores: {
    volatility: number;    // ATR-based (0-25)
    volume: number;        // Volume surge (0-25)
    liquidity: number;     // Spread quality (0-25)
    momentum: number;      // Trend strength (0-25)
    fundingBonus: number;  // High funding rate bonus (0-30)
  };
  recommendedStrategy: TradingStrategy;
  signal?: AgentAnalysis;
}

// Note: StrategyParams is now TrinityStrategyParams in ConsensusResult

// Wolf Pack Trades Table - All executed trades stored in database
export const wolfPackTrades = pgTable("wolf_pack_trades", {
  id: serial("id").primaryKey(),
  pair: text("pair").notNull(),
  direction: text("direction").notNull(), // "short" or "long"
  entryPrice: real("entry_price").notNull(),
  exitPrice: real("exit_price"),
  positionSizeUsd: real("position_size_usd").notNull(),
  stopLoss: real("stop_loss").notNull(),
  tp1: real("tp1").notNull(),
  tp2: real("tp2"),
  tp3: real("tp3"),
  pnlUsd: real("pnl_usd"),
  pnlR: real("pnl_r"),
  result: text("result"), // "win", "loss", "breakeven", "open"
  strategy: text("strategy").notNull(), // "SCALPING", "PYRAMID", "WATERFALL", "DOUBLING"
  fundingRateAtEntry: real("funding_rate_at_entry"),
  rsiAtEntry: real("rsi_at_entry"),
  entryReason: text("entry_reason"),
  exitReason: text("exit_reason"),
  entryTimestamp: timestamp("entry_timestamp").default(sql`CURRENT_TIMESTAMP`).notNull(),
  exitTimestamp: timestamp("exit_timestamp"),
});

export const insertWolfPackTradeSchema = createInsertSchema(wolfPackTrades).omit({
  id: true,
});

export type InsertWolfPackTrade = z.infer<typeof insertWolfPackTradeSchema>;
export type WolfPackTrade = typeof wolfPackTrades.$inferSelect;

// ============================================
// AI TRADING PLATFORM - LEADERBOARD SYSTEM
// ============================================

// AI Models Table - 8 competing AI models
export const aiModels = pgTable("ai_models", {
  id: serial("id").primaryKey(),
  name: text("name").notNull().unique(),
  modelId: text("model_id").notNull(),
  specialty: text("specialty").notNull(),
  tier: text("tier").notNull().default("Novice"),
  level: integer("level").notNull().default(1),
  rankingScore: real("ranking_score").notNull().default(0),
  totalTrades: integer("total_trades").notNull().default(0),
  winningTrades: integer("winning_trades").notNull().default(0),
  losingTrades: integer("losing_trades").notNull().default(0),
  totalProfit: real("total_profit").notNull().default(0),
  totalLoss: real("total_loss").notNull().default(0),
  winRate: real("win_rate").notNull().default(0),
  avgProfitPerTrade: real("avg_profit_per_trade").notNull().default(0),
  currentBalance: real("current_balance").notNull().default(10000),
  startingBalance: real("starting_balance").notNull().default(10000),
  dailyPnl: real("daily_pnl").notNull().default(0),
  startingDailyBalance: real("starting_daily_balance").notNull().default(10000),
  maxDrawdown: real("max_drawdown").notNull().default(0),
  sharpeRatio: real("sharpe_ratio").notNull().default(0),
  isActive: boolean("is_active").notNull().default(true),
  deactivationReason: text("deactivation_reason"),
  lastTradeAt: timestamp("last_trade_at"),
  description: text("description"),
  tradingStrategies: jsonb("trading_strategies"),
  riskManagement: jsonb("risk_management"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

export const insertAIModelSchema = createInsertSchema(aiModels).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertAIModel = z.infer<typeof insertAIModelSchema>;
export type AIModel = typeof aiModels.$inferSelect;

// Trades Table - All AI trading activity
export const aiTrades = pgTable("ai_trades", {
  id: serial("id").primaryKey(),
  aiModelId: integer("ai_model_id").notNull(),
  asset: text("asset").notNull(),
  market: text("market").notNull().default("futures"),
  direction: text("direction").notNull(),
  strategy: text("strategy").notNull(),
  entryPrice: real("entry_price").notNull(),
  exitPrice: real("exit_price"),
  quantity: real("quantity").notNull(),
  leverage: integer("leverage").notNull().default(1),
  profitLoss: real("profit_loss"),
  profitLossPercentage: real("profit_loss_percentage"),
  stopLoss: real("stop_loss").notNull(),
  takeProfit: jsonb("take_profit"),
  status: text("status").notNull().default("open"),
  confidence: real("confidence").notNull(),
  tradingMode: text("trading_mode").notNull().default("NORMAL"),
  reasoning: text("reasoning"),
  openedAt: timestamp("opened_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  closedAt: timestamp("closed_at"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

export const insertAITradeSchema = createInsertSchema(aiTrades).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertAITrade = z.infer<typeof insertAITradeSchema>;
export type AITrade = typeof aiTrades.$inferSelect;

// Predictions Table - User predictions on AI performance
export const predictions = pgTable("predictions", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull(),
  predictionType: text("prediction_type").notNull(),
  predictedAiModelId: integer("predicted_ai_model_id").notNull(),
  periodStart: timestamp("period_start").notNull(),
  periodEnd: timestamp("period_end").notNull(),
  status: text("status").notNull().default("pending"),
  actualWinnerId: integer("actual_winner_id"),
  rewardPoints: integer("reward_points").notNull().default(0),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

export const insertPredictionSchema = createInsertSchema(predictions).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertPrediction = z.infer<typeof insertPredictionSchema>;
export type Prediction = typeof predictions.$inferSelect;

// Market Opportunities Table - Scanned opportunities
export const marketOpportunities = pgTable("market_opportunities", {
  id: serial("id").primaryKey(),
  asset: text("asset").notNull(),
  market: text("market").notNull().default("futures"),
  price: real("price").notNull(),
  volume24h: real("volume_24h").notNull(),
  volatility: real("volatility").notNull(),
  score: real("score").notNull(),
  high24h: real("high_24h").notNull(),
  low24h: real("low_24h").notNull(),
  fundingRate: real("funding_rate"),
  rsi: real("rsi"),
  macdHistogram: real("macd_histogram"),
  scannedAt: timestamp("scanned_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

export const insertMarketOpportunitySchema = createInsertSchema(marketOpportunities).omit({
  id: true,
  createdAt: true,
});

export type InsertMarketOpportunity = z.infer<typeof insertMarketOpportunitySchema>;
export type MarketOpportunity = typeof marketOpportunities.$inferSelect;

// Performance Snapshots Table - Historical performance tracking
export const performanceSnapshots = pgTable("performance_snapshots", {
  id: serial("id").primaryKey(),
  aiModelId: integer("ai_model_id").notNull(),
  balance: real("balance").notNull(),
  totalProfit: real("total_profit").notNull(),
  winRate: real("win_rate").notNull(),
  totalTrades: integer("total_trades").notNull(),
  rankingScore: real("ranking_score").notNull(),
  tier: text("tier").notNull(),
  level: integer("level").notNull(),
  snapshotDate: timestamp("snapshot_date").default(sql`CURRENT_TIMESTAMP`).notNull(),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

export const insertPerformanceSnapshotSchema = createInsertSchema(performanceSnapshots).omit({
  id: true,
  createdAt: true,
});

export type InsertPerformanceSnapshot = z.infer<typeof insertPerformanceSnapshotSchema>;
export type PerformanceSnapshot = typeof performanceSnapshots.$inferSelect;

// Human Traders Table - For comparison
export const humanTraders = pgTable("human_traders", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  totalTrades: integer("total_trades").notNull().default(0),
  winningTrades: integer("winning_trades").notNull().default(0),
  totalProfit: real("total_profit").notNull().default(0),
  winRate: real("win_rate").notNull().default(0),
  avgTradeSpeed: integer("avg_trade_speed").notNull().default(15),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

export const insertHumanTraderSchema = createInsertSchema(humanTraders).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertHumanTrader = z.infer<typeof insertHumanTraderSchema>;
export type HumanTrader = typeof humanTraders.$inferSelect;

// Tier thresholds for ranking score
export const TIER_THRESHOLDS = {
  "Novice": { min: 0, max: 100 },
  "Intermediate": { min: 101, max: 250 },
  "Expert": { min: 251, max: 500 },
  "Master": { min: 501, max: 750 },
  "Legend": { min: 751, max: 1000 },
  "Gods Mode": { min: 1001, max: Infinity }
};

// Trading modes based on confidence
export const TRADING_MODES = {
  AGGRESSIVE: { minConfidence: 0.90, maxConfidence: 1.00, leverageRange: [15, 20], positionSize: [0.02, 0.03] },
  NORMAL: { minConfidence: 0.75, maxConfidence: 0.90, leverageRange: [5, 10], positionSize: [0.01, 0.02] },
  SAFE: { minConfidence: 0.50, maxConfidence: 0.75, leverageRange: [2, 5], positionSize: [0.005, 0.01] },
  NO_TRADE: { minConfidence: 0, maxConfidence: 0.50, leverageRange: [0, 0], positionSize: [0, 0] }
};

// Balance tiers for dynamic scaling
export const BALANCE_TIERS = {
  STARTER: { min: 0, max: 10000, tradeFrequency: 300, positionMultiplier: 1.0 },
  GROWTH: { min: 10000, max: 25000, tradeFrequency: 180, positionMultiplier: 1.2 },
  ACCELERATE: { min: 25000, max: 50000, tradeFrequency: 120, positionMultiplier: 1.4 },
  ELITE: { min: 50000, max: 100000, tradeFrequency: 90, positionMultiplier: 1.6 },
  GODS: { min: 100000, max: Infinity, tradeFrequency: 60, positionMultiplier: 2.0 }
};

// ============================================
// TRADING SYSTEM CONFIGURATION - PERSISTENT
// ============================================
export const tradingConfig = pgTable("trading_config", {
  id: serial("id").primaryKey(),
  configName: text("config_name").notNull().unique().default("default"),
  
  // Core Trading Settings
  totalCapital: real("total_capital").notNull().default(692),
  entrySize: real("entry_size").notNull().default(33),
  riskPerTradePercent: real("risk_per_trade_percent").notNull().default(4.8),
  maxLeverage: integer("max_leverage").notNull().default(5),
  
  // Cycle Settings
  cycleIntervalMs: integer("cycle_interval_ms").notNull().default(2500),
  maxTradesPerDay: integer("max_trades_per_day").notNull().default(400),
  
  // Trading Pairs
  tradingPairs: jsonb("trading_pairs"),
  tradingDirection: text("trading_direction").notNull().default("BOTH"),
  
  // Balance Protection
  dailyLossLimitPercent: real("daily_loss_limit_percent").notNull().default(5),
  maxDrawdownPercent: real("max_drawdown_percent").notNull().default(8),
  protectedBalancePercent: real("protected_balance_percent").notNull().default(92),
  
  // Tiered Stop Protection
  tier1LossUsd: real("tier1_loss_usd").notNull().default(5),
  tier1ReductionPercent: real("tier1_reduction_percent").notNull().default(50),
  tier2LossUsd: real("tier2_loss_usd").notNull().default(10),
  tier2ReductionPercent: real("tier2_reduction_percent").notNull().default(75),
  tier3LossUsd: real("tier3_loss_usd").notNull().default(15),
  
  // Position Sizing
  minPositionUsd: real("min_position_usd").notNull().default(33),
  maxPositionUsd: real("max_position_usd").notNull().default(66),
  defaultPositionUsd: real("default_position_usd").notNull().default(33),
  
  // Take Profit / Stop Loss
  takeProfitPercent: real("take_profit_percent").notNull().default(1.5),
  stopLossPercent: real("stop_loss_percent").notNull().default(0.8),
  
  // Withdrawal Settings
  coldWalletAddress: text("cold_wallet_address").default("0x8c710b67b2d8a8a6065480dA2Bcd110878a2a09D"),
  withdrawThresholdUsd: real("withdraw_threshold_usd").notNull().default(100),
  withdrawToWalletPercent: real("withdraw_to_wallet_percent").notNull().default(50),
  reinvestPercent: real("reinvest_percent").notNull().default(50),
  
  // AI Model Settings
  minConsensusVotes: integer("min_consensus_votes").notNull().default(6),
  minConfidencePercent: real("min_confidence_percent").notNull().default(70),
  
  // System Status
  isActive: boolean("is_active").notNull().default(true),
  lastUpdatedAt: timestamp("last_updated_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

export const insertTradingConfigSchema = createInsertSchema(tradingConfig).omit({
  id: true,
  createdAt: true,
  lastUpdatedAt: true,
});

export type InsertTradingConfig = z.infer<typeof insertTradingConfigSchema>;
export type TradingConfig = typeof tradingConfig.$inferSelect;
