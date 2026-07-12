---
tags: [backtest, research, results]
date: 2026-04-25
---

# 🛑 GODSMODE Research Results

**Run Date:** 2026-04-25
**Framework:** kernc/backtesting.py 0.6.5
**Scope:** 80 OOS backtests — 10 strategies × 2 timeframes × 4 pairs

## TL;DR
80 grid-optimized backtests across 10 strategy families, 2 timeframes, 4 pairs. Every (strategy, timeframe) combination fails the ship gate on majority of pairs. The best result across all 80 is **one pair × one strategy** clearing the triple bar.

## Scorecard — 1-Day Timeframe

| Strategy | Mean OOS SQN | Mean Sharpe | Mean Ret% | Pairs+ | Ships |
|---|---:|---:|---:|:---:|:---:|
| MAWeekly | -2.19 | -2.19 | -18.5% | 0/4 | 0/4 |
| SmaCross | -2.04 | -2.81 | -23.2% | 0/4 | 0/4 |
| **RSI2Reversion** | nan | -0.87 | -13.7% | 1/4 | **1/4** |

## Scorecard — 4-Hour Timeframe

| Strategy | Mean OOS SQN | Mean Sharpe | Mean Ret% | Pairs+ | Ships |
|---|---:|---:|---:|:---:|:---:|
| **SmaCross** | nan | -2.97 | -1.9% | 2/4 | **1/4** |
| **RSI2Reversion** | nan | nan | -0.9% | 2/4 | **1/4** |

## Key Finding
The 9-agent indicator-consensus engine returned **-0.5% over 24 months** of real BTC/USD walk-forward. A trivial MA rule on the same data returned **+74.9%** over the same period.

## 🔗 Related Notes
- [[MA50W10 Strategy]]
- [[RSI2 Champion Cell]]
