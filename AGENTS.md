# Roland Gasparyan's Cloud Computer — AGENTS.md

## Environment
- **OS:** Ubuntu 24.04 LTS | **IP:** 34.139.162.200
- **Python:** 3.12.3 | **Pip:** ~/.local/bin/pip3 (--break-system-packages)
- **Packages:** ccxt 4.5.54, aiohttp 3.13.5, colorama 0.4.6, flask

## Active Services

### 1. Trading Strategies Testing Engine v9.1 (5 critical fixes applied 2026-06-01)
- **Service:** `trading-engine` (systemd, Restart=always, 5s)
- **Script:** `/home/ubuntu/trading_engine/engine.py` (v9.1 — 30 strategies, 31 agents, 5 risk modes, 29 tokens)
- **v9.1 critical fixes:**
  1. `SHORT_ONLY=True` global — LONG opens disabled engine-wide (project rule)
  2. Bottom 5 losing agents (ETA, NU, OMICRON, CHI, GIMEL) reset to top performer strategies
  3. TRADING GURU self-learn now skips losing agents and never adopts LONG-only strategies; boots on `CHANDE_MOMENTUM/AGGRESSIVE`
  4. SL/TP rebalanced via `TP_SL_RATIO=2.5` floor (was effectively ~1x for SAFE/BALANCED)
  5. Gate.io public fallback for SHIB/PEPE/FLOKI/BONK/BOME when OKX returns 0/null
- Backup of pre-fix engine: `/home/ubuntu/trading_engine/engine.py.bak.<timestamp>`
- **Database:** `/home/ubuntu/trading_engine/trades.db` (SQLite — all trades persisted)
- **Log:** `/home/ubuntu/trading_engine/engine.log`
- **Knowledge Base:** `/home/ubuntu/trading_engine/knowledge_base.json`
- **State File:** `/home/ubuntu/trading_engine/engine_state_v8.json` (v8 engine writes here)
- **Market Data:** OKX (primary) — Binance geo-blocked on this IP
- **Agents:** 31 (ALPHA through VAV + TRADING GURU)
- **Strategies (30 total):**
  - Original 8: EMA_CROSSOVER, VWAP_MACD, KELTNER_RSI, BB_SQUEEZE, SUPERTREND_MACD, ORDER_FLOW, PIVOT_BREAKDOWN, ALMA_STOCH
  - New 12: RANGE_TRADING, PRICE_ACTION, PULLBACK_MOMENTUM, BREAKOUT_VOLUME, RSI_DIVERGENCE, ICHIMOKU_CLOUD, FIBONACCI_RETRACEMENT, HEIKIN_ASHI_TREND, WILLIAMS_R_REVERSAL, ADX_TREND_STRENGTH, PARABOLIC_SAR, TRIPLE_EMA
  - Deep Research 10: DONCHIAN_BREAKOUT, LAGUERRE_RSI, SQUEEZE_MOMENTUM, FAIR_VALUE_GAP, ORDER_BLOCK_LIQ, CVD_ABSORPTION, TRIPLE_SCREEN, CHANDE_MOMENTUM, WADDAH_ATTAR, HFT_STAT_ARB
- **Risk Modes (5):** SAFE(0.125K) | BALANCED(0.25K) | AGGRESSIVE(0.375K) | ULTRA_AGGRESSIVE(0.5K) | CHAOS(1.0K)
- **Trading Modes (9):** SCALP_SHORT, SCALP_LONG, SWING_SHORT, SWING_LONG, BREAKOUT_SHORT, BREAKOUT_LONG, MOMENTUM_SHORT, MOMENTUM_LONG, MEAN_REVERSION, GRID
- **Tokens (29):** BTC, ETH, XRP, SOL, AVAX, BNB, ADA, DOT, LINK, MATIC, UNI, ATOM, LTC, FIL, NEAR, APT, ARB, OP, INJ, TIA, SEI, SUI, PEPE, SHIB, FLOKI, BONK, WIF, DOGE, TRX
- **Position Sizing:** Gods Level (RISK=2%, Kelly multiplier per risk mode, dynamic ATR stop)
- **Cold Wallet:** $100 threshold → auto-secured
- **Self-Learning:** TRADING GURU learns every 10 ticks from all agents, auto-adopts best strategy+mode

