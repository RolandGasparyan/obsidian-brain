/**
 * AUTO-WITHDRAW SYSTEM - TURBO FAST Profit Protection
 * 
 * Automatically withdraws profits to BSC wallet INSTANTLY after every $100 profit.
 * Ultra-fast monitoring with 15-second intervals.
 * 
 * BSC Wallet: 0xa5df89870410335b41beac66508f7dfdc9491e46
 */

import { authenticatedRequest } from "./gateio";

interface WithdrawalRecord {
  amount: number;
  address: string;
  timestamp: string;
  balanceBefore: number;
  balanceAfter: number;
  status: "SUCCESS" | "FAILED" | "PENDING";
  txId: string;
  chain: string;
  error?: string;
}

interface WithdrawManagerConfig {
  coldWalletAddress: string;
  withdrawThreshold: number;
  startingBalance: number;
  chain: "BSC" | "ERC20" | "TRX";
  enabled: boolean;
  autoStart: boolean;
  monitorIntervalMs: number;
}

class AutoWithdrawManager {
  private config: WithdrawManagerConfig;
  private totalWithdrawn: number = 0;
  private withdrawalHistory: WithdrawalRecord[] = [];
  private lastWithdrawalTime: Date | null = null;
  private isProcessing: boolean = false;
  private monitorInterval: NodeJS.Timeout | null = null;

  constructor(config: Partial<WithdrawManagerConfig> = {}) {
    this.config = {
      coldWalletAddress: config.coldWalletAddress || "0xa5df89870410335b41beac66508f7dfdc9491e46",
      withdrawThreshold: config.withdrawThreshold || 100.0,
      startingBalance: config.startingBalance || 692.0,
      chain: config.chain || "BSC",
      enabled: config.enabled ?? true,
      autoStart: config.autoStart ?? true,
      monitorIntervalMs: config.monitorIntervalMs || 15000, // 15 seconds - TURBO FAST
    };

    console.log("\n⚡ TURBO AUTO-WITHDRAW System initialized");
    console.log(`   BSC Wallet: ${this.config.coldWalletAddress}`);
    console.log(`   Threshold: $${this.config.withdrawThreshold.toFixed(2)}`);
    console.log(`   Starting Balance: $${this.config.startingBalance.toFixed(2)}`);
    console.log(`   Chain: ${this.config.chain} (FAST)`);
    console.log(`   Monitor Interval: ${this.config.monitorIntervalMs / 1000}s`);
    console.log(`   Enabled: ${this.config.enabled}`);
    
    // Auto-start monitoring if enabled
    if (this.config.autoStart && this.config.enabled) {
      setTimeout(() => {
        this.startMonitoring(this.config.monitorIntervalMs);
      }, 5000);
    }
  }

  async quickTransfer(amount: number): Promise<WithdrawalRecord> {
    console.log(`\n⚡ QUICK TRANSFER: $${amount} → BSC Wallet`);
    
    const currentBalance = await this.getSpotBalance();
    
    if (amount > currentBalance) {
      throw new Error(`Insufficient balance: $${currentBalance.toFixed(2)} available`);
    }
    
    return this.executeWithdrawal(amount, currentBalance);
  }

  async checkAndWithdraw(): Promise<WithdrawalRecord | null> {
    if (!this.config.enabled || this.isProcessing) {
      return null;
    }

    const currentBalance = await this.getSpotBalance();
    const totalProfit = currentBalance - this.config.startingBalance;
    const netProfit = totalProfit - this.totalWithdrawn;

    if (netProfit >= this.config.withdrawThreshold) {
      const numIncrements = Math.floor(netProfit / this.config.withdrawThreshold);
      const withdrawAmount = numIncrements * this.config.withdrawThreshold;

      console.log(`\n💰 AUTO-WITHDRAW TRIGGERED: $${withdrawAmount} profit detected`);
      return await this.executeWithdrawal(withdrawAmount, currentBalance);
    }

    return null;
  }

  private async getSpotBalance(): Promise<number> {
    try {
      const result = await authenticatedRequest("GET", "/spot/accounts");
      const usdtAccount = Array.isArray(result) 
        ? result.find((a: any) => a.currency === "USDT")
        : null;
      return parseFloat(usdtAccount?.available || "0");
    } catch (error) {
      console.log("[TURBO-WITHDRAW] Could not fetch spot balance");
      return 0;
    }
  }

  private async executeWithdrawal(amount: number, currentBalance: number): Promise<WithdrawalRecord> {
    this.isProcessing = true;

    console.log("\n" + "⚡".repeat(40));
    console.log("💰 TURBO WITHDRAWAL EXECUTING");
    console.log("⚡".repeat(40));
    console.log(`Amount:      $${amount.toFixed(2)} USDT`);
    console.log(`To Address:  ${this.config.coldWalletAddress}`);
    console.log(`Chain:       ${this.config.chain} (FAST)`);
    console.log("⚡".repeat(40));

    let withdrawalRecord: WithdrawalRecord;

    try {
      const result = await this.callGateIOWithdrawal(amount);
      
      withdrawalRecord = {
        amount,
        address: this.config.coldWalletAddress,
        timestamp: new Date().toISOString(),
        balanceBefore: currentBalance,
        balanceAfter: currentBalance - amount,
        status: result.status,
        txId: result.txId || `TX_${Date.now()}`,
        chain: this.config.chain,
      };

      if (result.status === "SUCCESS" || result.status === "PENDING") {
        this.totalWithdrawn += amount;
        this.lastWithdrawalTime = new Date();
        console.log(`\n✅ WITHDRAWAL SENT!`);
        console.log(`   Amount: $${amount.toFixed(2)}`);
        console.log(`   TX ID: ${withdrawalRecord.txId}`);
        console.log(`   Total Withdrawn: $${this.totalWithdrawn.toFixed(2)}`);
      } else {
        console.log(`\n❌ WITHDRAWAL FAILED: ${result.error || "Unknown error"}`);
        withdrawalRecord.error = result.error;
      }
    } catch (error: any) {
      console.error(`\n❌ WITHDRAWAL ERROR: ${error.message}`);
      withdrawalRecord = {
        amount,
        address: this.config.coldWalletAddress,
        timestamp: new Date().toISOString(),
        balanceBefore: currentBalance,
        balanceAfter: currentBalance,
        status: "FAILED",
        txId: `FAILED_${Date.now()}`,
        chain: this.config.chain,
        error: error.message,
      };
    }

    this.withdrawalHistory.push(withdrawalRecord);
    console.log("⚡".repeat(40) + "\n");

    this.isProcessing = false;
    return withdrawalRecord;
  }

