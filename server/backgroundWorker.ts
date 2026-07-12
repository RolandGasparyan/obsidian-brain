import { log } from "./index";
import { wolfPack } from "./wolfpack";

interface BackgroundWorkerConfig {
  mode: "SHORTS_ONLY" | "SPOT_ONLY" | "BOTH";
  coins: string[];
  amountPerTrade: number;
  maxLeverage: number;
  scanInterval: number;
  executionInterval: number;
  maxCycles: number;
  autoRestart: boolean;
  healthCheckInterval: number;
  watchdogInterval: number;
}

// ═══════════════════════════════════════════════════════════════════════════
// ⚡ GODS LEVEL BACKGROUND WORKER - 24/7 UNCRASHABLE SYSTEM
// ═══════════════════════════════════════════════════════════════════════════
const DEFAULT_CONFIG: BackgroundWorkerConfig = {
  mode: "BOTH",
  coins: ["BTC_USDT", "ETH_USDT"],
  amountPerTrade: 33,
  maxLeverage: 5,
  scanInterval: 30000,
  executionInterval: 2000,
  maxCycles: 0,
  autoRestart: true,
  healthCheckInterval: 60000, // 60 seconds
  watchdogInterval: 30000 // 30 seconds
};

// ═══════════════════════════════════════════════════════════════════════════
// 🛡️ HEALTH CHECK STATE
// ═══════════════════════════════════════════════════════════════════════════
interface HealthCheckState {
  lastCheck: Date | null;
  checkCount: number;
  issuesFound: number;
  issuesFixed: number;
  crashRecoveries: number;
  consecutiveFailures: number;
  healthScore: number;
  engines: {
    wolfPack: boolean;
    aiModels: boolean;
    gateioConnection: boolean;
    autoPilot: boolean;
    tradingEngine: boolean;
    protectionSystem: boolean;
  };
  configs: {
    tradingConfig: boolean;
    balanceProtection: boolean;
    riskSettings: boolean;
  };
  lastErrors: string[];
}

class BackgroundWorker {
  private isRunning: boolean = false;
  private config: BackgroundWorkerConfig;
  private startTime: Date | null = null;
  private restartCount: number = 0;
  private lastError: string | null = null;
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private watchdogInterval: NodeJS.Timeout | null = null;
  private mainLoopInterval: NodeJS.Timeout | null = null;
  
  private healthState: HealthCheckState = {
    lastCheck: null,
    checkCount: 0,
    issuesFound: 0,
    issuesFixed: 0,
    crashRecoveries: 0,
    consecutiveFailures: 0,
    healthScore: 100,
    engines: {
      wolfPack: false,
      aiModels: false,
      gateioConnection: false,
      autoPilot: false,
      tradingEngine: false,
      protectionSystem: false
    },
    configs: {
      tradingConfig: false,
      balanceProtection: false,
      riskSettings: false
    },
    lastErrors: []
  };

