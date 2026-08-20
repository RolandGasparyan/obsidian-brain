---
title: Order Management
created: 2026-08-20
updated: 2026-08-20
type: concept
tags: [order-management, trading-engine, architecture]
sources: [Trading_Terminal_Lab_Codebase.md]
confidence: high
---

# Order Management

The order lifecycle in [[trading-engine]]: creation, filling, cancellation, and tracking.

## Order Types

| Type | Behavior |
|------|----------|
| **Market** | Filled immediately at current price |
| **Limit** | Pending until price crosses the limit price |
| **Stop** | Pending until price crosses the stop price |

## Order Lifecycle

1. **Created** — `place_order()` called with parameters
2. **Pending** — limit/stop orders wait for price trigger
3. **Filled** — price condition met, order executes
4. **Cancelled** — user cancels pending order before fill

## Fill Logic

- **Limit Buy:** filled when `tick.price <= order.price`
- **Limit Sell:** filled when `tick.price >= order.price`
- **Stop Sell:** filled when `tick.price <= order.stop_price`
- **Stop Buy:** filled when `tick.price >= order.stop_price`

## Position Impact

On fill:
- **Buy:** cash decreases, position increases (or new position created)
- **Sell:** cash increases, position decreases (or short position created)
- Average entry price is weighted-combined for existing positions

## Related

- [[trading-engine]] — implements this logic
- [[portfolio-tracking]] — tracks resulting positions
- [[mock-market-data]] — price ticks that trigger fills
