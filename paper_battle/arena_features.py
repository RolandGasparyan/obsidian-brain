#!/usr/bin/env python3
"""
arena_features.py — Shadow Arena entertainment-layer features

🎮 Backend logic for Shadow Arena enrichment features:
    • Market Weather Engine
    • Boss Events Detector
    • Crowd Reaction Synthesizer

🛡 PAPER-SAFE · READ-ONLY:
    - NEVER affects trading logic
    - NEVER reads or writes .api_key
    - NEVER opens exchange sockets
    - Pure functions on market data + agent state
    - Output goes to runtime/arena_features.json (separate from paper-arena.json)

Design principle (per Spec #22 Spec #23):
    "Controlled signal emergence, NOT dopamine"
    These features are VISUALIZATION/ENTERTAINMENT only. They:
    - Read from market data + paper-arena.json
    - Compute visualization state
    - Write enrichment JSON
    They DO NOT:
    - Modify agent decisions
    - Modify risk caps
    - Modify Layer 1 code

API:
    weather = compute_market_weather(btc_history, vol_pct, regime, macro_score)
    boss    = detect_boss_event(market_data_history, last_boss_event)
    crowd   = compute_crowd_reaction(recent_trades, leader_changes, boss_event)
"""

from __future__ import annotations

import statistics
from collections import deque
from datetime import datetime, timezone
from typing import Any


# ── MARKET WEATHER ──────────────────────────────────────────────────────────

WEATHER_STATES = ["SUNNY", "CLOUDY", "STORMY", "BLIZZARD", "DAWN"]


def compute_market_weather(
    btc_window: list[float] | deque,
    vol_pct: float,
    bayes_dominant: str,
    bayes_entropy: float,
    macro_score: float,
) -> dict[str, Any]:
    """
    Market weather state from trading conditions.

    SUNNY     calm trend · low vol · macro NEUTRAL+ · regime Trend or Expansion
    CLOUDY    medium vol · macro DEFENSIVE · regime Chop or Compression
    STORMY    high vol · macro DEFENSIVE/PANIC · regime Expansion or Recovery
    BLIZZARD  panic regime · high entropy · macro PANIC
    DAWN      recovery emerging · macro improving · regime Recovery

    Output:
        state              str (one of WEATHER_STATES)
        intensity          float 0-1 (severity within state)
        trend_direction    str "rising" | "falling" | "sideways"
        bias_visual        str (description for frontend)
    """
    btc = list(btc_window) if not isinstance(btc_window, list) else btc_window
    intensity = 0.5
    trend = "sideways"

    # Trend direction from recent move
    if len(btc) >= 6:
        recent_change_pct = (btc[-1] - btc[-6]) / btc[-6] * 100.0 if btc[-6] else 0.0
        if recent_change_pct > 0.10:
            trend = "rising"
        elif recent_change_pct < -0.10:
            trend = "falling"

    # State selection
    if bayes_dominant == "Panic" and bayes_entropy > 0.5 and macro_score < 30:
        state = "BLIZZARD"
        intensity = min(1.0, 0.5 + bayes_entropy * 0.3)
    elif bayes_dominant == "Recovery" and macro_score >= 30:
        state = "DAWN"
        intensity = min(1.0, 0.5 + (40 - macro_score) / 40 if macro_score < 40 else 0.5)
    elif vol_pct >= 1.0:
        state = "STORMY"
        intensity = min(1.0, vol_pct / 2.0)
    elif vol_pct < 0.15 and macro_score >= 40 and bayes_dominant in ("Trend", "Expansion"):
        state = "SUNNY"
        intensity = max(0.3, 1.0 - vol_pct / 0.15)
    else:
        state = "CLOUDY"
        intensity = 0.5

    visual_bias = {
        "SUNNY":    "bright · low-vol breakout potential",
        "CLOUDY":   "calm · regime watching",
        "STORMY":   "high vol · arena tension",
        "BLIZZARD": "panic · agents defensive · capital priority",
        "DAWN":     "recovery emerging · cautious optimism",
    }[state]

    return {
        "state": state,
        "intensity": round(intensity, 3),
        "trend_direction": trend,
        "vol_pct": round(vol_pct, 4),
        "regime": bayes_dominant,
        "macro_score": round(macro_score, 1),
        "bias_visual": visual_bias,
    }


# ── BOSS EVENTS ─────────────────────────────────────────────────────────────

# Cooldown to avoid spamming boss events
BOSS_COOLDOWN_SECONDS = 600   # 10 min cooldown between events


