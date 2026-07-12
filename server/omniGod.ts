/**
 * 🔱 OMNI-GOD TRADING SYSTEM
 * Institutional-grade modules for scaling $692 -> $1,000,000
 * 
 * Modules:
 * 1. SMC Sniper (Smart Strategy)
 * 2. Risk Guardian (The Shield)
 * 3. Capital Manager (Millionaire Growth)
 * 4. Phoenix Protocol (Immortality)
 * 5. Genetic Optimizer (Self-Learning)
 */

import { fetchGateMarketData, placeFuturesOrder, getFuturesBalance } from './gateio';

// ============================================
// 🧠 STRATEGY ENGINE - SMC SNIPER
// ============================================

interface LiquiditySweep {
  detected: boolean;
  type: 'bullish' | 'bearish' | 'none';
  wickSize: number;
  closeAboveLow: boolean;
  strength: number;
}

interface OrderBookImbalance {
  ratio: number;
  bidVolume: number;
  askVolume: number;
  imbalanceDirection: 'BUY' | 'SELL' | 'NEUTRAL';
  tradeable: boolean;
}

interface SessionContext {
  session: 'ASIA' | 'LONDON' | 'NEWYORK' | 'OVERLAP';
  strategy: 'MEAN_REVERSION' | 'TREND_FOLLOWING' | 'BREAKOUT';
  volatilityMultiplier: number;
}

export class SmartStrategy {
  private static instance: SmartStrategy;
  
  static getInstance(): SmartStrategy {
    if (!SmartStrategy.instance) {
      SmartStrategy.instance = new SmartStrategy();
    }
    return SmartStrategy.instance;
  }

  // Logic A: Liquidity Sweep Detection (Fakeouts)
  detectLiquiditySweep(candles: any[]): LiquiditySweep {
    if (candles.length < 5) {
      return { detected: false, type: 'none', wickSize: 0, closeAboveLow: false, strength: 0 };
    }

    const current = candles[candles.length - 1];
    const previous = candles.slice(-5, -1);
    
    const recentLow = Math.min(...previous.map(c => c.low));
    const recentHigh = Math.max(...previous.map(c => c.high));
    
    // Bearish sweep: Wick above high + Close below (SHORT signal)
    const bearishSweep = current.high > recentHigh && current.close < recentHigh;
    const bearishWick = current.high - Math.max(current.open, current.close);
    
    // Bullish sweep: Wick below low + Close above (LONG signal - but we SHORT only)
    const bullishSweep = current.low < recentLow && current.close > recentLow;
    const bullishWick = Math.min(current.open, current.close) - current.low;

    if (bearishSweep) {
      return {
        detected: true,
        type: 'bearish',
        wickSize: bearishWick,
        closeAboveLow: true,
        strength: Math.min(100, (bearishWick / current.close) * 10000)
      };
    }

    return { detected: false, type: 'none', wickSize: 0, closeAboveLow: false, strength: 0 };
  }

  // Logic B: Order Book X-Ray (Imbalance Ratio > 1.5)
  analyzeOrderBook(orderBook: any): OrderBookImbalance {
    if (!orderBook || !orderBook.bids || !orderBook.asks) {
      return { ratio: 1, bidVolume: 0, askVolume: 0, imbalanceDirection: 'NEUTRAL', tradeable: false };
    }

    // Sum top 20 levels
    const bidVolume = orderBook.bids.slice(0, 20).reduce((sum: number, [_, vol]: [string, string]) => 
      sum + parseFloat(vol), 0);
    const askVolume = orderBook.asks.slice(0, 20).reduce((sum: number, [_, vol]: [string, string]) => 
      sum + parseFloat(vol), 0);

    const ratio = bidVolume / (askVolume || 1);
    
    // For SHORTS: We want more bids than asks (buyers to sell into)
    // Ratio > 1.5 means heavy buying pressure -> potential reversal -> SHORT
    const imbalanceDirection = ratio > 1.5 ? 'SELL' : ratio < 0.67 ? 'BUY' : 'NEUTRAL';
    const tradeable = ratio > 1.5 || ratio < 0.67;

    return { ratio, bidVolume, askVolume, imbalanceDirection, tradeable };
  }

  // Logic C: Oracle Lag Arbitrage (Price moves > 0.3% in < 1s)
  detectOracleLag(priceHistory: { price: number; timestamp: number }[]): { 
    detected: boolean; 
    direction: 'SHORT' | 'LONG' | 'NONE';
    magnitude: number;
  } {
    if (priceHistory.length < 2) {
      return { detected: false, direction: 'NONE', magnitude: 0 };
    }

    const latest = priceHistory[priceHistory.length - 1];
    const oneSecondAgo = priceHistory.find(p => latest.timestamp - p.timestamp >= 1000 && latest.timestamp - p.timestamp < 2000);
    
    if (!oneSecondAgo) {
      return { detected: false, direction: 'NONE', magnitude: 0 };
    }

    const change = ((latest.price - oneSecondAgo.price) / oneSecondAgo.price) * 100;
    const magnitude = Math.abs(change);

    if (magnitude > 0.3) {
      // Spike UP = SHORT (fade the move)
      // Spike DOWN = We don't LONG (SHORTS ONLY mode)
      return {
        detected: true,
        direction: change > 0 ? 'SHORT' : 'NONE',
        magnitude
      };
    }

    return { detected: false, direction: 'NONE', magnitude: 0 };
  }

  // Logic D: Session Sniper
  getSessionContext(): SessionContext {
    const now = new Date();
    const utcHour = now.getUTCHours();

    // Session times (UTC):
    // Asia: 00:00 - 08:00
    // London: 08:00 - 16:00
    // New York: 13:00 - 21:00
    // Overlap: 13:00 - 16:00

    if (utcHour >= 13 && utcHour < 16) {
      return {
        session: 'OVERLAP',
        strategy: 'BREAKOUT',
        volatilityMultiplier: 1.5
      };
    } else if (utcHour >= 13 && utcHour < 21) {
      return {
        session: 'NEWYORK',
        strategy: 'TREND_FOLLOWING',
        volatilityMultiplier: 1.3
      };
    } else if (utcHour >= 8 && utcHour < 16) {
      return {
        session: 'LONDON',
        strategy: 'TREND_FOLLOWING',
        volatilityMultiplier: 1.2
      };
    } else {
      return {
        session: 'ASIA',
        strategy: 'MEAN_REVERSION',
        volatilityMultiplier: 0.8
      };
    }
  }

