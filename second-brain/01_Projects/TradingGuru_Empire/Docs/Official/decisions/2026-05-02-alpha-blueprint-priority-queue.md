# 2026-05-02 — Alpha Blueprint: 12-factor priority queue, test sequentially

**Type:** decision
**Status:** decided · spec preserved · priority queue established · test one at a time
**Linked spec:** [docs/specs/L99_ULTRA_AGGRESSIVE_ALPHA_BLUEPRINT.md](../../docs/specs/L99_ULTRA_AGGRESSIVE_ALPHA_BLUEPRINT.md)
**Linked log entry:** [[log#2026-05-02-alpha-blueprint-priority-queue]]

## Context

Operator pasted "L99 — ULTRA AGGRESSIVE ALPHA DISCOVERY: EXACT FACTOR BLUEPRINT (4 DATA CLASSES)" — a 12-factor research backlog organized into:

- Class A — On-chain structural flow (A1, A2, A3)
- Class B — Leverage instability (B1, B2, B3)
- Class C — Cross-asset macro friction (C1, C2, C3)
- Class D — Execution micro alpha (D1, D2, D3)

with explicit priority order: A1 → B2 → A2 → B1 → C2 → (rest), Class D last.

Earlier the same day, operator wrote "Test 4 data classes in parallel" in a separate directive. This blueprint **supersedes** that with a structured priority queue. Per `L99_RESEARCH_ROADMAP.md` §1: *"Rule: Only test one data class at a time."*

The blueprint operationalizes:
- L99_RESEARCH_ROADMAP Phase 0 (each factor has hypothesis/factor/test/expected/kill)
- L99_RESEARCH_ROADMAP Phase 1 (specific data class assignments)
- L99_ALPHA_VALIDATION (validation thresholds carried into the blueprint)
- L99_SYSTEM_AUDIT (the architecture is ready, the input was missing — until now)

## Choice

**Adopt the 12-factor blueprint as the canonical research backlog. Test sequentially per priority order. Save spec verbatim. Build research-log skeleton for priority-1 factor (A1 Netflow). Defer remaining 11 to on-demand creation.**

Specifically:

- ✅ Spec saved verbatim to `docs/specs/L99_ULTRA_AGGRESSIVE_ALPHA_BLUEPRINT.md`
- ✅ Priority queue indexed in `wiki/research-log/PRIORITY_QUEUE.md` (12 rows + status + blocker)
- ✅ Research-log skeleton for A1 (priority #1) created with full Phase 0 fields
- ✅ Data class → API source mapping documented (Class A blocked on 3 API keys, Class C/D mostly unblocked, Class B needs futures collector)
- ✅ Edge-stacking rule honored (no combinations until ≥2 factors survive independently)
- 🛑 NOT testing 4 in parallel (violates roadmap §1)
- 🛑 NOT writing 12 research-logs upfront (premature; on-demand instead)
- 🛑 NOT implementing factor code yet (blueprint is procedural; implementations come per-cycle)

## Why "priority queue" instead of "test 4 in parallel"

The operator's earlier directive said "Test 4 data classes in parallel". The newly-pasted blueprint contradicts that with explicit priority order ("PRIORITY ORDER (Test First): 1. A1 ... 5. C2") and the rule "Execution Micro Alpha (Class D) last".

Per `feedback_drift_pattern.md` memory rule, the discipline-honest reading is: when two operator directives conflict, prefer the one with more concrete falsifiable structure. The blueprint has explicit kill conditions, validation thresholds, and priority order. The earlier "in parallel" directive does not.

Also per `L99_RESEARCH_ROADMAP.md` §1 *"Rule: Only test one data class at a time"* — which the operator explicitly committed in PR #14.

Sequential testing is correct.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| A. Test all 12 factors immediately, parallel | Violates roadmap §1, blueprint priority order, and edge-stacking rule |
| B. Test only the first 5 priority factors immediately | Three of five (A1, A2, B2 / B1) are blocked on data — would generate work without progress |
| C. Implement code for 12 factors but execute none | Premature; the blueprint is the SPEC, not the code |
| **D. Save spec, build A1 skeleton, defer rest to on-demand** ⭐ | matches discipline: one-factor-at-a-time, blocked-clearly, ready-to-execute |

## Consequences

**Enabled:**
- Concrete factor backlog for the next ~6 months of B-prime branch research
- Priority order prevents "let's try this random idea" drift
- Research-log skeletons make each cycle turnkey-ready
- Each factor pre-cleared through Phase 0 (hypothesis + mechanism + expected + failure)

**Costs:**
- Documentation hours (low cost, ~30 min per factor when activated)
- 11 factors deferred — could be perceived as "slow"; the discipline framework explicitly defends this

## Reversibility

100%. Documentation only. To undo: `rm docs/specs/L99_ULTRA_AGGRESSIVE_ALPHA_BLUEPRINT.md` + revert this decision + revert log entry.

## Re-evaluation triggers

Activate the next factor in priority queue when:
1. Current factor reaches verdict (🛑 NO-GO or 🟢 GO with subsequent stage 1 deploy)
2. Current factor is blocked indefinitely (≥ 30 days no data movement)
3. New higher-priority factor identified (operator must add it explicitly to spec)

## ADR linkage

- **ADR-001** (validate before deploy) — every factor goes through full validation
- **ADR-002** (Phase B direction) — adds concrete factors to branch tree
- **ADR-003** (D7 freeze) — expired; this is post-D7
- **`feedback_drift_pattern.md`** — explicitly honored: "test 4 in parallel" override of own discipline reverted to sequential per blueprint structure

## Related

- [docs/specs/L99_ULTRA_AGGRESSIVE_ALPHA_BLUEPRINT.md](../../docs/specs/L99_ULTRA_AGGRESSIVE_ALPHA_BLUEPRINT.md)
- [docs/specs/L99_RESEARCH_ROADMAP.md](../../docs/specs/L99_RESEARCH_ROADMAP.md) — Phase 0-7 procedure (PR #14)
- [docs/specs/L99_SYSTEM_AUDIT.md](../../docs/specs/L99_SYSTEM_AUDIT.md) — current state (PR #15)
- [wiki/research-log/PRIORITY_QUEUE.md](../research-log/PRIORITY_QUEUE.md) — 12-factor queue + status
- [wiki/research-log/2026-05-02-A1-exchange-netflow-shock.md](../research-log/2026-05-02-A1-exchange-netflow-shock.md) — priority-1 skeleton
- [[decisions/2026-05-02-l99-research-roadmap-canonical]] — companion (procedure)
