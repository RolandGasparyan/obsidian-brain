"""
champion.rolling_metrics — Layer 5 support: Rolling Metrics Aggregator.

Consumes trade journal entries and computes rolling statistics used by
Layer 5 modules (drift protection, orchestrator, governor).

Edge-independent. Deterministic. NO exchange wiring.

API:
  - add_trade(TradeRecord)                       record a closed trade
  - compute() -> RollingMetrics                  current rolling-window stats

Computed metrics (within the most recent `window_size` trades):
  - trades                       count in window
  - win_rate                     fraction of trades with R > 0
  - profit_factor                gross_profit / gross_loss (∞ if no losses)
  - expectancy_r                 mean R-multiple
  - max_consecutive_losses       longest run of consecutive losing trades
  - drawdown_pct                 max DD WITHIN the window (not all-time)
  - information_coefficient      Pearson correlation between
                                 prediction and outcome arrays

Notes:
  - `drawdown_pct` is window-local. The PortfolioRiskGovernor tracks
    all-time peak DD separately for kill-switch purposes; this module's
    DD feeds the DriftProtectionEngine's rolling-DD threshold.
  - `profit_factor` returns float('inf') when there are no losses
    in the window. Downstream code should handle this by allowing it
    (i.e., `inf >= min_pf` is True).
  - Trades with R = 0 (exactly flat) are counted in `trades` and contribute
    to `expectancy_r` but are neither wins nor losses for `win_rate`.

Per ADR-001 + ADR-003 (D7 expired): library only.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Deque, List


# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class TradeRecord:
    """One closed trade. R-multiple is the standardized PnL unit
    (PnL / risk-per-trade). `equity` is portfolio value at trade close.
    `prediction` and `outcome` are the signal-side scalars used to compute
    the information coefficient (Pearson)."""

    r_multiple: float
    equity: float
    prediction: float = 0.0
    outcome: float = 0.0


@dataclass
class RollingMetrics:
    trades: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    max_consecutive_losses: int
    drawdown_pct: float
    information_coefficient: float


# ─────────────────────────────────────────────
# AGGREGATOR
# ─────────────────────────────────────────────

class RollingMetricsAggregator:
    """Fixed-window rolling aggregator. Older trades are evicted as the
    window fills."""

    def __init__(self, window_size: int = 50):
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.trades: Deque[TradeRecord] = deque(maxlen=window_size)

    # ─────────────────────────────────────────

    def add_trade(self, trade: TradeRecord) -> None:
        self.trades.append(trade)

    # ─────────────────────────────────────────

    def compute(self) -> RollingMetrics:
        if not self.trades:
            return RollingMetrics(
                trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                expectancy_r=0.0,
                max_consecutive_losses=0,
                drawdown_pct=0.0,
                information_coefficient=0.0,
            )

        r_values = [t.r_multiple for t in self.trades]
        trades = len(r_values)

        wins = [r for r in r_values if r > 0]
        losses = [r for r in r_values if r < 0]

        win_rate = len(wins) / trades

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (
            gross_profit / gross_loss if gross_loss > 0 else float("inf")
        )

        expectancy = sum(r_values) / trades

        # Max consecutive losses
        max_consec = 0
        current = 0
        for r in r_values:
            if r < 0:
                current += 1
                max_consec = max(max_consec, current)
            else:
                current = 0

        # Window-local drawdown
        equities = [t.equity for t in self.trades]
        peak = equities[0]
        max_dd = 0.0
        for eq in equities:
            peak = max(peak, eq)
            if peak > 0:
                dd = 1 - (eq / peak)
                max_dd = max(max_dd, dd)

        # Information Coefficient (Pearson correlation)
        preds = [t.prediction for t in self.trades]
        outcomes = [t.outcome for t in self.trades]
        ic = self._pearson(preds, outcomes)

        return RollingMetrics(
            trades=trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy_r=expectancy,
            max_consecutive_losses=max_consec,
            drawdown_pct=max_dd,
            information_coefficient=ic,
        )

    # ─────────────────────────────────────────

    @staticmethod
    def _pearson(x: List[float], y: List[float]) -> float:
        """Pearson correlation. Returns 0.0 when correlation is undefined
        (n < 2 or zero variance in either array)."""
        if len(x) < 2:
            return 0.0

        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)

        num = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
        den_x = math.sqrt(sum((a - mean_x) ** 2 for a in x))
        den_y = math.sqrt(sum((b - mean_y) ** 2 for b in y))

        if den_x == 0 or den_y == 0:
            return 0.0

        return num / (den_x * den_y)