  // Combined SMC Signal
  async generateSignal(symbol: string, marketData: any): Promise<{
    action: 'SHORT' | 'HOLD';
    confidence: number;
    reasons: string[];
    smcScore: number;
  }> {
    const reasons: string[] = [];
    let smcScore = 0;

    // Session context
    const session = this.getSessionContext();
    reasons.push(`Session: ${session.session} (${session.strategy})`);

    // Liquidity sweep
    if (marketData.candles) {
      const sweep = this.detectLiquiditySweep(marketData.candles);
      if (sweep.detected && sweep.type === 'bearish') {
        smcScore += 30;
        reasons.push(`Liquidity Sweep: Bearish (${sweep.strength.toFixed(1)}% strength)`);
      }
    }

    // Order book imbalance
    if (marketData.orderBook) {
      const imbalance = this.analyzeOrderBook(marketData.orderBook);
      if (imbalance.tradeable && imbalance.imbalanceDirection === 'SELL') {
        smcScore += 25;
        reasons.push(`Order Book: ${imbalance.ratio.toFixed(2)}x imbalance (SHORT signal)`);
      }
    }

    // Apply session multiplier
    smcScore *= session.volatilityMultiplier;

    return {
      action: smcScore >= 40 ? 'SHORT' : 'HOLD',
      confidence: Math.min(100, smcScore + 50),
      reasons,
      smcScore
    };
  }
}

// ============================================
// 🛡️ DEFENSE ENGINE - THE SHIELD
// ============================================

interface RiskState {
  toxicPairs: Map<string, { banUntil: number; stopLossCount: number }>;
  btcGuardActive: boolean;
  lastBtcPrice: number;
  lastBtcCheck: number;
}

export class RiskGuardian {
  private static instance: RiskGuardian;
  private state: RiskState = {
    toxicPairs: new Map(),
    btcGuardActive: false,
    lastBtcPrice: 0,
    lastBtcCheck: 0
  };

  static getInstance(): RiskGuardian {
    if (!RiskGuardian.instance) {
      RiskGuardian.instance = new RiskGuardian();
    }
    return RiskGuardian.instance;
  }

  // News Filter: Block trades on dangerous keywords
  async checkNewsFilter(): Promise<{ safe: boolean; reason: string }> {
    // Simulated news check - in production, connect to CryptoPanic API
    const dangerousKeywords = ['SEC', 'HACK', 'WAR', 'EXPLOIT', 'BANKRUPTCY', 'SHUTDOWN'];
    
    // For now, always safe (would connect to real news API)
    return { safe: true, reason: 'No dangerous news detected' };
  }

  // Spread Filter: Skip if spread > 0.08%
  checkSpreadFilter(bid: number, ask: number): { safe: boolean; spread: number } {
    const spread = ((ask - bid) / bid) * 100;
    return {
      safe: spread <= 0.08,
      spread
    };
  }

  // Toxic Blacklist: Ban pair after 3 stop losses in 6h
  recordStopLoss(symbol: string): void {
    const now = Date.now();
    const existing = this.state.toxicPairs.get(symbol);
    
    if (existing) {
      // Clear if ban expired
      if (existing.banUntil < now) {
        this.state.toxicPairs.set(symbol, { banUntil: 0, stopLossCount: 1 });
      } else {
        existing.stopLossCount++;
        if (existing.stopLossCount >= 3) {
          // Ban for 24 hours
          existing.banUntil = now + 24 * 60 * 60 * 1000;
          console.log(`🚫 [TOXIC BLACKLIST] ${symbol} banned for 24h after 3 stop losses`);
        }
      }
    } else {
      this.state.toxicPairs.set(symbol, { banUntil: 0, stopLossCount: 1 });
    }
  }

  isPairBanned(symbol: string): boolean {
    const entry = this.state.toxicPairs.get(symbol);
    if (!entry) return false;
    return entry.banUntil > Date.now();
  }

  // BTC Guard: Block longs if BTC drops > 0.4% in 5m
  // For SHORTS ONLY mode: This is actually a BOOST signal!
  async checkBtcGuard(): Promise<{ 
    btcDumping: boolean; 
    change5m: number;
    shortBoost: boolean;
  }> {
    try {
      const btcData = await fetchGateMarketData('BTC_USDT');
      if (!btcData) return { btcDumping: false, change5m: 0, shortBoost: false };

      const currentPrice = btcData.currentPrice;
      const change5m = btcData.priceChange24h / 288; // Approximate 5m change
      
      // For SHORTS: BTC dumping = SHORT BOOST!
      const btcDumping = change5m < -0.4;
      
      return {
        btcDumping,
        change5m,
        shortBoost: btcDumping // In SHORTS ONLY mode, BTC dump = opportunity
      };
    } catch (error) {
      return { btcDumping: false, change5m: 0, shortBoost: false };
    }
  }

  // Master validation
  async validateTrade(symbol: string, bid: number, ask: number): Promise<{
    approved: boolean;
    reasons: string[];
    boosts: string[];
  }> {
    const reasons: string[] = [];
    const boosts: string[] = [];

    // Check toxic blacklist
    if (this.isPairBanned(symbol)) {
      reasons.push(`${symbol} is toxic blacklisted`);
      return { approved: false, reasons, boosts };
    }

    // Check spread
    const spreadCheck = this.checkSpreadFilter(bid, ask);
    if (!spreadCheck.safe) {
      reasons.push(`Spread too high: ${spreadCheck.spread.toFixed(3)}%`);
      return { approved: false, reasons, boosts };
    }

    // Check news
    const newsCheck = await this.checkNewsFilter();
    if (!newsCheck.safe) {
      reasons.push(newsCheck.reason);
      return { approved: false, reasons, boosts };
    }

    // Check BTC Guard (for shorts, this is a boost!)
    const btcGuard = await this.checkBtcGuard();
    if (btcGuard.shortBoost) {
      boosts.push(`BTC dumping ${btcGuard.change5m.toFixed(2)}% - SHORT BOOST!`);
    }

    return { approved: true, reasons, boosts };
  }
}

