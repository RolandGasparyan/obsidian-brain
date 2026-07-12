# L99 — Edge Recovery Mode (profitability optimization core)

**Source:** Operator spec, 2026-04-25
**Status:** Spec verbatim + research backtest in `edge_recovery_backtest.py`

---

## I. The original spec (verbatim)

```
MISSION
  Increase expectancy. Reduce over-filtering. Focus on highest-yield setups.

STEP 1 — REMOVE SIGNAL CLUTTER
  Disable: Ultra Micro Mode · Monte Carlo filter · Dynamic weighting
  Keep:    Regime Filter · Volatility Expansion · Delta Acceleration
            · Depth Imbalance · Edge After Fees · Risk Control
  Minimal stack = higher clarity.

STEP 2 — TIGHTEN ENTRY STRUCTURE
  Enter ONLY when:
    Regime = Expansion
    Delta accelerating
    Break + continuation candle
    Edge ≥ 0.45%
  Raise threshold. Reduce mediocre trades.

STEP 3 — RISK STRUCTURE SHIFT
  Base risk: 0.8%
  Allow winner extension only after BE move.
  Cut losers fast at −0.35%.
  No wide stops. No averaging.

STEP 4 — SESSION FILTER
  Trade only during high-liquidity hours, BTC directional movement,
  news stabilization. No dead sessions.

STEP 5 — FREQUENCY CONTROL
  Max 5 trades per session.
  If 2 losses → stop session.
  Protect capital first.

STEP 6 — PROFITABILITY CHECK LOOP
  After 30 trades:
    if WR < 48% OR avg_R < 1.3 → tighten edge threshold, trade less
    if WR > 55% AND avg_R > 1.5 → enable mild compounding

CORE TRUTH
  Profit comes from quality, low emotion, controlled frequency,
  strict fee awareness. Not from complexity.
  Less noise. More edge. Protect USDT.
```

## II. Why this is the cleanest spec yet

The operator removed exactly the parts I previously flagged as
infeasible / aspirational / overfit:

- **Ultra Micro Mode** — explicitly disabled (was rejected as physically
  impossible on Gate.io public WS in `L99_SPOT_HYBRID.md §III`)
- **Dynamic weighting** — disabled (would need 1000+ trades per
  `L99_SPOT_HYBRID.md §II yellow zone`)
- **Cross-exchange** — not in this spec at all (was a separate 3-week
  project)
- **Edge gate raised from 0.30% to 0.45%** — tighter than ADR-002's
  spot calibration; matches the audit's recommendation that
  "post-fee spot edge needs ≥ 2× round-trip cost"

What remains is essentially a **disciplined trend-follow with regime
gating + hard stop + session filter + drawdown circuit breaker** —
all components that can be honestly tested.

## III. The honest test

`edge_recovery_backtest.py` runs four variants with backtesting.py
70/30 OOS split, on the same 4 pairs (ETH, SOL, XRP, AVAX):

  V1. Baseline — MAWeekly only (the documented failure case)
  V2. + ATR-expansion regime filter
  V3. + delta acceleration filter
  V4. Full L99 Edge Recovery — V3 + 2-bar continuation + edge ≥ 0.45%
                              + hard −0.35% stop

If each successive filter genuinely adds OOS Sharpe, the spec is
correct. If they reduce trade count without lifting Sharpe, the
filters are over-fitting (the failure mode the spec itself warns about).

The honest expectation per `GODMODE_AUDIT.md §8`: even with the
tighter gates, OOS Sharpe likely sits in the +0.0 to +0.5 range. The
spec's Step 6 profitability check loop (WR ≥ 55%, avg R ≥ 1.5) is
**deliberately demanding** — that bar is the right one. Most retail
crypto trend-follow falls below it.

## IV. Promotion path

If V4 (Full L99 Edge Recovery) clears:

  - OOS Sharpe ≥ 0.5 on ≥3 of 4 pairs, AND
  - WR ≥ 55% AND avg_R ≥ 1.5 (Step 6 mild-compounding gate)

then this becomes the next Phase B candidate — replacing the Vote
ensemble in `run_vote_strategy`. Otherwise we revert to the ADR-001
fallback (B1 on-chain) on D7.

`l99_validate.py` Phase 3 will pick up these results automatically
once committed.
