"""
L99 Bot — Main Orchestrator
Runs the full pilot loop: signal scan → order placement → position tracking → logging.

Usage:
    source venv/bin/activate
    python live_bot.py

Do not modify signal parameters. Risk config lives in config.py only.
"""
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import ccxt

import config
import db
import telegram_alerts as tg
from signal_engine import Signal, get_exchange, scan_all
from risk_monitor import RiskMonitor

# ── Logging setup ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-15s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(os.path.expanduser("~/logs/l99_bot.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("l99.bot")


# ── Open position tracker ─────────────────────────────────────

@dataclass
class OpenPosition:
    symbol:       str
    entry_time:   datetime
    entry_price:  float
    stop_price:   float
    target_price: float
    position_size: float   # in base currency units
    risk_pct:     float
    entry_order_id: str = ""
    stop_order_id:  str = ""
    tp_order_id:    str = ""


# ── Equity helper ─────────────────────────────────────────────

def fetch_usdt_balance() -> float:
    ex = get_exchange()
    bal = ex.fetch_balance()
    return float(bal["USDT"]["free"] + bal["USDT"]["used"])


def total_equity(open_positions: list[OpenPosition]) -> float:
    ex   = get_exchange()
    usdt = fetch_usdt_balance()
    for pos in open_positions:
        try:
            ticker = ex.fetch_ticker(pos.symbol)
            mid    = (ticker["bid"] + ticker["ask"]) / 2
            usdt  += pos.position_size * mid
        except Exception:
            pass
    return usdt


# ── Order placement ───────────────────────────────────────────

def place_limit_order(symbol: str, side: str, amount: float,
                      price: float) -> dict:
    ex = get_exchange()
    return ex.create_order(symbol, "limit", side, amount, price)


def place_stop_order(symbol: str, amount: float,
                     stop_price: float) -> dict:
    ex = get_exchange()
    # Gate.io spot: limit sell at stop price (acts as manual stop-loss)
    return ex.create_order(symbol, "limit", "sell", amount, stop_price)


def cancel_order(symbol: str, order_id: str) -> None:
    try:
        get_exchange().cancel_order(order_id, symbol)
    except Exception as e:
        logger.warning("Cancel failed %s %s: %s", symbol, order_id, e)


# ── Entry logic ───────────────────────────────────────────────

def open_position(sig: Signal, equity: float,
                  monitor: RiskMonitor) -> OpenPosition | None:
    if equity < 10:
        logger.warning("Equity %.2f USDT too low — fund testnet account", equity)
        return None

    risk_amt      = equity * config.RISK_PER_TRADE
    risk_per_unit = sig.entry_target - sig.stop_price
    if risk_per_unit <= 0:
        logger.warning("Invalid risk per unit for %s — skipping", sig.symbol)
        return None

    size = risk_amt / risk_per_unit

    try:
        entry_ord = place_limit_order(sig.symbol, "buy", size, sig.entry_target)
        tp_ord    = place_limit_order(sig.symbol, "sell", size, sig.target_price)
        stop_ord  = place_stop_order(sig.symbol, size, sig.stop_price)
    except ccxt.BaseError as e:
        logger.error("Order placement failed for %s: %s", sig.symbol, e)
        return None

    pos = OpenPosition(
        symbol         = sig.symbol,
        entry_time     = datetime.now(timezone.utc),
        entry_price    = sig.entry_target,
        stop_price     = sig.stop_price,
        target_price   = sig.target_price,
        position_size  = size,
        risk_pct       = config.RISK_PER_TRADE,
        entry_order_id = entry_ord["id"],
        tp_order_id    = tp_ord["id"],
        stop_order_id  = stop_ord["id"],
    )
    logger.info("Position opened: %s  size=%.4f  entry=%.4f  stop=%.4f  tp=%.4f",
                sig.symbol, size, sig.entry_target, sig.stop_price, sig.target_price)
    tg.alert_entry(sig.symbol, size, sig.entry_target, sig.stop_price, sig.target_price)

    db.log_signal({
        "symbol":          sig.symbol,
        "signal_time":     sig.signal_time,
        "adx":             sig.adx,
        "volume_ratio":    sig.volume_ratio,
        "breakout_level":  sig.breakout_level,
        "regime_state":    "BULL",
    })
    return pos


