"""
L99 Governance — Scaling Committee
Evaluates eligibility for capital tier transitions.
Upscaling NEVER automatic — requires manual confirmation token.
Downscaling IS automatic.
"""
import logging
from dataclasses import dataclass

from core.state_machine import ScalingTier

logger = logging.getLogger("l99.governance.scaling")

MAX_RISK_CAP = 0.015   # absolute hard cap — never exceed 1.5%


@dataclass
class ScalingEligibility:
    eligible:      bool
    current_tier:  ScalingTier
    target_tier:   ScalingTier | None
    reasons_met:   list[str]
    reasons_unmet: list[str]


def check_upgrade_eligibility(
    current_tier: ScalingTier,
    metrics: dict,
    trade_count: int,
    freeze_events_last_60d: int = 0,
) -> ScalingEligibility:
    if current_tier == ScalingTier.TIER_0:
        target = ScalingTier.TIER_1
        return _check_tier0_to_1(metrics, trade_count, target)

    if current_tier == ScalingTier.TIER_1:
        target = ScalingTier.TIER_2
        return _check_tier1_to_2(metrics, trade_count, freeze_events_last_60d, target)

    if current_tier == ScalingTier.TIER_2:
        target = ScalingTier.TIER_3
        return _check_tier2_to_3(metrics, trade_count, target)

    return ScalingEligibility(
        eligible=False, current_tier=current_tier, target_tier=None,
        reasons_met=[], reasons_unmet=["already at maximum tier"]
    )


def _check_tier0_to_1(metrics, trade_count, target) -> ScalingEligibility:
    met, unmet = [], []
    _gate(trade_count >= 50,    f"{trade_count}/50 testnet trades",    "≥50 testnet trades",    met, unmet)
    _gate(metrics.get("sharpe", 0) >= 1.5, f"Sharpe={metrics.get('sharpe',0):.3f}", "Sharpe≥1.5", met, unmet)
    return ScalingEligibility(eligible=not unmet, current_tier=ScalingTier.TIER_0,
                              target_tier=target, reasons_met=met, reasons_unmet=unmet)


def _check_tier1_to_2(metrics, trade_count, freeze_events, target) -> ScalingEligibility:
    met, unmet = [], []
    sharpe = metrics.get("sharpe", 0.0)
    pf     = metrics.get("profit_factor", 0.0)
    dd     = abs(metrics.get("current_dd", 1.0))

    _gate(trade_count >= 100,        f"{trade_count}/100 live trades",    "≥100 live trades",    met, unmet)
    _gate(sharpe >= 1.7,             f"Sharpe={sharpe:.3f}",              "Sharpe≥1.7",          met, unmet)
    _gate(pf >= 1.5,                 f"PF={pf:.2f}",                      "PF≥1.5",              met, unmet)
    _gate(dd < 0.15,                 f"DD={dd:.2%}",                      "DD<15%",              met, unmet)
    _gate(freeze_events == 0,        f"freeze_events={freeze_events}",    "no freeze events",    met, unmet)
    return ScalingEligibility(eligible=not unmet, current_tier=ScalingTier.TIER_1,
                              target_tier=target, reasons_met=met, reasons_unmet=unmet)


def _check_tier2_to_3(metrics, trade_count, target) -> ScalingEligibility:
    met, unmet = [], []
    sharpe = metrics.get("sharpe", 0.0)

    _gate(trade_count >= 200,   f"{trade_count}/200 live trades", "≥200 live trades", met, unmet)
    _gate(sharpe >= 1.8,        f"Sharpe={sharpe:.3f}",           "Sharpe≥1.8",       met, unmet)
    return ScalingEligibility(eligible=not unmet, current_tier=ScalingTier.TIER_2,
                              target_tier=target, reasons_met=met, reasons_unmet=unmet)


def _gate(condition: bool, actual: str, requirement: str,
          met: list, unmet: list) -> None:
    if condition:
        met.append(f"✓ {requirement} ({actual})")
    else:
        unmet.append(f"✗ {requirement} — got {actual}")
