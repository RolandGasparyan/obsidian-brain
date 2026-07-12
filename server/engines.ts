import type { MarketData, AgentAnalysis, ConsensusResult, SignalType, TradingStrategy } from "@shared/schema";

export interface EngineStatus {
  id: number;
  name: string;
  status: "ACTIVE" | "IDLE" | "TRIGGERED" | "ERROR";
  lastAction?: string;
  timestamp: string;
}

export interface SmartGate {
  name: string;
  passed: boolean;
  reason: string;
}

export interface WhaleActivity {
  detected: boolean;
  direction: "buy" | "sell" | "neutral";
  volume: number;
  impact: "high" | "medium" | "low";
}

export interface LiquiditySweep {
  detected: boolean;
  type: "stop_hunt_longs" | "stop_hunt_shorts" | "none";
  level: number;
  recovered: boolean;
}

export interface OIDivergence {
  detected: boolean;
  type: "bullish" | "bearish" | "none";
  priceDirection: "up" | "down" | "flat";
  oiDirection: "up" | "down" | "flat";
}

export interface CircuitBreaker {
  triggered: boolean;
  reason?: string;
  cooldownUntil?: string;
}

export interface EngineOutput {
  engines: EngineStatus[];
  smartGates: SmartGate[];
  whaleActivity: WhaleActivity;
  liquiditySweep: LiquiditySweep;
  oiDivergence: OIDivergence;
  circuitBreaker: CircuitBreaker;
  profitCascade: { level: number; percent: number }[];
  governorRisk: { maxRiskPercent: number; minRR: number; approved: boolean };
  turboScalp: { enabled: boolean; microTarget: number; microStop: number };
}

export class TradingEngines {
  private engineStatuses: EngineStatus[] = [];
  private dailyLoss: number = 0;
  private dailyTrades: number = 0;
  private consecutiveLosses: number = 0;
  private lastTradeTime: Date | null = null;

  constructor() {
    this.initializeEngines();
  }

  private initializeEngines() {
    const engineNames = [
      "TOP 3 SCANNER & ROTATION",
      "PRE-LLM REGIME FILTER",
      "MARKET INTEL ENGINE",
      "MULTI-AGENT BRAIN",
      "THE GOVERNOR (5%/2:1 RR)",
      "TURBO-SCALPER",
      "CIRCUIT BREAKERS",
      "TELEGRAM NOTIFIER",
      "COMMAND CENTER",
      "SELF-UPGRADER"
    ];

    this.engineStatuses = engineNames.map((name, i) => ({
      id: i + 1,
      name,
      status: "ACTIVE" as const,
      timestamp: new Date().toISOString()
    }));
  }

  engine1_ScanTop3(marketDataArray: MarketData[]): MarketData[] {
    this.updateEngine(1, "TRIGGERED", "Scanning top 3 pairs by score...");
    
    const scored = marketDataArray.map(m => ({
      data: m,
      score: this.calculatePairScore(m)
    }));
    
    scored.sort((a, b) => b.score - a.score);
    const top3 = scored.slice(0, 3).map(s => s.data);
    
    this.updateEngine(1, "ACTIVE", `Top 3: ${top3.map(t => t.symbol).join(", ")}`);
    return top3;
  }

  private calculatePairScore(m: MarketData): number {
    let score = 0;
    
    const volatility = ((m.high24h - m.low24h) / m.currentPrice) * 100;
    score += Math.min(25, volatility * 5);
    
    const volumeScore = Math.min(25, (m.volume24h / 1e9) * 5);
    score += volumeScore;
    
    const spreadScore = m.bidAskSpread ? Math.max(0, 25 - m.bidAskSpread * 10000) : 15;
    score += spreadScore;
    
    const rsiMomentum = Math.abs(m.rsi - 50) / 2;
    score += Math.min(25, rsiMomentum);
    
    if (Math.abs(m.fundingRate) > 0.0005) {
      score += 15;
    }
    
    return score;
  }

  engine2_RegimeFilter(marketData: MarketData): { regime: "TRENDING" | "RANGING" | "VOLATILE" | "DEAD"; tradeable: boolean } {
    this.updateEngine(2, "TRIGGERED", "Analyzing market regime...");
    
    const volatility = ((marketData.high24h - marketData.low24h) / marketData.currentPrice) * 100;
    const rsi = marketData.rsi;
    const macdStrength = Math.abs(marketData.macd.histogram);
    
    let regime: "TRENDING" | "RANGING" | "VOLATILE" | "DEAD" = "RANGING";
    let tradeable = true;
    
    if (volatility > 5) {
      regime = "VOLATILE";
      tradeable = true;
    } else if (volatility < 1 && macdStrength < 10) {
      regime = "DEAD";
      tradeable = false;
    } else if (rsi > 60 || rsi < 40) {
      regime = "TRENDING";
      tradeable = true;
    }
    
    this.updateEngine(2, "ACTIVE", `Regime: ${regime}, Tradeable: ${tradeable}`);
    return { regime, tradeable };
  }

