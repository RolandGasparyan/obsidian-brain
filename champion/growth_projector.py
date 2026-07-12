"""
champion.growth_projector — Layer 3 §3.2 + §3.4 Realistic monthly return estimator.

Implements Sections 3.2 + 3.4 of L99_CAPITAL_MATHEMATICS.md.

Edge-independent. Pure math. NO exchange wiring. NO strategy dependency.

Section 3.2 formula:

    raw_monthly = expectancy_R × trades_per_month × risk_per_trade

Then a variance haircut (Section 3.2 quote: "Reduce by 30-50% to account for
clustering"):

    adjusted_monthly = raw_monthly × (1 - variance_haircut)

Section 3.4 target bands for spot momentum (operator-spec):

    Conservative:                   3 - 6%
    Moderate:                       6 - 10%
    Aggressive but sustainable:     10 - 15%
    Anything > 20% consistently → suspect overfitting

The projector returns a classification telling the caller which band the
adjusted projection falls into, plus an overfitting warning when the raw
projection blows past 20%.

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class GrowthProjectorConfig:
    """Operator-spec defaults from L99_CAPITAL_MATHEMATICS §3.2 + §3.4."""

    variance_haircut: float = 0.40                # 40% haircut (mid of 30-50% spec band)
    target_band_min: float = 0.06                 # 6% conservative-moderate boundary
    target_band_max: float = 0.10                 # 10% moderate-aggressive boundary
    aggressive_max: float = 0.15                  # 15% aggressive-sustainable ceiling
    overfitting_warn_threshold: float = 0.20      # > 20% raw → suspect overfitting

    def __post_init__(self) -> None:
        if not (0.0 <= self.variance_haircut < 1.0):
            raise ValueError("variance_haircut must be in [0, 1)")
        if not (0.0 < self.target_band_min < self.target_band_max < self.aggressive_max):
            raise ValueError(
                "target_band_min < target_band_max < aggressive_max required"
            )


# ─────────────────────────────────────────────
# RESULT
# ─────────────────────────────────────────────

@dataclass
class ProjectionResult:
    raw_monthly: float
    adjusted_monthly: float
    classification: str             # "below_band" | "conservative" | "moderate" |
                                    # "aggressive_sustainable" | "above_band"
    overfitting_warning: bool


# ─────────────────────────────────────────────
# PROJECTOR
# ─────────────────────────────────────────────

class GrowthProjector:

    def __init__(self, config: Optional[GrowthProjectorConfig] = None):
        self.config = config or GrowthProjectorConfig()

    # ─────────────────────────────────────────

    def project(
        self,
        expectancy_r: float,
        trades_per_month: float,
        risk_per_trade: float,
    ) -> ProjectionResult:
        """Project realistic monthly return per Section 3.2 + classify per §3.4."""
        if trades_per_month < 0:
            raise ValueError("trades_per_month must be >= 0")
        if not (0.0 <= risk_per_trade <= 1.0):
            raise ValueError("risk_per_trade must be in [0, 1]")

        raw = expectancy_r * trades_per_month * risk_per_trade
        adjusted = raw * (1.0 - self.config.variance_haircut)

        cfg = self.config
        # Conservative band: just below target_band_min counts as conservative
        # but classification helps callers decide. Use abs() for negative
        # adjustments (negative expectancy gives below_band).
        if adjusted < cfg.target_band_min * 0.5:
            classification = "below_band"
        elif adjusted < cfg.target_band_min:
            classification = "conservative"
        elif adjusted < cfg.target_band_max:
            classification = "moderate"
        elif adjusted <= cfg.aggressive_max:
            classification = "aggressive_sustainable"
        else:
            classification = "above_band"

        # Overfitting warning fires on RAW (pre-haircut) value, since the
        # haircut is itself a variance-adjustment.
        overfitting = raw > cfg.overfitting_warn_threshold

        return ProjectionResult(
            raw_monthly=raw,
            adjusted_monthly=adjusted,
            classification=classification,
            overfitting_warning=overfitting,
        )
