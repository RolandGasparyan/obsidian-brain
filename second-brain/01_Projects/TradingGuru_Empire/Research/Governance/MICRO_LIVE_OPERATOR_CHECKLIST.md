# MICRO LIVE OPERATOR CHECKLIST — $10 USDT Test

**Created:** 2026-05-13
**Source spec:** `AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md` (spec #14)
**Status:** WAITING ON OPERATOR

This document translates Spec #14 Section IV into an actionable checklist with clear OPERATOR vs CLAUDE responsibilities. **Refusal #12 stays active until all OPERATOR steps are complete.**

---

## 🎯 Goal

Deploy $10 USDT canary in disciplined micro-live test per Spec #14 parameters. Validate execution stability, slippage, discipline enforcement. Earn the right to scale to Phase B ($25) → Phase C ($100) → Phase D ($250+).

---

## ✋ Why Claude cannot do these steps himself

Per Anthropic system rule + `AI_DISCIPLINE_CONSTITUTION` Articles 5-6 + `CAPITAL_DEFENSE_GRID` Layer 9, Claude is permanently prohibited from:
- Executing live trades on user accounts
- Generating API keys (security violation)
- Signing arm files (operator-authority artifacts)
- Clearing human kill-switch (L99 halt) without explicit verbatim

These are **architectural invariants**, not Claude defensiveness. The operator authored every single one of them.

---

## 📋 Operator Action Checklist (steps 1-5)

### ☐ Step 1 — Sub-Account Creation
**Who:** Operator
**Time estimate:** 10 minutes
**Steps:**
1. Log into Gate.io main account
2. Create new **sub-account** (NOT main account)
3. Name it: `tradingguru-canary-micro-2026-05-XX`
4. Deposit **exactly 10 USDT** from main account to sub-account
5. Verify deposit completed in sub-account balance

**Verification (Claude can do once you confirm):**
```bash
# Operator runs (Claude verifies via API later):
# Check sub-account balance shows 10 USDT
```

---

### ☐ Step 2 — API Key Generation
**Who:** Operator
**Time estimate:** 5 minutes
**Steps:**
1. In the **sub-account** (NOT main), create new API key
2. Permissions:
   - ✅ **Spot trading: enabled**
   - ❌ **Futures trading: disabled**
   - ❌ **Margin: disabled**
   - ❌ **Withdrawal: disabled** ← critical
   - ❌ **Internal transfer: disabled**
3. IP whitelist: add server IP `167.71.24.86` only
4. Copy API Key + Secret
5. SSH to server: `ssh root@167.71.24.86`
6. Write file: `/root/canary/.api_key`
7. Format:
   ```
   GATE_API_KEY=<your_api_key>
   GATE_API_SECRET=<your_api_secret>
   ```
8. Set permissions: `chmod 600 /root/canary/.api_key`
9. Verify: `ls -la /root/canary/.api_key` (should show `-rw-------`)

**⚠ Critical:** Do NOT share keys in chat. Do NOT commit to git. Hook will refuse.

---

### ☐ Step 3 — Decision Document
**Who:** Operator (Claude can help format if you share content)
**Time estimate:** 20 minutes
**Path:** `~/Desktop/agent/docs/decisions/2026-05-XX-stage1-micro-arm.md`

Required sections:
1. **Backtest evidence** — cite MA_STRATEGY.md (Sharpe 2.81, +3427% over 7.5y)
2. **Operator review** — your explicit acknowledgment of:
   - $10 max capital
   - 0.25% risk per trade ($0.025 per trade)
   - Max 3 trades per day
   - TP 1.0% / SL 0.5%
   - SAFE_ONLY mode
   - 7-day observation window
3. **Rationale** — why now, why this strategy, why these parameters
4. **Rollback path** — what happens if anything goes wrong (auto-halt triggers + manual stop procedure)
5. **Verbatim approval signature** — your name + timestamp + explicit statement

Template:
```markdown
# Decision — Stage 1 Micro Live Arm · 2026-05-XX

## Decision
Authorize $10 USDT canary live test per Spec #14 parameters.

## Backtest evidence
[cite MA_STRATEGY.md]

## Authorized parameters
- Max capital: $10 USDT
- Risk per trade: 0.25%
- Max trades/day: 3
- TP: 1.0%
- SL: 0.5%
- Mode: SAFE_ONLY
- Observation window: 7 days

## Rationale
[your reasoning]

## Rollback path
[exact commands to stop]

## Verbatim approval
"I, Roland Gasparyan, authorize the Stage 1 micro live test
on 2026-05-XX with the parameters listed above. Capital at risk
is limited to $10 USDT. All other capital remains in vault.
Auto-halt triggers per LAW 3 and Section VII Failure Protocol."

Signed: Roland Gasparyan
Date: 2026-05-XX
```

---

### ☐ Step 4 — Sign canary_arm.json
**Who:** Operator
**Time estimate:** 5 minutes
**Path:** `/root/canary/canary_arm.json`

Format:
```json
{
  "armed_by": "Roland Gasparyan",
  "armed_at": "2026-05-XX-T-HH:MM:SS-UTC",
  "decision_doc": "docs/decisions/2026-05-XX-stage1-micro-arm.md",
  "stage": 1,
  "max_capital_usd": 10,
  "max_loss_acceptable_usd": 0.50,
  "max_trades_per_day": 3,
  "max_lifetime_hours": 168,
  "verbatim_approval": "I authorize Stage 1 micro live test per spec #14",
  "signature": "<your sha256 hash of the verbatim line above>"
}
```

To generate signature:
```bash
echo -n "I authorize Stage 1 micro live test per spec #14" | shasum -a 256
```

Place file with `chmod 600`.

---

### ☐ Step 5 — Verbatim L99 Halt Clearance
**Who:** Operator
**Time estimate:** 1 minute
**Action:** Type in chat to me, exactly:

```
CLEAR_L99_HALT_2026-05-XX_STAGE1_MICRO_ARM_AUTHORIZED
```

(Replace `XX` with actual date.)

This is your **kill-switch override** per Capital Defense Grid Layer 9 + Constitution Article 6.

---

## 🤖 Claude Action Checklist (steps 6-9, auto after operator steps verified)

### ☐ Step 6 — Pre-Deployment Audit
**Who:** Claude
**Trigger:** After operator confirms steps 1-5 complete
**Actions:**
- Verify `/root/canary/.api_key` exists, chmod 600
- Verify `/root/canary/canary_arm.json` exists with valid signature
- Verify decision doc at correct path
- Verify L99 halt clearance verbatim received
- Verify all 5 LAYER_DISCIPLINE gates met
- Test Gate.io API connectivity (read-only call first, balance check)
- Confirm sub-account has 10 USDT
- Run `./sync.sh verify` final check

Output: PASS/FAIL report. If any fail → block deployment.

### ☐ Step 7 — Canary Deployment
**Who:** Claude
**Trigger:** Step 6 PASS
**Actions:**
- Apply Spec #14 Section III parameters to `canary_config.json` (validation only — file is locked)
- `systemctl start canary.service`
- Verify service active
- Watch first 5 minutes for any errors

### ☐ Step 8 — 7-Day Observation
**Who:** Claude (automatic)
**Tracks per Section IV:**
- Slippage per trade
- Execution delays (request → fill latency)
- Spread deviation
- Realized vs expected R-multiple
- Discipline enforcement (cooldowns honored? caps respected?)

Daily summary published to `runtime/canary_observation_day_N.json`.

### ☐ Step 9 — Post-Test Evaluation Report
**Who:** Claude
**Trigger:** Day 7 reached OR Failure Protocol triggered
**Output:** `docs/decisions/2026-05-XX-stage1-post-test-report.md`

Computes per Section V:
- Real expectancy (Σ R-multiples / trades)
- Risk-of-ruin estimate (Kelly + observed variance)
- Drawdown behavior (max DD, recovery time)
- Execution stability (slippage variance)

If stable → recommendation: proceed to Phase B ($25 USDT).
If unstable → recommendation: fix issues, retry, or abandon.

---

## ⚠ Failure Protocol (per Spec #14 Section VII)

Auto-triggers freeze + return to paper:
- 3 consecutive losses
- DD ≥ 2% ($0.20 from peak)
- Slippage anomaly (> 0.1% deviation)
- Regime misclassification

When triggered:
- `systemctl stop canary.service` (auto)
- Operator alerted
- Sandbox investigation begins

---

## 🛡 Sacred locks (verify before each step)

```bash
~/Desktop/agent/sync.sh verify
```

Must show:
- Canary SHA256: `704dd5725a909fe3f6...`
- L99 halt: engaged (until step 5)
- Exchange sockets: 0 (until step 7)
- All trading services: inactive (until step 7)

---

## Current state

```
Step 1 (Sub-account):       ⏸ PENDING (operator)
Step 2 (API key):           ⏸ PENDING (operator)
Step 3 (Decision doc):      ⏸ PENDING (operator)
Step 4 (canary_arm.json):   ⏸ PENDING (operator)
Step 5 (L99 verbatim clear): ⏸ PENDING (operator)
─────────────────────────────────────────────────
Step 6 (Pre-deploy audit):  WAITING on steps 1-5
Step 7 (Canary deploy):     WAITING on step 6
Step 8 (Observation):       WAITING on step 7
Step 9 (Post-test report):  WAITING on step 8
```

Tell me when you've completed steps 1-5 (or any subset), and I'll proceed with my side.

If you'd rather pause and walk this tomorrow rested → engine v1.2 stays stable, capital safe, no clock pressure.

---

## Cross-references

- `AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md` (spec #14) — source spec
- `AI_DISCIPLINE_CONSTITUTION.md` — Articles 5-6 enforcement
- `LAYER_DISCIPLINE.md` — 5-gate alignment
- `canary/ARMING_CHECKLIST.md` — original operator authorization procedure
- `9-refusals-log.md` — refusal #12 will resolve when steps 1-5 complete
