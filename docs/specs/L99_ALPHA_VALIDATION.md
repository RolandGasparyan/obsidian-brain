# L99 — FORMAL ALPHA VALIDATION + REALISTIC EXPECTANCY MODEL

**Source:** Operator spec, 2026-05-01 (D7 day 1, second paste)
**Status:** Spec preserved verbatim · validation framework, not strategy code · maps to existing 7-filter battery + 4-gate validator + `l99_validate.py`
**Pre-req for activation:** None — this is a *validation framework*. Applying it to current data already produces 🛑 reject (per Section 1.6) consistent with D6 NO-GO.

---

## I. The original spec (verbatim)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L99 — FORMAL ALPHA VALIDATION + REALISTIC EXPECTANCY MODEL
Institutional Quant Research Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CORE LAW:
No measurable edge → No capital.
No statistical stability → No scaling.
No expectancy → No strategy.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — ALPHA VALIDATION FRAMEWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Objective:
Determine whether a signal has statistically defensible predictive power.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.1 DATA REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Minimum:
- 3–6 months historical data
- ≥ 500 signal events (preferred ≥ 1000)
- Multiple regime environments

Data must include:
- Entry timestamp
- Signal strength
- Forward returns (1m, 5m, 15m, 1H)
- Volatility context
- Spread context
- Fee context

No cherry-picking.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.2 FEATURE VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each signal:

Compute:

Information Coefficient (IC):
Correlation(signal_score, forward_return)

Rolling IC (30-window)
IC stability across regimes

Thresholds:
|IC| ≥ 0.03 → minimum viable
|IC| ≥ 0.05 → strong
t-stat ≥ 2 → statistically defensible

If IC unstable across regimes → reject.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.3 WALK-FORWARD TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Split data into:

Train window
Test window (out-of-sample)

Rules:

- No parameter tuning on test window
- Test must show similar IC magnitude
- Expectancy must remain positive

If OOS degrades > 40% → unstable signal.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.4 REGIME SEGMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Segment performance by:

Volatility percentile
Volume percentile
Trend regime
Spread percentile

Check:

Does signal only work in EXPANSION?
Does it collapse in DEAD?

If signal is regime-dependent:
Restrict deployment to valid regime only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.5 FEE-ADJUSTED EDGE TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Net edge must exceed:

2 × trading fee + slippage buffer.

If gross edge = 0.4%
Fee + slippage = 0.3%
→ Not tradable.

Edge must survive friction.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.6 DECISION MATRIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If:

IC ≥ 0.03
t-stat ≥ 2
OOS positive
Fee-adjusted expectancy positive
Stable across regimes or properly gated

→ Candidate Alpha

Else → Reject or redesign.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — REALISTIC EXPECTANCY MODELING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Expectancy is the only number that matters.

Formula:

E = (WinRate × AvgWin) − (LossRate × AvgLoss)

All values must be fee-adjusted.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.1 BASE METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Measure:

Win Rate (WR)
Average R/WIN
Average R/LOSS
Profit Factor (PF)
Max consecutive losses
Max drawdown
Trade frequency

