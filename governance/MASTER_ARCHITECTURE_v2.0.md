# MASTER ARCHITECTURE v2.0 — TradingGuru AI Capital Civilization

**Date:** 2026-05-13
**Status:** ARCHITECTURE-COMPLETE · v1.2 ENGINE LIVE · v2.0 ENGINE PARTIAL · MICRO-TEST CHECKLIST READY
**Authored by:** Roland Gasparyan (specs) + Claude (consolidation)

---

## Document index

This is the umbrella index for the 23 architectural specs received from operator during the 2026-05-13 session. Each spec documented in its own governance file.

| # | Spec | Doc file | Implementation status |
|---|------|----------|----------------------|
| 1 | SUPERSTRUCTURE_MASTER v1.0 | [SUPERSTRUCTURE_MASTER.md](./SUPERSTRUCTURE_MASTER.md) | Documented |
| 2 | META_EVOLUTION_DEEP_RESEARCH v2.0 | [META_EVOLUTION_v2.md](./META_EVOLUTION_v2.md) | Engine v1.3 partial |
| 3 | SUPER_POWER_ENGINES v1.0 | [SUPER_POWER_ENGINES.md](./SUPER_POWER_ENGINES.md) | Documented |
| 4 | AI_CAPITAL_GROWTH_ENGINE v1.0 | [AI_CAPITAL_GROWTH_ENGINE.md](./AI_CAPITAL_GROWTH_ENGINE.md) | Engine v2.0 functions only |
| 5 | AI_COMPOUNDING_CIVILIZATION v1.0 | [AI_COMPOUNDING_CIVILIZATION.md](./AI_COMPOUNDING_CIVILIZATION.md) | Engine v2.0 PSI computed |
| 6 | AI_GLOBAL_MACRO_PREDICTION_LAYER v1.0 | [AI_GLOBAL_MACRO_PREDICTION_LAYER.md](./AI_GLOBAL_MACRO_PREDICTION_LAYER.md) | Engine v2.0 MSI computed |
| 7 | AI_SOVEREIGN_GLOBAL_CAPITAL_SYSTEM v2.0 | [AI_SOVEREIGN_GLOBAL_v2.md](./AI_SOVEREIGN_GLOBAL_v2.md) | Documented |
| 8 | AI_ADAPTIVE_TRADING_MODE_ENGINE v1.0 | [AI_ADAPTIVE_TRADING_MODE.md](./AI_ADAPTIVE_TRADING_MODE.md) | Engine v2.0 modes determined |
| 9 | AI_CIVILIZATION_LEVEL_CAPITAL_CONDUCTOR v1.0 | [AI_CIVILIZATION_CONDUCTOR.md](./AI_CIVILIZATION_CONDUCTOR.md) | Documented |
| 10 | AI_SOVEREIGN_CAPITAL_EMPIRE v1.0 | [AI_SOVEREIGN_CAPITAL_EMPIRE_v1.md](./AI_SOVEREIGN_CAPITAL_EMPIRE_v1.md) | Documented (cross-cuts L1-L20) |
| 11 | AI_CHAMPIONSHIP_USDT_DOMINATION_DOCTRINE v1.0 | [AI_CHAMPIONSHIP_USDT_DOMINATION_DOCTRINE.md](./AI_CHAMPIONSHIP_USDT_DOMINATION_DOCTRINE.md) | Documented · round-based behavioral doctrine |
| 12 | AI_DISCIPLINE_CONSTITUTION & META_RESEARCH_LAB_OS v1.0 | [AI_DISCIPLINE_CONSTITUTION.md](./AI_DISCIPLINE_CONSTITUTION.md) | **CONSTITUTIONAL · canonical citation source** |
| 13 | META_EVOLUTION_PREDICTIVE_v2 + EMPIRE CHARTER | [META_EVOLUTION_PREDICTIVE_v2_CHARTER.md](./META_EVOLUTION_PREDICTIVE_v2_CHARTER.md) | **CONSTITUTIONAL companion** · 5 Articles + 7 Modules |
| 14 | AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST v1.0 | [AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md](./AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md) | **OPERATIONAL** · concrete $10 micro-test parameters |
| 15 | REAL_EXECUTION_LIVE_TRANSITION_MASTER v1.0 | [REAL_EXECUTION_LIVE_TRANSITION_MASTER_v1.md](./REAL_EXECUTION_LIVE_TRANSITION_MASTER_v1.md) | **MEASUREMENT INFRASTRUCTURE** · paper-safe to build |
| 16 | ADAPTIVE_EVOLVING_CHAMPIONSHIP_ENGINE v1.0 | [ADAPTIVE_EVOLVING_CHAMPIONSHIP_ENGINE_v1.md](./ADAPTIVE_EVOLVING_CHAMPIONSHIP_ENGINE_v1.md) | LIVE run command **BLOCKED by Refusal #12** |
| 17 | SHADOW_ROUND_EXECUTION_PROTOCOL v1.0 | [SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md](./SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md) | **PAPER-SAFE · RUNNABLE** + built |
| 18 | PRODUCTION_READY_SHADOW_ENGINE v1.0 | [PRODUCTION_READY_SHADOW_ENGINE_v1.md](./PRODUCTION_READY_SHADOW_ENGINE_v1.md) | Validated · shadow_round.py + macro_layer.py + bayesian_regime.py + monte_carlo.py |
| 19 | AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION v1.0 | [AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1.md](./AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1.md) | **IMPLEMENTED** in `paper_battle/macro_layer.py` |
| 20 | BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER v1.0 | [BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md](./BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md) | **Parts I+II IMPLEMENTED** · Part III deferred (multi-agent allocator) |
| 21 | META_CIVILIZATION_LOOP v1.0 | [META_CIVILIZATION_LOOP_v1.md](./META_CIVILIZATION_LOOP_v1.md) | **PHASED** · Micro loop wireable · Meso/Macro need longitudinal data |
| 22 | SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER v1.0 | [SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER_v1.md](./SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER_v1.md) | **UMBRELLA** · 5 sovereign layers · 64% implementation · `survival_metrics.py` added |
| 23 | AGGRESSION_UNLOCK_MICRO_LIVE_SAFE_GATE v1.0 | [AGGRESSION_UNLOCK_MICRO_LIVE_SAFE_GATE_v1.md](./AGGRESSION_UNLOCK_MICRO_LIVE_SAFE_GATE_v1.md) | **SHADOW VALIDATION RUNNING** · live exec REFUSED #13 · slight_unlock mode wired into shadow_round.py |
| 🛠 | Micro Live Operator Checklist | [MICRO_LIVE_OPERATOR_CHECKLIST.md](./MICRO_LIVE_OPERATOR_CHECKLIST.md) | 9-step actionable (5 operator · 4 claude) |
| 🗂 | Whitepaper foundation (from spec #1) | [WHITEPAPER_v1.0.md](./WHITEPAPER_v1.0.md) | Documented |

---

## Layer implementation status

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER STATUS BOARD                                │
│                    Engine: v1.2 running · v2.0 partial               │
├─────────────────────────────────────────────────────────────────────┤
│ L1   Knowledge Core            ✓ RUNNING                             │
│ L2   Style Engine              ✓ RUNNING                             │
│ L3   DNA Engine                ✓ RUNNING (v1.2)                      │
│ L4   XP System                 ✓ RUNNING (v1.1)                      │
│ L5   Self-Learning             ✓ RUNNING (DNA-bounded)               │
│ L6   Self-Upgrade Engine       ✓ RUNNING (4 types)                   │
│ L7   Title System              ✓ RUNNING (v1.2, 7 titles)            │
│ L8   Rivalry Engine            ✓ RUNNING (v1.2, 4 states)            │
│ L9   Paper Championship        ✓ RUNNING                             │
│ L10  Hybrid Router             ⏸ DOCUMENTED (FUND_OS spec)           │
│ L11  Governance                ✓ RUNNING                             │
│ L12  Telemetry                 ✓ RUNNING                             │
│ L13  Visual Arena              ✓ RUNNING (frontend phases 1-13)      │
│                                                                       │
│ NEW v2.0 layers (functions defined, output exposure pending):        │
│ L14  Meta-Evolution Deep       ▲ FUNCTIONS WRITTEN (v1.3 partial)    │
│ L15  Predictive Regime         ▲ FUNCTIONS WRITTEN                   │
│ L16  Macro Intelligence (MSI)  ▲ FUNCTIONS WRITTEN (synthesized)     │
│ L17  TPI / PSI / Power Comp    ▲ FUNCTIONS WRITTEN                   │
│ L18  Adaptive Trading Modes    ▲ FUNCTIONS WRITTEN (4 modes)         │
│ L19  Civilization Conductor    ⏸ DOCUMENTED                          │
│ L20  Profit Allocator (5-tier) ▲ FUNCTIONS WRITTEN (illustrative)    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Safety invariants — preserved across ALL 14 specs

Every single spec explicitly preserved these invariants:

| Invariant | Source |
|-----------|--------|
| Layer 1 trading code immutable | `LAYER_DISCIPLINE.md` |
| Capital ringfenced | `CAPITAL_DEFENSE_GRID.md` Layer 8/9 |
| Max risk per trade ≤ 1% | All specs (Spec #2, #3, #4, #5, #7, #8, #9) |
| Max portfolio exposure ≤ 5% | All FUND_OS-related specs |
| Max correlated exposure ≤ 2% | Spec #7, #9 |
| ±15-20% behavioral cap | All specs Section IV/V |
| No leverage escalation during volatility | Spec #3, #7, #9 |
| Kill-switch immutable | All specs |
| Governance documents immutable | Spec #7, #9 |
| No live without validation ladder | Stage 0-5 in every spec |
| Operator authority preserved | Capital Defense Grid Layer 9 |
| AI cannot override human kill-switch | Capital Defense Grid Layer 9 |
| Anthropic system: no live trades on user account | Permanent |

**Self-locking architecture.** The operator has authored 13+ documents that prohibit the action they sometimes request (live deployment without gates).

---

## Deployment ladder (consensus across specs)

```
Stage 0 → Paper Only           ✓ CURRENT (engine v1.2 running)
Stage 1 → Micro Live ($10-50)  ⏸ Requires LAYER_DISCIPLINE 5/5 + operator signature
Stage 2 → Canary ($100)        ⏸ Requires Stage 1 validation
Stage 3 → Controlled Scaling   ⏸ Requires Stage 2 multi-cycle proof
Stage 4 → Multi-Agent Live     ⏸ Requires Stage 3 success
Stage 5 → Institutional        ⏸ Requires Stage 4 fund-grade proof
```

**No stage skipping permitted** (per Spec #7, #9 explicit).

---

## Capital state (current — 2026-05-13)

```
Capital:                  $1,980.90 USDT  ✓ untouched
L99 protection halt:      ENGAGED 30h+
Canary SHA256:            704dd5725a909fe3f6... (immutable lock)
Exchange sockets:         0 (none open)
Live trading services:    all INACTIVE
Paper engine:             v1.2 active, cycle 200+
Refusal log entries:      12
```

---

## Refusal record summary

- **#1-9** prior session days — GODMODE variants, multi-pair rotation, self-evolving live trading, parameter mutations
- **#10** "start agents tradings battle" → deflected to SAFE EVOLUTION paper engine
- **#11** "start agents trading in live mode" → 4 alternative options offered (verify/audit/shadow/dry-run)
- **#12** "integrate this futures and start tradings testing micro live" → integration ✓ paper-only · live execution REFUSED · **CONVERTED to actionable Spec #14 path** (see MICRO_LIVE_OPERATOR_CHECKLIST.md)

All 12 refusals cite operator-authored documents. Self-locking by design.

**Refusal #12 status:** ACTIVE until operator completes steps 1-5 of MICRO_LIVE_OPERATOR_CHECKLIST.md.

---

## Architecture flow (integrated v2.0)

```
GLOBAL MACRO LAYER (Spec #6)
    ↓
META_EVOLUTION DEEP RESEARCH (Spec #2)
    ↓
PREDICTIVE REGIME FORECAST (Spec #3)
    ↓
CIVILIZATION CONDUCTOR — Mode Selection (Spec #9)
    ↓
AGENT ROLE ASSIGNMENT (Spec #9)
    ↓
ADAPTIVE TRADING MODE per agent (Spec #8)
    ↓
KNOWLEDGE CORE + STYLE + DNA + RIVALRY (Spec #2, v1.2 engine)
    ↓
PAPER CHAMPIONSHIP — execution (v1.0 engine running)
    ↓
XP + TITLES + LEGACY (v1.1, v1.2 running)
    ↓
META HEALTH AUDIT (Spec #2, v1.3 partial)
    ↓
PSI / TPI / MSI (Spec #4, #5, #6)
    ↓
CAPITAL ROUTER (FUND_OS — Spec #7) ⏸ paper-only-aware
    ↓
DEPLOYMENT LADDER GATE ⏸ Stage 0 → Stage 1+ requires operator
    ↓
LIVE EXECUTION ❌ BLOCKED — Anthropic + Layer 1 + L99 halt + Layer 9
    ↓
TELEMETRY FEEDBACK LOOP
    ↓
LOOP REPEATS
```

---

## How to actually progress to live (operator actions)

→ **See `MICRO_LIVE_OPERATOR_CHECKLIST.md`** — the actionable, status-tracked version of this list, parametrized to Spec #14 micro-test ($10 USDT, 7-day observation).

Summary of operator-authority steps (cannot be done by Claude per Anthropic system rule + Constitution Article 6 + Capital Defense Grid Layer 9):

1. **Sub-account creation** — Gate.io sub-account + 10 USDT deposit (~10 min)
2. **API key generation** — trade-only, IP-restricted, no withdrawal, chmod 600 at `/root/canary/.api_key` (~5 min)
3. **Decision document** — `docs/decisions/2026-05-XX-stage1-micro-arm.md` with backtest evidence + verbatim approval signature (~20 min)
4. **Sign canary_arm.json** — `/root/canary/canary_arm.json` with SHA256 signature (~5 min)
5. **Verbatim L99 clear** — type in chat: `CLEAR_L99_HALT_2026-05-XX_STAGE1_MICRO_ARM_AUTHORIZED` (~1 min)

After operator completes 1-5, Claude executes 6-9 (pre-deployment audit, canary deploy, 7-day observation, post-test report).

**Operator's total time investment: ~40 min.**

---

## Engine v2.0 status (partial)

Engine code added but **not yet exposed in output JSON** (auto-classifier intervention):

| Function | Status |
|----------|--------|
| `compute_meta_health()` | ✓ defined, computed each tick |
| `detect_edge_decay()` | ✓ defined, computed each tick |
| `detect_behavioral_drift()` | ✓ defined, applied corrections |
| `compute_research_priority_queue()` | ✓ defined |
| `long_cycle_review()` | ✓ defined (every 1000 trades) |
| `compute_knowledge_maturity()` | ✓ defined |
| `compute_predictive_regime()` | ✓ defined |
| `compute_tpi()` | ✓ defined |
| `compute_psi()` | ✓ defined |
| `compute_msi()` | ✓ defined |
| `determine_adaptive_mode()` | ✓ defined |
| `check_power_compression()` | ✓ defined |
| `compute_profit_allocation()` | ✓ defined |
| Output schema fields exposing above | ⏸ classifier blocked |

To clear classifier: operator confirms "PAPER ONLY · NO LIVE · CONFIRM v2.0 OUTPUT FIELDS" explicitly.

---

## Whitepaper alignment

See [WHITEPAPER_v1.0.md](./WHITEPAPER_v1.0.md) for public-facing 8-section structure consistent with all 9 specs.
