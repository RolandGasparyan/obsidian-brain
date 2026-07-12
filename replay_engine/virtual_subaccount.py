#!/usr/bin/env python3
"""
virtual_subaccount.py — simulates 3 virtual sub-accounts for SHADOW BATTLE

🛡 PAPER-SAFE · VIRTUAL ALLOCATION ONLY · zero real exchange interaction.

Each virtual sub-account tracks:
    - Starting balance (default 200 USDT virtual)
    - Realized PnL from assigned agent's trades (mirrored from paper-arena)
    - Equity curve over time
    - Position state (in_trade / flat)
    - Discipline status (drawdown band)

This is NOT real exchange capital. The "balance" is a derivative computed
from the assigned agent's simulated PnL in paper_battle_engine v1.2.

Used by shadow_battle_runner.py to maintain 3-sub state alongside paper engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Constants ─────────────────────────────────────────────────────────────


DEFAULT_BALANCE = 200.0
DEFAULT_DD_CAP_PCT = 5.0     # virtual auto-freeze if balance drops > 5%
DEFAULT_PROFIT_CAP_PCT = 25.0  # virtual triumph-trigger if > 25%


# ── Subaccount state model ────────────────────────────────────────────────


@dataclass
class VirtualSubaccount:
    sub_id: str
    assigned_agent_name: str
    assigned_agent_role: str
    start_balance: float = DEFAULT_BALANCE
    current_balance: float = DEFAULT_BALANCE
    peak_balance: float = DEFAULT_BALANCE
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    state: str = "active"   # active | frozen-dd | triumph
    freeze_reason: str | None = None
    trades_mirrored: int = 0
    last_update_ts: float = 0.0

    @property
    def pnl_pct(self) -> float:
        if self.start_balance <= 0:
            return 0.0
        return (self.current_balance - self.start_balance) / self.start_balance * 100.0

    @property
    def drawdown_pct(self) -> float:
        if self.peak_balance <= 0:
            return 0.0
        return (self.peak_balance - self.current_balance) / self.peak_balance * 100.0

    def mirror_agent_pnl(
        self,
        agent_realized_pnl: float,
        agent_in_trade: bool,
        ts: float,
    ) -> dict[str, Any]:
        """
        Mirror the assigned agent's PnL into this virtual sub-account.

        Allocation: each virtual sub starts with $200 and scales the agent's
        simulated PnL (as a %) onto that base. Agent has its own arbitrary
        equity curve in paper-arena · we treat it as a return stream and
        re-base it onto $200 for this virtual sub.
        """
        # First update — establish baseline
        if self.last_update_ts == 0:
            self._baseline_agent_pnl = agent_realized_pnl
        baseline = getattr(self, "_baseline_agent_pnl", agent_realized_pnl)
        relative_pnl = agent_realized_pnl - baseline

        # Apply 1:1 ratio for simplicity (real-world would scale by leverage)
        delta_usdt = relative_pnl
        new_balance = self.start_balance + delta_usdt
        new_balance = max(0.0, new_balance)

        self.realized_pnl = delta_usdt
        self.current_balance = new_balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
        self.last_update_ts = ts
        self.trades_mirrored += 1 if agent_in_trade else 0

        # Discipline check
        if self.drawdown_pct >= DEFAULT_DD_CAP_PCT and self.state == "active":
            self.state = "frozen-dd"
            self.freeze_reason = f"virtual DD {self.drawdown_pct:.2f}% >= cap {DEFAULT_DD_CAP_PCT}%"
        elif self.pnl_pct >= DEFAULT_PROFIT_CAP_PCT and self.state == "active":
            self.state = "triumph"
            self.freeze_reason = f"virtual profit {self.pnl_pct:.2f}% >= triumph {DEFAULT_PROFIT_CAP_PCT}%"

        # Equity curve tail (last 60 points · ~10 min @ 10s)
        self.equity_curve.append({
            "t": ts,
            "b": round(new_balance, 4),
            "pnl": round(delta_usdt, 4),
        })
        if len(self.equity_curve) > 60:
            self.equity_curve = self.equity_curve[-60:]

        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sub_id":              self.sub_id,
            "assigned_agent":      self.assigned_agent_name,
            "assigned_agent_role": self.assigned_agent_role,
            "start_balance_usdt":  self.start_balance,
            "current_balance_usdt": round(self.current_balance, 4),
            "peak_balance_usdt":   round(self.peak_balance, 4),
            "realized_pnl_usdt":   round(self.realized_pnl, 4),
            "pnl_pct":             round(self.pnl_pct, 3),
            "drawdown_pct":        round(self.drawdown_pct, 3),
            "state":               self.state,
            "freeze_reason":       self.freeze_reason,
            "trades_mirrored":     self.trades_mirrored,
            "last_update_ts":      self.last_update_ts,
            "equity_curve_points": len(self.equity_curve),
            "equity_curve_tail":   self.equity_curve[-10:],   # last 10 points for UI
            "tg_safe":             True,
            "_note":               "VIRTUAL ALLOCATION ONLY · no real exchange capital",
        }


# ── Factory ───────────────────────────────────────────────────────────────


def make_subaccounts(
    top_champions: list[dict[str, Any]],
    balance_per_sub: float = DEFAULT_BALANCE,
) -> list[VirtualSubaccount]:
    """
    Build N virtual sub-accounts, one per champion in top_champions.
    """
    return [
        VirtualSubaccount(
            sub_id=f"VSUB_{c['rank']:02d}_{c['role']}",
            assigned_agent_name=c["name"],
            assigned_agent_role=c["role"],
            start_balance=balance_per_sub,
            current_balance=balance_per_sub,
            peak_balance=balance_per_sub,
        )
        for c in top_champions
    ]


# ── State persistence (survives restart) ──────────────────────────────────


def save_state(subs: list[VirtualSubaccount], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tg_safe": True,
        "_note": "VIRTUAL ALLOCATION ONLY · paper-safe",
        "subaccounts": [s.to_dict() for s in subs],
    }
    path.write_text(json.dumps(payload, indent=2, default=str))


def load_state(path: Path) -> list[dict[str, Any]] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data.get("subaccounts")
    except Exception:
        return None
