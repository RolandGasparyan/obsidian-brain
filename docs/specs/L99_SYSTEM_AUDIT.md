# L99 System Audit — Post-Architecture Phase

**Type:** read-only system audit (Phase 1 of operator's 2026-05-02 directive)
**Date:** 2026-05-02
**Scope:** All 17 merged `champion/` modules across Layers 2/3/4/5 + existing Layer 1 tooling
**Discipline boundary:** observation only — NO module logic changes, NO parameter optimization, NO live wiring. Per directive: *"Optimize only after statistical validation."*

---

## Executive summary

The merged L99 stack contains **17 modules / ~5300 LOC / 449 tests** across 4 layers (Layer 1 ~75% covered by pre-existing 7-filter battery). The architecture is internally coherent, well-tested, and discipline-honest: every layer collapses to "do not trade" on null edge.

### Headline findings

| # | Finding | Severity | Layer |
|---|---|:---:|:---:|
| 1 | No live wiring exists from any module to `gateio_executor.py` — all 17 modules are dormant pending validated alpha | INFO | all |
| 2 | Two regime-classification systems coexist (`MasterRegimeOrchestrator` binary labels vs `RegimeProbabilityEstimator` 4-class softmax) without an explicit bridge | ⚠ medium | 2 + 5 |
| 3 | `RollingMetricsAggregator` in Layer 5 support and `RegimeExpectancyMatrix` in Layer 3 both compute (WR, AvgWin, AvgLoss, E, PF) over trade lists; partially redundant | ⚠ low | 3 + 5 |
| 4 | `champion/risk.py` (existing 5-Layer Risk Protocol) and new `PortfolioRiskGovernor` (Layer 5 §6) overlap on DD kill, daily/weekly limits, and circuit breakers | ⚠ medium | 5 |
| 5 | `KellySizer` is fully edge-dependent; with E ≤ 0 it returns 0.0 and is structurally inert — currently the most under-utilized component | ⚠ info | 3 |
| 6 | `EquityMonteCarloSimulator` is the only module that requires a list of historical R-outcomes; no pipeline yet wires trade history to it | ⚠ info | 3 |
| 7 | `RegimeValidator` requires 100+ observations of `(probabilities, forward_return, forward_vol)` triples; no pipeline yet collects this | ⚠ info | 2 |
| 8 | Phase 0 hypothesis template (per L99_RESEARCH_ROADMAP §0) does not exist as a wiki convention | 🛑 gap | research-ops |
| 9 | Lag-shift-±1 robustness (Phase 3 of roadmap) not implemented in 7-filter battery | 🛑 gap | 1 |
| 10 | Phase 5 stress wrapper (2× fees, 1.5× slip, 20% degrade, noise) not implemented | 🛑 gap | 1 |
| 11 | Phase 6 post-cutoff stability check (regime cut at 2021-01-01) not implemented | 🛑 gap | 1 |
| 12 | B.2.4 naming conflict between `PHASE_B_DECISION_TREE.md` and `L99_RESEARCH_ROADMAP.md` | ⚠ low | docs |

**Recommendations:** all are documentation / infrastructure-only and edge-independent. Zero recommendations involve module logic changes or parameter tuning. **No optimization without validated edge.**

---

## I. Layer-by-layer audit

### Layer 1 — Alpha Validation

**Existing (pre-L99-suite):**
- `microstructure_robust_check.py` — 7-filter battery (stationarity / WF / BH-FDR / bootstrap CI / vol-adjusted / monotonicity / concurrent-feature)
- `microstructure_signal_nature.py` — Q1-Q5 quintile + multi-fee scenarios
- `professional_backtest.py` — backtest harness with stats outputs
- `l99_validate.py` — 5-phase deployment gate
- `rsi2_validate.py` — 4-gate validator (used to reject RSI-2)

**Audit:**

| Component | Bottleneck | Redundancy | Over-constraint | Under-utilized |
|---|---|---|---|---|
| 7-filter battery | Bootstrap CI step is heavy (caused 30-min subprocess timeout in D6 binding) | None | Filter #4 bootstrap N=1000 may be over-budget for 5-day data | Already heavily used |
| signal_nature | Hardcoded fee scenarios (15/30/60 bps) — easy to extend | None | None | Could test more fee tiers |
| professional_backtest | Single-window only; no rolling WF wrapper at this layer | filter #2 also does rolling WF | None | Used per-strategy, not orchestrated |
| l99_validate | Phase ladder is conceptual — no live integration with bot status | Stage thresholds duplicated in CHAMPION_MODE.md | None | Not run as part of CI |

**Layer 1 verdict:** 75% of `L99_RESEARCH_ROADMAP` Phase 2/3/5/6 requirements covered. Gaps: lag-shift, stress wrapper, post-cutoff. All implementable without edge.

### Layer 2 — Regime Probability (PR #12 merged)

**Modules (5):** `regime_probability.py`, `regime_breadth.py`, `regime_liquidity.py`, `regime_transition.py`, `regime_validation.py`.

**Audit:**

| Component | Bottleneck | Redundancy | Over-constraint | Under-utilized |
|---|---|---|---|---|
| `RegimeProbabilityEstimator` | Softmax weights are hand-tuned defaults; ML-fit weights would require labeled training data | None | Linear scoring can't capture "mid-vol peak" naturally — workaround via `mid_vol_score` derived feature | Not yet wired to any data source |
| `MarketBreadthCalculator` | Requires per-pair feeds (caller wires multiple pairs) | None | `min_history_bars >= ma_window` is correct constraint | Not wired to existing `microstructure_collector.py` |
| `LiquidityStabilityCalculator` | CoV pivot 0.5 is hand-calibrated; no automatic re-fit | Spread already in microstructure_collector | None | Not wired |
| `RegimeTransitionTracker` | None | None | Symmetric threshold (any regime > 0.30) — could be asymmetric | Useful as logging-only diagnostic |
| `RegimeValidator` | Requires 100+ observations to validate; would take weeks of paper data | None | Strict accept/reject — "insufficient_data" is third state | Cannot run validation until B.2.3 produces enough data |

**Layer 2 verdict:** internally consistent but currently DEAD because:
- `RegimeProbabilityEstimator.estimate()` requires `RegimeFeatures` (8 inputs) — only 4 of 8 are wired today (vol, spread, BTC trend, delta from microstructure_collector); breadth/liquidity/atr_expansion/volume_pct require new wiring
- Even fully wired, output goes nowhere live (no caller invokes it)

### Layer 3 — Capital Mathematics (PR #11 merged)

**Modules (4):** `kelly_sizer.py`, `equity_mc_sim.py`, `growth_projector.py`, `regime_expectancy_matrix.py`.

**Audit:**

| Component | Bottleneck | Redundancy | Over-constraint | Under-utilized |
|---|---|---|---|---|
| `KellySizer` | Returns 0.0 when E ≤ 0 — structurally inert pre-edge | None | Quarter Kelly + 1% cap are conservative-correct; no over-constraint | Cannot fire pre-edge |
| `EquityMonteCarloSimulator` | Requires historical R-outcome list (10+ trades min); no pipeline supplies it | None | None | Not wired to trade history |
| `GrowthProjector` | None — pure math | None | Variance haircut 40% is mid-spec band; could be parameterized further | Not connected to any input source |
| `RegimeExpectancyMatrix` | Requires (regime_label, signal_id, r_multiple) tuples — no pipeline supplies | partial overlap with `RollingMetricsAggregator` (both compute WR/E/PF) | min_trades=30 default may be too high for short-history regimes | Not yet populated |

**Layer 3 verdict:** all 4 modules are pure-math libraries waiting for input data. They cannot fire pre-edge.

### Layer 4 — Compounding Velocity (PR #13 merged)

**Modules (4):** `velocity_state_machine.py`, `velocity_score.py`, `anti_overcompounding.py`, `stair_step_compounder.py`.

**Audit:**

| Component | Bottleneck | Redundancy | Over-constraint | Under-utilized |
|---|---|---|---|---|
| `VelocityStateMachine` | None | None | ACCELERATION requires 5 simultaneous gates (PF, DD, trades, IC stable, EXPANSION); ~impossible without years of stable edge | Locked in CONSERVATIVE permanently |
| `VelocityScoreCalculator` | DD=0/Var=0 epsilon substitution gives huge VS for zero-volatility cases — caller must understand this | None | Reduction factor 0.5 is fixed; no graduated reduction | Cannot fire pre-edge |
| `AntiOvercompoundingMonitor` | None | partial overlap with `PortfolioRiskGovernor` daily/weekly R limits | Cooldown=10 trades is fixed | Will fire on any 3-loss streak in production |
| `StairStepCompounder` | None | None | None | Cannot trigger pre-edge (no equity growth) |

**Layer 4 verdict:** state machine is permanently in CONSERVATIVE; the rest of the layer is logically downstream of state transitions that won't happen pre-edge.

### Layer 5 — Hybrid Portfolio (PRs #9, #10 merged)

**Modules (4):** `portfolio_risk_governor.py`, `master_regime_orchestrator.py`, `drift_protection.py`, `rolling_metrics.py`.

**Audit:**

| Component | Bottleneck | Redundancy | Over-constraint | Under-utilized |
|---|---|---|---|---|
| `PortfolioRiskGovernor` | None | overlaps existing `champion/risk.py` 5-Layer Risk Protocol on DD kill + daily limits | Hard caps are spec-correct; not over-constrained | Not wired to live executor |
| `MasterRegimeOrchestrator` | Binary regime label (HIGH_VOL/TRENDING/LOW_VOL/NORMAL) — less granular than `RegimeProbabilityEstimator` 4-class output | partial overlap with `RegimeProbabilityEstimator` | Threshold 0.80 vol = HIGH_VOL is hardcoded | Not wired |
| `DriftProtectionEngine` | Sticky disable requires manual `reset()` — no auto-recovery | partial overlap with `champion/risk.py` daily/weekly DD escalation | None | Not wired |
| `RollingMetricsAggregator` | None | partial overlap with `RegimeExpectancyMatrix` | Window default 50 may be too short for stable PF | Cannot fire pre-trade-history |

**Layer 5 verdict:** all 4 modules are dormant. `PortfolioRiskGovernor` and `champion/risk.py` need explicit reconciliation when edge appears (which to use authoritative).

---

## II. Cross-layer composition audit

### Composition pipeline (theoretical, dormant)

```
[microstructure_collector] → [microstructure_robust_check (7-filter)] → [Candidate Alpha?]
                                                                              │
                                                              ┌───────────────┘
                                                              │
       ┌──────────────────────────────────────────────────────┼──────────────────────────────────┐
       │                                                      │                                  │
       ↓                                                      ↓                                  ↓
[regime_probability]                              [regime_expectancy_matrix]                [rolling_metrics]
       │                                                      │                                  │
       ↓ P(R1..R4)                                            ↓ best_cell                        ↓ RollingMetrics
[exposure_multiplier]                                  [kelly_sizer]                      [velocity_state_machine]
       │                                                      │                                  │
       └──────────────────────┬───────────────────────────────┴──────────────────────────────────┘
                              ↓
                  [velocity_score / anti_overcompounding / stair_step]
                              ↓
                  [portfolio_risk_governor.approve_new_position]
                              ↓
                  [LIVE EXECUTOR — BLOCKED until validated edge]
```

### Cross-layer issues

| Issue | Severity | Layers |
|---|:---:|:---:|
| **Two regime systems** — `MasterRegimeOrchestrator` (Layer 5, binary labels) and `RegimeProbabilityEstimator` (Layer 5 input via Layer 2, 4-class softmax) | ⚠ medium | 2 + 5 |
| **Two stats aggregators** — `RollingMetricsAggregator` (Layer 5 support, fixed window) and `RegimeExpectancyMatrix` (Layer 3, append-only by regime) | ⚠ low | 3 + 5 |
| **Two risk layers** — `champion/risk.py` (existing, Patches 1+3+5) and `PortfolioRiskGovernor` (Layer 5 §6) | ⚠ medium | 5 |
| **No driver script** — no Python entrypoint composes the layers end-to-end | 🛑 gap | all |

### Two regime systems (issue #2)

`MasterRegimeOrchestrator` was implemented from L99_HYBRID_PORTFOLIO §5 spec (PR #10) as a 4-state classifier (DISABLED_BY_DRIFT / HIGH_VOL / TRENDING / LOW_VOL / NORMAL) with binary thresholds.

`RegimeProbabilityEstimator` was implemented from L99_REGIME_PROBABILITY §3 spec (PR #12) as a 4-class softmax (DEAD / NORMAL / EXPANSION / HIGH_IMPULSE).

These are **different regime taxonomies**. Both have legitimacy:
- Orchestrator's binary labels are simpler and easier to reason about
- Probability estimator gives richer information for sizing decisions

**Resolution path (do NOT implement now):** when wiring goes live, the probability estimator should be the authoritative source and the orchestrator's `evaluate()` should consume the most-likely regime label as an input alongside binary trend/volatility features. This is documented in `wiki/findings/2026-05-01-l99-quant-suite-summary.md` already.

### Two stats aggregators (issue #3)

| Module | Aggregation | Window | Per-regime |
|---|---|---|---|
| `RollingMetricsAggregator` | Fixed window (default 50) | rolling | No |
| `RegimeExpectancyMatrix` | Append-only | unbounded | Yes |

These serve different use cases:
- RollingMetrics → drift protection (recent stability)
- RegimeExpectancyMatrix → Kelly inputs (long-run per-regime)

Not actually redundant; just overlapping on the surface. **No action needed.**

### Two risk layers (issue #4)

`champion/risk.py` (existing):
- 5 layers per CHAMPION_MODE.md §V (Trade / Daily / Weekly / Stage regression / Systemic)
- Daily 5% DD pause; 3-consec-loss-day -25% size; weekly negative -25% next week; -10% week 48h pause; -15% peak min size; BTC -20%/7d HALTED
- State enum: NORMAL / SIZE_REDUCED_DAILY / SIZE_REDUCED_WEEK / PAUSED_DAILY / PAUSED_WEEK_HARD / MIN_SIZE_DD15 / HALTED_SYSTEMIC

`PortfolioRiskGovernor` (Layer 5 §6, new):
- Caps + circuit breakers + DD kill switch
- 8% total exposure / 1.2% per position / 4% per sector / 3R daily / 6R weekly / 25% DD kill
- Boolean state: `kill_switch` + `cooldown_remaining`

**These overlap.** When wiring goes live, the project must decide which is authoritative. Options:

1. **Replace `champion/risk.py` with PortfolioRiskGovernor** — simpler but loses the existing 7-state machine
2. **Use `champion/risk.py` for state-machine logic + PortfolioRiskGovernor for hard caps** — composable; needs explicit ordering
3. **Use both with a clear precedence** — governor's kill_switch is terminal; risk.py's enum overlays

**No action now.** Documented for post-edge wiring decision.

### No driver script (issue #4)

There is no `run_l99_pipeline.py` or similar that composes:

```
RollingMetricsAggregator → RegimeProbabilityEstimator → DriftProtection
   → MasterRegimeOrchestrator → KellySizer → VelocityStateMachine
   → AntiOvercompoundingMonitor → StairStepCompounder → PortfolioRiskGovernor
```

All 17 modules are linked only by tests + import statements. **This is correct for pre-edge state** — a driver script would imply readiness for live wiring, which the discipline framework forbids.

When edge is validated, a driver script is the LAST piece to write before paper deployment. Document that explicitly.

---

## III. Efficiency Map (per directive)

### Edge-discovery efficiency

| Activity | Time spent | Time efficient? |
|---|---|:---:|
| Architecture (5 PRs, 17 modules, ~5300 LOC) | 2 days | ⚠ inefficient relative to edge value |
| Validation infrastructure (7-filter battery) | days, predates this session | ✅ |
| Edge research (microstructure cycle = D6 NO-GO) | 5+ days | ✅ produced definitive null result |
| On-chain research (B.2.3) | blocked on API keys | n/a |

**Efficiency observation:** the architecture phase consumed substantial time relative to its current utility (zero — all modules dormant). This is the operator's own diagnosis in L99_RESEARCH_ROADMAP: *"Architecture is finished. Now only two outcomes exist."*

The rational allocation going forward:
- **0%** new architecture
- **100%** edge research per Phase 7 of roadmap

### Code efficiency (existing modules)

All 17 new modules are O(N) or better in trade count. No quadratic algorithms. No unbounded memory. No I/O in hot paths.

Heaviest computational module: `EquityMonteCarloSimulator.simulate()` — O(N × M) where N=simulations (default 1000), M=trades. For 1000 sims × 50 trades = 50,000 multiplications + comparisons. Sub-second.

**No efficiency bottlenecks at the module level.**

---

## IV. Risk Map (per directive)

### Edge-independent risks (active now)

| Risk | Severity | Mitigation |
|---|:---:|---|
| Operator wires layers live before edge proof | 🔴 high | discipline framework + CLAUDE.md + ADR-001; agent refuses |
| Operator pastes another spec demanding immediate implementation | ⚠ medium | this audit + roadmap codify "no more layers" rule |
| API keys provided + collected data has bugs (collector untested at scale) | ⚠ medium | onchain_collector has 13/13 unit tests; validate parquet schema in first 60 min |
| Cost overrun on free-tier API limits | ⚠ low | rate-limit awareness in collector; documented in PR #6 |
| Existing live bots (Vote ensemble) bleed equity below circuit-breaker | 🔴 high | Patch 3 fired correctly on ETH 2026-04-30; production_monitor JSON parser fixed |

### Edge-dependent risks (latent, fire on live wiring)

| Risk | Severity if live | Likelihood pre-validation |
|---|:---:|:---:|
| KellySizer over-sizes on noisy IC | 🔴 catastrophic | high (without rolling-50 stability gate) |
| RegimeProbabilityEstimator miscalibrated weights → wrong exposure | ⚠ medium | medium |
| AntiOvercompoundingMonitor cooldown=10 too short for real edge decay | ⚠ low | low |
| Two risk layers (`risk.py` + Governor) interact unexpectedly | ⚠ medium | medium (no integration test exists) |
| Production_monitor doesn't track L99 layer health | ⚠ low | n/a (no live deploy) |

### Risk surface conclusion

The current risk surface is **almost entirely edge-independent**. Live wiring would activate the second table immediately. **No live wiring should happen without validated edge AND an explicit integration test for the two-risk-layer interaction.**

---

## V. Edge Activation Map (per directive)

What does each layer need to "fire" (transition from dormant → active)?

### Layer 1 (Alpha Validation)
- **Active path to fire:** receive real factor data → run 7-filter battery → output verdict
- **Currently:** ✅ already fires on each microstructure dataset; will fire on B.2.3 on-chain data when keys arrive
- **Activation requirements:** none beyond data availability

### Layer 2 (Regime Probability)
- **Active path to fire:** receive `RegimeFeatures` (8 inputs) → estimate → consume probabilities for sizing
- **Currently:** dormant
- **Activation requirements:**
  1. Wire 4 missing features (atr_expansion, volume_percentile, market_breadth, liquidity_stability) into microstructure_collector or a feature-engineering script
  2. Validate softmax weights on labeled data (Phase 8 of roadmap = post-edge calibration)
  3. Activate downstream consumer (sizing pipeline)

### Layer 3 (Capital Mathematics)
- **Active path to fire:** receive (WR, AvgWin, AvgLoss) → compute Kelly → return risk fraction > 0
- **Currently:** dormant (returns 0.0 because E ≤ 0 in all data classes seen)
- **Activation requirements:**
  1. Validated edge from B.2.3 or other B-prime branch
  2. Rolling-50 stability gate via RollingMetricsAggregator
  3. Sample size ≥ 30 trades per `RegimeExpectancyMatrix.best_cell()` default

### Layer 4 (Compounding Velocity)
- **Active path to fire:** state machine transitions out of CONSERVATIVE
- **Currently:** locked in CONSERVATIVE
- **Activation requirements (per spec §2):**
  1. PF ≥ 1.3 sustained → BASELINE
  2. PF ≥ 1.6 + DD < 8% + trades ≥ 200 + IC stable + EXPANSION regime → ACCELERATION

### Layer 5 (Risk Infrastructure)
- **Active path to fire:** approve/reject incoming position requests
- **Currently:** governor accepts requests, but no caller exists
- **Activation requirements:**
  1. Driver script that calls `governor.approve_new_position()` before each trade
  2. Reconciliation with existing `champion/risk.py`

---

## VI. Bottlenecks identified

### Bottleneck #1 — D6 binding subprocess timeout (already known)

`d6_final_run.py` invoked `microstructure_robust_check.py` via subprocess with 30-min timeout. On 5-day data, the bootstrap CI step (filter #4) exceeded this. Resulted in 3× auto-trigger failure on 2026-04-30.

**Status:** documented in `wiki/log.md`. Manual run completed in ~54 min. **Recommended fix (post-PR):** raise subprocess timeout to 90 min OR disable bootstrap CI for span > 100h (use bootstrap only on shorter samples).

### Bottleneck #2 — No live data feeding any L99 module

All 17 modules wait for input pipelines that don't exist yet. `RegimeFeatures` requires 8 inputs; only 4 are computable from current `microstructure_collector`. Layer 5 `PortfolioRiskGovernor.update_equity()` would need a live equity poller.

**Status:** intentional. Pipelines are post-edge work.

### Bottleneck #3 — `RegimeExpectancyMatrix` has no input

The matrix wants `(regime_label, signal_id, r_multiple)` tuples. Today's bot trades produce `(symbol, side, pnl)` only. There's no signal-id taxonomy and no regime-labeling-at-entry.

**Status:** post-edge work. Document required schema additions.

---

## VII. Redundant logic identified

| Pair | Overlap | Action |
|---|---|---|
| `RollingMetricsAggregator` ↔ `RegimeExpectancyMatrix` | Both compute WR/E/PF | Different scope (rolling vs append-only); keep both |
| `MasterRegimeOrchestrator` ↔ `RegimeProbabilityEstimator` | Different regime taxonomies | Reconcile at live-wiring time |
| `champion/risk.py` ↔ `PortfolioRiskGovernor` | DD kill, daily/weekly limits | Reconcile authoritativeness at live-wiring time |
| `AntiOvercompoundingMonitor` daily/weekly R ↔ `PortfolioRiskGovernor` daily/weekly R | Same triggers | One should defer to the other; document at live-wire |

**No action now.** All redundancies are at the conceptual layer; modules are correctly isolated and don't conflict at the test level (449 tests pass).

---

## VIII. Over-constraint identified

| Constraint | Where | Justification | Should it relax? |
|---|---|---|:---:|
| ACCELERATION requires 5 simultaneous gates | velocity_state_machine §2 | Operator spec | No |
| Quarter Kelly + 1% absolute cap | kelly_sizer §1.2 | Operator spec | No |
| Min trades = 30 for `best_cell()` | regime_expectancy_matrix | L99_ALPHA_VALIDATION §2.3 spec | No |
| Min observations = 100 for `RegimeValidator` | regime_validation §8 | Spec default | Possibly relax to 50 for B.2.3 (short data history) |
| PortfolioRiskGovernor 8% total / 1.2% per position | spec | L99_HYBRID §6 | No |

**No over-constraints.** All thresholds are spec-derived. Recommend NO relaxation pre-edge — that would be drift.

---

## IX. Under-utilized components

All 17 new modules are 0% utilized live (no caller). Most-utilized in tests:

| Module | Test invocations |
|---|---:|
| `PortfolioRiskGovernor` | 44 + integration |
| `RegimeProbabilityEstimator` | 16 + integration |
| `KellySizer` | 21 + integration |

Least-utilized in tests (still 0% live):

| Module | Test invocations |
|---|---:|
| `growth_projector` | 14 |
| `regime_breadth` | 12 |
| `regime_liquidity` | 10 |
| `regime_transition` | 12 |

**Observation:** test coverage is approximately equal. The "under-utilization" is at the runtime level, not the test level. **No action needed pre-edge.**

---

## X. Capital inefficiencies (theoretical, since no capital deployed)

Per directive, we model what capital inefficiencies would look like if the L99 stack were active today:

1. **Vote ensemble paper bot bleeds equity** (-2.40% over 7 days) → real opportunity cost ~$5/day on $200 starting capital. Currently absorbed without protection beyond Patch 3 circuit breaker.

2. **No yield on idle USDT** during the research-only phase. If $200 sat in a stablecoin yield protocol at 5% APR, that's ~$0.027/day of foregone yield. Negligible at this capital level. Not worth deploying yield infrastructure pre-edge.

3. **API costs (zero today)** — free tier on all data sources. No inefficiency.

4. **VPS cost** — fixed ($5–6/mo) regardless of utilization. With 17 dormant modules, ~$0.30/module/month. Acceptable overhead for post-edge readiness.

**Verdict:** no capital inefficiencies actionable pre-edge. The dominant inefficiency is Vote ensemble paper losses, which is the exact scenario the L99 governor was built for. Once edge appears, that scenario flips from "untrapped loss" to "validated drawdown within budget".

---

## XI. Recommendations (read-only — no action without explicit operator request)

### Edge-independent (implementable now if operator requests)

| # | Recommendation | LOC | Priority |
|---|---|---:|:---:|
| R1 | Phase 0 hypothesis template (`wiki/research-log/_template.md` + README) | ~80 | high |
| R2 | Lag-shift-±1 robustness check in `microstructure_robust_check.py` | ~50 | high |
| R3 | Phase 5 stress wrapper (2× fees / 1.5× slip / 20% degrade / noise) | ~150 | medium |
| R4 | Phase 6 post-cutoff stability check (regime cut at 2021-01-01) | ~80 | medium |
| R5 | B.2.4 naming reconciliation in `PHASE_B_DECISION_TREE.md` | ~30 | low |

This PR includes **R1 only** (Phase 0 template). R2-R5 are documented gaps for separate PRs on operator request.

### Edge-dependent (do NOT implement until validated alpha exists)

| # | Recommendation | Trigger |
|---|---|---|
| R6 | Reconcile `champion/risk.py` ↔ `PortfolioRiskGovernor` authority | First live-wiring proposal |
| R7 | Reconcile `MasterRegimeOrchestrator` ↔ `RegimeProbabilityEstimator` | First live-wiring proposal |
| R8 | Build driver script (`run_l99_pipeline.py`) | First Stage 1 paper deployment |
| R9 | Wire 4 missing `RegimeFeatures` (atr_expansion, volume_pct, breadth, liquidity) | When data sources exist |
| R10 | Tune Softmax weights from labeled data | Post-edge (need positive examples per regime) |

**No edge-dependent recommendations are actionable today.**

---

## XII. Research roadmap interaction

This audit complements `L99_RESEARCH_ROADMAP.md` (PR #14):
- The roadmap defines the procedure
- This audit defines the current state

Together, they establish the **immediate next action**: deliver the 3 API keys → execute one research cycle per the roadmap → verdict in ~2 weeks.

---

## XIII. Sources

- All 17 merged `champion/` modules
- `microstructure_*.py` family (existing Layer 1)
- `champion/risk.py` (existing 5-Layer Risk Protocol)
- `docs/specs/L99_RESEARCH_ROADMAP.md` (companion in PR #14)
- `docs/specs/L99_*.md` (all 5 layer specs)
- `wiki/log.md` and prior findings
- Operator directive 2026-05-02 (full-system audit instruction)

## Final discipline statement

**This audit changed zero module logic. Zero parameter values. Zero live wiring.**

Per directive: *"Optimize only after statistical validation."* The 17 merged modules remain dormant pending validated edge from a B-prime research branch. The architecture phase is closed.

The operator's roadmap states: *"No more layers. No more complexity. Only evidence."*

This audit is consistent with that rule. Recommended next step: deliver the 3 API keys.
