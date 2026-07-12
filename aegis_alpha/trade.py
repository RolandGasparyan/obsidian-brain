"""
aegis_alpha.trade — AlphaTrade state machine per CHAMPION_MODE.md §3.3.

A long-only momentum trade: opened above a 4H breakout, sized by
champion.PositionSizer, exited via a TP ladder + trailing stop +
hard time limit + immediate-exit conditions.

State machine:
    OPEN  → trade running, units > 0
    DONE  → all units exited; closed=True

Exit reasons (in priority order, first match wins):
    HARD_STOP             stop price hit (-1R) — never moved further
    TIME_EXIT_NO_1R       trade older than 48h with no 1R hit yet
    TIME_EXIT_MAX         trade older than max_hold (72h Stage 1)
    BTC_DROP_3PCT_1H      market-wide kill: BTC dropped > 3% in 1h
    BREAKOUT_RECLAIMED    bear reclaimed breakout level → failed
    VOLUME_COLLAPSE       trade-volume < 50% of entry-bar volume
    TP_LADDER_DONE        all TP levels hit
    TRAIL_STOP            trailing stop triggered after 3R+

R-multiple bookkeeping:
    R_value      = entry_price - initial_stop_price (always positive)
    pnl_in_R     = (exit_price - entry_price) / R_value
    cumulative_R weighted by fraction-of-position exited at each leg
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class TradeStatus(Enum):
    OPEN = "OPEN"
    DONE = "DONE"


class CloseReason(Enum):
    HARD_STOP            = "HARD_STOP"
    TIME_EXIT_NO_1R      = "TIME_EXIT_NO_1R"
    TIME_EXIT_MAX        = "TIME_EXIT_MAX"
    BTC_DROP_3PCT_1H     = "BTC_DROP_3PCT_1H"
    BREAKOUT_RECLAIMED   = "BREAKOUT_RECLAIMED"
    VOLUME_COLLAPSE      = "VOLUME_COLLAPSE"
    TP_LADDER_DONE       = "TP_LADDER_DONE"
    TRAIL_STOP           = "TRAIL_STOP"
    MANUAL               = "MANUAL"


# ── TP ladders per §3.3 ──────────────────────────────────────────────
# Standard (score 72-87): exit 50% @ 2R, 50% @ 3R or trail
# God-tier (score ≥88):   exit 30% @ 2R, 40% @ 3.5R, 30% trail
STANDARD_TP_LADDER = [(2.0, 0.50), (3.0, 0.50)]
GOD_TIER_TP_LADDER = [(2.0, 0.30), (3.5, 0.40), (math.inf, 0.30)]

NS_PER_HOUR = 3600 * 1_000_000_000


@dataclass
class TPLevel:
    """A single rung of the TP ladder."""
    R_multiple: float        # +2.0 = 2R above entry
    fraction:   float        # of original units (must sum to 1.0 across ladder)
    hit:        bool = False
    hit_t_ns:   int = 0
    hit_price:  float = 0.0


@dataclass
class TrailStopState:
    """Trailing-stop state. Activated only after 2R hit (move to BE),
    then real trail after 3R."""
    activated_breakeven: bool = False
    activated_trailing:  bool = False
    peak_close:          float = 0.0     # highest close since 3R hit


@dataclass
class AlphaTrade:
    """Long-only paper trade. Updated tick-by-tick (or candle-by-candle)
    via .on_candle() / .on_price(). Returns close events when exits fire.
    """
    pair:                 str
    score:                float
    god_tier:              bool
    open_t_ns:             int
    entry_price:           float
    initial_stop_price:    float           # never moved further from entry
    breakout_level:        float           # bears reclaim → exit
    units_total:           float
    notional_usd:          float
    entry_volume:          float           # for volume-collapse detection
    risk_amount_usd:       float           # 1R in dollar terms
    atr_4h_at_entry:       float

    # Mutable state
    current_stop:          float = 0.0
    units_remaining:       float = 0.0
    tp_levels:             List[TPLevel] = field(default_factory=list)
    trail:                 TrailStopState = field(default_factory=TrailStopState)
    realized_R:            float = 0.0          # cumulative R captured by partials
    closed:                bool = False
    close_reason:          str = ""
    closed_t_ns:           int = 0
    last_price:            float = 0.0
    max_price_seen:        float = 0.0

    # Tunables (Champion §3.3)
    MAX_HOLD_HRS_STAGE1:   float = 72.0
    NO_1R_TIMEOUT_HRS:     float = 48.0
    BTC_FLASH_DROP_PCT:    float = 0.03      # 3% in 1h → kill
    VOLUME_COLLAPSE_FRAC:  float = 0.50      # < 50% of entry vol → exit

    def __post_init__(self):
        self.current_stop = self.initial_stop_price
        self.units_remaining = self.units_total
        self.last_price = self.entry_price
        self.max_price_seen = self.entry_price
        if not self.tp_levels:
            ladder = GOD_TIER_TP_LADDER if self.god_tier else STANDARD_TP_LADDER
            self.tp_levels = [TPLevel(R_multiple=r, fraction=f) for r, f in ladder]

    # ── derived ──
    @property
    def status(self) -> TradeStatus:
        return TradeStatus.DONE if self.closed else TradeStatus.OPEN

    @property
    def R_value(self) -> float:
        return self.entry_price - self.initial_stop_price

    @property
    def held_hrs(self) -> float:
        return (self.last_price_t_ns - self.open_t_ns) / NS_PER_HOUR \
                if hasattr(self, "last_price_t_ns") else 0

    def hit_1R(self) -> bool:
        return self.max_price_seen >= self.entry_price + self.R_value

    def hit_2R(self) -> bool:
        return self.max_price_seen >= self.entry_price + 2 * self.R_value

    def hit_3R(self) -> bool:
        return self.max_price_seen >= self.entry_price + 3 * self.R_value

    def pnl_in_R(self, exit_price: float) -> float:
        if self.R_value <= 0: return 0.0
        return (exit_price - self.entry_price) / self.R_value

    # ── mutation: only the engine should call these ──
    def tighten_stop(self, new_stop: float) -> bool:
        """Only tighter (closer to current price). Refuses widening."""
        if new_stop > self.current_stop:
            self.current_stop = new_stop
            return True
        return False

    def update_trail_state(self, atr_4h: float):
        """Activate trail state per §3.3:
           - after 2R: stop → breakeven
           - after 3R: trail at 1× ATR_4H below the running peak close."""
        if self.hit_2R() and not self.trail.activated_breakeven:
            self.trail.activated_breakeven = True
            self.tighten_stop(self.entry_price)
        if self.hit_3R():
            self.trail.activated_trailing = True
            if self.last_price > self.trail.peak_close:
                self.trail.peak_close = self.last_price
            new_trail = self.trail.peak_close - atr_4h
            self.tighten_stop(new_trail)

    def realize_partial(self, fraction: float, price: float, t_ns: int):
        """Record a partial exit at `price` for `fraction` of original units."""
        if fraction <= 0 or self.units_remaining <= 0:
            return 0.0
        units = min(self.units_total * fraction, self.units_remaining)
        self.units_remaining -= units
        self.realized_R += self.pnl_in_R(price) * fraction
        return units

    def close_remaining(self, price: float, t_ns: int, reason: CloseReason):
        """Exit the rest of the position at `price`."""
        if self.units_remaining > 0 and self.units_total > 0:
            remaining_frac = self.units_remaining / self.units_total
            self.realized_R += self.pnl_in_R(price) * remaining_frac
            self.units_remaining = 0.0
        self.closed = True
        self.close_reason = reason.value
        self.closed_t_ns = t_ns

    # ── tick-by-tick update — the heart of the state machine ──
    def on_candle(self,
                  candle_high: float,
                  candle_low:  float,
                  candle_close: float,
                  candle_volume: float,
                  atr_4h_now: float,
                  t_ns: int,
                  btc_drop_1h_pct: float = 0.0,
                  ) -> List[Tuple[CloseReason, float, float]]:
        """Process one new bar. Returns a list of close events:
        [(reason, price, units), ...] for partials + final close.
        """
        events: List[Tuple[CloseReason, float, float]] = []
        if self.closed:
            return events

        self.last_price = candle_close
        self.last_price_t_ns = t_ns
        if candle_high > self.max_price_seen:
            self.max_price_seen = candle_high

        # ── HIGHEST-PRIORITY HARD-EXIT CHECKS ──
        # Hard stop hit (used candle low)
        if candle_low <= self.current_stop:
            units = self.units_remaining
            self.realize_partial(units / self.units_total, self.current_stop, t_ns)
            events.append((CloseReason.HARD_STOP, self.current_stop, units))
            self.closed = True
            self.close_reason = CloseReason.HARD_STOP.value
            self.closed_t_ns = t_ns
            return events

        # BTC flash crash kill
        if btc_drop_1h_pct >= self.BTC_FLASH_DROP_PCT:
            units = self.units_remaining
            self.close_remaining(candle_close, t_ns, CloseReason.BTC_DROP_3PCT_1H)
            events.append((CloseReason.BTC_DROP_3PCT_1H, candle_close, units))
            return events

        # Breakout reclaimed (close back below breakout level)
        if candle_close < self.breakout_level:
            units = self.units_remaining
            self.close_remaining(candle_close, t_ns, CloseReason.BREAKOUT_RECLAIMED)
            events.append((CloseReason.BREAKOUT_RECLAIMED, candle_close, units))
            return events

        # Volume collapse
        if (self.entry_volume > 0 and
                candle_volume < self.VOLUME_COLLAPSE_FRAC * self.entry_volume):
            units = self.units_remaining
            self.close_remaining(candle_close, t_ns, CloseReason.VOLUME_COLLAPSE)
            events.append((CloseReason.VOLUME_COLLAPSE, candle_close, units))
            return events

        # Time exits — relative to open_t_ns
        held_hrs = (t_ns - self.open_t_ns) / NS_PER_HOUR
        if held_hrs > self.MAX_HOLD_HRS_STAGE1:
            units = self.units_remaining
            self.close_remaining(candle_close, t_ns, CloseReason.TIME_EXIT_MAX)
            events.append((CloseReason.TIME_EXIT_MAX, candle_close, units))
            return events
        if held_hrs > self.NO_1R_TIMEOUT_HRS and not self.hit_1R():
            units = self.units_remaining
            self.close_remaining(candle_close, t_ns, CloseReason.TIME_EXIT_NO_1R)
            events.append((CloseReason.TIME_EXIT_NO_1R, candle_close, units))
            return events

        # ── TP LADDER PARTIAL FILLS ──
        for tp in self.tp_levels:
            if tp.hit: continue
            if not math.isfinite(tp.R_multiple):
                continue   # the trail-only leg of god-tier ladder
            target_price = self.entry_price + tp.R_multiple * self.R_value
            if candle_high >= target_price and self.units_remaining > 0:
                units = self.realize_partial(tp.fraction, target_price, t_ns)
                tp.hit = True
                tp.hit_t_ns = t_ns
                tp.hit_price = target_price
                events.append((CloseReason.TP_LADDER_DONE, target_price, units))

        # ── TRAILING STOP ACTIVATION (§3.3) ──
        self.update_trail_state(atr_4h_now)

        # If only the trail leg remains and trail is activated, the next
        # candle's stop check above will catch it.

        # All TP levels hit + no trail leg means we're flat
        if self.units_remaining <= 1e-9:
            self.closed = True
            self.close_reason = CloseReason.TP_LADDER_DONE.value
            self.closed_t_ns = t_ns

        return events

    def __repr__(self) -> str:
        return (f"<AlphaTrade {self.pair} "
                f"entry={self.entry_price:.4f} stop={self.current_stop:.4f} "
                f"units_left={self.units_remaining:.4f}/"
                f"{self.units_total:.4f} "
                f"realized_R={self.realized_R:+.2f} "
                f"closed={self.closed}>")
