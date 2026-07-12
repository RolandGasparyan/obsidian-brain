"""
L99 Execution — Exchange Router
Single entry point for all order execution.
Routes to PRIMARY (Binance 70%) or SECONDARY (Gate 30%).
Manages failover state — no rapid oscillation (MIN_SWITCH_INTERVAL = 30min).
Kill switch remains supreme authority; router never overrides risk engine.
"""
import json
import logging
import os
import threading
import time
from dataclasses import dataclass

import telegram_alerts as tg
from execution.exchange_base import ExchangeBase, HealthStatus

logger = logging.getLogger("l99.execution.router")

_STATE_PATH       = os.path.join(os.path.dirname(__file__), "../state/redundancy_state.json")
_MIN_SWITCH_SEC   = 30 * 60     # 30 minutes between switches
_RECOVERY_CHECKS  = 10          # consecutive healthy checks before reverting


@dataclass
class RouterState:
    active_exchange:          str   = "PRIMARY"
    failover_active:          bool  = False
    last_switch_ts:           float = 0.0
    consecutive_healthy:      int   = 0
    primary_order_failures:   int   = 0
    secondary_order_failures: int   = 0


class ExchangeRouter(ExchangeBase):
    """Implements ExchangeBase — callers treat the router as a single exchange."""

    exchange_id = "ROUTER"

    def __init__(self, primary: ExchangeBase, secondary: ExchangeBase) -> None:
        self._primary   = primary
        self._secondary = secondary
        self._lock      = threading.Lock()
        self._state     = self._load_state()

    # ── Active exchange accessor ──────────────────────────────────

    @property
    def _active(self) -> ExchangeBase:
        with self._lock:
            return self._secondary if self._state.failover_active else self._primary

    @property
    def is_failover_active(self) -> bool:
        with self._lock:
            return self._state.failover_active

    # ── ExchangeBase implementation ───────────────────────────────

    def get_balance(self) -> dict:
        return self._active.get_balance()

    def get_orderbook(self, symbol: str) -> dict:
        return self._active.get_orderbook(symbol)

    def place_order(self, symbol: str, side: str, size: float,
                    order_type: str, price: float | None = None,
                    params: dict | None = None) -> dict:
        try:
            result = self._active.place_order(symbol, side, size, order_type, price, params)
            self._reset_failure_counter()
            return result
        except Exception as e:
            self._on_order_failure()
            raise

    def cancel_order(self, order_id: str, symbol: str) -> None:
        self._active.cancel_order(order_id, symbol)

    def fetch_order(self, order_id: str, symbol: str) -> dict:
        return self._active.fetch_order(order_id, symbol)

    def fetch_open_positions(self) -> list[dict]:
        return self._active.fetch_open_positions()

    def fetch_recent_trades(self, symbol: str, limit: int = 10) -> list[dict]:
        return self._active.fetch_recent_trades(symbol, limit)

    def create_market_order(self, symbol: str, side: str, size: float) -> dict:
        """Emergency flatten — tries active exchange, then other."""
        try:
            return self._active.create_market_order(symbol, side, size)
        except Exception as e:
            logger.error("Market order on %s failed (%s) — trying other exchange",
                         self._active.exchange_id, e)
            other = self._secondary if not self._state.failover_active else self._primary
            return other.create_market_order(symbol, side, size)

    def health_check(self) -> HealthStatus:
        return self._active.health_check()

    # ── Failover control ──────────────────────────────────────────

    def trigger_failover(self, reason: str) -> bool:
        with self._lock:
            now = time.monotonic()
            if now - self._state.last_switch_ts < _MIN_SWITCH_SEC:
                logger.warning("Failover request blocked — cooldown active (%.0f sec remaining)",
                               _MIN_SWITCH_SEC - (now - self._state.last_switch_ts))
                return False

            self._state.failover_active = True
            self._state.last_switch_ts  = now
            self._state.consecutive_healthy = 0
            self._state.active_exchange = "SECONDARY"
            self._save_state()

        logger.critical("FAILOVER ACTIVATED: %s", reason)
        tg.send(f"⚠️ *FAILOVER ACTIVE*\nPrimary down — routing to SECONDARY\nReason: `{reason}`",
                key="failover")
        return True

    def check_recovery(self) -> None:
        """Called by health_monitor when primary is healthy again."""
        with self._lock:
            if not self._state.failover_active:
                return
            self._state.consecutive_healthy += 1
            if self._state.consecutive_healthy >= _RECOVERY_CHECKS:
                self._state.failover_active  = False
                self._state.active_exchange  = "PRIMARY"
                self._state.consecutive_healthy = 0
                self._state.last_switch_ts   = time.monotonic()
                self._save_state()
                logger.info("FAILOVER RECOVERED — primary restored after %d healthy checks",
                            _RECOVERY_CHECKS)
                tg.send("✅ *PRIMARY RESTORED*\nExchange router reverted to Binance.",
                        key="failover_recovery")

    # ── Internal ──────────────────────────────────────────────────

    def _on_order_failure(self) -> None:
        with self._lock:
            if self._state.failover_active:
                self._state.secondary_order_failures += 1
            else:
                self._state.primary_order_failures += 1
                logger.warning("Primary order failure count: %d",
                               self._state.primary_order_failures)
            self._save_state()

    def _reset_failure_counter(self) -> None:
        with self._lock:
            if not self._state.failover_active:
                self._state.primary_order_failures = 0

    def _load_state(self) -> RouterState:
        try:
            with open(_STATE_PATH) as f:
                d = json.load(f)
            return RouterState(
                active_exchange          = d.get("active_exchange", "PRIMARY"),
                failover_active          = d.get("failover_active", False),
                last_switch_ts           = d.get("last_switch_ts") or 0.0,
                consecutive_healthy      = d.get("consecutive_healthy", 0),
                primary_order_failures   = d.get("primary_order_failures", 0),
                secondary_order_failures = d.get("secondary_order_failures", 0),
            )
        except Exception:
            return RouterState()

    def _save_state(self) -> None:
        try:
            with open(_STATE_PATH, "w") as f:
                json.dump({
                    "active_exchange":          self._state.active_exchange,
                    "failover_active":          self._state.failover_active,
                    "last_switch_ts":           self._state.last_switch_ts,
                    "consecutive_healthy":      self._state.consecutive_healthy,
                    "primary_order_failures":   self._state.primary_order_failures,
                    "secondary_order_failures": self._state.secondary_order_failures,
                }, f, indent=2)
        except Exception as e:
            logger.error("Failed to persist router state: %s", e)