  engine3_MarketIntel(marketData: MarketData): {
    whaleActivity: WhaleActivity;
    liquiditySweep: LiquiditySweep;
    oiDivergence: OIDivergence;
  } {
    this.updateEngine(3, "TRIGGERED", "Gathering market intelligence...");
    
    const orderBookImbalance = marketData.orderBookImbalance || 0;
    const whaleThreshold = 0.15;
    
    const whaleActivity: WhaleActivity = {
      detected: Math.abs(orderBookImbalance) > whaleThreshold,
      direction: orderBookImbalance > whaleThreshold ? "buy" : orderBookImbalance < -whaleThreshold ? "sell" : "neutral",
      volume: Math.abs(orderBookImbalance) * marketData.volume24h,
      impact: Math.abs(orderBookImbalance) > 0.25 ? "high" : Math.abs(orderBookImbalance) > 0.15 ? "medium" : "low"
    };
    
    const priceVsLow = (marketData.currentPrice - marketData.low24h) / marketData.currentPrice;
    const priceVsHigh = (marketData.high24h - marketData.currentPrice) / marketData.currentPrice;
    
    const liquiditySweep: LiquiditySweep = {
      detected: priceVsLow < 0.005 || priceVsHigh < 0.005,
      type: priceVsLow < 0.005 ? "stop_hunt_longs" : priceVsHigh < 0.005 ? "stop_hunt_shorts" : "none",
      level: priceVsLow < 0.005 ? marketData.low24h : marketData.high24h,
      recovered: Math.abs(marketData.priceChange24h) < 1
    };
    
    const oiChange = marketData.openInterestChange24h || 0;
    const priceChange = marketData.priceChange24h;
    
    const oiDivergence: OIDivergence = {
      detected: (priceChange > 0 && oiChange < 0) || (priceChange < 0 && oiChange > 0),
      type: priceChange > 0 && oiChange < 0 ? "bearish" : priceChange < 0 && oiChange > 0 ? "bullish" : "none",
      priceDirection: priceChange > 0 ? "up" : priceChange < 0 ? "down" : "flat",
      oiDirection: oiChange > 0 ? "up" : oiChange < 0 ? "down" : "flat"
    };
    
    this.updateEngine(3, "ACTIVE", `Whale: ${whaleActivity.detected}, Sweep: ${liquiditySweep.detected}, OI Div: ${oiDivergence.detected}`);
    return { whaleActivity, liquiditySweep, oiDivergence };
  }

  engine5_Governor(consensus: ConsensusResult): { approved: boolean; maxRiskPercent: number; minRR: number; reason: string } {
    this.updateEngine(5, "TRIGGERED", "Evaluating risk parameters...");
    
    const maxRiskPercent = 5;
    const minRR = 1.5; // REDUCED: From 2:1 to 1.5:1 for more trade opportunities
    
    let approved = true;
    let reason = "Trade approved by Governor";
    
    if (!consensus.isActionable) {
      approved = false;
      reason = "Consensus not actionable";
    } else if (consensus.riskReward && consensus.riskReward.toTp2 < minRR) {
      approved = false;
      reason = `Risk:Reward ${consensus.riskReward.toTp2} below minimum ${minRR}`;
    } else if (this.dailyLoss > 10) {
      approved = false;
      reason = "Daily loss limit exceeded (10%)";
    } else if (this.consecutiveLosses >= 3) {
      approved = false;
      reason = "3 consecutive losses - cooling down";
    }
    
    this.updateEngine(5, approved ? "ACTIVE" : "TRIGGERED", reason);
    return { approved, maxRiskPercent, minRR, reason };
  }

  engine6_TurboScalper(marketData: MarketData): { enabled: boolean; microTarget: number; microStop: number; leverage: number } {
    this.updateEngine(6, "TRIGGERED", "Calculating scalp parameters...");
    
    const spread = marketData.bidAskSpread || 0.001;
    const volatility = ((marketData.high24h - marketData.low24h) / marketData.currentPrice) * 100;
    
    const enabled = spread < 0.001 && volatility > 1;
    const microTarget = marketData.currentPrice * 0.003;
    const microStop = marketData.currentPrice * 0.002;
    const leverage = enabled ? 50 : 20;
    
    this.updateEngine(6, enabled ? "ACTIVE" : "IDLE", `Scalping ${enabled ? "enabled" : "disabled"}, Target: ${microTarget.toFixed(2)}`);
    return { enabled, microTarget, microStop, leverage };
  }

