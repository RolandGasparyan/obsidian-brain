"""
L99 Bot — Risk Monitor & Kill Switch
Enforces all Stage 6 kill conditions in real time.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import deque

import numpy as np

import config
import db

logger = logging.getLogger("l99.risk")


@dataclass
class RiskState:
    start_equity:       float
    peak_equity:        float = 0.0
    current_equity:     float = 0.0
    consecutive_losses: int   = 0
    recent_slippages:   deque = field(default_factory=lambda: deque(maxlen=20))
    recent_pnls:        deque = field(default_factory=lambda: deque(maxlen=20))
    killed:             bool  = False
    kill_reason:        str   = ""

    def __post_init__(self):
        self.peak_equity    = self.start_equity
        self.current_equity = self.start_equity


class RiskMonitor:

    def __init__(self, start_equity: float):
        self.state = RiskState(start_equity=start_equity)

    # ── call after every closed trade ────────────────────────

    def on_trade_closed(self, pnl: float, slippage: float) -> None:
        self.state.current_equity += pnl
        self.state.peak_equity     = max(self.state.peak_equity,
                                         self.state.current_equity)
        self.state.recent_pnls.append(pnl)
        self.state.recent_slippages.append(abs(slippage))

        if pnl < 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0

        self._check_all()

    def on_equity_update(self, equity: float) -> None:
        self.state.current_equity = equity
        self.state.peak_equity    = max(self.state.peak_equity, equity)
        self._check_all()

    # ── kill switch evaluation ────────────────────────────────

    def _check_all(self) -> None:
        if self.state.killed:
            return

        checks = [
            self._check_consecutive_losses,
            self._check_drawdown,
            self._check_rolling_sharpe,
            self._check_slippage,
        ]
        for check in checks:
            reason = check()
            if reason:
                self._trigger_kill(reason)
                return

    def _check_consecutive_losses(self) -> str | None:
        if self.state.consecutive_losses >= config.KILL_CONSEC_LOSS:
            return f"{config.KILL_CONSEC_LOSS} consecutive losses"
        return None

    def _check_drawdown(self) -> str | None:
        if self.state.peak_equity == 0:
            return None
        dd = (self.state.current_equity - self.state.peak_equity) / self.state.peak_equity
        if dd <= -config.KILL_DD_ABS:
            return f"Drawdown {dd:.2%} exceeds kill level {-config.KILL_DD_ABS:.2%}"
        return None

    def _check_rolling_sharpe(self) -> str | None:
        pnls = list(self.state.recent_pnls)
        if len(pnls) < 20:
            return None
        arr = np.array(pnls)
        std = arr.std()
        if std == 0:
            return None
        sharpe = (arr.mean() / std) * np.sqrt(len(arr))
        if sharpe < config.KILL_SHARPE_MIN:
            return f"Rolling Sharpe {sharpe:.3f} < floor {config.KILL_SHARPE_MIN}"
        return None

    def _check_slippage(self) -> str | None:
        slips = list(self.state.recent_slippages)
        if len(slips) < 5:
            return None
        avg_slip = np.mean(slips)
        if avg_slip > config.KILL_SLIP_MAX:
            return f"Avg slippage {avg_slip:.4%} > limit {config.KILL_SLIP_MAX:.4%}"
        return None

    def _trigger_kill(self, reason: str) -> None:
        self.state.killed      = True
        self.state.kill_reason = reason
        logger.critical("KILL SWITCH TRIGGERED: %s", reason)
        try:
            db.log_kill(reason, self.state.current_equity)
        except Exception as e:
            logger.error("Failed to log kill event to DB: %s", e)

    # ── read-only properties ──────────────────────────────────

    @property
    def is_killed(self) -> bool:
        return self.state.killed

    @property
    def current_drawdown(self) -> float:
        if self.state.peak_equity == 0:
            return 0.0
        return (self.state.current_equity - self.state.peak_equity) / self.state.peak_equity

    @property
    def rolling_sharpe(self) -> float:
        pnls = list(self.state.recent_pnls)
        if len(pnls) < 5:
            return float("nan")
        arr = np.array(pnls)
        std = arr.std()
        if std == 0:
            return 0.0
        return float((arr.mean() / std) * np.sqrt(len(arr)))

    def status_dict(self) -> dict:
        return {
            "equity":        self.state.current_equity,
            "peak_equity":   self.state.peak_equity,
            "drawdown":      self.current_drawdown,
            "rolling_sharpe": self.rolling_sharpe,
            "consec_losses": self.state.consecutive_losses,
            "killed":        self.state.killed,
            "kill_reason":   self.state.kill_reason,
        }