# ── Exit logic ────────────────────────────────────────────────

def close_position(pos: OpenPosition, exit_price: float,
                   exit_time: datetime, equity: float,
                   monitor: RiskMonitor) -> None:
    cancel_order(pos.symbol, pos.stop_order_id)
    cancel_order(pos.symbol, pos.tp_order_id)

    actual_r  = (exit_price - pos.entry_price) / (pos.entry_price - pos.stop_price)
    fee       = pos.position_size * exit_price * config.FEE_RATE
    slippage  = abs(exit_price - pos.entry_price) * 0.0   # filled later from DB
    pnl       = (exit_price - pos.entry_price) * pos.position_size - fee

    db.log_trade({
        "symbol":        pos.symbol,
        "entry_time":    pos.entry_time,
        "exit_time":     exit_time,
        "entry_price":   pos.entry_price,
        "exit_price":    exit_price,
        "position_size": pos.position_size,
        "risk_pct":      pos.risk_pct,
        "R_multiple":    actual_r,
        "fee":           fee,
        "slippage":      slippage,
        "pnl":           pnl,
        "equity_after":  equity + pnl,
    })
    monitor.on_trade_closed(pnl, slippage)
    logger.info("Position closed: %s  exit=%.4f  R=%.2f  pnl=%.2f",
                pos.symbol, exit_price, actual_r, pnl)
    if actual_r < 0:
        tg.alert_stop(pos.symbol, pnl, actual_r)
    else:
        tg.alert_tp(pos.symbol, pnl, actual_r)


def flatten_all(open_positions: list[OpenPosition]) -> None:
    ex = get_exchange()
    for pos in open_positions:
        cancel_order(pos.symbol, pos.stop_order_id)
        cancel_order(pos.symbol, pos.tp_order_id)
        try:
            ticker = ex.fetch_ticker(pos.symbol)
            ex.create_market_order(pos.symbol, "sell", pos.position_size)
            logger.warning("Emergency flatten: %s", pos.symbol)
        except Exception as e:
            logger.error("Flatten failed for %s: %s", pos.symbol, e)


# ── Position monitoring ───────────────────────────────────────

def check_open_positions(open_positions: list[OpenPosition],
                         equity: float,
                         monitor: RiskMonitor) -> list[OpenPosition]:
    ex       = get_exchange()
    remaining = []
    for pos in open_positions:
        try:
            tp_ord   = ex.fetch_order(pos.tp_order_id,   pos.symbol)
            stop_ord = ex.fetch_order(pos.stop_order_id, pos.symbol)
        except Exception as e:
            logger.warning("Order fetch error %s: %s", pos.symbol, e)
            remaining.append(pos)
            continue

        if tp_ord["status"] == "closed":
            close_position(pos, pos.target_price,
                           datetime.now(timezone.utc), equity, monitor)
        elif stop_ord["status"] == "closed":
            close_position(pos, pos.stop_price,
                           datetime.now(timezone.utc), equity, monitor)
        else:
            remaining.append(pos)
    return remaining


# ── Main loop ─────────────────────────────────────────────────

def _preflight_check() -> None:
    mode = "TESTNET" if config.TESTNET else "LIVE"
    errors = []

    if config.LIVE_TRADING and config.TESTNET:
        errors.append("LIVE_TRADING=true but TESTNET=true — contradiction")
    if config.RISK_PER_TRADE > 0.02:
        errors.append(f"RISK_PER_TRADE {config.RISK_PER_TRADE:.1%} exceeds hard cap 2%")
    if not config.API_KEY:
        errors.append("GATE_API_KEY is not set in .env")

    if errors:
        for e in errors:
            logger.critical("PREFLIGHT FAIL: %s", e)
        raise SystemExit("Pre-flight check failed — see logs")

    logger.info("═" * 50)
    logger.info("  L99 Bot — Pre-flight OK")
    logger.info("  Mode:           %s", mode)
    logger.info("  Max concurrent: %d", config.MAX_CONCURRENT)
    logger.info("  Risk per trade: %.1f%%", config.RISK_PER_TRADE * 100)
    logger.info("  Kill DD:        %.0f%%", config.KILL_DD_ABS * 100)
    logger.info("  Entry logic:    next_open (bias-corrected)")
    logger.info("  Signal:         SACRED — unchanged")
    logger.info("═" * 50)


