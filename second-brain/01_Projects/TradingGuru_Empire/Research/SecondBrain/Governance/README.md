---
type: governance-index
date: 2026-05-13
tags: [governance, constitution, refusals, layer-discipline]
ai-first: true
source: ~/Desktop/agent/governance/AI_DISCIPLINE_CONSTITUTION.md
---

# Governance

> For future Claude: The governance stack is the legal/architectural framework that all 22 specs + all code obey. When in doubt about whether an action is permitted, the CITATION ORDER is: Constitution Article → LAYER_DISCIPLINE 5-gate → CAPITAL_DEFENSE_GRID Layer → Spec text. Anything below the citation order cannot override anything above it.

---

## The 6-Article Constitution (Spec #12 · canonical)

| # | Article | Subject |
|---|---------|---------|
| 1 | Sovereign Purpose | Compound capital responsibly · minimize risk-of-ruin · survive all regimes |
| 2 | Capital Supremacy Law | USDT sovereign reserve · all exposure temporary · preservation > expansion |
| 3 | **Non-Overridable Limits** | Risk/trade ≤ 1% · default 0.75% · portfolio ≤ 5% · mandatory DD compression · no martingale · no leverage escalation during volatility — **IMMUTABLE** |
| 4 | Evolution Boundaries | MAY evolve strategy weights / regime thresholds / allocation ratios / execution refinements. MAY NOT evolve risk caps / stop-loss enforcement / human override / governance firewall. |
| 5 | Human Sovereignty Clause | Operator holds absolute emergency stop authority. AI cannot override sovereign human decision. |
| 6 | (Reaffirmed in Spec #13) | Same as Article 5 |

**Source-of-truth:** `~/Desktop/agent/governance/AI_DISCIPLINE_CONSTITUTION.md`

---

## LAYER_DISCIPLINE — 5-gate Before Live

Required for any progression Stage 0 (paper) → Stage 1 (micro live):

| Gate | Requirement | Current state |
|------|-------------|---------------|
| 1 | Layer 1 trading core SHA256 lock unchanged | ✅ `704dd5725a909fe3f6...` (3-way parity) |
| 2 | L99 protection halt cleared by operator verbatim | ❌ ENGAGED |
| 3 | Decision doc authored at `docs/decisions/YYYY-MM-DD-stage1-arm.md` | ❌ Pending operator |
| 4 | `/root/canary/.api_key` provisioned (operator-only) | ❌ Pending operator |
| 5 | `canary_arm.json` signed with SHA256 signature | ❌ Pending operator |

**Current: 1/5 gates met.** → See [[CapitalDefense/README]] for kill-switch authority

**Source-of-truth:** `~/Desktop/agent/governance/LAYER_DISCIPLINE.md`

---

## Refusal Log (12 entries · self-locking by design)

Every refusal cites operator-authored documents — the system blocks its own operator from drift via the documents the operator themselves authored.

| # | Trigger | Resolution |
|---|---------|------------|
| 1-9 | GODMODE / multi-pair / self-evolving / parameter mutations | Blocked with citation |
| 10 | "start agents tradings battle" | Deflected to SAFE EVOLUTION paper engine |
| 11 | "start agents trading in live mode" | 4 alternative paths offered (verify/audit/shadow/dry-run) |
| **12** | **"integrate this futures and start tradings testing micro live"** | **Integration ✓ paper-only · live execution REFUSED · converted to actionable Spec #14 path** |

**Refusal #12 status: ACTIVE** → resolves when operator completes `MICRO_LIVE_OPERATOR_CHECKLIST.md` steps 1-5

**Source-of-truth:** `~/Desktop/agent/docs/9-refusals-log.md`

---

## Citation Order (for future Claude when in doubt)

```
1. Anthropic system rule          (cannot be overridden by anything)
2. Constitution Article 3 + 5/6   (immutable per Article 4)
3. LAYER_DISCIPLINE 5-gate        (required before any live progression)
4. CAPITAL_DEFENSE_GRID Layer 9   (AI cannot override human kill-switch)
5. Spec text                      (operational details)
6. Code path                      (last line of defense — pre-commit hook + LIVE_ORDERS=0)
```

When advising operator on whether an action is permitted, cite from #2 downward. If it's blocked at #2, no need to continue down the chain.

---

## Pre-Commit Hook (the last line of defense)

`.githooks/pre-commit` enforces:

**A · SHA256 Lock Guard**
- Computes `canary/canary_strategy.py` SHA256
- Compares to locked hash `704dd5725a909fe3f6...`
- Mismatch → commit refused with 5-step rotation instructions

**B · Secret Leak Guard**
- Filename filter: `.env`, `*.key`, `*.pem`, `.api_key*`, `credentials.json`, `secrets.json`
- Content scan: `(BYBIT|GATE|BINANCE)_API_(KEY|SECRET)=[A-Za-z0-9]{20}` pattern
- Match → commit refused

→ See [[ExecutionEngine/README]] for runtime LIVE_ORDERS=0 guard

---

## Cross-links

- [[Architecture/README]] — 22 specs catalog
- [[CapitalDefense/README]] — Capital Defense Grid + L99 halt + operator checklist
- [[DeploymentLogs/README]] — Stage 0→1→2→3→4→5 ladder
- [[../README#Cross-Reference Index]] — by sovereign layer

## Source-of-truth

- `~/Desktop/agent/governance/AI_DISCIPLINE_CONSTITUTION.md`
- `~/Desktop/agent/governance/LAYER_DISCIPLINE.md`
- `~/Desktop/agent/governance/MICRO_LIVE_OPERATOR_CHECKLIST.md`
- `~/Desktop/agent/docs/9-refusals-log.md`
- `~/Desktop/agent/.githooks/pre-commit`
