# REPLAY_TIMELINE_ENGINE v1.0

**Operator-authored intent:** 2026-05-14 (REPLAY TIMELINE ENGINE build brief)
**Status:** IMPLEMENTED · paper-safe · read-only
**Classification:** AI Trading Esports Replay Arena — Layer 3 cinematic infrastructure

---

## Why this spec exists

Operator brief: "Transform arena history into a cinematic replayable AI esports experience." This adds a **time-travel** layer on top of the live arena — users can rewind, replay, watch boss events, see regime flips, track rivalries.

Critically: this is **a separate read-only layer**. It does not modify the trading engine, the arena features service, or any Layer 1 / Layer 2 logic. It reads their JSON outputs and stores a compressed time-series.

---

## File Tree

```
replay_engine/
├── __init__.py
├── replay_collector.py        # main async service · captures snapshots every 10s
├── replay_timeline.py         # timeline navigation · sparse markers · heatmap
├── replay_storage.py          # gzipped JSONL · rolling 7-day retention
├── replay_serializer.py       # snapshot ↔ bytes · gzip I/O
├── replay_api.py              # periodic compactor → 5 public JSON files
├── replay_events.py           # 9 event types + 5 boss-moment auto-tags
├── replay_utils.py            # shared helpers
├── tradingguru-replay.service # systemd unit
└── snapshots/                 # .jsonl.gz daily files + 5 public JSONs

frontend/
├── ArenaReplayPanel.jsx       # main container · 4 modes
├── ReplayTimeline.jsx         # draggable scrubber · boss-moment pulses
├── ReplayControls.jsx         # rewind buttons · live toggle · mode picker
├── ReplayEventFeed.jsx        # rolling event sidebar · type-coded
└── ReplayMiniMap.jsx          # event-density heatmap bars
```

---

## Data Flow

```
paper-arena.service  →  paper-arena.json        (5s · 8-agent state)
tradingguru-arena    →  arena-features.json     (10s · weather/boss/crowd)
tradingguru-telemetry→  terminal.json           (60s · BTC market)
                              ↓
            ╭─────────────────────────────╮
            │  replay_collector.py        │
            │  • polls 3 sources @ 10s     │
            │  • builds snapshot dict     │
            │  • appends gzip JSONL       │
            │  • detects 9 event types    │
            │  • triggers compactor @ 30s │
            ╰─────────────────────────────╯
                              ↓
            snapshots/replay-YYYY-MM-DD.jsonl.gz  (rolling 7-day)
                              ↓
            ╭─────────────────────────────╮
            │  replay_api.compact_outputs │
            │  • streak detection         │
            │  • boss-moment tagging      │
            │  • sparse scrubber markers  │
            │  • heatmap density buckets  │
            ╰─────────────────────────────╯
                              ↓
        /var/www/.../api/battle/replay-*.json (5 files)
                              ↓
        nginx serves https://tradingguru.ai/api/battle/replay-*.json
                              ↓
        Frontend polls every 10s → renders esports HUD
```

---

## Snapshot Schema (per cycle, gzipped JSONL)

```json
{
  "t":                1747244400.123,
  "iso":              "2026-05-14T11:00:00Z",
  "leaderboard":      [{name, role, level, xp, title}, ...],
  "xp_delta":         {"Ares Valkor": +60, "Doran Pyle": -25},
  "regime":           "Trend",
  "regime_entropy":   0.6,
  "macro_score":      36.77,
  "macro_mode":       "DEFENSIVE",
  "weather":          "CLOUDY",
  "weather_intensity":0.5,
  "crowd":            "SILENT",
  "boss_event":       null | {type, severity, description, ...},
  "rivalries":        [...],
  "champion":         "Phoenyx Aldon",
  "btc_price":        79600.0,
  "tick":             1234,
  "tg_safe":          true
}
```

---

## Event Taxonomy (9 types · all paper-safe detection)

| # | Type | Detection logic | Severity |
|---|------|-----------------|----------|
| 1 | `AGENT_LEADER_CHANGE` | leaderboard[0].name differs vs prev | 0.7 |
| 2 | `XP_JUMP` | per-agent XP delta ≥ +50 | min(1, Δ/200) |
| 3 | `XP_COLLAPSE` | per-agent XP delta ≤ -25 | min(1, \|Δ\|/100) |
| 4 | `REGIME_TRANSITION` | Bayesian dominant regime changes | 0.6 |
| 5 | `VOLATILITY_STORM` | weather → STORMY or BLIZZARD (rising) | weather.intensity |
| 6 | `CROWD_REACTION` | crowd hits ROAR/GASP/BOO (new state) | level-mapped |
| 7 | `BOSS_EVENT` | arena_features boss_event field non-null (new) | boss.severity |
| 8 | `STREAK` | same agent holds lead ≥ 3 consecutive cycles | min(1, len/30) |
| 9 | `CHAMPION_SWAP` | champion (top XP holder) changes | 0.85 |

---

## Boss-Moment Auto-Tagging (5 highlight types)

Computed across full history each compaction cycle. Surfaced in `replay-bosses.json`.

| Type | Detection |
|------|-----------|
| `BIGGEST_XP_JUMP` | Single largest `XP_JUMP` event |
| `BIGGEST_COLLAPSE` | Single largest `XP_COLLAPSE` event |
| `LONGEST_STREAK` | Longest `STREAK` event |
| `VOLATILITY_EXPLOSION` | Highest avg-intensity sustained period (min 5 cycles · intensity ≥ 0.7) |
| `ARENA_DOMINATION` | Longest single-champion run (min 30 cycles) |

---

## Replay Modes (frontend)

| Mode | Description |
|------|-------------|
| **cinematic** | Bold motion · large transitions · single-column layout · gradient backdrop |
| **tactical** | Dense data · 2-column layout · event feed + boss moments side-by-side |
| **minimal** | Clean · scrubber + crowd only · zero distraction |
| **auto-highlight** | Auto-cycles cursor through boss moments every 15s |

Mode pick affects: layout, padding, background, animation density. Trading logic: never affected.

---

## Public API Endpoints (nginx-served · all JSON)

| URL | Updated | Purpose |
|-----|---------|---------|
| `/api/battle/replay-index.json` | 30s | Status · storage health · event-type counts |
| `/api/battle/replay-timeline.json` | 30s | Sparse scrubber markers (120 markers / 24h window) |
| `/api/battle/replay-events-recent.json` | 30s | Last 200 events (rolling, newest first) |
| `/api/battle/replay-bosses.json` | 30s | 5 auto-tagged boss moments |
| `/api/battle/replay-heatmap.json` | 30s | 60-bucket event-density heatmap for minimap |

---

## Storage & Retention

- **Per-day file:** `snapshots/replay-YYYY-MM-DD.jsonl.gz` (gzipped JSONL, append-only)
- **Single-file cap:** 10 MB · rolls to `.part2`, `.part3` if exceeded within UTC day
- **Retention:** newest 7 days · oldest deleted automatically
- **Total cap:** 100 MB (env-tunable via `REPLAY_MAX_TOTAL_MB`)
- **Compression:** gzip · typical ratio ~10× vs raw JSON (1 KB snap → ~100 bytes compressed)

Expected size for 7 days at 10s interval = 60,480 snapshots × ~0.5 KB avg compressed ≈ **30 MB**.

---

## Hard Safety Properties

This engine **CANNOT**:
- Modify agent decisions
- Affect risk caps (Article 3 / macro_layer / monte_carlo all unchanged)
- Touch `.api_key`, `canary.service`, `/root/canary/`, L99 halt, or `canary_arm.json`
- Open exchange write sockets
- Place real orders
- Modify any `paper_battle/*.py` or `canary/*.py` files

It **CAN** (and is designed to):
- Read public JSON outputs from other services
- Write to `replay_engine/snapshots/` (own dir)
- Write to `REPLAY_PUBLISH_DIR` (nginx-served path, if env set)
- Be killed via SIGTERM with clean exit

systemd unit has hard `Environment=` for all 3 paper-safe flags, and `ConditionPathExists` for `canary_strategy.py` + `protection_halt.json` (refuses to start if Layer 1 mutated).

Resource caps: `MemoryMax=200M`, `CPUQuota=20%`.

---

## Smoke Test Results (60s · Mac local)

```
✓ 6 ticks executed cleanly
✓ 5 snapshots written → replay-2026-05-14.jsonl.gz (1.3 KB)
✓ All 5 public JSON files generated
✓ replay-index.json: tg_safe=true · storage health populated
✓ Memory: <50 MB
✓ No exchange sockets opened
✓ No live execution attempted
```

Note: agents=0 on Mac local because paper-arena.service runs only on VPS. On VPS, the leaderboard + events will populate naturally as paper engine ticks.

---

## Cross-references

- `replay_engine/replay_collector.py` — main service
- `replay_engine/tradingguru-replay.service` — systemd unit
- `frontend/ArenaReplayPanel.jsx` — UI container
- `paper_battle/paper_battle_engine.py` — source of leaderboard (untouched)
- `paper_battle/arena_features.py` — source of weather/boss/crowd (untouched)
- `governance/SHADOW_ARENA_FEATURES_v1.md` — features layer this builds on
- `governance/SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER_v1.md` — sovereign discipline this respects
