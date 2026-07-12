# DECISION RECORD · STAGE 1 MICRO LIVE ARM · 2026-05-16

```
┌──────────────────────────────────────────────────────────────────┐
│  CLASSIFICATION   OPERATOR AUTHORIZATION · CAPITAL DEPLOYMENT     │
│  AUTHORITY        ROLAND GASPARYAN · SOVEREIGN OPERATOR           │
│  ARTIFACT TYPE    GOVERNANCE · AUDIT-READY · IMMUTABLE ON SIGN    │
│  STATUS           UNSIGNED · DRAFT · PENDING OPERATOR REVIEW      │
│  SCOPE            STAGE 1 ONLY · $10 USDT ISOLATED SUB-ACCOUNT    │
│  DURATION         ≤ 168 HOURS · AUTO-EXPIRE                       │
│  REVOCATION       OPERATOR-VERBATIM ONLY                          │
└──────────────────────────────────────────────────────────────────┘
```

> ⚠ **THIS DOCUMENT IS A DRAFT.** It is not authorization until every bracketed section is filled, the verbatim approval is typed by the operator, and the SHA-256 signature is placed below. Claude refuses to advance to Step 6 (Pre-Deploy Audit) of `MICRO_LIVE_OPERATOR_CHECKLIST.md` while this file remains unsigned.

---

## §0 · EXECUTIVE SUMMARY

The operator authorizes a **disciplined micro-capital live test** of the L99 trading system, bounded by the strictest envelope the governance stack permits. The test deploys **exactly $10 USDT** of operator capital into an **isolated Gate.io sub-account**, configured for **spot-only · SAFE_ONLY mode · no leverage · no withdrawals · no transfers**.

The system arms for a **maximum of 168 hours (7 calendar days)** with hard-coded **auto-freeze** on any of: 3 consecutive losses · ≥2% drawdown · slippage anomaly >0.1% · regime misclassification · API instability.

This document is the **single authoritative authorization** for Stage 1. No other artifact, message, or verbal acknowledgment substitutes for the verbatim signature in §10.

---

## §1 · DECISION (VERBATIM · DO NOT EDIT)

> **Authorize Stage 1 micro live test per Spec #14, with Spec #23 envelope applied where tighter, and Spec #22 sovereign-grade abort conditions enforced. Capital exposure capped at $10 USDT in isolated sub-account. Duration capped at 168 hours. All deviation auto-halts to paper.**

---

## §2 · CAPITAL ENVELOPE

```
LIVE CAPITAL                $10.00 USDT       (isolated sub-account ONLY)
MAIN ACCOUNT BALANCE        unchanged          (vault · untouched)
MAX SINGLE-TRADE RISK       $0.025             (0.25% of $10)
MAX EXPOSURE                $0.10              (1% of $10)
MAX ACCEPTABLE TOTAL LOSS   $0.50              (5% of $10 → auto-halt)
TARGET RETURN               N/A                (validation, not profit)
```

Any access to capital outside the sub-account is **prohibited by API permission scope**, verified in §6.

---

## §3 · ALLOWED SYSTEMS

| System | State | Reason |
|---|---|---|
| Spot trading (BTC/USDT) | ✅ ENABLED | Strategy requires market entry/exit |
| Take-profit orders (1.0%) | ✅ ENABLED | Mandatory exit discipline |
| Stop-loss orders (0.5%) | ✅ ENABLED | Mandatory loss discipline |
| Read-only balance/order REST | ✅ ENABLED | Auditability + state recovery |
| Auto-freeze triggers | ✅ ENABLED | Mandatory · cannot be disabled |
| Telemetry/observation logs | ✅ ENABLED | 7-day evaluation data |

---

## §4 · PROHIBITED SYSTEMS

| System | State | Enforcement |
|---|---|---|
| Margin trading | ❌ FORBIDDEN | Gate.io API permission scope |
| Futures trading | ❌ FORBIDDEN | Gate.io API permission scope |
| Lending/staking | ❌ FORBIDDEN | Gate.io API permission scope |
| Withdrawal | ❌ FORBIDDEN | Gate.io API permission scope |
| Internal transfer | ❌ FORBIDDEN | Gate.io API permission scope |
| Cross-account access | ❌ FORBIDDEN | Sub-account isolation |
| Position pyramiding | ❌ FORBIDDEN | `canary_config.NO_PYRAMIDING=true` |
| Capital migration | ❌ FORBIDDEN | `NO_CAPITAL_MIGRATION=true` |
| Strategy mutation in-flight | ❌ FORBIDDEN | `NO_STRATEGY_MUTATION=true` · canary SHA locked |
| Partial exit (must be 100% USDT) | ❌ FORBIDDEN | `FULL_EXIT_TO_USDT=true` |

