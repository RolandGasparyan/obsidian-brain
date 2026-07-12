# L99 — ADVANCED CAPITAL MATHEMATICS ENGINE

**Source:** Operator spec, 2026-05-01 (D7 day 1, third paste)
**Status:** Spec preserved verbatim · sizing/growth math, not strategy code · activates ONLY after [L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) Section 1.6 produces Candidate Alpha
**Pre-req for activation:** Validated edge with stable expectancy across rolling 200 trades. Current state: 🛑 no edge → all sizing math evaluates to "do not trade."

---

## I. The original spec (verbatim)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L99 — ADVANCED CAPITAL MATHEMATICS ENGINE
Kelly Constrained Sizing + Regime Expectancy + Growth Projection
Institutional Quant Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CORE LAW:
Maximize geometric growth.
Minimize ruin probability.
Constrain volatility.
Respect regime dependence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — KELLY-BASED CONSTRAINED SIZING MODEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Objective:
Optimize capital growth while preventing catastrophic drawdown.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.1 CLASSIC KELLY FORMULA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

f* = (bp − q) / b

Where:

b = Reward-to-risk ratio (Avg Win / Avg Loss)
p = Win rate
q = 1 − p
f* = Optimal fraction of capital to risk

Example:

Win rate (p) = 0.50
Avg R/WIN = 2
Avg R/LOSS = 1
b = 2

f* = (2×0.5 − 0.5) / 2
f* = (1 − 0.5) / 2
f* = 0.5 / 2
f* = 0.25 → 25% capital (theoretical full Kelly)

Full Kelly is too volatile.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.2 CONSTRAINED KELLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use:

Half Kelly (0.5 × f*)
or
Quarter Kelly (0.25 × f*)

Institutional Rule:

Max risk per trade = min(Quarter Kelly, 1%)

Example:

Full Kelly = 25%
Quarter Kelly = 6.25%
Risk cap = 1%

→ Use 1% per trade.

If Kelly < 1%:
Use Kelly-derived value.

Kelly must never override drawdown law.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.3 VOLATILITY ADJUSTED KELLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If rolling drawdown > 10%:
Reduce Kelly fraction by 50%.

If rolling expectancy < baseline:
Freeze Kelly scaling.

Kelly reacts to edge stability.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — REGIME-CONDITIONAL EXPECTANCY MATRIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Edge is regime-dependent.

Define regimes:

R1 — DEAD
R2 — NORMAL
R3 — EXPANSION
R4 — HIGH IMPULSE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.1 EXPECTANCY MATRIX STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each regime compute:

Win rate
Avg R/WIN
Avg R/LOSS
Expectancy
Profit factor

Example:

R1 DEAD:
WR = 42%
AvgWin = 1.3R
E = negative → disable trading

R2 NORMAL:
WR = 48%
AvgWin = 1.8R
E ≈ +0.34R

R3 EXPANSION:
WR = 52%
AvgWin = 2.2R
E ≈ +0.64R

R4 HIGH IMPULSE:
WR = 55%
AvgWin = 2.5R
E ≈ +0.875R

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.2 REGIME ACTIVATION RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Trade only when:

Expectancy > 0.3R

Scale risk:

NORMAL → 0.5R base
EXPANSION → 1R base
HIGH IMPULSE → 1R (never exceed cap)

DEAD → 0 exposure

Edge must justify risk.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.3 REGIME DRIFT DETECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If regime expectancy drops below 0:

Auto-disable that regime.

No override allowed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — CAPITAL GROWTH PROJECTION ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Objective:
Model long-term geometric growth with realistic variance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.1 GEOMETRIC GROWTH MODEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Capital evolution:

C(n) = C0 × Π (1 + r_i)

Where r_i = return per trade.

Approximate log growth:

g ≈ E − (variance / 2)

Higher variance reduces growth.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.2 EXPECTED MONTHLY RETURN ESTIMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Monthly return ≈

Expectancy × trades per month × risk per trade

Example:

E = +0.5R
Trades/month = 30
Risk per trade = 1%

Monthly ≈ 0.5 × 30 × 1%
= 15%

But variance must adjust.

Realistic adjustment:
Reduce by 30–50% to account for clustering.

Adjusted expected ≈ 7–10%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.3 MONTE CARLO GROWTH SIMULATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Simulate:

Randomized trade sequences
1000–5000 runs
Track:

Median equity curve
Worst 5% drawdown
Time to recovery
Probability of 30% DD

If ruin probability > 5%:
Reduce risk.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.4 SAFE GROWTH TARGETS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For spot momentum system:

