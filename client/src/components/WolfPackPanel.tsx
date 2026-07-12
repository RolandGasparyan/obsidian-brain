import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Activity,
  Play,
  Square,
  Zap,
  Target,
  CheckCircle2,
  Shield,
  AlertTriangle,
  TrendingUp,
  BarChart3,
  RefreshCw
} from "lucide-react";
import { apiRequest, queryClient } from "@/lib/queryClient";

interface StrategyStats {
  wins: number;
  losses: number;
  winRate: number;
  isActive: boolean;
}

interface UnbreakableState {
  consecutiveLosses: number;
  peakBudget: number;
  dynamicRiskPercent: number;
  strategyStats: Record<string, StrategyStats>;
  dailyPnl: number;
  dailyStartBudget: number;
  pausedUntil: string | null;
  pauseReason: string | null;
}

interface ActiveTrade {
  symbol: string;
  direction: string;
  entryPrice: number;
  currentStopLoss: number;
  tp1: number;
  tp2: number;
  tp3: number;
  positionSizeUsd: number;
  remainingPositionSizeUsd: number;
  breakevenSet: boolean;
  trailingActivated: boolean;
  pnlR: number;
}

interface WolfEngineState {
  pair: string;
  status: "ACTIVE" | "HALTED" | "ERROR" | "IDLE" | "PAUSED";
  budget: number;
  pnl: number;
  tradeCount: number;
  winCount: number;
  lossCount: number;
  currentStrategy: string;
  lastTradeWasLoss: boolean;
  doublingMultiplier: number;
  activeTrade: ActiveTrade | null;
  lastUpdate: string;
  unbreakable?: UnbreakableState;
}

interface WolfPackStats {
  isRunning: boolean;
  totalPnl: number;
  totalTrades: number;
  totalWins: number;
  totalLosses: number;
  winRate: number;
  engines: WolfEngineState[];
  config: {
    totalBudget: number;
    pairs: string[];
    riskPerTradePercent: number;
    maxLeverage: number;
    cycleIntervalMs: number;
    tradingDirection: string;
    unbreakable?: {
      dailyLossLimitPercent: number;
      consecutiveLossLimit: number;
      peakDrawdownLimitPercent: number;
      maxPortfolioExposurePercent: number;
      strategyPerformanceThreshold: number;
    };
  };
  circuitBreakerEvents?: string[];
}

