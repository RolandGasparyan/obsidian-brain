# ADR-003: Week-level action plan

**Status:** Accepted (2026-04-25)
**Deciders:** Roland (operator)

## Context

ADRs 001 and 002 resolve strategic direction. This ADR locks in the
day-by-day plan for the next 7 days to prevent micro-decision drift and
attention leakage.

## Decision

**The next 7 days have exactly one trading-research task: let the data
accumulate.** Everything else is non-trading.

## 7-day schedule

| Day | Date | Action | Time budget |
|---|---|---|---|
| D1 | 2026-04-25 | Commit ADR bundle. Telegram-verify collector + Vote bots. | 15 min |
| D2 | 2026-04-26 | Zero trading work. | 0 |
| D3 | 2026-04-27 | Sanity-check partial analyzer (verify pipeline, NOT interpret IC). | ≤ 1 h |
| D4 | 2026-04-28 | Zero trading work. | 0 |
| D5 | 2026-04-29 | Zero trading work. | 0 |
| D6 | 2026-04-30 | Full 5-day analyzer run. Commit `PHASE_A_RESULTS.md`. | ≤ 2 h |
| D7 | 2026-05-01 | Apply ADR-002 decision table OR trigger ADR-001 fallback. | ≤ 2 h |

## Hard rules

1. **No new strategy code on `main` for 5 days.** Pipeline bug fixes only.
2. **No real money.** Vote bots remain paper-real; collector observe-only.
3. **30-second daily Telegram check.** Verify both services alive.
4. **If operator feels the urge to tune MA50 one more time:** the answer is
   no. We proved that class is dead. Honoring that proof is the whole point
   of ADR-001.
5. **Ambiguous analyzer output** (IC 0.02–0.03, t 1.5–2.0) → default to
   ADR-001 fallback (pivot B1), not a sixth tuning round.

## Consequences

**Easier:** Zero attention on trading for 5 days. Single decision point D7.
**Harder:** Resisting curiosity to re-run with one more tweak mid-accumulation.
**Revisit:** If analyzer output is corrupt (parquet errors, all NaN),
plan rolls back one day and D7 slips accordingly.

## Action Items

1. [x] Phase A v2 deployed (commit `477419c`)
2. [ ] D1: commit this ADR bundle (this document)
3. [ ] D3: partial analyzer sanity-check
4. [ ] D6: full analyzer run + `PHASE_A_RESULTS.md`
5. [ ] D7: green-light Phase B per ADR-002 OR trigger ADR-001 fallback to B1
