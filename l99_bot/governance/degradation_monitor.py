"""
L99 Governance — Degradation Monitor
Detects statistical edge decay by comparing rolling metrics against stored baseline.
Only reduces risk or freezes — never increases.
"""
import logging
from dataclasses import dataclass

import db

logger = logging.getLogger("l99.governance.degradation")


@dataclass
class DegradationDecision:
    level:            int     # 0=none, 1=mild, 2=moderate, 3=freeze
    risk_multiplier:  float
    disable_assets:   list[str]
    requires_freeze:  bool
    reason:           str


def evaluate(current: dict, baseline: dict | None,
             per_asset: dict[str, dict] | None = None) -> DegradationDecision:
    if not baseline or baseline.get("count", 0) < 5:
        return DegradationDecision(
            level=0, risk_multiplier=1.0, disable_assets=[],
            requires_freeze=False, reason="no baseline — skipping degradation check"
        )

    base_sharpe   = baseline.get("sharpe", 0.0)
    current_sharpe = current.get("sharpe", 0.0)
    current_wr     = current.get("win_rate", 0.0)

    if base_sharpe <= 0:
        return DegradationDecision(
            level=0, risk_multiplier=1.0, disable_assets=[],
            requires_freeze=False, reason="baseline Sharpe zero — skipping"
        )

    sharpe_drop = (base_sharpe - current_sharpe) / base_sharpe   # positive = degraded

    # Level 3 — FREEZE
    if current_sharpe < 1.0:
        return DegradationDecision(
            level=3, risk_multiplier=0.0, disable_assets=[],
            requires_freeze=True,
            reason=f"Sharpe {current_sharpe:.3f} < 1.0 absolute floor"
        )

    # Level 2 — severe drop or low win rate
    if sharpe_drop >= 0.40 or current_wr < 0.45:
        weak_assets = _find_weak_assets(per_asset, sharpe_threshold=1.0)
        return DegradationDecision(
            level=2, risk_multiplier=0.5, disable_assets=weak_assets,
            requires_freeze=False,
            reason=(f"Sharpe drop {sharpe_drop:.0%} >= 40%" if sharpe_drop >= 0.40
                    else f"win rate {current_wr:.1%} < 45%")
        )

    # Level 1 — moderate drop
    if sharpe_drop >= 0.20:
        return DegradationDecision(
            level=1, risk_multiplier=0.75, disable_assets=[],
            requires_freeze=False,
            reason=f"Sharpe drop {sharpe_drop:.0%} >= 20% vs baseline"
        )

    return DegradationDecision(
        level=0, risk_multiplier=1.0, disable_assets=[],
        requires_freeze=False,
        reason="no degradation detected"
    )


def _find_weak_assets(per_asset: dict[str, dict] | None,
                      sharpe_threshold: float) -> list[str]:
    if not per_asset:
        return []
    return [sym for sym, m in per_asset.items()
            if m.get("sharpe", 0.0) < sharpe_threshold and m.get("count", 0) >= 10]
