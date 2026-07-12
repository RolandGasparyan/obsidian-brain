# Branch Lock — Coordination Protocol

When multiple Claude sessions touch the same repo, they MUST coordinate through this file.

## Active lock

- **Holder:** trading-session (Layer 3 championship UI)
- **Branch:** feature/phase2-neural-evolution
- **Scope:** /var/www/ai-trading-championship/src/components/*, /src/pages/ChampionshipPage.jsx, /src/main.jsx
- **NOT in scope:** /root/ai-l99-production/ (L99 production, separate concern)
- **NOT in scope:** /root/.l99/ (system-wide halt state)

## Past violations (audit trail)

- Parallel session modified Phase 3A files (StadiumLightingEngine -62 lines) despite this lock.
  Resolution: documented but not reverted, since Layer 3 free-form.

## Rule

If you are a Claude session and you read this file, you MUST:
1. Check if your work overlaps the active scope above
2. If yes — pause and write your intent here BEFORE touching files
3. If no — proceed but log your scope in the audit trail at the bottom

## Audit trail

| Date       | Session           | Scope                                     |
|------------|-------------------|-------------------------------------------|
| 2026-05-11 | Phase 1 wiring    | dashboard real-data, /api/battle endpoint |
| 2026-05-12 | Phase 2-4 design  | arena-overrides.css, design tokens        |
| 2026-05-13 | Phase 5-8 cinematic | Championship overlay + rivalry + stats   |
| 2026-05-13 | Isolation         | /root/agent/ creation (this commit)       |
