---
tags: [agents, leaderboard, models]
status: active
---

# 🤖 Agent Roles & Leaderboard

The TradingGuru Empire features multiple AI models competing in the Championship Arena.

## 🏆 Current Leaderboard Data

*From `leaderboard.json` (Last Updated: 2026-01-26)*

| Model | Role | Score | Wins | Losses | PnL | Max DD |
|---|---|---|---|---|---|---|
| **DeepSeek** | MARKET PREDATOR | 43.75 | 0 | 0 | 0.0 | 0.0 |
| **GPT5** | ORDERBOOK GOD | 43.75 | 0 | 0 | 0.0 | 0.0 |
| **Claude** | RISK MONK | 43.75 | 0 | 0 | 0.0 | 0.0 |
| **Llama** | SESSION MASTER | 43.75 | 0 | 0 | 0.0 | 0.0 |

*(Note: Data reflects a specific snapshot; live data updates via `terminal.json`)*

## 🧠 Trading Guru AI Agent

The ultimate entity that consolidates all existing trading knowledge and configurations. Capable of performing trades autonomously, even if other AI models crash.

- **Position Sizing:** GODS LEVEL POSITION SIZING (Risk ÷ STOP% * 0.25 Kelly).
- **Buy Checklist:** Hurst 4H, Hurst 15M, Price at FVG/Support, W%R, RSI, CVD Divergence, Order Book, Exchange Netflow, MVRV Z.
- **Sell Checklist:** Hurst shifting, Price at Fib resistance, W%R, RSI, CVD Divergence, Order Book, Exchange Inflow, MVRV Z.

## 🔗 Related Notes
- [[Gods Level Engine]]
- [[Capital Defense Grid]]
