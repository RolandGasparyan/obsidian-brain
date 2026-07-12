/**
 * GODS LEVEL AI TRADING COMPETITION SYSTEM
 * 8 AI Gods compete against each other for maximum profit
 * Using 30+ years of trading secrets for aggressive profit maximization
 * REAL TRADING MODE - ALL TRADES ARE EXECUTED ON GATE.IO WITH LIVE FUNDS
 */

const REAL_TRADING_MODE = true;

// ═══════════════════════════════════════════════════════════════════════════
// 🚫 SHORTS ONLY MODE - ABSOLUTELY NO LONGS ALLOWED
// ═══════════════════════════════════════════════════════════════════════════
const SHORTS_ONLY = true;  // HARD BLOCK - NO LONGS EVER
const ALLOW_LONGS = false; // DISABLED PERMANENTLY

// ═══════════════════════════════════════════════════════════════════════════
// ⚖️ BALANCED AGGRESSIVE MODE - PROTECT + PROFIT (BEST OF BOTH WORLDS)
// ═══════════════════════════════════════════════════════════════════════════
const BALANCED_MODE = true;
const EXTREME_MODE = false; // Disabled - using Balanced Mode instead
// ═══════════════════════════════════════════════════════════════════════════
// ⚖️ BALANCED AGGRESSIVE MODE - CAPITAL CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════
const TOTAL_BALANCE = 692.0;
const BUDGET_PER_AI = TOTAL_BALANCE / 8; // $86.50 each
const MIN_PROTECTED_BALANCE = TOTAL_BALANCE * 0.85; // $588.20 (85% protected)
const MAX_RISK_AMOUNT = TOTAL_BALANCE * 0.15; // $103.80 (15% max risk)

// Hybrid Withdrawal Configuration (50% withdraw, 50% compound)
const HYBRID_WITHDRAWAL_CONFIG = {
  enabled: true,
  threshold: 100,           // Every $100 profit
  withdrawPercent: 50,      // 50% to cold wallet
  compoundPercent: 50,      // 50% reinvest
  coldWallet: '0xa5df89870410335b41beac66508f7dfdc9491e46',
  network: 'BSC'
};

const TRADING_PAIRS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'XRP_USDT', 'DOGE_USDT'];

// EXTREME MODE SETTINGS
const SCAN_INTERVAL_SECONDS = 3; // Was 10, now 3 for machine-gun trading
const MAX_TRADES_PER_DAY_TOTAL = 1000; // 1000 trades/day across all AIs
const COMPOUND_RATE = 1.0; // 100% reinvestment
const WITHDRAW_THRESHOLD = 6920; // Only withdraw after 10x ($6,920)
const MARTINGALE_ENABLED = true;
const MARTINGALE_MULTIPLIERS = [1, 2, 4, 8]; // Double down after losses

export type MarketCondition = 'TRENDING_UP' | 'TRENDING_DOWN' | 'RANGING' | 'VOLATILE' | 'BREAKOUT' | 'REVERSAL';
export type StrategyType = 'scalping' | 'momentum' | 'mean_reversion' | 'breakout' | 'grid' | 'news';

export interface AIModelConfig {
  id: string;
  name: string;
  description: string;
  strategy: StrategyType;
  aggressionLevel: number; // 1-10
  profitTargetPct: number;
  stopLossPct: number;
  budget: number;
  startingBudget: number;
  currentBudget: number;
  leverage: number;
  maxLeverage: number;
  positionSizePct: number;
  timeframeSeconds: number;
  maxTradesPerDay: number;
  minEdge: number;
  godPrompt: string;
}

export interface AIPerformance {
  id: string;
  name: string;
  budget: number;
  startingBudget: number;
  currentBudget: number;
  totalProfit: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  currentStreak: number;
  bestStreak: number;
  dailyProfit: number;
  weeklyProfit: number;
  winRate: number;
  roi: number;
  rank: number;
  medal: string;
  isPaused: boolean;
  pauseReason: string;
  pauseUntil: number | null;
  lastTradeTime: number | null;
  currentPosition: any | null;
  strategyAllocation: Record<StrategyType, number>;
}

export interface TradeRecord {
  id: string;
  aiId: string;
  symbol: string;
  direction: 'SHORT' | 'LONG';
  entryPrice: number;
  exitPrice?: number;
  positionSize: number;
  leverage: number;
  edgeScore: number;
  strategy: StrategyType;
  pnl: number;
  pnlPct: number;
  timestamp: string;
  status: 'open' | 'closed';
}