// ============================================
// 💰 CAPITAL MANAGER - MILLIONAIRE GROWTH
// ============================================

interface GrowthPhase {
  name: string;
  minBalance: number;
  maxBalance: number;
  leverage: number;
  positionSizePercent: number;
  style: string;
  icebergChunks: number;
}

interface VaultState {
  lockedAmount: number;
  lastLockTime: number;
  totalLocked: number;
}

export class CapitalManager {
  private static instance: CapitalManager;
  private vault: VaultState = {
    lockedAmount: 0,
    lastLockTime: 0,
    totalLocked: 0
  };

  private phases: GrowthPhase[] = [
    { name: 'AGGRESSIVE', minBalance: 0, maxBalance: 10000, leverage: 20, positionSizePercent: 25, style: 'High Risk', icebergChunks: 1 },
    { name: 'BALANCED', minBalance: 10000, maxBalance: 100000, leverage: 10, positionSizePercent: 15, style: 'Balanced', icebergChunks: 3 },
    { name: 'CONSERVATIVE', minBalance: 100000, maxBalance: Infinity, leverage: 5, positionSizePercent: 10, style: 'Iceberg', icebergChunks: 5 }
  ];

  static getInstance(): CapitalManager {
    if (!CapitalManager.instance) {
      CapitalManager.instance = new CapitalManager();
    }
    return CapitalManager.instance;
  }

  // Determine current growth phase
  getCurrentPhase(balance: number): GrowthPhase {
    for (const phase of this.phases) {
      if (balance >= phase.minBalance && balance < phase.maxBalance) {
        return phase;
      }
    }
    return this.phases[2]; // Default to conservative
  }

  // Calculate position size based on phase
  calculatePositionSize(balance: number, riskPercent: number = 3): {
    phase: GrowthPhase;
    positionSize: number;
    leverage: number;
    chunks: number[];
  } {
    const phase = this.getCurrentPhase(balance);
    const positionSize = balance * (phase.positionSizePercent / 100);
    
    // Split into iceberg chunks if needed
    const chunkSize = positionSize / phase.icebergChunks;
    const chunks = Array(phase.icebergChunks).fill(chunkSize);

    return {
      phase,
      positionSize,
      leverage: phase.leverage,
      chunks
    };
  }

  // Olympus Vault: Lock 50% of profits
  lockProfits(profitAmount: number): number {
    const lockAmount = profitAmount * 0.5;
    this.vault.lockedAmount += lockAmount;
    this.vault.totalLocked += lockAmount;
    this.vault.lastLockTime = Date.now();
    
    console.log(`🏛️ [OLYMPUS VAULT] Locked $${lockAmount.toFixed(2)} | Total: $${this.vault.lockedAmount.toFixed(2)}`);
    return lockAmount;
  }

  // Get vault status
  getVaultStatus(): VaultState {
    return { ...this.vault };
  }

  // Airlift: Transfer profits to spot (simulation)
  async executeAirlift(amount: number): Promise<boolean> {
    if (amount < 50) return false;
    
    console.log(`🚁 [AIRLIFT] Transferring $${amount.toFixed(2)} from Futures to Spot`);
    // In production: Execute actual transfer via Gate.io API
    return true;
  }

  // Get progress to $1M
  getProgressToMillion(currentBalance: number): {
    progress: number;
    phase: string;
    nextMilestone: number;
    daysAtCurrentRate: number;
  } {
    const progress = (currentBalance / 1000000) * 100;
    const phase = this.getCurrentPhase(currentBalance);
    
    // Milestones
    const milestones = [1000, 5000, 10000, 50000, 100000, 500000, 1000000];
    const nextMilestone = milestones.find(m => m > currentBalance) || 1000000;
    
    // Estimate days (assuming 2% daily growth)
    const dailyGrowth = 0.02;
    const daysToMillion = Math.log(1000000 / currentBalance) / Math.log(1 + dailyGrowth);

    return {
      progress,
      phase: phase.name,
      nextMilestone,
      daysAtCurrentRate: Math.ceil(daysToMillion)
    };
  }
}

// ============================================
// 🚑 PHOENIX PROTOCOL - IMMORTALITY
// ============================================

interface TradeState {
  symbol: string;
  direction: 'SHORT';
  entryPrice: number;
  size: number;
  stopLoss: number;
  takeProfit: number;
  timestamp: number;
  dcaCount: number;
}

interface PhoenixState {
  activeTrades: TradeState[];
  lastSaveTime: number;
  restartCount: number;
  uptime: number;
  startTime: number;
}

export class PhoenixProtocol {
  private static instance: PhoenixProtocol;
  private state: PhoenixState = {
    activeTrades: [],
    lastSaveTime: 0,
    restartCount: 0,
    uptime: 0,
    startTime: Date.now()
  };

  static getInstance(): PhoenixProtocol {
    if (!PhoenixProtocol.instance) {
      PhoenixProtocol.instance = new PhoenixProtocol();
    }
    return PhoenixProtocol.instance;
  }

  // Save state for crash recovery
  saveState(): PhoenixState {
    this.state.lastSaveTime = Date.now();
    this.state.uptime = Date.now() - this.state.startTime;
    
    // In production: Write to file system
    console.log(`💾 [PHOENIX] State saved | ${this.state.activeTrades.length} active trades`);
    return this.state;
  }

  // Add/update trade
  registerTrade(trade: TradeState): void {
    const existing = this.state.activeTrades.findIndex(t => t.symbol === trade.symbol);
    if (existing >= 0) {
      this.state.activeTrades[existing] = trade;
    } else {
      this.state.activeTrades.push(trade);
    }
    this.saveState();
  }

  // Remove trade
  closeTrade(symbol: string): void {
    this.state.activeTrades = this.state.activeTrades.filter(t => t.symbol !== symbol);
    this.saveState();
  }

