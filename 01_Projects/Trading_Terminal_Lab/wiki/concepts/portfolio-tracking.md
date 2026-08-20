---
title: Portfolio Tracking
created: 2026-08-20
updated: 2026-08-20
type: concept
tags: [portfolio, pnl, trading-engine, architecture]
sources: [Trading_Terminal_Lab_Codebase.md]
confidence: high
---

# Portfolio Tracking

Position and P&L tracking in [[trading-engine]].

## Overview

The engine tracks:
- **Cash balance** — starts at $100,000, adjusted on each trade
- **Positions** — one per symbol, with qty, avg entry price, current price
- **Unrealized P&L** — `(current_price - avg_entry) * qty` for open positions
- **Realized P&L** — locked in when a position is closed

## Position Data

Each `Position` tracks:
- `qty` — quantity (negative for shorts)
- `avg_entry_price` — weighted average entry price
- `current_price` — updated every tick from [[mock-market-data]]
- `unrealized_pnl` — mark-to-market P&L
- `realized_pnl` — locked-in P&L from closed trades
- `market_value` — `qty * current_price`

## Portfolio Snapshot

`get_portfolio()` returns:
```json
{
  "cash": 95000.0,
  "total_value": 105000.0,
  "starting_balance": 100000.0,
  "total_pnl": 5000.0,
  "positions": { "BTC/USDT": { ... } }
}
```

## Related

- [[trading-engine]] — implements tracking
- [[order-management]] — trades update positions
- [[mock-market-data]] — prices used for P&L
