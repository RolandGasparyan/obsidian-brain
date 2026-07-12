# Crypto Trading Strategies — Complete Library for Testing Engine

**Source:** 340,000+ real paper trades from the Trading Guru engine (v9.1/v10.0) + external research  
**Last Updated:** 2026-06-01  
**Purpose:** Full reference for analyzing, comparing, and selecting strategies for the testing engine

---

## Master Performance Table (All Strategies — Real Backtested Data)

The table below is sorted by **Profit Factor (PF)** — the single most important metric for strategy quality. A PF > 1.0 means the strategy is profitable. All data comes from the live trading engine's SQLite database.

| Rank | Strategy | Trades | Win Rate | Profit Factor | Avg Win | Avg Loss | Total PnL |
|------|----------|--------|----------|---------------|---------|----------|-----------|
| 🥇 1 | **Chande Momentum Oscillator** | 26,043 | 44.8% | **1.278** | $1.39 | -$0.88 | +$3,529 |
| 🥈 2 | **ICT Fair Value Gap (FVG)** | 15,551 | 47.7% | **1.121** | $1.67 | -$1.36 | +$1,344 |
| 🥉 3 | **Squeeze Momentum (LazyBear)** | 17,947 | 47.6% | **1.082** | $1.66 | -$1.39 | +$1,079 |
| 4 | Williams %R Reversal | 10,871 | 46.6% | 1.069 | $1.52 | -$1.24 | +$499 |
| 5 | Order Flow Imbalance | 25,605 | 48.1% | 1.056 | $1.61 | -$1.42 | +$1,055 |
| 6 | EMA 9/21 Crossover | 4,136 | 45.0% | 1.054 | $1.09 | -$0.84 | +$103 |
| 7 | **Keltner Channel + RSI** | 15,461 | 47.6% | **1.046** | $2.57 | -$2.22 | +$837 |
| 8 | CVD Absorption Reversal | 6,237 | 44.9% | 1.042 | $1.48 | -$1.16 | +$168 |
| 9 | Range Trading S/R | 16,946 | 47.3% | 1.030 | $1.42 | -$1.23 | +$332 |
| 10 | Triple EMA (5/13/34) | 26,521 | 42.8% | 1.025 | $1.21 | -$0.89 | +$337 |
| 11 | Ichimoku Cloud Breakout | 4,407 | 45.7% | 1.021 | $1.71 | -$1.41 | +$71 |
| 12 | HFT Statistical Arbitrage | 29,374 | 45.3% | 1.021 | $1.15 | -$0.93 | +$312 |
| 13 | Donchian Channel Breakout | 15,395 | 44.1% | 1.018 | $3.06 | -$2.37 | +$359 |
| 14 | ICT Order Block + Liq Sweep | 8,925 | 44.9% | 1.017 | $1.64 | -$1.31 | +$112 |
| 15 | Pullback Momentum (50-EMA) | 7,703 | 47.1% | 1.012 | $1.95 | -$1.71 | +$82 |
| 16 | Price Action Candlestick | 5,805 | 48.5% | 1.012 | $1.53 | -$1.42 | +$51 |
| 17 | Bollinger Band Squeeze | 13,818 | 44.0% | 1.010 | $1.41 | -$1.09 | +$85 |
| 18 | Parabolic SAR Flip | 25,732 | 43.9% | 1.008 | $1.08 | -$0.84 | +$98 |
| ❌ | ALMA + Stochastic Reversal | 11,368 | 47.6% | 0.984 | $1.81 | -$1.67 | -$162 |
| ❌ | Heikin Ashi Trend Filter | 11,602 | 37.7% | 0.974 | $1.38 | -$0.86 | -$161 |
| ❌ | Laguerre RSI Pullback | 9,830 | 44.3% | 0.949 | $1.29 | -$1.08 | -$302 |
| ❌ | Elder Triple Screen System | 5,982 | 34.2% | 0.927 | $1.70 | -$0.95 | -$273 |
| ❌ | RSI Divergence | 12,350 | 46.5% | 0.919 | $1.37 | -$1.29 | -$695 |
| ❌ | Fibonacci Retracement | 9,861 | 47.0% | 0.912 | $1.40 | -$1.36 | -$628 |
| ❌ | Waddah Attar Explosion | 483 | 48.2% | 0.848 | $2.23 | -$2.45 | -$93 |
| ❌ | Pivot Point Breakdown | 1,466 | 44.1% | 0.826 | $0.83 | -$0.79 | -$113 |
| ❌ | VWAP + MACD Momentum | 1,205 | 43.2% | 0.771 | $0.96 | -$0.94 | -$148 |
| ❌ | SuperTrend + MACD | 678 | 45.1% | 0.707 | $0.95 | -$1.10 | -$120 |

