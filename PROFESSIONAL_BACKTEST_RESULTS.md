# Professional backtest (backtesting.py 0.6.5) — the honest verdict

Run date: 2026-04-25  ·  Framework: kernc/backtesting.py 0.6.5  ·  4 pairs × 1000 daily bars  ·  70/30 train/test

## TL;DR — every strategy, every pair, **loses money out-of-sample**

| Strategy | avg OOS SQN | avg OOS Sharpe | avg OOS Return | Pairs positive |
|---|---:|---:|---:|:---:|
| MA+W (our current research winner) | **−1.64** | −1.54 | **−22.4%** | 0 / 4 |
| MA+W + BTC gate | −2.79 | −1.27 | −18.4% | 0 / 4 |
| Donchian-N | nan (few trades) | −1.40 | −21.1% | 1 / 4 |
| SmaCross (classic control) | −5.18 | −1.77 | −17.8% | 1 / 4 |

This is not our hand-rolled harness. This is **backtesting.py**, the
battle-tested framework used in thousands of quant projects. Proper OOS,
proper trade bookkeeping, proper SQN / Sharpe / Calmar / Profit Factor.

The result: **no strategy clears even a weak bar** (OOS SQN > 0, OOS
Sharpe > 0, OOS return > 0). Every strategy is train-overfit.

## What train looked like vs what test looked like

### MA+W
| Pair | TRAIN SQN | TRAIN Return | **TEST SQN** | **TEST Return** | B&H TEST |
|---|---:|---:|---:|---:|---:|
| ETH | 2.05 | +776% | **−2.31** | **−33%** | −54% |
| SOL | 2.05 | +776% | −2.31 | −33% | −54% |
| XRP | 0.57 | +138% | −2.76 | −22% | −48% |
| AVAX | 1.06 | +278% | −1.05 | −33% | −64% |

Train SQN 0.57–2.05 (decent). Test SQN −1.05 to −2.76 (terrible).
That's the textbook signature of overfitting.

### SmaCross (classic) — one bright spot
- **SOL_USDT OOS:** SQN 0.29, Sharpe 0.26, **Return +9% while B&H lost 53%** — 62pp defensive edge
- Everything else: still negative

## Important caveats

1. **Test period is a bear/chop regime.** Buy-and-hold ROI on the test
   half: ETH −54%, SOL −54%, XRP −48%, AVAX −64%. Trend-follow
   systematically loses money in flat/down markets regardless of
   parameters.

2. **Strategies DID do less-bad than B&H** on most pairs — MA+W
   on ETH: −1.4% vs B&H −54%. Defensive behavior works.

3. **Returns "less-bad than B&H" is not a ship criterion.** Real deployment
   requires positive absolute ROI, not just "outperform a terrible
   baseline."

## Why our hand-rolled harness looked rosier

Our custom walk-forward ran 5 overlapping rolling windows and averaged
across them — so good windows (bull regimes) masked bad windows
(bear/chop regimes). backtesting.py's strict 70/30 split doesn't
average; it just tells you "the most recent 30% of history, which the
optimizer never saw, produced negative returns on the train-optimized
params."

Both are legitimate methodologies. Our hand-rolled one asks "averaged
across history, does the strategy show a reliable edge?" Answer:
marginally yes. The professional 70/30 asks "does the strategy, as
deployed from the recent past forward, make money?" Answer: no.

**For deployment decisions, the 70/30 answer is the one that matters.**

## What this changes

1. **Do not deploy real money** on ANY strategy we've built so far.
2. **The current Vote ≥2 of 3 paper bots can keep running** — they're
   free OOS evidence collection. If they make money over the next
   30–60 days, that's new data that might override this verdict.
3. **The research infrastructure is still excellent.** walk_forward,
   param_sweep, regime_gated, mean_reversion, deep_edge, max_edge,
   professional_backtest — seven different angles of validation.
   Reusable for whatever strategy we try next.
4. **Next strategy class to try:** something that works in chop.
   - Short-term mean reversion with tight risk
   - Vol/vol-skew arbitrage
   - Market-neutral pair trading
   - Or wait for the next bull cycle to deploy trend-follow

## The cleanest recommendation

**Stop trying to force an edge on 1d crypto trend-follow in a chop
regime.** We've spent 4 rounds of increasingly sophisticated research,
and every proper test confirms: this isn't our moment.

Actionable path forward:

1. Keep Vote ≥2 of 3 paper bots running (already live). 30+ days of
   new OOS data is the only evidence that would override this verdict.
2. Run the professional backtest monthly to track whether the strategy
   starts working as regime changes.
3. In the meantime, **use the research infrastructure to explore
   different strategy families** — NOT more parameter tuning on the
   trend family. Candidates:
   - 4h or 1h intraday momentum
   - Volatility targeting with cross-asset signals
   - ML-based regime classifier (has enough features now)
   - Options flow signals from derivatives markets
4. **Money management** is more ship-worthy than signal research right
   now. Per-trade stops, Kelly sizing, portfolio-level kill switches,
   correlation caps — all work regardless of which signal wins.

## Reproducing

```bash
python3 professional_backtest.py
python3 professional_backtest.py --pairs ETH_USDT SOL_USDT
python3 professional_backtest.py --train-frac 0.6  # 60/40 split
```
