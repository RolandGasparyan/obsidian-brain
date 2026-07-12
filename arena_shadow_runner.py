#!/usr/bin/env python3
"""
arena_shadow_runner.py — Shadow Arena CLI Wrapper

🎮 PAPER-SAFE wrapper that enriches paper-arena.json with arena_features.json.
🛡 NEVER touches live execution. NEVER reads .api_key. NEVER opens exchange
   write sockets (only public REST for market data).

Usage:
    ./arena_shadow_runner.py --mode shadow --market real --execution paper \\
        --agents HUNTER,RISK,ALPHA,REGIME,EXECUTOR,RECOVERY,SKEPTIC,CHAMPION \\
        --enable-xp --enable-commentary --enable-rivalries \\
        --enable-weather --enable-boss-events --enable-crowd \\
        --feed terminal.json

What it does:
    1. Validates paper-safe env (refuses if TG_DISABLE_REAL_ORDERS != 1)
    2. Polls market data (terminal.json if present, else Gate.io public REST)
    3. Reads paper-arena.json if present (for agent state)
    4. Computes weather/boss/crowd via paper_battle.arena_features
    5. Writes runtime/arena_features.json every tick
    6. Exits cleanly on SIGTERM

What it does NOT do:
    - Replace paper-arena.service (paper_battle_engine.py keeps running)
    - Touch /root/canary/ or any live trading code
    - Modify agent decisions
    - Affect risk caps

Design: this is a SECONDARY layer that READS engine output and ADDS visual
state. The engine remains the single source of trading truth.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import statistics
import sys
import time
import urllib.request
import urllib.error
from collections import deque
from pathlib import Path
from typing import Any

# ── PATH SETUP ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "paper_battle"))

from arena_features import compute_arena_features  # noqa: E402

# ── HARD SAFETY GUARD ───────────────────────────────────────────────────────

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


TG_DISABLE_REAL_ORDERS = _env_int("TG_DISABLE_REAL_ORDERS", 1)
TG_PAPER_EXECUTION     = _env_int("TG_PAPER_EXECUTION", 1)
LIVE_ORDERS            = _env_int("LIVE_ORDERS", 0)

if TG_DISABLE_REAL_ORDERS != 1 or TG_PAPER_EXECUTION != 1 or LIVE_ORDERS != 0:
    sys.stderr.write(
        "❌ REFUSED: arena_shadow_runner.py is paper-safe only.\n"
        "   Required env: TG_DISABLE_REAL_ORDERS=1  TG_PAPER_EXECUTION=1  LIVE_ORDERS=0\n"
        f"   Got: TG_DISABLE_REAL_ORDERS={TG_DISABLE_REAL_ORDERS}  "
        f"TG_PAPER_EXECUTION={TG_PAPER_EXECUTION}  LIVE_ORDERS={LIVE_ORDERS}\n"
        "   See: governance/MICRO_LIVE_OPERATOR_CHECKLIST.md for the live-mode path.\n"
    )
    sys.exit(2)


# ── CONSTANTS ───────────────────────────────────────────────────────────────

PAIRS = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT", "XRP_USDT"]
SCAN_INTERVAL_SEC = 10

# Detect server vs local
_SERVER_TERMINAL  = Path("/var/www/ai-trading-championship/dist/api/battle/terminal.json")
_SERVER_PAPER_ARENA = Path("/var/www/ai-trading-championship/dist/api/battle/paper-arena.json")
RUNTIME_DIR = ROOT / "runtime"
RUNTIME_DIR.mkdir(exist_ok=True, parents=True)

OUTPUT_PATH = RUNTIME_DIR / "arena_features.json"
LATEST_PATH = RUNTIME_DIR / "arena_features_latest.json"
PID_FILE    = RUNTIME_DIR / "arena_shadow_runner.pid"

# Optional secondary publish path for nginx-served frontend consumption.
# Set ARENA_FEATURES_PUBLISH_PATH=/var/www/ai-trading-championship/dist/api/battle/arena-features.json
# on the VPS systemd service. On Mac dev, leave unset.
_PUBLISH = os.environ.get("ARENA_FEATURES_PUBLISH_PATH", "").strip()
PUBLISH_PATH = Path(_PUBLISH) if _PUBLISH else None

# Bayesian / macro state we maintain locally (computed each tick from market data)
# Keeps wrapper self-sufficient even if paper-arena.json doesn't expose these fields.


# ── MARKET DATA POLLING ─────────────────────────────────────────────────────


def fetch_ticker_pair(pair: str) -> dict | None:
    url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "arena-shadow-runner/1.0"})
        # URL is a static https:// literal built from a hardcoded base
        # (api.gateio.ws/api/v4/spot/tickers) with a pair string from
        # the trusted PAIRS constant. No user-controlled input, no
        # file:// or custom-scheme path. B310 risk is structural, not
        # exploitable here.
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
        if data:
            return data[0]
    except (urllib.error.URLError, ValueError, KeyError, TimeoutError):
        pass
    return None


def fetch_market_snapshot() -> dict[str, dict]:
    """Pull all 5 USDT pair tickers."""
    snapshot = {}
    for pair in PAIRS:
        t = fetch_ticker_pair(pair)
        if t:
            snapshot[pair] = t
    return snapshot


# ── DERIVED METRICS (simple Bayes/macro proxies) ───────────────────────────


def derive_signals(
    btc_window: deque,
    spread_window: deque,
    eth_window: deque,
    raw_tickers: dict,
) -> dict[str, Any]:
    """
    Compute lightweight macro_score, bayes_panic_pct, bayes_dominant, etc.
    Mirrors paper_battle/macro_layer.py + bayesian_regime.py logic but local
    to this runner (no cross-import dependency on running engine).
    """
    btc = list(btc_window)
    if len(btc) < 12:
        return {
            "vol_pct": 0.3, "macro_score": 50.0,
            "bayes_dominant": "Chop", "bayes_entropy": 1.0, "bayes_panic_pct": 16.7,
        }

    mean = statistics.fmean(btc)
    vol_pct = (statistics.pstdev(btc) / mean * 100.0) if mean else 0.3
    momentum_pct = ((btc[-1] - btc[-12]) / btc[-12] * 100.0) if btc[-12] else 0.0

    # Simple macro_score 0-100 (vol + spread + correlation surrogates)
    vol_pressure = min(100.0, max(0.0, (vol_pct - 0.10) / (0.80 - 0.10) * 100.0))
    spread_unstable = 50.0
    if len(spread_window) >= 6:
        sp = list(spread_window)
        sp_mean = statistics.fmean(sp)
        if sp_mean > 0:
            cv = statistics.pstdev(sp) / sp_mean
            spread_unstable = min(100.0, max(0.0, (cv - 0.2) / (1.0 - 0.2) * 100.0))
    macro_score = 0.5 * vol_pressure + 0.5 * spread_unstable
    macro_score = max(0.0, min(100.0, macro_score))

    # Simple Bayes: regime classification from vol + momentum
    if vol_pct >= 1.4 and momentum_pct < -0.6:
        dominant, panic_p, entropy = "Panic", 80.0, 0.4
    elif vol_pct >= 0.8:
        dominant, panic_p, entropy = "Expansion", 15.0, 0.9
    elif vol_pct < 0.15:
        dominant, panic_p, entropy = "Compression", 5.0, 0.7
    elif momentum_pct > 0.3:
        dominant, panic_p, entropy = "Trend", 5.0, 0.6
    elif momentum_pct > 0.2:
        dominant, panic_p, entropy = "Recovery", 8.0, 0.8
    else:
        dominant, panic_p, entropy = "Chop", 10.0, 1.0

    return {
        "vol_pct": vol_pct,
        "momentum_pct": momentum_pct,
        "macro_score": macro_score,
        "bayes_dominant": dominant,
        "bayes_panic_pct": panic_p,
        "bayes_entropy": entropy,
    }


# ── PAPER-ARENA.JSON READ (for agent leader/title state) ───────────────────


def read_paper_arena() -> dict[str, Any]:
    """
    Best-effort read of paper-arena.json from server-published location.
    Returns relevant subset for crowd reaction computation.
    """
    candidates = [
        _SERVER_PAPER_ARENA,
        ROOT / "runtime" / "paper-arena.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                data = json.loads(p.read_text())
                return {
                    "leader_agent": data.get("leaderboard", [{}])[0].get("name", "") if data.get("leaderboard") else "",
                    "recent_trades": data.get("recent_trades", [])[-5:],
                    "agents_count": len(data.get("agents", [])),
                    "tick": data.get("tick", 0),
                    "source": str(p),
                }
            except Exception:
                continue
    return {"leader_agent": "", "recent_trades": [], "agents_count": 0, "tick": 0, "source": "none"}


# ── ARGUMENT PARSING ────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Shadow Arena CLI wrapper (paper-safe)")
    p.add_argument("--mode", default="shadow", choices=["shadow"], help="(only shadow supported)")
    p.add_argument("--market", default="real", choices=["real"], help="(only real market supported)")
    p.add_argument("--execution", default="paper", choices=["paper"], help="(only paper supported)")
    p.add_argument("--agents", default="HUNTER,RISK,ALPHA,REGIME,EXECUTOR,RECOVERY,SKEPTIC,CHAMPION",
                   help="comma-separated agent roles (informational only — agents run in paper-arena.service)")
    p.add_argument("--enable-xp", action="store_true", help="XP system marker (paper-arena.service handles it)")
    p.add_argument("--enable-commentary", action="store_true", help="commentary marker")
    p.add_argument("--enable-rivalries", action="store_true", help="rivalry marker")
    p.add_argument("--enable-weather", action="store_true", default=True, help="market weather computation")
    p.add_argument("--enable-boss-events", action="store_true", default=True, help="boss event detection")
    p.add_argument("--enable-crowd", action="store_true", default=True, help="crowd reaction synthesis")
    p.add_argument("--feed", default="terminal.json", help="(informational — uses terminal.json if available)")
    p.add_argument("--scan-interval", type=int, default=SCAN_INTERVAL_SEC, help="seconds between feature computations")
    p.add_argument("--max-iterations", type=int, default=0, help="0 = infinite (default), N = run N iterations then exit")
    return p.parse_args()


# ── MAIN LOOP ───────────────────────────────────────────────────────────────


_STOP = False


def _handle_stop(*_: object) -> None:
    global _STOP
    _STOP = True


def run() -> int:
    args = parse_args()
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    PID_FILE.write_text(str(os.getpid()))

    print("⚔️ TRADINGGURU SHADOW ARENA — feature enricher")
    print(f"   mode               : {args.mode}")
    print(f"   market             : {args.market}")
    print(f"   execution          : {args.execution}")
    print(f"   agents             : {args.agents}")
    print(f"   scan_interval_sec  : {args.scan_interval}")
    print(f"   output             : {OUTPUT_PATH}")
    print("   LIVE_ORDERS=0      : ✓ HARD GUARDED")
    print(f"   features active    : weather={args.enable_weather} "
          f"boss={args.enable_boss_events} crowd={args.enable_crowd}")
    print(f"   PID                : {os.getpid()}")
    print()

    btc_window = deque(maxlen=60)
    eth_window = deque(maxlen=60)
    spread_window = deque(maxlen=60)
    last_boss: dict | None = None
    last_leader: str = ""
    tick_count = 0

    try:
        while not _STOP:
            if args.max_iterations and tick_count >= args.max_iterations:
                break
            tick_count += 1
            now_ts = time.time()

            # Fetch market snapshot
            snapshot = fetch_market_snapshot()
            if not snapshot:
                time.sleep(args.scan_interval)
                continue

            btc = snapshot.get("BTC_USDT")
            eth = snapshot.get("ETH_USDT")
            if not btc:
                time.sleep(args.scan_interval)
                continue

            try:
                btc_price = float(btc.get("last") or 0)
                btc_bid = float(btc.get("highest_bid") or btc_price)
                btc_ask = float(btc.get("lowest_ask") or btc_price)
                btc_window.append(btc_price)
                spread = ((btc_ask - btc_bid) / btc_price * 100.0) if btc_price else 0.0
                spread_window.append(spread)
                if eth:
                    eth_window.append(float(eth.get("last") or 0))
            except (TypeError, ValueError):
                time.sleep(args.scan_interval)
                continue

            # Derive signals
            sig = derive_signals(btc_window, spread_window, eth_window, snapshot)

            # Read paper-arena state for crowd context
            arena = read_paper_arena()
            leader_changed = bool(last_leader and arena["leader_agent"] and arena["leader_agent"] != last_leader)
            last_leader = arena["leader_agent"] or last_leader

            # Compute features
            features = compute_arena_features(
                btc_history=btc_window,
                spread_history=spread_window,
                vol_pct=sig["vol_pct"],
                bayes_dominant=sig["bayes_dominant"],
                bayes_entropy=sig["bayes_entropy"],
                bayes_panic_pct=sig["bayes_panic_pct"],
                macro_score=sig["macro_score"],
                recent_trades=arena["recent_trades"],
                leader_changed=leader_changed,
                title_defended_or_lost=False,  # TODO: read from paper-arena.json title events
                last_boss_event=last_boss,
                avg_realized_r=0.0,
                now_ts=now_ts,
            )

            # Update boss state if new event triggered
            if features["boss_event"]:
                last_boss = features["boss_event"]

            # Enrich with metadata
            features.update({
                "tick": tick_count,
                "btc_price": btc_price,
                "btc_spread_pct": round(spread, 5),
                "agent_count_paper_arena": arena["agents_count"],
                "current_leader": arena["leader_agent"],
                "leader_changed_this_tick": leader_changed,
                "runner_version": "arena-shadow-1.0",
                "tg_disable_real_orders": True,
                "tg_paper_execution": True,
            })

            # Write outputs
            payload = json.dumps(features, indent=2)
            OUTPUT_PATH.write_text(payload)
            LATEST_PATH.write_text(payload)
            # Optional secondary publish (e.g., nginx-served public location)
            if PUBLISH_PATH is not None:
                try:
                    PUBLISH_PATH.parent.mkdir(parents=True, exist_ok=True)
                    PUBLISH_PATH.write_text(payload)
                except OSError as e:
                    if tick_count <= 2:  # log only first 2 ticks to avoid spam
                        print(f"  ⚠ publish to {PUBLISH_PATH} failed: {e}")

            # Heartbeat output
            if tick_count % 6 == 0 or features["boss_event"]:
                weather = features["market_weather"]
                crowd = features["crowd_reaction"]
                boss_marker = f" BOSS={features['boss_event']['type']}" if features["boss_event"] else ""
                print(f"  ⚔️ tick={tick_count} BTC=${btc_price:,.2f} "
                      f"weather={weather['state']}({weather['intensity']:.2f}) "
                      f"crowd={crowd['level']} leader={arena['leader_agent'] or 'none'}{boss_marker}")

            time.sleep(args.scan_interval)

    finally:
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except OSError:
                pass
        print()
        print(f"⚔️ arena_shadow_runner stopped after {tick_count} ticks")
        print(f"  last output: {OUTPUT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(run())