def detect_boss_event(
    btc_history: list[float] | deque,
    spread_history: list[float] | deque,
    bayes_panic_pct: float,
    bayes_entropy: float,
    last_boss_event: dict | None,
    now_ts: float,
) -> dict[str, Any] | None:
    """
    Detect rare market events worthy of "boss" UI treatment.

    Boss types (5):
        FLASH_CRASH       price drops > 1.0% in 5 min
        WHALE_PUMP        price surges > 1.0% in 5 min
        VOLATILITY_BOSS   realized vol > 1.8% sustained
        REGIME_QUAKE      Bayesian Panic posterior > 80% with entropy < 0.2 (locked panic)
        LIQUIDITY_DROUGHT spread expanded > 3x recent mean

    Returns dict or None if no event triggers.
    Caller is responsible for cooldown enforcement via `last_boss_event` arg.
    """
    # Cooldown check
    if last_boss_event:
        elapsed = now_ts - last_boss_event.get("triggered_at_ts", 0)
        if elapsed < BOSS_COOLDOWN_SECONDS:
            return None

    btc = list(btc_history) if not isinstance(btc_history, list) else btc_history
    if len(btc) < 12:
        return None
    sp = list(spread_history) if not isinstance(spread_history, list) else spread_history

    # FLASH_CRASH / WHALE_PUMP — 5-min move
    if len(btc) >= 30:  # assumes ~10s ticks → 30 ticks = 5 min
        move_pct = (btc[-1] - btc[-30]) / btc[-30] * 100.0 if btc[-30] else 0.0
        if move_pct <= -1.0:
            return _build_boss("FLASH_CRASH", abs(move_pct), now_ts,
                               f"BTC -{abs(move_pct):.2f}% in 5 min")
        if move_pct >= 1.0:
            return _build_boss("WHALE_PUMP", abs(move_pct), now_ts,
                               f"BTC +{abs(move_pct):.2f}% in 5 min")

    # VOLATILITY_BOSS — sustained high realized vol
    mean = statistics.fmean(btc[-12:])
    if mean > 0:
        vol = statistics.pstdev(btc[-12:]) / mean * 100.0
        if vol >= 1.8:
            return _build_boss("VOLATILITY_BOSS", min(1.0, vol / 3.0), now_ts,
                               f"realized vol {vol:.2f}% sustained")

    # REGIME_QUAKE — locked Panic with high certainty
    if bayes_panic_pct >= 80.0 and bayes_entropy < 0.2:
        return _build_boss("REGIME_QUAKE", min(1.0, bayes_panic_pct / 100.0), now_ts,
                           f"Bayesian Panic {bayes_panic_pct:.1f}% · entropy {bayes_entropy:.2f}")

    # LIQUIDITY_DROUGHT — spread expansion vs baseline
    if len(sp) >= 30:
        recent = statistics.fmean(sp[-6:])
        baseline = statistics.fmean(sp[-30:-6]) if len(sp) >= 30 else recent
        if baseline > 0 and recent > 3.0 * baseline:
            return _build_boss("LIQUIDITY_DROUGHT",
                               min(1.0, recent / (5.0 * baseline)),
                               now_ts,
                               f"spread expanded {recent / baseline:.1f}x vs baseline")

    return None


def _build_boss(boss_type: str, severity: float, ts: float, description: str) -> dict[str, Any]:
    return {
        "type": boss_type,
        "severity": round(severity, 3),
        "triggered_at_ts": ts,
        "triggered_at_utc": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
        "duration_estimate_min": _boss_duration(boss_type),
        "description": description,
        "cooldown_active_until_ts": ts + BOSS_COOLDOWN_SECONDS,
    }


def _boss_duration(boss_type: str) -> int:
    return {
        "FLASH_CRASH":       8,
        "WHALE_PUMP":        8,
        "VOLATILITY_BOSS":  20,
        "REGIME_QUAKE":     15,
        "LIQUIDITY_DROUGHT": 12,
    }.get(boss_type, 10)


# ── CROWD REACTIONS ─────────────────────────────────────────────────────────

CROWD_LEVELS = ["SILENT", "MURMUR", "APPLAUSE", "ROAR", "BOO", "GASP"]


