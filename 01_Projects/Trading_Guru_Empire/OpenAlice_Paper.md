---
title: OpenAlice (paper mode)
type: system
tags: [trading-guru-empire, openalice, paper, research]
updated: 2026-06-08
---

# 🤖 OpenAlice — paper / research only

[TraderAlice/OpenAlice](https://github.com/TraderAlice/OpenAlice) — autonomous AI trading agent (TypeScript, AGPL-3.0). Installed at `~/tradingguru-empire/openalice`.

> [!danger] Paper mode only
> Installed with **MockBroker** (simulated fills) + guards. **No live broker, no API keys, no live execution.** Going live is a manual step the operator takes — not automated, not wired by Claude. See `OPENALICE_PAPER_SAFETY.md` in the repo.

## What it is
- Unified Trading Account (UTA) wrapping brokers; AI never touches brokers directly
- **Trading-as-Git**: stage → commit → push to execute (push = simulated under MockBroker)
- **Guards**: max position size, cooldown, symbol whitelist (ESLint-for-trading)
- Agent powered by Claude Code CLI workspaces

## Run (paper)
```bash
cd ~/tradingguru-empire/openalice
pnpm install && pnpm build && pnpm start   # → localhost:3002
# UI → new UTA → MockBroker → set guards
```

## Empire fit (research)
Use for simulation/analysis alongside [[Council_Runner_Automation]] and shadow battles. Keep `LIVE_ORDERS=0` discipline — analysis, not live trades.

Related: [[Trading_Guru_Empire_MOC]]
