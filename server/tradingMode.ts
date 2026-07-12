/**
 * TRADING MODE CONFIGURATION - SPOT vs FUTURES
 * 
 * SPOT TRADING:
 * - Buy/sell actual crypto
 * - No leverage
 * - Lower risk
 * - Can only profit from price increases (LONG only)
 * 
 * FUTURES TRADING:
 * - Trade contracts (not actual crypto)
 * - Leverage available (2x-125x)
 * - Higher risk
 * - Can profit from both LONG and SHORT
 */

export enum TradingMode {
  SPOT = "spot",
  FUTURES = "futures",
}

export enum FuturesType {
  USDT_PERPETUAL = "usdt_perpetual",
  COIN_PERPETUAL = "coin_perpetual",
  DELIVERY = "delivery",
}

export enum MarginMode {
  ISOLATED = "isolated",
  CROSS = "cross",
}

export interface TradingModeConfig {
  mode: TradingMode;
  futuresType: FuturesType;
  maxLeverage: number;
  allowShort: boolean;
  allowLong: boolean;
  marginMode: MarginMode;
  autoAddMargin: boolean;
  liquidationBuffer: number;
}

const PRESET_CONFIGS: Record<string, TradingModeConfig> = {
  spot_safe: {
    mode: TradingMode.SPOT,
    futuresType: FuturesType.USDT_PERPETUAL,
    maxLeverage: 1,
    allowShort: false,
    allowLong: true,
    marginMode: MarginMode.ISOLATED,
    autoAddMargin: false,
    liquidationBuffer: 0,
  },

  futures_conservative: {
    mode: TradingMode.FUTURES,
    futuresType: FuturesType.USDT_PERPETUAL,
    maxLeverage: 5,
    allowShort: true,
    allowLong: true,
    marginMode: MarginMode.ISOLATED,
    autoAddMargin: false,
    liquidationBuffer: 0.30,
  },

  futures_moderate: {
    mode: TradingMode.FUTURES,
    futuresType: FuturesType.USDT_PERPETUAL,
    maxLeverage: 10,
    allowShort: true,
    allowLong: true,
    marginMode: MarginMode.ISOLATED,
    autoAddMargin: false,
    liquidationBuffer: 0.20,
  },

  futures_aggressive: {
    mode: TradingMode.FUTURES,
    futuresType: FuturesType.USDT_PERPETUAL,
    maxLeverage: 20,
    allowShort: true,
    allowLong: true,
    marginMode: MarginMode.ISOLATED,
    autoAddMargin: false,
    liquidationBuffer: 0.15,
  },

  futures_shorts_only: {
    mode: TradingMode.FUTURES,
    futuresType: FuturesType.USDT_PERPETUAL,
    maxLeverage: 10,
    allowShort: true,
    allowLong: false,
    marginMode: MarginMode.ISOLATED,
    autoAddMargin: false,
    liquidationBuffer: 0.20,
  },

  futures_longs_only: {
    mode: TradingMode.FUTURES,
    futuresType: FuturesType.USDT_PERPETUAL,
    maxLeverage: 10,
    allowShort: false,
    allowLong: true,
    marginMode: MarginMode.ISOLATED,
    autoAddMargin: false,
    liquidationBuffer: 0.20,
  },
};

class TradingModeManager {
  private config: TradingModeConfig;
  private presetName: string;

  constructor(preset: string = "futures_shorts_only") {
    this.presetName = preset;
    this.config = PRESET_CONFIGS[preset] ? { ...PRESET_CONFIGS[preset] } : { ...PRESET_CONFIGS.futures_moderate };
    this.printConfig();
  }

  private printConfig(): void {
    console.log("\n" + "=".repeat(80));
    console.log("⚙️  TRADING MODE CONFIGURATION");
    console.log("=".repeat(80));
    console.log(`Preset: ${this.presetName.toUpperCase()}`);
    console.log(`Mode: ${this.config.mode.toUpperCase()}`);

    if (this.config.mode === TradingMode.SPOT) {
      console.log("\n📊 SPOT TRADING");
      console.log("   ✅ Buy/sell actual crypto");
      console.log("   ✅ No leverage (1x only)");
      console.log("   ✅ Lower risk");
      console.log("   ✅ Can only LONG (profit from price increases)");
      console.log("   ❌ Cannot SHORT (cannot profit from price decreases)");
    } else {
      console.log(`\n🚀 FUTURES TRADING (${this.config.futuresType.toUpperCase()})`);
      console.log(`   ✅ Leverage: ${this.config.maxLeverage}x`);
      console.log(`   ✅ Margin: ${this.config.marginMode.toUpperCase()} (${this.config.marginMode === MarginMode.ISOLATED ? "safer" : "more capital efficient"})`);
      
      const directions = [];
      if (this.config.allowLong) directions.push("LONG");
      if (this.config.allowShort) directions.push("SHORT");
      console.log(`   ✅ Directions: ${directions.join(" + ") || "NONE"}`);
      console.log(`   ✅ Liquidation Buffer: ${(this.config.liquidationBuffer * 100).toFixed(0)}%`);
      
      if (this.config.maxLeverage >= 20) {
        console.log("   🔴 RISK LEVEL: EXTREME");
      } else if (this.config.maxLeverage >= 10) {
        console.log("   🟠 RISK LEVEL: HIGH");
      } else if (this.config.maxLeverage >= 5) {
        console.log("   🟡 RISK LEVEL: MEDIUM");
      } else {
        console.log("   🟢 RISK LEVEL: LOW");
      }
    }

    console.log("=".repeat(80) + "\n");
  }

