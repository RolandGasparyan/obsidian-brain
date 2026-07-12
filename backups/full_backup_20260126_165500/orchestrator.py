"""
Trading Guru - God of Gods Orchestrator
The master controller that coordinates all AI agents and synthesizes their analyses.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .config import config, TradingConfig
from .models import (
    AgentAnalysis, 
    ConsensusResult, 
    TradeSignal,
    MarketData
)
from ..agents import (
    create_deepseek_agent,
    create_gpt5_agent,
    create_claude_agent,
    create_grok_agent,
    create_llama_agent,
    create_qwen_agent,
    BaseAgent
)
from ..utils.market_utils import (
    generate_mock_market_data,
    generate_mock_onchain_data,
    generate_mock_sentiment_data,
    format_market_data_for_prompt
)


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    min_consensus_agents: int = 4
    confluence_threshold: float = 0.7
    min_risk_reward: float = 2.0
    max_position_size_pct: float = 5.0
    enable_parallel_analysis: bool = True


class GodOfGodsOrchestrator:
    """
    The God of Gods - Master Controller
    
    Coordinates all six AI agents and synthesizes their analyses into
    actionable trade signals.
    
    Workflow:
    1. Phase 1 (Sentinels): Grok & Llama scan for immediate opportunities
    2. Phase 2 (Strategists): GPT-5 & Claude provide macro/psychological overlay
    3. Phase 3 (Executioners): DeepSeek & Qwen calculate precise levels
    4. Phase 4 (Synthesis): Combine all analyses into consensus
    """
    
    def __init__(self, orchestrator_config: OrchestratorConfig = None):
        self.config = orchestrator_config or OrchestratorConfig()
        
        # Initialize all agents
        self.agents: Dict[str, BaseAgent] = {
            "deepseek": create_deepseek_agent(),
            "gpt5": create_gpt5_agent(),
            "claude": create_claude_agent(),
            "grok": create_grok_agent(),
            "llama": create_llama_agent(),
            "qwen": create_qwen_agent(),
        }
        
        # Agent groupings
        self.sentinels = ["grok", "llama"]
        self.strategists = ["gpt5", "claude"]
        self.executioners = ["deepseek", "qwen"]
        
        # Analysis history
        self.analysis_history: List[ConsensusResult] = []
        self.signal_history: List[TradeSignal] = []
        
        # Status
        self.is_running = False
        self.last_analysis_time: Optional[datetime] = None
    
    async def analyze_market(
        self, 
        symbol: str = "BTC/USDT",
        market_data: dict = None,
        onchain_data: dict = None,
        sentiment_data: dict = None
    ) -> ConsensusResult:
        """
        Perform full market analysis using all agents.
        
        Args:
            symbol: Trading pair to analyze
            market_data: Market data dict (will generate mock if None)
            onchain_data: On-chain data dict (will generate mock if None)
            sentiment_data: Sentiment data dict (will generate mock if None)
        
        Returns:
            ConsensusResult with synthesized analysis
        """
        self.is_running = True
        
        # Generate mock data if not provided
        if market_data is None:
            market_data = generate_mock_market_data(symbol)
        if onchain_data is None:
            onchain_data = generate_mock_onchain_data(symbol.split('/')[0])
        if sentiment_data is None:
            sentiment_data = generate_mock_sentiment_data(symbol.split('/')[0])
        
        print(f"\n{'='*60}")
        print(f"🔮 GOD OF GODS ANALYSIS INITIATED")
        print(f"📊 Symbol: {symbol}")
        print(f"💰 Current Price: ${market_data.get('current_price', 0):,.2f}")
        print(f"{'='*60}\n")
        
        # Phase 1: Sentinels (Real-time scan)
        print("📡 PHASE 1: SENTINEL SCAN (Grok & Llama)")
        sentinel_analyses = await self._run_phase(
            self.sentinels, 
            market_data, 
            onchain_data, 
            sentiment_data
        )
        
        # Phase 2: Strategists (Macro overlay)
        print("\n🎯 PHASE 2: STRATEGIC OVERLAY (GPT-5 & Claude)")
        strategist_analyses = await self._run_phase(
            self.strategists,
            market_data,
            onchain_data,
            sentiment_data
        )
        
        # Phase 3: Executioners (Precise levels)
        print("\n⚔️ PHASE 3: EXECUTION PLANNING (DeepSeek & Qwen)")
        executioner_analyses = await self._run_phase(
            self.executioners,
            market_data,
            onchain_data,
            sentiment_data
        )
        
        # Combine all analyses
        all_analyses = sentinel_analyses + strategist_analyses + executioner_analyses
        
        # Phase 4: Synthesis
        print("\n🧠 PHASE 4: CONSENSUS SYNTHESIS")
        consensus = self._synthesize_consensus(symbol, all_analyses, market_data)
        
        # Store in history
        self.analysis_history.append(consensus)
        self.last_analysis_time = datetime.now()
        self.is_running = False
        
        return consensus
    
    async def _run_phase(
        self,
        agent_names: List[str],
        market_data: dict,
        onchain_data: dict,
        sentiment_data: dict
    ) -> List[AgentAnalysis]:
        """Run analysis for a group of agents."""
        analyses = []
        
        if self.config.enable_parallel_analysis:
            # Run agents in parallel
            tasks = []
            for name in agent_names:
                agent = self.agents.get(name)
                if agent and agent.config.enabled:
                    tasks.append(
                        agent.analyze(
                            market_data,
                            onchain_data=onchain_data,
                            sentiment_data=sentiment_data
                        )
                    )
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, AgentAnalysis):
                        analyses.append(result)
                        self._print_agent_result(result)
                    elif isinstance(result, Exception):
                        print(f"  ❌ Agent error: {result}")
        else:
            # Run agents sequentially
            for name in agent_names:
                agent = self.agents.get(name)
                if agent and agent.config.enabled:
                    try:
                        result = await agent.analyze(
                            market_data,
                            onchain_data=onchain_data,
                            sentiment_data=sentiment_data
                        )
                        analyses.append(result)
                        self._print_agent_result(result)
                    except Exception as e:
                        print(f"  ❌ {agent.name} error: {e}")
        
        return analyses
    
    def _print_agent_result(self, analysis: AgentAnalysis):
        """Print agent analysis result."""
        signal_emoji = {
            "short": "🔴",
            "long": "🟢",
            "neutral": "⚪"
        }
        emoji = signal_emoji.get(analysis.signal, "⚪")
        
        print(f"  {emoji} {analysis.agent_name} ({analysis.agent_role}):")
        print(f"     Signal: {analysis.signal.upper()} | Confidence: {analysis.confidence:.0%}")
        if analysis.entry_price:
            print(f"     Entry: ${analysis.entry_price:,.2f}")
        if analysis.key_findings:
            print(f"     Key Finding: {analysis.key_findings[0][:60]}...")
    
    def _synthesize_consensus(
        self,
        symbol: str,
        analyses: List[AgentAnalysis],
        market_data: dict
    ) -> ConsensusResult:
        """Synthesize all agent analyses into a consensus result."""
        
        # Count signals
        signal_counts = {"short": 0, "long": 0, "neutral": 0}
        weighted_confidence = {"short": 0.0, "long": 0.0, "neutral": 0.0}
        
        for analysis in analyses:
            signal = analysis.signal.lower()
            if signal in signal_counts:
                signal_counts[signal] += 1
                weighted_confidence[signal] += analysis.confidence
        
        # Determine consensus signal
        if signal_counts["short"] >= signal_counts["long"] and signal_counts["short"] > signal_counts["neutral"]:
            consensus_signal = "short"
            agreeing_agents = signal_counts["short"]
        elif signal_counts["long"] > signal_counts["short"] and signal_counts["long"] > signal_counts["neutral"]:
            consensus_signal = "long"
            agreeing_agents = signal_counts["long"]
        else:
            consensus_signal = "neutral"
            agreeing_agents = signal_counts["neutral"]
        
        # Calculate confluence score
        total_agents = len(analyses)
        confluence_score = agreeing_agents / total_agents if total_agents > 0 else 0
        
        # Aggregate trade levels from agreeing agents
        entry_prices = []
        stop_losses = []
        targets_1 = []
        targets_2 = []
        
        for analysis in analyses:
            if analysis.signal.lower() == consensus_signal:
                if analysis.entry_price:
                    entry_prices.append(analysis.entry_price)
                if analysis.stop_loss:
                    stop_losses.append(analysis.stop_loss)
                if analysis.target_1:
                    targets_1.append(analysis.target_1)
                if analysis.target_2:
                    targets_2.append(analysis.target_2)
        
        # Calculate average levels
        avg_entry = sum(entry_prices) / len(entry_prices) if entry_prices else None
        avg_stop = sum(stop_losses) / len(stop_losses) if stop_losses else None
        avg_target1 = sum(targets_1) / len(targets_1) if targets_1 else None
        avg_target2 = sum(targets_2) / len(targets_2) if targets_2 else None
        
        # Calculate risk-reward if we have entry and targets
        risk_reward = None
        if avg_entry and avg_stop and avg_target1:
            risk = abs(avg_entry - avg_stop)
            reward = abs(avg_target1 - avg_entry)
            risk_reward = reward / risk if risk > 0 else 0
        
        # Create entry zone
        entry_zone_high = max(entry_prices) if entry_prices else None
        entry_zone_low = min(entry_prices) if entry_prices else None
        
        consensus = ConsensusResult(
            timestamp=datetime.now(),
            symbol=symbol,
            total_agents=total_agents,
            agreeing_agents=agreeing_agents,
            consensus_signal=consensus_signal,
            confluence_score=confluence_score,
            agent_analyses=analyses,
            entry_zone_high=entry_zone_high,
            entry_zone_low=entry_zone_low,
            invalidation_level=avg_stop,
            primary_target=avg_target1,
            secondary_target=avg_target2,
            risk_reward_ratio=risk_reward,
            position_size_recommendation=self._calculate_position_size(confluence_score)
        )
        
        # Print consensus summary
        self._print_consensus_summary(consensus)
        
        return consensus
    
    def _calculate_position_size(self, confluence_score: float) -> float:
        """Calculate recommended position size based on confluence."""
        base_size = self.config.max_position_size_pct
        
        if confluence_score >= 0.9:
            return base_size
        elif confluence_score >= 0.8:
            return base_size * 0.8
        elif confluence_score >= 0.7:
            return base_size * 0.6
        elif confluence_score >= 0.6:
            return base_size * 0.4
        else:
            return base_size * 0.2
    
    def _print_consensus_summary(self, consensus: ConsensusResult):
        """Print the consensus summary."""
        print(f"\n{'='*60}")
        print(f"📊 CONSENSUS RESULT")
        print(f"{'='*60}")
        
        signal_emoji = {"short": "🔴", "long": "🟢", "neutral": "⚪"}
        emoji = signal_emoji.get(consensus.consensus_signal, "⚪")
        
        print(f"\n{emoji} SIGNAL: {consensus.consensus_signal.upper()}")
        print(f"📈 Confluence Score: {consensus.confluence_score:.0%} ({consensus.agreeing_agents}/{consensus.total_agents} agents)")
        print(f"✅ Actionable: {'YES' if consensus.is_actionable else 'NO'}")
        
        if consensus.entry_zone_low and consensus.entry_zone_high:
            print(f"\n💰 Entry Zone: ${consensus.entry_zone_low:,.2f} - ${consensus.entry_zone_high:,.2f}")
        if consensus.invalidation_level:
            print(f"🛑 Invalidation: ${consensus.invalidation_level:,.2f}")
        if consensus.primary_target:
            print(f"🎯 Target 1: ${consensus.primary_target:,.2f}")
        if consensus.secondary_target:
            print(f"🎯 Target 2: ${consensus.secondary_target:,.2f}")
        if consensus.risk_reward_ratio:
            print(f"📊 Risk/Reward: 1:{consensus.risk_reward_ratio:.1f}")
        if consensus.position_size_recommendation:
            print(f"💼 Position Size: {consensus.position_size_recommendation:.1f}% of portfolio")
        
        print(f"\n{'='*60}\n")
    
    def generate_trade_signal(self, consensus: ConsensusResult) -> Optional[TradeSignal]:
        """
        Generate a trade signal from consensus if actionable.
        
        Args:
            consensus: The consensus result to evaluate
            
        Returns:
            TradeSignal if actionable, None otherwise
        """
        if not consensus.is_actionable:
            print("⚠️ Consensus not actionable - insufficient agreement or confidence")
            return None
        
        if consensus.consensus_signal == "neutral":
            print("⚠️ Neutral signal - no trade recommended")
            return None
        
        if not consensus.entry_zone_low or not consensus.invalidation_level or not consensus.primary_target:
            print("⚠️ Missing critical price levels - cannot generate signal")
            return None
        
        # Check risk-reward
        if consensus.risk_reward_ratio and consensus.risk_reward_ratio < self.config.min_risk_reward:
            print(f"⚠️ Risk/Reward ({consensus.risk_reward_ratio:.1f}) below minimum ({self.config.min_risk_reward})")
            return None
        
        # Generate signal
        signal = TradeSignal(
            signal_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(),
            symbol=consensus.symbol,
            direction=consensus.consensus_signal,
            entry_price=(consensus.entry_zone_low + consensus.entry_zone_high) / 2,
            entry_zone_high=consensus.entry_zone_high,
            entry_zone_low=consensus.entry_zone_low,
            stop_loss=consensus.invalidation_level,
            take_profit_1=consensus.primary_target,
            take_profit_2=consensus.secondary_target,
            position_size_pct=consensus.position_size_recommendation or 2.0,
            leverage=1,
            confluence_score=consensus.confluence_score,
            consensus_agents=consensus.agreeing_agents,
            reasoning=self._generate_reasoning(consensus)
        )
        
        self.signal_history.append(signal)
        
        print(f"\n🚀 TRADE SIGNAL GENERATED: {signal.signal_id}")
        print(f"   Direction: {signal.direction.upper()}")
        print(f"   Entry: ${signal.entry_price:,.2f}")
        print(f"   Stop: ${signal.stop_loss:,.2f}")
        print(f"   Target: ${signal.take_profit_1:,.2f}")
        
        return signal
    
    def _generate_reasoning(self, consensus: ConsensusResult) -> str:
        """Generate reasoning summary from consensus."""
        reasons = []
        
        for analysis in consensus.agent_analyses:
            if analysis.signal.lower() == consensus.consensus_signal:
                if analysis.key_findings:
                    reasons.append(f"{analysis.agent_name}: {analysis.key_findings[0]}")
        
        return " | ".join(reasons[:3])
    
    def get_status(self) -> dict:
        """Get orchestrator status."""
        return {
            "is_running": self.is_running,
            "last_analysis": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            "total_analyses": len(self.analysis_history),
            "total_signals": len(self.signal_history),
            "agents": {name: agent.get_status() for name, agent in self.agents.items()}
        }
    
    def enable_agent(self, agent_name: str):
        """Enable a specific agent."""
        if agent_name in self.agents:
            self.agents[agent_name].config.enabled = True
    
    def disable_agent(self, agent_name: str):
        """Disable a specific agent."""
        if agent_name in self.agents:
            self.agents[agent_name].config.enabled = False


# Factory function
def create_orchestrator(config: OrchestratorConfig = None) -> GodOfGodsOrchestrator:
    """Create a new God of Gods orchestrator."""
    return GodOfGodsOrchestrator(config)
