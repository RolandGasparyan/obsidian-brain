import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Zap, 
  Brain, 
  Shield, 
  Activity, 
  Target,
  TrendingUp,
  AlertTriangle,
  Send,
  Settings,
  RefreshCw,
  CheckCircle2,
  Sparkles,
  Triangle,
  Waves,
  RotateCcw,
  Percent,
  StopCircle,
  Pause,
  SlidersHorizontal,
  Crosshair
} from "lucide-react";

interface EngineStatus {
  id: number;
  name: string;
  status: "ACTIVE" | "IDLE" | "TRIGGERED" | "ERROR";
  lastAction?: string;
  timestamp: string;
}

interface Feature {
  name: string;
  active: boolean;
}

interface AIModel {
  name: string;
  role: string;
  active: boolean;
}

interface DynamicStrategy {
  id: string;
  name: string;
  trigger: string;
  description: string;
  icon: string;
}

interface DynamicStrategyConfig {
  enabled: boolean;
  profile: string;
  currentStrategy: string;
  regime: string;
  doublingMultiplier: number;
  strategies: DynamicStrategy[];
  adxThresholds: {
    hyperTrending: number;
    trending: number;
    ranging: number;
    neutral: number;
  };
}

interface AlphaPillar {
  id: number;
  name: string;
  description: string;
  active: boolean;
  icon: string;
}

interface AlphaArenaConfig {
  enabled: boolean;
  riskProfile: string;
  pillars: AlphaPillar[];
  consensus: {
    required: number;
    total: number;
    description: string;
  };
  models: AIModel[];
}

interface EnginesResponse {
  engines: EngineStatus[];
  profitCascade: { level: number; percent: number }[];
  features: Feature[];
  aiModels: AIModel[];
  dynamicStrategy?: DynamicStrategyConfig;
  alphaArena?: AlphaArenaConfig;
}

const engineIcons: Record<number, any> = {
  1: Target,
  2: Shield,
  3: Brain,
  4: Sparkles,
  5: TrendingUp,
  6: Zap,
  7: AlertTriangle,
  8: Send,
  9: Settings,
  10: RefreshCw
};

