#!/usr/bin/env python3
"""
replay_utils.py — shared helpers for the replay engine

🛡 PAPER-SAFE · READ-ONLY · NEVER touches /root/canary/, .api_key, or live state.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    """ISO 8601 UTC timestamp (matches paper-arena.json convention)."""
    return datetime.now(timezone.utc).isoformat()


def utc_iso(ts: float) -> str:
    """Convert unix ts to ISO 8601 UTC string."""
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def utc_day(ts: float | None = None) -> str:
    """Day string YYYY-MM-DD UTC for snapshot file rotation."""
    if ts is None:
        ts = time.time()
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def now_ts() -> float:
    return time.time()


def short_hash(data: Any, length: int = 8) -> str:
    """Stable short hash of any JSON-serializable value (for event IDs)."""
    raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:length]


def safe_get(d: dict | None, *keys, default=None):
    """Safe nested-key lookup, never raises."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def diff_pct(a: float, b: float) -> float:
    """Percent change from a→b · safe on zero."""
    if a == 0:
        return 0.0
    return (b - a) / abs(a) * 100.0


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def fmt_duration(seconds: float) -> str:
    """Human duration: 90s · 5m · 2h 14m · 1d 4h"""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m = s // 60
    if m < 60:
        return f"{m}m"
    h = m // 60
    m = m % 60
    if h < 24:
        return f"{h}h {m}m" if m else f"{h}h"
    d = h // 24
    h = h % 24
    return f"{d}d {h}h" if h else f"{d}d"


def file_size_human(path: Path) -> str:
    """Pretty file size: 12 KB · 4.3 MB · 1.2 GB."""
    if not path.exists():
        return "0 B"
    n = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}".rstrip("0").rstrip(".") + (f" {unit}" if False else "")
        n /= 1024
    return f"{n:.1f} TB"