  engine7_CircuitBreakers(): CircuitBreaker {
    this.updateEngine(7, "TRIGGERED", "Checking circuit breakers...");
    
    let triggered = false;
    let reason: string | undefined;
    let cooldownUntil: string | undefined;
    
    if (this.dailyLoss > 15) {
      triggered = true;
      reason = "Daily loss exceeds 15% - HALT ALL TRADING";
      cooldownUntil = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    } else if (this.consecutiveLosses >= 5) {
      triggered = true;
      reason = "5 consecutive losses - 1 hour cooldown";
      cooldownUntil = new Date(Date.now() + 60 * 60 * 1000).toISOString();
    } else if (this.dailyTrades >= 20) {
      triggered = true;
      reason = "Max daily trades reached (20)";
      cooldownUntil = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();
    }
    
    this.updateEngine(7, triggered ? "TRIGGERED" : "ACTIVE", reason || "All systems normal");
    return { triggered, reason, cooldownUntil };
  }

  runSmartGates(marketData: MarketData, consensus: ConsensusResult): SmartGate[] {
    const gates: SmartGate[] = [
      {
        name: "Confluence Check",
        passed: consensus.confluenceLevel !== "WEAK",
        reason: `Confluence: ${consensus.confluenceLevel}`
      },
      {
        name: "Volume Filter",
        passed: marketData.volume24h > 100000000,
        reason: `Volume: $${(marketData.volume24h / 1e9).toFixed(2)}B`
      },
      {
        name: "Spread Check",
        passed: (marketData.bidAskSpread || 0.01) < 0.005,
        reason: `Spread: ${((marketData.bidAskSpread || 0) * 100).toFixed(3)}%`
      },
      {
        name: "RSI Filter",
        passed: marketData.rsi > 20 && marketData.rsi < 80,
        reason: `RSI: ${marketData.rsi}`
      },
      {
        name: "Funding Rate",
        passed: Math.abs(marketData.fundingRate) < 0.001,
        reason: `Funding: ${(marketData.fundingRate * 100).toFixed(4)}%`
      },
      {
        name: "MACD Alignment",
        passed: (consensus.consensusSignal === "long" && marketData.macd.histogram > 0) ||
                (consensus.consensusSignal === "short" && marketData.macd.histogram < 0) ||
                consensus.consensusSignal === "neutral",
        reason: `MACD Hist: ${marketData.macd.histogram.toFixed(2)}`
      },
      {
        name: "Price vs VWAP",
        passed: true,
        reason: `${marketData.currentPrice > marketData.vwap ? "Above" : "Below"} VWAP`
      },
      {
        name: "Bollinger Position",
        passed: marketData.currentPrice > marketData.bollingerBands.lower && 
                marketData.currentPrice < marketData.bollingerBands.upper,
        reason: `Within Bollinger Bands`
      }
    ];
    
    return gates;
  }

  getProfitCascade(): { level: number; percent: number }[] {
    return [
      { level: 1, percent: 50 },
      { level: 2, percent: 70 },
      { level: 3, percent: 90 },
      { level: 4, percent: 100 }
    ];
  }

  runAllEngines(marketData: MarketData, consensus: ConsensusResult): EngineOutput {
    const intel = this.engine3_MarketIntel(marketData);
    const regime = this.engine2_RegimeFilter(marketData);
    const governor = this.engine5_Governor(consensus);
    const turboScalp = this.engine6_TurboScalper(marketData);
    const circuitBreaker = this.engine7_CircuitBreakers();
    const smartGates = this.runSmartGates(marketData, consensus);
    
    this.updateEngine(4, "ACTIVE", "Multi-Agent Brain coordinating...");
    this.updateEngine(8, "ACTIVE", "Telegram ready");
    this.updateEngine(9, "ACTIVE", "Command Center online");
    this.updateEngine(10, "ACTIVE", "Self-upgrader monitoring");
    
    return {
      engines: this.engineStatuses,
      smartGates,
      whaleActivity: intel.whaleActivity,
      liquiditySweep: intel.liquiditySweep,
      oiDivergence: intel.oiDivergence,
      circuitBreaker,
      profitCascade: this.getProfitCascade(),
      governorRisk: { maxRiskPercent: governor.maxRiskPercent, minRR: governor.minRR, approved: governor.approved },
      turboScalp: { enabled: turboScalp.enabled, microTarget: turboScalp.microTarget, microStop: turboScalp.microStop }
    };
  }

  private updateEngine(id: number, status: "ACTIVE" | "IDLE" | "TRIGGERED" | "ERROR", lastAction: string) {
    const engine = this.engineStatuses.find(e => e.id === id);
    if (engine) {
      engine.status = status;
      engine.lastAction = lastAction;
      engine.timestamp = new Date().toISOString();
    }
  }

  getEngineStatuses(): EngineStatus[] {
    return this.engineStatuses;
  }

  recordTrade(profit: number) {
    this.dailyTrades++;
    if (profit < 0) {
      this.dailyLoss += Math.abs(profit);
      this.consecutiveLosses++;
    } else {
      this.consecutiveLosses = 0;
    }
    this.lastTradeTime = new Date();
  }

  resetDaily() {
    this.dailyLoss = 0;
    this.dailyTrades = 0;
    this.consecutiveLosses = 0;
  }
}

export const tradingEngines = new TradingEngines();
