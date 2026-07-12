#!/usr/bin/env python3
"""
champion_selector.py — picks top-N agents from paper-arena.json

🛡 PAPER-SAFE · READ-ONLY · pure scoring math on telemetry.

Composite metric (weighted):
    score = 0.35 · xp_norm
          + 0.25 · winrate_norm
          + 0.20 · sharpe_norm
          + 0.20 · stability_norm

Where:
    xp_norm        agent.xp / max_xp
    winrate_norm   agent.win_rate (already 0-1)
    sharpe_norm    sigmoid(agent.sharpe_sim) (saturating-positive)
    stability_norm 1 - agent.behavioral_drift  (if present, else 0.5)

API:
    top3 = select_top_n(agents_list, n=3)
    → list[{rank, agent, composite_score, components}]
"""

from __future__ import annotations

import math
from typing import Any


# Default selection metrics (operator override via env in runner)
DEFAULT_METRICS = ["xp", "winrate", "sharpe", "stability"]

WEIGHTS = {
    "xp":        0.35,
    "winrate":   0.25,
    "sharpe":    0.20,
    "stability": 0.20,
}


def _sigmoid(x: float) -> float:
    """Sigmoid · maps real number to (0, 1) · saturating-positive."""
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def _resolve_name(agent: dict) -> str:
    return (agent.get("full_name")
            or agent.get("name")
            or agent.get("character_name")
            or agent.get("codename")
            or agent.get("label")
            or agent.get("role")
            or "?")


def _resolve_role(agent: dict) -> str:
    return (agent.get("codename")
            or agent.get("label")
            or agent.get("role")
            or agent.get("archetype")
            or "AGENT").upper()


def _safe_float(v, default: float = 0.0) -> float:
    """Coerce mixed-type values (dict / list / None / str) to float."""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        # Engine may expose {score: 0.05, ...} structures — try common keys
        for k in ("score", "value", "current", "level"):
            if k in v:
                return _safe_float(v[k], default)
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def score_agent(agent: dict, max_xp: float) -> dict[str, Any]:
    """Compute composite score for one agent. max_xp passed to normalize."""
    xp = _safe_float(agent.get("xp") or agent.get("level_xp"))
    win_rate = _safe_float(agent.get("win_rate"))
    sharpe = _safe_float(agent.get("sharpe_sim") or agent.get("sharpe"))
    drift = _safe_float(agent.get("behavioral_drift"))

    xp_norm = (xp / max_xp) if max_xp > 0 else 0.0
    winrate_norm = max(0.0, min(1.0, win_rate))
    sharpe_norm = _sigmoid(sharpe / 2.0)
    stability_norm = max(0.0, min(1.0, 1.0 - drift))

    components = {
        "xp_norm":        round(xp_norm, 4),
        "winrate_norm":   round(winrate_norm, 4),
        "sharpe_norm":    round(sharpe_norm, 4),
        "stability_norm": round(stability_norm, 4),
    }
    composite = (
        WEIGHTS["xp"]        * xp_norm +
        WEIGHTS["winrate"]   * winrate_norm +
        WEIGHTS["sharpe"]    * sharpe_norm +
        WEIGHTS["stability"] * stability_norm
    )
    return {
        "agent_id":      agent.get("id") or _resolve_role(agent),
        "name":          _resolve_name(agent),
        "role":          _resolve_role(agent),
        "level":         agent.get("level", 1),
        "xp":            int(xp),
        "title":         (agent.get("current_titles") or [None])[0] or agent.get("title"),
        "color":         agent.get("color"),
        "icon":          agent.get("icon"),
        "personality":   agent.get("personality_type"),
        "backstory":     agent.get("backstory"),
        "composite_score": round(composite, 4),
        "components":    components,
        "raw_stats": {
            "xp":           int(xp),
            "win_rate":     round(win_rate, 4),
            "sharpe_sim":   round(sharpe, 4),
            "behavioral_drift": round(drift, 4),
            "wins":         _safe_float(agent.get("wins")),
            "losses":       _safe_float(agent.get("losses")),
            "consecutive_wins": _safe_float(agent.get("consecutive_wins")),
            "discipline_score": _safe_float(agent.get("discipline_score")),
        },
    }


def select_top_n(
    agents: list[dict[str, Any]],
    n: int = 3,
    metrics: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Pick top-N agents by composite score.

    Args:
        agents:  list of agent dicts from paper-arena.json
        n:       how many to pick (default 3)
        metrics: optional override list (currently informational · weights fixed
                 in this version per spec discipline)

    Returns:
        list of length min(n, len(agents)) · ranked 1..n · richest profile data
    """
    if not agents:
        return []
    max_xp = max(
        (float(a.get("xp") or a.get("level_xp") or 0) for a in agents),
        default=1.0,
    )
    if max_xp <= 0:
        max_xp = 1.0

    scored = [score_agent(a, max_xp) for a in agents]
    scored.sort(key=lambda s: s["composite_score"], reverse=True)

    top = scored[:n]
    for i, entry in enumerate(top):
        entry["rank"] = i + 1
    return top


def selection_summary(top: list[dict]) -> dict[str, Any]:
    """Compact summary suitable for index/header rendering."""
    return {
        "champion_count": len(top),
        "champions": [
            {
                "rank":  c["rank"],
                "name":  c["name"],
                "role":  c["role"],
                "level": c["level"],
                "xp":    c["xp"],
                "title": c["title"],
                "composite_score": c["composite_score"],
                "color": c["color"],
                "icon":  c["icon"],
            }
            for c in top
        ],
        "metrics_used": DEFAULT_METRICS,
        "weights": WEIGHTS,
    }
