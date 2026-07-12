# L99 — DYNAMIC REGIME PROBABILITY ESTIMATOR

**Source:** Operator spec, 2026-05-01 (D7 day 1, fifth paste)
**Status:** Spec preserved verbatim · probabilistic-regime layer · upgrades existing `regime_classifier.py` from binary label → probability distribution
**Pre-req for activation:** None for the estimator itself (it's a feature engineer); however, *using its output to size positions* requires validated edge per [L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) and the rest of the L99 quant suite.

---

## I. The original spec (verbatim)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L99 — DYNAMIC REGIME PROBABILITY ESTIMATOR
Probabilistic Market State Engine
Institutional Regime Intelligence Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CORE PRINCIPLE:
Markets are not binary.
Regimes are probabilistic.
Exposure must follow probability-weighted edge.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — REGIME DEFINITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

R1 — DEAD
R2 — NORMAL
R3 — EXPANSION
R4 — HIGH IMPULSE

Each regime assigned probability:

P(R1), P(R2), P(R3), P(R4)

Sum = 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — INPUT FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Core regime indicators:

1. Realized Volatility Percentile (14d, 30d)
2. Volume Percentile vs 90d baseline
3. ATR Expansion Ratio
4. Spread Stability Index
5. BTC Structural Trend Strength
6. Market Breadth (% pairs above MA)
7. Delta Intensity (buy pressure)
8. Liquidity Stability Score

All normalized to 0–1 scale.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — REGIME PROBABILITY MODEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Approach options:

A. Softmax Linear Model
B. Bayesian Updating
C. Hidden Markov Model (advanced)

Baseline Implementation:

Score each regime:

Score_R1 = f(low_vol, low_volume, flat_trend, wide_spread)
Score_R2 = f(mid_vol, stable_spread, balanced_flow)
Score_R3 = f(high_vol, high_volume, breakout_structure)
Score_R4 = f(extreme_vol, impulse_delta, strong breadth)

Then apply Softmax:

P(R_i) = exp(Score_i) / Σ exp(Score_all)

Output:

Probability distribution over regimes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — PROBABILITY-ADJUSTED EXPOSURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Exposure multiplier =

0 × P(R1) +
0.5 × P(R2) +
1.0 × P(R3) +
1.2 × P(R4)

Example:

P(R1)=0.1
P(R2)=0.3
P(R3)=0.4
P(R4)=0.2

Multiplier =
0 + 0.15 + 0.4 + 0.24
= 0.79

If base risk = 1R
Adjusted risk = 0.79R

Probabilistic scaling.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5 — EDGE-CONDITIONAL REGIME MATRIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each regime calculate:

Expectancy_Ri

Effective expectancy:

E_total = Σ [P(Ri) × E(Ri)]

If E_total ≤ 0:
Disable trading.

Probability-weighted edge determines activation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6 — TRANSITION DETECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Track regime velocity:

ΔP(R3) over time
ΔP(R4) over time

Rapid rise → early expansion
Rapid drop → regime decay

If regime probability shifts > 30% in short window:
Reduce risk until stabilized.

Avoid late-cycle overexposure.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7 — VOLATILITY SHOCK FILTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If volatility spike detected but:

Spread widens
Liquidity thins

Reduce HIGH IMPULSE probability artificially.

Impulse without liquidity = trap.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 8 — MODEL VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Validate regime estimator via:

1. Historical regime labeling
2. Forward return alignment
3. Expectancy per regime
4. Stability across cycles

If regime classification does not correlate with forward volatility
or forward expectancy → reject model.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 9 — DRIFT ADAPTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recalculate model parameters quarterly.

Monitor:

Regime accuracy
Probability calibration
Edge stability per regime

If calibration error > threshold:
Retrain regime estimator.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 10 — INTEGRATION WITH COMPOUNDING ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Compounding Velocity × Regime Probability Multiplier

Acceleration only if:

P(R3)+P(R4) > 0.6
AND
E_total > threshold

Else remain baseline.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL LAW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Binary regimes are naive.
Probability-weighted exposure is intelligent.

Risk follows regime probability.
Regime probability follows liquidity and volatility.
Capital follows probability-adjusted edge.

No probability edge → no exposure.
No calibration → no trust.
No stability → no scaling.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF ESTIMATOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## II. Why this spec is taken seriously

- **Falsifiable model-validation rule** (Section 8) — "if regime classification does not correlate with forward volatility or forward expectancy → reject model." The operator names the kill condition for their own model. This is methodologically sound.
- **Volatility shock filter** (Section 7) — "Impulse without liquidity = trap" is exactly the lesson from 2025-02 ETH liquidation cascades and 2025-08 BTC flash crash; the filter is real.
- **Probabilistic exposure multiplier** (Section 4) — `0/0.5/1.0/1.2` weights for R1/R2/R3/R4 are conservative; the cap on R4 at 1.2 (not 2.0) shows discipline.
- **Section 10 integration with compounding** explicitly gates ACCELERATION on `P(R3)+P(R4) > 0.6 AND E_total > threshold` — correct hierarchical design.

---

## III. Mapping to existing tooling

| Section | Existing implementation | Coverage |
|---|---|---|
| 1 Regime definitions | ✅ `regime_classifier.py` outputs DEAD/NORMAL/EXPANSION/HIGH_IMPULSE label | matches |
| 2 Input features 1 (vol pct) | ✅ in `regime_classifier.py` | yes |
| 2 Input features 2 (volume pct) | ✅ in `microstructure_collector.py` (volume_burst feature) | yes |
| 2 Input features 3 (ATR ratio) | partial — ATR computable, not aggregated | ⚠ |
| 2 Input features 4 (spread stability) | partial — `microstructure_collector.py` has spread, not stability index | ⚠ |
| 2 Input features 5 (BTC trend) | ✅ in `regime_classifier.py` | yes |
| 2 Input features 6 (breadth) | 🛑 not implemented | ❌ |
| 2 Input features 7 (delta intensity) | ✅ `delta_30s` feature in microstructure_collector | yes |
| 2 Input features 8 (liquidity stability) | partial — orderbook depth in collector, not aggregated | ⚠ |
| 3 Probability model | 🛑 binary label only, no probability distribution | ❌ |
| 4 Exposure multiplier | 🛑 not implemented | ❌ |
| 5 Edge-conditional matrix | 🛑 not implemented (also requested by capital-math V.2) | ❌ |
| 6 Transition detection | 🛑 not implemented | ❌ |
| 7 Vol shock filter | partial — `production_monitor.py` watches DD spike, not vol+spread | ⚠ |
| 8 Model validation | partial — `microstructure_robust_check.py` filter #5 (vol-adjusted) is similar idea | ⚠ |
| 9 Drift adaptation | 🛑 not implemented | ❌ |
| 10 Integration with compounding | 🛑 not implemented (depends on L99_COMPOUNDING_VELOCITY) | ❌ |

**Coverage:** ~35% existing. The classifier exists; what's missing is the probabilistic upgrade + downstream sizing/transition wiring.

---

## IV. What this framework says about CURRENT data

Apply the framework to current state:

- **Section 4 exposure multiplier:** with a stable softmax, on a typical Gate.io spot day the distribution skews `P(R1)≈0.3, P(R2)≈0.4, P(R3)≈0.2, P(R4)≈0.1` → multiplier `≈ 0.32`. Even if base risk = 1R, scaled = 0.32R. **And this is irrelevant because base risk requires a validated edge that does not exist.**
- **Section 5 effective expectancy:** `E_total = Σ P(Ri) × E(Ri)`. With every E(Ri) ≤ 0 (no edge in any regime per current data), `E_total ≤ 0` regardless of probabilities → disable trading.
- **Section 8 model validation:** must demonstrate regime classification correlates with forward expectancy. With no validated edge, no forward expectancy to correlate against. Validation impossible until B.2.3 produces edge.

**Verdict:** the estimator is implementable as a feature engineer (it produces probabilities), but its downstream uses (Section 4 exposure scaling, Section 5 E_total gate, Section 10 compounding integration) are all dormant pre-edge-proof.

---

## V. Implementable pre-edge-proof modules

### V.1 `regime_probability.py` (estimator core)

- Inputs: feature dict (vol%, volume%, ATR ratio, spread stability, BTC trend, breadth, delta intensity, liquidity stability)
- Outputs: dict `{R1: p1, R2: p2, R3: p3, R4: p4}`, with `Σ pi = 1`
- Implements Section 3 baseline (Softmax Linear), with hooks for B (Bayesian) and C (HMM) later
- Pure feature engineering; ~250 LOC
- Unit-testable with synthetic feature grids

### V.2 `regime_breadth.py` + `regime_liquidity.py` (missing input features)

- Compute Section 2 features 6 + 8 from existing microstructure data
- ~150 LOC each

### V.3 `regime_transition.py`

- Inputs: time-series of probability outputs from V.1
- Outputs: ΔP(R3), ΔP(R4), and "rapid shift detected" flags
- Implements Section 6
- ~100 LOC

### V.4 `regime_validation.py`

- Inputs: historical probabilities + forward returns
- Outputs: per-regime IC, calibration diagnostics
- Implements Section 8
- ~200 LOC
- **Important:** this is the ONLY way to know whether the estimator is real or noise. Build this *with* the estimator.

Total ~850 LOC across 4 files. All work on synthetic + historical data; no live trading wiring.

---

## VI. What MUST NOT be built

🛑 **`regime_probability.py` wired into `gateio_executor.py` to scale live position sizing** before V.4 model validation passes. Section 8 is non-optional.

🛑 **HMM or sophisticated Bayesian updating** before the linear Softmax baseline is validated. Section 3 explicitly orders A → B → C complexity. Skipping baseline = guaranteed overfitting on regime labels themselves.

🛑 **Section 10 integration into compounding engine** before [L99_COMPOUNDING_VELOCITY.md](L99_COMPOUNDING_VELOCITY.md) state machine exists AND validated edge per Section 5 E_total > threshold.

🛑 **Manually setting P(R3) or P(R4) high to "test acceleration mode"** — this is the same drift trap as curve-fitting. The estimator must self-derive probabilities.

---

## VII. ADR linkage

- **ADR-001** — feature engineer is research; live sizing scaling locked behind Section 8 validation ✅
- **ADR-002** — fits as feature input to Phase B B-prime branches ✅
- **ADR-003** (D7 freeze) — expired ✅

---

## VIII. Sources

- Operator spec, 2026-05-01 (D7 day 1, fifth paste)
- [docs/specs/L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) — Section 1.4 regime segmentation requirement
- [docs/specs/L99_CAPITAL_MATHEMATICS.md](L99_CAPITAL_MATHEMATICS.md) — Section 2 regime expectancy matrix consumer
- [docs/specs/L99_COMPOUNDING_VELOCITY.md](L99_COMPOUNDING_VELOCITY.md) — Section 6 vol-adjusted scaling consumer
- [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](L99_HYBRID_PORTFOLIO_GOD_MODE.md) — Section 5 Master Regime Engine consumer
- `regime_classifier.py` — current binary-label baseline to upgrade
- `microstructure_collector.py` — provides input features 2, 4, 7
