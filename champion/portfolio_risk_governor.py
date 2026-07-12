"""
champion.portfolio_risk_governor — Layer 5 §6 Portfolio Risk Governor.

Implements the Portfolio Risk Governor as described in
docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md §6 and the operator's
2026-05-01 paste.

Edge-independent capital protection. Pure math + state machine.
NO exchange wiring. NO strategy dependency.

Authoritative rule per spec:

    Risk > Alpha

The governor enforces:
  - Max total exposure          (default 8% of equity)
  - Max single position size    (default 1.2%)
  - Sector correlation cap      (default 4% per cluster)
  - Daily R circuit breaker     (default −3R closes the day)
  - Weekly R circuit breaker    (default −6R closes the week)
  - Drawdown kill switch        (default −25% from peak)
  - Optional regime multiplier  (set externally; default 1.0)

API surface:
  - register_trade_result(r_multiple) → updates today/week R, may set kill
  - update_equity(new_equity)         → tracks equity peak, may set kill
  - approve_new_position(symbol, fr)  → True if cap budget allows
  - open_position(symbol, fr)         → records open exposure
  - close_position(symbol)            → removes exposure
  - set_sector(symbol, sector)        → maps a symbol to a correlation cluster
  - force_kill() / reset_kill()       → manual override
  - status()                          → snapshot dict

Per ADR-001 + ADR-003 (D7 expired): this module is library-only. It does
not call any exchange API and does not transition any live bot. Wiring it
into `gateio_executor.py` requires:
    1. A validated edge (B.2.3 on-chain or other B-prime branch)
    2. 4-gate validation pass on that edge
    3. 60-day Stage 1 paper validation pass

Until then this module is exercised only by `tests/test_portfolio_risk_governor.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict


# Float-precision tolerance for cap comparisons. Absolute, not relative.
# Risk fractions in this module are bounded by max_total_exposure (default
# 0.08), so 1e-9 is ~7 orders of magnitude smaller than the smallest cap and
# cannot meaningfully affect risk decisions. Required because composing a
# handful of 1.2% positions in float-64 yields totals like
# 0.07200000000000001, which the bare-`>` cap check would reject.
_CAP_EPSILON = 1e-9


# ─────────────────────────────────────────────────────────────
# CONFIG STRUCTURE
# ─────────────────────────────────────────────────────────────

@dataclass
class PortfolioRiskConfig:
    """Operator-spec defaults; override per-deployment if Stage 1 metrics warrant."""

    max_total_exposure: float = 0.08       #  8% of portfolio
    max_single_position: float = 0.012     #  1.2% of portfolio
    max_sector_exposure: float = 0.04      #  4% per correlated cluster
    daily_loss_limit_r: float = 3.0        #  3R daily
    weekly_loss_limit_r: float = 6.0       #  6R weekly
    max_drawdown_pct: float = 0.25         # 25% hard kill from peak equity
    regime_multiplier: float = 1.0         # Optional hook (e.g. 0.5 in DEAD)


# ─────────────────────────────────────────────────────────────
# STATE STRUCTURE
# ─────────────────────────────────────────────────────────────

@dataclass
class PortfolioRiskState:
    """Mutable state owned by a PortfolioRiskGovernor instance."""

    equity_peak: float
    equity_current: float
    open_positions: Dict[str, float] = field(default_factory=dict)
    sector_map: Dict[str, str] = field(default_factory=dict)
    realized_r_today: float = 0.0
    realized_r_week: float = 0.0
    last_reset_day: datetime = field(default_factory=datetime.utcnow)
    last_reset_week: datetime = field(default_factory=datetime.utcnow)
    kill_switch: bool = False


# ─────────────────────────────────────────────────────────────
# CORE ENGINE
# ─────────────────────────────────────────────────────────────

class PortfolioRiskGovernor:
    """Stateful risk governor; one instance per portfolio.

    Not thread-safe. Caller serializes access (the live trading-bot
    architecture has a single executor thread per portfolio, so this
    matches existing constraints).
    """

    def __init__(self, config: PortfolioRiskConfig, starting_equity: float):
        if starting_equity <= 0:
            raise ValueError("starting_equity must be positive")
        self.config = config
        self.state = PortfolioRiskState(
            equity_peak=starting_equity,
            equity_current=starting_equity,
        )

    # ─────────────────────────────────────────

    def update_equity(self, new_equity: float) -> None:
        """Update current equity. Tracks peak. May trigger drawdown kill."""
        self.state.equity_current = new_equity

        if new_equity > self.state.equity_peak:
            self.state.equity_peak = new_equity

        self._check_drawdown()

    def _check_drawdown(self) -> None:
        if self.state.equity_peak <= 0:
            return
        dd = 1 - (self.state.equity_current / self.state.equity_peak)
        if dd >= self.config.max_drawdown_pct:
            self.state.kill_switch = True

    # ─────────────────────────────────────────

    def register_trade_result(self, r_multiple: float) -> None:
        """Record a closed-trade R-multiple. Negative = loss. May trigger
        daily or weekly circuit breaker."""
        self._reset_if_needed()

        self.state.realized_r_today += r_multiple
        self.state.realized_r_week += r_multiple

        if self.state.realized_r_today <= -self.config.daily_loss_limit_r:
            self.state.kill_switch = True

        if self.state.realized_r_week <= -self.config.weekly_loss_limit_r:
            self.state.kill_switch = True

    # ─────────────────────────────────────────

    def approve_new_position(self, symbol: str, risk_fraction: float) -> bool:
        """Return True if a new position of size `risk_fraction` (as a fraction
        of portfolio equity) is permitted under all current caps. Does NOT
        record the position; caller must then `open_position` if approved
        and the trade actually fills.
        """
        if self.state.kill_switch:
            return False

        # Apply optional regime multiplier (e.g., DEAD regime → 0)
        effective_fraction = risk_fraction * self.config.regime_multiplier

        if effective_fraction > self.config.max_single_position + _CAP_EPSILON:
            return False

        total_exposure = sum(self.state.open_positions.values())
        if total_exposure + effective_fraction > self.config.max_total_exposure + _CAP_EPSILON:
            return False

        sector = self.state.sector_map.get(symbol)
        if sector:
            sector_exposure = sum(
                v for s, v in self.state.open_positions.items()
                if self.state.sector_map.get(s) == sector
            )
            if sector_exposure + effective_fraction > self.config.max_sector_exposure + _CAP_EPSILON:
                return False

        return True

    # ─────────────────────────────────────────

    def open_position(self, symbol: str, risk_fraction: float) -> None:
        """Record an open position. Caller is responsible for first calling
        `approve_new_position`; this method does not re-check caps."""
        self.state.open_positions[symbol] = risk_fraction

    def close_position(self, symbol: str) -> None:
        """Remove an open position. No-op if symbol is not open."""
        if symbol in self.state.open_positions:
            del self.state.open_positions[symbol]

    # ─────────────────────────────────────────

    def set_sector(self, symbol: str, sector: str) -> None:
        """Tag `symbol` as belonging to a correlation cluster. The sector cap
        is enforced across all symbols sharing the same cluster name."""
        self.state.sector_map[symbol] = sector

    # ─────────────────────────────────────────

    def _reset_if_needed(self) -> None:
        """Roll daily/weekly accumulators when the elapsed window expires.

        Note: this is a 24h / 7d *elapsed* window from the last reset, not
        a UTC-midnight or ISO-week boundary. Operator preferred this in the
        spec and we keep it. Switch to `datetime.combine(now.date(), time.min)`
        only after live-deployment review.
        """
        now = datetime.utcnow()

        if now - self.state.last_reset_day > timedelta(days=1):
            self.state.realized_r_today = 0.0
            self.state.last_reset_day = now

        if now - self.state.last_reset_week > timedelta(days=7):
            self.state.realized_r_week = 0.0
            self.state.last_reset_week = now

    # ─────────────────────────────────────────

    def force_kill(self) -> None:
        """Manual emergency stop. Sets kill_switch = True."""
        self.state.kill_switch = True

    def reset_kill(self) -> None:
        """Clear kill_switch. Caller must have determined root cause is resolved."""
        self.state.kill_switch = False

    # ─────────────────────────────────────────

    def status(self) -> Dict:
        """Snapshot dict for monitoring and logging."""
        if self.state.equity_peak > 0:
            drawdown_pct = 1 - (self.state.equity_current / self.state.equity_peak)
        else:
            drawdown_pct = 0.0
        return {
            "equity_current": self.state.equity_current,
            "equity_peak": self.state.equity_peak,
            "drawdown_pct": drawdown_pct,
            "open_positions": dict(self.state.open_positions),
            "total_exposure": sum(self.state.open_positions.values()),
            "realized_r_today": self.state.realized_r_today,
            "realized_r_week": self.state.realized_r_week,
            "kill_switch": self.state.kill_switch,
        }
