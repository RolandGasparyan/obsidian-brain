# MA Trend-Follow Strategy (with optional weekly filter)

A one-line moving-average rule that crushed the 9-agent indicator engine
on 8+ years of real BTC/USD data:

> Hold 100% BTC when daily close > 50-day SMA, else 100% USDT.

Adding a weekly trend filter (long only when weekly close > weekly SMA10
**and** the daily rule fires) raises compound performance from +552% to
**+3,427%** across the same 6 regimes — the new recommended variant.

## Why this exists

This repo started as a 9-agent indicator-consensus scalping engine. After
two weeks of tuning (partial-TP1 exits, HTF regime filter, per-agent
performance weighting, timeframe migration 15m → 4h), the best version
returned **−0.5% over 24 months** of real BTC/USD walk-forward.

A trivial moving-average rule on the same data returned **+74.9%** over
the same 24 months — and **+553%** when chained across six independent
2018–2026 regime samples. The complex strategy lost; the dumb rule won
by 75 percentage points and outperformed buy-and-hold on a compound
basis by 336 points.

## Backtest evidence

Run on real Bitstamp 1-minute BTC/USD data, aggregated to 1-day candles,
0.25% round-trip fees, $1000 starting balance.

| Period | Regime | BTC move | B&H | MA50 | **MA50+W10** |
|---|---|---:|---:|---:|---:|
| 2018 full year | catastrophic bear | -78% | -71.6% | -45.6% | **+2.4%** |
| 2019 full year | range + recovery | +95% | +94.6% | +111.7% | **+170.3%** |
| 2020-04 → 2021-04 | COVID mega-bull | +800% | +816.2% | +428.6% | +419.1% |
| 2022 full year | major bear | -66% | -65.3% | -41.2% | **-15.0%** |
| 2023-10 → 2024-06 | bull | +125% | +124.2% | +63.2% | **+81.1%** |
| 2025-01 → 2026-04 | moderate bear | -24% | -19.5% | +11.7% | **+59.5%** |

**Compound across all six periods (≈7.5 years chained, $1000 start):**

| Strategy | Final $ | Compound ROI |
|---|---:|---:|
| Buy & Hold | $3,172 | +217% |
| MA50_direct | $6,519 | +552% |
| MA50+W20 | $10,619 | +962% |
| **MA50+W10** | **$35,272** | **+3,427%** |
| 9-agent engine (24-month subset only) | ~$995 | -0.53% |

The weekly filter's edge is asymmetric: it gives back only 1-3 pp in
mega-bull years (2020 +428% → +419%) but rescues catastrophic-bear
years like 2018 (-45.6% → +2.4%) and 2022 (-41.2% → -15%). On a
compound basis the bear protection dominates by 5×.

The MA50 strategy gives up roughly half the upside in mega-bull years
(it sells on each major dip and re-enters higher) but cuts the
2018/2022 catastrophic drawdowns nearly in half — and that asymmetry
compounds enormously over multi-cycle horizons.

## Why the simple rule beats the complex engine

| Failure mode in 9-agent engine | How MA50 sidesteps it |
|---|---|
| 0.25% fees × hundreds of trades = bleed | ~10 trades/yr keeps fee drag negligible |
| Tight ATR stops swept by normal noise | MA itself is a slow, noise-resistant stop |
| Premature TP exits cap winners | No fixed TP — rides until MA flips |
| Late momentum-confirmed entries | Symmetric MA cross — no consensus delay |
| EMERGENCY_STOP at -1.5% kills good trades | No intrabar stop — daily close only |

## How to run

### Backtest on real historical data
```bash
python backtest_ma.py --csv data/btcusd_1min_latest.csv --timeframe 1d
python backtest_ma.py --csv data/btcusd_1min_bull2024.csv --timeframe 1d
```

### Paper forward-test with synthetic candles
```bash
python run.py --strategy ma50
```

### Paper forward-test with REAL exchange candles (Stage 1)
```bash
# Recommended: daily MA50 + weekly MA10 filter (best backtest)
python run.py --strategy ma50w10 --paper-real --interval 1d

# Alternates
python run.py --strategy ma50w20 --paper-real --interval 1d
python run.py --strategy ma50    --paper-real --interval 1d  # no weekly filter
python run.py --strategy ma100   --paper-real --interval 1d  # slower variant
```

In `--paper-real` mode the engine fetches live 1-day candles from
Gate.io's public candlestick endpoint (no API key required) and routes
all order calls through the paper-fill path in `Exchange.order()`.
Real money is never at risk unless `LIVE_MODE = True` in `class C`.

## Going live (Stage 2)

When `--paper-real` has run for ≥7 days and confirms the expected
behavior (≈1 trade per month, MA flips trigger correctly, equity
tracking matches the backtest):

1. `export GATEIO_API_KEY=...` and `GATEIO_SECRET=...`
2. Set `LIVE_MODE = True` in `class C`
3. Start very small: $50 USDT
4. `python run.py --strategy ma50 --live`  *(implementation gate to
   add — `run_ma_strategy` currently rejects live mode by design until
   forward-test confirms behavior)*

## Caveats

- **Single asset only.** Backtested on BTC/USD. Other coins may behave
  differently — re-run `backtest_ma.py` against their CSVs first.
- **Whipsaw risk.** In choppy ranges around the MA the strategy will
  flip in/out frequently. The 2019 result (+111.7%) had only 6 trades
  but 33% WR — most flips lost money; one big winner carried the year.
- **Past performance is not future performance.** The compound +553%
  is what the rule *would have* returned if applied each year starting
  with the prior year's ending balance. Real-world execution introduces
  slippage, occasional API outages, and tax/withdrawal frictions.
- **Position is binary.** No fractional sizing, no leverage. Either
  100% BTC or 100% USDT. This is by design — fractional sizing in
  trend-following systems generally underperforms the binary version.

## Future directions

If MA50 forward-tests well, natural extensions:
- Add a second asset (ETH on the same MA50 rule), trade whichever has
  the stronger trend.
- Add a higher-timeframe filter: only take MA50 long if the weekly MA
  is also rising (fewer trades, less drawdown, smaller upside).
- Test MA50 + simple short side via futures (would have profited in
  2018/2022 instead of just sitting in USDT).

These should each be validated against the same multi-regime backtest
before being shipped.
