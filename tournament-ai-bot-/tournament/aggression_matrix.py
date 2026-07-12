"""
aggression_matrix.py
--------------------
Dynamic Aggression Control Matrix.

PURE LOGIC LAYER. No state, no threads, no time calls, no I/O.
Same inputs -> same outputs, every call. Fully deterministic.

Inputs:
    capital              (UsdtCore snapshot: equity_usdt, starting_usdt)
    volatility_state     (VolState enum from detector)
    current_drawdown     (0.0 to 1.0, peak-to-trough on equity)
    weekly_growth_rate   (fractional change over 7 days, e.g. 0.15 = +15%)
    loss_cluster_flag    (bool: is breaker currently tripped?)

Outputs:
    effective_risk           float  (final risk multiplier to apply)
    effective_threshold      float  (composite score threshold)
    max_concurrent_trades    int
    cooldown_minutes         float  (extra cooldown to layer on top of breaker)

Design principles:
    - Every combination of inputs maps to ONE directive. No hidden state.
    - Risk direction is always clear: hotter growth = more aggression ONLY
      when drawdown is small AND no cluster AND volatility is expanding.
    - Any single "bad" signal (cluster, big DD, compressed vol) clamps risk
      DOWN regardless of other inputs.
    - The matrix is explicit. Every cell is named. Not tunable at runtime -
      tune by editing this file, which forces code review.

Placement in the pipeline:
    fusion_brain -> scorer -> aggression_matrix -> risk_controller -> execution

The matrix sits BEFORE risk_controller and produces the values that feed into
RiskContext. risk_controller retains veto power (hard DD cap, daily loss cap,
etc.) but its soft multipliers are superseded by matrix outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .volatility_expansion_detector import VolState


# ---- discretization buckets (deterministic lookup keys) ----

class CapitalBand(str, Enum):
    """Banded by growth multiple (equity / starting)."""
    EARLY = "EARLY"       # x < 1.5
    MID = "MID"           # 1.5 <= x < 3.0
    ENDGAME = "ENDGAME"   # x >= 3.0


class DrawdownBand(str, Enum):
    NONE = "NONE"         # < 2%
    MILD = "MILD"         # 2% - 5%
    MODERATE = "MODERATE" # 5% - 10%
    SEVERE = "SEVERE"     # >= 10%


class GrowthBand(str, Enum):
    SHRINKING = "SHRINKING"   # < -2% weekly
    FLAT = "FLAT"             # -2% to 2%
    GROWING = "GROWING"       # 2% to 8%
    HOT = "HOT"               # 8% to 20%
    BLAZING = "BLAZING"       # > 20%


class VolBand(str, Enum):
    EXPANDING = "EXPANDING"
    COMPRESSED = "COMPRESSED"
    NEUTRAL = "NEUTRAL"
    EXPANDED = "EXPANDED"


@dataclass(frozen=True)
class MatrixInputs:
    equity_usdt: float
    starting_usdt: float
    volatility_state: VolState
    current_drawdown: float        # 0.0 to 1.0
    weekly_growth_rate: float      # fractional, e.g. 0.15
    loss_cluster_flag: bool


@dataclass(frozen=True)
class AggressionDirective:
    effective_risk: float              # multiplier applied to base risk %
    effective_threshold: float         # composite score threshold
    max_concurrent_trades: int
    cooldown_minutes: float            # extra cooldown layered on breaker
    # introspection - so the dashboard and logs can show why we got here
    capital_band: CapitalBand
    drawdown_band: DrawdownBand
    growth_band: GrowthBand
    vol_band: VolBand
    lock_reason: Optional[str]         # if non-None, matrix clamped aggressively

    def to_log_dict(self) -> dict:
        return {
            "eff_risk": self.effective_risk,
            "eff_thr": self.effective_threshold,
            "max_conc": self.max_concurrent_trades,
            "cooldown_min": self.cooldown_minutes,
            "capital": self.capital_band.value,
            "dd": self.drawdown_band.value,
            "growth": self.growth_band.value,
            "vol": self.vol_band.value,
            "lock": self.lock_reason,
        }


# ---- classification (pure functions) ----

def _capital_band(equity: float, starting: float) -> CapitalBand:
    if starting <= 0:
        return CapitalBand.EARLY  # defensive
    x = equity / starting
    if x < 1.5:
        return CapitalBand.EARLY
    if x < 3.0:
        return CapitalBand.MID
    return CapitalBand.ENDGAME


def _drawdown_band(dd: float) -> DrawdownBand:
    if dd < 0.02:
        return DrawdownBand.NONE
    if dd < 0.05:
        return DrawdownBand.MILD
    if dd < 0.10:
        return DrawdownBand.MODERATE
    return DrawdownBand.SEVERE


def _growth_band(weekly_rate: float) -> GrowthBand:
    if weekly_rate < -0.02:
        return GrowthBand.SHRINKING
    if weekly_rate < 0.02:
        return GrowthBand.FLAT
    if weekly_rate < 0.08:
        return GrowthBand.GROWING
    if weekly_rate < 0.20:
        return GrowthBand.HOT
    return GrowthBand.BLAZING


def _vol_band(state: VolState) -> VolBand:
    # pass-through mapping; keeps matrix independent of detector internals
    return VolBand(state.value)


# ---- the matrix itself ----
# Each cell is a (effective_risk, effective_threshold_delta_from_base,
#                 max_concurrent, cooldown_minutes) tuple.
# Base threshold is 62.0; delta is added to that.
# Base concurrent is 2.
# Cooldown is EXTRA minutes on top of breaker — 0 means no extra cooldown.

_BASE_THRESHOLD = 62.0

# Dimension: (capital_band, drawdown_band, growth_band, vol_band)
# We don't enumerate all 3*4*5*4 = 240 cells - instead we compute via
# composable rules, which is still deterministic but DRY.

def _base_risk_from_capital(band: CapitalBand) -> float:
    return {
        CapitalBand.EARLY: 1.25,
        CapitalBand.MID: 1.00,
        CapitalBand.ENDGAME: 0.55,
    }[band]


def _drawdown_risk_multiplier(band: DrawdownBand) -> float:
    return {
        DrawdownBand.NONE: 1.00,
        DrawdownBand.MILD: 0.85,
        DrawdownBand.MODERATE: 0.65,
        DrawdownBand.SEVERE: 0.35,
    }[band]


def _growth_risk_multiplier(band: GrowthBand, capital: CapitalBand) -> float:
    """Growth boost is phase-gated: ENDGAME caps at 1.0 regardless of growth."""
    raw = {
        GrowthBand.SHRINKING: 0.70,
        GrowthBand.FLAT: 0.95,
        GrowthBand.GROWING: 1.05,
        GrowthBand.HOT: 1.20,
        GrowthBand.BLAZING: 1.35,
    }[band]
    if capital == CapitalBand.ENDGAME:
        return min(raw, 1.00)
    if capital == CapitalBand.MID:
        return min(raw, 1.20)
    return raw


def _vol_risk_multiplier(band: VolBand) -> float:
    return {
        VolBand.EXPANDING: 1.10,
        VolBand.COMPRESSED: 0.80,
        VolBand.NEUTRAL: 0.90,
        VolBand.EXPANDED: 0.50,   # we shouldn't be entering here anyway
    }[band]


def _threshold_delta(
    capital: CapitalBand, dd: DrawdownBand, growth: GrowthBand, vol: VolBand,
) -> float:
    """Composite score threshold delta. Higher = more selective."""
    delta = 0.0

    # Capital phase
    if capital == CapitalBand.EARLY:
        delta -= 2.0
    elif capital == CapitalBand.ENDGAME:
        delta += 6.0

    # Drawdown - tighten as DD worsens
    if dd == DrawdownBand.MILD:
        delta += 3.0
    elif dd == DrawdownBand.MODERATE:
        delta += 7.0
    elif dd == DrawdownBand.SEVERE:
        delta += 12.0

    # Growth - loosen when growing, tighten when shrinking
    if growth == GrowthBand.SHRINKING:
        delta += 5.0
    elif growth == GrowthBand.HOT:
        delta -= 2.0
    elif growth == GrowthBand.BLAZING:
        delta -= 3.0

    # Volatility - tighten for non-expanding
    if vol == VolBand.COMPRESSED:
        delta += 4.0
    elif vol == VolBand.NEUTRAL:
        delta += 2.0
    elif vol == VolBand.EXPANDED:
        delta += 15.0  # effectively a block, but let risk_controller do the hard veto

    return delta


def _max_concurrent(capital: CapitalBand, dd: DrawdownBand) -> int:
    if dd == DrawdownBand.SEVERE:
        return 1
    if capital == CapitalBand.ENDGAME:
        return 1
    if dd == DrawdownBand.MODERATE:
        return 1
    return 2


def _cooldown_minutes(
    capital: CapitalBand, dd: DrawdownBand, loss_cluster: bool,
) -> float:
    """Extra cooldown LAYERED on top of breaker. 0 in normal operation."""
    if not loss_cluster:
        return 0.0
    # Loss cluster active - extra protection scaled by phase and DD
    base = {
        CapitalBand.EARLY: 5.0,
        CapitalBand.MID: 10.0,
        CapitalBand.ENDGAME: 20.0,
    }[capital]
    if dd == DrawdownBand.MODERATE:
        base *= 1.5
    elif dd == DrawdownBand.SEVERE:
        base *= 2.5
    return base


class AggressionMatrix:
    """Pure logic. Stateless. Thread-safe by virtue of being stateless."""

    def __init__(self, base_threshold: float = 62.0) -> None:
        # only config lives on the instance, and it's immutable after construction
        self._base_threshold = float(base_threshold)

    @property
    def base_threshold(self) -> float:
        return self._base_threshold

    def evaluate(self, inputs: MatrixInputs) -> AggressionDirective:
        # 1. classify inputs into bands (deterministic)
        cap = _capital_band(inputs.equity_usdt, inputs.starting_usdt)
        dd = _drawdown_band(inputs.current_drawdown)
        growth = _growth_band(inputs.weekly_growth_rate)
        vol = _vol_band(inputs.volatility_state)

        # 2. compute effective_risk via composable multipliers
        base_risk = _base_risk_from_capital(cap)
        risk = (
            base_risk
            * _drawdown_risk_multiplier(dd)
            * _growth_risk_multiplier(growth, cap)
            * _vol_risk_multiplier(vol)
        )

        # 3. loss cluster flag forces hard cap on risk
        lock_reason = None
        if inputs.loss_cluster_flag:
            risk = min(risk, 0.40)
            lock_reason = "loss_cluster_active"

        # 4. severe drawdown is a hard cap regardless of other signals
        if dd == DrawdownBand.SEVERE:
            risk = min(risk, 0.35)
            lock_reason = lock_reason or "severe_drawdown"

        # 5. expanded vol is a hard cap (we shouldn't enter, but belt+braces)
        if vol == VolBand.EXPANDED:
            risk = min(risk, 0.50)
            lock_reason = lock_reason or "volatility_expanded"

        # 6. global safety ceiling (never exceed 2.0, never below 0.0)
        risk = max(0.0, min(risk, 2.0))

        # 7. threshold
        threshold = self._base_threshold + _threshold_delta(cap, dd, growth, vol)
        # clamp to sane range
        threshold = max(50.0, min(90.0, threshold))

        # 8. concurrency and cooldown
        max_conc = _max_concurrent(cap, dd)
        cooldown = _cooldown_minutes(cap, dd, inputs.loss_cluster_flag)

        return AggressionDirective(
            effective_risk=round(risk, 3),
            effective_threshold=round(threshold, 2),
            max_concurrent_trades=max_conc,
            cooldown_minutes=round(cooldown, 1),
            capital_band=cap,
            drawdown_band=dd,
            growth_band=growth,
            vol_band=vol,
            lock_reason=lock_reason,
        )
