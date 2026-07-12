# /docs — Documentation for the Trading Agent

## Layout

```
docs/
├── README.md                          ← this file
├── MA_STRATEGY.md                     ← the only validated edge (canonical spec)
├── 9-refusals-log.md                  ← session firewall record (9 drift refusals)
├── decisions/                         ← 11 decision notes (from wiki/decisions)
├── obsidian-mirror/                   ← LIFE VAULT mirrors for this agent
│   ├── 2026-05-13 — Phase 5-8...md    ← today's Dev Log
│   ├── Daily-2026-05-13.md            ← today's Daily note
│   └── MA50W10-Strategy.md            ← Knowledge note on the strategy
└── wiki-mirror/                       ← RESEARCH WIKI mirrors for this agent
    ├── tradingguru-architecture-3-layer-vision.md
    ├── tradingguru-immutable-layer-governance.md
    ├── tradingguru-agent-isolation.md
    ├── 2026-05-13-agent-isolation-and-sync-repo.md
    └── 2026-05-13-isolation-migration-complete.md
```

## Origin paths (where the master copies live)

| Mirror | Master location | Vault |
|---|---|---|
| `obsidian-mirror/*` | `~/REINCARNATION-Brain/Dev Logs/`, `Daily/`, `Knowledge/` | Life OS (Obsidian) |
| `wiki-mirror/*` | `~/Desktop/ai-trading-championship/wiki/{concepts,decisions,findings}/` | Research wiki (Obsidian) |
| `decisions/*` | `~/Desktop/ai-trading-championship/wiki/decisions/` | Research wiki (Obsidian) |
| `MA_STRATEGY.md` | `~/Desktop/ai-trading-championship/MA_STRATEGY.md` | Repo root (frontend repo) |

These are **copies, not single-sources**. Master copies live in the Obsidian vaults. This repo's mirrors are point-in-time snapshots for self-contained access — i.e., a fresh Claude session cloning only this repo gets everything it needs without needing the vaults.

## How to refresh mirrors

```bash
# From local Mac:
cp "~/REINCARNATION-Brain/Dev Logs/2026-05-13 — ...md" docs/obsidian-mirror/
cp "~/REINCARNATION-Brain/Daily/2026-05-13.md" docs/obsidian-mirror/Daily-2026-05-13.md
cp "~/REINCARNATION-Brain/Knowledge/MA50W10-Strategy.md" docs/obsidian-mirror/

cp ~/Desktop/ai-trading-championship/wiki/concepts/tradingguru-*.md docs/wiki-mirror/
cp ~/Desktop/ai-trading-championship/wiki/decisions/2026-05-13-*.md docs/wiki-mirror/
cp ~/Desktop/ai-trading-championship/wiki/findings/2026-05-13-*.md docs/wiki-mirror/

./sync.sh push "docs: refresh obsidian + wiki mirrors"
```

## What's authoritative

When in doubt:

1. **Strategy spec** — `MA_STRATEGY.md` is authoritative (in this repo + frontend repo + obsidian Knowledge note; all should match)
2. **Refusal log** — `9-refusals-log.md` is authoritative (this repo)
3. **Layer governance** — `wiki-mirror/tradingguru-immutable-layer-governance.md` is authoritative (master in wiki)
4. **Agent isolation** — `wiki-mirror/tradingguru-agent-isolation.md` is authoritative (master in wiki)
5. **Today's session log** — `obsidian-mirror/2026-05-13 — Phase 5-8...md` is authoritative (master in life vault)

If two mirrors disagree, the Obsidian vault wins. Refresh from there.