  canTradeDirection(direction: string): boolean {
    const dir = direction.toUpperCase();
    if (dir === "LONG") {
      return this.config.allowLong;
    } else if (dir === "SHORT") {
      return this.config.mode === TradingMode.FUTURES && this.config.allowShort;
    }
    return false;
  }

  getMaxLeverage(): number {
    return this.config.mode === TradingMode.FUTURES ? this.config.maxLeverage : 1;
  }

  isFutures(): boolean {
    return this.config.mode === TradingMode.FUTURES;
  }

  isSpot(): boolean {
    return this.config.mode === TradingMode.SPOT;
  }

  calculatePositionValue(positionSize: number, leverage?: number): number {
    if (this.config.mode === TradingMode.SPOT) {
      return positionSize;
    }
    const lev = leverage || this.config.maxLeverage;
    return positionSize * lev;
  }

  calculateLiquidationPrice(entryPrice: number, leverage: number, direction: string): number {
    if (this.config.mode === TradingMode.SPOT) {
      return 0;
    }

    const dir = direction.toUpperCase();
    if (dir === "LONG") {
      return entryPrice * (1 - 1 / leverage);
    } else {
      return entryPrice * (1 + 1 / leverage);
    }
  }

  getRiskWarning(): string {
    if (this.config.mode === TradingMode.SPOT) {
      return "⚠️ SPOT TRADING: Lower risk, can only profit from price increases (LONG only)";
    }

    const leverage = this.config.maxLeverage;
    let riskLevel: string;
    let emoji: string;

    if (leverage >= 20) {
      riskLevel = "EXTREME";
      emoji = "🔴";
    } else if (leverage >= 10) {
      riskLevel = "HIGH";
      emoji = "🟠";
    } else if (leverage >= 5) {
      riskLevel = "MEDIUM";
      emoji = "🟡";
    } else {
      riskLevel = "LOW";
      emoji = "🟢";
    }

    return `${emoji} FUTURES TRADING (${leverage}x): ${riskLevel} RISK - Can be liquidated if price moves against you`;
  }

  getStatus(): object {
    return {
      preset: this.presetName,
      mode: this.config.mode,
      futuresType: this.config.futuresType,
      maxLeverage: this.config.maxLeverage,
      allowShort: this.config.allowShort,
      allowLong: this.config.allowLong,
      marginMode: this.config.marginMode,
      autoAddMargin: this.config.autoAddMargin,
      liquidationBuffer: this.config.liquidationBuffer,
      riskWarning: this.getRiskWarning(),
      isFutures: this.isFutures(),
      isSpot: this.isSpot(),
    };
  }

  setPreset(preset: string): void {
    if (PRESET_CONFIGS[preset]) {
      this.presetName = preset;
      this.config = { ...PRESET_CONFIGS[preset] };
      this.printConfig();
    } else {
      console.error(`Unknown preset: ${preset}. Available: ${Object.keys(PRESET_CONFIGS).join(", ")}`);
    }
  }

  updateConfig(updates: Partial<TradingModeConfig>): void {
    Object.assign(this.config, updates);
    this.presetName = "custom";
    console.log("Trading mode config updated:", this.config);
  }

  getAvailablePresets(): string[] {
    return Object.keys(PRESET_CONFIGS);
  }

  getPresetConfig(preset: string): TradingModeConfig | null {
    return PRESET_CONFIGS[preset] ? { ...PRESET_CONFIGS[preset] } : null;
  }
}

function compareModes(): string {
  return `
╔════════════════════╦═══════════════════════╦═══════════════════════════╗
║ Feature            ║ SPOT Trading          ║ FUTURES Trading           ║
╠════════════════════╬═══════════════════════╬═══════════════════════════╣
║ Asset              ║ Actual crypto         ║ Contracts                 ║
║ Leverage           ║ None (1x)             ║ 1x-125x                   ║
║ Risk               ║ Lower                 ║ Higher                    ║
║ Profit Speed       ║ Slower                ║ Faster                    ║
║ Liquidation Risk   ║ None                  ║ Yes                       ║
║ Directions         ║ LONG only             ║ LONG + SHORT              ║
║ Profit from Rise   ║ Yes                   ║ Yes (LONG)                ║
║ Profit from Fall   ║ No                    ║ Yes (SHORT)               ║
║ Margin Required    ║ Full amount           ║ Partial (margin)          ║
║ Best For           ║ HODLing, low risk     ║ Active trading            ║
╚════════════════════╩═══════════════════════╩═══════════════════════════╝

💡 RECOMMENDATION:
   • Use SPOT: Lower risk, LONG-only, slower profits, own actual crypto
   • Use FUTURES: Higher risk, LONG+SHORT, faster profits, can use leverage
`;
}

export const tradingModeManager = new TradingModeManager("futures_shorts_only");

export { TradingModeManager, PRESET_CONFIGS, compareModes };
