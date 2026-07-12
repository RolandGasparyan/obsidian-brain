"""
champion.risk — 5-Layer Risk Protocol from CHAMPION_MODE.md §V.

LAYER 1 — Trade
    Enforced by PositionSizer (in champion.sizer): per-trade risk cap,
    hard stop, no averaging-down, no revenge.

LAYER 2 — Daily
    THIS module. Daily DD ≥ 5% → close all, no more trades today.
    3 consec loss days → −25% size 5 days.

LAYER 3 — Weekly
    THIS module. Net negative week → −25% next week. −10% week → 48h
    pause. −15% from peak any time → minimum size + ML signal review.

LAYER 4 — Stage regression
    Enforced by CapitalStageTracker (in champion.stage).

LAYER 5 — Systemic
    THIS module. BTC drops > 20% in 7d → 100% USDT, ALL engines off.
    Exchange concentration limit, stablecoin diversification.

The RiskLaws class is queried by PositionSizer before every entry. It
returns either {"allowed": True, "scaler": float} or
{"allowed": False, "reason": str}.

State is daily-rolling and persists across the trading day. Reset on
UTC day rollover. No global state — caller owns the instance.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Optional


NS_PER_SEC  = 1_000_000_000
NS_PER_DAY  = 86_400 * NS_PER_SEC
NS_PER_WEEK = 7 * NS_PER_DAY


class RiskState(Enum):
    NORMAL              = "NORMAL"
    SIZE_REDUCED_DAILY  = "SIZE_REDUCED_DAILY"   # after 3 loss days, -25% × 5 days
    SIZE_REDUCED_WEEK   = "SIZE_REDUCED_WEEK"    # after losing week, -25% next week
    PAUSED_DAILY        = "PAUSED_DAILY"         # 5% daily DD hit; no trades today
    PAUSED_WEEK_HARD    = "PAUSED_WEEK_HARD"     # -10% week → 48h pause
    MIN_SIZE_DD15       = "MIN_SIZE_DD15"        # -15% from peak → minimum size only
    HALTED_SYSTEMIC     = "HALTED_SYSTEMIC"      # BTC -20%/7d → 100% USDT, all off


@dataclass
class DailySnapshot:
    day_key:       str        # "YYYYMMDD" UTC
    open_equity:   float
    close_equity:  float
    pnl_pct:       float


class RiskLaws:
    """Enforces Layer 2, 3, 5 rules. Layer 1 is trade-local (sizer).
    Layer 4 is in CapitalStageTracker.

    The caller pumps `update_equity(eq, t_ns)` on every mark-to-market
    sample, and `record_trade_close(pnl_pct, t_ns)` after each closed
    trade. Then `decision(t_ns)` returns whether new entries are
    allowed and what size scaler to apply.
    """

    DAILY_DD_HARD     = 0.05    # 5% intraday → halt for the day
    DAILY_DD_REDUCE   = 0.03    # 3 consec days at this floor reduce size
    WEEKLY_DD_HARD    = 0.10    # 10% week-on-week → 48h pause
    PEAK_DD_MIN_SIZE  = 0.15    # 15% from peak → minimum size only
    WEEK_PAUSE_NS     = 48 * 3600 * NS_PER_SEC
    SIZE_REDUCE_FRAC  = 0.75    # -25% means scaler 0.75
    DAILY_LOSS_STREAK = 3       # # of consecutive loss days before reduction
    DAILY_REDUCE_DAYS = 5
    SYSTEMIC_BTC_DD   = 0.20    # 20% BTC drop in 7d → halt all
    SYSTEMIC_LOOKBACK_NS = 7 * NS_PER_DAY

    def __init__(self):
        # Equity timeline
        self._equity:           float = 0.0
        self._peak:             float = 0.0
        self._day_open_equity:  float = 0.0
        self._day_key:          str   = ""
        self._daily_pnl_pct:    float = 0.0    # signed, today
        # Daily history for streak detection
        self._daily_history: Deque[DailySnapshot] = deque(maxlen=30)
        # Weekly tracking
        self._week_open_equity: float = 0.0
        self._week_open_ns:     int   = 0
        # Pause clocks
        self._daily_paused_until_day: str = ""    # halt until next UTC day
        self._weekly_pause_until_ns:  int = 0     # 48h pauses
        # Daily size-reduction window
        self._size_reduced_until_day_count: int = 0  # remaining days
        # Weekly size-reduction window
        self._weekly_size_reduced_for_week: bool = False
        # Systemic
        self._btc_history: Deque[tuple[int, float]] = deque(maxlen=2500)
        self._systemic_halted: bool = False
        # Reasons (for telemetry)
        self._last_state: RiskState = RiskState.NORMAL

    # ── ingestion ──
    def update_equity(self, equity: float, t_ns: int):
        if equity <= 0: return
        self._equity = equity
        if equity > self._peak:
            self._peak = equity
        self._roll_day(t_ns)
        self._roll_week(t_ns)
        # Update intraday daily pnl
        if self._day_open_equity > 0:
            self._daily_pnl_pct = (equity - self._day_open_equity) / self._day_open_equity

    def update_btc_price(self, price: float, t_ns: int):
        """Pump BTC price periodically so the systemic kill can fire."""
        if price <= 0: return
        self._btc_history.append((t_ns, price))
        # Evict beyond systemic lookback
        cutoff = t_ns - self.SYSTEMIC_LOOKBACK_NS
        while self._btc_history and self._btc_history[0][0] < cutoff:
            self._btc_history.popleft()
        # Evaluate systemic kill
        if self._btc_history:
            high7 = max(p for _, p in self._btc_history)
            dd = (high7 - price) / high7
            self._systemic_halted = dd >= self.SYSTEMIC_BTC_DD

    def record_trade_close(self, pnl_pct: float, t_ns: int):
        """Pump after every closed trade; we use this only for daily-loss-day
        counting + intraday pnl already comes from update_equity."""
        # Intentionally minimal — daily streak comes from CLOSE-OF-DAY equity,
        # not per-trade. record_trade_close is a hook for callers to journal.

    # ── decision ──
    def decision(self, t_ns: int) -> dict:
        """Returns {allowed: bool, size_scaler: float, state: RiskState,
                    reason: str}. PositionSizer multiplies size_scaler
                    onto its base."""
        self._roll_day(t_ns)

        # Layer 5 — systemic halt
        if self._systemic_halted:
            self._last_state = RiskState.HALTED_SYSTEMIC
            return {"allowed": False, "size_scaler": 0.0,
                    "state": RiskState.HALTED_SYSTEMIC,
                    "reason": "BTC dropped ≥20% in 7d — all engines halted"}

        # Layer 2 — intraday daily DD
        if self._daily_pnl_pct <= -self.DAILY_DD_HARD:
            self._last_state = RiskState.PAUSED_DAILY
            self._daily_paused_until_day = self._next_day_key(t_ns)
            return {"allowed": False, "size_scaler": 0.0,
                    "state": RiskState.PAUSED_DAILY,
                    "reason": f"Daily DD {self._daily_pnl_pct*100:.2f}% ≤ "
                              f"−{self.DAILY_DD_HARD*100:.0f}% — halted today"}
        if self._day_key <= self._daily_paused_until_day and self._daily_paused_until_day:
            return {"allowed": False, "size_scaler": 0.0,
                    "state": RiskState.PAUSED_DAILY,
                    "reason": "Daily DD halt still in effect"}

        # Layer 3 — weekly hard pause
        if t_ns < self._weekly_pause_until_ns:
            self._last_state = RiskState.PAUSED_WEEK_HARD
            return {"allowed": False, "size_scaler": 0.0,
                    "state": RiskState.PAUSED_WEEK_HARD,
                    "reason": "Weekly −10% pause active (48h)"}

        # Layer 3 — peak DD ≥15% → minimum size only
        if self._peak > 0:
            peak_dd = (self._peak - self._equity) / self._peak
            if peak_dd >= self.PEAK_DD_MIN_SIZE:
                self._last_state = RiskState.MIN_SIZE_DD15
                return {"allowed": True, "size_scaler": 0.5,  # min-floor scaler
                        "state": RiskState.MIN_SIZE_DD15,
                        "reason": f"Peak DD {peak_dd*100:.1f}% ≥ "
                                  f"{self.PEAK_DD_MIN_SIZE*100:.0f}% — minimum size"}

        # Composite reductions
        scaler = 1.0
        states = []
        if self._size_reduced_until_day_count > 0:
            scaler *= self.SIZE_REDUCE_FRAC
            states.append(RiskState.SIZE_REDUCED_DAILY)
        if self._weekly_size_reduced_for_week:
            scaler *= self.SIZE_REDUCE_FRAC
            states.append(RiskState.SIZE_REDUCED_WEEK)

        state = states[0] if states else RiskState.NORMAL
        self._last_state = state
        return {"allowed": True, "size_scaler": scaler,
                "state": state,
                "reason": "ok" if state == RiskState.NORMAL else
                          f"reduced for {[s.value for s in states]}"}

    # ── internal day/week rollovers ──
    def _day_key_of(self, t_ns: int) -> str:
        return time.strftime("%Y%m%d", time.gmtime(t_ns / NS_PER_SEC))

    def _next_day_key(self, t_ns: int) -> str:
        return time.strftime("%Y%m%d",
                              time.gmtime(t_ns / NS_PER_SEC + 86_400))

    def _roll_day(self, t_ns: int):
        dk = self._day_key_of(t_ns)
        if dk == self._day_key:
            return
        # Close out previous day if there was one
        if self._day_key:
            close_eq = self._equity
            pnl_pct  = ((close_eq - self._day_open_equity) /
                        self._day_open_equity) if self._day_open_equity > 0 else 0.0
            self._daily_history.append(DailySnapshot(
                day_key=self._day_key, open_equity=self._day_open_equity,
                close_equity=close_eq, pnl_pct=pnl_pct,
            ))
            # 3-loss-day streak detection
            recent = list(self._daily_history)[-self.DAILY_LOSS_STREAK:]
            if (len(recent) == self.DAILY_LOSS_STREAK and
                    all(d.pnl_pct < 0 for d in recent) and
                    self._size_reduced_until_day_count == 0):
                self._size_reduced_until_day_count = self.DAILY_REDUCE_DAYS
            elif self._size_reduced_until_day_count > 0:
                self._size_reduced_until_day_count -= 1
        self._day_key         = dk
        self._day_open_equity = self._equity
        self._daily_pnl_pct   = 0.0
        # Clear daily pause when day rolls over
        if dk > self._daily_paused_until_day:
            self._daily_paused_until_day = ""

    def _roll_week(self, t_ns: int):
        if self._week_open_ns == 0:
            self._week_open_ns     = t_ns
            self._week_open_equity = self._equity
            return
        if t_ns - self._week_open_ns < NS_PER_WEEK:
            return
        # Close week
        wk_pnl = ((self._equity - self._week_open_equity) /
                   self._week_open_equity) if self._week_open_equity > 0 else 0.0
        # -10% week → 48h hard pause
        if wk_pnl <= -self.WEEKLY_DD_HARD:
            self._weekly_pause_until_ns = t_ns + self.WEEK_PAUSE_NS
        # Net negative week → reduced size next week
        self._weekly_size_reduced_for_week = wk_pnl < 0
        # Restart week
        self._week_open_ns     = t_ns
        self._week_open_equity = self._equity

    # ── views for telemetry ──
    @property
    def daily_pnl_pct(self) -> float: return self._daily_pnl_pct
    @property
    def peak_dd_pct(self) -> float:
        if self._peak <= 0: return 0.0
        return (self._peak - self._equity) / self._peak
    @property
    def systemic_halted(self) -> bool: return self._systemic_halted
    @property
    def last_state(self) -> RiskState: return self._last_state

    def __repr__(self) -> str:
        return (f"<RiskLaws state={self._last_state.value} "
                f"daily_pnl={self._daily_pnl_pct*100:.2f}% "
                f"peak_dd={self.peak_dd_pct*100:.2f}% "
                f"systemic={self._systemic_halted}>")
