#!/usr/bin/env python3
"""
bayesian_regime.py — Bayesian Regime Transition Model

Per governance/BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md (spec #20 Part I).

🛡 PAPER-SAFE. Pure math on price/feature observations. No exchange writes.

Regime set: Trend, Chop, Expansion, Compression, Panic, Recovery
Output: probability vector + dominant regime + Shannon entropy

API:
    bayes = BayesianRegime()
    posterior, dominant, entropy = bayes.update(features)
    # posterior: {regime: probability}
    # dominant: argmax regime
    # entropy: Shannon nats (0 = certain, log(6) ≈ 1.79 = max uncertainty)
"""

from __future__ import annotations

import math


REGIMES = ["Trend", "Chop", "Expansion", "Compression", "Panic", "Recovery"]

# Transition matrix T[i][j] = P(regime_t=j | regime_t-1=i).
# Operator-specified excerpts (Spec #20 Part I) + completion via row-normalization.
# Diagonal-weighted (regimes are sticky) with operator transitions as priors.
_TRANSITIONS_RAW = {
    "Trend":       {"Trend": 0.55, "Chop": 0.22, "Expansion": 0.10, "Compression": 0.04, "Panic": 0.05, "Recovery": 0.04},
    "Chop":        {"Trend": 0.18, "Chop": 0.40, "Expansion": 0.30, "Compression": 0.06, "Panic": 0.04, "Recovery": 0.02},
    "Expansion":   {"Trend": 0.30, "Chop": 0.10, "Expansion": 0.40, "Compression": 0.05, "Panic": 0.10, "Recovery": 0.05},
    "Compression": {"Trend": 0.15, "Chop": 0.15, "Expansion": 0.48, "Compression": 0.18, "Panic": 0.02, "Recovery": 0.02},
    "Panic":       {"Trend": 0.05, "Chop": 0.10, "Expansion": 0.05, "Compression": 0.05, "Panic": 0.15, "Recovery": 0.60},
    "Recovery":    {"Trend": 0.30, "Chop": 0.20, "Expansion": 0.20, "Compression": 0.10, "Panic": 0.05, "Recovery": 0.15},
}


