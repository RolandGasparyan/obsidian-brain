---
title: Triangular Arbitrage Bot
created: 2026-08-20
updated: 2026-08-20
type: entity
tags: [arb-bot, binance, ccxt, triangular-arbitrage, websocket]
sources: [Triangular_Arbitrage_Bot.md]
confidence: high
---

# Triangular Arbitrage Bot

Crypto triangular arbitrage scanner integrated into [[trading-terminal-lab]].

## Overview

Python bot using `ccxt` library to scan Binance for triangular arbitrage. 733 USDT pairs → 265,356 triangles. WebSocket real-time price feed.

## Architecture

- **Scanner:** `src/triangular_scanner.py` — generates all possible triangles from USDT pairs, calculates profit after fees
- **Exchange:** `src/exchange_client.py` — ccxt wrapper (Binance/Bybit/OKX/Gate)
- **WebSocket:** `src/websocket_feed.py` — real-time Binance prices (verified ✅)
- **Executor:** `src/trade_executor.py` — executes trades with risk management
- **Config:** `config.yaml` — exchange, trade amount, min profit, fees

## 3 Modes

1. **Scanner** — read-only, shows opportunities (no trading)
2. **Paper** — simulated trading (testnet)
3. **Live** — real money trading

## Integration

Now part of [[trading-terminal-lab]] with a dedicated "Arb Scanner" tab in the web UI.

## Related

- [[trading-engine]] — mock trading engine (separate from arb bot)
- [[mcp-server]] — MCP server (exposes trading-engine tools)
- [[triangular-arbitrage]] — concept page
- [[mock-market-data]] — GBM simulation (for mock engine, not arb bot)
