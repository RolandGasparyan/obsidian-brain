"""
tournament/
-----------
Tournament-mode extension modules for Trading Guru. v2 (aggression-tuned).

Public API:
    UsdtCore, TradeEvent, UsdtSnapshot
    ChampionMomentumEngine, CandidateFeatures, ScoreBreakdown
    PerformanceOracle, ThresholdDirective, PerformanceStats
    CapitalPhaseManager, Phase, PhaseDirective
    TournamentRiskController, RiskContext, EntryDecision, Verdict
    EdgeDecayDetector, EdgeStatus, DecayVerdict
    VolatilityExpansionDetector, VolatilityReading, VolState, PhaseHint
    AggressionScaler, AggressionReading, AggressionMode
    LossClusterBreaker, BreakerDecision, BreakerState
    TournamentBrain (composition root)
"""
from .usdt_domination_core import UsdtCore, TradeEvent, UsdtSnapshot
from .champion_momentum_engine import (
    ChampionMomentumEngine, CandidateFeatures, ScoreBreakdown, DEFAULT_WEIGHTS,
)
from .performance_oracle import (
    PerformanceOracle, ThresholdDirective, PerformanceStats,
)
from .capital_phase_manager import (
    CapitalPhaseManager, Phase, PhaseDirective,
    DEFAULT_EARLY, DEFAULT_MID, DEFAULT_ENDGAME,
)
from .tournament_risk_controller import (
    TournamentRiskController, RiskContext, EntryDecision, Verdict,
)
from .edge_decay_detector import (
    EdgeDecayDetector, EdgeStatus, DecayVerdict,
)
from .volatility_expansion_detector import (
    VolatilityExpansionDetector, VolatilityReading, VolState, PhaseHint,
)
from .aggression_scaler import (
    AggressionScaler, AggressionReading, AggressionMode,
)
from .aggression_matrix import (
    AggressionMatrix, MatrixInputs, AggressionDirective,
    CapitalBand, DrawdownBand, GrowthBand, VolBand,
)
from .loss_cluster_breaker import (
    LossClusterBreaker, BreakerDecision, BreakerState, BreakerTelemetry,
)
from .brain import TournamentBrain, BrainDecision

__all__ = [
    "UsdtCore", "TradeEvent", "UsdtSnapshot",
    "ChampionMomentumEngine", "CandidateFeatures", "ScoreBreakdown", "DEFAULT_WEIGHTS",
    "PerformanceOracle", "ThresholdDirective", "PerformanceStats",
    "CapitalPhaseManager", "Phase", "PhaseDirective",
    "DEFAULT_EARLY", "DEFAULT_MID", "DEFAULT_ENDGAME",
    "TournamentRiskController", "RiskContext", "EntryDecision", "Verdict",
    "EdgeDecayDetector", "EdgeStatus", "DecayVerdict",
    "VolatilityExpansionDetector", "VolatilityReading", "VolState", "PhaseHint",
    "AggressionScaler", "AggressionReading", "AggressionMode",
    "AggressionMatrix", "MatrixInputs", "AggressionDirective",
    "CapitalBand", "DrawdownBand", "GrowthBand", "VolBand",
    "LossClusterBreaker", "BreakerDecision", "BreakerState", "BreakerTelemetry",
    "TournamentBrain", "BrainDecision",
]
