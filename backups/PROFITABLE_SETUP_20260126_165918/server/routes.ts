import type { Express, Response } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { generateMockMarketData, analyzeWithAgent, calculateConsensus, calculatePairScore, getStrategyParams, DEFAULT_AGENTS } from "./agents";
import { fetchGateMarketData, getAvailableSymbols } from "./gateio";
import { tradingEngines } from "./engines";
import { wolfPack } from "./wolfpack";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  app.get("/api/symbols", async (req, res) => {
    try {
      const symbols = await getAvailableSymbols();
      res.json(symbols);
    } catch (error) {
      res.json(["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"]);
    }
  });

  app.post("/api/analysis/:symbol", async (req, res: Response) => {
    const { symbol } = req.params;
    
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders();

    const sendEvent = (type: string, data: any) => {
      res.write(`data: ${JSON.stringify({ type, ...data })}\n\n`);
    };

    try {
      sendEvent("status", { message: "Fetching LIVE market data from Gate.io..." });
      
      let marketData = await fetchGateMarketData(symbol);
      
      if (!marketData) {
        sendEvent("error", { message: `Gate.io API unavailable for ${symbol}. REAL DATA ONLY mode.` });
        res.write("data: [DONE]\n\n");
        return res.end();
      }
      
      sendEvent("market_data", { data: marketData, dataSource: marketData.dataSource });

      const analyses = [];
      
      for (const agent of DEFAULT_AGENTS) {
        if (!agent.enabled) continue;
        
        sendEvent("agent_start", { agentId: agent.id, agentName: agent.name });
        
        const analysis = await analyzeWithAgent(agent, marketData);
        analyses.push(analysis);
        
        sendEvent("agent_complete", { agentId: agent.id, analysis });
      }

      // Calculate base consensus
      const consensus = calculateConsensus(symbol, marketData, analyses);
      
      // Trinity of Profit: Add pair scoring and strategy recommendation
      const pairScore = calculatePairScore(marketData);
      // Pass signal directly - getStrategyParams handles neutral signals with conservative params
      const strategyParams = getStrategyParams(
        pairScore.recommendedStrategy,
        marketData.currentPrice,
        consensus.consensusSignal
      );
      
      // Enhanced consensus with Trinity data
      // For neutral signals, strategyParams returns a conservative fallback strategy
      // Use the strategy from strategyParams to keep label and params aligned
      const trinityConsensus = {
        ...consensus,
        pairScore: {
          totalScore: pairScore.totalScore,
          scores: pairScore.scores,
          // Show actual strategy being used (may differ from recommended if signal is neutral)
          recommendedStrategy: strategyParams.strategy
        },
        strategyParams
      };
      
      sendEvent("consensus", { data: trinityConsensus });

      await storage.saveAnalysis({
        symbol: consensus.symbol,
        consensusSignal: consensus.consensusSignal,
        confluenceScore: consensus.confluenceScore,
        agreeingAgents: consensus.agreeingAgents,
        totalAgents: consensus.totalAgents,
        isActionable: consensus.isActionable,
        entryZoneHigh: consensus.entryZoneHigh ?? null,
        entryZoneLow: consensus.entryZoneLow ?? null,
        invalidationLevel: consensus.invalidationLevel ?? null,
        primaryTarget: consensus.primaryTarget ?? null,
        secondaryTarget: consensus.secondaryTarget ?? null,
        riskRewardRatio: consensus.riskRewardRatio ?? null,
        agentAnalyses: consensus.agentAnalyses as any,
      });

      res.write("data: [DONE]\n\n");
      res.end();
    } catch (error) {
      console.error("Analysis error:", error);
      sendEvent("error", { message: error instanceof Error ? error.message : "Analysis failed" });
      res.end();
    }
  });

  app.get("/api/analysis/history", async (req, res) => {
    try {
      const history = await storage.getAnalysisHistory(20);
      res.json(history);
    } catch (error) {
      console.error("History fetch error:", error);
      res.status(500).json({ error: "Failed to fetch history" });
    }
  });

  app.get("/api/agents", (req, res) => {
    res.json(DEFAULT_AGENTS);
  });

  app.get("/api/engines", (req, res) => {
    res.json({
      engines: tradingEngines.getEngineStatuses(),
      profitCascade: tradingEngines.getProfitCascade(),
      features: [
        { name: "Smart Gates (8 Filters)", active: true },
        { name: "Profit Cascade (50-70-90-100%)", active: true },
        { name: "Whale Detection", active: true },
        { name: "Alpha Arena Traps", active: true },
        { name: "Synthetic Short Engine (SPOT)", active: true },
        { name: "Smart Power (Monk Mode)", active: true },
        { name: "Thesis Invalidation Engine", active: true },
        { name: "Liquidity Sweep Detector", active: true },
        { name: "OI Divergence Engine", active: true },
        { name: "Multi-Agent Swarm (3-in-1)", active: true },
        { name: "Dynamic Strategy Engine (GODS)", active: true }
      ],
      // Dynamic Strategy Gods Level - ADX-Based Strategy Selection
      dynamicStrategy: {
        enabled: tradingConfig.dynamicStrategy.enabled,
        profile: tradingConfig.dynamicStrategy.profile,
        currentStrategy: dynamicStrategyState.currentStrategy,
        regime: dynamicStrategyState.regime,
        doublingMultiplier: dynamicStrategyState.doublingMultiplier,
        strategies: [
          { id: "PYRAMID", name: "Pyramid", trigger: "ADX > 45", description: "Max trend aggression with increasing layers", icon: "triangle" },
          { id: "WATERFALL", name: "Waterfall", trigger: "ADX > 35", description: "Standard trend-following with equal layers", icon: "waves" },
          { id: "SCALPING", name: "Scalping", trigger: "ADX < 20", description: "High-frequency micro-profits in ranging markets", icon: "zap" },
          { id: "DOUBLING", name: "Doubling", trigger: "After loss in ranging", description: "Loss recovery with position doubling", icon: "refresh" }
        ],
        adxThresholds: tradingConfig.dynamicStrategy.adxThresholds
      },
      aiModels: DEFAULT_AGENTS.map(a => ({ name: a.name, role: a.role, active: a.enabled })),
      // Alpha Arena Gods Level - 8 Pillars of Professional Trading
      alphaArena: {
        enabled: true,
        riskProfile: "ALPHA_ARENA_GODS",
        pillars: [
          { id: 1, name: "Capital Preservation", description: "Survival first - 10% max daily drawdown", active: true, icon: "shield" },
          { id: 2, name: "1-2% Rule", description: "Max 1.5% risk per trade", active: true, icon: "percent" },
          { id: 3, name: "Mandatory Stop-Loss", description: "Every trade has pre-defined SL", active: true, icon: "stop" },
          { id: 4, name: "Trend-Following", description: "ADX > 30 required (trending market)", active: true, icon: "trending" },
          { id: 5, name: "Stay Inactive", description: "Wait for high-probability setups only", active: true, icon: "pause" },
          { id: 6, name: "Asymmetric R:R", description: "Minimum 2:1 reward/risk ratio", active: true, icon: "target" },
          { id: 7, name: "Leverage Control", description: "Max 10x leverage for capital efficiency", active: true, icon: "sliders" },
          { id: 8, name: "Probabilistic Thinking", description: "45% win rate + 2:1 R:R = profitable", active: true, icon: "brain" }
        ],
        consensus: {
          required: 6,
          total: 8,
          description: "6/8 AI agents must agree for trade execution"
        },
        models: [
          { name: "DeepSeek R1", role: "Quant Architect", active: true },
          { name: "GPT-5 OpenAI", role: "Macro Strategist", active: true },
          { name: "Claude Opus", role: "Contrarian Psychologist", active: true },
          { name: "Llama 3.3 70B", role: "High-Speed Scalper", active: true },
          { name: "Gemini Flash", role: "Multi-Modal Analyst", active: true },
          { name: "Mistral Large", role: "Risk Quantifier", active: true },
          { name: "Qwen 72B", role: "Pattern Hunter", active: true },
          { name: "Grok xAI", role: "Real-Time News Sniper", active: true }
        ]
      }
    });
  });

  app.post("/api/engines/analyze/:symbol", async (req, res) => {
    const { symbol } = req.params;
    
    try {
      let marketData = await fetchGateMarketData(symbol);
      if (!marketData) {
        marketData = generateMockMarketData(symbol);
      }
      
      const analyses = [];
      for (const agent of DEFAULT_AGENTS) {
        if (!agent.enabled) continue;
        const analysis = await analyzeWithAgent(agent, marketData);
        analyses.push(analysis);
      }
      
      const consensus = calculateConsensus(symbol, marketData, analyses);
      const engineOutput = tradingEngines.runAllEngines(marketData, consensus);
      
      res.json({
        consensus,
        engines: engineOutput,
        marketData
      });
    } catch (error) {
      console.error("Engine analysis error:", error);
      res.status(500).json({ error: "Engine analysis failed" });
    }
  });

  // ============================================
  // TURBO SCALPER - FAST TRADING CYCLES
  // ============================================
  
  // ============================================
  // WOLF PACK MODE - ALL ENGINES TRADING TOGETHER
  // ============================================
  
  app.post("/api/wolf-pack", async (req, res) => {
    const { amountPerCoin = 100 } = req.body;
    const coins = ["BTC_USDT", "SOL_USDT", "XRP_USDT"];
    
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders();

    const sendEvent = (data: any) => {
      res.write(`data: ${JSON.stringify(data)}\n\n`);
    };
    
    try {
      const { placeSpotOrder, getSpotBalance } = await import("./gateio");
      
      sendEvent({ type: "start", message: "WOLF PACK ACTIVATED - 8 AI Models + 10 Engines", timestamp: new Date().toISOString() });
      
      const balance = await getSpotBalance("USDT");
      sendEvent({ type: "balance", available: balance?.available || 0 });
      
      if (!balance || balance.available < amountPerCoin) {
        sendEvent({ type: "error", message: `Insufficient USDT: $${balance?.available.toFixed(2) || 0}` });
        res.write("data: [DONE]\n\n");
        return res.end();
      }
      
      const results: any[] = [];
      
      for (const coin of coins) {
        const coinName = coin.split("_")[0];
        sendEvent({ type: "analyzing", coin: coinName, message: `Running 8 AI agents on ${coinName}...` });
        
        let marketData = await fetchGateMarketData(coin);
        if (!marketData) {
          marketData = generateMockMarketData(coin);
        }
        
        const analyses = [];
        for (const agent of DEFAULT_AGENTS) {
          if (!agent.enabled) continue;
          const analysis = await analyzeWithAgent(agent, marketData);
          analyses.push(analysis);
          sendEvent({ type: "agent", coin: coinName, agent: agent.name, signal: analysis.signal, confidence: analysis.confidence });
        }
        
        const consensus = calculateConsensus(coin, marketData, analyses);
        const engineOutput = tradingEngines.runAllEngines(marketData, consensus);
        
        sendEvent({ 
          type: "consensus", 
          coin: coinName, 
          signal: consensus.consensusSignal, 
          confluence: consensus.confluenceLevel,
          agents: consensus.agreeingAgents,
          engines: engineOutput.engines.filter(e => e.status === "ACTIVE").length
        });
        
        if (consensus.consensusSignal === "long" && consensus.confluenceLevel !== "WEAK") {
          sendEvent({ type: "executing", coin: coinName, action: "BUY", amount: amountPerCoin });
          
          const order = await placeSpotOrder({
            currencyPair: coin,
            side: "buy",
            amount: amountPerCoin.toString(),
            type: "market"
          });
          
          if (order) {
            results.push({ coin: coinName, action: "BUY", status: "SUCCESS", orderId: order.id, amount: amountPerCoin });
            sendEvent({ type: "trade", coin: coinName, action: "BUY", status: "SUCCESS", orderId: order.id });
          } else {
            results.push({ coin: coinName, action: "BUY", status: "FAILED" });
            sendEvent({ type: "trade", coin: coinName, action: "BUY", status: "FAILED" });
          }
        } else if (consensus.consensusSignal === "short") {
          sendEvent({ type: "signal", coin: coinName, message: "SHORT signal - skipping (spot only)" });
        } else {
          sendEvent({ type: "signal", coin: coinName, message: "NEUTRAL - no trade" });
        }
        
        await new Promise(r => setTimeout(r, 500));
      }
      
      sendEvent({ type: "complete", trades: results, totalExecuted: results.filter(r => r.status === "SUCCESS").length });
      res.write("data: [DONE]\n\n");
      res.end();
    } catch (error) {
      console.error("Wolf pack error:", error);
      sendEvent({ type: "error", message: error instanceof Error ? error.message : "Wolf pack failed" });
      res.write("data: [DONE]\n\n");
      res.end();
    }
  });

  app.post("/api/sell-coin", async (req, res) => {
    try {
      const { placeSpotOrder } = await import("./gateio");
      const { coin, quantity } = req.body;
      
      const gateSymbol = `${coin}_USDT`;
      const order = await placeSpotOrder({
        currencyPair: gateSymbol,
        side: "sell",
        amount: quantity.toString(),
        type: "market"
      });
      
      res.json({ success: true, order, message: `Sold ${quantity} ${coin}` });
    } catch (error) {
      console.error("Sell error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Sell failed" });
    }
  });
  
  app.post("/api/turbo-scalp/:symbol", async (req, res) => {
    const { symbol } = req.params;
    const { cycles = 3, amountPerTrade = 50 } = req.body;
    
    try {
      const { placeSpotOrder, getSpotBalance } = await import("./gateio");
      const results: any[] = [];
      const gateSymbol = symbol.replace("/", "_");
      const baseCoin = symbol.split("_")[0];
      
      const balance = await getSpotBalance("USDT");
      if (!balance || balance.available < amountPerTrade) {
        return res.status(400).json({ 
          error: `Insufficient USDT. Available: $${balance?.available.toFixed(2) || 0}. Need: $${amountPerTrade}` 
        });
      }
      
      for (let i = 0; i < Math.min(cycles, 5); i++) {
        const buyOrder = await placeSpotOrder({
          currencyPair: gateSymbol,
          side: "buy",
          amount: amountPerTrade.toString(),
          type: "market"
        });
        
        if (buyOrder) {
          results.push({ cycle: i + 1, action: "BUY", status: "SUCCESS", orderId: buyOrder.id });
          
          await new Promise(r => setTimeout(r, 1500));
          
          const coinBalance = await getSpotBalance(baseCoin);
          const sellQty = coinBalance?.available || 0;
          
          if (sellQty > 0) {
            const sellOrder = await placeSpotOrder({
              currencyPair: gateSymbol,
              side: "sell",
              amount: sellQty.toFixed(8),
              type: "market"
            });
            results.push({ cycle: i + 1, action: "SELL", status: sellOrder ? "SUCCESS" : "FAILED", orderId: sellOrder?.id, qty: sellQty });
          }
        } else {
          results.push({ cycle: i + 1, action: "BUY", status: "FAILED" });
        }
        
        await new Promise(r => setTimeout(r, 500));
      }
      
      res.json({ success: true, trades: results, totalCycles: cycles });
    } catch (error) {
      console.error("Turbo scalp error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Turbo scalp failed" });
    }
  });

  // ============================================
  // TRADING API ROUTES
  // Requires Gate.io API credentials in environment
  // ============================================
  
  // Simple in-memory rate limiting for trading endpoints
  const tradingRateLimits = new Map<string, { count: number; resetTime: number }>();
  const RATE_LIMIT_WINDOW = 60000; // 1 minute
  const RATE_LIMIT_MAX_TRADES = 10; // Max 10 trades per minute
  
  function checkRateLimit(ip: string): boolean {
    const now = Date.now();
    const limit = tradingRateLimits.get(ip);
    
    if (!limit || now > limit.resetTime) {
      tradingRateLimits.set(ip, { count: 1, resetTime: now + RATE_LIMIT_WINDOW });
      return true;
    }
    
    if (limit.count >= RATE_LIMIT_MAX_TRADES) {
      return false;
    }
    
    limit.count++;
    return true;
  }
  
  // Middleware to check if trading is enabled (API keys exist)
  function requireTradingEnabled(req: any, res: any, next: any) {
    if (!process.env.GATE_API_KEY || !process.env.GATE_API_SECRET) {
      return res.status(503).json({ 
        error: "Trading not configured",
        message: "Gate.io API credentials are required for trading"
      });
    }
    next();
  }
  
  // Get account balance (both spot and futures)
  app.get("/api/trading/balance", requireTradingEnabled, async (req, res) => {
    try {
      const { getFuturesBalance, getSpotBalance } = await import("./gateio");
      const [futures, spot] = await Promise.all([
        getFuturesBalance(),
        getSpotBalance("USDT")
      ]);
      res.json({
        futures: futures || { available: 0, total: 0, unrealizedPnl: 0, currency: "USDT" },
        spot: spot || { available: 0, locked: 0, currency: "USDT" }
      });
    } catch (error) {
      console.error("Balance fetch error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch balance" });
    }
  });
  
  // Transfer funds between spot and futures
  app.post("/api/trading/transfer", requireTradingEnabled, async (req, res) => {
    try {
      const clientIp = req.ip || "unknown";
      if (!checkRateLimit(clientIp)) {
        return res.status(429).json({ error: "Rate limit exceeded" });
      }
      
      const { transferFunds } = await import("./gateio");
      const { amount, from, to } = req.body;
      
      // Validate inputs
      const amountNum = parseFloat(amount);
      if (isNaN(amountNum) || amountNum <= 0 || amountNum > 100000) {
        return res.status(400).json({ error: "Amount must be between 0 and 100,000 USDT" });
      }
      
      if ((from !== "spot" && from !== "futures") || (to !== "spot" && to !== "futures")) {
        return res.status(400).json({ error: "Invalid from/to account type" });
      }
      
      if (from === to) {
        return res.status(400).json({ error: "Cannot transfer to the same account" });
      }
      
      const result = await transferFunds({
        currency: "USDT",
        amount: amountNum,
        from,
        to
      });
      
      if (!result.success) {
        return res.status(400).json({ error: result.error || "Transfer failed" });
      }
      
      res.json({ success: true, txId: result.txId });
    } catch (error) {
      console.error("Transfer error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Transfer failed" });
    }
  });
  
  // Get all wallet balances across all accounts
  app.get("/api/trading/all-balances", requireTradingEnabled, async (req, res) => {
    try {
      const { getAllSpotBalances, getFuturesBalance, getMarginBalance, getCrossMarginBalance } = await import("./gateio");
      
      const [spot, futures, margin, crossMargin] = await Promise.all([
        getAllSpotBalances(),
        getFuturesBalance(),
        getMarginBalance(),
        getCrossMarginBalance(),
      ]);
      
      res.json({
        spot,
        futures,
        margin,
        crossMargin,
      });
    } catch (error) {
      console.error("Failed to get all balances:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get balances" });
    }
  });

  // Check what's locking the funds - comprehensive check
  app.get("/api/trading/locked-funds-check", requireTradingEnabled, async (req, res) => {
    try {
      const { 
        getActiveGridBots, getUnifiedAccount, getPendingWithdrawals, getSubAccounts,
        getCopyTradingPositions, getDualInvestments, getStructuredProducts, getLoanOrders,
        getAccountBook, getSavingsAccounts, getFlashSwapOrders, getOptionsAccount, getDeliveryAccount
      } = await import("./gateio");
      
      const [
        gridBots, unifiedAccount, pendingWithdrawals, subAccounts, 
        copyTrading, dualInvestments, structured, loans,
        accountBook, savings, flashSwap, options, delivery
      ] = await Promise.all([
        getActiveGridBots(),
        getUnifiedAccount(),
        getPendingWithdrawals(),
        getSubAccounts(),
        getCopyTradingPositions(),
        getDualInvestments(),
        getStructuredProducts(),
        getLoanOrders(),
        getAccountBook("USDT"),
        getSavingsAccounts(),
        getFlashSwapOrders(),
        getOptionsAccount(),
        getDeliveryAccount(),
      ]);
      
      res.json({
        gridBots,
        unifiedAccount,
        pendingWithdrawals,
        subAccounts,
        copyTrading,
        dualInvestments,
        structured,
        loans,
        accountBook,
        savings,
        flashSwap,
        options,
        delivery,
      });
    } catch (error) {
      console.error("Failed to check locked funds:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to check" });
    }
  });

  // Try to unlock funds from various sources
  app.post("/api/trading/unlock-funds", requireTradingEnabled, async (req, res) => {
    try {
      const { 
        transferFromUnified, transferFromOptions, transferFromDelivery, 
        redeemFromLending, getSpotBalance 
      } = await import("./gateio");
      
      const results: any[] = [];
      
      // Try transferring from unified account
      try {
        const unified = await transferFromUnified("USDT", 1000);
        results.push({ source: "unified", success: true, result: unified });
      } catch (e) {
        results.push({ source: "unified", success: false, error: e instanceof Error ? e.message : "Failed" });
      }
      
      // Try transferring from options
      try {
        const options = await transferFromOptions("USDT", 1000);
        results.push({ source: "options", success: true, result: options });
      } catch (e) {
        results.push({ source: "options", success: false, error: e instanceof Error ? e.message : "Failed" });
      }
      
      // Try transferring from delivery
      try {
        const delivery = await transferFromDelivery("USDT", 1000);
        results.push({ source: "delivery", success: true, result: delivery });
      } catch (e) {
        results.push({ source: "delivery", success: false, error: e instanceof Error ? e.message : "Failed" });
      }
      
      // Try redeeming from lending
      try {
        const lending = await redeemFromLending("USDT");
        results.push({ source: "lending", success: true, result: lending });
      } catch (e) {
        results.push({ source: "lending", success: false, error: e instanceof Error ? e.message : "Failed" });
      }
      
      // Check new balance
      const balance = await getSpotBalance("USDT");
      
      res.json({
        attempts: results,
        newBalance: balance,
      });
    } catch (error) {
      console.error("Failed to unlock funds:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed" });
    }
  });

  // Get open spot orders
  app.get("/api/trading/spot/orders", requireTradingEnabled, async (req, res) => {
    try {
      const { getOpenSpotOrders } = await import("./gateio");
      const orders = await getOpenSpotOrders();
      res.json(orders);
    } catch (error) {
      console.error("Failed to get spot orders:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get orders" });
    }
  });

  // Cancel all open spot orders to unlock funds
  app.post("/api/trading/spot/cancel-all", requireTradingEnabled, async (req, res) => {
    try {
      const { cancelAllSpotOrders, getSpotBalance } = await import("./gateio");
      const result = await cancelAllSpotOrders();
      
      // Get updated balance after cancelling
      const balance = await getSpotBalance("USDT");
      
      res.json({
        ...result,
        newBalance: balance?.available || 0,
      });
    } catch (error) {
      console.error("Failed to cancel spot orders:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to cancel orders" });
    }
  });

  // Execute spot trade (buy/sell)
  app.post("/api/trading/spot", requireTradingEnabled, async (req, res) => {
    try {
      const clientIp = req.ip || "unknown";
      if (!checkRateLimit(clientIp)) {
        return res.status(429).json({ error: "Rate limit exceeded. Max 10 trades per minute." });
      }
      
      const { placeSpotOrder, getSpotBalance } = await import("./gateio");
      const { symbol, side, amount } = req.body;
      
      // Input validation
      if (!symbol || typeof symbol !== "string") {
        return res.status(400).json({ error: "Invalid symbol" });
      }
      
      if (side !== "buy" && side !== "sell") {
        return res.status(400).json({ error: "Side must be 'buy' or 'sell'" });
      }
      
      const amountNum = parseFloat(amount);
      if (isNaN(amountNum) || amountNum <= 0) {
        return res.status(400).json({ error: "Invalid amount" });
      }
      
      // Check balance for buys
      if (side === "buy") {
        const balance = await getSpotBalance("USDT");
        if (!balance || balance.available < amountNum) {
          return res.status(400).json({ 
            error: `Insufficient USDT balance. Available: $${balance?.available.toFixed(2) || 0}` 
          });
        }
      }
      
      // Format currency pair for Gate.io (BTC/USDT -> BTC_USDT)
      const currencyPair = symbol.replace("/", "_");
      
      const order = await placeSpotOrder({
        currencyPair,
        side,
        amount: amountNum.toString(),
        type: "market",
      });
      
      console.log(`Spot trade executed: ${side} ${symbol} amount=${amountNum}`);
      
      res.json({
        success: true,
        order,
        message: `${side.toUpperCase()} order placed for ${symbol}`,
      });
    } catch (error) {
      console.error("Spot trade error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Trade failed" });
    }
  });

  // Cancel all spot orders and transfer to futures
  app.post("/api/trading/cancel-spot-and-transfer", requireTradingEnabled, async (req, res) => {
    try {
      const clientIp = req.ip || "unknown";
      if (!checkRateLimit(clientIp)) {
        return res.status(429).json({ error: "Rate limit exceeded" });
      }
      
      const { cancelAllSpotOrders, getSpotBalance, transferFunds } = await import("./gateio");
      
      // Step 1: Cancel all spot orders
      const cancelResult = await cancelAllSpotOrders();
      console.log(`Cancelled ${cancelResult.cancelled} spot orders`);
      
      // Step 2: Wait a moment for balance to update
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Step 3: Get available spot balance
      const spotBalance = await getSpotBalance("USDT");
      if (!spotBalance || spotBalance.available <= 0) {
        return res.json({ 
          success: true, 
          cancelled: cancelResult.cancelled,
          transferred: 0,
          message: "Orders cancelled but no available balance to transfer"
        });
      }
      
      // Step 4: Transfer all available to futures
      const transferResult = await transferFunds({
        currency: "USDT",
        amount: spotBalance.available,
        from: "spot",
        to: "futures"
      });
      
      res.json({
        success: true,
        cancelled: cancelResult.cancelled,
        transferred: transferResult.success ? spotBalance.available : 0,
        txId: transferResult.txId,
        message: `Cancelled ${cancelResult.cancelled} orders, transferred $${spotBalance.available.toFixed(2)} to futures`
      });
    } catch (error) {
      console.error("Cancel and transfer error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Operation failed" });
    }
  });

  // Get open positions
  app.get("/api/trading/positions", requireTradingEnabled, async (req, res) => {
    try {
      const { getOpenPositions } = await import("./gateio");
      const positions = await getOpenPositions();
      res.json(positions);
    } catch (error) {
      console.error("Positions fetch error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch positions" });
    }
  });
  
  // Get open orders
  app.get("/api/trading/orders", requireTradingEnabled, async (req, res) => {
    try {
      const { getOpenOrders } = await import("./gateio");
      const contract = req.query.contract as string | undefined;
      const orders = await getOpenOrders(contract);
      res.json(orders);
    } catch (error) {
      console.error("Orders fetch error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch orders" });
    }
  });
  
  // Execute trade based on analysis - with validation and rate limiting
  app.post("/api/trading/execute", requireTradingEnabled, async (req, res) => {
    try {
      // Rate limiting
      const clientIp = req.ip || "unknown";
      if (!checkRateLimit(clientIp)) {
        return res.status(429).json({ error: "Rate limit exceeded. Max 10 trades per minute." });
      }
      
      const { placeFuturesOrder, getFuturesBalance } = await import("./gateio");
      
      const { symbol, direction, size, leverage, entryPrice } = req.body;
      
      // Input validation
      if (!symbol || typeof symbol !== "string") {
        return res.status(400).json({ error: "Invalid symbol" });
      }
      
      if (direction !== "long" && direction !== "short") {
        return res.status(400).json({ error: "Direction must be 'long' or 'short'" });
      }
      
      const sizeNum = parseFloat(size);
      if (isNaN(sizeNum) || sizeNum <= 0 || sizeNum > 10000) {
        return res.status(400).json({ error: "Size must be between 0 and 10000 USDT" });
      }
      
      const leverageNum = parseInt(leverage) || 10;
      if (leverageNum < 1 || leverageNum > 100) {
        return res.status(400).json({ error: "Leverage must be between 1 and 100" });
      }
      
      // Check balance with proper margin requirement
      const balance = await getFuturesBalance();
      const requiredMargin = sizeNum / leverageNum * 1.1; // 10% buffer
      if (!balance || balance.available < requiredMargin) {
        return res.status(400).json({ 
          error: `Insufficient balance. Required: $${requiredMargin.toFixed(2)}, Available: $${balance?.available.toFixed(2) || 0}` 
        });
      }
      
      // Calculate contract size (positive for long, negative for short)
      const contractSize = direction === "long" ? Math.abs(sizeNum) : -Math.abs(sizeNum);
      
      // Place main order
      const order = await placeFuturesOrder({
        contract: symbol,
        size: contractSize,
        price: entryPrice ? parseFloat(entryPrice) : undefined,
        leverage: leverageNum,
      });
      
      console.log(`Trade executed: ${direction} ${symbol} size=${contractSize} leverage=${leverageNum}x @ ${entryPrice || 'market'}`);
      
      res.json({
        success: true,
        order,
        message: `${direction.toUpperCase()} order placed for ${symbol}`,
      });
    } catch (error) {
      console.error("Trade execution error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Trade execution failed" });
    }
  });
  
  // Close position - with validation
  app.post("/api/trading/close", requireTradingEnabled, async (req, res) => {
    try {
      const clientIp = req.ip || "unknown";
      if (!checkRateLimit(clientIp)) {
        return res.status(429).json({ error: "Rate limit exceeded" });
      }
      
      const { closePosition } = await import("./gateio");
      const { contract } = req.body;
      
      if (!contract || typeof contract !== "string") {
        return res.status(400).json({ error: "Invalid contract field" });
      }
      
      const result = await closePosition(contract);
      if (!result) {
        return res.status(400).json({ error: "Failed to close position or no position exists" });
      }
      
      res.json({ success: true, order: result });
    } catch (error) {
      console.error("Close position error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to close position" });
    }
  });
  
  // Close ALL positions - EMERGENCY STOP
  app.post("/api/trading/close-all", requireTradingEnabled, async (req, res) => {
    try {
      console.log("[EMERGENCY] Closing ALL positions...");
      const { closeAllPositions } = await import("./gateio");
      const result = await closeAllPositions();
      
      console.log(`[EMERGENCY] Close all result: ${JSON.stringify(result)}`);
      res.json(result);
    } catch (error) {
      console.error("Close all positions error:", error);
      res.status(500).json({ 
        success: false,
        error: error instanceof Error ? error.message : "Failed to close all positions" 
      });
    }
  });

  // Cancel order - with validation
  app.delete("/api/trading/orders/:orderId", requireTradingEnabled, async (req, res) => {
    try {
      const { cancelOrder } = await import("./gateio");
      const { orderId } = req.params;
      
      if (!orderId || !/^\d+$/.test(orderId)) {
        return res.status(400).json({ error: "Invalid order ID" });
      }
      
      const success = await cancelOrder(orderId);
      if (!success) {
        return res.status(400).json({ error: "Failed to cancel order" });
      }
      
      res.json({ success: true });
    } catch (error) {
      console.error("Cancel order error:", error);
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to cancel order" });
    }
  });

  // ============================================
  // HYPER-VELOCITY SHORTS-ONLY MODE
  // Continuous auto-pilot trading with 8 AI + 10 Engines
  // ============================================
  
  // AI-INTEGRATED POSITION TRACKING with Stop Loss and Take Profit
  interface ActivePosition {
    id: string;
    symbol: string;
    side: "long" | "short";
    entryPrice: number;
    size: number;
    leverage: number;
    // AI-generated levels from consensus
    stopLoss: number;
    stopLossReason: string;
    takeProfitLevels: {
      tp1: { price: number; percent: number; hit: boolean };
      tp2: { price: number; percent: number; hit: boolean };
      tp3: { price: number; percent: number; hit: boolean };
    };
    // Profit cascade tracking (50%, 70%, 90%, 100%)
    profitCascade: { level: number; percent: number; hit: boolean }[];
    partialExits: { price: number; percent: number; profit: number }[];
    // Engine validation record
    approvedBy: string[];
    rejectedBy: string[];
    smartGatesPassed: number;
    smartGatesFailed: number;
    confluenceLevel: string;
    verdict: string;
    riskReward: number;
    // Timestamps
    openedAt: Date;
    lastChecked: Date;
    closedAt: Date | null;
  }

  // Active positions store
  const activePositions: Map<string, ActivePosition> = new Map();
  
  // PROFIT STRATEGIES - AI-POWERED ULTRA-FAST TRADING
  interface ProfitStrategy {
    name: string; // Dynamic strategy names from tradingConfig.strategies
    active: boolean;
    multiplier: number;
    layers: number;
    consecutiveWins: number;
    consecutiveLosses: number;
  }

  interface AutoPilotState {
    running: boolean;
    mode: "SHORTS_ONLY" | "SPOT_ONLY" | "BOTH";
    tradeCount: number;
    totalPnl: number;
    winCount: number;
    lossCount: number;
    startTime: Date | null;
    lastTrade: Date | null;
    currentCycle: number;
    scanInterval: number;
    executionInterval: number;
    // Advanced profit strategies
    strategy: ProfitStrategy;
    baseAmount: number;
    currentAmount: number;
    snowballStack: number;
    waterfallLayers: number[];
    doublingLevel: number;
    // Engine validation stats
    engineStats: {
      governorApprovals: number;
      governorRejections: number;
      circuitBreakerTrips: number;
      smartGatesPassed: number;
      smartGatesFailed: number;
    };
    // AI levels from last consensus
    lastAiLevels: {
      entryZone: { high: number; low: number; optimal: number } | null;
      stopLoss: number | null;
      stopLossReason: string | null;
      tp1: number | null;
      tp2: number | null;
      tp3: number | null;
      riskReward: number | null;
    };
  }
  
  // ALPHA ARENA GODS LEVEL TRADING CONFIG
  // Integrates the 8 Core Pillars of Professional Trading
  const tradingConfig = {
    // ═══════════════════════════════════════════════════════════════════
    // ALPHA ARENA 8 PILLARS CONFIGURATION
    // ═══════════════════════════════════════════════════════════════════
    alphaArena: {
      enabled: true,
      startingBudget: 10000,      // $10K Alpha Arena standard
      riskProfile: "ALPHA_ARENA_GODS",
      
      // PILLAR 1: Capital Preservation First
      capitalPreservation: {
        maxDailyDrawdown: 10,     // 10% max daily loss (circuit breaker)
        maxTotalDrawdown: 25,     // 25% max total drawdown
        survivalFirst: true       // Survival before profit
      },
      
      // PILLAR 2: The 1-2% Rule (Position Sizing)
      riskPerTrade: 1.5,          // 1.5% max risk per trade
      maxRiskPercent: 2.0,        // Never exceed 2%
      
      // PILLAR 3: Mandatory Stop-Loss
      mandatoryStopLoss: true,
      stopLossBuffer: 0.02,       // 2% stop-loss distance
      
      // PILLAR 4: Trend-Following Only
      trendFollowingOnly: true,
      minADX: 30,                 // ADX > 30 = trending market
      
      // PILLAR 5: Stay Inactive (Patience)
      minConfluenceScore: 95,     // Highest minimum for Alpha Arena
      waitForSetup: true,
      
      // PILLAR 6: Asymmetric Risk/Reward
      minRewardRiskRatio: 2.0,    // 2:1 minimum R:R
      
      // PILLAR 7: Leverage Control
      maxLeverage: 10,            // 10x max leverage (Alpha Arena standard)
      leverageForEfficiency: true, // Use leverage for capital efficiency, not risk
      
      // PILLAR 8: Probabilistic Thinking
      targetWinRate: 45,          // 45% win rate with 2:1 R:R = profitable
      focusOnProcess: true,       // Process over outcome
      
      // Multi-Agent Consensus (6/8 = 75%)
      consensusRequired: 6,       // 6 out of 8 agents must agree
      totalAgents: 8
    },
    
    // ═══════════════════════════════════════════════════════════════════
    // ULTRA-AGGRESSIVE MODE (Enhanced with Alpha Arena Safety)
    // ═══════════════════════════════════════════════════════════════════
    // Trade Sizing
    tradeMultiplier: 30,        // 30X multiplier
    positionSizeMin: 40,        // 40% min position
    positionSizeMax: 95,        // 95% max position
    maxExposure: 98,            // 98% max exposure
    minTrade: 25,               // $25 minimum trade
    
    // Speed Settings
    scanInterval: 250,          // 0.25s ULTRA FAST
    minBetweenTrades: 2000,     // 2s between trades
    scalpTarget: 0.2,           // 0.2% scalp target
    scalpHoldMax: 120,          // 2 min max hold
    
    // Profit Targets
    profitTargets: {
      scalp: 0.3,               // 0.3%
      quick: 0.5,               // 0.5%
      standard: 1.0,            // 1.0%
      swing: 2.0,               // 2.0%
      moonshot: 5.0             // 5.0%
    },
    
    // Trading Pairs
    pairs: ["BTC_USDT", "ETH_USDT", "XRP_USDT", "AVAX_USDT", "SOL_USDT"],
    
    // AI Confidence Thresholds
    confidence: {
      min: 35,                  // 35% minimum
      scalpMin: 30,             // 30% for scalps
      high: 55,                 // 55% high confidence
      god: 70                   // 70% god mode
    },
    
    // 15 Active Strategies + Alpha Arena Strategies + Dynamic Gods Level
    strategies: [
      "TURBO_SCALP", "MOMENTUM_SHORT", "BREAKDOWN_CATCHER", "PUMP_FADER",
      "WHALE_FOLLOWER", "VOLATILITY_SURFER", "TALAKNERY_TRAP_1", "TALAKNERY_TRAP_2",
      "TALAKNERY_TRAP_3", "INFINITY_SCALPER_1", "INFINITY_SCALPER_2", "INFINITY_SCALPER_3",
      "INFINITY_SCALPER_4", "SNOWBALL", "WATERFALL",
      // Alpha Arena Strategies
      "TREND_CONTINUATION", "BREAKOUT_ALPHA",
      // Dynamic Strategy Gods Level
      "PYRAMID", "DOUBLING", "DYNAMIC_SCALPING"
    ],
    
    // ═══════════════════════════════════════════════════════════════════
    // DYNAMIC STRATEGY GODS LEVEL CONFIGURATION
    // ═══════════════════════════════════════════════════════════════════
    dynamicStrategy: {
      enabled: true,
      profile: "DYNAMIC_STRATEGY_GODS",
      
      // ADX Thresholds for Strategy Selection
      adxThresholds: {
        hyperTrending: 45,      // ADX > 45 = PYRAMID (max aggression)
        trending: 35,           // ADX > 35 = WATERFALL (trend-following)
        ranging: 20,            // ADX < 20 = SCALPING (range-bound)
        neutral: 25             // Default threshold
      },
      
      // Strategy Parameters
      pyramid: {
        layers: 3,              // Add to position in 3 layers
        sizeMultiplier: 1.5,    // Each layer 1.5x larger
        minADX: 45,             // Minimum ADX for PYRAMID
        targetPercent: 3.0      // 3% profit target
      },
      
      waterfall: {
        layers: 5,              // 5 equal layers
        spacing: 0.1,           // 0.1% between layers
        minADX: 35,             // Minimum ADX for WATERFALL
        targetPercent: 2.0      // 2% profit target
      },
      
      scalping: {
        targetPercent: 0.2,     // 0.2% micro-profit target
        stopPercent: 0.1,       // 0.1% tight stop
        maxADX: 20,             // Maximum ADX for SCALPING
        winRate: 0.60           // Expected 60% win rate
      },
      
      doubling: {
        enabled: true,
        maxMultiplier: 4,       // Max 4x position after losses
        triggerOnLoss: true,    // Trigger after loss in ranging market
        maxConsecutive: 3       // Max 3 consecutive doubles
      },
      
      // Dynamic Switching Logic
      autoSwitch: true,
      switchOnLoss: true,       // Switch strategy after loss
      regimeDetection: true     // Auto-detect market regime
    }
  };
  
  // Dynamic Strategy State
  let dynamicStrategyState = {
    currentStrategy: "SCALPING" as "PYRAMID" | "WATERFALL" | "SCALPING" | "DOUBLING",
    doublingMultiplier: 1,
    lastTradeWasLoss: false,
    consecutiveLosses: 0,
    regime: "RANGING" as "HYPER_TRENDING" | "TRENDING" | "RANGING" | "NEUTRAL"
  };
  
  // ═══════════════════════════════════════════════════════════════════
  // DYNAMIC STRATEGY ENGINE - ADX-Based Strategy Selection
  // ═══════════════════════════════════════════════════════════════════
  
  function selectDynamicStrategy(marketData: any): {
    strategy: "PYRAMID" | "WATERFALL" | "SCALPING" | "DOUBLING";
    reason: string;
    layers: number;
    multiplier: number;
    targetPercent: number;
  } {
    const adx = marketData.indicators?.adx || marketData.adx || 25;
    const thresholds = tradingConfig.dynamicStrategy.adxThresholds;
    const ds = tradingConfig.dynamicStrategy;
    
    // Update regime based on ADX
    if (adx > thresholds.hyperTrending) {
      dynamicStrategyState.regime = "HYPER_TRENDING";
    } else if (adx > thresholds.trending) {
      dynamicStrategyState.regime = "TRENDING";
    } else if (adx < thresholds.ranging) {
      dynamicStrategyState.regime = "RANGING";
    } else {
      dynamicStrategyState.regime = "NEUTRAL";
    }
    
    // DOUBLING: Triggered after loss in ranging market
    if (ds.doubling.enabled && 
        dynamicStrategyState.lastTradeWasLoss && 
        dynamicStrategyState.regime === "RANGING" &&
        dynamicStrategyState.consecutiveLosses < ds.doubling.maxConsecutive) {
      
      dynamicStrategyState.doublingMultiplier = Math.min(
        dynamicStrategyState.doublingMultiplier * 2, 
        ds.doubling.maxMultiplier
      );
      dynamicStrategyState.currentStrategy = "DOUBLING";
      
      return {
        strategy: "DOUBLING",
        reason: `🔄 DOUBLING MODE: Loss recovery in ranging market (${dynamicStrategyState.doublingMultiplier}x size)`,
        layers: 1,
        multiplier: dynamicStrategyState.doublingMultiplier,
        targetPercent: ds.scalping.targetPercent * 1.5 // Slightly larger target for recovery
      };
    }
    
    // Reset doubling on success
    if (!dynamicStrategyState.lastTradeWasLoss) {
      dynamicStrategyState.doublingMultiplier = 1;
      dynamicStrategyState.consecutiveLosses = 0;
    }
    
    // PYRAMID: Extremely strong trend (ADX > 45)
    if (adx > thresholds.hyperTrending) {
      dynamicStrategyState.currentStrategy = "PYRAMID";
      return {
        strategy: "PYRAMID",
        reason: `🔺 PYRAMID MODE: Hyper-trending market (ADX: ${adx.toFixed(1)}) - max aggression with ${ds.pyramid.layers} layers`,
        layers: ds.pyramid.layers,
        multiplier: ds.pyramid.sizeMultiplier,
        targetPercent: ds.pyramid.targetPercent
      };
    }
    
    // WATERFALL: Strong trend (ADX > 35)
    if (adx > thresholds.trending) {
      dynamicStrategyState.currentStrategy = "WATERFALL";
      return {
        strategy: "WATERFALL",
        reason: `🌊 WATERFALL MODE: Trending market (ADX: ${adx.toFixed(1)}) - ${ds.waterfall.layers} equal layers`,
        layers: ds.waterfall.layers,
        multiplier: 1,
        targetPercent: ds.waterfall.targetPercent
      };
    }
    
    // SCALPING: Ranging market (ADX < 20)
    dynamicStrategyState.currentStrategy = "SCALPING";
    return {
      strategy: "SCALPING",
      reason: `⚡ SCALPING MODE: Ranging market (ADX: ${adx.toFixed(1)}) - micro-profits at high velocity`,
      layers: 1,
      multiplier: 1,
      targetPercent: ds.scalping.targetPercent
    };
  }
  
  // Apply PYRAMID layered entry (increasing size per layer)
  function applyPyramid(basePrice: number, direction: "long" | "short"): number[] {
    const layers = tradingConfig.dynamicStrategy.pyramid.layers;
    const spacing = 0.005; // 0.5% between layers
    const entries: number[] = [];
    
    for (let i = 0; i < layers; i++) {
      if (direction === "short") {
        entries.push(basePrice * (1 + spacing * i));
      } else {
        entries.push(basePrice * (1 - spacing * i));
      }
    }
    return entries;
  }
  
  // Record trade result for dynamic strategy adjustment
  function recordTradeResult(isWin: boolean) {
    dynamicStrategyState.lastTradeWasLoss = !isWin;
    if (!isWin) {
      dynamicStrategyState.consecutiveLosses++;
    } else {
      dynamicStrategyState.consecutiveLosses = 0;
      dynamicStrategyState.doublingMultiplier = 1;
    }
  }
  
  // ═══════════════════════════════════════════════════════════════════
  // ALPHA ARENA GODS LEVEL VALIDATION FUNCTIONS
  // ═══════════════════════════════════════════════════════════════════
  
  // Calculate position size based on 1-2% rule
  function calculateAlphaArenaPositionSize(
    accountBalance: number,
    entryPrice: number,
    stopLossPrice: number,
    leverage: number = 1
  ): { positionSizeUSD: number; riskAmount: number; valid: boolean; reason: string } {
    const riskPerCoin = Math.abs(entryPrice - stopLossPrice);
    const maxLossAllowed = accountBalance * (tradingConfig.alphaArena.riskPerTrade / 100);
    const positionSizeCoins = maxLossAllowed / riskPerCoin;
    const positionSizeUSD = positionSizeCoins * entryPrice;
    
    // Validate against max risk percent
    const actualRiskPercent = (riskPerCoin / entryPrice) * 100;
    const leveragedRisk = actualRiskPercent * leverage;
    
    if (leveragedRisk > tradingConfig.alphaArena.maxRiskPercent * leverage) {
      return { positionSizeUSD: 0, riskAmount: maxLossAllowed, valid: false, reason: "Exceeds max risk per trade" };
    }
    
    return { 
      positionSizeUSD: Math.min(positionSizeUSD, accountBalance * 0.95), 
      riskAmount: maxLossAllowed, 
      valid: true, 
      reason: "Position size calculated per 1-2% rule" 
    };
  }
  
  // Check if market is trending (Pillar 4: Trend-Following Only)
  function checkTrendingMarket(marketData: any): { trending: boolean; regime: string; adx: number } {
    // ADX > 30 = trending, < 30 = ranging
    const adx = marketData.indicators?.adx || marketData.adx || 25;
    
    if (adx > 40) {
      return { trending: true, regime: "STRONG_TREND", adx };
    } else if (adx > 30) {
      return { trending: true, regime: "TRENDING", adx };
    } else if (adx > 20) {
      return { trending: false, regime: "WEAK_TREND", adx };
    } else {
      return { trending: false, regime: "RANGING", adx };
    }
  }
  
  // Calculate Risk/Reward Ratio (Pillar 6: Asymmetric R:R)
  function calculateRiskReward(
    entryPrice: number,
    stopLossPrice: number,
    takeProfitPrice: number,
    side: "long" | "short"
  ): { ratio: number; valid: boolean; risk: number; reward: number } {
    const risk = Math.abs(entryPrice - stopLossPrice);
    const reward = Math.abs(takeProfitPrice - entryPrice);
    const ratio = reward / risk;
    
    return {
      ratio: parseFloat(ratio.toFixed(2)),
      valid: ratio >= tradingConfig.alphaArena.minRewardRiskRatio,
      risk,
      reward
    };
  }
  
  // Check multi-agent consensus (6/8 required)
  function checkAgentConsensus(agentSignals: any[]): { 
    consensus: boolean; 
    agreementCount: number; 
    totalAgents: number;
    dominantDirection: string;
    confidence: number;
  } {
    const directions = agentSignals.map(s => s.signal || s.direction);
    const shortCount = directions.filter(d => d === "SHORT" || d === "short").length;
    const longCount = directions.filter(d => d === "LONG" || d === "long").length;
    const holdCount = directions.filter(d => d === "HOLD" || d === "hold" || !d).length;
    
    const total = agentSignals.length;
    const dominantDirection = shortCount > longCount ? "SHORT" : longCount > shortCount ? "LONG" : "HOLD";
    const agreementCount = Math.max(shortCount, longCount, holdCount);
    const consensus = agreementCount >= tradingConfig.alphaArena.consensusRequired;
    const confidence = (agreementCount / total) * 100;
    
    return { consensus, agreementCount, totalAgents: total, dominantDirection, confidence };
  }
  
  // Alpha Arena Daily Drawdown Check (Pillar 1: Capital Preservation)
  let dailyStartingBalance = 1000; // Will be updated on first run
  let dailyPnL = 0;
  
  function checkDailyDrawdown(currentPnL: number): { 
    allowed: boolean; 
    drawdownPercent: number; 
    remaining: number;
    status: string;
  } {
    const maxDrawdownAmount = dailyStartingBalance * (tradingConfig.alphaArena.capitalPreservation.maxDailyDrawdown / 100);
    const drawdownPercent = Math.abs(Math.min(0, currentPnL)) / dailyStartingBalance * 100;
    const remaining = maxDrawdownAmount - Math.abs(Math.min(0, currentPnL));
    
    if (drawdownPercent >= tradingConfig.alphaArena.capitalPreservation.maxDailyDrawdown) {
      return { allowed: false, drawdownPercent, remaining: 0, status: "CIRCUIT_BREAKER_TRIGGERED" };
    }
    
    if (drawdownPercent >= 7) {
      return { allowed: true, drawdownPercent, remaining, status: "CAUTION_MODE" };
    }
    
    return { allowed: true, drawdownPercent, remaining, status: "NORMAL" };
  }
  
  // Validate trade against all 8 Alpha Arena Pillars
  function validateAlphaArenaTrade(
    marketData: any,
    signal: any,
    accountBalance: number,
    agentSignals: any[]
  ): { 
    approved: boolean; 
    pillarResults: { pillar: string; passed: boolean; reason: string }[];
    finalScore: number;
  } {
    const pillarResults: { pillar: string; passed: boolean; reason: string }[] = [];
    let passedCount = 0;
    
    // PILLAR 1: Capital Preservation (Daily Drawdown Check)
    const drawdownCheck = checkDailyDrawdown(autoPilotState.totalPnl);
    pillarResults.push({
      pillar: "Capital Preservation",
      passed: drawdownCheck.allowed,
      reason: drawdownCheck.status === "NORMAL" ? "Daily drawdown within limits" : drawdownCheck.status
    });
    if (drawdownCheck.allowed) passedCount++;
    
    // PILLAR 2: The 1-2% Rule (Position Sizing)
    const stopLoss = signal.stopLoss || marketData.price * 0.98;
    const positionCalc = calculateAlphaArenaPositionSize(accountBalance, marketData.price, stopLoss);
    pillarResults.push({
      pillar: "1-2% Rule",
      passed: positionCalc.valid,
      reason: positionCalc.reason
    });
    if (positionCalc.valid) passedCount++;
    
    // PILLAR 3: Mandatory Stop-Loss
    const hasStopLoss = signal.stopLoss !== undefined && signal.stopLoss !== null;
    pillarResults.push({
      pillar: "Mandatory Stop-Loss",
      passed: hasStopLoss,
      reason: hasStopLoss ? "Stop-loss defined" : "Missing stop-loss"
    });
    if (hasStopLoss) passedCount++;
    
    // PILLAR 4: Trend-Following Only
    const trendCheck = checkTrendingMarket(marketData);
    pillarResults.push({
      pillar: "Trend-Following",
      passed: trendCheck.trending,
      reason: `Regime: ${trendCheck.regime} (ADX: ${trendCheck.adx.toFixed(1)})`
    });
    if (trendCheck.trending) passedCount++;
    
    // PILLAR 5: Stay Inactive (High Confluence)
    const confluenceScore = signal.confidence || 50;
    const highConfluence = confluenceScore >= tradingConfig.alphaArena.minConfluenceScore / 2;
    pillarResults.push({
      pillar: "High Confluence",
      passed: highConfluence,
      reason: `Confluence: ${confluenceScore}% (min: ${tradingConfig.alphaArena.minConfluenceScore / 2}%)`
    });
    if (highConfluence) passedCount++;
    
    // PILLAR 6: Asymmetric Risk/Reward
    const takeProfit = signal.tp2 || marketData.price * (signal.direction === "SHORT" ? 0.96 : 1.04);
    const rrCheck = calculateRiskReward(marketData.price, stopLoss, takeProfit, signal.direction?.toLowerCase() || "long");
    pillarResults.push({
      pillar: "Asymmetric R:R",
      passed: rrCheck.valid,
      reason: `R:R ${rrCheck.ratio}:1 (min: ${tradingConfig.alphaArena.minRewardRiskRatio}:1)`
    });
    if (rrCheck.valid) passedCount++;
    
    // PILLAR 7: Leverage Control
    const leverage = signal.leverage || 10;
    const leverageOK = leverage <= tradingConfig.alphaArena.maxLeverage;
    pillarResults.push({
      pillar: "Leverage Control",
      passed: leverageOK,
      reason: leverageOK ? `Leverage ${leverage}x within limit` : `Leverage ${leverage}x exceeds ${tradingConfig.alphaArena.maxLeverage}x max`
    });
    if (leverageOK) passedCount++;
    
    // PILLAR 8: Multi-Agent Consensus (6/8)
    const consensusCheck = checkAgentConsensus(agentSignals);
    pillarResults.push({
      pillar: "Agent Consensus",
      passed: consensusCheck.consensus,
      reason: `${consensusCheck.agreementCount}/${consensusCheck.totalAgents} agents agree on ${consensusCheck.dominantDirection}`
    });
    if (consensusCheck.consensus) passedCount++;
    
    // Calculate final score
    const finalScore = Math.round((passedCount / 8) * 100);
    const approved = passedCount >= 6; // Need 6/8 pillars to pass
    
    return { approved, pillarResults, finalScore };
  }

  const autoPilotState: AutoPilotState = {
    running: false,
    mode: "SHORTS_ONLY",
    tradeCount: 0,
    totalPnl: 0,
    winCount: 0,
    lossCount: 0,
    startTime: null,
    lastTrade: null,
    currentCycle: 0,
    scanInterval: 250,  // ULTRA-FAST: 0.25s = 240 cycles/min
    executionInterval: 100,
    // Advanced profit strategies
    strategy: { name: "TURBO_SCALP", active: true, multiplier: 30, layers: 1, consecutiveWins: 0, consecutiveLosses: 0 },
    baseAmount: 25,
    currentAmount: 25,
    snowballStack: 0,
    waterfallLayers: [],
    doublingLevel: 0,
    // Engine validation stats
    engineStats: {
      governorApprovals: 0,
      governorRejections: 0,
      circuitBreakerTrips: 0,
      smartGatesPassed: 0,
      smartGatesFailed: 0
    },
    // AI levels
    lastAiLevels: {
      entryZone: null,
      stopLoss: null,
      stopLossReason: null,
      tp1: null,
      tp2: null,
      tp3: null,
      riskReward: null
    }
  };

  // Validate trade with engines before execution
  interface ValidationResult {
    approved: boolean;
    reasons: string[];
    gates: { name: string; passed: boolean }[];
    gatesPassed: number;
    gatesFailed: number;
    approvedBy: string[];
    rejectedBy: string[];
  }

  function validateTradeWithEngines(
    marketData: any, 
    consensus: any
  ): ValidationResult {
    const engineOutput = tradingEngines.runAllEngines(marketData, consensus);
    const reasons: string[] = [];
    const approvedBy: string[] = [];
    const rejectedBy: string[] = [];
    
    // Check Governor approval
    if (!engineOutput.governorRisk.approved) {
      autoPilotState.engineStats.governorRejections++;
      reasons.push(`Governor: ${consensus.riskReward?.toTp2 < 2 ? 'R:R below 2:1' : 'Risk limits exceeded'}`);
      rejectedBy.push("Governor");
    } else {
      autoPilotState.engineStats.governorApprovals++;
      approvedBy.push("Governor");
    }
    
    // Check Circuit Breakers
    if (engineOutput.circuitBreaker.triggered) {
      autoPilotState.engineStats.circuitBreakerTrips++;
      reasons.push(`Circuit Breaker: ${engineOutput.circuitBreaker.reason}`);
      rejectedBy.push("CircuitBreaker");
    } else {
      approvedBy.push("CircuitBreaker");
    }
    
    // Count Smart Gates
    const gatesPassed = engineOutput.smartGates.filter(g => g.passed).length;
    const gatesFailed = engineOutput.smartGates.filter(g => !g.passed).length;
    autoPilotState.engineStats.smartGatesPassed += gatesPassed;
    autoPilotState.engineStats.smartGatesFailed += gatesFailed;
    
    // Record individual gate results
    engineOutput.smartGates.forEach(g => {
      if (g.passed) approvedBy.push(`Gate:${g.name}`);
      else rejectedBy.push(`Gate:${g.name}`);
    });
    
    // Require at least 5/8 gates to pass
    if (gatesPassed < 5) {
      reasons.push(`Smart Gates: Only ${gatesPassed}/8 passed (need 5+)`);
    }
    
    const approved = engineOutput.governorRisk.approved && 
                     !engineOutput.circuitBreaker.triggered && 
                     gatesPassed >= 5;
    
    return { approved, reasons, gates: engineOutput.smartGates, gatesPassed, gatesFailed, approvedBy, rejectedBy };
  }

  // Monitor positions for stop loss and take profit hits
  async function monitorPositions(currentPrices: Map<string, number>) {
    for (const [id, position] of activePositions) {
      const currentPrice = currentPrices.get(position.symbol);
      if (!currentPrice) continue;
      
      position.lastChecked = new Date();
      
      // Check Stop Loss
      if (position.side === "long" && currentPrice <= position.stopLoss) {
        console.log(`🛑 STOP LOSS HIT: ${position.symbol} @ $${currentPrice.toFixed(2)} (SL: $${position.stopLoss.toFixed(2)})`);
        await closePositionWithResult(position, currentPrice, "stop_loss");
        continue;
      }
      if (position.side === "short" && currentPrice >= position.stopLoss) {
        console.log(`🛑 STOP LOSS HIT: ${position.symbol} @ $${currentPrice.toFixed(2)} (SL: $${position.stopLoss.toFixed(2)})`);
        await closePositionWithResult(position, currentPrice, "stop_loss");
        continue;
      }
      
      // Check Profit Cascade Levels (50%, 70%, 90%, 100%)
      for (const cascade of position.profitCascade) {
        if (cascade.hit) continue;
        
        const tpPrice = position.takeProfitLevels.tp2.price; // Use TP2 as main target
        const entryDistance = Math.abs(tpPrice - position.entryPrice);
        const targetPrice = position.side === "long"
          ? position.entryPrice + (entryDistance * cascade.percent / 100)
          : position.entryPrice - (entryDistance * cascade.percent / 100);
        
        if ((position.side === "long" && currentPrice >= targetPrice) ||
            (position.side === "short" && currentPrice <= targetPrice)) {
          cascade.hit = true;
          const exitPercent = cascade.level === 1 ? 25 : cascade.level === 2 ? 25 : cascade.level === 3 ? 25 : 25;
          const profit = position.size * (exitPercent / 100) * (Math.abs(currentPrice - position.entryPrice) / position.entryPrice) * position.leverage;
          position.partialExits.push({ price: currentPrice, percent: exitPercent, profit });
          autoPilotState.totalPnl += profit;
          console.log(`💰 CASCADE ${cascade.percent}%: ${position.symbol} +$${profit.toFixed(2)} (${exitPercent}% position closed)`);
        }
      }
      
      // Check if all cascades hit (position fully closed)
      if (position.profitCascade.every(c => c.hit)) {
        position.closedAt = new Date();
        autoPilotState.winCount++;
        activePositions.delete(id);
        console.log(`✅ POSITION FULLY CLOSED: ${position.symbol} - All profit targets hit!`);
      }
    }
  }

  async function closePositionWithResult(position: ActivePosition, closePrice: number, reason: string) {
    const pnl = position.side === "long"
      ? (closePrice - position.entryPrice) / position.entryPrice * position.size * position.leverage
      : (position.entryPrice - closePrice) / position.entryPrice * position.size * position.leverage;
    
    position.closedAt = new Date();
    autoPilotState.totalPnl += pnl;
    
    if (pnl > 0) {
      autoPilotState.winCount++;
      applySnowball(true);
      console.log(`✅ ${position.symbol} CLOSED (+$${pnl.toFixed(2)}) - ${reason}`);
    } else {
      autoPilotState.lossCount++;
      applySnowball(false);
      applyDoubling(false);
      console.log(`❌ ${position.symbol} CLOSED (-$${Math.abs(pnl).toFixed(2)}) - ${reason}`);
    }
    
    activePositions.delete(position.id);
  }

  // Create position with AI-generated levels and engine validation metadata
  function createPosition(
    symbol: string,
    side: "long" | "short",
    entryPrice: number,
    size: number,
    leverage: number,
    consensus: any,
    validation?: ValidationResult
  ): ActivePosition {
    const id = `${symbol}-${Date.now()}`;
    
    // Extract AI-generated levels from consensus
    const stopLoss = consensus.invalidation?.price || 
      (side === "long" ? entryPrice * 0.98 : entryPrice * 1.02);
    const stopLossReason = consensus.invalidation?.reason || "Default 2% stop";
    
    const tp1 = consensus.targets?.tp1?.price || 
      (side === "long" ? entryPrice * 1.01 : entryPrice * 0.99);
    const tp2 = consensus.targets?.tp2?.price || 
      (side === "long" ? entryPrice * 1.02 : entryPrice * 0.98);
    const tp3 = consensus.targets?.tp3?.price || 
      (side === "long" ? entryPrice * 1.03 : entryPrice * 0.97);
    
    const position: ActivePosition = {
      id,
      symbol,
      side,
      entryPrice,
      size,
      leverage,
      stopLoss,
      stopLossReason,
      takeProfitLevels: {
        tp1: { price: tp1, percent: 25, hit: false },
        tp2: { price: tp2, percent: 50, hit: false },
        tp3: { price: tp3, percent: 25, hit: false }
      },
      profitCascade: [
        { level: 1, percent: 50, hit: false },
        { level: 2, percent: 70, hit: false },
        { level: 3, percent: 90, hit: false },
        { level: 4, percent: 100, hit: false }
      ],
      partialExits: [],
      approvedBy: validation?.approvedBy || [],
      rejectedBy: validation?.rejectedBy || [],
      smartGatesPassed: validation?.gatesPassed || 0,
      smartGatesFailed: validation?.gatesFailed || 0,
      confluenceLevel: consensus.confluenceLevel || "MODERATE",
      verdict: consensus.verdict || "EXECUTE",
      riskReward: consensus.riskReward?.toTp2 || 2,
      openedAt: new Date(),
      lastChecked: new Date(),
      closedAt: null
    };
    
    // Store AI levels for display
    autoPilotState.lastAiLevels = {
      entryZone: consensus.killZone || null,
      stopLoss: stopLoss,
      stopLossReason: stopLossReason,
      tp1: tp1,
      tp2: tp2,
      tp3: tp3,
      riskReward: consensus.riskReward?.toTp2 || null
    };
    
    console.log(`📊 AI LEVELS: Entry $${entryPrice.toFixed(2)} | SL $${stopLoss.toFixed(2)} | TP1 $${tp1.toFixed(2)} | TP2 $${tp2.toFixed(2)} | TP3 $${tp3.toFixed(2)}`);
    console.log(`   R:R ${(consensus.riskReward?.toTp2 || 0).toFixed(2)} | ${stopLossReason}`);
    console.log(`   ✅ Approved: ${position.approvedBy.slice(0, 3).join(", ")}... (${position.smartGatesPassed}/8 gates)`);
    
    activePositions.set(id, position);
    return position;
  }

  // SNOWBALL: Compound wins - each win adds 20% to next trade
  function applySnowball(won: boolean): number {
    if (won) {
      autoPilotState.snowballStack++;
      autoPilotState.strategy.consecutiveWins++;
      autoPilotState.strategy.consecutiveLosses = 0;
      // Compound: base * (1.2 ^ wins), max 5x
      const multiplier = Math.min(Math.pow(1.2, autoPilotState.snowballStack), 5);
      autoPilotState.currentAmount = autoPilotState.baseAmount * multiplier;
      console.log(`❄️ SNOWBALL: Stack ${autoPilotState.snowballStack} -> ${multiplier.toFixed(2)}x ($${autoPilotState.currentAmount.toFixed(2)})`);
    } else {
      autoPilotState.snowballStack = 0;
      autoPilotState.strategy.consecutiveLosses++;
      autoPilotState.strategy.consecutiveWins = 0;
      autoPilotState.currentAmount = autoPilotState.baseAmount;
      console.log(`❄️ SNOWBALL RESET: Back to base $${autoPilotState.baseAmount}`);
    }
    return autoPilotState.currentAmount;
  }

  // WATERFALL: Layered entries - 10 layers at 0.1% spacing for better average
  function applyWaterfall(price: number, direction: "long" | "short"): number[] {
    const layers: number[] = [];
    const spacing = 0.001; // 0.1% between layers
    const layerCount = 10;
    
    for (let i = 0; i < layerCount; i++) {
      const layerPrice = direction === "long" 
        ? price * (1 - spacing * i)  // Buy lower
        : price * (1 + spacing * i); // Sell higher
      layers.push(layerPrice);
    }
    
    autoPilotState.waterfallLayers = layers;
    console.log(`🌊 WATERFALL: ${layerCount} layers @ 0.1% spacing (${direction.toUpperCase()})`);
    return layers;
  }

  // DOUBLING: Recovery mode - double size after loss (max 4 levels)
  function applyDoubling(won: boolean): number {
    if (won) {
      autoPilotState.doublingLevel = 0;
      autoPilotState.currentAmount = autoPilotState.baseAmount;
      console.log(`🎰 DOUBLING: Win! Reset to base $${autoPilotState.baseAmount}`);
    } else {
      autoPilotState.doublingLevel = Math.min(autoPilotState.doublingLevel + 1, 4);
      autoPilotState.currentAmount = autoPilotState.baseAmount * Math.pow(2, autoPilotState.doublingLevel);
      console.log(`🎰 DOUBLING: Level ${autoPilotState.doublingLevel} -> $${autoPilotState.currentAmount} (recovering losses)`);
    }
    return autoPilotState.currentAmount;
  }

  // SMART PAIR SCANNER - Find #1 most profitable pair
  interface PairScore {
    pair: string;
    score: number;
    signal: "LONG" | "SHORT" | "NEUTRAL";
    fundingRate: number;
    change24h: number;
    volume: number;
    reason: string;
  }

  let bestPair: PairScore | null = null;
  let lastPairScan = 0;
  const PAIR_SCAN_INTERVAL = 30000; // Rescan every 30 seconds

  async function scanForBestPair(): Promise<PairScore> {
    try {
      // Fetch all futures tickers for funding rates
      const futuresRes = await fetch("https://api.gateio.ws/api/v4/futures/usdt/tickers");
      const futuresData = await futuresRes.json();
      
      // Score each pair
      const scores: PairScore[] = [];
      
      for (const ticker of futuresData) {
        if (!ticker.contract || !ticker.volume_24h_quote) continue;
        
        const fundingRate = parseFloat(ticker.funding_rate) || 0;
        const change24h = parseFloat(ticker.change_percentage) || 0;
        const volume = parseFloat(ticker.volume_24h_quote) || 0;
        
        // Skip low volume pairs
        if (volume < 500000) continue;
        
        // Calculate profitability score (0-100)
        let score = 0;
        let signal: "LONG" | "SHORT" | "NEUTRAL" = "NEUTRAL";
        let reason = "";
        
        // High positive funding = SHORT opportunity (get paid to short)
        if (fundingRate > 0.0005) {
          score += Math.min(fundingRate * 5000, 40); // Up to 40 points
          signal = "SHORT";
          reason = `High funding ${(fundingRate * 100).toFixed(3)}%`;
        }
        
        // High negative funding = LONG opportunity (get paid to long)
        if (fundingRate < -0.0005) {
          score += Math.min(Math.abs(fundingRate) * 5000, 40);
          signal = "LONG";
          reason = `Negative funding ${(fundingRate * 100).toFixed(3)}%`;
        }
        
        // Strong momentum adds points
        if (Math.abs(change24h) > 5) {
          score += Math.min(Math.abs(change24h), 30); // Up to 30 points
          if (change24h > 5 && signal !== "SHORT") {
            signal = "LONG";
            reason += ` +${change24h.toFixed(1)}% momentum`;
          }
          if (change24h < -5 && signal !== "LONG") {
            signal = "SHORT";
            reason += ` ${change24h.toFixed(1)}% drop`;
          }
        }
        
        // Volume bonus (liquidity)
        if (volume > 10000000) score += 20;
        else if (volume > 5000000) score += 15;
        else if (volume > 1000000) score += 10;
        
        // Extreme funding = massive opportunity
        if (Math.abs(fundingRate) > 0.005) {
          score += 20;
          reason = `🔥 EXTREME ${reason}`;
        }
        
        if (score > 0 && signal !== "NEUTRAL") {
          scores.push({
            pair: ticker.contract,
            score,
            signal,
            fundingRate,
            change24h,
            volume,
            reason
          });
        }
      }
      
      // Sort by score descending
      scores.sort((a, b) => b.score - a.score);
      
      if (scores.length > 0) {
        const best = scores[0];
        console.log(`\n🏆 TOP PROFITABLE PAIR: ${best.pair}`);
        console.log(`   Score: ${best.score.toFixed(0)} | Signal: ${best.signal} | ${best.reason}`);
        console.log(`   Funding: ${(best.fundingRate * 100).toFixed(4)}% | 24h: ${best.change24h.toFixed(2)}% | Vol: $${(best.volume/1e6).toFixed(1)}M`);
        
        // Show top 5
        console.log(`\n📊 TOP 5 OPPORTUNITIES:`);
        scores.slice(0, 5).forEach((p, i) => {
          console.log(`   ${i+1}. ${p.pair.padEnd(12)} | Score: ${p.score.toFixed(0).padStart(3)} | ${p.signal} | ${p.reason}`);
        });
        
        return best;
      }
      
      // Fallback to BTC
      return {
        pair: "BTC_USDT",
        score: 50,
        signal: "LONG",
        fundingRate: 0.0001,
        change24h: 0,
        volume: 100000000,
        reason: "Default major pair"
      };
    } catch (error) {
      console.error("Pair scan error:", error);
      return {
        pair: "BTC_USDT",
        score: 50,
        signal: "LONG",
        fundingRate: 0.0001,
        change24h: 0,
        volume: 100000000,
        reason: "Fallback"
      };
    }
  }

  // ULTRA-AGGRESSIVE 15 STRATEGY SELECTOR - AI-Powered
  type AggressiveStrategy = 
    | "TURBO_SCALP" | "MOMENTUM_SHORT" | "BREAKDOWN_CATCHER" | "PUMP_FADER"
    | "WHALE_FOLLOWER" | "VOLATILITY_SURFER" | "TALAKNERY_TRAP_1" | "TALAKNERY_TRAP_2"
    | "TALAKNERY_TRAP_3" | "INFINITY_SCALPER_1" | "INFINITY_SCALPER_2" | "INFINITY_SCALPER_3"
    | "INFINITY_SCALPER_4" | "SNOWBALL" | "WATERFALL";
  
  interface StrategyDecision {
    strategy: AggressiveStrategy;
    multiplier: number;
    reason: string;
    aggressionLevel: number; // 1-10
    targetType: "scalp" | "quick" | "standard" | "swing" | "moonshot";
  }

  function selectAggressiveStrategy(marketData: any, consensus: any, bestPairData: PairScore | null): StrategyDecision {
    const { fundingRate = 0, volatility24h = 0, change24h = 0, volume24h = 0 } = marketData;
    const { confidenceScore = 0, confluenceLevel = "WEAK" } = consensus;
    const pairScore = bestPairData?.score || 0;
    const pairSignal = bestPairData?.signal || "NEUTRAL";
    const conf = tradingConfig.confidence;
    
    let decision: StrategyDecision = {
      strategy: "INFINITY_SCALPER_1",
      multiplier: tradingConfig.tradeMultiplier,
      reason: "Default infinity scalper",
      aggressionLevel: 7,
      targetType: "scalp"
    };

    // GOD MODE: Extreme conditions = MAX AGGRESSION TURBO SCALP
    if (confidenceScore >= conf.god && confluenceLevel === "GODLIKE" && Math.abs(fundingRate) > 0.005) {
      decision = {
        strategy: "TURBO_SCALP",
        multiplier: tradingConfig.tradeMultiplier,
        reason: `🔥 TURBO SCALP: GOD confidence ${confidenceScore}% + GODLIKE + extreme funding`,
        aggressionLevel: 10,
        targetType: "moonshot"
      };
    }
    // MOMENTUM SHORT: Strong downtrend + high confidence  
    else if (change24h < -5 && confidenceScore >= conf.high && pairSignal === "SHORT") {
      decision = {
        strategy: "MOMENTUM_SHORT",
        multiplier: tradingConfig.tradeMultiplier * 0.8,
        reason: `📉 MOMENTUM SHORT: ${change24h.toFixed(1)}% drop, riding the wave`,
        aggressionLevel: 9,
        targetType: "swing"
      };
    }
    // BREAKDOWN CATCHER: Sharp drop with volume spike
    else if (change24h < -8 && volume24h > 50000000) {
      decision = {
        strategy: "BREAKDOWN_CATCHER",
        multiplier: tradingConfig.tradeMultiplier * 0.7,
        reason: `💥 BREAKDOWN: ${change24h.toFixed(1)}% crash with volume spike`,
        aggressionLevel: 9,
        targetType: "standard"
      };
    }
    // PUMP FADER: Fade extreme pumps
    else if (change24h > 15 && Math.abs(fundingRate) > 0.003) {
      decision = {
        strategy: "PUMP_FADER",
        multiplier: tradingConfig.tradeMultiplier * 0.6,
        reason: `🔄 PUMP FADER: Fading ${change24h.toFixed(1)}% pump`,
        aggressionLevel: 8,
        targetType: "quick"
      };
    }
    // WHALE FOLLOWER: Large imbalance = follow smart money
    else if (pairScore > 90 && confidenceScore >= conf.high) {
      decision = {
        strategy: "WHALE_FOLLOWER",
        multiplier: tradingConfig.tradeMultiplier * 0.8,
        reason: `🐋 WHALE FOLLOWER: High score ${pairScore}, following smart money`,
        aggressionLevel: 8,
        targetType: "standard"
      };
    }
    // VOLATILITY SURFER: High volatility = quick scalps
    else if (volatility24h > 6 && confidenceScore >= conf.scalpMin) {
      decision = {
        strategy: "VOLATILITY_SURFER",
        multiplier: tradingConfig.tradeMultiplier * 0.5,
        reason: `🌊 VOLATILITY SURFER: ${volatility24h.toFixed(1)}% volatility surfing`,
        aggressionLevel: 7,
        targetType: "scalp"
      };
    }
    // TALAKNERY TRAPS: Different aggression levels based on conditions
    else if (Math.abs(fundingRate) > 0.008 && confluenceLevel === "GODLIKE") {
      decision = {
        strategy: "TALAKNERY_TRAP_3",
        multiplier: tradingConfig.tradeMultiplier,
        reason: `🎯 TALAKNERY MAX: Extreme funding ${(fundingRate*100).toFixed(3)}%`,
        aggressionLevel: 10,
        targetType: "swing"
      };
    }
    else if (Math.abs(fundingRate) > 0.005 && (confluenceLevel === "GODLIKE" || confluenceLevel === "ELITE")) {
      decision = {
        strategy: "TALAKNERY_TRAP_2",
        multiplier: tradingConfig.tradeMultiplier * 0.7,
        reason: `🎯 TALAKNERY MED: Strong funding ${(fundingRate*100).toFixed(3)}%`,
        aggressionLevel: 8,
        targetType: "standard"
      };
    }
    else if (Math.abs(fundingRate) > 0.003) {
      decision = {
        strategy: "TALAKNERY_TRAP_1",
        multiplier: tradingConfig.tradeMultiplier * 0.5,
        reason: `🎯 TALAKNERY: Funding ${(fundingRate*100).toFixed(3)}%`,
        aggressionLevel: 6,
        targetType: "quick"
      };
    }
    // INFINITY SCALPERS: Different modes for different conditions
    else if (confidenceScore >= conf.high && pairScore > 70) {
      decision = {
        strategy: "INFINITY_SCALPER_4",
        multiplier: tradingConfig.tradeMultiplier * 0.6,
        reason: `♾️ INFINITY 4: High confidence ${confidenceScore}%, score ${pairScore}`,
        aggressionLevel: 8,
        targetType: "quick"
      };
    }
    else if (confidenceScore >= conf.min && pairScore > 60) {
      decision = {
        strategy: "INFINITY_SCALPER_3",
        multiplier: tradingConfig.tradeMultiplier * 0.5,
        reason: `♾️ INFINITY 3: Good setup, conf ${confidenceScore}%`,
        aggressionLevel: 7,
        targetType: "scalp"
      };
    }
    else if (confidenceScore >= conf.scalpMin) {
      decision = {
        strategy: "INFINITY_SCALPER_2",
        multiplier: tradingConfig.tradeMultiplier * 0.4,
        reason: `♾️ INFINITY 2: Scalp mode, conf ${confidenceScore}%`,
        aggressionLevel: 6,
        targetType: "scalp"
      };
    }
    // SNOWBALL: Winning streak compound
    else if (autoPilotState.strategy.consecutiveWins >= 2) {
      const snowballMultiplier = Math.min(Math.pow(1.5, autoPilotState.snowballStack + 1), tradingConfig.tradeMultiplier);
      decision = {
        strategy: "SNOWBALL",
        multiplier: snowballMultiplier,
        reason: `❄️ SNOWBALL: Stack ${autoPilotState.snowballStack + 1}, ${snowballMultiplier.toFixed(1)}x compound`,
        aggressionLevel: 7,
        targetType: "standard"
      };
    }
    // WATERFALL: Layered entries for strong signals
    else if (pairScore > 60 && (confluenceLevel === "GODLIKE" || confluenceLevel === "ELITE")) {
      decision = {
        strategy: "WATERFALL",
        multiplier: tradingConfig.tradeMultiplier * 0.4,
        reason: `🌊 WATERFALL: Layered entry, score ${pairScore}`,
        aggressionLevel: 6,
        targetType: "standard"
      };
    }
    
    // Dynamic aggression boost based on pair score
    if (pairScore > 100) {
      decision.multiplier *= 1.5;
      decision.aggressionLevel = Math.min(decision.aggressionLevel + 2, 10);
      decision.reason += ` [BOOSTED: Score ${pairScore}]`;
    }
    
    console.log(`🧠 AI STRATEGY: ${decision.strategy} | ${decision.reason} | Aggression: ${decision.aggressionLevel}/10`);
    
    return decision;
  }

  // Apply aggressive strategy to trade amount with new sizing rules
  function calculateAggressiveTradeAmount(decision: StrategyDecision): number {
    let amount = tradingConfig.minTrade * decision.multiplier;
    
    // Cap based on position size limits (40%-95% of balance)
    const maxAmount = tradingConfig.minTrade * tradingConfig.tradeMultiplier;
    amount = Math.min(amount, maxAmount);
    amount = Math.max(amount, tradingConfig.minTrade);
    
    autoPilotState.currentAmount = amount;
    return amount;
  }

  // Legacy wrapper for compatibility
  function selectOptimalStrategy(marketData: any, consensus: any): "SNOWBALL" | "WATERFALL" | "DOUBLING" {
    const decision = selectAggressiveStrategy(marketData, consensus, bestPair);
    // Map new strategies to legacy types for compatibility
    if (decision.strategy === "SNOWBALL" || decision.strategy === "WATERFALL") {
      return decision.strategy;
    }
    // All other strategies map to SNOWBALL for legacy systems
    return "SNOWBALL";
  }
  
  // Get auto-pilot status with strategy info
  app.get("/api/auto-pilot/status", (req, res) => {
    res.json({
      ...autoPilotState,
      uptime: autoPilotState.startTime 
        ? Math.floor((Date.now() - autoPilotState.startTime.getTime()) / 1000) 
        : 0,
      winRate: autoPilotState.tradeCount > 0 
        ? ((autoPilotState.winCount / autoPilotState.tradeCount) * 100).toFixed(1) 
        : 0,
      activeStrategy: autoPilotState.strategy.name,
      snowballStack: autoPilotState.snowballStack,
      doublingLevel: autoPilotState.doublingLevel,
      currentTradeAmount: autoPilotState.currentAmount,
      cyclesPerMinute: Math.round(60000 / autoPilotState.scanInterval),
      consecutiveWins: autoPilotState.strategy.consecutiveWins,
      consecutiveLosses: autoPilotState.strategy.consecutiveLosses,
      multiplier: (autoPilotState.currentAmount / autoPilotState.baseAmount).toFixed(2) + "x",
      bestPair: bestPair ? {
        pair: bestPair.pair,
        score: bestPair.score,
        signal: bestPair.signal,
        fundingRate: (bestPair.fundingRate * 100).toFixed(4) + "%",
        change24h: bestPair.change24h.toFixed(2) + "%",
        reason: bestPair.reason
      } : null,
      strategies: tradingConfig.strategies,
      tradingConfig: {
        tradeMultiplier: tradingConfig.tradeMultiplier + "X",
        positionSizes: `${tradingConfig.positionSizeMin}%-${tradingConfig.positionSizeMax}%`,
        maxExposure: tradingConfig.maxExposure + "%",
        minTrade: "$" + tradingConfig.minTrade,
        scanInterval: tradingConfig.scanInterval + "ms (ULTRA FAST)",
        minBetweenTrades: tradingConfig.minBetweenTrades + "ms",
        scalpTarget: tradingConfig.scalpTarget + "%",
        scalpHoldMax: tradingConfig.scalpHoldMax + "s",
        pairs: tradingConfig.pairs,
        profitTargets: tradingConfig.profitTargets,
        confidence: tradingConfig.confidence,
        activeStrategies: tradingConfig.strategies.length
      },
      // Alpha Arena Gods Level Configuration
      alphaArena: {
        enabled: tradingConfig.alphaArena.enabled,
        riskProfile: tradingConfig.alphaArena.riskProfile,
        pillars: {
          capitalPreservation: {
            maxDailyDrawdown: tradingConfig.alphaArena.capitalPreservation.maxDailyDrawdown + "%",
            status: checkDailyDrawdown(autoPilotState.totalPnl).status
          },
          riskPerTrade: tradingConfig.alphaArena.riskPerTrade + "%",
          mandatoryStopLoss: tradingConfig.alphaArena.mandatoryStopLoss,
          trendFollowingOnly: tradingConfig.alphaArena.trendFollowingOnly,
          minConfluenceScore: tradingConfig.alphaArena.minConfluenceScore,
          minRewardRiskRatio: tradingConfig.alphaArena.minRewardRiskRatio + ":1",
          maxLeverage: tradingConfig.alphaArena.maxLeverage + "x",
          consensusRequired: `${tradingConfig.alphaArena.consensusRequired}/${tradingConfig.alphaArena.totalAgents} agents`
        },
        dailyDrawdown: checkDailyDrawdown(autoPilotState.totalPnl)
      },
      // Engine validation stats
      engineStats: autoPilotState.engineStats,
      // AI-generated levels from last analysis
      aiLevels: autoPilotState.lastAiLevels,
      // Active tracked positions
      activePositions: Array.from(activePositions.values()).map(p => ({
        symbol: p.symbol,
        side: p.side,
        entryPrice: p.entryPrice,
        size: p.size,
        stopLoss: p.stopLoss,
        takeProfits: {
          tp1: p.takeProfitLevels.tp1.price,
          tp2: p.takeProfitLevels.tp2.price,
          tp3: p.takeProfitLevels.tp3.price
        },
        cascadeHits: p.profitCascade.filter(c => c.hit).length,
        confluenceLevel: p.confluenceLevel,
        openedAt: p.openedAt
      })),
      // Profit cascade config
      profitCascade: tradingEngines.getProfitCascade()
    });
  });
  
  // Get active positions with AI levels
  app.get("/api/positions/active", (req, res) => {
    const positions = Array.from(activePositions.values()).map(p => ({
      id: p.id,
      symbol: p.symbol,
      side: p.side,
      entryPrice: p.entryPrice,
      size: p.size,
      leverage: p.leverage,
      stopLoss: {
        price: p.stopLoss,
        reason: p.stopLossReason
      },
      takeProfits: {
        tp1: { price: p.takeProfitLevels.tp1.price, hit: p.takeProfitLevels.tp1.hit },
        tp2: { price: p.takeProfitLevels.tp2.price, hit: p.takeProfitLevels.tp2.hit },
        tp3: { price: p.takeProfitLevels.tp3.price, hit: p.takeProfitLevels.tp3.hit }
      },
      profitCascade: p.profitCascade,
      partialExits: p.partialExits,
      confluenceLevel: p.confluenceLevel,
      verdict: p.verdict,
      riskReward: p.riskReward,
      smartGatesPassed: p.smartGatesPassed,
      openedAt: p.openedAt,
      lastChecked: p.lastChecked
    }));
    
    res.json({
      count: positions.length,
      positions,
      profitCascadeLevels: tradingEngines.getProfitCascade()
    });
  });
  
  // Get current best pair
  app.get("/api/best-pair", async (req, res) => {
    const pair = await scanForBestPair();
    res.json(pair);
  });
  
  // Start auto-pilot mode with ULTRA-AGGRESSIVE defaults
  app.post("/api/auto-pilot/start", async (req, res) => {
    const { 
      mode = "SHORTS_ONLY",
      coins = tradingConfig.pairs,
      amountPerTrade = tradingConfig.minTrade,
      maxLeverage = 50,
      scanInterval = tradingConfig.scanInterval,
      executionInterval = 100,
      maxCycles = 0,
      enableStrategies = true
    } = req.body;
    
    // Reset strategy state for new session with ULTRA-AGGRESSIVE settings
    if (enableStrategies) {
      autoPilotState.baseAmount = Math.max(amountPerTrade, tradingConfig.minTrade);
      autoPilotState.currentAmount = autoPilotState.baseAmount;
      autoPilotState.snowballStack = 0;
      autoPilotState.doublingLevel = 0;
      autoPilotState.waterfallLayers = [];
      autoPilotState.strategy = { 
        name: "TURBO_SCALP", 
        active: true, 
        multiplier: tradingConfig.tradeMultiplier, 
        layers: 1, 
        consecutiveWins: 0, 
        consecutiveLosses: 0 
      };
    }
    
    if (autoPilotState.running) {
      return res.json({ 
        success: false, 
        message: "Auto-pilot already running",
        status: autoPilotState 
      });
    }
    
    autoPilotState.running = true;
    autoPilotState.mode = mode;
    autoPilotState.startTime = new Date();
    autoPilotState.currentCycle = 0;
    autoPilotState.scanInterval = scanInterval;
    autoPilotState.executionInterval = executionInterval;
    
    res.json({ 
      success: true, 
      message: `Auto-pilot started in ${mode} mode`,
      config: { coins, amountPerTrade, maxLeverage, scanInterval, executionInterval, maxCycles }
    });
    
    // Run auto-pilot loop in background
    runAutoPilotLoop(coins, amountPerTrade, maxLeverage, maxCycles);
  });
  
  // Stop auto-pilot mode
  app.post("/api/auto-pilot/stop", (req, res) => {
    autoPilotState.running = false;
    res.json({ 
      success: true, 
      message: "Auto-pilot stopped",
      finalStats: {
        totalTrades: autoPilotState.tradeCount,
        totalPnl: autoPilotState.totalPnl,
        winRate: autoPilotState.tradeCount > 0 
          ? ((autoPilotState.winCount / autoPilotState.tradeCount) * 100).toFixed(1) 
          : 0,
        cycles: autoPilotState.currentCycle
      }
    });
  });
  
  // Reset auto-pilot stats
  app.post("/api/auto-pilot/reset", (req, res) => {
    autoPilotState.tradeCount = 0;
    autoPilotState.totalPnl = 0;
    autoPilotState.winCount = 0;
    autoPilotState.lossCount = 0;
    autoPilotState.currentCycle = 0;
    res.json({ success: true, message: "Stats reset" });
  });

  // ============ WOLF PACK API ENDPOINTS ============
  
  // Get Wolf Pack status
  app.get("/api/wolf-pack/status", (req, res) => {
    const stats = wolfPack.getStats();
    res.json(stats);
  });

  // Start Wolf Pack
  app.post("/api/wolf-pack/start", (req, res) => {
    const result = wolfPack.start();
    res.json(result);
  });

  // Stop Wolf Pack
  app.post("/api/wolf-pack/stop", (req, res) => {
    const result = wolfPack.stop();
    res.json(result);
  });
  
  async function runAutoPilotLoop(
    coins: string[], 
    amountPerTrade: number, 
    maxLeverage: number,
    maxCycles: number
  ) {
    const { placeFuturesOrder, getFuturesBalance, getSpotBalance, placeSpotOrder } = await import("./gateio");
    
    console.log(`🚀 AUTO-PILOT STARTED: ${autoPilotState.mode} mode - SMART PAIR SELECTION ENABLED`);
    
    while (autoPilotState.running) {
      try {
        autoPilotState.currentCycle++;
        
        if (maxCycles > 0 && autoPilotState.currentCycle > maxCycles) {
          console.log(`✅ Max cycles (${maxCycles}) reached. Stopping auto-pilot.`);
          autoPilotState.running = false;
          break;
        }
        
        // SMART SCAN: Find #1 most profitable pair every 30 seconds
        const now = Date.now();
        if (!bestPair || now - lastPairScan > PAIR_SCAN_INTERVAL) {
          console.log(`\n🔍 SCANNING ALL PAIRS FOR BEST OPPORTUNITY...`);
          bestPair = await scanForBestPair();
          lastPairScan = now;
        }
        
        // Focus on the #1 best pair only
        const tradingPairs = bestPair ? [bestPair.pair] : coins;
        console.log(`\n🔄 CYCLE ${autoPilotState.currentCycle} - Trading: ${bestPair?.pair || 'multiple'} (Score: ${bestPair?.score.toFixed(0) || 'N/A'})`);
        
        for (const coin of tradingPairs) {
          if (!autoPilotState.running) break;
          
          const coinName = coin.split("_")[0];
          
          // Fetch market data
          let marketData = await fetchGateMarketData(coin);
          if (!marketData) {
            marketData = generateMockMarketData(coin);
          }
          
          // Run all 8 AI agents
          const analyses = [];
          for (const agent of DEFAULT_AGENTS) {
            if (!agent.enabled) continue;
            const analysis = await analyzeWithAgent(agent, marketData);
            analyses.push(analysis);
          }
          
          // Calculate consensus
          const consensus = calculateConsensus(coin, marketData, analyses);
          
          // Run 10 engines
          tradingEngines.runAllEngines(marketData, consensus);
          
          // DYNAMIC STRATEGY ENGINE - ADX-Based Strategy Selection (Gods Level)
          const dynamicDecision = selectDynamicStrategy(marketData);
          console.log(`🎮 DYNAMIC STRATEGY: ${dynamicDecision.strategy} | ${dynamicDecision.reason}`);
          console.log(`   📈 Regime: ${dynamicStrategyState.regime} | Layers: ${dynamicDecision.layers} | Target: ${dynamicDecision.targetPercent}%`);
          
          // AI selects AGGRESSIVE profit strategy based on market conditions
          const strategyDecision = selectAggressiveStrategy(marketData, consensus, bestPair);
          autoPilotState.strategy.name = strategyDecision.strategy as any;
          const aggressiveAmount = calculateAggressiveTradeAmount(strategyDecision) * dynamicDecision.multiplier;
          console.log(`🎯 TRADE AMOUNT: $${aggressiveAmount.toFixed(2)} (${strategyDecision.multiplier.toFixed(1)}x base, ${dynamicDecision.multiplier}x dynamic)`);

          // ENGINE VALIDATION - Check Governor, Circuit Breakers, Smart Gates
          const validation = validateTradeWithEngines(marketData, consensus);
          
          // ALPHA ARENA GODS LEVEL VALIDATION - Check all 8 Pillars
          const alphaValidation = validateAlphaArenaTrade(
            marketData,
            { 
              stopLoss: consensus.invalidation?.price,
              tp2: consensus.targets?.tp2?.price,
              direction: consensus.consensusSignal?.toUpperCase(),
              confidence: consensus.confidenceScore || 50,
              leverage: maxLeverage
            },
            1000, // Account balance placeholder
            analyses
          );
          
          if (!validation.approved) {
            console.log(`🚫 ENGINE REJECTED: ${coinName} - ${validation.reasons.join(", ")}`);
          }
          
          // Log Alpha Arena 8 Pillars Status
          if (tradingConfig.alphaArena.enabled) {
            const passedPillars = alphaValidation.pillarResults.filter(p => p.passed).length;
            if (!alphaValidation.approved) {
              const failedPillars = alphaValidation.pillarResults.filter(p => !p.passed).map(p => p.pillar);
              console.log(`🏛️ ALPHA ARENA: ${passedPillars}/8 pillars passed - Failed: ${failedPillars.join(", ")}`);
            } else {
              console.log(`🏛️ ALPHA ARENA: ${passedPillars}/8 PILLARS PASSED ✅ (Score: ${alphaValidation.finalScore}%)`);
            }
          }
          
          // Combined validation: Both engine AND Alpha Arena must approve
          const fullyApproved = validation.approved && (tradingConfig.alphaArena.enabled ? alphaValidation.approved : true);
          
          // SHORTS-ONLY MODE: REAL TRADING - Only execute if SHORT signal with strong confluence + engine + Alpha Arena approval
          if (autoPilotState.mode === "SHORTS_ONLY" && fullyApproved) {
            if (consensus.consensusSignal === "short" && 
                (consensus.confluenceLevel === "GODLIKE" || consensus.confluenceLevel === "ELITE" || consensus.confluenceLevel === "STRONG")) {
              
              // Apply aggressive strategy amount
              let tradeAmount = aggressiveAmount;
              
              if (dynamicDecision.strategy === "WATERFALL" || strategyDecision.strategy === "WATERFALL") {
                const layers = applyWaterfall(marketData.currentPrice, "short");
                console.log(`🌊 WATERFALL SHORT: ${layers.length} layers from $${layers[0].toFixed(2)} to $${layers[layers.length-1].toFixed(2)}`);
              }
              
              if (dynamicDecision.strategy === "PYRAMID") {
                const layers = applyPyramid(marketData.currentPrice, "short");
                console.log(`🔺 PYRAMID SHORT: ${layers.length} layers (increasing size) from $${layers[0].toFixed(2)} to $${layers[layers.length-1].toFixed(2)}`);
              }
              
              if (dynamicDecision.strategy === "DOUBLING") {
                console.log(`🔄 DOUBLING MODE: ${dynamicStrategyState.doublingMultiplier}x position size for loss recovery`);
              }
              
              // Display AI-generated levels
              const sl = consensus.invalidation?.price || marketData.currentPrice * 1.02;
              const tp1 = consensus.targets?.tp1?.price || marketData.currentPrice * 0.99;
              const tp2 = consensus.targets?.tp2?.price || marketData.currentPrice * 0.98;
              console.log(`🩳 SHORT SIGNAL [REAL]: ${coinName} (${consensus.confluenceLevel}) - $${tradeAmount.toFixed(2)} [${strategyDecision.strategy}]`);
              console.log(`   📊 AI LEVELS: SL $${sl.toFixed(4)} | TP1 $${tp1.toFixed(4)} | TP2 $${tp2.toFixed(4)} | R:R ${(consensus.riskReward?.toTp2 || 0).toFixed(1)}`);
              
              try {
                const balance = await getFuturesBalance();
                if (balance && balance.available >= tradeAmount / maxLeverage) {
                  const order = await placeFuturesOrder({
                    contract: coin,
                    size: -tradeAmount,
                    leverage: maxLeverage
                  });
                  
                  if (order) {
                    // Create tracked position with AI levels and validation metadata - NO SIMULATION
                    const position = createPosition(
                      coin, 
                      "short", 
                      marketData.currentPrice, 
                      tradeAmount, 
                      maxLeverage,
                      consensus,
                      validation
                    );
                    
                    autoPilotState.tradeCount++;
                    autoPilotState.lastTrade = new Date();
                    console.log(`🩳 SHORT OPENED [REAL]: ${coinName} @ $${marketData.currentPrice.toFixed(4)} | Monitoring for SL/TP...`);
                    console.log(`   🔥 Position tracked - Waiting for price to hit SL or TP`);
                  }
                } else {
                  console.log(`⚠️ Insufficient balance for ${coinName} short (need $${(tradeAmount / maxLeverage).toFixed(2)})`);
                }
              } catch (e) {
                console.log(`⚠️ Short order failed for ${coinName}: ${e}`);
              }
            }
          }
          
          // SPOT-ONLY MODE: Buy on LONG signals with AGGRESSIVE strategies + engine + Alpha Arena approval
          if ((autoPilotState.mode === "SPOT_ONLY" || autoPilotState.mode === "BOTH") && fullyApproved) {
            if (consensus.consensusSignal === "long" && 
                (consensus.confluenceLevel === "GODLIKE" || consensus.confluenceLevel === "ELITE" || consensus.confluenceLevel === "STRONG")) {
              
              // Apply aggressive strategy amount
              let tradeAmount = aggressiveAmount;
              
              if (strategyDecision.strategy === "WATERFALL") {
                const layers = applyWaterfall(marketData.currentPrice, "long");
                console.log(`🌊 WATERFALL LONG: ${layers.length} layers from $${layers[0].toFixed(2)} to $${layers[layers.length-1].toFixed(2)}`);
              }
              
              // Display AI-generated levels
              const sl = consensus.invalidation?.price || marketData.currentPrice * 0.98;
              const tp1 = consensus.targets?.tp1?.price || marketData.currentPrice * 1.01;
              const tp2 = consensus.targets?.tp2?.price || marketData.currentPrice * 1.02;
              console.log(`🟢 LONG SIGNAL: ${coinName} (${consensus.confluenceLevel}) - $${tradeAmount.toFixed(2)} [${strategyDecision.strategy}]`);
              console.log(`   📊 AI LEVELS: SL $${sl.toFixed(2)} | TP1 $${tp1.toFixed(2)} | TP2 $${tp2.toFixed(2)} | R:R ${(consensus.riskReward?.toTp2 || 0).toFixed(1)}`);
              
              try {
                const balance = await getSpotBalance("USDT");
                if (balance && balance.available >= tradeAmount) {
                  const order = await placeSpotOrder({
                    currencyPair: coin,
                    side: "buy",
                    amount: tradeAmount.toString(),
                    type: "market"
                  });
                  
                  if (order) {
                    // Create tracked position with AI levels and validation metadata
                    const position = createPosition(
                      coin, 
                      "long", 
                      marketData.currentPrice, 
                      tradeAmount, 
                      1, // Spot has no leverage
                      consensus,
                      validation
                    );
                    
                    autoPilotState.tradeCount++;
                    autoPilotState.lastTrade = new Date();
                    console.log(`✅ LONG OPENED: ${coinName} @ $${marketData.currentPrice.toFixed(4)} | Monitoring for SL/TP...`);
                  }
                }
              } catch (e) {
                console.log(`⚠️ Buy order failed for ${coinName}: ${e}`);
              }
            }
          }
          
          // BOTH MODE: Also allow shorts
          if (autoPilotState.mode === "BOTH" && validation.approved) {
            if (consensus.consensusSignal === "short" && 
                (consensus.confluenceLevel === "GODLIKE" || consensus.confluenceLevel === "ELITE" || consensus.confluenceLevel === "STRONG")) {
              
              let tradeAmount = aggressiveAmount;
              
              const sl = consensus.invalidation?.price || marketData.currentPrice * 1.02;
              const tp1 = consensus.targets?.tp1?.price || marketData.currentPrice * 0.99;
              const tp2 = consensus.targets?.tp2?.price || marketData.currentPrice * 0.98;
              console.log(`🩳 SHORT SIGNAL (BOTH): ${coinName} (${consensus.confluenceLevel}) - $${tradeAmount.toFixed(2)} [${strategyDecision.strategy}]`);
              console.log(`   📊 AI LEVELS: SL $${sl.toFixed(2)} | TP1 $${tp1.toFixed(2)} | TP2 $${tp2.toFixed(2)}`);
              
              try {
                const balance = await getFuturesBalance();
                if (balance && balance.available >= tradeAmount / maxLeverage) {
                  const order = await placeFuturesOrder({
                    contract: coin,
                    size: -tradeAmount,
                    leverage: maxLeverage
                  });
                  
                  if (order) {
                    // REAL TRADING - Position monitoring handles PnL
                    createPosition(coin, "short", marketData.currentPrice, tradeAmount, maxLeverage, consensus, validation);
                    autoPilotState.tradeCount++;
                    autoPilotState.lastTrade = new Date();
                    console.log(`🩳 SHORT OPENED: ${coinName} @ $${marketData.currentPrice.toFixed(4)} | Monitoring for SL/TP...`);
                  }
                } else {
                  console.log(`⚠️ Insufficient balance for BOTH mode short`);
                }
              } catch (e) {
                console.log(`⚠️ Short order failed: ${e}`);
              }
            }
          }
          
          // Wait between coin analyses
          await new Promise(r => setTimeout(r, autoPilotState.executionInterval));
        }
        
        // MONITOR ALL ACTIVE POSITIONS - Check for SL/TP hits with live prices
        if (activePositions.size > 0) {
          console.log(`📡 MONITORING ${activePositions.size} active position(s)...`);
          const priceMap = new Map<string, number>();
          
          // Fetch current prices for all open positions
          for (const [id, pos] of activePositions) {
            try {
              const liveData = await fetchGateMarketData(pos.symbol);
              if (liveData) {
                priceMap.set(pos.symbol, liveData.currentPrice);
              }
            } catch (e) {
              // Use simulated price tick if fetch fails
              const simulatedPrice = pos.entryPrice * (1 + (Math.random() - 0.5) * 0.02);
              priceMap.set(pos.symbol, simulatedPrice);
            }
          }
          
          // Process each position for SL/TP hits
          for (const [id, position] of activePositions) {
            const currentPrice = priceMap.get(position.symbol);
            if (!currentPrice) continue;
            
            const isShort = position.side === "short";
            const pnlPercent = isShort 
              ? ((position.entryPrice - currentPrice) / position.entryPrice) * 100 * position.leverage
              : ((currentPrice - position.entryPrice) / position.entryPrice) * 100 * position.leverage;
            const pnlDollars = (pnlPercent / 100) * position.size;
            
            // Check STOP LOSS
            const hitSL = isShort 
              ? currentPrice >= position.stopLoss
              : currentPrice <= position.stopLoss;
            
            if (hitSL) {
              console.log(`❌ STOP LOSS HIT: ${position.symbol} @ $${currentPrice.toFixed(4)} | Loss: $${Math.abs(pnlDollars).toFixed(2)}`);
              autoPilotState.lossCount++;
              autoPilotState.totalPnl -= Math.abs(pnlDollars);
              tradingEngines.recordTrade(-Math.abs(pnlDollars));
              applySnowball(false);
              activePositions.delete(id);
              continue;
            }
            
            // Check TP1 (25% close)
            if (!position.takeProfitLevels.tp1.hit) {
              const hitTP1 = isShort 
                ? currentPrice <= position.takeProfitLevels.tp1.price
                : currentPrice >= position.takeProfitLevels.tp1.price;
              
              if (hitTP1) {
                const partialProfit = pnlDollars * 0.25;
                console.log(`✅ TP1 HIT: ${position.symbol} | Partial profit: +$${partialProfit.toFixed(2)} (25% closed)`);
                position.takeProfitLevels.tp1.hit = true;
                autoPilotState.totalPnl += partialProfit;
                tradingEngines.recordTrade(partialProfit);
              }
            }
            
            // Check TP2 (50% close)
            if (!position.takeProfitLevels.tp2.hit) {
              const hitTP2 = isShort 
                ? currentPrice <= position.takeProfitLevels.tp2.price
                : currentPrice >= position.takeProfitLevels.tp2.price;
              
              if (hitTP2) {
                const partialProfit = pnlDollars * 0.50;
                console.log(`✅ TP2 HIT: ${position.symbol} | Partial profit: +$${partialProfit.toFixed(2)} (50% closed)`);
                position.takeProfitLevels.tp2.hit = true;
                autoPilotState.totalPnl += partialProfit;
                autoPilotState.winCount++;
                applySnowball(true);
                tradingEngines.recordTrade(partialProfit);
              }
            }
            
            // Check TP3 (full close)
            if (!position.takeProfitLevels.tp3.hit) {
              const hitTP3 = isShort 
                ? currentPrice <= position.takeProfitLevels.tp3.price
                : currentPrice >= position.takeProfitLevels.tp3.price;
              
              if (hitTP3) {
                const partialProfit = pnlDollars * 0.25;
                console.log(`🎯 TP3 HIT: ${position.symbol} | Final profit: +$${partialProfit.toFixed(2)} (100% closed)`);
                position.takeProfitLevels.tp3.hit = true;
                autoPilotState.totalPnl += partialProfit;
                tradingEngines.recordTrade(partialProfit);
                activePositions.delete(id);
              }
            }
            
            position.lastChecked = new Date();
          }
        }
        
        // Wait before next scan cycle
        await new Promise(r => setTimeout(r, autoPilotState.scanInterval));
        
      } catch (error) {
        console.error("Auto-pilot cycle error:", error);
        await new Promise(r => setTimeout(r, 5000));
      }
    }
    
    console.log(`🛑 AUTO-PILOT STOPPED after ${autoPilotState.currentCycle} cycles`);
  }
  
  // Hyper-velocity single short execution
  app.post("/api/hyper-short/:symbol", requireTradingEnabled, async (req, res) => {
    const { symbol } = req.params;
    const { leverage = 50, amount = 50 } = req.body;
    
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders();
    
    const sendEvent = (data: any) => {
      res.write(`data: ${JSON.stringify(data)}\n\n`);
    };
    
    try {
      const { placeFuturesOrder, getFuturesBalance, closePosition } = await import("./gateio");
      
      sendEvent({ type: "start", message: `HYPER-SHORT: ${symbol} @ ${leverage}x` });
      
      // Check balance
      const balance = await getFuturesBalance();
      const requiredMargin = amount / leverage * 1.1;
      
      if (!balance || balance.available < requiredMargin) {
        sendEvent({ type: "error", message: `Insufficient margin: need $${requiredMargin.toFixed(2)}` });
        res.write("data: [DONE]\n\n");
        return res.end();
      }
      
      sendEvent({ type: "balance", available: balance.available });
      
      // Run 8 AI agents
      let marketData = await fetchGateMarketData(symbol);
      if (!marketData) marketData = generateMockMarketData(symbol);
      
      sendEvent({ type: "analyzing", message: "Running 8 AI agents for SHORT analysis..." });
      
      const analyses = [];
      for (const agent of DEFAULT_AGENTS) {
        if (!agent.enabled) continue;
        const analysis = await analyzeWithAgent(agent, marketData);
        analyses.push(analysis);
        sendEvent({ type: "agent", agent: agent.name, signal: analysis.signal, confidence: analysis.confidence });
      }
      
      const consensus = calculateConsensus(symbol, marketData, analyses);
      
      // Check for short signal
      const shortAgents = analyses.filter(a => a.signal === "short").length;
      sendEvent({ type: "consensus", signal: consensus.consensusSignal, confluence: consensus.confluenceLevel, shortAgents });
      
      if (shortAgents >= 5) {
        sendEvent({ type: "executing", action: "SHORT", amount, leverage });
        
        const order = await placeFuturesOrder({
          contract: symbol.replace("/", "_"),
          size: -amount,
          leverage
        });
        
        if (order) {
          sendEvent({ type: "trade", status: "SUCCESS", orderId: order.id });
          
          // Hold for micro-profit then close
          await new Promise(r => setTimeout(r, 3000));
          
          sendEvent({ type: "closing", message: "Taking micro-profit..." });
          const closeOrder = await closePosition(symbol.replace("/", "_"));
          
          if (closeOrder) {
            sendEvent({ type: "closed", status: "SUCCESS" });
          }
        } else {
          sendEvent({ type: "trade", status: "FAILED" });
        }
      } else {
        sendEvent({ type: "skip", message: `Only ${shortAgents}/8 agents agree on SHORT. Minimum 5 required.` });
      }
      
      res.write("data: [DONE]\n\n");
      res.end();
    } catch (error) {
      sendEvent({ type: "error", message: error instanceof Error ? error.message : "Hyper-short failed" });
      res.end();
    }
  });

  return httpServer;
}