def run() -> None:
    _preflight_check()

    mode = "TESTNET" if config.TESTNET else "LIVE"
    logger.info("L99 Bot starting — mode=%s", mode)

    db.init_pool()
    db.create_tables()

    equity  = fetch_usdt_balance()
    monitor = RiskMonitor(start_equity=equity)
    open_positions: list[OpenPosition] = []
    _last_summary_day: int = -1

    # Governance layer — enabled only after GOVERNANCE_ENABLED=true + 50 trades
    gov_engine = None
    if config.GOVERNANCE_ENABLED:
        from governance.governance_engine import GovernanceEngine
        gov_engine = GovernanceEngine()
        logger.info("Governance engine active")

    logger.info("Start equity: %.2f USDT", equity)
    tg.alert_start(
        mode          = mode,
        max_concurrent= config.MAX_CONCURRENT,
        risk_pct      = config.RISK_PER_TRADE,
        kill_dd       = config.KILL_DD_ABS,
    )

    while True:
        try:
            equity = total_equity(open_positions)
            monitor.on_equity_update(equity)

            if monitor.is_killed:
                logger.critical("System killed: %s — flattening all positions",
                                monitor.state.kill_reason)
                tg.alert_kill(monitor.state.kill_reason, equity)
                flatten_all(open_positions)
                break

            # Governance evaluation (no-op when disabled)
            gov_decision = None
            if gov_engine is not None:
                gov_decision = gov_engine.evaluate(
                    current_drawdown=monitor.current_drawdown
                )
                if gov_decision.is_frozen:
                    logger.critical("Governance FREEZE: %s", gov_decision.reason)
                    flatten_all(open_positions)
                    break

            effective_concurrent = (
                gov_decision.effective_max_concurrent
                if gov_decision else config.MAX_CONCURRENT
            )
            disabled_assets = gov_decision.disabled_assets if gov_decision else []

            # check existing positions
            open_positions = check_open_positions(open_positions, equity, monitor)

            # scan for new signals (only if under concurrent cap)
            slots = effective_concurrent - len(open_positions)
            if slots > 0:
                signals = scan_all()
                active_symbols = {p.symbol for p in open_positions}

                for sig in signals:
                    if sig.symbol in active_symbols:
                        continue
                    if sig.symbol in disabled_assets:
                        logger.info("Governance: skipping disabled asset %s", sig.symbol)
                        continue
                    if slots <= 0:
                        break
                    pos = open_position(sig, equity, monitor)
                    if pos:
                        open_positions.append(pos)
                        active_symbols.add(sig.symbol)
                        slots -= 1

            # log system metrics
            db.log_metrics({
                "live_sharpe":    monitor.rolling_sharpe,
                "drawdown":       monitor.current_drawdown,
                "open_positions": len(open_positions),
                "total_equity":   equity,
            })

            # daily Telegram summary (once per UTC day)
            today = datetime.now(timezone.utc).day
            if today != _last_summary_day:
                _last_summary_day = today
                s = monitor.status_dict()
                sr = s["rolling_sharpe"]
                tg.alert_metrics(
                    sharpe   = sr if sr == sr else 0.0,   # nan-safe
                    dd       = s["drawdown"],
                    equity   = equity,
                    open_pos = len(open_positions),
                )

            status = monitor.status_dict()
            logger.info(
                "equity=%.2f  dd=%.2f%%  sharpe=%.3f  open=%d  consec_loss=%d",
                status["equity"], status["drawdown"] * 100,
                0.0 if __import__("math").isnan(float(status["rolling_sharpe"])) else float(status["rolling_sharpe"]),
                len(open_positions), status["consec_losses"],
            )

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt — flattening all positions")
            flatten_all(open_positions)
            break
        except Exception as e:
            logger.error("Main loop error: %s", e, exc_info=True)

        time.sleep(config.POLL_SECONDS)


if __name__ == "__main__":
    run()
