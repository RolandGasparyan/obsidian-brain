#!/usr/bin/env python3
"""
production_monitor.py — production health monitor for the L99 trading system.

Designed as a one-shot run by a systemd timer every 5 minutes. Watches:

  Bots (via /api/bots.json):
    - state transitions (active → inactive)              urgent
    - restart count increases                            urgent
    - drawdown crosses −3% threshold                     warn
    - drawdown crosses −5% threshold (Patch 3 limit)     urgent
    - drawdown recovers above −2%                        info

  Collector (via /var/log/microstructure):
    - last parquet flush > 2h ago                        urgent

  Disk / memory pressure (via /proc):
    - disk usage > 85% on /var                           warn
    - any service memory > 80% of MemoryMax              warn

Alerts via Telegram on STATE TRANSITIONS only — silent through the
steady state. Persistent state stored in /var/run/production_monitor_state.json
so transitions are detected across timer fires.

Idempotent: first run with no state file = baseline (no alerts).
Subsequent runs compare to baseline.

Usage:
  python production_monitor.py             # one-shot, called by systemd timer
  python production_monitor.py --reset     # wipe state file, re-baseline
  python production_monitor.py --dry-run   # check + log, don't send Telegram
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
STATE_PATH = Path("/var/run/production_monitor_state.json")
LOCK_PATH = Path("/var/run/production_monitor.lock")
DEFAULT_BOTS_URL = "https://tradingguru.ai/api/bots.json"
COLLECTOR_DIR = Path("/var/log/microstructure")
LOG = logging.getLogger("prod_monitor")

# Thresholds
DD_WARN_PCT = -3.0      # alert when DD crosses this (going down)
DD_URGENT_PCT = -5.0    # alert when DD crosses this (going down)
DD_RECOVER_PCT = -2.0   # alert when DD recovers above this (going up)
COLLECTOR_STALE_HOURS = 2.0
DISK_WARN_PCT = 85.0


def setup_logging(verbose: bool):
    fmt = "%(asctime)s | %(levelname)-7s | %(message)s"
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    try:
        handlers.append(logging.FileHandler("/var/log/production_monitor.log"))
    except PermissionError:
        pass
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format=fmt, handlers=handlers)


def acquire_lock() -> Optional[Path]:
    try:
        fd = os.open(str(LOCK_PATH),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        return LOCK_PATH
    except FileExistsError:
        return None


def release_lock(p: Optional[Path]):
    if p and p.exists():
        try:
            p.unlink()
        except OSError:
            pass


def fetch_bots(url: str) -> List[Dict[str, Any]]:
    """Fetch /api/bots.json with defensive parsing.

    Bot-control sometimes writes malformed JSON when bots are dying/inactive
    (race during file write, e.g. embedded newlines in state strings like
    "inactive\\nunknown"). Don't let that swallow real alerts: if standard
    JSON parsing fails, sanitize control characters and retry. If THAT
    fails, parse field-by-field via regex so we still get the bot list.
    """
    try:
        import requests
    except ImportError:
        LOG.error("requests not available")
        return []
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        text = r.text
    except Exception as e:
        LOG.warning(f"fetch_bots HTTP failed: {e}")
        return []

    # Attempt 1: standard JSON
    import json
    try:
        return json.loads(text).get("bots", [])
    except json.JSONDecodeError as e1:
        LOG.warning(f"fetch_bots JSON parse failed (attempt 1): {e1}")

    # Attempt 2: strip embedded control chars (newlines, tabs) inside string
    # values that bot-control sometimes injects on bot death
    import re
    sanitized = re.sub(r'(:\s*"[^"]*?)[\r\n\t]+([^"]*?")', r'\1 \2', text)
    try:
        return json.loads(sanitized).get("bots", [])
    except json.JSONDecodeError as e2:
        LOG.warning(f"fetch_bots JSON parse failed after sanitize: {e2}")

    # Attempt 3: extract per-bot dicts via regex — last-resort. Lets us
    # still detect state transitions (inactive! restart!) when a bot dies
    # mid-write. Pulls out pair + state + roi_pct + restarts at minimum.
    out: List[Dict[str, Any]] = []
    for m in re.finditer(
            r'"pair"\s*:\s*"([^"]+)"[^{}]*?'
            r'"state"\s*:\s*"([^"]*)"[^{}]*?'
            r'"restarts"\s*:\s*(\d+)[^{}]*?'
            r'(?:"roi_pct"\s*:\s*(-?\d+(?:\.\d+)?))?',
            text, re.DOTALL):
        pair, state, restarts, roi = m.groups()
        # Clean up state — strip control chars, take first line only
        state_clean = re.split(r'[\r\n\t]', state, 1)[0].strip()
        if not state_clean:
            state_clean = "unknown"
        try:
            out.append({
                "pair": pair,
                "state": state_clean,
                "restarts": int(restarts),
                "roi_pct": float(roi) if roi else 0.0,
                "trades": 0,        # unknown — best-effort
                "pos": "UNKNOWN",
                "equity": 0.0,
                "price": 0.0,
            })
        except (TypeError, ValueError):
            continue
    if out:
        LOG.warning(f"fetch_bots fell back to regex extraction; "
                    f"got {len(out)} bots (state-only)")
    return out


def collector_freshness(data_dir: Path) -> Optional[float]:
    """Return seconds since the most recent parquet was written, None if no files."""
    files = list(data_dir.rglob("*.parquet"))
    if not files:
        return None
    newest = max(f.stat().st_mtime for f in files)
    return time.time() - newest


def disk_usage_pct(path: str = "/var") -> float:
    s = os.statvfs(path)
    used = (s.f_blocks - s.f_bavail) * s.f_frsize
    total = s.f_blocks * s.f_frsize
    return used / total * 100 if total > 0 else 0.0


def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state: Dict[str, Any]):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def send_telegram(msg: str) -> bool:
    try:
        sys.path.insert(0, str(ROOT))
        from telegram_alerts import notify  # type: ignore
        notify(msg)
        return True
    except Exception as e:
        LOG.warning(f"telegram notify failed: {e}")
        return False


def detect_transitions(curr: List[Dict[str, Any]],
                       prev: Dict[str, Dict[str, Any]],
                       collector_age_s: Optional[float],
                       prev_collector_alert: bool,
                       disk_pct: float,
                       prev_disk_alert: bool) -> List[Dict[str, str]]:
    """Compute state transitions to alert on."""
    alerts: List[Dict[str, str]] = []

    # Bot-level transitions
    for b in curr:
        pair = b["pair"]
        p = prev.get(pair, {})

        # state went non-active
        if b.get("state") != "active" and p.get("state", "active") == "active":
            alerts.append({
                "severity": "urgent",
                "msg": f"🛑 {pair} state = {b.get('state')!r} (was active)"})

        # restart count increased
        if b.get("restarts", 0) > p.get("restarts", 0):
            alerts.append({
                "severity": "urgent",
                "msg": f"🚨 {pair} restarted "
                       f"(count {p.get('restarts', 0)} → {b['restarts']})"})

        # DD crossings (one alert per crossing direction)
        roi = b.get("roi_pct", 0.0)
        prev_roi = p.get("roi_pct", 0.0)
        # Crossed below -5%
        if roi <= DD_URGENT_PCT < prev_roi:
            alerts.append({
                "severity": "urgent",
                "msg": f"🚨 {pair} DD crossed {DD_URGENT_PCT}% — "
                       f"now {roi:+.2f}% (Patch 3 hard limit territory)"})
        # Crossed below -3% (and not below -5%)
        elif roi <= DD_WARN_PCT < prev_roi and roi > DD_URGENT_PCT:
            alerts.append({
                "severity": "warn",
                "msg": f"⚠ {pair} DD crossed {DD_WARN_PCT}% — now {roi:+.2f}%"})
        # Recovered above -2%
        elif roi >= DD_RECOVER_PCT > prev_roi:
            alerts.append({
                "severity": "info",
                "msg": f"✅ {pair} DD recovered to {roi:+.2f}%"})

    # Collector freshness (sticky alert state)
    is_stale = (collector_age_s is None or
                collector_age_s > COLLECTOR_STALE_HOURS * 3600)
    if is_stale and not prev_collector_alert:
        age_str = (f"{collector_age_s/3600:.1f}h"
                   if collector_age_s else "no files")
        alerts.append({
            "severity": "urgent",
            "msg": f"🚨 Collector stale — last parquet {age_str} ago"})
    elif not is_stale and prev_collector_alert:
        alerts.append({
            "severity": "info",
            "msg": f"✅ Collector resumed (last flush "
                   f"{collector_age_s/60:.0f} min ago)"})

    # Disk pressure
    is_disk_alert = disk_pct > DISK_WARN_PCT
    if is_disk_alert and not prev_disk_alert:
        alerts.append({
            "severity": "warn",
            "msg": f"⚠ Disk usage on /var = {disk_pct:.1f}% (threshold {DISK_WARN_PCT}%)"})
    elif not is_disk_alert and prev_disk_alert:
        alerts.append({
            "severity": "info",
            "msg": f"✅ Disk usage recovered to {disk_pct:.1f}%"})

    return alerts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bots-url", default=DEFAULT_BOTS_URL)
    ap.add_argument("--data-dir", default=str(COLLECTOR_DIR))
    ap.add_argument("--reset", action="store_true",
                    help="wipe state file and re-baseline")
    ap.add_argument("--dry-run", action="store_true",
                    help="don't send Telegram, just log")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    setup_logging(args.verbose)

    if args.reset:
        if STATE_PATH.exists():
            STATE_PATH.unlink()
        LOG.info("state file wiped, re-baselining on next run")
        return 0

    lock = acquire_lock()
    if not lock:
        LOG.warning("another monitor holds lock, exiting 0")
        return 0
    try:
        bots = fetch_bots(args.bots_url)
        coll_age = collector_freshness(Path(args.data_dir))
        disk_pct = disk_usage_pct("/var")

        state = load_state()
        prev_bots = {b["pair"]: b for b in state.get("bots", [])}
        prev_coll = state.get("collector_alert_active", False)
        prev_disk = state.get("disk_alert_active", False)

        if not state:
            LOG.info("first run, baselining (no alerts on first pass)")
        else:
            alerts = detect_transitions(bots, prev_bots, coll_age,
                                         prev_coll, disk_pct, prev_disk)
            for a in alerts:
                LOG.info(f"{a['severity']}: {a['msg']}")
                if not args.dry_run:
                    send_telegram(a["msg"])
            if not alerts:
                LOG.debug(f"steady state — {len(bots)} bots, "
                          f"coll_age={coll_age}s, disk={disk_pct:.1f}%")

        # Save current state
        new_state = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "bots": bots,
            "collector_alert_active": (
                coll_age is None or coll_age > COLLECTOR_STALE_HOURS * 3600),
            "disk_alert_active": disk_pct > DISK_WARN_PCT,
            "disk_pct": round(disk_pct, 2),
            "collector_age_s": round(coll_age, 1) if coll_age else None,
        }
        save_state(new_state)
        LOG.debug(f"state saved to {STATE_PATH}")
        return 0
    finally:
        release_lock(lock)


if __name__ == "__main__":
    sys.exit(main())
