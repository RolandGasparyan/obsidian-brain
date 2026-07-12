#!/usr/bin/env python3
"""
Phase A — Microstructure data pipeline.

Subscribes to Gate.io public WebSocket streams (order_book + trades) for a
small pair universe and continuously computes a short, honest feature set
that the microstructure literature actually supports as predictive at
1-to-10-minute horizons:

    depth_imbalance    top-10 bid / top-10 ask notional ratio
    spread_pct         (ask1 - bid1) / mid, fractional
    delta_30s          aggressive buy notional - aggressive sell notional, last 30 s
    trade_intensity    trade count per second, last 30 s
    volatility_burst   stdev of last 20 trade log-returns, annualized-ish
    mid_price          used later for forward-return labels

NO EXECUTION. NO ORDER PLACEMENT. NO POSITION TRACKING. This is a
data-gathering daemon. The point is to have real order-book-derived
features on disk so that microstructure_analyze.py can answer one
question before we spend a line on Phase B:

    "Does any of this predict 2-10 minute forward returns, out of sample,
     on a pair we actually intend to trade?"

Architecture
  - One asyncio task per pair for the order-book channel
  - One asyncio task per pair for the trades channel
  - Every 1 s a feature snapshot is computed from current state and
    appended to an in-memory buffer
  - Hourly the buffer is flushed to a Parquet file partitioned by
    date/hour/pair
  - Reconnects with exponential backoff on WebSocket drops

Outputs
  /var/log/microstructure/YYYY-MM-DD/HH/PAIR.parquet
  (configurable via --out-dir)

Usage
  python microstructure_collector.py
  python microstructure_collector.py --pairs ETH_USDT SOL_USDT --snap-hz 2
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import signal
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None   # derivatives poller becomes a no-op if missing

# L99 Supreme Regime Detection layer
try:
    from regime_classifier import RegimeState, compute_regime, refresh_ohlc
    _HAS_REGIME = True
except ImportError:
    _HAS_REGIME = False

try:
    import websockets
except ImportError:
    print("pip install websockets pyarrow pandas", file=sys.stderr); sys.exit(1)
try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    print("pip install websockets pyarrow pandas", file=sys.stderr); sys.exit(1)


GATEIO_SPOT_WS    = "wss://api.gateio.ws/ws/v4/"
GATEIO_FUTURES_WS = "wss://fx-ws.gateio.ws/v4/ws/usdt"
DEFAULT_PAIRS     = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]


def _ws_endpoint(market: str) -> str:
    return GATEIO_FUTURES_WS if market == "futures" else GATEIO_SPOT_WS


def _book_channel(market: str) -> str:
    return "futures.order_book" if market == "futures" else "spot.order_book"


def _trades_channel(market: str) -> str:
    return "futures.trades" if market == "futures" else "spot.trades"


def _book_subscribe_payload(market: str, pair: str) -> list:
    # Gate.io spot:    [pair, depth, interval]   e.g. ["BTC_USDT", "20", "1000ms"]
    # Gate.io futures: [pair, depth, interval]   e.g. ["BTC_USDT", "20", "0"]
    if market == "futures":
        return [pair, "20", "0"]
    return [pair, "20", "1000ms"]


# ── per-pair in-memory state ──────────────────────────────────────────
@dataclass
class OrderBook:
    """Top-N snapshot. We use the `spot.order_book` channel which pushes
    a full top-N snapshot on a fixed cadence (100ms or 1000ms). No diff
    merging required for Phase A."""
    bids: List[Tuple[float, float]] = field(default_factory=list)   # [(price, size), ...]
    asks: List[Tuple[float, float]] = field(default_factory=list)
    last_update_ms: int = 0

    @property
    def mid(self) -> float:
        if not self.bids or not self.asks: return float("nan")
        return (self.bids[0][0] + self.asks[0][0]) / 2

    @property
    def spread_pct(self) -> float:
        if not self.bids or not self.asks: return float("nan")
        m = self.mid
        if m <= 0: return float("nan")
        return (self.asks[0][0] - self.bids[0][0]) / m

    def top_n_notional(self, n: int = 10) -> Tuple[float, float]:
        bid_n = sum(p * s for p, s in self.bids[:n])
        ask_n = sum(p * s for p, s in self.asks[:n])
        return bid_n, ask_n

    def micro_price(self) -> float:
        """Stoikov micro-price — size-weighted mid that leans toward the
        side with more resting liquidity on the opposite wall. Classical
        microstructure literature shows this dominates plain midpoint
        for sub-minute return prediction."""
        if not self.bids or not self.asks: return float("nan")
        bp, bs = self.bids[0]
        ap, as_ = self.asks[0]
        tot = bs + as_
        if tot <= 0: return float("nan")
        # Bigger ask size → price leans toward bid (pressure down)
        return (bp * as_ + ap * bs) / tot

    def book_slope(self, n: int = 10, side: str = "bid") -> float:
        """Linear slope of cumulative size vs price distance from best.
        A steep slope means absorbing walls; a shallow slope means
        fragile book that can gap on a single market order.

        Returned in units of "size accumulated per 1% of price distance".
        """
        levels = self.bids[:n] if side == "bid" else self.asks[:n]
        if len(levels) < 2: return 0.0
        ref = levels[0][0]
        if ref <= 0: return 0.0
        cum_size = 0.0
        xs, ys = [], []
        for p, s in levels:
            cum_size += s
            dist_pct = abs(p - ref) / ref * 100   # % distance from best
            xs.append(dist_pct)
            ys.append(cum_size)
        # Least-squares slope
        n2 = len(xs)
        sx = sum(xs); sy = sum(ys)
        sxx = sum(x * x for x in xs)
        sxy = sum(x * y for x, y in zip(xs, ys))
        denom = n2 * sxx - sx * sx
        if denom == 0: return 0.0
        return (n2 * sxy - sx * sy) / denom


@dataclass
class OFIState:
    """Order Flow Imbalance (Cont/Kukanov/Stoikov 2014). Between two
    order-book snapshots, measure the net change in bid vs ask top-of-
    book size, adjusted for any price-level move. Positive OFI = buy
    pressure; negative = sell pressure.

    Peer-reviewed IC at 1-10 min horizons in equities: 0.05 to 0.15.
    Crypto spot hasn't been studied as rigorously, which is exactly
    why we want to measure it ourselves.
    """
    prev_bid_px:   float = float("nan")
    prev_bid_size: float = float("nan")
    prev_ask_px:   float = float("nan")
    prev_ask_size: float = float("nan")

    def update(self, bp: float, bs: float, ap: float, as_: float) -> float:
        if math.isnan(self.prev_bid_px):
            self.prev_bid_px, self.prev_bid_size = bp, bs
            self.prev_ask_px, self.prev_ask_size = ap, as_
            return 0.0
        # Bid-side contribution
        if   bp > self.prev_bid_px:  bid_e = bs             # price moved up, new size
        elif bp < self.prev_bid_px:  bid_e = -self.prev_bid_size  # level left, lost previous
        else:                        bid_e = bs - self.prev_bid_size
        # Ask-side contribution (symmetric, opposite sign)
        if   ap < self.prev_ask_px:  ask_e = as_
        elif ap > self.prev_ask_px:  ask_e = -self.prev_ask_size
        else:                        ask_e = as_ - self.prev_ask_size
        ofi = bid_e - ask_e
        self.prev_bid_px, self.prev_bid_size = bp, bs
        self.prev_ask_px, self.prev_ask_size = ap, as_
        return ofi


@dataclass
class TradeBuffer:
    """Rolling 30-second window of trades. Each entry:
        (ts_ms, price, size, side_sign)
    where side_sign = +1 for aggressor-buy (taker buy), -1 for aggressor-sell.
    Gate.io's `spot.trades` gives `side = "buy" | "sell"` meaning the
    aggressor side of the match.
    """
    trades: Deque[Tuple[int, float, float, int]] = field(default_factory=deque)
    window_ms: int = 30_000

    def add(self, ts_ms: int, price: float, size: float, side: str):
        side_sign = +1 if side == "buy" else -1
        self.trades.append((ts_ms, price, size, side_sign))
        # Trim
        cutoff = ts_ms - self.window_ms
        while self.trades and self.trades[0][0] < cutoff:
            self.trades.popleft()

    def stats(self, now_ms: int) -> Dict[str, float]:
        # Trim against the current wall time too, not just last trade ts
        cutoff = now_ms - self.window_ms
        while self.trades and self.trades[0][0] < cutoff:
            self.trades.popleft()
        if not self.trades:
            return dict(delta_30s=0.0, trade_intensity=0.0,
                        volatility_burst=0.0, trade_count=0)
        buy_n  = sum(p * s for _, p, s, sd in self.trades if sd > 0)
        sell_n = sum(p * s for _, p, s, sd in self.trades if sd < 0)
        delta  = buy_n - sell_n
        count  = len(self.trades)
        intensity = count / (self.window_ms / 1000.0)
        # log-return stdev of last 20 trades (or fewer)
        last_prices = [p for _, p, _, _ in list(self.trades)[-20:]]
        if len(last_prices) >= 2:
            rets = []
            for i in range(1, len(last_prices)):
                if last_prices[i - 1] > 0:
                    rets.append(math.log(last_prices[i] / last_prices[i - 1]))
            if rets:
                mu = sum(rets) / len(rets)
                var = sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)
                vol_burst = math.sqrt(var)
            else:
                vol_burst = 0.0
        else:
            vol_burst = 0.0
        return dict(delta_30s=delta, trade_intensity=intensity,
                    volatility_burst=vol_burst, trade_count=count)


@dataclass
class DerivSnapshot:
    """Latest perpetual-futures snapshot for a given underlying. Refreshed
    by a separate REST polling task every ~15 s. Two orders of magnitude
    slower than spot but that's fine — funding / OI / basis move on
    minutes-to-hours, not milliseconds."""
    mark_price:      float = float("nan")
    index_price:     float = float("nan")
    funding_rate_8h: float = float("nan")   # next period's predicted funding
    open_interest:   float = float("nan")   # in base-coin units
    last_refresh_ms: int   = 0


@dataclass
class PairState:
    pair: str
    book: OrderBook = field(default_factory=OrderBook)
    tape: TradeBuffer = field(default_factory=TradeBuffer)
    # Rolling OFI accumulator. Reset every 30 s so the feature represents
    # "net flow over last 30 s" rather than "since service started."
    ofi_state: OFIState = field(default_factory=OFIState)
    ofi_30s_buffer: Deque[Tuple[int, float]] = field(default_factory=deque)
    # Derivatives snapshot (populated by poll_derivatives_task)
    deriv: DerivSnapshot = field(default_factory=DerivSnapshot)
    # L99 regime state (rolling baselines + OHLC cache)
    regime: Optional[object] = None     # RegimeState if regime_classifier loaded
    # rolling buffer of feature snapshots waiting for Parquet flush
    buffer: List[Dict] = field(default_factory=list)

    def push_ofi(self, ts_ms: int, ofi_event: float):
        self.ofi_30s_buffer.append((ts_ms, ofi_event))
        cutoff = ts_ms - 30_000
        while self.ofi_30s_buffer and self.ofi_30s_buffer[0][0] < cutoff:
            self.ofi_30s_buffer.popleft()

    def ofi_sum_30s(self, now_ms: int) -> float:
        cutoff = now_ms - 30_000
        while self.ofi_30s_buffer and self.ofi_30s_buffer[0][0] < cutoff:
            self.ofi_30s_buffer.popleft()
        return sum(v for _, v in self.ofi_30s_buffer)


# ── WebSocket handlers ────────────────────────────────────────────────
async def ws_book_task(state: PairState, market: str, log: logging.Logger):
    """Subscribe to {spot|futures}.order_book (top 20). Reconnect forever
    with exponential backoff."""
    endpoint = _ws_endpoint(market)
    channel  = _book_channel(market)
    backoff = 1
    while True:
        try:
            async with websockets.connect(endpoint, ping_interval=20,
                                           ping_timeout=10) as ws:
                now = int(time.time())
                payload = {
                    "time":    now,
                    "channel": channel,
                    "event":   "subscribe",
                    "payload": _book_subscribe_payload(market, state.pair),
                }
                await ws.send(json.dumps(payload))
                log.info(f"[{market}] {state.pair} book subscribed")
                backoff = 1
                async for msg in ws:
                    data = json.loads(msg)
                    if data.get("event") != "update":
                        continue
                    r = data.get("result", {})
                    # Spot result: {"t":..., "s": pair, "bids":[[px,sz]], "asks":[[..]]}
                    # Futures   :  {"t":..., "contract": pair, "bids":[{"p":..,"s":..}], ...}
                    pair_field = r.get("s") or r.get("contract")
                    if pair_field and pair_field != state.pair:
                        continue
                    bids_raw = r.get("bids", [])
                    asks_raw = r.get("asks", [])
                    # Normalize both formats to [(price, size), ...]
                    def _norm(level):
                        if isinstance(level, dict):
                            return float(level.get("p", 0)), float(level.get("s", 0))
                        return float(level[0]), float(level[1])
                    state.book.bids = [_norm(x) for x in bids_raw]
                    state.book.asks = [_norm(x) for x in asks_raw]
                    state.book.last_update_ms = int(r.get("t", time.time() * 1000))
                    # OFI feeds on every book update (not just snapshot ticks)
                    if state.book.bids and state.book.asks:
                        bp, bs = state.book.bids[0]
                        ap, as_ = state.book.asks[0]
                        ev = state.ofi_state.update(bp, bs, ap, as_)
                        state.push_ofi(state.book.last_update_ms, ev)
        except Exception as e:
            log.warning(f"[{market}] {state.pair} book WS error: {e} — reconnect in {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


async def ws_trades_task(state: PairState, market: str, log: logging.Logger):
    endpoint = _ws_endpoint(market)
    channel  = _trades_channel(market)
    backoff = 1
    while True:
        try:
            async with websockets.connect(endpoint, ping_interval=20,
                                           ping_timeout=10) as ws:
                now = int(time.time())
                payload = {
                    "time":    now,
                    "channel": channel,
                    "event":   "subscribe",
                    "payload": [state.pair],
                }
                await ws.send(json.dumps(payload))
                log.info(f"[{market}] {state.pair} trades subscribed")
                backoff = 1
                async for msg in ws:
                    data = json.loads(msg)
                    if data.get("event") != "update":
                        continue
                    result = data.get("result")
                    # Spot returns single dict; futures returns list of dicts
                    rows = result if isinstance(result, list) else [result]
                    for r in rows:
                        if not isinstance(r, dict):
                            continue
                        # Spot: side="buy"|"sell", amount=str, price=str, create_time_ms=str
                        # Futures: size=signed float (+ buyer / − seller), price=str,
                        #          create_time_ms=str, contract=pair
                        if market == "futures":
                            sz_signed = float(r.get("size", 0))
                            if sz_signed == 0:
                                continue
                            side = "buy" if sz_signed > 0 else "sell"
                            sz   = abs(sz_signed)
                        else:
                            sz   = float(r.get("amount", 0))
                            side = r.get("side", "buy")
                            if sz <= 0:
                                continue
                        ct_ms = r.get("create_time_ms")
                        ts_ms = int(float(ct_ms)) if ct_ms else int(time.time() * 1000)
                        px   = float(r.get("price", 0))
                        if px > 0 and sz > 0:
                            state.tape.add(ts_ms, px, sz, side)
        except Exception as e:
            log.warning(f"[{market}] {state.pair} trades WS error: {e} — reconnect in {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


# ── derivatives polling (funding / OI / basis) ───────────────────────
async def poll_derivatives_task(states: Dict[str, "PairState"],
                                 log: logging.Logger,
                                 interval_s: int = 15):
    """Hit Gate.io REST every `interval_s` seconds for each pair's USDT
    perpetual snapshot. Funding + OI + mark_price go into PairState.deriv.
    No WebSocket needed — these values move on minutes-to-hours scales.

    Endpoints used:
      GET /futures/usdt/contract_stats?contract=BTC_USDT  (OI, tickers)
      GET /futures/usdt/funding_rate?contract=BTC_USDT    (funding history)

    Graceful degradation: if requests/library missing or API fails, the
    deriv fields stay NaN and downstream snapshots simply omit them.
    """
    if requests is None:
        log.warning("requests missing — derivatives poller disabled")
        return
    base = "https://api.gateio.ws/api/v4/futures/usdt"
    while True:
        for pair, st in states.items():
            try:
                r1 = requests.get(f"{base}/contracts/{pair}", timeout=5)
                if r1.status_code == 200:
                    j = r1.json()
                    st.deriv.mark_price      = float(j.get("mark_price", 0)    or 0) or float("nan")
                    st.deriv.index_price     = float(j.get("index_price", 0)   or 0) or float("nan")
                    st.deriv.funding_rate_8h = float(j.get("funding_rate", 0)  or 0) or 0.0
                r2 = requests.get(f"{base}/tickers?contract={pair}", timeout=5)
                if r2.status_code == 200:
                    j2 = r2.json()
                    if j2 and isinstance(j2, list):
                        t = j2[0]
                        # Gate.io returns `total_size` as OI in base-coin units
                        total_size = t.get("total_size")
                        if total_size is not None:
                            st.deriv.open_interest = float(total_size)
                st.deriv.last_refresh_ms = int(time.time() * 1000)
            except Exception as e:
                log.warning(f"{pair} deriv poll: {e}")
        await asyncio.sleep(interval_s)


# ── feature snapshot loop ─────────────────────────────────────────────
async def snapshot_task(states: Dict[str, PairState], snap_hz: float,
                        out_dir: Path, log: logging.Logger,
                        market: str = "spot"):
    interval = 1.0 / snap_hz
    log.info(f"snapshotting at {snap_hz} Hz → {out_dir}")
    last_hour = _hour_stamp()
    while True:
        now_ms = int(time.time() * 1000)
        for pair, st in states.items():
            if not st.book.bids or not st.book.asks:
                continue
            bid10, ask10 = st.book.top_n_notional(10)
            if bid10 + ask10 <= 0:
                continue
            depth_imbalance = bid10 / ask10 if ask10 > 0 else float("nan")
            tape_stats = st.tape.stats(now_ms)
            mp           = st.book.micro_price()
            slope_bid    = st.book.book_slope(10, "bid")
            slope_ask    = st.book.book_slope(10, "ask")
            ofi_30s      = st.ofi_sum_30s(now_ms)
            # Derivatives (NaN if poller hasn't run yet or API down)
            mark_px  = st.deriv.mark_price
            fund_8h  = st.deriv.funding_rate_8h
            oi       = st.deriv.open_interest
            basis_pct = (mark_px - st.book.mid) / st.book.mid \
                        if (not math.isnan(mark_px) and st.book.mid > 0) else float("nan")
            snap = dict(
                ts_ms           = now_ms,
                pair            = pair,
                market          = market,
                mid             = st.book.mid,
                micro_price     = mp,
                bid1            = st.book.bids[0][0],
                ask1            = st.book.asks[0][0],
                bid1_size       = st.book.bids[0][1],
                ask1_size       = st.book.asks[0][1],
                spread_pct      = st.book.spread_pct,
                bid10_notional  = bid10,
                ask10_notional  = ask10,
                depth_imbalance = depth_imbalance,
                book_slope_bid  = slope_bid,
                book_slope_ask  = slope_ask,
                delta_30s       = tape_stats["delta_30s"],
                trade_count_30s = tape_stats["trade_count"],
                trade_intensity = tape_stats["trade_intensity"],
                volatility_burst= tape_stats["volatility_burst"],
                ofi_30s         = ofi_30s,
                # ── derivatives / perpetual signals ──
                perp_mark       = mark_px,
                basis_pct       = basis_pct,
                funding_rate_8h = fund_8h,
                perp_oi         = oi,
                deriv_lag_ms    = (now_ms - st.deriv.last_refresh_ms)
                                   if st.deriv.last_refresh_ms else -1,
                book_lag_ms     = now_ms - st.book.last_update_ms,
            )
            # ── L99 regime classifier scoring (spot only) ──
            if _HAS_REGIME and st.regime is not None:
                try:
                    rs = compute_regime(
                        st.regime,
                        delta_30s      = tape_stats["delta_30s"],
                        spread_pct     = st.book.spread_pct,
                        bid10_notional = bid10,
                        ask10_notional = ask10,
                    )
                    snap.update(dict(
                        regime_score    = rs.score,
                        regime_label    = rs.label,
                        regime_layer1   = rs.layer1,
                        regime_layer2   = rs.layer2,
                        regime_layer3   = rs.layer3,
                        regime_layer4   = rs.layer4,
                        atr5m_ratio     = rs.atr5m_ratio,
                        range_accel     = rs.range_accel,
                        delta_strength  = rs.delta_strength,
                        delta_accel     = rs.delta_accel,
                        spread_stability= rs.spread_stability,
                        depth_density   = rs.depth_density,
                    ))
                except Exception as e:
                    log.warning(f"{pair} regime score: {e}")
            st.buffer.append(snap)

        # Hourly flush
        hr = _hour_stamp()
        if hr != last_hour:
            await flush_all(states, out_dir, last_hour, log)
            last_hour = hr
        await asyncio.sleep(interval)


def _hour_stamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d/%H")


async def flush_all(states: Dict[str, PairState], out_dir: Path,
                    hour_stamp: str, log: logging.Logger):
    """Write each pair's buffer to Parquet and clear it."""
    hr_dir = out_dir / hour_stamp
    hr_dir.mkdir(parents=True, exist_ok=True)
    for pair, st in states.items():
        if not st.buffer:
            continue
        df = pd.DataFrame(st.buffer)
        df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
        out_path = hr_dir / f"{pair}.parquet"
        pre_existing = out_path.exists()
        if pre_existing:
            try:
                existing = pq.read_table(out_path).to_pandas()
                df = pd.concat([existing, df], ignore_index=True)
            except Exception as e:
                log.warning(f"{pair} parquet re-merge failed: {e} — overwriting")
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, out_path, compression="zstd")
        log.info(f"flushed {pair}: +{len(st.buffer)} rows → {out_path} "
                 f"(total {len(df)}{' merged' if pre_existing else ''})")
        st.buffer.clear()


