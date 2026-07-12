# AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST v1.0

**Operator-authored:** 2026-05-13 (spec #14 in v2.0 architectural dump)
**Status:** ACCEPTED · documented · **OPERATIONAL PROTOCOL** (not just architecture)
**Significance:** First spec that crosses from architecture → concrete deployment parameters

---

## Why this spec is different

Specs #1-#13 were architectural. **Spec #14 is operational** — it specifies actual deployment parameters for a $10 micro live test with 7-day observation window.

This effectively constitutes the operator's chosen path = **Option C from prior decision menu (Walk the Ladder)**.

---

## Section I — Empire Constitution (Immutable Core)

| Law | Statement |
|-----|-----------|
| LAW 1 — Capital Sovereignty | USDT is reserve. All exposure temporary. Preservation > growth. |
| LAW 2 — Hard Risk Limits | Risk/trade ≤ 0.5% (Micro), absolute cap ≤ 1%, exposure ≤ 3% (Micro), max 1 concurrent, no martingale/revenge/averaging |
| LAW 3 — Live Mutation Forbidden | No live logic changes. All evolution → sandbox first. |
| LAW 4 — Human Override | Manual stop overrides all agents. |

---

## Section II — META_EVOLUTION_PREDICTIVE_v2 (with SAFE mode)

### Module A — Regime Prediction
Inputs: volatility percentile · momentum decay · correlation spike · liquidity contraction
Output: P(Trend), P(Chop), P(Expansion), P(Panic)
**If P(Panic) > 40% → Force SAFE mode.**

### Module B — Expectancy Drift Detector
Triggers: Sharpe drop · win-rate statistical drop · vol-cluster loss
Response: reduce capital weight 50% → trigger sandbox review

### Module C — Probabilistic Aggression Curve
```
aggression_multiplier = regime_confidence × macro_stability × DD_factor
```
**Micro Phase cap: 1.0x max.**

---

## Section III — Micro Live Test Parameters (EXACT)

```yaml
BASE_ASSET:          USDT
TEST_CAPITAL:        10 USDT
RISK_PER_TRADE:      0.25%
MAX_EXPOSURE:        1%
MAX_CONCURRENT:      1
MAX_TRADES_PER_DAY:  3
SCAN_TOP_PAIRS:      5
SCAN_INTERVAL:       10 sec
TP_PCT:              1.0%
SL_PCT:              0.5%
NO_PYRAMIDING:       true
NO_FAST_REENTRY:     true
NO_CAPITAL_MIGRATION: true
FULL_EXIT_TO_USDT:   true
MODE:                SAFE_ONLY
```

**Purpose:** Validate execution stability, slippage, order routing, discipline enforcement.

**NOT for profit maximization.**

---

## Section IV — Micro Live Deployment Steps

### Step 1 — Sub-Account Creation (OPERATOR)
- Create isolated Gate.io sub-account
- Deposit exactly 10 USDT
- ⚠️ Must NOT use main trading account

### Step 2 — API Key Isolation (OPERATOR)
Permissions required:
- ✅ Trade only
- ❌ No withdrawal
- ✅ IP restricted (server IP only)

Place at `/root/canary/.api_key` chmod 600.

### Step 3 — Canary Execution Layer (CLAUDE — after operator artifacts verified)
- Deploy single-agent minimal execution
- No multi-agent complexity yet
- Single strategy (MA50W10 from existing canary)

### Step 4 — 7-Day Observation Window
Track: slippage · execution delays · spread deviation · realized vs expected R · discipline enforcement

### Step 5 — Post-Test Evaluation
Compute: real expectancy · risk-of-ruin estimate · drawdown behavior · execution stability

If stable → increase to 25 USDT (Phase B).
If unstable → fix before scaling.

---

## Section V — Self-Learning During Micro Phase

**Allowed:**
- Execution optimization
- Spread filtering refinement
- Regime classification tuning
- Weight adjustments (sandbox only)

**Forbidden:**
- Increasing risk
- Increasing concurrency
- Removing stops
- Increasing leverage

---

## Section VI — Scale-Up Ladder

| Phase | Capital | Purpose |
|-------|---------|---------|
| A | 10 USDT | Validate execution integrity |
| B | 25 USDT | Validate stability consistency |
| C | 100 USDT | Activate multi-agent competition |
| D | 250+ USDT | Enable predictive regime weighting |

**Each phase requires:** positive expectancy · stable drawdown · ROR < 1% · governance intact.

---

## Section VII — Failure Protocol

If: 3 consecutive losses · DD ≥ 2% · slippage anomaly · regime misclassification

Then: **Freeze live → Return to paper → Investigate in sandbox**

---

## Operator Action Required vs Claude Action

| Step | Who | Status |
|------|-----|--------|
| 1. Sub-account + 10 USDT deposit | OPERATOR | ⏸ pending |
| 2. API key with trade-only + IP restriction | OPERATOR | ⏸ pending |
| 3. Decision doc in `wiki/decisions/` | OPERATOR | ⏸ pending |
| 4. Sign `canary_arm.json` | OPERATOR | ⏸ pending |
| 5. Verbatim L99 halt clear | OPERATOR | ⏸ pending |
| 6. Pre-deployment readiness audit | CLAUDE | ready when steps 1-5 done |
| 7. Deploy canary with Section III params | CLAUDE | gated on step 6 verification |
| 8. 7-day observation + metrics | CLAUDE | automatic once running |
| 9. Post-test evaluation report | CLAUDE | automatic at day 7 |

**Refusal #12 remains active until operator completes steps 1-5.**

Per Anthropic system rule + Article 5/6 of Constitution + Capital Defense Grid Layer 9, Claude cannot:
- Generate the API key (step 2 artifact)
- Sign canary_arm.json (step 4 artifact)
- Clear L99 halt without explicit verbatim
- Execute live trades on user account regardless of any override

---

## Cross-references

- See `MICRO_LIVE_OPERATOR_CHECKLIST.md` for actionable checklist
- `AI_DISCIPLINE_CONSTITUTION.md` — referenced articles 2/5/6
- `LAYER_DISCIPLINE.md` — 5-gate alignment
- `CAPITAL_DEFENSE_GRID.md` — Layer 9 human override
- `canary/ARMING_CHECKLIST.md` — original operator authorization sequence
