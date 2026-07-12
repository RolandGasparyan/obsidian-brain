"""
L99 Governance — Failover Policy
Defines edge-case rules for dual-exchange scenarios.
Kill switch remains global and supreme — failover cannot override it.
"""
import logging

logger = logging.getLogger("l99.governance.failover")


def handle_primary_fails_mid_position(router, position) -> str:
    """
    Case A: Primary fails while a position is open.
    → Let position close naturally on primary (orders already placed).
    → Route NEW entries to secondary.
    Policy: do not forcefully move open positions between exchanges.
    """
    logger.warning("Primary fail mid-position (%s): position will close on primary, "
                   "new entries routed to secondary.", position.get("symbol", "UNKNOWN"))
    return "ROUTE_NEW_TO_SECONDARY"


def handle_both_exchanges_fail(router) -> str:
    """
    Case B: Both exchanges unavailable.
    → EMERGENCY_FREEZE — halt all new entries.
    → Alert operator. No automatic recovery.
    """
    logger.critical("BOTH EXCHANGES UNAVAILABLE — EMERGENCY FREEZE")
    try:
        import telegram_alerts as tg
        tg.send(
            "🚨 *EMERGENCY FREEZE*\nBoth exchanges unavailable.\n"
            "All entries halted. Manual intervention required.",
            key="emergency_freeze",
        )
    except Exception:
        pass
    return "EMERGENCY_FREEZE"


def handle_price_divergence(symbol: str, primary_price: float,
                            secondary_price: float) -> str:
    """
    Case C: Price divergence > 0.5% between exchanges.
    → Suspend new entries on this symbol.
    → Alert anomaly.
    """
    divergence = abs(primary_price - secondary_price) / primary_price
    if divergence > 0.005:
        logger.warning("Price divergence %s: primary=%.4f secondary=%.4f  diff=%.3f%%",
                       symbol, primary_price, secondary_price, divergence * 100)
        try:
            import telegram_alerts as tg
            tg.send(
                f"⚠️ *Price Divergence*\n"
                f"Symbol: `{symbol}`\n"
                f"Primary:   `{primary_price:.4f}`\n"
                f"Secondary: `{secondary_price:.4f}`\n"
                f"Spread: `{divergence:.3%}` — entries suspended.",
                key=f"divergence_{symbol}",
            )
        except Exception:
            pass
        return "SUSPEND_ENTRIES"
    return "OK"


def recovery_requirements() -> dict:
    """
    Policy requirements before reverting PRIMARY after failover.
    Enforced by exchange_router.check_recovery().
    """
    return {
        "consecutive_healthy_checks": 10,
        "observation_window_minutes": 15,
        "requires_manual_confirmation": True,
    }
