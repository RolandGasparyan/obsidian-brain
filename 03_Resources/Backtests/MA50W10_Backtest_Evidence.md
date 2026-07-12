---
tags: [backtest, MA50W10, evidence]
date: 2026-04-25
---

# 📊 MA50W10 Backtest Evidence

Real Bitstamp 1-minute BTC/USD data, aggregated to 1-day candles, 0.25% round-trip fees, $1,000 starting balance.

## 📈 Performance by Period

| Period | Regime | BTC Move | B&H | MA50 | **MA50+W10** |
|---|---|---:|---:|---:|---:|
| 2018 full year | Catastrophic bear | -78% | -71.6% | -45.6% | **+2.4%** |
| 2019 full year | Range + recovery | +95% | +94.6% | +111.7% | **+170.3%** |
| 2020-04 → 2021-04 | COVID mega-bull | +800% | +816.2% | +428.6% | +419.1% |
| 2022 full year | Major bear | -66% | -65.3% | -41.2% | **-15.0%** |
| 2023-10 → 2024-06 | Bull | +125% | +124.2% | +63.2% | **+81.1%** |
| 2025-01 → 2026-04 | Moderate bear | -24% | -19.5% | +11.7% | **+59.5%** |

## 🏆 Compound Performance (~7.5 years, $1,000 start)

| Strategy | Final $ | Compound ROI |
|---|---:|---:|
| Buy & Hold | $3,172 | +217% |
| MA50 Direct | $6,519 | +552% |
| MA50+W20 | $10,619 | +962% |
| **MA50+W10** | **$35,272** | **+3,427%** |
| 9-Agent Engine (24-month only) | ~$995 | -0.53% |

## 🧠 Why the Simple Rule Beats the Complex Engine

| Failure Mode in 9-Agent Engine | How MA50 Sidesteps It |
|---|---|
| 0.25% fees × hundreds of trades = bleed | ~10 trades/yr keeps fee drag negligible |
| Tight ATR stops swept by normal noise | MA itself is a slow, noise-resistant stop |
| Premature TP exits cap winners | No fixed TP — rides until MA flips |
| Late momentum-confirmed entries | Symmetric MA cross — no consensus delay |
| EMERGENCY_STOP at -1.5% kills good trades | No intrabar stop — daily close only |

## 🔗 Related Notes
- [[MA50W10_Strategy]]
- [[GODSMODE_Research_Results]]
