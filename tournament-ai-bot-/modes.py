"""config/modes.py – Mode definitions for the Tournament AI Engine.

Drop this into trading_guru/trading_guru/config/ alongside your existing
modes.py (or merge it in). The TOURNAMENT_MODE entry wires up TournamentBrain
and is what you pass to --mode when launching with live/paper trading.

Usage in launch.py:
    from trading_guru.config.modes import TOURNAMENT_MODE
    if config.mode == "tournament":
        from trading_guru.tournament import TournamentBrain
        tournament_brain = TournamentBrain(
            starting_usdt=config.starting_balance_usdt,
            base_score_threshold=TOURNAMENT_MODE.base_score_threshold,
            performance_window=200,
            edge_review_every=50,
        )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Shared spot pairs used across tournament mode
# ---------------------------------------------------------------------------
SPOT_KING_PAIRS: List[str] = [
    "BTC_USDT",
    "ETH_USDT",
    "SOL_USDT",
    "BNB_USDT",
]


# ---------------------------------------------------------------------------
# Mode configuration dataclass (mirrors whatever structure your engine uses)
# ---------------------------------------------------------------------------
@dataclass
class ModeConfig:
    name: str
    pairs: List[str]
    use_tournament_brain: bool = False
    base_score_threshold: float = 62.0
    max_concurrent_trades: int = 2
    # Guardian hard-stop drawdown BEFORE tournament 15 % cap kicks in
    guardian_halt_drawdown: float = 0.08
    # Paper-mode calibration target – must pass before going live
    paper_min_trades: int = 50
    paper_min_win_rate: float = 0.55
    paper_min_expectancy_r: float = 0.25
    paper_max_drawdown: float = 0.06
    extra_flags: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tournament mode – spot-only, Gate.io, no leverage, full TournamentBrain
# ---------------------------------------------------------------------------
TOURNAMENT_MODE = ModeConfig(
    name="tournament",
    pairs=SPOT_KING_PAIRS,
    use_tournament_brain=True,
    base_score_threshold=62.0,    # tune after paper-trade calibration
    max_concurrent_trades=2,
    guardian_halt_drawdown=0.08,  # still active, below tournament hard cap
    paper_min_trades=50,
    paper_min_win_rate=0.55,
    paper_min_expectancy_r=0.25,
    paper_max_drawdown=0.06,
)

# Convenience mapping for launch.py: modes_registry["tournament"]
modes_registry: dict[str, ModeConfig] = {
    TOURNAMENT_MODE.name: TOURNAMENT_MODE,
}
