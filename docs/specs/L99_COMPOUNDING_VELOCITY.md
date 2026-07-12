# L99 — COMPOUNDING VELOCITY OPTIMIZER

**Source:** Operator spec, 2026-05-01 (D7 day 1, fourth paste)
**Status:** Spec preserved verbatim · scaling/state-machine layer · activates ONLY after [L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) Section 1.6 produces Candidate Alpha AND [L99_CAPITAL_MATHEMATICS.md](L99_CAPITAL_MATHEMATICS.md) Section 1.2 cap is honored
**Pre-req for activation:** Validated edge + rolling-50 stable PF/WR per L99_ALPHA_VALIDATION Section 3 deployment gate. Current state: 🛑 no edge → engine permanently in CONSERVATIVE state.

---

## I. The original spec (verbatim)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L99 — COMPOUNDING VELOCITY OPTIMIZER
Geometric Growth Control Engine
Institutional Capital Acceleration Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CORE PRINCIPLE:
Compounding is powerful.
Uncontrolled compounding destroys accounts.
Velocity must follow edge stability.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — DEFINE COMPOUNDING VELOCITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Compounding Velocity (CV) =
Expected Monthly Growth × Stability Factor × Risk Multiplier

Where:

Expected Monthly Growth =
Expectancy × Trades per Month × Risk per Trade

Stability Factor =
(Profit Factor Stability × IC Stability × Drawdown Stability)

Risk Multiplier =
Function of rolling performance vs baseline

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — VELOCITY STATES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STATE 1 — CONSERVATIVE MODE
Conditions:
PF < 1.3 OR
Rolling 50 barely passes OR
DD > 10%

Risk:
0.5R per trade
No scaling allowed

Purpose:
Stabilize capital.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STATE 2 — BASELINE MODE
Conditions:
PF 1.3–1.5
Stable IC
DD < 10%

Risk:
0.75R–1R per trade
Slow compounding allowed

Purpose:
Controlled growth.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STATE 3 — ACCELERATION MODE
Conditions:
PF ≥ 1.6
Rolling 200 stable
IC consistent
DD < 8%
Regime = EXPANSION

Risk:
Increase by +0.25R step
Never exceed 1.25R cap

Purpose:
Maximize geometric growth during edge dominance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — VELOCITY FORMULA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Velocity Score (VS) =

(PF × E × IC Stability) /
(DD% × Variance)

If VS < threshold → reduce risk.
If VS high and stable → allow scaling.

Scaling Rule:

If VS > 2.0 and stable 30 trades →
Increase risk by +0.25R

If VS < 1.0 →
Reduce risk by 50%

If VS < 0 →
Freeze engine

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — ANTI-OVERCOMPOUNDING LAW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If:

3 consecutive losses at elevated risk
OR
Daily loss > 3R
OR
Weekly loss > 6R

Immediate:

Reduce risk to baseline
Disable acceleration for 10 trades

Capital protection overrides velocity.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5 — GROWTH PROJECTION CONTROL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Monthly Expected Growth Bands:

Stable Mode:
3–6%

Baseline Mode:
6–10%

Acceleration Mode:
10–15%

If projection > 20% consistently:
Re-evaluate overfitting risk.

Extreme projected growth → suspect instability.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6 — VOLATILITY ADJUSTED SCALING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If regime volatility percentile > 70%:
Allow acceleration only if spread stable.

If volatility spikes but spreads widen:
Do NOT scale.

Expansion without liquidity stability = trap.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7 — CAPITAL STAIR-STEP MODEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Instead of continuous compounding:

Use staircase growth.

Example:

Capital grows 10%
Lock new baseline
Reset risk to original fraction
Recalculate Kelly
Resume compounding

This prevents exponential blow-up cycles.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 8 — VELOCITY COOLING SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After strong run (≥ 15R month):

Force temporary reduction:
−25% risk for next 10 trades.

Purpose:
Avoid peak-risk bias.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 9 — MATHEMATICAL TARGET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

True objective:

Maximize log-growth (geometric mean)
Minimize drawdown convexity
Avoid ruin probability > 1%

Velocity is allowed only when:

Edge stability > volatility risk.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL LAW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Compounding follows edge.
Edge follows regime.
Regime follows liquidity.
Liquidity follows reality.

No edge → no acceleration.
No stability → no scaling.
No discipline → no capital.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF OPTIMIZER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## II. Why this spec is taken seriously

- **Tri-state machine with falsifiable transition rules** (Section 2) — not "just go aggressive when winning"
- **Anti-overcompounding law** (Section 4) — explicit `3 consecutive losses → baseline + 10-trade cooldown` is the single most-violated law by amateur compounders
- **Stair-step model** (Section 7) — recognizes continuous compounding's blow-up risk; resets risk fraction at each step
- **Velocity cooling after strong runs** (Section 8) — explicit defense against post-streak overconfidence (peak-risk bias)
- **Section 9 Mathematical Target** names log-growth optimization with ruin-probability cap < 1% as the actual objective. This is institutional-quant correct.

