import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Zap, 
  Timer, 
  Globe, 
  Brain, 
  Calculator, 
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2
} from "lucide-react";
import type { AgentConfig, AgentAnalysis, SignalType } from "@shared/schema";
import { cn } from "@/lib/utils";

const iconMap: Record<string, React.ElementType> = {
  Zap,
  Timer,
  Globe,
  Brain,
  Calculator,
  TrendingUp,
};

const phaseColors: Record<string, string> = {
  sentinel: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  strategist: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  executioner: "bg-orange-500/10 text-orange-400 border-orange-500/20",
};

const phaseLabels: Record<string, string> = {
  sentinel: "Sentinel",
  strategist: "Strategist",
  executioner: "Executioner",
};

interface AgentCardProps {
  agent: AgentConfig;
  analysis?: AgentAnalysis;
  isAnalyzing?: boolean;
}

function SignalIcon({ signal }: { signal: SignalType }) {
  if (signal === "long") {
    return <TrendingUp className="h-4 w-4 text-emerald-500" />;
  }
  if (signal === "short") {
    return <TrendingDown className="h-4 w-4 text-rose-500" />;
  }
  return <Minus className="h-4 w-4 text-amber-500" />;
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  const percentage = Math.round(confidence * 100);
  const color = confidence >= 0.7 
    ? "bg-emerald-500" 
    : confidence >= 0.5 
    ? "bg-amber-500" 
    : "bg-rose-500";
  
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">Confidence</span>
        <span className="font-medium">{percentage}%</span>
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div 
          className={cn("h-full rounded-full transition-all duration-500", color)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export function AgentCard({ agent, analysis, isAnalyzing }: AgentCardProps) {
  const Icon = iconMap[agent.icon] || Zap;
  
  return (
    <Card 
      className={cn(
        "relative overflow-hidden transition-all duration-300",
        isAnalyzing && "ring-2 ring-primary/50 animate-pulse-slow",
        analysis && analysis.signal !== "neutral" && "ring-1",
        analysis?.signal === "long" && "ring-emerald-500/30",
        analysis?.signal === "short" && "ring-rose-500/30"
      )}
      data-testid={`card-agent-${agent.id}`}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-2.5 rounded-lg",
              phaseColors[agent.phase]
            )}>
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold leading-tight">
                {agent.name}
              </CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                {agent.role}
              </p>
            </div>
          </div>
          <Badge 
            variant="outline" 
            className={cn("text-[10px] uppercase font-medium", phaseColors[agent.phase])}
          >
            {phaseLabels[agent.phase]}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-3">
        {isAnalyzing ? (
          <div className="flex items-center justify-center py-4 gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">Analyzing...</span>
          </div>
        ) : analysis ? (
          <>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <SignalIcon signal={analysis.signal} />
                <span className={cn(
                  "text-sm font-semibold uppercase",
                  analysis.signal === "long" && "text-emerald-500",
                  analysis.signal === "short" && "text-rose-500",
                  analysis.signal === "neutral" && "text-amber-500"
                )}>
                  {analysis.signal}
                </span>
              </div>
              {analysis.entryPrice && (
                <span className="text-xs text-muted-foreground">
                  Entry: ${analysis.entryPrice.toLocaleString()}
                </span>
              )}
            </div>
            
            <ConfidenceBar confidence={analysis.confidence} />
            
            {analysis.keyFindings.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Key Finding:</p>
                <p className="text-xs line-clamp-2">
                  {analysis.keyFindings[0]}
                </p>
              </div>
            )}
          </>
        ) : (
          <div className="py-4 text-center">
            <p className="text-xs text-muted-foreground">
              {agent.description}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
