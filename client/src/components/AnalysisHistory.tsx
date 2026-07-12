import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  History, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  CheckCircle2,
  XCircle
} from "lucide-react";
import type { AnalysisHistory as AnalysisHistoryType } from "@shared/schema";
import { cn } from "@/lib/utils";

interface AnalysisHistoryProps {
  history: AnalysisHistoryType[];
  isLoading?: boolean;
}

function SignalBadge({ signal }: { signal: string }) {
  const config = {
    long: { icon: TrendingUp, color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/30" },
    short: { icon: TrendingDown, color: "text-rose-500 bg-rose-500/10 border-rose-500/30" },
    neutral: { icon: Minus, color: "text-amber-500 bg-amber-500/10 border-amber-500/30" },
  };
  const cfg = config[signal as keyof typeof config] || config.neutral;
  const Icon = cfg.icon;

  return (
    <Badge variant="outline" className={cn("gap-1 uppercase text-[10px]", cfg.color)}>
      <Icon className="h-3 w-3" />
      {signal}
    </Badge>
  );
}

export function AnalysisHistory({ history, isLoading }: AnalysisHistoryProps) {
  if (isLoading) {
    return (
      <Card data-testid="panel-history">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            Analysis History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 animate-pulse">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded-md" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="panel-history">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <History className="h-5 w-5 text-primary" />
          Analysis History
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8 px-6">
            No analysis history yet
          </p>
        ) : (
          <ScrollArea className="h-[300px] px-6 pb-6">
            <div className="space-y-3">
              {history.map((item) => (
                <div 
                  key={item.id}
                  className="flex items-center justify-between p-3 rounded-md bg-muted/50 hover-elevate"
                >
                  <div className="flex items-center gap-3">
                    <SignalBadge signal={item.consensusSignal} />
                    <div>
                      <p className="text-sm font-medium">{item.symbol}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(item.createdAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">Confluence</p>
                      <p className="text-sm font-medium tabular-nums">
                        {Math.round(item.confluenceScore * 100)}%
                      </p>
                    </div>
                    {item.isActionable ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-muted-foreground" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
