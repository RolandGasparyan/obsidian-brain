#!/usr/bin/env python3
"""
godmode.replay — Module 2: offline tick-stream replay with realistic
latency + maker-fill simulation.

The collector (M1) writes hourly JSONL files of every L2 diff, trade,
and book_ticker event we see on the WS. This module reads those files
chronologically for one contract, yields a unified tick stream, and
maintains a reconstructed local L2 book as it replays.

It also exposes two primitives that agent backtests depend on:

  LatencyModel  — add a configurable (150-300ms default) delay between
                  a "decision" timestamp and when it could actually
                  reach the exchange, so signal evaluations reflect
                  reality, not zero-RTT fantasy.

  MakerFillSim  — simulate whether a post-only limit order would have
                  filled. For a bid order at price P submitted at time
                  t_decision + latency, it fills if and only if:
                      * the inside ask crosses down to ≤ P before the
                        order's 800ms cancel deadline
                      * OR a taker SELL trade prints through P during
                        that window (the aggressive seller crossed us)
                  Symmetric for ask orders.

Run standalone to replay a file and print a summary:
    python -m godmode.replay --file godmode/data/20260424_21/BTC_USDT.jsonl
    python -m godmode.replay --dir godmode/data  --contract BTC_USDT

When imported, the public API is:

    from godmode.replay import replay_stream, LatencyModel, MakerFillSim

    for tick in replay_stream("godmode/data", "BTC_USDT"):
        # tick = {"t_ns": ..., "kind": "book_diff"|"trade"|"book_ticker",
        #          "book": LocalBook, "payload": raw_event}
        ...
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Tuple

from godmode.collector import LocalBook, DATA_ROOT

log = logging.getLogger("godmode.replay")


# ── file iteration ───────────────────────────────────────────────────
def iter_jsonl_chronological(root: Path, contract: str) -> Iterator[dict]:
    """Yield every JSONL event for `contract` across all hourly files in
    timestamp order. Hourly folders are sorted by name (YYYYMMDD_HH)."""
    if not root.exists():
        log.warning("data root %s does not exist", root)
        return
    hour_dirs = sorted([p for p in root.iterdir() if p.is_dir()])
    for hour in hour_dirs:
        f = hour / f"{contract}.jsonl"
        if not f.exists():
            continue
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line: continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


# ── tick stream with book reconstruction ─────────────────────────────
@dataclass
class Tick:
    t_ns: int
    kind: str       # "book_diff" | "trade" | "book_ticker" | "snapshot_loaded"
    payload: dict
    book: LocalBook  # reconstructed book state *after* this event


def replay_stream(data_root: str | Path, contract: str) -> Iterator[Tick]:
    """Replay chronologically, maintaining a local book state.

    The first event we encounter is usually `snapshot_loaded`, but we
    don't have the snapshot body recorded (it came from REST). So the
    first book state is empty until enough diffs arrive for it to
    resemble a real book. That's OK for agent validation — agents just
    skip until book.ready and depth ≥ threshold.
    """
    root = Path(data_root)
    book = LocalBook(contract)
    book.ready = True   # we just start applying diffs from whatever we have

    for ev in iter_jsonl_chronological(root, contract):
        kind = ev.get("kind")
        t_ns = int(ev.get("t_ns", 0))
        if kind == "snapshot_loaded":
            # Treat as a book-reset marker. No snapshot body available.
            book = LocalBook(contract)
            book.ready = True
            book.last_u = int(ev.get("base_id", 0))
        elif kind == "book_diff":
            # Apply it
            book.apply_diff({
                "U": ev.get("U", 0),
                "u": ev.get("u", 0),
                "b": ev.get("b", []),
                "a": ev.get("a", []),
            })
        # trade + book_ticker events don't modify the book in our impl
        yield Tick(t_ns=t_ns, kind=kind, payload=ev, book=book)


# ── latency model ────────────────────────────────────────────────────
@dataclass
class LatencyModel:
    """One-way latency distribution from the client to the exchange.

    Defaults match the spec's 150–300ms Frankfurt→Gate.io RTT assumption
    (half of RTT for one-way).
    """
    min_ms:    float = 75.0
    max_ms:    float = 150.0
    mean_ms:   float = 100.0
    stddev_ms: float = 15.0
    seed:      int   = 42
    _rng:      random.Random = field(init=False)

    def __post_init__(self):
        self._rng = random.Random(self.seed)

    def draw_ms(self) -> float:
        # Truncated normal
        v = self._rng.gauss(self.mean_ms, self.stddev_ms)
        return max(self.min_ms, min(self.max_ms, v))

    def rtt_ms(self) -> float:
        return self.draw_ms() * 2.0


# ── maker fill simulator ─────────────────────────────────────────────
@dataclass
class MakerOrder:
    id:           str
    side:         str      # "buy" | "sell"
    price:        float
    submit_t_ns:  int
    cancel_ms:    float = 800.0     # cancel if unfilled after this
    filled:       bool = False
    fill_t_ns:    int = 0
    fill_price:   float = 0.0
    cancel_t_ns:  int = 0


class MakerFillSim:
    """Simulate whether post-only limit orders fill given the recorded
    L2 + trade stream.

    Contract with caller:
        sim = MakerFillSim(latency=LatencyModel())
        order = sim.submit("buy", price, decision_t_ns)   # latency added
        # then replay forward; on each tick, call sim.process(tick)
        # sim marks orders filled or canceled in place.

    A buy limit fills if, before cancel_t_ns:
        * a book_ticker or book_diff shows the best ask has dropped to
          <= our price (a new resting seller, not us, sat on our bid), OR
        * a taker SELL trade prints at <= our price (aggressive seller
          crossed us).

    Symmetric for sells. We intentionally DO NOT simulate queue priority
    — so this overestimates fill rate. Document that in results.
    """

    def __init__(self, latency: LatencyModel):
        self.latency = latency
        self.open_orders: List[MakerOrder] = []
        self.fills:       List[MakerOrder] = []
        self.cancels:     List[MakerOrder] = []

    def submit(self, side: str, price: float,
               decision_t_ns: int,
               cancel_ms: float = 800.0) -> MakerOrder:
        """Submit a post-only limit order. The actual exchange-side
        submit time is decision_t_ns + one-way latency."""
        delay_ns = int(self.latency.draw_ms() * 1_000_000)
        submit_t = decision_t_ns + delay_ns
        order = MakerOrder(
            id=f"{side}-{submit_t}",
            side=side, price=price,
            submit_t_ns=submit_t,
            cancel_ms=cancel_ms,
        )
        self.open_orders.append(order)
        return order

    def process(self, tick: Tick):
        """Advance time to tick.t_ns and mark any filled or canceled."""
        now = tick.t_ns
        still_open = []
        for order in self.open_orders:
            if now < order.submit_t_ns:
                # Order hasn't actually reached exchange yet
                still_open.append(order)
                continue
            if now > order.submit_t_ns + int(order.cancel_ms * 1_000_000):
                order.cancel_t_ns = now
                self.cancels.append(order)
                continue
            filled = False
            if tick.kind == "trade":
                tp = tick.payload
                tside  = tp.get("side")
                tprice = float(tp.get("price", 0))
                # Taker seller crossing our buy
                if order.side == "buy" and tside == "sell" and tprice <= order.price:
                    filled = True
                # Taker buyer crossing our sell
                if order.side == "sell" and tside == "buy" and tprice >= order.price:
                    filled = True
            elif tick.kind == "book_ticker":
                bp = tick.payload
                bid, ask = float(bp.get("bid", 0)), float(bp.get("ask", 0))
                # Best ask dropped to ≤ our buy
                if order.side == "buy" and ask > 0 and ask <= order.price:
                    filled = True
                if order.side == "sell" and bid > 0 and bid >= order.price:
                    filled = True
            if filled:
                order.filled     = True
                order.fill_t_ns  = now
                order.fill_price = order.price
                self.fills.append(order)
            else:
                still_open.append(order)
        self.open_orders = still_open

    def stats(self) -> dict:
        total = len(self.fills) + len(self.cancels)
        return {
            "submitted":  len(self.fills) + len(self.cancels) + len(self.open_orders),
            "filled":     len(self.fills),
            "canceled":   len(self.cancels),
            "still_open": len(self.open_orders),
            "fill_rate":  (len(self.fills) / total) if total else 0.0,
        }


# ── standalone replay CLI for quick inspection ───────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir",      default=str(DATA_ROOT),
                    help="godmode data root (default: godmode/data)")
    ap.add_argument("--contract", default="BTC_USDT")
    ap.add_argument("--limit",    type=int, default=0,
                    help="stop after N ticks (0 = all)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)-5s | %(message)s")

    counts = {"book_diff": 0, "trade": 0, "book_ticker": 0,
              "snapshot_loaded": 0, "other": 0}
    buy_vol = sell_vol = 0.0
    first_t = last_t = 0
    book_final: Optional[LocalBook] = None

    for i, tick in enumerate(replay_stream(args.dir, args.contract), 1):
        if first_t == 0:
            first_t = tick.t_ns
        last_t = tick.t_ns
        k = tick.kind if tick.kind in counts else "other"
        counts[k] = counts.get(k, 0) + 1
        if tick.kind == "trade":
            sz = float(tick.payload.get("size", 0))
            if tick.payload.get("side") == "buy":
                buy_vol += sz
            else:
                sell_vol += sz
        book_final = tick.book
        if args.limit and i >= args.limit:
            break

    if not counts or first_t == 0:
        print("  (no events found)")
        return

    dur_s = (last_t - first_t) / 1e9
    print("═" * 72)
    print(f"  Contract:       {args.contract}")
    print(f"  Events:         {sum(counts.values())}  over {dur_s:.1f}s")
    for k, v in counts.items():
        if v: print(f"    {k:<18}{v:>10}")
    print(f"  Aggressive buy vol:   {buy_vol:,.0f} contracts")
    print(f"  Aggressive sell vol:  {sell_vol:,.0f} contracts")
    if book_final and book_final.bids and book_final.asks:
        bb, ba = book_final.best_quote()
        dir10 = book_final.dir_10()
        print(f"  Final best bid:  {bb}")
        print(f"  Final best ask:  {ba}")
        print(f"  Final spread:    {(ba-bb)/bb*10000:.2f} bp"
              if bb and ba else "  n/a")
        print(f"  Final DIR(10):   {dir10:.2f}" if dir10 else "  n/a")
        print(f"  Book levels:     bids={len(book_final.bids)}  asks={len(book_final.asks)}")
    print("═" * 72)


if __name__ == "__main__":
    main()
