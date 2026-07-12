#!/usr/bin/env python3
"""
Canary Balances API — exposes the *real* spot USDT balances for the 3 canary
agents (TITAN / VELOCITY / SENTINEL) to the Manus webdev backend.

Why this lives on the DO VPS:
- Gate.io API keys for these accounts are IP-whitelisted to the DO VPS only.
  Calling Gate.io from anywhere else (Manus sandbox, GCP VPS, end-user browser)
  returns HTTP 403, which is the correct security posture.
- This service runs LOCALLY on the DO VPS, signs the Gate.io request with the
  on-disk credentials, and re-publishes only the public-safe numbers
  (total / available / locked) over an unauthenticated CORS-enabled JSON
  endpoint that the Manus webdev tRPC layer can proxy.

Endpoints:
    GET /healthz            -> 200 OK { "ok": true }
    GET /api/balances       -> { agents: [{ key, label, total, available, locked, isLive, error }, ...], ts }

Run as a systemd service (see install_balances_api.sh) on port 8090. We do not
collide with the existing canary-api on 8080.
"""

import hashlib
import hmac
import json
import os
import pathlib
import time
from typing import Optional, Tuple
from urllib import parse, request, error

from flask import Flask, jsonify

GATE_BASE = "https://api.gateio.ws/api/v4"
KEY_DIR = pathlib.Path(os.environ.get("CANARY_KEY_DIR", "/root/canary"))
PORT = int(os.environ.get("BALANCES_PORT", "8090"))

# (file_name, agent_key, friendly_label)
AGENTS = [
    (".api_key_main", "main", "TITAN"),
    (".api_key_sub1", "sub1", "VELOCITY"),
    (".api_key_sub2", "sub2", "SENTINEL"),
]

app = Flask(__name__)


def _read_keys(filename: str) -> Optional[Tuple[str, str]]:
    p = KEY_DIR / filename
    if not p.exists():
        return None
    raw = p.read_text().strip()
    if ":" not in raw:
        return None
    k, s = raw.split(":", 1)
    return k.strip(), s.strip()


def _gate_get(path: str, query: str, key: str, secret: str, timeout: float = 6.0):
    """Perform a signed GET against the Gate.io v4 API. Returns parsed JSON or
    raises. Designed for low-traffic balance reads only."""
    ts = str(int(time.time()))
    body_hash = hashlib.sha512(b"").hexdigest()
    sign_str = f"GET\n{path}\n{query}\n{body_hash}\n{ts}"
    sign = hmac.new(secret.encode(), sign_str.encode(), hashlib.sha512).hexdigest()
    url = f"{GATE_BASE.rstrip('/')}{path.replace('/api/v4', '', 1)}"
    if query:
        url = f"{url}?{query}"
    req = request.Request(
        url,
        headers={
            "KEY": key,
            "SIGN": sign,
            "Timestamp": ts,
            "Accept": "application/json",
            "User-Agent": "TradingGuruBalancesAPI/1.0",
        },
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _spot_usdt(key: str, secret: str) -> dict:
    data = _gate_get("/api/v4/spot/accounts", "currency=USDT", key, secret)
    if not isinstance(data, list):
        return {"total": 0.0, "available": 0.0, "locked": 0.0}
    usdt = next((row for row in data if row.get("currency") == "USDT"), None)
    if not usdt:
        return {"total": 0.0, "available": 0.0, "locked": 0.0}
    available = float(usdt.get("available") or 0)
    locked = float(usdt.get("locked") or 0)
    return {"total": available + locked, "available": available, "locked": locked}


@app.after_request
def _cors(resp):
    # The webdev tRPC layer proxies this server-side, but allowing CORS keeps
    # the endpoint usable for direct browser debugging.
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "ts": int(time.time())})


@app.get("/api/balances")
def balances():
    out = []
    for filename, agent_key, label in AGENTS:
        creds = _read_keys(filename)
        if not creds:
            out.append({
                "key": agent_key, "label": label,
                "total": 0.0, "available": 0.0, "locked": 0.0,
                "isLive": False, "error": f"keys not found at {filename}",
            })
            continue
        try:
            bal = _spot_usdt(*creds)
            out.append({
                "key": agent_key, "label": label,
                "total": round(bal["total"], 2),
                "available": round(bal["available"], 2),
                "locked": round(bal["locked"], 2),
                "isLive": True, "error": None,
            })
        except error.HTTPError as e:
            out.append({
                "key": agent_key, "label": label,
                "total": 0.0, "available": 0.0, "locked": 0.0,
                "isLive": False, "error": f"gate http {e.code}",
            })
        except Exception as e:  # noqa: BLE001
            out.append({
                "key": agent_key, "label": label,
                "total": 0.0, "available": 0.0, "locked": 0.0,
                "isLive": False, "error": str(e)[:160],
            })
    return jsonify({"ts": int(time.time()), "agents": out})


if __name__ == "__main__":
    # Bind to all interfaces so the service is reachable from outside the VPS
    # (the firewall must be the security boundary, not 127.0.0.1).
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
