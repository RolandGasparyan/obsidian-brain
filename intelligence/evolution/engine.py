"""
╔══════════════════════════════════════════════════════════════════════════╗
║          EVOLUTION ENGINE — SELF-UPGRADING CORE                          ║
║          Strategy Mutation · DNA Optimization · Survival Selection       ║
╚══════════════════════════════════════════════════════════════════════════╝

The Evolution Engine is the genetic algorithm layer of the Trading Guru
ecosystem. It evaluates agent fitness, mutates strategies, promotes winners,
and eliminates underperformers — creating a self-improving AI civilization.
"""

import json
import random
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

log = logging.getLogger("evolution_engine")

EVOLUTION_STATE_FILE = Path(__file__).parent / "evolution_state.json"

# ── Agent DNA — Strategy Parameters ───────────────────────────────────────
@dataclass
class AgentDNA:
    """The genetic blueprint of a trading agent."""
    agent_id:         str
    agent_class:      str   # Momentum, Scalper, Sniper, Macro, Liquidity, RL, Shadow
    rsi_threshold:    float = 70.0    # RSI overbought level for SHORT entry
    wr_threshold:     float = -15.0   # W%R overbought level
    checklist_min:    int   = 6       # Minimum GODS LEVEL checklist score
    confidence_min:   float = 0.65    # Minimum confidence to trade
    risk_per_trade:   float = 0.02    # 2% risk per trade
    kelly_factor:     float = 0.25    # Kelly adjustment
    stop_pct:         float = 0.015   # 1.5% stop loss
    take_profit_pct:  float = 0.03    # 3% take profit (2:1 R:R)
    generation:       int   = 1
    mutations:        int   = 0

    def mutate(self, mutation_rate: float = 0.15) -> "AgentDNA":
        """Create a mutated copy of this DNA."""
        child = AgentDNA(
            agent_id     = f"{self.agent_id}_gen{self.generation + 1}",
            agent_class  = self.agent_class,
            rsi_threshold   = self._mutate_param(self.rsi_threshold,   65.0, 80.0, mutation_rate),
            wr_threshold    = self._mutate_param(self.wr_threshold,    -25.0, -5.0, mutation_rate),
            checklist_min   = max(4, min(8, self.checklist_min + random.choice([-1, 0, 1]))),
            confidence_min  = self._mutate_param(self.confidence_min,   0.55, 0.85, mutation_rate),
            risk_per_trade  = self._mutate_param(self.risk_per_trade,   0.01, 0.03, mutation_rate),
            kelly_factor    = self._mutate_param(self.kelly_factor,     0.15, 0.35, mutation_rate),
            stop_pct        = self._mutate_param(self.stop_pct,         0.01, 0.025, mutation_rate),
            take_profit_pct = self._mutate_param(self.take_profit_pct,  0.02, 0.05, mutation_rate),
            generation      = self.generation + 1,
            mutations       = self.mutations + 1,
        )
        return child

    @staticmethod
    def _mutate_param(value: float, low: float, high: float, rate: float) -> float:
        if random.random() < rate:
            delta = (high - low) * random.uniform(-0.1, 0.1)
            return round(max(low, min(high, value + delta)), 4)
        return value

    def to_dict(self) -> dict:
        return asdict(self)


