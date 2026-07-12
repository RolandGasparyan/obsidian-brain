"""
L99 Governance — Risk Committee
Evaluates current rolling metrics and returns a risk decision.
Never increases risk — only reduces or freezes.
"""
import logging
from dataclasses import dataclass

from core.state_machine import RiskLevel
import config

logger = logging.getLogger("l99.governance.risk")

# Risk multipliers per level
_MULTIPLIERS: dict[RiskLevel, float] = {
    RiskLevel.NORMAL:     1.0,
    RiskLevel.THROTTLED:  0.75,
    RiskLevel.RESTRICTED: 0.5,
    RiskLevel.FROZEN:     0.0,
}

_MAX_CONCURRENT: dict[RiskLevel, int] = {
    RiskLevel.NORMAL:     config.MAX_CONCURRENT,
    RiskLevel.THROTTLED:  config.MAX_CONCURRENT,
    RiskLevel.RESTRICTED: 1,
    RiskLevel.FROZEN:     0,
}


@dataclass
class RiskDecision:
    level:             RiskLevel
    risk_multiplier:   float
    max_concurrent:    int
    reason:            str

    @property
    def effective_risk_pct(self) -> float:
        return config.RISK_PER_TRADE * self.risk_multiplier


def evaluate(metrics: dict, current_drawdown: float) -> RiskDecision:
    sharpe = metrics.get("sharpe", 0.0)
    pf     = metrics.get("profit_factor", 0.0)
    count  = metrics.get("count", 0)
    dd_abs = abs(current_drawdown)
    kill_threshold = config.KILL_DD_ABS

    if count < 5:
        return RiskDecision(
            level=RiskLevel.NORMAL, risk_multiplier=1.0,
            max_concurrent=config.MAX_CONCURRENT,
            reason="insufficient data — normal mode"
        )

    # FROZEN: drawdown at/beyond kill threshold
    if dd_abs >= kill_threshold:
        return RiskDecision(
            level=RiskLevel.FROZEN, risk_multiplier=0.0,
            max_concurrent=0,
            reason=f"drawdown {dd_abs:.2%} >= kill threshold {kill_threshold:.2%}"
        )

    # RESTRICTED: Sharpe < 1.0 OR PF < 1.3 OR DD > 70% of kill level
    if sharpe < 1.0 or pf < 1.3 or dd_abs > 0.7 * kill_threshold:
        reason = (f"sharpe={sharpe:.3f} < 1.0" if sharpe < 1.0 else
                  f"PF={pf:.2f} < 1.3" if pf < 1.3 else
                  f"DD {dd_abs:.2%} > 70% of kill threshold")
        return RiskDecision(
            level=RiskLevel.RESTRICTED, risk_multiplier=0.5,
            max_concurrent=1, reason=reason
        )

    # THROTTLED: Sharpe < 1.2
    if sharpe < 1.2:
        return RiskDecision(
            level=RiskLevel.THROTTLED, risk_multiplier=0.75,
            max_concurrent=config.MAX_CONCURRENT,
            reason=f"sharpe={sharpe:.3f} < 1.2"
        )

    return RiskDecision(
        level=RiskLevel.NORMAL, risk_multiplier=1.0,
        max_concurrent=config.MAX_CONCURRENT,
        reason="metrics within normal bounds"
    )
