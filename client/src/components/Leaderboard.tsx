import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Trophy, TrendingUp, TrendingDown, Zap, Crown, Shield, Target, Star, CheckCircle, Brain, Gauge, Users } from "lucide-react";

interface AIModel {
  id: number;
  name: string;
  specialty: string;
  tier: string;
  level: number;
  rankingScore: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  totalProfit: number;
  totalLoss: number;
  winRate: number;
  currentBalance: number;
  startingBalance: number;
  dailyPnl: number;
  isActive: boolean;
  deactivationReason: string | null;
}

const TIER_CONFIG: Record<string, { icon: string; color: string; bg: string }> = {
  "Novice": { icon: "shield", color: "text-gray-400", bg: "bg-gray-800" },
  "Intermediate": { icon: "star", color: "text-green-400", bg: "bg-green-900/30" },
  "Expert": { icon: "zap", color: "text-blue-400", bg: "bg-blue-900/30" },
  "Master": { icon: "target", color: "text-purple-400", bg: "bg-purple-900/30" },
  "Legend": { icon: "crown", color: "text-yellow-400", bg: "bg-yellow-900/30" },
  "Gods Mode": { icon: "crown", color: "text-red-400", bg: "bg-red-900/30" }
};

function TierBadge({ tier }: { tier: string }) {
  const config = TIER_CONFIG[tier] || TIER_CONFIG["Novice"];
  return (
    <Badge className={`${config.bg} ${config.color} border-none`}>
      {tier === "Gods Mode" && <Crown className="w-3 h-3 mr-1" />}
      {tier === "Legend" && <Star className="w-3 h-3 mr-1" />}
      {tier === "Master" && <Target className="w-3 h-3 mr-1" />}
      {tier === "Expert" && <Zap className="w-3 h-3 mr-1" />}
      {tier}
    </Badge>
  );
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) return <Crown className="w-6 h-6 text-yellow-400" data-testid="rank-badge-1" />;
  if (rank === 2) return <Trophy className="w-5 h-5 text-gray-400" data-testid="rank-badge-2" />;
  if (rank === 3) return <Star className="w-5 h-5 text-amber-600" data-testid="rank-badge-3" />;
  return <span className="text-lg font-bold text-muted-foreground" data-testid={`rank-badge-${rank}`}>#{rank}</span>;
}

export function Leaderboard() {
  const { data: leaderboard, isLoading } = useQuery<AIModel[]>({
    queryKey: ["/api/leaderboard"],
    refetchInterval: 10000
  });

  if (isLoading) {
    return (
      <Card className="bg-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-400" />
            AI Trading Leaderboard
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card" data-testid="leaderboard-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Trophy className="w-5 h-5 text-yellow-400" />
          AI Trading Leaderboard
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-sm text-muted-foreground mb-4 pb-4 border-b border-border" data-testid="fair-competition-status">
          <div className="flex items-center gap-2 mb-3" data-testid="text-universal-knowledge-header">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span>All 8 AI models use identical Universal Knowledge Base</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-muted/50 p-3 rounded-lg" data-testid="card-universal-knowledge">
              <div className="flex items-center gap-1 text-muted-foreground text-xs mb-1">
                <Brain className="w-3 h-3" />
                Universal Knowledge
              </div>
              <div className="text-foreground font-bold" data-testid="text-knowledge-value">100%</div>
              <div className="text-xs text-muted-foreground">Full access for all AIs</div>
            </div>
            <div className="bg-muted/50 p-3 rounded-lg" data-testid="card-trading-methods">
              <div className="flex items-center gap-1 text-muted-foreground text-xs mb-1">
                <Gauge className="w-3 h-3" />
                Trading Methods
              </div>
              <div className="text-foreground font-bold" data-testid="text-methods-value">50+</div>
              <div className="text-xs text-muted-foreground">Fib, VWAP, FVG, Harmonics</div>
            </div>
            <div className="bg-muted/50 p-3 rounded-lg" data-testid="card-competition-factor">
              <div className="flex items-center gap-1 text-muted-foreground text-xs mb-1">
                <Target className="w-3 h-3" />
                Competition Factor
              </div>
              <div className="text-foreground font-bold" data-testid="text-competition-value">Execution</div>
              <div className="text-xs text-muted-foreground">Timing, risk mgmt, patterns</div>
            </div>
            <div className="bg-muted/50 p-3 rounded-lg" data-testid="card-fair-competition">
              <div className="flex items-center gap-1 text-muted-foreground text-xs mb-1">
                <Users className="w-3 h-3" />
                Fair Competition
              </div>
              <div className="text-green-400 font-bold flex items-center gap-1" data-testid="text-fair-competition-value">
                <CheckCircle className="w-3 h-3" /> Yes
              </div>
              <div className="text-xs text-muted-foreground">Same tools, different execution</div>
            </div>
          </div>
        </div>
        <div className="space-y-3">
          {leaderboard?.map((model, index) => {
            const pnl = model.currentBalance - model.startingBalance;
            const pnlPercent = (pnl / model.startingBalance) * 100;
            const isProfit = pnl >= 0;

            return (
              <div
                key={model.id}
                className={`flex items-center gap-4 p-3 rounded-lg transition-all hover-elevate ${
                  index < 3 ? "bg-gradient-to-r from-yellow-900/20 to-transparent" : "bg-muted/50"
                } ${!model.isActive ? "opacity-60" : ""}`}
                data-testid={`leaderboard-row-${model.id}`}
              >
                <div className="w-10 flex justify-center">
                  <RankBadge rank={index + 1} />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold truncate" data-testid={`model-name-${model.id}`}>{model.name}</span>
                    <TierBadge tier={model.tier} />
                    {!model.isActive && (
                      <Badge variant="destructive" className="text-xs">Inactive</Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">{model.specialty}</div>
                </div>

                <div className="text-right space-y-1">
                  <div className="font-mono font-bold" data-testid={`model-score-${model.id}`}>
                    {model.rankingScore.toFixed(1)} pts
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Lv.{model.level}
                  </div>
                </div>

                <div className="text-right space-y-1 w-24">
                  <div className={`font-mono font-bold ${isProfit ? "text-green-400" : "text-red-400"}`} data-testid={`model-pnl-${model.id}`}>
                    {isProfit ? "+" : ""}{pnl.toFixed(2)}
                  </div>
                  <div className={`text-xs flex items-center justify-end gap-1 ${isProfit ? "text-green-400" : "text-red-400"}`}>
                    {isProfit ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {pnlPercent.toFixed(2)}%
                  </div>
                </div>

                <div className="text-right space-y-1 w-20">
                  <div className="font-mono" data-testid={`model-winrate-${model.id}`}>{model.winRate.toFixed(1)}%</div>
                  <div className="text-xs text-muted-foreground">{model.totalTrades} trades</div>
                </div>

                <div className="w-20">
                  <Progress value={model.winRate} className="h-2" />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default Leaderboard;
