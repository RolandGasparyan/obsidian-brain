# L99 — ULTRA AGGRESSIVE ALPHA DISCOVERY: Exact Factor Blueprint (4 Data Classes)

**Source:** Operator spec, 2026-05-02 (factor blueprint paste, post-research-roadmap)
**Status:** Spec preserved verbatim · 12 factors across 4 classes · priority queue defined · operationalized via `wiki/research-log/`
**Pre-req for activation per factor:** API keys for the relevant data class + Phase 0 hypothesis note + access to historical data

---

## I. The original spec (verbatim)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L99 — ULTRA AGGRESSIVE ALPHA DISCOVERY
EXACT FACTOR BLUEPRINT (4 DATA CLASSES)
Version: 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MISSION:
Systematically test structurally justified alpha candidates.
No indicator stacking.
No curve fitting.
All signals must pass full validation battery.

PRIMARY VALIDATION RULES:
- |IC| ≥ 0.04
- t-stat ≥ 2.0
- Profit Factor ≥ 1.3
- Q5−Q1 ≥ 60 bps (after fees)
- Monte Carlo stability
- Multi-regime survival
- Fail ANY → immediate kill

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLASS A — ON-CHAIN STRUCTURAL FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A1 — Exchange Netflow Shock Reversal

Hypothesis:
Large BTC exchange inflow spike predicts short-term downside.

Factor:
Netflow_z = (Netflow - rolling_mean_30d) / rolling_std_30d
Signal = Netflow_z > +2

Test Horizons:
t+1d
t+3d
t+7d

Expected:
Negative forward return.

Kill If:
Edge disappears post-2022.

──────────────────────────────────

A2 — Stablecoin Supply Impulse

Hypothesis:
Sudden stablecoin minting injects liquidity → bullish drift.

Factor:
SC_growth_7d = % change in total USDT+USDC supply (7d)
Signal = SC_growth_7d_z > +1.5

Test:
t+3d
t+7d

Expected:
Positive forward returns.

──────────────────────────────────

A3 — SOPR Regime Flip

Hypothesis:
SOPR crossing above 1 after prolonged <1 regime → bullish shift.

Factor:
SOPR_regime = rolling_mean_7d(SOPR)
Signal = Cross(SOPR_regime, 1.0)

Test:
Pre/post crossing return distribution.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLASS B — LEVERAGE INSTABILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

B1 — OI + Flat Price Divergence

Hypothesis:
Open Interest spike with flat price → leverage buildup → breakout risk.

Factor:
OI_z > +2
AND
abs(price_change_24h) < 1%

Test:
Volatility expansion within 48h.

──────────────────────────────────

B2 — Funding Extreme Mean Reversion

Hypothesis:
Funding > extreme threshold for 24h → short-term reversal.

Factor:
Funding_rolling_mean_24h > threshold

Test:
t+24h
t+48h

Expected:
Opposite direction move.

──────────────────────────────────

B3 — Liquidation Cluster Proximity

Hypothesis:
Price near major liquidation band → cascade probability.

Factor:
Distance_to_liq_band < 1%

Test:
Probability of ≥2% move within 12h.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLASS C — CROSS-ASSET MACRO FRICTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

C1 — BTC–DXY Divergence Break

Hypothesis:
BTC up while DXY up → unsustainable divergence.

Factor:
Rolling_30d_corr(BTC,DXY) < -0.3
AND BTC_3d_return > 3%
AND DXY_3d_return > 1%

Test:
3–5 day correction probability.

──────────────────────────────────

C2 — Volatility Regime Transition

Hypothesis:
ATR percentile jump from <30% to >70% → regime shift.

Factor:
ATR_percentile_14d crosses 70%

Test:
Continuation vs mean-reversion bias.

──────────────────────────────────

C3 — BTC–SPX Correlation Breakdown

Hypothesis:
Correlation collapse signals instability.

Factor:
Rolling_60d_corr drops below 0

