# L99 — Unified Operations Runbook

Three engines under one Champion-Mode governance layer. Read
`CHAMPION_MODE.md` first; this is the *how to operate it* counterpart.

---

## Architecture

```
                         ┌─────────────────────────┐
                         │  CHAMPION GOVERNANCE    │
                         │  ──────────────────────  │
                         │  CapitalStageTracker    │
                         │  RiskLaws               │
                         │  PositionSizer          │
                         │  TradeJournal           │
                         │  ViabilityThresholds    │
                         └────────────┬────────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
       ┌─────────▼────────┐ ┌─────────▼────────┐ ┌─────────▼────────┐
       │  /godmode        │ │  /aegis-alpha    │ │  /quant-predator │
       │  Futures, 2-5min │ │  Spot, 4-72h     │ │  Spot, 2-14d     │
       │  Microstructure  │ │  Momentum 4H     │ │  MTF position    │
       │  Maker-biased    │ │  Top-50 USDT     │ │  BTC + top-20    │
       └─────────┬────────┘ └─────────┬────────┘ └─────────┬────────┘
                 │                    │                    │
       ┌─────────▼────────┐ ┌─────────▼────────┐ ┌─────────▼────────┐
       │ Gate.io Futures  │ │ Gate.io Spot     │ │ Gate.io Spot     │
       │ WS L2 + REST     │ │ REST candles     │ │ REST candles     │
       └──────────────────┘ └──────────────────┘ └──────────────────┘
```

Single source of risk truth: every engine routes orders through
`champion.PositionSizer.compute_size()`. No engine can violate doctrine.

---

## Build status

| Module | State | Notes |
|---|:---:|---|
| `champion/stage.py` | ✅ live | 4 stages, regression rule |
| `champion/risk.py` | ✅ live | 5-layer risk laws |
| `champion/sizer.py` | ✅ live | base × scalers × throttles |
| `champion/journal.py` | ✅ live | viability gate (50-trade window) |
| `l99/config.py` | ✅ live | unified config |
| `l99/cli.py` | ✅ live | `python -m l99 <cmd>` |
| `l99/btc_vol.py` | ✅ live | 14d realized-vol pctile feed |
| `aegis_alpha/scanner.py` | ✅ live | §3.1 scoring |
| `aegis_alpha/executor.py` | ✅ live | §3.2 + §3.3 entry/exit logic |
| `aegis_alpha/runtime.py` | ✅ live | paper-shadow loop |
| `godmode/collector.py` | ✅ live (24/7 systemd on VPS) | L2 + tape |
| `godmode/replay.py` | ✅ live | tick replay + maker-fill sim |
| `godmode/streams.py` | ✅ live | S1, S2, S5, S7 fully implemented; S3, S4, S6 v1 |
| `godmode/runtime.py` | ✅ live | wired to `champion.PositionSizer` |
| `quant_predator/` | ⏳ skeleton | scanner + executor stubs only |

---

## CLI — daily operations

```bash
# system status across all engines
python -m l99 status

# aegis-alpha spot scanner (one-shot)
python -m l99 scan-alpha --top 50 --show 20

# aegis-alpha paper-shadow (single cycle then exit)
python -m l99 paper-alpha --once

# aegis-alpha paper-shadow (continuous loop, 4H cadence)
python -m l99 paper-alpha

# BTC vol regime
python -m l99 btc-vol [--refresh]

# Champion §VI viability metrics
python -m l99 journal-stats --engine aegis_alpha --window 50

# global kill — every engine refuses new entries until cleared
python -m l99 halt-all
python -m l99 resume-all
```

---

## Paper-shadow forward-test plan

Champion gate: **50+ trades minimum** before any real capital, all 8
viability metrics must pass on the most recent 50 trades.

Phase 1 — Now (data accumulation):
1. `godmode-collector.service` runs 24/7 (already on VPS)
2. `python -m l99 paper-alpha` runs every 4h (cron or systemd)
3. Champion journal accumulates closed-trade records
4. Daily check: `python -m l99 journal-stats --engine aegis_alpha`

Phase 2 — Conditional (only when paper proves viability):
- 50 trades on aegis_alpha, all metrics pass → consider tiny real capital
- Same independently for godmode and quant-predator
- Real-money rollout still subject to Champion §V risk protocol

Phase 3 — Scale (only after Phase 2 sustains 90 days):
- Stage 1 capital: $3k seed (per CHAMPION_MODE.md §1.3)
- Allocations per stage from `l99.CONFIG.allocation(stage)`

---

## Suggested systemd units (when ready to deploy)

`/etc/systemd/system/aegis-paper.service`:

```ini
[Unit]
Description=L99 aegis_alpha paper-shadow loop
After=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/ai-trading-championship
Environment=PYTHONUNBUFFERED=1
Environment=L99_STARTING_EQUITY=3000.0
ExecStart=/var/www/ai-trading-championship/venv/bin/python -m l99 paper-alpha
StandardOutput=append:/var/log/aegis-paper.log
StandardError=append:/var/log/aegis-paper.log
Restart=on-failure
RestartSec=30
MemoryMax=512M
RuntimeMaxSec=7d

[Install]
WantedBy=multi-user.target
```

`godmode-collector.service` is already running on the VPS (commit 2515379+).

---

## File map

```
champion/                — Doctrine governance (risk + sizing + journal)
godmode/                 — Engine 1: futures microstructure
aegis_alpha/             — Engine 2: spot momentum
quant_predator/          — Engine 3: MTF position trading (skeleton)
l99/                     — Top-level config + CLI + utilities
.l99_data/<engine>/      — Per-engine journals, decisions, snapshots (gitignored)
tests/                   — 50+ unit tests, all passing
CHAMPION_MODE.md         — The doctrine (north star)
GODMODE_FUTURES_ARCH.md  — godmode architecture
L99_OPERATIONS.md        — this document
```

---

## Hard rules (immutable, never override)

1. Every order routes through `champion.PositionSizer.compute_size()`.
2. Stops only tighten, never widen.
3. No `STATE_B → STATE_B` (always return to USDT between trades).
4. Stage regression is instant; promotion requires 1% buffer.
5. Daily DD ≥ 5% → halt today. Weekly DD ≥ 10% → 48h pause. Peak DD ≥
   15% → minimum size only. BTC −20% in 7d → ALL engines off.
6. After 50 trades, if any §VI metric fails minimum → engine pauses
   until reviewed.
7. No real money until paper-shadow proves viability per §VI.

The doctrine is the only thing the code is allowed to enforce.
The code is the only thing allowed to enforce the doctrine.