> **Key insight:** The top 8 strategies (PF ≥ 1.042) are profitable. The bottom 10 (PF < 1.0) are net losers and should be disabled or replaced.

---

## Best Strategy × Asset Combinations (Top 20 by Profit Factor)

Some strategies perform dramatically better on specific assets. These are the highest-PF combinations from the database.

| Rank | Strategy | Asset | Trades | Win Rate | Profit Factor | Total PnL |
|------|----------|-------|--------|----------|---------------|-----------|
| 🔥 1 | Chande Momentum Oscillator | **FLOKI/USDT** | 388 | 24.5% | **15.485** | +$368 |
| 🔥 2 | Chande Momentum Oscillator | **BOME/USDT** | 377 | 24.7% | **9.249** | +$435 |
| 🔥 3 | Chande Momentum Oscillator | **BONK/USDT** | 201 | 54.7% | **4.893** | +$89 |
| 4 | Williams %R Reversal | FLOKI/USDT | 48 | 39.6% | **4.612** | +$20 |
| 5 | ICT Fair Value Gap (FVG) | BOME/USDT | 84 | 34.5% | **4.279** | +$122 |
| 6 | Parabolic SAR Flip | WIF/USDT | 41 | 36.6% | **4.160** | +$31 |
| 7 | Chande Momentum Oscillator | DOGE/USDT | 273 | 49.8% | **3.900** | +$189 |
| 8 | RSI Divergence | BOME/USDT | 36 | 41.7% | **3.435** | +$15 |
| 9 | Parabolic SAR Flip | FLOKI/USDT | 105 | 34.3% | **3.053** | +$59 |
| 10 | Chande Momentum Oscillator | WIF/USDT | 444 | 40.8% | **2.803** | +$156 |
| 11 | ICT Fair Value Gap (FVG) | OP/USDT | 137 | 54.7% | **2.780** | +$78 |
| 12 | ICT Order Block + Liq Sweep | PEPE/USDT | 40 | 50.0% | **2.705** | +$16 |
| 13 | Chande Momentum Oscillator | OP/USDT | 580 | 44.1% | **2.486** | +$286 |
| 14 | Fibonacci Retracement | UNI/USDT | 48 | 52.1% | **2.477** | +$34 |
| 15 | Keltner Channel + RSI | OP/USDT | 51 | 54.9% | **2.390** | +$139 |
| 16 | Bollinger Band Squeeze | DOGE/USDT | 341 | 48.1% | **2.371** | +$128 |
| 17 | Parabolic SAR Flip | BOME/USDT | 61 | 21.3% | **2.342** | +$17 |
| 18 | Fibonacci Retracement | ATOM/USDT | 95 | 48.4% | **2.327** | +$57 |
| 19 | Price Action Candlestick | BONK/USDT | 64 | 50.0% | **2.251** | +$21 |
| 20 | ICT Fair Value Gap (FVG) | ADA/USDT | 331 | 47.7% | **2.234** | +$146 |

---

## Best Assets by Profit Factor (All Strategies Combined)

| Rank | Asset | Trades | Win Rate | Profit Factor | Total PnL |
|------|-------|--------|----------|---------------|-----------|
| 🥇 1 | **BOME/USDT** | 3,582 | 23.0% | **1.507** | +$701 |
| 🥈 2 | **DOT/USDT** | 11,415 | 35.6% | **1.229** | +$1,699 |
| 🥉 3 | **SHIB/USDT** | 3,976 | 43.1% | **1.191** | +$267 |
| 4 | WIF/USDT | 2,828 | 33.5% | 1.179 | +$230 |
| 5 | ATOM/USDT | 10,566 | 34.4% | 1.172 | +$1,343 |
| 6 | ADA/USDT | 8,149 | 39.7% | 1.154 | +$644 |
| 7 | UNI/USDT | 6,555 | 43.1% | 1.147 | +$540 |
| 8 | FLOKI/USDT | 3,867 | 22.2% | 1.140 | +$170 |
| 9 | LTC/USDT | 6,024 | 42.5% | 1.133 | +$363 |
| 10 | OP/USDT | 3,363 | 35.8% | 1.128 | +$274 |