Test:
Volatility spike likelihood.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLASS D — EXECUTION MICRO ALPHA (MAKER EDGE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

D1 — Spread Compression Breakout

Hypothesis:
Spread compresses to 10th percentile → imminent expansion.

Factor:
Spread_percentile_1h < 10%

Test:
1h breakout probability.

──────────────────────────────────

D2 — Orderbook Imbalance Persistence

Hypothesis:
Top-level imbalance persists → short drift.

Factor:
DIR = sum(bid_vol_5) / sum(ask_vol_5)
Signal = DIR > 1.5 sustained ≥10 snapshots

Test:
t+30m directional drift.

──────────────────────────────────

D3 — Passive Fill Edge

Hypothesis:
Queue modeling reveals maker rebate-adjusted edge.

Requires:
Queue simulation model.

Test:
Rebate-adjusted expectancy positive after slippage.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIORITY ORDER (Test First)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. A1 — Netflow Shock
2. B2 — Funding Extreme
3. A2 — Stablecoin Impulse
4. B1 — OI Divergence
5. C2 — Vol Regime Shift

Execution Micro Alpha (Class D) last — highest complexity.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE STACKING RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Do NOT combine factors initially.

Only combine if:
- ≥2 survive independently
- Correlation < 0.6
- Orthogonal drivers
- Regime-conditional performance stable

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL WAR RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

No validated statistical edge → stay in USDT.
No emotional override.
No endless optimization.
Only evidence-based deployment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## II. How this spec fits

This is **the missing input** to the L99 architecture: a concrete list of factors to test, in priority order, with kill criteria.

It operationalizes:
- `L99_RESEARCH_ROADMAP.md` Phase 1 (data class selection) — by naming 12 specific factors across 4 classes
- `L99_ALPHA_VALIDATION.md` Section 1.6 — by setting validation thresholds (|IC| ≥ 0.04, t-stat ≥ 2.0, PF ≥ 1.3, Q5−Q1 ≥ 60 bps)
- `L99_RESEARCH_ROADMAP.md` Phase 0 — by giving each factor explicit hypothesis + factor formula + test horizons + expected behavior + kill condition

The merged 5-layer L99 architecture (PRs #9-#13) plus PR #14 roadmap plus PR #15 audit plus this PR #16 blueprint = **complete pre-edge research stack**. Only missing piece: the data (API keys).

---

## III. Data class → API source mapping

| Class | Factors | Required API |
|---|---|---|
| A — On-chain structural flow | A1, A2, A3 | CryptoQuant + Glassnode |
| B — Leverage instability | B1, B2, B3 | Gate.io futures API + (optionally) Coinglass / Coinalyze for liquidations |
| C — Cross-asset macro | C1, C2, C3 | Yahoo Finance (DXY, SPX) + existing BTC feed + Gate.io spot ATR |
| D — Execution micro alpha | D1, D2, D3 | Existing `microstructure_collector.py` |

**Class A** is fully blocked on the 3 API keys (CryptoQuant + Glassnode + Whale Alert) — same blocker as B.2.3.

**Class B** requires one new collector for funding rate + OI from Gate.io futures (Gate.io provides futures API but the existing collector is spot-only).

**Class C** requires DXY + SPX historical data (free via yfinance / Yahoo Finance).

**Class D** is unblocked — current `microstructure_collector` already captures spread + orderbook imbalance.

---

## IV. Priority queue (first 5 to test)

| Rank | Factor | Class | Status | Blocker |
|:---:|---|---|:---:|---|
| 1 | A1 — Netflow Shock | A | 🔴 blocked | API keys (CryptoQuant) |
| 2 | B2 — Funding Extreme | B | 🟡 partially blocked | needs Gate.io futures collector |
| 3 | A2 — Stablecoin Impulse | A | 🔴 blocked | API keys (Glassnode) |
| 4 | B1 — OI Divergence | B | 🟡 partially blocked | Gate.io futures collector |
| 5 | C2 — Vol Regime Shift | C | 🟢 unblocked | (uses existing data) |

**C2 is the only fully-unblocked priority factor.** Could be the first cycle even before API keys arrive — uses ATR percentile from already-collected microstructure data.

---

## V. Edge stacking rule

The spec is explicit: **do NOT combine factors initially.** Each must pass independently.

Combining is allowed only when:
1. ≥ 2 factors survive independently
2. Correlation < 0.6 (orthogonal)
3. Stable in multi-regime conditions

This rules out the "ensemble of weak factors" pattern that was tried (and rejected) in `feat/ensemble-edge-sweep` (PR #3).

---

## VI. What this spec REPLACES

- **Ad-hoc factor selection** → 12-factor explicit backlog with hypothesis + kill criteria
- **"Try this random idea"** → strict priority queue with blockers identified
- **Stacked indicators** → independent-test rule

This spec does NOT supersede:
- `L99_RESEARCH_ROADMAP.md` — the *procedure* (Phases 0-7) still applies to each factor here
- `L99_ALPHA_VALIDATION.md` — the *thresholds* still apply
- `L99_SYSTEM_AUDIT.md` — the *current state assessment* still applies

This spec ADDS:
- Explicit factors to put through the procedure
- Concrete kill conditions per factor
- Priority order (so we don't waste cycles on Class D before B.2.3)

---

## VII. Operationalization

Each of the 12 factors gets a `wiki/research-log/<date>-<factor-id>-<slug>.md` note when the cycle starts. The note follows the Phase 0 template (PR #15).

Cross-link table:

| Factor | Research-log path |
|---|---|
| A1 | `wiki/research-log/<date>-A1-exchange-netflow-shock.md` |
| A2 | `wiki/research-log/<date>-A2-stablecoin-supply-impulse.md` |
| A3 | `wiki/research-log/<date>-A3-sopr-regime-flip.md` |
| B1 | `wiki/research-log/<date>-B1-oi-flat-price-divergence.md` |
| B2 | `wiki/research-log/<date>-B2-funding-extreme.md` |
| B3 | `wiki/research-log/<date>-B3-liquidation-cluster.md` |
| C1 | `wiki/research-log/<date>-C1-btc-dxy-divergence.md` |
| C2 | `wiki/research-log/<date>-C2-vol-regime-transition.md` |
| C3 | `wiki/research-log/<date>-C3-btc-spx-correlation.md` |
| D1 | `wiki/research-log/<date>-D1-spread-compression.md` |
| D2 | `wiki/research-log/<date>-D2-orderbook-imbalance.md` |
| D3 | `wiki/research-log/<date>-D3-passive-fill-edge.md` |

Priority-1 factor (A1 Netflow Shock) gets its research-log skeleton in this PR (`wiki/research-log/2026-05-02-A1-exchange-netflow-shock.md`).

The remaining 11 factors get skeletons created on-demand as cycles begin (one at a time per spec rule).

---

## VIII. ADR linkage

- **ADR-001** (validate before deploy) — every factor goes through full validation per `L99_ALPHA_VALIDATION` thresholds
- **ADR-002** (Phase B direction) — extends the decision tree with concrete factor list per branch
- **ADR-003** (D7 freeze) — expired; this is post-D7 documentation work

---

## IX. Sources

- Operator spec, 2026-05-02 (Ultra Aggressive Alpha Discovery factor blueprint)
- [docs/specs/L99_RESEARCH_ROADMAP.md](L99_RESEARCH_ROADMAP.md) — companion (procedure)
- [docs/specs/L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) — companion (thresholds)
- [docs/specs/L99_SYSTEM_AUDIT.md](L99_SYSTEM_AUDIT.md) — companion (current state)
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — branch tree (B.2.4 conflict still TODO)
- `wiki/research-log/_template.md` — Phase 0 template per L99_RESEARCH_ROADMAP §0
