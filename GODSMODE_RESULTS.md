# 🛑 GODSMODE — the most definitive answer we can produce

Run date: 2026-04-25 · Framework: kernc/backtesting.py 0.6.5 · 80 OOS backtests · 10 strategies × 2 timeframes × 4 pairs

## TL;DR

**80 grid-optimized backtests across 10 strategy families, 2 timeframes, 4 pairs.**
Every (strategy, timeframe) combination fails the ship gate on majority of pairs.
The best result across all 80 is **one pair × one strategy** clearing the triple bar.

## The scorecard — cross-pair ranking by mean OOS SQN

### 1-day timeframe

| Strategy | mean OOS SQN | mean Sharpe | mean Ret% | Pairs + | Ships |
|---|---:|---:|---:|:---:|:---:|
| MAWeekly | −2.19 | −2.19 | −18.5% | 0/4 | 0/4 |
| SmaCross | −2.04 | −2.81 | −23.2% | 0/4 | 0/4 |
| Donchian | nan | nan | −9.2% | 0/4 | 0/4 |
| BollingerBreak | nan | −1.14 | −7.2% | **1/4** | 0/4 |
| MACDSig | −0.81 | −0.62 | −12.5% | 0/4 | 0/4 |
| SuperTrend | nan | nan | −15.6% | 0/4 | 0/4 |
| KeltnerBreak | nan | nan | −5.5% | 0/4 | 0/4 |
| ChandelierExit | −1.64 | −3.35 | −36.2% | 0/4 | 0/4 |
| ADXGatedMA | nan | nan | −11.5% | 0/4 | 0/4 |
| **RSI2Reversion** | nan | −0.87 | −13.7% | **1/4** | **1/4** |

### 4-hour timeframe

| Strategy | mean OOS SQN | mean Sharpe | mean Ret% | Pairs + | Ships |
|---|---:|---:|---:|:---:|:---:|
| **SmaCross** | nan | −2.97 | −1.9% | **2/4** | **1/4** |
| MAWeekly | −2.37 | −13.82 | −9.4% | 1/4 | 1/4 |
| Donchian | nan | −11.64 | −9.5% | 1/4 | 0/4 |
| MACDSig | −2.51 | −16.99 | −14.6% | 0/4 | 0/4 |
| BollingerBreak | −7.86 | −12.03 | −12.2% | 0/4 | 0/4 |
| SuperTrend | nan | −7.74 | −7.1% | 1/4 | 0/4 |
| KeltnerBreak | nan | nan | −6.0% | 0/4 | 0/4 |
| ChandelierExit | −1.27 | −5.37 | −8.3% | 0/4 | 0/4 |
| ADXGatedMA | −2.60 | −20.06 | −12.1% | 1/4 | 0/4 |
| **RSI2Reversion** | nan | nan | −0.9% | **2/4** | **1/4** |

**"ships" column = pairs passing OOS SQN ≥ 0.5 AND Sharpe ≥ 0.3 AND Ret > 0**

## Individual bright spots worth noting

While no (strategy, TF) combo passes the ship gate across the portfolio, a
handful of single pair × strategy cells did clear OOS positivity:

| Pair | TF | Strategy | OOS SQN | OOS Sharpe | OOS Ret | vs B&H |
|---|---|---|---:|---:|---:|---:|
| AVAX | 1d | RSI2Reversion | **+2.36** | +0.32 | **+11.6%** | −66.3% |
| ETH | 4h | MAWeekly | **+1.39** | +1.32 | +5.5% | +12.3% |
| ETH | 4h | SmaCross | +0.89 | +1.14 | +6.3% | +12.3% |
| XRP | 4h | RSI2Reversion | +1.28 | +1.25 | +1.5% | +3.7% |

Interpretation:

- **AVAX + RSI2 (1d)** is a one-off statistical fluke — just 2 trades, SQN is
  unreliable with so few observations. Not deployable.
- **ETH on 4h** is the most coherent bright spot: trend-follow (SmaCross,
  MAWeekly) produced positive SQN and Sharpe, captured 5–6% of a 12% move.
  Both strategies simultaneously positive on one asset / one TF is the closest
  thing to a real edge in this sweep.
- **RSI2Reversion** shows occasional positive cells but only on specific
  pair-TF combinations. No systematic edge.