Any attempt by the executor to invoke a prohibited system **auto-halts the service**.

---

## §5 · RISK LIMITS

```yaml
MODE                  MICRO_LIVE_SAFE
RISK_PER_TRADE        0.25%
MAX_RISK_HARDCAP      0.40%      # Article 3 inviolable
MAX_EXPOSURE          1.00%
MAX_CONCURRENT_POS    1
MAX_TRADES_PER_DAY    3
MAX_LIFETIME_HOURS    168        # 7 days
TP_PCT                1.00%
SL_PCT                0.50%
SESSION_DD_FREEZE     1.50%      # session-level kill
ACCOUNT_DD_FREEZE     2.00%      # account-level kill
CONSEC_LOSS_FREEZE    2          # 2 in a row → freeze (stricter than spec #14's "3")
SCAN_TOP_PAIRS        5
SCAN_INTERVAL         10s
```

Constitution Article 3 caps remain inviolable. Any field above tightened beyond the values shown is acceptable; any field loosened violates the envelope and **must auto-halt** at runtime.

---

## §6 · EMERGENCY HALT LOGIC

Auto-halt triggers (any one fires → `systemctl stop canary.service` + paper fallback + operator alert):

```
TRIGGER                          DETECTION                           ACTION
─────────────────────────────────────────────────────────────────────────────
2 consecutive losses             order_outcome stream                FREEZE
DD ≥ 2% ($0.20 from peak)        position state machine              FREEZE
Slippage > 0.1% deviation        fill-price vs target-price diff     FREEZE
Bayesian PANIC > 65% sustained   regime_detector.py                  FREEZE
API REST 3-fail streak           HTTP retry loop counter             FREEZE
Heartbeat missed > 60s           canary_killswitch.py watchdog       FREEZE
Strategy SHA mismatch            integrity hook                      KILL+ALERT
Unauthorized account modify      sub-account ledger diff             KILL+ALERT
Operator manual stop             systemctl stop                      STOP
```

Manual kill-switch (operator):
```bash
ssh root@167.71.24.86 'systemctl stop canary.service && \
  echo "{\"halted\":true,\"reason\":\"OPERATOR_MANUAL\",\"ts\":$(date +%s),\"engaged_by\":\"operator_manual\"}" \
    > /root/.l99/protection_halt.json && \
  systemctl status canary.service && \
  ss -tnp | grep -iE "gate|bybit"'
```

---

## §7 · OBSERVATION OBJECTIVES (7-DAY WINDOW)

The test gathers data to answer **four binary questions**, all of which must answer ✅ to advance to Phase B ($25):

| # | Question | Measure | Pass criteria |
|---|---|---|---|
| 1 | Does execution behave like backtest? | Realized R-multiple distribution | Within ±0.5σ of backtest expectancy |
| 2 | Is slippage acceptable? | Fill-vs-target deviation per trade | < 0.1% mean · < 0.3% p95 |
| 3 | Is the kill-switch sovereign? | Manual stop response time | < 5 seconds end-to-end |
| 4 | Does discipline hold under stress? | Violations per 100 trade-attempts | 0 violations · session caps respected |

If any answer ❌ → return to paper · diagnose · re-arm only after RCA + fix + new decision doc.

Daily observation file: `runtime/canary_observation_day_N.json` published by Claude.

---

## §8 · ROLLBACK CONDITIONS

**Automatic rollback** (any trigger from §6 fires):

```
1. canary.service           → stop (systemd)
2. open positions           → market-close to USDT (if any · spec mandates flat-on-exit)
3. .l99/protection_halt.json → engaged with reason field
4. arm.json                 → marked stale (status: "halted")
5. Operator alert           → fired (channel of operator's choice)
6. Investigation log        → seeded with last 100 decisions + last 24h trades
```

**Manual rollback** (operator decision, no auto-trigger):

```bash
# Operator runs from local terminal:
ssh root@167.71.24.86 'systemctl stop canary.service'
ssh root@167.71.24.86 'cat /root/canary/runtime/decisions.log | tail -100'
ssh root@167.71.24.86 'cat /root/canary/runtime/trades.log | tail -50'
```

**Post-rollback** (mandatory before any re-arm):

1. Read `audit/2026-05-XX/STAGE1_POST_TEST_REPORT.md` (Claude generates)
2. Decision: proceed to Phase B · fix-and-retry · permanently abandon
3. If retry → new decision doc · new arm.json · new SHA · re-clear L99

---

## §9 · OPERATOR AUTHORIZATION SECTION

