# 🏆 Champion Cell — first OOS-clearing configuration in the research arc

**Identified:** 2026-04-25 by `champion_select.py`
**Status:** ⛔ **REJECTED at D7 validation gate** by `rsi2_validate.py` (2026-04-25)
**Source backtest:** 4 pairs × 10 candidate strategies × 70/30 OOS split via backtesting.py 0.6.5

> **2026-04-25 update:** the +1.80 OOS Sharpe was a single-window
> artifact. Rolling walk-forward showed only 1/5 windows beat B&H and
> Monte Carlo permutation classified the edge as **LIKELY NOISE** (real
> Sharpe beats only 37% of shuffled-return runs). See section "D7
> validation results" below. Strategy will NOT ship at D7. Vote
> ensemble stays in production. ADR-003 discipline confirmed correct.

---

## The result

| Field | Value |
|---|---|
| **Strategy** | RSI-2 mean reversion (Connors-style) |
| **Entry** | RSI(2) < 10 |
| **Exit** | RSI(2) > 70 |
| **Pair** | XRP_USDT |
| **Timeframe** | 4h |
| **Commission modeled** | 0.0025 (0.25% RT — conservative) |

| Out-of-sample metric | Value | Ship-gate threshold | Pass |
|---|---:|---:|:---:|
| Sharpe Ratio | **+1.80** | ≥ 0.50 | ✅ |
| Return | **+7.8%** | > 0 | ✅ |
| vs Buy-and-Hold | +7.8% vs +5.8% B&H | beats B&H | ✅ |
| Win Rate | **72%** | ≥ 55% | ✅ |
| Trades | 18 | ≥ 5 | ✅ |
| Max Drawdown | −6.6% | < 15% | ✅ |
| Profit Factor | 2.10 | > 1.5 | ✅ |
| SQN | +1.10 | > 1.0 | ✅ |

**This is the first cell across nine research scripts that clears every
audit ship-gate with a statistically meaningful sample size.**

## Why it survived where MA-family didn't

The RSI-2 strategy is mechanically **decorrelated** from the MA-family
strategies that failed every prior round:

| Family | Wins when… | Loses when… |
|---|---|---|
| MA / Vote / Donchian (trend) | sustained directional moves | chop, sideways, mean-reverting |
| RSI-2 (mean reversion) | chop, range-bound | strong sustained trends |

Crypto has been in chop / mean-reverting regime for the entire OOS
period (last 30% of 1000 daily bars). The trend strategies all failed.
A mean-reversion strategy mechanically benefits from the same regime
that punishes the others. That's not luck — it's regime-class fit.

## Other near-winners worth noting

The composite ranking by `champion_select.py` (Sharpe + WR-bonus −
DD-penalty + EV-bonus):

| # | Pair | TF | Strategy | OOS Sharpe | OOS Ret | WR | Trades |
|---:|---|:---:|---|---:|---:|:---:|:---:|
| 1 | **XRP** | **4h** | **RSI-2** | **+1.80** | **+7.8%** | **72%** | **18** |
| 2 | ETH | 4h | MAW 20+5 | +0.98 | +6.5% | 44% | 9 |
| 3 | SOL | 4h | RSI-2 | +0.36 | +1.4% | 69% | 16 |
| 4 | ETH | 1d | RSI-2 | +0.47 | +20.1% | 60% | 15 |
| 5 | ETH | 4h | MAW 50+5 | +0.12 | +0.8% | 29% | 7 |

Three of the top five are RSI-2 cells. The pattern is consistent:
**mean-reversion on 4h is the regime-fit edge in current crypto data.**

## What this is NOT

1. **Not yet deployed.** Running production bots are still on Vote
   ensemble (trend-follow). RSI-2 is not yet a `--strategy` flag
   option in `run.py`. Implementing it requires NEW strategy code,
   which `ADR-003` forbids on `main` until D7 (May 1).

2. **Not yet walk-forward-validated.** The 70/30 OOS split is one
   sample. Before deployment we should run:
   - Monte Carlo permutation test (target |IC| ≥ 0.04, t ≥ 2.0)
   - Rolling walk-forward (≥ 4/5 windows beat B&H)
   - Slippage stress test (RSI-2 fires often → fees hurt more)

3. **Not yet risk-overlay'd.** Patches 1+3+5 from `GODMODE_AUDIT.md` are
   tuned for trend-follow (hard stop, DD breaker, bar-close gate). RSI-2
   needs its own risk overlay — natural stop is "if RSI doesn't recover
   in N bars, exit" rather than a fixed-pct floor. To be designed
   in the D7+ implementation.

## D7 deployment plan (gated by ADR-001 D6 analyzer + this finding)

