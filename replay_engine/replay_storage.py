#!/usr/bin/env python3
"""
replay_storage.py — gzipped JSONL snapshot storage + rolling retention

🛡 PAPER-SAFE · READ + WRITE ONLY to its own snapshots/ directory.

Storage layout:
    snapshots/replay-YYYY-MM-DD.jsonl.gz   (one per UTC day, append-only)
    snapshots/replay-events-rolling.jsonl.gz  (rolling events cache)

Constraints:
    - Capped storage: default 100 MB total (configurable via env)
    - Rolling retention: keeps newest N days, deletes older
    - Single-day cap: 10 MB pre-rotation (then opens .part2, .part3, etc.)
    - Daemon-safe: tolerates restart, never loses data, idempotent append
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator

from replay_serializer import (
    append_gzip_jsonl,
    read_gzip_jsonl,
    count_gzip_jsonl_lines,
)
from replay_utils import utc_day, file_size_human


class ReplayStorage:
    """File-system snapshot store with rolling retention."""

    def __init__(
        self,
        snapshots_dir: Path,
        retention_days: int = 7,
        max_total_mb: int = 100,
        max_day_file_mb: int = 10,
    ):
        self.dir = Path(snapshots_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self.max_total_bytes = max_total_mb * 1024 * 1024
        self.max_day_bytes = max_day_file_mb * 1024 * 1024
        self._current_day = utc_day()
        self._current_part = 1
        self._snapshots_written_today = 0

    # ── Path helpers ────────────────────────────────────────────────────

    def day_file_path(self, day: str, part: int = 1) -> Path:
        suffix = "" if part == 1 else f".part{part}"
        return self.dir / f"replay-{day}{suffix}.jsonl.gz"

    def current_path(self) -> Path:
        # Reset part counter on day rollover
        if self._current_day != utc_day():
            self._current_day = utc_day()
            self._current_part = 1
            self._snapshots_written_today = 0
            self.cleanup_old_days()

        path = self.day_file_path(self._current_day, self._current_part)
        # Roll part if size exceeded
        if path.exists() and path.stat().st_size >= self.max_day_bytes:
            self._current_part += 1
            path = self.day_file_path(self._current_day, self._current_part)
        return path

    # ── Append ──────────────────────────────────────────────────────────

    def append_snapshot(self, snapshot: dict[str, Any]) -> int:
        path = self.current_path()
        n = append_gzip_jsonl(path, snapshot)
        self._snapshots_written_today += 1
        return n

    # ── Rolling retention ──────────────────────────────────────────────

    def cleanup_old_days(self) -> list[Path]:
        """Delete files older than retention_days. Returns deleted paths."""
        files = sorted(self.dir.glob("replay-*.jsonl.gz"))
        # Extract dates (replay-YYYY-MM-DD.jsonl.gz or .partN)
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).date()
        deleted = []
        for p in files:
            stem = p.name.replace("replay-", "").split(".")[0]  # YYYY-MM-DD (or with .partN suffix removed)
            try:
                d = datetime.strptime(stem, "%Y-%m-%d").date()
            except ValueError:
                continue
            if d < cutoff:
                try:
                    p.unlink()
                    deleted.append(p)
                except OSError:
                    pass
        # Also enforce total-size cap (oldest-first deletion)
        self._enforce_total_size_cap()
        return deleted

    def _enforce_total_size_cap(self) -> None:
        files = sorted(self.dir.glob("replay-*.jsonl.gz"))
        total = sum(p.stat().st_size for p in files)
        if total <= self.max_total_bytes:
            return
        # Delete oldest until under cap
        for p in files:
            if total <= self.max_total_bytes:
                break
            try:
                size = p.stat().st_size
                p.unlink()
                total -= size
            except OSError:
                continue

    # ── Read ────────────────────────────────────────────────────────────

    def all_snapshot_files(self) -> list[Path]:
        return sorted(self.dir.glob("replay-*.jsonl.gz"))

    def read_all_snapshots(self) -> Iterator[dict[str, Any]]:
        """Stream every snapshot from every file (chronological order)."""
        for p in self.all_snapshot_files():
            yield from read_gzip_jsonl(p)

    def read_recent_snapshots(self, n: int) -> list[dict[str, Any]]:
        """Last N snapshots across files (chronological)."""
        files = self.all_snapshot_files()
        if not files:
            return []
        # Try last file first; if fewer than n, walk backwards
        collected: list[dict[str, Any]] = []
        for p in reversed(files):
            file_snaps = list(read_gzip_jsonl(p))
            collected = file_snaps + collected
            if len(collected) >= n:
                return collected[-n:]
        return collected

    def total_size_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.all_snapshot_files())

    def total_snapshots(self) -> int:
        return sum(count_gzip_jsonl_lines(p) for p in self.all_snapshot_files())

    def integrity_report(self) -> dict[str, Any]:
        files = self.all_snapshot_files()
        total_bytes = sum(p.stat().st_size for p in files)
        return {
            "snapshots_dir":        str(self.dir),
            "file_count":           len(files),
            "files":                [
                {"name": p.name, "size_bytes": p.stat().st_size,
                 "size_human": file_size_human(p)}
                for p in files
            ],
            "total_size_bytes":     total_bytes,
            "total_size_mb":        round(total_bytes / 1024 / 1024, 3),
            "retention_days":       self.retention_days,
            "max_total_mb_cap":     self.max_total_bytes / 1024 / 1024,
            "max_day_file_mb_cap":  self.max_day_bytes / 1024 / 1024,
            "current_day":          self._current_day,
            "current_part":         self._current_part,
            "snapshots_written_today_session": self._snapshots_written_today,
        }


# ── Convenience factory from env vars ───────────────────────────────────────


def storage_from_env(default_dir: Path) -> ReplayStorage:
    return ReplayStorage(
        snapshots_dir=Path(os.environ.get("REPLAY_SNAPSHOTS_DIR", str(default_dir))),
        retention_days=int(os.environ.get("REPLAY_RETENTION_DAYS", "7")),
        max_total_mb=int(os.environ.get("REPLAY_MAX_TOTAL_MB", "100")),
        max_day_file_mb=int(os.environ.get("REPLAY_MAX_DAY_FILE_MB", "10")),
    )
