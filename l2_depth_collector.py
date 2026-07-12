#!/usr/bin/env python3
"""
L2 Depth Collector — focused 20-level orderbook ladder capture for D3
(liquidity vacuum burst) factor research.

Per /L99_NATIVE_ONLY_MODE directive (2026-05-02): no external providers,
exchange-native data only. Captures full L2 depth ladders that the existing
`microstructure_collector.py` (top-of-book aggregates) does NOT save.

Captures (per snapshot):
  - timestamp_ms
  - pair
  - bid_levels: [[price, size], ...] top 20
  - ask_levels: [[price, size], ...] top 20
  - mid_price
  - spread_bps
  - cum_bid_depth_5pct: cumulative bid notional within 5% of mid
  - cum_ask_depth_5pct: cumulative ask notional within 5% of mid
  - cum_bid_depth_1pct: same within 1% of mid
  - cum_ask_depth_1pct: same within 1% of mid

Why these features (D3 mechanism):
  Liquidity vacuum = sudden thinning of cumulative depth at multiple levels.
  Pre-vacuum ladder is "stacked"; vacuum bar shows orders pulled across
  levels; burst = forward |return| > threshold. The 5%/1% cumulative
  bands let us detect gradual vs cliff thinning.

Hard rules honored:
  - No live trading
  - No order placement
  - Public WebSocket only, no auth
  - No external providers
  - Capital remains 100% USDT

Output: parquet files at OUT_DIR/YYYY-MM-DD/HH/PAIR.parquet
Usage:  python3 l2_depth_collector.py [--pairs PAIR ...] [--out-dir DIR]
Deploy: systemd unit `l2-depth-collector.service` on VPS, restart on failure.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

_MISSING_DEPS: List[str] = []

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore[assignment]
    _MISSING_DEPS.append("websockets")

try:
    import pandas as pd
    import pyarrow as pa  # noqa: F401
    import pyarrow.parquet as pq  # noqa: F401
except ImportError:
    pd = None  # type: ignore[assignment]
    _MISSING_DEPS.append("pandas/pyarrow")


def _require_runtime_deps() -> None:
    """Called from main() / before any function that needs the optional
    deps. Lets tests import this module without crashing when the heavy
    runtime libs aren't installed."""
    if _MISSING_DEPS:
        print(f"pip install {' '.join(_MISSING_DEPS)}", file=sys.stderr)
        sys.exit(1)


GATEIO_WS = "wss://api.gateio.ws/ws/v4/"
DEFAULT_PAIRS = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]
DEFAULT_OUT = "/var/log/l2_depth"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
)
log = logging.getLogger("l2_depth")