Conservative:
3–6% monthly

Moderate:
6–10% monthly

Aggressive but sustainable:
10–15% monthly

Anything above consistently → suspect overfitting.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.5 SCALING LAW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scale capital only if:

Rolling 200 trades:
PF ≥ 1.4
Stable regime matrix
No drift detected

Increase risk incrementally:
+0.25R step

Never double risk.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — RISK OF RUIN FORMULA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Approximation:

Ruin ≈ ((1 − edge) / (1 + edge)) ^ capital_units

Edge = expectancy per unit risk.

Lower risk per trade → exponentially lower ruin probability.

Target ruin probability < 1%.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5 — FINAL PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Kelly guides scaling.
Regime controls exposure.
Expectancy governs activation.
Variance limits growth.
Risk defines survival.

Growth without control = destruction.
Control without growth = stagnation.
Balance = institutional edge.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## II. Why this spec is taken seriously

Three quality markers absent from prior vibe-pastes:

1. **Constrained Kelly with hard cap** (Section 1.2): `min(Quarter Kelly, 1%)`. Acknowledges full Kelly variance as unacceptable. Operator-engineering match.
2. **Regime-conditional sizing matrix** (Section 2.2): explicit `DEAD → 0 exposure`, `NORMAL → 0.5R`, `EXPANSION → 1R`. Refuses to size positions when regime expectancy is negative.
3. **Realistic growth targets** (Section 3.4): 3–6% conservative, "anything above consistently → suspect overfitting." This is the first user-paste in the project arc that explicitly *names overfitting as the failure mode of optimistic projections.*

Combined with [L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md), this is the **sizing/growth** layer of a coherent three-layer plan:

- **Layer 1 — Validation:** prove edge exists ([L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md))
- **Layer 2 — Capital Math:** size positions safely on validated edge (this spec)
- **Layer 3 — Architecture:** orchestrate multiple validated edges ([L99_HYBRID_PORTFOLIO_GOD_MODE.md](L99_HYBRID_PORTFOLIO_GOD_MODE.md))

---

## III. Mapping to existing tooling

| Section | Existing implementation | Coverage |
|---|---|---|
| 1.1 Classic Kelly | 🛑 not implemented | ❌ |
| 1.2 Constrained Kelly + 1% cap | partial — `risk.py` HARD_STOP_PCT=2.5% (per-bot, not Kelly-derived) | ⚠ |
| 1.3 Vol-adjusted Kelly | partial — `risk.py` Patch 3 max_drawdown_pct=5% halt; not Kelly-frac reduction | ⚠ |
| 2.1 Regime expectancy matrix | 🛑 not implemented | ❌ |
| 2.2 Regime activation rule | partial — `regime_classifier.py` exists but does NOT gate sizing | ⚠ |
| 2.3 Regime drift auto-disable | 🛑 not implemented | ❌ |
| 3.1 Geometric growth model | implicit in `professional_backtest.py` equity curve | ⚠ |
| 3.2 Monthly return estimation | 🛑 not implemented | ❌ |
| 3.3 Monte Carlo growth sim | 🛑 not implemented (bootstrap CI on IC exists, equity-curve MC does not) | ❌ |
| 3.4 Safe growth targets | conceptual in `CHAMPION_MODE.md` capital ladder | ⚠ |
| 3.5 Scaling law (rolling 200, +0.25R) | partial — `l99_validate.py` 5-phase ladder; not +0.25R increments | ⚠ |
| 4 Ruin formula | 🛑 not implemented | ❌ |

**Coverage:** ~20% existing. This spec describes a substantial body of new sizing/growth math.

---

## IV. What this framework says about CURRENT data

Apply the framework to the current state:

- **Section 1.1 Kelly inputs:** `b = AvgWin/AvgLoss = undefined` (no winning trades in last 7 days of Vote ensemble paper); `p = WR ≈ 0`. Formula returns `f* < 0` → do not trade.
- **Section 2.1 Regime matrix:** undefined per regime (no statistically meaningful sample yet).
- **Section 2.2 Activation rule:** `E < 0.3R` → no regime activated.
- **Section 3.4 Growth target:** N/A — applies only after edge validated.
- **Section 4 Ruin formula:** with `edge ≤ 0`, ruin probability → 1 over enough trades.

**Verdict:** the math itself, applied to current observed data, says "do not trade." Same conclusion as 5 prior rigor levels and the L99_ALPHA_VALIDATION Section 1.6. Three frameworks now agree.

---

## V. Implementable pre-edge-proof modules