No vanity metrics.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.2 TARGET PROFILE (SPOT MOMENTUM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Realistic durable target:

WR: 48–55%
Avg R/WIN: ≥ 2.0
Avg R/LOSS: 1.0
PF: 1.3–1.6
Max DD < 20%

Example:

WR = 50%
Avg Win = 2R
Avg Loss = 1R

E = (0.5 × 2) − (0.5 × 1)
E = 1 − 0.5 = +0.5R per trade

Positive.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.3 SAMPLE SIZE REQUIREMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Minimum:
50 trades → viability gate
200 trades → early statistical confidence
500+ trades → strong confidence

Less than 50 → noise zone.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.4 MONTE CARLO SIMULATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Simulate:

Randomized order of trade outcomes
1000+ simulations

Observe:

Worst-case drawdown
Equity volatility
Probability of ruin

If probability of ruin > 5% → reduce risk.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.5 POSITION SIZING STABILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use fixed fractional risk:

0.5R – 1R per trade

Never increase risk without:

Rolling 50 pass
Stable PF > 1.3
Stable WR > 48%

Compounding must be earned.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.6 DRIFT DETECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Monitor rolling:

WR
PF
Expectancy
IC

If expectancy drops below 0:
Disable signal immediately.

No emotional override.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.7 EDGE DECAY MONITOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If:

Rolling IC < 50% historical average
OR
PF < 1.1
OR
WR < 42%

→ Edge decay detected
→ Pause engine
→ Revalidate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — DEPLOYMENT GATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before real capital:

Must pass:

Rolling 50 trades:
WR ≥ 48%
Avg R/WIN ≥ 2
PF ≥ 1.3
Expectancy ≥ +0.48R
Max DD < 20%

If any fail:
Remain paper-only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — CORE PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Edge > Architecture
Expectancy > Trade count
Stability > Speed
Capital > Ego
Evidence > Excitement

No IC → No strategy.
No expectancy → No trading.
No stability → No scaling.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF FRAMEWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## II. Why this spec is taken seriously

Unlike vibe-pastes, this framework:

- Specifies numerical thresholds (|IC| ≥ 0.03, t-stat ≥ 2, OOS degradation cap 40%, fee buffer 2× trading fee, ruin probability < 5%)
- Lists falsifiable rejection criteria (Section 1.6 decision matrix)
- Acknowledges regime dependence (Section 1.4)
- Includes drift detection + auto-disable triggers (Sections 2.6, 2.7)
- Refuses to substitute architecture or trade frequency for edge (Section 4)

This is the **validation/measurement** companion to the [L99_HYBRID_PORTFOLIO_GOD_MODE.md](L99_HYBRID_PORTFOLIO_GOD_MODE.md) **architecture** spec. Together they form a coherent two-layer plan: validate edge first, then orchestrate engines on top of validated edge.

---

## III. Mapping to existing tooling

| Section | Existing implementation | Coverage |
|---|---|---|
| 1.1 Data requirements | `microstructure_collector.py` (1Hz × 5 pairs, parquet hourly) | ✅ exceeds 500 events; 1.5M rows / 133.7h |
| 1.2 IC + t-stat | `microstructure_robust_check.py` (filters #1–#7 incl. IC + significance) | ✅ |
| 1.3 Walk-forward | `microstructure_robust_check.py` filter #2 (rolling WF) | ✅ |
| 1.4 Regime segmentation | `regime_classifier.py` + `microstructure_robust_check.py` filter #5 (vol-adjusted) | ⚠ partial — vol adjusted yes, full 4-regime conditional matrix not yet wired |
| 1.5 Fee-adjusted edge test | quintile-economics gate (Q5−Q1 vs 30 bps) | ✅ |
| 1.6 Decision matrix | `D6_FINAL_VERDICT.md` output schema | ✅ |
| 2.1 Base metrics | `professional_backtest.py` outputs all (WR, PF, DD, etc.) | ✅ |
| 2.2 Target profile | `l99_validate.py` (WR 48%+, PF 1.3+, Expectancy 0.48R+) | ✅ |
| 2.3 Sample size | `l99_validate.py` (≥30 trades Stage-1, ≥50 rolling) | ✅ |
| 2.4 Monte Carlo | `microstructure_robust_check.py` filter #4 (bootstrap CI) | ⚠ partial — bootstrap CI on IC; no equity-curve MC ruin sim |
| 2.5 Sizing stability | `risk.py` Patches 1+3+5 (HARD_STOP_PCT, max_drawdown_pct) | ⚠ partial — fixed fractional, not Kelly-derived |
| 2.6 Drift detection | `production_monitor.py` (state transitions on DD/inactive) | ⚠ partial — state-machine, not IC/PF/expectancy monitor |
| 2.7 Edge decay | 🛑 NOT yet implemented as an automated monitor | ❌ |
| 3 Deployment gate | `l99_validate.py` 5-phase gate | ✅ matches |

**Coverage:** ~75% existing. Gaps are: full regime-conditional expectancy matrix, equity-curve MC, automated IC/PF drift monitor with engine-level auto-disable.

---

## IV. What this framework says about CURRENT data

Apply the Section 1.6 decision matrix to the current data class (Gate.io spot 5 pairs, 30 bps taker, 133.7h):

| Criterion | Threshold | Best observed | Pass? |
|---|---|---|---|
| \|IC\| | ≥ 0.03 | XRP basis_pct +0.272, BTC depth_imbalance +0.160 | ✅ |
| t-stat | ≥ 2 | top cells significant per BH-FDR filter | ✅ |
| OOS positive | yes | passed rolling WF filter #2 | ✅ |
| Fee-adjusted expectancy | positive after 2× fee + slippage | gross 14 bps Q5−Q1 vs 60+ bps required | ❌ |
| Stable across regimes | yes | passed vol-adjusted filter #5 | ✅ |

**Verdict per Section 1.6:** ❌ Reject. The Section 1.5 Fee-Adjusted Edge Test is the gate that fails — exactly what 5 prior rigor levels independently confirmed.

This framework doesn't change the verdict; it formalizes the same conclusion using the operator's own preferred language. **The operator and the existing rigor framework are in violent agreement.**

---

## V. What's genuinely new (gap analysis)

Three pieces are not yet implemented:

### V.1 Regime-conditional expectancy matrix (Section 1.4 full + Section 2.6)

`regime_classifier.py` outputs `DEAD / NORMAL / EXPANSION / HIGH_IMPULSE`, but no module currently:
- Bins live trades by regime label at entry
- Computes per-regime WR/AvgWin/AvgLoss/E/PF
- Auto-disables a (signal × regime) cell when its expectancy crosses zero

**Implementable pre-edge-proof?** Yes — works on synthetic + paper-trade data. Useful infrastructure that improves any future validated engine.

### V.2 Equity-curve Monte Carlo (Section 2.4)

`microstructure_robust_check.py` runs bootstrap CI on IC and quintile spreads. It does NOT simulate randomized orderings of an equity curve to estimate ruin probability and worst-case drawdown.

**Implementable pre-edge-proof?** Yes — pure simulation tool, takes any trade list as input.

### V.3 Edge decay monitor (Section 2.7)

`production_monitor.py` watches bot state (DD, inactivity, restarts). It does NOT compute rolling IC against a baseline or PF/WR against historical average and trigger engine pause.

**Implementable pre-edge-proof?** Partial — needs a validated edge to define "historical average" against which rolling stats are compared. Until B.2.3 produces validated edge, baseline does not exist. Stub implementable now, activation gated.

---

## VI. What CAN be built pre-edge-proof

Three deliverables are pure infrastructure (no edge required):

1. `regime_expectancy_matrix.py` — given a trade list + regime labels, produces 4×N WR/E/PF table per regime per signal. Takes synthetic or paper data.
2. `equity_mc_sim.py` — given a trade-return list, runs 1000+ randomized orderings, outputs worst 5% DD, ruin probability, time-to-recovery distribution.
3. `drift_monitor.py` (stub) — schema-only; activates when edge is validated and baseline is set.

Each is small (~200–400 LOC), has clear input/output contracts, and can be unit-tested without market data.

---

## VII. What MUST NOT be built

🛑 Trading engines using current data class (microstructure on Gate.io spot at 30 bps) — Section 1.6 already rejects them.
🛑 Kelly-sized position sizer for null-edge strategy — Section 1.6 reject means there is nothing to size.
🛑 Signal-quality scoring system on top of features that fail Section 1.5 — circular validation.
🛑 "Optimization" of parameters of a strategy that fails Section 1.6 — guaranteed curve-fit per Section 1.3 OOS rule.

---

## VIII. Order of operations (gating)

**Pre-B.2.3-edge (now):** items VI.1–VI.3 implementable as standalone library modules. Tests use synthetic data + Vote ensemble paper history (~4 closed trades, statistically meaningless but useful for plumbing).

**During B.2.3 collection (~5 days after API keys provided):** library modules sit unused; on-chain collector accumulates B1 data class.

**Post-B.2.3 7-filter battery (one-shot, ~10 min):** apply this framework's Section 1.6 to B1 features. Most likely outcome based on prior null pattern: ❌ reject. Less likely but possible: 1+ signal passes, becomes Candidate Alpha.

**If Candidate Alpha:** activate Section 3 Deployment Gate via `l99_validate.py`. ≥50 paper trades, WR ≥ 48%, PF ≥ 1.3, E ≥ +0.48R, DD < 20%. ~2–3 months elapsed.

**If Section 3 passes:** activate `regime_expectancy_matrix.py` to find the (signal × regime) cells with highest E. Activate `drift_monitor.py` with validated baseline.

**If multi-engine deploy considered:** layer L99_HYBRID_PORTFOLIO_GOD_MODE on top.

---

## IX. ADR linkage

- **ADR-001** (validate before deploy) — this spec IS the formal version of ADR-001's validation requirement
- **ADR-003** (D7 freeze) — expired today; framework documentation is not strategy code, no freeze conflict
- `feedback_drift_pattern.md` (memory) — this spec is being engaged with rigor; not silently built into engines

---

## X. Sources

- Operator spec, 2026-05-01 (D7 day 1, second paste)
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — branch B structure
- [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](L99_HYBRID_PORTFOLIO_GOD_MODE.md) — companion architecture spec
- [docs/specs/L99_DEPLOYMENT_VALIDATOR.md](L99_DEPLOYMENT_VALIDATOR.md) — earlier deployment-gate spec
- `microstructure_robust_check.py` (7-filter battery)
- `l99_validate.py` (5-phase deployment gate)
- `regime_classifier.py`
- `wiki/findings/2026-04-30-d6-binding-no-go.md` — proves Section 1.6 reject for current data class
