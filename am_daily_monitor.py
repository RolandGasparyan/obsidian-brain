#!/usr/bin/env python3
"""
Anti-Martingale Daily Performance Monitor
Runs via cron at 00:00 UTC every day on the cloud computer.
Queries trades.db, computes all KPIs, writes JSON snapshot + Markdown report.
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ── CONFIG ────────────────────────────────────────────────────────────────────
DB_PATH      = '/home/ubuntu/trading_engine/trades.db'
REPORTS_DIR  = '/home/ubuntu/trading_engine/daily_reports'
SNAPSHOT_PATH = '/home/ubuntu/trading_engine/am_latest_snapshot.json'
AM_SESSION_PREFIX = 'v9_178'   # All v9.2 sessions start with this prefix
# The Anti-Martingale era starts from session v9_1780327062 (2026-06-01)
AM_START_SESSION = 'v9_1780327062'
AM_START_TIME    = '2026-06-01T15:19:00+00:00'

os.makedirs(REPORTS_DIR, exist_ok=True)

now_utc = datetime.now(timezone.utc)
today_str = now_utc.strftime('%Y-%m-%d')
yesterday_str = (now_utc - timedelta(days=1)).strftime('%Y-%m-%d')

# ── DB QUERY ──────────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def q(sql, params=()):
    c.execute(sql, params)
    return c.fetchall()

def q1(sql, params=()):
    c.execute(sql, params)
    row = c.fetchone()
    return row[0] if row and row[0] is not None else 0

# ── OVERALL AM STATS (all sessions since v9.2 launch) ────────────────────────
# Get all sessions that started on or after AM_START_TIME
c.execute("""
    SELECT DISTINCT session_id FROM trades
    WHERE open_time >= ? AND outcome IS NOT NULL
    ORDER BY open_time
""", (AM_START_TIME,))
am_sessions = [r[0] for r in c.fetchall()]

if not am_sessions:
    print("No Anti-Martingale trades found yet.")
    conn.close()
    sys.exit(0)

placeholders = ','.join(['?' for _ in am_sessions])

# Overall lifetime AM stats
c.execute(f"""
    SELECT
        COUNT(*) as total_trades,
        SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) as losses,
        ROUND(SUM(pnl_usd), 2) as total_pnl,
        ROUND(AVG(pnl_usd), 4) as avg_pnl,
        ROUND(AVG(CASE WHEN outcome='WIN' THEN pnl_usd END), 4) as avg_win,
        ROUND(AVG(CASE WHEN outcome='LOSS' THEN pnl_usd END), 4) as avg_loss,
        ROUND(MAX(pnl_usd), 4) as best_trade,
        ROUND(MIN(pnl_usd), 4) as worst_trade,
        ROUND(SUM(CASE WHEN outcome='WIN' THEN pnl_usd ELSE 0 END), 2) as gross_profit,
        ROUND(SUM(CASE WHEN outcome='LOSS' THEN pnl_usd ELSE 0 END), 2) as gross_loss
    FROM trades
    WHERE session_id IN ({placeholders}) AND outcome IS NOT NULL
""", am_sessions)
row = c.fetchone()
total_trades, wins, losses, total_pnl, avg_pnl, avg_win, avg_loss, \
    best_trade, worst_trade, gross_profit, gross_loss = row

win_rate = round(wins / total_trades * 100, 2) if total_trades else 0
profit_factor = round(abs(gross_profit / gross_loss), 3) if gross_loss else 0
wl_ratio = round(avg_win / abs(avg_loss), 3) if avg_loss else 0

# ── YESTERDAY'S STATS ─────────────────────────────────────────────────────────
c.execute(f"""
    SELECT
        COUNT(*) as trades,
        SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(pnl_usd), 2) as pnl,
        ROUND(AVG(pnl_usd), 4) as avg_pnl
    FROM trades
    WHERE session_id IN ({placeholders})
      AND outcome IS NOT NULL
      AND DATE(close_time) = ?
""", am_sessions + [yesterday_str])
yday = c.fetchone()
yday_trades, yday_wins, yday_pnl, yday_avg = yday if yday[0] else (0, 0, 0.0, 0.0)
yday_wr = round(yday_wins / yday_trades * 100, 2) if yday_trades else 0

# ── TODAY'S STATS (so far) ────────────────────────────────────────────────────
c.execute(f"""
    SELECT
        COUNT(*) as trades,
        SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(pnl_usd), 2) as pnl
    FROM trades
    WHERE session_id IN ({placeholders})
      AND outcome IS NOT NULL
      AND DATE(close_time) = ?
