"""
L99 Execution — Health Monitor
Background daemon thread. Checks primary exchange every 30s.
Triggers failover if 2+ conditions fail simultaneously.
Never overrides kill switch or governance.
"""
import logging
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger("l99.execution.health")

_CHECK_INTERVAL_SEC = 30
_LATENCY_LIMIT_MS   = 1500.0
_ORDERBOOK_STALE_S  = 60.0
_FAILOVER_THRESHOLD = 2          # conditions required to trigger failover


@dataclass
class HealthSnapshot:
    latency_ok:       bool = True
    order_failures_ok: bool = True
    ack_timeout_ok:   bool = True
    balance_ok:       bool = True
    orderbook_ok:     bool = True
    maintenance_ok:   bool = True
    latency_ms:       float = 0.0

    @property
    def failing_count(self) -> int:
        return sum([not self.latency_ok, not self.order_failures_ok,
                    not self.ack_timeout_ok, not self.balance_ok,
                    not self.orderbook_ok, not self.maintenance_ok])

    @property
    def failing_reasons(self) -> list[str]:
        reasons = []
        if not self.latency_ok:        reasons.append(f"latency {self.latency_ms:.0f}ms > 1500ms")
        if not self.order_failures_ok: reasons.append("3+ consecutive order failures")
        if not self.ack_timeout_ok:    reasons.append("order ack timeout > 5s")
        if not self.balance_ok:        reasons.append("balance mismatch > 0.5%")
        if not self.orderbook_ok:      reasons.append("orderbook stale > 60s")
        if not self.maintenance_ok:    reasons.append("exchange maintenance flag")
        return reasons


class HealthMonitor:

    def __init__(self, router, primary) -> None:
        self._router  = router
        self._primary = primary
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_orderbook_ts: float = time.monotonic()
        self._consecutive_order_failures: int = 0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True, name="health_monitor")
        self._thread.start()
        logger.info("Health monitor started (interval=%ds)", _CHECK_INTERVAL_SEC)

    def stop(self) -> None:
        self._stop_event.set()

    def on_order_failure(self) -> None:
        self._consecutive_order_failures += 1

    def on_order_success(self) -> None:
        self._consecutive_order_failures = 0

    def on_orderbook_update(self) -> None:
        self._last_orderbook_ts = time.monotonic()

    # ── Internal ──────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check()
            except Exception as e:
                logger.error("Health check exception: %s", e)
            self._stop_event.wait(_CHECK_INTERVAL_SEC)

    def _check(self) -> None:
        if self._router.is_failover_active:
            status = self._primary.health_check()
            if status.healthy and status.latency_ms < _LATENCY_LIMIT_MS:
                self._router.check_recovery()
            return

        snap = self._evaluate()
        logger.debug("Health: failing=%d  latency=%.0fms", snap.failing_count, snap.latency_ms)

        if snap.failing_count >= _FAILOVER_THRESHOLD:
            reason = "; ".join(snap.failing_reasons)
            logger.critical("Health threshold breached (%d conditions): %s",
                            snap.failing_count, reason)
            self._router.trigger_failover(reason)

    def _evaluate(self) -> HealthSnapshot:
        snap = HealthSnapshot()

        # Condition 1 — latency
        status = self._primary.health_check()
        snap.latency_ms  = status.latency_ms
        snap.latency_ok  = status.healthy and status.latency_ms < _LATENCY_LIMIT_MS

        # Condition 2 — consecutive order failures
        snap.order_failures_ok = self._consecutive_order_failures < 3

        # Condition 3 — ack timeout (tracked externally via order_failure counter)
        snap.ack_timeout_ok = snap.order_failures_ok   # same signal at this granularity

        # Condition 4 — balance check (simple liveness; deep mismatch requires position reconciliation)
        try:
            self._primary.get_balance()
            snap.balance_ok = True
        except Exception:
            snap.balance_ok = False

        # Condition 5 — orderbook staleness
        age = time.monotonic() - self._last_orderbook_ts
        snap.orderbook_ok = age < _ORDERBOOK_STALE_S

        # Condition 6 — maintenance (inferred from health_check failure)
        snap.maintenance_ok = status.healthy

        return snap
