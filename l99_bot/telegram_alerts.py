"""
L99 Bot — Telegram Alert Layer
Visibility only. Does not affect signal logic, DB, or kill switch.
"""
import logging
import os
import time

import requests

logger = logging.getLogger("l99.telegram")

TOKEN   = os.getenv("TELEGRAM_TOKEN",   os.getenv("TG_TOKEN",   ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("TG_CHAT_ID", ""))

_DEBOUNCE_SEC = 30
_last_sent: dict[str, float] = {}   # key → last send timestamp


def _debounce_ok(key: str) -> bool:
    now = time.monotonic()
    last = _last_sent.get(key, 0.0)
    if now - last < _DEBOUNCE_SEC:
        return False
    _last_sent[key] = now
    return True


def send(message: str, key: str = "general") -> None:
    if not TOKEN or not CHAT_ID:
        logger.debug("Telegram not configured — skipping alert")
        return
    if not _debounce_ok(key):
        logger.debug("Telegram debounced: %s", key)
        return
    url     = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload, timeout=5)
        if not r.ok:
            logger.warning("Telegram API error %s: %s", r.status_code, r.text[:120])
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)


# ── Typed alert helpers ───────────────────────────────────────

def alert_start(mode: str, max_concurrent: int,
                risk_pct: float, kill_dd: float) -> None:
    send(
        f"🟢 *L99 Bot started successfully.*\n"
        f"Mode: `{mode}`\n"
        f"Max concurrent: `{max_concurrent}`\n"
        f"Risk per trade: `{risk_pct:.0%}`\n"
        f"Kill DD: `{kill_dd:.0%}`",
        key="system_start",
    )


def alert_entry(symbol: str, size: float,
                entry: float, stop: float, tp: float) -> None:
    send(
        f"🚀 *ENTRY*\n"
        f"Symbol: `{symbol}`\n"
        f"Size:   `{size:.4f}`\n"
        f"Entry:  `{entry:.4f}`\n"
        f"Stop:   `{stop:.4f}`\n"
        f"TP:     `{tp:.4f}`",
        key=f"entry_{symbol}",
    )


def alert_stop(symbol: str, pnl: float, r_multiple: float) -> None:
    send(
        f"🛑 *STOP HIT*\n"
        f"Symbol: `{symbol}`\n"
        f"R:      `{r_multiple:.2f}`\n"
        f"PnL:    `{pnl:+.2f} USDT`",
        key=f"exit_{symbol}",
    )


def alert_tp(symbol: str, pnl: float, r_multiple: float) -> None:
    send(
        f"🎯 *TAKE PROFIT*\n"
        f"Symbol: `{symbol}`\n"
        f"R:      `{r_multiple:.2f}`\n"
        f"PnL:    `{pnl:+.2f} USDT`",
        key=f"exit_{symbol}",
    )


def alert_kill(reason: str, equity: float) -> None:
    # kill switch bypasses debounce — always fires
    _last_sent["kill"] = 0.0
    send(
        f"🔥 *KILL SWITCH TRIGGERED*\n"
        f"Reason: `{reason}`\n"
        f"Equity: `{equity:,.2f} USDT`\n"
        f"System halted.",
        key="kill",
    )


def alert_metrics(sharpe: float, dd: float,
                  equity: float, open_pos: int) -> None:
    send(
        f"📊 *Daily Summary*\n"
        f"Equity:  `{equity:,.2f} USDT`\n"
        f"Sharpe:  `{sharpe:.3f}`\n"
        f"DD:      `{dd:+.2%}`\n"
        f"Open:    `{open_pos}` positions",
        key="daily_summary",
    )


# ── Governance alert helpers ──────────────────────────────────

def alert_governance_info(message: str) -> None:
    send(f"ℹ️ *Governance INFO*\n{message}", key="gov_info")


def alert_governance_warning(reason: str, metrics: dict) -> None:
    send(
        f"⚠️ *Governance WARNING — THROTTLED*\n"
        f"Reason: `{reason}`\n"
        f"Sharpe: `{metrics.get('sharpe', 0):.3f}`  "
        f"PF: `{metrics.get('profit_factor', 0):.2f}`",
        key="gov_warning",
    )


def alert_governance_critical(reason: str, metrics: dict) -> None:
    send(
        f"🔴 *Governance CRITICAL — RESTRICTED*\n"
        f"Reason: `{reason}`\n"
        f"Sharpe: `{metrics.get('sharpe', 0):.3f}`  "
        f"PF: `{metrics.get('profit_factor', 0):.2f}`  "
        f"Win: `{metrics.get('win_rate', 0):.1%}`",
        key="gov_critical",
    )


def alert_governance_freeze(sharpe: float, pf: float,
                            dd: float, reason: str) -> None:
    _last_sent["gov_freeze"] = 0.0   # bypass debounce
    send(
        f"❄️ *Governance FREEZE*\n"
        f"Reason:  `{reason}`\n"
        f"Sharpe:  `{sharpe:.3f}`\n"
        f"PF:      `{pf:.2f}`\n"
        f"DD:      `{dd:+.2%}`\n"
        f"Action:  Manual review required.",
        key="gov_freeze",
    )
