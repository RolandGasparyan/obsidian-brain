# RESEARCH ARC COMPLETE — formal decision to pause factor research

**Status:** **PAUSED** until material change in inputs
**Decided:** 2026-05-05
**Authority:** Operator decision after 12 convergent NULLs via 12 distinct mechanisms
**Position:** 100% USDT (locked indefinitely under current inputs)
**Framework readiness:** harness + amendments are PRODUCTION READY for any future factor research when inputs change

---

## Why this decision exists

This document formalizes the operator's strategic choice to stop active factor research at the close of the 12-NULL arc. It is not a defeat — it is the same `feedback_drift_pattern.md` discipline applied at the meta-level: **the framework has spoken honestly, and continuing to test factors against unchanged inputs is the same drift it was built to prevent**.

12 NULLs via 12 mechanically distinct mechanisms is overwhelming empirical evidence. Each successive NULL has surfaced **fewer** new methodology lessons. X1 (NULL #12) was explicitly redundant with Rule 10. The marginal value of NULL #13 against current inputs is approximately zero.

A senior researcher's response after 12 NULLs is not "try factor #13". It is "what would change the inputs?".

---

## What the framework has earned

After this arc, the project owns:

  - 12 falsified factor families catalogued in [`NULL_REGISTRY.md`](NULL_REGISTRY.md)
  - 11 crystallized methodology rules (Rule 1 → Rule 11)
  - L99 7-filter battery with locked thresholds (Amendment A1, A2)
  - §3.5 backtest gate, validated in production (caught XRP marginal-positive on X1)
  - `factor_research_harness.py` v1.0.0 — single canonical entry point that physically refuses to violate any rule
  - 6 open / merged PRs documenting the arc end-to-end (#27 through #32)

This is durable infrastructure. It does not depreciate just because the operator stops feeding it new specs. It will be ready the moment any input changes.

---

## Empirical summary — 12 NULLs

| # | Family | Year of NULL | Failure mode |
|---|---|---|---|
| 1 | D6 microstructure | 2026-04 | edge < fee gate |
| 2 | l99 first run | 2026-05 | N < 100 |
| 3 | C2_4H | 2026-05 | condition mis-alignment |
| 4 | C1 BTC-DXY | 2026-05 | joint-condition rarity |
| 5 | NATIVE per-pair | 2026-05 | N < 100 + API depth |
| 6 | NATIVE D2 corrected | 2026-05 | look-ahead artifact |
| 7 | B1 funding mean | 2026-05 | sample window + fee math bugs |
| 8 | B2 OI spike | 2026-05 | `\|abs\|` not directionally tradeable |
| 9 | B3 basis compression | 2026-05 | same `\|abs\|` + spec rejection |
| 10 | A2 stablecoin supply | 2026-05 | clears L99, fails equity backtest |
| 11 | V1 VWAP-gap mean-rev | 2026-05 | wrong-signed in trending market |
| 12 | X1 funding sign-flip | 2026-05 | high cadence cannot beat B&H |

The arc spans roughly two months of intensive research. Each NULL was documented in its own finding doc with mechanism-level diagnosis.

---

## What "material change in inputs" means

Research resumes when AT LEAST ONE of the following changes:

### Capital
  - Capital crosses a threshold where tier-VIP fee discounts become accessible (Gate.io VIP3+ ~$1M+)
  - OR allocation to OTC desks where bid/ask spread overhead drops below current taker
  - Without this, every additional bps of round-trip fee makes the §3.5 gate harder, not easier

### Data access
  - **Options data** (Deribit / OKX options chains): enables vol-prediction factors that B2/B3 had no instrument for
  - **L1/L2 orderbook** (full-depth, not metrics): enables genuine microstructure factors at higher frequency than D6 caught
  - **Private signal feeds** (e.g. on-chain MEV bundle previews, professional CEX-CEX latency feeds, Tier-1 funding-flow APIs): enables information-asymmetry plays
  - **Cross-venue arbitrage data** (DEX prices in real-time): enables triangular arbitrage factors not testable on Gate.io alone

### Infrastructure
  - **Sub-second execution** (colo or near-colo) — the 4h cadence in this arc was a constraint imposed by Gate.io public API, not a choice
  - **HFT-grade signal-to-execution latency** (<10ms): enables aggressor-detection factors

### Market regime
  - Sustained range-bound regime (≥ 6 months on ≥ 3 of 5 pairs) — enables mean-reversion factor families that V1 was wrong-signed against
  - Genuine bear regime with sufficient N for statistical testing
  - Note: this is the WEAKEST trigger. Regime change without input change still leaves us with the same fee + cadence + data constraints. Proceed only with explicit operator decision doc.

Any of these triggers a "research resume" decision doc that explicitly references this RESEARCH_ARC_COMPLETE.md. **Without an explicit trigger, no new factor research is warranted.**

---

## What stays alive

  - **Position management**: 100% USDT held indefinitely. No stage-1 paper validation runs (none of the 12 candidates qualified). The L99-stack 17 modules remain dormant.
  - **Framework**: `factor_research_harness.py`, `NULL_REGISTRY.md`, `L99_ALPHA_VALIDATION_AMENDMENTS.md`, `wiki/research-log/_template.md` — all canonical on `main` once PRs #29-#32 merge.
  - **Drift discipline**: `feedback_drift_pattern.md` user memory rule remains binding. This decision doc is itself an application of that rule at meta-level.

## What stops

  - No new factor specs proposed
  - No re-tests of registered NULLs (per Rule 11 / Amendment A6)
  - No threshold tuning
  - No live deployment attempts
  - No paper-validation runs on candidates that failed §3.5 (XRP X1 etc.)

## What MUST NOT happen

🛑 Re-spec X1 with different sign-flip threshold ("but it had positive return on XRP!")
🛑 Lower §3.5 thresholds to manufacture a Stage 1 promotion
🛑 Test factor #13 without an explicit material-change decision doc
🛑 Claim "12 NULLs is bad luck"
🛑 Use the harness as a paper-validation runner for any prior NULL
🛑 Substitute architecture work or "engine refactor" for edge — the L99 spec's own §4 forbids this

---

## Operator-accountability cadence

When research is paused, operator should still:

  - Quarterly: review `NULL_REGISTRY.md` for any retroactive lesson updates (e.g., new public methodology paper that surfaces a Rule 12)
  - Quarterly: verify position is still 100% USDT and no drift attempts have occurred
  - Annually: review whether any "material change" trigger has fired
  - Continuously: any new spec idea must be validated against `null_registry_distinction` BEFORE writing code

This is light overhead. It costs ~2 hours/year. The alternative is rebuilding cognitive state from scratch when a trigger eventually fires.

---

## Why this is the senior-researcher move

A junior researcher's response after 12 NULLs: "let me try factor #13".

A senior researcher's response: "what does the 12-NULL signal teach me?".

The signal is: **simple statistical-factor strategies on retail Gate.io public 4h data with current capital and infrastructure do not have demonstrable edge in 2023-2026 crypto markets**. This is informative. It is not a setback. It is a calibrated empirical answer to the question the framework was built to ask.

Acting on the answer = stop. Ignoring the answer to keep producing research artifacts = drift.

The same `feedback_drift_pattern.md` rule that prevented PR #1's "live deploy" attempt now prevents PR #32+'s "factor #13 attempt". Both are the same discipline applied at different scales.

---

## Acceptance criteria for this decision

This document is accepted (i.e. research arc is formally closed) when:

  - [x] All 12 NULLs are catalogued in `NULL_REGISTRY.md`
  - [x] L99 thresholds and §3.5 gate are codified (`L99_ALPHA_VALIDATION_AMENDMENTS.md`)
  - [x] Harness is shipped and regression-tested against ≥ 1 prior NULL
  - [x] Harness is production-validated against ≥ 1 fresh spec (X1)
  - [x] Discipline state recorded in every artifact: position 100% USDT, no live config change, no threshold modification
  - [ ] Operator merges PRs #29 → #30 → #31 → #27 → #28 → #32 to canonicalize on `main`

The last checkbox is the only outstanding item. It is operator-only — agent cannot self-merge per discipline.

---

## Resumption protocol

If a "material change" trigger fires:

1. Operator drafts a new decision doc: `docs/specs/RESEARCH_RESUMED_<YYYY-MM-DD>.md`
2. The new doc explicitly references this RESEARCH_ARC_COMPLETE.md and identifies which trigger fired
3. New factor specs proposed via the harness only (`factor_research_harness.py`)
4. NULL_REGISTRY auto-augmented per Amendment A8

No silent resumption. No "I had a great idea, let me just try it". The doc-then-spec-then-harness-then-result discipline is the entire reason 12 NULLs was a clean experiment instead of a chaotic year of vibes.

---

## Final position

**100% USDT.** Indefinitely, until material change.

This is the single number that summarizes the arc. The framework has produced a durable empirical answer; the operator has the discipline to act on it; the cognitive infrastructure is ready for whatever change comes next.

---

## Sources

- 12 finding docs in `wiki/findings/2026-04-*` and `wiki/findings/2026-05-*`
- [`NULL_REGISTRY.md`](NULL_REGISTRY.md) — canonical 12-NULL ground truth
- [`L99_ALPHA_VALIDATION.md`](L99_ALPHA_VALIDATION.md) (operator paste, preserved verbatim)
- [`L99_ALPHA_VALIDATION_AMENDMENTS.md`](L99_ALPHA_VALIDATION_AMENDMENTS.md) — A1-A8
- `factor_research_harness.py` v1.0.0 — production-validated single entry point
- `feedback_drift_pattern.md` (user memory) — drift discipline at meta-level
- Operator instruction "vorna chisht?" 2026-05-05 selecting Option 1