```
┌──────────────────────────────────────────────────────────────────┐
│  Operator Name:       Roland Gasparyan                            │
│  Operator Role:       Sovereign · Sole Capital Authority          │
│  Authorization Date:  2026-05-17                                  │
│  Authorization Time:  13:52:27 UTC                                │
│  Geographic Location: Yerevan, Armenia                            │
│  Mental State:        ☑ Rested  ☑ Alert  ☑ Sober  ☑ Unhurried    │
│  Verifications:       ☑ Backtest evidence read                    │
│                       ☑ 3-round shadow report read                │
│                       ☑ Capital envelope acknowledged             │
│                       ☑ Prohibited systems acknowledged           │
│                       ☑ Risk limits acknowledged                  │
│                       ☑ Halt logic acknowledged                   │
│                       ☑ Rollback path tested mentally             │
│                       ☑ Main account balance noted: $1,960.65 USDT│
│                       ☑ Sub-account created · balance: $10 USDT   │
│                       ☑ API key file on VPS · chmod 600 verified  │
└──────────────────────────────────────────────────────────────────┘
```

**Operator rationale** (REQUIRED · why arm now · what new evidence supports this · what would change my mind):

> Arming Stage 1 now to validate end-to-end execution at minimum capital before any meaningful commitment. The MA50W10 strategy is the only L99-validated edge (Sharpe 2.81 across 7.5y backtest · max DD -23% · ~10 trades/year average) and 3 paper shadow rounds (R1 73.18 · R2 73.34 · R3 73.44 · all INSTITUTIONAL_READY · zero governance violations) have closed every pre-arm gate they can. The remaining unknown is real-exchange behavior — slippage variance, fill latency, API stability under regime change. $10 USDT is the smallest meaningful capital that surfaces these unknowns without material risk. Capital ceiling is bounded at -$0.50 with auto-halt; my main account ($1,960.65 USDT) remains untouched in vault. Mental state confirmed rested, alert, sober, unhurried. If any anomaly fires in the first 24 hours, the system auto-halts and I will sleep on the result before any re-arm.

---

## §10 · VERBATIM APPROVAL · SIGNATURE BLOCK

By signing below, I, **Roland Gasparyan**, on **2026-05-17**, authorize the Stage 1 micro live test against my Gate.io isolated sub-account, with capital strictly capped at **$10 USDT**. I confirm that:

1. All other capital remains in the main account, untouched.
2. The API key on `/root/canary/.api_key` is scoped to spot-trading only, no withdrawal, no transfer, no margin.
3. Auto-halt triggers per §6 are inviolable and cannot be overridden by Claude.
4. The kill-switch is my exclusive authority per **Constitution Article 6** + **Capital Defense Grid Layer 9**.
5. Claude will not execute live trades without all 5 operator gates (sub-account · API key · this signed doc · signed `canary_arm.json` · L99 verbatim clearance) confirmed.
6. The session expires automatically at **2026-05-23 23:59:59 UTC** (168 hours from arm).

I authorize this exact statement:

> **"I authorize Stage 1 micro live test per spec #14"**

```
Operator Signature:   Roland Gasparyan (electronically signed)
Operator Print:       Roland Gasparyan
Date:                 2026-05-17
Time (UTC):           13:52:27 UTC
```

---

## §11 · SHA-256 VERIFICATION

The `signature` field in `/root/canary/canary_arm.json` MUST equal the SHA-256 hash of the verbatim line above.

**Generation command** (operator runs on local terminal):

```bash
echo -n "I authorize Stage 1 micro live test per spec #14" | shasum -a 256
```

**Expected output format:**

```
<64-character-hex-digest>  -
```

The 64-character hex is the signature. Paste it into `canary_arm.json` `signature` field.

**Verification command** (Claude runs during §6 pre-deploy audit):

```bash
EXPECTED=$(echo -n "I authorize Stage 1 micro live test per spec #14" | shasum -a 256 | awk '{print $1}')
ACTUAL=$(jq -r '.signature' /root/canary/canary_arm.json)
[ "$EXPECTED" = "$ACTUAL" ] && echo "✓ signature valid" || echo "✗ MISMATCH · refuse to deploy"
```

---

## §12 · IMMUTABLE SACRED-LOCK SNAPSHOT (at sign time)

```
ARTIFACT                       SHA-256                                                            STATUS
────────────────────────────────────────────────────────────────────────────────────────────────────────────
canary/canary_strategy.py      704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143  LOCKED
canary/canary_config.json      25dccca16ed48950c24b9a2dc565166a93dbbe68a5f552689debec89d2f8bfb2  LOCKED
governance/AI_DISCIPLINE_       fa9e72ba630c16f54e0c894c52c1fa7a7d70956736171585330c92ed9ef4187d  LOCKED
  CONSTITUTION.md
governance/CAPITAL_DEFENSE_     7424beff7138d30cbc903feae5cdcacc5a729f2f478834ab7b6fb6d27e5a8947  LOCKED
  GRID.md
governance/MICRO_LIVE_           27755c3b9bea402da972fed93139664fcce7eec5c074b413bd0cca1cb17a46cc  LOCKED
  OPERATOR_CHECKLIST.md
─────────────────────────────────────────────────────────────────────────────────────────────────────────────
L99 halt status                ENGAGED · halted=true · OPERATOR_EMERGENCY_STOP_2026-05-12          PRE-CLEAR
Exchange write sockets         0                                                                  VERIFIED
Trading services               canary.service: inactive                                           VERIFIED
.api_key on VPS                <chmod 600 required · operator Step 2>                             PRE-VERIFY
canary_arm.json on VPS         <signature SHA-256 match required · operator Step 4>               PRE-VERIFY
Sub-account balance            10 USDT (target)                                                   PRE-VERIFY
canary_config envelope         matches §5 risk limits exactly · 24/24 fields                      VERIFIED 2026-05-16
```

