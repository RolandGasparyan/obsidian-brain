import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Zap, 
  Shield, 
  TrendingUp, 
  Layers, 
  Target, 
  Activity,
  Brain,
  Eye,
  BarChart3,
  Gauge,
  Crown,
  Swords
} from "lucide-react";

interface SecretStrategy {
  id: string;
  name: string;
  edge: number;
  description: string;
  minConfidence: number;
  regimes: string[];
  signals: {
    bullish: string[];
    bearish: string[];
  };
}

interface BalanceTier {
  min: number;
  max: number | null;
  tradeFrequency: number;
  positionMultiplier: number;
  tierName: string;
  maxLeverage: number;
  atrMultiplier: number;
  riskPerTrade: number;
}

interface TradingMode {
  name: string;
  minEdge: number;
  leverageRange: string;
  positionRange: string;
  atrStopMultiplier: number;
  atrTakeProfitMultiplier: number;
}

export default function GodsLevelStrategy() {
  const { data: strategiesData } = useQuery<{ count: number; strategies: SecretStrategy[] }>({
    queryKey: ["/api/gods-level/strategies"]
  });

  const { data: tiersData } = useQuery<{ count: number; tiers: BalanceTier[] }>({
    queryKey: ["/api/gods-level/tiers"]
  });

  const { data: modesData } = useQuery<{ count: number; modes: TradingMode[] }>({
    queryKey: ["/api/gods-level/modes"]
  });

  const { data: statusData } = useQuery<any>({
    queryKey: ["/api/gods-level/status"],
    refetchInterval: 5000
  });

  const getEdgeColor = (edge: number) => {
    if (edge >= 0.90) return "bg-emerald-500";
    if (edge >= 0.80) return "bg-green-500";
    if (edge >= 0.70) return "bg-yellow-500";
    return "bg-orange-500";
  };

  const getTierColor = (tierName: string) => {
    switch (tierName) {
      case "Titan": return "text-purple-400 border-purple-500";
      case "Gods": return "text-yellow-400 border-yellow-500";
      case "Elite": return "text-blue-400 border-blue-500";
      case "Accelerated": return "text-green-400 border-green-500";
      case "Growth": return "text-cyan-400 border-cyan-500";
      default: return "text-gray-400 border-gray-500";
    }
  };

  const getModeColor = (mode: string) => {
    switch (mode) {
      case "ULTRA_AGGRESSIVE": return "bg-red-600";
      case "AGGRESSIVE": return "bg-orange-600";
      case "NORMAL": return "bg-yellow-600";
      case "SAFE": return "bg-green-600";
      case "ULTRA_SAFE": return "bg-blue-600";
      default: return "bg-gray-600";
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center gap-3 mb-8">
          <Crown className="h-10 w-10 text-yellow-500" />
          <div>
            <h1 className="text-3xl font-bold">ULTIMATE Gods Level Strategy</h1>
            <p className="text-muted-foreground">Maximum Power Trading System v2.0</p>
          </div>
          {statusData?.enabled && (
            <Badge className="ml-auto bg-green-600" data-testid="badge-status">
              <Zap className="h-3 w-3 mr-1" />
              ACTIVE
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card data-testid="card-strategies-count">
            <CardContent className="p-4 flex items-center gap-3">
              <Swords className="h-8 w-8 text-red-500" />
              <div>
                <p className="text-2xl font-bold">{strategiesData?.count || 15}</p>
                <p className="text-sm text-muted-foreground">Secret Strategies</p>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="card-tiers-count">
            <CardContent className="p-4 flex items-center gap-3">
              <Layers className="h-8 w-8 text-purple-500" />
              <div>
                <p className="text-2xl font-bold">{tiersData?.count || 6}</p>
                <p className="text-sm text-muted-foreground">Balance Tiers</p>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="card-modes-count">
            <CardContent className="p-4 flex items-center gap-3">
              <Gauge className="h-8 w-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">{modesData?.count || 5}</p>
                <p className="text-sm text-muted-foreground">Trading Modes</p>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="card-leverage-max">
            <CardContent className="p-4 flex items-center gap-3">
              <TrendingUp className="h-8 w-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold">50x</p>
                <p className="text-sm text-muted-foreground">Max Leverage</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {statusData?.components && (
            <>
              <Card className="border-green-500/30" data-testid="card-whale-detection">
                <CardContent className="p-3 flex items-center gap-2">
                  <Eye className="h-5 w-5 text-green-500" />
                  <div>
                    <p className="text-sm font-medium">Whale Detection</p>
                    <p className="text-xs text-green-500">ACTIVE</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-blue-500/30" data-testid="card-sentiment">
                <CardContent className="p-3 flex items-center gap-2">
                  <Brain className="h-5 w-5 text-blue-500" />
                  <div>
                    <p className="text-sm font-medium">Sentiment Analysis</p>
                    <p className="text-xs text-blue-500">ACTIVE</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-purple-500/30" data-testid="card-regime">
                <CardContent className="p-3 flex items-center gap-2">
                  <Activity className="h-5 w-5 text-purple-500" />
                  <div>
                    <p className="text-sm font-medium">7 Market Regimes</p>
                    <p className="text-xs text-purple-500">ACTIVE</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-orange-500/30" data-testid="card-atr">
                <CardContent className="p-3 flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-orange-500" />
                  <div>
                    <p className="text-sm font-medium">ATR Risk Management</p>
                    <p className="text-xs text-orange-500">ACTIVE</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-yellow-500/30" data-testid="card-edge">
                <CardContent className="p-3 flex items-center gap-2">
                  <Target className="h-5 w-5 text-yellow-500" />
                  <div>
                    <p className="text-sm font-medium">60% Edge Threshold</p>
                    <p className="text-xs text-yellow-500">ENFORCED</p>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>

        <Tabs defaultValue="strategies" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="strategies" data-testid="tab-strategies">
              <Swords className="h-4 w-4 mr-2" />
              15 Secret Strategies
            </TabsTrigger>
            <TabsTrigger value="tiers" data-testid="tab-tiers">
              <Layers className="h-4 w-4 mr-2" />
              6 Balance Tiers
            </TabsTrigger>
            <TabsTrigger value="modes" data-testid="tab-modes">
              <Gauge className="h-4 w-4 mr-2" />
              5 Trading Modes
            </TabsTrigger>
          </TabsList>

          <TabsContent value="strategies" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Swords className="h-5 w-5 text-red-500" />
                  15 Secret High-Edge Trading Strategies
                </CardTitle>
                <CardDescription>
                  Advanced trading strategies with edge scores from 60% to 92%
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {strategiesData?.strategies?.map((strategy) => (
                    <Card key={strategy.id} className="border-muted" data-testid={`card-strategy-${strategy.id}`}>
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-semibold">{strategy.name}</h3>
                          <Badge className={`${getEdgeColor(strategy.edge)} text-white`}>
                            {(strategy.edge * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mb-3">{strategy.description}</p>
                        <Progress value={strategy.edge * 100} className="h-2 mb-2" />
                        <div className="flex flex-wrap gap-1">
                          {strategy.regimes?.slice(0, 3).map((regime) => (
                            <Badge key={regime} variant="outline" className="text-xs">
                              {regime}
                            </Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="tiers" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5 text-purple-500" />
                  6 Dynamic Balance Tiers (Up to 50x Leverage)
                </CardTitle>
                <CardDescription>
                  Position sizing and leverage scale with account balance
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {tiersData?.tiers?.map((tier) => (
                    <Card 
                      key={tier.tierName} 
                      className={`border-2 ${getTierColor(tier.tierName)}`}
                      data-testid={`card-tier-${tier.tierName.toLowerCase()}`}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className={`font-bold text-lg ${getTierColor(tier.tierName).split(' ')[0]}`}>
                            {tier.tierName === "Titan" && <Crown className="h-5 w-5 inline mr-1" />}
                            {tier.tierName}
                          </h3>
                          <Badge variant="outline">{tier.maxLeverage}x</Badge>
                        </div>
                        
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Balance Range</span>
                            <span>${tier.min.toLocaleString()} - {tier.max === null || tier.max === Infinity ? "∞" : `$${tier.max.toLocaleString()}`}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Position Multiplier</span>
                            <span>{tier.positionMultiplier}x</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Risk Per Trade</span>
                            <span>{(tier.riskPerTrade * 100).toFixed(1)}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">ATR Multiplier</span>
                            <span>{tier.atrMultiplier}x</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Trade Frequency</span>
                            <span>{tier.tradeFrequency}s</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="modes" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Gauge className="h-5 w-5 text-blue-500" />
                  5 Edge-Based Trading Modes
                </CardTitle>
                <CardDescription>
                  Dynamically selected based on calculated edge score
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {modesData?.modes?.map((mode) => (
                    <Card key={mode.name} className="border-muted" data-testid={`card-mode-${mode.name.toLowerCase()}`}>
                      <CardContent className="p-4">
                        <div className="flex items-center gap-4">
                          <Badge className={`${getModeColor(mode.name)} text-white min-w-32 justify-center`}>
                            {mode.name.replace("_", " ")}
                          </Badge>
                          
                          <div className="flex-1 grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                            <div>
                              <p className="text-muted-foreground">Min Edge</p>
                              <p className="font-semibold">{(mode.minEdge * 100).toFixed(0)}%</p>
                            </div>
                            <div>
                              <p className="text-muted-foreground">Leverage</p>
                              <p className="font-semibold">{mode.leverageRange}</p>
                            </div>
                            <div>
                              <p className="text-muted-foreground">Position Size</p>
                              <p className="font-semibold">{mode.positionRange}</p>
                            </div>
                            <div>
                              <p className="text-muted-foreground">ATR Stop</p>
                              <p className="font-semibold">{mode.atrStopMultiplier}x</p>
                            </div>
                            <div>
                              <p className="text-muted-foreground">ATR TP</p>
                              <p className="font-semibold">{mode.atrTakeProfitMultiplier}x</p>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                <Card className="mt-6 border-yellow-500/30">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <Shield className="h-8 w-8 text-yellow-500" />
                      <div>
                        <h4 className="font-semibold">60% Minimum Edge Threshold</h4>
                        <p className="text-sm text-muted-foreground">
                          Trades are only executed when the multi-factor edge score exceeds 60%. 
                          Edge is calculated from: Technical Analysis (30%) + Order Book (30%) + Sentiment (20%) + Strategy Edge (10%) + Whale Detection (10%)
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