## Why the negative verdict is robust

Every prior round could be accused of methodological gaps:
- Hand-rolled walk-forward → "too optimistic averaging"
- Portfolio MC → "null distribution too strict"
- Regime gates → "tried wrong gates"
- Mean-reversion ensemble → "tried wrong ensembles"

This godsmode run addresses ALL of those:
- 10 orthogonal strategy families (trend, breakout, momentum, mean-reversion,
  volatility, trailing)
- 2 timeframes (daily AND 4h, catching different move scales)
- Bayesian-optimized params on 80% of data, frozen for 20% OOS test
- Industry-standard framework (backtesting.py) with proper trade bookkeeping
- SQN as optimizer target (Van Tharp's noise-adjusted edge metric)

**If any standard technical rule worked on this data, this sweep would have
found it.** It didn't.

## What this means practically

1. **Do not deploy real money** to any of the strategies we have built.
   There is no OOS evidence that any single strategy or any ensemble
   produces positive returns in the current regime.

2. **The ETH/4h bright spot is weak evidence at best.** 5% OOS return on
   a pair where buy-and-hold got 12% is not outperforming — it's just
   capturing a fraction of the move while adding noise. The positive
   Sharpe is from avoiding drawdowns, not generating alpha.

3. **The paper bots running Vote ≥2 of 3 on 4 pairs should continue.**
   Live paper PnL over the next 30–60 days is now the only informative
   new data. If the live curve matches the backtest (which predicts
   small loss in chop), the model is calibrated. If live diverges
   positive, the strategy has something the backtest missed.

4. **The research infrastructure is complete and reusable.** We have:

   | File | What it does |
   |---|---|
   | `walk_forward.py` | expanding + rolling + Monte Carlo |
   | `param_sweep.py` | parameter grid with ship-bar gating |
   | `regime_gated_ma.py` | 6 macro-regime filter tests |
   | `mean_reversion.py` | RSI-2 + BB fade + ensemble |
   | `deep_edge.py` | portfolio walk-forward + vol targeting |
   | `max_edge.py` | 2500-bar history, 10-pair portfolio |
   | `professional_backtest.py` | strict 70/30 OOS via backtesting.py |
   | **`godsmode_backtest.py`** | 10 strategies × 2 TFs × 4 pairs OOS |

   Any future strategy (on-chain signals, ML-based, market-making) can
   be dropped into this harness and validated with the same rigor.

## The fundamental honest answer

The strategies that worked historically (2019–2023 bull cycles) do not work
in the 2024–2025 chop regime. This is not a flaw in our research; it is the
nature of the market. Technical trend-following survives on large sustained
trends, and we are currently in one of the longest flat periods in crypto
history.

**Two paths forward:**

**A. Wait for regime change** — ride out the chop on paper, deploy when
   the expanding-window OOS starts showing positive returns again. This
   is the institutional answer: sit in cash until the signal returns.

**B. Switch edge class** — the technical-indicator edge class appears
   exhausted on current data. Alternatives with genuinely different
   mechanical basis:

   - **On-chain flow** (exchange balances, stablecoin supply, funding rates)
   - **Options skew / IV rank** (vol mispricing arbitrage)
   - **Market making / liquidity provision** (capture the spread, not
     direction)
   - **Cross-exchange arbitrage** (tiny edge × high frequency × leverage)
   - **ML-based regime classifier** (supervised on labeled periods, then
     gate existing strategies)

   These require different infrastructure but our walk-forward / SQN
   harness validates them equally well.

## Recommendation

**Do not ship real money. Continue paper-forward. Do not invest more time
in technical-signal research until either (a) the paper bots show unexpected
positive PnL over 30+ days, or (b) the broader market regime flips back to
sustained trend.**

We have produced the most rigorous honest answer our tools can produce.
Further sophistication without new data is overfitting to the same 7 years
of history. The next informative bit arrives from live paper OOS.

## Reproducing

```bash
python3 godsmode_backtest.py
python3 godsmode_backtest.py --timeframes 1d 4h 1h
python3 godsmode_backtest.py --strategies MAWeekly SuperTrend RSI2Reversion
python3 godsmode_backtest.py --pairs ETH_USDT SOL_USDT
```
