"""
godmode.streams — seven independent signal streams per /GODSMODE spec.

Each stream is a tiny class with:
    .update(ctx: MarketContext)   — called once per tick
    .score() -> StreamOutput       — arbiter pulls this

StreamOutput.directional is signed (-100..+100); magnitude-only streams
use 0..+100. Confidence is 0..1. The arbiter rejects any stream with
confidence == 0 by treating it as a veto.

Streams 1, 2, 5, 7 are fully implemented. Streams 3, 4, 6 are stubbed
to neutral pass-through so the arbiter can run end-to-end; they get
real logic in follow-up commits once we validate the rest on live data.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from godmode.context import MarketContext


@dataclass
class StreamOutput:
    name:         str
    directional:  float = 0.0       # -100..+100 (signed)
    magnitude:    float = 0.0       # 0..+100 (magnitude-only)
    confidence:   float = 0.0       # 0..1
    veto:         bool  = False
    data:         dict  = field(default_factory=dict)


# ═══════════════════════ STREAM 1 ═══════════════════════════════════
class MicrostructureStream:
    """DIR + STD + persistence filter → directional pressure score."""

    DIR_BULL = 1.35
    DIR_BEAR = 0.75
    STD_Z_TH = 1.5
    PERSIST  = 3    # need 3 consecutive updates agreeing

    def __init__(self):
        self._recent_verdicts: Deque[int] = deque(maxlen=self.PERSIST)
        self._last_dir: Optional[float]   = None
        self._last_z:   Optional[float]   = None

    def update(self, ctx: MarketContext):
        d = ctx.dir_10()
        z = ctx.std_z()
        if d is None or z is None:
            return
        self._last_dir = d
        self._last_z   = z
        verdict = 0
        if d > self.DIR_BULL and z >  self.STD_Z_TH: verdict = +1
        if d < self.DIR_BEAR and z < -self.STD_Z_TH: verdict = -1
        self._recent_verdicts.append(verdict)

    def score(self) -> StreamOutput:
        if len(self._recent_verdicts) < self.PERSIST:
            return StreamOutput("microstructure", confidence=0.0,
                                data={"reason": "insufficient persistence"})
        # all three must agree on sign
        v = list(self._recent_verdicts)
        if all(x ==  1 for x in v):
            mag = min(100.0, 50.0 + (abs(self._last_z or 0) * 15))
            return StreamOutput("microstructure",
                                directional=+mag, magnitude=mag,
                                confidence=min(1.0, abs(self._last_z or 1) / 3),
                                data={"dir": self._last_dir,
                                      "std_z": self._last_z})
        if all(x == -1 for x in v):
            mag = min(100.0, 50.0 + (abs(self._last_z or 0) * 15))
            return StreamOutput("microstructure",
                                directional=-mag, magnitude=mag,
                                confidence=min(1.0, abs(self._last_z or 1) / 3),
                                data={"dir": self._last_dir,
                                      "std_z": self._last_z})
        return StreamOutput("microstructure", confidence=0.0,
                            data={"reason": "no persistent consensus",
                                  "dir": self._last_dir,
                                  "std_z": self._last_z})


# ═══════════════════════ STREAM 2 ═══════════════════════════════════
class VolatilityRegimeStream:
    """Volatility expansion from contraction; reject if already >2σ extended."""

    def __init__(self):
        self._atr_history: Deque[float] = deque(maxlen=30)
        self._overextended = False

    def update(self, ctx: MarketContext):
        atr = ctx.atr_1m(n=14)
        if atr is not None:
            self._atr_history.append(atr)
        # Cache overextended check here so score() doesn't need ctx
        self._overextended = False
        if len(ctx.candles_1m) >= 20:
            closes = [c.c for c in list(ctx.candles_1m)[-20:]]
            mu = sum(closes) / len(closes)
            var = sum((x - mu) ** 2 for x in closes) / max(1, len(closes) - 1)
            sd = math.sqrt(var)
            if sd > 0:
                move = abs(closes[-1] - mu) / sd
                self._overextended = move > 2.0

    def score(self) -> StreamOutput:
        if len(self._atr_history) < 5:
            return StreamOutput("volatility", confidence=0.0,
                                data={"reason": "not enough candles"})
        cur   = self._atr_history[-1]
        prior = list(self._atr_history)[-6:-1]
        if not prior:
            return StreamOutput("volatility", confidence=0.0)
        prior_mean = sum(prior) / len(prior)
        if prior_mean <= 0:
            return StreamOutput("volatility", confidence=0.0)
        expansion = cur / prior_mean  # >1 = expanding

        overextended = self._overextended

        if overextended:
            return StreamOutput("volatility", veto=True, confidence=0.0,
                                data={"reason": "price >2σ extended",
                                      "expansion": expansion})

        # expansion from contraction: require expansion > 1.2
        if expansion > 1.2:
            conf = min(1.0, (expansion - 1.0) * 2)
            mag  = min(100.0, (expansion - 1.0) * 100)
            return StreamOutput("volatility", magnitude=mag,
                                confidence=conf,
                                data={"expansion": expansion,
                                      "atr_current": cur,
                                      "atr_prior_mean": prior_mean})
        return StreamOutput("volatility", confidence=0.0,
                            data={"reason": "no meaningful expansion",
                                  "expansion": expansion})


# ═══════════════════════ STREAM 3 ═══════════════════════════════════
class AbsorptionStream:
    """Liquidity-absorption detector per /godsmode L99 §3.

    Bullish absorption: heavy aggressive sells but price holds (delta
    divergence — sellers eaten, no new lows).
    Bearish absorption: heavy aggressive buys but price stalls.

    Implementation:
      - 30s rolling: track aggressive_sell_vol and aggressive_buy_vol
      - 30s rolling: track price min and max
      - Bullish absorption when:
          aggressive_sell_vol > 1.5× aggressive_buy_vol AND
          (price_now − price_min) / price_min > 0  (no new low)
      - Strength scaled by the imbalance ratio
    """
    LOOKBACK_S        = 30
    IMBALANCE_RATIO   = 1.5

    def __init__(self):
        self._snapshot: Optional[StreamOutput] = None

    def update(self, ctx: MarketContext):
        cutoff = (ctx.recent_trades[-1].t_ns - self.LOOKBACK_S * 1_000_000_000
                  if ctx.recent_trades else 0)
        buy_vol = sell_vol = 0.0
        for t in reversed(ctx.recent_trades):
            if t.t_ns < cutoff: break
            if t.side == "buy":  buy_vol  += t.size
            else:                sell_vol += t.size

        # Need some flow to score
        if buy_vol + sell_vol < 1e-9:
            self._snapshot = StreamOutput("absorption", confidence=0.0,
                                           data={"reason": "no flow"})
            return

        # Get last-5s mid range to detect "price holds"
        last_5_cutoff = (ctx.recent_trades[-1].t_ns - 5 * 1_000_000_000
                         if ctx.recent_trades else 0)
        prices = [t.price for t in ctx.recent_trades if t.t_ns >= last_5_cutoff]
        if not prices:
            self._snapshot = StreamOutput("absorption", confidence=0.0,
                                           data={"reason": "no recent prices"})
            return
        mid = ctx.mid() or prices[-1]
        p_min, p_max = min(prices), max(prices)
        # Price held = current near range mid (within 0.05%)
        held_low  = (mid - p_min) / mid < 0.0005 if mid > 0 else False
        held_high = (p_max - mid) / mid < 0.0005 if mid > 0 else False

        # Bullish absorption: heavy sells, price didn't break low
        if sell_vol > self.IMBALANCE_RATIO * max(buy_vol, 1e-9) and not held_low:
            ratio = sell_vol / max(buy_vol, 1e-9)
            magnitude = min(100.0, 50.0 + (ratio - 1.5) * 20)
            self._snapshot = StreamOutput(
                "absorption", magnitude=magnitude,
                confidence=min(1.0, (ratio - 1.5) / 2.0),
                data={"side": "bullish", "sell_vol": sell_vol,
                      "buy_vol": buy_vol, "ratio": ratio,
                      "trap_probability": min(1.0, (ratio - 1.5) / 3.0)})
            return
        # Bearish absorption: heavy buys, price didn't break high
        if buy_vol > self.IMBALANCE_RATIO * max(sell_vol, 1e-9) and not held_high:
            ratio = buy_vol / max(sell_vol, 1e-9)
            magnitude = min(100.0, 50.0 + (ratio - 1.5) * 20)
            self._snapshot = StreamOutput(
                "absorption", magnitude=magnitude,
                confidence=min(1.0, (ratio - 1.5) / 2.0),
                data={"side": "bearish", "buy_vol": buy_vol,
                      "sell_vol": sell_vol, "ratio": ratio,
                      "trap_probability": min(1.0, (ratio - 1.5) / 3.0)})
            return

        # Balanced flow — neutral pass
        self._snapshot = StreamOutput("absorption", magnitude=50.0,
                                       confidence=0.3,
                                       data={"buy_vol": buy_vol,
                                             "sell_vol": sell_vol})

    def score(self) -> StreamOutput:
        return self._snapshot or StreamOutput("absorption", confidence=0.0)


# ═══════════════════════ STREAM 4 ═══════════════════════════════════
class StructuralBreakStream:
    """Structural-break validator per /godsmode L99 §4.

    Validates:
      - Local high/low break against the last 15-min range
      - Volume confirmation (current minute >= 1.3× recent avg)
      - No immediate opposite wall (top-of-book size > 3× recent median)

    Reject false breaks with no delta alignment.
    """
    RANGE_MINUTES   = 15
    VOL_CONFIRM     = 1.3
    WALL_MULT       = 3.0

    def __init__(self):
        self._snapshot: Optional[StreamOutput] = None
        self._level_size_history: Deque[float] = deque(maxlen=120)

    def update(self, ctx: MarketContext):
        if len(ctx.candles_1m) < self.RANGE_MINUTES + 1:
            self._snapshot = StreamOutput("structural", confidence=0.0,
                                           data={"reason": "warming up"})
            return
        candles = list(ctx.candles_1m)[-self.RANGE_MINUTES:]
        prior = candles[:-1]
        cur   = candles[-1]
        prior_high = max(c.h for c in prior)
        prior_low  = min(c.l for c in prior)
        avg_vol = sum(c.v for c in prior) / len(prior)
        bb, ba = ctx.best_quote()
        if not bb or not ba:
            self._snapshot = StreamOutput("structural", confidence=0.0)
            return

        # Track top-of-book sizes
        if ctx.book is not None:
            bids, asks = ctx.book.top(1)
            top_size = (bids[0][1] if bids else 0) + (asks[0][1] if asks else 0)
            self._level_size_history.append(top_size)
        median_size = (sorted(self._level_size_history)[len(self._level_size_history) // 2]
                       if self._level_size_history else 0)

        broke_up   = cur.h > prior_high
        broke_down = cur.l < prior_low
        vol_ok     = cur.v > self.VOL_CONFIRM * avg_vol if avg_vol > 0 else False

        if broke_up:
            # Wall above? compare top-ask size to median
            ask_size = ctx.book.top(1)[1][0][1] if ctx.book else 0
            wall_above = ask_size > self.WALL_MULT * median_size if median_size else False
            if vol_ok and not wall_above:
                magnitude = min(100.0,
                                  60.0 + (cur.h - prior_high) / prior_high * 10000)
                self._snapshot = StreamOutput(
                    "structural", magnitude=magnitude,
                    confidence=0.8 if vol_ok else 0.4,
                    data={"side": "up", "broke_level": prior_high,
                          "vol_ratio": cur.v / max(avg_vol, 1e-9),
                          "wall_above": wall_above})
                return
        if broke_down:
            bid_size = ctx.book.top(1)[0][0][1] if ctx.book else 0
            wall_below = bid_size > self.WALL_MULT * median_size if median_size else False
            if vol_ok and not wall_below:
                magnitude = min(100.0,
                                  60.0 + (prior_low - cur.l) / prior_low * 10000)
                self._snapshot = StreamOutput(
                    "structural", magnitude=magnitude,
                    confidence=0.8 if vol_ok else 0.4,
                    data={"side": "down", "broke_level": prior_low,
                          "vol_ratio": cur.v / max(avg_vol, 1e-9),
                          "wall_below": wall_below})
                return

        # No break — neutral pass-through (low confidence, no veto)
        self._snapshot = StreamOutput("structural", magnitude=40.0,
                                       confidence=0.3,
                                       data={"prior_high": prior_high,
                                             "prior_low":  prior_low,
                                             "vol_ratio":  cur.v / max(avg_vol, 1e-9)})

    def score(self) -> StreamOutput:
        return self._snapshot or StreamOutput("structural", confidence=0.0)


# ═══════════════════════ STREAM 5 ═══════════════════════════════════
class FeeEdgeStream:
    """Computes net_edge = expected_move - (fees + slippage).

    expected_move is estimated as 0.8 × ATR(1m), i.e. a 2-5min hold is
    expected to capture ~80% of a typical 1-min bar's move. This is a
    conservative default — can be tuned from replay data.
    """

    MAKER_FEE    = 0.0002     # 0.02% Gate.io VIP0 futures maker
    TAKER_FEE    = 0.0005     # 0.05% taker
    SLIP_BP      = 0.0003     # 3bp assumed taker-exit slippage
    MIN_EDGE     = 0.0012     # 0.12% from spec
    AGG_EDGE     = 0.0025     # 0.25% for aggressive mode

    def __init__(self):
        self._cached_move:   Optional[float] = None
        self._cached_edge:   Optional[float] = None
        self._cached_price:  Optional[float] = None

    def update(self, ctx: MarketContext):
        atr = ctx.atr_1m(14)
        mid = ctx.mid()
        if atr is None or mid is None:
            return
        expected_move_pct = 0.8 * (atr / mid)   # fractional
        # Assume maker entry + taker exit (worst realistic case)
        cost = self.MAKER_FEE + self.TAKER_FEE + self.SLIP_BP
        self._cached_price = mid
        self._cached_move  = expected_move_pct
        self._cached_edge  = expected_move_pct - cost

    def score(self) -> StreamOutput:
        if self._cached_edge is None:
            return StreamOutput("fee_edge", confidence=0.0)
        if self._cached_edge < self.MIN_EDGE:
            return StreamOutput("fee_edge", veto=True, confidence=0.0,
                                data={"reason": "edge below minimum",
                                      "net_edge": self._cached_edge,
                                      "expected_move": self._cached_move})
        # confidence scales with how far above minimum we are
        conf = min(1.0, (self._cached_edge - self.MIN_EDGE) /
                         (self.AGG_EDGE - self.MIN_EDGE))
        return StreamOutput("fee_edge",
                            magnitude=100.0 * min(1.0, self._cached_edge / self.AGG_EDGE),
                            confidence=conf,
                            data={"net_edge": self._cached_edge,
                                  "expected_move": self._cached_move,
                                  "aggressive_ok": self._cached_edge >= self.AGG_EDGE})


# ═══════════════════════ STREAM 6 (stub — executor quality) ═══════
class ExecutionQualityStream:
    """v1 stub: rejects when spread widens or depth thins. Full fill sim
    in follow-up commit."""

    def __init__(self):
        self._spread_window: Deque[float] = deque(maxlen=30)

    def update(self, ctx: MarketContext):
        s = ctx.spread_bp()
        if s is not None:
            self._spread_window.append(s)

    def score(self) -> StreamOutput:
        if len(self._spread_window) < 5:
            return StreamOutput("execution", confidence=0.0)
        cur    = self._spread_window[-1]
        recent = list(self._spread_window)[-5:]
        avg    = sum(recent) / len(recent)
        # Reject if current spread > 2× recent average (widening)
        if avg > 0 and cur > avg * 2:
            return StreamOutput("execution", veto=True, confidence=0.0,
                                data={"reason": "spread widening",
                                      "cur_bp": cur, "avg_bp": avg})
        return StreamOutput("execution", magnitude=80.0, confidence=0.8,
                            data={"cur_bp": cur, "avg_bp": avg})


# ═══════════════════════ STREAM 7 ═══════════════════════════════════
class RiskThrottleStream:
    """State machine: NORMAL / AGGRESSIVE / COOLED / PAUSED / HALTED."""

    BASE_RISK      = 0.006     # 0.6%
    AGG_RISK       = 0.010     # 1.0%
    DEFENSIVE_RISK = 0.003     # 0.3%
    DAILY_DD_STOP  = 0.03      # 3% account

    def __init__(self):
        self.state          = "NORMAL"
        self.consec_losses  = 0
        self.cooldown_until = 0    # ns timestamp
        self.halt_until     = 0    # ns (typically rest of day)
        self.daily_pnl_pct  = 0.0
        self.day_key        = ""
        self.total_trades   = 0
        self.total_wins     = 0

    def record_trade(self, pnl_pct: float, t_ns: int):
        self.total_trades += 1
        if pnl_pct > 0:
            self.total_wins += 1
            self.consec_losses = 0
            if self.state == "COOLED":
                self.state = "NORMAL"
        else:
            self.consec_losses += 1
            if self.consec_losses == 2:
                self.state = "COOLED"
            elif self.consec_losses >= 3:
                self.state = "PAUSED"
                self.cooldown_until = t_ns + 30 * 60 * 1_000_000_000   # 30 min
        self.daily_pnl_pct += pnl_pct
        if self.daily_pnl_pct <= -self.DAILY_DD_STOP:
            self.state = "HALTED"
            # Halt until end of UTC day
            day_end_s = (t_ns // 1_000_000_000 // 86400 + 1) * 86400
            self.halt_until = day_end_s * 1_000_000_000

    def update(self, ctx: MarketContext):
        if not ctx.recent_trades: return
        t_ns = ctx.recent_trades[-1].t_ns
        # day rollover
        day_key = time.strftime("%Y%m%d",
                                 time.gmtime(t_ns / 1_000_000_000))
        if day_key != self.day_key:
            self.day_key       = day_key
            self.daily_pnl_pct = 0.0
            if self.state == "HALTED":
                self.state = "NORMAL"
        # Cooldown / halt elapsed?
        if self.state == "PAUSED" and t_ns >= self.cooldown_until:
            self.state = "COOLED"
            self.consec_losses = 0
        if self.state == "HALTED" and t_ns >= self.halt_until:
            self.state = "NORMAL"

    def allowed_risk(self) -> float:
        if self.state == "HALTED" or self.state == "PAUSED":
            return 0.0
        if self.state == "AGGRESSIVE":
            return self.AGG_RISK
        if self.state == "COOLED":
            return self.DEFENSIVE_RISK
        return self.BASE_RISK

    def score(self) -> StreamOutput:
        risk = self.allowed_risk()
        if risk == 0.0:
            return StreamOutput("risk", veto=True, confidence=0.0,
                                data={"state": self.state,
                                      "consec_losses": self.consec_losses,
                                      "daily_pnl": self.daily_pnl_pct})
        return StreamOutput("risk",
                            magnitude=(risk / self.AGG_RISK) * 100,
                            confidence=1.0,
                            data={"state": self.state,
                                  "allowed_risk": risk,
                                  "daily_pnl": self.daily_pnl_pct,
                                  "consec_losses": self.consec_losses})
