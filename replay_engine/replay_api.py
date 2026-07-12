#!/usr/bin/env python3
"""
replay_api.py — periodic compactor that publishes replay JSON for frontend

🛡 PAPER-SAFE · READ from storage / WRITE only to:
    - replay_engine/snapshots/ (own dir)
    - /var/www/ai-trading-championship/dist/api/battle/replay-*.json (public)

Generated public JSONs (all served by nginx):
    /api/battle/replay-index.json            — list of days · counts · sizes · health
    /api/battle/replay-timeline.json         — sparse markers for scrubber (last 24h, 120 markers)
    /api/battle/replay-events-recent.json    — last 200 events (rolling)
    /api/battle/replay-bosses.json           — 5 auto-tagged boss moments
    /api/battle/replay-heatmap.json          — event density buckets for minimap

The collector calls compact_outputs() every COMPACT_INTERVAL_SEC.
Frontend polls these endpoints (light JSON, no replay-state on server).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from replay_serializer import compact_json_dump, pretty_json_dump
from replay_storage import ReplayStorage
from replay_events import (
    detect_streaks,
    auto_tag_boss_moments,
    event_dict,
    ReplayEvent,
)
from replay_timeline import (
    build_timeline,
    sparse_for_scrubber,
    event_density_heatmap,
)
from replay_utils import utc_now_iso


# Optional publish path (server-side nginx)
PUBLISH_DIR_ENV = "REPLAY_PUBLISH_DIR"
DEFAULT_PUBLISH_DIR = Path("/var/www/ai-trading-championship/dist/api/battle")


def get_publish_dir() -> Path | None:
    p = os.environ.get(PUBLISH_DIR_ENV, "").strip()
    if p:
        return Path(p)
    if DEFAULT_PUBLISH_DIR.exists():
        return DEFAULT_PUBLISH_DIR
    return None


# ── Recent-window helpers ──────────────────────────────────────────────────


RECENT_HOURS_DEFAULT = 24
EVENTS_RECENT_LIMIT = 200
SCRUBBER_MARKERS = 120
HEATMAP_BUCKETS = 60


# ── Main compactor ──────────────────────────────────────────────────────────


def compact_outputs(
    storage: ReplayStorage,
    recent_events_list: list[ReplayEvent] | None = None,
    recent_hours: int = RECENT_HOURS_DEFAULT,
) -> dict[str, Any]:
    """
    Compute + write all 5 public replay JSON files.
    Returns the index dict (also written to disk).
    """
    publish_dir = get_publish_dir()

    # 1. Recent snapshots (last N hours)
    all_snaps_iter = storage.read_all_snapshots()
    snapshots = list(all_snaps_iter)
    if not snapshots:
        return {"status": "empty", "snapshot_count": 0}

    # Trim by ts: last N hours
    last_t = snapshots[-1].get("t", 0.0)
    cutoff = last_t - recent_hours * 3600
    recent_snaps = [s for s in snapshots if s.get("t", 0.0) >= cutoff]

    # 2. Build timeline + sparse markers
    timeline = build_timeline(recent_snaps)
    scrubber = sparse_for_scrubber(timeline, n_markers=SCRUBBER_MARKERS)

    # 3. Events (cross-tick detection)
    if recent_events_list is None:
        # Re-derive events from scratch (slow path · used when collector not running)
        from replay_events import detect_events
        events: list[ReplayEvent] = []
        prev = None
        for i, s in enumerate(recent_snaps):
            events.extend(detect_events(prev, s, i))
            prev = s
    else:
        events = [e for e in recent_events_list if e.t >= cutoff]

    # Streak detection
    events.extend(detect_streaks(recent_snaps))

    # 4. Recent events (capped)
    events_sorted = sorted(events, key=lambda e: e.t, reverse=True)
    events_recent = [event_dict(e) for e in events_sorted[:EVENTS_RECENT_LIMIT]]

    # 5. Auto-tag boss moments
    boss_moments = auto_tag_boss_moments(recent_snaps, events)

    # 6. Heatmap
    heatmap = event_density_heatmap(timeline, [event_dict(e) for e in events],
                                     n_buckets=HEATMAP_BUCKETS)

    # 7. Index
    integrity = storage.integrity_report()
    index = {
        "generated_at_utc": utc_now_iso(),
        "tg_safe": True,
        "recent_hours": recent_hours,
        "snapshot_count_total": integrity["file_count"],
        "snapshot_count_recent": len(recent_snaps),
        "event_count_recent": len(events_recent),
        "boss_moment_count": len(boss_moments),
        "timeline": {
            "first_ts": timeline.get("first_ts"),
            "last_ts": timeline.get("last_ts"),
            "duration_seconds": timeline.get("duration_seconds"),
        },
        "storage": integrity,
        "event_types_seen": _count_event_types(events),
        "files": {
            "index":         "replay-index.json",
            "timeline":      "replay-timeline.json",
            "events_recent": "replay-events-recent.json",
            "bosses":        "replay-bosses.json",
            "heatmap":       "replay-heatmap.json",
        },
    }

    # 8. Write outputs
    targets: list[Path] = [storage.dir.parent / "snapshots"]
    if publish_dir:
        targets.append(publish_dir)

    for tgt in targets:
        try:
            tgt.mkdir(parents=True, exist_ok=True)
            (tgt / "replay-index.json").write_text(pretty_json_dump(index))
            (tgt / "replay-timeline.json").write_text(compact_json_dump({
                "tg_safe": True, "markers": scrubber,
                "timeline": {k: timeline.get(k) for k in
                             ("first_ts", "last_ts", "duration_seconds", "count")},
            }))
            (tgt / "replay-events-recent.json").write_text(compact_json_dump({
                "tg_safe": True, "events": events_recent,
            }))
            (tgt / "replay-bosses.json").write_text(compact_json_dump({
                "tg_safe": True, "moments": boss_moments,
            }))
            (tgt / "replay-heatmap.json").write_text(compact_json_dump({
                "tg_safe": True, "buckets": heatmap,
            }))
        except OSError:
            continue

    return index


def _count_event_types(events: list[ReplayEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in events:
        counts[e.event_type] = counts.get(e.event_type, 0) + 1
    return counts


# ── CLI entry (for ad-hoc compaction) ──────────────────────────────────────


if __name__ == "__main__":
    from replay_storage import storage_from_env
    from pathlib import Path
    here = Path(__file__).resolve().parent
    storage = storage_from_env(here / "snapshots")
    result = compact_outputs(storage)
    print(pretty_json_dump(result))
