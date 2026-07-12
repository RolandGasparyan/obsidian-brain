"""
tournament_risk_controller.py
-----------------------------
Top-level risk veto. Sits ABOVE guardian.py conceptually: guardian is internal
safety, this is tournament-competitive risk (protect the lead, prevent ruin
from loss clusters, enforce daily caps derived from the capital phase).

Behaviorally: decision_pipeline asks `allow_new_entry(context)` before passing
a candidate to execution. If this returns BlockedDecision, the candidate is
rejected with a reason. Guardian.py retains ultimate authority over position
management of OPEN trades - this module only gates NEW entries.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Optional

from .capital_phase_manager import PhaseDirective
from .performance_oracle import PerformanceStats
from .usdt_domination_core import UsdtSnapshot


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass
class EntryDecision:
    verdict: Verdict
    reason: str
    risk_multiplier: float = 1.0   # applied on top of phase multiplier if ALLOW


@dataclass
class RiskContext:
    equity_usdt: float
    starting_usdt: float
    open_positions: int
    realized_pnl_today_usdt: float
    phase: PhaseDirective
    stats: PerformanceStats
    snapshot: UsdtSnapshot


class TournamentRiskController:
    """Stateless veto logic + lightweight cooldown tracking."""

    def __init__(
        self,
        cooldown_after_loss_streak: int = 3,
        cooldown_minutes: float = 15.0,
        hard_dd_cap: float = 0.15,
    ) -> None:
        self._lock = RLock()
        self._cooldown_trigger = cooldown_after_loss_streak
        self._cooldown_seconds = cooldown_minutes * 60.0
        self._cooldown_until: float = 0.0
        self._hard_dd_cap = hard_dd_cap

    def notify_loss_streak(self, streak: int) -> None:
        """Called by launch.py or performance_oracle consumer."""
        if streak >= self._cooldown_trigger:
            with self._lock:
                self._cooldown_until = time.time() + self._cooldown_seconds

    def in_cooldown(self) -> bool:
        with self._lock:
            return time.time() < self._cooldown_until

    def allow_new_entry(self, ctx: RiskContext) -> EntryDecision:
        # 1. Hard drawdown cap (ruin prevention, above guardian)
        dd_pct = 1.0 - (ctx.equity_usdt / ctx.starting_usdt) if ctx.starting_usdt > 0 else 0.0
        if dd_pct >= self._hard_dd_cap:
            return EntryDecision(Verdict.BLOCK, f"hard_dd_cap_breached({dd_pct:.2%})")

        # 2. Phase-level daily loss cap (derived from equity, not starting)
        daily_loss_pct = -ctx.realized_pnl_today_usdt / ctx.equity_usdt if ctx.equity_usdt > 0 else 0.0
        if daily_loss_pct >= ctx.phase.daily_loss_cap_pct:
            return EntryDecision(
                Verdict.BLOCK,
                f"daily_loss_cap({daily_loss_pct:.2%} >= {ctx.phase.daily_loss_cap_pct:.2%})",
            )

        # 3. Max concurrent trades per phase
        if ctx.open_positions >= ctx.phase.max_concurrent_trades:
            return EntryDecision(
                Verdict.BLOCK,
                f"max_concurrent({ctx.open_positions}/{ctx.phase.max_concurrent_trades})",
            )

        # 4. Cooldown after loss cluster
        if self.in_cooldown():
            return EntryDecision(Verdict.BLOCK, "loss_cluster_cooldown")

        # 5. Performance-based soft scaling of risk
        mult = 1.0
        if ctx.stats.sample_size >= 20:
            if ctx.stats.expectancy_r < 0:
                # negative expectancy and not yet blocked by oracle threshold:
                # still allow but cut size aggressively
                mult *= 0.5
            if ctx.stats.loss_streak_current >= 2:
                mult *= 0.75
            if ctx.stats.profit_factor != float("inf") and ctx.stats.profit_factor < 1.1:
                mult *= 0.85

        return EntryDecision(Verdict.ALLOW, "ok", risk_multiplier=round(mult, 3))
