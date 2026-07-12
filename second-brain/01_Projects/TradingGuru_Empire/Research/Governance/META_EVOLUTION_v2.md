# META_EVOLUTION_DEEP_RESEARCH_ENGINE v2.0

**Operator-authored:** 2026-05-13 (spec #2)
**Status:** ACCEPTED · partial engine implementation (functions written, output exposure pending)
**Layer:** L14 (Meta-Evolution Deep Layer)

---

## Purpose

Transform from "self-learning trading engine" → "self-researching adaptive intelligence laboratory."
The system studies itself, questions its edge, validates hypotheses, prevents strategic decay.

---

## Section I — Meta Observation Layer

**Implementation:** `compute_meta_health()` in `paper_battle_engine.py`

Tracked variables:
- Rolling 50 trade performance
- Rolling 200 trade baseline
- Regime-specific win rate
- Signal precision decay
- R-multiple stability
- Drawdown clustering index
- Overconfidence drift
- Aggression creep
- Volatility sensitivity variance

Output: `meta_health_score ∈ 0-100`

If `meta_health_score < 60` → enter **Observation Mode**:
- Reduce adaptive shifts
- Suspend upgrades
- Increase data collection window
- Freeze parameter mutations

---

## Section II — Edge Decay Detection

**Implementation:** `detect_edge_decay()` in engine.

4 trigger conditions:
1. `rolling_50_return < rolling_200_return`
2. `win_rate_drop > 10%`
3. `risk_adjusted_return < baseline_threshold`
4. `volatility_regime_mismatch_detected`

| Triggers | Warning level | Action |
|----------|---------------|--------|
| 2+ | Level 1 | Heightened monitoring |
| 3+ | Level 2 | Sandbox testing mandatory |
| 4 | Quarantine | Paper-only · live disabled · research priority escalated |

---

## Section III — Sandbox Research Lab

**Status:** Spec'd · paper engine itself functions as sandbox · no separate sandbox process yet

Rules:
- Isolated simulation only
- No live capital
- No cross-layer mutation
- Min 200 simulated trades
- Must outperform baseline by >10%
- DD must remain < baseline

Hypothesis examples: adjust breakout filter weight, add volatility compression modifier, change confirmation window, regime-dependent threshold.

If validated → Controlled Experiment Phase (parallel to main logic).

---

## Section IV — Adaptive Intelligence Control

**Implementation:** `LEARNING_DELTA_CAP = 0.15` enforced in `self_learning_update()`.

| Parameter | Cap |
|-----------|-----|
| Threshold sensitivity | ±15% |
| Aggression coefficient | ±15% |
| Regime weighting | ±15% |
| Trade frequency bias | ±10% |

Hard locked (NEVER modifiable):
- Core entry logic
- Core exit logic
- Risk per trade caps
- Capital governance rules

---

## Section V — Meta Consciousness Engine

**Implementation:** `detect_behavioral_drift()` + `apply_drift_correction()`.

Drift triggers:
- Aggression increasing without performance gain
- Trade frequency increasing while precision dropping
- Drawdown duration expanding
- Recovery time increasing

Response (bounded):
- Reduce aggression 5%
- Increase confirmation filter
- Extend cooldown window (signal only)
- Elevate discipline weighting (signal only)

---

## Section VI — Research Priority Queue

**Implementation:** `compute_research_priority_queue()` — top 2 active per cycle.

Priorities in order:
1. Edge decay detection
2. Regime inefficiency
3. Volatility misalignment
4. Execution latency inefficiency
5. Parameter overfitting risk

---

## Section VII — Knowledge Evolution Score

**Implementation:** `compute_knowledge_maturity()` per agent.

Range: `1.0 – 1.5`

Increases on:
- Validated improvements integrated
- Edge stable across regimes
- Drawdown compression
- Volatility adaptation

`final_score = base_score × evolution_multiplier × knowledge_maturity_factor`

---

## Section VIII — Long Cycle Strategy Review

**Implementation:** `long_cycle_review()` — every 1000 total trades across roster.

Outputs:
- Research Summary Report
- Upgrade Recommendations
- Stability Forecast

---

## Section IX — Safety Constraints

Meta engine **CANNOT**:
- Deploy unvalidated strategy live
- Increase risk caps
- Bypass governance
- Alter capital router rules
- Override emergency halt

---

## Cross-references

- `MASTER_ARCHITECTURE_v2.0.md` — index
- `LAYER_DISCIPLINE.md` — 5-gate strategic lock
- `paper_battle/paper_battle_engine.py` — implementation