This spec is the **state-machine layer** above [L99_CAPITAL_MATHEMATICS.md](L99_CAPITAL_MATHEMATICS.md): given Kelly produces a fraction, this decides whether to *use* that fraction, half of it, or freeze.

---

## III. Mapping to existing tooling

| Section | Existing implementation | Coverage |
|---|---|---|
| 1 CV definition | 🛑 no module aggregates these | ❌ |
| 2 STATE 1 (Conservative) | partial — `risk.py` has fixed sizing, no state | ⚠ |
| 2 STATE 2 (Baseline) | 🛑 no state machine | ❌ |
| 2 STATE 3 (Acceleration) | 🛑 no rolling 200 evaluator | ❌ |
| 3 Velocity Score | 🛑 not implemented | ❌ |
| 4 Anti-overcompounding | partial — Patch 3 max_drawdown_pct=5% halt; not 3-consecutive-loss cooldown | ⚠ |
| 5 Growth bands | conceptual in `CHAMPION_MODE.md` ladder | ⚠ |
| 6 Vol-adjusted scaling | partial — `regime_classifier.py` outputs label, no scaling integration | ⚠ |
| 7 Stair-step model | partial — `l99_validate.py` Phase ladder is conceptually similar | ⚠ |
| 8 Velocity cooling | 🛑 not implemented | ❌ |
| 9 Mathematical target | aspirational in `CHAMPION_MODE.md` | ⚠ |

**Coverage:** ~10% existing. This spec is mostly new code.

---

## IV. What this framework says about CURRENT data

Apply the framework to current state:

- **Section 2 entry condition for STATE 1:** `PF < 1.3 OR DD > 10%` → triggered (Vote ensemble has no winning trades, DD already at -2.40% over 7 days, would breach 10% on extrapolation). Engine = CONSERVATIVE.
- **Section 3 Velocity Score:** `VS = (PF × E × IC_stability) / (DD% × variance)`. With `PF undefined, E ≤ 0, DD% > 0` → `VS ≤ 0` → freeze engine.
- **Section 9 mathematical target:** log-growth requires `E > variance/2`; with `E ≤ 0`, log-growth negative. Do not deploy.

**Verdict:** the math says "freeze." Same conclusion as [L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) Section 1.6, [L99_CAPITAL_MATHEMATICS.md](L99_CAPITAL_MATHEMATICS.md) Section 1.1, and 5 prior rigor levels.

---

## V. Implementable pre-edge-proof modules

These are pure state-machine / formula libraries; useful when edge appears, harmless if edge never appears:

### V.1 `velocity_state_machine.py`

- Inputs: rolling PF, rolling WR, rolling DD, rolling-50 trade count, regime label
- Outputs: state ∈ {CONSERVATIVE, BASELINE, ACCELERATION}
- Implements Section 2 transition rules verbatim
- Pure logic; ~150 LOC

### V.2 `velocity_score.py`

- Inputs: PF, E, IC stability, DD%, variance
- Outputs: VS score + scaling action
- Implements Section 3 verbatim
- ~80 LOC

### V.3 `anti_overcompounding.py`

- Inputs: trade history (last N), current risk fraction
- Outputs: triggered flags (3-loss / daily-3R / weekly-6R) + recommended cooldown
- Implements Section 4 verbatim
- ~120 LOC

### V.4 `stair_step_compounder.py`

- Inputs: account history with locked baselines
- Outputs: next risk fraction (post-Section-7 reset)
- ~100 LOC

All four work on synthetic + paper data. Total ~450 LOC.

---

## VI. What MUST NOT be built

🛑 Live state machine driving sizing on **null-edge** Vote ensemble — currently STATE = CONSERVATIVE permanently; building the live wiring just lets a future Engine-with-edge plug in. Until that engine exists, wiring is premature optimization.

🛑 ACCELERATION mode activated by relaxing Section 2 thresholds. Section 2 thresholds (PF ≥ 1.6, rolling 200 stable, IC consistent, DD < 8%) are calibrated; lowering them defeats the discipline.

🛑 Any compounding cycle on current Vote ensemble. Section 7 stair-step model assumes positive log-growth; current state is negative.

---

## VII. ADR linkage

- **ADR-001** (validate before deploy) — all velocity scaling locked behind validated edge ✅
- **ADR-002** — sits as scaling layer above Phase B branches ✅
- **ADR-003** (D7 freeze) — expired today; framework documentation post-D7 ✅

---

## VIII. Sources

- Operator spec, 2026-05-01 (D7 day 1, fourth paste)
- [docs/specs/L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) — required validation gate
- [docs/specs/L99_CAPITAL_MATHEMATICS.md](L99_CAPITAL_MATHEMATICS.md) — produces the Kelly fraction this spec gates
- [docs/specs/L99_REGIME_PROBABILITY.md](L99_REGIME_PROBABILITY.md) — companion spec for probabilistic regime input to Section 6
- [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](L99_HYBRID_PORTFOLIO_GOD_MODE.md) — portfolio-level orchestration above this layer
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — branch B structure