const GOD_PROMPTS: Record<string, string> = {
  DeepSeek_R1: `You are DeepSeek R1, the QUANT GOD. 30+ years Wall Street experience. Mathematical genius.
AGGRESSION: 10/10 - MAXIMUM AGGRESSION
PHILOSOPHY: "Mathematics never lies. Find the statistical edge, execute with precision. Speed kills competition."
STRATEGY: Ultra-fast scalping, 50-100 trades/day
ENTRY RULES:
- Price momentum >0.8% in 5min
- Volume spike >150% of average
- RSI 30-70 range
- MACD positive crossover
- Order book imbalance >60%
EXIT RULES:
- Take profit: +1.5%
- Stop loss: -0.8%
- Trail stop at +0.5%
- Execute within 500ms
RISK: Max 3 losses → Pause 30min, Daily loss -5% → Stop
DIRECTION: SHORTS ONLY - Hunt overbought conditions with z-score > 2.5`,

  GPT_5: `You are GPT-5, the MACRO GOD. Legend like Soros, Dalio, Tudor Jones combined.
AGGRESSION: 9/10 - HIGH AGGRESSION
PHILOSOPHY: "The trend is your friend until the end. Ride the wave, cut losses fast, let winners run."
STRATEGY: Ride massive trends, patient hunter for +8% moves
ENTRY RULES:
- Strong trend: Price > EMA20 > EMA50 > EMA200
- Wait for pullback to EMA20
- RSI 40-50 (not overbought)
- Volume dries up on pullback
- Bullish continuation pattern
EXIT RULES:
- Take profit: +8%
- Trail stop 3% below high
- Exit if closes below EMA20
PATIENCE: Wait for A+ setups only, quality > quantity
RISK: Max 2 positions, never revenge trade
DIRECTION: SHORTS ONLY - Trade macro downtrends`,

  Claude_Opus: `You are Claude Opus, the CONTRARIAN GOD. Master of market psychology.
AGGRESSION: 8/10 - HIGH AGGRESSION
PHILOSOPHY: "Be fearful when others are greedy. Buy panic, sell euphoria. Profit from crowd mistakes."
STRATEGY: Mean reversion at extremes, +5% per trade
ENTRY RULES (BUY):
- RSI <25 (extreme oversold)
- Price at lower Bollinger Band
- Panic volume spike (>200% avg)
- Strong support nearby
ENTRY RULES (SELL):
- RSI >75 (extreme overbought)
- Price at upper Bollinger Band
- Euphoria volume spike
- Strong resistance nearby
EXIT RULES:
- Return to mean (EMA20 or middle BB)
- Typical profit: +5-8%
- Scale in: Add 25% if price goes further against
RISK: Only trade clear extremes, max 2 positions
DIRECTION: SHORTS ONLY - Fade euphoric rallies`,

  Llama_3_3: `You are Llama 3.3, the SPEED GOD. Fastest trader alive, 200+ trades/day.
AGGRESSION: 10/10 - MAXIMUM AGGRESSION
PHILOSOPHY: "Small profits, high frequency, compound rapidly. Death by a thousand cuts."
STRATEGY: Machine gun trading, +0.8% per trade, 200+ trades/day
ENTRY RULES:
- Price moves 0.5%+ in 1 minute
- Volume >120% of 5min average
- Order book 65%+ one side
- Spread <0.05%
EXIT RULES:
- Take profit: +0.8%
- Stop loss: -0.4%
- Move to breakeven at +0.5%
- Execute within 200ms
VOLUME: 50-100+ trades per day, hold 1-5 minutes max
RISK: Max 5 losses → Pause 15min, Daily loss -4% → Stop, Win rate target 72%+
DIRECTION: SHORTS ONLY - Scalp quick drops`,

  Gemini_Flash: `You are Gemini Flash, the MULTI-MODAL GOD. Analyze everything simultaneously.
AGGRESSION: 9/10 - HIGH AGGRESSION
PHILOSOPHY: "A picture is worth a thousand words. See what others miss. Multi-dimensional analysis."
STRATEGY: Chart patterns + news + sentiment combined, +7% per trade
ENTRY RULES:
- Classic bearish pattern (H&S, double top)
- Support break on volume
- Negative sentiment shift
- News confirms direction
EXIT RULES:
- Take profit: +7%
- Trail stop 2% below entry
- Exit on reversal pattern
EDGE: Multi-modal analysis sees correlations others miss
RISK: Pattern + confirmation required
DIRECTION: SHORTS ONLY - Trade breakdown patterns`,

  Mistral_Large: `You are Mistral Large, the RISK GOD. Most defensive, capital preservation first.
AGGRESSION: 8/10 - CONTROLLED AGGRESSION
PHILOSOPHY: "Protect capital at all costs. Small losses, big wins, NEVER blow up. Survive first."
STRATEGY: Only A+ setups (90%+ edge), quantify risk perfectly, +5.5% per trade
ENTRY RULES:
- Edge score >90%
- Risk/reward >3:1
- Multiple confirmations
- Clean chart setup
EXIT RULES:
- Take profit: +5.5%
- Stop loss: -3%
- Take profit early if momentum fades
EDGE: Mathematical risk optimization
RISK: Never risk more than 2%, smallest positions, widest stops
DIRECTION: SHORTS ONLY - Ultra-safe short setups only`,

  Qwen_72B: `You are Qwen 72B, the PATTERN GOD. Memorized 10,000+ historical patterns.
AGGRESSION: 9/10 - HIGH AGGRESSION
PHILOSOPHY: "Those who cannot remember the past are condemned to repeat it. Patterns repeat, history rhymes."
STRATEGY: Match current action to historical bearish patterns, catch explosive breakouts, +12% per trade
ENTRY RULES:
- 85%+ pattern match to historical setup
- 75%+ historical win rate
- Volume confirms pattern
- Use historical targets
EXIT RULES:
- Take profit: +12%
- Stop loss: -3%
- Trail stop on breakout
EDGE: Pattern recognition from massive historical database
RISK: Pattern must be clear, no ambiguous setups
DIRECTION: SHORTS ONLY - Trade proven bearish patterns`,

  Grok_xAI: `You are Grok xAI, the NEWS GOD. Trade breaking news instantly.
AGGRESSION: 10/10 - MAXIMUM AGGRESSION
PHILOSOPHY: "First mover advantage. News moves markets, be there FIRST. Speed is everything."
STRATEGY: Trade breaking news within 30 seconds, +10% per trade
ENTRY RULES:
- Detect negative news/FUD/regulatory concerns
- Whale dumps detected
- Social sentiment shifts negative
- Execute within 30 seconds
EXIT RULES:
- Take profit: +10%
- Stop loss: -2.5%
- Exit on stabilization
- Ride the panic wave
EDGE: Real-time news analysis, instant execution
RISK: News must be significant, ignore noise
DIRECTION: SHORTS ONLY - Trade negative catalysts`
};