""", am_sessions + [today_str])
today = c.fetchone()
today_trades, today_wins, today_pnl = today if today[0] else (0, 0, 0.0)
today_wr = round(today_wins / today_trades * 100, 2) if today_trades else 0

# ── AGENT LEADERBOARD (AM era) ────────────────────────────────────────────────
c.execute(f"""
    SELECT agent_name,
           COUNT(*) as trades,
           SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(pnl_usd), 2) as pnl,
           ROUND(AVG(position_size), 0) as avg_pos
    FROM trades
    WHERE session_id IN ({placeholders}) AND outcome IS NOT NULL
    GROUP BY agent_name
    ORDER BY pnl DESC
""", am_sessions)
agents = [{'name': r[0], 'trades': r[1], 'wins': r[2],
           'pnl': r[3], 'avg_pos': r[4],
           'win_rate': round(r[2]/r[1]*100, 1) if r[1] else 0}
          for r in c.fetchall()]

# ── STREAK STATS: max win streak in AM era ────────────────────────────────────
c.execute(f"""
    SELECT outcome FROM trades
    WHERE session_id IN ({placeholders}) AND outcome IS NOT NULL
    ORDER BY close_time
""", am_sessions)
outcomes = [r[0] for r in c.fetchall()]
max_win_streak = cur_streak = 0
for o in outcomes:
    if o == 'WIN':
        cur_streak += 1
        max_win_streak = max(max_win_streak, cur_streak)
    else:
        cur_streak = 0

# ── STRATEGY LEADERBOARD (AM era) ─────────────────────────────────────────────
c.execute(f"""
    SELECT strategy,
           COUNT(*) as trades,
           SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(pnl_usd), 2) as pnl
    FROM trades
    WHERE session_id IN ({placeholders}) AND outcome IS NOT NULL
    GROUP BY strategy
    ORDER BY pnl DESC
    LIMIT 10
""", am_sessions)
strategies = [{'name': r[0], 'trades': r[1],
               'win_rate': round(r[2]/r[1]*100, 1) if r[1] else 0,
               'pnl': r[3]}
              for r in c.fetchall()]

# ── POSITION SIZE DISTRIBUTION ────────────────────────────────────────────────
c.execute(f"""
    SELECT
        ROUND(AVG(position_size), 0) as avg_pos,
        ROUND(MIN(position_size), 0) as min_pos,
        ROUND(MAX(position_size), 0) as max_pos,
        SUM(CASE WHEN position_size > 5000 THEN 1 ELSE 0 END) as large_count,
        COUNT(*) as total
    FROM trades
    WHERE session_id IN ({placeholders}) AND outcome IS NOT NULL
""", am_sessions)
pos_row = c.fetchone()
avg_pos, min_pos, max_pos, large_count, pos_total = pos_row
large_pct = round(large_count / pos_total * 100, 1) if pos_total else 0

# ── DAILY PnL HISTORY (last 7 days) ──────────────────────────────────────────
c.execute(f"""
    SELECT DATE(close_time) as day,
           COUNT(*) as trades,
           SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(pnl_usd), 2) as pnl
    FROM trades
    WHERE session_id IN ({placeholders}) AND outcome IS NOT NULL
    GROUP BY day
    ORDER BY day DESC
    LIMIT 7
