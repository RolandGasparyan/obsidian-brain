#!/usr/bin/env python3
"""
replay_timeline.py — timeline navigation + scrubber math

🛡 PAPER-SAFE · pure functions on stored snapshots.

Public API:
    timeline = build_timeline(snapshots)
    cursor   = seek(timeline, rewind_seconds)
    sparse   = sparse_for_scrubber(timeline, n_markers=120)
"""

from __future__ import annotations

import bisect
from typing import Any


def build_timeline(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Build a timeline index from snapshots.

    Returns:
        {
          "ts_list":    [t0, t1, t2, ...],
          "iso_list":   [iso0, iso1, ...],
          "first_ts":   float,
          "last_ts":    float,
          "duration_seconds": float,
          "count":      int,
        }
    """
    if not snapshots:
        return {
            "ts_list": [], "iso_list": [],
            "first_ts": 0.0, "last_ts": 0.0,
            "duration_seconds": 0.0, "count": 0,
        }
    ts_list = [s.get("t", 0.0) for s in snapshots]
    iso_list = [s.get("iso", "") for s in snapshots]
    return {
        "ts_list":          ts_list,
        "iso_list":         iso_list,
        "first_ts":         ts_list[0],
        "last_ts":          ts_list[-1],
        "duration_seconds": ts_list[-1] - ts_list[0],
        "count":            len(ts_list),
    }


def seek(timeline: dict[str, Any], target_ts: float) -> int:
    """
    Find snapshot index closest to (or just before) target_ts.
    Returns -1 if timeline empty.
    """
    ts_list = timeline.get("ts_list", [])
    if not ts_list:
        return -1
    if target_ts <= ts_list[0]:
        return 0
    if target_ts >= ts_list[-1]:
        return len(ts_list) - 1
    # Binary search
    idx = bisect.bisect_right(ts_list, target_ts) - 1
    return max(0, idx)


def rewind(timeline: dict[str, Any], rewind_seconds: float) -> int:
    """Index for (last_ts - rewind_seconds)."""
    if not timeline.get("ts_list"):
        return -1
    target = timeline["last_ts"] - rewind_seconds
    return seek(timeline, target)


def window(timeline: dict[str, Any], start_ts: float, end_ts: float) -> tuple[int, int]:
    """Return (start_idx, end_idx) slice for ts window."""
    if not timeline.get("ts_list"):
        return (0, 0)
    s = seek(timeline, start_ts)
    e = seek(timeline, end_ts)
    return (s, min(e + 1, timeline["count"]))


# ── Sparse markers (for scrubber UI · 120 markers default) ─────────────────


def sparse_for_scrubber(
    timeline: dict[str, Any],
    n_markers: int = 120,
) -> list[dict[str, Any]]:
    """
    Downsample timeline to N evenly-spaced markers for UI scrubber rendering.
    Each marker carries minimal info: t, iso, idx (for fast lookup).
    """
    ts = timeline.get("ts_list", [])
    iso = timeline.get("iso_list", [])
    count = len(ts)
    if count == 0:
        return []
    if count <= n_markers:
        return [{"t": ts[i], "iso": iso[i], "idx": i} for i in range(count)]
    step = count / n_markers
    out = []
    for k in range(n_markers):
        i = min(int(k * step), count - 1)
        out.append({"t": ts[i], "iso": iso[i], "idx": i})
    return out


# ── Heatmap (event density per bucket · for minimap) ───────────────────────


def event_density_heatmap(
    timeline: dict[str, Any],
    events: list[dict[str, Any]],
    n_buckets: int = 60,
) -> list[dict[str, Any]]:
    """
    Group events into N time-buckets across the timeline span for minimap rendering.
    """
    if not timeline.get("ts_list") or not events:
        return [{"bucket": i, "count": 0, "max_severity": 0.0,
                 "dominant_type": None} for i in range(n_buckets)]

    first = timeline["first_ts"]
    span = timeline["duration_seconds"] or 1.0

    buckets = [{"count": 0, "severity_sum": 0.0, "max_severity": 0.0,
                "type_counts": {}} for _ in range(n_buckets)]

    for e in events:
        t = e.get("t", 0.0)
        idx = int((t - first) / span * n_buckets)
        idx = max(0, min(n_buckets - 1, idx))
        b = buckets[idx]
        b["count"] += 1
        sev = e.get("severity", 0.5)
        b["severity_sum"] += sev
        b["max_severity"] = max(b["max_severity"], sev)
        et = e.get("event_type", "UNKNOWN")
        b["type_counts"][et] = b["type_counts"].get(et, 0) + 1

    out = []
    for i, b in enumerate(buckets):
        dom_type = None
        if b["type_counts"]:
            dom_type = max(b["type_counts"], key=b["type_counts"].get)
        out.append({
            "bucket": i,
            "count": b["count"],
            "max_severity": round(b["max_severity"], 3),
            "avg_severity": round(b["severity_sum"] / b["count"], 3) if b["count"] else 0.0,
            "dominant_type": dom_type,
        })
    return out