  private async callGateIOWithdrawal(amount: number): Promise<{ status: "SUCCESS" | "FAILED" | "PENDING"; txId?: string; error?: string }> {
    try {
      // Use /wallet/withdrawals endpoint with authenticated request
      const result = await authenticatedRequest("POST", "/wallet/withdrawals", {
        currency: "USDT",
        amount: amount.toString(),
        address: this.config.coldWalletAddress,
        chain: this.config.chain,
      });

      console.log(`[TURBO-WITHDRAW] Gate.io response:`, JSON.stringify(result).slice(0, 200));

      return {
        status: result.status === "DONE" ? "SUCCESS" : "PENDING",
        txId: result.txid || result.id || result.withdraw_order_id,
      };
    } catch (error: any) {
      console.log(`[TURBO-WITHDRAW] API Error: ${error.message}`);
      return {
        status: "FAILED",
        error: error.message,
      };
    }
  }

  startMonitoring(intervalMs: number = 15000): void {
    if (this.monitorInterval) {
      clearInterval(this.monitorInterval);
    }

    console.log(`\n🔍 TURBO Auto-Withdraw Monitor STARTED (every ${intervalMs / 1000}s)`);

    this.monitorInterval = setInterval(async () => {
      try {
        const result = await this.checkAndWithdraw();
        
        if (result && result.status !== "FAILED") {
          console.log(`\n✅ PROFIT SECURED: $${result.amount.toFixed(2)} → BSC Wallet`);
        }
      } catch (error: any) {
        console.error(`❌ Monitor error: ${error.message}`);
      }
    }, intervalMs);
  }

  stopMonitoring(): void {
    if (this.monitorInterval) {
      clearInterval(this.monitorInterval);
      this.monitorInterval = null;
      console.log("🛑 TURBO Auto-Withdraw Monitor stopped");
    }
  }

  getStatus(): object {
    return {
      enabled: this.config.enabled,
      coldWalletAddress: this.config.coldWalletAddress,
      withdrawThreshold: this.config.withdrawThreshold,
      startingBalance: this.config.startingBalance,
      chain: this.config.chain,
      totalWithdrawn: this.totalWithdrawn,
      withdrawalCount: this.withdrawalHistory.length,
      lastWithdrawal: this.lastWithdrawalTime?.toISOString() || null,
      isMonitoring: !!this.monitorInterval,
      isProcessing: this.isProcessing,
      monitorIntervalMs: this.config.monitorIntervalMs,
      mode: "TURBO_FAST",
    };
  }

  getWithdrawalHistory(): WithdrawalRecord[] {
    return [...this.withdrawalHistory];
  }

  setEnabled(enabled: boolean): void {
    this.config.enabled = enabled;
    console.log(`TURBO Auto-Withdraw ${enabled ? "ENABLED ⚡" : "DISABLED"}`);
    
    if (enabled && !this.monitorInterval) {
      this.startMonitoring(this.config.monitorIntervalMs);
    } else if (!enabled && this.monitorInterval) {
      this.stopMonitoring();
    }
  }

  updateConfig(updates: Partial<WithdrawManagerConfig>): void {
    if (updates.coldWalletAddress) this.config.coldWalletAddress = updates.coldWalletAddress;
    if (updates.withdrawThreshold) this.config.withdrawThreshold = updates.withdrawThreshold;
    if (updates.startingBalance) this.config.startingBalance = updates.startingBalance;
    if (updates.chain) this.config.chain = updates.chain;
    if (updates.enabled !== undefined) this.config.enabled = updates.enabled;
    if (updates.monitorIntervalMs) {
      this.config.monitorIntervalMs = updates.monitorIntervalMs;
      if (this.monitorInterval) {
        this.startMonitoring(updates.monitorIntervalMs);
      }
    }
    
    console.log("TURBO Auto-Withdraw config updated:", this.config);
  }

  async manualWithdraw(amount: number): Promise<WithdrawalRecord> {
    const currentBalance = await this.getSpotBalance();
    
    if (amount > currentBalance * 0.95) {
      throw new Error(`Cannot withdraw $${amount} - exceeds 95% of balance $${currentBalance.toFixed(2)}`);
    }
    if (amount < 1) {
      throw new Error(`Minimum withdrawal is $1`);
    }
    if (amount > 50000) {
      throw new Error(`Maximum single withdrawal is $50,000`);
    }
    
    return this.executeWithdrawal(amount, currentBalance);
  }
}

export const autoWithdrawManager = new AutoWithdrawManager({
  coldWalletAddress: "0xa5df89870410335b41beac66508f7dfdc9491e46",
  withdrawThreshold: 100.0,
  startingBalance: 692.0,
  chain: "BSC",
  enabled: true,
  autoStart: true,
  monitorIntervalMs: 15000, // 15 seconds - TURBO FAST
});

export { AutoWithdrawManager };