# ── Agent Performance Record ───────────────────────────────────────────────
@dataclass
class AgentPerformance:
    agent_id:        str
    wins:            int   = 0
    losses:          int   = 0
    total_pnl:       float = 0.0
    max_drawdown:    float = 0.0
    sharpe_ratio:    float = 0.0
    win_rate:        float = 0.0
    fitness_score:   float = 0.0
    rank:            int   = 0
    elo:             int   = 1200
    xp:              int   = 0
    evolution_stage: str   = "ROOKIE"  # ROOKIE → VETERAN → ELITE → LEGEND → GOD

    def update_fitness(self):
        """Calculate composite fitness score for evolution selection."""
        total_trades = self.wins + self.losses
        if total_trades == 0:
            self.fitness_score = 0.0
            return

        self.win_rate = self.wins / total_trades
        # Weighted fitness: 40% win rate, 30% PnL, 20% Sharpe, 10% low drawdown
        drawdown_score = max(0.0, 1.0 - (self.max_drawdown / 0.20))
        self.fitness_score = round(
            (self.win_rate * 0.40)
            + (min(self.total_pnl / 1000.0, 1.0) * 0.30)
            + (min(self.sharpe_ratio / 3.0, 1.0) * 0.20)
            + (drawdown_score * 0.10),
            4
        )

    def update_evolution_stage(self):
        """Promote agent based on XP milestones."""
        if   self.xp >= 10000: self.evolution_stage = "GOD"
        elif self.xp >= 5000:  self.evolution_stage = "LEGEND"
        elif self.xp >= 2000:  self.evolution_stage = "ELITE"
        elif self.xp >= 500:   self.evolution_stage = "VETERAN"
        else:                  self.evolution_stage = "ROOKIE"

    def record_trade(self, pnl: float, drawdown: float = 0.0):
        """Record a completed trade result."""
        if pnl > 0:
            self.wins  += 1
            self.xp    += int(pnl * 10)
            self.elo   += 16
        else:
            self.losses += 1
            self.elo    = max(800, self.elo - 16)

        self.total_pnl    += pnl
        self.max_drawdown  = max(self.max_drawdown, drawdown)
        self.update_fitness()
        self.update_evolution_stage()