def _row_normalize(matrix: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    out = {}
    for i, row in matrix.items():
        s = sum(row.values())
        if s <= 0:
            out[i] = {j: 1.0 / len(REGIMES) for j in REGIMES}
        else:
            out[i] = {j: v / s for j, v in row.items()}
    return out


TRANSITIONS = _row_normalize(_TRANSITIONS_RAW)


def _gaussian_likelihood(value: float, mean: float, sigma: float) -> float:
    """Unnormalized Gaussian density."""
    if sigma <= 0:
        sigma = 1e-6
    z = (value - mean) / sigma
    return math.exp(-0.5 * z * z)


def likelihood_per_regime(features: dict[str, float]) -> dict[str, float]:
    """
    P(X | R) for each regime, given observed features.

    Features expected (any subset, missing keys assigned neutral):
        vol_pct           realized volatility % (0-2 typical)
        momentum_pct      12-tick momentum %    (-2 to +2 typical)
        spread_cv         spread coefficient-of-variation
        correlation_abs   |corr(BTC,ETH)| over returns
    """
    vol     = features.get("vol_pct", 0.3)
    mom     = features.get("momentum_pct", 0.0)
    sp_cv   = features.get("spread_cv", 0.5)
    corr    = features.get("correlation_abs", 0.5)

    # Regime-specific feature profiles (operator-aligned, normalized scales).
    # Each entry: (mean, sigma) per feature.
    profiles = {
        "Trend":       {"vol": (0.45, 0.20), "mom": (0.80, 0.40), "sp_cv": (0.35, 0.20), "corr": (0.55, 0.20)},
        "Chop":        {"vol": (0.30, 0.15), "mom": (0.00, 0.20), "sp_cv": (0.40, 0.20), "corr": (0.40, 0.20)},
        "Expansion":   {"vol": (0.80, 0.30), "mom": (0.30, 0.40), "sp_cv": (0.55, 0.25), "corr": (0.60, 0.20)},
        "Compression": {"vol": (0.10, 0.08), "mom": (0.00, 0.15), "sp_cv": (0.25, 0.15), "corr": (0.35, 0.20)},
        "Panic":       {"vol": (1.40, 0.50), "mom": (-1.00, 0.60), "sp_cv": (1.20, 0.40), "corr": (0.90, 0.10)},
        "Recovery":    {"vol": (0.70, 0.30), "mom": (0.60, 0.40), "sp_cv": (0.50, 0.25), "corr": (0.65, 0.20)},
    }

    out: dict[str, float] = {}
    for regime, p in profiles.items():
        l_vol  = _gaussian_likelihood(vol,    *p["vol"])
        l_mom  = _gaussian_likelihood(mom,    *p["mom"])
        l_sp   = _gaussian_likelihood(sp_cv,  *p["sp_cv"])
        l_corr = _gaussian_likelihood(corr,   *p["corr"])
        # Product likelihood (assume conditional independence).
        out[regime] = l_vol * l_mom * l_sp * l_corr
    return out


def _normalize(d: dict[str, float]) -> dict[str, float]:
    s = sum(d.values())
    if s <= 0:
        return {k: 1.0 / len(d) for k in d}
    return {k: v / s for k, v in d.items()}


def shannon_entropy(probs: dict[str, float]) -> float:
    """Shannon entropy in nats. Max = ln(6) ≈ 1.792."""
    out = 0.0
    for p in probs.values():
        if p > 0:
            out -= p * math.log(p)
    return out


def transition_acceleration(prev: dict[str, float], curr: dict[str, float]) -> float:
    """L1 distance between successive posteriors — measures regime shift speed."""
    return 0.5 * sum(abs(curr.get(r, 0) - prev.get(r, 0)) for r in REGIMES)


class BayesianRegime:
    def __init__(self) -> None:
        # Start with uniform prior.
        self.prior = {r: 1.0 / len(REGIMES) for r in REGIMES}
        self.last_posterior: dict[str, float] | None = None
        self.history: list[dict[str, float]] = []

    def update(self, features: dict[str, float]) -> tuple[dict[str, float], str, float, float]:
        # Predictive prior P(R_t) = Σ_i T[i,j] × P(R_t-1=i)
        predictive = {j: 0.0 for j in REGIMES}
        for i in REGIMES:
            for j in REGIMES:
                predictive[j] += TRANSITIONS[i][j] * self.prior.get(i, 0)

        # Likelihood P(X | R_t)
        like = likelihood_per_regime(features)

        # Posterior ∝ predictive × likelihood
        unnorm = {r: predictive[r] * like.get(r, 0) for r in REGIMES}
        posterior = _normalize(unnorm)

        # Acceleration vs last posterior.
        if self.last_posterior is not None:
            accel = transition_acceleration(self.last_posterior, posterior)
        else:
            accel = 0.0

        dominant = max(posterior.items(), key=lambda kv: kv[1])[0]
        entropy = shannon_entropy(posterior)

        # Carry forward.
        self.last_posterior = dict(posterior)
        self.prior = dict(posterior)
        self.history.append(dict(posterior))

        return posterior, dominant, entropy, accel

    def regime_distribution(self) -> dict[str, float]:
        """Round summary: time-share of each regime as dominant across history."""
        if not self.history:
            return {r: 0.0 for r in REGIMES}
        counts: dict[str, int] = {r: 0 for r in REGIMES}
        for post in self.history:
            d = max(post.items(), key=lambda kv: kv[1])[0]
            counts[d] = counts.get(d, 0) + 1
        n = len(self.history)
        return {r: round(c / n * 100.0, 1) for r, c in counts.items()}
