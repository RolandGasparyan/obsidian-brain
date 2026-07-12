#!/usr/bin/env python3
"""
replay_collector.py — main async service entry · captures arena history

🛡 PAPER-SAFE · READ-ONLY of paper-arena.json + arena-features.json + terminal.json.
🛡 NEVER reads .api_key · NEVER opens exchange sockets · NEVER writes to /root/canary/.
🛡 Refuses to start unless TG_PAPER_EXECUTION=1 + TG_DISABLE_REAL_ORDERS=1 + LIVE_ORDERS=0.

Lifecycle:
  1. Polls 3 JSON sources every SCAN_INTERVAL_SEC
  2. Builds a snapshot dict combining their state
  3. Appends to gzipped JSONL via replay_storage
  4. Periodically (every 30s) calls replay_api.compact_outputs()
  5. SIGTERM → clean shutdown · finalizes current file
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

# ── Path setup ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from replay_utils import now_ts, utc_iso, safe_get
from replay_storage import storage_from_env
from replay_events import detect_events, ReplayEvent


# ── Hard safety guard ───────────────────────────────────────────────────────


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


TG_PAPER_EXECUTION     = _env_int("TG_PAPER_EXECUTION", 1)
TG_DISABLE_REAL_ORDERS = _env_int("TG_DISABLE_REAL_ORDERS", 1)
LIVE_ORDERS            = _env_int("LIVE_ORDERS", 0)

if TG_PAPER_EXECUTION != 1 or TG_DISABLE_REAL_ORDERS != 1 or LIVE_ORDERS != 0:
    sys.stderr.write(
        "❌ REFUSED: replay_collector.py is paper-safe only.\n"
        "   Required: TG_PAPER_EXECUTION=1  TG_DISABLE_REAL_ORDERS=1  LIVE_ORDERS=0\n"
        "   This service is READ-ONLY · NEVER touches Layer 1 code or .api_key.\n"
    )
    sys.exit(2)


# ── Constants ──────────────────────────────────────────────────────────────

SCAN_INTERVAL_SEC = _env_int("REPLAY_SCAN_INTERVAL_SEC", 10)
COMPACT_INTERVAL_SEC = _env_int("REPLAY_COMPACT_INTERVAL_SEC", 30)
DEFAULT_SNAPSHOTS_DIR = ROOT / "snapshots"

# JSON source candidates (server-published nginx paths · local-dev fallback)
PAPER_ARENA_CANDIDATES = [
    Path("/var/www/ai-trading-championship/dist/api/battle/paper-arena.json"),
    ROOT.parent / "runtime" / "paper-arena.json",
]
ARENA_FEATURES_CANDIDATES = [
    Path("/var/www/ai-trading-championship/dist/api/battle/arena-features.json"),
    ROOT.parent / "runtime" / "arena_features.json",
]
TERMINAL_CANDIDATES = [
    Path("/var/www/ai-trading-championship/dist/api/battle/terminal.json"),
    ROOT.parent / "runtime" / "terminal.json",
]


# ── JSON source readers ─────────────────────────────────────────────────────


def _read_first(paths: list[Path]) -> dict[str, Any]:
    for p in paths:
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                continue
    return {}


def fetch_arena_state() -> dict[str, Any]:
    return _read_first(PAPER_ARENA_CANDIDATES)


def fetch_features_state() -> dict[str, Any]:
    return _read_first(ARENA_FEATURES_CANDIDATES)


def fetch_terminal_state() -> dict[str, Any]:
    return _read_first(TERMINAL_CANDIDATES)


# ── Snapshot builder ────────────────────────────────────────────────────────


def build_snapshot(
    arena: dict, features: dict, terminal: dict,
    prev_xp: dict[str, int] | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    """
    Combine 3 source JSONs into one snapshot.
    Returns (snapshot, new_xp_map) — caller persists xp_map across ticks for delta tracking.
    """
    t = now_ts()
    leaderboard_src = arena.get("agents") or arena.get("leaderboard") or []
    leaderboard = []
    new_xp = {}
    xp_delta = {}

    for entry in leaderboard_src[:16]:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("full_name")
                or entry.get("name")
                or entry.get("character_name")
                or entry.get("codename")
                or entry.get("label")
                or entry.get("role")
                or "?")
        xp = entry.get("xp", entry.get("level_xp", 0)) or 0
        leaderboard.append({
            "name":  name,
            "role":  entry.get("role") or entry.get("archetype") or "",
            "level": entry.get("level", 0) or 0,
            "xp":    xp,
            "title": entry.get("title") or entry.get("current_title") or "",
        })
        try:
            new_xp[name] = int(xp)
            if prev_xp is not None and name in prev_xp:
                delta = int(xp) - prev_xp[name]
                if delta != 0:
                    xp_delta[name] = delta
        except (TypeError, ValueError):
            pass

    snapshot = {
        "t":               t,
        "iso":             utc_iso(t),
        "leaderboard":     leaderboard,
        "xp_delta":        xp_delta,
        "regime":          safe_get(features, "market_weather", "regime") or arena.get("regime") or terminal.get("regime") or "Chop",
        "regime_entropy":  arena.get("bayes_entropy", 0.0) or 0.0,
        "macro_score":     safe_get(features, "market_weather", "macro_score") or 50.0,
        "macro_mode":      safe_get(features, "market_weather", "state") or "CLOUDY",
        "weather":         safe_get(features, "market_weather", "state") or "CLOUDY",
        "weather_intensity": safe_get(features, "market_weather", "intensity") or 0.5,
        "crowd":           safe_get(features, "crowd_reaction", "level") or "SILENT",
        "boss_event":      features.get("boss_event"),
        "rivalries":       arena.get("rivalries") or [],
        "champion":        _detect_champion(leaderboard),
        "btc_price":       _btc_price(terminal, features),
        "tick":            arena.get("tick", 0),
        "tg_safe":         True,
    }
    return snapshot, new_xp


def _detect_champion(leaderboard: list[dict]) -> str:
    """Champion = current leader by XP (top of leaderboard)."""
    if not leaderboard:
        return ""
    return leaderboard[0].get("name", "")


def _btc_price(terminal: dict, features: dict) -> float:
    try:
        v = terminal.get("price") or terminal.get("btc_price")
        if v:
            return float(v)
    except (TypeError, ValueError):
        pass
    try:
        return float(features.get("btc_price", 0.0))
    except (TypeError, ValueError):
        return 0.0


# ── Main loop ───────────────────────────────────────────────────────────────


_STOP = False


def _handle_stop(*_: object) -> None:
    global _STOP
    _STOP = True


def run() -> int:
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    storage = storage_from_env(DEFAULT_SNAPSHOTS_DIR)
    pid_file = storage.dir / "replay_collector.pid"
    pid_file.write_text(str(os.getpid()))

    print("🎬 TRADINGGURU REPLAY COLLECTOR — paper-safe history capture")
    print(f"   snapshots dir       : {storage.dir}")
    print(f"   scan interval       : {SCAN_INTERVAL_SEC}s")
    print(f"   compact interval    : {COMPACT_INTERVAL_SEC}s")
    print(f"   retention days      : {storage.retention_days}")
    print(f"   max total cap       : {storage.max_total_bytes // 1024 // 1024} MB")
    print(f"   max single-day cap  : {storage.max_day_bytes // 1024 // 1024} MB")
    print(f"   PID                 : {os.getpid()}")
    print("   tg_safe markers     : TG_PAPER_EXECUTION=1 TG_DISABLE_REAL_ORDERS=1 LIVE_ORDERS=0")
    print()

    prev_xp: dict[str, int] = {}
    prev_snapshot: dict | None = None
    snapshot_index: int = -1
    last_compact_ts: float = 0.0
    tick_count: int = 0
    recent_events: list[ReplayEvent] = []

    try:
        # Lazy-import to avoid circular at module load
        from replay_api import compact_outputs

        while not _STOP:
            tick_count += 1
            t_start = time.time()

            # 1. Read sources
            arena = fetch_arena_state()
            features = fetch_features_state()
            terminal = fetch_terminal_state()

            if not arena and not features:
                # Nothing to snapshot — skip this tick
                _sleep_remainder(t_start)
                continue

            # 2. Build snapshot
            snapshot, new_xp = build_snapshot(arena, features, terminal, prev_xp=prev_xp)
            prev_xp = new_xp
            snapshot_index += 1

            # 3. Append to gzip jsonl
            storage.append_snapshot(snapshot)

            # 4. Detect events between prev and current
            events_this_tick = detect_events(prev_snapshot, snapshot, snapshot_index)
            recent_events.extend(events_this_tick)
            if len(recent_events) > 500:
                recent_events = recent_events[-500:]
            prev_snapshot = snapshot

            # 5. Periodic compaction → JSON outputs for frontend
            now = time.time()
            if now - last_compact_ts >= COMPACT_INTERVAL_SEC:
                try:
                    compact_outputs(storage, recent_events_list=list(recent_events))
                except Exception as e:
                    print(f"  ⚠ compact failed: {e}")
                last_compact_ts = now

            # 6. Heartbeat
            if tick_count % 6 == 0 or events_this_tick:
                ev_marker = f" · {len(events_this_tick)} event(s)" if events_this_tick else ""
                print(f"  🎬 tick={tick_count} idx={snapshot_index} "
                      f"agents={len(snapshot['leaderboard'])} "
                      f"regime={snapshot['regime']} "
                      f"weather={snapshot['weather']} "
                      f"crowd={snapshot['crowd']} "
                      f"size={storage.total_size_bytes() / 1024:.1f}KB{ev_marker}")

            _sleep_remainder(t_start)

    finally:
        try:
            pid_file.unlink()
        except OSError:
            pass
        print()
        print(f"🎬 replay_collector stopped after {tick_count} ticks")
        report = storage.integrity_report()
        print(f"  total snapshots stored: {report.get('file_count')} file(s)")
        print(f"  storage size         : {report['total_size_mb']} MB")

    return 0


def _sleep_remainder(t_start: float) -> None:
    elapsed = time.time() - t_start
    if elapsed < SCAN_INTERVAL_SEC:
        time.sleep(SCAN_INTERVAL_SEC - elapsed)


if __name__ == "__main__":
    sys.exit(run())
