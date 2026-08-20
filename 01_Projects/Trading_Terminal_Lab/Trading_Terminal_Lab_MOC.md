---
title: Trading Terminal Lab — MOC
type: project-moc
tags: [project, trading-terminal-lab, moc, mcp, trading, hermes]
status: active
updated: 2026-08-20
---

# 🧪 Trading Terminal Lab — Map of Content

> Lightweight trading terminal with MCP (Model Context Protocol) connector. Built on Hermes Agent desktop, synced to Obsidian Brain. Live code at `~/Projects/trading-terminal-mcp/` ([[Trading_Terminal_Lab_Codebase]]).

## 🔗 Links

- **Hermes Project:** `Trading Terminal Lab` (p_de393953)
- **Local path:** `~/Projects/trading-terminal-mcp/`
- **Web UI:** http://localhost:8080
- **GitHub:** (not yet pushed)
- **Trading Monitor Cron:** `24a35c6064f8` — hourly VPS health → Telegram ([[Trading_Monitor_Agent]])

## 🏗️ Architecture

| Module | File | Description |
|--------|------|-------------|
| **Trading Engine** | `src/trading_engine.py` | Pure Python — 8 symbols (BTC, ETH, SOL, DOGE, AAPL, TSLA, NVDA, GOOGL), GBM price simulation, market/limit/stop orders, portfolio tracking, P&L |
| **Web Server** | `src/main.py` | aiohttp HTTP + WebSocket server, REST API, live price broadcasting every 1s |
| **MCP Server** | `src/mcp_server.py` | MCP stdio server — 6 tools: `get_market_data`, `place_order`, `cancel_order`, `get_portfolio`, `get_orders`, `get_trades` |
| **Web UI** | `static/index.html` + `style.css` + `app.js` | Dark terminal theme, real-time WebSocket prices, portfolio, orders table |
| **Tests** | `tests/test_engine.py` + `tests/test_mcp_e2e.py` | 8+ unit tests, all passing ✅ |

## 📡 API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/market` | Market data (all or by symbol) |
| GET | `/api/portfolio` | Portfolio with positions & P&L |
| GET | `/api/orders` | Order history (filter by status) |
| GET | `/api/trades` | Executed trades |
| POST | `/api/order` | Place new order |
| DELETE | `/api/order/{id}` | Cancel pending order |
| WS | `/ws` | Live market data + portfolio stream |

## 🔌 MCP Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `get_market_data` | `symbol?` | Price, bid, ask, volume, change_24h |
| `place_order` | `symbol, side, qty, order_type?, price?, stop_price?` | Order confirmation |
| `cancel_order` | `order_id` | Success/failure |
| `get_portfolio` | — | Cash, positions, total value, P&L |
| `get_orders` | `status?` | Order list |
| `get_trades` | — | Executed trade list |

## 🧠 Knowledge Graph

- [[Trading_Terminal_Lab_Codebase]] — code structure & architecture
- [[Trading_Terminal_Lab_Wiki]] — Karpathy LLM Wiki (concepts, entities)
- [[Trading_Monitor_Agent]] — Hermes Super Agent (hourly VPS health → Telegram)
- [[Trading_Guru_Empire_MOC]] — parent trading ecosystem
- [[6_EMPIRES_OS_Project_State]] — 3D corporation (VPS down)

## 🔄 Arb Scanner (Triangular Arbitrage)

- [[Triangular_Arbitrage_Bot]] — Binance, 733 USDT զույգ, 265K եռյակ, WebSocket-ով
- 3 ռեժիմ՝ scanner (միայն տեսնել), paper (սիմուլացիա), live (իրական)
- Session: @session:default/20260820_122120_b5f8d7
- Տեղը: `~/Projects/trading-terminal-mcp/arb-bot/`

## 📋 Roadmap

- [x] Build core trading engine (mock market, orders, portfolio)
- [x] Build MCP server (6 tools)
- [x] Build web UI (dark theme, WebSocket)
- [x] Write tests (8+ passing)
- [x] Create Hermes Project
- [x] Create Obsidian Brain notes
- [x] Set up Graphify knowledge graph
- [x] Set up Karpathy LLM Wiki
- [x] Build Triangular Arbitrage Bot
- [x] Unify all UI buttons, sizes, positions
- [x] Add Arb Scanner tab in web UI
- [ ] Push to GitHub (trading-terminal-mcp repo)
- [ ] Connect arb bot to real Binance API keys
- [ ] Add more trading strategies

## 🔁 Sync

- **Obsidian Brain:** `~/Documents/Guru/01_Projects/Trading_Terminal_Lab/`
- **Brain Sync:** Vault → Git → GitHub + VPS (every 5 min via launchd)
- **Graphify:** `~/Projects/trading-terminal-mcp/graphify-out/`
- **Wiki:** `~/Documents/Guru/01_Projects/Trading_Terminal_Lab/wiki/`
