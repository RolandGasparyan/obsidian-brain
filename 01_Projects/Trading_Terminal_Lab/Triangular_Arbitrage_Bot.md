---
title: Triangular Arbitrage Bot
type: project-doc
tags: [project, trading-terminal-lab, arb-bot, binance, ccxt, triangular-arbitrage]
status: active
updated: 2026-08-20
---

# 🔄 Triangular Arbitrage Bot

> Crypto triangular arbitrage scanner bot. Built in session @session:default/20260820_122120_b5f8d7. Lives at `~/Projects/trading-terminal-mcp/arb-bot/`.

## Overview

A Python bot that scans **Binance** (and Bybit/OKX) for triangular arbitrage opportunities using real-time WebSocket price feeds.

### Key Stats
- **733 USDT pairs** on Binance
- **265,356 triangles** generated
- **WebSocket** real-time price feed (20 symbols)
- **3 modes:** scanner (read-only), paper (simulation), live (real money)
- **ccxt** library for exchange connectivity

## Architecture

| File | Description |
|------|-------------|
| `main.py` | Entry point — 3 modes (live, paper, scanner) |
| `config.yaml` | All config (exchange, amount, risk, fees) |
| `src/config_loader.py` | Config reader (dataclass-based) |
| `src/exchange_client.py` | ccxt exchange client (Binance/Bybit/OKX/Gate) |
| `src/triangular_scanner.py` | Triangle generator + profit calculator |
| `src/trade_executor.py` | Trade executor + risk management |
| `src/websocket_feed.py` | WebSocket price feed (Binance verified ✅) |
| `src/logger.py` | Logger + CSV trade history |
| `test_math.py` | Math verification test ✅ |

## How It Works

### Triangle Cycle: `USDT → BTC → ETH → USDT`

1. **Step 1:** USDT → BTC via `BTC/USDT` pair
2. **Step 2:** BTC → ETH via `ETH/BTC` pair
3. **Step 3:** ETH → USDT via `ETH/USDT` pair

If final USDT > initial USDT + fees → **arbitrage opportunity exists**.

### Arbitrage Condition

```
(1 / P_btc_usdt) × (1 / P_eth_btc) × P_eth_usdt > 1 + fees
```

### Tested Results

- ✅ Binance API connection (733 USDT pairs)
- ✅ 265,356 triangles generated
- ✅ WebSocket price feed working (12 tickers received)
- ✅ Math verification (2.72% profit correctly calculated)
- ⚠️ Real opportunities: 0 found via public API (normal — HFT bots beat us)

## Integration with Trading Terminal Lab

The arb bot is now part of the [[Trading_Terminal_Lab_MOC]] project:

- **UI:** "🔄 Arb Scanner" tab in the web terminal
- **Config:** Exchange, base currency, trade amount, min profit, max pairs
- **Log:** Real-time scanner log in the UI
- **Opportunities:** Live opportunity list with cycle + profit %

## Session

Built in session @session:default/20260820_122120_b5f8d7 (192 messages, Arbitrage research → Bot construction → Testing)

## Related

- [[Trading_Terminal_Lab_MOC]] — parent project
- [[Trading_Terminal_Lab_Codebase]] — codebase overview
- [[Trading_Guru_Empire_MOC]] — trading ecosystem
