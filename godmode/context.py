"""
godmode.context — shared rolling market state consumed by all streams.

Every stream reads from a single `MarketContext` updated tick-by-tick,
so we avoid per-stream book reconstruction + give the arbiter a
consistent snapshot.

State kept:
    book             — live LocalBook (from M1 / M2 replay)
    recent_trades    — deque of (t_ns, side, price, size), 10-min window
    recent_tickers   — deque of book_ticker events, 10-min window
    candles_1m       — deque of (open, high, low, close, volume) per minute
    candles_30m      — rolling 30-minute range stats
    baseline_delta   — 10-min rolling baseline for STD Z-score (from collector)
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple


NS_PER_MIN = 60 * 1_000_000_000
NS_PER_SEC = 1_000_000_000


@dataclass
class TradeRec:
    t_ns:  int
    side:  str         # "buy" | "sell"
    price: float
    size:  float


@dataclass
class TickerRec:
    t_ns:  int
    bid:   float
    ask:   float
    bs:    float
    as_:   float


@dataclass
class Candle1m:
    open_ts_ns: int
    o: float
    h: float
    l: float
    c: float
    v: float      # sum of aggressive volume in the minute (buy + sell, abs)

    def update(self, price: float, vol: float = 0.0):
        if price > self.h: self.h = price
        if price < self.l: self.l = price
        self.c = price
        self.v += vol


class MarketContext:
    """Single source of truth for streams. Fed by the replay tick bus
    or a thin live adapter."""

    def __init__(self, contract: str,
                 trade_window_s: int = 600,
                 ticker_window_s: int = 600,
                 candle_1m_keep: int = 30,
                 candle_30m_keep: int = 6):
        self.contract          = contract
        self.trade_window_ns   = trade_window_s * NS_PER_SEC
        self.ticker_window_ns  = ticker_window_s * NS_PER_SEC
        self.book              = None    # LocalBook, injected from tick
        self.recent_trades:   Deque[TradeRec]  = deque()
        self.recent_tickers:  Deque[TickerRec] = deque()
        self.candles_1m:      Deque[Candle1m]  = deque(maxlen=candle_1m_keep)
        self.candles_30m_ranges: Deque[float]  = deque(maxlen=candle_30m_keep)
        self._std_baseline: Deque[float]       = deque(maxlen=600)  # 10-min at 1Hz
        self._last_sample_ts: int              = 0

        # derived cached
        self.last_price: Optional[float] = None

    # ── tick ingestion ───────────────────────────────────────────
    def ingest(self, tick):
        """tick is a godmode.replay.Tick (or equivalent from a live
        adapter) with t_ns, kind, payload, book."""
        self.book = tick.book
        t_ns = tick.t_ns
        if tick.kind == "trade":
            p = tick.payload
            side  = p.get("side", "buy")
            price = float(p.get("price", 0))
            size  = float(p.get("size", 0))
            self.last_price = price
            self.recent_trades.append(TradeRec(t_ns, side, price, size))
            self._bump_candle(t_ns, price, size)
        elif tick.kind == "book_ticker":
            p = tick.payload
            bid = float(p.get("bid", 0))
            ask = float(p.get("ask", 0))
            if bid > 0 and ask > 0:
                self.last_price = (bid + ask) / 2
                self.recent_tickers.append(
                    TickerRec(t_ns, bid, ask,
                              float(p.get("bs", 0)), float(p.get("as_", 0))))
                self._bump_candle(t_ns, self.last_price, 0.0)

        # evict old
        cutoff_trades  = t_ns - self.trade_window_ns
        while self.recent_trades  and self.recent_trades[0].t_ns  < cutoff_trades:
            self.recent_trades.popleft()
        cutoff_tickers = t_ns - self.ticker_window_ns
        while self.recent_tickers and self.recent_tickers[0].t_ns < cutoff_tickers:
            self.recent_tickers.popleft()

        # update STD baseline at ~1Hz
        if t_ns - self._last_sample_ts > NS_PER_SEC:
            self._std_baseline.append(self.std_30s())
            self._last_sample_ts = t_ns

    # ── candle bookkeeping ───────────────────────────────────────
    def _bump_candle(self, t_ns: int, price: float, vol: float):
        m_open = (t_ns // NS_PER_MIN) * NS_PER_MIN
        if not self.candles_1m or self.candles_1m[-1].open_ts_ns != m_open:
            # close previous candle, compute 30m range and push
            if self.candles_1m:
                # collect last-30 candles' H-L range
                last_n = list(self.candles_1m)[-30:]
                if last_n:
                    hi = max(c.h for c in last_n)
                    lo = min(c.l for c in last_n)
                    self.candles_30m_ranges.append(hi - lo)
            self.candles_1m.append(Candle1m(
                open_ts_ns=m_open, o=price, h=price, l=price, c=price, v=vol))
        else:
            self.candles_1m[-1].update(price, vol)

    # ── derived metrics used by multiple streams ─────────────────
    def dir_10(self) -> Optional[float]:
        if self.book is None: return None
        return self.book.dir_10()

    def best_quote(self) -> Tuple[Optional[float], Optional[float]]:
        if self.book is None: return None, None
        return self.book.best_quote()

    def mid(self) -> Optional[float]:
        bb, ba = self.best_quote()
        if bb is None or ba is None: return None
        return (bb + ba) / 2.0

    def spread_bp(self) -> Optional[float]:
        bb, ba = self.best_quote()
        if not (bb and ba and bb > 0): return None
        return (ba - bb) / bb * 10_000

    def std_30s(self) -> float:
        """Aggressive buy vol minus aggressive sell vol over the last 30s."""
        cutoff = 0
        if self.recent_trades:
            cutoff = self.recent_trades[-1].t_ns - 30 * NS_PER_SEC
        b = a = 0.0
        for t in reversed(self.recent_trades):
            if t.t_ns < cutoff: break
            if t.side == "buy":  b += t.size
            else:                a += t.size
        return b - a

    def std_z(self) -> Optional[float]:
        if len(self._std_baseline) < 30: return None
        n = len(self._std_baseline)
        mu = sum(self._std_baseline) / n
        var = sum((x - mu) ** 2 for x in self._std_baseline) / max(1, n - 1)
        sd = math.sqrt(var)
        if sd == 0: return None
        return (self.std_30s() - mu) / sd

    def atr_1m(self, n: int = 14) -> Optional[float]:
        """Average True Range on last n 1-min candles."""
        if len(self.candles_1m) < n + 1: return None
        trs = []
        cs = list(self.candles_1m)[-(n + 1):]
        for i in range(1, len(cs)):
            hi = cs[i].h; lo = cs[i].l; prev_c = cs[i - 1].c
            tr = max(hi - lo, abs(hi - prev_c), abs(lo - prev_c))
            trs.append(tr)
        return sum(trs) / len(trs)

    def range_30m_percentile(self) -> Optional[float]:
        """Current 30-min range's percentile within the rolling window.
        Returns 0.0–1.0; low = tight range (squeeze)."""
        if not self.candles_30m_ranges: return None
        current = self.candles_30m_ranges[-1]
        n_below = sum(1 for r in self.candles_30m_ranges if r <= current)
        return n_below / len(self.candles_30m_ranges)

    def bollinger_squeeze(self, n: int = 20) -> Optional[bool]:
        """True if the last n 1m candle closes have std-dev in bottom 20% of
        a self-rolling band width history. Kept simple."""
        if len(self.candles_1m) < n: return None
        closes = [c.c for c in list(self.candles_1m)[-n:]]
        mu = sum(closes) / n
        var = sum((x - mu) ** 2 for x in closes) / max(1, n - 1)
        sd = math.sqrt(var)
        band_width = sd * 4
        # compare to recent band widths (expand candles_1m maxlen to ~120 or track separately)
        # For v1 we just flag True if band_width < 0.1% of mid
        mid = self.mid()
        if not mid: return None
        return band_width / mid < 0.001   # 10bp band = squeeze
