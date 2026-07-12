"""
brain.py
--------
Composition root for the tournament system. v3.

v3 changes:
    - AggressionMatrix integrated BEFORE TournamentRiskController
    - Matrix outputs (effective_risk, effective_threshold, max_concurrent,
      cooldown_minutes) override phase directive values for risk context
    - Equity history sampled in on_telemetry_tick for weekly growth rate
    - Peak equity tracked for live drawdown

Pipeline order (unchanged placement of earlier gates):
    1. Breaker check (fast short-circuit)
    2. Volatility gate (per-pair, phase-aware)
    3. Composite score
    4. Matrix computes directive (NEW)
    5. Volatility/score gates using MATRIX threshold
    6. Risk controller with matrix-derived context
    7. Final risk multiplier = matrix.effective_risk * risk_controller.risk_multiplier
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from threading import RLock
from typing import Optional

import numpy as np

from .aggression_matrix import (
    AggressionDirective, AggressionMatrix, MatrixInputs,
)
from .aggression_scaler import (
    AggressionMode, AggressionReading, AggressionScaler,
)
from .capital_phase_manager import CapitalPhaseManager, Phase, PhaseDirective
from .champion_momentum_engine import (
    CandidateFeatures, ChampionMomentumEngine, ScoreBreakdown,
)
from .edge_decay_detector import DecayVerdict, EdgeDecayDetector, EdgeStatus
from .loss_cluster_breaker import (
    BreakerDecision, BreakerState, LossClusterBreaker,
)
from .performance_oracle import PerformanceOracle, ThresholdDirective
from .tournament_risk_controller import (
    EntryDecision, RiskContext, TournamentRiskController, Verdict,
)
from .usdt_domination_core import TradeEvent, UsdtCore, UsdtSnapshot
from .volatility_expansion_detector import (
    PhaseHint, VolatilityExpansionDetector, VolatilityReading, VolState,
)

log = logging.getLogger("trading_guru.tournament")


_PHASE_TO_HINT = {
    Phase.EARLY: PhaseHint.EARLY,
    Phase.MID: PhaseHint.MID,
    Phase.ENDGAME: PhaseHint.ENDGAME,
}


@dataclass
class BrainDecision:
    allow: bool
    reason: str
    composite_score: float
    effective_threshold: float
    volatility: VolatilityReading
    score_breakdown: ScoreBreakdown
    risk: EntryDecision
    phase: PhaseDirective
    threshold_directive: ThresholdDirective
    aggression: AggressionReading
    matrix: AggressionDirective          # NEW v3
    breaker_cooldown_seconds: float
    edge_status: Optional[EdgeStatus] = None
    recommended_risk_multiplier: float = 1.0

    def to_log_dict(self) -> dict:
        return {
            "allow": self.allow,
            "reason": self.reason,
            "score": self.composite_score,
            "threshold": self.effective_threshold,
            "vol": f"{self.volatility.state.value}@{self.volatility.score}",
            "phase": self.phase.phase.value,
            "matrix": self.matrix.to_log_dict(),
            "risk_mult": self.recommended_risk_multiplier,
            "breaker_cd_s": self.breaker_cooldown_seconds,
        }


class TournamentBrain:
    """Facade used by fusion_brain. Thread-safe."""

    def __init__(
        self,
        starting_usdt: float,
        base_score_threshold: float = 62.0,
        performance_window: int = 200,
        edge_review_every: int = 50,
        aggression_window_minutes: float = 30.0,
    ) -> None:
        self._lock = RLock()
        self.usdt = UsdtCore(starting_usdt=starting_usdt)
        self.scorer = ChampionMomentumEngine()
        self.oracle = PerformanceOracle(
            window_size=performance_window,
            base_threshold=base_score_threshold,
        )
        self.phases = CapitalPhaseManager()
        self.risk = TournamentRiskController()
        self.decay = EdgeDecayDetector()
        self.vol = VolatilityExpansionDetector()
        self.aggression = AggressionScaler(window_minutes=aggression_window_minutes)
        self.breaker = LossClusterBreaker()
        self.matrix = AggressionMatrix(base_threshold=base_score_threshold)
        self._edge_review_every = edge_review_every
        self._last_edge_status: Optional[EdgeStatus] = None

    # ---- lifecycle hooks ----

    def on_trade_deployed(self, notional_usdt: float) -> None:
        self.usdt.record_deploy(notional_usdt)

    def on_trade_closed(self, event: TradeEvent) -> None:
        self.usdt.record_fill(event)
        self.oracle.record(event)
        self.aggression.sample(self.usdt.growth_multiple())

        stats = self.oracle.stats()
        self.risk.notify_loss_streak(stats.loss_streak_current)

        snap = self.usdt.snapshot()
        phase = self.phases.current().phase
        breaker_decision = self.breaker.on_close(event, snap.equity_usdt, phase)
        if breaker_decision.state != BreakerState.OPEN and breaker_decision.trigger != "none":
            log.warning("tournament.breaker_tripped trigger=%s cooldown=%.0fs",
                        breaker_decision.trigger, breaker_decision.cooldown_seconds)

        if self.oracle.review_due(self._edge_review_every):
            events = list(self.oracle._events)  # noqa: SLF001
            self._last_edge_status = self.decay.evaluate(events)
            log.info("tournament.edge_review verdict=%s note=%s",
                     self._last_edge_status.verdict.value, self._last_edge_status.note)
            if self._last_edge_status.verdict == DecayVerdict.HARD_DECAY:
                new_base = min(85.0, self.oracle._base_threshold + 3.0)  # noqa: SLF001
                self.oracle.set_base_threshold(new_base)
                log.warning("tournament.edge_decay tightened_base=%s", new_base)
            self.oracle.mark_reviewed()

    def on_daily_tick(self) -> PhaseDirective:
        growth = self.usdt.growth_multiple()
        directive = self.phases.evaluate(growth)
        self.aggression.sample(growth)
        log.info("tournament.phase_tick growth=%.3f phase=%s",
                 growth, directive.phase.value)
        return directive

    def on_telemetry_tick(self) -> None:
        """Called every ~60s by launch.py. Feeds aggression scaler and
        (on hourly cadence) equity history ring for weekly growth rate."""
        self.aggression.sample(self.usdt.growth_multiple())

    def on_hourly_tick(self) -> None:
        """Called every 60 minutes by launch.py. Records an equity sample
        into the rolling ring for weekly_growth_rate computation."""
        self.usdt.record_equity_sample(time.time())

    # ---- entry evaluation ----

    def evaluate_entry(
        self,
        features: CandidateFeatures,
        ohlcv: dict,
        open_positions: int,
        realized_pnl_today_usdt: float,
    ) -> BrainDecision:
        phase = self.phases.current()
        phase_hint = _PHASE_TO_HINT[phase.phase]
        snap = self.usdt.snapshot()
        stats = self.oracle.stats()
        thr = self.oracle.threshold()
        aggr = self.aggression.read(phase.phase, snap.rotation_velocity)

        # 0. fast-path: breaker tripped
        breaker_cd = self.breaker.cooldown_remaining()
        loss_cluster_flag = not self.breaker.allow()
        if loss_cluster_flag:
            vol_reading = VolatilityReading(
                VolState.NEUTRAL, 0.5, 0.0, 0.0, 0.0, 0.0, "skipped_breaker_tripped", 0,
            )
            breakdown = ScoreBreakdown(total=0.0, components={}, weighted={}, rejected_reasons=[])
            # still compute matrix for telemetry consistency
            matrix_directive = self._compute_matrix(snap, vol_reading.state, loss_cluster_flag)
            return BrainDecision(
                allow=False,
                reason=f"breaker_tripped:{self.breaker._last_trigger}",  # noqa: SLF001
                composite_score=0.0,
                effective_threshold=matrix_directive.effective_threshold,
                volatility=vol_reading,
                score_breakdown=breakdown,
                risk=EntryDecision(Verdict.BLOCK, "breaker", 0.0),
                phase=phase,
                threshold_directive=thr,
                aggression=aggr,
                matrix=matrix_directive,
                breaker_cooldown_seconds=breaker_cd,
                edge_status=self._last_edge_status,
                recommended_risk_multiplier=0.0,
            )

        # 1. volatility read (needed as input to matrix)
        vol_reading = self.vol.read(
            pair=features.pair,
            high=np.asarray(ohlcv["high"]),
            low=np.asarray(ohlcv["low"]),
            close=np.asarray(ohlcv["close"]),
            volume=np.asarray(ohlcv["volume"]),
            phase=phase_hint,
        )

        # 2. composite score
        breakdown = self.scorer.score(features)

        # 3. matrix evaluation (NEW v3) - runs BEFORE risk_controller
        matrix_directive = self._compute_matrix(snap, vol_reading.state, loss_cluster_flag=False)
        effective_threshold = matrix_directive.effective_threshold

        # 4. volatility gating using matrix threshold
        compressed_bonus = self.vol.compressed_watch_bonus(phase_hint)
        neutral_floor = self.vol.neutral_floor(phase_hint)

        if vol_reading.state == VolState.EXPANDED:
            return self._block(
                "volatility_already_expanded",
                breakdown, vol_reading, phase, thr, effective_threshold,
                aggr, matrix_directive, breaker_cd,
            )
        if vol_reading.state == VolState.NEUTRAL and vol_reading.score < neutral_floor:
            return self._block(
                f"volatility_neutral_low({vol_reading.score}<{neutral_floor})",
                breakdown, vol_reading, phase, thr, effective_threshold,
                aggr, matrix_directive, breaker_cd,
            )
        if vol_reading.state == VolState.COMPRESSED and breakdown.total < (effective_threshold + compressed_bonus):
            return self._block(
                f"compressed_needs_elite({breakdown.total}<{effective_threshold + compressed_bonus})",
                breakdown, vol_reading, phase, thr, effective_threshold,
                aggr, matrix_directive, breaker_cd,
            )

        # 5. score threshold check using MATRIX threshold
        if breakdown.total < effective_threshold:
            return self._block(
                f"score_below_threshold({breakdown.total}<{effective_threshold})",
                breakdown, vol_reading, phase, thr, effective_threshold,
                aggr, matrix_directive, breaker_cd,
            )

        # 6. tournament risk veto - now takes MATRIX max_concurrent
        # Build a synthesized PhaseDirective from matrix outputs so risk_controller
        # uses matrix values without changing its interface.
        synthesized_phase = PhaseDirective(
            phase=phase.phase,
            risk_multiplier=matrix_directive.effective_risk,
            score_threshold_delta=0.0,  # threshold already applied above
            max_concurrent_trades=matrix_directive.max_concurrent_trades,
            daily_loss_cap_pct=phase.daily_loss_cap_pct,  # retain phase's cap
            rationale=f"matrix:{matrix_directive.lock_reason or 'ok'}",
        )
        ctx = RiskContext(
            equity_usdt=snap.equity_usdt,
            starting_usdt=self.usdt.starting_capital(),
            open_positions=open_positions,
            realized_pnl_today_usdt=realized_pnl_today_usdt,
            phase=synthesized_phase,
            stats=stats,
            snapshot=snap,
        )
        risk_decision = self.risk.allow_new_entry(ctx)
        if risk_decision.verdict == Verdict.BLOCK:
            return BrainDecision(
                allow=False,
                reason=f"risk_block:{risk_decision.reason}",
                composite_score=breakdown.total,
                effective_threshold=effective_threshold,
                volatility=vol_reading,
                score_breakdown=breakdown,
                risk=risk_decision,
                phase=phase,
                threshold_directive=thr,
                aggression=aggr,
                matrix=matrix_directive,
                breaker_cooldown_seconds=breaker_cd,
                edge_status=self._last_edge_status,
                recommended_risk_multiplier=0.0,
            )

        # 7. final multiplier = matrix.effective_risk * risk_controller.risk_multiplier
        # (matrix already folded in phase, DD, growth, vol; risk_controller adds
        # short-term performance tweaks like streak-based size cuts)
        final_mult = matrix_directive.effective_risk * risk_decision.risk_multiplier
        final_mult = min(final_mult, 2.0)  # hard global cap

        return BrainDecision(
            allow=True,
            reason="allow",
            composite_score=breakdown.total,
            effective_threshold=effective_threshold,
            volatility=vol_reading,
            score_breakdown=breakdown,
            risk=risk_decision,
            phase=phase,
            threshold_directive=thr,
            aggression=aggr,
            matrix=matrix_directive,
            breaker_cooldown_seconds=breaker_cd,
            edge_status=self._last_edge_status,
            recommended_risk_multiplier=round(final_mult, 3),
        )

    def _compute_matrix(
        self, snap: UsdtSnapshot, vol_state: VolState, loss_cluster_flag: bool,
    ) -> AggressionDirective:
        """Thin wrapper that assembles matrix inputs from brain state."""
        return self.matrix.evaluate(MatrixInputs(
            equity_usdt=snap.equity_usdt,
            starting_usdt=self.usdt.starting_capital(),
            volatility_state=vol_state,
            current_drawdown=self.usdt.current_drawdown(),
            weekly_growth_rate=self.usdt.weekly_growth_rate(),
            loss_cluster_flag=loss_cluster_flag,
        ))

    def _block(
        self, reason, breakdown, vol, phase, thr, effective, aggr, matrix_directive, breaker_cd,
    ) -> BrainDecision:
        return BrainDecision(
            allow=False,
            reason=reason,
            composite_score=breakdown.total,
            effective_threshold=effective,
            volatility=vol,
            score_breakdown=breakdown,
            risk=EntryDecision(Verdict.BLOCK, reason, 0.0),
            phase=phase,
            threshold_directive=thr,
            aggression=aggr,
            matrix=matrix_directive,
            breaker_cooldown_seconds=breaker_cd,
            edge_status=self._last_edge_status,
            recommended_risk_multiplier=0.0,
        )

    # ---- telemetry ----

    def telemetry(self) -> dict:
        snap = self.usdt.snapshot()
        stats = self.oracle.stats()
        thr = self.oracle.threshold()
        phase = self.phases.current()
        aggr = self.aggression.read(phase.phase, snap.rotation_velocity)
        breaker_tel = self.breaker.telemetry(phase.phase, snap.equity_usdt)
        # matrix snapshot using current state
        loss_cluster_flag = not self.breaker.allow()
        # use a synthesized vol state of NEUTRAL for a static telemetry read;
        # real matrix during evaluation uses the actual candidate's vol state
        matrix_directive = self._compute_matrix(
            snap, VolState.NEUTRAL, loss_cluster_flag,
        )
        return {
            "equity_usdt": snap.equity_usdt,
            "free_usdt": snap.free_usdt,
            "deployed_usdt": snap.deployed_usdt,
            "growth_multiple": self.usdt.growth_multiple(),
            "current_drawdown": round(self.usdt.current_drawdown(), 4),
            "weekly_growth_rate": round(self.usdt.weekly_growth_rate(), 4),
            "realized_24h": snap.realized_pnl_24h,
            "turnover_24h": snap.turnover_24h,
            "rotation_velocity": snap.rotation_velocity,
            "trades_24h": snap.trade_count_24h,
            "win_rate": stats.win_rate,
            "expectancy_r": stats.expectancy_r,
            "profit_factor": stats.profit_factor,
            "sharpe": stats.sharpe,
            "max_dd": stats.max_drawdown_pct,
            "loss_streak": stats.loss_streak_current,
            "phase": phase.phase.value,
            "threshold": thr.effective_threshold,
            "threshold_rationale": thr.rationale,
            "aggression_mode": aggr.mode.value,
            "aggression_mult": aggr.multiplier,
            "growth_velocity_per_hour": aggr.growth_velocity_per_hour,
            "breaker_state": breaker_tel.state.value,
            "breaker_cooldown_s": breaker_tel.cooldown_remaining_seconds,
            "breaker_trips_24h": breaker_tel.trips_last_24h,
            "edge": self._last_edge_status.verdict.value if self._last_edge_status else "N/A",
            "matrix_effective_risk": matrix_directive.effective_risk,
            "matrix_effective_threshold": matrix_directive.effective_threshold,
            "matrix_max_concurrent": matrix_directive.max_concurrent_trades,
            "matrix_cooldown_min": matrix_directive.cooldown_minutes,
            "matrix_lock_reason": matrix_directive.lock_reason,
            "matrix_bands": {
                "capital": matrix_directive.capital_band.value,
                "dd": matrix_directive.drawdown_band.value,
                "growth": matrix_directive.growth_band.value,
                "vol": matrix_directive.vol_band.value,
            },
        }
