import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  BarChart3,
  Percent,
  DollarSign,
  Flame,
  Scale,
  Target
} from "lucide-react";
import type { MarketData } from "@shared/schema";
import { cn } from "@/lib/utils";

interface MarketDataPanelProps {
  data?: MarketData;
  isLoading?: boolean;
}

function StatItem({ 
  label, 
  value, 
  icon: Icon, 
  trend,
  suffix = ""
}: { 
  label: string; 
  value: string | number; 
  icon?: React.ElementType;
  trend?: "up" | "down" | "neutral";
  suffix?: string;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <span className={cn(
        "text-sm font-medium tabular-nums",
        trend === "up" && "text-emerald-500",
        trend === "down" && "text-rose-500"
      )}>
        {typeof value === "number" ? value.toLocaleString() : value}{suffix}
      </span>
    </div>
  );
}

export function MarketDataPanel({ data, isLoading }: MarketDataPanelProps) {
  if (isLoading) {
    return (
      <Card data-testid="panel-market-data">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Market Data
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 animate-pulse">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="flex justify-between">
                <div className="h-4 w-24 bg-muted rounded" />
                <div className="h-4 w-16 bg-muted rounded" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card data-testid="panel-market-data">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Market Data
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            Select a symbol and run analysis to view market data
          </p>
        </CardContent>
      </Card>
    );
  }

  const priceChange = data.priceChange24h;
  const priceTrend = priceChange > 0 ? "up" : priceChange < 0 ? "down" : "neutral";

  return (
    <Card data-testid="panel-market-data">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Market Data
          </CardTitle>
          <Badge variant="outline" className="font-mono">
            {data.symbol}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-1">
        <div className="flex items-center justify-between py-3 border-b border-border">
          <span className="text-2xl font-bold tabular-nums">
            ${data.currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <div className={cn(
            "flex items-center gap-1 text-sm font-medium px-2 py-1 rounded",
            priceTrend === "up" && "bg-emerald-500/10 text-emerald-500",
            priceTrend === "down" && "bg-rose-500/10 text-rose-500",
            priceTrend === "neutral" && "bg-amber-500/10 text-amber-500"
          )}>
            {priceTrend === "up" ? (
              <TrendingUp className="h-4 w-4" />
            ) : priceTrend === "down" ? (
              <TrendingDown className="h-4 w-4" />
            ) : null}
            {priceChange > 0 ? "+" : ""}{priceChange.toFixed(2)}%
          </div>
        </div>

        <StatItem label="24h High" value={`$${data.high24h.toLocaleString()}`} icon={TrendingUp} />
        <StatItem label="24h Low" value={`$${data.low24h.toLocaleString()}`} icon={TrendingDown} />
        <StatItem label="24h Volume" value={`$${(data.volume24h / 1e6).toFixed(2)}M`} icon={BarChart3} />
        <StatItem label="VWAP" value={`$${data.vwap.toLocaleString()}`} icon={DollarSign} />
        <StatItem label="RSI (14)" value={data.rsi.toFixed(1)} icon={Percent} trend={data.rsi > 70 ? "down" : data.rsi < 30 ? "up" : "neutral"} />
        
        <div className="pt-3 mt-3 border-t border-border">
          <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
            <Scale className="h-3 w-3" />
            Derivatives
          </p>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-muted/50 rounded-md p-2">
              <p className="text-[10px] text-muted-foreground">Funding Rate</p>
              <p className={cn(
                "text-sm font-medium tabular-nums",
                data.fundingRate > 0 ? "text-emerald-500" : "text-rose-500"
              )}>
                {(data.fundingRate * 100).toFixed(4)}%
              </p>
            </div>
            <div className="bg-muted/50 rounded-md p-2">
              <p className="text-[10px] text-muted-foreground">L/S Ratio</p>
              <p className={cn(
                "text-sm font-medium tabular-nums",
                data.longShortRatio > 1 ? "text-emerald-500" : "text-rose-500"
              )}>
                {data.longShortRatio.toFixed(2)}
              </p>
            </div>
            <div className="bg-muted/50 rounded-md p-2">
              <p className="text-[10px] text-muted-foreground">Open Interest</p>
              <p className="text-sm font-medium tabular-nums">
                ${(data.openInterest / 1e9).toFixed(2)}B
              </p>
            </div>
            {data.orderBookImbalance !== undefined && (
              <div className="bg-muted/50 rounded-md p-2">
                <p className="text-[10px] text-muted-foreground">Order Book</p>
                <p className={cn(
                  "text-sm font-medium tabular-nums",
                  data.orderBookImbalance > 0 ? "text-emerald-500" : "text-rose-500"
                )}>
                  {data.orderBookImbalance > 0 ? "Buy " : "Sell "}
                  {Math.abs(data.orderBookImbalance * 100).toFixed(1)}%
                </p>
              </div>
            )}
          </div>
        </div>

        {data.liquidations24h && data.liquidations24h.totalLiquidations > 0 && (
          <div className="pt-3 mt-3 border-t border-border">
            <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
              <Flame className="h-3 w-3 text-orange-500" />
              24h Liquidations
            </p>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-rose-500/10 rounded-md p-2">
                <p className="text-[10px] text-muted-foreground">Longs</p>
                <p className="text-sm font-medium tabular-nums text-rose-500">
                  ${(data.liquidations24h.longLiquidations / 1e6).toFixed(1)}M
                </p>
              </div>
              <div className="bg-emerald-500/10 rounded-md p-2">
                <p className="text-[10px] text-muted-foreground">Shorts</p>
                <p className="text-sm font-medium tabular-nums text-emerald-500">
                  ${(data.liquidations24h.shortLiquidations / 1e6).toFixed(1)}M
                </p>
              </div>
              <div className="bg-muted/50 rounded-md p-2">
                <p className="text-[10px] text-muted-foreground">Total</p>
                <p className="text-sm font-medium tabular-nums">
                  ${(data.liquidations24h.totalLiquidations / 1e6).toFixed(1)}M
                </p>
              </div>
            </div>
          </div>
        )}

        {data.markPrice && (
          <div className="pt-3 mt-3 border-t border-border">
            <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
              <Target className="h-3 w-3" />
              Futures Prices
            </p>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-muted/50 rounded-md p-2">
                <p className="text-[10px] text-muted-foreground">Mark Price</p>
                <p className="text-sm font-medium tabular-nums">
                  ${data.markPrice.toLocaleString()}
                </p>
              </div>
              {data.indexPrice && (
                <div className="bg-muted/50 rounded-md p-2">
                  <p className="text-[10px] text-muted-foreground">Index Price</p>
                  <p className="text-sm font-medium tabular-nums">
                    ${data.indexPrice.toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
