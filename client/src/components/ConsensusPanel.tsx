import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Users, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Target,
  Shield,
  Crosshair,
  Zap,
  Crown,
  Flame
} from "lucide-react";
import type { ConsensusResult } from "@shared/schema";
import { cn } from "@/lib/utils";

interface ConsensusPanelProps {
  consensus?: ConsensusResult;
  isLoading?: boolean;
}

function SignalDisplay({ signal, isActionable }: { signal: string; isActionable: boolean }) {
  const signalConfig = {
    long: {
      icon: TrendingUp,
      color: "text-emerald-500",
      bgColor: "bg-emerald-500/10",
      borderColor: "border-emerald-500/30",
      glowClass: "glow-primary",
    },
    short: {
      icon: TrendingDown,
      color: "text-rose-500",
      bgColor: "bg-rose-500/10",
      borderColor: "border-rose-500/30",
      glowClass: "glow-destructive",
    },
    neutral: {
      icon: Minus,
      color: "text-amber-500",
      bgColor: "bg-amber-500/10",
      borderColor: "border-amber-500/30",
      glowClass: "",
    },
  };

  const config = signalConfig[signal as keyof typeof signalConfig] || signalConfig.neutral;
  const Icon = config.icon;

  return (
    <div className={cn(
      "flex flex-col items-center justify-center p-6 rounded-lg border-2",
      config.bgColor,
      config.borderColor,
      isActionable && config.glowClass
    )}>
      <Icon className={cn("h-12 w-12 mb-2", config.color)} />
      <span className={cn("text-2xl font-bold uppercase", config.color)}>
        {signal}
      </span>
      <Badge 
        variant={isActionable ? "default" : "secondary"} 
        className={cn("mt-2", isActionable && "bg-emerald-500")}
      >
        {isActionable ? (
          <><CheckCircle2 className="h-3 w-3 mr-1" /> Actionable</>
        ) : (
          <><AlertTriangle className="h-3 w-3 mr-1" /> Not Actionable</>
        )}
      </Badge>
    </div>
  );
}

