"""
L99 Governance — State Machine
Defines all governance states, risk levels, scaling tiers, and valid transitions.
Only governance_engine.py may call transition(); all other modules read state only.
"""
from enum import Enum


class GovernanceState(str, Enum):
    NORMAL           = "STATE_NORMAL"
    THROTTLED        = "STATE_THROTTLED"
    RESTRICTED       = "STATE_RESTRICTED"
    FROZEN           = "STATE_FROZEN"
    REVIEW_REQUIRED  = "STATE_REVIEW_REQUIRED"
    SCALING_PENDING  = "STATE_SCALING_PENDING"


class RiskLevel(str, Enum):
    NORMAL      = "LEVEL_NORMAL"
    THROTTLED   = "LEVEL_THROTTLED"
    RESTRICTED  = "LEVEL_RESTRICTED"
    FROZEN      = "LEVEL_FROZEN"


class ScalingTier(str, Enum):
    TIER_0 = "TIER_0"   # testnet
    TIER_1 = "TIER_1"   # pilot capital
    TIER_2 = "TIER_2"   # small capital
    TIER_3 = "TIER_3"   # scaled capital


_VALID_TRANSITIONS: dict[GovernanceState, list[GovernanceState]] = {
    GovernanceState.NORMAL:          [GovernanceState.THROTTLED, GovernanceState.RESTRICTED,
                                      GovernanceState.FROZEN, GovernanceState.SCALING_PENDING],
    GovernanceState.THROTTLED:       [GovernanceState.NORMAL, GovernanceState.RESTRICTED,
                                      GovernanceState.FROZEN],
    GovernanceState.RESTRICTED:      [GovernanceState.NORMAL, GovernanceState.THROTTLED,
                                      GovernanceState.FROZEN, GovernanceState.REVIEW_REQUIRED],
    GovernanceState.FROZEN:          [GovernanceState.REVIEW_REQUIRED],
    GovernanceState.REVIEW_REQUIRED: [GovernanceState.NORMAL],        # manual only
    GovernanceState.SCALING_PENDING: [GovernanceState.NORMAL],        # manual confirm
}


def is_valid_transition(from_state: GovernanceState, to_state: GovernanceState) -> bool:
    return to_state in _VALID_TRANSITIONS.get(from_state, [])


def assert_valid_transition(from_state: GovernanceState, to_state: GovernanceState) -> None:
    if not is_valid_transition(from_state, to_state):
        raise ValueError(
            f"Invalid governance transition: {from_state} → {to_state}"
        )
