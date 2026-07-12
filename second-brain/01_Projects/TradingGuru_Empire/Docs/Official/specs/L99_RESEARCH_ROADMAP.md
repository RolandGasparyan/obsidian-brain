# L99 — INSTITUTIONAL ALPHA RESEARCH ROADMAP

**Source:** Operator spec, 2026-05-02 (post-architecture-completion)
**Status:** Spec preserved verbatim · canonical research-operations protocol · supersedes ad-hoc validation-cycle planning
**Pre-req for activation:** None — this IS the research operating procedure that runs from D7+ until validated edge OR exhaustion of B-prime branches.

---

## I. The original spec (verbatim)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L99 — INSTITUTIONAL ALPHA RESEARCH ROADMAP
Edge Discovery Framework — Post-Architecture Phase
Version: 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STATUS:
Architecture complete (Layers 2–5 implemented).
No validated alpha.
Research phase begins.

Core Principle:
No edge → No capital.
No mechanism → No signal.
No stability → No deployment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 0 — SCIENTIFIC PROTOCOL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every factor must define:

1. Hypothesis
2. Mechanism
3. Expected Market Behavior
4. Failure Condition

Template:

Hypothesis:
<Clear directional statement>

Mechanism:
<Flow / behavioral / reflexive explanation>

Expected:
<What price should do and when>

Failure:
<What invalidates the idea>

No hypothesis → reject immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — DATA CLASS SELECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tier 1 (Test First):
- Exchange netflows (BTC, ETH)
- Stablecoin supply delta
- SOPR (Spent Output Profit Ratio)
- Realized Cap HODL Waves
- Funding Rate + OI divergence

Tier 2:
- Whale transfer clustering
- Miner outflows
- Dormant coin movement

Low Structural Edge Probability:
- Retail sentiment metrics
- Social media signals

Rule:
Only test one data class at a time.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — FACTOR CONSTRUCTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each factor:

1. Stationarity Check
   - ADF test
   - Reject non-stationary series

2. Lag Sweep
   Test forward returns:
   - t+1h
   - t+4h
   - t+1d
   - t+3d
   - t+7d

3. Quantile Spread Test
   - Split into Q1–Q5 buckets
   - Compute:
       Q5_mean_return − Q1_mean_return
   - Must exceed 60 bps after fees

4. Regime Separation
   - Test in low vol
   - Test in high vol
   - Must survive in ≥2 regimes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3 — STATISTICAL VALIDATION BATTERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Minimum thresholds:

Information Coefficient:
    |IC| ≥ 0.04
    t-stat ≥ 2.0

Profit Factor:
    PF ≥ 1.3

Expectancy:
    Positive after fee adjustment

Rolling Stability:
    No collapse in rolling 24-month windows

Monte Carlo:
    Shuffle trade order
    Ruin probability acceptable

Edge must not disappear when:
    - Lag shifted ±1
    - Sample split into halves

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4 — STRUCTURAL MECHANISM AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For any passing signal:

Ask:

1. Is this behavioral?
2. Is this flow-based?
3. Is this mechanical?
4. Is this reflexive?

If mechanism unclear → discard.

Backtest without mechanism = illusion.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5 — EDGE SURVIVABILITY STRESS TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Simulate:

- 2× fees
- 1.5× slippage
- 20% signal degradation
- Random noise injection

If edge collapses → reject.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 6 — KILL CRITERIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Immediate rejection if:

- IC flips sign OOS
- Q5−Q1 collapses post-2021
- Only profitable in one regime
- Overfit signature (spike then decay)

No emotional override allowed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 7 — DECISION TREE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If On-chain (B.2.3) fails:

Next branches:

B.2.2  Maker execution simulation
B.2.4  Cross-asset flow correlation
B.3    Options skew / gamma exposure

No random pivoting.
Structured pivot only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIMELINE PER DATA CLASS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Data collection:      5–10 days
Factor engineering:   3–5 days
Validation battery:   2–3 days
Decision:             1 day

≈ 2 weeks per disciplined cycle.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REALITY CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Microstructure edge failed.

On-chain is a different signal class.
Probability of real durable edge:
< 20%

Expectation:
Most factors fail at:
- Fee adjustment
- Regime stability
- Monte Carlo reshuffle

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Architecture is finished.

Now only two outcomes exist:

1. Validated alpha → activate L99 stack
2. No alpha → pivot or stop

No more layers.
No more complexity.
Only evidence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## II. Why this spec is the most important post-architecture document

This is the operator's explicit commitment to **stop building infrastructure** and **start measuring**. It aligns with:

- **ADR-001** (validate before deploy) — this IS the formal validation procedure
- **`feedback_drift_pattern.md`** memory — this spec EXPLICITLY rules out "more layers, more complexity" as drift
- **All 5 prior NULL findings** — Phase 6 kill criteria match the patterns those findings discovered (curve-fit, regime-fragility, fee-collapse)

Operator's "Reality Check" section names <20% probability of real durable edge. This is calibrated honesty — the prior null pattern is acknowledged, not denied.

