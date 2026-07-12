---
tags: [strategy, validated, live]
status: active
---

# 📈 MA50W10 Strategy (The ONE Validated Edge)

This is the only strategy authorized for live trading in the TradingGuru Empire as of May 2026.

## 📝 Description
A moving-average trend-follow strategy with a weekly filter that crushed the 9-agent indicator engine on 8+ years of real BTC/USD data.

> Hold 100% BTC when daily close > 50-day SMA AND weekly close > weekly SMA10, else 100% USDT.

## 🛠️ Parameters
- **Daily SMA:** 50 period
- **Weekly SMA:** 10 period
- **Entry:** `price > SMA50(daily) AND price > SMA10(weekly)`
- **Exit:** `price ≤ SMA50(daily) OR price ≤ SMA10(weekly) OR held ≥ 46h`

## 📊 Backtest Results (7.5 years chained)
- **Compound ROI:** +3,427%
- **Sharpe Ratio:** 2.81
- **Max Drawdown:** -23%

## 🧠 Notes & Observations
The weekly filter's edge is asymmetric: it gives back only 1-3 pp in mega-bull years but rescues catastrophic-bear years (e.g., 2018: -45.6% → +2.4%). On a compound basis, the bear protection dominates by 5x.

## 🔗 Related Notes
- [[3-Layer Architecture]]
- [[Gods Level Engine]]
