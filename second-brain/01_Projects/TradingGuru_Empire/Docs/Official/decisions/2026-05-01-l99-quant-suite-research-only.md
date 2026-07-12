# 2026-05-01 — L99 Quant Suite (4 specs): research only, library modules implementable, engines gated by edge proof

**Type:** decision
**Status:** decided · 4 specs preserved · library modules implementable pre-edge-proof · live engine wiring forbidden until B.2.3 produces validated edge
**Linked log entry:** [[log#2026-05-01-l99-quant-suite-research-only]]

## Context

Following yesterday's L99_HYBRID_PORTFOLIO_GOD_MODE spec, operator pasted four additional specs in rapid succession on 2026-05-01:

1. [docs/specs/L99_ALPHA_VALIDATION.md](../../docs/specs/L99_ALPHA_VALIDATION.md) — Formal Alpha Validation + Realistic Expectancy Model
2. [docs/specs/L99_CAPITAL_MATHEMATICS.md](../../docs/specs/L99_CAPITAL_MATHEMATICS.md) — Kelly Constrained Sizing + Regime Expectancy + Growth Projection
3. [docs/specs/L99_COMPOUNDING_VELOCITY.md](../../docs/specs/L99_COMPOUNDING_VELOCITY.md) — Compounding Velocity Optimizer
4. [docs/specs/L99_REGIME_PROBABILITY.md](../../docs/specs/L99_REGIME_PROBABILITY.md) — Dynamic Regime Probability Estimator

Combined with yesterday's [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](../../docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md), these form a complete five-layer institutional quant stack:

```
┌─────────────────────────────────────────────────┐
│ Layer 5: PORTFOLIO ARCHITECTURE                  │  L99_HYBRID_PORTFOLIO_GOD_MODE
│         (multi-engine orchestration)             │
├─────────────────────────────────────────────────┤
│ Layer 4: COMPOUNDING / VELOCITY                  │  L99_COMPOUNDING_VELOCITY
│         (state machine: CONSERVATIVE/BASE/ACCEL) │
├─────────────────────────────────────────────────┤
│ Layer 3: CAPITAL MATH                            │  L99_CAPITAL_MATHEMATICS
│         (Kelly + ruin formula + growth proj.)    │
├─────────────────────────────────────────────────┤
│ Layer 2: REGIME INTELLIGENCE                     │  L99_REGIME_PROBABILITY
│         (probabilistic regime distribution)      │
├─────────────────────────────────────────────────┤
│ Layer 1: ALPHA VALIDATION                        │  L99_ALPHA_VALIDATION
│         (IC, OOS, fee-adjusted edge gate)        │
└─────────────────────────────────────────────────┘
```

Each layer feeds the next. Layer 1 is the gating layer — without a Candidate Alpha there, layers 2–5 have nothing to operate on.

## Choice

**Save all 4 specs verbatim. Document mapping per spec. Permit pre-edge-proof implementation of pure-math library modules. Forbid live engine wiring until B.2.3 produces validated edge per Layer 1.**

Specifically:

- ✅ Save 4 spec files verbatim under `docs/specs/`
- ✅ Per-spec mapping (Section III of each file) to existing tooling
- ✅ Per-spec gap analysis (Section V of each file) listing pure-math modules implementable now
- ✅ Per-spec prohibition list (Section VI of each file) blocking premature live wiring
- 🛑 NOT implementing engines on `main`
- 🛑 NOT activating Layer 4 ACCELERATION mode
- 🛑 NOT scaling capital pre-Stage-1
- 🛑 NOT skipping any rolling-50 / rolling-200 thresholds

## What CAN be built pre-edge-proof (across all 4 specs)

Pure-math library modules that work on synthetic data and don't touch live exchange APIs:

| Module | From spec | LOC | Purpose |
|---|---|---:|---|
| `kelly_sizer.py` | Capital Math V.1 | ~150 | Constrained-Kelly fraction with caps |
| `equity_mc_sim.py` | Capital Math V.3 | ~200 | Monte Carlo on trade orderings |
| `growth_projector.py` | Capital Math V.4 | ~100 | Realistic monthly return estimator |
| `regime_expectancy_matrix.py` | Capital Math V.2 + Alpha Val V.1 | ~250 | (regime × signal) WR/E/PF |
| `velocity_state_machine.py` | Compounding V.1 | ~150 | CONSERVATIVE/BASELINE/ACCELERATION |
| `velocity_score.py` | Compounding V.2 | ~80 | VS computation + scaling action |
| `anti_overcompounding.py` | Compounding V.3 | ~120 | 3-loss / daily-3R / weekly-6R triggers |
| `stair_step_compounder.py` | Compounding V.4 | ~100 | Reset-to-baseline staircase model |
| `regime_probability.py` | Regime Prob V.1 | ~250 | Softmax baseline regime estimator |
| `regime_breadth.py` + `regime_liquidity.py` | Regime Prob V.2 | ~300 | Missing input features |
| `regime_transition.py` | Regime Prob V.3 | ~100 | ΔP(R3), ΔP(R4) tracker |
| `regime_validation.py` | Regime Prob V.4 | ~200 | Calibration diagnostics |

**Total:** ~2000 LOC across 12 modules. All synthetic-data unit-testable. Build only on user request and only one at a time.

## What MUST NOT be built (across all 4 specs)

🛑 Live position sizing using `kelly_sizer.py` on null-edge Vote ensemble — Layer 1 reject blocks this
🛑 Live state-machine transitions using `velocity_state_machine.py` on null-edge data
🛑 Live regime-probability multiplier in `gateio_executor.py` before `regime_validation.py` Section 8 passes
🛑 Section 7 stair-step compounding cycles on Vote ensemble — `E ≤ 0` makes baseline reset meaningless
🛑 Backtest sweep with Kelly sizing or velocity acceleration on current data — guaranteed curve-fit per Alpha Validation Section 1.3 OOS rule
🛑 Section 10 (Regime × Compounding integration) — composes 3 layers, none of which are validated

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| A. Implement all 12 modules immediately + auto-deploy | Reproduces drift pattern; modules useless without validated edge below them; live deploy violates ADR-001 |
| B. Refuse to engage; only document yesterday's hybrid spec | These 4 specs are real engineering with falsifiable rules (Section 8 of Regime Prob, Section 4 of Compounding); merit real engagement |
| C. Build modules now, but unit-test only — no live wiring | Considered viable; deferred until user explicitly requests a specific module to avoid premature optimization |
| **D. Save specs, document gates, build modules only on user request, never wire live pre-edge-proof** ⭐ | balances respect for substantial spec work with discipline; reversible; works regardless of B.2.3 outcome |

## Consequences

**Enabled:**
- 5-layer quant stack now formally documented in `docs/specs/`
- Each spec has explicit mapping to existing tooling (Section III), gap analysis (Section V), prohibition list (Section VI)
- Future Claude sessions read these specs when relevant; consistent gating story
- If/when B.2.3 produces edge, the implementation roadmap is already mapped

**Costs:**
- Documentation hours (low cost, ~30 min total)
- Risk that operator interprets "documented" as "approved for deployment" — explicitly prevented by Section VI of each spec doc + this decision doc

## Reversibility

100%. Documentation only. To undo: `rm docs/specs/L99_ALPHA_VALIDATION.md docs/specs/L99_CAPITAL_MATHEMATICS.md docs/specs/L99_COMPOUNDING_VELOCITY.md docs/specs/L99_REGIME_PROBABILITY.md` plus this decision doc + the findings doc. No code, no production wiring, no live deployment.

## Re-evaluation triggers

Activate any module's *live* wiring (not just standalone library form) when:

1. B.2.3 (on-chain B1) OR another B-prime branch produces a validated edge ≥ +5 bps net per trade after fees
2. That edge clears 4-gate validation (rolling WF / MC permutation / fee stress / bootstrap CI)
3. That edge clears 60-day Stage 1 paper validation per `l99_validate.py` (≥30 trades, PnL>0, DD<5%, Sharpe≥0.5)
4. **Then and only then:** `kelly_sizer.py` may produce a sizing fraction; `velocity_state_machine.py` may transition out of CONSERVATIVE; `regime_probability.py` outputs may multiply position sizes.

Until #1-#3 are met, all 12 modules either stay unimplemented or remain library-only with synthetic-data tests.

## ADR linkage

- **ADR-001** — D-day discipline: validation before deployment ✅ honored across all 4 specs
- **ADR-002** — Phase B direction: each spec sits as orchestration layer above Phase B branches ✅
- **ADR-003** — D7 freeze: expired 2026-05-01 00:00 UTC; this commit is post-D7 ✅
- `feedback_drift_pattern.md` (memory) — never silently build from vision pastes ✅ each spec gets real engagement, not silent build

## Related

- [docs/specs/L99_ALPHA_VALIDATION.md](../../docs/specs/L99_ALPHA_VALIDATION.md) — Layer 1 spec
- [docs/specs/L99_CAPITAL_MATHEMATICS.md](../../docs/specs/L99_CAPITAL_MATHEMATICS.md) — Layer 3 spec
- [docs/specs/L99_COMPOUNDING_VELOCITY.md](../../docs/specs/L99_COMPOUNDING_VELOCITY.md) — Layer 4 spec
- [docs/specs/L99_REGIME_PROBABILITY.md](../../docs/specs/L99_REGIME_PROBABILITY.md) — Layer 2 spec
- [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](../../docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md) — Layer 5 spec (yesterday)
- [[findings/2026-05-01-l99-quant-suite-summary]] — overview + 5-layer diagram
- [[decisions/2026-05-01-l99-hybrid-spec-research-only]] — sister decision (Layer 5)
- [[findings/2026-04-30-d6-binding-no-go]] — proves Layer 1 currently rejects all candidates on Gate.io spot 30 bps
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — branch B.2.4 hosts these specs as the post-edge orchestration layer
