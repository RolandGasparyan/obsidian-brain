# Changelog — tradingguru-agent

All notable changes to the trading agent + championship UI tracked here.
Format inspired by Keep a Changelog. Versions follow semver — major.minor.patch.

---

## [1.0.0] — 2026-05-13

### 🏁 The first complete, shippable version of the TradingGuru AI Trading Championship ecosystem.

**Capital state at v1.0:** $1,980.90 USDT untouched · L99 halt engaged 29h+ · Canary SHA256 `704dd5725a909fe3f6…` locked across 4 locations · 0 live exchange sockets.

### Added — Layer 3 cinematic UI

- **Phase 1** Real-data wiring across 5 surfaces (Landing/Dashboard/Championship/Arena/War Room)
- **Phase 2** AgentBrainStreamV2 + MarketWeatherLayer + CrowdReactionLayer
- **Phase 3** StadiumLightingEngine + pixel TradingView chart
- **Phase 4** Design system unification (17 canonical tokens · 217-hex migration)
- **Phase 5** `ChampionshipOverlay` — XP Leaderboard + 3-personality Caster + ChampionCrown ceremony
- **Phase 6** `AgentRivalryPanel` — TITLE FIGHT + FACTION CIVIL WAR + faction-war ranking
- **Phase 7** `AgentDetailedStats` — 11 fields per agent · expandable cards · deterministic derivation
- **Phase 8** `ChampionshipCyclePanel` — Hourly/Daily/Weekly cycles + 6 titles (Sharpe King · Momentum Predator · Survival Champion · Volatility Emperor · Recovery Master · Arena Legend)
- **Phase 9** SAFE EVOLUTION — 8-agent paper battle engine (`paper-arena.service`) producing rich telemetry every 5s · `PaperArenaShowcase` + `usePaperArena` hook · all output marked `PAPER_SANDBOX_NO_REAL_CAPITAL`
- **Phase 10** UI Unification — real + paper agents merged across all Phase 5-8 components (10 agents in views instead of 2)
- **Phase 11** `usePaperAudioCues` hook — Web Audio synthesized SFX on paper events (BIG_SIM_SWING / WIN_STREAK / LOSS_STREAK / champion change) · `RacingDashboard` at `/racing` route — 8-lane cinematic racing track with continuous animation loop
- **Phase 12** `SpectatorMode` — global toggle hides dev panels for clean view · hotkey `S` · mobile responsive fixes in `arena-overrides.css`
- **Phase 13** LandingPage prominent "🏁 WATCH THE PAPER RACE" pulsing CTA → `/racing`

### Added — Trading agent isolation

- `/root/agent/` (server) + `~/Desktop/agent/` (local) as the unified, isolated home for everything trading-agent
- Private GitHub repo `RolandGasparyan/tradingguru-agent` as single source of truth
- Bidirectional `sync.sh` helper with 5-section verify command (auto-detects local vs server execution)
- `bootstrap.sh` — session startup helper with health check + doc reading order
- Pre-commit hook (`.githooks/pre-commit`) with SHA256 lock guard + secret-pattern scan
- Documentation: `MA_STRATEGY.md`, `9-refusals-log.md`, 11 decisions, governance docs
- 4 wiki concepts (3-layer architecture, immutable layer governance, agent isolation, predictions-market-architecture) propagated to research wiki + mirrored in agent repo

### Added — Generative art

- `algorithmic-art/harmonic-pursuit.md` — algorithmic philosophy (6 paragraphs)
- `algorithmic-art/harmonic-pursuit.html` — self-contained interactive p5.js + Web Audio piece
  - 8 racers tuned to just-intonation harmonic series (1, 9/8, 5/4, 4/3, 3/2, 5/3, 15/8, 2)
  - Layered Perlin noise field driving direction
  - Web Audio synthesis: velocity → gain, x → pan, y → filter cutoff
  - Convolver reverb with procedural impulse response
  - Reproducible by seed, parametrically tunable, Anthropic-branded UI

### Added — Operational infrastructure

