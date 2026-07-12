import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Radar, TrendingUp, TrendingDown, Zap, RefreshCw } from "lucide-react";

interface MarketOpportunity {
  id: number;
  asset: string;
  market: string;
  price: number;
  volume24h: number;
  volatility: number;
  score: number;
  high24h: number;
  low24h: number;
  fundingRate: number | null;
  rsi: number | null;
  scannedAt: string;
}

export function MarketScanner() {
  const { data: opportunities, isLoading, refetch } = useQuery<MarketOpportunity[]>({
    queryKey: ["/api/market/opportunities"],
    refetchInterval: 30000
  });

  if (isLoading) {
    return (
      <Card className="bg-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Radar className="w-5 h-5 text-purple-400" />
            Market Scanner
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-12 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const formatVolume = (vol: number) => {
    if (vol >= 1e9) return `$${(vol / 1e9).toFixed(2)}B`;
    if (vol >= 1e6) return `$${(vol / 1e6).toFixed(2)}M`;
    return `$${vol.toFixed(0)}`;
  };

  return (
    <Card className="bg-card" data-testid="market-scanner">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Radar className="w-5 h-5 text-purple-400" />
          Market Scanner
          <Button variant="ghost" size="sm" className="ml-auto" onClick={() => refetch()} data-testid="button-refresh-scanner">
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {opportunities?.slice(0, 10).map((opp) => {
            const priceChange = ((opp.price - opp.low24h) / opp.low24h) * 100;
            const isPositive = priceChange >= 0;
            const fundingPositive = (opp.fundingRate || 0) >= 0;

            return (
              <div
                key={opp.id}
                className="flex items-center gap-3 p-2 rounded-lg bg-muted/50 hover-elevate transition-all"
                data-testid={`opportunity-row-${opp.asset}`}
              >
                <div className="w-24">
                  <span className="font-mono font-medium" data-testid={`opp-asset-${opp.asset}`}>
                    {opp.asset.replace("_", "/")}
                  </span>
                </div>

                <Badge variant="secondary" className="text-xs w-16 justify-center">
                  {opp.market}
                </Badge>

                <div className="w-24 text-right font-mono" data-testid={`opp-price-${opp.asset}`}>
                  ${opp.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </div>

                <div className="w-20 text-right text-xs text-muted-foreground">
                  {formatVolume(opp.volume24h)}
                </div>

                <div className="w-16 text-right">
                  <span className={`text-xs ${opp.volatility > 5 ? "text-orange-400" : "text-muted-foreground"}`}>
                    {opp.volatility.toFixed(2)}%
                  </span>
                </div>

                {opp.fundingRate !== null && (
                  <div className={`w-16 text-right text-xs ${fundingPositive ? "text-green-400" : "text-red-400"}`}>
                    {fundingPositive ? "+" : ""}{(opp.fundingRate * 100).toFixed(4)}%
                  </div>
                )}

                {opp.rsi !== null && (
                  <div className={`w-12 text-right text-xs ${opp.rsi > 70 ? "text-red-400" : opp.rsi < 30 ? "text-green-400" : "text-muted-foreground"}`}>
                    RSI {opp.rsi.toFixed(0)}
                  </div>
                )}

                <div className="flex-1 min-w-20">
                  <div className="flex items-center gap-2">
                    <Progress value={opp.score * 100} className="h-2 flex-1" />
                    <span className="text-xs font-medium w-8">{(opp.score * 100).toFixed(0)}%</span>
                  </div>
                </div>

                <div className={`w-6 flex items-center ${opp.score > 0.7 ? "text-green-400" : opp.score > 0.5 ? "text-yellow-400" : "text-muted-foreground"}`}>
                  {opp.score > 0.7 && <Zap className="w-4 h-4" />}
                </div>
              </div>
            );
          })}

          {(!opportunities || opportunities.length === 0) && (
            <div className="text-center py-8 text-muted-foreground">
              No market data available. Start the trading engine to scan markets.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default MarketScanner;
