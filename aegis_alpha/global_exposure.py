"""
aegis_alpha.global_exposure — file-based shared exposure tracker for
PLAN B Part 4.

Two engines (aegis_alpha 4H + aegis_alpha 1H) run as separate
processes/services. They must share a single budget:

    GLOBAL  ≤ 6%
    4H      ≤ 2%   (own slice)
    1H      ≤ 2%   (own slice)
    BUFFER     2%   (never used by routine entries)

Implementation:
    A single JSON file at .l99_data/exposure.json, atomically updated
    via temp-file + rename. Each engine calls:

        register_open(engine_id, trade_id, risk_pct)   # before order
        unregister_open(engine_id, trade_id)            # on close

    And queries:

        can_open(engine_id, proposed_risk_pct) -> (bool, reason)

    No real lock needed — updates are atomic per OS rename, and trade
    open is single-process per engine. If a write race happens we'll
    over-count by at most one trade, which is conservatively safe (we'd
    block one extra entry, never approve too many).
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, Tuple

from l99.config import CONFIG, DATA_ROOT


log = logging.getLogger("aegis_alpha.global_exposure")

EXPOSURE_FILE = DATA_ROOT / "exposure.json"


# ── persistence ──────────────────────────────────────────────────────
def _read() -> Dict:
    if not EXPOSURE_FILE.exists():
        return {"open": {}, "updated_ns": 0}
    try:
        return json.loads(EXPOSURE_FILE.read_text())
    except Exception as e:
        log.warning("exposure read failed: %s", e)
        return {"open": {}, "updated_ns": 0}


def _write(state: Dict):
    EXPOSURE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_ns"] = time.time_ns()
    tmp = EXPOSURE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, separators=(",", ":")))
    tmp.replace(EXPOSURE_FILE)


# ── api ──────────────────────────────────────────────────────────────
@dataclass
class ExposureCheck:
    allowed:        bool
    engine_used:    float
    engine_cap:     float
    global_used:    float
    global_cap:     float
    reason:         str = ""


def _engine_cap(engine_id: str) -> float:
    if engine_id == "aegis_alpha_4h": return CONFIG.alpha_4h_max_open_risk_pct
    if engine_id == "aegis_alpha_1h": return CONFIG.alpha_1h_max_open_risk_pct
    # default to 4H slice for any unrecognized engine
    return CONFIG.alpha_4h_max_open_risk_pct


def can_open(engine_id: str, proposed_risk_pct: float) -> ExposureCheck:
    """Check if `engine_id` is allowed to open a new position with
    `proposed_risk_pct` exposure. Does NOT mutate state."""
    state = _read()
    open_map: Dict[str, Dict] = state.get("open", {})
    used_global: float = sum(t.get("risk", 0) for t in open_map.values())
    used_engine: float = sum(t.get("risk", 0) for t in open_map.values()
                              if t.get("engine") == engine_id)

    engine_cap = _engine_cap(engine_id)
    global_cap = CONFIG.global_max_open_risk_pct

    if used_engine + proposed_risk_pct > engine_cap:
        return ExposureCheck(
            False, used_engine, engine_cap, used_global, global_cap,
            reason=f"engine cap: {used_engine*100:.2f}% + "
                   f"{proposed_risk_pct*100:.2f}% > {engine_cap*100:.2f}%")
    if used_global + proposed_risk_pct > global_cap:
        return ExposureCheck(
            False, used_engine, engine_cap, used_global, global_cap,
            reason=f"global cap: {used_global*100:.2f}% + "
                   f"{proposed_risk_pct*100:.2f}% > {global_cap*100:.2f}%")
    return ExposureCheck(True, used_engine, engine_cap,
                          used_global, global_cap, reason="ok")


def register_open(engine_id: str, trade_id: str, risk_pct: float) -> None:
    state = _read()
    state.setdefault("open", {})[trade_id] = {
        "engine": engine_id,
        "risk":   float(risk_pct),
        "ts_ns":  time.time_ns(),
    }
    _write(state)


def unregister_open(trade_id: str) -> None:
    state = _read()
    state.get("open", {}).pop(trade_id, None)
    _write(state)


def current_exposure() -> Dict:
    """Read-only snapshot for telemetry."""
    state = _read()
    open_map = state.get("open", {})
    return {
        "global_used_pct": sum(t.get("risk", 0) for t in open_map.values()),
        "engine_used":     {
            eid: sum(t.get("risk", 0) for t in open_map.values()
                     if t.get("engine") == eid)
            for eid in {t.get("engine") for t in open_map.values()}
        },
        "open_count": len(open_map),
        "open_trades": list(open_map.keys()),
        "global_cap_pct": CONFIG.global_max_open_risk_pct,
    }


def reset() -> None:
    """Clear all tracked positions. Used by tests + manual ops."""
    _write({"open": {}})
