---
tags: [strategy, research, rejected]
status: rejected-at-d7
---

# 📈 RSI-2 Mean Reversion (Champion Cell)

**Identified:** 2026-04-25 by `champion_select.py`
**Status:** REJECTED at D7 validation gate (2026-04-25)

## 📝 Description
A Connors-style RSI-2 mean reversion strategy. The first cell across nine research scripts to clear every audit ship-gate with a statistically meaningful sample size.

## 🛠️ Parameters
- **Entry:** RSI(2) < 10
- **Exit:** RSI(2) > 70
- **Pair:** XRP_USDT
- **Timeframe:** 4h
- **Commission Modeled:** 0.25% RT (conservative)

## 📊 OOS Backtest Results

| Metric | Value | Threshold | Pass |
|---|---:|---:|:---:|
| Sharpe Ratio | +1.80 | ≥ 0.50 | ✅ |
| Return | +7.8% | > 0 | ✅ |
| vs Buy-and-Hold | +7.8% vs +5.8% B&H | beats B&H | ✅ |
| Win Rate | 72% | ≥ 55% | ✅ |
| Trades | 18 | ≥ 5 | ✅ |
| Max Drawdown | -6.6% | < 15% | ✅ |
| Profit Factor | 2.10 | > 1.5 | ✅ |
| SQN | +1.10 | > 1.0 | ✅ |

## ❌ Why It Was Rejected
The +1.80 OOS Sharpe was a single-window artifact. Rolling walk-forward showed only 1/5 windows beat B&H, and Monte Carlo permutation classified the edge as **LIKELY NOISE** (real Sharpe beats only 37% of shuffled-return runs).

## 🔗 Related Notes
- [[MA50W10 Strategy]]
- [[GODSMODE Research Results]]