---

## Strategy Deep Dives — Top 10 Profitable Strategies

### 1. Chande Momentum Oscillator (CMO)
**Category:** Momentum  
**Overall PF:** 1.278 | **Win Rate:** 44.8% | **Total PnL:** +$3,529 (26,043 trades)

The CMO is the single best-performing strategy across the entire engine. It measures the difference between the sum of recent gains and losses, normalized to a -100 to +100 scale. Unlike RSI, it uses both up and down days in the denominator, making it more sensitive to momentum shifts.

**Entry Signal (Short):** CMO(14) > 50 (overbought momentum) AND price is below 20-period EMA.  
**Confirmation:** RSI > 60, Volume > 120% of 10-period SMA average.  
**Stop Loss:** 1.5× ATR above entry.  
**Take Profit:** 2.5× Stop Loss distance (2.5:1 R:R).  
**Best Pairs:** FLOKI (PF 15.5), BOME (PF 9.2), BONK (PF 4.9), DOGE (PF 3.9), WIF (PF 2.8), OP (PF 2.5).  
**Avoid:** XRP, ETH, BTC (low PF on large-cap assets).

---

### 2. ICT Fair Value Gap (FVG)
**Category:** Smart Money Concepts  
**Overall PF:** 1.121 | **Win Rate:** 47.7% | **Total PnL:** +$1,344 (15,551 trades)

A 3-candle pattern where a rapid price move creates an imbalance (gap) between the first candle's high and the third candle's low (bearish FVG). Price tends to retrace into this gap before resuming the trend.

**Entry Signal (Short):** Bearish FVG forms (candle[i-2].high > candle[i].low with a gap ≥ 0.1%). Price retraces up into the FVG zone and shows rejection.  
**Confirmation:** RSI > 55, price above 20-period EMA.  
**Stop Loss:** Above the top of the FVG zone + 0.5× ATR.  
**Take Profit:** 2.5× Stop Loss distance.  
**Best Pairs:** BOME (PF 4.3), OP (PF 2.8), ADA (PF 2.2).

---

### 3. Squeeze Momentum (LazyBear)
**Category:** Volatility / Breakout  
**Overall PF:** 1.082 | **Win Rate:** 47.6% | **Total PnL:** +$1,079 (17,947 trades)

Identifies periods of low volatility ("squeeze") when Bollinger Bands contract inside Keltner Channels. When the squeeze releases, it signals a high-probability breakout. The momentum histogram direction determines trade direction.

**Entry Signal (Short):** Bollinger Bands (20, 2.0) are inside Keltner Channels (20, 1.5) — squeeze active. When bands expand (squeeze fires), momentum histogram is negative → SHORT.  
**Confirmation:** RSI > 55, Volume > 130% of 10-period SMA.  
**Stop Loss:** 1.5× ATR above entry.  
**Take Profit:** 2.5× Stop Loss distance.  
**Best Pairs:** All top 8 assets (broad applicability).

---

### 4. Williams %R Reversal
**Category:** Mean Reversion  
**Overall PF:** 1.069 | **Win Rate:** 46.6% | **Total PnL:** +$499 (10,871 trades)

Williams %R measures the current closing price relative to the highest high over a lookback period. Values above -20 indicate overbought conditions.

**Entry Signal (Short):** Williams %R(14) rises above -20 (overbought) and then crosses back below -20.  
**Confirmation:** RSI > 60, price at or above 20-period EMA.  
**Stop Loss:** 1.5× ATR above entry.  
**Take Profit:** 2.5× Stop Loss distance.  
**Best Pairs:** FLOKI (PF 4.6), top 6 assets.

---

### 5. Order Flow Imbalance
**Category:** Microstructure / Volume  
**Overall PF:** 1.056 | **Win Rate:** 48.1% | **Total PnL:** +$1,055 (25,605 trades)

Analyzes the ratio of sell volume to total volume over recent candles. A high sell-to-total ratio indicates aggressive selling pressure (order flow imbalance) that often precedes further downward movement.

