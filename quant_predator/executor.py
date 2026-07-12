"""
quant_predator.executor — position-trade executor (skeleton).

Hold time 2-14 days. Higher edge target (≥1.0% net) justifies wider
stops and slower management. Same Champion sizer + journal pattern as
aegis_alpha.

SKELETON: defines the structure but does NOT implement entry/exit
logic. Will be filled in after aegis_alpha + godmode produce 60+ days
of paper-shadow evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from champion import PositionSizer


@dataclass
class PredatorTrade:
    """Position trade — placeholder. Real fields filled in implementation."""
    pair:        str
    entry:       float
    stop:        float
    units:       float


class PredatorExecutor:
    """SKELETON. Real implementation routes through champion.sizer
    and writes to the same journal as aegis_alpha + godmode."""

    def __init__(self, sizer: PositionSizer,
                 journal_path: Optional[Path] = None):
        self.sizer = sizer
        self.journal_path = journal_path
        self.open_trades: List[PredatorTrade] = []

    def try_open(self, *args, **kwargs):
        raise NotImplementedError("quant_predator entry logic not yet implemented")

    def on_daily_bar(self, *args, **kwargs):
        raise NotImplementedError("quant_predator manage logic not yet implemented")
