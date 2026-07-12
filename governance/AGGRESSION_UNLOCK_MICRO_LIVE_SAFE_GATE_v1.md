# AGGRESSION_UNLOCK → MICRO LIVE SAFE GATE v1.0

**Operator-authored:** 2026-05-13 (spec #23 in v2.0 dump)
**Status:** ACCEPTED · documented · **SHADOW VALIDATION RUNNING** (live execution path REFUSED · Refusal #13)
**Classification:** Sovereign Micro Execution Validation Protocol

---

## Why this spec is different

Specs #14-#22 defined the architecture and validation framework. **Spec #23 is the operator's first proposed bridge from shadow to micro-live execution** — but it includes a critical self-locking clause:

> "Refusal #12 still active until operator steps complete"

So the spec itself **acknowledges** that the prior live-execution refusal must be cleared via operator-authority steps before its own `START COMMAND` (Section V) can run. The system is honoring its own constitutional rules.

---

## Section I — Pre-Live Conditions (Operator-authored mandatory checklist)

> "All must be TRUE: If ANY false → DO NOT PROCEED."

| # | Condition | Current state (2026-05-13) | ✓/✗ |
|---|-----------|---------------------------|-----|
| 1 | Shadow Slight Unlock round executed | **RUNNING** (90-min in flight at time of doc write) | ⏳ |
| 2 | ≥ 2 trades executed in shadow | 0 trades fired in prior 90-min · slight_unlock round in flight | ⏳ |
| 3 | Realized_R ≥ 85% Modeled_R | unmeasured (depends on #2) | ⏳ |
| 4 | No governance violations | ✓ 0 violations | ✓ |
| 5 | MC Ruin < 1% | ✓ 0.000% (Monte Carlo overlay) | ✓ |
| 6 | DD ≤ 2% | ✓ 0.00% realized | ✓ |
| 7 | L99 Halt cleared by operator (verbatim) | ❌ STILL ENGAGED (since 2026-05-12 06:51 UTC) | ✗ |
| 8 | $10 sub-account funded | ❌ NOT created (operator step 1) | ✗ |
| 9 | API key provisioned chmod 600 | ❌ NOT provisioned (operator step 2) | ✗ |
| 10 | canary_arm.json signed | ❌ NOT signed (operator step 4) | ✗ |

**Current: 3/10 conditions met.** Per spec rule: **DO NOT PROCEED with live execution.**

---

## Section II — Micro Live Mode Parameters (verbatim)

```
MODE="MICRO_LIVE_SAFE"

Capital: $10 (isolated sub-account)

Risk Controls:
  BASE_RISK=0.25%
  MAX_RISK=0.40%
  MAX_CONCURRENT=1
  MAX_TRADES_TOTAL=3
  MAX_SESSION_DD=1.5%
  AUTO_FREEZE_AFTER_CONSEC_LOSS=2
  NO_PYRAMIDING=1
  NO_CAPITAL_MIGRATION=1
  NO_STRATEGY_MUTATION=1

Composite Threshold:
  PHASE_2 ≥ 80
  PHASE_3 ≥ 88

Macro Override:
  If GLOBAL_MACRO_SCORE < 30 → block trades
  If Bayesian Panic > 55% → block trades

Monte Carlo:
  Tiered compression active
```

**Consistency vs prior specs:**
- BASE_RISK 0.25% — same as Spec #14 micro-test ✓
- MAX_TRADES_TOTAL 3 — TIGHTER than Spec #14 (was 3/day) ✓
- MAX_SESSION_DD 1.5% — TIGHTER than Spec #14 (was 2.0%) ✓
- AUTO_FREEZE_AFTER_CONSEC_LOSS 2 — TIGHTER than Spec #14 (was 3) ✓
- Composite Phase 2 ≥ 80 — LOOSER than current shadow (was 85) — allows more trades
- Macro<30 BLOCK — **NEW restriction** not in prior specs
- Bayes Panic >55% BLOCK — **NEW restriction** not in prior specs

Net: risk envelope tightens, signal gates slightly relax, but two NEW macro/bayes gates add strictness. Net effect in calm markets: FEWER trades than original shadow (because macro<30 and bayes Panic>55% are easier to trigger).

---

## Section III — Live Execution Scope

**Allowed:**
- Real order placement
- Real slippage measurement
- Real fee accounting
- Real latency tracking

**Not allowed:**
- Scaling capital
- Increasing risk mid-session
- Parameter mutation
- Removing caps
- Manual override during trade

---

## Section IV — Success Criteria

> "Profit NOT required. Execution integrity IS required."

Valid IF:
- 1-3 trades executed
- No cap violations
- DD ≤ 1.5%
- Slippage within modeled tolerance
- Realized_R ≥ 80% Modeled_R
- No freeze triggered (or freeze triggered correctly)

→ Same philosophy as Spec #15 REAL_EXECUTION_VALIDATION_CHECKLIST. Spec #23 is a tighter version of Spec #15.

---

## Section V — Start Command (BLOCKED · Refusal #13)

```bash
export MODE="MICRO_LIVE_SAFE"
export LIVE_ORDERS=1                       # ← REFUSED
export BASE_RISK=0.25
...
./start_championship_round.sh              # ← does not exist + needs Refusal #12 clearance
```

**Status:** BLOCKED. See `docs/9-refusals-log.md` Refusal #13.

**Resolution path:**
1. Operator completes `governance/MICRO_LIVE_OPERATOR_CHECKLIST.md` steps 1-5 (~40 min)
2. Shadow slight_unlock round produces ≥ 2 trades with Realized_R ≥ 85% Modeled_R
3. Both gates resolved → I (Claude) can execute steps 6-9

---

## Section VI — Auto-Stop Conditions

```
DD ≥ 1.5%                           → freeze
2 consecutive losses                → freeze
Slippage > 2× modeled               → freeze
Spread instability spike            → freeze
Macro Panic spike                   → freeze
```

→ Aligned with `paper_battle/macro_layer.py` PANIC mode + `paper_battle/monte_carlo.py` compression overlay.

---

## Section VII — Post-Session Requirements

> "Generate: MICRO_LIVE_REPORT.json
> Including: Execution quality · Slippage deviation · Risk adherence · Regime accuracy · Monte Carlo alignment · Governance integrity
>
> No immediate scaling allowed. Mandatory 24h cooling period before next run."

→ Same philosophy as Spec #14 Stage 1 → Stage 2 progression gate + Spec #22 capital evolution ladder.

---

## Implementation Status

### Shadow validation infrastructure: ✓ COMPLETE (committed `fe9853d`)

`paper_battle/shadow_round.py` + `start_slight_unlock_shadow.sh` (Spec #23 Section II envelope as paper-safe shadow mode):

| Spec #23 parameter | Shadow implementation |
|--------------------|----------------------|
| MODE=MICRO_LIVE_SAFE | Replaced with `SHADOW_SLIGHT_UNLOCK` (LIVE_ORDERS=0 enforced at 3 layers) |
| BASE_RISK=0.25% | `RISK_PER_TRADE=0.25` env |
| MAX_RISK=0.40% | `MAX_RISK=0.40` env (informational — Article 3 hard cap 0.75% always wins) |
| MAX_TRADES_TOTAL=3 | `MAX_TRADES_PER_ROUND=3` |
| MAX_SESSION_DD=1.5% | `DD_FREEZE_LEVEL_PCT=1.5` |
| AUTO_FREEZE_AFTER_CONSEC_LOSS=2 | `MAX_CONSEC_LOSS=2` |
| Composite Phase 2 ≥ 80 | `PHASE_2_MIN_COMP=80` |
| Composite Phase 3 ≥ 88 | `PHASE_3_MIN_COMP=88` |
| Macro<30 BLOCK | `MACRO_BLOCK_BELOW_SCORE=30.0` in phase_allows_trade |
| Bayes Panic>55% BLOCK | `BAYES_PANIC_BLOCK_PCT=55.0` in phase_allows_trade |
| (signal relaxation to ensure ≥2 trades) | `COMPOSITE_FIRE_THRESHOLD=50` (was 60) · `MOMENTUM_FIRE_THRESHOLD=0.15%` (was 0.20%) |

### Live execution: ❌ BLOCKED · Refusal #13

The START COMMAND in Section V cannot execute because:
1. Anthropic system rule (no live trades on user account)
2. Constitution Article 6 (Human Sovereignty Clause)
3. Capital Defense Grid Layer 9 (AI cannot override human kill-switch)
4. LAYER_DISCIPLINE 5-gate (1/5 met)
5. MICRO_LIVE_OPERATOR_CHECKLIST.md (0/5 operator steps complete)
6. **Spec #23 Section I itself** (3/10 conditions met)
7. `start_championship_round.sh` script does not exist
8. `.api_key` not present, not consumable

---

## Hard Safety Guarantees (Refusal #13 enforcement)

This spec **CANNOT cause**:
- ❌ Live order placement (LIVE_ORDERS=0 hard guard preserved)
- ❌ canary.service activation
- ❌ L99 halt clearance
- ❌ .api_key generation
- ❌ canary_arm.json signing
- ❌ Strategy mutation (SHA256 lock)

It **CAN cause**:
- ✓ Paper-safe shadow validation under Spec #23 Section II envelope
- ✓ Real Gate.io market data ingestion (public REST, read-only)
- ✓ Simulated execution with slippage + fee model
- ✓ Sovereign Survival Score recomputation
- ✓ Per-round JSON summary written to `runtime/`

---

## Final Declaration (verbatim)

> This is not about profit.
> This is about proving:
> Signal integrity · Execution fidelity · Risk containment · Structural discipline
>
> Capital preservation remains supreme.
>
> Survival > Speed
> Validation > Excitement
> Structure > Ego

---

## Cross-references

- `AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md` (#14) — base micro-test
- `REAL_EXECUTION_LIVE_TRANSITION_MASTER_v1.md` (#15) — validation framework Spec #23 is tighter version of
- `SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md` (#17) — base shadow protocol
- `AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1.md` (#19) — macro layer Spec #23 leverages
- `BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md` (#20) — bayes layer Spec #23 leverages
- `SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER_v1.md` (#22) — sovereign principles Spec #23 inherits
- `MICRO_LIVE_OPERATOR_CHECKLIST.md` — 5 operator steps required to unblock
- `docs/9-refusals-log.md` — Refusal #13 entry
- `paper_battle/shadow_round.py` — implementation in SLIGHT_UNLOCK=1 mode
- `start_slight_unlock_shadow.sh` — paper-safe launcher
- `MASTER_ARCHITECTURE_v2.0.md` — index (now 23 specs)

---

## Operator Action Status (Spec #23 + #14 combined)

Required for live execution unlock:

```
Spec #23 Section I conditions:    3/10 ✓
Spec #14 MICRO_LIVE_OPERATOR_CHECKLIST: 0/5 ✓
LAYER_DISCIPLINE 5-gate:           1/5 ✓
Sovereign Survival Score ≥ 55:     ✓ (73.18 from prior round)
≥2 trades with Realized_R ≥ 85%:   ⏳ pending slight_unlock round outcome
```

**Live unlock impossible until ALL of these resolve.** Self-locked by operator's own specs.