> **§12 snapshot captured 2026-05-16 by pre-live audit.** Claude re-verifies these SHAs during §6 pre-deploy audit. If any artifact mutates between this signature and pre-deploy audit, the audit FAILS and the test is refused.

Claude computes the to-be-computed SHAs during §6 pre-deploy audit. If any artifact has mutated between this signature and pre-deploy audit, the audit fails and the test is refused.

---

## §13 · CROSS-REFERENCES

| Governing document | Section invoked | Purpose |
|---|---|---|
| `governance/AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md` | Spec #14 §IV | Operational protocol |
| `governance/AGGRESSION_UNLOCK_MICRO_LIVE_SAFE_GATE_v1.md` | Spec #23 | Envelope inheritance |
| `governance/MICRO_LIVE_OPERATOR_CHECKLIST.md` | Steps 1-9 | This is Step 3 |
| `governance/AI_DISCIPLINE_CONSTITUTION.md` | Art 3 + Art 6 | Hard caps + override |
| `governance/CAPITAL_DEFENSE_GRID.md` | Layer 9 | Kill-switch sovereignty |
| `audit/2026-05-13/SLIGHT_UNLOCK_ROUND_REPORT.md` | R2 results | Backtest evidence |
| `audit/2026-05-14/DISCIPLINED_UNLOCK_V1_ROUND_REPORT.md` | R3 + recommendation | Progression gate |
| `canary/canary_config.json` | Full config | Live execution params |
| `canary/ARMING_CHECKLIST.md` | Technical procedure | Step-by-step on VPS |
| `9-refusals-log.md` | Refusal #12 (and #11-#17) | Resolves on signature |

---

## §14 · SIGN-OFF AREA · OPERATOR FILLS

Sign below ONLY when:

- [x] §1 verbatim line is unedited
- [x] §2 capital figures match Gate.io sub-account balance (Guru33 = $10 USDT · verified 2026-05-17)
- [x] §3-§4 system permission lists match Gate.io API key scope (operator-attested · audit at Step 7)
- [x] §5 risk limits match `canary_config.json` (24/24 envelope fields match · SHA 25dccca16ed48950...)
- [x] §6 halt triggers verified in `canary_killswitch.py` (pre-live audit 2026-05-16 confirmed)
- [x] §7 four binary questions are understood and accepted
- [x] §8 rollback commands tested mentally
- [x] §9 all checkboxes ticked + rationale filled
- [ ] §10 verbatim line typed in chat by operator (DEFERRED to Step 8 of MICRO_LIVE_OPERATOR_CHECKLIST.md)
- [x] §11 SHA-256 generated and placed in `canary_arm.json` (a476c869199bea30...)
- [x] §12 sacred-lock snapshot accepted as immutable baseline

```
═══════════════════════════════════════════════════════════════════
                     OPERATOR SIGNATURE BLOCK
═══════════════════════════════════════════════════════════════════

Operator:        Roland Gasparyan

Signature:       Roland Gasparyan (electronically signed)

Date:            2026-05-17

Time (UTC):      13:52:27 UTC

SHA-256 of §1:   a476c869199bea3040a13cb996f1f4ea758bb0b989c3423d0f86ec7060f96a12
                 (64-char hex of "I authorize Stage 1 micro live test per spec #14")
                 Verify: echo -n "I authorize Stage 1 micro live test per spec #14" | shasum -a 256

Location:        Yerevan, Armenia

L99 verbatim:    [ ] typed in chat per MICRO_LIVE_OPERATOR_CHECKLIST.md Step 5
                 (intentionally UNTICKED · operator types in chat at Step 8 only after Step 7 audit PASS)

═══════════════════════════════════════════════════════════════════
                     END · OPERATOR SIGNATURE BLOCK
═══════════════════════════════════════════════════════════════════
```

**With all fields above filled (except L99 verbatim · intentionally deferred to Step 8), this document is SIGNED. Authorization is conditional on PRE-DEPLOY AUDIT pass at Step 7.**
