# NULL_REGISTRY — canonical record of falsified factor families

**Purpose:** every factor family that has been research-tested in this
project and produced a NULL verdict, recorded in a single ground-truth
table so future researchers (human or agent) can see at a glance:

  1. Which mechanism has already been falsified
  2. Why it failed (one sentence)
  3. The methodology lesson surfaced
  4. The PR / finding doc where it lives

**Discipline:** no factor family on this list may be re-tested with the
same construction. A "re-spec" requires (a) a different mechanism,
(b) a different decision rule, (c) operator approval as a decision
doc — not a silent retry.

**Last updated:** 2026-05-05

---

## Cumulative pattern (11 NULLs, 11 distinct mechanisms)

| # | Family | Hypothesis | Failed because | Lesson surfaced | Finding doc |
|---|---|---|---|---|---|
| 1 | D6 microstructure | tick-level orderbook imbalance predicts forward 1-5m | edge < fee gate | first encounter of "edge < fees = no edge" | (D6 NO-GO) |
| 2 | l99_battery first run | factor pipeline against collected data | N < 100 in collected window | sample size cannot be hand-waved; collect more or shrink scope | `2026-05-02-l99-battery-first-run-insufficient-data.md` |
| 3 | C2_4H | 4h volatility expansion regimes | condition criteria mis-aligned with available data shape | spec must be testable in current data class before counting as "tested" | `2026-05-02-c2-4h-structural-infeasibility.md` |
| 4 | C1 BTC-DXY joint | macro condition + crypto condition jointly | joint-condition rarity → N too small in any sub-population | joint conditions multiply rarity; budget N before joining | `2026-05-02-c1-btc-dxy-structural-infeasibility.md` |
| 5 | NATIVE per-pair | per-pair 4h native factors | N < 100 + Gate.io API depth limit | API depth is a real constraint, not a flag to ignore | `2026-05-02-l99-native-only-look-ahead-caught.md` |
| 6 | NATIVE D2 corrected | re-run after look-ahead correction | look-ahead artifact had been the entire "edge" | look-ahead is a methodology bug, not a tuning parameter | `2026-05-02-l99-native-only-look-ahead-caught.md` |
| 7 | B1 funding mean | funding extremes → mean-reversion | sample window too short + per-leg fee math 100× off + L99.QUINTILE_MIN unit-inconsistent | fee math, sample bounds, and unit consistency are show-stoppers; Council-review caught it | `2026-05-05-b1-corrected-collapses-to-null.md` |
| 8 | B2 OI spike + flat price | high OI buildup → vol expansion | `\|abs\|` forward signal is not directionally tradeable on perp | SIGNED forward returns mandatory; `\|abs\|` only valid for long-vol instruments | `2026-05-05-b2-b3-extended-methodology-pitfall.md` |
| 9 | B3 basis compression | basis z → vol expansion | same `\|abs\|` pitfall + spec hypothesis directionally rejected | cross-pair sign consistency required to claim universe-level mechanism | `2026-05-05-b2-b3-extended-methodology-pitfall.md` |
| 10 | A2 stablecoin supply impulse | USDT+USDC growth z → bullish drift | clears L99 cross-sectional Q5−Q1; fails sequential equity backtest; paired/regime "perfecting" makes it WORSE | L99 quintile-spread is necessary-but-not-sufficient; need §3.5 backtest gate | `2026-05-05-a2-backtest-bt-falsifies-candidate.md` |
| 11 | V1 VWAP-gap mean-rev | z-extreme gap reverts to VWAP | mean-rev fades trends; 2023-2026 strongly trending → wrong-signed bets | trend-context awareness mandatory before deploying mean-rev factors | `2026-05-05-v1-vwap-gap-mean-rev-11th-null.md` |
| 12 | X1 funding sign-flip event-study | 8h funding sign-flip = stress-relief mean-reversion catalyst (paired Q1−Q5) | event-study geometry produced 0/15 L99 + 0/5 §3.5 pairs; harness rejected the candidate cleanly on first non-regression use | event-studies on Gate.io retail data + 4h cadence inherit the same "no edge here" empirical signal as continuous factors; the harness works as designed (Rule 6 + Rule 10 mechanically enforced) | `2026-05-05-x1-funding-signflip-12th-null.md` |

---

## Methodology lessons crystallized from this list

These are the **structural rules** future research must obey. Each is
tied to the NULL that surfaced it. Violating any one resurrects an
already-falsified path.

### Rule 1 — SIGNED forward returns (B2/B3 lesson)
Forward return must be `(close[i+h] − close[i]) / close[i]`, **signed**.
`|abs|` proxies measure volatility prediction (long-vol payoff), not
directional perp edge. Skip `|abs|` testing unless you have a
long-vol instrument available.

