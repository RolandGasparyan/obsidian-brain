#!/usr/bin/env python3
"""
replay_serializer.py — snapshot ↔ JSONL conversion + gzip I/O

🛡 PAPER-SAFE · READ-ONLY (only writes snapshot files, never touches trading code).

Snapshot schema (one line per cycle, gzipped):
    {
      "t":          1747244400.123,        # unix ts with ms
      "iso":        "2026-05-14T11:00:00Z",
      "leaderboard":[{name, role, level, xp, title}, ...],
      "xp_delta":   {"Ares Valkor": +25, ...},
      "regime":     "Trend",               # Bayesian dominant
      "regime_entropy": 0.6,
      "macro_score":36.77,
      "macro_mode": "DEFENSIVE",
      "weather":    "CLOUDY",
      "weather_intensity": 0.5,
      "crowd":      "SILENT",
      "boss_event": null | {type, severity, description},
      "rivalries":  [{a, b, state}, ...],
      "champion":   "Phoenyx Aldon",
      "btc_price":  79600.0,
      "tick":       1234,
      "tg_safe":    true
    }
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Iterator


def serialize_snapshot(snapshot: dict[str, Any]) -> bytes:
    """Snapshot dict → newline-terminated UTF-8 bytes."""
    return (json.dumps(snapshot, separators=(",", ":"), default=str) + "\n").encode("utf-8")


def deserialize_snapshot(line: bytes | str) -> dict[str, Any] | None:
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="replace")
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def append_gzip_jsonl(path: Path, snapshot: dict[str, Any]) -> int:
    """Append one snapshot line to a gzip-compressed JSONL file. Returns bytes written."""
    payload = serialize_snapshot(snapshot)
    # gzip 'ab' mode appends compressed members → still valid gzip stream
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "ab") as f:
        f.write(payload)
    return len(payload)


def read_gzip_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Stream snapshots from a gzip JSONL file."""
    if not path.exists():
        return
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            snap = deserialize_snapshot(line)
            if snap is not None:
                yield snap


def read_gzip_jsonl_tail(path: Path, n: int) -> list[dict[str, Any]]:
    """
    Read last N snapshots from a gzip JSONL.
    Note: gzip can't seek-from-end, so we stream full file.
    For files >50MB consider sharding.
    """
    if not path.exists():
        return []
    # Use a rolling list (O(n) memory)
    result: list[dict[str, Any]] = []
    for snap in read_gzip_jsonl(path):
        result.append(snap)
        if len(result) > n:
            result.pop(0)
    return result


def count_gzip_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def compact_json_dump(data: Any) -> str:
    """Minified JSON dump for outputs the frontend reads."""
    return json.dumps(data, separators=(",", ":"), default=str)


def pretty_json_dump(data: Any) -> str:
    """Human-readable JSON dump for archives + debugging."""
    return json.dumps(data, indent=2, default=str)