export function ConsensusPanel({ consensus, isLoading }: ConsensusPanelProps) {
  if (isLoading) {
    return (
      <Card data-testid="panel-consensus">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Agent Consensus
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-muted-foreground">Agents analyzing market...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!consensus) {
    return (
      <Card data-testid="panel-consensus">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Agent Consensus
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-12">
            Run analysis to see agent consensus
          </p>
        </CardContent>
      </Card>
    );
  }

  const confluencePercentage = Math.round(consensus.confluenceScore * 100);
  const agentAgreement = (consensus.agreeingAgents / consensus.totalAgents) * 100;

  return (
    <Card data-testid="panel-consensus">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Agent Consensus
          </CardTitle>
          <Badge variant="outline" className="font-mono">
            {consensus.symbol}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <SignalDisplay 
          signal={consensus.consensusSignal} 
          isActionable={consensus.isActionable} 
        />

        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Confluence Score</span>
              <span className="font-medium">{confluencePercentage}%</span>
            </div>
            <Progress 
              value={confluencePercentage} 
              className={cn(
                "h-2",
                confluencePercentage >= 70 && "[&>div]:bg-emerald-500",
                confluencePercentage >= 50 && confluencePercentage < 70 && "[&>div]:bg-amber-500",
                confluencePercentage < 50 && "[&>div]:bg-rose-500"
              )}
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Agent Agreement</span>
              <span className="font-medium">{consensus.agreeingAgents}/{consensus.totalAgents} agents</span>
            </div>
            <Progress 
              value={agentAgreement} 
              className="h-2 [&>div]:bg-blue-500"
            />
          </div>
        </div>

        {/* Gods Mode: Confluence Level & Verdict */}
        {consensus.confluenceLevel && (
          <div className="flex items-center justify-between pt-4 border-t border-border">
            <div className="flex items-center gap-2">
              <Crown className={cn(
                "h-5 w-5",
                consensus.confluenceLevel === "GODLIKE" && "text-yellow-500",
                consensus.confluenceLevel === "ELITE" && "text-purple-500",
                consensus.confluenceLevel === "STRONG" && "text-blue-500",
                consensus.confluenceLevel === "MODERATE" && "text-amber-500",
                consensus.confluenceLevel === "WEAK" && "text-muted-foreground"
              )} />
              <span className={cn(
                "text-sm font-bold",
                consensus.confluenceLevel === "GODLIKE" && "text-yellow-500",
                consensus.confluenceLevel === "ELITE" && "text-purple-500",
                consensus.confluenceLevel === "STRONG" && "text-blue-500",
                consensus.confluenceLevel === "MODERATE" && "text-amber-500"
              )}>
                {consensus.confluenceLevel}
              </span>
            </div>
            {consensus.verdict && (
              <Badge 
                variant="outline"
                className={cn(
                  "font-mono",
                  consensus.verdict === "EXECUTE" && "border-emerald-500 text-emerald-500",
                  consensus.verdict === "WAIT" && "border-amber-500 text-amber-500",
                  consensus.verdict === "NO_TRADE" && "border-muted-foreground text-muted-foreground"
                )}
                data-testid="badge-verdict"
              >
                {consensus.verdict}
              </Badge>
            )}
          </div>
        )}

        {/* Gods Mode: Kill Zone */}
        {consensus.killZone && (
          <div className="pt-4 border-t border-border">
            <div className="flex items-center gap-2 mb-3">
              <Crosshair className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">Kill Zone</span>
              <Badge variant="secondary" className="text-xs">
                {consensus.killZone.widthPercent.toFixed(3)}%
              </Badge>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-muted/50 rounded-md p-2 text-center">
                <p className="text-[10px] text-muted-foreground">Low</p>
                <p className="text-sm font-medium tabular-nums text-amber-500">
                  ${consensus.killZone.low.toLocaleString()}
                </p>
              </div>
              <div className="bg-primary/10 rounded-md p-2 text-center border border-primary/30">
                <p className="text-[10px] text-primary">Optimal</p>
                <p className="text-sm font-bold tabular-nums text-primary">
                  ${consensus.killZone.optimal.toLocaleString()}
                </p>
              </div>
              <div className="bg-muted/50 rounded-md p-2 text-center">
                <p className="text-[10px] text-muted-foreground">High</p>
                <p className="text-sm font-medium tabular-nums text-amber-500">
                  ${consensus.killZone.high.toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Targets & Invalidation */}
        {consensus.isActionable && (
          <div className="grid grid-cols-2 gap-3 pt-4 border-t border-border">
            {consensus.invalidation && (
              <div className="bg-rose-500/10 rounded-md p-3">
                <div className="flex items-center gap-1 text-xs text-rose-400 mb-1">
                  <Shield className="h-3 w-3" />
                  Stop Loss
                </div>
                <p className="text-sm font-medium text-rose-500 tabular-nums">
                  ${consensus.invalidation.price.toLocaleString()}
                </p>
                <p className="text-[10px] text-rose-400/70 mt-1 truncate">
                  {consensus.invalidation.reason}
                </p>
              </div>
            )}
            {consensus.targets?.tp1 && (
              <div className="bg-emerald-500/10 rounded-md p-3">
                <div className="flex items-center gap-1 text-xs text-emerald-400 mb-1">
                  <Target className="h-3 w-3" />
                  TP1 (25%)
                </div>
                <p className="text-sm font-medium text-emerald-500 tabular-nums">
                  ${consensus.targets.tp1.price.toLocaleString()}
                </p>
              </div>
            )}
            {consensus.targets?.tp2 && (
              <div className="bg-emerald-500/10 rounded-md p-3">
                <div className="flex items-center gap-1 text-xs text-emerald-400 mb-1">
                  <Target className="h-3 w-3" />
                  TP2 (50%)
                </div>
                <p className="text-sm font-medium text-emerald-500 tabular-nums">
                  ${consensus.targets.tp2.price.toLocaleString()}
                </p>
              </div>
            )}
            {consensus.riskReward && (
              <div className="bg-blue-500/10 rounded-md p-3">
                <div className="flex items-center gap-1 text-xs text-blue-400 mb-1">
                  <CheckCircle2 className="h-3 w-3" />
                  Risk/Reward
                </div>
                <p className="text-sm font-medium text-blue-500 tabular-nums">
                  1:{consensus.riskReward.toTp2}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Trinity of Profit: Strategy Recommendation */}
        {consensus.pairScore && (
          <div className="pt-4 border-t border-border">
            <div className="flex items-center gap-2 mb-3">
              <Flame className="h-4 w-4 text-orange-500" />
              <span className="text-sm font-medium">Trinity of Profit</span>
              <Badge variant="outline" className="text-xs font-mono">
                Score: {consensus.pairScore.totalScore}/130
              </Badge>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted-foreground">Recommended Strategy</span>
              <Badge 
                className={cn(
                  "font-mono",
                  consensus.pairScore.recommendedStrategy === "WATERFALL" && "bg-blue-500",
                  consensus.pairScore.recommendedStrategy === "SCALPING" && "bg-purple-500",
                  consensus.pairScore.recommendedStrategy === "SNOWBALL" && "bg-emerald-500",
                  consensus.pairScore.recommendedStrategy === "DOUBLING" && "bg-amber-500"
                )}
                data-testid="badge-strategy"
              >
                {consensus.pairScore.recommendedStrategy}
              </Badge>
            </div>
            {consensus.strategyParams && (
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-muted/50 rounded p-2">
                  <p className="text-[10px] text-muted-foreground">Leverage</p>
                  <p className="text-sm font-medium">{consensus.strategyParams.leverage}x</p>
                </div>
                <div className="bg-muted/50 rounded p-2">
                  <p className="text-[10px] text-muted-foreground">Target</p>
                  <p className="text-sm font-medium text-emerald-500">{consensus.strategyParams.targetPercent}%</p>
                </div>
                <div className="bg-muted/50 rounded p-2">
                  <p className="text-[10px] text-muted-foreground">Stop</p>
                  <p className="text-sm font-medium text-rose-500">{consensus.strategyParams.stopLossPercent}%</p>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