- `paper-arena.service` systemd unit (hardened: ProtectSystem=full, ReadOnly canary/L99 paths, ReadWrite paper_battle + api/battle only)
- `paper_battle_engine.py` self-healing on `vite build` parent-dir wipes (mkdir per tick)
- Server cleanup archive (`/root/_archive_2026-05-13/`) — 7.4 GB legacy code archived for 7-day verify window
- Local cleanup archive (`~/Desktop/_archive_2026-05-13/`) — 1.4 GB legacy Desktop folders archived
- Obsidian propagation: Dev Log, Daily note, Projects/AI-Trading-Championship update, 3 new wiki pages

### Changed

- Frontend bundle: `index-Bed1UVIZ.js` (391 kB / 104 kB gzip) — grew from 363 kB pre-Phase 10 due to paper-arena integration + Spectator + Racing dashboard
- CSS: `arena-overrides.css` expanded with spectator-mode rules + mobile-responsive overrides (188 lines)

### Refused (Layer 1 discipline held)

10 distinct drift attempts refused with cited rationale. See `docs/9-refusals-log.md`. Highlights:

1. GODMODE_USDT_ROTATION_KING blueprint
2. Multi-pair USDT rotation (4 pairs)
3. Self-evolving live trading
4. Parameter mutations on locked MA50W10
5. Stage2 transition without canary completion
6. OVERRIDE_GOVERNANCE_DOC requests
7. "start agents tradings battle" (deflected to SAFE EVOLUTION paper mode instead — operator-authored alternative respected)

### Sacred locks (immutable at v1.0)

| Item | Value |
|------|-------|
| Canary SHA256 | `704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143` |
| Locations matching | 4 (local repo · server repo · server live · snapshot) |
| L99 protection halt | `halted: true`, engaged 2026-05-12 06:51 UTC |
| Capital | $1,980.90 USDT untouched |
| Live exchange sockets | 0 |
| canary.service | inactive · static |
| monster-agent.service | inactive · disabled · masked-equivalent |

### Routes live at v1.0

| Route | Purpose |
|-------|---------|
| `/` | Landing page with 🏁 WATCH THE PAPER RACE CTA |
| `/championship` | Phase 5-10 overlays · 10-agent merged views |
| `/racing` | Phase 11 RacingDashboard · 8-lane cinematic + audio |
| `/arena` | RacingArena (original gladiator visualization) |
| `/dashboard` | TradingTerminal · real telemetry |
| `/predictions` | Own-arena prediction markets |
| `/war-room` | App fallback |
| `/control` | ControlCenter |
| `/api/battle/terminal.json` | Real telemetry (60s cadence) |
| `/api/battle/paper-arena.json` | Paper battle (5s cadence) |
| `/api/battle/bots.json` | Bot status |

### Services active at v1.0

| Service | State |
|---------|-------|
| `tradingguru-telemetry.service` | active · enabled |
| `tradingguru-bots-updater.service` | active · enabled |
| `microstructure-collector.service` | active |
| `paper-arena.service` | active · 8-agent paper engine |
| `nginx.service` | active |
| `canary.service` | **inactive · static** (sacred lock) |
| `canary-killswitch.service` | **inactive · static** |
| `monster-agent.service` | **inactive · disabled** (paper bot, stopped permanently) |

---

## How to use this version

```bash
# Sync the latest state
~/Desktop/agent/sync.sh pull

# Verify everything is healthy
~/Desktop/agent/sync.sh verify

# Bootstrap a new Claude session
~/Desktop/agent/bootstrap.sh

# View the live race
open https://tradingguru.ai/racing

# View the generative art piece
open ~/Desktop/agent/algorithmic-art/harmonic-pursuit.html
```

---

## Branches for the future (NOT in v1.0)

- v1.1 Phase 14: Documentation + onboarding video + public-facing README
- v2.0 Layer 1 canary arm cycle 1 (requires all 5 LAYER_DISCIPLINE gates + operator verbatim)
- v2.0 Multi-pair MA50W10 instances (if operator decides to expand)
- v2.0 Public launch + announcement strategy

All future versions require operator decision docs in `docs/decisions/` before code lands.