### Rule 2 — Per-leg fee math (B1 lesson)
Per-leg fee in bps is `fee_rate * 10000` (single side); round-trip is
`* 2`. Quintile-spread NET = `(Q5 − Q1) * 100 − fee_rt * 10000 * 2`.
A bug here is invisible in the metrics and silently passes broken
factors. `L99.QUINTILE_MIN` is in **bps** (60.0), not 0.60.

### Rule 3 — Look-ahead clean alignment (NATIVE D2 lesson)
Any signal-to-bar alignment that uses daily / lower-frequency data
inside higher-frequency bars must use `bisect_right(sorted_ts, bar_ts) - 1`
(strictly past). Anything that includes the bar's own day's close is
look-ahead.

### Rule 4 — Cross-pair sign consistency (B2 lesson)
A "universe factor" that has positive IC on some pairs and negative IC
on others is not a universe factor — it is a per-pair pattern. Require
≥ 4 of 5 pairs to share IC sign before counting universe-level.

### Rule 5 — N budget before joint conditions (C1 lesson)
Joining two conditions with empirical rates `p1` and `p2` produces a
joint rate ≤ `p1 * p2` plus correlation noise. Compute the expected
joint N **before** running; if expected N < 200, do not run.

### Rule 6 — Cross-sectional pooling ≠ sequential trading (A2 lesson)
L99 Q5−Q1 measures cross-sectional rank-correlation; backtesting.py
measures sequential equity. A factor can pass cross-section and fail
backtest because of:
  (a) temporal heterogeneity (one good year masking three bad years)
  (b) entry/exit timing non-equivalence to perfect-pairing
  (c) compounding drawdowns that the t-stat ignores
Therefore §3.5 (backtest) is **mandatory** alongside §3 (paper).

### Rule 7 — Mean-reversion needs regime context (V1 lesson)
Mean-reversion strategies systematically lose money in trending markets.
Before deploying any mean-reversion factor, demonstrate that the
deployment regime contains sufficient sustained range periods (N ≥ 100)
and that the factor's IC is positive within those range periods
specifically. Universe-level "marginal" results in trending macros are
not deployable.

### Rule 8 — `|IC|` near zero with high t-stat is a red flag (B2/B3 lesson)
When the underlying signal is `|abs|` or otherwise non-directional, the
distribution of returns is one-sided and t-stat is mechanically inflated
by win-rate ~100%. Investigate PF >> 100 and t-stat >> 5 with extreme
suspicion.

### Rule 9 — Threshold discipline (this entire arc's lesson)
L99 thresholds (`IC ≥ 0.04`, `t ≥ 2.0`, `PF ≥ 1.3`, `Q5−Q1 ≥ 60 bps NET`,
`MC ≥ 80%`, `Reg ≥ 2`, `N ≥ 100`) are **locked**. Tuning them down to
manufacture a pass is curve-fit drift, not research. The 11-NULL
pattern argues the thresholds are correctly calibrated.

### Rule 10 — §3.5 backtest gate is non-negotiable (V1 lesson)
A candidate that clears L99 must additionally produce:
  - Sharpe ≥ 1.0 over full available history
  - Beat per-pair buy-and-hold benchmark
  - ≥ 3 of 4 yearly OOS folds with Sharpe > 0
  - MaxDD > −25%
  - ≥ 30 trades for power
  - Win Rate ≥ 40%

These are evaluated programmatically via `backtesting.py`. No manual
override.

### Rule 11 — Re-spec ≠ retry (this whole project's lesson)
After a NULL, do not "tune" the same factor with different parameters.
Either (a) move on to a different mechanism, or (b) submit an
operator-approved decision doc that explicitly motivates the new spec
and how it avoids the prior failure mode. A bare retry counts as drift.

---

## Re-test protocol (for adding entry #12+ to this registry)

If a future factor family produces a NULL:

1. Add a row to the table above with:
   - Family name (short)
   - Hypothesis (one-line)
   - Failed-because (one-line — surface mechanism, not symptom)
   - New methodology lesson (or "redundant with rule N")
   - Finding doc filename

2. If the failure surfaced a NEW methodology lesson:
   - Add it as a new Rule N+1 below Rule 11
   - Bump the rule count in the section header

3. If the failure was redundant (already covered by an existing rule):
   - Note "redundant with Rule N" in the table
   - Do NOT add a new rule — duplicate rules dilute discipline

4. Always commit the registry update in the same PR as the NULL finding.

---

## What this registry is NOT

- It is not a leaderboard. There is no "best NULL".
- It is not a roadmap of what to try next. The next factor must come from outside this list, not from the negative space of it.
- It is not a license to retry. A factor on this list cannot be re-tested with the same construction.

---

## Sources

- All linked finding docs in `wiki/findings/`
- `docs/specs/L99_ALPHA_VALIDATION.md` (operator spec)
- `docs/specs/L99_ALPHA_VALIDATION_AMENDMENTS.md` (this PR)
- `wiki/research-log/_template.md` (this PR — upgraded)