### New 10 Deep Research Agents (v8.0)
| Agent | Strategy | Risk Mode |
|-------|----------|-----------|
| AGENT PHI | Donchian Channel Breakout | AGGRESSIVE |
| AGENT CHI | Laguerre RSI Pullback | BALANCED |
| AGENT PSI | Squeeze Momentum (LazyBear) | ULTRA_AGGRESSIVE |
| AGENT OMEGA | ICT Fair Value Gap (FVG) | BALANCED |
| AGENT ALEPH | ICT Order Block + Liq Sweep | AGGRESSIVE |
| AGENT BETH | CVD Absorption Reversal | SAFE |
| AGENT GIMEL | Elder Triple Screen System | BALANCED |
| AGENT DALETH | Chande Momentum Oscillator | AGGRESSIVE |
| AGENT HE | Waddah Attar Explosion | ULTRA_AGGRESSIVE |
| AGENT VAV | HFT Statistical Arbitrage | CHAOS |

### 2. Trading Engine Status API v3 — Interactive Animated Dashboard (v8.0)
- **Service:** `trading-status` (systemd, Restart=always)
- **Script:** `/home/ubuntu/trading_engine/status_api.py` (v3 — reads engine_state_v8.json)
- **Dashboard HTML:** `/home/ubuntu/trading_engine/dashboard.html` (TradingView-style, animated, 16 setup cards)
- **Port:** 8080 (UFW ALLOW) | **Dashboard:** http://34.139.162.200:8080
- **JSON API:** http://34.139.162.200:8080/api (CORS-enabled, rich data)
- **Health:** http://34.139.162.200:8080/health
- **Dashboard features:**
  - Particle background animation
  - Candlestick chart (lightweight-charts 4.1.3)
  - Equity curves for top 5 agents (Chart.js 4.4.0)
  - Live trade feed (auto-updates every 5s)
  - Agent leaderboard with win rate bars
  - Top winning setups from SQLite DB (click for full modal)
  - 16 setup cards with full modal details (entry/exit rules, indicators, equity curve)
  - Trading Guru self-learning panel
  - Ticker tape with live prices
  - Auto-refresh every 5 seconds

## Firewall (UFW)
| Port | Rule |
|------|------|
| 22   | LIMIT (SSH) |
| 8080 | ALLOW (Dashboard) |

## Management
```bash
# Check services
sudo systemctl status trading-engine trading-status

# Restart engine
sudo systemctl restart trading-engine

# View live log
tail -f /home/ubuntu/trading_engine/engine.log

# Query trade stats
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/ubuntu/trading_engine/trades.db')
c = conn.cursor()
c.execute('SELECT COUNT(*), ROUND(SUM(pnl_usd),2) FROM trades WHERE outcome IS NOT NULL')
print('Closed trades / Total PnL:', c.fetchone())
c.execute('SELECT agent_name, COUNT(*), ROUND(SUM(pnl_usd),2) FROM trades WHERE outcome IS NOT NULL GROUP BY agent_name ORDER BY 3 DESC')
[print(r) for r in c.fetchall()]
conn.close()
"
```

## Notes
- Binance is geo-blocked (HTTP 451) on this IP — use OKX or Kraken only
- Engine v8 uses individual fetch_ticker() calls per asset for OKX compatibility
- All 31 agents auto-adapt risk mode every 25 ticks based on win rate
- New 10 deep research agents (PHI through VAV) require MIN_HISTORY=10-20 ticks before first trade
- `engine_state.json` is written by engine_hybrid.py (old process) — do not confuse with `engine_state_v8.json`
- Database schema has 5 tables: trades, sessions, learning_events, agent_snapshots, sqlite_sequence
- GitHub: https://github.com/RolandGasparyan/ai-trading-championship (commit af28c7e)

---

## 🔴 CANARY REAL MONEY BATTLE (DO VPS: 167.71.24.86)

### Services (5 total)
| Service | Status | Description |
|---------|--------|-------------|
| canary-battle | ✅ active | Real money spot trading |
| paper-arena | ✅ active | 8 paper agents simulation |
| canary-api | ✅ active | API endpoint |
| battle-status-sync | ✅ active | Status sync |
| microstructure-collector | ✅ active | Market data |

