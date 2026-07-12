#!/usr/bin/env python3
"""
d6_autotrigger.py — automatic Phase A binding-run trigger.

Designed to be called every 30 minutes by a systemd timer from
Apr 30 onwards. Behaviour:

  1. Check the parquet collector's accumulated span
  2. If span < 120h → exit 0 (not yet), no notification
  3. If span ≥ 120h AND no prior trigger marker exists:
       a. Run d6_final_run.py (the orchestrator)
       b. Read the resulting D6_FINAL_VERDICT.md
       c. Push a 1-paragraph Telegram alert with the GO / NO-GO line
       d. Drop a marker file so we don't re-trigger
  4. If marker exists → exit 0 (already done)

This eliminates "did we remember to run it?" as a failure mode at the
single most important decision point of Phase A. Runs whatever the
verdict is; presumes nothing.

Lock file: /var/run/d6_autotrigger.lock (atomic create → exclusive run)
Marker:    <project>/D6_TRIGGERED.flag (touched on first successful run)
Logs:      /var/log/d6_autotrigger.log

Usage:
  python d6_autotrigger.py                # one-shot, called by systemd timer
  python d6_autotrigger.py --force        # ignore marker, re-run
  python d6_autotrigger.py --dry-run      # check only, don't run orchestrator
"""
from __future__ import annotations

import argparse
import datetime
import logging
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCK_PATH = Path("/var/run/d6_autotrigger.lock")
MARKER = ROOT / "D6_TRIGGERED.flag"
DEFAULT_DATA_DIR = "/var/log/microstructure"
TARGET_HOURS = 120.0
LOG = logging.getLogger("d6_autotrigger")


def setup_logging(verbose: bool):
    fmt = "%(asctime)s | %(levelname)-7s | %(message)s"
    handlers = [logging.StreamHandler()]
    log_file = Path("/var/log/d6_autotrigger.log")
    try:
        handlers.append(logging.FileHandler(log_file))
    except PermissionError:
        pass
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format=fmt, handlers=handlers)


def acquire_lock() -> Path | None:
    """Atomic O_EXCL create; returns the lock path on success, None if held."""
    try:
        fd = os.open(str(LOCK_PATH),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        return LOCK_PATH
    except FileExistsError:
        return None


def release_lock(path: Path | None):
    if path and path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def measure_span(data_dir: Path) -> tuple[float, int, int]:
    """Return (span_hours, n_pairs, total_rows)."""
    import pandas as pd
    files = sorted(data_dir.rglob("*.parquet"))
    if not files:
        return 0.0, 0, 0
    pairs: set[str] = set()
    rows = 0
    first = None
    last = None
    for f in files:
        pairs.add(f.stem)
        df = pd.read_parquet(f, columns=["ts_ms"])
        if df.empty:
            continue
        ts0, ts1 = df["ts_ms"].iloc[0] / 1000, df["ts_ms"].iloc[-1] / 1000
        first = ts0 if first is None else min(first, ts0)
        last = ts1 if last is None else max(last, ts1)
        rows += len(df)
    if first is None or last is None:
        return 0.0, len(pairs), rows
    return (last - first) / 3600.0, len(pairs), rows


def send_telegram(msg: str) -> bool:
    """Send a Telegram notification using the existing module."""
    try:
        sys.path.insert(0, str(ROOT))
        from telegram_alerts import notify  # type: ignore
        notify(msg)
        return True
    except Exception as e:
        LOG.warning(f"telegram notify failed: {e}")
        return False


def parse_verdict_summary(verdict_md: Path) -> str:
    """Pull the GO / NO-GO + lead-cell paragraph from the generated md."""
    if not verdict_md.exists():
        return "verdict file not found"
    text = verdict_md.read_text()
    # Find the "Phase B promotion verdict" section
    lines = text.splitlines()
    capture = False
    out: list[str] = []
    for line in lines:
        if line.startswith("## 4. Phase B promotion verdict"):
            capture = True
            continue
        if capture:
            if line.startswith("## "):
                break
            if line.strip():
                out.append(line)
    return "\n".join(out)[:1500]   # Telegram caps at ~4096 chars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--target-hours", type=float, default=TARGET_HOURS)
    ap.add_argument("--force", action="store_true",
                    help="ignore D6_TRIGGERED.flag marker, re-run anyway")
    ap.add_argument("--dry-run", action="store_true",
                    help="check span but don't run orchestrator")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    setup_logging(args.verbose)
    LOG.info(f"start, target={args.target_hours}h, force={args.force}, "
             f"dry_run={args.dry_run}")

    # 0. marker check
    if MARKER.exists() and not args.force:
        LOG.info(f"marker {MARKER} exists, exiting 0 (already triggered)")
        return 0

    # 1. lock
    lock = acquire_lock()
    if not lock:
        LOG.warning(f"another autotrigger holds {LOCK_PATH}, exiting 0")
        return 0
    try:
        # 2. measure
        span, n_pairs, rows = measure_span(Path(args.data_dir))
        LOG.info(f"span={span:.1f}h, pairs={n_pairs}, rows={rows:,d}")
        if span < args.target_hours:
            LOG.info(f"span below target ({span:.1f} < {args.target_hours}), "
                     f"not triggering")
            return 0
        if args.dry_run:
            LOG.info("dry-run mode, would trigger but exiting 0")
            return 0

        # 3. run orchestrator
        LOG.info(f"target reached ({span:.1f}h ≥ {args.target_hours}h), "
                 f"running d6_final_run.py")
        py = sys.executable
        venv = ROOT / "venv" / "bin" / "python"
        if venv.exists():
            py = str(venv)
        proc = subprocess.run(
            [py, str(ROOT / "d6_final_run.py"),
             "--data-dir", args.data_dir],
            cwd=str(ROOT),
            capture_output=True, text=True, timeout=1800,
        )
        LOG.info(f"d6_final_run.py exit={proc.returncode}")
        if proc.returncode != 0:
            tail = (proc.stdout + proc.stderr)[-1500:]
            LOG.error(f"orchestrator failed: {tail}")
            send_telegram(
                f"🛑 D6 auto-trigger ran orchestrator at "
                f"{datetime.datetime.utcnow().isoformat()}Z but it failed "
                f"with exit {proc.returncode}.\n\nLast lines:\n{tail[-800:]}")
            return proc.returncode

        # 4. read verdict, send Telegram
        verdict_md = ROOT / "D6_FINAL_VERDICT.md"
        summary = parse_verdict_summary(verdict_md)
        ts = datetime.datetime.utcnow().isoformat()
        is_go = "🟢 GO" in summary or "GO — Phase B candidate" in summary
        prefix = "🟢" if is_go else "🛑"
        msg = (f"{prefix} D6 BINDING VERDICT — {ts}Z\n"
               f"data: {span:.1f}h · {n_pairs} pairs · {rows:,} rows\n\n"
               f"{summary}\n\n"
               f"Full verdict: D6_FINAL_VERDICT.md")
        sent = send_telegram(msg)
        LOG.info(f"telegram sent: {sent}")

        # 5. drop marker
        MARKER.write_text(f"triggered at {ts}\nspan={span:.1f}h\n"
                          f"verdict={'GO' if is_go else 'NO-GO'}\n")
        LOG.info(f"marker written: {MARKER}")
        return 0

    finally:
        release_lock(lock)


if __name__ == "__main__":
    sys.exit(main())