**Entry Signal (Short):** Sell volume ratio > 60% over the last 5 candles (calculated as: sell_vol / (buy_vol + sell_vol) where volumes are weighted by candle body direction).  
**Confirmation:** RSI > 55, Volume spike > 120% of average.  
**Stop Loss:** 1.5× ATR above entry.  
**Take Profit:** 2.5× Stop Loss distance.  
**Best Pairs:** All top 10 assets (broadest applicability of any strategy).

---

### 6. EMA 9/21 Crossover
**Category:** Trend Following  
**Overall PF:** 1.054 | **Win Rate:** 45.0% | **Total PnL:** +$103 (4,136 trades)

A classic dual-EMA crossover system. The 9-period EMA is the fast line and the 21-period EMA is the slow line. Crossovers signal trend direction changes.

**Entry Signal (Short):** 9-period EMA crosses below 21-period EMA (Death Cross on short timeframe).  
**Confirmation:** Price below 50-period EMA (broader downtrend), RSI < 50.  
**Stop Loss:** 1.5× ATR above entry.  
**Take Profit:** 2.5× Stop Loss distance.  
**Best Pairs:** Works broadly across all assets.

---

### 7. Keltner Channel + RSI
**Category:** Volatility / Mean Reversion  
**Overall PF:** 1.046 | **Win Rate:** 47.6% | **Total PnL:** +$837 (15,461 trades)

Keltner Channels use ATR to define dynamic support/resistance bands around an EMA. Price touching or exceeding the upper band combined with RSI overbought signals a high-probability short entry.

**Entry Signal (Short):** Price closes above the upper Keltner Channel (20-period EMA ± 2.0× ATR) AND RSI(14) > 70.  
**Confirmation:** Price above 20-period EMA.  
**Stop Loss:** 1.5× ATR above entry.  
**Take Profit:** 2.5× Stop Loss distance.  
**Best Pairs:** OP (PF 2.4), DOT, ATOM.

---

### 8. CVD Absorption Reversal
**Category:** Volume / Microstructure  
**Overall PF:** 1.042 | **Win Rate:** 44.9% | **Total PnL:** +$168 (6,237 trades)

Cumulative Volume Delta (CVD) tracks the cumulative difference between buying and selling volume. When CVD is rising (buyers aggressive) but price fails to make higher highs, it signals seller absorption — a bearish reversal signal.

**Entry Signal (Short):** CVD is positive over the last N candles (buyers dominant), but price is flat or declining (sellers absorbing). Absorption ratio > 0.7.  
**Confirmation:** RSI > 55, Volume > 110% of average.  
**Stop Loss:** 1.5× ATR above entry.  
**Take Profit:** 2.5× Stop Loss distance.  
**Best Pairs:** All top 8 assets.

---

### 9. Donchian Channel Breakout
**Category:** Trend Following / Breakout  
**Overall PF:** 1.018 | **Win Rate:** 44.1% | **Total PnL:** +$359 (15,395 trades)

Uses the highest high and lowest low over N periods. A break below the lower channel signals a new downtrend with strong momentum.

**Entry Signal (Short):** Price closes below the 20-period Donchian lower channel (20-period low).  
**Confirmation:** High volume on the breakout candle (> 150% of average).  
**Stop Loss:** Upper Donchian Channel (20-period high).  
**Take Profit:** 2× the channel width below entry.  
**Best Pairs:** Works broadly; best in trending markets.

---

### 10. ICT Order Block + Liquidity Sweep
**Category:** Smart Money Concepts  
**Overall PF:** 1.017 | **Win Rate:** 44.9% | **Total PnL:** +$112 (8,925 trades)

An Order Block is the last bearish candle before a significant upward move (demand zone) or the last bullish candle before a significant downward move (supply zone). A Liquidity Sweep occurs when price briefly spikes above a prior high (taking out stop-losses) before reversing.

**Entry Signal (Short):** Price sweeps above a prior swing high (liquidity grab), then closes back below it. The sweep candle is near a bearish Order Block (supply zone).  
**Confirmation:** RSI > 60, Volume spike on the sweep candle.  
**Stop Loss:** Above the high of the sweep candle.  
**Take Profit:** 2.5× Stop Loss distance.  
**Best Pairs:** PEPE (PF 2.7), BOME, ADA.

---

## Strategies to AVOID (PF < 1.0 — Net Losers)

These strategies lost money across 340,000+ trades and should be disabled or completely reworked before re-testing.

