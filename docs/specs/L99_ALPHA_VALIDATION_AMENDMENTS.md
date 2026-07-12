# L99_ALPHA_VALIDATION — Amendments (post-11-NULL methodology meta-pivot)

**Source:** Operator decision 2026-05-05, path C selected after V1 became 11th NULL
**Status:** Amendments to operator-pasted [L99_ALPHA_VALIDATION.md](L99_ALPHA_VALIDATION.md). Original spec preserved verbatim; this file adds clarifications, formalizations, and the §3.5 backtest gate.
**Authority:** these amendments take precedence in any conflict with looser language elsewhere; they cannot be relaxed without operator approval as a new decision doc.

---

## Why this exists

11 factor families have been research-tested in this project. All produced NULL. The convergence is informative, not coincidental: each NULL surfaced a methodology lesson that, once applied, made it harder for the next factor family to slip through with a false positive.

The original `L99_ALPHA_VALIDATION.md` (operator paste, 2026-05-01) captures the right principles but does not yet include:

  - `§3.5` backtest gate (added after A2 cleared cross-section but failed equity)
  - `§4 (extended)` mechanism-audit checklist (added after B2/B3 `|abs|` pitfall)
  - `§1.6 (strengthened)` decision matrix that requires BOTH cross-section AND backtest pass
  - Locked threshold language (no tuning permitted)

This document encodes those additions. Future factor research must conform to both the original spec and these amendments simultaneously.

---

## Amendment A1 — §1.6 Decision Matrix (strengthened)

### Original (preserved)
> If: IC ≥ 0.03; t-stat ≥ 2; OOS positive; Fee-adjusted expectancy positive; Stable across regimes or properly gated → Candidate Alpha. Else → Reject or redesign.

### Amended (this project's locked thresholds)

A factor is a **Candidate Alpha** if and only if it clears ALL of:

**Cross-sectional gate (L99 7-filter battery, locked thresholds):**
  - `|IC| ≥ 0.04` (raised from 0.03 — the prior threshold let A2 through)
  - `|t-stat| ≥ 2.0`
  - `PF ≥ 1.3`
  - `Q5 − Q1 ≥ 60 bps NET` (per-leg fee math: `fee_rt × 10000 × 2`)
  - `MC stability ≥ 80%`
  - `Regime count ≥ 2`
  - `N ≥ 100`

**Backtest gate (§3.5, mandatory — see Amendment A4 below):**
  - `Sharpe ≥ 1.0` on full available history
  - Beat per-pair buy-and-hold benchmark
  - `≥ 3 of 4` yearly OOS folds with `Sharpe > 0`
  - `MaxDD > −25%`
  - `≥ 30` trades for power
  - `Win Rate ≥ 40%`

**Cross-pair sign consistency:**
  - `≥ 4 of 5` pairs share IC sign before counting universe-level result

Failing **any** gate → REJECT. No "marginal pass" exists. No threshold tuning permitted.

---

## Amendment A2 — Locked thresholds (no tuning permitted)

The thresholds in Amendment A1 are **locked** at their stated values. They may not be loosened to manufacture a Candidate Alpha. They may be **tightened** in a future amendment that documents both the empirical justification and the operator approval.

The 11-NULL pattern is treated as evidence that the current thresholds are correctly calibrated, not as evidence that they are too strict.

Specifically prohibited:
  - Lowering `Sharpe ≥ 1.0` to "Sharpe ≥ 0.5" because "we have a positive return"
  - Reducing `MaxDD > −25%` to "−40%" because "crypto is volatile"
  - Reducing `≥ 3 of 4 good years` to "best year shows edge"
  - Lowering `|IC| ≥ 0.04` to "0.02" because "small edges compound"

Each of these has been considered in the 11-NULL post-mortem and rejected.

---

## Amendment A3 — Per-leg fee math (B1 lesson, codified)

Per-leg fee in basis points equals `fee_rate * 10000` (one side). Round-trip is `× 2`.

