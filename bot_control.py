#!/usr/bin/env python3
"""
Tiny HTTP control service for the trading bots.

Binds to 127.0.0.1:5055 and exposes three token-protected endpoints
that wrap `systemctl` for the trading-bot@*.service units. Nginx
proxies /api/control/* here, so the public surface is a single origin.

Endpoints:
  POST /api/control/stop-all   — stops every bot
  POST /api/control/start-all  — starts every bot
  POST /api/control/restart-all
  POST /api/control/stop/<pair>
  POST /api/control/start/<pair>
  GET  /api/control/status     — lightweight state snapshot
  GET  /api/control/health     — 200 + "ok" (no auth)

Every mutating call requires an `X-Control-Token` header matching the
token stored in /etc/trading-bot-control.token (root-only 600).

The token is generated on first run with `secrets.token_urlsafe(32)`;
the human operator cats it once and saves it locally.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import secrets
import signal
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

PAIRS = ["ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]
TOKEN_FILE = Path("/etc/trading-bot-control.token")
BIND = ("127.0.0.1", 5055)

log = logging.getLogger("bot_control")


def load_or_create_token() -> str:
    if TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text().strip()
        if t:
            return t
    t = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(t + "\n")
    os.chmod(TOKEN_FILE, 0o600)
    log.info("new control token written to %s", TOKEN_FILE)
    return t


TOKEN = load_or_create_token()


def _systemctl(action: str, unit: str) -> dict:
    cp = subprocess.run(
        ["systemctl", action, unit],
        capture_output=True, text=True, timeout=15,
    )
    return {
        "unit": unit,
        "action": action,
        "returncode": cp.returncode,
        "stderr": cp.stderr.strip()[:800] if cp.stderr else "",
    }


def _unit(pair: str) -> str:
    return f"trading-bot@{pair}.service"


def _bot_state(pair: str) -> dict:
    unit = _unit(pair)
    active = subprocess.run(
        ["systemctl", "is-active", unit], capture_output=True, text=True).stdout.strip()
    enabled = subprocess.run(
        ["systemctl", "is-enabled", unit], capture_output=True, text=True).stdout.strip()
    return {"pair": pair, "unit": unit, "state": active, "enabled": enabled}


class Handler(BaseHTTPRequestHandler):
    server_version = "BotControl/1.0"

    def log_message(self, fmt, *args):  # route access log to Python logging
        log.info("%s - %s", self.address_string(), fmt % args)

    # ── helpers ──
    def _send(self, code: int, body: dict | str, content_type="application/json"):
        if isinstance(body, (dict, list)):
            payload = json.dumps(body).encode()
        else:
            payload = str(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        # CORS: we're served from the same origin through nginx, but
        # allow GET across origins so curl and dashboards work
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "X-Control-Token, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(payload)

    def _auth(self) -> bool:
        hdr = self.headers.get("X-Control-Token", "")
        # constant-time compare
        return bool(hdr) and secrets.compare_digest(hdr, TOKEN)

    def _path_parts(self) -> list[str]:
        p = urlparse(self.path).path.strip("/")
        return p.split("/") if p else []

    # ── HTTP verbs ──
    def do_OPTIONS(self):
        self._send(204, "")

    def do_GET(self):
        parts = self._path_parts()
        if parts == ["api", "control", "health"]:
            return self._send(200, {"ok": True, "ts": datetime.datetime.utcnow().isoformat() + "Z"})
        if parts == ["api", "control", "status"]:
            if not self._auth():
                return self._send(401, {"error": "unauthorized"})
            return self._send(200, {"bots": [_bot_state(p) for p in PAIRS]})
        self._send(404, {"error": "not found", "path": self.path})

    def do_POST(self):
        parts = self._path_parts()
        if not self._auth():
            return self._send(401, {"error": "unauthorized"})

        if len(parts) < 3 or parts[:2] != ["api", "control"]:
            return self._send(404, {"error": "not found"})

        action = parts[2]

        if action in ("stop-all", "start-all", "restart-all"):
            verb = {"stop-all": "stop", "start-all": "start", "restart-all": "restart"}[action]
            results = [_systemctl(verb, _unit(p)) for p in PAIRS]
            ok = all(r["returncode"] == 0 for r in results)
            return self._send(200 if ok else 207, {"action": action, "results": results})

        if action in ("stop", "start", "restart") and len(parts) == 4:
            pair = parts[3].upper()
            if pair not in PAIRS:
                return self._send(400, {"error": f"unknown pair: {pair}"})
            return self._send(200, _systemctl(action, _unit(pair)))

        return self._send(404, {"error": "unknown action", "action": action})


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    httpd = HTTPServer(BIND, Handler)

    def _quit(*_):
        log.info("shutting down")
        httpd.shutdown()
    signal.signal(signal.SIGTERM, _quit)
    signal.signal(signal.SIGINT,  _quit)

    log.info("bot_control listening on %s:%s", *BIND)
    log.info("token loaded from %s (%d chars)", TOKEN_FILE, len(TOKEN))
    try:
        httpd.serve_forever()
    finally:
        log.info("bye")


if __name__ == "__main__":
    main()