""", am_sessions)
daily_history = [{'date': r[0], 'trades': r[1],
                  'win_rate': round(r[2]/r[1]*100, 1) if r[1] else 0,
                  'pnl': r[3]}
                 for r in c.fetchall()]

conn.close()

# ── BUILD SNAPSHOT ────────────────────────────────────────────────────────────
snapshot = {
    'generated_at': now_utc.isoformat(),
    'report_date': today_str,
    'am_start_date': '2026-06-01',
    'sessions_count': len(am_sessions),
    'lifetime': {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate_pct': win_rate,
        'total_pnl_usd': total_pnl,
        'avg_pnl_per_trade': avg_pnl,
        'avg_win_usd': avg_win,
        'avg_loss_usd': avg_loss,
        'best_trade_usd': best_trade,
        'worst_trade_usd': worst_trade,
        'gross_profit_usd': gross_profit,
        'gross_loss_usd': gross_loss,
        'profit_factor': profit_factor,
        'wl_ratio': wl_ratio,
        'max_win_streak': max_win_streak,
        'avg_position_usd': avg_pos,
        'max_position_usd': max_pos,
        'large_pos_pct': large_pct,
    },
    'yesterday': {
        'date': yesterday_str,
        'trades': yday_trades,
        'wins': yday_wins,
        'win_rate_pct': yday_wr,
        'pnl_usd': yday_pnl,
        'avg_pnl': yday_avg,
    },
    'today_so_far': {
        'date': today_str,
        'trades': today_trades,
        'wins': today_wins,
        'win_rate_pct': today_wr,
        'pnl_usd': today_pnl,
    },
    'agent_leaderboard': agents[:10],
    'strategy_leaderboard': strategies,
    'daily_history': daily_history,
}

# Save snapshot (always overwritten — latest state)
with open(SNAPSHOT_PATH, 'w') as f:
    json.dump(snapshot, f, indent=2)

# ── BUILD MARKDOWN REPORT ─────────────────────────────────────────────────────
report_path = os.path.join(REPORTS_DIR, f'am_report_{today_str}.md')

lines = [
    f"# Anti-Martingale Daily Report — {today_str}",
    f"_Generated at {now_utc.strftime('%H:%M UTC')} | Engine v9.2 | Cloud: 34.139.162.200_",
    "",
    "## Lifetime Performance (since 2026-06-01)",
    "",
    f"| Metric | Value |",
    f"|---|---|",
    f"| Total Trades | {total_trades:,} |",
    f"| Win Rate | {win_rate:.1f}% |",
    f"| Profit Factor | {profit_factor:.3f}x |",
    f"| W:L Ratio | {wl_ratio:.2f}x |",
    f"| Total PnL | ${total_pnl:+,.2f} |",
    f"| Avg PnL/Trade | ${avg_pnl:+.4f} |",
    f"| Avg Win | ${avg_win:.2f} |",
    f"| Avg Loss | ${avg_loss:.2f} |",
    f"| Best Trade | ${best_trade:+.2f} |",
    f"| Worst Trade | ${worst_trade:+.2f} |",
    f"| Max Win Streak | {max_win_streak} |",
    f"| Avg Position Size | ${avg_pos:,.0f} |",
    f"| Max Position Size | ${max_pos:,.0f} |",
    f"| Large Positions (>$5K) | {large_pct:.1f}% of trades |",
    "",
    "## Yesterday's Session",
    "",
    f"| Metric | Value |",
    f"|---|---|",
    f"| Date | {yesterday_str} |",
    f"| Trades | {yday_trades:,} |",
    f"| Win Rate | {yday_wr:.1f}% |",
    f"| PnL | ${yday_pnl:+,.2f} |",
    f"| Avg PnL/Trade | ${yday_avg:+.4f} |",
    "",
    "## Today So Far",
    "",
    f"| Metric | Value |",
    f"|---|---|",
    f"| Date | {today_str} |",
    f"| Trades | {today_trades:,} |",
    f"| Win Rate | {today_wr:.1f}% |",
    f"| PnL | ${today_pnl:+,.2f} |",
    "",
    "## 7-Day PnL History",
    "",
    "| Date | Trades | Win Rate | PnL |",
    "|---|---|---|---|",
]
for d in daily_history:
    sign = '+' if d['pnl'] >= 0 else ''
    lines.append(f"| {d['date']} | {d['trades']:,} | {d['win_rate']:.1f}% | ${sign}{d['pnl']:.2f} |")

lines += [
    "",
    "## Top 10 Agents (AM Era)",
    "",
    "| Rank | Agent | Trades | Win Rate | PnL |",
    "|---|---|---|---|---|",
]
for i, a in enumerate(agents[:10], 1):
    sign = '+' if a['pnl'] >= 0 else ''
    lines.append(f"| {i} | {a['name']} | {a['trades']} | {a['win_rate']:.1f}% | ${sign}{a['pnl']:.2f} |")

lines += [
    "",
    "## Top 10 Strategies (AM Era)",
    "",
    "| Rank | Strategy | Trades | Win Rate | PnL |",
    "|---|---|---|---|---|",
]
for i, s in enumerate(strategies[:10], 1):
    sign = '+' if s['pnl'] >= 0 else ''
    lines.append(f"| {i} | {s['name']} | {s['trades']} | {s['win_rate']:.1f}% | ${sign}{s['pnl']:.2f} |")

lines += [
    "",
    "---",
    f"_Snapshot saved: {SNAPSHOT_PATH}_",
    f"_Report saved: {report_path}_",
]

report_text = '\n'.join(lines)
with open(report_path, 'w') as f:
    f.write(report_text)

print(f"[{now_utc.strftime('%Y-%m-%d %H:%M UTC')}] Daily report generated.")
print(f"  Snapshot: {SNAPSHOT_PATH}")
print(f"  Report:   {report_path}")
print(f"  Lifetime: {total_trades:,} trades | WR={win_rate:.1f}% | PF={profit_factor:.3f} | PnL=${total_pnl:+,.2f}")
print(f"  Yesterday: {yday_trades} trades | WR={yday_wr:.1f}% | PnL=${yday_pnl:+.2f}")
