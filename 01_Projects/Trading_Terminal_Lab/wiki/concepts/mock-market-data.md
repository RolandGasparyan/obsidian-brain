---
title: Mock Market Data
created: 2026-08-20
updated: 2026-08-20
type: concept
tags: [market-data, trading-engine, architecture]
sources: [Trading_Terminal_Lab_Codebase.md]
confidence: high
---

# Mock Market Data

Price simulation using Geometric Brownian Motion (GBM) in [[trading-engine]].

## Overview

The engine simulates live market data for 8 symbols. Each symbol has:
- `base_price` — starting price
- `volatility` — controls price swing magnitude

## GBM Formula

```python
drift = random.gauss(0, volatility)
new_price = old_price * (1 + drift * 0.1)
```

- Updated every 1 second via `_price_loop()`
- Floor at 10% of base price (prevents price going to zero)
- Bid/ask spread: `price * 0.0001` on each side

## Symbols

| Symbol | Base Price | Volatility |
|--------|-----------|------------|
| BTC/USDT | $95,000 | 2% |
| ETH/USDT | $3,200 | 2.5% |
| SOL/USDT | $180 | 3% |
| DOGE/USDT | $0.38 | 4% |
| AAPL | $230 | 1% |
| TSLA | $420 | 2% |
| NVDA | $140 | 1.5% |
| GOOGL | $175 | 1.2% |

## Related

- [[trading-engine]] — implements the simulation
- [[order-management]] — limit/stop orders trigger on these prices
- [[portfolio-tracking]] — P&L calculated from these prices
