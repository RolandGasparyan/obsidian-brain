# ADR-004 — Paper Battle Architecture

**Status:** ACCEPTED · 2026-05-13
**Layer:** Layer 2 (telemetry producer) + Layer 3 (cinematic visualization)
**Supersedes:** none
**Superseded by:** none

---

## Context

The TradingGuru AI Trading Championship needs to FEEL alive — multiple AI agents racing, rivalries forming, events firing, commentary streaming — even when:

1. Layer 1 trading core is disciplined (canary inactive, L99 halt engaged)
2. No real capital is at risk
3. No exchange orders are being sent

Without a way to express this aliveness, the championship architecture (3-layer vision codified 2026-05-12) reduces to a static dashboard showing inactive services.

The operator authored "SAFE EVOLUTION MODE" on 2026-05-13 specifying:
- Multiple agents emitting trades/confidence/XP/streaks/rivalries/commentary
- Increased event frequency
- Cinematic intensity
- NO real orders, NO exchange execution, NO capital movement
- "Fake telemetry for entertainment: ALLOWED if clearly sandbox/paper/demo. Fake PNL or fake LIVE MONEY claims: NEVER."

This ADR codifies the architectural decision that resulted.

---

## Decision

Build a separate paper-battle producer service that:

1. **Lives in the isolated agent home** — `/root/agent/paper_battle/` per the agent isolation discipline
2. **Reads** real market state from `/api/battle/terminal.json` (one-way, read-only)
3. **Simulates** 8 named agents with deterministic-but-rich state every 5 seconds
4. **Writes** to a SEPARATE endpoint `/api/battle/paper-arena.json` — never overwrites terminal.json
5. **Labels** every output with mandatory paper-mode markers:
   - `mode: "PAPER_SANDBOX_NO_REAL_CAPITAL"` (top-level)
   - `real_capital_usd: 0.00`
   - `exchange_orders_sent: 0`
   - `layer1_locked: true`
   - `layer1_canary_sha256: 704dd5725a909fe3f6…`
   - `layer1_l99_halted: true`
   - Per-agent `_paper_mode: true` + `_real_capital_at_risk_usd: 0.00`
6. **Never connects** to any exchange API, never reads any key file, never touches Layer 1 code paths
7. **Runs as systemd service** with hardened isolation (`ReadOnlyPaths` for canary + L99 state, `ReadWritePaths` limited to paper_battle/ + api/battle/)

The frontend consumes paper-arena.json via `usePaperArena()` hook (parallel to existing `useTerminalData()`). Phase 5-8 components merge real + paper agents in their views, tagging paper agents visually with 🎮 PAPER badges.

---

## Why this architecture (over alternatives)

### Alternative A: Augment existing `bots_updater.py` (REJECTED)

Modify `/root/ai-l99-production/bots_updater.py` to include 8 paper agents alongside real bots in `terminal.json`.

**Rejected because:**
- Mixes real + paper data in the same source-of-truth file — violates Layer 2 integrity rule ("numbers still derive from real terminal.json")
- Cross-cuts the L99 master system, which is a separate concern per Layer 1 isolation
- Future Claude session debugging telemetry can't tell which fields are real vs simulated without reading code

### Alternative B: Add to existing monster-agent paper bot (REJECTED)

Reuse the already-running `monster-agent.service` which was emitting paper data.

**Rejected because:**
- The `monster-agent` runs MONSTER ARMY code (recovery factor 6.0, snowball, dynamic scaling) — the exact code I refused to deploy live 9 times in this session
- Misleading service description ("L99 APEX BRAIN — Single Unified Trading Bot 24/7") masks its paper-only nature
- Operator chose "Stop ու permanently" via AskUserQuestion
- Building on it would have reinforced the misleading naming + made future cleanup harder

### Alternative C: Pure client-side simulation (REJECTED)

Generate paper agents in JavaScript in the browser.

**Rejected because:**
- Different browsers would see different races (no canonical state)
- Sync between multiple viewers impossible
- Deterministic seeding harder than server-side
- Doesn't survive page refresh

### Alternative D: Separate paper-battle producer + separate endpoint (ACCEPTED)

Build `paper_battle_engine.py` in `/root/agent/paper_battle/`, run as `paper-arena.service`, write to `/var/www/.../dist/api/battle/paper-arena.json`. Frontend consumes via `usePaperArena()` hook.

**Accepted because:**
- Single source of truth for paper data (paper-arena.json)
- Real telemetry (terminal.json) stays untouched — Layer 2 integrity preserved
- Lives in isolated agent home — discipline reinforced
- Reproducible: deterministic noise (SHA256-derived from seed + agent ID + cycle)
- Auditable: every file path documented, every dependency traced
- Self-healing: mkdir parent on every tick (survives `vite build` wipes)
- Reversible: stop service, delete folder, no system impact

---

## Consequences

### Positive

- Arena feels alive (10 agents racing on /championship instead of 2 real ones)
- Spectator visual interest sustained even when canary inactive
- Web Audio cues add sonic dimension to paper events (Phase 11)
- New `/racing` route showcases cinematic 8-lane visualization
- Demonstrates governance respect — operator's "Golden Rule" enforced ("fake telemetry OK if clearly labeled; fake PnL claims NEVER")
- Paper agents serve as backtesting-style preview of how multi-agent live system would feel (without any real risk)

### Negative

- Adds a service to maintain (paper-arena.service)
- Adds a JSON endpoint to monitor (paper-arena.json)
- Frontend complexity: components now merge two data sources
- Audio system requires user gesture to enable (browser autoplay policy)

### Mitigations applied

- Systemd unit hardened with `ConditionPathExists` guards (refuses to start if canary or L99 halt missing)
- Engine self-heals from filesystem changes
- Mandatory paper-mode markers on every output (audit-friendly)
- Frontend gracefully degrades if paper-arena.json unavailable
- Audio toggle defaults OFF (respects autoplay + user preference)

---

## Verification

Implemented + verified 2026-05-13:

- ✅ 8 agents emit rich telemetry every 5s
- ✅ Cycle counter persists across restarts
- ✅ SHA256 lock survives all integrations (verified 4/4 locations)
- ✅ Pre-commit hook refuses canary mutations (tested with intentional bad commit)
- ✅ Bidirectional sync round-trip working (server → GitHub → local + reverse)
- ✅ Mandatory paper markers present in every output (validated via curl + Python)
- ✅ No exchange sockets opened during 6+ hours of paper-engine runtime
- ✅ Capital state unchanged: $1,980.90 USDT

---

## References

- Operator verbatim: SAFE EVOLUTION MODE document (2026-05-13)
- `wiki/concepts/tradingguru-architecture-3-layer-vision.md`
- `wiki/concepts/tradingguru-immutable-layer-governance.md`
- `wiki/concepts/tradingguru-agent-isolation.md`
- `paper_battle/paper_battle_engine.py` — implementation
- `paper_battle/paper-arena.service` — systemd unit
- `/var/www/ai-trading-championship/src/lib/usePaperArena.js` — frontend consumer
- `/var/www/ai-trading-championship/src/lib/usePaperAudioCues.js` — Phase 11 audio
- `/var/www/ai-trading-championship/src/pages/RacingDashboard.jsx` — Phase 11 racing dashboard

---

## Open questions (deferred to future ADR)

- Should paper agents eventually consume historical OHLCV for more realistic simulation?
- Should the paper race results feed into a leaderboard persisted across sessions?
- If/when canary is armed, should real canary signals also stream into paper-arena.json for unified UI?

These are out of scope for v1.0. To be addressed in v1.1+ if relevant.
