"""
Deterministic offline replay test for the MA50W10 strategy.

Loads canary/paper/fixtures/synthetic_btc_trend.json, drives it through
canary/paper/replay.py against the locked canary_strategy module, and
asserts the resulting trade ledger matches the expected outcome.

No network. No ccxt. No live executor. Pure strategy → replay → assert.

Compatible with `pytest` (auto-discovered by CI) AND standalone:
    python3 canary/tests/test_paper_replay.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

try:
    import pytest  # noqa: F401
except ImportError:
    pytest = None

HERE = Path(__file__).resolve().parent
CANARY = HERE.parent
STRATEGY_PY = CANARY / "canary_strategy.py"
REPLAY_PY = CANARY / "paper" / "replay.py"
FIXTURE = CANARY / "paper" / "fixtures" / "synthetic_btc_trend.json"


def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass(*) can resolve cls.__module__ for
    # string-annotation introspection (PEP 563 / `from __future__ import annotations`).
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _build_frames(fixture: dict, strategy_mod):
    """Materialize fixture into replay.Frame objects with timestamps anchored to now."""
    replay = _load_by_path("canary_paper_replay", REPLAY_PY)
    now = int(time.time())
    daily = list(fixture["daily_history"])
    weekly = list(fixture["weekly_history"])
    frames = []
    for f in fixture["frames"]:
        ts = now - int(f["minutes_ago"]) * 60
        daily.extend(f.get("daily_append", []))
        weekly.extend(f.get("weekly_append", []))
        frames.append(replay.Frame(
            ts=ts,
            price=float(f["price"]),
            daily_closes=list(daily),
            weekly_closes=list(weekly),
            daily_latest_ts_ms=ts * 1000,
            weekly_latest_ts_ms=ts * 1000,
        ))
    return replay, frames


def test_fixture_runs_deterministically():
    """Run the synthetic_btc_trend fixture; ledger must match fixture['expected']."""
    fixture = json.loads(FIXTURE.read_text())
    strat = _load_by_path("canary_strategy", STRATEGY_PY)
    replay_mod, frames = _build_frames(fixture, strat)
    result = replay_mod.replay(frames, strat)

    exp = fixture["expected"]
    assert len(result.trades) == exp["trades_count"], \
        f"expected {exp['trades_count']} trade(s), got {len(result.trades)}"

    trade = result.trades[0]
    assert abs(trade.entry_price - exp["entry_price"]) < 1e-9, \
        f"entry_price {trade.entry_price} != {exp['entry_price']}"
    assert abs(trade.exit_price - exp["exit_price"]) < 1e-9, \
        f"exit_price {trade.exit_price} != {exp['exit_price']}"
    assert abs(trade.size_usdt - exp["size_usdt"]) < 1e-9, \
        f"size_usdt {trade.size_usdt} != {exp['size_usdt']}"
    assert trade.exit_reason.startswith(exp["exit_reason_prefix"]), \
        f"exit_reason {trade.exit_reason!r} does not start with {exp['exit_reason_prefix']!r}"
    expected_pnl = exp["pnl_pct_of_size"] * exp["size_usdt"]
    assert abs(trade.pnl_usdt - expected_pnl) < 1e-6, \
        f"pnl_usdt {trade.pnl_usdt} != expected {expected_pnl}"


def test_replay_counters_match_frame_count():
    """Each frame must be accounted for exactly once across entry/exit/veto/hold counters."""
    fixture = json.loads(FIXTURE.read_text())
    strat = _load_by_path("canary_strategy", STRATEGY_PY)
    replay_mod, frames = _build_frames(fixture, strat)
    result = replay_mod.replay(frames, strat)
    total = (result.entry_signals + result.entry_vetoes
             + result.exit_signals + result.hold_decisions)
    assert total == len(frames), \
        f"signal counters {total} != frame count {len(frames)}"


def test_replay_with_flat_market_takes_no_trade():
    """A frame stream where price never exceeds SMA50/SMA10 must produce 0 trades."""
    strat = _load_by_path("canary_strategy", STRATEGY_PY)
    replay_mod = _load_by_path("canary_paper_replay", REPLAY_PY)
    now = int(time.time())
    flat_daily = [100.0] * 50         # SMA50 = 100
    flat_weekly = [100.0] * 10        # W_SMA10 = 100
    frames = [
        replay_mod.Frame(
            ts=now - 60 * 60,
            price=95.0,                # below SMA50 and W_SMA10 → no enter
            daily_closes=flat_daily,
            weekly_closes=flat_weekly,
            daily_latest_ts_ms=(now - 60 * 60) * 1000,
            weekly_latest_ts_ms=(now - 60 * 60) * 1000,
        ),
    ]
    result = replay_mod.replay(frames, strat)
    assert len(result.trades) == 0
    assert result.entry_signals == 0
    assert result.entry_vetoes == 1


def test_replay_respects_stale_ohlcv_guard():
    """If daily candle is too old (> 26h), should_enter must veto — no trade."""
    strat = _load_by_path("canary_strategy", STRATEGY_PY)
    replay_mod = _load_by_path("canary_paper_replay", REPLAY_PY)
    now = int(time.time())
    # Conditions favour an entry, BUT daily timestamp is 30h old.
    daily = [100.0] * 49 + [150.0]
    weekly = [100.0] * 9 + [130.0]
    stale_daily_ms = (now - 30 * 3600) * 1000
    frames = [
        replay_mod.Frame(
            ts=now,
            price=145.0,
            daily_closes=daily,
            weekly_closes=weekly,
            daily_latest_ts_ms=stale_daily_ms,
            weekly_latest_ts_ms=now * 1000,
        ),
    ]
    result = replay_mod.replay(frames, strat)
    assert len(result.trades) == 0, "stale daily must veto entry"
    assert result.entry_signals == 0
    assert result.entry_vetoes == 1


# ---- standalone runner ----------------------------------------------------

def _main():
    tests = [
        ("fixture runs deterministically", test_fixture_runs_deterministically),
        ("counters sum to frame count", test_replay_counters_match_frame_count),
        ("flat market → no trade", test_replay_with_flat_market_takes_no_trade),
        ("stale OHLCV vetoes entry", test_replay_respects_stale_ohlcv_guard),
    ]
    passes = fails = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passes += 1
        except AssertionError as e:
            print(f"  FAIL  {name} — {e}")
            fails += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name} — {type(e).__name__}: {e}")
            fails += 1
    print(f"\nRESULT: {passes}/{passes + fails} passed · {fails} failed")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    _main()
