---
title: Trading Terminal Lab — Wiki
type: project-doc
tags: [project, trading-terminal-lab, wiki, karpathy, knowledge-graph]
status: active
updated: 2026-08-20
---

# 📚 Trading Terminal Lab — Karpathy LLM Wiki

> Knowledge base built on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Lives inside the Obsidian vault.

## Location

`~/Documents/Guru/01_Projects/Trading_Terminal_Lab/wiki/`

## Structure

```
wiki/
├── SCHEMA.md              # Conventions, tag taxonomy, thresholds
├── index.md               # Content catalog (8 pages)
├── log.md                 # Chronological action log
├── entities/              # Entity pages (4)
│   ├── trading-engine.md
│   ├── mcp-server.md
│   ├── hermes-agent.md
│   └── trading-monitor-bot.md
├── concepts/              # Concept pages (4)
│   ├── mcp-protocol.md
│   ├── order-management.md
│   ├── mock-market-data.md
│   └── portfolio-tracking.md
├── comparisons/           # (empty)
├── queries/               # (empty)
└── raw/                   # Source material (empty)
    ├── articles/
    ├── papers/
    ├── transcripts/
    └── assets/
```

## Pages: 8

### Entities (4)
- [[trading-engine]] — Core engine: 8 symbols, GBM, order routing
- [[mcp-server]] — MCP stdio server, 6 tools
- [[hermes-agent]] — Hermes Agent desktop, AI assistant
- [[trading-monitor-bot]] — Telegram bot for hourly alerts

### Concepts (4)
- [[mcp-protocol]] — Model Context Protocol overview
- [[order-management]] — Order lifecycle (market/limit/stop)
- [[mock-market-data]] — GBM price simulation
- [[portfolio-tracking]] — Position & P&L tracking

## Graphify

Code knowledge graph at `~/Projects/trading-terminal-mcp/graphify-out/`:
- **83 nodes**, 10 communities
- `graph.json`, `graph.html`, `GRAPH_REPORT.md`

## Related

- [[Trading_Terminal_Lab_MOC]] — project overview
- [[Trading_Terminal_Lab_Codebase]] — code structure