def compute_crowd_reaction(
    recent_trades: list[dict],
    leader_changed: bool,
    title_defended_or_lost: bool,
    boss_event_active: bool,
    avg_realized_r: float = 0.0,
) -> dict[str, Any]:
    """
    Synthetic crowd reaction to recent arena events.

    Reactions triggered by:
    - Recent trade win/loss outcome (R-multiple based)
    - Leader changes (rivalry tension)
    - Title defense or loss
    - Boss event presence (gasp during high-tension)

    Returns crowd state for arena UI.
    """
    level = "SILENT"
    sentiment = "neutral"
    triggers: list[str] = []

    # Boss event → GASP (always wins)
    if boss_event_active:
        level = "GASP"
        sentiment = "tense"
        triggers.append("boss_event_active")
        return {
            "level": level,
            "sentiment": sentiment,
            "intensity": 1.0,
            "triggered_by": triggers,
        }

    # Title defended/lost
    if title_defended_or_lost:
        level = "ROAR"
        sentiment = "dramatic"
        triggers.append("title_event")

    # Leader changed (rivalry tension)
    if leader_changed:
        if level == "SILENT":
            level = "APPLAUSE"
        sentiment = "competitive"
        triggers.append("leader_change")

    # Recent trade outcome
    if recent_trades:
        avg_r_recent = avg_realized_r if avg_realized_r else statistics.fmean(
            [t.get("realized_r", 0.0) for t in recent_trades[-5:]]
        )
        if avg_r_recent >= 1.5:
            if level == "SILENT":
                level = "ROAR"
            sentiment = "excited"
            triggers.append(f"strong_wins_r={avg_r_recent:.2f}")
        elif avg_r_recent <= -0.8:
            level = "BOO"
            sentiment = "disappointed"
            triggers.append(f"strong_losses_r={avg_r_recent:.2f}")
        elif avg_r_recent > 0.5:
            if level == "SILENT":
                level = "APPLAUSE"
            triggers.append(f"positive_r={avg_r_recent:.2f}")
        elif -0.5 < avg_r_recent < 0.5 and level == "SILENT":
            level = "MURMUR"
            triggers.append("flat_outcomes")

    intensity_map = {
        "SILENT":    0.0,
        "MURMUR":    0.3,
        "APPLAUSE":  0.6,
        "ROAR":      0.85,
        "BOO":       0.7,
        "GASP":      1.0,
    }

    return {
        "level": level,
        "sentiment": sentiment,
        "intensity": intensity_map[level],
        "triggered_by": triggers,
    }


# ── PACKAGED ENRICHMENT ─────────────────────────────────────────────────────


def compute_arena_features(
    btc_history: list[float] | deque,
    spread_history: list[float] | deque,
    vol_pct: float,
    bayes_dominant: str,
    bayes_entropy: float,
    bayes_panic_pct: float,
    macro_score: float,
    recent_trades: list[dict] | None = None,
    leader_changed: bool = False,
    title_defended_or_lost: bool = False,
    last_boss_event: dict | None = None,
    avg_realized_r: float = 0.0,
    now_ts: float | None = None,
) -> dict[str, Any]:
    """
    Single entry-point: compute all 3 arena features in one call.
    Designed for `arena_shadow_runner.py` to invoke each tick.
    """
    import time
    if now_ts is None:
        now_ts = time.time()

    weather = compute_market_weather(
        btc_window=btc_history,
        vol_pct=vol_pct,
        bayes_dominant=bayes_dominant,
        bayes_entropy=bayes_entropy,
        macro_score=macro_score,
    )

    boss = detect_boss_event(
        btc_history=btc_history,
        spread_history=spread_history,
        bayes_panic_pct=bayes_panic_pct,
        bayes_entropy=bayes_entropy,
        last_boss_event=last_boss_event,
        now_ts=now_ts,
    )

    # Boss event still active during cooldown? Pass forward for crowd reaction.
    active_boss = boss if boss else (
        last_boss_event
        if last_boss_event and now_ts < last_boss_event.get("cooldown_active_until_ts", 0)
        else None
    )

    crowd = compute_crowd_reaction(
        recent_trades=recent_trades or [],
        leader_changed=leader_changed,
        title_defended_or_lost=title_defended_or_lost,
        boss_event_active=active_boss is not None,
        avg_realized_r=avg_realized_r,
    )

    return {
        "market_weather": weather,
        "boss_event": boss,                # only when a NEW event triggers
        "boss_event_active": active_boss,  # may include in-cooldown previous event
        "crowd_reaction": crowd,
        "computed_at_utc": datetime.fromtimestamp(now_ts, timezone.utc).isoformat(),
        "tg_safe": True,                   # marker: no trading-logic interference
    }
