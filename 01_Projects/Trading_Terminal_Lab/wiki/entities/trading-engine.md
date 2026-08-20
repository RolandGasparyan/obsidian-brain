---
title: Trading Engine
created: 2026-08-20
updated: 2026-08-20
type: entity
tags: [trading-engine, order-management, python, market-data]
sources: [Trading_Terminal_Lab_Codebase.md]
confidence: high
---

# Trading Engine

The core trading engine for [[trading-terminal-lab]]. Pure Python, zero external dependencies.

## Overview

The `TradingEngine` class (`src/trading_engine.py`) is the heart of the system. It simulates a live trading environment with:

- **8 symbols:** BTC/USDT, ETH/USDT, SOL/USDT, DOGE/USDT, AAPL, TSLA, NVDA, GOOGL
- **3 order types:** Market, Limit, Stop
- **Portfolio tracking:** Cash, positions, unrealized/realized P&L
- **Price simulation:** Geometric Brownian Motion (GBM), updated every 1 second

## Key Methods

| Method | Description |
|--------|-------------|
| `place_order(symbol, side, qty, ...)` | Submit market/limit/stop order |
| `cancel_order(order_id)` | Cancel pending order |
| `get_portfolio()` | Cash + positions + total value + P&L |
| `get_market_data(symbol?)` | Current prices for one or all symbols |
| `get_orders(status?)` | Order history (filterable) |
| `get_trades()` | All executed trades |

## Architecture

The engine uses a simple asyncio loop (`_price_loop`) that:
1. Updates each symbol's price via GBM: `new_price = old_price * (1 + drift * 0.1)`
2. Updates unrealized P&L for all open positions
3. Checks pending limit/stop orders against current prices
4. Fills orders whose conditions are met

## Related

- [[mcp-server]] — exposes this engine via MCP protocol
- [[order-management]] — order lifecycle details
- [[mock-market-data]] — GBM price simulation
- [[portfolio-tracking]] — position & P&L tracking
