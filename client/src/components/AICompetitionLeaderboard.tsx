import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trophy, Play, Pause, RefreshCw, TrendingUp, TrendingDown, Zap, Brain, Target, Shield, LineChart, Newspaper, Eye, Calculator } from "lucide-react";

interface AIPerformance {
  id: string;
  name: string;
  budget: number;
  startingBudget: number;
  totalProfit: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  currentStreak: number;
  dailyProfit: number;
  winRate: number;
  roi: number;
  rank: number;
  isPaused: boolean;
  pauseReason: string;
}

interface CompetitionStats {
  totalBalance: number;
  totalProfit: number;
  totalTrades: number;
  activeAIs: number;
  pausedAIs: number;
  leader: AIPerformance | null;
}

interface CompetitionStatus {
  isRunning: boolean;
  mode: string;
  direction: string;
  totalBalance: number;
  budgetPerAI: number;
  leaderboard: AIPerformance[];
  stats: CompetitionStats;
}

const AI_ICONS: Record<string, React.ReactNode> = {
  DeepSeek_R1: <Calculator className="w-4 h-4" />,
  GPT_5: <TrendingUp className="w-4 h-4" />,
  Claude_Opus: <Brain className="w-4 h-4" />,
  Llama_3_3: <Zap className="w-4 h-4" />,
  Gemini_Flash: <Eye className="w-4 h-4" />,
  Mistral_Large: <Shield className="w-4 h-4" />,
  Qwen_72B: <LineChart className="w-4 h-4" />,
  Grok_xAI: <Newspaper className="w-4 h-4" />
};

const RANK_VARIANTS: Array<"default" | "secondary" | "destructive" | "outline"> = [
  "default",
  "secondary",
  "outline",
  "secondary",
  "secondary",
  "secondary",
  "secondary",
  "secondary"
];

export function AICompetitionLeaderboard() {
  const { data: status, isLoading, refetch } = useQuery<CompetitionStatus>({
    queryKey: ["/api/competition/status"],
    refetchInterval: 5000
  });

  if (isLoading) {
    return (
      <Card className="w-full" data-testid="competition-leaderboard-loading">
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-muted rounded w-1/3"></div>
            <div className="space-y-2">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                <div key={i} className="h-12 bg-muted rounded"></div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!status) return null;

  const { leaderboard, stats, isRunning, budgetPerAI, direction } = status;

  return (
    <Card className="w-full" data-testid="competition-leaderboard">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-500" />
            <CardTitle className="text-lg">AI Trading Competition</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={isRunning ? "default" : "secondary"} data-testid="status-badge-running">
              {isRunning ? "RUNNING" : "STOPPED"}
            </Badge>
            <Badge variant="outline" data-testid="status-badge-direction">
              {direction}
            </Badge>
            <Button size="icon" variant="ghost" onClick={() => refetch()} data-testid="button-refresh-leaderboard">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <div className="grid grid-cols-4 gap-2 text-center text-sm">
          <div className="p-2 bg-muted rounded" data-testid="stat-total-balance">
            <div className="text-muted-foreground">Total Balance</div>
            <div className="font-bold">${stats.totalBalance.toFixed(2)}</div>
          </div>
          <div className="p-2 bg-muted rounded" data-testid="stat-total-profit">
            <div className="text-muted-foreground">Total Profit</div>
            <div className={`font-bold ${stats.totalProfit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {stats.totalProfit >= 0 ? '+' : ''}${stats.totalProfit.toFixed(2)}
            </div>
          </div>
          <div className="p-2 bg-muted rounded" data-testid="stat-total-trades">
            <div className="text-muted-foreground">Total Trades</div>
            <div className="font-bold">{stats.totalTrades}</div>
          </div>
          <div className="p-2 bg-muted rounded" data-testid="stat-active-ais">
            <div className="text-muted-foreground">Active AIs</div>
            <div className="font-bold">{stats.activeAIs}/8</div>
          </div>
        </div>

        <div className="text-xs text-muted-foreground text-center">
          Each AI starts with ${budgetPerAI.toFixed(2)} budget
        </div>

        <div className="space-y-2">
          {leaderboard.map((ai) => (
            <div
              key={ai.id}
              className={`flex items-center gap-2 p-2 rounded border ${ai.isPaused ? 'opacity-50 bg-muted' : ''}`}
              data-testid={`ai-row-${ai.id}`}
            >
              <Badge variant={RANK_VARIANTS[ai.rank - 1] || 'secondary'} data-testid={`rank-badge-${ai.id}`}>
                #{ai.rank}
              </Badge>
              
              <div className="flex items-center gap-1 flex-1 min-w-0">
                {AI_ICONS[ai.id]}
                <span className="font-medium truncate text-sm" data-testid={`ai-name-${ai.id}`}>{ai.name}</span>
                {ai.isPaused && (
                  <Badge variant="destructive" className="text-xs ml-1" data-testid={`paused-badge-${ai.id}`}>
                    <Pause className="w-3 h-3 mr-1" />
                    PAUSED
                  </Badge>
                )}
              </div>

              <div className="flex items-center gap-3 text-sm">
                <div className={`font-bold min-w-16 text-right ${ai.totalProfit >= 0 ? 'text-green-500' : 'text-red-500'}`} data-testid={`profit-${ai.id}`}>
                  {ai.totalProfit >= 0 ? '+' : ''}${ai.totalProfit.toFixed(2)}
                </div>
                
                <div className={`min-w-14 text-right ${ai.roi >= 0 ? 'text-green-500' : 'text-red-500'}`} data-testid={`roi-${ai.id}`}>
                  {ai.roi >= 0 ? '+' : ''}{ai.roi.toFixed(1)}%
                </div>
                
                <div className="min-w-12 text-right text-muted-foreground" data-testid={`winrate-${ai.id}`}>
                  {ai.winRate.toFixed(0)}% WR
                </div>
                
                <div className="min-w-10 text-right text-muted-foreground" data-testid={`trades-${ai.id}`}>
                  {ai.totalTrades}T
                </div>

                {ai.currentStreak !== 0 && (
                  <Badge variant={ai.currentStreak > 0 ? "default" : "destructive"} className="text-xs" data-testid={`streak-${ai.id}`}>
                    {ai.currentStreak > 0 ? (
                      <><TrendingUp className="w-3 h-3 mr-1" />{ai.currentStreak}</>
                    ) : (
                      <><TrendingDown className="w-3 h-3 mr-1" />{Math.abs(ai.currentStreak)}</>
                    )}
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>

        {stats.leader && (
          <div className="p-3 bg-muted border rounded-lg" data-testid="leader-highlight">
            <div className="flex items-center gap-2 flex-wrap">
              <Trophy className="w-5 h-5 text-primary" />
              <span className="font-bold" data-testid="leader-label">Leading:</span>
              <span data-testid="leader-name">{stats.leader.name}</span>
              <span className={`font-bold ml-auto ${stats.leader.totalProfit >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`} data-testid="leader-profit">
                +${stats.leader.totalProfit.toFixed(2)} ({stats.leader.roi.toFixed(1)}% ROI)
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
