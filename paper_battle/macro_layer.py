#!/usr/bin/env python3
"""
macro_layer.py — Global Macro Prediction Layer

Per governance/AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1.md (spec #19).

🛡 PAPER-SAFE. Reads public market data only. Adjusts risk/exposure/aggression
within constitutional caps. CANNOT override Article 3 hard limits.

API:
    score = compute_global_macro_score(price_windows, spread_history, tickers)
        → dict with keys:
            score                 (float 0-100)
            mode                  (str)  DEFENSIVE | NEUTRAL | EXPANSION | HIGH_OPPORTUNITY | PANIC
            risk_multiplier       (float, capped to Article 3)
            exposure_cap_pct      (float, capped to Article 3)
            aggression_allowed    (bool)
            inputs                (dict of normalized component scores)
"""

from __future__ import annotations

import statistics
from collections import deque
from typing import Any


# Constitutional hard caps (Article 3 + Spec #19 Section VI).
ARTICLE3_RISK_PER_TRADE_MAX_PCT = 0.75
ARTICLE3_EXPOSURE_MAX_PCT       = 1.00
ARTICLE3_MAX_CONSEC_LOSS        = 3
ARTICLE3_MAX_DD_PCT             = 2.0

# Weights per Spec #19 Section I.
WEIGHTS = {
    "volatility_pressure": 0.30,
    "correlation_stress":  0.25,
    "spread_instability":  0.25,
    "volume_expansion":    0.20,
}


def _pearson(a: list[float], b: list[float]) -> float:
    """Plain Pearson correlation with safe defaults."""
    n = min(len(a), len(b))
    if n < 4:
        return 0.0
    a, b = a[-n:], b[-n:]
    ma = sum(a) / n
    mb = sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return 0.0
    return cov / (va * vb) ** 0.5


def _normalize(value: float, lo: float, hi: float) -> float:
    """Clamp + scale to 0-100."""
    if hi <= lo:
        return 50.0
    pct = (value - lo) / (hi - lo) * 100.0
    return max(0.0, min(100.0, pct))


def _volatility_pressure(btc_window: list[float]) -> float:
    """High volatility = HIGH pressure. Returns 0-100."""
    if len(btc_window) < 8:
        return 50.0
    mean = statistics.fmean(btc_window)
    if mean <= 0:
        return 50.0
    vol_pct = statistics.pstdev(btc_window) / mean * 100.0
    # Calm BTC: vol < 0.1% over short window. Stressed: > 0.8%.
    return _normalize(vol_pct, lo=0.10, hi=0.80)


def _correlation_stress(btc_window: list[float], eth_window: list[float]) -> float:
    """High |correlation| between BTC and ETH = stress (risk-on / risk-off lockstep)."""
    if len(btc_window) < 8 or len(eth_window) < 8:
        return 50.0
    # Use returns, not prices.
    btc_rets = [btc_window[i] - btc_window[i-1] for i in range(1, len(btc_window))]
    eth_rets = [eth_window[i] - eth_window[i-1] for i in range(1, len(eth_window))]
    corr = abs(_pearson(btc_rets, eth_rets))
    # Healthy markets: |corr| < 0.6. Stress: |corr| > 0.9.
    return _normalize(corr, lo=0.40, hi=0.95)


def _spread_instability(spread_history: list[float]) -> float:
    """High std/mean of spread = unstable execution conditions."""
    if len(spread_history) < 6:
        return 50.0
    m = statistics.fmean(spread_history)
    if m <= 0:
        return 50.0
    sd = statistics.pstdev(spread_history)
    cv = sd / m
    # CV < 0.2 → stable. CV > 1.0 → unstable.
    return _normalize(cv, lo=0.20, hi=1.00)


def _volume_expansion(tickers: dict[str, dict[str, Any]]) -> float:
    """
    Volume expansion: current ticker quote_volume vs synthetic baseline.
    Without persistent history we use a 24h-vol-relative heuristic:
        if total quote vol across pairs > $5B → expansion (score high)
    Returns 0-100.
    """
    if not tickers:
        return 50.0
    total = 0.0
    for tk in tickers.values():
        try:
            total += float(tk.get("quote_volume", 0) or 0)
        except (TypeError, ValueError):
            continue
    # Heuristic band: $2B (quiet) → $20B (active)
    return _normalize(total, lo=2_000_000_000, hi=20_000_000_000)


