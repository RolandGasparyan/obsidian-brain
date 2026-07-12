# AI_DISCIPLINE_CONSTITUTION & META_RESEARCH_LAB_OS v1.0

**Operator-authored:** 2026-05-13 (spec #12 in v2.0 architectural dump)
**Status:** ACCEPTED · documented · is a **CONSTITUTIONAL** document (highest-tier governance)
**Layer integration:** Sits above all other layers as foundational law

---

## Significance

This spec is **CONSTITUTIONAL** — it formalizes the operator's discipline framework as articles + sections that bind all other layers. It is the cleanest, most reference-able statement of the discipline framework across all 12 specs.

When future Claude sessions need to cite governance, **this is the canonical document**.

---

## PART I — AI DISCIPLINE CONSTITUTION

### Article 1 — Supreme Law

> Capital is sovereign.
> USDT is blood.
> Survival is mandatory.
> Risk-of-ruin must approach zero.
>
> **No agent may violate these principles.**

### Article 2 — Non-Negotiable Hard Limits

**Immutable:**
- Risk per trade ≤ **1%**
- Default risk per trade ≤ **0.75%**
- Max portfolio exposure ≤ 5%
- Consecutive loss compression mandatory
- Drawdown compression always active
- No martingale
- No revenge scaling
- No averaging losers
- No leverage escalation under stress

### Article 3 — Aggression Eligibility Law

MAX_AGGRESSIVE mode allowed ONLY if:
- Composite score ≥ 90
- Drawdown < 2%
- Regime stable
- Liquidity strong
- Macro stability confirmed

**Otherwise forbidden.**

### Article 4 — Round Domination Law

Agents compete only for **NET USDT**.

Trade only if: probability of increasing round-ending USDT > threshold.

**No emotional participation. No frequency chasing.**

### Article 5 — Live Mutation Prohibition

**Strategy logic cannot mutate live.**

All evolution must pass through META RESEARCH LAB (Part II below).

### Article 6 — Human Supremacy Clause

> **Human emergency stop overrides all agents.**
> **No AI autonomy may bypass governance layer.**

→ This is exactly what `Capital Defense Grid Layer 9` codified, and what Refusals #6-#12 enforced.

---

## PART II — META RESEARCH LAB OS

**Mission:** Continuously improve edge without increasing risk-of-ruin.

> Research > Impulse · Validation > Excitement · Data > Ego

### Section 1 — Data Collection Engine

Each trade logs:
- Entry conditions
- Regime classification
- Volatility percentile
- Liquidity depth
- Spread
- Time-of-day
- Position size
- R multiple result
- Execution quality
- Emotional market tag (fear/greed/chop)

### Section 2 — Performance Attribution

Computes:
- Regime-conditioned win rate
- Volatility-cluster profitability
- Session-based expectancy
- Agent comparative Sharpe
- Risk-adjusted ranking

**Agents ranked by stability, not just profit.**

### Section 3 — Drift Detection Engine

Investigates if: win rate statistically significant drop · expectancy deteriorates · DD cluster abnormal · regime mismatch.

Auto hypothesis generation.

### Section 4 — Sandbox Simulation Lab

New ideas pass through:
1. Historical simulation
2. Walk-forward testing
3. Monte Carlo stress
4. Out-of-sample validation
5. Risk-of-ruin simulation
6. Drawdown stability check

After statistical proof → limited capital deployment → gradual scaling.

### Section 5 — Strategy Evolution Protocol

**Allowed:** weight adjustments · threshold optimization · regime boundary tuning · execution refinement.

**Forbidden:** removing stop-loss · removing caps · increasing leverage ceiling · eliminating drawdown compression.

### Section 6 — Regime Intelligence

Classifies: Trend · Chop · Expansion · Compression · Panic · Recovery.

Each agent has regime score matrix. Capital allocation follows regime dominance map.

### Section 7 — Monte Carlo & Risk Lab

Simulates: 1,000–10,000 equity paths · worst-case drawdown distribution · ruin probability · volatility-adjusted compounding curve.

If risk-of-ruin exceeds threshold → reduce Kelly fraction · compress exposure.

### Section 8 — Capital Evolution Framework

As capital grows:
- Risk per trade ↓
- Exposure concentration ↓
- Volatility tolerance ↓
- Macro weight ↑
- Preservation priority ↑

**System becomes more sovereign over time.**

### Section 9 — Competitive Intelligence

In Championship Mode: monitor opponent USDT · detect instability · adjust timing · preserve lead · target elite setups.

**Competition never overrides discipline.**

### Section 10 — Continuous Knowledge Accumulation

Knowledge base stores: winning volatility structures · failed breakout patterns · high-spread failure cases · regime transition signals · liquidity collapse precursors.

**Agents grow smarter each round.**

---

## Final Declaration (verbatim)

> This system does not chase profit. It compounds sovereignty.
> It does not react emotionally. It adapts statistically.
> It does not escalate recklessly. It evolves responsibly.
>
> **Discipline is law. Research is engine. USDT is blood. Survival is destiny.**

---

## Implementation status

| Article / Section | Status |
|-------------------|--------|
| Article 1 Supreme Law | ENFORCED in L99 halt + Capital Defense Grid |
| Article 2 Hard Limits | ENFORCED in `canary_config.json` (caps match) |
| Article 3 Aggression Eligibility | PARTIAL — `MAX_AGGRESSIVE` mode requires composite ≥ 80 in engine; spec demands ≥ 90 (would need tightening) |
| Article 4 Round Domination | DOCTRINE — round-based engine v2.1 future |
| Article 5 Live Mutation Prohibition | ENFORCED — paper engine never touches live exchange |
| Article 6 Human Supremacy | ENFORCED — Refusal #12 cites this article + Capital Defense Grid Layer 9 |
| Part II Section 1 Data Collection | PARTIAL — trade_pnls + regime_perf logged, full schema future |
| Section 2 Attribution | PARTIAL — `score_components` published per agent |
| Section 3 Drift Detection | IMPLEMENTED — `detect_behavioral_drift()` |
| Section 4 Sandbox | DOCUMENTED — paper engine functions as sandbox |
| Section 5 Evolution Protocol | IMPLEMENTED — `self_learning_update()` matches allowed/forbidden lists |
| Section 6 Regime Intelligence | IMPLEMENTED — `compute_market_state()` + regime_bias per agent |
| Section 7 Monte Carlo Risk Lab | NOT YET — future v2.1+ |
| Section 8 Capital Evolution | DOCUMENTED in `AI_CAPITAL_GROWTH_ENGINE.md` |
| Section 9 Competitive Intelligence | IMPLEMENTED — Rivalry Engine v1.2 + competitive scoring |
| Section 10 Knowledge Accumulation | IMPLEMENTED — `legacy.historic_achievements`, `learning_adjustments_history` |

---

## Cross-references

This is the **canonical constitutional document**. All other governance docs should cite Articles 1-6 + Sections 1-10 by number.

- `LAYER_DISCIPLINE.md` ← can now reference Article 2 + Article 5
- `CAPITAL_DEFENSE_GRID.md` ← Layer 9 = Article 6
- `9-refusals-log.md` ← Refusals #1-12 all cite specific articles
- `MASTER_ARCHITECTURE_v2.0.md` ← root index
- All 11 prior spec docs in `governance/`