export function EnginesPanel() {
  const { data, isLoading } = useQuery<EnginesResponse>({
    queryKey: ["/api/engines"],
    refetchInterval: 5000
  });

  if (isLoading || !data) {
    return (
      <Card data-testid="card-engines-loading">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-5 w-5 text-primary" />
            10 Trading Engines
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-8 bg-muted rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="panel-engines">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-5 w-5 text-primary" />
            10 Trading Engines
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data.engines.map((engine) => {
            const Icon = engineIcons[engine.id] || Activity;
            return (
              <div
                key={engine.id}
                className="flex items-center justify-between py-1.5 px-2 rounded bg-muted/50"
                data-testid={`engine-${engine.id}`}
              >
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">
                    ENGINE {engine.id}: {engine.name}
                  </span>
                </div>
                <Badge
                  variant="outline"
                  className={`text-xs ${
                    engine.status === "ACTIVE"
                      ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                      : engine.status === "TRIGGERED"
                      ? "bg-yellow-500/10 text-yellow-500 border-yellow-500/30"
                      : engine.status === "ERROR"
                      ? "bg-red-500/10 text-red-500 border-red-500/30"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {engine.status}
                </Badge>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-5 w-5 text-primary" />
            Extra Features
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-1.5">
            {data.features.map((feature, i) => (
              <div
                key={i}
                className="flex items-center gap-2 text-sm"
                data-testid={`feature-${i}`}
              >
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                <span className="text-muted-foreground">{feature.name}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-5 w-5 text-primary" />
            8 AI Models Active
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-1.5">
            {data.aiModels.map((model, i) => (
              <div
                key={i}
                className="flex items-center justify-between py-1 px-2 rounded bg-muted/50"
                data-testid={`ai-model-${i}`}
              >
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span className="text-sm font-medium">{model.name}</span>
                </div>
                <span className="text-xs text-muted-foreground">{model.role}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-5 w-5 text-primary" />
            Profit Cascade
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            {data.profitCascade.map((level) => (
              <Badge
                key={level.level}
                variant="outline"
                className="bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
              >
                TP{level.level}: {level.percent}%
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {data.dynamicStrategy?.enabled && (
        <Card data-testid="card-dynamic-strategy">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-base">
              <div className="flex items-center gap-2">
                <Crosshair className="h-5 w-5 text-amber-500" />
                Dynamic Strategy GODS
              </div>
              <Badge 
                variant="outline" 
                className="bg-amber-500/10 text-amber-500 border-amber-500/30"
              >
                {data.dynamicStrategy.currentStrategy}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Regime:</span>
              <Badge variant="outline" className={
                data.dynamicStrategy.regime === "HYPER_TRENDING" 
                  ? "bg-red-500/10 text-red-500 border-red-500/30"
                  : data.dynamicStrategy.regime === "TRENDING"
                  ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                  : data.dynamicStrategy.regime === "RANGING"
                  ? "bg-blue-500/10 text-blue-500 border-blue-500/30"
                  : "bg-muted text-muted-foreground"
              }>
                {data.dynamicStrategy.regime}
              </Badge>
            </div>
            {data.dynamicStrategy.doublingMultiplier > 1 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Doubling:</span>
                <Badge variant="outline" className="bg-orange-500/10 text-orange-500 border-orange-500/30">
                  {data.dynamicStrategy.doublingMultiplier}x Size
                </Badge>
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 pt-2">
              {data.dynamicStrategy.strategies.map((strat) => {
                const isActive = data.dynamicStrategy?.currentStrategy === strat.id;
                const StratIcon = strat.id === "PYRAMID" ? Triangle 
                  : strat.id === "WATERFALL" ? Waves 
                  : strat.id === "SCALPING" ? Zap 
                  : RotateCcw;
                return (
                  <div
                    key={strat.id}
                    className={`flex items-center gap-2 p-2 rounded text-xs ${
                      isActive 
                        ? "bg-amber-500/20 border border-amber-500/40" 
                        : "bg-muted/50"
                    }`}
                    data-testid={`strategy-${strat.id}`}
                  >
                    <StratIcon className={`h-3.5 w-3.5 ${isActive ? "text-amber-500" : "text-muted-foreground"}`} />
                    <div>
                      <div className={`font-medium ${isActive ? "text-amber-500" : ""}`}>{strat.name}</div>
                      <div className="text-muted-foreground text-[10px]">{strat.trigger}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {data.alphaArena?.enabled && (
        <Card data-testid="card-alpha-arena">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-base">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-purple-500" />
                Alpha Arena 8 Pillars
              </div>
              <Badge 
                variant="outline" 
                className="bg-purple-500/10 text-purple-500 border-purple-500/30"
              >
                {data.alphaArena.consensus.required}/{data.alphaArena.consensus.total} Consensus
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.alphaArena.pillars.map((pillar) => {
              const PillarIcon = pillar.icon === "shield" ? Shield
                : pillar.icon === "percent" ? Percent
                : pillar.icon === "stop" ? StopCircle
                : pillar.icon === "trending" ? TrendingUp
                : pillar.icon === "pause" ? Pause
                : pillar.icon === "target" ? Target
                : pillar.icon === "sliders" ? SlidersHorizontal
                : Brain;
              return (
                <div
                  key={pillar.id}
                  className="flex items-center gap-2 py-1 px-2 rounded bg-muted/50"
                  data-testid={`pillar-${pillar.id}`}
                >
                  <PillarIcon className="h-3.5 w-3.5 text-purple-400" />
                  <div className="flex-1">
                    <span className="text-sm font-medium">{pillar.name}</span>
                    <span className="text-xs text-muted-foreground ml-2">{pillar.description}</span>
                  </div>
                  {pillar.active && (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
