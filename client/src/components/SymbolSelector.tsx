import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Play, Loader2, RefreshCw } from "lucide-react";
import { WATCHLIST } from "@shared/schema";
import { cn } from "@/lib/utils";

interface SymbolSelectorProps {
  selectedSymbol: string;
  onSymbolChange: (symbol: string) => void;
  onAnalyze: () => void;
  isAnalyzing: boolean;
}

export function SymbolSelector({
  selectedSymbol,
  onSymbolChange,
  onAnalyze,
  isAnalyzing,
}: SymbolSelectorProps) {
  return (
    <div className="flex items-center gap-3">
      <Select value={selectedSymbol} onValueChange={onSymbolChange}>
        <SelectTrigger 
          className="w-[180px] font-mono"
          data-testid="select-symbol"
        >
          <SelectValue placeholder="Select symbol" />
        </SelectTrigger>
        <SelectContent>
          {WATCHLIST.map((symbol) => (
            <SelectItem 
              key={symbol} 
              value={symbol}
              data-testid={`option-symbol-${symbol.replace("/", "-")}`}
            >
              {symbol}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button
        onClick={onAnalyze}
        disabled={!selectedSymbol || isAnalyzing}
        className={cn(
          "gap-2 min-w-[140px]",
          isAnalyzing && "animate-pulse-slow"
        )}
        data-testid="button-analyze"
      >
        {isAnalyzing ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Analyzing...
          </>
        ) : (
          <>
            <Play className="h-4 w-4" />
            Run Analysis
          </>
        )}
      </Button>
    </div>
  );
}
