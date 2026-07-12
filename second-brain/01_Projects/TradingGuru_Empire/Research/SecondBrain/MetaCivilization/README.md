---
type: meta-civilization-index
date: 2026-05-13
tags: [meta-loop, evolution, micro, meso, macro, civilization-defense]
ai-first: true
source: ~/Desktop/agent/governance/META_CIVILIZATION_LOOP_v1.md
---

# Meta-Civilization Loop

> For future Claude: 3-cycle evolution structure. The Micro loop calibrates each round. The Meso loop tunes weekly. The Macro loop audits quarterly. **Each loop can ONLY adjust within Constitution Article 4 mutation boundaries** — never risk caps, stop-losses, kill switches, or governance firewall.

---

## The 3 Cycles

### Micro Loop (per round · IMPLEMENTABLE NOW)

**Cadence:** end of each 90-min shadow round

**Inputs:**
- Realized R vs Modeled R deviation
- Risk compression accuracy
- Macro-regime anticipation accuracy
- Agent allocation efficiency (deferred — needs Spec #20 Part III)
- Monte Carlo calibration error

**Output:** `META_PERFORMANCE_SCORE` (0-100)

**Actions if deviation > threshold:**
- Reduce aggression globally (`base_aggression *= 0.9`)
- Carry forward weighted posterior into next round
- Recalibrate slippage model

**Constraint:** Calibration only. No structural rewrite at micro level.

**Build status:** Wireable as `paper_battle/meta_loop_micro.py` — reads round summary JSON, writes `runtime/calibration.json` for next round.

---

### Meso Loop (weekly · REQUIRES 7d DATA)

**Cadence:** weekly (or 7-day equivalent)

**Inputs:** 7 days of trade logs (JSONL) + round summaries

**System asks:**
1. Which regime transitions were mispredicted?
2. Which agents underperformed expectation?
3. Was Kelly compression sufficient?
4. Did Monte Carlo under/overestimate tail risk?

**Outputs:**
- Update transition matrix probabilities (bounded ±10%/week)
- Update macro weight coefficients
- Update agent regime-performance vectors
- Reweight feature importance in composite scoring

**Build status:** Deferred — needs longitudinal data. Implementation as `paper_battle/meta_loop_meso.py`.

---

### Macro Loop (quarterly · REQUIRES 90d DATA)

**Cadence:** quarterly (or 90-day equivalent)

**Three audits:**
1. **Structural Stress Audit** — capital survival probability, RoR stability, correlation resilience, black-swan response time
2. **Intelligence Drift Detection** — edge decay, strategy entropy, overfitting check
3. **Evolution Decision Matrix** — maintain / compress / add regime / retire agent / introduce sandbox experiment / adjust capital roadmap

**Mandatory ladder:** All upgrades pass through **Sandbox → Monte Carlo → Limited Deployment → Full Adoption.**

**Build status:** Deferred — needs 13+ weeks of data.

---

## Self-Observation (SELF_STATE_VECTOR)

System monitors itself via:
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

## Evolution Speed Governor

`EVOLUTION_RATE ∈ [0–1]` based on:
- Data volume → more data, faster evolution permissible
- Confidence stability → more confidence, faster
- Stress test accuracy → MC calibration vs realized
- Drawdown stability

**Caps:**
- High EVOLUTION_RATE → cap structural changes
- Low EVOLUTION_RATE → permit controlled experimentation

---

## Civilization Growth Model

| Capital | Behavior |
|---------|----------|
| $1K | Survival focus |
| $10K | Stability optimization |
| $100K | Allocation sophistication |
| $1M | Preservation priority |
| $10M | Sovereign risk discipline |
| $100M+ | Systemic resilience focus |

**Rule:** More capital → more discipline.

At each milestone:
- Kelly fraction tightens
- Exposure caps tighten
- Allocation concentration tightens
- Aggression unlock thresholds rise

Current state: **$1K Survival Focus** (paper-only with even stricter sub-caps per Spec #14 micro-test).

---

## Anti-Collapse Protocol (CIVILIZATION DEFENSE MODE)

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

→ Aligned with existing auto-freeze logic + macro layer's PANIC mode.

---

## 4-Layer Meta-Learning Stack

| Layer | Subject | Mapped to |
|-------|---------|-----------|
| 1 · Tactical | Entry/exit accuracy | shadow round signal threshold tuning |
| 2 · Strategic | Regime anticipation | bayesian_regime transition matrix update |
| 3 · Allocation | Capital routing | (deferred — Spec #20 Part III) |
| 4 · Structural | Architecture itself | quarterly only, full audit ladder |

**Critical:** Each layer isolated. No cross-layer chaos.

---

## Constitutional Article 4 Mutation Boundaries

Meta loop **CANNOT**:
- Override stop-loss logic
- Increase leverage above constitutional cap
- Remove risk compression
- Modify capital firewall
- Disable human override
- Bypass sandbox protocol

→ Same boundaries as [[Governance/README#The 6-Article Constitution]] Article 3-4.

---

## Cross-links

- [[Architecture/README]] — Layer 4 in 5-sovereign model
- [[Governance/README]] — Article 4 mutation boundaries
- [[ExecutionEngine/README]] — shadow round generates the data this loop consumes
- [[RegimeModels/README]] — transition matrix is the Meso loop's update target
- [[MonteCarlo/README]] — MC calibration is the Macro loop's audit target

## Source-of-truth

- `~/Desktop/agent/governance/META_CIVILIZATION_LOOP_v1.md` (spec #21)
- `~/Desktop/agent/governance/SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER_v1.md` (spec #22)