# ── main ─────────────────────────────────────────────────────────────
async def amain(args):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(message)s",
        stream=sys.stdout,
    )
    log = logging.getLogger("microstructure")

    states = {p: PairState(pair=p) for p in args.pairs}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Attach regime state per pair (L99 classifier) — only meaningful for spot
    # market right now since the classifier polls Gate.io spot 1m candles.
    if _HAS_REGIME and args.market == "spot":
        for p, st in states.items():
            st.regime = RegimeState(pair=p)
        log.info(f"L99 regime classifier ENABLED for {len(states)} pairs")
    elif _HAS_REGIME:
        log.info(f"L99 regime classifier disabled in --market={args.market} mode")

    tasks = []
    for pair, st in states.items():
        tasks.append(asyncio.create_task(ws_book_task(st, args.market, log)))
        tasks.append(asyncio.create_task(ws_trades_task(st, args.market, log)))
    tasks.append(asyncio.create_task(
        snapshot_task(states, args.snap_hz, out_dir, log, args.market)))
    # Derivatives REST poll only makes sense for the spot collector — it
    # gives spot a "what is the perp side doing?" view. Futures collector
    # IS the perp side; basis_pct/funding/oi columns will simply stay NaN.
    if args.market == "spot":
        tasks.append(asyncio.create_task(
            poll_derivatives_task(states, log, interval_s=args.deriv_poll_s)))

    # L99 OHLC refresh tasks (one per pair, every 30 s) — gated to spot market
    if _HAS_REGIME and args.market == "spot":
        for st in states.values():
            if st.regime is not None:
                tasks.append(asyncio.create_task(refresh_ohlc(st.regime, log)))

    # Graceful shutdown — flush buffers before exiting
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    def _sig(*_):
        if not stop.done(): stop.set_result(None)
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, _sig)

    log.info(f"collector running · pairs={args.pairs} · out={out_dir}")
    await stop
    log.info("shutdown requested — flushing buffers")
    for t in tasks:
        t.cancel()
    await flush_all(states, out_dir, _hour_stamp(), log)
    log.info("bye")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=DEFAULT_PAIRS)
    ap.add_argument("--out-dir", default="/var/log/microstructure")
    ap.add_argument("--market", choices=["spot", "futures"], default="spot",
                    help="Gate.io market — 'spot' uses public spot WS, "
                         "'futures' uses perpetual USDT WS (different endpoint, "
                         "different trade format, fee economics 5x better)")
    ap.add_argument("--snap-hz", type=float, default=1.0,
                    help="snapshot rate in Hz (1.0 = every 1s)")
    ap.add_argument("--deriv-poll-s", type=int, default=15,
                    help="derivatives REST poll interval (spot mode only)")
    args = ap.parse_args()
    asyncio.run(amain(args))


if __name__ == "__main__":
    main()