  constructor(config: Partial<BackgroundWorkerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  async start(): Promise<{ success: boolean; message: string }> {
    if (this.isRunning) {
      return { success: false, message: "Background worker already running" };
    }

    this.isRunning = true;
    this.startTime = new Date();
    
    log(`🔱 GODS LEVEL 24/7 BACKGROUND WORKER STARTING`, "worker");
    log(`   Mode: ${this.config.mode}`, "worker");
    log(`   Health Check: Every ${this.config.healthCheckInterval / 1000}s`, "worker");
    log(`   Watchdog: Every ${this.config.watchdogInterval / 1000}s`, "worker");
    log(`   Auto-restart: ${this.config.autoRestart ? "ENABLED" : "DISABLED"}`, "worker");

    // Start main loop
    this.runMainLoop();
    
    // Start health check interval (every 60 seconds)
    this.startHealthCheckLoop();
    
    // Start watchdog (every 30 seconds)
    this.startWatchdog();

    return { 
      success: true, 
      message: `🔱 Gods Level Worker started - 24/7 uncrashable mode` 
    };
  }

  stop(): { success: boolean; message: string } {
    this.isRunning = false;
    
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
    
    if (this.watchdogInterval) {
      clearInterval(this.watchdogInterval);
      this.watchdogInterval = null;
    }
    
    if (this.mainLoopInterval) {
      clearInterval(this.mainLoopInterval);
      this.mainLoopInterval = null;
    }
    
    log("⏹️ BACKGROUND WORKER STOPPED", "worker");
    return { success: true, message: "Background worker stopped" };
  }

  getStatus() {
    return {
      isRunning: this.isRunning,
      mode: this.config.mode,
      startTime: this.startTime,
      restartCount: this.restartCount,
      lastError: this.lastError,
      config: this.config,
      uptime: this.startTime 
        ? Math.floor((Date.now() - this.startTime.getTime()) / 1000) 
        : 0,
      healthCheck: this.healthState
    };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 🔄 MAIN LOOP - Keep engines running
  // ═══════════════════════════════════════════════════════════════════════════
  private runMainLoop() {
    this.mainLoopInterval = setInterval(async () => {
      if (!this.isRunning) return;
      
      try {
        await this.ensureEnginesRunning();
      } catch (error) {
        this.lastError = error instanceof Error ? error.message : "Unknown error";
        log(`❌ Main loop error: ${this.lastError}`, "worker");
      }
    }, 5000);
  }

  private async ensureEnginesRunning(): Promise<void> {
    try {
      // Check auto-pilot
      const autoPilotResponse = await fetch("http://localhost:5000/api/auto-pilot/status");
      const autoPilotStatus = await autoPilotResponse.json();
      
      if (!autoPilotStatus.running) {
        log("🚀 Auto-pilot not running, starting...", "worker");
        await fetch("http://localhost:5000/api/auto-pilot/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mode: this.config.mode,
            coins: this.config.coins,
            amountPerTrade: this.config.amountPerTrade,
            maxLeverage: this.config.maxLeverage,
            scanInterval: this.config.scanInterval,
            executionInterval: this.config.executionInterval,
            maxCycles: this.config.maxCycles
          })
        });
      }
      
      // Check trading engine
      const engineResponse = await fetch("http://localhost:5000/api/trading-engine/status");
      const engineStatus = await engineResponse.json();
      
      if (!engineStatus.isRunning) {
        log("🔧 Trading engine not running, starting...", "worker");
        await fetch("http://localhost:5000/api/trading-engine/start", { method: "POST" });
      }
      
    } catch (error) {
      // Network errors are expected during startup
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 🏥 COMPREHENSIVE HEALTH CHECK - Every 60 seconds
  // ═══════════════════════════════════════════════════════════════════════════
  private startHealthCheckLoop() {
    // Initial check after 10 seconds
    setTimeout(() => this.performComprehensiveHealthCheck(), 10000);
    
    // Regular checks every 60 seconds
    this.healthCheckInterval = setInterval(() => {
      this.performComprehensiveHealthCheck();
    }, this.config.healthCheckInterval);
  }

  private async performComprehensiveHealthCheck(): Promise<void> {
    if (!this.isRunning) return;
    
    const startTime = Date.now();
    const issues: string[] = [];
    const fixes: string[] = [];
    
    log("\n[HEALTH CHECK] 🔱 Starting comprehensive 60-second health check...", "worker");
    
    try {
      // ========== 1. TEST WOLF PACK ENGINE ==========
      const wolfPackResult = await this.testWolfPack();
      this.healthState.engines.wolfPack = wolfPackResult.passed;
      if (!wolfPackResult.passed) {
        issues.push(`Wolf Pack: ${wolfPackResult.error}`);
        const fixed = await this.recoverWolfPack();
        if (fixed) fixes.push("Wolf Pack restarted");
      }
      
      // ========== 2. TEST AI MODELS ==========
      const aiResult = await this.testAIModels();
      this.healthState.engines.aiModels = aiResult.passed;
      if (!aiResult.passed) {
        issues.push(`AI Models: ${aiResult.error}`);
      }
      
      // ========== 3. TEST GATE.IO CONNECTION ==========
      const gateioResult = await this.testGateioConnection();
      this.healthState.engines.gateioConnection = gateioResult.passed;
      if (!gateioResult.passed) {
        issues.push(`Gate.io: ${gateioResult.error}`);
      }
      
      // ========== 4. TEST AUTO-PILOT ==========
      const autoPilotResult = await this.testAutoPilot();
      this.healthState.engines.autoPilot = autoPilotResult.passed;
      if (!autoPilotResult.passed) {
        issues.push(`Auto-Pilot: ${autoPilotResult.error}`);
        const fixed = await this.recoverAutoPilot();
        if (fixed) fixes.push("Auto-Pilot restarted");
      }
      
      // ========== 5. TEST TRADING ENGINE ==========
      const tradingEngineResult = await this.testTradingEngine();
      this.healthState.engines.tradingEngine = tradingEngineResult.passed;
      if (!tradingEngineResult.passed) {
        issues.push(`Trading Engine: ${tradingEngineResult.error}`);
        const fixed = await this.recoverTradingEngine();
        if (fixed) fixes.push("Trading Engine restarted");
      }
      
      // ========== 6. TEST PROTECTION SYSTEM ==========
      const protectionResult = await this.testProtectionSystem();
      this.healthState.engines.protectionSystem = protectionResult.passed;
      if (!protectionResult.passed) {
        issues.push(`Protection: ${protectionResult.error}`);
        const fixed = await this.enableUnbreakableMode();
        if (fixed) fixes.push("Unbreakable Mode re-enabled");
      }
      
      // ========== 7. VERIFY TRADING CONFIG ==========
      const configResult = await this.verifyTradingConfig();
      this.healthState.configs.tradingConfig = configResult.valid;
      if (!configResult.valid) {
        issues.push(`Config: ${configResult.error}`);
      }
      
      // ========== 8. VERIFY BALANCE PROTECTION ==========
      const balanceResult = await this.verifyBalanceProtection();
      this.healthState.configs.balanceProtection = balanceResult.valid;
      if (!balanceResult.valid) {
        issues.push(`Balance Protection: ${balanceResult.error}`);
      }
      
      // ========== 9. VERIFY RISK SETTINGS ==========
      const riskResult = await this.verifyRiskSettings();
      this.healthState.configs.riskSettings = riskResult.valid;
      if (!riskResult.valid) {
        issues.push(`Risk: ${riskResult.error}`);
      }
      
      // ========== CALCULATE HEALTH SCORE ==========
      const enginesPassed = Object.values(this.healthState.engines).filter(v => v).length;
      const configsPassed = Object.values(this.healthState.configs).filter(v => v).length;
      const total = Object.keys(this.healthState.engines).length + Object.keys(this.healthState.configs).length;
      
      this.healthState.healthScore = Math.round(((enginesPassed + configsPassed) / total) * 100);
      this.healthState.lastCheck = new Date();
      this.healthState.checkCount++;
      this.healthState.issuesFound += issues.length;
      this.healthState.issuesFixed += fixes.length;
      this.healthState.lastErrors = issues.slice(-10);
      
      // Track consecutive failures
      if (issues.length > 0) {
        this.healthState.consecutiveFailures++;
      } else {
        this.healthState.consecutiveFailures = 0;
      }
      
      // ========== LOG RESULTS ==========
      const duration = Date.now() - startTime;
      
      if (issues.length === 0) {
        log(`[HEALTH CHECK] ✅ ALL SYSTEMS OPERATIONAL (${duration}ms) - Health: ${this.healthState.healthScore}%`, "worker");
      } else {
        log(`[HEALTH CHECK] ⚠️ Found ${issues.length} issues:`, "worker");
        issues.forEach(issue => log(`  - ${issue}`, "worker"));
        if (fixes.length > 0) {
          log(`[HEALTH CHECK] 🔧 Applied ${fixes.length} fixes:`, "worker");
          fixes.forEach(fix => log(`  - ${fix}`, "worker"));
        }
      }
      
      // ========== CRITICAL FAILURE - FULL RECOVERY ==========
      if (this.healthState.consecutiveFailures >= 5) {
        log("[HEALTH CHECK] 🚨 CRITICAL: Max failures reached - initiating full recovery!", "worker");
        await this.performFullSystemRecovery();
      }
      
    } catch (error: any) {
      log(`[HEALTH CHECK] ❌ Error: ${error.message}`, "worker");
      this.healthState.lastErrors.push(error.message);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 🐕 WATCHDOG - Ensures health checks are running
  // ═══════════════════════════════════════════════════════════════════════════
  private startWatchdog() {
    this.watchdogInterval = setInterval(() => {
      if (!this.isRunning) return;
      
      // Check if health checks are stale
      if (this.healthState.lastCheck) {
        const timeSinceLastCheck = Date.now() - this.healthState.lastCheck.getTime();
        if (timeSinceLastCheck > 120000) { // 2 minutes
          log("[WATCHDOG] ⚠️ Health checks stale - forcing check...", "worker");
          this.performComprehensiveHealthCheck();
        }
      }
      
      // Log watchdog status
      log(`[WATCHDOG] 🐕 Active | Health: ${this.healthState.healthScore}% | Uptime: ${this.getUptime()}`, "worker");
      
    }, this.config.watchdogInterval);
  }

  private getUptime(): string {
    if (!this.startTime) return "0s";
    const seconds = Math.floor((Date.now() - this.startTime.getTime()) / 1000);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}h ${minutes}m ${secs}s`;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 🧪 ENGINE TESTS
  // ═══════════════════════════════════════════════════════════════════════════
  private async testWolfPack(): Promise<{ passed: boolean; error?: string }> {
    try {
      const stats = wolfPack.getStats();
      if (!stats.isRunning) {
        return { passed: false, error: "Not running" };
      }
      if (!stats.engines || stats.engines.length === 0) {
        return { passed: false, error: "No engines" };
      }
      return { passed: true };
    } catch (error: any) {
      return { passed: false, error: error.message };
    }
  }

  private async testAIModels(): Promise<{ passed: boolean; error?: string }> {
    try {
      const response = await fetch("http://localhost:5000/api/trading-engine/status");
      const status = await response.json();
      if (status.modelsCount < 8) {
        return { passed: false, error: `Only ${status.modelsCount} models active` };
      }
      return { passed: true };
    } catch (error: any) {
      return { passed: false, error: error.message };
    }
  }

  private async testGateioConnection(): Promise<{ passed: boolean; error?: string }> {
    try {
      const { fetchGateMarketData } = await import('./gateio');
      const data = await fetchGateMarketData('BTC_USDT');
      // Check if data was returned (data has currentPrice property)
      if (!data) {
        return { passed: false, error: "No market data returned" };
      }
      return { passed: true };
    } catch (error: any) {
      return { passed: false, error: error.message };
    }
  }

  private async testAutoPilot(): Promise<{ passed: boolean; error?: string }> {
    try {
      const response = await fetch("http://localhost:5000/api/auto-pilot/status");
      const status = await response.json();
      if (!status.running) {
        return { passed: false, error: "Not running" };
      }
      return { passed: true };
    } catch (error: any) {
      return { passed: false, error: error.message };
    }
  }

  private async testTradingEngine(): Promise<{ passed: boolean; error?: string }> {
    try {
      const response = await fetch("http://localhost:5000/api/trading-engine/status");
      const status = await response.json();
      if (!status.isRunning) {
        return { passed: false, error: "Not running" };
      }
      return { passed: true };
    } catch (error: any) {
      return { passed: false, error: error.message };
    }
  }

  private async testProtectionSystem(): Promise<{ passed: boolean; error?: string }> {
    try {
      const godsStatus = wolfPack.getGodsModeStatus();
      if (!godsStatus.unbreakableMode) {
        return { passed: false, error: "Unbreakable mode disabled" };
      }
      return { passed: true };
    } catch (error: any) {
      return { passed: false, error: error.message };
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ✅ CONFIG VERIFICATION
  // ═══════════════════════════════════════════════════════════════════════════
  private async verifyTradingConfig(): Promise<{ valid: boolean; error?: string }> {
    try {
      const stats = wolfPack.getStats();
      const config = stats.config;
      if (!config) return { valid: false, error: "Config missing" };
      if (config.totalBudget <= 0) return { valid: false, error: "Invalid budget" };
      if (!config.pairs || config.pairs.length === 0) return { valid: false, error: "No pairs" };
      return { valid: true };
    } catch (error: any) {
      return { valid: false, error: error.message };
    }
  }

  private async verifyBalanceProtection(): Promise<{ valid: boolean; error?: string }> {
    try {
      const stats = wolfPack.getStats();
      if (!stats.autoStopProtection) return { valid: false, error: "Protection missing" };
      if (!stats.autoStopProtection.tieredProtection) return { valid: false, error: "Tiers missing" };
      return { valid: true };
    } catch (error: any) {
      return { valid: false, error: error.message };
    }
  }

  private async verifyRiskSettings(): Promise<{ valid: boolean; error?: string }> {
    try {
      const stats = wolfPack.getStats();
      const config = stats.config;
      if (config.maxLeverage > 20) return { valid: false, error: "Leverage too high" };
      if (config.riskPerTradePercent > 10) return { valid: false, error: "Risk too high" };
      return { valid: true };
    } catch (error: any) {
      return { valid: false, error: error.message };
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 🔧 AUTO-RECOVERY FUNCTIONS
  // ═══════════════════════════════════════════════════════════════════════════
  private async recoverWolfPack(): Promise<boolean> {
    try {
      log("[RECOVERY] 🔧 Restarting Wolf Pack...", "worker");
      try { wolfPack.stop(); } catch (e) {}
      await new Promise(resolve => setTimeout(resolve, 2000));
      wolfPack.start();
      await new Promise(resolve => setTimeout(resolve, 2000));
      this.healthState.crashRecoveries++;
      return wolfPack.getStats().isRunning;
    } catch (error) {
      return false;
    }
  }

  private async recoverAutoPilot(): Promise<boolean> {
    try {
      log("[RECOVERY] 🔧 Restarting Auto-Pilot...", "worker");
      await fetch("http://localhost:5000/api/auto-pilot/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: this.config.mode,
          coins: this.config.coins,
          amountPerTrade: this.config.amountPerTrade,
          maxLeverage: this.config.maxLeverage
        })
      });
      this.healthState.crashRecoveries++;
      return true;
    } catch (error) {
      return false;
    }
  }

  private async recoverTradingEngine(): Promise<boolean> {
    try {
      log("[RECOVERY] 🔧 Restarting Trading Engine...", "worker");
      await fetch("http://localhost:5000/api/trading-engine/start", { method: "POST" });
      this.healthState.crashRecoveries++;
      return true;
    } catch (error) {
      return false;
    }
  }

  private async enableUnbreakableMode(): Promise<boolean> {
    try {
      log("[RECOVERY] 🛡️ Enabling Unbreakable Mode...", "worker");
      // Unbreakable mode is always enabled by default in the Gods Mode system
      // Just verify it's active through getGodsModeStatus
      const godsStatus = wolfPack.getGodsModeStatus();
      return godsStatus.unbreakableMode === true;
    } catch (error) {
      return false;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 🚨 FULL SYSTEM RECOVERY
  // ═══════════════════════════════════════════════════════════════════════════
  private async performFullSystemRecovery(): Promise<void> {
    log("\n[RECOVERY] 🔱 FULL SYSTEM RECOVERY INITIATED", "worker");
    
    try {
      // 1. Stop everything
      log("[RECOVERY] Step 1: Stopping all engines...", "worker");
      try { wolfPack.stop(); } catch (e) {}
      
      // 2. Wait for clean state
      log("[RECOVERY] Step 2: Waiting for clean state...", "worker");
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      // 3. Restart Wolf Pack
      log("[RECOVERY] Step 3: Restarting Wolf Pack...", "worker");
      wolfPack.start();
      
      // 4. Verify protection (Unbreakable mode is always enabled by default)
      log("[RECOVERY] Step 4: Verifying protection...", "worker");
      const godsStatus = wolfPack.getGodsModeStatus();
      log(`[RECOVERY] Gods Mode Status: Unbreakable=${godsStatus.unbreakableMode}`, "worker");
      
      // 5. Restart Auto-Pilot
      log("[RECOVERY] Step 5: Restarting Auto-Pilot...", "worker");
      await fetch("http://localhost:5000/api/auto-pilot/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: this.config.mode,
          coins: this.config.coins,
          amountPerTrade: this.config.amountPerTrade,
          maxLeverage: this.config.maxLeverage
        })
      });
      
      // 6. Restart Trading Engine
      log("[RECOVERY] Step 6: Restarting Trading Engine...", "worker");
      await fetch("http://localhost:5000/api/trading-engine/start", { method: "POST" });
      
      // 7. Verify recovery
      log("[RECOVERY] Step 7: Verifying recovery...", "worker");
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      const stats = wolfPack.getStats();
      if (stats.isRunning) {
        log("[RECOVERY] ✅ FULL SYSTEM RECOVERY SUCCESSFUL", "worker");
        this.healthState.crashRecoveries++;
        this.healthState.consecutiveFailures = 0;
      } else {
        log("[RECOVERY] ⚠️ Recovery incomplete", "worker");
      }
      
    } catch (error: any) {
      log(`[RECOVERY] ❌ Recovery failed: ${error.message}`, "worker");
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 🔧 PUBLIC METHODS
  // ═══════════════════════════════════════════════════════════════════════════
  updateConfig(newConfig: Partial<BackgroundWorkerConfig>) {
    this.config = { ...this.config, ...newConfig };
    log(`⚙️ Worker config updated: ${JSON.stringify(newConfig)}`, "worker");
  }

  triggerHealthCheck(): Promise<void> {
    return this.performComprehensiveHealthCheck() as any;
  }

  triggerFullRecovery(): Promise<void> {
    return this.performFullSystemRecovery();
  }

  getHealthState(): HealthCheckState {
    return { ...this.healthState };
  }
}

export const backgroundWorker = new BackgroundWorker();

export async function startBackgroundWorker(): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, 3000));
  
  log("═══════════════════════════════════════════════════════════", "worker");
  log("   🔱 GODS LEVEL 24/7 UNCRASHABLE BACKGROUND WORKER        ", "worker");
  log("   Health Check: Every 60 seconds                          ", "worker");
  log("   Watchdog: Every 30 seconds                               ", "worker");
  log("   Auto-Recovery: ENABLED                                   ", "worker");
  log("═══════════════════════════════════════════════════════════", "worker");
  
  const result = await backgroundWorker.start();
  log(result.message, "worker");
}
