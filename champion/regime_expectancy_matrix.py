"""
champion.regime_expectancy_matrix — Layer 3 §2.1 + Layer 1 §1.4 (regime × signal) matrix.

Implements Section 2.1 of L99_CAPITAL_MATHEMATICS.md plus Section 1.4 of
L99_ALPHA_VALIDATION.md.

Edge-independent. Pure math. NO exchange wiring. NO strategy dependency.

Records trades tagged by `(regime, signal)` cell, then computes per-cell
metrics (WR, AvgWin, AvgLoss, Expectancy, ProfitFactor) used by:
  - L99_CAPITAL_MATHEMATICS §2.2 regime activation rule
    ("Trade only when Expectancy > 0.3R; scale risk per regime")
  - L99_ALPHA_VALIDATION §1.4 regime segmentation
    ("Restrict deployment to valid regime only")
  - L99_REGIME_PROBABILITY §5 edge-conditional regime matrix
    (E_total = Σ P(Ri) × E(Ri))

API:
  - add_trade(regime, signal, r_multiple)        record a closed trade
  - compute_cell(regime, signal) -> CellMetrics  current stats for one cell
  - compute() -> Dict[(regime, signal), CellMetrics]  every populated cell
  - best_cell(min_trades=30) -> ((regime, signal), CellMetrics) | None
    highest expectancy cell with sufficient sample
  - cells_above_expectancy(threshold, min_trades=30) -> list of qualifying cells

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

CellKey = Tuple[str, str]  # (regime, signal)


@dataclass
class CellMetrics:
    n_trades: int
    win_rate: float
    avg_win_r: float        # mean of positive R-multiples (0 if no wins)
    avg_loss_r: float       # mean absolute value of negative R-multiples (0 if no losses)
    expectancy_r: float
    profit_factor: float    # gross_profit / gross_loss (∞ if no losses, 0 if no wins)


# ─────────────────────────────────────────────
# MATRIX
# ─────────────────────────────────────────────

class RegimeExpectancyMatrix:
    """Append-only collector of (regime, signal)-tagged trade outcomes.
    Computes per-cell statistics on demand."""

    def __init__(self) -> None:
        self._records: Dict[CellKey, List[float]] = {}

    # ─────────────────────────────────────────

    def add_trade(self, regime: str, signal: str, r_multiple: float) -> None:
        """Record a single closed trade. Trades accumulate without bound;
        for rolling windows, use champion.rolling_metrics instead."""
        key: CellKey = (regime, signal)
        self._records.setdefault(key, []).append(r_multiple)

    # ─────────────────────────────────────────

    def compute_cell(self, regime: str, signal: str) -> Optional[CellMetrics]:
        """Compute metrics for a single cell. Returns None if cell empty."""
        rs = self._records.get((regime, signal))
        if not rs:
            return None
        return _compute_metrics(rs)

    # ─────────────────────────────────────────

    def compute(self) -> Dict[CellKey, CellMetrics]:
        """Compute metrics for every populated cell."""
        return {key: _compute_metrics(rs) for key, rs in self._records.items()}

    # ─────────────────────────────────────────

    def best_cell(self, min_trades: int = 30) -> Optional[Tuple[CellKey, CellMetrics]]:
        """Return the (regime, signal) cell with the highest expectancy among
        cells with at least min_trades observations. None if no cell qualifies.

        Min-trades default 30 matches L99_ALPHA_VALIDATION §2.3 viability gate.
        """
        candidates = [
            (key, _compute_metrics(rs))
            for key, rs in self._records.items()
            if len(rs) >= min_trades
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda kv: kv[1].expectancy_r)

    # ─────────────────────────────────────────

    def cells_above_expectancy(
        self,
        threshold: float,
        min_trades: int = 30,
    ) -> List[Tuple[CellKey, CellMetrics]]:
        """Return all cells where expectancy >= threshold and n_trades >= min_trades.
        Sorted by expectancy descending.

        Default threshold for activation per §2.2 is +0.3R.
        """
        qualifying = [
            (key, m)
            for key, rs in self._records.items()
            if len(rs) >= min_trades
            for m in [_compute_metrics(rs)]
            if m.expectancy_r >= threshold
        ]
        return sorted(qualifying, key=lambda kv: kv[1].expectancy_r, reverse=True)


# ─────────────────────────────────────────────
# INTERNAL COMPUTE
# ─────────────────────────────────────────────

def _compute_metrics(r_values: List[float]) -> CellMetrics:
    n = len(r_values)
    wins = [r for r in r_values if r > 0]
    losses = [r for r in r_values if r < 0]

    win_rate = len(wins) / n
    avg_win_r = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss_r = (abs(sum(losses)) / len(losses)) if losses else 0.0
    expectancy = sum(r_values) / n

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    return CellMetrics(
        n_trades=n,
        win_rate=win_rate,
        avg_win_r=avg_win_r,
        avg_loss_r=avg_loss_r,
        expectancy_r=expectancy,
        profit_factor=profit_factor,
    )
