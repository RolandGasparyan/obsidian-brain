import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  TrendingUp, 
  TrendingDown,
  Target,
  Shield,
  DollarSign,
  Clock,
  Crosshair
} from "lucide-react";
import type { TradeSignal } from "@shared/schema";
import { cn } from "@/lib/utils";

interface TradeSignalCardProps {
  signal: TradeSignal;
}

export function TradeSignalCard({ signal }: TradeSignalCardProps) {
  const isLong = signal.direction === "long";
  const isShort = signal.direction === "short";

  return (
    <Card 
      className={cn(
        "relative overflow-hidden",
        isLong && "ring-1 ring-emerald-500/30",
        isShort && "ring-1 ring-rose-500/30"
      )}
      data-testid={`card-signal-${signal.id}`}
    >
      <div className={cn(
        "absolute top-0 left-0 right-0 h-1",
        isLong && "bg-emerald-500",
        isShort && "bg-rose-500",
        !isLong && !isShort && "bg-amber-500"
      )} />
      
      <CardHeader className="pb-2 pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isLong ? (
              <TrendingUp className="h-5 w-5 text-emerald-500" />
            ) : (
              <TrendingDown className="h-5 w-5 text-rose-500" />
            )}
            <CardTitle className="text-base">
              {signal.symbol}
            </CardTitle>
          </div>
          <Badge 
            variant="outline"
            className={cn(
              "font-bold uppercase",
              isLong && "border-emerald-500/30 text-emerald-500 bg-emerald-500/10",
              isShort && "border-rose-500/30 text-rose-500 bg-rose-500/10"
            )}
          >
            {signal.direction}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Crosshair className="h-3 w-3" />
              Entry Zone
            </div>
            <p className="text-sm font-medium tabular-nums">
              ${signal.entryZoneLow.toLocaleString()} - ${signal.entryZoneHigh.toLocaleString()}
            </p>
          </div>
          
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <DollarSign className="h-3 w-3" />
              Entry
            </div>
            <p className="text-sm font-medium tabular-nums">
              ${signal.entryPrice.toLocaleString()}
            </p>
          </div>
          
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-xs text-rose-400">
              <Shield className="h-3 w-3" />
              Stop Loss
            </div>
            <p className="text-sm font-medium text-rose-500 tabular-nums">
              ${signal.stopLoss.toLocaleString()}
            </p>
          </div>
          
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-xs text-emerald-400">
              <Target className="h-3 w-3" />
              Take Profit
            </div>
            <p className="text-sm font-medium text-emerald-500 tabular-nums">
              ${signal.takeProfit1.toLocaleString()}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-border">
          <div className="flex items-center gap-3">
            <div className="text-xs">
              <span className="text-muted-foreground">Confluence: </span>
              <span className="font-medium">{Math.round(signal.confluenceScore * 100)}%</span>
            </div>
            <div className="text-xs">
              <span className="text-muted-foreground">Position: </span>
              <span className="font-medium">{signal.positionSizePct}%</span>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {new Date(signal.timestamp).toLocaleTimeString()}
          </div>
        </div>

        <p className="text-xs text-muted-foreground line-clamp-2">
          {signal.reasoning}
        </p>
      </CardContent>
    </Card>
  );
}
