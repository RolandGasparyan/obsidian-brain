import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Leaderboard } from "@/components/Leaderboard";
import { LiveTradeFeed } from "@/components/LiveTradeFeed";
import { MarketScanner } from "@/components/MarketScanner";
import { AIvsHuman } from "@/components/AIvsHuman";
import { AICompetitionLeaderboard } from "@/components/AICompetitionLeaderboard";
import { Play, Square, RefreshCw, Trophy, Activity, Radar, Bot, Zap } from "lucide-react";

export function TradingRace() {
  const { toast } = useToast();
  const [engineStatus, setEngineStatus] = useState<"stopped" | "running" | "initializing">("stopped");

  const initMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/trading-engine/initialize");
      return res.json();
    },
    onSuccess: (data: any) => {
      toast({ title: "AI Models Initialized", description: `${data.models?.length || 8} AI models ready to trade` });
      queryClient.invalidateQueries({ queryKey: ["/api/leaderboard"] });
      queryClient.invalidateQueries({ queryKey: ["/api/ai-models"] });
    },
    onError: (error: Error) => {
      toast({ title: "Initialization Failed", description: error.message, variant: "destructive" });
    }
  });

  const startMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/trading-engine/start"),
    onSuccess: () => {
      setEngineStatus("running");
      toast({ title: "Trading Engine Started", description: "8 AI models are now trading in real-time" });
    },
    onError: (error: Error) => {
      toast({ title: "Start Failed", description: error.message, variant: "destructive" });
    }
  });

  const stopMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/trading-engine/stop"),
    onSuccess: () => {
      setEngineStatus("stopped");
      toast({ title: "Trading Engine Stopped", description: "All AI models paused" });
    },
    onError: (error: Error) => {
      toast({ title: "Stop Failed", description: error.message, variant: "destructive" });
    }
  });

  return (
    <div className="min-h-screen bg-background p-4" data-testid="trading-race-page">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3" data-testid="page-title">
              <Trophy className="w-8 h-8 text-yellow-400" />
              AI Trading Race
            </h1>
            <p className="text-muted-foreground mt-1" data-testid="page-subtitle">
              8 AI Models competing for the #1 spot - Real-time trading on Gate.io
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Badge
              className={`${
                engineStatus === "running"
                  ? "bg-green-900/50 text-green-300"
                  : engineStatus === "initializing"
                  ? "bg-yellow-900/50 text-yellow-300"
                  : "bg-gray-800 text-gray-400"
              }`}
              data-testid="engine-status"
            >
              <span className={`w-2 h-2 rounded-full mr-2 ${
                engineStatus === "running" ? "bg-green-400 animate-pulse" : "bg-gray-500"
              }`} />
              {engineStatus === "running" ? "Racing" : engineStatus === "initializing" ? "Initializing" : "Stopped"}
            </Badge>

            <Button
              variant="outline"
              size="sm"
              onClick={() => initMutation.mutate()}
              disabled={initMutation.isPending}
              data-testid="button-initialize"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${initMutation.isPending ? "animate-spin" : ""}`} />
              Initialize
            </Button>

            {engineStatus === "running" ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => stopMutation.mutate()}
                disabled={stopMutation.isPending}
                data-testid="button-stop-engine"
              >
                <Square className="w-4 h-4 mr-2" />
                Stop
              </Button>
            ) : (
              <Button
                variant="default"
                size="sm"
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
                data-testid="button-start-engine"
              >
                <Play className="w-4 h-4 mr-2" />
                Start Race
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <Card className="bg-gradient-to-br from-cyan-900/30 to-transparent" data-testid="stat-ai-models">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Bot className="w-8 h-8 text-cyan-400" />
                <div>
                  <div className="text-2xl font-bold" data-testid="stat-ai-models-value">8</div>
                  <div className="text-xs text-muted-foreground">AI Models</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-900/30 to-transparent" data-testid="stat-trading">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Activity className="w-8 h-8 text-green-400" />
                <div>
                  <div className="text-2xl font-bold" data-testid="stat-trading-value">24/7</div>
                  <div className="text-xs text-muted-foreground">Trading</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-yellow-900/30 to-transparent" data-testid="stat-direction">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Zap className="w-8 h-8 text-yellow-400" />
                <div>
                  <div className="text-2xl font-bold" data-testid="stat-direction-value">SHORTS</div>
                  <div className="text-xs text-muted-foreground">Only Mode</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-900/30 to-transparent" data-testid="stat-consensus">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Radar className="w-8 h-8 text-purple-400" />
                <div>
                  <div className="text-2xl font-bold" data-testid="stat-consensus-value">6/8</div>
                  <div className="text-xs text-muted-foreground">Consensus</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <AICompetitionLeaderboard />

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-6">
            <Leaderboard />
            <LiveTradeFeed />
          </div>

          <div className="space-y-6">
            <AIvsHuman />
            <MarketScanner />
          </div>
        </div>
      </div>
    </div>
  );
}

export default TradingRace;
