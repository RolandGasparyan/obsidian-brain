# ADR-001: Stack continuation vs. edge-class pivot

**Status:** Accepted (2026-04-25) · Gate-triggered via Phase A analyzer on ~2026-04-30
**Deciders:** Roland (operator)

## Context

After 5 increasingly rigorous research rounds — walk-forward, param sweep,
regime gates, mean-reversion ensemble, deep_edge, max_edge with 9-pair
portfolio, professional backtest.py with 70/30 OOS split, godsmode 80 runs —
zero standard technical-signal strategy cleared the ship gate on any
combination of 10+ strategies × 2 timeframes × 4–9 pairs we tested.

The honest finding was not "our parameters are wrong." The edge class
(moving-average trend-follow and close cousins) does not currently produce
statistically distinguishable signal above fee+slippage drag on 1d/4h spot
crypto data for the pairs we tested.

## Decision

**Adopt Option A: continue the current stack for exactly 5 more days,
auto-gated by the `microstructure_analyze.py` IC/t-stat threshold.**

- Day 0–5: Phase A data accumulation, no new trading code on `main`.
- Day 5: run analyzer. `|IC| ≥ 0.04 AND |t| ≥ 2.0` on ≥2 pairs → ADR-002.
- Otherwise: automatically pivot to B1 (on-chain edge class) per fallback.

The cheap experiment resolves first. Sunk cost is capped at 5 days.

## Options Considered

### Option A — Continue, resolve via Phase A analyzer (5 days)
Infrastructure is built. OFI has peer-reviewed IC in equities
(Cont–Kukanov–Stoikov 2014). Crypto spot is unstudied. 5-day data window
is cheap, binary, and decisive.

### Option B — Pivot to different edge class (2–4 weeks)
- **B1: On-chain flow** (Glassnode/Coinglass/CryptoQuant) — hourly-to-daily
  signals, peer-reviewed positive IC in 2024–2025 papers. 90% infra reuse.
- **B2: Market-making** — spread capture, inventory-neutral in theory,
  requires real OMS + inventory model.
- **B3: Cross-exchange arbitrage** — multi-venue integration, slow-moving
  tiers still exist but fast tiers eaten by pros.

### Option C — Stop actively developing, hold position
Paper bots keep running. Research infra bit-rots. Highest honesty, lowest
learning.

## Trade-off Analysis

The decision variable is **operator attention**, not money or infra.

| Path | Attention cost | Time to next verdict | Learning value |
|---|---|---|---|
| A (continue) | 5 days passive + 2h active | 5 days | High (cheap test) |
| B1 (on-chain) | 2–3 weeks active | 2–3 weeks | Medium-high |
| B2 (MM) | 4+ weeks | 4+ weeks | Medium (risk of reproducing B1's failure) |
| C (stop) | 0 | — | Zero new |

A first is dominant: cheapest to resolve, already in motion, failure case
triggers B1 automatically.

## Consequences

**Easier:** 5 days of zero ambiguity. Binary decision point.
**Harder:** Resisting mid-stream temptation to tune MA50 "one more time."
**Revisit:** If analyzer shows borderline (|IC| 0.02–0.03, |t| 1.5–2.0),
default is pivot (B1), not a 6th tuning round.

## Action Items

1. [ ] D1: commit this ADR bundle
2. [ ] D3 (~2026-04-27): sanity-check partial analyzer output
3. [ ] D6 (~2026-04-30): full 5-day analyzer run
4. [ ] D7: green-light Phase B per ADR-002, or trigger B1 pivot
