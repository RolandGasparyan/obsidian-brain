---
title: Oracle Arena — MOC
type: moc
tags: [ai, oracle-arena, trading-agents, multi-agent, llm]
created: 2026-10-10
updated: 2026-10-10
---

# 🔮 Oracle Arena — MOC

> Multi-agent LLM trading-arena. Persona agents predict UP / DOWN / SKIP for symbols over fixed horizons, scored against real historical prices they cannot see. Research briefs from TradingAgents via tuning-loop. Results mirrored into this Brain by `sync-brain.mjs`.
>
> Existing sync: Oracle Arena → Obsidian Brain (auto-push on 5-minute cadence via LaunchAgent)
>
> Standard: **ABSOLUTE** — AI competition at its highest form

---

## Architecture

| Layer | Component | Stack | Purpose |
|---|---|---|---|
| Server | Express API + run engine | JavaScript | Core arena: agents predict, score, rank |
| Data | Yahoo Finance layer | JavaScript | Real historical prices (agents can't see) |
| Store | JSON file store | JavaScript | agents.json, runs.json, caches, snapshots |
| Research | TradingAgents pipeline | Python (tuning-loop) | Bull/bear cases, verdict, risk per symbol |
| MCP Bridge | MCP server | JavaScript | Connects to Hermes/Claude/etc |
| Frontend | Static public/ | HTML/JS | Optional UI |
| Brain Sync | sync-brain.mjs | JavaScript | Mirrors results into this Obsidian vault |

## Repo Structure

```
oracle-arena/
├── server/
│   ├── lib/engine.js          # Run engine (agent vs symbol, horizon scoring)
│   ├── lib/market.js          # Yahoo Finance data fetch, caching
│   ├── lib/store.js           # JSON persistence
│   ├── research.js            # TradingAgents bridge
│   └── mcp/server.js          # MCP integration
├── public/                    # Static UI (optional)
├── data/
│   ├── agents.json            # Persona agent configs
│   ├── runs.json              # Historical runs
│   ├── research/              # TradingAgents briefs per symbol
│   └── snapshots/             # Point-in-time state
└── tests/                     # unit tests
```

## Key Features

- **Multi-agent**: N persona agents run in parallel per symbol
- **Fixed horizon scoring**: Agents predict UP/DOWN/SKIP; scored against real prices they never saw
- **Research briefs**: TradingAgents generates bull/bear/verdict/risk per symbol before each run
- **Cached research**: First (symbol, date) is slow (LLM pipeline); subsequent runs are instant
- **Brain sync**: `sync-brain.mjs` exports results to this Obsidian vault every 5 minutes

## Connection to Trading Guru

Oracle Arena is the *single-agent research lab*. Trading Guru is the *multi-agent championship*. Both feed into the same Brain. Oracle Arena tests individual agent quality; Trading Guru tests multi-agent competition at scale.

## Integration Status

- [x] Repo cloned to scratch
- [x] Brain sync active (sync-brain.mjs runs via LaunchAgent)
- [ ] Full spec document (same grade as Trading Guru blueprint)
- [ ] Unified auth with 6-empires gateway
- [ ] Live championship bridge (Trading Guru agents → Oracle Arena)

## Next Actions

- [ ] Create ABSOLUTE blueprint for Oracle Arena (same depth as Trading Guru)
- [ ] Integrate with 6-empires shared backend
- [ ] Add spiritual/personality layer to agent personas (each agent embodies a pillar)
- [ ] Build public-facing UI at oracle.6-empires.com

---

_Part of [[ABSOLUTE_BRAIN]] — synced by Hermes Agent._