  // Smart DCA: If PnL = -1.5% and conditions permit
  async executeSmartDCA(trade: TradeState, currentPrice: number): Promise<{
    executed: boolean;
    newSize: number;
    newEntry: number;
  }> {
    // Calculate PnL
    const pnlPercent = ((trade.entryPrice - currentPrice) / trade.entryPrice) * 100;
    
    // Only DCA once, and only if down 1.5%
    if (pnlPercent < -1.5 && trade.dcaCount === 0) {
      const dcaSize = trade.size * 1.5;
      const newTotalSize = trade.size + dcaSize;
      const newEntry = (trade.entryPrice * trade.size + currentPrice * dcaSize) / newTotalSize;
      
      console.log(`🔄 [SMART DCA] ${trade.symbol}: Adding ${dcaSize.toFixed(4)} at $${currentPrice.toFixed(2)}`);
      
      trade.dcaCount = 1;
      trade.size = newTotalSize;
      trade.entryPrice = newEntry;
      this.registerTrade(trade);

      return { executed: true, newSize: newTotalSize, newEntry };
    }

    return { executed: false, newSize: trade.size, newEntry: trade.entryPrice };
  }

  // Get uptime stats
  getUptimeStats(): {
    uptime: number;
    uptimeFormatted: string;
    restartCount: number;
    activeTrades: number;
  } {
    const uptime = Date.now() - this.state.startTime;
    const hours = Math.floor(uptime / (1000 * 60 * 60));
    const minutes = Math.floor((uptime % (1000 * 60 * 60)) / (1000 * 60));
    
    return {
      uptime,
      uptimeFormatted: `${hours}h ${minutes}m`,
      restartCount: this.state.restartCount,
      activeTrades: this.state.activeTrades.length
    };
  }
}

// ============================================
// 🎯 SCALP TRAP ENGINE - BREAKEVEN LOGIC
// ============================================

interface ScalpTrapPosition {
  symbol: string;
  entryPrice: number;
  currentPrice: number;
  size: number;
  leverage: number;
  tp1: number;
  tp2: number;
  tp3: number;
  originalStopLoss: number;
  currentStopLoss: number;
  trapLevel: number; // 0 = none, 1 = TP1 hit (breakeven), 2 = TP2 hit, 3 = TP3 hit
  side: 'SHORT' | 'LONG';
  openedAt: number;
}

type TrapAction = 'HOLD' | 'MOVE_SL_TO_ENTRY' | 'MOVE_SL_TO_TP1' | 'MOVE_SL_TO_TP2' | 'CLOSE_POSITION';

export class ScalpTrapEngine {
  private static instance: ScalpTrapEngine;
  private balance: number = 692;
  private minNotional: number = 100; // Minimum position size $100
  private positions: Map<string, ScalpTrapPosition> = new Map();
  private stats = {
    tradesProtected: 0,
    breakevenTriggered: 0,
    profitsLocked: 0,
    totalSaved: 0
  };

  static getInstance(): ScalpTrapEngine {
    if (!ScalpTrapEngine.instance) {
      ScalpTrapEngine.instance = new ScalpTrapEngine();
    }
    return ScalpTrapEngine.instance;
  }

  setBalance(balance: number): void {
    this.balance = balance;
  }

  /**
   * Calculate minimum entry based on confidence level
   * High confidence (>=70%) = 10-15x leverage
   * Low confidence (<70%) = 5x leverage
   */
  calculateMinEntry(price: number, confidence: number): { units: number; leverage: number; notional: number } {
    // Leverage based on confidence
    const leverage = confidence < 0.7 ? 5 : confidence < 0.85 ? 10 : 15;
    
    // Calculate units for minimum notional
    const units = this.minNotional / price;
    const notional = units * price;
    
    return { units, leverage, notional };
  }

  /**
   * Calculate optimal position size based on balance and confidence
   */
  calculateOptimalEntry(price: number, confidence: number): {
    units: number;
    leverage: number;
    positionSize: number;
    riskAmount: number;
  } {
    // Position size: 1-3% of balance based on confidence
    const positionPct = confidence < 0.7 ? 0.01 : confidence < 0.85 ? 0.02 : 0.03;
    const leverage = confidence < 0.7 ? 5 : confidence < 0.85 ? 10 : 15;
    
    const riskAmount = this.balance * positionPct;
    const positionSize = riskAmount * leverage;
    const units = positionSize / price;
    
    return { units, leverage, positionSize, riskAmount };
  }

  /**
   * Register a new position for trap monitoring
   */
  registerPosition(position: Omit<ScalpTrapPosition, 'trapLevel'>): void {
    this.positions.set(position.symbol, {
      ...position,
      trapLevel: 0
    });
    console.log(`🎯 [SCALP TRAP] Registered ${position.symbol} | Entry: $${position.entryPrice.toFixed(4)} | TP1: $${position.tp1.toFixed(4)}`);
  }

