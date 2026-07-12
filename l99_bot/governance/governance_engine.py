"""
L99 Governance — Engine
Single orchestrator for all governance decisions.
Only this module may change governance state.
Called from live_bot.py main loop when GOVERNANCE_ENABLED=true.
"""
import json
import logging
from dataclasses import dataclass, field

import db
import telegram_alerts as tg
import config
from core.state_machine import (
    GovernanceState, RiskLevel, assert_valid_transition
)
from governance.performance_metrics import fetch_portfolio_metrics, fetch_per_asset_metrics
from governance.risk_committee import evaluate as risk_evaluate, RiskDecision
from governance.degradation_monitor import evaluate as degradation_evaluate
from governance.capital_allocator import compute_weights, AllocationResult

logger = logging.getLogger("l99.governance.engine")

_MIN_TRADES_TO_ACTIVATE = getattr(config, "GOVERNANCE_MIN_TRADES", 50)
_REBALANCE_EVERY        = 20   # closed trades between allocation updates


@dataclass
class GovernanceDecision:
    state:                GovernanceState
    effective_risk_pct:   float
    effective_max_concurrent: int
    is_frozen:            bool
    disabled_assets:      list[str]              = field(default_factory=list)
    asset_weights:        dict[str, float]       = field(default_factory=dict)
    reason:               str                    = ""


class GovernanceEngine:

    def __init__(self) -> None:
        self._state       = GovernanceState.NORMAL
        self._baseline:   dict | None = None
        self._allocation: AllocationResult | None = None
        self._last_rebalance_count: int = 0
        self._load_state()

    # ── Public ───────────────────────────────────────────────────

    def evaluate(self, current_drawdown: float = 0.0) -> GovernanceDecision:
        metrics     = fetch_portfolio_metrics(30)
        per_asset   = fetch_per_asset_metrics(30)
        trade_count = metrics.get("count", 0)

        if trade_count < _MIN_TRADES_TO_ACTIVATE:
            return self._passthrough(
                f"governance inactive — {trade_count}/{_MIN_TRADES_TO_ACTIVATE} trades"
            )

        self._maybe_set_baseline(metrics)

        risk_dec  = risk_evaluate(metrics, current_drawdown)
        deg_dec   = degradation_evaluate(metrics, self._baseline, per_asset)

        # Degradation overrides risk_committee if more severe
        multiplier = min(risk_dec.risk_multiplier, deg_dec.risk_multiplier)
        is_frozen  = (risk_dec.level == RiskLevel.FROZEN or deg_dec.requires_freeze)

        new_state = self._state
        if is_frozen:
            new_state = GovernanceState.FROZEN
        elif multiplier <= 0.5:
            new_state = GovernanceState.RESTRICTED
        elif multiplier < 1.0:
            new_state = GovernanceState.THROTTLED
        else:
            new_state = GovernanceState.NORMAL

        if new_state != self._state:
            self._transition(self._state, new_state,
                             deg_dec.reason or risk_dec.reason, metrics)

        # Rebalance allocator every _REBALANCE_EVERY trades
        if (trade_count - self._last_rebalance_count) >= _REBALANCE_EVERY:
            self._allocation = compute_weights(per_asset, trade_count)
            self._last_rebalance_count = trade_count

        alloc = self._allocation
        return GovernanceDecision(
            state                  = self._state,
            effective_risk_pct     = config.RISK_PER_TRADE * multiplier,
            effective_max_concurrent = 0 if is_frozen else risk_dec.max_concurrent,
            is_frozen              = is_frozen,
            disabled_assets        = deg_dec.disable_assets + (alloc.disabled_assets if alloc else []),
            asset_weights          = alloc.weights if alloc else {},
            reason                 = risk_dec.reason,
        )

    # ── Internal ─────────────────────────────────────────────────

    def _passthrough(self, reason: str) -> GovernanceDecision:
        return GovernanceDecision(
            state                    = GovernanceState.NORMAL,
            effective_risk_pct       = config.RISK_PER_TRADE,
            effective_max_concurrent = config.MAX_CONCURRENT,
            is_frozen                = False,
            reason                   = reason,
        )

    def _transition(self, from_state: GovernanceState, to_state: GovernanceState,
                    reason: str, metrics: dict) -> None:
        try:
            assert_valid_transition(from_state, to_state)
        except ValueError as e:
            logger.warning("Governance transition blocked: %s", e)
            return

        self._state = to_state
        logger.warning("Governance state: %s → %s  reason=%s", from_state, to_state, reason)

        db.log_governance_event(
            event_type     = "STATE_CHANGE",
            old_state      = from_state,
            new_state      = to_state,
            reason         = reason,
            metrics_snapshot = metrics,
        )
        self._send_alert(from_state, to_state, reason, metrics)

    def _send_alert(self, from_state, to_state, reason, metrics) -> None:
        sharpe = metrics.get("sharpe", 0.0)
        pf     = metrics.get("profit_factor", 0.0)
        dd     = metrics.get("current_dd", 0.0)

        if to_state == GovernanceState.FROZEN:
            tg.alert_governance_freeze(sharpe=sharpe, pf=pf, dd=dd, reason=reason)
        elif to_state in (GovernanceState.RESTRICTED, GovernanceState.REVIEW_REQUIRED):
            tg.alert_governance_critical(reason=reason, metrics=metrics)
        elif to_state == GovernanceState.THROTTLED:
            tg.alert_governance_warning(reason=reason, metrics=metrics)
        else:
            tg.alert_governance_info(
                f"Governance restored to {to_state} — {reason}"
            )

    def _maybe_set_baseline(self, metrics: dict) -> None:
        if self._baseline is None:
            self._baseline = db.get_governance_baseline()
        if self._baseline is None and metrics.get("count", 0) >= _MIN_TRADES_TO_ACTIVATE:
            db.save_governance_baseline(metrics)
            self._baseline = metrics
            logger.info("Governance baseline set: sharpe=%.3f pf=%.2f",
                        metrics.get("sharpe", 0), metrics.get("profit_factor", 0))

    def _load_state(self) -> None:
        try:
            saved = db.get_current_governance_state()
            if saved:
                self._state = GovernanceState(saved)
        except Exception:
            pass
