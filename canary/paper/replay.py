"""Deterministic OFFLINE replay engine for the MA50W10 strategy.

INPUT  : a sequence of pre-built `Frame`s (timestamp + price + daily/weekly
         closes + candle ages). No network. No ccxt. No live executor.
OUTPUT : a `ReplayResult` carrying the closed-trade ledger + signal counters.

The replay treats the strategy module as a black box: it calls
`strategy_module.should_enter(...)` / `should_exit(...)` exactly as the
live executor does, with the same keyword arguments. This guarantees the
replay can never diverge from live signal logic without the divergence
showing up in the strategy module itself (which is SHA256-locked).

State machine: flat → long → flat. trades_today resets on UTC day rollover.
Cooldown is enforced between exit and next entry attempt.

NO position sizing innovation. NO new exit rules. NO new entry rules.
The replay engine is purely a host that calls the strategy primitives.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Frame:
    """One observation moment fed to the strategy."""
    ts: int                              # epoch seconds
    price: float
    daily_closes: List[float]
    weekly_closes: List[float]
    daily_latest_ts_ms: int              # for staleness check
    weekly_latest_ts_ms: int


@dataclass
class Trade:
    """A closed round-trip."""
    entry_ts: int
    entry_price: float
    exit_ts: int
    exit_price: float
    size_usdt: float
    pnl_usdt: float
    exit_reason: str                     # raw reason string from should_exit


@dataclass
class ReplayResult:
    trades: List[Trade] = field(default_factory=list)
    entry_signals: int = 0               # times should_enter returned True
    exit_signals: int = 0                # times should_exit returned True
    entry_vetoes: int = 0                # times should_enter returned False while flat
    hold_decisions: int = 0              # times should_exit returned False while long


def replay(frames: List[Frame], strategy_module) -> ReplayResult:
    """Step through `frames` in order, applying strategy signals.

    `strategy_module` must expose `should_enter`, `should_exit`, and
    `trade_size_usdt` with the same signatures as `canary_strategy`.
    """
    last_exit_ts = 0
    trades_today = 0
    current_day: Optional[int] = None
    open_position: Optional[dict] = None
    result = ReplayResult()

    for f in frames:
        day = f.ts // 86400
        if day != current_day:
            trades_today = 0
            current_day = day

        if open_position is None:
            seconds_since_last_exit = (f.ts - last_exit_ts) if last_exit_ts else 10**9
            ok, _reason = strategy_module.should_enter(
                current_price=f.price,
                daily_closes=f.daily_closes,
                weekly_closes=f.weekly_closes,
                daily_latest_ts_ms=f.daily_latest_ts_ms,
                weekly_latest_ts_ms=f.weekly_latest_ts_ms,
                seconds_since_last_exit=seconds_since_last_exit,
                trades_today=trades_today,
                have_open_position=False,
            )
            if ok:
                size = strategy_module.trade_size_usdt()
                open_position = {
                    "entry_ts": f.ts,
                    "entry_price": f.price,
                    "size_usdt": size,
                }
                result.entry_signals += 1
                trades_today += 1
            else:
                result.entry_vetoes += 1
        else:
            seconds_held = f.ts - open_position["entry_ts"]
            ok, reason = strategy_module.should_exit(
                current_price=f.price,
                daily_closes=f.daily_closes,
                weekly_closes=f.weekly_closes,
                daily_latest_ts_ms=f.daily_latest_ts_ms,
                weekly_latest_ts_ms=f.weekly_latest_ts_ms,
                seconds_held=seconds_held,
            )
            if ok:
                size = open_position["size_usdt"]
                base = size / open_position["entry_price"]
                pnl = (f.price - open_position["entry_price"]) * base
                result.trades.append(Trade(
                    entry_ts=open_position["entry_ts"],
                    entry_price=open_position["entry_price"],
                    exit_ts=f.ts,
                    exit_price=f.price,
                    size_usdt=size,
                    pnl_usdt=pnl,
                    exit_reason=reason,
                ))
                last_exit_ts = f.ts
                open_position = None
                result.exit_signals += 1
            else:
                result.hold_decisions += 1

    return result
