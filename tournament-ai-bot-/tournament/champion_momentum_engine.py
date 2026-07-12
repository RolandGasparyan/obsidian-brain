"""
champion_momentum_engine.py
---------------------------
Weighted composite scoring for tournament entry decisions.

Replaces N-of-M binary gates with a continuous score in [0, 100].
fusion_brain.py calls score() per candidate; decision_pipeline compares
against an adaptive threshold from capital_phase_manager + performance_oracle.

Dimensions (weights sum to 1.0 by default, overridable per mode):
    momentum      0.22   trend strength, ROC, EMA stack
    volume        0.15   relative volume vs N-period median
    regime        0.15   regime classifier fit score
    orderflow     0.12   taker buy ratio, bid/ask imbalance
    smart_money   0.10   large-trade bias (CVD slope)
    ml_confidence 0.12   external ML prob from fusion_brain
    risk_reward   0.14   ATR-normalized R:R of proposed stop/target

Non-goals:
    - Does not fetch data. Caller provides precomputed features.
    - Does not decide entry. Returns score + breakdown.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np


DEFAULT_WEIGHTS: Dict[str, float] = {
    "momentum": 0.22,
    "volume": 0.15,
    "regime": 0.15,
    "orderflow": 0.12,
    "smart_money": 0.10,
    "ml_confidence": 0.12,
    "risk_reward": 0.14,
}


@dataclass
class CandidateFeatures:
    """Precomputed per-pair features. All values should already be normalized
    to [0, 1] where higher = more bullish, except where noted."""
    pair: str
    # momentum
    roc_pct: float                      # raw % return over lookback (signed)
    ema_stack_score: float              # [0,1] 1 = fast>mid>slow, aligned
    rsi: float                          # 0-100 raw
    # volume
    rel_volume: float                   # ratio vs median (1.0 = normal)
    # regime
    regime_fit: float                   # [0,1] classifier confidence for momentum regime
    # orderflow
    taker_buy_ratio: float              # 0-1 (>0.5 = buy pressure)
    book_imbalance: float               # [-1,1] (bid-ask)/(bid+ask)
    # smart money
    cvd_slope_z: float                  # z-score of cumulative volume delta slope
    # ML
    ml_long_prob: float                 # 0-1
    # risk/reward
    atr_pct: float                      # ATR / price
    proposed_rr: float                  # target_distance / stop_distance
    # optional overrides
    side: str = "long"                  # spot only, effectively always 'long'


@dataclass
class ScoreBreakdown:
    total: float                        # 0-100
    components: Dict[str, float]        # each 0-100 pre-weight
    weighted: Dict[str, float]          # each contribution post-weight
    rejected_reasons: list[str] = field(default_factory=list)


def _clip01(x: float) -> float:
    if x != x:  # NaN guard
        return 0.0
    return max(0.0, min(1.0, x))


def _sigmoid(x: float, k: float = 1.0) -> float:
    return 1.0 / (1.0 + math.exp(-k * x))


class ChampionMomentumEngine:
    """Stateless scorer. Safe for concurrent use."""

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        w = dict(DEFAULT_WEIGHTS)
        if weights:
            w.update(weights)
        total = sum(w.values())
        if total <= 0:
            raise ValueError("weights must sum to > 0")
        # renormalize so weights always sum to 1 even if caller passes partial overrides
        self._w = {k: v / total for k, v in w.items()}

    @property
    def weights(self) -> Dict[str, float]:
        return dict(self._w)

    # ---- individual component scorers, each returning [0, 100] ----

    @staticmethod
    def _score_momentum(f: CandidateFeatures) -> float:
        # ROC normalized via sigmoid around 0 with k tuned so 2% -> ~0.73
        roc = _sigmoid(f.roc_pct, k=35.0)
        ema = _clip01(f.ema_stack_score)
        # RSI sweet spot 55-70 for momentum; penalize overbought >80
        if f.rsi <= 50:
            rsi = 0.0
        elif f.rsi <= 70:
            rsi = (f.rsi - 50) / 20.0
        elif f.rsi <= 80:
            rsi = 1.0
        else:
            rsi = max(0.0, 1.0 - (f.rsi - 80) / 20.0)
        raw = 0.45 * roc + 0.35 * ema + 0.20 * rsi
        return 100.0 * _clip01(raw)

    @staticmethod
    def _score_volume(f: CandidateFeatures) -> float:
        # log-scaled relative volume; 1x -> 0, 2x -> ~0.5, 4x -> ~0.87
        if f.rel_volume <= 0:
            return 0.0
        x = math.log2(max(f.rel_volume, 0.25))
        return 100.0 * _clip01(_sigmoid(x - 0.5, k=1.2))

    @staticmethod
    def _score_regime(f: CandidateFeatures) -> float:
        return 100.0 * _clip01(f.regime_fit)

    @staticmethod
    def _score_orderflow(f: CandidateFeatures) -> float:
        taker = _clip01(f.taker_buy_ratio)
        # shift so 0.5 -> 0, 0.7 -> 1.0
        taker_norm = _clip01((taker - 0.5) / 0.2)
        imbalance = _clip01((f.book_imbalance + 1.0) / 2.0)  # map [-1,1] -> [0,1]
        return 100.0 * (0.65 * taker_norm + 0.35 * imbalance)

    @staticmethod
    def _score_smart_money(f: CandidateFeatures) -> float:
        # z-score; +1.5 -> strong, -1.5 -> 0
        return 100.0 * _clip01(_sigmoid(f.cvd_slope_z, k=1.2))

    @staticmethod
    def _score_ml(f: CandidateFeatures) -> float:
        # calibration: <0.5 is useless, 0.5 -> 0, 0.75 -> 50, 0.9 -> 90
        p = _clip01(f.ml_long_prob)
        if p <= 0.5:
            return 0.0
        return 100.0 * _clip01((p - 0.5) / 0.45)

    @staticmethod
    def _score_rr(f: CandidateFeatures) -> float:
        # require >= 1.3 R:R; cap credit at 3.5 R:R
        rr = max(0.0, f.proposed_rr)
        if rr < 1.0:
            return 0.0
        return 100.0 * _clip01((rr - 1.0) / 2.5)

    # ---- public API ----

    def score(self, f: CandidateFeatures) -> ScoreBreakdown:
        components = {
            "momentum": self._score_momentum(f),
            "volume": self._score_volume(f),
            "regime": self._score_regime(f),
            "orderflow": self._score_orderflow(f),
            "smart_money": self._score_smart_money(f),
            "ml_confidence": self._score_ml(f),
            "risk_reward": self._score_rr(f),
        }
        weighted = {k: components[k] * self._w[k] for k in components}
        total = sum(weighted.values())

        # soft-reject reasons (informational, not gating)
        reasons = []
        if components["risk_reward"] < 20:
            reasons.append("rr_below_1.3")
        if components["momentum"] < 30:
            reasons.append("weak_momentum")
        if components["regime"] < 30:
            reasons.append("regime_mismatch")

        return ScoreBreakdown(
            total=round(total, 2),
            components={k: round(v, 2) for k, v in components.items()},
            weighted={k: round(v, 3) for k, v in weighted.items()},
            rejected_reasons=reasons,
        )

    def batch_score(self, candidates: list[CandidateFeatures]) -> list[ScoreBreakdown]:
        # vectorization not worth it for <200 pairs; keep explicit for debuggability
        return [self.score(c) for c in candidates]
