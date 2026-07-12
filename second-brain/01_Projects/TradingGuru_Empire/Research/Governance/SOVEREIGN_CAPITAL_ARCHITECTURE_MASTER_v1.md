# SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER v1.0

**Operator-authored:** 2026-05-13 (spec #22 — the architectural umbrella)
**Status:** ACCEPTED · documented · **CONSOLIDATIVE** · maps all 21 prior specs into 5 sovereign layers
**Classification:** Long-horizon capital operating system architecture (10-20 year survivability target)

---

## Why this spec matters

Specs #1-#21 each described a component or behavior. **Spec #22 is the philosophical north star** — the architectural framing that tells future-Claude (and future-operator) what every prior spec is in service of: not a trading bot, but a sovereign capital organism designed to survive multi-decade horizons.

> "Capital preservation > Aggressive growth. Survival > Speed. Structure > Emotion. Probabilities > Predictions. Discipline > Ego."

---

## Section II — Five Sovereign Layers (with current implementation mapping)

### Layer 1 — SURVIVAL CORE

**Mission:** Prevent structural collapse.

| Component | Current implementation |
|-----------|-----------------------|
| Hard exposure caps | `LAYER_DISCIPLINE.md` 5-gate · `macro_layer.ARTICLE3_EXPOSURE_MAX_PCT=1.0` |
| Risk per trade ceiling | `Constitution Article 3` · `macro_layer.ARTICLE3_RISK_PER_TRADE_MAX_PCT=0.75` |
| Portfolio concentration limits | Shadow runner `MAX_CONCURRENT=1` · `NO_CAPITAL_MIGRATION=1` |
| Drawdown compression ladder | `mc_compress_active` + `bayes_entropy>1.5 → 0.7× compression` |
| Risk-of-ruin < 1% | `monte_carlo.kelly_compression_required` enforces |
| Black Swan freeze protocol | `shadow_round.check_auto_freeze` (3 consec / DD≥2% / slip spike) |
| Capital firewall | `CAPITAL_DEFENSE_GRID.md` Layer 8 · L99 halt |
| Kill-switch sovereignty | `CAPITAL_DEFENSE_GRID.md` Layer 9 · operator-verbatim only |

**Invariant:** "Nothing overrides this layer." → Matches Constitution Article 3 + Capital Defense Grid Layer 9 + Anthropic system rule.

**Status:** ✅ FULLY IMPLEMENTED

---

### Layer 2 — ADAPTIVE INTELLIGENCE LAYER

**Mission:** Prevent edge decay.

| Component | Current implementation |
|-----------|-----------------------|
| Bayesian regime transition modeling | `paper_battle/bayesian_regime.py` (6 regimes, transition matrix, Shannon entropy) |
| Macro pressure index | `paper_battle/macro_layer.py` (0-100 score, 5 modes) |
| Regime entropy detection | `bayesian_regime.shannon_entropy()` · wired into risk sizing |
| Execution quality calibration | `shadow_round` execution_stability_score (0-100, CV-based) |
| Drift monitoring | ⏳ DEFERRED — Spec #21 Meso loop (needs 7d data) |
| Performance variance tracking | Partial — `slippage_history` variance · expand in meso loop |

**Status:** 🟡 70% IMPLEMENTED (drift monitoring deferred to Spec #21 Meso loop)

---

### Layer 3 — CAPITAL ORCHESTRATION SYSTEM

**Mission:** Optimize allocation efficiency.

| Component | Current implementation |
|-----------|-----------------------|
| Multi-agent weighted allocation matrix | ⏳ DEFERRED — Spec #20 Part III (needs design) |
| Correlation compression | Partial — `macro_layer._correlation_stress` measures, doesn't yet act |
| Risk concentration score | ⏳ DEFERRED — needs multi-agent |
| Aggression governor | ✅ `macro_layer.apply_macro_to_risk` + phase logic + entropy compression |
| Capital migration logic | ❌ Forbidden in micro-test (Spec #14 `NO_CAPITAL_MIGRATION=1`). Will unlock at Phase 3+ post-validation. |
| Exposure balancing | Single-strategy now · multi-agent in Spec #20 Part III |

**Status:** 🟡 30% IMPLEMENTED (single-strategy aggression governor active; multi-agent allocator deferred)

---

### Layer 4 — META-CIVILIZATION LOOP

**Mission:** Govern evolution safely.

| Component | Current implementation |
|-----------|-----------------------|
| Micro cycle (per round calibration) | ⏳ DEFERRED — Spec #21 Phase 1 (wireable after 5+ rounds) |
| Meso cycle (weekly research update) | ⏳ DEFERRED — Spec #21 Phase 3 (needs 7d data) |
| Macro cycle (quarterly structural audit) | ⏳ DEFERRED — Spec #21 Phase 5 (needs 90d data) |
| Evolution speed governor | ⏳ DEFERRED — Spec #21 Section IV |
| Mutation boundaries | ✅ Codified — Constitution Article 4 ("May NOT evolve: risk caps, stop-loss, human override, governance firewall") |
| Sandbox validation | ✅ Codified — `AI_SOVEREIGN_GLOBAL_v2.md` Layer 7 ("No stage skipping permitted") |
| Strategy retirement logic | ⏳ DEFERRED — needs multi-agent + 90d data |
| Structural drift detection | ⏳ DEFERRED — needs longitudinal data |

**Status:** 🟡 20% IMPLEMENTED (boundaries codified; loops deferred per Spec #21 phased roadmap)

---

### Layer 5 — HUMAN SOVEREIGN CONTROL

**Mission:** Preserve final authority.

| AI cannot... | Enforcement |
|--------------|-------------|
| Remove risk caps | Constitution Article 3 (immutable) + Spec #19 Section VI |
| Increase leverage ceiling | Constitution Article 3 (immutable) |
| Disable capital firewall | Capital Defense Grid Layer 8 + L99 halt |
| Override kill switch | Capital Defense Grid Layer 9 + Anthropic system rule |
| Self-modify core invariants | Pre-commit hook SHA256 lock guard + Constitution Article 4 |

**Status:** ✅ FULLY IMPLEMENTED · all 5 enforcements active

---

## Section III — Capital Evolution Ladder

| Capital | Behavior | Current vs Target |
|---------|----------|-------------------|
| $1K | Survival priority | ← we are here (paper) |
| $10K | Stability optimization | future |
| $100K | Allocation sophistication | future |
| $1M | Preservation discipline | future |
| $10M | Volatility compression | future |
| $100M+ | Systemic risk immunity | future |

> **Rule (verbatim):** "More capital = more discipline."

→ Same as Spec #21 Section VI Civilization Growth Model.

**Current state:** pre-Stage-1 paper. All micro-test parameters (Spec #14: 0.25% risk, 1% exposure, 1 concurrent) already enforce $1K-survival discipline more strictly than Spec #22's $1K row demands — the system is currently OVER-disciplined for its capital tier, which is the correct posture for a new system.

---

## Section IV — Probabilistic Governance

> "High entropy → reduce aggression. Low entropy + validated edge → controlled expansion. No binary thinking. Only probability-weighted action."

**Implementation:**
- `bayesian_regime.shannon_entropy` → fed into `shadow_round.simulate_trade`
- Rule (already coded): `if bayes_entropy > 1.5: risk_pct ≤ 0.7 × RISK_PER_TRADE_PCT`
- Posterior-driven sizing rather than binary regime tags

✅ ACTIVE

---

## Section V — Monte Carlo Civilization Audit

> "5,000–10,000 capital paths · regime switching randomness · slippage variability · drawdown clustering · tail event modeling. If projected ruin > threshold: compress risk. Simulation always precedes scale."

**Implementation:** `paper_battle/monte_carlo.py` (Spec #20 Part II)
- 2,000-5,000 paths × 20 trades (configurable)
- Trigger schedule: round_start | regime_shift | 3_consec_losses
- Outputs: p05/p50/p95 equity, max_dd_p95, RoR, Kelly fraction
- Auto-compression when projected DD > Article 3 tolerance OR RoR > 1%

✅ ACTIVE

---

## Section VI — Defense Modes

| Mode | Trigger | Implementation |
|------|---------|----------------|
| **DEFENSIVE MODE** | macro_score 40-70 | ✅ `macro_layer` mode=DEFENSIVE → risk_mult=0.6 · exposure=0.5% · aggression OFF |
| **OBSERVATION MODE** | instability detected | ⏳ DEFERRED — Spec #21 Section III (needs longitudinal stability metric) |
| **CIVILIZATION DEFENSE MODE** | regime misprediction spike OR MC tail error OR DD acceleration | ⏳ DEFERRED — Spec #21 Section VII (needs meso cycle data) |
| **PANIC MODE** (de-facto) | macro_score < 25 | ✅ `macro_layer` mode=PANIC → risk_mult=0.5 · exposure=0.4% · aggression OFF |
| **AUTO-FREEZE** | 3 consec losses / DD ≥ 2% / slip spike 2× | ✅ `shadow_round.check_auto_freeze` |

**Status:** 🟡 60% IMPLEMENTED (DEFENSIVE + PANIC + AUTO-FREEZE active; OBSERVATION + CIVILIZATION_DEFENSE need longitudinal stability metrics)

---

## Section VII — Success Metrics (verbatim)

> System success is NOT:
> - Highest single round profit
> - Aggressive short-term spike
> - One championship victory
>
> System success IS:
> - Low volatility equity curve
> - Controlled drawdown behavior
> - High survival probability
> - Stable compounding
> - Low entropy allocation
> - Tail-risk immunity

**What's currently measured:**
- ✅ Low volatility equity curve → `execution_stability_score`
- ✅ Controlled drawdown → `max_dd_pct` + `monte_carlo.max_dd_p95_pct`
- ✅ High survival probability → `monte_carlo.risk_of_ruin_pct`
- ✅ Stable compounding → `monte_carlo.cagr_estimate_pct`
- ✅ Low entropy allocation → `avg_regime_entropy_nats`
- 🟡 Tail-risk immunity → partial via `p05_equity`; full CVaR/expected-shortfall pending

**Next concrete build:** `paper_battle/survival_metrics.py` — single function `compute_sovereign_survival_score(round_summary)` that combines the 6 metrics into a 0-100 sovereign-grade score. Estimated build: 30 min. Will surface as `sovereign_survival_score` in round summary.

---

## Section VIII — What this gives over long horizon (verbatim philosophical)

> "Reduced collapse probability · Controlled risk scaling · Structural learning · Allocation intelligence · Capital longevity · Institutional-grade discipline. Not speed. Not hype. Not blind aggression. **Longevity.**"

---

## Implementation Status Summary

| Layer | Status | Gap |
|-------|--------|-----|
| 1. Survival Core | ✅ 100% | — |
| 2. Adaptive Intelligence | 🟡 70% | drift monitoring (Spec #21 meso) |
| 3. Capital Orchestration | 🟡 30% | multi-agent allocator (Spec #20 Part III) |
| 4. Meta-Civilization Loop | 🟡 20% | micro/meso/macro loops (Spec #21 phased) |
| 5. Human Sovereign Control | ✅ 100% | — |

**Aggregate:** ~64% — strong foundation, gaps are well-defined and time-gated (need data accumulation, not new architecture).

---

## Final Declaration (verbatim)

> Shadow validates. Micro proves. Capital scales. Discipline governs. **Survival compounds.**

---

## Cross-references

- `AI_DISCIPLINE_CONSTITUTION.md` (#12) — canonical citation source
- `META_EVOLUTION_PREDICTIVE_v2_CHARTER.md` (#13) — constitutional companion
- `AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md` (#14) — operational protocol
- `SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md` (#17) — shadow runner spec
- `AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1.md` (#19) — Layer 2 macro
- `BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md` (#20) — Layer 2 bayesian + Layer 3 allocator (Part III deferred)
- `META_CIVILIZATION_LOOP_v1.md` (#21) — Layer 4 evolution loops
- `MICRO_LIVE_OPERATOR_CHECKLIST.md` — operator path to Stage 1 Capital Evolution
- `MASTER_ARCHITECTURE_v2.0.md` — index of all 22 specs
