import time
import random
from typing import List
from trading_guru.core.config import config
from trading_guru.core.models import OrchestratorState, MarketData, PairScore, TradeSignal
from trading_guru.utils.market_utils import get_mock_market_data, get_all_mock_pairs, calculate_pair_score, get_recommended_strategy
from trading_guru.agents.llm_agent import ALL_AGENTS

class GodsModeOrchestrator:
    def __init__(self):
        self.state = OrchestratorState(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            active_pairs=[],
            pair_scores=[],
            active_trades=[],
            daily_pnl=0.0,
            risk_level=config.RISK_PROFILE
        )
        self.current_trading_pair = None
        self.trade_count = 0
        self.strategy_pnl = {"waterfall": 0.0, "doubling": 0.0, "snowball": 0.0, "scalping": 0.0}
        print(f"Orchestrator initialized in {config.TRADING_DIRECTION} {config.RISK_PROFILE} mode.")

    def _run_pair_scanner(self) -> List[PairScore]:
        """Runs the AI-powered pair scanner, only scoring for short potential."""
        print("\n--- Running Master Pair Scanner (AI Confluence) for SHORTS ---")
        all_pairs = get_all_mock_pairs()
        pair_results = []

        for symbol in all_pairs:
            market_data = get_mock_market_data(symbol)
            
            base_score = calculate_pair_score(market_data)
            
            agent_signals = []
            total_agent_score = 0
            
            for agent in ALL_AGENTS:
                agent_result = agent.analyze(market_data, "Pair Scanning Context")
                agent_signals.append(agent_result["signal"])
                total_agent_score += agent_result["score"]
            
            final_score = int((base_score + (total_agent_score / len(ALL_AGENTS))) / 2)
            
            final_signal = random.choice(agent_signals)
            
            pair_score = PairScore(
                symbol=symbol,
                total_score=final_score,
                scores={"base": base_score, "agent_avg": int(total_agent_score / len(ALL_AGENTS))},
                recommended_strategy=get_recommended_strategy(final_score, market_data),
                signal=final_signal
            )
            pair_results.append(pair_score)

        pair_results.sort(key=lambda x: x.total_score, reverse=True)
        self.state.pair_scores = pair_results[:5]
        return self.state.pair_scores

    def _run_rotation_engine(self, top_pairs: List[PairScore]):
        """Manages the intelligent pair rotation."""
        
        if not top_pairs or top_pairs[0].total_score < config.MIN_CONFLUENCE_SCORE:
            print("No high-confidence short setups found. Pausing trading.")
            self.current_trading_pair = None
            return

        best_pair = top_pairs[0]
        
        if self.current_trading_pair is None:
            self.current_trading_pair = best_pair
            print(f"Initial SHORT selection: {best_pair.symbol} (Score: {best_pair.total_score})")
            return

        current_score = next((p.total_score for p in top_pairs if p.symbol == self.current_trading_pair.symbol), 0)
        
        if best_pair.total_score > current_score + config.ROTATION_THRESHOLD:
            print(f"ROTATION TRIGGERED: {best_pair.symbol} ({best_pair.total_score}) is significantly better for SHORTING than {self.current_trading_pair.symbol} ({current_score}).")
            self.current_trading_pair = best_pair
            print(f"Switched to: {best_pair.symbol}. Strategy: {best_pair.recommended_strategy}")
        else:
            print(f"Staying on {self.current_trading_pair.symbol}. Best alternative score: {best_pair.total_score}. Difference too small.")

    def _execute_strategy(self):
        """Executes the recommended strategy on the current pair."""
        if not self.current_trading_pair:
            return

        pair = self.current_trading_pair
        signal = pair.signal
        
        self.trade_count += 1
        
        strategy = pair.recommended_strategy
        
        if random.random() < 0.85: 
            pnl_percent = random.uniform(0.001, 0.003) 
            pnl_usd = signal.entry_size_usd * pnl_percent * config.MAX_LEVERAGE
            self.state.daily_pnl += pnl_usd
            self.strategy_pnl[strategy] += pnl_usd
            status = "WIN"
        else:
            loss_percent = random.uniform(0.0005, 0.001) 
            pnl_usd = signal.entry_size_usd * loss_percent * config.MAX_LEVERAGE
            self.state.daily_pnl -= pnl_usd
            self.strategy_pnl[strategy] -= pnl_usd
            status = "LOSS"
            
        print(f"\n--- Trade #{self.trade_count}: {strategy.upper()} ({status}) on {pair.symbol} ---")
        print(f"  Entry Size: ${signal.entry_size_usd:.2f} | PNL USD: ${pnl_usd:.2f} | Total PNL: ${self.state.daily_pnl:.2f}")
        
        if strategy == "snowball" and status == "WIN":
            config.MIN_ENTRY_SIZE_USD = min(config.MIN_ENTRY_SIZE_USD + pnl_usd, 10.0)
            print(f"  [SNOWBALL] New Min Entry Size: ${config.MIN_ENTRY_SIZE_USD:.2f}")
        elif strategy == "doubling" and status == "LOSS":
            config.MIN_ENTRY_SIZE_USD = min(config.MIN_ENTRY_SIZE_USD * 2, 20.0)
            print(f"  [DOUBLING] Increased Min Entry Size: ${config.MIN_ENTRY_SIZE_USD:.2f}")
        elif strategy == "doubling" and status == "WIN":
            config.MIN_ENTRY_SIZE_USD = 1.0
            print(f"  [DOUBLING] Reset Min Entry Size: ${config.MIN_ENTRY_SIZE_USD:.2f}")
        
    def run_loop(self):
        """The main high-frequency trading loop."""
        print("Starting Trinity of Profit Orchestrator Loop...")
        
        while True:
            self.state.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            top_pairs = self._run_pair_scanner()
            
            self._run_rotation_engine(top_pairs)
            
            if self.current_trading_pair:
                self._execute_strategy()
            
            print(f"\n[ORCHESTRATOR STATUS @ {self.state.timestamp}]")
            print(f"  Total Trades: {self.trade_count}")
            print(f"  Current Short Pair: {self.current_trading_pair.symbol if self.current_trading_pair else 'NONE'}")
            print(f"  Daily PNL: ${self.state.daily_pnl:.2f}")
            print(f"  Strategy PNL: {self.strategy_pnl}")
            
            time.sleep(config.SCAN_INTERVAL_SECONDS)
