"""
champion.master_regime_orchestrator — Layer 5 §5 Master Regime Orchestrator.

Coordinates:
  - Drift protection signal (input from DriftProtectionEngine)
  - Regime classifier outputs (volatility percentile, trend score)
  - Exposure multiplier per regime

Edge-independent. Pure logic. NO exchange wiring.

Composition contract (downstream of L99 quant suite):

    DriftProtectionEngine.evaluate(...)        → bool: drift_enabled
    MasterRegimeOrchestrator.evaluate(...)     → OrchestratorDecision
    PortfolioRiskGovernor.approve_new_position → bool: position approved

Decision priority (matches L99_HYBRID_PORTFOLIO_GOD_MODE §5):
  1. Drift disabled  → DISABLED_BY_DRIFT (multiplier 0.0; never trade)
  2. High volatility → HIGH_VOL          (multiplier 0.5; defensive)
  3. Trending        → TRENDING          (multiplier 1.2; opportunity)
  4. Low volatility  → LOW_VOL           (multiplier 0.7; reduced engagement)
  5. Otherwise       → NORMAL            (multiplier 1.0)

Note that high-volatility check fires BEFORE trending — when both signals
co-occur, defensive sizing wins. Low-vol fires AFTER trending — a strong
trend in a quiet market still triggers opportunity sizing.

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

from dataclasses import dataclass


# ─────────────────────────────────────────────
# DECISION OUTPUT
# ─────────────────────────────────────────────

@dataclass
class OrchestratorDecision:
    engine_enabled: bool
    exposure_multiplier: float
    regime_label: str


# ─────────────────────────────────────────────
# THRESHOLDS (operator-spec values)
# ─────────────────────────────────────────────

# Volatility percentile boundaries (0.0 = lowest, 1.0 = highest 30d).
_HIGH_VOL_THRESHOLD = 0.80
_LOW_VOL_THRESHOLD = 0.20

# Trend strength score (0.0 = no trend, 1.0 = max trend).
_TREND_THRESHOLD = 0.7

# Multipliers per regime.
_MUL_DISABLED = 0.0
_MUL_HIGH_VOL = 0.5
_MUL_TRENDING = 1.2
_MUL_LOW_VOL = 0.7
_MUL_NORMAL = 1.0


# ─────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────

class MasterRegimeOrchestrator:
    """Stateful regime orchestrator. `current_regime` reflects the most
    recent `evaluate()` outcome and is exposed for monitoring."""

    def __init__(self) -> None:
        self.current_regime: str = "NORMAL"

    # ─────────────────────────────────────────

    def evaluate(
        self,
        drift_enabled: bool,
        regime_volatility_percentile: float,
        regime_trend_score: float,
    ) -> OrchestratorDecision:
        if not drift_enabled:
            self.current_regime = "DISABLED_BY_DRIFT"
            return OrchestratorDecision(
                engine_enabled=False,
                exposure_multiplier=_MUL_DISABLED,
                regime_label="DISABLED_BY_DRIFT",
            )

        # Regime priority: HIGH_VOL → TRENDING → LOW_VOL → NORMAL
        if regime_volatility_percentile > _HIGH_VOL_THRESHOLD:
            self.current_regime = "HIGH_VOL"
            multiplier = _MUL_HIGH_VOL
        elif regime_trend_score > _TREND_THRESHOLD:
            self.current_regime = "TRENDING"
            multiplier = _MUL_TRENDING
        elif regime_volatility_percentile < _LOW_VOL_THRESHOLD:
            self.current_regime = "LOW_VOL"
            multiplier = _MUL_LOW_VOL
        else:
            self.current_regime = "NORMAL"
            multiplier = _MUL_NORMAL

        return OrchestratorDecision(
            engine_enabled=True,
            exposure_multiplier=multiplier,
            regime_label=self.current_regime,
        )
