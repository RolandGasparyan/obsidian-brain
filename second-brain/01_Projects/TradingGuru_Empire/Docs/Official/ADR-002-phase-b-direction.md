# ADR-002: Phase B direction — what to build on a detected signal

**Status:** Conditional — activates only if ADR-001 analyzer gate passes (~2026-04-30)
**Deciders:** Roland (operator)

## Context

If Phase A analyzer finds ≥1 feature with `|IC| ≥ 0.04, |t| ≥ 2.0` on ≥2
pairs, we have statistically detectable signal at some horizon between 60s
and 1800s. We then need the right architecture to extract alpha from it
without overfitting.

## Spot fee calibration (2026-04-25 update)

Operator confirmed Phase B target market is **Gate.io spot, not
perpetual futures**. This recalibrates every fee gate:

| Parameter | Spot economics |
|---|---|
| Maker fee | 0.10% |
| Taker fee | 0.15% |
| Round-trip break-even | 0.20% |
| Realistic round-trip with slippage | 0.25% |
| L99 minimum edge gate (S5) | 0.30% (was 0.12% on futures) |
| L99 aggressive edge gate | 0.50% (was 0.25%) |

Practical implication: many candidate signals that would be tradable
on futures will be filtered out by the fee-aware edge agent on spot.
That is the correct behavior. Spot is harder. Better to know going in.

Sharpe ceiling realistic: 0.5-1.5 on spot vs 1.5-2.5 on futures for
the same architecture. Lower trade frequency, higher per-trade conviction.

The Phase B architecture options (α threshold / β ML / γ regime gate)
all stand, but each candidate must clear the 0.30% net edge gate, not 0.12%.

## Decision (conditional)

Apply this table to the analyzer's output:

| Passing feature(s) | Phase B option |
|---|---|
| basis_pct or funding_rate_8h (multi-hour) | **γ** — regime-gate existing Vote bots |
| OFI or micro_price (sub-10-min) | **α** — single-feature threshold strategy |
| Multiple features, all weak | **β** — ML ensemble with brutal walk-forward |
| book_slope asymmetry only | **α first**, defer δ (market-making) |

## Options Considered

### α — Single-feature threshold (simplest)

Trade when surviving feature is in top/bottom decile of rolling distribution.
Exit on mean-reversion to median.

- Complexity: ~200 LoC
- Fee headroom: requires IC ≥ 0.08 to survive 0.20% round-trip
- Overfit risk: low (one parameter)
- Time to paper-deploy: 2–3 days

### β — LightGBM ensemble on all 11 features

Predict sign of forward return from full feature set + rolling stats.

- Complexity: ~600 LoC
- Data needs: ≥ 30 days diverse regimes (5 days is marginal)
- Overfit risk: **high** (11 raw × rolling stats = hundreds of effective features)
- Time to paper-deploy: 1 week

### γ — Regime gate on existing Vote bots

Use surviving feature as binary classifier: "bull regime" (enable Vote
ensemble) vs "chop regime" (force USDT).

- Complexity: ~400 LoC
- Data needs: 5 days sufficient for binary gate
- Overfit risk: low (one threshold)
- Time to paper-deploy: 3–4 days

### δ — Market-making prototype

If book-slope asymmetry is the passing signal, go directly to MM: quote
tighter on thicker side, wider on thinner.

- Complexity: ~2,000 LoC (real OMS + inventory risk model)
- Data needs: months of regime calibration
- Expected Sharpe: 1.5–3.0 if calibrated, 0 otherwise
- Time to paper-deploy: 3–4 weeks
- **Verdict:** defer. Too large a commit without stronger signal.

## Trade-off Analysis

Microstructure signals decay rapidly. Even IC 0.06 at 300s may be competed
away during our 2-week paper-validation window. **Regime gating (γ) has the
longest half-life** because it rides existing Vote logic and only adds a
filter — no new trading logic to compete on.

Threshold (α) is the simplest mapping from IC to P&L but is most exposed to
decay.

ML (β) is the highest-ceiling option but requires ≥ 30 days of data. 5 days
is too short — would overfit even with nested CV.

## Consequences

**Easier:** Concrete decision rule based on what the data shows.
**Harder:** If multiple features pass, choice between γ and α is subjective.
**Revisit:** If Phase B paper validation also fails, re-open ADR-001 with
Option B (edge-class pivot) as the accepted path.

## Action Items (activate on gate pass)

1. [ ] Identify passing feature(s) + horizon(s) from analyzer
2. [ ] Apply decision table → select α / β / γ
3. [ ] Implement in ≤ 1 week using existing harness
4. [ ] Walk-forward validate via `professional_backtest.py` 70/30 OOS
5. [ ] Paper-deploy alongside Vote bots for 30-day parallel test
6. [ ] Real money only after 30-day parallel shows positive OOS
