import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Wallet,
  Zap,
  ArrowRightLeft,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { ConsensusResult } from "@shared/schema";

interface TradeExecutionPanelProps {
  consensus: ConsensusResult;
  symbol: string;
}

interface BalanceResponse {
  futures: {
    available: number;
    total: number;
    unrealizedPnl: number;
    currency: string;
  };
  spot: {
    available: number;
    locked: number;
    currency: string;
  };
}

interface Position {
  contract: string;
  size: number;
  leverage: number;
  entryPrice: number;
  markPrice: number;
  unrealizedPnl: number;
  margin: number;
}

export function TradeExecutionPanel({ consensus, symbol }: TradeExecutionPanelProps) {
  const { toast } = useToast();
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [showTransferDialog, setShowTransferDialog] = useState(false);
  const [tradeSize, setTradeSize] = useState("10");
  const [transferAmount, setTransferAmount] = useState("");

  const { data: balance, isLoading: balanceLoading } = useQuery<BalanceResponse>({
    queryKey: ["/api/trading/balance"],
    refetchInterval: 30000,
  });

  const { data: positions = [], isLoading: positionsLoading } = useQuery<Position[]>({
    queryKey: ["/api/trading/positions"],
    refetchInterval: 10000,
  });

  const transferMutation = useMutation({
    mutationFn: async (params: { amount: number; from: string; to: string }) => {
      const response = await apiRequest("POST", "/api/trading/transfer", params);
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Transfer Complete",
        description: "Funds transferred successfully",
      });
      queryClient.invalidateQueries({ queryKey: ["/api/trading/balance"] });
      setShowTransferDialog(false);
      setTransferAmount("");
    },
    onError: (error: Error) => {
      toast({
        title: "Transfer Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const executeTradeMutation = useMutation({
    mutationFn: async (params: {
      symbol: string;
      side: "buy" | "sell";
      amount: number;
    }) => {
      const response = await apiRequest("POST", "/api/trading/spot", params);
      return response.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Trade Executed",
        description: data.message,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/trading/positions"] });
      queryClient.invalidateQueries({ queryKey: ["/api/trading/balance"] });
      setShowConfirmDialog(false);
    },
    onError: (error: Error) => {
      toast({
        title: "Trade Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const closePositionMutation = useMutation({
    mutationFn: async (contract: string) => {
      const response = await apiRequest("POST", "/api/trading/close", { contract });
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Position Closed",
        description: "Your position has been closed successfully",
      });
      queryClient.invalidateQueries({ queryKey: ["/api/trading/positions"] });
      queryClient.invalidateQueries({ queryKey: ["/api/trading/balance"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Close Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const currentPosition = positions.find(
    (p) => p.contract === symbol.replace("/", "_")
  );

  // Spot trading mode - buy or sell
  const canTrade = consensus.verdict === "EXECUTE" || consensus.verdict === "WAIT";
  const [tradeSide, setTradeSide] = useState<"buy" | "sell">("buy");

  const handleExecuteTrade = () => {
    const amount = parseFloat(tradeSize);

    if (isNaN(amount) || amount <= 0) {
      toast({
        title: "Invalid Amount",
        description: "Please enter a valid trade amount",
        variant: "destructive",
      });
      return;
    }

    executeTradeMutation.mutate({
      symbol,
      side: tradeSide,
      amount,
    });
  };

  const handleTransfer = () => {
    const amount = parseFloat(transferAmount);
    if (isNaN(amount) || amount <= 0) {
      toast({
        title: "Invalid Amount",
        description: "Please enter a valid transfer amount",
        variant: "destructive",
      });
      return;
    }
    transferMutation.mutate({ amount, from: "spot", to: "futures" });
  };

  const handleTransferAll = () => {
    if (balance?.spot.available && balance.spot.available > 0) {
      transferMutation.mutate({ 
        amount: balance.spot.available, 
        from: "spot", 
        to: "futures" 
      });
    }
  };

  return (
    <Card className="border-primary/30" data-testid="panel-trade-execution">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg flex-wrap">
          <Zap className="h-5 w-5 text-primary" />
          Spot Trading
          <Badge variant="secondary" className="text-xs">BUY / SELL</Badge>
          <div className="flex items-center gap-2 ml-auto">
            {balance && (
              <>
                <Badge variant="outline" className="font-mono text-xs">
                  <Wallet className="h-3 w-3 mr-1" />
                  Futures: ${balance.futures.available.toFixed(2)}
                </Badge>
                <Badge variant="secondary" className="font-mono text-xs">
                  Spot: ${balance.spot.available.toFixed(2)}
                </Badge>
                {balance.spot.available > 0 && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowTransferDialog(true)}
                    className="h-6 text-xs px-2"
                    data-testid="button-open-transfer"
                  >
                    <ArrowRightLeft className="h-3 w-3 mr-1" />
                    Transfer
                  </Button>
                )}
              </>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {currentPosition && (
          <div className="p-3 rounded-lg bg-muted/50 border border-border">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Open Position</span>
              <Badge
                variant="outline"
                className={cn(
                  currentPosition.size > 0 ? "text-emerald-500" : "text-rose-500"
                )}
              >
                {currentPosition.size > 0 ? "LONG" : "SHORT"}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Size:</span>{" "}
                <span className="font-mono">{Math.abs(currentPosition.size)}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Entry:</span>{" "}
                <span className="font-mono">${currentPosition.entryPrice.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-muted-foreground">PnL:</span>{" "}
                <span
                  className={cn(
                    "font-mono",
                    currentPosition.unrealizedPnl >= 0 ? "text-emerald-500" : "text-rose-500"
                  )}
                >
                  ${currentPosition.unrealizedPnl.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Leverage:</span>{" "}
                <span className="font-mono">{currentPosition.leverage}x</span>
              </div>
            </div>
            <Button
              variant="destructive"
              size="sm"
              className="w-full mt-3"
              onClick={() => closePositionMutation.mutate(currentPosition.contract)}
              disabled={closePositionMutation.isPending}
              data-testid="button-close-position"
            >
              {closePositionMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <XCircle className="h-4 w-4 mr-2" />
              )}
              Close Position
            </Button>
          </div>
        )}

        {!currentPosition && (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="tradeSize" className="text-xs">
                Amount (USDT)
              </Label>
              <Input
                id="tradeSize"
                type="number"
                value={tradeSize}
                onChange={(e) => setTradeSize(e.target.value)}
                placeholder="10"
                className="font-mono"
                data-testid="input-trade-size"
              />
            </div>

            {consensus.killZone && (
              <div className="grid grid-cols-3 gap-2 p-2 rounded-lg bg-muted/30 text-center">
                <div>
                  <p className="text-[10px] text-muted-foreground">Entry</p>
                  <p className="text-xs font-mono text-primary">
                    ${consensus.killZone.optimal.toLocaleString()}
                  </p>
                </div>
                {consensus.invalidation && (
                  <div>
                    <p className="text-[10px] text-muted-foreground">Stop</p>
                    <p className="text-xs font-mono text-rose-500">
                      ${consensus.invalidation.price.toLocaleString()}
                    </p>
                  </div>
                )}
                {consensus.targets?.tp1 && (
                  <div>
                    <p className="text-[10px] text-muted-foreground">TP1</p>
                    <p className="text-xs font-mono text-emerald-500">
                      ${consensus.targets.tp1.price.toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <Button
                className="w-full bg-green-600 hover:bg-green-700"
                disabled={!canTrade || executeTradeMutation.isPending}
                onClick={() => {
                  setTradeSide("buy");
                  setShowConfirmDialog(true);
                }}
                data-testid="button-buy"
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                BUY
              </Button>
              <Button
                className="w-full bg-rose-600 hover:bg-rose-700"
                disabled={!canTrade || executeTradeMutation.isPending}
                onClick={() => {
                  setTradeSide("sell");
                  setShowConfirmDialog(true);
                }}
                data-testid="button-sell"
              >
                <TrendingDown className="h-4 w-4 mr-2" />
                SELL
              </Button>
            </div>

            {!canTrade && (
              <p className="text-xs text-center text-muted-foreground">
                Run analysis first to enable trading
              </p>
            )}
            
            <p className="text-xs text-center text-primary/80 font-medium">
              Spot Trading - Buy low, sell high
            </p>
          </>
        )}
      </CardContent>

      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Confirm Trade Execution
            </DialogTitle>
            <DialogDescription>
              You are about to execute a real trade on Gate.io. This will use actual
              funds from your account.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-4">
            <div className="flex justify-between items-center p-3 rounded-lg bg-muted/50">
              <span className="text-sm text-muted-foreground">Action</span>
              <Badge className={tradeSide === "buy" ? "bg-green-500" : "bg-rose-500"}>
                {tradeSide.toUpperCase()}
              </Badge>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-muted/50">
              <span className="text-sm text-muted-foreground">Symbol</span>
              <span className="font-mono font-medium">{symbol}</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-muted/50">
              <span className="text-sm text-muted-foreground">Amount</span>
              <span className="font-mono font-medium">${tradeSize} USDT</span>
            </div>
            {consensus.killZone && (
              <div className="flex justify-between items-center p-3 rounded-lg bg-muted/50">
                <span className="text-sm text-muted-foreground">Current Price</span>
                <span className="font-mono font-medium text-primary">
                  ${consensus.killZone.optimal.toLocaleString()}
                </span>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowConfirmDialog(false)}
              data-testid="button-cancel-trade"
            >
              Cancel
            </Button>
            <Button
              className={tradeSide === "buy" ? "bg-green-600 hover:bg-green-700" : "bg-rose-600 hover:bg-rose-700"}
              onClick={handleExecuteTrade}
              disabled={executeTradeMutation.isPending}
              data-testid="button-confirm-trade"
            >
              {executeTradeMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CheckCircle2 className="h-4 w-4 mr-2" />
              )}
              Confirm {tradeSide.toUpperCase()}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showTransferDialog} onOpenChange={setShowTransferDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ArrowRightLeft className="h-5 w-5 text-primary" />
              Transfer Funds
            </DialogTitle>
            <DialogDescription>
              Transfer USDT from your Spot wallet to Futures wallet for trading.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-xs text-muted-foreground mb-1">Spot Balance</p>
                <p className="font-mono font-medium text-lg">
                  ${balance?.spot.available.toFixed(2) || "0.00"}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-xs text-muted-foreground mb-1">Futures Balance</p>
                <p className="font-mono font-medium text-lg text-primary">
                  ${balance?.futures.available.toFixed(2) || "0.00"}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="transferAmount">Amount to Transfer (USDT)</Label>
              <div className="flex gap-2">
                <Input
                  id="transferAmount"
                  type="number"
                  value={transferAmount}
                  onChange={(e) => setTransferAmount(e.target.value)}
                  placeholder="Enter amount"
                  className="font-mono"
                  data-testid="input-transfer-amount"
                />
                <Button
                  variant="outline"
                  onClick={() => setTransferAmount(balance?.spot.available.toString() || "0")}
                  data-testid="button-max-transfer"
                >
                  MAX
                </Button>
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setShowTransferDialog(false)}
              data-testid="button-cancel-transfer"
            >
              Cancel
            </Button>
            <Button
              variant="secondary"
              onClick={handleTransferAll}
              disabled={transferMutation.isPending || !balance?.spot.available}
              data-testid="button-transfer-all"
            >
              {transferMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Transfer All
            </Button>
            <Button
              onClick={handleTransfer}
              disabled={transferMutation.isPending || !transferAmount}
              data-testid="button-confirm-transfer"
            >
              {transferMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CheckCircle2 className="h-4 w-4 mr-2" />
              )}
              Transfer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
