# Stage 1 Forward-Test Checklist

Before any real money touches the exchange, `--strategy ma50w10` must
run in `--paper-real` mode on your own machine for at least 7 calendar
days and pass every check below. The backtest says it should work.
Stage 1 confirms it actually does against live Gate.io candles,
without putting a cent at risk.

## Prerequisites (do once)

```bash
git pull                                  # latest branch
python -m pytest tests/ -q                # must show 13 passed
python run.py --dryrun                    # must show 28/28 PASSED
```

Do **not** proceed to the run below if either fails.

## The Stage 1 run

```bash
python run.py --strategy ma50w10 --paper-real --interval 1d \
    2>&1 | tee stage1.log
```

Keep it running continuously. Suspend your laptop, come back to it — the
strategy acts once per day when the daily bar closes, so a few hours of
sleep mode is fine. Target: **7+ consecutive days**.

## Day-by-day expected behavior

| Day | What you should see |
|---|---|
| 1 | Banner prints, `loop 20/40/60 …` lines every 20 iterations |
| 1-3 | Equity stays flat if BTC is below 50d SMA or weekly below SMA10 |
| Any day | If BTC daily close crosses above SMA50 **and** weekly > SMA10, you'll see `📈 BUY` and position flips to LONG |
| Any day | If either condition flips, you'll see `📉 SELL` and position returns to USDT |
| After 7 days | 0–2 trades is normal — this strategy is slow by design |

The backtest averages roughly **one full round-trip every 6-10 weeks**
in non-bull regimes. If you see more than 4 round-trips in 7 days,
something is wrong — see the red flags section.

## Green flags (Stage 1 is passing)

- ✅ No crashes, no stack traces. Warnings about `fetch_bars` retries
  during brief API hiccups are fine as long as they resolve.
- ✅ Every `📈 BUY` price is close to the price Gate.io showed when the
  daily bar closed (you can cross-check on gate.com BTC_USDT 1D chart).
- ✅ Position state (LONG vs USDT) matches what you'd predict from
  eyeballing the SMA50 and weekly SMA10 on the chart.
- ✅ `equity=$…` numbers change only when a `📈 BUY` or `📉 SELL`
  actually fires — otherwise equity stays fixed (paper positions
  aren't marked-to-market in the current logger, by design).
- ✅ If BTC is clearly trending up for a week and you're not LONG,
  you can see *why* in the weekly filter (open the chart — weekly
  SMA10 probably declined; filter was correctly conservative).

## Red flags (ABORT and investigate)

| Symptom | Likely cause | Action |
|---|---|---|
| Stack traces on startup | engine/module mismatch after `git pull` | re-run `python run.py --dryrun` |
| Continuous `fetch_bars empty` warnings | Gate.io IP-blocking your region, wrong pair name, or rate limiting | stop, investigate, do NOT go live |
| Many flips per day (>2) | bug in weekly aggregation or stale data | stop, file issue, do NOT go live |
| Long position opened when BTC is obviously in a downtrend | weekly filter not being applied | stop, inspect `weekly_bars` in `run_ma_strategy`, do NOT go live |
| `LIVE_MODE` shows 🔴 in any banner | misconfiguration | stop immediately, set back to False |
| Orders log shows anything other than `paper: True` in the fill dict | execution routing broken | stop immediately |

## Decision criteria (after 7+ days)

You may move to Stage 2 (real money) only if **all** are true:

1. Stage 1 ran ≥7 consecutive days without restart.
2. Zero red flags triggered.
3. Every trade the strategy took matches an entry/exit you can justify
   on the BTC 1D chart.
4. Your paper equity ≈ a buy-and-hold baseline on any day the strategy
   was LONG (within slippage/fee budget of ±0.5%).
5. You are prepared for the system to lose money in live — Stage 1
   doesn't guarantee Stage 2 profitability, it only rules out
   *mechanical* failures.

If any of these fail, **do not proceed to live**. Either fix the
cause or abandon the project.

## Stage 2 (after all the above)

When ready — and only then — see the "Going live" section in
`MA_STRATEGY.md`. Short version:

```bash
# 1. Rotate + export keys (never paste them in chat or commit)
export GATEIO_API_KEY=...
export GATEIO_SECRET=...

# 2. Edit gods_level_engine.py:  class C:  LIVE_MODE = True

# 3. Start with the smallest meaningful position — $50 USDT max
python run.py --strategy ma50w10 --live

# 4. At the prompt, type exactly:  CONFIRM LIVE TRADING
#    (any typo aborts — this is intentional)
```

Keep balance small until you have ≥30 days of live trades that behave
like the backtest. Scale up slowly from there if at all.