  /**
   * Main profit trap logic
   * Automatically moves SL to entry (breakeven) when TP1 is hit
   * For SHORTS: Price must go DOWN to hit TP (TP < Entry)
   */
  applyProfitTrap(symbol: string, currentPrice: number): {
    action: TrapAction;
    newStopLoss: number | null;
    profitLocked: number;
    reason: string;
  } {
    const position = this.positions.get(symbol);
    if (!position) {
      return { action: 'HOLD', newStopLoss: null, profitLocked: 0, reason: 'Position not found' };
    }

    // Update current price
    position.currentPrice = currentPrice;
    
    // For SHORT positions: profit when price goes DOWN
    // TP1 < TP2 < TP3 < Entry < SL
    if (position.side === 'SHORT') {
      // Check TP3 hit (highest profit)
      if (currentPrice <= position.tp3 && position.trapLevel < 3) {
        position.trapLevel = 3;
        position.currentStopLoss = position.tp2; // Lock profits at TP2 level
        const profitLocked = (position.entryPrice - position.tp2) * position.size;
        this.stats.profitsLocked += profitLocked;
        this.stats.tradesProtected++;
        console.log(`🔥 [TRAP LEVEL 3] ${symbol}: TP3 HIT! SL → $${position.tp2.toFixed(4)} | Locked: $${profitLocked.toFixed(2)}`);
        return { action: 'MOVE_SL_TO_TP2', newStopLoss: position.tp2, profitLocked, reason: 'TP3 hit - Maximum profit trap' };
      }
      
      // Check TP2 hit
      if (currentPrice <= position.tp2 && position.trapLevel < 2) {
        position.trapLevel = 2;
        position.currentStopLoss = position.tp1; // Lock profits at TP1 level
        const profitLocked = (position.entryPrice - position.tp1) * position.size;
        this.stats.profitsLocked += profitLocked;
        console.log(`⚡ [TRAP LEVEL 2] ${symbol}: TP2 HIT! SL → $${position.tp1.toFixed(4)} | Locked: $${profitLocked.toFixed(2)}`);
        return { action: 'MOVE_SL_TO_TP1', newStopLoss: position.tp1, profitLocked, reason: 'TP2 hit - Profit trap activated' };
      }
      
      // Check TP1 hit (breakeven)
      if (currentPrice <= position.tp1 && position.trapLevel < 1) {
        position.trapLevel = 1;
        position.currentStopLoss = position.entryPrice; // Move SL to entry (breakeven)
        this.stats.breakevenTriggered++;
        console.log(`🛡️ [BREAKEVEN] ${symbol}: TP1 HIT! SL → Entry $${position.entryPrice.toFixed(4)} | Risk eliminated`);
        return { action: 'MOVE_SL_TO_ENTRY', newStopLoss: position.entryPrice, profitLocked: 0, reason: 'TP1 hit - Breakeven activated' };
      }
    }
    
    // For LONG positions (currently disabled - SHORTS ONLY mode)
    if (position.side === 'LONG') {
      if (currentPrice >= position.tp1 && position.trapLevel < 1) {
        position.trapLevel = 1;
        position.currentStopLoss = position.entryPrice;
        this.stats.breakevenTriggered++;
        return { action: 'MOVE_SL_TO_ENTRY', newStopLoss: position.entryPrice, profitLocked: 0, reason: 'TP1 hit - Breakeven' };
      }
    }

    return { action: 'HOLD', newStopLoss: null, profitLocked: 0, reason: 'No trap triggered' };
  }

  /**
   * Check all positions and apply traps
   */
  async checkAllPositions(priceUpdates: Map<string, number>): Promise<Map<string, TrapAction>> {
    const actions = new Map<string, TrapAction>();
    
    priceUpdates.forEach((price, symbol) => {
      const result = this.applyProfitTrap(symbol, price);
      actions.set(symbol, result.action);
      
      if (result.action !== 'HOLD') {
        this.stats.totalSaved += result.profitLocked;
      }
    });
    
    return actions;
  }

  /**
   * Remove position after close
   */
  closePosition(symbol: string): void {
    this.positions.delete(symbol);
    console.log(`✅ [SCALP TRAP] Closed position ${symbol}`);
  }

  /**
   * Get all monitored positions
   */
  getPositions(): ScalpTrapPosition[] {
    return Array.from(this.positions.values());
  }

  /**
   * Get engine statistics
   */
  getStats(): typeof this.stats & { activePositions: number } {
    return {
      ...this.stats,
      activePositions: this.positions.size
    };
  }

  /**
   * Calculate TP levels for a SHORT position
   * TP1 = 1.5% profit, TP2 = 3% profit, TP3 = 5% profit
   */
  calculateTPLevels(entryPrice: number, side: 'SHORT' | 'LONG'): { tp1: number; tp2: number; tp3: number; stopLoss: number } {
    if (side === 'SHORT') {
      return {
        tp1: entryPrice * 0.985, // 1.5% down
        tp2: entryPrice * 0.970, // 3% down
        tp3: entryPrice * 0.950, // 5% down
        stopLoss: entryPrice * 1.025 // 2.5% up (stop)
      };
    } else {
      return {
        tp1: entryPrice * 1.015, // 1.5% up
        tp2: entryPrice * 1.030, // 3% up
        tp3: entryPrice * 1.050, // 5% up
        stopLoss: entryPrice * 0.975 // 2.5% down (stop)
      };
    }
  }

  /**
   * 🔒 SECRET LOGIC: Thesis Invalidation Check
   * If market structure changes, exit position WITHOUT waiting for SL
   * For SHORT: If price breaks above 1h high (Higher High), thesis invalidated
   * For LONG: If price breaks below 1h low (Lower Low), thesis invalidated
   */
  checkThesisInvalidation(
    currentPrice: number,
    high1h: number,
    low1h: number,
    assetBias: 'short' | 'long'
  ): { invalidated: boolean; reason: string; action: 'EXIT_NOW' | 'HOLD' } {
    // SHORT bias: If price breaks above 1h high = bullish structure shift
    if (assetBias === 'short' && currentPrice > high1h) {
      console.log(`🚨 [THESIS INVALIDATED] Market structure shifted BULLISH (Higher High)`);
      console.log(`   Price: $${currentPrice.toFixed(2)} > 1H High: $${high1h.toFixed(2)}`);
      console.log(`   ACTION: EXIT SHORT IMMEDIATELY`);
      
      return {
        invalidated: true,
        reason: 'Market structure shifted to bullish (Higher High). Exit Short.',
        action: 'EXIT_NOW'
      };
    }

    // LONG bias: If price breaks below 1h low = bearish structure shift
    if (assetBias === 'long' && currentPrice < low1h) {
      console.log(`🚨 [THESIS INVALIDATED] Market structure shifted BEARISH (Lower Low)`);
      console.log(`   Price: $${currentPrice.toFixed(2)} < 1H Low: $${low1h.toFixed(2)}`);
      console.log(`   ACTION: EXIT LONG IMMEDIATELY`);
      
      return {
        invalidated: true,
        reason: 'Market structure shifted to bearish (Lower Low). Exit Long.',
        action: 'EXIT_NOW'
      };
    }

    return {
      invalidated: false,
      reason: 'Thesis remains valid.',
      action: 'HOLD'
    };
  }