def compute_global_macro_score(
    price_windows: dict[str, deque],
    spread_history: list[float],
    raw_tickers: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Compute Global Macro Score and resulting mode/multipliers.

    price_windows: {pair: deque of recent price floats}
    spread_history: list of recent spread_pct floats (any pair)
    raw_tickers: optional Gate.io ticker dicts for quote_volume access

    Returns dict ready to log and apply.
    """
    btc = list(price_windows.get("BTC_USDT", []))
    eth = list(price_windows.get("ETH_USDT", []))

    vol_pressure       = _volatility_pressure(btc)
    correlation_stress = _correlation_stress(btc, eth)
    spread_unstable    = _spread_instability(spread_history)
    volume_expand      = _volume_expansion(raw_tickers or {})

    score = (
        WEIGHTS["volatility_pressure"] * vol_pressure +
        WEIGHTS["correlation_stress"]  * correlation_stress +
        WEIGHTS["spread_instability"]  * spread_unstable +
        WEIGHTS["volume_expansion"]    * volume_expand
    )
    score = max(0.0, min(100.0, score))

    # Mode + multipliers per Spec #19 Section II.
    if score < 25:
        mode = "PANIC"
        risk_mult = 0.5
        exposure_cap = 0.4
        aggression = False
    elif score < 40:
        mode = "DEFENSIVE"
        risk_mult = 0.6
        exposure_cap = 0.5
        aggression = False
    elif score < 70:
        mode = "NEUTRAL"
        risk_mult = 1.0
        exposure_cap = 1.0
        aggression = False
    elif score < 85:
        mode = "EXPANSION"
        risk_mult = 1.1
        exposure_cap = 1.0
        aggression = True
    else:
        mode = "HIGH_OPPORTUNITY"
        risk_mult = 1.2
        exposure_cap = 1.0
        aggression = True

    # Hard-cap clamp per Article 3 + Spec #19 Section VI.
    # Macro can only DECREASE caps, never increase.
    exposure_cap = min(exposure_cap, ARTICLE3_EXPOSURE_MAX_PCT)

    return {
        "score":              round(score, 2),
        "mode":               mode,
        "risk_multiplier":    risk_mult,
        "exposure_cap_pct":   round(exposure_cap, 4),
        "aggression_allowed": aggression,
        "inputs": {
            "volatility_pressure": round(vol_pressure, 2),
            "correlation_stress":  round(correlation_stress, 2),
            "spread_instability":  round(spread_unstable, 2),
            "volume_expansion":    round(volume_expand, 2),
        },
    }


def apply_macro_to_risk(
    base_risk_pct: float,
    macro: dict[str, Any],
    phase: int,
    equity_change_pct: float,
) -> tuple[float, str]:
    """
    Apply macro multiplier with phase × macro interaction (Spec #19 Section V).

    Phase 1: macro CANNOT increase aggression — only compression.
    Phase 2: macro may scale up to 1.1×.
    Phase 3 leading (equity_change > 0.5%): macro ignored, defensive.
    Phase 3 trailing: macro may unlock controlled expansion.

    Hard cap: never exceeds Article 3 RISK_PER_TRADE_MAX (0.75%).
    """
    mult = macro["risk_multiplier"]
    if phase == 1:
        effective_mult = min(1.0, mult)   # compression only
        reason = "phase1_compression_only"
    elif phase == 2:
        effective_mult = min(1.1, mult)
        reason = "phase2_capped_at_1.1"
    else:  # phase 3
        if equity_change_pct > 0.5:
            effective_mult = min(0.8, mult)  # defensive
            reason = "phase3_defensive_leading"
        else:
            effective_mult = min(1.1, mult)
            reason = "phase3_trailing_expansion_capped"

    adjusted = base_risk_pct * effective_mult
    # Article 3 hard cap.
    capped = min(adjusted, ARTICLE3_RISK_PER_TRADE_MAX_PCT)
    if capped < adjusted:
        reason += "+article3_cap"
    return capped, reason


def aggregate_macro_distribution(observations: list[dict[str, Any]]) -> dict[str, float]:
    """For round summary: distribution % of each mode across all macro observations."""
    if not observations:
        return {"PANIC": 0, "DEFENSIVE": 0, "NEUTRAL": 0, "EXPANSION": 0, "HIGH_OPPORTUNITY": 0}
    n = len(observations)
    counts: dict[str, int] = {}
    for o in observations:
        m = o.get("mode", "NEUTRAL")
        counts[m] = counts.get(m, 0) + 1
    return {k: round(v / n * 100.0, 1) for k, v in counts.items()}
