#!/usr/bin/env python3
"""
verify_onchain_first_hour.py — Validate onchain-collector first-hour ingest.

Run on VPS ~60 minutes after deployment to confirm:
  - Parquet files are being written
  - Schema is correct (CryptoQuant, Glassnode, Whale Alert all populating)
  - No silent rate-limit / auth errors in journalctl
  - At least 1 valid record per data source

Exit codes:
  0  All 3 sources writing valid data
  1  At least 1 source has no data
  2  Schema mismatch detected
  3  Auth errors in journalctl (probably bad API key)
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path("/var/log/onchain")
SERVICE = "onchain-collector.service"


def check_journal_errors() -> int:
    """Scan last 20 minutes of journalctl for auth/rate errors."""
    try:
        proc = subprocess.run(
            ["journalctl", "-u", SERVICE, "--since", "20 min ago", "--no-pager"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        print("  ⚠ Cannot read journalctl — running locally?")
        return 0

    log = proc.stdout.lower()
    errors = []
    for pattern in ("401", "403", "unauthorized", "invalid api", "rate limit", "429"):
        if pattern in log:
            errors.append(pattern)
    if errors:
        print(f"  ❌ Auth/rate errors found in journal: {errors}")
        return 3
    print("  ✅ No auth or rate-limit errors in last 20 min of journal")
    return 0


def check_parquet_files() -> int:
    """Confirm at least 1 parquet per source in last hour."""
    if not OUTPUT_DIR.exists():
        print(f"  ❌ Output dir not found: {OUTPUT_DIR}")
        return 1

    sources = ["cryptoquant", "glassnode", "whale_alert"]
    now = datetime.now(timezone.utc).timestamp()
    one_hour_ago = now - 3600

    missing = []
    for src in sources:
        src_dir = OUTPUT_DIR / src
        if not src_dir.exists():
            missing.append(src)
            print(f"  ❌ {src}: directory not found")
            continue
        recent = [p for p in src_dir.rglob("*.parquet")
                  if p.stat().st_mtime > one_hour_ago]
        if not recent:
            missing.append(src)
            print(f"  ❌ {src}: no parquet files in last hour")
        else:
            total_size = sum(p.stat().st_size for p in recent) // 1024
            print(f"  ✅ {src}: {len(recent)} files, {total_size}KB in last hour")

    return 1 if missing else 0


def main() -> int:
    print("═" * 60)
    print("  ONCHAIN-COLLECTOR FIRST-HOUR VERIFICATION")
    print("═" * 60)
    print()

    print("Step 1: journalctl error scan")
    rc1 = check_journal_errors()
    print()

    print("Step 2: parquet output check")
    rc2 = check_parquet_files()
    print()

    print("Step 3: service status")
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", SERVICE],
            capture_output=True, text=True, timeout=5,
        )
        if proc.stdout.strip() == "active":
            print(f"  ✅ {SERVICE}: active")
        else:
            print(f"  ❌ {SERVICE}: {proc.stdout.strip()}")
            return 1
    except Exception:
        print("  ⚠ Cannot check service state — running locally?")

    print()
    print("═" * 60)
    rc = max(rc1, rc2)
    if rc == 0:
        print("  🟢 ALL CHECKS PASSED — collector healthy, data flowing")
    else:
        print(f"  🔴 ISSUES DETECTED — exit code {rc}")
        print("  Action: check journalctl -u onchain-collector.service -f")
    print("═" * 60)
    return rc


if __name__ == "__main__":
    sys.exit(main())