```
D6 (Apr 30)
  microstructure_analyze.py runs against 5d of WS data.
  Result is independent of this champion finding.

D7 (May 1) — implementation window opens
  Build:
    [ ] gods_level_engine.py: add RSI2Strategy class with
        - HARD_STOP_PCT  (per-trade floor, RSI-2 specific tuning)
        - MAX_HOLD_BARS  (force exit if RSI doesn't recover in 24 bars)
        - bar-close gate from Patch 5 already applies
    [ ] run.py: add --strategy rsi2 flag + run_rsi2_strategy
    [ ] tests/test_rsi2.py: hard stop, RSI thresholds, bar-close
    [ ] config.py: PAIRS = ["XRP_USDT"] (single pair, focus)
    [ ] systemd unit: --strategy rsi2 --interval 4h
  Validate:
    [ ] walk_forward.py with RSI2 (Monte Carlo permutation, IC, rolling wins)
    [ ] professional_backtest.py 70/30 OOS reconfirm Sharpe +1.80
    [ ] godsmode_backtest.py extend with RSI2 in candidate matrix
  Deploy:
    [ ] Stop SOL/XRP/AVAX bots
    [ ] Restart XRP bot with --strategy rsi2 --interval 4h
    [ ] Keep ETH bot on Vote as decorrelated control
  Result tracking:
    [ ] Telegram alerts for every RSI-2 BUY/SELL
    [ ] After 30+ closed trades, evaluate vs backtest expectation

D7+45  Stage 2 gate ($200 real capital, audit §7) only if:
  - 30+ closed paper trades
  - Cumulative paper PnL > 0
  - Live trade rate within 30% of backtest expectation (≈ 12-18 trades / 60 days)
  - No DD or stop-loss circuit-breaker fires
```

## What stays the same

- ADR-001 binding: D6 analyzer is still the next decision point
- ADR-002 promotion table still applies if microstructure shows signal
- ADR-003 hard rule: no strategy code on main until D7
- l99_validate.py still gates real-money deployment via `GO` verdict
- Audit Stage 2 gate ($200 cap, 60 days paper minimum) still applies

## D7 validation results — 2026-04-25 (`rsi2_validate.py`)

The 70/30 OOS split that produced the +1.80 Sharpe is one specific
window. Before any D7 implementation effort, four independent ship
gates were run on the same data:

| Gate | Test | Result | Verdict |
|---|---|---|:---:|
| 1 | Rolling walk-forward, 5 windows | 1/5 windows beat B&H + Sharpe>0 | 🛑 FAIL |
| 2 | Monte Carlo permutation, 200 runs | Real Sharpe beats 37% of shuffles | 🛑 FAIL — LIKELY NOISE |
| 3 | Fee stress @ 0.40% RT | Sharpe +0.62 ≥ target 0.50 | ✅ PASS |
| 4 | MAX_HOLD_BARS sweep {12..72} | All collapse to identical +1.32 | ⚠ neutral |

**Walk-forward window-by-window:**

| Window | OOS Ret | B&H Ret | Edge | Sharpe | Trades |
|---|---:|---:|---:|---:|---:|
| [0..166] | −10.07% | −7.15% | −2.92% | −144.65 | 2 |
| [208..374] | −4.76% | +2.60% | −7.36% | −36.72 | 1 |
| [417..583] | −2.34% | +3.88% | −6.21% | −8.96 | 1 |
| [625..791] | +0.49% | +2.06% | −1.57% | +1.25 | 3 |
| **[834..1000]** | **+3.63%** | −1.31% | **+4.94%** | **+4.62** | 3 |

Only the final window (which overlaps the 70/30 OOS slice that
produced the champion) is profitable. The other four lose. The +1.80
"champion Sharpe" reflects a single regime, not a persistent edge.

**Monte Carlo:** synthesizing 200 price paths with identical drift +
volatility but shuffled temporal order, RSI-2 produces a Sharpe
distribution centered on −4.44. Real Sharpe is −4.40, beating only 37%
of shuffles. A real edge should sit in the top 5% (≥ 95th percentile);
this sits in the bottom half. The strategy is statistically
indistinguishable from noise on this dataset.

## Closing note

For 30 hours we have been correctly answering "no" to "is it
profitable?" because no rigorous test produced a profitable cell. The
70/30 split made it look like we'd found one — but the moment we
ran the rest of the validation suite (walk-forward, MC permutation),
the result evaporated. **That is exactly how the validation suite is
supposed to work.**

ADR-003's 5-day delay is what protected us. Without it, we would have
spent the D7 implementation window writing RSI2Strategy code and
switching live capital to a curve-fit. The discipline did its job.

**Path forward (revised 2026-04-25):**
1. Vote ensemble stays in production. No D7 strategy switch.
2. ADR-001 D6 microstructure analyzer (Apr 30) is now the only live
   decision point left in Phase A.
3. If D6 yields no signal either, ADR-002 fallback (B1 on-chain) is
   the next research direction — not another OHLCV trend variant.
4. RSI-2 stays in `champion_select.py` as a documented research dead
   end. Future candidates must clear all 4 D7 gates, not just the
   single 70/30 split.
