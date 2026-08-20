---
title: Triangular Arbitrage
created: 2026-08-20
updated: 2026-08-20
type: concept
tags: [triangular-arbitrage, trading, concept]
sources: [Triangular_Arbitrage_Bot.md]
confidence: high
---

# Triangular Arbitrage

A trading strategy that exploits price inconsistencies between three currency pairs on the same exchange.

## How It Works

Given three pairs forming a cycle (e.g., `USDT → BTC → ETH → USDT`):

1. Convert USDT to BTC at `BTC/USDT` price
2. Convert BTC to ETH at `ETH/BTC` price
3. Convert ETH back to USDT at `ETH/USDT` price

If the final amount > initial amount + fees, there's an arbitrage opportunity.

## Mathematical Condition

```
(1 / P_btc_usdt) × (1 / P_eth_btc) × P_eth_usdt > 1 + total_fees
```

## Real-World Challenges

- **Fees:** 3 trades × 0.1-0.2% = 0.3-0.6% total cost
- **Slippage:** Large orders move the price
- **Speed:** Opportunities last milliseconds
- **Competition:** HFT bots with co-located servers
- **API rate limits:** Exchange throttles API calls

## In Trading Terminal Lab

[[triangular-arb-bot]] implements this strategy with:
- 733 USDT pairs on Binance → 265,356 triangles
- WebSocket real-time price feed
- 3 modes: scanner, paper, live

## Related

- [[triangular-arb-bot]] — implementation
- [[mock-market-data]] — GBM simulation (for the mock engine)
- [[order-management]] — order lifecycle
- [[portfolio-tracking]] — position tracking
