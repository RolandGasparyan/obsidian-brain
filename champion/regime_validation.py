"""
champion.regime_validation — Layer 2 §8 Regime estimator calibration validator.

Implements Section 8 of L99_REGIME_PROBABILITY.md.

Edge-independent. Pure math. NO exchange wiring.

Operator spec quote:

    Validate regime estimator via:
      1. Historical regime labeling
      2. Forward return alignment
      3. Expectancy per regime
      4. Stability across cycles

    If regime classification does not correlate with forward volatility
    or forward expectancy → reject model.

This module accumulates `(probabilities, forward_return, forward_volatility)`
observations and computes:

  - Pearson IC between P(EXPANSION) and forward_volatility
    (EXPANSION should be POSITIVELY correlated with subsequent vol)
  - Pearson IC between (most-likely regime) one-hot and forward_return
    (EXPANSION/HIGH_IMPULSE should align with positive forward returns
     when the strategy has a directional edge)
  - Per-regime expectancy of forward_return (which regime is profitable?)
  - Calibration diagnostics: does the predicted distribution actually
    correspond to observed outcomes?

Validation gate (operator spec):

  - If expansion-vol IC < min_vol_ic_threshold → reject
  - If best per-regime expectancy < min_regime_expectancy → reject
  - If sample size < min_observations → return "insufficient_data"

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from champion.regime_probability import RegimeProbabilities


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class RegimeValidatorConfig:
    min_observations: int = 100              # below this → "insufficient_data"
    min_vol_ic_threshold: float = 0.05       # P(EXPANSION) vs forward_vol
    min_regime_expectancy: float = 0.0       # at least one regime must beat 0


# ─────────────────────────────────────────────
# RESULT
# ─────────────────────────────────────────────

@dataclass
class RegimeValidationResult:
    n_observations: int
    expansion_vol_ic: float                   # IC(P(EXPANSION), forward_vol)
    high_impulse_vol_ic: float                # IC(P(HIGH_IMPULSE), forward_vol)
    regime_expectancies: Dict[str, float]     # forward_return mean per most-likely regime
    regime_counts: Dict[str, int]
    verdict: str                              # "accept" | "reject" | "insufficient_data"
    rejection_reasons: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────
# VALIDATOR
# ─────────────────────────────────────────────

class RegimeValidator:
    """Append-only collector + on-demand validator."""

    def __init__(self, config: Optional[RegimeValidatorConfig] = None):
        self.config = config or RegimeValidatorConfig()
        self._records: List[Tuple[RegimeProbabilities, float, float]] = []

    # ─────────────────────────────────────────

    def add_observation(
        self,
        probs: RegimeProbabilities,
        forward_return: float,
        forward_volatility: float,
    ) -> None:
        """Record one observation: a probability vector at time t, the
        return realized over [t, t+horizon], and the volatility realized
        over the same window."""
        if forward_volatility < 0:
            raise ValueError("forward_volatility must be >= 0")
        self._records.append((probs, forward_return, forward_volatility))

    # ─────────────────────────────────────────

    def reset(self) -> None:
        self._records.clear()

    # ─────────────────────────────────────────

    def n_observations(self) -> int:
        return len(self._records)

    # ─────────────────────────────────────────

    def validate(self) -> RegimeValidationResult:
        """Compute calibration diagnostics + accept/reject verdict."""
        n = len(self._records)
        cfg = self.config

        if n < cfg.min_observations:
            return RegimeValidationResult(
                n_observations=n,
                expansion_vol_ic=0.0,
                high_impulse_vol_ic=0.0,
                regime_expectancies={},
                regime_counts={},
                verdict="insufficient_data",
                rejection_reasons=[],
            )

        p_expansion = [r[0].p_expansion for r in self._records]
        p_high = [r[0].p_high_impulse for r in self._records]
        forward_vols = [r[2] for r in self._records]

        ic_expansion = _pearson(p_expansion, forward_vols)
        ic_high = _pearson(p_high, forward_vols)

        # Bucket forward_returns by most-likely regime label.
        regime_returns: Dict[str, List[float]] = {
            "DEAD": [], "NORMAL": [], "EXPANSION": [], "HIGH_IMPULSE": []
        }
        for probs, fwd_ret, _ in self._records:
            regime_returns[probs.most_likely].append(fwd_ret)

        regime_expectancies = {
            label: (sum(rs) / len(rs)) if rs else 0.0
            for label, rs in regime_returns.items()
        }
        regime_counts = {label: len(rs) for label, rs in regime_returns.items()}

        rejection_reasons: List[str] = []
        if ic_expansion < cfg.min_vol_ic_threshold:
            rejection_reasons.append(
                f"expansion_vol_ic={ic_expansion:.4f} < threshold={cfg.min_vol_ic_threshold}"
            )

        best_regime_e = max(regime_expectancies.values()) if regime_expectancies else 0.0
        if best_regime_e <= cfg.min_regime_expectancy:
            rejection_reasons.append(
                f"best_regime_expectancy={best_regime_e:.4f} <= "
                f"threshold={cfg.min_regime_expectancy}"
            )

        verdict = "reject" if rejection_reasons else "accept"

        return RegimeValidationResult(
            n_observations=n,
            expansion_vol_ic=ic_expansion,
            high_impulse_vol_ic=ic_high,
            regime_expectancies=regime_expectancies,
            regime_counts=regime_counts,
            verdict=verdict,
            rejection_reasons=rejection_reasons,
        )


# ─────────────────────────────────────────────
# INTERNAL
# ─────────────────────────────────────────────

def _pearson(x: List[float], y: List[float]) -> float:
    """Pearson correlation. Returns 0.0 when undefined (n<2 or zero variance)."""
    if len(x) < 2:
        return 0.0
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    num = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    den_x = math.sqrt(sum((a - mean_x) ** 2 for a in x))
    den_y = math.sqrt(sum((b - mean_y) ** 2 for b in y))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)