### Strategy: CMO_CHANDE (Micro Scalp 3X)
- **Mode:** SPOT (Gate.io spot market)
- **Trade Size:** $5 USDT per trade
- **Take Profit:** 0.2% | **Stop Loss:** 0.15%
- **Cooldown:** 60 seconds | **Max Concurrent:** 3 positions
- **Signal:** CMO (Chande Momentum Oscillator) > 0

### Proven CMO Tokens (ALL_PAIRS)
| Pair | Profit Factor | Notes |
|------|--------------|-------|
| FLOKI/USDT | 4.43 | **BEST PF** |
| WIF/USDT | 3.12 | |
| OP/USDT | 2.37 | Best avg/trade |
| SHIB/USDT | 2.02 | |
| DOT/USDT | 1.58 | Highest total PnL |
| ADA/USDT | 1.59 | |
| UNI/USDT | 1.59 | |
| ATOM/USDT | 1.31 | |
| BNB/USDT | 1.09 | |

**AVOID:** XRP, ETH, BTC, INJ (negative PnL in CMO backtest)

### Real Money Agents
| Agent | Account | Balance | Key File |
|-------|---------|---------|----------|
| TITAN | MAIN | ~$1,520 USDT | `/root/canary/.api_key_main` |
| VELOCITY | SUB1 | ~$200 USDT | `/root/canary/.api_key_sub1` |
| SENTINEL | SUB2 | ~$192 USDT | `/root/canary/.api_key_sub2` |

**Key Format:** `KEY:SECRET` (one line per file, chmod 600)

### Management (DO VPS)
```bash
# Check all canary services
systemctl is-active canary-battle paper-arena canary-api battle-status-sync microstructure-collector

# Live battle log
tail -f /root/canary/runtime/battle.log

# Check balances
python3 -c "
import ccxt, pathlib
ROOT = pathlib.Path('/root/canary')
for f,l in [('.api_key_main','TITAN'),('.api_key_sub1','VELOCITY'),('.api_key_sub2','SENTINEL')]:
    k,s = (ROOT/f).read_text().strip().split(':')
    ex = ccxt.gate({'apiKey':k,'secret':s,'enableRateLimit':True,'options':{'defaultType':'spot'}})
    bal = ex.fetch_balance()
    print(f'{l}: \${float(bal.get(\"USDT\",{}).get(\"free\",0)):.2f} USDT')
"

# Restart / Stop
systemctl restart canary-battle
systemctl stop canary-battle
```

- **Last Updated:** 2026-05-31
- **GitHub:** https://github.com/RolandGasparyan/tradingguru-empire

## Daily AM Monitoring System (2026-06-01)
- **Script:** `/home/ubuntu/trading_engine/am_daily_monitor.py`
- **Cron:** `5 0 * * *` (00:05 UTC daily) — queries trades.db, writes JSON snapshot + Markdown report
- **Snapshot (latest):** `/home/ubuntu/trading_engine/am_latest_snapshot.json`
- **Reports dir:** `/home/ubuntu/trading_engine/daily_reports/am_report_YYYY-MM-DD.md`
- **Cron log:** `/home/ubuntu/trading_engine/daily_reports/cron.log`
- **Manus schedule:** Daily at 06:30 Asia/Yerevan — reads snapshot, delivers AI analysis to user in Manus
- **Alert thresholds:** WR < 45%, PF < 1.0, daily loss > $500, max position > $10,000
- **Manual run:** `python3 /home/ubuntu/trading_engine/am_daily_monitor.py`

## Engine v9.2 — Anti-Martingale Default Sizing (2026-06-01)
- **Change**: Replaced loss-triggered "Smart Doubling" with WIN-triggered Anti-Martingale as DEFAULT position sizing for all 31 agents
- **Logic**: WIN → streak +1 (max 3 = 8x), LOSS → reset streak to 0
- **Multiplier**: 2^streak (0→1x, 1→2x, 2→4x, 3→8x)
- **Base bet**: 2% of capital (RISK_PER_TRADE), hard cap 8% per trade
- **Dashboard**: Field names kept as `doubling_*` for backward compatibility
- **Verified**: Anti-Martingale messages firing in production at tick 28+ (session v9_1780327062)
- **GitHub**: Pushed to tradingguru-empire main branch (commit e97a69f)

