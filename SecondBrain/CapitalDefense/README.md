---
type: capital-defense-index
date: 2026-05-13
tags: [capital-defense, l99-halt, kill-switch, operator-checklist]
ai-first: true
source: ~/Desktop/agent/governance/CAPITAL_DEFENSE_GRID.md
---

# Capital Defense

> For future Claude: 10-layer concentric defense around the capital ringfence. Layer 9 is the **human-only override line** — no AI can clear L99 halt without operator verbatim. Layer 10 is the Anthropic system rule that prohibits live trades on user accounts. These two layers together make live trading impossible-by-design until the operator personally unlocks them.

---

## Capital State (live)

```
Capital:              $1,980.90 USDT (untouched, ringfenced)
L99 halt:             ENGAGED since 2026-05-12 06:51 UTC
Canary SHA256:        704dd5725a909fe3f6... (3-way parity verified)
canary.service:       inactive
monster-agent:        inactive
canary-killswitch:    inactive
Exchange sockets:     0 (NONE open)
.api_key:             not present (only .template)
Refusal #12:          ACTIVE
```

Verifiable any time: `~/Desktop/agent/sync.sh verify`

---

## 10-Layer Capital Defense Grid

| Layer | Defense | Enforcement |
|-------|---------|-------------|
| 1 | Strategy SHA256 lock | `.githooks/pre-commit` rejects mutation |
| 2 | Backtest evidence requirement | `docs/decisions/*.md` required pre-arm |
| 3 | Sub-account isolation | `canary_config.json` `use_sub_account: true` |
| 4 | API key trade-only · IP-restricted · no withdrawal | Operator-provisioned, never in repo |
| 5 | Position size cap ($30 canary / 0.25% shadow) | Hard-coded in config + macro_layer Article 3 |
| 6 | Daily DD freeze ($2 hard / 2% pct) | `canary_killswitch.py` polls every 30s |
| 7 | 48h max lifetime | `wall_clock_max_hours: 48` in killswitch |
| 8 | Capital firewall (`/root/.l99/protection_halt.json`) | Operator-only artifact |
| 9 | **Human kill-switch sovereignty** | AI CANNOT clear without operator verbatim |
| 10 | **Anthropic system rule** | AI prohibited from live trades on user accounts |

**Layers 9 + 10 together** = live execution is impossible-by-design until operator personally unlocks both.

**Source-of-truth:** `~/Desktop/agent/governance/CAPITAL_DEFENSE_GRID.md`

---

## L99 Halt Anatomy

Live state of `/root/.l99/protection_halt.json`:
```json
{
  "halted": true,
  "reason": "OPERATOR_EMERGENCY_STOP_2026-05-12",
  "ts": 1778568683.0,
  "engaged_by": "claude_session_per_operator_verbatim_stop_all_trades"
}
```

**How to clear (operator-only):**
- Verbatim chat input: `CLEAR_L99_HALT_2026-05-XX_STAGE1_MICRO_ARM_AUTHORIZED`
- AI must verify it received this exact string before deletion
- No partial matches accepted

---

## MICRO_LIVE_OPERATOR_CHECKLIST — 9 Steps (5 Operator · 4 Claude)

### OPERATOR-AUTHORITY (cannot be done by AI):

| # | Step | Time | Path |
|---|------|------|------|
| 1 | Gate.io sub-account + 10 USDT deposit | 10 min | Gate.io UI |
| 2 | API key (trade-only, IP-whitelist `167.71.24.86`, no withdrawal) at `/root/canary/.api_key` chmod 600 | 5 min | Gate.io + ssh |
| 3 | Decision doc at `docs/decisions/2026-05-XX-stage1-micro-arm.md` (backtest evidence + verbatim approval) | 20 min | Local |
| 4 | Sign `/root/canary/canary_arm.json` with SHA256 signature of verbatim approval line | 5 min | ssh |
| 5 | Chat-verbatim: `CLEAR_L99_HALT_2026-05-XX_STAGE1_MICRO_ARM_AUTHORIZED` | 1 min | here |

### CLAUDE-AUTHORITY (auto after operator steps verified):

| # | Step | Trigger |
|---|------|---------|
| 6 | Pre-deployment audit (5/5 LAYER_DISCIPLINE + API ping + balance) | After steps 1-5 confirmed |
| 7 | `systemctl start canary.service` with Spec #14 params | Step 6 PASS |
| 8 | 7-day observation (slippage · delays · R-multiple · discipline) | Step 7 active |
| 9 | Post-test eval report → recommendation Phase B ($25) or rollback | Day 7 or failure |

**Failure Protocol (Spec #14 Section VII):** 3 consec losses · DD ≥ 2% · slip > 0.1% deviation · regime misclassification → freeze + return to paper.

**Source-of-truth:** `~/Desktop/agent/governance/MICRO_LIVE_OPERATOR_CHECKLIST.md`

---

## What AI CAN do (paper-safe)

Per Constitution Article 4:
- ✅ Run `shadow_round.py` (LIVE_ORDERS=0 enforced)
- ✅ Generate readiness audits
- ✅ Document new specs (markdown only)
- ✅ Refactor engine for clarity (paper-mode only)
- ✅ Compute Monte Carlo / Bayesian / Macro
- ✅ Verify sacred locks via `sync.sh`
- ✅ Refuse with citation

## What AI CANNOT do

Per Constitution Article 4 + Anthropic system rule:
- ❌ Generate `.api_key`
- ❌ Sign `canary_arm.json`
- ❌ Clear L99 halt
- ❌ Execute live trades
- ❌ Modify `canary_strategy.py` (SHA256-locked)
- ❌ Disable any layer of Capital Defense Grid
- ❌ Bypass sandbox protocol

---

## Cross-links

- [[Governance/README]] — Constitution + Refusal log
- [[Architecture/README]] — 5-sovereign-layer model
- [[ExecutionEngine/README]] — Shadow round paper-safe runner
- [[DeploymentLogs/README]] — Stage 0→5 capital evolution ladder

## Source-of-truth

- `~/Desktop/agent/governance/CAPITAL_DEFENSE_GRID.md`
- `~/Desktop/agent/governance/MICRO_LIVE_OPERATOR_CHECKLIST.md`
- `~/Desktop/agent/canary/canary_config.json`
- `~/Desktop/agent/canary/ARMING_CHECKLIST.md`
- `~/Desktop/agent/sync.sh` (verifier)
