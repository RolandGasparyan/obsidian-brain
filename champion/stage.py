"""
champion.stage — Capital Stage Tracker per CHAMPION_MODE.md §1.3 + §4.1.

Four discrete capital stages with hard equity boundaries:

    Stage 1   $3k   →  $20k    Ultra Aggressive       1.5% base, 2.0% max, 0.5% min
    Stage 2   $20k  →  $150k   Controlled Aggression  1.0% base, 1.5% max, 0.4% min
    Stage 3   $150k →  $500k   Optimized Risk         0.75% base, 1.0% max, 0.3% min
    Stage 4   $500k →  $1M+    Capital Preservation   0.5% base, 0.75% max, 0.25% min

REGRESSION RULE (immutable, doctrine §V):
    If equity drops back to a previous stage's boundary, the tracker
    REGRESSES to that stage and adopts its (smaller) risk envelope
    immediately. No pride. No ego. Compounding is sacred.

This module is pure state — no I/O, no global state. The orchestrating
layer (champion.sizer) calls update_equity() and reads back the
current envelope.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Stage(IntEnum):
    STAGE_1 = 1
    STAGE_2 = 2
    STAGE_3 = 3
    STAGE_4 = 4


@dataclass(frozen=True)
class StageRules:
    stage:        Stage
    floor_usd:    float    # equity must be >= floor to be IN this stage
    ceiling_usd:  float    # equity strictly < ceiling
    base_risk:    float    # fraction of equity at default
    max_risk:     float    # never exceed (even with win-streak scaler)
    min_risk:     float    # floor under cooldowns / vol scalers
    target_monthly_pct: float
    description:  str


# Doctrine §1.3 — these numbers are LITERALLY from CHAMPION_MODE.md.
# Do not tune without amending the doctrine first.
STAGE_RULES: dict[Stage, StageRules] = {
    Stage.STAGE_1: StageRules(
        stage=Stage.STAGE_1,
        floor_usd=0.0,         ceiling_usd=20_000.0,
        base_risk=0.015,       max_risk=0.020,    min_risk=0.005,
        target_monthly_pct=0.13,
        description="Ultra Aggressive ($3k → $20k)",
    ),
    Stage.STAGE_2: StageRules(
        stage=Stage.STAGE_2,
        floor_usd=20_000.0,    ceiling_usd=150_000.0,
        base_risk=0.010,       max_risk=0.015,    min_risk=0.004,
        target_monthly_pct=0.10,
        description="Controlled Aggression ($20k → $150k)",
    ),
    Stage.STAGE_3: StageRules(
        stage=Stage.STAGE_3,
        floor_usd=150_000.0,   ceiling_usd=500_000.0,
        base_risk=0.0075,      max_risk=0.010,    min_risk=0.003,
        target_monthly_pct=0.065,
        description="Optimized Risk ($150k → $500k)",
    ),
    Stage.STAGE_4: StageRules(
        stage=Stage.STAGE_4,
        floor_usd=500_000.0,   ceiling_usd=float("inf"),
        base_risk=0.005,       max_risk=0.0075,   min_risk=0.0025,
        target_monthly_pct=0.04,
        description="Capital Preservation ($500k+)",
    ),
}


def stage_for_equity(eq: float) -> Stage:
    """Pure function: equity → Stage. Sole entry point for stage logic."""
    if eq < 20_000.0:    return Stage.STAGE_1
    if eq < 150_000.0:   return Stage.STAGE_2
    if eq < 500_000.0:   return Stage.STAGE_3
    return Stage.STAGE_4


class CapitalStageTracker:
    """Tracks current equity, current stage, peak equity, and emits
    transition events when stages change.

    Regression: if a *new* equity reading falls below the floor of the
    current stage, we regress immediately to the lower stage's envelope.
    Promotion: if equity crosses above the ceiling, we promote (but
    only on a >= 1% buffer beyond the ceiling — no thrash on boundary
    chops).
    """

    PROMOTION_BUFFER_FRAC = 0.01   # 1% above ceiling required to promote

    def __init__(self, starting_equity: float = 3_000.0):
        if starting_equity <= 0:
            raise ValueError("starting_equity must be > 0")
        self._equity:    float = starting_equity
        self._peak:      float = starting_equity
        self._initial:   float = starting_equity
        self._stage:     Stage = stage_for_equity(starting_equity)
        self._transitions: list[tuple[Stage, Stage, float]] = []

    # ── read-only views ──
    @property
    def equity(self) -> float:           return self._equity
    @property
    def peak_equity(self) -> float:      return self._peak
    @property
    def initial_equity(self) -> float:   return self._initial
    @property
    def stage(self) -> Stage:            return self._stage
    @property
    def rules(self) -> StageRules:       return STAGE_RULES[self._stage]
    @property
    def base_risk_pct(self) -> float:    return self.rules.base_risk
    @property
    def max_risk_pct(self) -> float:     return self.rules.max_risk
    @property
    def min_risk_pct(self) -> float:     return self.rules.min_risk
    @property
    def transitions(self):
        return tuple(self._transitions)

    # ── mutation ──
    def update_equity(self, new_equity: float) -> Stage | None:
        """Set the latest equity reading.

        Returns the *new* Stage if a transition occurred, else None.
        Regression is instant; promotion requires a 1% buffer beyond
        the ceiling.
        """
        if new_equity <= 0:
            raise ValueError("equity must remain > 0")
        old_stage = self._stage
        self._equity = new_equity
        if new_equity > self._peak:
            self._peak = new_equity

        natural_stage = stage_for_equity(new_equity)

        # Regression — strict drop below current floor → revert immediately
        if natural_stage < old_stage:
            self._stage = natural_stage
        # Promotion — only when comfortably past ceiling
        elif natural_stage > old_stage:
            ceiling = STAGE_RULES[old_stage].ceiling_usd
            if new_equity >= ceiling * (1 + self.PROMOTION_BUFFER_FRAC):
                self._stage = natural_stage

        if self._stage != old_stage:
            self._transitions.append((old_stage, self._stage, new_equity))
            return self._stage
        return None

    # ── progress reporting ──
    def progress_to_target(self, target_usd: float = 1_000_000.0) -> float:
        """0.0–1.0 fraction toward $1M target on a log-scaled path
        (because returns compound; linear progress understates early gains).
        """
        if self._equity <= self._initial: return 0.0
        if self._equity >= target_usd:    return 1.0
        import math
        return (math.log(self._equity / self._initial)
                / math.log(target_usd / self._initial))

    def doublings_achieved(self) -> float:
        """log2(equity / initial) — 8.4 needed to reach $1M from $3k."""
        import math
        return math.log2(self._equity / self._initial)

    def __repr__(self) -> str:
        return (f"<CapitalStage stage={self._stage.name} "
                f"eq=${self._equity:,.2f} peak=${self._peak:,.2f} "
                f"base_risk={self.base_risk_pct*100:.2f}%>")
