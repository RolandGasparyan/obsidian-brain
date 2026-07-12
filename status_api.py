#!/usr/bin/env python3
"""
Trading Engine Status API v3 — Interactive Dashboard on port 8080.
Serves the new animated TradingView-style dashboard at / and JSON at /api.
Reads from engine_state.json (updated every 5 ticks by the engine).
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

STATE_FILE  = "/home/ubuntu/trading_engine/engine_state_v8.json"
KB_FILE     = "/home/ubuntu/trading_engine/knowledge_base.json"
DB_FILE     = "/home/ubuntu/trading_engine/trades.db"
DASH_FILE   = "/home/ubuntu/trading_engine/dashboard.html"

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return None

def load_kb():
    try:
        with open(KB_FILE) as f:
            kb = json.load(f)
            return kb.get("upgrades", [])[-10:]
    except Exception:
        return []

def load_recent_trades(limit=20):
    """Load recent closed trades from SQLite."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT agent_name as agent, asset, trading_mode as mode,
                   strategy, risk_mode,
                   entry_price, exit_price, pnl_usd, outcome,
                   close_time as closed_at
            FROM trades
            WHERE outcome IN ('WIN','LOSS')
            ORDER BY close_time DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []

def load_winning_setups():
    """Aggregate top winning setups from DB."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            SELECT strategy, trading_mode as mode,
                   COUNT(*) as total,
                   SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
                   SUM(pnl_usd) as total_pnl
            FROM trades
            WHERE outcome IN ('WIN','LOSS')
            GROUP BY strategy, trading_mode
            HAVING total >= 5
            ORDER BY (wins * 1.0 / total) DESC
            LIMIT 6
        """)
        rows = cur.fetchall()
        conn.close()
        result = []
        for r in rows:
            strat, mode, total, wins, pnl = r
            wr = wins / total * 100 if total else 0
            result.append({
                "strategy": strat or "—",
                "mode": mode or "—",
                "total": total,
                "wins": wins,
                "win_rate": round(wr, 1),
                "total_pnl": round(pnl or 0, 2)
            })
        return result
    except Exception:
        return []

def load_dashboard_html():
    """Load the pre-built interactive dashboard HTML."""
    try:
        with open(DASH_FILE, 'rb') as f:
            return f.read()
    except Exception:
        return b"<html><body><h1>Dashboard loading...</h1></body></html>"

def build_api_json(state):
    """Build rich JSON response for the dashboard /api endpoint."""
    if not state:
        return json.dumps({"status": "starting", "agents": []})

    agents_raw = state.get("agents", [])
    guru_raw   = state.get("guru", {})
    all_agents = agents_raw + ([guru_raw] if guru_raw else [])

    # Normalize agent fields
    agents_out = []
    for a in all_agents:
        cap  = a.get("capital", 1000.0)
        cold = a.get("cold_wallet", 0.0)
        wins = a.get("wins", 0)
        losses = a.get("losses", 0)
        total = wins + losses
        wr = a.get("win_rate", (wins / total * 100) if total else 0)
        is_guru   = a.get("name") == "TRADING GURU"
        is_halted = a.get("halted", False)
        status = "LEARNING" if is_guru else ("HALTED" if is_halted else "ACTIVE")
        agents_out.append({
            "name":        a.get("name", "UNKNOWN"),
            "strategy":    a.get("strategy", "—"),
            "mode":        a.get("current_mode", a.get("mode", "—")),
            "risk":        a.get("risk_mode", a.get("risk", "BALANCED")),
            "capital":     round(cap, 2),
            "cold_wallet": round(cold, 2),
            "total_value": round(cap + cold, 2),
            "wins":        wins,
            "losses":      losses,
            "win_rate":    round(wr, 1),
            "status":      status,
            "open_trades": a.get("open_trades", 0),
        })

    # Recent trades from DB (richer than state file)
    recent_db = load_recent_trades(20)
    recent_trades = []
    for t in recent_db:
        recent_trades.append({
            "agent":    t.get("agent", ""),
            "asset":    t.get("asset", ""),
            "mode":     t.get("mode", ""),
            "strategy": t.get("strategy", ""),
            "risk":     t.get("risk_mode", "BALANCED"),
            "outcome":  t.get("outcome", ""),
            "pnl":      round(t.get("pnl_usd", 0), 4),
            "time":     (t.get("closed_at") or "")[:19].replace("T", " "),
        })

    # Winning setups from DB
    winning_setups = load_winning_setups()

    # Guru upgrades
    upgrades = load_kb()
    guru_upgrades = len(upgrades)

    # Prices from state
    prices = state.get("prices", {})

    # Uptime
    ts_str = state.get("timestamp", "")
    uptime_hours = 0
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        # Approximate: engine started ~24h ago
        uptime_hours = state.get("uptime_hours", 24)
    except Exception:
        uptime_hours = state.get("uptime_hours", 0)

    return json.dumps({
        "status":           "running",
        "version":          state.get("version", "v8.0"),
        "tick":             state.get("tick", 0),
        "timestamp":        ts_str,
        "uptime_hours":     uptime_hours,
        "agents":           agents_out,
        "total_agents":     len(agents_out),
        "strategies_count": state.get("strategies_count", 30),
        "recent_trades":    recent_trades,
        "winning_setups":   winning_setups,
        "guru_upgrades":    guru_upgrades,
        "prices":           prices,
    }, indent=2)


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress access logs

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api":
            state = load_state()
            body  = build_api_json(state).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/health":
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        else:
            # Serve the interactive dashboard for all other paths
            body = load_dashboard_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    print("Status API v3 running on http://0.0.0.0:8080")
    print(f"Dashboard: {DASH_FILE}")
    server.serve_forever()