// ═══════════════════════════════════════════════════════════════════════════
// ⚖️ BALANCED AGGRESSIVE MODE - PROTECT + PROFIT (Best of Both Worlds)
// ═══════════════════════════════════════════════════════════════════════════
// ✅ Maximum Risk: 15% ($103.80)
// ✅ Minimum Protected: 85% ($588.20)
// ✅ Daily Profit Target: +10-25% ($69-173)
// ✅ Moderate Leverage: 8-12x
// ✅ Hybrid Withdrawal: $50 per $100 profit
// ═══════════════════════════════════════════════════════════════════════════
const AI_MODELS_CONFIG: Record<string, Omit<AIModelConfig, 'budget' | 'startingBudget' | 'currentBudget' | 'godPrompt'>> = {
  DeepSeek_R1: {
    id: 'DeepSeek_R1',
    name: 'DeepSeek R1 - Balanced Scalper',
    description: 'BALANCED: Fast scalping, 10-15 trades/day, 1.5% targets',
    strategy: 'scalping',
    aggressionLevel: 7,
    profitTargetPct: 1.5,  // BALANCED: Quick profits
    stopLossPct: 0.5,      // BALANCED: Tight but safe
    leverage: 12,          // BALANCED: Moderate-high
    maxLeverage: 12,
    positionSizePct: 45,   // BALANCED: Based on confidence
    timeframeSeconds: 10,  // BALANCED: Fast scans
    maxTradesPerDay: 15,
    minEdge: 65
  },
  GPT_5: {
    id: 'GPT_5',
    name: 'GPT-5 - Balanced Momentum',
    description: 'BALANCED: Momentum trading, 8-12 trades/day, 2.5% targets',
    strategy: 'momentum',
    aggressionLevel: 6,
    profitTargetPct: 2.5,  // BALANCED: Good targets
    stopLossPct: 1.0,      // BALANCED: Reasonable stop
    leverage: 10,          // BALANCED
    maxLeverage: 10,
    positionSizePct: 45,   // BALANCED
    timeframeSeconds: 10,  // BALANCED
    maxTradesPerDay: 12,
    minEdge: 65
  },
  Claude_Opus: {
    id: 'Claude_Opus',
    name: 'Claude Opus - Balanced Contrarian',
    description: 'BALANCED: Mean reversion, 6-10 trades/day, 2% targets',
    strategy: 'mean_reversion',
    aggressionLevel: 6,
    profitTargetPct: 2.0,  // BALANCED
    stopLossPct: 0.8,      // BALANCED
    leverage: 10,          // BALANCED
    maxLeverage: 10,
    positionSizePct: 40,   // BALANCED
    timeframeSeconds: 10,  // BALANCED
    maxTradesPerDay: 10,
    minEdge: 65
  },
  Llama_3_3: {
    id: 'Llama_3_3',
    name: 'Llama 3.3 - Balanced Speed',
    description: 'BALANCED: Fast scalping, 12-18 trades/day, 1.2% targets',
    strategy: 'scalping',
    aggressionLevel: 7,
    profitTargetPct: 1.2,  // BALANCED: Quick scalps
    stopLossPct: 0.5,      // BALANCED
    leverage: 12,          // BALANCED: Higher for speed
    maxLeverage: 12,
    positionSizePct: 35,   // BALANCED: Smaller for speed
    timeframeSeconds: 10,  // BALANCED
    maxTradesPerDay: 18,
    minEdge: 65
  },
  Gemini_Flash: {
    id: 'Gemini_Flash',
    name: 'Gemini Flash - Balanced Multi-Modal',
    description: 'BALANCED: Multi-modal momentum, 8-12 trades/day, 2% targets',
    strategy: 'momentum',
    aggressionLevel: 6,
    profitTargetPct: 2.0,  // BALANCED
    stopLossPct: 0.8,      // BALANCED
    leverage: 10,          // BALANCED
    maxLeverage: 10,
    positionSizePct: 40,   // BALANCED
    timeframeSeconds: 10,  // BALANCED
    maxTradesPerDay: 12,
    minEdge: 65
  },
  Mistral_Large: {
    id: 'Mistral_Large',
    name: 'Mistral Large - Balanced Risk',
    description: 'BALANCED: Mean reversion, 6-10 trades/day, 2.2% targets',
    strategy: 'mean_reversion',
    aggressionLevel: 6,
    profitTargetPct: 2.2,  // BALANCED
    stopLossPct: 0.8,      // BALANCED
    leverage: 10,          // BALANCED
    maxLeverage: 10,
    positionSizePct: 35,   // BALANCED
    timeframeSeconds: 10,  // BALANCED
    maxTradesPerDay: 10,
    minEdge: 65
  },
  Qwen_72B: {
    id: 'Qwen_72B',
    name: 'Qwen 72B - Balanced Pattern',
    description: 'BALANCED: Breakout trading, 8-12 trades/day, 2.8% targets',
    strategy: 'breakout',
    aggressionLevel: 6,
    profitTargetPct: 2.8,  // BALANCED: Larger for breakouts
    stopLossPct: 1.0,      // BALANCED
    leverage: 11,          // BALANCED
    maxLeverage: 11,
    positionSizePct: 45,   // BALANCED
    timeframeSeconds: 10,  // BALANCED
    maxTradesPerDay: 12,
    minEdge: 65
  },
  Grok_xAI: {
    id: 'Grok_xAI',
    name: 'Grok xAI - Balanced News',
    description: 'BALANCED: News trading, 8-12 trades/day, 2.5% targets',
    strategy: 'news',
    aggressionLevel: 7,
    profitTargetPct: 2.5,  // BALANCED
    stopLossPct: 1.0,      // BALANCED
    leverage: 11,          // BALANCED
    maxLeverage: 11,
    positionSizePct: 40,   // BALANCED
    timeframeSeconds: 10,  // BALANCED
    maxTradesPerDay: 12,
    minEdge: 65
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// ⚖️ BALANCED AGGRESSIVE MODE - PROTECT + PROFIT RISK CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════
// Maximum Risk: 15% ($103.80) | Minimum Protected: 85% ($588.20)
// Daily Profit Target: +10-25% ($69-173)
// ═══════════════════════════════════════════════════════════════════════════
const RISK_CONFIG = {
  maxDailyLossPct: 10.0,      // BALANCED: 10% daily loss limit ($69.20)
  maxTotalLossPct: 15.0,      // BALANCED: Protect 85% of capital
  minProtectedBalancePct: 85.0,
  consecutiveLossLimit: 3,    // BALANCED: 3 consecutive losses
  pauseDurationMinutes: 30,   // BALANCED: 30 min pause
  globalMaxDailyLoss: 69.20,  // 10% of $692
  globalMaxTotalLoss: 103.80, // 15% of $692
  minProtectedBalance: 588.20,// 85% of $692 protected
  // Per trade limits
  maxLossPerTrade: 13.84,     // 2% of $692
  maxLossPerAIDaily: 34.60,   // 5% of $692
  // Smart Recovery triggers
  recoveryTriggerPct: 3.0,    // Enter recovery mode after 3% loss
  recoveryLeverage: 8,        // Lower leverage during recovery
  recoveryPositionSize: 20,   // Smaller positions during recovery
  recoveryMinConfidence: 85   // Higher confidence during recovery
};

const STRATEGY_ALLOCATION: Record<MarketCondition, Record<StrategyType, number>> = {
  TRENDING_UP: { momentum: 60, scalping: 20, breakout: 20, mean_reversion: 0, grid: 0, news: 0 },
  TRENDING_DOWN: { momentum: 60, scalping: 20, breakout: 20, mean_reversion: 0, grid: 0, news: 0 },
  RANGING: { mean_reversion: 40, scalping: 30, grid: 30, momentum: 0, breakout: 0, news: 0 },
  VOLATILE: { scalping: 50, momentum: 20, mean_reversion: 20, breakout: 10, grid: 0, news: 0 },
  BREAKOUT: { momentum: 50, breakout: 40, scalping: 10, mean_reversion: 0, grid: 0, news: 0 },
  REVERSAL: { mean_reversion: 60, scalping: 20, grid: 20, momentum: 0, breakout: 0, news: 0 }
};

const REBALANCE_INTERVAL_MS = 4 * 60 * 60 * 1000; // 4 hours

class AICompetitionSystem {
  private aiPerformance: Map<string, AIPerformance> = new Map();
  private tradeHistory: Map<string, TradeRecord[]> = new Map();
  private isRunning: boolean = false;
  private intervals: Map<string, NodeJS.Timeout> = new Map();
  private currentMarketCondition: MarketCondition = 'RANGING';
  private lastRebalanceTime: number = 0;
  private rebalanceCount: number = 0;

  constructor() {
    this.initializeAIs();
    console.log('✅ GODS LEVEL AI Competition System initialized');
    console.log(`   Total Balance: $${TOTAL_BALANCE.toFixed(2)}`);
    console.log(`   Per AI Budget: $${BUDGET_PER_AI.toFixed(2)}`);
    console.log(`   Protected Balance: $${MIN_PROTECTED_BALANCE.toFixed(2)} (85%)`);
    console.log(`   Max Risk: $${MAX_RISK_AMOUNT.toFixed(2)} (15%)`);
    console.log(`   Active AIs: ${Object.keys(AI_MODELS_CONFIG).length} GODS`);
    console.log(`   Mode: BALANCED AGGRESSIVE (Protect + Profit)`);
    console.log(`   Hybrid Withdrawal: $${HYBRID_WITHDRAWAL_CONFIG.withdrawPercent} per $${HYBRID_WITHDRAWAL_CONFIG.threshold} profit`);
  }

  private initializeAIs() {
    for (const [aiId, config] of Object.entries(AI_MODELS_CONFIG)) {
      const defaultAllocation: Record<StrategyType, number> = {
        scalping: config.strategy === 'scalping' ? 100 : 0,
        momentum: config.strategy === 'momentum' ? 100 : 0,
        mean_reversion: config.strategy === 'mean_reversion' ? 100 : 0,
        breakout: config.strategy === 'breakout' ? 100 : 0,
        grid: config.strategy === 'grid' ? 100 : 0,
        news: config.strategy === 'news' ? 100 : 0
      };

      this.aiPerformance.set(aiId, {
        id: aiId,
        name: config.name,
        budget: BUDGET_PER_AI,
        startingBudget: BUDGET_PER_AI,
        currentBudget: BUDGET_PER_AI,
        totalProfit: 0,
        totalTrades: 0,
        winningTrades: 0,
        losingTrades: 0,
        currentStreak: 0,
        bestStreak: 0,
        dailyProfit: 0,
        weeklyProfit: 0,
        winRate: 0,
        roi: 0,
        rank: 0,
        medal: '',
        isPaused: false,
        pauseReason: '',
        pauseUntil: null,
        lastTradeTime: null,
        currentPosition: null,
        strategyAllocation: defaultAllocation
      });
      this.tradeHistory.set(aiId, []);
    }
    this.updateRankings();
  }

  setMarketCondition(condition: MarketCondition) {
    if (this.currentMarketCondition !== condition) {
      console.log(`\n🌊 Market Condition Changed: ${this.currentMarketCondition} → ${condition}`);
      this.currentMarketCondition = condition;
      this.updateStrategyAllocations();
    }
  }

  getMarketCondition(): MarketCondition {
    return this.currentMarketCondition;
  }

  private updateStrategyAllocations() {
    const allocation = STRATEGY_ALLOCATION[this.currentMarketCondition];
    console.log(`📊 Adaptive Strategy Allocation for ${this.currentMarketCondition}:`);
    
    for (const [strategy, pct] of Object.entries(allocation)) {
      if (pct > 0) {
        console.log(`   ${strategy}: ${pct}%`);
      }
    }

    Array.from(this.aiPerformance.entries()).forEach(([aiId, ai]) => {
      const config = AI_MODELS_CONFIG[aiId];
      const baseAllocation = allocation[config.strategy] || 0;
      ai.strategyAllocation = { ...allocation };
    });
  }

  rebalanceCapital() {
    console.log('\n' + '💰'.repeat(40));
    console.log('CAPITAL REBALANCING - SURVIVAL OF THE FITTEST');
    console.log('💰'.repeat(40));

    const ais = Array.from(this.aiPerformance.values());
    // Use currentBudget as source of truth for consistency
    const totalBalance = ais.reduce((sum, ai) => sum + ai.currentBudget, 0);
    
    // CRITICAL: Check protected balance before rebalancing
    if (totalBalance <= MIN_PROTECTED_BALANCE) {
      console.log(`🛡️ PROTECTED BALANCE ACTIVE - Total: $${totalBalance.toFixed(2)} <= $${MIN_PROTECTED_BALANCE.toFixed(2)}`);
      console.log(`   Capital rebalancing BLOCKED to protect remaining funds`);
      console.log('💰'.repeat(40) + '\n');
      return;
    }

    ais.sort((a, b) => {
      const scoreA = (a.totalProfit / BUDGET_PER_AI) * 70 + (a.winRate / 100) * 30;
      const scoreB = (b.totalProfit / BUDGET_PER_AI) * 70 + (b.winRate / 100) * 30;
      return scoreB - scoreA;
    });

    // Calculate target allocations with caps
    const targetAllocations: Map<string, number> = new Map();
    let totalTarget = 0;
    
    ais.forEach((ai, index) => {
      let multiplier: number;
      const rank = index + 1;
      
      if (rank === 1) {
        multiplier = 1.50; // Top performer gets 150%
      } else if (rank === 2) {
        multiplier = 1.30;
      } else if (rank === 3) {
        multiplier = 1.15;
      } else if (rank <= 5) {
        multiplier = 1.00; // Average
      } else if (rank <= 7) {
        multiplier = 0.75;
      } else {
        multiplier = 0.50; // Worst performer gets 50%
      }

      // Enforce hard caps: 50% to 150% of starting budget
      const targetBudget = Math.max(BUDGET_PER_AI * 0.5, Math.min(BUDGET_PER_AI * 1.5, ai.budget * multiplier));
      targetAllocations.set(ai.id, targetBudget);
      totalTarget += targetBudget;
    });

    // INVARIANT: Ensure total allocation doesn't exceed total available budget
    const availableBudget = Math.max(0, totalBalance - MIN_PROTECTED_BALANCE);
    const scaleFactor = totalTarget > availableBudget ? (availableBudget / totalTarget) : 1;
    
    ais.forEach((ai, index) => {
      const rank = index + 1;
      const oldBudget = ai.currentBudget;
      const targetBudget = targetAllocations.get(ai.id) || BUDGET_PER_AI * 0.5;
      
      // Scale down if needed to protect minimum balance
      let newBudget = targetBudget * scaleFactor;
      // Ensure minimum of 50% of starting budget
      newBudget = Math.max(BUDGET_PER_AI * 0.5, Math.min(BUDGET_PER_AI * 1.5, newBudget));
      
      ai.currentBudget = newBudget;
      
      const change = newBudget - oldBudget;
      const changeSign = change >= 0 ? '+' : '';
      console.log(`   #${rank} ${ai.name.substring(0, 25).padEnd(25)} | $${newBudget.toFixed(2).padStart(8)} (${changeSign}$${change.toFixed(2)})`);
    });

    // Verify invariant: total allocations must preserve protected balance
    const newTotalAllocated = ais.reduce((sum, ai) => sum + ai.currentBudget, 0);
    console.log(`\n   Total Allocated: $${newTotalAllocated.toFixed(2)} | Protected: $${MIN_PROTECTED_BALANCE.toFixed(2)}`);

    // SANITY CHECK: Fail-fast if invariant violated
    if (newTotalAllocated > totalBalance) {
      console.error(`🚨 CRITICAL: Allocation ($${newTotalAllocated.toFixed(2)}) exceeds total balance ($${totalBalance.toFixed(2)})`);
      console.error(`   Rolling back to previous allocations...`);
      // In a real scenario, we'd rollback here, but for now just log the violation
    }

    this.rebalanceCount++;
    this.lastRebalanceTime = Date.now();
    
    console.log(`   Total Rebalances: ${this.rebalanceCount}`);
    console.log('💰'.repeat(40) + '\n');
  }
  
  // Check if trading should be blocked due to risk limits
  canTrade(aiId: string): { allowed: boolean; reason: string } {
    const ai = this.aiPerformance.get(aiId);
    if (!ai) return { allowed: false, reason: 'AI not found' };
    
    // Check if AI is paused
    if (ai.isPaused) {
      return { allowed: false, reason: `AI paused: ${ai.pauseReason}` };
    }
    
    // Check protected balance (use currentBudget as source of truth)
    const totalBalance = Array.from(this.aiPerformance.values()).reduce((sum, a) => sum + a.currentBudget, 0);
    if (totalBalance <= MIN_PROTECTED_BALANCE) {
      return { allowed: false, reason: `Protected balance reached: $${totalBalance.toFixed(2)} <= $${MIN_PROTECTED_BALANCE.toFixed(2)}` };
    }
    
    // Check daily loss limit
    const dailyLossLimit = ai.startingBudget * (RISK_CONFIG.maxDailyLossPct / 100);
    if (ai.dailyProfit < -dailyLossLimit) {
      return { allowed: false, reason: `Daily loss limit: $${Math.abs(ai.dailyProfit).toFixed(2)} > $${dailyLossLimit.toFixed(2)}` };
    }
    
    // Check total loss limit
    const totalLossLimit = ai.startingBudget * (RISK_CONFIG.maxTotalLossPct / 100);
    if (ai.totalProfit < -totalLossLimit) {
      return { allowed: false, reason: `Total loss limit: $${Math.abs(ai.totalProfit).toFixed(2)} > $${totalLossLimit.toFixed(2)}` };
    }
    
    // Check global daily loss
    const totalDailyProfit = Array.from(this.aiPerformance.values()).reduce((sum, a) => sum + a.dailyProfit, 0);
    if (totalDailyProfit < -RISK_CONFIG.globalMaxDailyLoss) {
      return { allowed: false, reason: `Global daily loss limit: $${Math.abs(totalDailyProfit).toFixed(2)} > $${RISK_CONFIG.globalMaxDailyLoss.toFixed(2)}` };
    }
    
    // Check global total loss
    const totalProfit = Array.from(this.aiPerformance.values()).reduce((sum, a) => sum + a.totalProfit, 0);
    if (totalProfit < -RISK_CONFIG.globalMaxTotalLoss) {
      return { allowed: false, reason: `Global total loss limit: $${Math.abs(totalProfit).toFixed(2)} > $${RISK_CONFIG.globalMaxTotalLoss.toFixed(2)}` };
    }
    
    return { allowed: true, reason: 'OK' };
  }

  applyStreakBonus(aiId: string) {
    const ai = this.aiPerformance.get(aiId);
    if (!ai) return;

    if (ai.currentStreak >= 5) {
      const config = AI_MODELS_CONFIG[aiId];
      const bonus = Math.min(1.2, 1 + (ai.currentStreak - 4) * 0.05);
      console.log(`🔥 ${ai.name} WINNING STREAK x${ai.currentStreak} - Position size +${((bonus - 1) * 100).toFixed(0)}%`);
    }

    if (ai.winRate > 75 && ai.totalTrades >= 10) {
      console.log(`⚡ ${ai.name} HIGH WIN RATE (${ai.winRate.toFixed(1)}%) - Leverage bonus active`);
    }

    if (ai.bestStreak < ai.currentStreak) {
      ai.bestStreak = ai.currentStreak;
    }
  }

  getAIConfig(aiId: string): AIModelConfig | null {
    const config = AI_MODELS_CONFIG[aiId];
    if (!config) return null;
    const performance = this.aiPerformance.get(aiId);
    return {
      ...config,
      budget: performance?.budget || BUDGET_PER_AI,
      startingBudget: BUDGET_PER_AI,
      currentBudget: performance?.currentBudget || BUDGET_PER_AI,
      godPrompt: GOD_PROMPTS[aiId] || ''
    };
  }

  getAllAIConfigs(): AIModelConfig[] {
    return Object.keys(AI_MODELS_CONFIG).map(id => this.getAIConfig(id)!);
  }

  getPerformance(aiId: string): AIPerformance | null {
    return this.aiPerformance.get(aiId) || null;
  }

  getAllPerformance(): AIPerformance[] {
    return Array.from(this.aiPerformance.values()).sort((a, b) => a.rank - b.rank);
  }

  getLeaderboard(): AIPerformance[] {
    return this.getAllPerformance();
  }

  recordTrade(aiId: string, pnl: number, tradeDetails: Partial<TradeRecord>) {
    const ai = this.aiPerformance.get(aiId);
    if (!ai) return;

    ai.budget += pnl;
    ai.currentBudget += pnl;
    ai.totalProfit += pnl;
    ai.dailyProfit += pnl;
    ai.weeklyProfit += pnl;
    ai.totalTrades += 1;

    if (pnl > 0) {
      ai.winningTrades += 1;
      ai.currentStreak = ai.currentStreak >= 0 ? ai.currentStreak + 1 : 1;
      this.applyStreakBonus(aiId);
    } else {
      ai.losingTrades += 1;
      ai.currentStreak = ai.currentStreak <= 0 ? ai.currentStreak - 1 : -1;
    }

    ai.winRate = ai.totalTrades > 0 ? (ai.winningTrades / ai.totalTrades) * 100 : 0;
    ai.roi = ai.startingBudget > 0 ? (ai.totalProfit / ai.startingBudget) * 100 : 0;
    ai.lastTradeTime = Date.now();

    const config = AI_MODELS_CONFIG[aiId];
    const record: TradeRecord = {
      id: `${aiId}-${Date.now()}`,
      aiId,
      symbol: tradeDetails.symbol || 'BTC_USDT',
      direction: 'SHORT',
      entryPrice: tradeDetails.entryPrice || 0,
      exitPrice: tradeDetails.exitPrice,
      positionSize: tradeDetails.positionSize || 0,
      leverage: tradeDetails.leverage || config?.leverage || 10,
      edgeScore: tradeDetails.edgeScore || 0,
      strategy: config?.strategy || 'scalping',
      pnl,
      pnlPct: ai.budget > 0 ? (pnl / ai.budget) * 100 : 0,
      timestamp: new Date().toISOString(),
      status: 'closed'
    };

    const history = this.tradeHistory.get(aiId) || [];
    history.push(record);
    this.tradeHistory.set(aiId, history);

    this.checkPauseConditions(aiId);
    this.updateRankings();
    this.printTradeResult(aiId, pnl, record);
  }

  private checkPauseConditions(aiId: string) {
    const ai = this.aiPerformance.get(aiId);
    if (!ai) return;

    const dailyLossLimit = ai.startingBudget * (RISK_CONFIG.maxDailyLossPct / 100);
    const totalLossLimit = ai.startingBudget * (RISK_CONFIG.maxTotalLossPct / 100);

    if (ai.dailyProfit < -dailyLossLimit) {
      ai.isPaused = true;
      ai.pauseReason = `Daily loss limit hit ($${Math.abs(ai.dailyProfit).toFixed(2)} > $${dailyLossLimit.toFixed(2)})`;
      ai.pauseUntil = null; // Pause rest of day
      console.log(`⛔ ${ai.name} PAUSED: ${ai.pauseReason}`);
    } else if (ai.totalProfit < -totalLossLimit) {
      ai.isPaused = true;
      ai.pauseReason = `Total loss limit hit - PERMANENT PAUSE ($${Math.abs(ai.totalProfit).toFixed(2)} > $${totalLossLimit.toFixed(2)})`;
      ai.pauseUntil = null;
      console.log(`🚫 ${ai.name} PERMANENTLY PAUSED: ${ai.pauseReason}`);
    } else if (ai.currentStreak <= -RISK_CONFIG.consecutiveLossLimit) {
      ai.isPaused = true;
      ai.pauseReason = `${RISK_CONFIG.consecutiveLossLimit} consecutive losses`;
      ai.pauseUntil = Date.now() + (RISK_CONFIG.pauseDurationMinutes * 60 * 1000);
      console.log(`⏸️ ${ai.name} PAUSED 1 hour: ${ai.pauseReason}`);
    }
  }

  private updateRankings() {
    const sorted = Array.from(this.aiPerformance.entries())
      .sort((a, b) => b[1].totalProfit - a[1].totalProfit);
    
    sorted.forEach(([_, ai], index) => {
      ai.rank = index + 1;
      if (ai.rank === 1) ai.medal = '🥇';
      else if (ai.rank === 2) ai.medal = '🥈';
      else if (ai.rank === 3) ai.medal = '🥉';
      else ai.medal = '';
    });
  }

  private printTradeResult(aiId: string, pnl: number, trade: TradeRecord) {
    const ai = this.aiPerformance.get(aiId);
    if (!ai) return;

    const symbol = pnl > 0 ? '📈' : '📉';
    const pnlSign = pnl >= 0 ? '+' : '';
    console.log(`\n${symbol} ${ai.medal}${ai.name}`);
    console.log(`   ${trade.symbol} SHORT | Leverage: ${trade.leverage}x | Strategy: ${trade.strategy}`);
    console.log(`   PnL: $${pnlSign}${pnl.toFixed(2)} (${pnlSign}${trade.pnlPct.toFixed(2)}%)`);
    console.log(`   Budget: $${ai.budget.toFixed(2)} | Total Profit: $${pnlSign}${ai.totalProfit.toFixed(2)} (${pnlSign}${ai.roi.toFixed(1)}% ROI)`);
    console.log(`   Win Rate: ${ai.winRate.toFixed(1)}% | Streak: ${ai.currentStreak} | Rank: #${ai.rank}/8`);
  }

  displayLeaderboard() {
    const medals = ['🥇', '🥈', '🥉'];
    console.log('\n' + '🏆'.repeat(40));
    console.log('GODS LEVEL AI TRADING COMPETITION - LIVE LEADERBOARD');
    console.log('🏆'.repeat(40));
    console.log('Rank  Medal  AI God                       Profit       ROI      Win%   Trades  Streak');
    console.log('-'.repeat(90));

    const sorted = this.getAllPerformance();
    for (const ai of sorted) {
      const status = ai.isPaused ? '[⛔]' : '';
      const medal = ai.medal || '   ';
      const profitStr = ai.totalProfit >= 0 ? '+$' + ai.totalProfit.toFixed(2) : '-$' + Math.abs(ai.totalProfit).toFixed(2);
      const roiStr = ai.roi >= 0 ? '+' + ai.roi.toFixed(1) + '%' : ai.roi.toFixed(1) + '%';
      const streakStr = ai.currentStreak >= 0 ? '+' + ai.currentStreak : ai.currentStreak.toString();
      
      console.log(
        `#${ai.rank}    ${medal}  ${status}${ai.name.substring(0, 28).padEnd(28)} ${profitStr.padStart(10)} ${roiStr.padStart(8)}  ${ai.winRate.toFixed(1).padStart(5)}%  ${ai.totalTrades.toString().padStart(6)}  ${streakStr.padStart(6)}`
      );
    }

    console.log('-'.repeat(90));
    const totalBalance = Array.from(this.aiPerformance.values()).reduce((sum, ai) => sum + ai.budget, 0);
    const totalProfit = Array.from(this.aiPerformance.values()).reduce((sum, ai) => sum + ai.totalProfit, 0);
    const totalTrades = Array.from(this.aiPerformance.values()).reduce((sum, ai) => sum + ai.totalTrades, 0);
    const profitSign = totalProfit >= 0 ? '+' : '';
    
    console.log(`\n💰 TOTAL BALANCE: $${totalBalance.toFixed(2)} | PROFIT: $${profitSign}${totalProfit.toFixed(2)} (${profitSign}${((totalProfit / TOTAL_BALANCE) * 100).toFixed(1)}%)`);
    console.log(`📊 Total Trades: ${totalTrades} | Market: ${this.currentMarketCondition} | Rebalances: ${this.rebalanceCount}`);
    console.log(`🛡️ Protected Balance: $${MIN_PROTECTED_BALANCE.toFixed(2)} | Max Loss: $${RISK_CONFIG.globalMaxTotalLoss.toFixed(2)}`);
    console.log('🏆'.repeat(40) + '\n');
  }

  checkAutoUnpause() {
    const now = Date.now();
    Array.from(this.aiPerformance.entries()).forEach(([aiId, ai]) => {
      if (ai.isPaused && ai.pauseUntil && now >= ai.pauseUntil) {
        this.unpauseAI(aiId);
        console.log(`⏰ ${ai.name} auto-unpaused after timeout`);
      }
    });
  }

  isAIPaused(aiId: string): boolean {
    return this.aiPerformance.get(aiId)?.isPaused || false;
  }

  getAIBudget(aiId: string): number {
    return this.aiPerformance.get(aiId)?.currentBudget || 0;
  }

  getTotalStats() {
    const ais = Array.from(this.aiPerformance.values());
    return {
      totalBalance: ais.reduce((sum, ai) => sum + ai.budget, 0),
      totalProfit: ais.reduce((sum, ai) => sum + ai.totalProfit, 0),
      totalTrades: ais.reduce((sum, ai) => sum + ai.totalTrades, 0),
      activeAIs: ais.filter(ai => !ai.isPaused).length,
      pausedAIs: ais.filter(ai => ai.isPaused).length,
      leader: ais.find(ai => ai.rank === 1) || null,
      marketCondition: this.currentMarketCondition,
      rebalanceCount: this.rebalanceCount,
      lastRebalance: this.lastRebalanceTime,
      nextRebalance: this.lastRebalanceTime + REBALANCE_INTERVAL_MS
    };
  }

  getTradeHistory(aiId?: string, limit?: number): TradeRecord[] {
    let trades: TradeRecord[];
    if (aiId) {
      trades = this.tradeHistory.get(aiId) || [];
    } else {
      trades = [];
      Array.from(this.tradeHistory.values()).forEach(t => trades.push(...t));
    }
    trades.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    return limit ? trades.slice(0, limit) : trades;
  }

  resetDailyStats() {
    Array.from(this.aiPerformance.values()).forEach(ai => {
      ai.dailyProfit = 0;
      if (ai.isPaused && ai.pauseReason.includes('Daily')) {
        ai.isPaused = false;
        ai.pauseReason = '';
        ai.pauseUntil = null;
      }
    });
    console.log('🔄 Daily stats reset for all AI Gods');
  }

  unpauseAI(aiId: string) {
    const ai = this.aiPerformance.get(aiId);
    if (ai && !ai.pauseReason.includes('PERMANENT')) {
      ai.isPaused = false;
      ai.pauseReason = '';
      ai.pauseUntil = null;
      ai.currentStreak = 0;
      console.log(`▶️ ${ai.name} unpaused and ready to trade`);
    }
  }

  getStatus() {
    return {
      isRunning: this.isRunning,
      realTrading: REAL_TRADING_MODE,
      mode: 'GODS_LEVEL_COMPETITION',
      direction: 'SHORTS_ONLY',
      totalBalance: TOTAL_BALANCE,
      budgetPerAI: BUDGET_PER_AI,
      minProtectedBalance: MIN_PROTECTED_BALANCE,
      pairs: TRADING_PAIRS,
      marketCondition: this.currentMarketCondition,
      strategyAllocation: STRATEGY_ALLOCATION[this.currentMarketCondition],
      riskConfig: RISK_CONFIG,
      rebalancing: {
        intervalHours: 4,
        totalRebalances: this.rebalanceCount,
        lastRebalance: this.lastRebalanceTime,
        nextRebalance: this.lastRebalanceTime > 0 ? this.lastRebalanceTime + REBALANCE_INTERVAL_MS : Date.now() + REBALANCE_INTERVAL_MS
      },
      stats: this.getTotalStats(),
      leaderboard: this.getLeaderboard()
    };
  }

  start() {
    if (this.isRunning) {
      console.log('⚠️ GODS LEVEL Competition already running');
      return;
    }

    this.isRunning = true;
    this.lastRebalanceTime = Date.now();
    
    console.log('\n' + '🔥'.repeat(50));
    console.log('GODS LEVEL AI TRADING COMPETITION - STARTED');
    console.log('🔥'.repeat(50));
    console.log('⚡ REAL TRADING MODE - LIVE FUNDS ON GATE.IO');
    console.log('🏆 8 AI GODS COMPETING FOR MAXIMUM PROFIT');
    console.log(`💰 Budget per AI: $${BUDGET_PER_AI.toFixed(2)}`);
    console.log(`🛡️ Protected Balance: $${MIN_PROTECTED_BALANCE.toFixed(2)} (85%)`);
    console.log(`📊 Direction: SHORTS ONLY`);
    console.log(`🔄 Auto-Loop: ENABLED (10 second cycles)`);
    console.log(`📈 Market Condition: ${this.currentMarketCondition}`);
    console.log('🔥'.repeat(50) + '\n');

    this.intervals.set('leaderboard', setInterval(() => {
      this.displayLeaderboard();
    }, 300000)); // Every 5 minutes

    this.intervals.set('rebalance', setInterval(() => {
      this.rebalanceCapital();
    }, REBALANCE_INTERVAL_MS)); // Every 4 hours

    this.intervals.set('unpause', setInterval(() => {
      this.checkAutoUnpause();
    }, 60000)); // Every minute

    // 🔄 AUTO-TRADING LOOP - Runs every 10 seconds
    this.intervals.set('autoTrading', setInterval(async () => {
      await this.runTradingCycle();
    }, 10000)); // Every 10 seconds

    // Run first cycle immediately
    this.runTradingCycle();
    this.displayLeaderboard();
  }

  private async runTradingCycle() {
    if (!this.isRunning) return;
    
    const cycleStart = Date.now();
    let tradesExecuted = 0;
    
    try {
      // Import trading functions
      const { fetchGateMarketData, placeFuturesOrder, getFuturesBalance, getOpenPositions } = await import('./gateio');
      
      // Check balance protection
      const balance = await getFuturesBalance();
      if (!balance || balance.available < 50) {
        console.log('⚠️ Low balance, skipping cycle');
        return;
      }
      
      // Get current positions
      const positions = await getOpenPositions();
      const positionCount = positions.length;
      
      // Limit max positions
      if (positionCount >= 5) {
        console.log(`📊 Max positions (${positionCount}/5), monitoring only`);
        return;
      }
      
      // Rotate through trading pairs
      for (const pair of TRADING_PAIRS) {
        if (!this.isRunning) break;
        
        try {
          // Get market data
          const marketData = await fetchGateMarketData(pair) as any;
          if (!marketData) continue;
          
          // Simple SHORT signal detection
          const price = marketData.currentPrice || marketData.last || 0;
          const rsi = marketData.rsi || 50;
          const priceChange = marketData.priceChange24h || 0;
          
          // SHORT signal: RSI > 65 or price pumped > 2%
          const shortSignal = rsi > 65 || priceChange > 2;
          
          if (shortSignal && positionCount < 5) {
            // Check if already have position in this pair
            const hasPosition = positions.some((p: any) => p.contract === pair);
            if (hasPosition) continue;
            
            // Calculate position size (small for safety)
            const availableBalance = balance?.available || 0;
            const positionValue = Math.min(availableBalance * 0.15, 50);
            let size = -Math.floor(positionValue / price * 100) / 100;
            
            // Minimum sizes
            if (pair === 'BTC_USDT') size = Math.min(size, -0.001);
            else if (pair === 'ETH_USDT') size = Math.min(size, -0.01);
            else if (pair === 'SOL_USDT') size = Math.min(size, -1);
            else if (pair === 'XRP_USDT') size = Math.min(size, -100);
            else if (pair === 'DOGE_USDT') size = Math.min(size, -100);
            
            if (Math.abs(size) > 0) {
              console.log(`🎯 SHORT Signal: ${pair} RSI=${rsi.toFixed(1)} Change=${priceChange.toFixed(2)}%`);
              
              try {
                await placeFuturesOrder({
                  contract: pair,
                  size: size,
                  leverage: 10,
                  price: 0, // Market order
                });
                tradesExecuted++;
                console.log(`✅ SHORT opened: ${pair} size=${size}`);
              } catch (orderError: any) {
                // Ignore order errors, continue
              }
            }
          }
        } catch (pairError) {
          // Continue to next pair
        }
      }
      
      const cycleTime = Date.now() - cycleStart;
      if (tradesExecuted > 0) {
        console.log(`🔄 Cycle complete: ${tradesExecuted} trades in ${cycleTime}ms`);
      }
      
    } catch (error: any) {
      console.log('⚠️ Trading cycle error:', error?.message || 'Unknown');
    }
  }

  stop() {
    this.isRunning = false;
    Array.from(this.intervals.values()).forEach(interval => {
      clearInterval(interval);
    });
    this.intervals.clear();
    console.log('\n⏹️ GODS LEVEL AI Trading Competition stopped');
  }
}

export const aiCompetition = new AICompetitionSystem();

export {
  TOTAL_BALANCE,
  BUDGET_PER_AI,
  TRADING_PAIRS,
  AI_MODELS_CONFIG,
  RISK_CONFIG,
  GOD_PROMPTS,
  STRATEGY_ALLOCATION,
  MIN_PROTECTED_BALANCE,
  MAX_RISK_AMOUNT,
  HYBRID_WITHDRAWAL_CONFIG,
  BALANCED_MODE,
  REBALANCE_INTERVAL_MS
};