Quintile-spread NET in basis points:

```
Q5_Q1_net_bps = (mean(Q5) - mean(Q1)) * 100 - fee_rt * 10000 * 2
```

`L99.QUINTILE_MIN` is in **basis points** (= 60.0). The earlier value `0.60` was unit-inconsistent; PR #24 corrected it. Any future code that re-introduces `0.60` is wrong.

Per-leg fee tiers (Gate.io retail):
  - `A_VIP0_taker`       = `0.00125` per side  (25 bps RT)
  - `B_VIP1_GT_discount` = `0.00090` per side  (18 bps RT)
  - `C_VIP1_maker_only`  = `0.00070` per side  (14 bps RT)

For paired trades (long X / short Y), commissions apply to **both** legs simultaneously; effective per-side fee is `2 × fee_per_leg`.

---

## Amendment A4 — §3.5 Backtest Gate (NEW, mandatory)

### Why §3.5 exists

A2 (PR #26) cleared L99 cross-section with 7 of 27 combinations passing. The same factor, when placed inside a `backtesting.py` equity-curve harness (PR #27), produced:
  - Full-history Sharpe `0.25` (well below `1.0`)
  - 9× underperformance vs ETH buy-and-hold
  - Monotonically degrading Sharpe across yearly folds (`+0.97 → +0.01 → −0.27 → −0.54`)

The cross-sectional rank-correlation that L99 measures is **not** the same quantity as the sequential equity-curve return that determines deployability. A factor can pass the former and fail the latter because of:
  - Temporal heterogeneity (one-year survivorship)
  - Entry/exit timing non-equivalence to perfect Q5−Q1 pairing
  - Compounding drawdowns invisible to the t-stat

§3.5 closes this gap.

### §3.5 specification

A candidate factor must produce, via a `backtesting.py` (or equivalent) full-equity harness:

```
Sharpe Ratio       ≥ 1.0   on full available history (≥ 3 years preferred)
Return [%]         > Buy & Hold Return [%]   on the relevant pair / universe
Max Drawdown [%]   > -25%
# Trades           ≥ 30
Win Rate [%]       ≥ 40%
Yearly OOS folds:  ≥ 3 of 4 (or ≥ 75% of available years) with Sharpe > 0
```

These are evaluated **programmatically** within the runner script, with hard pass/fail. The runner saves a single boolean `gate_pass` plus a list `gate_failures`. No human override.

The gate is applied at the most generous fee tier first (maker). If the strategy fails at maker, it is REJECTED — there is no point evaluating taker.

### §3.5 implementation pattern

Reference: `v1_vwap_gap.py` `gate()` function. Recommended signature:

```python
def gate(full_stats: Dict, yearly_stats: Dict[str, Dict]) -> Tuple[bool, List[str]]:
    """Return (gate_pass, list_of_failures)."""
```

Future factor runners must include this function and call it before promoting any candidate to §3 (Stage 1 paper validation).

---

## Amendment A5 — §4 Mechanism Audit Extended

### Original §4 (Phase 4 in `_template.md`)
> Mechanism specifically named (one of: behavioral / flow / mechanical / reflexive). Cannot be re-explained as overfitting.

### Extended (lessons from B2/B3, A2, V1)

In addition to the original, every factor must pass the following audit before §3 / §3.5 evaluation:

**A5.1 — Forward signal directionality**
  - [ ] Forward return is `(close[i+h] − close[i]) / close[i]`, **signed**
  - [ ] **NOT** `|abs|` of price change (that proxies vol expansion, not direction)
  - [ ] If using `|abs|`, the strategy must be a long-vol instrument (options, variance swap), not a perp directional trade

**A5.2 — Decision rule per quintile**
  - [ ] Hypothesis specifies whether the trade is `long Q5` / `short Q5` / `long Q1−short Q5` (paired)
  - [ ] Mean-reversion factors flip sign convention: `long Q1` / `short Q5`
  - [ ] Direction must be locked **before** running L99, not chosen after seeing the result

**A5.3 — Cross-pair sign consistency**
  - [ ] At least 4 of 5 universe pairs share IC sign
  - [ ] If only 1 pair shows edge, that is a **per-pair pattern**, not a universe factor
  - [ ] Per-pair patterns require their own decision doc and cannot be backfitted to a universe spec

**A5.4 — Look-ahead audit**
  - [ ] Signal at `bar[i]` uses only data with timestamp `≤ bar[i].ts`
  - [ ] If aligning daily / lower-freq data into 4h bars, use `bisect_right(sorted_ts, bar_ts) - 1` (strictly past)
  - [ ] Forward returns use `closes[i + h]` for `h ≥ 1`; never `closes[i]`

**A5.5 — Joint-condition N budget**
  - [ ] If signal requires conditions A AND B, expected joint N is computed before the run
  - [ ] If expected joint N < 200, the joint condition is rejected; either widen one condition or pick a different factor

**A5.6 — Trend-context check (mean-rev factors only)**
  - [ ] If the factor is mean-reversion, demonstrate sustained range regimes exist in the test window with N ≥ 100
  - [ ] In strongly-trending macros (any pair with `>±50%` 12-month return), mean-reversion factors are pre-rejected unless the trend regime can be filtered out cleanly

**A5.7 — `|IC|` near zero with high t-stat is a red flag**
  - [ ] If `t-stat > 5` but `|IC| < 0.05`, investigate
  - [ ] Likely cause: one-sided return distribution (e.g. `|abs|` forward signal)
  - [ ] Likely cause: outlier dominance (PF > 100 means a few big wins drive everything)

---

## Amendment A6 — Re-spec discipline

A factor family that has produced a NULL (see [`NULL_REGISTRY.md`](NULL_REGISTRY.md)) cannot be re-tested with the same construction.

Re-spec requires:
  1. **Different mechanism** — not just different parameters
  2. **Different decision rule** — not just different threshold values
  3. **Operator-approved decision doc** — explicitly motivates the new spec and how it avoids the prior failure mode
  4. **Listed failure mode of the prior NULL** — proof that the new spec doesn't re-trigger the same trap

A bare retry counts as drift and is prohibited per the project's `feedback_drift_pattern.md` memory rule.

---

## Amendment A7 — Discipline state recording

Every factor research run must record, alongside its results JSON:

```json
{
  "discipline_state": {
    "position_when_started": "100% USDT",
    "position_when_finished": "100% USDT",
    "live_config_changed": false,
    "thresholds_modified": false,
    "deployment_attempted": false,
    "operator_decision_doc_required_for_promote": true
  }
}
```

If `live_config_changed`, `thresholds_modified`, or `deployment_attempted` are true at any point, that PR is automatically blocked from merge until the operator approves a separate decision doc explaining why.

---

## Amendment A8 — NULL registry as ground truth

The [`NULL_REGISTRY.md`](NULL_REGISTRY.md) file is the canonical record of falsified factor families. Every NULL finding MUST add a row to that file in the same PR as the finding doc.

The registry's "Methodology lessons crystallized" section is the de-facto source of truth for project methodology. Conflicts between this amendments doc and the registry's lesson list must be reconciled — both are authoritative, and discrepancies are bugs.

---

## Sources

- [`L99_ALPHA_VALIDATION.md`](L99_ALPHA_VALIDATION.md) — original spec preserved verbatim
- [`L99_RESEARCH_ROADMAP.md`](L99_RESEARCH_ROADMAP.md) — companion architecture spec
- [`NULL_REGISTRY.md`](NULL_REGISTRY.md) — 11-NULL ground truth
- All `wiki/findings/2026-05-*` finding docs
- Operator decision 2026-05-05 selecting path C (methodology meta-pivot)
- `feedback_drift_pattern.md` (user memory) — drift discipline source
