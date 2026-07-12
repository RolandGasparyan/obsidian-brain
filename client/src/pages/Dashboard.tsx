import { useState, useCallback, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { SymbolSelector } from "@/components/SymbolSelector";
import { AgentGrid } from "@/components/AgentGrid";
import { MarketDataPanel } from "@/components/MarketDataPanel";
import { ConsensusPanel } from "@/components/ConsensusPanel";
import { TradeExecutionPanel } from "@/components/TradeExecutionPanel";
import { AnalysisHistory } from "@/components/AnalysisHistory";
import { EnginesPanel } from "@/components/EnginesPanel";
import { WolfPackPanel } from "@/components/WolfPackPanel";
import { ThemeToggle } from "@/components/ThemeToggle";
import { 
  Zap, 
  Activity, 
  Crown,
  RefreshCw,
  Radio,
  AlertTriangle,
  Repeat,
  Square
} from "lucide-react";
import { 
  DEFAULT_AGENTS, 
  WATCHLIST,
  type MarketData, 
  type AgentAnalysis, 
  type ConsensusResult,
  type AnalysisHistory as AnalysisHistoryType
} from "@shared/schema";

export default function Dashboard() {
  const { toast } = useToast();
  const [selectedSymbol, setSelectedSymbol] = useState("BTC/USDT");
  const [analyzingAgents, setAnalyzingAgents] = useState<string[]>([]);
  const [agentAnalyses, setAgentAnalyses] = useState<Record<string, AgentAnalysis>>({});
  const [marketData, setMarketData] = useState<MarketData | undefined>();
  const [consensus, setConsensus] = useState<ConsensusResult | undefined>();
  const [dataSource, setDataSource] = useState<"live" | "simulated">("live");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [autoLoop, setAutoLoop] = useState(false);
  const [symbolIndex, setSymbolIndex] = useState(0);
  const autoLoopRef = useRef(false);

  const historyQuery = useQuery<AnalysisHistoryType[]>({
    queryKey: ["/api/analysis/history"],
  });

  const analyzeMutation = useMutation({
    mutationFn: async (symbol: string) => {
      setAgentAnalyses({});
      setConsensus(undefined);
      setMarketData(undefined);
      setDataSource("live");
      setStatusMessage("");
      setAnalyzingAgents(DEFAULT_AGENTS.map(a => a.id));
      
      const response = await fetch(`/api/analysis/${encodeURIComponent(symbol)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      
      if (!response.ok) {
        throw new Error("Analysis failed");
      }
      
      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");
      
      const decoder = new TextDecoder();
      let buffer = "";
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);
          if (data === "[DONE]") continue;
          
          try {
            const event = JSON.parse(data);
            
            if (event.type === "status") {
              setStatusMessage(event.message);
            } else if (event.type === "market_data") {
              setMarketData(event.data);
              if (event.dataSource) {
                setDataSource(event.dataSource);
              }
              setStatusMessage("");
            } else if (event.type === "agent_start") {
              setAnalyzingAgents(prev => 
                prev.filter(id => id !== event.agentId)
              );
            } else if (event.type === "agent_complete") {
              setAnalyzingAgents(prev => 
                prev.filter(id => id !== event.agentId)
              );
              setAgentAnalyses(prev => ({
                ...prev,
                [event.agentId]: event.analysis,
              }));
            } else if (event.type === "consensus") {
              setConsensus(event.data);
              setAnalyzingAgents([]);
            } else if (event.type === "error") {
              console.error("Analysis error:", event.message);
            }
          } catch (e) {
            console.error("Failed to parse SSE event:", e);
          }
        }
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/analysis/history"] });
      toast({
        title: "Analysis Complete",
        description: `${selectedSymbol} analysis finished successfully`,
      });
    },
    onError: (error: Error) => {
      setAnalyzingAgents([]);
      toast({
        title: "Analysis Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleAnalyze = useCallback(() => {
    if (selectedSymbol) {
      analyzeMutation.mutate(selectedSymbol);
    }
  }, [selectedSymbol, analyzeMutation]);

  const isAnalyzing = analyzeMutation.isPending || analyzingAgents.length > 0;

  useEffect(() => {
    autoLoopRef.current = autoLoop;
  }, [autoLoop]);

  useEffect(() => {
    if (autoLoop && !isAnalyzing && consensus) {
      const nextIndex = (symbolIndex + 1) % WATCHLIST.length;
      setSymbolIndex(nextIndex);
      const nextSymbol = WATCHLIST[nextIndex];
      setSelectedSymbol(nextSymbol);
      
      const timer = setTimeout(() => {
        if (autoLoopRef.current) {
          analyzeMutation.mutate(nextSymbol);
        }
      }, 1000); // TRIPLED CYCLES - 1s delay for max profit
      
      return () => clearTimeout(timer);
    }
  }, [autoLoop, isAnalyzing, consensus, symbolIndex, analyzeMutation]);

  useEffect(() => {
    if (autoLoop && !isAnalyzing && !consensus) {
      analyzeMutation.mutate(selectedSymbol);
    }
  }, [autoLoop]);

  const toggleAutoLoop = useCallback(() => {
    setAutoLoop(prev => !prev);
  }, []);

  return (
    <div className="min-h-screen bg-background trading-grid" data-testid="page-dashboard">
      <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Crown className="h-7 w-7 text-primary" />
                <div>
                  <h1 className="text-lg font-bold leading-tight">Trading Guru</h1>
                  <p className="text-xs text-muted-foreground">God of Gods Level Trading System</p>
                </div>
              </div>
              <Badge variant="outline" className="ml-2 gap-1 bg-primary/10 text-primary border-primary/30">
                <Zap className="h-3 w-3" />
                8 AI Models
              </Badge>
              <Badge variant="outline" className="gap-1 bg-emerald-500/10 text-emerald-500 border-emerald-500/30">
                <Activity className="h-3 w-3" />
                10 Engines
              </Badge>
              {marketData && (
                <Badge 
                  variant="outline" 
                  className={`gap-1 ${
                    dataSource === "live" 
                      ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30" 
                      : "bg-yellow-500/10 text-yellow-500 border-yellow-500/30"
                  }`}
                  data-testid="badge-data-source"
                >
                  {dataSource === "live" ? (
                    <Radio className="h-3 w-3" />
                  ) : (
                    <AlertTriangle className="h-3 w-3" />
                  )}
                  {dataSource === "live" ? "Live Data" : "Simulated"}
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-4">
              <SymbolSelector
                selectedSymbol={selectedSymbol}
                onSymbolChange={setSelectedSymbol}
                onAnalyze={handleAnalyze}
                isAnalyzing={isAnalyzing}
              />
              <Button
                onClick={toggleAutoLoop}
                variant={autoLoop ? "destructive" : "outline"}
                size="sm"
                className="gap-2"
                data-testid="button-autoloop"
              >
                {autoLoop ? (
                  <>
                    <Square className="h-4 w-4" />
                    Stop 24/7
                  </>
                ) : (
                  <>
                    <Repeat className="h-4 w-4" />
                    24/7 Loop
                  </>
                )}
              </Button>
              {autoLoop && (
                <Badge 
                  variant="outline" 
                  className="gap-1 bg-amber-500/10 text-amber-500 border-amber-500/30 animate-pulse"
                  data-testid="badge-autoloop"
                >
                  <Repeat className="h-3 w-3 animate-spin" />
                  Auto-Analyzing ({symbolIndex + 1}/{WATCHLIST.length})
                </Badge>
              )}
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            <AgentGrid
              agents={DEFAULT_AGENTS}
              analyses={agentAnalyses}
              analyzingAgents={analyzingAgents}
            />
          </div>
          
          <div className="lg:col-span-4 space-y-6">
            <ConsensusPanel 
              consensus={consensus}
              isLoading={isAnalyzing && !consensus}
            />
            {consensus && (
              <TradeExecutionPanel 
                consensus={consensus}
                symbol={selectedSymbol}
              />
            )}
            <MarketDataPanel 
              data={marketData}
              isLoading={isAnalyzing && !marketData}
            />
            <EnginesPanel />
            <WolfPackPanel />
            <AnalysisHistory 
              history={historyQuery.data || []}
              isLoading={historyQuery.isLoading}
            />
          </div>
        </div>
      </main>

      <footer className="border-t border-border mt-12">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <Activity className="h-3 w-3 text-emerald-500" />
              <span>System Online</span>
            </div>
            <p>Trading Guru - AI-Powered Market Analysis</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
