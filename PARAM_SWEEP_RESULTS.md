# MA-family parameter sweep — no combo clears the ship gate

Run date: 2026-04-24  ·  Grid: 4 MA periods × 4 weekly periods × 1 hysteresis × 4 pairs = 64 runs × 100 MC shuffles each

## TL;DR — parameter tuning alone won't save MA

The MA trend-follow family has some signal (Sharpe 1.5–2.5 is non-trivial) but the
edge is **regime-dependent**, not **structural**. Every (MA, W) combo we tested
wins some windows and loses others. None crossed all three bars of the ship gate:

- MC percentile ≥ 99 % on ≥ 3 pairs  →  best combo hits **1 / 4**
- Rolling-window wins ≥ 4 / 5 on ≥ 3 pairs  →  best combo hits **0 / 4**
- Recent 6-month ROI > 0 on all 4 pairs  →  best combo hits **3 / 4**

The conclusion is structural: the MA family itself is the ceiling on this data,
not parameter choice. Moving forward requires **regime gating** or a
**decorrelated strategy class**, not more knob twiddling.

## Top 5 combos by cross-pair composite score

| Rank | MA period | Weekly filter | Hyst | Score | MC ≥99 | Roll ≥4/5 | Recent>0 |
|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 1 | 20 | 5 | 0.25% | **13.65** | 0/4 | 0/4 | 3/4 |
| 2 | 20 | 10 | 0.25% | 12.63 | 1/4 | 0/4 | 3/4 |
| 3 | 50 | 10 | 0.25% | 11.46 | 0/4 | 0/4 | 2/4 |
| 4 | 50 | 5 | 0.25% | 10.20 | 0/4 | 0/4 | 1/4 |
| 5 | 100 | 10 | 0.25% | 9.58 | 0/4 | 0/4 | 0/4 |

Our original production choice (MA50+W10) ranks **#3**, only marginally worse
than MA20+W5 (#1). So we were in the right neighborhood — just not good enough.

## Per-pair champion combo vs current live rule

For reference, if we were willing to tailor the rule to each pair:

| Pair | Best combo (this sweep) | Full ROI | Sharpe | MC % | Recent ROI |
|---|---|---:|---:|---:|---:|
| ETH | MA50+W5 | +851% | 2.30 | 98% | +16.2% |
| SOL | MA50+W5 | +3,181% | 2.51 | 96% | −5.3% |
| XRP | MA20+W5 | +1,005% | 1.94 | 87% | +4.9% |
| AVAX | MA100+W5 | +1,795% | 2.26 | 97% | 0% |

⚠️ **DO NOT use pair-tailored combos in production.** Picking the best
combo per pair IS overfitting — it uses the in-sample future to pick the
rule. The only legitimate cross-pair combo is the one that performs
well on the majority of pairs without being tuned to any single one.

## Concrete lessons from the sweep

### 1. Shorter MA + faster weekly filter beats the defaults
MA20+W5 beats MA50+W10 on composite score. Shorter daily MA catches
reversals earlier at the cost of more trades (47 vs 31 over 1000 bars).
The extra fee drag is outweighed by the extra signal.

### 2. The weekly filter is nearly free value
Every MA period performs dramatically better WITH a weekly filter than
without (e.g. MA50+W0: +152% ROI, Sharpe 0.97 vs MA50+W5: +851% ROI,
Sharpe 2.30 on ETH). The filter suppresses most false signals during
downtrends — this part of the thesis holds up.

### 3. Rolling-window wins are the hardest test
Across all 64 combos and pairs, zero cell hits `wins ≥ 4/5`. The
strategy's edge is NOT stable across five different 5-month chunks of
history. It wins big in some regimes (2021 bull, early-2024 alt cycle)
and loses in others (2022 bear, 2025 chop).

### 4. Hysteresis at 0.25% is fine — not the bottleneck
We held hysteresis fixed at 0.25% (fee-equivalent) in this sweep. The
whipsaw problem was solved; further tuning doesn't move the needle.

## Recommended next steps

In descending order of expected payoff:

### A. Regime gate (fastest, highest ROI per day of work)
Only enable the MA strategy when macro conditions favor trend-following.
Candidates for the gate:

- **Cross-asset volatility** — turn on when BTC 30d-vol > 4%, off otherwise.
- **Trend strength** — turn on when the 200d MA slope is positive, off otherwise.
- **Breadth** — turn on when > 60% of top-20 crypto market caps are above
  their 50d MA.

A rule that trades only 30–50 % of the time but clears the ship gate in
those periods is more valuable than one that trades 100 % of the time
and has regime-averaged noise.

### B. Mean-reversion pair strategy (decorrelated)
Build a Bollinger-fade or RSI-2 strategy with the same walk-forward
harness. Trend and mean-reversion are mechanically decorrelated — one
works in smooth trends, the other in choppy markets. Ensemble of the
two may clear the ship gate where either alone fails.

### C. Breakout (Donchian-N) as alternative trend form
Donchian channel breakouts are the classic alt to MA-based trend. Less
noise-prone around the MA crossover. Walk-forward it on the same bars
and compare to MA family.

### D. Accept marginal edge + hard risk cap
If everything else fails, the MA20+W5 combo is PROBABLY positive EV
in bull regimes. Deploy it with:

- Position size 25% of full Kelly (very small)
- Hard 5% weekly DD kill switch
- Telegram approval required for every entry

Effective expected return: low. But the infrastructure is already built.

## Reproducing

```bash
# Full sweep (4 pairs × 16 combos × 100 MC, ~1 minute)
python3 param_sweep.py

# Broader grid on one pair
python3 param_sweep.py --pairs ETH_USDT --mc-runs 200

# Add new pairs
python3 param_sweep.py --pairs NEAR_USDT ARB_USDT --mc-runs 100
```
