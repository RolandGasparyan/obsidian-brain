#!/usr/bin/env python3
"""
shadow_battle_runner.py — PHASE TITAN top-3 champion shadow battle

🎬 Paper-safe esports broadcast of top-3 paper-arena champions
   competing for virtual sub-account supremacy.

🛡 SAFETY GUARANTEES (hard-enforced at startup):
   ✓ TG_DISABLE_REAL_ORDERS=1 (refuses to start otherwise)
   ✓ TG_PAPER_EXECUTION=1     (refuses to start otherwise)
   ✓ LIVE_ORDERS=0            (refuses to start otherwise)
   ✗ NEVER reads .api_key
   ✗ NEVER opens exchange write sockets
   ✗ NEVER touches /root/canary/ or Layer 1 code
   ✗ NEVER calls real exchange APIs
   ✓ Only reads: paper-arena.json (already published locally)

Output: /var/www/.../api/battle/shadow-battle.json
        (3 virtual sub-accounts · top-3 champion assignments · equity curves)

Refresh: every 15s default (TG_UPDATE_INTERVAL env)
Selection: re-evaluates top-3 every 60s (champions can shift)
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

# ── Path setup ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from champion_selector import select_top_n, selection_summary
from virtual_subaccount import VirtualSubaccount, make_subaccounts, save_state


# ── Hard safety guard ───────────────────────────────────────────────────────


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


TG_DISABLE_REAL_ORDERS = _env_int("TG_DISABLE_REAL_ORDERS", 1)
TG_PAPER_EXECUTION     = _env_int("TG_PAPER_EXECUTION", 1)
TG_SAFE_MODE           = _env_int("TG_SAFE_MODE", 1)
LIVE_ORDERS            = _env_int("LIVE_ORDERS", 0)

if TG_DISABLE_REAL_ORDERS != 1 or TG_PAPER_EXECUTION != 1 or LIVE_ORDERS != 0:
    sys.stderr.write(
        "❌ REFUSED: shadow_battle_runner.py is PAPER-SAFE only.\n"
        f"   Required env: TG_DISABLE_REAL_ORDERS=1  TG_PAPER_EXECUTION=1  LIVE_ORDERS=0\n"
        f"   Got: TG_DISABLE_REAL_ORDERS={TG_DISABLE_REAL_ORDERS}  "
        f"TG_PAPER_EXECUTION={TG_PAPER_EXECUTION}  LIVE_ORDERS={LIVE_ORDERS}\n"
        "   This service NEVER opens exchange sockets · NEVER reads .api_key.\n"
        "   See: governance/MICRO_LIVE_OPERATOR_CHECKLIST.md for live-mode path.\n"
    )
    sys.exit(2)


# ── Config ──────────────────────────────────────────────────────────────────

UPDATE_INTERVAL_SEC = _env_int("TG_UPDATE_INTERVAL", 15)
SELECTION_REFRESH_SEC = _env_int("TG_SELECTION_REFRESH_SEC", 60)
VIRTUAL_SUBS = _env_int("TG_VIRTUAL_SUBS", 3)
VIRTUAL_BALANCE_PER_AGENT = _env_float("TG_VIRTUAL_BALANCE_PER_AGENT", 200.0)
AUTO_SELECT_TOP3 = _env_int("TG_AUTO_SELECT_TOP3", 1)
ARENA_MODE = os.environ.get("TG_ARENA_MODE", "STANDARD")  # OMEGA · STANDARD
VISUAL_INTENSITY = os.environ.get("TG_VISUAL_INTENSITY", "NORMAL")  # MAX · HIGH · NORMAL

# Source data paths
PAPER_ARENA_CANDIDATES = [
    Path("/var/www/ai-trading-championship/dist/api/battle/paper-arena.json"),
    ROOT.parent / "runtime" / "paper-arena.json",
]

# Output paths
OUTPUT_PUBLISH_DIR = Path(os.environ.get(
    "REPLAY_PUBLISH_DIR",
    "/var/www/ai-trading-championship/dist/api/battle"
))
STATE_FILE = ROOT / "snapshots" / "shadow_battle_state.json"


# ── Source readers ──────────────────────────────────────────────────────────


def fetch_paper_arena() -> dict[str, Any]:
    for p in PAPER_ARENA_CANDIDATES:
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                continue
    return {}


# ── Main loop ───────────────────────────────────────────────────────────────


_STOP = False


def _handle_stop(*_: object) -> None:
    global _STOP
    _STOP = True


def run() -> int:
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    pid_file = ROOT / "snapshots" / "shadow_battle.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))

    print("⚔️ PHASE TITAN · TOP-3 SHADOW BATTLE")
    print(f"   mode               : {ARENA_MODE}")
    print(f"   visual intensity   : {VISUAL_INTENSITY}")
    print(f"   virtual subs       : {VIRTUAL_SUBS} × ${VIRTUAL_BALANCE_PER_AGENT}")
    print(f"   update interval    : {UPDATE_INTERVAL_SEC}s")
    print(f"   selection refresh  : every {SELECTION_REFRESH_SEC}s")
    print(f"   output             : {OUTPUT_PUBLISH_DIR}/shadow-battle.json")
    print("   ✓ TG_DISABLE_REAL_ORDERS=1 · TG_PAPER_EXECUTION=1 · LIVE_ORDERS=0")
    print(f"   PID                : {os.getpid()}")
    print()

    subs: list[VirtualSubaccount] = []
    current_champions: list[dict] = []
    last_selection_ts: float = 0.0
    tick = 0
    started_at_ts = time.time()

    try:
        while not _STOP:
            tick += 1
            now = time.time()

            arena = fetch_paper_arena()
            agents = arena.get("agents") or arena.get("leaderboard") or []

            # Re-evaluate top-3 every SELECTION_REFRESH_SEC
            need_select = (
                not current_champions
                or (now - last_selection_ts) >= SELECTION_REFRESH_SEC
            )
            if agents and need_select:
                new_top = select_top_n(agents, n=VIRTUAL_SUBS)
                if new_top:
                    # If champions changed, build new sub-accounts
                    new_names = [c["name"] for c in new_top]
                    old_names = [s.assigned_agent_name for s in subs]
                    if new_names != old_names:
                        # Preserve balances if same agent re-elected at same rank
                        new_subs = make_subaccounts(new_top, balance_per_sub=VIRTUAL_BALANCE_PER_AGENT)
                        for ns in new_subs:
                            # Try to find prior sub with same agent
                            prior = next((s for s in subs
                                          if s.assigned_agent_name == ns.assigned_agent_name), None)
                            if prior:
                                ns.current_balance = prior.current_balance
                                ns.peak_balance = prior.peak_balance
                                ns.realized_pnl = prior.realized_pnl
                                ns.equity_curve = prior.equity_curve
                                ns.trades_mirrored = prior.trades_mirrored
                                ns._baseline_agent_pnl = getattr(prior, "_baseline_agent_pnl", 0.0)
                        subs = new_subs
                    current_champions = new_top
                    last_selection_ts = now
                    print(f"  ⚔ champion roster refreshed @ t+{int(now - started_at_ts)}s:")
                    for c in current_champions:
                        print(f"      #{c['rank']}  {c['name']:20s} ({c['role']:9s})  "
                              f"L{c['level']} · XP {c['xp']:5d} · score {c['composite_score']:.3f}")

            # Mirror per-champion PnL into virtual subaccounts (safe-coerce types)
            for sub in subs:
                agent = next((a for a in agents
                              if (a.get("full_name") or a.get("name") or "") == sub.assigned_agent_name),
                             None)
                if agent is None:
                    continue
                pnl_raw = agent.get("simulated_pnl_usd")
                try:
                    agent_pnl = float(pnl_raw) if pnl_raw is not None and not isinstance(pnl_raw, dict) else 0.0
                except (TypeError, ValueError):
                    agent_pnl = 0.0
                agent_in_trade = bool(agent.get("in_trade") or False)
                sub.mirror_agent_pnl(agent_pnl, agent_in_trade, now)

            # Build output payload
            payload = build_payload(subs, current_champions, started_at_ts, tick, arena)

            # Write to nginx-served + local snapshot
            try:
                OUTPUT_PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
                (OUTPUT_PUBLISH_DIR / "shadow-battle.json").write_text(
                    json.dumps(payload, indent=2, default=str)
                )
            except OSError as e:
                if tick == 1:
                    print(f"  ⚠ publish failed: {e}")

            # Persist state
            try:
                save_state(subs, STATE_FILE)
            except Exception:
                pass

            # Heartbeat
            if tick % 4 == 0 or tick <= 2:
                top_sub = max(subs, key=lambda s: s.current_balance, default=None)
                top_label = (f"{top_sub.assigned_agent_name}=${top_sub.current_balance:.2f}"
                             if top_sub else "(none)")
                print(f"  ⚡ tick={tick} subs={len(subs)} top={top_label} "
                      f"mode={ARENA_MODE}/{VISUAL_INTENSITY}")

            time.sleep(UPDATE_INTERVAL_SEC)

    finally:
        try:
            pid_file.unlink()
        except OSError:
            pass
        print()
        print(f"⚔ shadow_battle stopped after {tick} ticks")

    return 0


def build_payload(
    subs: list[VirtualSubaccount],
    champions: list[dict],
    started_at_ts: float,
    tick: int,
    arena: dict,
) -> dict[str, Any]:
    return {
        "tg_safe":               True,
        "live_orders":           0,
        "tg_disable_real_orders":True,
        "_note":                 "VIRTUAL ALLOCATION · paper-safe shadow battle",
        "phase":                 "TITAN",
        "arena_mode":            ARENA_MODE,
        "visual_intensity":      VISUAL_INTENSITY,
        "tick":                  tick,
        "started_at_ts":         started_at_ts,
        "elapsed_seconds":       round(time.time() - started_at_ts, 1),
        "update_interval_sec":   UPDATE_INTERVAL_SEC,
        "champions":             champions,
        "selection_summary":     selection_summary(champions),
        "virtual_subaccounts":   [s.to_dict() for s in subs],
        "totals": {
            "starting_capital_total_usdt": sum(s.start_balance for s in subs),
            "current_capital_total_usdt":  round(sum(s.current_balance for s in subs), 4),
            "aggregate_pnl_usdt":          round(sum(s.realized_pnl for s in subs), 4),
            "subs_active":                 sum(1 for s in subs if s.state == "active"),
            "subs_frozen":                 sum(1 for s in subs if s.state == "frozen-dd"),
            "subs_triumph":                sum(1 for s in subs if s.state == "triumph"),
        },
        "arena_cycle":           arena.get("cycle"),
        "arena_mode_engine":     arena.get("mode"),
    }


if __name__ == "__main__":
    sys.exit(run())
