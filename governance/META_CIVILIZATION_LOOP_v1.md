# META_CIVILIZATION_LOOP v1.0

**Operator-authored:** 2026-05-13 (spec #21 in v2.0 dump)
**Status:** ACCEPTED · documented · **IMPLEMENTATION PHASED** (Micro loop wireable now, Meso/Macro require longitudinal data)
**Classification:** Ultra-strategic evolution layer

---

## Why this spec is different

Specs #14-#20 specified what the system does each round. **Spec #21 specifies how the system improves itself over time** — across three nested time horizons:

| Loop | Horizon | What it improves | Buildable now? |
|------|---------|------------------|----------------|
| **Micro Meta Loop** | Per round (90 min) | Calibration: slippage model, priors, aggression | ✓ Yes — wireable into shadow_round summary |
| **Meso Meta Loop** | Weekly | Transition matrix, macro weights, agent regime-performance vectors | ⏳ Requires 7d of round summaries |
| **Macro Meta Loop** | Quarterly | Structural changes: retire agents, add regimes, capital roadmap | ⏳ Requires 13+ weeks of data |

---

## Section II — Meta-Cycle Structure

### A. Micro Meta Loop (per round) — IMPLEMENTABLE NOW

**Inputs (per round):**
- Realized R vs Modeled R deviation
- Risk compression accuracy
- Macro-regime anticipation accuracy
- Agent allocation efficiency (deferred — needs Spec #20 Part III)
- Monte Carlo calibration error (predicted DD vs realized DD)

**Output:** `META_PERFORMANCE_SCORE` (0-100)

**Actions if deviation > threshold:**
- Reduce aggression globally (`base_aggression *= 0.9`)
- Adjust Bayesian priors (carry forward weighted posterior into next round)
- Recalibrate slippage model (`slip_base *= realized_avg / modeled_avg`)

**Critical constraint:** No structural rewrite at micro level. Calibration only.

**Implementation path:** Add `paper_battle/meta_loop_micro.py` that runs at end of each round, reads the round summary JSON, computes meta_performance_score, writes calibration adjustments to `runtime/calibration.json` for next round to consume.

### B. Meso Meta Loop (weekly) — REQUIRES 7d DATA

**Inputs:** 7 days of trade logs (JSONL) + round summaries

**System asks:**
1. Which regime transitions were mispredicted?
2. Which agents underperformed expectation? (deferred)
3. Was Kelly compression sufficient?
4. Did Monte Carlo under/overestimate tail risk?

**Outputs:**
- Update transition matrix probabilities (bounded ±10%/week)
- Update macro weight coefficients
- Update agent regime-performance vectors
- Reweight feature importance in composite scoring

**Implementation path:** `paper_battle/meta_loop_meso.py` — runs weekly via cron or manual trigger. Reads all `runtime/shadow_round_*.jsonl` from past 7 days, computes adjustments, writes to versioned `runtime/transition_matrix_vN.json` and `runtime/macro_weights_vN.json`.

### C. Macro Meta Loop (quarterly) — REQUIRES 90d DATA

Three audits:
1. **Structural Stress Audit** — capital survival probability, RoR stability, correlation resilience, black-swan response time
2. **Intelligence Drift Detection** — edge decay, strategy entropy, overfitting check
3. **Evolution Decision Matrix** — maintain / compress / add regime / retire agent / introduce sandbox experiment / adjust capital roadmap

**Critical constraint:** All upgrades pass through **Sandbox → Monte Carlo → Limited Deployment → Full Adoption** ladder.

---

## Section III — Meta-Consciousness Engine

System monitors itself via `SELF_STATE_VECTOR`:
- Stability Index
- Regime prediction entropy (already exposed in shadow round summary as `avg_regime_entropy_nats`)
- Allocation concentration risk (deferred)
- Drawdown volatility
- Learning acceleration rate
- Mutation frequency

**OBSERVATION MODE triggers** if instability detected:
- Reduced trade frequency
- Higher composite threshold
- No new structural experiments
- Increased simulation frequency

---

## Section IV — Evolution Speed Governor

`EVOLUTION_RATE ∈ [0–1]` based on:
- Data volume (more data → faster evolution permissible)
- Confidence stability (more confidence → faster)
- Stress test accuracy (Monte Carlo calibration vs realized)
- Drawdown stability

**Caps:**
- High EVOLUTION_RATE → cap structural changes
- Low EVOLUTION_RATE → permit controlled experimentation

---

## Section V — Research Direction Engine

Allocates research effort proportionally to:
```
research_priority_i = error_magnitude_i × capital_impact_i × confidence_deficit_i
```

Domains:
- Execution microstructure
- Regime classification improvement
- Slippage modeling refinement
- Agent architecture mutation
- Capital allocation optimization
- Macro feature expansion

---

## Section VI — Civilization Growth Model

Capital milestones tighten discipline:

| Capital | Behavior |
|---------|----------|
| $1K | Survival focus |
| $10K | Stability optimization |
| $100K | Allocation sophistication |
| $1M | Preservation priority |
| $10M | Sovereign risk discipline |
| $100M+ | Systemic resilience focus |

At each milestone:
- Kelly fraction tightens
- Exposure caps tighten
- Allocation concentration tightens
- Aggression unlock thresholds rise

**Rule:** More capital → more discipline.

Current state: pre-$1K (paper). All micro-test parameters from Spec #14 enforce $1K-survival-focus discipline.

---

## Section VII — Anti-Collapse Protocol (CIVILIZATION DEFENSE MODE)

Triggers:
- Consecutive regime mispredictions spike
- Monte Carlo tail error > threshold
- Risk of ruin rises
- DD acceleration detected

Actions:
- Freeze structural upgrades
- Compress risk globally
- Enter observation mode
- Increase simulation density
- Audit transition matrix

→ Aligned with existing auto-freeze logic in shadow_round.py (`check_auto_freeze`) and macro layer's PANIC mode.

---

## Section VIII — Meta-Learning Stack (4 isolated layers)

| Layer | Subject | Mapped to |
|-------|---------|-----------|
| 1 · Tactical | Entry/exit accuracy | shadow_round signal threshold tuning |
| 2 · Strategic | Regime anticipation | bayesian_regime transition matrix update |
| 3 · Allocation | Capital routing | (deferred — Spec #20 Part III) |
| 4 · Structural | Architecture itself | quarterly only, full audit ladder |

**Critical constraint:** Each layer isolated. No cross-layer chaos.

---

## Section IX — HARD CONSTITUTIONAL BOUNDARIES

Meta loop **CANNOT**:
- Override stop-loss logic
- Increase leverage above constitutional cap
- Remove risk compression
- Modify capital firewall
- Disable human override
- Bypass sandbox protocol

→ Same boundaries as `AI_DISCIPLINE_CONSTITUTION` Article 3. **Evolution permitted. Recklessness not.**

---

## Implementation Roadmap

| Phase | Component | Trigger |
|-------|-----------|---------|
| 1 | Micro meta loop (per-round calibration) | After shadow round v1.1 produces 5+ rounds of data |
| 2 | Round-history JSON aggregator | Day +7 (need a week of rounds) |
| 3 | Meso meta loop (weekly review) | Day +7-14 |
| 4 | Multi-agent allocator (Spec #20 Part III prerequisite) | Operator design decision |
| 5 | Macro meta loop (quarterly audit) | Day +90 |
| 6 | Civilization Defense Mode triggers | Day +14 (wire to existing freeze logic) |

**Current state:** Phase 0 — single shadow round runner with macro + Bayesian + Monte Carlo functional. Phases 1-6 build incrementally as data accumulates.

---

## Final declaration (verbatim)

> Shadow validates. Micro tests. Capital scales. Discipline compounds. Evolution governed.

---

## Cross-references

- `SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md` (#17) — base protocol that produces the data this loop consumes
- `PRODUCTION_READY_SHADOW_ENGINE_v1.md` (#18) — production bar
- `AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1.md` (#19) — macro layer feeds meta-evolution
- `BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md` (#20) — Bayesian/MC are the calibration targets
- `AI_DISCIPLINE_CONSTITUTION.md` — Articles 3, 6 — inviolable boundaries
- `MASTER_ARCHITECTURE_v2.0.md` — index
