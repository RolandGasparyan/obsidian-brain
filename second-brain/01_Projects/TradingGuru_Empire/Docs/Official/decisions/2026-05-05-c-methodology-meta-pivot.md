# Decision — Path C: Methodology Meta-Pivot Selected

**Date:** 2026-05-05
**Status:** decided
**PR:** #29
**Tags:** decision, methodology, post-11-null

## For future Claude

After 11 distinct factor families produced NULL verdicts under increasingly strict methodology (D6, l99_first, C2_4H, C1, NATIVE, NATIVE_D2, B1, B2, B3, A2, V1), the operator selected path C — codify lessons into durable artifacts — over path A2 (one more factor family) and path B (accept null + lock).

Rationale: A2 = continuing the same expected-value-zero loop; B = leaves nothing transferable for future research. C converts the dearly-purchased lessons into a structurally bias-resistant framework that survives session resets and works regardless of whether new data sources or capital arrive.

## Decision

Stop new factor research. Build:

1. **`docs/specs/NULL_REGISTRY.md`** — canonical 11-NULL ground truth + 11 methodology rules
2. **`docs/specs/L99_ALPHA_VALIDATION_AMENDMENTS.md`** — locks thresholds, formalizes §3.5 backtest gate, extends §4 mechanism audit
3. **7 concept pages in `wiki/concepts/`** — atomic codification of recurring lessons
4. **`wiki/research-log/_template.md` upgrade** — Phase-by-phase checklist that prevents repeat of caught traps
5. **`wiki/log.md` + `wiki/index.md` regenerated** — current as of 2026-05-05

## What this prevents

- Lowering L99 thresholds to manufacture a "pass" (locked in amendments)
- Re-testing a NULL family with the same construction (re-spec discipline)
- Skipping §3.5 backtest gate after passing L99 (now mandatory)
- Forgetting the |abs| forward signal pitfall (B2/B3 lesson codified as Rule 1 + concept page)
- Forgetting per-leg fee math (B1 lesson codified as Rule 2 + concept page)
- Forgetting cross-sectional ≠ sequential (A2 lesson codified as Rule 6 + concept page)
- Forgetting trend-context for mean-reversion factors (V1 lesson codified as Rule 7 + concept page)

## Position when decided

100% USDT. 17 L99 modules dormant. No live config integration. No threshold tuning.

## What CAN happen after this PR merges

- **Pause all new factor research** until material change (new data class, new capital tier, options/orderbook access)
- **Future agent sessions** start from `_CLAUDE.md` + `index.md` + `NULL_REGISTRY.md` + amendments — automatically inheriting the discipline
- **If a 12th factor family is proposed**, it must (a) cite which Rules in NULL_REGISTRY it does NOT trigger, (b) include §3.5 gate from day 1, (c) come with operator approval as a separate decision doc

## What MUST NOT happen after this PR

- Loosen any threshold without an operator-approved decision doc
- Re-test V1, A2, or any other NULL family with tweaked parameters and call it new
- Promote AVAX-only V1 result to "candidate"
- Skip §3.5 evaluation on a new factor

## Sources

- [[findings/2026-05-05-a2-backtest-bt-falsifies-candidate]] (PR #27)
- [[findings/2026-05-05-v1-vwap-gap-mean-rev-11th-null]] (PR #28)
- [[findings/2026-05-05-c-methodology-meta-pivot]]
- [[concepts/null-pattern-convergence]]
- [docs/specs/NULL_REGISTRY.md](../../docs/specs/NULL_REGISTRY.md)
- [docs/specs/L99_ALPHA_VALIDATION_AMENDMENTS.md](../../docs/specs/L99_ALPHA_VALIDATION_AMENDMENTS.md)
- Operator instruction sequence 2026-05-05: A2 backtesting → "katarelagorcel" attempt → path A pivot → "vorna amen lavy" path-C selection
- Memory rule `feedback_drift_pattern.md`
