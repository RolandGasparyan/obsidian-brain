# 2026-05-02 — L99 Research Roadmap is the canonical research-operations protocol

**Type:** decision
**Status:** decided · supersedes ad-hoc validation planning
**Linked log entry:** [[log#2026-05-02-l99-research-roadmap-canonical]]
**Linked spec:** [docs/specs/L99_RESEARCH_ROADMAP.md](../../docs/specs/L99_RESEARCH_ROADMAP.md)

## Context

After the 5-layer L99 quant infrastructure landed on main across 5 merged PRs (#9, #10, #11, #12, #13 — 17 modules, ~5300 LOC, 449 tests), operator pasted a research-operations protocol formalizing what happens next.

Quote from spec: *"Architecture is finished. Now only two outcomes exist: 1. Validated alpha → activate L99 stack. 2. No alpha → pivot or stop."*

This is the operator's explicit commitment to STOP building infrastructure and START measuring. It aligns with the project's discipline framework (`feedback_drift_pattern.md`, ADR-001) but elevates that discipline to a formal 7-phase research procedure.

## Choice

**Adopt L99_RESEARCH_ROADMAP.md as the canonical research-operations protocol. All future factor research follows the 7-phase template. No new architectural layers without explicit operator request.**

Specifically:

- ✅ Spec saved verbatim to `docs/specs/L99_RESEARCH_ROADMAP.md`
- ✅ Phase-by-phase mapping to existing tooling (~80% covered by existing 7-filter battery + Layer 3 MC simulator + signal_nature)
- ✅ Documented gaps: Phase 0 hypothesis template, Phase 5 stress wrapper, Phase 6 post-cutoff check, lag-shift-±1
- ✅ Documented B.2.4 naming conflict between this spec and `PHASE_B_DECISION_TREE.md` (resolution: rename Hybrid Portfolio to B.2.5; new B.2.4 = cross-asset flow)
- 🛑 NOT implementing the missing pieces yet — they're documented as gaps; user can request them as separate PRs
- 🛑 NOT pivoting away from B.2.3 — the on-chain branch remains the active research direction

## Why this is the right kind of "yes"

This spec is methodologically excellent. It includes:

1. **Phase 0 scientific protocol** — every factor must define hypothesis + mechanism + expected + failure BEFORE coding
2. **Tier 1 / Tier 2 / rejected data classes** — explicit rejection of retail-sentiment / social-media as low-edge categories
3. **Quantitative thresholds** with concrete numbers (|IC| ≥ 0.04, t-stat ≥ 2.0, PF ≥ 1.3, Q5−Q1 > 60 bps after fees)
4. **Phase 4 mechanism audit** — "backtest without mechanism = illusion"
5. **Phase 5 stress-test battery** — 2× fees, 1.5× slippage, 20% signal degradation, noise injection
6. **Phase 6 kill criteria** with "no emotional override allowed"
7. **Reality check** stating < 20% probability of real durable edge — calibrated honesty matching prior null pattern
8. **Final rule** — "No more layers. No more complexity. Only evidence."

This is institutional-grade research methodology. Engaging with it as a research operations protocol is correct.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| A. Treat as another vibe-paste, ignore | Spec has falsifiable kill criteria + mechanism audit — not vibes |
| B. Implement all gap pieces immediately | Premature optimization; user hasn't requested specific gaps |
| **C. Save spec, document mapping, defer gap fixes to user request, keep B.2.3 as immediate focus** ⭐ | matches existing engagement pattern with operator specs |

## Consequences

**Enabled:**
- Future factor research has a clear 7-phase template
- Architecture phase is officially closed; no more layer additions without explicit need
- Decision tree gets a defensible extension (B.3 options skew as new data class)
- Coverage gap analysis tells future Claude sessions exactly what's missing

**Costs:**
- Documentation hours (low cost)
- B.2.4 naming conflict requires a follow-up reconciliation PR

## Reversibility

100%. Documentation only. To undo: `rm docs/specs/L99_RESEARCH_ROADMAP.md` + revert this decision doc + revert log entry.

## Re-evaluation triggers

This protocol governs research from now until ONE of:

1. Validated alpha emerges from a factor → graduate to L99 stack live wiring
2. All Phase 7 branches (B.2.2 / B.2.3 / B.2.4 / B.3) exhaust without edge → operator decides to pivot or stop
3. Operator explicitly supersedes with a new protocol document

## ADR linkage

- **ADR-001** (validate before deploy) — this spec is the OPERATIONAL definition of "validate"
- **ADR-002** (Phase B direction) — extends decision tree with B.3 options skew
- **ADR-003** (D7 freeze) — expired; this spec applies post-D7
- `feedback_drift_pattern.md` — explicitly honored ("No more layers. Only evidence.")

## Related

- [docs/specs/L99_RESEARCH_ROADMAP.md](../../docs/specs/L99_RESEARCH_ROADMAP.md) — full spec verbatim + mapping + gating
- [[decisions/2026-05-01-l99-quant-suite-research-only]] — Layers 1-4 spec preservation
- [[decisions/2026-05-01-l99-hybrid-spec-research-only]] — Layer 5 spec preservation
- [[findings/2026-04-30-d6-binding-no-go]] — proves microstructure null (the spec's "Reality Check" cite)
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — decision tree (B.2.4 conflict TODO)