| Strategy | PF | Total PnL | Why It Fails |
|----------|----|-----------|--------------|
| SuperTrend + MACD | 0.707 | -$120 | Lagging signals in volatile crypto; too many whipsaws |
| VWAP + MACD Momentum | 0.771 | -$148 | VWAP less meaningful in 24/7 crypto vs. traditional markets |
| Pivot Point Breakdown | 0.826 | -$113 | Static pivot levels don't adapt to crypto's extreme ranges |
| Waddah Attar Explosion | 0.848 | -$93 | Insufficient trade count; signal too infrequent |
| Fibonacci Retracement | 0.912 | -$628 | Works on specific pairs (UNI, ATOM) but loses heavily on others |
| RSI Divergence | 0.919 | -$695 | Divergence signals too early in strong trending markets |
| Elder Triple Screen | 0.927 | -$273 | Multi-timeframe complexity causes signal lag |
| Laguerre RSI Pullback | 0.949 | -$302 | Pullback entries in downtrends cut too early |

> **Exception:** Fibonacci Retracement has a PF of 2.477 on UNI/USDT and 2.327 on ATOM/USDT specifically. It should be used only on these two assets and disabled for all others.

---

## Strategy Selection Guide for Testing Engine

### Tier 1 — Core Strategies (Always Active)
These strategies have the highest PF and broadest applicability. They should be the default for all agents.

| Strategy | Why |
|----------|-----|
| **Chande Momentum Oscillator** | Highest PF (1.278), massive total PnL, exceptional on meme coins |
| **ICT Fair Value Gap (FVG)** | High PF (1.121), high win rate (47.7%), works on many assets |
| **Squeeze Momentum (LazyBear)** | High PF (1.082), excellent for capturing explosive moves |

### Tier 2 — Pair-Specific Specialists (Active on Best Pairs Only)
These strategies have lower overall PF but exceptional performance on specific assets.

| Strategy | Best Pairs |
|----------|-----------|
| **Parabolic SAR Flip** | WIF (PF 4.16), FLOKI (PF 3.05), BOME (PF 2.34) |
| **Williams %R Reversal** | FLOKI (PF 4.61), top 6 assets |
| **Keltner Channel + RSI** | OP (PF 2.39), DOT, ATOM |
| **Bollinger Band Squeeze** | DOGE (PF 2.37), SOL, ADA |
| **Fibonacci Retracement** | UNI (PF 2.48), ATOM (PF 2.33) ONLY |

### Tier 3 — Volume Confirmation Layers (Use as Filters)
These strategies are best used as confirmation signals layered on top of Tier 1 strategies rather than as standalone entries.

| Strategy | Role |
|----------|------|
| **Order Flow Imbalance** | Confirm sell pressure before entry |
| **CVD Absorption Reversal** | Confirm seller absorption before entry |
| **ICT Order Block + Liq Sweep** | Identify high-probability reversal zones |

### Tier 4 — Macro Filters (On-Chain / Sentiment)
These are not trade-by-trade signals but macro filters that adjust position sizing or disable trading entirely.

| Indicator | Signal | Action |
|-----------|--------|--------|
| MVRV Z-Score > 2.5 | Asset overvalued | Reduce position size by 50% |
| Exchange Inflow Spike | Whales selling | Skip new entries for 1-2 hours |
| Funding Rate > 0.1% | Market over-leveraged long | Increase short signal confidence |
| Fear & Greed Index > 80 | Extreme greed | Tighten stop-losses by 20% |

---

## Implementation Checklist for Testing Engine

When adding a new strategy to the testing engine, verify the following:

- [ ] Strategy has a minimum of 50 trades in backtest before evaluating PF
- [ ] PF > 1.0 on the specific asset being traded
- [ ] Win Rate > 40% (ensures enough winners to build streaks for Anti-Martingale)
- [ ] Average Win > Average Loss (positive expectancy per trade)
- [ ] Stop Loss is ATR-based (adapts to volatility)
- [ ] Take Profit is minimum 2.0× Stop Loss (2:1 R:R minimum, 2.5:1 preferred)
- [ ] Strategy is SHORT-only (project rule — no LONG trades)
- [ ] Minimum 2 confirmation signals required before entry
- [ ] Position size uses Gods Level formula: (Capital × 2%) ÷ SL% × Kelly(0.25)

---

*All performance data sourced from the Trading Guru Engine v9.1/v10.0 SQLite database (`trades.db`) — 340,000+ real paper trades on OKX live market data.*
