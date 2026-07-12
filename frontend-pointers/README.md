# Frontend Pointers — Where Layer 3 Cinematic UI Lives

**Not copied here** — the frontend repo is large (218 dirs, vite build, node_modules).
This folder holds only POINTERS to where the frontend code actually lives.

---

## Layer 3 frontend locations

| Location                                              | Purpose                       |
|-------------------------------------------------------|-------------------------------|
| `~/Desktop/ai-trading-championship/`                  | Local clone (read/write)      |
| `/root/ai-trading-championship/` (server)             | Server clone (mirror)         |
| `/var/www/ai-trading-championship/` (server)          | **Production deployed build** |

## Active branch

```
feature/phase2-neural-evolution
```

## My recent commits (this session)

| Commit  | Description                                        |
|---------|----------------------------------------------------|
| 088e039 | Phase 5: ChampionshipOverlay (XP + Caster + Crown)  |
| f232c77 | Phase 6-7-8: Rivalry + DetailedStats + CyclePanel  |

## Components I built (Layer 3, free-form)

- `src/components/ChampionshipOverlay.jsx`
- `src/components/AgentRivalryPanel.jsx`
- `src/components/AgentDetailedStats.jsx`
- `src/components/ChampionshipCyclePanel.jsx`

## Key files

- `src/main.jsx` — global Shell with cinematic layers
- `src/pages/ChampionshipPage.jsx` — championship route
- `src/styles/arena-overrides.css` — design system tokens

## Open coordination items (informational, NOT tasks)

- PR #39 + PR #40 — `mergeable=false` (parallel session conflicts)
- `terminal.json` schema oscillation (two publishers racing)
- BRANCH_LOCK violation by parallel session (Phase 3A files modified)

These are upstream/parallel-session concerns. This isolated agent stays out of them.