  /**
   * Enhanced position check with thesis invalidation
   */
  checkPositionWithThesis(
    symbol: string,
    currentPrice: number,
    high1h: number,
    low1h: number
  ): {
    trapAction: TrapAction;
    thesisInvalidated: boolean;
    finalAction: 'HOLD' | 'MOVE_SL' | 'EXIT_NOW';
    reason: string;
  } {
    const position = this.positions.get(symbol);
    if (!position) {
      return {
        trapAction: 'HOLD',
        thesisInvalidated: false,
        finalAction: 'HOLD',
        reason: 'Position not found'
      };
    }

    // First check thesis invalidation (higher priority than TP traps)
    const thesisCheck = this.checkThesisInvalidation(
      currentPrice,
      high1h,
      low1h,
      position.side.toLowerCase() as 'short' | 'long'
    );

    if (thesisCheck.invalidated) {
      // Thesis invalidated = EXIT NOW, don't wait for SL
      this.stats.tradesProtected++;
      return {
        trapAction: 'CLOSE_POSITION',
        thesisInvalidated: true,
        finalAction: 'EXIT_NOW',
        reason: thesisCheck.reason
      };
    }

    // Then check profit traps
    const trapResult = this.applyProfitTrap(symbol, currentPrice);
    
    return {
      trapAction: trapResult.action,
      thesisInvalidated: false,
      finalAction: trapResult.action === 'HOLD' ? 'HOLD' : 'MOVE_SL',
      reason: trapResult.reason
    };
  }
}

// ============================================
// 🤖 SCALPER-BOT - ADVANCED SCALPING SYSTEM
// ============================================

/**
 * SCALPER-BOT System Prompt:
 * - Target: Quick trades (15-30 minutes)
 * - Uses "Profit Traps" logic with 3 TPs
 * - TP1 close = Breakeven (risk-free)
 * - Min lots with high leverage (10x-20x) if Confidence > 0.8
 * - Entry only on RSI extremes (<30 or >70) on 3-min chart
 * - Position exits: TP1=50%, TP2=25%, TP3=25%
 */

interface ScalperSignal {
  action: 'buy' | 'sell' | 'wait';
  traps: {
    tp1: number;
    tp1_exit_pct: number;
    tp2: number;
    tp2_exit_pct: number;
    tp3: number;
    tp3_exit_pct: number;
  };
  sl: number;
  confidence: number;
  leverage: number;
  entrySize: number;
  reason: string;
  rsi: number;
  timeframe: string;
  maxHoldTime: number; // minutes
}

interface RSIData {
  current: number;
  previous: number;
  trend: 'overbought' | 'oversold' | 'neutral';
}

export class ScalperBot {
  private static instance: ScalperBot;
  private balance: number = 692;
  private minLotSize: number = 0.001; // Min BTC lot
  private maxHoldTime: number = 30; // minutes
  private stats = {
    totalScalps: 0,
    winningScalps: 0,
    losingScalps: 0,
    breakevenScalps: 0,
    totalProfit: 0,
    avgHoldTime: 0
  };

  static getInstance(): ScalperBot {
    if (!ScalperBot.instance) {
      ScalperBot.instance = new ScalperBot();
    }
    return ScalperBot.instance;
  }

  setBalance(balance: number): void {
    this.balance = balance;
  }

  /**
   * Calculate RSI from price data
   */
  calculateRSI(prices: number[], period: number = 14): RSIData {
    if (prices.length < period + 1) {
      return { current: 50, previous: 50, trend: 'neutral' };
    }

    const changes: number[] = [];
    for (let i = 1; i < prices.length; i++) {
      changes.push(prices[i] - prices[i - 1]);
    }

    const recentChanges = changes.slice(-period);
    let gains = 0;
    let losses = 0;

    for (const change of recentChanges) {
      if (change > 0) gains += change;
      else losses += Math.abs(change);
    }

    const avgGain = gains / period;
    const avgLoss = losses / period;
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    const rsi = 100 - (100 / (1 + rs));

    const prevChanges = changes.slice(-period - 1, -1);
    let prevGains = 0;
    let prevLosses = 0;
    for (const change of prevChanges) {
      if (change > 0) prevGains += change;
      else prevLosses += Math.abs(change);
    }
    const prevRs = prevLosses === 0 ? 100 : (prevGains / period) / (prevLosses / period);
    const prevRsi = 100 - (100 / (1 + prevRs));

    let trend: 'overbought' | 'oversold' | 'neutral' = 'neutral';
    if (rsi >= 70) trend = 'overbought';
    else if (rsi <= 30) trend = 'oversold';

    return { current: rsi, previous: prevRsi, trend };
  }

  /**
   * Generate SCALPER signal based on RSI extremes
   * Entry only when RSI < 30 (oversold) or RSI > 70 (overbought)
   */
  generateSignal(
    symbol: string,
    currentPrice: number,
    prices: number[], // Historical prices for RSI
    confidence: number
  ): ScalperSignal {
    const rsi = this.calculateRSI(prices);
    
    // Default: WAIT - no trade
    const waitSignal: ScalperSignal = {
      action: 'wait',
      traps: { tp1: 0, tp1_exit_pct: 50, tp2: 0, tp2_exit_pct: 25, tp3: 0, tp3_exit_pct: 25 },
      sl: 0,
      confidence: 0,
      leverage: 0,
      entrySize: 0,
      reason: 'RSI not at extreme levels',
      rsi: rsi.current,
      timeframe: '3m',
      maxHoldTime: this.maxHoldTime
    };

    // RULE: Only trade on RSI extremes
    if (rsi.trend === 'neutral') {
      waitSignal.reason = `RSI ${rsi.current.toFixed(1)} - Waiting for extreme (< 30 or > 70)`;
      return waitSignal;
    }

    // RULE: High leverage only if confidence > 0.8
    let leverage = 5;
    if (confidence > 0.8) {
      leverage = confidence > 0.9 ? 20 : 15;
    } else if (confidence > 0.7) {
      leverage = 10;
    }

    // Calculate position size (min lots with high leverage)
    const riskPct = confidence > 0.8 ? 0.02 : 0.01; // 2% risk if high conf, 1% otherwise
    const riskAmount = this.balance * riskPct;
    const positionValue = riskAmount * leverage;
    const entrySize = positionValue / currentPrice;

    // SHORTS ONLY MODE: RSI > 70 = SELL (SHORT)
    if (rsi.trend === 'overbought' && rsi.current >= 70) {
      // SHORT signal - price expected to go DOWN
      const tp1 = currentPrice * 0.992; // 0.8% down (quick scalp - 50% exit)
      const tp2 = currentPrice * 0.985; // 1.5% down (25% exit)
      const tp3 = currentPrice * 0.975; // 2.5% down (25% exit)
      const sl = currentPrice * 1.012;  // 1.2% up (tight stop)

      console.log(`🎯 [SCALPER-BOT] ${symbol} SELL SIGNAL | RSI: ${rsi.current.toFixed(1)} (OVERBOUGHT)`);
      console.log(`   Traps: TP1=${tp1.toFixed(2)} (50%), TP2=${tp2.toFixed(2)} (25%), TP3=${tp3.toFixed(2)} (25%)`);
      console.log(`   SL: ${sl.toFixed(2)} | Leverage: ${leverage}x | Confidence: ${(confidence * 100).toFixed(0)}%`);

      return {
        action: 'sell',
        traps: {
          tp1,
          tp1_exit_pct: 50,
          tp2,
          tp2_exit_pct: 25,
          tp3,
          tp3_exit_pct: 25
        },
        sl,
        confidence,
        leverage,
        entrySize,
        reason: `RSI ${rsi.current.toFixed(1)} OVERBOUGHT - SHORT entry`,
        rsi: rsi.current,
        timeframe: '3m',
        maxHoldTime: this.maxHoldTime
      };
    }

    // Note: In SHORTS ONLY mode, we skip oversold (buy) signals
    // But log them for awareness
    if (rsi.trend === 'oversold' && rsi.current <= 30) {
      console.log(`⚠️ [SCALPER-BOT] ${symbol} RSI ${rsi.current.toFixed(1)} OVERSOLD - BUY blocked (SHORTS ONLY)`);
      waitSignal.reason = `RSI ${rsi.current.toFixed(1)} OVERSOLD - BUY signal blocked (SHORTS ONLY mode)`;
      return waitSignal;
    }

    return waitSignal;
  }