export function WolfPackPanel() {
  const { data, isLoading } = useQuery<WolfPackStats>({
    queryKey: ["/api/wolf-pack/status"],
    refetchInterval: 2000
  });

  const startMutation = useMutation({
    mutationFn: () => apiRequest("/api/wolf-pack/start", "POST"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/wolf-pack/status"] });
    }
  });

  const stopMutation = useMutation({
    mutationFn: () => apiRequest("/api/wolf-pack/stop", "POST"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/wolf-pack/status"] });
    }
  });

  if (isLoading || !data) {
    return (
      <Card data-testid="card-wolfpack-loading">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-5 w-5 text-amber-500" />
            Wolf Pack Loading...
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const pausedEngines = data.engines.filter(e => e.status === "PAUSED").length;
  const haltedEngines = data.engines.filter(e => e.status === "HALTED").length;

  return (
    <div className="space-y-4" data-testid="panel-wolfpack">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-base">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-amber-500" />
              Unbreakable Gods Mode
            </div>
            <div className="flex items-center gap-2">
              <Badge 
                variant="outline" 
                className={data.isRunning 
                  ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30" 
                  : "bg-muted text-muted-foreground"
                }
                data-testid="badge-wolfpack-status"
              >
                {data.isRunning ? "RUNNING" : "STOPPED"}
              </Badge>
              {pausedEngines > 0 && (
                <Badge variant="outline" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/30" data-testid="badge-wolfpack-paused">
                  {pausedEngines} PAUSED
                </Badge>
              )}
              {haltedEngines > 0 && (
                <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/30" data-testid="badge-wolfpack-halted">
                  {haltedEngines} HALTED
                </Badge>
              )}
              {data.isRunning ? (
                <Button 
                  size="sm" 
                  variant="destructive"
                  onClick={() => stopMutation.mutate()}
                  disabled={stopMutation.isPending}
                  data-testid="button-stop-wolfpack"
                >
                  <Square className="h-4 w-4 mr-1" />
                  Stop
                </Button>
              ) : (
                <Button 
                  size="sm"
                  onClick={() => startMutation.mutate()}
                  disabled={startMutation.isPending}
                  data-testid="button-start-wolfpack"
                >
                  <Play className="h-4 w-4 mr-1" />
                  Start
                </Button>
              )}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-4 gap-3">
            <div className="p-3 rounded bg-muted/50 text-center" data-testid="stat-wolfpack-pnl">
              <div className="text-xs text-muted-foreground">Total PnL</div>
              <div className={`text-lg font-bold ${data.totalPnl >= 0 ? "text-emerald-500" : "text-red-500"}`} data-testid="text-wolfpack-pnl-value">
                ${data.totalPnl.toFixed(2)}
              </div>
            </div>
            <div className="p-3 rounded bg-muted/50 text-center" data-testid="stat-wolfpack-trades">
              <div className="text-xs text-muted-foreground">Total Trades</div>
              <div className="text-lg font-bold" data-testid="text-wolfpack-trades-value">{data.totalTrades}</div>
            </div>
            <div className="p-3 rounded bg-muted/50 text-center" data-testid="stat-wolfpack-winrate">
              <div className="text-xs text-muted-foreground">Win Rate</div>
              <div className="text-lg font-bold" data-testid="text-wolfpack-winrate-value">{data.winRate.toFixed(1)}%</div>
            </div>
            <div className="p-3 rounded bg-muted/50 text-center" data-testid="stat-wolfpack-active">
              <div className="text-xs text-muted-foreground">Active Engines</div>
              <div className="text-lg font-bold" data-testid="text-wolfpack-active-value">
                {data.engines.filter(e => e.status === "ACTIVE").length}/{data.engines.length}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-500" />
              Engine Status
            </h3>
            {data.engines.map((engine) => (
              <div
                key={engine.pair}
                className={`p-3 rounded border ${
                  engine.status === "ACTIVE" 
                    ? "border-emerald-500/30 bg-emerald-500/5" 
                    : engine.status === "HALTED"
                    ? "border-red-500/30 bg-red-500/5"
                    : engine.status === "PAUSED"
                    ? "border-yellow-500/30 bg-yellow-500/5"
                    : "border-muted bg-muted/30"
                }`}
                data-testid={`engine-${engine.pair}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium" data-testid={`text-engine-pair-${engine.pair}`}>{engine.pair.replace("_", "/")}</span>
                    <Badge variant="outline" className="text-xs" data-testid={`badge-engine-strategy-${engine.pair}`}>
                      {engine.currentStrategy}
                    </Badge>
                    {engine.doublingMultiplier > 1 && (
                      <Badge variant="outline" className="text-xs bg-orange-500/10 text-orange-500 border-orange-500/30" data-testid={`badge-engine-multiplier-${engine.pair}`}>
                        {engine.doublingMultiplier}x
                      </Badge>
                    )}
                    {engine.unbreakable && engine.unbreakable.dynamicRiskPercent !== data.config.riskPerTradePercent && (
                      <Badge variant="outline" className="text-xs bg-blue-500/10 text-blue-500 border-blue-500/30" data-testid={`badge-engine-risk-${engine.pair}`}>
                        Risk: {engine.unbreakable.dynamicRiskPercent.toFixed(1)}%
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    {engine.unbreakable?.pauseReason && (
                      <Badge variant="outline" className="text-[10px] bg-yellow-500/10 text-yellow-500 border-yellow-500/30" data-testid={`badge-engine-pause-reason-${engine.pair}`}>
                        {engine.unbreakable.pauseReason}
                      </Badge>
                    )}
                    <Badge 
                      variant="outline" 
                      className={`text-xs ${
                        engine.status === "ACTIVE" 
                          ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                          : engine.status === "HALTED"
                          ? "bg-red-500/10 text-red-500 border-red-500/30"
                          : engine.status === "PAUSED"
                          ? "bg-yellow-500/10 text-yellow-500 border-yellow-500/30"
                          : "bg-muted text-muted-foreground"
                      }`}
                      data-testid={`badge-engine-status-${engine.pair}`}
                    >
                      {engine.status}
                    </Badge>
                  </div>
                </div>

                <div className="grid grid-cols-5 gap-2 text-xs">
                  <div data-testid={`stat-engine-budget-${engine.pair}`}>
                    <span className="text-muted-foreground">Budget:</span>
                    <span className="ml-1 font-medium">${engine.budget.toFixed(0)}</span>
                  </div>
                  <div data-testid={`stat-engine-pnl-${engine.pair}`}>
                    <span className="text-muted-foreground">PnL:</span>
                    <span className={`ml-1 font-medium ${engine.pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                      ${engine.pnl.toFixed(2)}
                    </span>
                  </div>
                  <div data-testid={`stat-engine-wl-${engine.pair}`}>
                    <span className="text-muted-foreground">W/L:</span>
                    <span className="ml-1 font-medium">
                      <span className="text-emerald-500">{engine.winCount}</span>
                      /
                      <span className="text-red-500">{engine.lossCount}</span>
                    </span>
                  </div>
                  <div data-testid={`stat-engine-trades-${engine.pair}`}>
                    <span className="text-muted-foreground">Trades:</span>
                    <span className="ml-1 font-medium">{engine.tradeCount}</span>
                  </div>
                  {engine.unbreakable && (
                    <div data-testid={`stat-engine-consec-${engine.pair}`}>
                      <span className="text-muted-foreground">Consec L:</span>
                      <span className={`ml-1 font-medium ${engine.unbreakable.consecutiveLosses >= 3 ? "text-red-500" : ""}`}>
                        {engine.unbreakable.consecutiveLosses}
                      </span>
                    </div>
                  )}
                </div>

                {engine.activeTrade && (
                  <div className="mt-2 pt-2 border-t border-muted text-xs" data-testid={`trade-active-${engine.pair}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <Target className="h-3 w-3 text-amber-500" />
                      <span className="font-medium" data-testid={`text-trade-direction-${engine.pair}`}>Active Trade: {engine.activeTrade.direction.toUpperCase()}</span>
                      <span className={`${engine.activeTrade.pnlR >= 0 ? "text-emerald-500" : "text-red-500"}`} data-testid={`text-trade-pnlr-${engine.pair}`}>
                        {engine.activeTrade.pnlR.toFixed(2)}R
                      </span>
                      {engine.activeTrade.breakevenSet && (
                        <Badge variant="outline" className="text-[10px] bg-blue-500/10 text-blue-500 border-blue-500/30" data-testid={`badge-trade-be-${engine.pair}`}>
                          BE Set
                        </Badge>
                      )}
                      {engine.activeTrade.trailingActivated && (
                        <Badge variant="outline" className="text-[10px] bg-purple-500/10 text-purple-500 border-purple-500/30" data-testid={`badge-trade-trailing-${engine.pair}`}>
                          Trailing
                        </Badge>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-[10px] text-muted-foreground">
                      <div data-testid={`text-trade-entry-${engine.pair}`}>Entry: ${engine.activeTrade.entryPrice.toFixed(4)}</div>
                      <div data-testid={`text-trade-sl-${engine.pair}`}>SL: ${engine.activeTrade.currentStopLoss.toFixed(4)}</div>
                      <div data-testid={`text-trade-size-${engine.pair}`}>Size: ${engine.activeTrade.remainingPositionSizeUsd.toFixed(0)}</div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card data-testid="card-unbreakable-features">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield className="h-5 w-5 text-primary" />
            Unbreakable Protection Suite
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Circuit Breakers
              </h4>
              <div className="flex items-center gap-2" data-testid="feature-daily-loss">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Daily Loss Limit (-10%)</span>
              </div>
              <div className="flex items-center gap-2" data-testid="feature-consec-loss">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Consecutive Loss Pause (5 losses)</span>
              </div>
              <div className="flex items-center gap-2" data-testid="feature-drawdown">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Drawdown Protection (-15%)</span>
              </div>
              <div className="flex items-center gap-2" data-testid="feature-volatility">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Volatility Spike Halt (3x ATR)</span>
              </div>
            </div>
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <BarChart3 className="h-3 w-3" />
                Risk Intelligence
              </h4>
              <div className="flex items-center gap-2" data-testid="feature-correlation">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Correlation Guard (BTC/ETH)</span>
              </div>
              <div className="flex items-center gap-2" data-testid="feature-exposure">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Exposure Limiter (40% max)</span>
              </div>
              <div className="flex items-center gap-2" data-testid="feature-kelly">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <span>Kelly Criterion Dynamic Risk</span>
              </div>
              <div className="flex items-center gap-2" data-testid="feature-self-healing">
                <RefreshCw className="h-4 w-4 text-emerald-500" />
                <span>Self-Healing Strategy Disable</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="card-smart-exit-features">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-5 w-5 text-primary" />
            Smart Exit Features
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-2" data-testid="feature-breakeven">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>Breakeven at 1R Profit</span>
            </div>
            <div className="flex items-center gap-2" data-testid="feature-trailing">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>Trailing Stop (1.5x ATR)</span>
            </div>
            <div className="flex items-center gap-2" data-testid="feature-multi-tp">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>Multi-Target TP (1R/2R/3R)</span>
            </div>
            <div className="flex items-center gap-2" data-testid="feature-dynamic-strategy">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>Dynamic Strategy Selection</span>
            </div>
            <div className="flex items-center gap-2" data-testid="feature-budget-allocation">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>Per-Engine Budget Allocation</span>
            </div>
            <div className="flex items-center gap-2" data-testid="feature-state-persistence">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>State Persistence & Logging</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {data.circuitBreakerEvents && data.circuitBreakerEvents.length > 0 && (
        <Card data-testid="card-circuit-breaker-events">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Recent Circuit Breaker Events
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-xs font-mono max-h-32 overflow-y-auto">
              {data.circuitBreakerEvents.slice(-5).reverse().map((event, i) => (
                <div key={i} className="text-muted-foreground" data-testid={`event-circuit-breaker-${i}`}>
                  {event}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
