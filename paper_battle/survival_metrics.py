#!/usr/bin/env python3
"""
survival_metrics.py — Sovereign Survival Score

Per governance/SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER_v1.md (spec #22 Section VII).

System success measured by LONGEVITY metrics, not single-round profit:
    • Low volatility equity curve
    • Controlled drawdown behavior
    • High survival probability
    • Stable compounding
    • Low entropy allocation
    • Tail-risk immunity

API:
    score = compute_sovereign_survival_score(round_summary)
    → dict with sovereign_survival_score (0-100) + component breakdown
"""

from __future__ import annotations

import math
from typing import Any


# Component weights — sum to 1.0
WEIGHTS = {
    "low_volatility":        0.18,  # execution stability proxy
    "drawdown_control":      0.20,  # max_dd within band
    "survival_probability":  0.22,  # 100% - risk_of_ruin
    "stable_compounding":    0.15,  # CAGR sanity + edge_preservation
    "low_entropy":           0.10,  # regime predictability
    "tail_risk_immunity":    0.15,  # p05 vs starting capital
}


def _safe(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bounded(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _low_volatility_score(execution_stability_score: float) -> float:
    """
    Already 0-100. Higher = lower slippage variance = lower equity curve volatility.
    Pass threshold: ≥ 80 (Spec #15 Section IV).
    """
    return _bounded(execution_stability_score)


def _drawdown_control_score(max_dd_pct: float, max_dd_p95_pct: float,
                            constitutional_dd_pct: float = 2.0) -> float:
    """
    Realized + projected DD vs Article 3 cap.
    100 if both <= 50% of cap. 0 if either >= 200% of cap.
    """
    realized_norm = max(0.0, min(1.0, max_dd_pct / constitutional_dd_pct))
    projected_norm = max(0.0, min(1.0, max_dd_p95_pct / constitutional_dd_pct))
    worst = max(realized_norm, projected_norm)
    # 0 → 100, 0.5 → 75, 1.0 → 50, 1.5 → 25, 2.0+ → 0
    score = 100.0 * max(0.0, 1.0 - worst * 0.5)
    return _bounded(score)


def _survival_probability_score(risk_of_ruin_pct: float,
                                max_ror_pct: float = 1.0) -> float:
    """
    Spec #22 + #20: target RoR < 1%. Penalize harshly above.
    RoR 0% → 100. RoR = max → 50. RoR = 5*max → 0.
    """
    if risk_of_ruin_pct <= 0:
        return 100.0
    ratio = risk_of_ruin_pct / max_ror_pct
    if ratio >= 5.0:
        return 0.0
    # Smooth decay: 100 * (1 - log10(1 + 9 * ratio/5))
    score = 100.0 * max(0.0, 1.0 - math.log10(1.0 + 9.0 * ratio / 5.0))
    return _bounded(score)


def _stable_compounding_score(cagr_estimate_pct: float,
                              edge_preservation_pct: float) -> float:
    """
    Two-factor: CAGR positive AND edge preservation ≥ 90%.
    Edge dominates: if edge < 90% the strategy is bleeding cost, regardless of CAGR sign.
    """
    # Edge preservation portion (Spec #15 PASS threshold 90%).
    if edge_preservation_pct <= 0:
        edge_part = 0.0
    elif edge_preservation_pct >= 100:
        edge_part = 100.0
    else:
        edge_part = max(0.0, edge_preservation_pct - 50.0) * 2.0  # 50% → 0, 75% → 50, 100% → 100
    # CAGR portion: positive bonus, negative penalty.
    cagr_part = _bounded(50.0 + cagr_estimate_pct * 5.0)  # 0% CAGR → 50, +10% → 100, -10% → 0
    return _bounded(0.7 * edge_part + 0.3 * cagr_part)


def _low_entropy_score(avg_regime_entropy_nats: float,
                       max_entropy: float = 1.792) -> float:
    """
    Shannon entropy of 6-regime posterior. Max ln(6) ≈ 1.792.
    Lower entropy = more predictable regime = higher score.
    Floor at 30 even at max entropy (we don't fully penalize healthy uncertainty).
    """
    if max_entropy <= 0:
        return 50.0
    norm = max(0.0, min(1.0, avg_regime_entropy_nats / max_entropy))
    return _bounded(30.0 + (1.0 - norm) * 70.0)


def _tail_risk_immunity_score(p05_equity: float, starting_capital: float) -> float:
    """
    5th-percentile equity from Monte Carlo vs starting capital.
    p05 == starting → 100 (no tail loss in worst 5%).
    p05 == 0.95 × starting → 50.
    p05 == 0.85 × starting → 0.
    """
    if starting_capital <= 0:
        return 50.0
    ratio = p05_equity / starting_capital
    if ratio >= 1.0:
        return 100.0
    if ratio <= 0.85:
        return 0.0
    # Linear between 0.85 and 1.0
    return _bounded((ratio - 0.85) / 0.15 * 100.0)


def compute_sovereign_survival_score(round_summary: dict[str, Any]) -> dict[str, Any]:
    """
    Compute the Sovereign Survival Score from a shadow round summary dict.

    Returns dict with:
        sovereign_survival_score   (float 0-100)
        sovereign_grade            (str)
        components                 (dict of named subscores)
        weights                    (dict, for transparency)
        spec_section               "Spec #22 Section VII"
    """
    execution_stability = _safe(round_summary.get("execution_stability_score"))
    max_dd_pct          = _safe(round_summary.get("max_dd_pct"))
    edge_preservation   = _safe(round_summary.get("edge_preservation_pct"))
    avg_entropy         = _safe(round_summary.get("avg_regime_entropy_nats"))
    mc                  = round_summary.get("monte_carlo_latest") or {}
    max_dd_p95          = _safe(mc.get("max_dd_p95_pct"))
    risk_of_ruin        = _safe(mc.get("risk_of_ruin_pct"))
    cagr                = _safe(mc.get("cagr_estimate_pct"))
    p05_equity          = _safe(mc.get("p05_equity"))
    starting_capital    = _safe(round_summary.get("virtual_capital_start_usdt"), 10.0)

    components = {
        "low_volatility":       _low_volatility_score(execution_stability),
        "drawdown_control":     _drawdown_control_score(max_dd_pct, max_dd_p95),
        "survival_probability": _survival_probability_score(risk_of_ruin),
        "stable_compounding":   _stable_compounding_score(cagr, edge_preservation),
        "low_entropy":          _low_entropy_score(avg_entropy),
        "tail_risk_immunity":   _tail_risk_immunity_score(p05_equity, starting_capital),
    }

    score = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    score = _bounded(score)

    # Grade ladder per Spec #22 Capital Evolution table mood.
    if score >= 85:
        grade = "SOVEREIGN_GRADE"
    elif score >= 70:
        grade = "INSTITUTIONAL_READY"
    elif score >= 55:
        grade = "MICRO_READY"
    elif score >= 40:
        grade = "PAPER_VALIDATING"
    else:
        grade = "INSUFFICIENT_LONGEVITY"

    return {
        "sovereign_survival_score": round(score, 2),
        "sovereign_grade": grade,
        "components": {k: round(v, 2) for k, v in components.items()},
        "weights": WEIGHTS,
        "spec_section": "Spec #22 Section VII",
    }
