---
title: Trading Terminal Lab — Codebase
type: project-doc
tags: [project, trading-terminal-lab, codebase, architecture]
status: active
updated: 2026-08-20
---

# 🧱 Trading Terminal Lab — Codebase

> Code structure and architecture for `~/Projects/trading-terminal-mcp/`

## File Tree

```
trading-terminal-mcp/
├── README.md                    # Project overview
├── requirements.txt             # aiohttp, mcp, pydantic
├── src/
│   ├── main.py                  # HTTP + WebSocket server (aiohttp)
│   ├── trading_engine.py        # Core engine (pure Python, zero deps)
│   └── mcp_server.py            # MCP server (6 tools, stdio transport)
├── static/
│   ├── index.html               # Web UI (dark terminal theme)
│   ├── style.css                # Dark theme styles
│   └── app.js                   # Frontend logic (WebSocket, charts)
├── tests/
│   ├── test_engine.py           # 8 unit tests ✅
│   └── test_mcp_e2e.py          # MCP end-to-end tests
└── .venv/                       # Python venv
```

## Architecture

### Trading Engine (`trading_engine.py`)

Pure Python, zero external dependencies. Key classes:

- **`TradingEngine`** — main orchestrator
  - `place_order(symbol, side, qty, order_type, price?, stop_price?)` → `Order`
  - `cancel_order(order_id)` → `bool`
  - `get_portfolio()` → dict with cash, positions, P&L
  - `get_market_data(symbol?)` → dict
  - `get_orders(status?)` → list
  - `get_trades()` → list
  - `_price_loop()` — GBM price simulation, runs every 1s
  - `_check_pending_orders()` — fills limit/stop orders when price crosses

- **`Order`** — dataclass with id, symbol, side, type, qty, status
- **`Position`** — tracks qty, avg_entry, unrealized/realized P&L
- **`Tick`** — real-time price snapshot (price, bid, ask, volume, change)

**Symbols:** BTC/USDT, ETH/USDT, SOL/USDT, DOGE/USDT, AAPL, TSLA, NVDA, GOOGL

**Order Types:** Market, Limit, Stop
**Order Status:** Pending, Filled, Partial, Cancelled, Rejected

### Web Server (`main.py`)

aiohttp-based, zero external deps beyond aiohttp. Features:
- REST API: 5 endpoints (market, portfolio, orders, trades, place/cancel)
- WebSocket: live price + portfolio broadcast every 1s
- Static file serving for web UI
- Port 8080 (configurable via `PORT` env var)

### MCP Server (`mcp_server.py`)

Model Context Protocol server using stdio transport. 6 tools exposed:
1. `get_market_data` — current prices
2. `place_order` — submit order
3. `cancel_order` — cancel pending
4. `get_portfolio` — positions & P&L
5. `get_orders` — order history
6. `get_trades` — executed trades

## Tech Stack

- **Python:** 3.11+ (uses `from __future__ import annotations`)
- **aiohttp:** HTTP server + WebSocket
- **MCP:** Model Context Protocol (stdio)
- **pytest:** test runner
- **No frontend framework** — vanilla HTML/CSS/JS

## Related

- [[Trading_Terminal_Lab_MOC]] — project overview
- [[Trading_Guru_Empire_MOC]] — parent trading ecosystem
