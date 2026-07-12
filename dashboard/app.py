"""
L99 Bot — Trading Dashboard (rebuilt clean)
Reads real-time data from PostgreSQL.
Port 8080. Auto-refresh every 30s.
"""
import os
from datetime import datetime, timezone
from flask import Flask, render_template_string
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)

DB_CFG = dict(
    dbname=os.getenv("DB_NAME", "l99"),
    user=os.getenv("DB_USER", "l99_user"),
    password=os.getenv("DB_PASS", ""),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 5432)),
)

LIVE_TRADING = os.getenv("LIVE_TRADING", "false").lower() == "true"


def get_conn():
    return psycopg2.connect(**DB_CFG)


def query(sql, args=()):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, args)
            return cur.fetchall()


def query_one(sql, args=()):
    rows = query(sql, args)
    return rows[0] if rows else None


def get_kpis():
    sm = query_one("SELECT live_sharpe, drawdown, open_positions, total_equity FROM system_metrics ORDER BY id DESC LIMIT 1")
    closed_trades = query("SELECT pnl, r_multiple FROM trades WHERE status='CLOSED'")
    if not sm:
        sm = {"live_sharpe": None, "drawdown": 0, "open_positions": 0, "total_equity": 0}
    total_trades = len(closed_trades)
    wins = sum(1 for t in closed_trades if (t["pnl"] or 0) > 0)
    win_rate = (wins / total_trades * 100) if total_trades else 0
    total_pnl = sum(float(t["pnl"] or 0) for t in closed_trades)
    avg_r = sum(float(t["r_multiple"] or 0) for t in closed_trades) / total_trades if total_trades else 0
    sharpe = sm.get("live_sharpe")
    if sharpe is None or (isinstance(sharpe, float) and sharpe != sharpe):
        sharpe_str = "nan"
    else:
        sharpe_str = f"{float(sharpe):.3f}"
    return {
        "equity": float(sm["total_equity"] or 0),
        "drawdown": float(sm["drawdown"] or 0) * 100,
        "sharpe": sharpe_str,
        "open_pos": int(sm["open_positions"] or 0),
        "total_trades": total_trades,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_r": avg_r,
    }


def get_equity_history(n=50):
    rows = query(
        "SELECT total_equity FROM system_metrics ORDER BY id DESC LIMIT %s", (n,)
    )
    return list(reversed([float(r["total_equity"] or 0) for r in rows]))


def get_trade_history(n=50):
    return query(
        """SELECT id, symbol, entry_time, exit_time, entry_price, exit_price,
                  position_size, r_multiple, pnl, fee
           FROM trades ORDER BY id DESC LIMIT %s""", (n,)
    )


