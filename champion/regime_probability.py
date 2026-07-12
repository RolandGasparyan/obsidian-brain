"""
champion.regime_probability — Layer 2 §1-§5 Dynamic Regime Probability Estimator.

Implements Sections 1-5 of L99_REGIME_PROBABILITY.md.

Edge-independent. Pure feature engineering. NO exchange wiring. NO strategy
dependency. Library only.

The estimator outputs a probability distribution over 4 regimes:

    R1 — DEAD          (low vol, low volume, no trend, wide spread)
    R2 — NORMAL        (mid vol, stable spread, balanced flow)
    R3 — EXPANSION     (high vol, high volume, breakout)
    R4 — HIGH_IMPULSE  (extreme vol, impulse delta, strong breadth)

Approach (Section 3, baseline):

    score_R = Σ (weight[i] × feature[i]) + bias
    P(R)   = softmax(scores)

Plus a derived `mid_vol_score` feature (peak at vol_pct=0.5, falling off
linearly toward 0 and 1) so NORMAL can be modeled by a single-peaked
function within an otherwise linear scoring scheme.

Section 4 exposure multiplier:

    multiplier = 0.0×P(R1) + 0.5×P(R2) + 1.0×P(R3) + 1.2×P(R4)

Section 5 effective expectancy:

    E_total = Σ P(Ri) × E(Ri)

If E_total ≤ 0 → caller must disable trading.

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from typing import Dict, Optional


# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class RegimeFeatures:
    """All inputs in [0, 1] (normalize externally before passing in).

    Maps to L99_REGIME_PROBABILITY §2 input features:
      1. Realized Volatility Percentile (vol_percentile)
      2. Volume Percentile vs 90d baseline (volume_percentile)
      3. ATR Expansion Ratio (atr_expansion)
      4. Spread Stability Index (spread_stability)
      5. BTC Structural Trend Strength (btc_trend)
      6. Market Breadth (market_breadth) — see champion.regime_breadth
      7. Delta Intensity (delta_intensity)
      8. Liquidity Stability Score (liquidity_stability) — see champion.regime_liquidity
    """
    vol_percentile: float = 0.0
    volume_percentile: float = 0.0
    atr_expansion: float = 0.0
    spread_stability: float = 0.0
    btc_trend: float = 0.0
    market_breadth: float = 0.0
    delta_intensity: float = 0.0
    liquidity_stability: float = 0.0

    def __post_init__(self) -> None:
        for f in fields(self):
            v = getattr(self, f.name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{f.name} must be in [0, 1], got {v}")


@dataclass
class RegimeWeights:
    """Linear weights for one regime: score = Σ weight[i]·feature[i] + bias."""
    vol_percentile: float = 0.0
    volume_percentile: float = 0.0
    atr_expansion: float = 0.0
    spread_stability: float = 0.0
    btc_trend: float = 0.0
    market_breadth: float = 0.0
    delta_intensity: float = 0.0
    liquidity_stability: float = 0.0
    mid_vol_score: float = 0.0     # derived: 1 - 2·|vol_pct - 0.5|, peak at 0.5
    bias: float = 0.0


@dataclass
class RegimeProbabilities:
    """Probability distribution over 4 regimes; sum = 1."""
    p_dead: float
    p_normal: float
    p_expansion: float
    p_high_impulse: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "DEAD": self.p_dead,
            "NORMAL": self.p_normal,
            "EXPANSION": self.p_expansion,
            "HIGH_IMPULSE": self.p_high_impulse,
        }

    @property
    def most_likely(self) -> str:
        """Label of the regime with the highest probability."""
        d = self.as_dict()
        return max(d, key=d.get)


# ─────────────────────────────────────────────
# DEFAULT WEIGHTS (operator-spec-derived)
# ─────────────────────────────────────────────

# DEAD — low everything; positive bias keeps it competitive at zero input.
_DEFAULT_WEIGHTS_DEAD = RegimeWeights(
    vol_percentile=-2.0,
    volume_percentile=-2.0,
    btc_trend=-1.0,
    spread_stability=-1.0,
    bias=2.0,
)

# NORMAL — wins via mid_vol_score peak; small positive contribution from
# spread_stability indicates orderly market.
_DEFAULT_WEIGHTS_NORMAL = RegimeWeights(
    spread_stability=0.5,
    mid_vol_score=2.0,
    bias=0.0,
)

# EXPANSION — high vol, high volume, atr expansion, btc trend.
_DEFAULT_WEIGHTS_EXPANSION = RegimeWeights(
    vol_percentile=2.0,
    volume_percentile=1.5,
    atr_expansion=1.0,
    btc_trend=1.0,
    bias=-1.0,
)

# HIGH_IMPULSE — extreme vol, impulse delta, strong breadth; large negative
# bias so it only activates on multi-feature extremes.
_DEFAULT_WEIGHTS_HIGH_IMPULSE = RegimeWeights(
    vol_percentile=3.0,
    delta_intensity=2.0,
    market_breadth=2.0,
    atr_expansion=1.0,
    bias=-3.0,
)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class RegimeProbabilityConfig:
    weights_dead: RegimeWeights = field(
        default_factory=lambda: _DEFAULT_WEIGHTS_DEAD
    )
    weights_normal: RegimeWeights = field(
        default_factory=lambda: _DEFAULT_WEIGHTS_NORMAL
    )
    weights_expansion: RegimeWeights = field(
        default_factory=lambda: _DEFAULT_WEIGHTS_EXPANSION
    )
    weights_high_impulse: RegimeWeights = field(
        default_factory=lambda: _DEFAULT_WEIGHTS_HIGH_IMPULSE
    )

    # Section 4 exposure multipliers
    mul_dead: float = 0.0
    mul_normal: float = 0.5
    mul_expansion: float = 1.0
    mul_high_impulse: float = 1.2


# ─────────────────────────────────────────────
# ESTIMATOR
# ─────────────────────────────────────────────

class RegimeProbabilityEstimator:
    """Stateless softmax-linear regime classifier.

    Does NOT track history; for transition velocity, see
    `champion.regime_transition.RegimeTransitionTracker`.

    Does NOT validate; for calibration diagnostics, see
    `champion.regime_validation.RegimeValidator`.
    """

    def __init__(self, config: Optional[RegimeProbabilityConfig] = None):
        self.config = config or RegimeProbabilityConfig()

    # ─────────────────────────────────────────

    @staticmethod
    def _score(weights: RegimeWeights, features: RegimeFeatures) -> float:
        mid_vol = 1.0 - 2.0 * abs(features.vol_percentile - 0.5)
        return (
            weights.vol_percentile * features.vol_percentile
            + weights.volume_percentile * features.volume_percentile
            + weights.atr_expansion * features.atr_expansion
            + weights.spread_stability * features.spread_stability
            + weights.btc_trend * features.btc_trend
            + weights.market_breadth * features.market_breadth
            + weights.delta_intensity * features.delta_intensity
            + weights.liquidity_stability * features.liquidity_stability
            + weights.mid_vol_score * mid_vol
            + weights.bias
        )

    # ─────────────────────────────────────────

    def estimate(self, features: RegimeFeatures) -> RegimeProbabilities:
        """Compute P(R1..R4) via softmax over per-regime linear scores."""
        cfg = self.config
        scores = [
            self._score(cfg.weights_dead, features),
            self._score(cfg.weights_normal, features),
            self._score(cfg.weights_expansion, features),
            self._score(cfg.weights_high_impulse, features),
        ]

        # Softmax with numerical stability (subtract max).
        max_s = max(scores)
        exps = [math.exp(s - max_s) for s in scores]
        total = sum(exps)
        probs = [e / total for e in exps]

        return RegimeProbabilities(
            p_dead=probs[0],
            p_normal=probs[1],
            p_expansion=probs[2],
            p_high_impulse=probs[3],
        )

    # ─────────────────────────────────────────

    def exposure_multiplier(self, probs: RegimeProbabilities) -> float:
        """Section 4: probability-weighted exposure multiplier."""
        cfg = self.config
        return (
            cfg.mul_dead * probs.p_dead
            + cfg.mul_normal * probs.p_normal
            + cfg.mul_expansion * probs.p_expansion
            + cfg.mul_high_impulse * probs.p_high_impulse
        )

    # ─────────────────────────────────────────

    @staticmethod
    def effective_expectancy(
        probs: RegimeProbabilities,
        e_per_regime: Dict[str, float],
    ) -> float:
        """Section 5: E_total = Σ P(Ri) × E(Ri).

        e_per_regime keys: 'DEAD', 'NORMAL', 'EXPANSION', 'HIGH_IMPULSE'.
        Missing keys default to 0.0.

        If E_total ≤ 0, caller MUST disable trading per spec.
        """
        return (
            probs.p_dead * e_per_regime.get("DEAD", 0.0)
            + probs.p_normal * e_per_regime.get("NORMAL", 0.0)
            + probs.p_expansion * e_per_regime.get("EXPANSION", 0.0)
            + probs.p_high_impulse * e_per_regime.get("HIGH_IMPULSE", 0.0)
        )