# ── Evolution Engine ───────────────────────────────────────────────────────
class EvolutionEngine:
    """
    Genetic algorithm engine for the Trading Guru AI Championship.

    Lifecycle:
    1. Evaluate fitness of all agents
    2. Select survivors (top performers)
    3. Eliminate underperformers
    4. Mutate survivors to create new generation
    5. Promote champions to higher evolution stages
    6. Update population and save state
    """

    AGENT_CLASSES = ["Momentum", "Scalper", "Sniper", "Macro", "Liquidity", "RL", "Shadow"]
    POPULATION_SIZE = 21   # 3 agents per class
    SURVIVAL_RATE   = 0.60  # Top 60% survive each generation
    MUTATION_RATE   = 0.15

    def __init__(self):
        self.generation      = 1
        self.population: dict[str, AgentDNA]         = {}
        self.performance: dict[str, AgentPerformance] = {}
        self._load_state()

        if not self.population:
            self._initialize_population()

        log.info("Evolution Engine ready — Generation %d, Population: %d",
                 self.generation, len(self.population))

    def _initialize_population(self):
        """Seed the initial population with one agent per class."""
        for agent_class in self.AGENT_CLASSES:
            for i in range(3):
                agent_id = f"{agent_class.lower()}_{i+1:02d}"
                self.population[agent_id]  = AgentDNA(agent_id=agent_id, agent_class=agent_class)
                self.performance[agent_id] = AgentPerformance(agent_id=agent_id)
        log.info("Initial population seeded: %d agents across %d classes",
                 len(self.population), len(self.AGENT_CLASSES))

    def record_trade(self, agent_id: str, pnl: float, drawdown: float = 0.0):
        """Record a trade result for a specific agent."""
        if agent_id not in self.performance:
            self.performance[agent_id] = AgentPerformance(agent_id=agent_id)
        self.performance[agent_id].record_trade(pnl, drawdown)

    def run_evolution_cycle(self) -> dict:
        """
        Execute one full evolution cycle.
        Returns a summary of promotions, eliminations, and mutations.
        """
        log.info("═══ EVOLUTION CYCLE %d STARTING ═══", self.generation)

        # Step 1: Update all fitness scores
        for agent_id, perf in self.performance.items():
            perf.update_fitness()

        # Step 2: Rank agents by fitness
        ranked = sorted(
            self.performance.values(),
            key=lambda p: p.fitness_score,
            reverse=True
        )

        # Assign ranks
        for i, perf in enumerate(ranked):
            perf.rank = i + 1

        # Step 3: Survival selection
        survivor_count = max(3, int(len(ranked) * self.SURVIVAL_RATE))
        survivors      = ranked[:survivor_count]
        eliminated     = ranked[survivor_count:]

        log.info("Survivors: %d | Eliminated: %d", len(survivors), len(eliminated))

        # Step 4: Eliminate underperformers
        eliminated_ids = []
        for perf in eliminated:
            if perf.agent_id in self.population:
                del self.population[perf.agent_id]
                eliminated_ids.append(perf.agent_id)
                log.info("  ❌ Eliminated: %s (fitness: %.3f)", perf.agent_id, perf.fitness_score)

        # Step 5: Mutate survivors to fill population
        new_agents = []
        survivor_dnas = [self.population[p.agent_id] for p in survivors if p.agent_id in self.population]

        while len(self.population) < self.POPULATION_SIZE and survivor_dnas:
            parent = random.choice(survivor_dnas)
            child_dna = parent.mutate(self.MUTATION_RATE)
            self.population[child_dna.agent_id]  = child_dna
            self.performance[child_dna.agent_id] = AgentPerformance(agent_id=child_dna.agent_id)
            new_agents.append(child_dna.agent_id)
            log.info("  🧬 New agent: %s (from %s, gen %d)",
                     child_dna.agent_id, parent.agent_id, child_dna.generation)

        # Step 6: Promote champions
        promotions = []
        for perf in survivors[:3]:
            old_stage = perf.evolution_stage
            perf.update_evolution_stage()
            if perf.evolution_stage != old_stage:
                promotions.append(f"{perf.agent_id}: {old_stage} → {perf.evolution_stage}")
                log.info("  🏆 PROMOTED: %s → %s", perf.agent_id, perf.evolution_stage)

        self.generation += 1
        self._save_state()

        summary = {
            "generation":      self.generation,
            "population_size": len(self.population),
            "survivors":       len(survivors),
            "eliminated":      eliminated_ids,
            "new_agents":      new_agents,
            "promotions":      promotions,
            "top_agent":       ranked[0].agent_id if ranked else None,
            "top_fitness":     ranked[0].fitness_score if ranked else 0.0,
        }

        log.info("═══ EVOLUTION CYCLE COMPLETE — Gen %d | Top: %s (%.3f) ═══",
                 self.generation, summary["top_agent"], summary["top_fitness"])
        return summary

    def get_leaderboard(self, top_n: int = 10) -> list[dict]:
        """Return the current agent leaderboard sorted by fitness."""
        ranked = sorted(
            self.performance.values(),
            key=lambda p: p.fitness_score,
            reverse=True
        )[:top_n]

        return [
            {
                "rank":            i + 1,
                "agent_id":        p.agent_id,
                "evolution_stage": p.evolution_stage,
                "fitness":         round(p.fitness_score, 3),
                "win_rate":        f"{p.win_rate:.1%}",
                "total_pnl":       round(p.total_pnl, 2),
                "elo":             p.elo,
                "xp":              p.xp,
            }
            for i, p in enumerate(ranked)
        ]

    def _save_state(self):
        state = {
            "generation":  self.generation,
            "population":  {k: v.to_dict() for k, v in self.population.items()},
            "performance": {k: asdict(v) for k, v in self.performance.items()},
            "updated_at":  datetime.now(timezone.utc).isoformat(),
        }
        EVOLUTION_STATE_FILE.write_text(json.dumps(state, indent=2))

    def _load_state(self):
        if EVOLUTION_STATE_FILE.exists():
            try:
                data = json.loads(EVOLUTION_STATE_FILE.read_text())
                self.generation = data.get("generation", 1)
                for k, v in data.get("population", {}).items():
                    self.population[k] = AgentDNA(**v)
                for k, v in data.get("performance", {}).items():
                    self.performance[k] = AgentPerformance(**v)
                log.info("Evolution state restored — Generation %d", self.generation)
            except Exception as e:
                log.warning("Could not restore evolution state: %s", e)


# ── CLI entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [EVOLUTION] %(levelname)s — %(message)s")

    engine = EvolutionEngine()

    # Simulate some trades
    import random
    for agent_id in list(engine.population.keys()):
        for _ in range(random.randint(5, 20)):
            pnl = random.uniform(-50, 150)
            engine.record_trade(agent_id, pnl, max(0, -pnl / 1000))

    # Run one evolution cycle
    summary = engine.run_evolution_cycle()
    print("\n═══ EVOLUTION SUMMARY ═══")
    print(json.dumps(summary, indent=2))

    print("\n═══ LEADERBOARD ═══")
    for entry in engine.get_leaderboard(5):
        print(f"  #{entry['rank']} {entry['agent_id']:25s} "
              f"[{entry['evolution_stage']:8s}] "
              f"Fitness: {entry['fitness']:.3f} | "
              f"Win: {entry['win_rate']} | "
              f"PnL: ${entry['total_pnl']:,.2f} | "
              f"ELO: {entry['elo']}")