---

## III. Mapping to existing tooling

### Phase 0 — Scientific Protocol

| Requirement | Existing implementation | Gap |
|---|---|---|
| Hypothesis statement | None — research-only convention | 🛑 needs research-log template |
| Mechanism statement | None | 🛑 |
| Expected behavior | None | 🛑 |
| Failure condition | None | 🛑 |

**Action:** create `wiki/research-log/` directory with a template enforcing Phase 0 fields. Each new factor gets one note before any code is written.

### Phase 1 — Data Class Selection

| Tier | Coverage |
|---|---|
| Tier 1: Exchange netflows | ✅ planned via `onchain_collector.py` (PR #6) — CryptoQuant netflow endpoint |
| Tier 1: Stablecoin supply delta | ⚠ partial — Glassnode supports it; not yet in collector |
| Tier 1: SOPR | ✅ planned — Glassnode endpoint |
| Tier 1: Realized Cap HODL Waves | 🛑 not planned for current collector |
| Tier 1: Funding Rate + OI divergence | 🛑 not planned (would need futures-exchange collector) |
| Tier 2: Whale clustering | ✅ planned — Whale Alert endpoint + WhaleTxBuffer |
| Tier 2: Miner outflows | ⚠ partial — CryptoQuant supports it; not yet in collector |
| Tier 2: Dormant coin movement | 🛑 not planned |
| Rejected: retail / social | ✅ rejected per spec; matches `decisions/2026-04-29-miroshark-research-only.md` |

**Action:** B.2.3 first cycle covers ~3 Tier 1 + 2 Tier 2 factors. Subsequent cycles can extend.

### Phase 2 — Factor Construction

| Requirement | Existing tool |
|---|---|
| Stationarity (ADF) | ✅ `microstructure_robust_check.py` filter #1 |
| Lag Sweep (1h/4h/1d/3d/7d) | ⚠ partial — current tooling tests 1m/5m/15m/1H; daily/weekly horizons not yet wired |
| Quantile Spread Q5−Q1 + 60 bps fee gate | ✅ `microstructure_signal_nature.py` |
| Regime Separation (≥2 regimes) | ✅ `microstructure_robust_check.py` filter #5 (vol-adjusted) |

**Action:** extend `microstructure_robust_check.py` lag sweep to include 1d/3d/7d for on-chain factors (which are slower-moving than orderbook microstructure).

### Phase 3 — Statistical Validation Battery

| Threshold | Existing check |
|---|---|
| \|IC\| ≥ 0.04, t-stat ≥ 2.0 | ✅ filters #1, #3 (BH-FDR) |
| PF ≥ 1.3 | ✅ in `professional_backtest.py` outputs |
| Positive expectancy after fees | ✅ filter #5 + signal_nature.py |
| Rolling 24-month stability | ⚠ partial — filter #2 does rolling WF; window length is configurable but on-chain data history is shorter than 24 months for most APIs |
| Monte Carlo (shuffle trade order) | ✅ via `champion/equity_mc_sim.py` (Layer 3, merged) |
| Lag shift ±1 stability | 🛑 not currently in 7-filter battery |
| Sample-split halves stability | ✅ filter #2 implicitly does this |

**Action:** add lag-shift-±1 robustness check to `microstructure_robust_check.py`. Other checks already covered.

### Phase 4 — Structural Mechanism Audit

| Question | Existing tool |
|---|---|
| Behavioral / flow / mechanical / reflexive classification | 🛑 not implemented |

**Action:** mechanism audit is a manual reasoning step, not a tool. Enforce via Phase 0 template requirement.

### Phase 5 — Edge Survivability Stress Test

| Stress | Existing tool |
|---|---|
| 2× fees | ✅ `microstructure_signal_nature.py` multi-fee scenarios |
| 1.5× slippage | ⚠ partial — slippage not currently parameterized |
| 20% signal degradation | 🛑 not implemented |
| Random noise injection | 🛑 not implemented |

**Action:** add stress-test wrapper to `microstructure_robust_check.py` that runs the full battery under 4 stress scenarios.

### Phase 6 — Kill Criteria

| Criterion | Detection mechanism |
|---|---|
| IC flips sign OOS | ✅ filter #2 captures this |
| Q5−Q1 collapse post-2021 | ⚠ partial — needs a "regime cut" date filter |
| Single-regime profitability | ✅ filter #5 |
| Overfit signature (spike then decay) | ⚠ partial — rolling-IC trace exists but no automated spike-decay classifier |

**Action:** add a "post-cutoff stability check" to validate edge holds in recent data, not just full sample.

### Phase 7 — Decision Tree

The spec's branches differ slightly from the existing `PHASE_B_DECISION_TREE.md`:

| Spec branch | Existing tree | Reconciliation |
|---|---|---|
| B.2.2 Maker execution simulation | B.2.2 (matches) | ✅ |
| B.2.4 Cross-asset flow correlation | B.2.4 in existing tree = L99 Hybrid Portfolio | ⚠ **conflict — see below** |
| B.3 Options skew / gamma exposure | not in existing tree | new branch |

### B.2.4 naming conflict

`PHASE_B_DECISION_TREE.md` (committed via PR #7) defines B.2.4 as the L99 Hybrid Portfolio orchestration layer. This spec redefines B.2.4 as Cross-asset flow correlation. **These are different things.**

**Resolution:** treat the two specs as evolving the decision tree. Hybrid Portfolio remains a *post-edge orchestration* concept (Layer 5 architecture). Cross-asset flow is a *new data class* for edge discovery.

Will rename in `PHASE_B_DECISION_TREE.md` (separate follow-up PR):
- B.2.4 → **B.2.5** Hybrid Portfolio orchestration (post-edge)
- New B.2.4 → Cross-asset flow correlation (data class)
- New B.3 → Options skew / gamma exposure (data class)

---

## IV. Coverage summary

Of the existing 7-filter battery + Layer 3 MC simulator + signal_nature multi-fee, this spec is **~80% covered** by existing tooling. The Phase 0 template + Phase 5 stress wrapper + Phase 6 post-cutoff check are the documented gaps.

**Implementable now (no edge proof needed):**
1. `wiki/research-log/_template.md` — Phase 0 hypothesis/mechanism/expected/failure form
2. `microstructure_robust_check.py` — add lag-shift-±1 + post-cutoff stability + stress wrapper

**Implementable when on-chain data arrives (post-keys):**
3. Daily/weekly lag horizons (1d/3d/7d) — not just intraday
4. Mechanism audit notes per Tier 1 factor

**NOT implementable now:**
- Phase 1 Tier 1/2 data — requires the 3 API keys (CryptoQuant + Glassnode + Whale Alert) currently the blocking prereq

---

## V. What this spec REPLACES

- **Ad-hoc validation cycles** → 2-week disciplined cycles per Phase 7 timeline
- **Vibes-based factor selection** → Tier 1/2 ranking with explicit rejection of retail/social
- **"Maybe we should also try X"** → structured pivot only, one data class at a time
- **"Architecture might fix it"** → "No more layers. Only evidence." (final rule)

This spec ends the architecture phase. After this, code commits should be:
1. Validation tooling (Phase 5/6 gap fixes)
2. Specific factor implementations following Phase 0 template
3. NOT new architectural layers

---

## VI. Linkage to merged L99 stack

The 5-layer L99 quant stack on main (PRs #9, #10, #11, #12, #13) is the **target** for validated alpha:

```
[Validated Alpha from research roadmap]
              │
              ↓
    Layer 2 (Regime Probability)
              │
              ↓
    Layer 3 (Capital Math / Kelly)
              │
              ↓
    Layer 4 (Velocity / Compounding)
              │
              ↓
    Layer 5 (Portfolio / Risk Governor)
              │
              ↓
        [Live execution]
```

Without the research roadmap producing validated alpha, the 17 merged modules sit dormant. **This spec is the missing input to the merged architecture.**

---

## VII. Order of operations (immediate)

1. ✅ This spec preserved verbatim + mapped + decisioned (this PR)
2. ⏳ User provides 3 free-tier API keys (CryptoQuant + Glassnode + Whale Alert) — **STILL blocking**
3. → On VPS deploy `onchain-collector.service` (already-built code in PR #6)
4. → 5–10 days passive collection (Phase 7 timeline)
5. → 3–5 days factor engineering on first Tier 1 factor (e.g., exchange netflows)
6. → 2–3 days run validation battery
7. → 1 day decision: 🟢 Candidate Alpha → 4-gate validation → Stage 1 paper deploy. 🛑 NO-GO → next factor or B-prime branch per Phase 7.

Total cycle: ~2 weeks per data class.

---

## VIII. ADR linkage

- **ADR-001** (validate before deploy) — this spec is the OPERATIONAL definition of "validate"
- **ADR-002** (Phase B direction) — spec extends decision tree with B.3 options skew
- **ADR-003** (D7 freeze) — expired; this spec applies post-D7

---

## IX. Sources

- Operator spec, 2026-05-02 (post-architecture commitment document)
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — branch tree (B.2.4 conflict to be resolved)
- [microstructure_robust_check.py](../../microstructure_robust_check.py) — 7-filter battery (~80% of Phase 2/3/5/6)
- [microstructure_signal_nature.py](../../microstructure_signal_nature.py) — quintile + multi-fee
- `champion/equity_mc_sim.py` (merged) — Phase 3 Monte Carlo
- [docs/specs/L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md) — companion validation framework spec
- [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](L99_HYBRID_PORTFOLIO_GOD_MODE.md) — orchestration target
- [docs/specs/L99_CAPITAL_MATHEMATICS.md](L99_CAPITAL_MATHEMATICS.md) — sizing target
- [docs/specs/L99_COMPOUNDING_VELOCITY.md](L99_COMPOUNDING_VELOCITY.md) — scaling target
- [docs/specs/L99_REGIME_PROBABILITY.md](L99_REGIME_PROBABILITY.md) — regime intel target
