"""
Telegram push notifications for the trading bot.

Reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from the environment.
If either is missing, every call becomes a no-op — so the bot runs
happily without Telegram configured, and adding alerts later is just
setting two env vars and restarting the service.

Usage:
    from telegram_alerts import notify

    notify("📈 MA-BUY  ETH @2312.35  size 0.108 ETH  bal $0.00")

Rate-limit friendly: messages are POSTed synchronously with a 4-second
timeout and silently drop on any network error — we never want an
alert failure to take down the trading loop.

Setup (one-off):
  1. Open Telegram, message @BotFather → /newbot → follow prompts
  2. Copy the token (looks like "7123456789:AAH...")
  3. Send any message to your new bot
  4. Visit https://api.telegram.org/bot<TOKEN>/getUpdates to find your
     chat id (`message.chat.id`)
  5. Export:
       export TELEGRAM_BOT_TOKEN=7123...
       export TELEGRAM_CHAT_ID=123456789
     or add them to the systemd unit's Environment= line
"""
from __future__ import annotations

import logging
import os
import socket
import time
from typing import Optional

try:
    import requests
except ImportError:  # keep the module importable even w/o requests
    requests = None  # type: ignore

_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
# TELEGRAM_CHAT_ID may be a single id or comma-separated list — every
# listed chat receives every notification.
_CHATS = [c.strip() for c in os.getenv("TELEGRAM_CHAT_ID", "").split(",") if c.strip()]
_HOST  = socket.gethostname()

# Per-process rate limit: at most 20 messages per minute. Telegram
# itself allows 30/s to a single chat, but we don't want a logic bug
# to spam the user's phone.
_WINDOW       = 60.0
_MAX_PER_WIN  = 20
_recent_sends: list[float] = []


def is_configured() -> bool:
    return bool(_TOKEN) and bool(_CHATS) and requests is not None


def _rate_ok() -> bool:
    now = time.monotonic()
    # drop old timestamps
    cutoff = now - _WINDOW
    while _recent_sends and _recent_sends[0] < cutoff:
        _recent_sends.pop(0)
    if len(_recent_sends) >= _MAX_PER_WIN:
        return False
    _recent_sends.append(now)
    return True


def notify(
    text: str,
    *,
    silent: bool = False,
    tag: Optional[str] = None,
) -> bool:
    """
    Send a message to the configured Telegram chat.
    Returns True on delivery, False otherwise (including when not
    configured — the caller should never crash on a False return).

    `silent=True` sends without a notification sound (good for the
    per-loop heartbeat pings). `tag` is a short label prepended to the
    message so you can tell which bot sent it.
    """
    if not is_configured():
        return False
    if not _rate_ok():
        logging.warning("telegram_alerts: rate limit hit, dropping msg")
        return False

    # Plain-text only — Telegram's legacy Markdown parser chokes on
    # common characters (underscores in pair names, trade-style emojis,
    # hyphens in host names). Emojis + caps carry the visual weight.
    label = f"[{tag or _HOST}] "
    body  = label + text
    # Deliver to every configured chat — one failure doesn't abort the rest
    any_ok = False
    for chat in _CHATS:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{_TOKEN}/sendMessage",
                json={
                    "chat_id":              chat,
                    "text":                 body,
                    "disable_notification":  silent,
                    "disable_web_page_preview": True,
                },
                timeout=4,
            )
            r.raise_for_status()
            any_ok = True
        except Exception as e:
            logging.warning("telegram_alerts: send to %s failed: %s", chat, e)
    return any_ok


def notify_startup(pair: str, balance: float, strategy: str) -> None:
    notify(
        f"🚀 Bot online\n"
        f"pair: {pair}\n"
        f"strategy: {strategy}\n"
        f"paper balance: ${balance:.2f}",
        silent=True,
        tag=pair,
    )


def notify_buy(pair: str, price: float, units: float) -> None:
    notify(
        f"📈 MA-BUY {pair}\n"
        f"price ${price:,.2f} · size {units:.6f}",
        tag=pair,
    )


def notify_sell(pair: str, price: float, pnl: float, pnl_pct: float) -> None:
    icon = "✅" if pnl > 0 else "❌"
    sign = "+" if pnl >= 0 else ""
    notify(
        f"{icon} MA-SELL {pair}\n"
        f"price ${price:,.2f} · "
        f"pnl {sign}${pnl:.2f} ({sign}{pnl_pct:.2f}%)",
        tag=pair,
    )


def notify_drawdown(pair: str, dd_pct: float, equity: float, peak: float) -> None:
    notify(
        f"⚠️ DRAWDOWN WARNING {pair}\n"
        f"dd -{dd_pct:.2f}% from peak ${peak:.2f}\n"
        f"current equity ${equity:.2f}",
        tag=pair,
    )


def notify_circuit_break(pair: str, dd_pct: float, equity: float) -> None:
    notify(
        f"🛑 CIRCUIT BREAKER {pair}\n"
        f"dd -{dd_pct:.2f}% triggered hard stop\n"
        f"flattened at equity ${equity:.2f}",
        tag=pair,
    )


def notify_error(pair: str, err: str) -> None:
    notify(
        f"🚨 Bot error {pair}\n{err[:1500]}",
        tag=pair,
    )


if __name__ == "__main__":
    # Smoke test — run manually after exporting the env vars
    if not is_configured():
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — nothing to test.")
        raise SystemExit(0)
    ok = notify("🧪 Smoke test from telegram_alerts.py")
    print("sent" if ok else "failed")
