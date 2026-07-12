"""
performance_oracle.py
---------------------
Rolling performance statistics + adaptive threshold controller.

Responsibilities:
    - Maintain rolling window of closed trades.
    - Compute expectancy, win rate, profit factor, Sharpe, max DD.
    - Emit threshold deltas to apply on top of the base composite score threshold.
    - Trigger edge-decay alerts (see edge_decay_detector for the detection logic;
      this module exposes the aggregate stats it needs).

The oracle does NOT know about pairs or orders. It consumes TradeEvent from
usdt_domination_core and reports.
"""
from __future__ import annotations

import math
import statistics
from collections import deque
from dataclasses import dataclass
from threading import RLock
from typing import Deque, Optional

from .usdt_domination_core import TradeEvent


@dataclass
class PerformanceStats:
    sample_size: int
    win_rate: float          # 0-1
    expectancy_usdt: float   # mean PnL per trade
    expectancy_r: float      # mean PnL expressed in R (using avg_loss magnitude)
    profit_factor: float     # gross wins / gross losses, inf if no losses
    sharpe: float            # trade-wise Sharpe, annualized by trades/day assumption
    max_drawdown_pct: float  # worst peak-to-trough on cumulative equity curve
    avg_win_usdt: float
    avg_loss_usdt: float
    loss_streak_current: int
    loss_streak_max: int


@dataclass
class ThresholdDirective:
    """Additive delta to apply to the base composite score threshold."""
    base_threshold: float
    delta: float
    effective_threshold: float
    rationale: str


class PerformanceOracle:
    """Thread-safe rolling performance tracker."""

    def __init__(
        self,
        window_size: int = 200,
        min_sample: int = 20,
        base_threshold: float = 62.0,
    ) -> None:
        self._lock = RLock()
        self._events: Deque[TradeEvent] = deque(maxlen=window_size)
        self._min_sample = min_sample
        self._base_threshold = float(base_threshold)
        self._trades_since_review = 0

    def record(self, event: TradeEvent) -> None:
        with self._lock:
            self._events.append(event)
            self._trades_since_review += 1

    def review_due(self, every: int = 50) -> bool:
        with self._lock:
            return self._trades_since_review >= every

    def mark_reviewed(self) -> None:
        with self._lock:
            self._trades_since_review = 0

    # ---- statistics ----

    def stats(self) -> PerformanceStats:
        with self._lock:
            events = list(self._events)

        n = len(events)
        if n == 0:
            return PerformanceStats(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0)

        pnls = [e.realized_pnl_usdt for e in events]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        win_rate = len(wins) / n
        avg_win = statistics.mean(wins) if wins else 0.0
        avg_loss = statistics.mean(losses) if losses else 0.0  # negative
        expectancy = statistics.mean(pnls)
        expectancy_r = expectancy / abs(avg_loss) if avg_loss < 0 else 0.0

        gross_w = sum(wins)
        gross_l = abs(sum(losses))
        profit_factor = gross_w / gross_l if gross_l > 0 else float("inf")

        # Sharpe (trade-level), annualized assuming avg holding. Quick proxy:
        if n >= 2:
            mean_p = statistics.mean(pnls)
            std_p = statistics.pstdev(pnls)
            sharpe_per_trade = mean_p / std_p if std_p > 0 else 0.0
            # assume tournament trading cadence ~30 trades/day; annualize
            sharpe = sharpe_per_trade * math.sqrt(30 * 365)
        else:
            sharpe = 0.0

        # Max drawdown on cumulative PnL
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in pnls:
            cum += p
            peak = max(peak, cum)
            dd = peak - cum
            if peak > 0:
                max_dd = max(max_dd, dd / peak)

        # Loss streaks
        cur_streak = 0
        max_streak = 0
        for p in pnls:
            if p < 0:
                cur_streak += 1
                max_streak = max(max_streak, cur_streak)
            else:
                cur_streak = 0

        return PerformanceStats(
            sample_size=n,
            win_rate=round(win_rate, 4),
            expectancy_usdt=round(expectancy, 4),
            expectancy_r=round(expectancy_r, 3),
            profit_factor=round(profit_factor, 3) if profit_factor != float("inf") else float("inf"),
            sharpe=round(sharpe, 3),
            max_drawdown_pct=round(max_dd, 4),
            avg_win_usdt=round(avg_win, 4),
            avg_loss_usdt=round(avg_loss, 4),
            loss_streak_current=cur_streak,
            loss_streak_max=max_streak,
        )

    # ---- adaptive threshold ----

    def threshold(self) -> ThresholdDirective:
        s = self.stats()
        base = self._base_threshold

        if s.sample_size < self._min_sample:
            return ThresholdDirective(
                base_threshold=base,
                delta=0.0,
                effective_threshold=base,
                rationale=f"insufficient_sample({s.sample_size}/{self._min_sample})",
            )

        delta = 0.0
        reasons = []

        # Win rate adjustments
        if s.win_rate < 0.40:
            delta += 6.0
            reasons.append(f"low_winrate({s.win_rate:.2f})")
        elif s.win_rate > 0.62:
            delta -= 3.0
            reasons.append(f"high_winrate({s.win_rate:.2f})")

        # Expectancy adjustments
        if s.expectancy_r < 0:
            delta += 8.0
            reasons.append("negative_expectancy")
        elif s.expectancy_r > 0.35:
            delta -= 2.0
            reasons.append("strong_expectancy")

        # Loss streak tightening
        if s.loss_streak_current >= 4:
            delta += 5.0
            reasons.append(f"loss_streak({s.loss_streak_current})")

        # Drawdown defense
        if s.max_drawdown_pct > 0.08:
            delta += 4.0
            reasons.append(f"dd({s.max_drawdown_pct:.2%})")

        # Clamp delta so oracle never paralyzes or over-loosens the system
        delta = max(-6.0, min(15.0, delta))
        effective = base + delta

        return ThresholdDirective(
            base_threshold=base,
            delta=round(delta, 2),
            effective_threshold=round(effective, 2),
            rationale=", ".join(reasons) if reasons else "stable",
        )

    def set_base_threshold(self, value: float) -> None:
        with self._lock:
            self._base_threshold = float(value)