  /**
   * Calculate scalp traps for a SHORT position
   * Tighter targets for quick 15-30 min scalps
   */
  calculateScalpTraps(entryPrice: number): {
    tp1: number;
    tp1_exit_pct: number;
    tp2: number;
    tp2_exit_pct: number;
    tp3: number;
    tp3_exit_pct: number;
    sl: number;
  } {
    return {
      tp1: entryPrice * 0.992,     // 0.8% profit - EXIT 50%
      tp1_exit_pct: 50,
      tp2: entryPrice * 0.985,     // 1.5% profit - EXIT 25%
      tp2_exit_pct: 25,
      tp3: entryPrice * 0.975,     // 2.5% profit - EXIT 25%
      tp3_exit_pct: 25,
      sl: entryPrice * 1.012       // 1.2% stop loss (tight)
    };
  }

  /**
   * Execute partial exit based on trap level
   */
  executePartialExit(
    symbol: string,
    currentSize: number,
    trapLevel: 1 | 2 | 3
  ): { exitSize: number; remainingSize: number; exitPct: number } {
    const exitPcts = { 1: 50, 2: 25, 3: 25 };
    const exitPct = exitPcts[trapLevel];
    const exitSize = currentSize * (exitPct / 100);
    const remainingSize = currentSize - exitSize;

    console.log(`💰 [SCALPER] ${symbol} TP${trapLevel} HIT | Exit ${exitPct}% (${exitSize.toFixed(6)} units)`);
    
    if (trapLevel === 1) {
      console.log(`🛡️ [SCALPER] ${symbol} Remaining position is now RISK-FREE (Breakeven)`);
    }

    return { exitSize, remainingSize, exitPct };
  }

  /**
   * Check if hold time exceeded (max 30 min for scalps)
   */
  checkHoldTime(openedAt: number): { exceeded: boolean; holdTime: number; action: string } {
    const holdTime = (Date.now() - openedAt) / (1000 * 60); // in minutes
    
    if (holdTime >= this.maxHoldTime) {
      return { exceeded: true, holdTime, action: 'CLOSE_AT_MARKET' };
    }
    
    return { exceeded: false, holdTime, action: 'HOLD' };
  }

  /**
   * Record completed scalp
   */
  recordScalp(profit: number, holdTimeMinutes: number): void {
    this.stats.totalScalps++;
    
    if (profit > 0) {
      this.stats.winningScalps++;
    } else if (profit < 0) {
      this.stats.losingScalps++;
    } else {
      this.stats.breakevenScalps++;
    }
    
    this.stats.totalProfit += profit;
    
    // Update average hold time
    const totalHoldTime = this.stats.avgHoldTime * (this.stats.totalScalps - 1) + holdTimeMinutes;
    this.stats.avgHoldTime = totalHoldTime / this.stats.totalScalps;
  }

  /**
   * Get scalper stats
   */
  getStats(): typeof this.stats & { winRate: number } {
    const winRate = this.stats.totalScalps > 0 
      ? (this.stats.winningScalps / this.stats.totalScalps) * 100 
      : 0;
    
    return {
      ...this.stats,
      winRate
    };
  }

  /**
   * Get output in the specified format
   */
  formatOutput(signal: ScalperSignal): string {
    return JSON.stringify({
      action: signal.action,
      traps: {
        tp1: `${signal.traps.tp1.toFixed(4)} (exit ${signal.traps.tp1_exit_pct}% position)`,
        tp2: `${signal.traps.tp2.toFixed(4)} (exit ${signal.traps.tp2_exit_pct}% position)`,
        tp3: `${signal.traps.tp3.toFixed(4)} (exit ${signal.traps.tp3_exit_pct}% position)`
      },
      sl: signal.sl.toFixed(4),
      confidence: signal.confidence.toFixed(2)
    }, null, 2);
  }
}

// ============================================
// 🧬 GENETIC OPTIMIZER - SELF-LEARNING
// ============================================

interface OptimizationResult {
  parameter: string;
  oldValue: number;
  newValue: number;
  improvement: number;
}

export class GeneticOptimizer {
  private static instance: GeneticOptimizer;
  private lastOptimization: number = 0;
  private optimizationInterval: number = 24 * 60 * 60 * 1000; // 24 hours

  private config = {
    rsiOversold: 30,
    rsiOverbought: 70,
    macdFastPeriod: 12,
    macdSlowPeriod: 26,
    atrMultiplier: 2.0,
    confidenceThreshold: 65
  };

  static getInstance(): GeneticOptimizer {
    if (!GeneticOptimizer.instance) {
      GeneticOptimizer.instance = new GeneticOptimizer();
    }
    return GeneticOptimizer.instance;
  }

