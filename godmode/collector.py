#!/usr/bin/env python3
"""
godmode.collector — Module 1: Gate.io USDT Futures L2 book + trade-tape
collector.

Connects to `wss://fx-ws.gateio.ws/v4/ws/usdt`, subscribes to the
`futures.order_book_update`, `futures.trades`, and `futures.book_ticker`
channels for one or more perpetual contracts, maintains a local L2 book
seeded from the REST snapshot, detects sequence gaps, and logs every
event to JSONL files under godmode/data/.

Also emits a rolling "microstructure snapshot" — DIR (Depth Imbalance
Ratio), STD (aggressive buy minus sell volume, 30s rolling), best
bid/ask — every 2 seconds so a monitoring dashboard can consume it
without touching the underlying tick bus.

No trading is done here. This module is pure data acquisition. Agents
M3a-M3d read the recorded files (via godmode.replay) or subscribe to
the in-process tick callbacks.

Dependencies:
    pip install websockets aiohttp

Run:
    python -m godmode.collector --contracts BTC_USDT
    python -m godmode.collector --contracts BTC_USDT ETH_USDT --verbose

Stop with Ctrl-C — graceful shutdown flushes pending file writes.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import aiohttp
    import websockets
except ImportError as _e:
    # Optional runtime deps. Allow this module to be imported by tests /
    # tools that don't actually exercise the WebSocket / HTTP paths. Code
    # that needs them will hit AttributeError on `aiohttp.None` later, or
    # callers can check `RUNTIME_DEPS_OK`.
    aiohttp = None  # type: ignore[assignment]
    websockets = None  # type: ignore[assignment]
    RUNTIME_DEPS_OK = False
    _RUNTIME_DEP_ERROR = str(_e)
else:
    RUNTIME_DEPS_OK = True
    _RUNTIME_DEP_ERROR = ""

log = logging.getLogger("godmode.collector")

# ── endpoints ─────────────────────────────────────────────────────────
WS_URL         = "wss://fx-ws.gateio.ws/v4/ws/usdt"
REST_BOOK_URL  = "https://api.gateio.ws/api/v4/futures/usdt/order_book"

# Storage under repo: godmode/data/<date>/<contract>.jsonl
DATA_ROOT = Path(__file__).resolve().parent / "data"
SNAPSHOT_PATH = DATA_ROOT / "microstructure_snapshot.json"  # live-readable

# ── L2 book ──────────────────────────────────────────────────────────
class LocalBook:
    """Single-contract L2 book maintained from diff updates.

    `bids` / `asks` are dicts price → size (floats), sorted on-demand.
    `last_u` is the last update id we've applied; used to detect gaps.
    """
    __slots__ = ("contract", "bids", "asks", "last_u", "ready")

    def __init__(self, contract: str):
        self.contract = contract
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        self.last_u: int = 0
        self.ready: bool = False

    def apply_snapshot(self, snapshot: dict):
        self.bids = {float(p): float(s) for p, s in
                     ((x["p"], x["s"]) for x in snapshot.get("bids", []))}
        self.asks = {float(p): float(s) for p, s in
                     ((x["p"], x["s"]) for x in snapshot.get("asks", []))}
        self.last_u = int(snapshot.get("id", 0))
        self.ready = True

    def apply_diff(self, msg: dict) -> str:
        """Apply a futures.order_book_update notification.

        Returns:
            "ok"       — applied cleanly
            "stale"    — older than current book, ignored
            "gap"      — sequence gap, book must be re-snapshotted
        """
        U = int(msg["U"])
        u = int(msg["u"])
        if u < self.last_u:
            return "stale"
        if self.last_u > 0 and U > self.last_u + 1:
            return "gap"
        # Sizes are ABSOLUTE, not deltas. 0 => delete level.
        for p, s in ((x["p"], x["s"]) for x in msg.get("b", [])):
            price, size = float(p), float(s)
            if size == 0.0:
                self.bids.pop(price, None)
            else:
                self.bids[price] = size
        for p, s in ((x["p"], x["s"]) for x in msg.get("a", [])):
            price, size = float(p), float(s)
            if size == 0.0:
                self.asks.pop(price, None)
            else:
                self.asks[price] = size
        self.last_u = u
        return "ok"

    def top(self, depth: int = 10) -> Tuple[List[Tuple[float, float]],
                                            List[Tuple[float, float]]]:
        """Return top-N bids (descending price) and asks (ascending price)."""
        bids_sorted = sorted(self.bids.items(), key=lambda x: -x[0])[:depth]
        asks_sorted = sorted(self.asks.items(), key=lambda x:  x[0])[:depth]
        return bids_sorted, asks_sorted

    def dir_10(self) -> Optional[float]:
        """Depth Imbalance Ratio on top-10 levels."""
        bids, asks = self.top(10)
        bv = sum(s for _, s in bids)
        av = sum(s for _, s in asks)
        if av <= 0:
            return None
        return bv / av

    def best_quote(self) -> Tuple[Optional[float], Optional[float]]:
        if not self.bids or not self.asks:
            return None, None
        return max(self.bids), min(self.asks)


# ── JSONL writer (one file per contract per UTC hour) ────────────────
class HourlyJsonl:
    def __init__(self, contract: str):
        self.contract = contract
        self._fh = None
        self._hour_key = ""

    def _target(self) -> Path:
        now = time.gmtime()
        hour_key = f"{now.tm_year:04d}{now.tm_mon:02d}{now.tm_mday:02d}_{now.tm_hour:02d}"
        return DATA_ROOT / hour_key / f"{self.contract}.jsonl"

    def write(self, record: dict):
        path = self._target()
        key = str(path)
        if key != self._hour_key:
            if self._fh is not None:
                self._fh.close()
            path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(path, "a", buffering=1)  # line-buffered
            self._hour_key = key
        self._fh.write(json.dumps(record, separators=(",", ":")))
        self._fh.write("\n")

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None


# ── derived-signal rolling state ─────────────────────────────────────
class MicrostructureState:
    """Per-contract rolling state for DIR / STD / tape / quote snapshot."""

    def __init__(self):
        self.aggr_buy_30s   = deque()   # (t_ns, size)
        self.aggr_sell_30s  = deque()
        self.baseline_delta = deque(maxlen=600)  # 10-min baseline for STD Z

    def record_trade(self, t_ns: int, side: str, size: float):
        if side == "buy":
            self.aggr_buy_30s.append((t_ns, size))
        else:
            self.aggr_sell_30s.append((t_ns, size))
        cutoff = t_ns - 30_000_000_000  # 30 seconds in ns
        while self.aggr_buy_30s  and self.aggr_buy_30s[0][0]  < cutoff:
            self.aggr_buy_30s.popleft()
        while self.aggr_sell_30s and self.aggr_sell_30s[0][0] < cutoff:
            self.aggr_sell_30s.popleft()

    def std_30s(self) -> float:
        b = sum(s for _, s in self.aggr_buy_30s)
        a = sum(s for _, s in self.aggr_sell_30s)
        return b - a

    def update_baseline(self):
        self.baseline_delta.append(self.std_30s())

    def std_z(self) -> Optional[float]:
        if len(self.baseline_delta) < 30:
            return None
        n = len(self.baseline_delta)
        mu = sum(self.baseline_delta) / n
        var = sum((x - mu) ** 2 for x in self.baseline_delta) / max(1, n - 1)
        sd = var ** 0.5
        if sd == 0:
            return None
        return (self.std_30s() - mu) / sd


# ── REST snapshot bootstrap ──────────────────────────────────────────
async def fetch_rest_snapshot(session: aiohttp.ClientSession,
                              contract: str, limit: int = 100) -> dict:
    params = {"contract": contract, "limit": str(limit), "with_id": "true"}
    async with session.get(REST_BOOK_URL, params=params, timeout=10) as r:
        r.raise_for_status()
        return await r.json()


# ── main per-contract loop ───────────────────────────────────────────
async def run_contract(contract: str, stop_evt: asyncio.Event,
                       verbose: bool = False):
    book   = LocalBook(contract)
    mstate = MicrostructureState()
    writer = HourlyJsonl(contract)

    backoff = 1.0
    # Buffer of diff notifications while waiting for the REST snapshot
    pending: deque = deque(maxlen=2000)

    while not stop_evt.is_set():
        try:
            log.info("[%s] ws connect", contract)
            async with websockets.connect(
                WS_URL,
                ping_interval=20, ping_timeout=20,
                max_size=16 * 1024 * 1024,
            ) as ws:
                backoff = 1.0

                # Subscribe to the 3 channels
                t = int(time.time())
                subs = [
                    {"time": t, "channel": "futures.order_book_update",
                     "event": "subscribe",
                     "payload": [contract, "100ms", "100"]},
                    {"time": t, "channel": "futures.trades",
                     "event": "subscribe", "payload": [contract]},
                    {"time": t, "channel": "futures.book_ticker",
                     "event": "subscribe", "payload": [contract]},
                ]
                for s in subs:
                    await ws.send(json.dumps(s))

                # Reset book state; need a fresh REST snapshot after resubscribe
                book.ready = False
                pending.clear()

                async with aiohttp.ClientSession() as session:
                    snap = await fetch_rest_snapshot(session, contract)
                    book.apply_snapshot(snap)
                    base_id = book.last_u
                    log.info("[%s] REST snapshot base_id=%d",
                             contract, base_id)

                writer.write({"t_ns": time.time_ns(),
                              "kind": "snapshot_loaded",
                              "base_id": base_id})

                last_baseline_update = 0.0
                last_emit            = 0.0

                async for raw in ws:
                    if stop_evt.is_set():
                        break
                    now_ns = time.time_ns()
                    now_s  = now_ns / 1e9
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue

                    ch = msg.get("channel", "")
                    ev = msg.get("event", "")
                    if ev in ("subscribe", "unsubscribe"):
                        if msg.get("error"):
                            log.error("[%s] sub error: %s",
                                      contract, msg["error"])
                        continue
                    if ev != "update":
                        continue
                    result = msg.get("result")
                    if result is None:
                        continue

                    if ch == "futures.order_book_update":
                        # Reconciliation: ignore notifications with u < base_id
                        u = int(result.get("u", 0))
                        U = int(result.get("U", 0))
                        if not book.ready or u <= base_id:
                            # Book not seeded yet or update stale; buffer just in case
                            continue
                        status = book.apply_diff(result)
                        if status == "gap":
                            log.warning("[%s] sequence GAP at u=%d — "
                                        "re-snapshot", contract, u)
                            break   # break async-for → outer reconnect loop
                        writer.write({"t_ns": now_ns, "kind": "book_diff",
                                      "U": U, "u": u,
                                      "b": result.get("b", []),
                                      "a": result.get("a", [])})

                    elif ch == "futures.trades":
                        # result is a list of trade dicts
                        for tr in result if isinstance(result, list) else [result]:
                            # Gate.io trade: {"size": float, "id": int, "create_time_ms": int,
                            #                  "price": str, "contract": str}
                            # Aggressor side inferred from size sign: positive=buy, negative=sell
                            try:
                                size = float(tr.get("size", 0))
                            except Exception:
                                continue
                            side = "buy" if size > 0 else "sell"
                            abs_size = abs(size)
                            mstate.record_trade(now_ns, side, abs_size)
                            writer.write({"t_ns": now_ns, "kind": "trade",
                                          "side": side, "price": float(tr.get("price", 0)),
                                          "size": abs_size,
                                          "id": tr.get("id")})

                    elif ch == "futures.book_ticker":
                        writer.write({"t_ns": now_ns, "kind": "book_ticker",
                                      "bid": float(result.get("b", 0)),
                                      "ask": float(result.get("a", 0)),
                                      "bs":  float(result.get("B", 0)),
                                      "as_": float(result.get("A", 0))})

                    # Keep baseline + snapshot fresh at 2Hz
                    if now_s - last_baseline_update > 1.0:
                        mstate.update_baseline()
                        last_baseline_update = now_s
                    if now_s - last_emit > 2.0:
                        _emit_snapshot(contract, book, mstate)
                        last_emit = now_s
                        if verbose:
                            dir_ = book.dir_10()
                            bb, ba = book.best_quote()
                            log.info("[%s] DIR=%s spread=%s STD_Z=%s",
                                     contract,
                                     f"{dir_:.2f}" if dir_ else "n/a",
                                     f"{(ba-bb)/bb*10000:.1f}bp"
                                         if bb and ba else "n/a",
                                     f"{mstate.std_z():+.2f}"
                                         if mstate.std_z() is not None else "n/a")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("[%s] ws error: %s — reconnect in %.1fs",
                        contract, e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(30.0, backoff * 2)

    writer.close()


def _emit_snapshot(contract: str, book: LocalBook,
                   m: MicrostructureState):
    """Write a small live-readable JSON blob with derived signals."""
    bb, ba = book.best_quote()
    spread_bp = None
    if bb and ba and bb > 0:
        spread_bp = (ba - bb) / bb * 10000
    record = {
        "contract": contract,
        "t_ns":     time.time_ns(),
        "bid":      bb,
        "ask":      ba,
        "spread_bp": spread_bp,
        "dir_10":   book.dir_10(),
        "std_30s":  m.std_30s(),
        "std_z":    m.std_z(),
        "n_trades_buy_30s":  len(m.aggr_buy_30s),
        "n_trades_sell_30s": len(m.aggr_sell_30s),
        "book_last_u": book.last_u,
    }
    path = DATA_ROOT / f"snapshot_{contract}.json"
    tmp  = path.with_suffix(".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(record, f)
    os.replace(tmp, path)


# ── entry ────────────────────────────────────────────────────────────
async def main_async(contracts: List[str], verbose: bool):
    stop_evt = asyncio.Event()

    def _sig(*_):
        log.info("shutdown signal — stopping collectors")
        stop_evt.set()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_running_loop().add_signal_handler(s, _sig)
        except NotImplementedError:
            pass  # Windows

    tasks = [asyncio.create_task(run_contract(c, stop_evt, verbose))
             for c in contracts]
    await asyncio.gather(*tasks, return_exceptions=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contracts", nargs="+", default=["BTC_USDT"],
                    help="Gate.io perpetual contracts (default BTC_USDT)")
    ap.add_argument("--verbose", action="store_true",
                    help="Print derived DIR/STD snapshot lines every 2s")
    args = ap.parse_args()

    logging.basicConfig(
        level  = logging.INFO,
        format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    log.info("godmode.collector starting on %s", args.contracts)
    log.info("data dir: %s", DATA_ROOT)

    asyncio.run(main_async(args.contracts, args.verbose))


if __name__ == "__main__":
    main()
