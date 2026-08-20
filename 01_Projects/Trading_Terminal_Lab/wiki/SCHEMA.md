# Wiki Schema — Trading Terminal Lab

## Domain
Trading terminal development — MCP protocol integration, trading engine architecture, order management, portfolio tracking, mock market data simulation, and AI agent connectivity.

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `trading-engine.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- **Provenance markers:** On pages that synthesize 3+ sources, append `^[raw/articles/source-file.md]`
  at the end of paragraphs whose claims come from a specific source.

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
---
```

## Tag Taxonomy
- Architecture: architecture, mcp, api, websocket, rest
- Trading: trading-engine, order-management, portfolio, market-data, pnl
- Tech: python, aiohttp, mcp-protocol, stdio, testing
- Agents: hermes, ai-agent, automation, cron, telegram
- Meta: comparison, timeline, concept, entity

## Page Thresholds
- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions, minor details
- **Split a page** when it exceeds ~200 lines
