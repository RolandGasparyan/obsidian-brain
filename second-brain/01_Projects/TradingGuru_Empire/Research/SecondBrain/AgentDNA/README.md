---
type: agent-dna-index
date: 2026-05-13
tags: [agents, dna, titles, rivalries, championship]
ai-first: true
source: ~/Desktop/agent/paper_battle/paper_battle_engine.py
---

# Agent DNA

> For future Claude: 8 named agents compete in the paper championship. Each has IMMUTABLE DNA (personality constraints) + dynamic XP/level/title/rivalry state. The current shadow round runner is single-strategy; multi-agent shadow execution is **deferred** (Spec #20 Part III) pending design decision on how to wire these 8 agents into multi-agent allocator.

---

## The 8 Named Agents

Source: `paper_battle/paper_battle_engine.py` v1.2 (cycle 200+ running on server)

| # | Name | Archetype | Status |
|---|------|-----------|--------|
| 1 | **Ares Valkor** | Aggressive momentum hunter | Active |
| 2 | **Cassia Verax** | Mean-reversion strategist | Active |
| 3 | **Niven Sharp** | Precision tactical | Active |
| 4 | **Thane Korvan** | Risk-compressed survivor | Active |
| 5 | **Mira Voss** | Macro/regime specialist | Active |
| 6 | **Phoenyx Aldon** | Recovery / post-drawdown | Active |
| 7 | **Doran Pyle** | Skeptic / contrarian | Active |
| 8 | **Atlas Crowne** | Champion / balanced | Active |

→ Operator's roles per Spec #20 Part III (HUNTER/RISK/ALPHA/REGIME/EXECUTOR/RECOVERY/SKEPTIC/CHAMPION) map onto these 8 names via DNA traits.

---

## The Layer Stack (paper_battle_engine.py)

| Layer | Component | Status |
|-------|-----------|--------|
| L1 | Knowledge Core (immutable rules) | ✓ |
| L2 | Style Engine (per-agent behavior variation) | ✓ |
| L3 | **DNA Engine** (IMMUTABLE personality constraints) | ✓ v1.2 |
| L4 | XP System (`floor(sqrt(xp/50))` level formula) | ✓ |
| L5 | Self-Learning (±15% bounded by DNA) | ✓ |
| L6 | Self-Upgrade (Precision / RiskCompress / Aggression / RegimeMaster) | ✓ |
| L7 | **Title System** (7 titles, defense mechanics, +10% XP mult) | ✓ |
| L8 | **Rivalry Engine** (4 states, XP pressure, counter-style memory) | ✓ |
| L9 | Paper Championship (scoring, tiers, ranking) | ✓ |
| L10 | Hybrid Router | ⏳ future |
| L11 | Governance | ✓ |
| L12 | Telemetry | ✓ (paper-arena.json publisher) |
| L13 | Visual Arena | ✓ (frontend /championship + /racing) |

---

## DNA Engine (L3)

Each agent has:
- **Immutable traits** — aggression baseline, risk tolerance, signal preference
- **Mutable behaviors** — bounded ±15% per cycle, never overflowing DNA bounds
- **Universal cap** — `MAX_BEHAVIOR_SHIFT = 0.15` (across all agents)

This is the **L3 contract**: DNA never changes, but behavior within DNA can evolve.

---

## Title System (L7) — 7 Titles

Titles confer **+10% XP multiplier** and are defended by trades. Cannot increase risk caps.

(Specific titles in source code — refer to `paper_battle_engine.py`.)

---

## Rivalry Engine (L8) — 4 States

- **Neutral** — no active rivalry
- **Provoked** — recent loss to specific opponent
- **Hunting** — actively counter-styling opponent
- **Dominant** — consistent wins establish style memory

Rivalries create XP pressure but cannot bypass cooldown or governance.

---

## Self-Learning + Self-Upgrade

**Self-Learning (L5):** Each agent adjusts behavior weights within ±15% per cycle, bounded by DNA.

**Self-Upgrade (L6):** 4 upgrade paths:
- `PRECISION` — tighter entries, less drawdown
- `RISK_COMPRESS` — smaller sizing during instability
- `AGGRESSION` — broader signal acceptance
- `REGIME_MASTER` — better regime classification

All paths must stay within Constitution Article 3 hard caps.

---

## Multi-Agent Allocator (Spec #20 Part III) — DEFERRED

The operator's spec defines:

```
Agent_Regime_Score_i = Σ (Regime_Prob × Agent_Performance_in_Regime)
```

With stability adjustments, macro overlay, normalization, and constraints:
- Single agent cap ≤ 40%
- Min allocation ≥ 5%
- Total exposure ≤ constitutional limit

**Why deferred:**
1. Current `shadow_round.py` is single-strategy
2. Each agent needs its own per-tick signal generator
3. Per-regime historical performance needs persistent storage
4. Stability metrics need rolling tracking per agent
5. Allocator runs each tick or each minute to set per-agent weights

**Total scope to wire:** ~400-600 lines new code + state file design.

**Decision needed:** Reuse paper_battle_engine agents in parallel shadow? OR define 8 lightweight signal variants inline? OR rewrite shadow as multi-agent v2?

---

## Cross-links

- [[Architecture/README]] — Layer stack within Sovereign architecture
- [[ExecutionEngine/README]] — current single-strategy shadow runner
- [[MetaCivilization/README#Allocation Learning]] — Layer 3 learning of allocator weights

## Source-of-truth

- `~/Desktop/agent/paper_battle/paper_battle_engine.py` (cycle 200+ active)
- `~/Desktop/agent/governance/BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md` Part III
- `~/Desktop/agent/governance/AI_CHAMPIONSHIP_USDT_DOMINATION_DOCTRINE.md`