@dataclass
class OrderBook:
    """Top-N snapshot mirror; updated from full-snapshot pushes."""
    pair: str
    bids: List[Tuple[float, float]] = field(default_factory=list)  # [(price, size)] desc
    asks: List[Tuple[float, float]] = field(default_factory=list)  # [(price, size)] asc
    last_update_ms: int = 0

    def apply_snapshot(self, msg: Dict) -> None:
        """Replace book with full snapshot from Gate.io order_book channel."""
        result = msg.get("result", {})
        bids_raw = result.get("bids", []) or []
        asks_raw = result.get("asks", []) or []
        # Each is [price_str, size_str]
        self.bids = [(float(p), float(s)) for p, s in bids_raw if float(s) > 0]
        self.asks = [(float(p), float(s)) for p, s in asks_raw if float(s) > 0]
        self.bids.sort(key=lambda x: -x[0])  # desc
        self.asks.sort(key=lambda x: x[0])   # asc
        self.last_update_ms = int(time.time() * 1000)

    def best_bid(self) -> Optional[float]:
        return self.bids[0][0] if self.bids else None

    def best_ask(self) -> Optional[float]:
        return self.asks[0][0] if self.asks else None

    def mid(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is None or ba is None:
            return None
        return (bb + ba) / 2.0

    def spread_bps(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is None or ba is None or bb <= 0:
            return None
        m = (bb + ba) / 2.0
        return (ba - bb) / m * 10000

    def cum_depth(self, side: str, band_pct: float) -> float:
        """Cumulative notional within `band_pct` of mid."""
        m = self.mid()
        if m is None:
            return 0.0
        cutoff = m * (1.0 - band_pct / 100.0) if side == "bid" else m * (1.0 + band_pct / 100.0)
        levels = self.bids if side == "bid" else self.asks
        total = 0.0
        for price, size in levels:
            if side == "bid" and price < cutoff:
                break
            if side == "ask" and price > cutoff:
                break
            total += price * size
        return total


@dataclass
class SnapshotBuffer:
    """In-memory buffer of snapshot rows; flushed hourly to parquet."""
    rows: List[Dict] = field(default_factory=list)

    def add(self, row: Dict) -> None:
        self.rows.append(row)

    def flush(self, out_dir: Path, pair: str) -> Optional[Path]:
        if not self.rows:
            return None
        # Use the first row's timestamp to determine bucket
        ts0_ms = self.rows[0]["ts_ms"]
        dt = datetime.fromtimestamp(ts0_ms / 1000.0, timezone.utc)
        dst_dir = out_dir / dt.strftime("%Y-%m-%d") / dt.strftime("%H")
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{pair}.parquet"

        df = pd.DataFrame(self.rows)
        # Convert list-typed columns (bid_levels / ask_levels) to JSON strings
        for col in ("bid_levels", "ask_levels"):
            if col in df.columns:
                df[col] = df[col].apply(lambda v: json.dumps(v) if v is not None else None)

        if dst.exists():
            existing = pd.read_parquet(dst)
            df = pd.concat([existing, df], ignore_index=True)
        df.to_parquet(dst, index=False)
        n = len(self.rows)
        self.rows.clear()
        return dst


def build_subscribe_payload(pair: str) -> Dict:
    """Subscribe to spot.order_book channel — top-20 snapshots, 100ms cadence."""
    return {
        "time": int(time.time()),
        "channel": "spot.order_book",
        "event": "subscribe",
        "payload": [pair, "20", "100ms"],
    }


def make_snapshot_row(pair: str, book: OrderBook) -> Optional[Dict]:
    if not book.bids or not book.asks:
        return None
    mid = book.mid()
    if mid is None:
        return None
    return {
        "ts_ms": book.last_update_ms,
        "pair": pair,
        "mid_price": mid,
        "spread_bps": book.spread_bps(),
        "best_bid": book.best_bid(),
        "best_ask": book.best_ask(),
        "bid_levels": [[p, s] for p, s in book.bids[:20]],
        "ask_levels": [[p, s] for p, s in book.asks[:20]],
        "cum_bid_depth_1pct": book.cum_depth("bid", 1.0),
        "cum_ask_depth_1pct": book.cum_depth("ask", 1.0),
        "cum_bid_depth_5pct": book.cum_depth("bid", 5.0),
        "cum_ask_depth_5pct": book.cum_depth("ask", 5.0),
    }


async def collect_pair(pair: str, out_dir: Path, snap_hz: float, stop: asyncio.Event) -> None:
    """One coroutine per pair: subscribe, maintain book, snapshot 1Hz, flush hourly."""
    book = OrderBook(pair=pair)
    buf = SnapshotBuffer()
    last_snap = 0.0
    last_flush_hour = -1
    backoff = 1.0

    while not stop.is_set():
        try:
            async with websockets.connect(GATEIO_WS, ping_interval=20, ping_timeout=20) as ws:
                payload = build_subscribe_payload(pair)
                await ws.send(json.dumps(payload))
                log.info(f"[{pair}] subscribed to spot.order_book")
                backoff = 1.0

                while not stop.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    except asyncio.TimeoutError:
                        log.warning(f"[{pair}] receive timeout; reconnecting")
                        break

                    msg = json.loads(raw)
                    if msg.get("event") in ("subscribe", "unsubscribe"):
                        continue
                    if msg.get("channel") != "spot.order_book":
                        continue
                    book.apply_snapshot(msg)

                    # 1Hz snapshot
                    now = time.time()
                    if now - last_snap >= 1.0 / snap_hz:
                        row = make_snapshot_row(pair, book)
                        if row is not None:
                            buf.add(row)
                        last_snap = now

                    # Hourly flush
                    cur_hour = datetime.now(timezone.utc).hour
                    if last_flush_hour == -1:
                        last_flush_hour = cur_hour
                    elif cur_hour != last_flush_hour:
                        dst = buf.flush(out_dir, pair)
                        if dst:
                            log.info(f"[{pair}] flushed → {dst}")
                        last_flush_hour = cur_hour

        except Exception as e:
            log.warning(f"[{pair}] WS error: {e}; backoff {backoff:.1f}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)

    # Final flush on shutdown
    dst = buf.flush(out_dir, pair)
    if dst:
        log.info(f"[{pair}] final flush → {dst}")


async def main_async(pairs: List[str], out_dir: Path, snap_hz: float) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stop = asyncio.Event()

    def shutdown(*_):
        log.info("shutdown signal; flushing")
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_event_loop().add_signal_handler(sig, shutdown)
        except NotImplementedError:
            # Windows
            signal.signal(sig, lambda *_: shutdown())

    tasks = [asyncio.create_task(collect_pair(p, out_dir, snap_hz, stop)) for p in pairs]
    await asyncio.gather(*tasks, return_exceptions=True)


def main() -> int:
    _require_runtime_deps()
    p = argparse.ArgumentParser(description="L2 Depth Collector — Gate.io spot")
    p.add_argument("--pairs", nargs="+", default=DEFAULT_PAIRS,
                   help="Trading pairs (default: 5 majors)")
    p.add_argument("--out-dir", default=DEFAULT_OUT,
                   help=f"Parquet output directory (default: {DEFAULT_OUT})")
    p.add_argument("--snap-hz", type=float, default=1.0,
                   help="Snapshot frequency Hz (default: 1.0)")
    args = p.parse_args()

    log.info(f"starting L2 depth collector | pairs={args.pairs} | out={args.out_dir}")
    asyncio.run(main_async(args.pairs, Path(args.out_dir), args.snap_hz))
    return 0


if __name__ == "__main__":
    sys.exit(main())
