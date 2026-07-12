"""
l99.publish_status — emit a JSON status blob to a path nginx can serve.

Run from cron every minute:
    * * * * * root /var/www/.../venv/bin/python -m l99.publish_status

The blob aggregates the latest snapshots from every engine + viability
metrics from the journals + system flags. Frontend dashboard reads it
at /api/l99-status.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from l99.config import CONFIG, EngineId, EnginePaths, DATA_ROOT


def gather() -> dict:
    out = {
        "generated_at_ns": time.time_ns(),
        "starting_equity": CONFIG.starting_equity,
        "killed":          (DATA_ROOT / "KILL_ALL").exists(),
        "engines":         {},
    }
    for eid in EngineId:
        paths = EnginePaths.for_engine(eid)
        block = {
            "enabled":  CONFIG.is_engine_enabled(eid),
            "snapshot": None,
            "viability": None,
        }
        if paths.snapshot.exists():
            try:
                block["snapshot"] = json.loads(paths.snapshot.read_text())
                block["snapshot_age_s"] = int(
                    time.time() - paths.snapshot.stat().st_mtime)
            except Exception as e:
                block["snapshot_error"] = str(e)
        # Viability metrics (if journal exists and module importable)
        if paths.journal.exists():
            try:
                from champion.journal import TradeJournal
                j = TradeJournal(paths.journal)
                m = j.compute_metrics(window=50, engine=eid.value)
                j.close()
                block["viability"] = {
                    "n_trades":        m.n_trades,
                    "win_rate":        m.win_rate,
                    "ev_per_trade":    m.ev_per_trade,
                    "profit_factor":   (None if not (m.profit_factor and m.profit_factor < float("inf"))
                                          else m.profit_factor),
                    "max_consec_loss": m.max_consec_losses,
                    "is_viable":       m.is_viable,
                    "fail_reasons":    m.fail_reasons,
                }
            except Exception as e:
                block["viability_error"] = str(e)
        out["engines"][eid.value] = block
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                     default="/var/www/ai-trading-championship/dist/api/l99-status.json")
    args = ap.parse_args()
    blob = gather()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(blob, indent=2, default=str))
    tmp.replace(out)
    # Also emit to stdout for cron logs
    sys.stdout.write(f"l99-status published → {out} ({len(json.dumps(blob))} bytes)\n")


if __name__ == "__main__":
    main()