Even without validated edge, four pieces are pure math (no live deploy risk) and useful to have ready when edge appears:

### V.1 `kelly_sizer.py`

- Inputs: rolling WR, AvgWin, AvgLoss, current capital, current rolling DD, baseline expectancy
- Outputs: recommended risk fraction (capped at min(Quarter Kelly, 1%))
- Implements Sections 1.1, 1.2, 1.3 verbatim
- Unit-testable with synthetic stats; ~150 LOC

### V.2 `regime_expectancy_matrix.py` (also called for in [L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) §V.1)

- Inputs: trade list (entry timestamp, R-outcome) + regime label per timestamp
- Outputs: 4×N matrix of WR/E/PF per (regime × signal) cell
- Implements Sections 2.1, 2.2, 2.3
- ~250 LOC

### V.3 `equity_mc_sim.py`

- Inputs: list of per-trade R-outcomes
- Outputs: 1000–5000 randomized orderings, percentile equity curves, P(ruin), P(30% DD), median time-to-recovery
- Implements Sections 3.3, 4
- ~200 LOC

### V.4 `growth_projector.py`

- Inputs: validated expectancy, trade-frequency, risk-per-trade, variance, target horizon
- Outputs: expected monthly + median + worst 5%, with explicit "REDUCE BY 30–50%" applied per Section 3.2
- Implements Section 3.2
- ~100 LOC

All four are math libraries. They are USELESS if you trade null-edge data through them, but harmless to build because they don't touch live exchange APIs.

---

## VI. What MUST NOT be built

🛑 **A live `kelly_sizer.py` driving `gateio_executor.py`** before Section 1.6 of L99_ALPHA_VALIDATION produces Candidate Alpha. Sizing null edge optimally = optimally losing money. ADR-001 violation.

🛑 **Backtest sweep with Kelly sizing on current data** to "find the best Kelly fraction." This is parameter optimization on null edge — guaranteed curve-fit per L99_ALPHA_VALIDATION Section 1.3.

🛑 **Multi-engine portfolio orchestration** (L99_HYBRID_PORTFOLIO_GOD_MODE Engines A/B/C) with this spec's regime matrix until each engine has individual Stage-1 validation per [L99_DEPLOYMENT_VALIDATOR.md](L99_DEPLOYMENT_VALIDATOR.md).

🛑 **Compounding via `+0.25R step` (Section 3.5)** without first satisfying `Rolling 200 trades, PF ≥ 1.4, stable regime matrix`. Current Vote ensemble has 4 closed trades — 196 trades short of trigger.

---

## VII. Order of operations (gating)

| Step | Status | Trigger to next |
|---|---|---|
| **0. Frameworks documented** | ✅ this PR | merge |
| **1. Stub library modules** (V.1–V.4 with synthetic-data unit tests) | ⏳ implementable now | user request |
| **2. B.2.3 on-chain collection** | 🛑 blocked on API keys | user provides 3 keys |
| **3. 7-filter battery on B1 features** | pending step 2 | one Candidate Alpha |
| **4. l99_validate Stage 1 paper** | pending step 3 | 50 trades, WR/PF/E thresholds |
| **5. Activate `regime_expectancy_matrix.py`** | pending step 4 | 4-regime matrix populated |
| **6. Activate `kelly_sizer.py`** | pending step 5 | rolling 200 trades, PF ≥ 1.4 stable |
| **7. Capital scaling per Section 3.5** | pending step 6 | +0.25R increments only |

**Earliest credible step 6:** ~6+ months from now (5d collection + 7-filter + 200 paper trades minimum at ~30 trades/month). Probably longer.

---

## VIII. ADR linkage

- **ADR-001** (validate before deploy) — explicitly honored: every Section 1/2/3 lever locked behind validated-edge gate
- **ADR-002** (Phase B direction) — capital math activates only after a B-branch produces edge
- **ADR-003** (D7 freeze) — expired; documentation work post-D7
- `feedback_drift_pattern.md` — engaged with rigor; not silently building Kelly engine on null edge

---

## IX. Sources

- Operator spec, 2026-05-01 (D7 day 1, third paste)
- [docs/specs/L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) — required prerequisite
- [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](L99_HYBRID_PORTFOLIO_GOD_MODE.md) — orchestration layer
- [docs/specs/L99_DEPLOYMENT_VALIDATOR.md](L99_DEPLOYMENT_VALIDATOR.md) — earlier deployment gate
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — branch B structure
- `risk.py`, `regime_classifier.py`, `l99_validate.py`, `professional_backtest.py`
- Edward O. Thorp, "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market" (1997)
