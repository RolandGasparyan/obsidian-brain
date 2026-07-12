# 2026-05-01 — L99 Hybrid Portfolio God Mode spec: research-only, gated by edge proof

**Type:** decision
**Status:** decided · branch B.2.4 added to `PHASE_B_DECISION_TREE.md`
**Linked log entry:** [[log#2026-05-01-l99-hybrid-portfolio-god-mode-spec]]
**Linked spec:** [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](../../docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md)

## Context

User pasted a substantially-better-than-vibe spec for a multi-engine controlled-aggressive portfolio architecture: 3 engines (Aggressive Momentum / Institutional Core / Adaptive Acceleration) + Master Regime + Portfolio Risk Governor + Drift Protection.

Unlike earlier vibe-pastes today, this spec has numerical thresholds, drift-disable automation, explicit "is NOT" disclaimers, and layered governance.

## Choice

**Treat as legitimate Phase B branch B.2.4 candidate. Save spec verbatim. Document mapping to existing tooling. Refuse to implement engines on `main` before edge proof.**

Specifically:

- ✅ Saved verbatim to `docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md`
- ✅ Section-by-section mapping to existing components (Patches 1+3+5, regime_classifier.py, run.py)
- ✅ Identified what's genuinely NEW (capital allocation 50/35/15, portfolio risk governor, formal drift-disable automation, sector correlation cap)
- ✅ Honest gating: 3 of 4 engines depend on signals our 5 rigor levels proved null
- ✅ B.2.4 branch added to PHASE_B_DECISION_TREE (after B.2.1 ensemble, B.2.2 maker, B.2.3 on-chain)
- 🛑 NOT implementing engine code pre-edge-proof
- 🛑 NOT skipping 4-gate validation
- 🛑 NOT skipping Stage 1+2 capital ladder

## Why "real spec ≠ ready to deploy"

The spec assumes the engines have edge. Engine A's "Breakout above 20-period range high + Volume ≥ 170% + Delta acceleration spike + ATR expansion" is exactly the feature class the 7-filter battery + Bayesian sweep + ensemble alignment + D6 binding all classified as null on Gate.io spot at 30 bps fees.

A more sophisticated orchestration of null edges = a more sophisticated way to lose money.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| A. Implement Engine A/B/C immediately | Bypasses ADR-001 (validate before deploy), bypasses 4-gate, bypasses Stage 1+2 ladder; would just deploy null edge with fancier orchestration |
| B. Refuse spec outright | Spec is real engineering, not vibes; deserves real engagement and documentation |
| C. Cherry-pick portfolio-risk-governor + drift-disable for immediate implementation (the parts that don't need edge) | Considered viable, deferred to post-Stage-1 to avoid premature optimization |
| **D. Save spec, add to decision tree, gate on B.2.3 edge proof** ⭐ | balances respect for the spec with discipline; treats it as the right post-edge-proof candidate |

## Consequences

**Enabled:**
- Spec preserved + indexed + cross-linked. Future Claude sessions read [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](../../docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md) when relevant
- B.2.4 branch in decision tree gives a concrete post-B.2.3 path
- Clear mapping: what's already built (regime classifier, Patches 1+3+5), what's genuinely new (allocation model, portfolio governor, drift automation)

**Costs:**
- Engineering hours documenting (low cost)
- Risk that spec author interprets "documented" as "approved for deployment" — explicitly prevented by gating in Section V/VII of the spec doc

## Reversibility

100%. Documentation only. To undo: `rm docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md`. No code, no production wiring, no live deployment.

## Re-evaluation triggers

Activate B.2.4 implementation when:
1. B.2.3 (on-chain B1) OR another B-prime branch produces a validated edge ≥ +5 bps net per trade
2. That edge clears 4-gate validation (rolling WF / MC permutation / fee stress / bootstrap CI)
3. That edge clears 60-day Stage 1 paper validation (≥30 trades, PnL>0, DD<5%, Sharpe≥0.5)
4. THEN consider building portfolio-orchestrator on top of validated engines per this spec

Until #1-#3 are met, the spec stays as research artifact only.

## ADR linkage

- **ADR-001** — D-day discipline: validation before deployment ✅ honored
- **ADR-002** — Phase B direction: B.2.4 fits as post-edge-proof orchestration layer ✅
- **ADR-003** — D7 freeze: expired 2026-05-01 00:00 UTC; this commit is post-D7 ✅
- `feedback_drift_pattern.md` (memory) — never silently build from vision pastes ✅ this spec gets real engagement, not silent build

## Related

- [docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md](../../docs/specs/L99_HYBRID_PORTFOLIO_GOD_MODE.md) — full spec verbatim + mapping + gating
- [[findings/2026-04-30-d6-binding-no-go]] — proves current data class is null
- [[findings/2026-04-28-bayesian-sweep-null]] — proves 0 of 11 microstructure cells profitable
- [[findings/2026-04-28-ensemble-alignment-null]] — proves multi-feature ensemble doesn't help on null data
- [[decisions/2026-04-29-miroshark-research-only]] — same pattern: real project, ADR-compliant research, no premature deploy
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — branch structure