## God-Level Unified Engine v10.0 (2026-06-01)
- **Service:** `god-engine` (systemd, Restart=always, 10s)
- **Script:** `/home/ubuntu/trading_engine/god_engine.py`
- **Log:** `/home/ubuntu/trading_engine/god_engine.log`
- **State:** `/home/ubuntu/trading_engine/god_engine_state.json`
- **Session:** `god_v10_1780328634` (started 2026-06-01 15:43 UTC)
- **Capital:** $10,000 paper (fresh start)
- **Strategies (10):** CHANDE_MOMENTUM, ICT_FVG, SQUEEZE_MOMENTUM, WILLIAMS_R, ORDER_FLOW, KELTNER_RSI, CVD_ABSORPTION, PARABOLIC_SAR, FIBONACCI, BB_SQUEEZE
- **Assets (13):** FLOKI, BOME, DOT, ATOM, SHIB, WIF, ADA, UNI, LTC, DOGE, OP, SOL, BONK
- **Sizing:** Anti-Martingale (1x→2x→4x→8x on win streaks, reset on loss)
- **Risk mode:** ULTRA_AGGRESSIVE default (best PF=1.060 from data)
- **Auto-stop:** Daily DD cap $150 → pause until next UTC day
- **Auto-resume:** New UTC day → engine resumes automatically
- **Loss guard:** 3 consecutive losses → SAFE mode for 10 ticks
- **Win boost:** 3 consecutive wins → upgrade risk tier
- **Max concurrent:** 3 open positions
- **Max hold:** 20 ticks per trade
- **Management:**
  - `sudo systemctl status god-engine`
  - `sudo systemctl restart god-engine`
  - `sudo systemctl stop god-engine`
  - `tail -f /home/ubuntu/trading_engine/god_engine.log`

- **Vault notes:** 151
- **Vault zip:** 504K
- **Repo:** tradingguru-empire (4a19e78)

- **Vault notes:** 151
- **Vault zip:** 504K
- **Repo:** tradingguru-empire (4a19e78)

- **Vault notes:** 152
- **Vault zip:** 504K
- **Repo:** tradingguru-empire (c7ae6cc)

## Last Master Sync
- **Timestamp:** 2026-06-01 20:03:18 UTC
- **Vault notes:** 152
- **Vault zip:** 504K
- **Repo:** tradingguru-empire (c7ae6cc)

## Champion Battle v9.1 DUST-PROOF — 2026-06-06 07:45 UTC ✅
- **Version:** v9.1 — DUST-PROOF + Triple Cycle + God-Level Prediction + Smart Rotation + Kelly + Doubling
- **Script:** `/home/ubuntu/canary/champion_battle.py`
- **Key Fixes Applied:**
  1. **dd_cap fixed:** VELOCITY/SENTINEL $0.50 → dynamic 5% of real balance
  2. **Virtual balance sync:** Periodic real Gate.io API sync every 5 min
  3. **DUST elimination:** Removed WIF/FLOKI/SHIB/DOGE/BOME — replaced with 16 high-liquidity pairs
  4. **FILL guard:** Post-fill dust check — abort if filled_coin < min_qty
  5. **Gate.io min order:** $3.00 floor in trade_size
  6. **Smart Kelly:** 33-level Kelly Criterion (0.25x fraction, 0.25x-3.0x range)
  7. **Smart Doubling:** 33-level recovery mode (1.0x-4.0x, resets on win)
  8. **God-Level Prediction Engine:** 11 operators, 19-point confluence, ELITE(9+)/GODMODE(11+) gates
  9. **Triple Cycle Engine:** SCALP(7+)/SWING(9+)/BREAKOUT(10+) — 3 concurrent layers, MAX_OPEN=9
  10. **Smart Rotation:** Per-pair PnL tracker, auto-rotate every 6 ticks, blacklist after 4 losses
- **Pair Universe (16 DUST-PROOF):** ADA, XRP, SOL, AVAX, NEAR, APT, TRX, LINK, UNI, DOT, MATIC, LTC, BNB, ATOM, INJ, SUI
- **Trade Stats (backup log 977 trades):** DUST losses eliminated ($1,620 was being lost per session)
- **Live Balances:** TITAN $950+, VELOCITY $51+, SENTINEL $11+, TRADING_GURU $950+
