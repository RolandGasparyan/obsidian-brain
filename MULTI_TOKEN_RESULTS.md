# Multi-token MA50+W10 backtest results

Run date: 2026-04-24  
Source: Gate.io public candlesticks API  
Starting balance: $1,000 · Fees: 0.25% round-trip

## Summary

**MA50+W10 beat buy-and-hold on 26 / 26 tokens tested** across three batches.

| Batch | Tokens | Timeframe | Bars | Span | MA50+W10 avg ROI | B&H avg ROI | Edge |
|---|---|---|---|---|---:|---:|---:|
| Majors daily | 10 | 1d | 1000 | 2.7 years | **+581.36%** | +63.97% | +517.39% |
| Majors 4h   | 10 | 4h | 1000 | 5.5 months (bear) | **+9.88%** | −40.98% | +50.86% |
| Memecoins daily | 6 | 1d | ≤1000 | up to 2.7 years | **+4,507.82%** | +313.34% | +4,194.48% |

## Batch 1 — Major alts, daily (2.7y)

| # | Token | MA50+W10 | B&H | Δ |
|---|---|---:|---:|---:|
| 1 | SOL | +1,401.19% | +255.73% | +1,145.46% |
| 2 | AVAX | +817.82% | −28.31% | +846.14% |
| 3 | DOGE | +638.52% | +25.70% | +612.82% |
| 4 | ETH | +543.29% | +24.73% | +518.56% |
| 5 | XRP | +540.94% | +104.13% | +436.81% |
| 6 | LINK | +518.06% | +23.88% | +494.18% |
| 7 | ADA | +408.52% | −20.54% | +429.06% |
| 8 | BTC | +406.58% | +166.92% | +239.66% |
| 9 | DOT | +268.07% | −75.80% | +343.86% |
| 10 | BNB | +270.63% | +163.27% | +107.36% |
| | **AVG** | **+581.36%** | +63.97% | +517.39% |

## Batch 2 — Major alts, 4h (5.5mo bear)

| # | Token | MA50+W10 | B&H | Δ |
|---|---|---:|---:|---:|
| 1 | ETH | +25.84% | −31.22% | +57.07% |
| 2 | XRP | +15.55% | −36.18% | +51.73% |
| 3 | ADA | +12.73% | −54.39% | +67.12% |
| 4 | BTC | +11.49% | −23.14% | +34.63% |
| 5 | AVAX | +11.46% | −44.27% | +55.73% |
| 6 | BNB | +9.49% | −34.94% | +44.43% |
| 7 | DOT | +8.10% | −59.95% | +68.04% |
| 8 | SOL | +6.73% | −44.68% | +51.42% |
| 9 | DOGE | +3.11% | −42.99% | +46.10% |
| 10 | LINK | −5.73% | −38.03% | +32.29% |
| | **AVG** | **+9.88%** | −40.98% | +50.86% |

Interpretation: in a bear tape where every major lost 20–60%, MA50+W10
preserved capital on 9/10 and came out slightly positive on average.
This is the filter's defensive value — not about outsized gains, but
about not blowing up during drawdowns.

## Batch 3 — Memecoins, daily

| # | Token | MA50+W10 | B&H | Δ |
|---|---|---:|---:|---:|
| 1 | BONK | +19,623.69% | +1,770.82% | +17,852.86% |
| 2 | FLOKI | +3,200.02% | +50.34% | +3,149.68% |
| 3 | PEPE | +2,723.92% | +198.07% | +2,525.85% |
| 4 | WIF | +991.43% | −24.05% | +1,015.48% |
| 5 | SHIB | +532.70% | −25.26% | +557.96% |
| 6 | TRUMP | −24.82% | −89.88% | +65.06% |
| | **AVG** | **+4,507.82%** | +313.34% | +4,194.48% |

Note: TRUMP is a 5-month-old token with only 4 trades executed; the
strategy stayed in cash ~75% of the time, losing 25% while B&H lost 90%.

## Caveats

1. **Survivorship bias** — every token here existed 1000 days ago and is
   still on Gate.io today. Failed tokens are not in the sample.
2. **Slippage / liquidity** — real fills on memecoins (especially BONK
   in its early days) would be worse than the model assumes. Treat
   memecoin numbers as upper bounds, not expectations.
3. **Single regime per pair** — 1000 bars is one ~2.7y sample; future
   regimes may behave differently.
4. **Fees modeled at 0.25% RT** — Gate.io maker+taker combined; if the
   live bot takes market orders both ways the effective fee is higher.

## Reproduce

```bash
python3 backtest_multi_token.py
python3 backtest_multi_token.py --interval 4h --limit 1000
python3 backtest_multi_token.py --pairs PEPE_USDT WIF_USDT BONK_USDT FLOKI_USDT SHIB_USDT TRUMP_USDT
```
