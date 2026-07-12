#!/usr/bin/env python3
"""
replay_events.py — event taxonomy + detection + boss-moment auto-tagging

🛡 PAPER-SAFE · READ-ONLY logic on snapshots.

Detects 9 event types between consecutive snapshots:
  1. AGENT_LEADER_CHANGE
  2. XP_JUMP           (per-agent ≥ 50 XP single cycle)
  3. XP_COLLAPSE       (per-agent ≤ -25 XP single cycle)
  4. REGIME_TRANSITION (Bayesian dominant changes)
  5. VOLATILITY_STORM  (weather → STORMY or BLIZZARD)
  6. CROWD_REACTION    (crowd level rises to ROAR/GASP/BOO)
  7. BOSS_EVENT        (boss_event field non-null in current snapshot)
  8. STREAK            (consecutive wins/losses ≥ 3 by same agent)
  9. CHAMPION_SWAP     (championship title changes hand)

Auto-tagging boss moments (5 types) across full history:
  - BIGGEST_XP_JUMP
  - BIGGEST_COLLAPSE
  - LONGEST_STREAK
  - VOLATILITY_EXPLOSION (highest weather intensity sustained period)
  - ARENA_DOMINATION (single agent holds champion ≥ 30 cycles)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

from replay_utils import short_hash, safe_get


# ── EVENT TYPES ─────────────────────────────────────────────────────────────

EVENT_TYPES = [
    "AGENT_LEADER_CHANGE",
    "XP_JUMP",
    "XP_COLLAPSE",
    "REGIME_TRANSITION",
    "VOLATILITY_STORM",
    "CROWD_REACTION",
    "BOSS_EVENT",
    "STREAK",
    "CHAMPION_SWAP",
]

# Severity thresholds
XP_JUMP_THRESHOLD = 50
XP_COLLAPSE_THRESHOLD = -25
STREAK_MIN_LENGTH = 3


@dataclass
class ReplayEvent:
    event_id: str
    event_type: str
    t: float                 # unix ts
    iso: str                 # ISO UTC
    severity: float = 0.5    # 0-1 for UI styling
    actors: list[str] = field(default_factory=list)
    description: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    snapshot_index: int = -1


# ── EVENT DETECTION (between 2 consecutive snapshots) ─────────────────────


def detect_events(
    prev: dict[str, Any] | None,
    curr: dict[str, Any],
    snapshot_index: int,
) -> list[ReplayEvent]:
    """Compute all events visible between prev and curr snapshots."""
    events: list[ReplayEvent] = []
    t = curr.get("t", 0.0)
    iso = curr.get("iso", "")

    # 1 · AGENT_LEADER_CHANGE
    prev_leader = safe_get(prev, "leaderboard", 0, "name") if prev else None
    curr_leader = safe_get(curr, "leaderboard", 0, "name")
    if prev_leader and curr_leader and prev_leader != curr_leader:
        events.append(ReplayEvent(
            event_id=short_hash((t, "leader", prev_leader, curr_leader)),
            event_type="AGENT_LEADER_CHANGE",
            t=t, iso=iso, severity=0.7,
            actors=[prev_leader, curr_leader],
            description=f"{curr_leader} takes lead from {prev_leader}",
            payload={"from": prev_leader, "to": curr_leader},
            snapshot_index=snapshot_index,
        ))

    # 2-3 · XP_JUMP / XP_COLLAPSE
    xp_delta = curr.get("xp_delta") or {}
    for agent, delta in xp_delta.items():
        try:
            d = float(delta)
        except (TypeError, ValueError):
            continue
        if d >= XP_JUMP_THRESHOLD:
            events.append(ReplayEvent(
                event_id=short_hash((t, "xp_jump", agent, d)),
                event_type="XP_JUMP",
                t=t, iso=iso,
                severity=min(1.0, d / 200.0),
                actors=[agent],
                description=f"{agent} gains +{d:.0f} XP",
                payload={"agent": agent, "delta": d},
                snapshot_index=snapshot_index,
            ))
        elif d <= XP_COLLAPSE_THRESHOLD:
            events.append(ReplayEvent(
                event_id=short_hash((t, "xp_collapse", agent, d)),
                event_type="XP_COLLAPSE",
                t=t, iso=iso,
                severity=min(1.0, abs(d) / 100.0),
                actors=[agent],
                description=f"{agent} loses {d:.0f} XP",
                payload={"agent": agent, "delta": d},
                snapshot_index=snapshot_index,
            ))

    # 4 · REGIME_TRANSITION
    prev_regime = safe_get(prev, "regime") if prev else None
    curr_regime = safe_get(curr, "regime")
    if prev_regime and curr_regime and prev_regime != curr_regime:
        events.append(ReplayEvent(
            event_id=short_hash((t, "regime", prev_regime, curr_regime)),
            event_type="REGIME_TRANSITION",
            t=t, iso=iso,
            severity=0.6,
            actors=[],
            description=f"Bayesian regime shifted {prev_regime} → {curr_regime}",
            payload={"from": prev_regime, "to": curr_regime,
                     "entropy": curr.get("regime_entropy", 0.0)},
            snapshot_index=snapshot_index,
        ))

    # 5 · VOLATILITY_STORM
    weather = curr.get("weather")
    if weather in ("STORMY", "BLIZZARD"):
        prev_weather = safe_get(prev, "weather") if prev else None
        if prev_weather != weather:
            events.append(ReplayEvent(
                event_id=short_hash((t, "vol_storm", weather)),
                event_type="VOLATILITY_STORM",
                t=t, iso=iso,
                severity=curr.get("weather_intensity", 0.7),
                actors=[],
                description=f"Market weather → {weather}",
                payload={"weather": weather,
                         "intensity": curr.get("weather_intensity", 0.0)},
                snapshot_index=snapshot_index,
            ))

    # 6 · CROWD_REACTION
    crowd = curr.get("crowd")
    if crowd in ("ROAR", "GASP", "BOO"):
        prev_crowd = safe_get(prev, "crowd") if prev else None
        if prev_crowd != crowd:
            sev_map = {"ROAR": 0.7, "BOO": 0.6, "GASP": 0.9}
            events.append(ReplayEvent(
                event_id=short_hash((t, "crowd", crowd)),
                event_type="CROWD_REACTION",
                t=t, iso=iso,
                severity=sev_map.get(crowd, 0.5),
                actors=[],
                description=f"Crowd: {crowd}",
                payload={"level": crowd},
                snapshot_index=snapshot_index,
            ))

    # 7 · BOSS_EVENT (passes through arena_features)
    boss = curr.get("boss_event")
    if boss and isinstance(boss, dict):
        # Only fire if NEW (not seen in prev)
        prev_boss = safe_get(prev, "boss_event") if prev else None
        prev_boss_id = safe_get(prev_boss, "triggered_at_ts") if prev_boss else None
        curr_boss_id = boss.get("triggered_at_ts")
        if prev_boss_id != curr_boss_id:
            events.append(ReplayEvent(
                event_id=short_hash((t, "boss", boss.get("type"), curr_boss_id)),
                event_type="BOSS_EVENT",
                t=t, iso=iso,
                severity=boss.get("severity", 0.8),
                actors=[],
                description=f"BOSS: {boss.get('type')} — {boss.get('description', '')}",
                payload={"boss_type": boss.get("type"),
                         "boss_severity": boss.get("severity"),
                         "duration_min": boss.get("duration_estimate_min")},
                snapshot_index=snapshot_index,
            ))

    # 9 · CHAMPION_SWAP
    prev_champ = safe_get(prev, "champion") if prev else None
    curr_champ = safe_get(curr, "champion")
    if prev_champ and curr_champ and prev_champ != curr_champ:
        events.append(ReplayEvent(
            event_id=short_hash((t, "champ", prev_champ, curr_champ)),
            event_type="CHAMPION_SWAP",
            t=t, iso=iso, severity=0.85,
            actors=[prev_champ, curr_champ],
            description=f"Championship: {curr_champ} dethrones {prev_champ}",
            payload={"from": prev_champ, "to": curr_champ},
            snapshot_index=snapshot_index,
        ))

    return events


def detect_streaks(snapshots: list[dict[str, Any]]) -> list[ReplayEvent]:
    """
    Streaks detector over a window of snapshots (event type #8).
    A streak fires when same agent holds leader position ≥ STREAK_MIN_LENGTH cycles.
    """
    if len(snapshots) < STREAK_MIN_LENGTH:
        return []
    events: list[ReplayEvent] = []
    current_leader: str | None = None
    streak_start_idx: int = -1
    streak_len: int = 0

    for i, snap in enumerate(snapshots):
        leader = safe_get(snap, "leaderboard", 0, "name")
        if leader == current_leader and leader is not None:
            streak_len += 1
        else:
            # Closing previous streak
            if streak_len >= STREAK_MIN_LENGTH and current_leader:
                snap_at_end = snapshots[i - 1]
                events.append(ReplayEvent(
                    event_id=short_hash(("streak", current_leader, streak_start_idx, streak_len)),
                    event_type="STREAK",
                    t=snap_at_end.get("t", 0.0),
                    iso=snap_at_end.get("iso", ""),
                    severity=min(1.0, streak_len / 30.0),
                    actors=[current_leader],
                    description=f"{current_leader} held lead for {streak_len} cycles",
                    payload={"agent": current_leader, "length": streak_len,
                             "start_index": streak_start_idx, "end_index": i - 1},
                    snapshot_index=i - 1,
                ))
            current_leader = leader
            streak_start_idx = i
            streak_len = 1

    # Tail streak
    if streak_len >= STREAK_MIN_LENGTH and current_leader:
        snap_at_end = snapshots[-1]
        events.append(ReplayEvent(
            event_id=short_hash(("streak_tail", current_leader, streak_start_idx, streak_len)),
            event_type="STREAK",
            t=snap_at_end.get("t", 0.0),
            iso=snap_at_end.get("iso", ""),
            severity=min(1.0, streak_len / 30.0),
            actors=[current_leader],
            description=f"{current_leader} held lead for {streak_len} cycles (ongoing)",
            payload={"agent": current_leader, "length": streak_len,
                     "start_index": streak_start_idx, "end_index": len(snapshots) - 1,
                     "ongoing": True},
            snapshot_index=len(snapshots) - 1,
        ))

    return events


# ── BOSS-MOMENT AUTO-TAGGING (5 types · cross-history) ──────────────────────


def auto_tag_boss_moments(
    snapshots: list[dict[str, Any]],
    events: list[ReplayEvent],
) -> list[dict[str, Any]]:
    """
    Identifies the 5 "must-see" highlights from history:
      - BIGGEST_XP_JUMP        (single largest XP_JUMP event)
      - BIGGEST_COLLAPSE       (single largest XP_COLLAPSE event)
      - LONGEST_STREAK         (longest STREAK event)
      - VOLATILITY_EXPLOSION   (highest sustained weather intensity)
      - ARENA_DOMINATION       (longest single-champion run)

    Returns list of moment dicts ready for replay-bosses.json.
    """
    moments: list[dict[str, Any]] = []

    # XP jumps + collapses
    xp_jumps = [e for e in events if e.event_type == "XP_JUMP"]
    if xp_jumps:
        biggest = max(xp_jumps, key=lambda e: e.payload.get("delta", 0))
        moments.append({
            "type": "BIGGEST_XP_JUMP",
            "event_id": biggest.event_id,
            "t": biggest.t, "iso": biggest.iso,
            "actors": biggest.actors,
            "description": biggest.description,
            "magnitude": biggest.payload.get("delta", 0),
            "snapshot_index": biggest.snapshot_index,
        })

    xp_collapses = [e for e in events if e.event_type == "XP_COLLAPSE"]
    if xp_collapses:
        worst = min(xp_collapses, key=lambda e: e.payload.get("delta", 0))
        moments.append({
            "type": "BIGGEST_COLLAPSE",
            "event_id": worst.event_id,
            "t": worst.t, "iso": worst.iso,
            "actors": worst.actors,
            "description": worst.description,
            "magnitude": worst.payload.get("delta", 0),
            "snapshot_index": worst.snapshot_index,
        })

    # Longest streak
    streaks = [e for e in events if e.event_type == "STREAK"]
    if streaks:
        longest = max(streaks, key=lambda e: e.payload.get("length", 0))
        moments.append({
            "type": "LONGEST_STREAK",
            "event_id": longest.event_id,
            "t": longest.t, "iso": longest.iso,
            "actors": longest.actors,
            "description": longest.description,
            "magnitude": longest.payload.get("length", 0),
            "snapshot_index": longest.snapshot_index,
        })

    # Volatility explosion (highest intensity weather sustained 5+ cycles)
    sustained_stormy = _find_sustained_volatility(snapshots, min_intensity=0.7, min_cycles=5)
    if sustained_stormy:
        moments.append(sustained_stormy)

    # Arena domination (longest champion-held)
    champ_run = _find_longest_champion_run(snapshots)
    if champ_run:
        moments.append(champ_run)

    return moments


def _find_sustained_volatility(
    snapshots: list[dict[str, Any]],
    min_intensity: float = 0.7,
    min_cycles: int = 5,
) -> dict[str, Any] | None:
    best_start = -1
    best_len = 0
    best_avg_intensity = 0.0
    cur_start = -1
    cur_len = 0
    cur_sum = 0.0

    for i, snap in enumerate(snapshots):
        intensity = snap.get("weather_intensity", 0.0)
        if intensity >= min_intensity and snap.get("weather") in ("STORMY", "BLIZZARD"):
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            cur_sum += intensity
        else:
            if cur_len >= min_cycles:
                avg = cur_sum / cur_len
                if cur_len * avg > best_len * best_avg_intensity:
                    best_start, best_len, best_avg_intensity = cur_start, cur_len, avg
            cur_len = 0
            cur_sum = 0.0
    # Trailing
    if cur_len >= min_cycles:
        avg = cur_sum / cur_len
        if cur_len * avg > best_len * best_avg_intensity:
            best_start, best_len, best_avg_intensity = cur_start, cur_len, avg

    if best_len < min_cycles:
        return None
    s = snapshots[best_start]
    e = snapshots[best_start + best_len - 1]
    return {
        "type": "VOLATILITY_EXPLOSION",
        "event_id": short_hash(("vol_exp", best_start, best_len)),
        "t": s.get("t", 0.0), "iso": s.get("iso", ""),
        "actors": [],
        "description": f"Sustained {best_len}-cycle volatility (avg intensity {best_avg_intensity:.2f})",
        "magnitude": round(best_avg_intensity, 3),
        "duration_cycles": best_len,
        "snapshot_index": best_start,
        "ended_at_index": best_start + best_len - 1,
        "ended_at_iso": e.get("iso", ""),
    }


def _find_longest_champion_run(snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not snapshots:
        return None
    best_champ: str | None = None
    best_len: int = 0
    best_start: int = -1
    cur_champ: str | None = None
    cur_len: int = 0
    cur_start: int = -1

    for i, snap in enumerate(snapshots):
        c = snap.get("champion")
        if c and c == cur_champ:
            cur_len += 1
        else:
            if cur_len > best_len:
                best_champ, best_len, best_start = cur_champ, cur_len, cur_start
            cur_champ = c
            cur_start = i
            cur_len = 1
    if cur_len > best_len:
        best_champ, best_len, best_start = cur_champ, cur_len, cur_start

    if not best_champ or best_len < 30:
        return None
    s = snapshots[best_start]
    return {
        "type": "ARENA_DOMINATION",
        "event_id": short_hash(("arena_dom", best_champ, best_start, best_len)),
        "t": s.get("t", 0.0), "iso": s.get("iso", ""),
        "actors": [best_champ],
        "description": f"{best_champ} held championship for {best_len} cycles",
        "magnitude": best_len,
        "snapshot_index": best_start,
    }


def event_dict(event: ReplayEvent) -> dict[str, Any]:
    return asdict(event)
