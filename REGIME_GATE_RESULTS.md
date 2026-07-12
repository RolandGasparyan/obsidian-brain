# Regime gating makes MA worse, not better

Run date: 2026-04-24 · MA20+W5 base strategy · 6 gates × 4 pairs × 100 MC runs

## TL;DR — unexpected finding

Hypothesis: MA20+W5 fails the ship gate because it trades in unfavorable
regimes. Filtering by macro conditions (trend slope, price vs 200MA, vol
threshold) should make the gated version clear the bar.

Result: **every regime gate tested REDUCED Sharpe, MC%, and ROI** compared
to the ungated baseline. The MA edge is derived from trading *every*
regime indiscriminately — selectively skipping regimes removes more
winners than losers.

| Gate | Description | avg Sharpe | avg MC % | MC ≥99 | Rolling 4/5 | Recent >0 |
|---|---|---:|---:|---:|---:|---:|
| **none** (baseline) | MA20+W5, always active | **+2.15** | **93.0%** | 0/4 | 0/4 | **3/4** |
| slope | 200d SMA slope > 0 | +1.09 | 62.2% | 0/4 | 0/4 | 0/4 |
| above | price > 200d MA | +1.30 | 68.2% | 0/4 | 0/4 | 0/4 |
| hivol | 30d vol > 100% annualized | +0.57 | 53.8% | 0/4 | 0/4 | 1/4 |
| combo | slope+vol together | +0.41 | 45.5% | 0/4 | 0/4 | 0/4 |
| strict | slope + above + vol | +0.34 | 41.8% | 0/4 | 0/4 | 0/4 |

## Why this is important

1. **We now know what we DON'T need to build.** A macro regime classifier
   wouldn't save MA. No need to invest a week in training one.
2. **The MA edge is noisy, not regime-specific.** You can't cleanly separate
   "good MA regimes" from "bad MA regimes" using these simple features. The
   signal IS the noise.
3. **Path forward is clear:** pivot to a decorrelated strategy class (mean-
   reversion, breakout) and ensemble, or accept MA20+W5 baseline with
   risk controls.

## Baseline MA20+W5 (ungated) — what we actually have

| Pair | ROI | Sharpe | MC % | Rolling | Recent 6-mo |
|---|---:|---:|---:|:---:|---:|
| ETH_USDT | +810% | 2.22 | 97% | 3/5 | **+23.4%** |
| SOL_USDT | +2,470% | 2.38 | 95% | 3/5 | +8.4% |
| XRP_USDT | +1,008% | 1.95 | 87% | 3/5 | +5.2% |
| AVAX_USDT | +1,517% | 2.04 | 93% | 2/5 | −14.2% |

Ship-gate scorecard:
- MC ≥ 99 % on ≥3 pairs: **0/4** (3 pairs at 93–97 %, close but not there)
- Rolling ≥ 4/5 on ≥3 pairs: **0/4** (all at 2–3/5)
- Recent 6-mo ROI > 0 on all 4: **3/4** (AVAX −14.2 % drags)

**Still fails the formal ship gate**, but it's the closest we've gotten.
Median Sharpe is a respectable 2.1 and 3 of 4 pairs have positive recent
returns.

## Decision tree

### Option 1: Accept MA20+W5 baseline with tight risk controls
- Deploy the 4 live bots with strategy=`ma20w5`
- Position size 25 % of full Kelly (small)
- 5 % portfolio-level weekly DD → full kill
- Telegram approval required per-entry (two-man rule) for Stage 2

Expected return: **modest** (say 10–30 % / year net after real-world frictions,
with substantial variance). Not the +3,427 % headline. But positive-EV with
hard downside caps.

### Option 2: Pivot to mean-reversion + ensemble
Build `mean_reversion.py` (Bollinger fade or RSI-2), walk-forward validate
with the same harness. If it clears the ship gate on its own OR in
ensemble with MA20+W5 (each contributes decorrelated returns), deploy
the ensemble.

Expected time: 1 day. Expected outcome: unknown, but mean-reversion is
mechanically decorrelated from trend-follow, so the ensemble math favors it.

### Option 3: Breakout (Donchian-N)
Alt trend-following form. May or may not fare better than MA. Worth
2–3 hours as sanity check but lower priority than mean-reversion.

## Recommendation

Do **option 2** — build mean-reversion and ensemble. It's the single best
use of the next day of work because:

- Trend + mean-reversion ensembles have decades of academic + practical
  support. The failure modes are uncorrelated.
- If MR alone clears the ship gate, we ship it.
- If MR fails but ensembles with MA clear the gate, we ship the ensemble.
- If both fail, MA20+W5 with tight risk is still the fallback — we've
  lost nothing.

## Reproducing

```bash
# Full 6-gate × 4-pair sweep
python3 regime_gated_ma.py --mc-runs 100

# Different MA/weekly combo
python3 regime_gated_ma.py --ma 50 --weekly 10

# Only ETH, more Monte Carlo runs
python3 regime_gated_ma.py --pairs ETH_USDT --mc-runs 500
```
