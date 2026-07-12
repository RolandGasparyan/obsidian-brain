import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Activity, TrendingUp, TrendingDown, Clock } from "lucide-react";

interface Trade {
  id: number;
  aiModelId: number;
  asset: string;
  direction: string;
  strategy: string;
  entryPrice: number;
  exitPrice: number | null;
  profitLoss: number | null;
  profitLossPercentage: number | null;
  confidence: number;
  tradingMode: string;
  status: string;
  leverage: number;
  openedAt: string;
  closedAt: string | null;
}

const MODEL_NAMES: Record<number, string> = {
  1: "DeepSeek R1",
  2: "GPT-5",
  3: "Claude Opus",
  4: "Llama 3.3",
  5: "Gemini Flash",
  6: "Mistral Large",
  7: "Qwen 72B",
  8: "Grok xAI"
};

export function LiveTradeFeed() {
  const { data: trades, isLoading } = useQuery<Trade[]>({
    queryKey: ["/api/trades/recent"],
    refetchInterval: 5000
  });

  if (isLoading) {
    return (
      <Card className="bg-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            Live Trade Feed
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-12 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card" data-testid="live-trade-feed">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-400" />
          Live Trade Feed
          <Badge variant="outline" className="ml-auto">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse mr-1" />
            Live
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="max-h-96 overflow-y-auto">
        <div className="space-y-2">
          {trades?.slice(0, 20).map((trade) => {
            const isProfit = (trade.profitLoss || 0) >= 0;
            const modelName = MODEL_NAMES[trade.aiModelId] || `AI #${trade.aiModelId}`;
            const timestamp = new Date(trade.openedAt).toLocaleTimeString();

            return (
              <div
                key={trade.id}
                className="flex items-center gap-3 p-2 rounded-lg bg-muted/50 hover-elevate transition-all"
                data-testid={`trade-row-${trade.id}`}
              >
                <div className="flex items-center gap-1 text-xs text-muted-foreground w-16">
                  <Clock className="w-3 h-3" />
                  {timestamp}
                </div>

                <div className="w-24 truncate text-sm font-medium" data-testid={`trade-model-${trade.id}`}>
                  {modelName}
                </div>

                <div className="w-20">
                  <Badge
                    className={`${
                      trade.direction === "SHORT"
                        ? "bg-red-900/50 text-red-300"
                        : "bg-green-900/50 text-green-300"
                    }`}
                    data-testid={`trade-direction-${trade.id}`}
                  >
                    {trade.direction}
                  </Badge>
                </div>

                <div className="flex-1 min-w-0">
                  <span className="font-mono text-sm" data-testid={`trade-asset-${trade.id}`}>{trade.asset}</span>
                </div>

                <div className="w-16 text-right">
                  <span className="text-xs text-muted-foreground">{trade.leverage}x</span>
                </div>

                <div className="w-20">
                  <div className="flex items-center gap-1">
                    <Progress value={trade.confidence > 1 ? trade.confidence : trade.confidence * 100} className="h-1 flex-1" />
                    <span className="text-xs text-muted-foreground">{trade.confidence > 1 ? trade.confidence.toFixed(0) : (trade.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {(trade.status?.toLowerCase() === "closed" || trade.status?.toLowerCase() === "completed") && trade.profitLoss !== null ? (
                  <div className={`w-20 text-right font-mono text-sm ${isProfit ? "text-green-400" : "text-red-400"}`} data-testid={`trade-pnl-${trade.id}`}>
                    <div className="flex items-center justify-end gap-1">
                      {isProfit ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {isProfit ? "+" : ""}{trade.profitLoss.toFixed(2)}
                    </div>
                  </div>
                ) : (
                  <div className="w-20 text-right">
                    <Badge variant="outline" className="text-xs">Open</Badge>
                  </div>
                )}

                <div className="w-20">
                  <Badge variant="secondary" className="text-xs truncate">
                    {trade.strategy}
                  </Badge>
                </div>
              </div>
            );
          })}

          {(!trades || trades.length === 0) && (
            <div className="text-center py-8 text-muted-foreground">
              No trades yet. Initialize the trading engine to start.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default LiveTradeFeed;
