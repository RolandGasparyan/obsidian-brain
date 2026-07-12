import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Bot, User, Zap, Target, DollarSign, Shield } from "lucide-react";

interface ComparisonData {
  comparison: {
    speed: { ai: number; human: number; aiAdvantage: string };
    accuracy: { ai: number; human: number; aiAdvantage: string };
    profitability: { ai: number; human: number; aiAdvantage: string };
    risk: { ai: number; human: number; aiAdvantage: string };
  };
  aiModels: any[];
  humanTraders: any[];
}

export function AIvsHuman() {
  const { data, isLoading } = useQuery<ComparisonData>({
    queryKey: ["/api/ai-vs-human"],
    refetchInterval: 30000
  });

  if (isLoading) {
    return (
      <Card className="bg-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-cyan-400" />
            AI vs Human Comparison
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const metrics = [
    {
      icon: Zap,
      label: "Trade Speed",
      aiValue: `${data?.comparison.speed.ai}s`,
      humanValue: `${data?.comparison.speed.human}s`,
      aiPercent: 100,
      humanPercent: (data?.comparison.speed.ai || 0.5) / (data?.comparison.speed.human || 15) * 100,
      advantage: data?.comparison.speed.aiAdvantage,
      color: "bg-cyan-500"
    },
    {
      icon: Target,
      label: "Win Rate",
      aiValue: `${data?.comparison.accuracy.ai?.toFixed(1) || 0}%`,
      humanValue: `${data?.comparison.accuracy.human?.toFixed(1) || 0}%`,
      aiPercent: data?.comparison.accuracy.ai || 0,
      humanPercent: data?.comparison.accuracy.human || 0,
      advantage: data?.comparison.accuracy.aiAdvantage,
      color: "bg-green-500"
    },
    {
      icon: DollarSign,
      label: "Avg Profit",
      aiValue: `$${data?.comparison.profitability.ai?.toFixed(0) || 0}`,
      humanValue: `$${data?.comparison.profitability.human?.toFixed(0) || 0}`,
      aiPercent: 100,
      humanPercent: ((data?.comparison.profitability.human || 0) / (data?.comparison.profitability.ai || 1)) * 100,
      advantage: data?.comparison.profitability.aiAdvantage,
      color: "bg-yellow-500"
    },
    {
      icon: Shield,
      label: "Max Drawdown",
      aiValue: `${data?.comparison.risk.ai}%`,
      humanValue: `${data?.comparison.risk.human}%`,
      aiPercent: 100 - (data?.comparison.risk.ai || 0),
      humanPercent: 100 - (data?.comparison.risk.human || 0),
      advantage: data?.comparison.risk.aiAdvantage,
      color: "bg-purple-500"
    }
  ];

  return (
    <Card className="bg-card" data-testid="ai-vs-human-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-cyan-400" />
          AI vs Human Comparison
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {metrics.map((metric) => (
            <div key={metric.label} className="space-y-2" data-testid={`metric-${metric.label.toLowerCase().replace(" ", "-")}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <metric.icon className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium">{metric.label}</span>
                </div>
                <span className="text-xs text-green-400 font-medium">{metric.advantage}</span>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      <Bot className="w-3 h-3 text-cyan-400" />
                      <span className="text-xs text-muted-foreground">AI</span>
                    </div>
                    <span className="text-sm font-mono font-bold text-cyan-400">{metric.aiValue}</span>
                  </div>
                  <Progress value={metric.aiPercent} className={`h-2 ${metric.color}`} />
                </div>
                
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      <User className="w-3 h-3 text-orange-400" />
                      <span className="text-xs text-muted-foreground">Human</span>
                    </div>
                    <span className="text-sm font-mono text-orange-400">{metric.humanValue}</span>
                  </div>
                  <Progress value={metric.humanPercent} className="h-2 bg-orange-900/30" />
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 pt-4 border-t border-border">
          <div className="grid grid-cols-2 gap-4 text-center">
            <div className="p-3 rounded-lg bg-cyan-900/20">
              <div className="text-2xl font-bold text-cyan-400">{data?.aiModels?.length || 8}</div>
              <div className="text-xs text-muted-foreground">Active AI Models</div>
            </div>
            <div className="p-3 rounded-lg bg-orange-900/20">
              <div className="text-2xl font-bold text-orange-400">{data?.humanTraders?.length || 3}</div>
              <div className="text-xs text-muted-foreground">Human Benchmarks</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default AIvsHuman;
