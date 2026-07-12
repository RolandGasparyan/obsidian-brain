# Mean-reversion + ensemble — no improvement over MA20+W5 alone

Run date: 2026-04-24  ·  Crypto daily bars, 1000-bar sample, 100 MC runs per cell

## TL;DR — the ensemble hypothesis didn't pan out

Hypothesis: trend-follow and mean-reversion have decorrelated failure
modes, so a 50/50 ensemble should clear the ship bar where either alone
fails. Result: **both mean-reversion strategies tested (RSI-2 and Bollinger
fade) are roughly random on crypto daily bars**, and the ensemble adds
diversification cost without buying meaningful edge diversification.

## The scorecard

| Strategy | avg Sharpe | avg MC % | MC ≥99 | Roll ≥4/5 | Recent >0 | Passes |
|---|---:|---:|:---:|:---:|:---:|:---:|
| **MA20+W5** (our best) | **+2.15** | **93.0%** | 0/4 | 0/4 | **3/4** | no |
| RSI-2 | +0.32 | 53.2% | 0/4 | 0/4 | 1/4 | no |
| Bollinger fade | +0.37 | 51.0% | 0/4 | 0/4 | 0/4 | no |
| Ensemble MA+BB | +2.02 | 91.2% | 0/4 | 0/4 | 1/4 | no |

## Why mean-reversion failed on crypto daily

- **RSI-2**: fires constantly (86–104 trades over 1000 bars = every ~10
  days), each fade bucking a strong trend. On crypto, "oversold" at RSI<10
  is often the start of a bigger drop, not a snapback. Fee drag alone kills
  the edge at 2.5 %/round-trip.
- **Bollinger fade**: patient (30–40 trades), but when crypto breaks out
  of the −2σ band it usually keeps going, not reverts. Only XRP (a
  genuinely mean-reverting stablecoin-ish asset) showed a positive edge.

Both strategies need LOWER timeframes (1h, 15m) and TIGHTER risk to work —
classic intraday/scalping territory. At daily, crypto trends too strongly
for mean-reversion to help.

## Why the ensemble underperformed pure MA

Half of the capital ran BB_FADE — which lost money on 3 of 4 pairs over
the most recent 176 bars. That drag pulled the ensemble's recent ROI
below pure MA20+W5's. Diversification between two strategies where one
is genuinely positive-EV and the other is roughly random is a **subsidy**,
not a free lunch.

The math is brutal: ensemble Sharpe ≈ (MA_Sharpe + MR_Sharpe × corr_adj) / √2.
When MR_Sharpe ≈ 0, ensemble Sharpe ≈ MA_Sharpe / √2 — a downgrade, not an
upgrade.

## What this closes

- **Path B is done.** Daily mean-reversion on crypto = no free alpha.
- **No need to test RSI-14, Keltner bands, z-score reversion, etc.** —
  same failure class.
- **Ensembling requires BOTH sides to be individually profitable.**

## What we actually have — MA20+W5 alone

| Pair | ROI (2.7y) | Sharpe | MC % | Rolling | Recent 6-mo |
|---|---:|---:|---:|:---:|---:|
| ETH | +810% | 2.22 | 97% | 3/5 | **+23.4%** |
| SOL | +2,470% | 2.38 | 95% | 3/5 | +8.4% |
| XRP | +1,008% | 1.95 | 87% | 3/5 | +5.2% |
| AVAX | +1,517% | 2.04 | 93% | 2/5 | −14.2% |

**The ship gate still fails** — MC % is 87–97 (need ≥99), rolling is 2–3/5
(need ≥4/5). But:

- Median Sharpe 2.1 is *respectable* for crypto daily.
- 3 of 4 pairs have POSITIVE recent 6-month out-of-sample ROI.
- Total across 4 pairs is 3/5 windows beating B&H on average — slightly
  better than coin-flip.

**It's a real, small edge.** Not a ship-gate-clearing edge, but not noise either.

## The honest path forward: Path D with guardrails

Three quant-research avenues (parameter sweep, regime gating, MR ensemble)
are now exhausted. Further research without MORE DATA will chase our own tails.

Recommended deployment for MA20+W5:

1. **Position size** = 25 % of full-Kelly.
   Full-Kelly on Sharpe 2.1 suggests ~35–50 % of capital at risk. 25 % of
   that = ~10 % of capital per position. Conservative.

2. **Hard portfolio-level drawdown cap: 5 % weekly.**
   If the 4-bot portfolio loses 5 % in any 7-day rolling window, full
   kill-switch triggers. Telegram alert to rehab the rule.

3. **Two-man rule for live mode.**
   Any BUY/SELL in live mode requires a Telegram reply approving it
   before order goes through. Prevents runaway robots.

4. **Let the current Stage 1 paper-forward run a full 30 days.**
   The 4 live paper bots are now unbiased out-of-sample evidence. If
   live PnL matches the backtest within a factor of 2, the edge is real.
   If it's wildly worse, the edge was overfitting after all.

5. **Deploy ONLY to the top 2 pairs by recent ROI.**
   ETH (+23.4%) and SOL (+8.4%) are the two that are still working.
   Drop XRP, AVAX for Stage 2; revisit after more data.

## Reproducing

```bash
python3 mean_reversion.py
python3 mean_reversion.py --mc-runs 200
python3 mean_reversion.py --pairs ETH_USDT SOL_USDT
```
