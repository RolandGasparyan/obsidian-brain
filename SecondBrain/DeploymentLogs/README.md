---
type: deployment-logs-index
date: 2026-05-13
tags: [deployment, ladder, sessions, handoff, milestones]
ai-first: true
source: ~/Desktop/agent/session-notes/
---

# Deployment Logs

> For future Claude: This folder tracks the **6-stage capital evolution ladder** (Stage 0 paper → Stage 5 institutional) and session-by-session deployment progress. **Currently at Stage 0** (paper-only). Stage 1 ($10 micro-live) requires operator completing `MICRO_LIVE_OPERATOR_CHECKLIST.md` steps 1-5.

---

## The 6-Stage Capital Evolution Ladder

Per Spec #14 + Spec #22 consensus:

| Stage | Capital | Purpose | Status |
|-------|---------|---------|--------|
| **0** | **0 (paper)** | **Validate engine logic** | ← **current** |
| 1 | $10 USDT | Validate execution integrity (slippage / spread / fills) | ⏳ Pending operator steps 1-5 |
| 2 | $25 USDT | Validate stability consistency | gated on Stage 1 PASS |
| 3 | $100 USDT | Activate multi-agent competition | gated on Stage 2 multi-cycle proof |
| 4 | $250+ USDT | Enable predictive regime weighting | gated on Stage 3 success |
| 5 | $1K+ USDT | Multi-agent live + institutional features | gated on Stage 4 fund-grade proof |

**Each stage requires:** positive expectancy · stable drawdown · ROR < 1% · governance intact.

**No stage skipping permitted** (per Spec #7 + Spec #9 explicit + Constitution Article 6).

---

## Stage 1 Requirements (per MICRO_LIVE_OPERATOR_CHECKLIST)

### Operator-authority steps (cannot be done by AI):

1. **Gate.io sub-account** + 10 USDT deposit (~10 min)
2. **API key** (trade-only · IP-whitelist `167.71.24.86` · no withdrawal) at `/root/canary/.api_key` chmod 600 (~5 min)
3. **Decision doc** at `docs/decisions/2026-05-XX-stage1-micro-arm.md` with backtest evidence + verbatim approval (~20 min)
4. **Sign canary_arm.json** with SHA256 signature of verbatim approval line (~5 min)
5. **Verbatim L99 clearance**: chat-type `CLEAR_L99_HALT_2026-05-XX_STAGE1_MICRO_ARM_AUTHORIZED` (~1 min)

**Total operator time: ~40 min**

### Claude-authority steps (auto after operator steps verified):

6. Pre-deployment audit (5/5 LAYER_DISCIPLINE gates + API connectivity + balance check)
7. `systemctl start canary.service` with Spec #14 params
8. 7-day observation (slippage · execution delays · R-multiple · discipline enforcement)
9. Post-test evaluation report → recommendation Phase B ($25) or rollback

---

## Stage 1 PASS Criteria (per Spec #14 + Spec #15)

| Criterion | Threshold | Source |
|-----------|-----------|--------|
| Execution Stability Score | ≥ 80 | Spec #15 Section I |
| Realized_R / Modeled_R | ≥ 90% | Spec #15 Section I |
| Risk caps violations | 0 | Constitution Article 3 |
| Max DD vs Monte Carlo band | within p95 | Spec #20 Part II |
| Risk-of-ruin | < 1% | Constitution Article 1 |
| Sovereign Survival Score | ≥ 70 (INSTITUTIONAL_READY) | Spec #22 Section VII |
| Min trades captured | 20-30 over 7d | Spec #14 Section IV |

If PASS → Stage 2 ($25)
If FAIL → return to paper + investigate

---

## Failure Protocol (Spec #14 Section VII)

Auto-triggers freeze + return to paper:
- 3 consecutive losses
- DD ≥ 2% ($0.20 from peak at Stage 1)
- Slippage anomaly (> 0.1% deviation)
- Regime misclassification

When triggered:
- `systemctl stop canary.service` (auto)
- Operator alerted
- Sandbox investigation begins

---

## Session Handoffs (chronological)

### Session 2026-05-12 (prior)
- Operator-authored Capital Defense Grid v1.0 (10 layers)
- Operator-authored Layer Discipline 5-gate
- Operator-authored Refusal log entries 1-11
- L99 halt ENGAGED 06:51 UTC
- Capital ringfenced at $1,980.90 USDT

### Session 2026-05-13 (this one)
- 22 specs documented (one architectural day · 12+ governance commits)
- Shadow round runner v1.1 built + macro/bayes/MC/survival_metrics modules
- Refusal #12 logged (live micro execution refused per Constitution Article 6)
- MICRO_LIVE_OPERATOR_CHECKLIST.md authored (9-step path to Stage 1)
- 90-min shadow round in flight (PID 41772, ~63 min elapsed at audit time)
- Sovereign Production Discipline 7-phase audit completed (this command)
- Status: STILL Stage 0 paper · all locks intact · refusal #12 ACTIVE

---

## Frontend Deployment State (separate repo)

→ Lives in `~/Desktop/ai-trading-championship/` (this repo)
→ Last build: `index-DlpRpMsk.js` deployed to `https://tradingguru.ai`
→ Routes: `/`, `/championship`, `/racing`, `/arena`, `/dashboard`, `/predictions`, `/control`
→ Tag: `v1.0` on `tradingguru-agent` mirror repo

---

## What this Sovereign Setup audit accomplished (2026-05-13 phases 1-7)

1. Phase 1: Structural audit → repo structurally clean, no production blockers
2. Phase 2: Design normalization → N/A for agent scope (frontend separate repo)
3. Phase 3: Data purification → zero fake/mock data, comprehensive paper labeling
4. Phase 4: Sovereign structure → 5 layers verified, sacred locks all pass
5. Phase 5: Obsidian SecondBrain → 11 markdown files written (this folder + 9 siblings + root)
6. Phase 6: GitHub production → see `audit/2026-05-13/RELEASE_NOTES_v1.1.md`
7. Phase 7: Deployment readiness → see `audit/2026-05-13/DEPLOYMENT_READY_CHECKLIST.md`

---

## Cross-links

- [[CapitalDefense/README]] — MICRO_LIVE_OPERATOR_CHECKLIST full text
- [[ExecutionEngine/README]] — current shadow runner in flight
- [[Architecture/README#Capital Evolution Ladder]] — long-horizon ladder

## Source-of-truth

- `~/Desktop/agent/session-notes/2026-05-13-session-handoff.md`
- `~/Desktop/agent/governance/MICRO_LIVE_OPERATOR_CHECKLIST.md`
- `~/Desktop/agent/governance/AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md`
- `~/Desktop/agent/governance/CAPITAL_DEFENSE_GRID.md`
- `~/Desktop/agent/canary/ARMING_CHECKLIST.md`
