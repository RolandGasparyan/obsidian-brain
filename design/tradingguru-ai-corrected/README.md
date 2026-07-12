# tradingguru.ai — Corrected Design

**Paths:**
- `design/tradingguru-ai-corrected/index.html` — single-page design spec
- `design/tradingguru-ai-corrected/full-site/` — complete multi-page static site (6 pages + 404)
- `design/tradingguru-ai-corrected/full-site/DEPLOY.md` — deploy / port instructions

**Date:** 2026-05-19
**Status:** Design spec + ready-to-deploy static site — to be ported into the frontend repo (`ai-trading-championship`)

---

## What the previous live design got wrong

The version currently rendering at `https://tradingguru.ai` contains demo
data that contradicts the project's own governance:

| Element on live site                       | Problem                                                     |
|--------------------------------------------|-------------------------------------------------------------|
| `$1,000,000 USDT — TARGET — WINNER TAKES ALL` | No prize pool exists. No buy-in exists. Fabricated.       |
| `FIRST AGENT TO HIT THE MILLION WINS THE POT` | Implies a competition with payouts that does not exist.   |
| Any pre-baked PnL / cycle / win-rate cards | Telemetry must show real state or `—`, never staged demos.  |
| Live-trading badging / "GO LIVE" CTAs      | L99 halt engaged. Capital ringfenced. Paper-only.           |

These contradict:

- `governance/LAYER_DISCIPLINE.md` (firewall: L3 cannot fake L1 state)
- `docs/9-refusals-log.md` (refusal #04, #06: no go-live, no fabricated edge)
- `README.md` sacred locks table (capital paused, sockets = 0)

## Corrections applied in this spec

1. **Removed the $1,000,000 USDT "winner takes all" pot entirely.** Replaced
   with an honest hero stating the project is paper-mode, no prize pool, no live
   orders.
2. **Removed every demo number from every panel.** Where the live frontend
   currently shows fabricated stats (PnL, cycles, win rates), this spec shows
   either a verified governance value (capital, SHA256, sockets=0, refusals=9)
   or an explicit empty state with `—` and the sentence "shown only when
   measured, never estimated."
3. **Added a `◆ NOTICE` disclosure block** directly in the hero making the
   paper-mode posture unambiguous to first-time visitors.
4. **Preserved the retro-pixel + CRT aesthetic** (Press Start 2P + VT323,
   scanline overlay, amber glow, corner brackets) so the visual identity stays
   continuous — only the *content* is corrected.
5. **Replay Arena panel** ships with four empty-state blocks (Event Feed, Boss
   Moments, Heatmap, Cycle Stats) that populate only when the L2 telemetry feed
   is live. No mocked rows, no placeholder bars.

## Source data — what's allowed to be hard-coded

Only values that are independently locked elsewhere in this repo may appear
as constants in the design:

| Value                                | Source of truth                                     |
|--------------------------------------|-----------------------------------------------------|
| `$1,980.90 USDT`                      | `README.md` sacred locks table                      |
| `SHA256 704dd5725a909fe3f6…`          | `README.md` sacred locks table                      |
| `Live sockets: 0`                     | `README.md` sacred locks table                      |
| `Refusals on record: 9`               | `docs/9-refusals-log.md`                            |
| `L99 halt engaged`                    | `README.md` sacred locks table                      |
| `Paper-only · read-only`              | `governance/LAYER_DISCIPLINE.md`                    |

Everything else is `—`.

## Porting checklist for the frontend repo

When this design is ported into `ai-trading-championship`:

- [ ] Delete the `$1,000,000 USDT` hero component and any references in routing.
- [ ] Delete or stub any component that renders win rates / PnL / cycles from
      a constant rather than from the live telemetry endpoint.
- [ ] Add the `◆ NOTICE` disclosure block to the top of the landing route.
- [ ] Wire the four arena empty-states to the existing `/api/battle/replay-*.json`
      endpoints; show the empty-state copy until the response is non-empty.
- [ ] Verify the capital/SHA256/sockets/refusals cards read from a single
      governance JSON, not duplicated constants in components.

This file is the design contract. The frontend repo owns the implementation.