def get_recent_signals(n=40):
    return query(
        """SELECT id, symbol, signal_time, adx, volume_ratio, breakout_level, regime_state
           FROM signals ORDER BY id DESC LIMIT %s""", (n,)
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>L99 Bot — Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d0f14; color: #e2e8f0; font-family: 'Courier New', monospace; font-size: 13px; }
  header { background: #111827; border-bottom: 1px solid #1e293b; padding: 14px 24px; display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 18px; font-weight: 700; color: #38bdf8; letter-spacing: 1px; }
  header .mode { padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; }
  header .mode-live { background: #7f1d1d; color: #f87171; }
  header .mode-paper { background: #14532d; color: #4ade80; }
  header .ts { color: #64748b; font-size: 11px; margin-left: auto; }
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 20px 24px 0; }
  .card { background: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; }
  .card .label { color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
  .card .value { font-size: 24px; font-weight: 700; }
  .green { color: #4ade80; }
  .red { color: #f87171; }
  .yellow { color: #fbbf24; }
  .dim { color: #64748b; }
  section { padding: 0 24px 20px; }
  section h2 { color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 24px 0 10px; border-bottom: 1px solid #1e293b; padding-bottom: 6px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { color: #64748b; font-size: 11px; text-align: left; padding: 8px 10px; border-bottom: 1px solid #1e293b; font-weight: 400; text-transform: uppercase; letter-spacing: 0.5px; }
  td { padding: 9px 10px; border-bottom: 1px solid #0f172a; }
  td.symbol { color: #38bdf8; font-weight: 700; }
  .badge-win { background: #14532d; color: #4ade80; padding: 2px 7px; border-radius: 3px; font-size: 10px; }
  .badge-loss { background: #450a0a; color: #f87171; padding: 2px 7px; border-radius: 3px; font-size: 10px; }
  .badge-bull { background: #14532d; color: #4ade80; padding: 2px 7px; border-radius: 3px; font-size: 10px; }
  .equity-chart { background: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; margin: 20px 24px 0; }
  .equity-chart h2 { margin: 0 0 12px; border: none; padding: 0; }
  .empty { color: #64748b; text-align: center; padding: 30px; font-style: italic; }
  svg { width: 100%; height: 80px; }
</style>
</head>
<body>
<header>
  <h1>⚡ L99 BOT</h1>
  <span class="mode {{ 'mode-live' if live else 'mode-paper' }}">{{ 'LIVE' if live else 'PAPER' }}</span>
  <span class="ts">Auto-refresh: 30s | {{ now }}</span>
</header>

<div class="grid">
  <div class="card">
    <div class="label">Equity</div>
    <div class="value green">${{ "{:,.2f}".format(kpis.equity) }}</div>
  </div>
  <div class="card">
    <div class="label">Drawdown</div>
    <div class="value {{ 'red' if kpis.drawdown < -1 else 'green' }}">{{ "{:+.2f}".format(kpis.drawdown) }}%</div>
  </div>
  <div class="card">
    <div class="label">Sharpe (rolling)</div>
    <div class="value">{{ kpis.sharpe }}</div>
  </div>
  <div class="card">
    <div class="label">Open Positions</div>
    <div class="value">{{ kpis.open_pos }}</div>
  </div>
  <div class="card">
    <div class="label">Total Trades</div>
    <div class="value">{{ kpis.total_trades }}</div>
  </div>
  <div class="card">
    <div class="label">Win Rate</div>
    <div class="value {{ 'green' if kpis.win_rate >= 40 else ('yellow' if kpis.win_rate >= 30 else 'red') }}">{{ "{:.1f}".format(kpis.win_rate) }}%</div>
  </div>
  <div class="card">
    <div class="label">Total PnL</div>
    <div class="value {{ 'green' if kpis.total_pnl >= 0 else 'red' }}">{{ "{:+.2f}".format(kpis.total_pnl) }} USDT</div>
  </div>
  <div class="card">
    <div class="label">Avg R-Multiple</div>
    <div class="value {{ 'green' if kpis.avg_r >= 0 else 'red' }}">{{ "{:+.2f}".format(kpis.avg_r) }}R</div>
  </div>
</div>

<div class="equity-chart">
  <h2>Equity History (last {{ equity_n }} readings)</h2>
  {% if equity_pts %}
  <svg viewBox="0 0 500 80" preserveAspectRatio="none">
    <polyline fill="none" stroke="#38bdf8" stroke-width="1.5" points="{{ equity_polyline }}" />
  </svg>
  {% else %}
  <div class="empty">No equity history yet — waiting for first reading</div>
  {% endif %}
</div>

<section>
  <h2>Trade History (last 50)</h2>
  <table>
    <thead><tr>
      <th>#</th><th>Symbol</th><th>Entry</th><th>Exit</th>
      <th>Entry $</th><th>Exit $</th><th>Size</th><th>R</th>
      <th>PnL (USDT)</th><th>Fee</th><th>Result</th>
    </tr></thead>
    <tbody>
    {% for t in trades %}
      <tr>
        <td>{{ t.id }}</td>
        <td class="symbol">{{ t.symbol }}</td>
        <td class="dim">{{ t.entry_time.strftime('%m/%d %H:%M') if t.entry_time else '-' }}</td>
        <td class="dim">{{ t.exit_time.strftime('%m/%d %H:%M') if t.exit_time else '-' }}</td>
        <td>{{ "{:.4f}".format(t.entry_price or 0) }}</td>
        <td>{{ "{:.4f}".format(t.exit_price or 0) }}</td>
        <td>{{ "{:.4f}".format(t.position_size or 0) }}</td>
        <td class="{{ 'green' if (t.r_multiple or 0) >= 0 else 'red' }}">{{ "{:+.2f}".format(t.r_multiple or 0) }}</td>
        <td class="{{ 'green' if (t.pnl or 0) >= 0 else 'red' }}">{{ "{:+.2f}".format(t.pnl or 0) }}</td>
        <td class="dim">{{ "{:.4f}".format(t.fee or 0) }}</td>
        <td>{% if (t.pnl or 0) >= 0 %}<span class="badge-win">WIN</span>{% else %}<span class="badge-loss">LOSS</span>{% endif %}</td>
      </tr>
    {% else %}
      <tr><td colspan="11" class="empty">No closed trades yet — bot scanning for SACRED signal</td></tr>
    {% endfor %}
    </tbody>
  </table>
</section>

<section>
  <h2>Recent Signals (last 40)</h2>
  <table>
    <thead><tr><th>#</th><th>Symbol</th><th>Signal Time</th><th>ADX</th><th>Vol Ratio</th><th>Breakout Level</th><th>Regime</th></tr></thead>
    <tbody>
    {% for s in signals %}
      <tr>
        <td>{{ s.id }}</td>
        <td class="symbol">{{ s.symbol }}</td>
        <td class="dim">{{ s.signal_time.strftime('%m/%d %H:%M') if s.signal_time else '-' }}</td>
        <td class="green">{{ "{:.2f}".format(s.adx or 0) }}</td>
        <td>{{ "{:.2f}".format(s.volume_ratio or 0) }}x</td>
        <td>{{ "{:.4f}".format(s.breakout_level or 0) }}</td>
        <td><span class="badge-bull">{{ s.regime_state or '-' }}</span></td>
      </tr>
    {% else %}
      <tr><td colspan="7" class="empty">No signals yet — next 4H bar close: {{ next_bar }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
</section>

</body>
</html>"""


@app.route("/")
def home():
    kpis = get_kpis()
    eq = get_equity_history(50)
    trades = get_trade_history(50)
    signals = get_recent_signals(40)
    if eq:
        mn, mx = min(eq), max(eq)
        rng = mx - mn if mx > mn else 1
        pts = " ".join(
            f"{i*500/(len(eq)-1) if len(eq) > 1 else 250:.1f},{80 - ((v - mn) / rng) * 70 - 5:.1f}"
            for i, v in enumerate(eq)
        )
    else:
        pts = ""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    next_bar_hour = (datetime.now(timezone.utc).hour // 4 + 1) * 4 % 24
    next_bar = f"{next_bar_hour:02d}:00 UTC"
    return render_template_string(
        TEMPLATE,
        kpis=kpis,
        equity_pts=eq,
        equity_polyline=pts,
        equity_n=len(eq),
        trades=trades,
        signals=signals,
        live=LIVE_TRADING,
        now=now,
        next_bar=next_bar,
    )


@app.route("/health")
def health():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
