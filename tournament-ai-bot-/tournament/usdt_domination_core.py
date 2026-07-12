"""
usdt_domination_core.py
-----------------------
Canonical USDT accounting + capital rotation telemetry for tournament mode.

Responsibility:
    - Normalize every realized PnL to USDT terms (spot only).
    - Track capital turnover rate (how fast capital is being cycled).
    - Expose snapshot of equity, free USDT, deployed USDT, and rotation velocity.

Non-goals:
    - Does not place orders.
    - Does not compute unrealized PnL from live prices (gate_client.py owns that).
    - Does not touch trade_manager state; consumes events only.

Integration:
    from tournament.usdt_domination_core import UsdtCore, TradeEvent
    core = UsdtCore(starting_usdt=1000.0)
    # After each fill, in the trade_manager callback (read-only hook):
    core.record_fill(TradeEvent(...))
    snapshot = core.snapshot()
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import RLock
from typing import Deque, Optional


@dataclass(frozen=True)
class TradeEvent:
    """Read-only event emitted by trade_manager on fill close."""
    trade_id: str
    pair: str
    side: str               # 'buy' or 'sell' (spot)
    entry_usdt: float       # notional deployed in USDT at entry
    exit_usdt: float        # notional returned in USDT at exit
    realized_pnl_usdt: float
    fees_usdt: float
    opened_ts: float
    closed_ts: float

    @property
    def holding_seconds(self) -> float:
        return max(0.0, self.closed_ts - self.opened_ts)

    @property
    def roi(self) -> float:
        if self.entry_usdt <= 0:
            return 0.0
        return self.realized_pnl_usdt / self.entry_usdt


@dataclass
class UsdtSnapshot:
    equity_usdt: float
    free_usdt: float
    deployed_usdt: float
    realized_pnl_total: float
    realized_pnl_24h: float
    fees_24h: float
    turnover_24h: float          # total notional traded / equity
    trade_count_24h: int
    avg_holding_seconds_24h: float
    rotation_velocity: float     # trades * avg_roi / hour, signed
    all_in_usdt: bool            # True iff nothing deployed


class UsdtCore:
    """Thread-safe USDT ledger. All mutations guarded by RLock for async callers."""

    _WINDOW_SECONDS = 24 * 3600
    _EQUITY_RING_SIZE = 200   # enough for 7+ days at hourly samples

    def __init__(self, starting_usdt: float) -> None:
        if starting_usdt <= 0:
            raise ValueError("starting_usdt must be positive")
        self._lock = RLock()
        self._starting = float(starting_usdt)
        self._free_usdt = float(starting_usdt)
        self._deployed_usdt = 0.0
        self._realized_total = 0.0
        self._events: Deque[TradeEvent] = deque(maxlen=10_000)
        # equity history: list of (ts, equity) tuples, appended hourly by caller
        self._equity_history: Deque[tuple[float, float]] = deque(maxlen=self._EQUITY_RING_SIZE)
        # peak equity for drawdown computation
        self._peak_equity: float = float(starting_usdt)

    # ---- mutation hooks (read-only to external state) ----

    def record_deploy(self, notional_usdt: float) -> None:
        """Called when capital leaves USDT into a position."""
        if notional_usdt <= 0:
            return
        with self._lock:
            self._free_usdt -= notional_usdt
            self._deployed_usdt += notional_usdt

    def record_fill(self, event: TradeEvent) -> None:
        """Called on position close. Moves deployed -> free and books PnL."""
        with self._lock:
            self._deployed_usdt -= event.entry_usdt
            if self._deployed_usdt < 0:
                self._deployed_usdt = 0.0  # clamp float drift
            self._free_usdt += event.exit_usdt
            self._realized_total += event.realized_pnl_usdt
            self._events.append(event)
            # update peak on every fill; peak only rises
            equity = self._free_usdt + self._deployed_usdt
            if equity > self._peak_equity:
                self._peak_equity = equity

    def record_equity_sample(self, ts: float) -> None:
        """Called hourly by launch.py to populate equity history ring.
        Enables weekly_growth_rate computation in the aggression matrix."""
        with self._lock:
            equity = self._free_usdt + self._deployed_usdt
            self._equity_history.append((ts, equity))
            if equity > self._peak_equity:
                self._peak_equity = equity

    def current_drawdown(self) -> float:
        """Peak-to-current drawdown as fraction of peak. Always in [0, 1]."""
        with self._lock:
            equity = self._free_usdt + self._deployed_usdt
            if self._peak_equity <= 0:
                return 0.0
            return max(0.0, 1.0 - equity / self._peak_equity)

    def weekly_growth_rate(self) -> float:
        """Fractional growth over the last ~7 days.
        Returns 0.0 if insufficient history (< 24 samples)."""
        with self._lock:
            if len(self._equity_history) < 24:
                return 0.0
            now_ts = self._equity_history[-1][0]
            # find oldest sample within 7 days (or fall back to oldest available)
            cutoff = now_ts - 7 * 24 * 3600
            baseline = None
            for ts, eq in self._equity_history:
                if ts >= cutoff:
                    baseline = eq
                    break
            if baseline is None or baseline <= 0:
                # use oldest sample we have
                baseline = self._equity_history[0][1]
                if baseline <= 0:
                    return 0.0
            current = self._equity_history[-1][1]
            return (current - baseline) / baseline

    # ---- read side ----

    def snapshot(self) -> UsdtSnapshot:
        now = time.time()
        cutoff = now - self._WINDOW_SECONDS
        with self._lock:
            recent = [e for e in self._events if e.closed_ts >= cutoff]
            pnl_24h = sum(e.realized_pnl_usdt for e in recent)
            fees_24h = sum(e.fees_usdt for e in recent)
            notional_24h = sum(e.entry_usdt for e in recent)
            avg_hold = (
                sum(e.holding_seconds for e in recent) / len(recent)
                if recent else 0.0
            )
            equity = self._free_usdt + self._deployed_usdt
            turnover = notional_24h / equity if equity > 0 else 0.0

            # rotation velocity: trades/hr * mean_roi (signed edge per hour)
            if recent:
                hours = self._WINDOW_SECONDS / 3600
                mean_roi = sum(e.roi for e in recent) / len(recent)
                velocity = (len(recent) / hours) * mean_roi
            else:
                velocity = 0.0

            return UsdtSnapshot(
                equity_usdt=equity,
                free_usdt=self._free_usdt,
                deployed_usdt=self._deployed_usdt,
                realized_pnl_total=self._realized_total,
                realized_pnl_24h=pnl_24h,
                fees_24h=fees_24h,
                turnover_24h=turnover,
                trade_count_24h=len(recent),
                avg_holding_seconds_24h=avg_hold,
                rotation_velocity=velocity,
                all_in_usdt=self._deployed_usdt < 1e-6,
            )

    def starting_capital(self) -> float:
        return self._starting

    def growth_multiple(self) -> float:
        """Current equity / starting equity. Core tournament KPI."""
        snap = self.snapshot()
        return snap.equity_usdt / self._starting if self._starting > 0 else 1.0
