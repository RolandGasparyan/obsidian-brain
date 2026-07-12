"""
canary_api_server.py — Static JSON API server for Trading Guru Championship
Serves /var/www/ai-trading-championship/dist/ on port 8765
Endpoints consumed by web app (server/routers.ts):
  GET /api/battle/terminal.json        — real-time account balances + championship
  GET /api/battle/live_battle.json     — raw live battle state
  GET /api/battle/multi_battle_status.json — multi-account status
  GET /api/bots.json                   — bot list
  GET /health                          — health check
"""
import json
import os
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8765
SERVE_ROOT = Path("/var/www/ai-trading-championship/dist")
RUNTIME = Path("/root/canary/runtime")
STATUS_FILE = RUNTIME / "multi_battle_status.json"
CHAMPION_STATE_FILE = RUNTIME / "champion_state.json"
CHAMPION_ROUNDS_FILE = RUNTIME / "battle_rounds.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [canary-api] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("canary-api")


def read_json_file(path: Path):
    """Read JSON file, return None on error."""
    try:
        return json.loads(path.read_text())
    except Exception as e:
        log.warning("read %s: %s", path, e)
        return None


def make_fallback_terminal():
    """Generate a minimal terminal.json from runtime state files if /var/www is not populated."""
    runtime = RUNTIME
    accounts = {}
    for acc_id, label in [("MAIN", "TITAN"), ("SUB1", "VELOCITY"), ("SUB2", "SENTINEL")]:
        state_file = runtime / f"state_{acc_id.lower()}.json"
        st = read_json_file(state_file) or {}
        accounts[acc_id] = {
            "agent_label": label,
            "capital_usd": st.get("balance", 0),
            "status": "LIVE" if st else "UNKNOWN",
            "trades_today": st.get("trades_today", 0),
            "session_pnl_usd": st.get("session_pnl", 0),
            "daily_dd_usd": st.get("daily_dd_usd", 0),
            "open_positions": len(st.get("positions", {})),
            "positions": st.get("positions", {}),
        }
    multi = read_json_file(STATUS_FILE) or {}
    # Prefer champion_battle.py state files (v2.2+) for championship data
    champ_state = read_json_file(CHAMPION_STATE_FILE) or {}
    champ_rounds = read_json_file(CHAMPION_ROUNDS_FILE) or {}
    # Merge champion_state accounts into accounts dict if available
    if champ_state.get("agents"):
        for agent in champ_state["agents"]:
            name = agent.get("name", "")
            acc_map = {"TITAN": "MAIN", "VELOCITY": "SUB1", "SENTINEL": "SUB2"}
            acc_id = acc_map.get(name)
            if acc_id and acc_id in accounts:
                accounts[acc_id]["capital_usd"] = agent.get("balance", 0)
                accounts[acc_id]["session_pnl_usd"] = agent.get("session_pnl", 0)
                accounts[acc_id]["daily_dd_usd"] = agent.get("daily_dd", 0)
                accounts[acc_id]["open_positions"] = len(agent.get("positions", {}))
                accounts[acc_id]["positions"] = agent.get("positions", {})
                accounts[acc_id]["status"] = "LIVE" if agent.get("mode", "").startswith("LIVE") else "SIM"
    # Build championship from champion_battle data (v2.2 round-end USDT sweep)
    championship = champ_state.get("championship", multi.get("championship", {}))
    if not championship and champ_rounds:
        # Reconstruct from battle_rounds.json
        history = champ_rounds.get("history", [])
        crowns = {}
        for r in history:
            w = r.get("winner")
            if w:
                crowns[w] = crowns.get(w, 0) + 1
        championship = {
            "current_round_id": champ_rounds.get("current_round_id"),
            "round_interval_sec": champ_rounds.get("round_interval_sec"),
            "history": list(reversed(history))[:10],
            "round_wins": crowns,
            "winner_rule": "highest_usdt_balance",
        }
    pairs = champ_state.get("pairs") or ["FLOKI/USDT", "WIF/USDT", "OP/USDT", "SHIB/USDT",
                                          "DOT/USDT", "ADA/USDT", "UNI/USDT", "ATOM/USDT", "BNB/USDT"]
    strategy = champ_state.get("strategy") or "CMO_CHANDE"
    return {
        "schema_version": "2.0",
        "mode": champ_state.get("mode", "LIVE_REAL_CAPITAL"),
        "disclaimer": "REAL capital. 3 Gate.io accounts live.",
        "accounts": accounts,
        "strategy": strategy,
        "pairs": pairs,
        "championship": championship,
        "live": {
            "aggregate_session_pnl_usd": sum(
                float(a.get("session_pnl_usd", 0)) for a in accounts.values()
            ),
            "aggregate_trades_today": sum(
                int(a.get("trades_today", 0)) for a in accounts.values()
            ),
            "alive_accounts": sum(1 for a in accounts.values() if a["status"] == "LIVE"),
            "total_accounts": 3,
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


class CanaryAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Suppress default HTTP access log spam; use our logger
        if "health" not in self.path:
            log.info("GET %s %s", self.path, args[1] if len(args) > 1 else "")

    def send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def send_404(self):
        self.send_json({"error": "not found", "path": self.path}, 404)

    def do_GET(self):
        path = self.path.split("?")[0]

        # Health check
        if path == "/health":
            self.send_json({"ok": True, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            return

        # Serve static JSON files from /var/www/...
        if path.startswith("/api/") or path.startswith("/bots"):
            # Map URL path to filesystem path
            fs_path = SERVE_ROOT / path.lstrip("/")
            if fs_path.exists() and fs_path.is_file():
                data = read_json_file(fs_path)
                if data is not None:
                    self.send_json(data)
                    return
            # Fallback: generate terminal.json from runtime state
            if "terminal.json" in path:
                data = make_fallback_terminal()
                self.send_json(data)
                return
            if "multi_battle_status" in path:
                data = read_json_file(STATUS_FILE) or {"error": "no data yet"}
                self.send_json(data)
                return
            self.send_404()
            return

        # Champion logs + state endpoints
        if self._serve_logs_and_state(path):
            return

        self.send_404()

    def _serve_logs_and_state(self, path):
        """Serve champion_battle logs and state for remote debugging."""
        if path in ("/api/logs/champion", "/api/logs/champion_battle"):
            log_file = RUNTIME / "champion_battle.log"
            stderr_file = RUNTIME / "champion_battle.stderr.log"
            lines = []
            for f in (log_file, stderr_file):
                if f.exists():
                    try:
                        all_lines = f.read_text(errors="replace").splitlines()
                        lines.extend([f"[{f.name}] {l}" for l in all_lines[-100:]])
                    except Exception as e:
                        lines.append(f"[error reading {f.name}]: {e}")
            self.send_json({"lines": lines[-150:], "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            return True
        if path == "/api/champion/state":
            data = read_json_file(CHAMPION_STATE_FILE) or {"error": "champion_state.json not found"}
            self.send_json(data)
            return True
        return False

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()


def main():
    log.info("canary-api starting on port %d", PORT)
    log.info("serving %s", SERVE_ROOT)
    server = HTTPServer(("0.0.0.0", PORT), CanaryAPIHandler)
    log.info("canary-api ready — http://0.0.0.0:%d", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("canary-api stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