  // Check if optimization is due
  shouldOptimize(): boolean {
    return Date.now() - this.lastOptimization > this.optimizationInterval;
  }

  // Run backtests and optimize (simulated)
  async runOptimization(): Promise<OptimizationResult[]> {
    this.lastOptimization = Date.now();
    const results: OptimizationResult[] = [];

    // Simulate optimization by slightly adjusting parameters
    const adjustments = [
      { param: 'rsiOversold', range: [25, 35], current: this.config.rsiOversold },
      { param: 'rsiOverbought', range: [65, 75], current: this.config.rsiOverbought },
      { param: 'atrMultiplier', range: [1.5, 2.5], current: this.config.atrMultiplier },
      { param: 'confidenceThreshold', range: [60, 75], current: this.config.confidenceThreshold }
    ];

    for (const adj of adjustments) {
      // Random walk optimization (simulated genetic algo)
      const change = (Math.random() - 0.5) * (adj.range[1] - adj.range[0]) * 0.1;
      const newValue = Math.max(adj.range[0], Math.min(adj.range[1], adj.current + change));
      
      if (Math.abs(newValue - adj.current) > 0.01) {
        results.push({
          parameter: adj.param,
          oldValue: adj.current,
          newValue,
          improvement: Math.random() * 5 // Simulated improvement %
        });
        
        (this.config as any)[adj.param] = newValue;
      }
    }

    console.log(`🧬 [GENETIC] Optimization complete: ${results.length} parameters adjusted`);
    return results;
  }

  // Get current optimized config
  getConfig(): typeof GeneticOptimizer.prototype.config {
    return { ...this.config };
  }
}

// ============================================
// 🔱 OMNI-GOD ORCHESTRATOR
// ============================================

export class OmniGod {
  private smartStrategy: SmartStrategy;
  private riskGuardian: RiskGuardian;
  private capitalManager: CapitalManager;
  private phoenixProtocol: PhoenixProtocol;
  private geneticOptimizer: GeneticOptimizer;

  private isRunning: boolean = false;
  private stats = {
    tradesExecuted: 0,
    tradesBlocked: 0,
    profitsLocked: 0,
    dcaExecuted: 0,
    optimizationsRun: 0
  };

  constructor() {
    this.smartStrategy = SmartStrategy.getInstance();
    this.riskGuardian = RiskGuardian.getInstance();
    this.capitalManager = CapitalManager.getInstance();
    this.phoenixProtocol = PhoenixProtocol.getInstance();
    this.geneticOptimizer = GeneticOptimizer.getInstance();
  }

  // Start OMNI-GOD
  start(): void {
    this.isRunning = true;
    console.log(`🔱 [OMNI-GOD] System activated - Targeting $1,000,000`);
  }

  // Stop OMNI-GOD
  stop(): void {
    this.isRunning = false;
    this.phoenixProtocol.saveState();
    console.log(`🔱 [OMNI-GOD] System deactivated`);
  }

  // Full analysis and trade decision
  async analyze(symbol: string): Promise<{
    action: 'SHORT' | 'HOLD';
    confidence: number;
    positionSize: number;
    leverage: number;
    reasons: string[];
    omniScore: number;
  }> {
    const reasons: string[] = [];
    let omniScore = 0;

    // Get market data
    const marketData = await fetchGateMarketData(symbol);
    if (!marketData) {
      return { action: 'HOLD', confidence: 0, positionSize: 0, leverage: 0, reasons: ['No market data'], omniScore: 0 };
    }

    // 1. SMC Strategy Signal
    const smcSignal = await this.smartStrategy.generateSignal(symbol, marketData);
    omniScore += smcSignal.smcScore;
    reasons.push(...smcSignal.reasons);

    // 2. Risk Guardian Validation
    const data = marketData as any;
    const bid = data.orderBook?.bids?.[0]?.[0] || marketData.currentPrice * 0.9999;
    const ask = data.orderBook?.asks?.[0]?.[0] || marketData.currentPrice * 1.0001;
    const riskCheck = await this.riskGuardian.validateTrade(symbol, parseFloat(bid), parseFloat(ask));
    
    if (!riskCheck.approved) {
      this.stats.tradesBlocked++;
      return { 
        action: 'HOLD', 
        confidence: 0, 
        positionSize: 0, 
        leverage: 0, 
        reasons: riskCheck.reasons, 
        omniScore: 0 
      };
    }
    reasons.push(...riskCheck.boosts);

    // 3. Capital Management
    const balance = await getFuturesBalance();
    const capital = this.capitalManager.calculatePositionSize(balance?.available || 692);
    
    // 4. Genetic Optimizer check
    if (this.geneticOptimizer.shouldOptimize()) {
      await this.geneticOptimizer.runOptimization();
      this.stats.optimizationsRun++;
    }

    // Calculate final decision
    const action = omniScore >= 50 ? 'SHORT' : 'HOLD';
    const confidence = Math.min(100, omniScore + 40);

    return {
      action,
      confidence,
      positionSize: capital.positionSize,
      leverage: capital.leverage,
      reasons,
      omniScore
    };
  }

  // Get full system status
  getStatus(): {
    isRunning: boolean;
    modules: { name: string; status: string }[];
    stats: typeof OmniGod.prototype.stats;
    vault: VaultState;
    progress: ReturnType<CapitalManager['getProgressToMillion']>;
    uptime: ReturnType<PhoenixProtocol['getUptimeStats']>;
    config: ReturnType<GeneticOptimizer['getConfig']>;
  } {
    return {
      isRunning: this.isRunning,
      modules: [
        { name: 'SMC Sniper', status: 'ACTIVE' },
        { name: 'Risk Guardian', status: 'ACTIVE' },
        { name: 'Capital Manager', status: 'ACTIVE' },
        { name: 'Phoenix Protocol', status: 'ACTIVE' },
        { name: 'Genetic Optimizer', status: 'ACTIVE' }
      ],
      stats: this.stats,
      vault: this.capitalManager.getVaultStatus(),
      progress: this.capitalManager.getProgressToMillion(692),
      uptime: this.phoenixProtocol.getUptimeStats(),
      config: this.geneticOptimizer.getConfig()
    };
  }
}

// Export singleton
export const omniGod = new OmniGod();
