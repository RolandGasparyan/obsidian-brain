"""
champion.equity_mc_sim — Layer 3 §3.3 + §4 Monte Carlo equity-curve simulator.

Implements Sections 3.3 + 4 of L99_CAPITAL_MATHEMATICS.md.

Edge-independent. Pure math. NO exchange wiring. NO strategy dependency.

Given a list of historical per-trade R-multiples, simulate N randomized
orderings to estimate:
  - Median / 5th / 95th percentile final equity
  - Median / worst-case max drawdown
  - Probability of ruin (DD ≥ ruin_threshold from peak)
  - Probability of crossing dd_threshold at any point
  - Median time-to-recovery from worst DD

Approach (Section 3.3):
  1. Shuffle the input R-list randomly N times
  2. For each shuffle, walk an equity curve: equity_t+1 = equity_t × (1 + r_t × risk)
     (multiplicative compounding; risk fraction is fixed at risk_per_trade)
  3. Track per-curve max DD and time-to-recovery
  4. Aggregate across simulations

Operator note: "Edge = expectancy per unit risk" (Section 4). Lower
risk_per_trade → exponentially lower ruin probability. The simulator
exposes this directly: ruin probability is a function of risk.

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class McSimConfig:
    """Operator-spec defaults from L99_CAPITAL_MATHEMATICS §3.3 + §4."""

    n_simulations: int = 1000               # 1000-5000 per Section 3.3
    starting_equity: float = 10_000.0
    risk_per_trade: float = 0.01            # 1R = 1% of equity
    ruin_threshold: float = 0.50            # 50% DD = ruin
    dd_threshold: float = 0.30              # threshold for "crossed 30% DD"
    seed: Optional[int] = None              # for deterministic tests

    def __post_init__(self) -> None:
        if self.n_simulations < 1:
            raise ValueError("n_simulations must be >= 1")
        if self.starting_equity <= 0:
            raise ValueError("starting_equity must be > 0")
        if not (0 < self.risk_per_trade <= 1):
            raise ValueError("risk_per_trade must be in (0, 1]")
        if not (0 < self.ruin_threshold <= 1):
            raise ValueError("ruin_threshold must be in (0, 1]")
        if not (0 < self.dd_threshold <= 1):
            raise ValueError("dd_threshold must be in (0, 1]")


# ─────────────────────────────────────────────
# RESULT
# ─────────────────────────────────────────────

@dataclass
class McSimResult:
    n_simulations: int
    median_final_equity: float
    p5_final_equity: float
    p95_final_equity: float
    median_max_drawdown: float
    p95_max_drawdown: float           # worst-case DD across sims (95th pct)
    prob_ruin: float                  # fraction of sims that hit ruin_threshold
    prob_dd_threshold: float          # fraction of sims that crossed dd_threshold
    median_time_to_recovery: int      # bars to fully recover from each sim's worst DD


# ─────────────────────────────────────────────
# SIMULATOR
# ─────────────────────────────────────────────

class EquityMonteCarloSimulator:

    def __init__(self, config: Optional[McSimConfig] = None):
        self.config = config or McSimConfig()

    # ─────────────────────────────────────────

    def simulate(self, r_outcomes: Sequence[float]) -> McSimResult:
        """Run n_simulations randomized orderings of r_outcomes through
        a multiplicative equity curve. Return aggregate statistics."""
        if len(r_outcomes) == 0:
            raise ValueError("r_outcomes must be non-empty")

        rng = random.Random(self.config.seed)
        cfg = self.config

        finals: List[float] = []
        max_dds: List[float] = []
        ruin_count = 0
        dd_threshold_count = 0
        recovery_times: List[int] = []

        r_list = list(r_outcomes)

        for _ in range(cfg.n_simulations):
            shuffled = r_list[:]
            rng.shuffle(shuffled)

            equity = cfg.starting_equity
            peak = equity
            worst_dd = 0.0
            worst_dd_bar = 0
            recovered_bar: Optional[int] = None

            for t, r in enumerate(shuffled):
                equity = equity * (1.0 + r * cfg.risk_per_trade)
                if equity > peak:
                    peak = equity
                    # Recovery from prior worst DD if equity matches/exceeds peak
                    if recovered_bar is None and worst_dd > 0:
                        recovered_bar = t
                if peak > 0:
                    dd = 1.0 - (equity / peak)
                    if dd > worst_dd:
                        worst_dd = dd
                        worst_dd_bar = t

            finals.append(equity)
            max_dds.append(worst_dd)

            if worst_dd >= cfg.ruin_threshold:
                ruin_count += 1
            if worst_dd >= cfg.dd_threshold:
                dd_threshold_count += 1

            # Time to recovery: bars from worst-DD point to first peak-equal/exceed
            if recovered_bar is not None and recovered_bar > worst_dd_bar:
                recovery_times.append(recovered_bar - worst_dd_bar)
            else:
                # Did not recover within the simulation window; use length as upper bound
                recovery_times.append(len(shuffled) - worst_dd_bar)

        finals_sorted = sorted(finals)
        max_dds_sorted = sorted(max_dds)
        recovery_sorted = sorted(recovery_times)

        return McSimResult(
            n_simulations=cfg.n_simulations,
            median_final_equity=_percentile(finals_sorted, 0.50),
            p5_final_equity=_percentile(finals_sorted, 0.05),
            p95_final_equity=_percentile(finals_sorted, 0.95),
            median_max_drawdown=_percentile(max_dds_sorted, 0.50),
            p95_max_drawdown=_percentile(max_dds_sorted, 0.95),
            prob_ruin=ruin_count / cfg.n_simulations,
            prob_dd_threshold=dd_threshold_count / cfg.n_simulations,
            median_time_to_recovery=int(_percentile(recovery_sorted, 0.50)),
        )


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile of pre-sorted values. q in [0, 1]."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = q * (len(sorted_values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac
