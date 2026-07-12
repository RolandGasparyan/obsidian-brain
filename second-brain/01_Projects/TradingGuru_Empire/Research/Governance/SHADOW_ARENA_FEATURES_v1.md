# SHADOW_ARENA_FEATURES v1.0

**Operator-authored intent:** 2026-05-14 (TRADINGGURU SHADOW ARENA BOOT bash script)
**Status:** IMPLEMENTED · **PAPER-SAFE ONLY** · entertainment-layer only
**Classification:** Visualization enrichment for Shadow Arena UI

---

## Why this spec exists

The operator's `arena_shadow_runner` bash script requested 3 new entertainment features:
- `TG_ENABLE_MARKET_WEATHER`
- `TG_ENABLE_BOSS_EVENTS`
- `TG_ENABLE_CROWD_REACTIONS`

These are NOT trading-logic features. They are **visualization/state enrichment** computed from existing market data + agent state, written to `runtime/arena_features.json` for frontend consumption.

This doc defines them so future Claude/operator can understand the design (they're not in any of Specs #1-23).

---

## Implementation Files

```
paper_battle/arena_features.py   ← pure functions (weather + boss + crowd)
arena_shadow_runner.py           ← CLI wrapper that drives them
```

Hard safety: refuses to start unless `TG_DISABLE_REAL_ORDERS=1` + `TG_PAPER_EXECUTION=1` + `LIVE_ORDERS=0`.

---

## Feature 1 · Market Weather Engine

**Function:** `compute_market_weather(btc_window, vol_pct, bayes_dominant, bayes_entropy, macro_score)`

**5 states:**

| State | Trigger | Visual bias |
|-------|---------|-------------|
| SUNNY | vol < 0.15% · macro ≥ 40 · regime Trend or Expansion | bright · low-vol breakout potential |
| CLOUDY | default (medium vol) | calm · regime watching |
| STORMY | vol ≥ 1.0% | high vol · arena tension |
| BLIZZARD | Bayes Panic + entropy > 0.5 + macro < 30 | panic · agents defensive · capital priority |
| DAWN | Bayes Recovery + macro ≥ 30 | recovery emerging · cautious optimism |

**Output fields:** `state`, `intensity` (0-1), `trend_direction` (rising/falling/sideways), `vol_pct`, `regime`, `macro_score`, `bias_visual`.

**Updates:** every tick (default 10s).

**Trading impact:** **NONE.** Read-only side effect.

---

## Feature 2 · Boss Events Detector

**Function:** `detect_boss_event(btc_history, spread_history, bayes_panic_pct, bayes_entropy, last_boss_event, now_ts)`

**5 boss types:**

| Boss Type | Trigger condition |
|-----------|-------------------|
| `FLASH_CRASH` | BTC drops > 1.0% in 5 min (30 ticks) |
| `WHALE_PUMP` | BTC surges > 1.0% in 5 min |
| `VOLATILITY_BOSS` | Realized vol > 1.8% sustained |
| `REGIME_QUAKE` | Bayesian Panic posterior > 80% with entropy < 0.2 (locked panic) |
| `LIQUIDITY_DROUGHT` | Spread expanded > 3× recent baseline |

**Cooldown:** 600s between boss events (prevents spamming).

**Duration estimates:** FLASH_CRASH 8 min · WHALE_PUMP 8 min · VOLATILITY_BOSS 20 min · REGIME_QUAKE 15 min · LIQUIDITY_DROUGHT 12 min.

**Trading impact:** **NONE.** Pure detection. Agent decisions remain governed by macro_layer/bayesian_regime/monte_carlo (not boss events). Future Claude must NOT wire boss events into trading decisions — that would violate Spec #22 "controlled signal emergence, NOT dopamine."

---

## Feature 3 · Crowd Reaction Synthesizer

**Function:** `compute_crowd_reaction(recent_trades, leader_changed, title_defended_or_lost, boss_event_active, avg_realized_r)`

**6 reaction levels:**

| Level | Intensity | Trigger |
|-------|-----------|---------|
| `SILENT` | 0.0 | quiet · no recent activity |
| `MURMUR` | 0.3 | flat trade outcomes |
| `APPLAUSE` | 0.6 | positive R-multiples (0.5+) or leader change |
| `ROAR` | 0.85 | strong wins (avg R ≥ 1.5) or title event |
| `BOO` | 0.7 | strong losses (avg R ≤ -0.8) |
| `GASP` | 1.0 | boss event active (ALWAYS WINS — highest priority) |

**Sentiment tags:** `neutral · excited · disappointed · competitive · tense · dramatic`.

**Trading impact:** **NONE.** Crowd reactions are output-only.

---

## Output Schema

`runtime/arena_features.json` (written every ~10 seconds):

```json
{
  "market_weather": {
    "state": "STORMY",
    "intensity": 0.72,
    "trend_direction": "falling",
    "vol_pct": 1.15,
    "regime": "Expansion",
    "macro_score": 28.4,
    "bias_visual": "high vol · arena tension"
  },
  "boss_event": {
    "type": "FLASH_CRASH",
    "severity": 0.85,
    "triggered_at_ts": 1747244400,
    "triggered_at_utc": "2026-05-14T11:00:00+00:00",
    "duration_estimate_min": 8,
    "description": "BTC -1.42% in 5 min",
    "cooldown_active_until_ts": 1747245000
  },
  "boss_event_active": { ... },  // either current boss OR in-cooldown previous boss
  "crowd_reaction": {
    "level": "GASP",
    "sentiment": "tense",
    "intensity": 1.0,
    "triggered_by": ["boss_event_active"]
  },
  "computed_at_utc": "...",
  "tick": 12,
  "btc_price": 79305.42,
  "btc_spread_pct": 0.013,
  "agent_count_paper_arena": 8,
  "current_leader": "Phoenyx Aldon",
  "leader_changed_this_tick": false,
  "runner_version": "arena-shadow-1.0",
  "tg_safe": true,
  "tg_disable_real_orders": true,
  "tg_paper_execution": true
}
```

---

## Architecture Position

```
                                                  ┌──────────────────────┐
              Gate.io public REST                 │  Frontend (Layer 3)  │
                      ↓                           │  /championship/      │
              ┌──────────────┐                    │  /arena/             │
              │ paper-arena. │                    │  reads:              │
              │ service      │  ──→ paper-arena ──┤    paper-arena.json  │
              │ (engine v1.2)│    .json (5s)      │    arena_features.   │
              └──────────────┘                    │    json (10s)        │
                      ↓                           │                      │
              ┌──────────────┐                    │  Renders:            │
              │ arena_shadow │                    │  • leaderboard       │
              │ _runner.py   │  ──→ arena_features│  • weather backdrop  │
              │ (parallel)   │    .json (10s)     │  • boss event banner │
              └──────────────┘                    │  • crowd animations  │
                                                  └──────────────────────┘

Separation:
  • paper-arena.service = trading-logic source of truth
  • arena_shadow_runner = visualization enrichment
  • Two independent JSON outputs · frontend consumes both · no race conditions
```

---

## Hard Safety Properties

These features **CANNOT**:
- Modify agent trading decisions
- Affect risk caps (Article 3 / macro_layer / monte_carlo all unchanged)
- Touch `.api_key`, `canary.service`, `/root/canary/`, L99 halt, or canary_arm.json
- Open exchange write sockets
- Place real orders

They **CAN** (and are designed to):
- Read market data via public REST (read-only)
- Read paper-arena.json (read-only)
- Write `runtime/arena_features.json` (single output file)
- Be killed via SIGTERM with clean exit + pid file cleanup

If future Claude/operator wants to wire arena features into trading decisions:
- Author a NEW spec (e.g., Spec #25 "BOSS_EVENT_RISK_MODULATION")
- Update Constitution Article 4 evolution boundaries if needed
- Re-validate all 5 LAYER_DISCIPLINE gates against new spec
- That is NOT this v1.

---

## Cross-references

- `paper_battle/arena_features.py` — pure-function implementation
- `arena_shadow_runner.py` — CLI wrapper (paper-safe guards)
- `governance/SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER_v1.md` (Spec #22) — Layer 3 (Cinematic) where arena UI lives
- `governance/AI_CHAMPIONSHIP_USDT_DOMINATION_DOCTRINE.md` (Spec #11) — championship layer rules
- `paper_battle/paper_battle_engine.py` — 8-agent engine (untouched, source of agent state)
- `runtime/arena_features.json` — output file (gitignored)
