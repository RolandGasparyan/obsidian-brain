# Wiki Log — Trading Terminal Lab

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete

## [2026-08-20] create | Wiki initialized
- Domain: Trading terminal development (MCP, trading engine, AI agents)
- Structure created with SCHEMA.md, index.md, log.md
- Initial pages: 8 (4 entities + 4 concepts)

## [2026-08-20] update | Added triangular arbitrage pages
- Added entity: [[triangular-arb-bot]] (Binance, 733 pairs, 265K triangles)
- Added concept: [[triangular-arbitrage]] (math, challenges, integration)
- Updated index.md (10 total pages)
- Source: session @session:default/20260820_122120_b5f8d7
- Arb bot moved into ~/Projects/trading-terminal-mcp/arb-bot/
- Web UI updated: unified buttons/sizes/positions + Arb Scanner tab

## [2026-08-20] create | Trading Academy
- Added entity: [[trading-academy]]
- Added eight AI faculty roles and ten prerequisite-based curriculum modules
- Added deterministic assessments, SQLite persistence, MCP/REST tools, and append-only audit
- Added a Hermes no-agent Cron cycle every two hours for three paper-only trainees
- Verified live execution requests are rejected and audited
- Updated index.md (11 total pages)

## [2026-08-20] update | Activated persistent Trading Academy agents
- Created Hermes profiles: `academyquant`, `academystrategy`, `academyrisk`
- Added role-specific SOULs, Nous Portal model pins, and launchd-supervised gateways
- Connected least-privilege MCP allowlists without order placement/cancellation tools
- Added six-hour continuity learning routines and verified one run per profile
- Added a grounded deterministic math replay fixture; all three trainees scored 100 and advanced to `microstructure`
- Full project suite verified: 136 tests passed
