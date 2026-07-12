import { AgentCard } from "@/components/AgentCard";
import { Badge } from "@/components/ui/badge";
import type { AgentConfig, AgentAnalysis, AgentPhase } from "@shared/schema";
import { cn } from "@/lib/utils";

interface AgentGridProps {
  agents: AgentConfig[];
  analyses: Record<string, AgentAnalysis>;
  analyzingAgents: string[];
}

const phaseOrder: AgentPhase[] = ["sentinel", "strategist", "executioner"];

const phaseConfig: Record<AgentPhase, { label: string; description: string; color: string }> = {
  sentinel: {
    label: "Phase 1: Sentinel",
    description: "Real-time monitoring & initial signal detection",
    color: "bg-blue-500",
  },
  strategist: {
    label: "Phase 2: Strategist",
    description: "Macro analysis & pattern validation",
    color: "bg-purple-500",
  },
  executioner: {
    label: "Phase 3: Executioner",
    description: "Precision entries & risk calculation",
    color: "bg-orange-500",
  },
};

export function AgentGrid({ agents, analyses, analyzingAgents }: AgentGridProps) {
  return (
    <div className="space-y-6" data-testid="grid-agents">
      {phaseOrder.map((phase) => {
        const phaseAgents = agents.filter((a) => a.phase === phase && a.enabled);
        if (phaseAgents.length === 0) return null;

        const config = phaseConfig[phase];
        const isPhaseAnalyzing = phaseAgents.some((a) => analyzingAgents.includes(a.id));

        return (
          <div key={phase} className="space-y-3">
            <div className="flex items-center gap-3">
              <div className={cn(
                "w-1 h-6 rounded-full",
                config.color,
                isPhaseAnalyzing && "animate-pulse"
              )} />
              <div>
                <h3 className="text-sm font-semibold">{config.label}</h3>
                <p className="text-xs text-muted-foreground">{config.description}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {phaseAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  analysis={analyses[agent.id]}
                  isAnalyzing={analyzingAgents.includes(agent.id)}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
