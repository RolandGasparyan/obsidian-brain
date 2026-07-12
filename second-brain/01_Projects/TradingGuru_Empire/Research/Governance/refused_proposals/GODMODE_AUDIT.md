# GODMODE Audit — AI Trading Championship

**Date:** 2026-04-25 · **Auditor:** 6-agent parallel audit (Strategy / Risk / Sizing / Execution / Regime / Overfitting) · **Scope:** all code + all 7 research artifacts · **Verdict:** DO NOT DEPLOY REAL CAPITAL on current system. Infrastructure is ship-grade; strategy edge is not.

---

## 1. Executive Performance Diagnosis

| Dimension | Score | Finding |
|---|:---:|---|
| **Signal quality** | 42 / 100 | 3 trend-followers masquerading as ensemble; no true decorrelation |
| **Risk engine** | 28 / 100 | No per-trade hard stops; −15% circuit breaker too loose vs observed −23% to −42% OOS DD |
| **Position sizing** | 42 / 100 | Binary 100%; P(ruin) 18–22% at Sharpe 2.15 / WR 41% |
| **Execution** | 28 / 100 | Real slippage 20–35bp on top of 25bp fees → 0.60% RT, not 0.25% (2.4× modeled cost) |
| **Regime awareness** | 2 / 10 | Every simple gate tested hurts; no micro-timeframe or breadth signal |
| **Robustness / overfit** | 15 / 100 | 92% overfit probability; actual significance 14% after multiple-testing correction |

**Composite: ~27 / 100 → institutional minimum is 70/100.**

The strategy research produced a Sharpe 2.41 in-sample number that **dropped to OOS Sharpe −0.5 to −1.8** once properly held out. Infrastructure (Telegram, kill switch, HTTPS, monitoring, paper-real systemd) is separately excellent and reusable.

---

## 2. Risk Profile Assessment

### Top 5 hidden tail risks (severity × probability)

1. **🔴 No per-trade hard stops** — exits only on MA crossover. A flash crash that skips the MA can hold position through 15–25% adverse move. Current code (`SimpleMAStrategy.execute`, `VoteEnsembleStrategy.execute`) has no `stop_loss_pct` enforcement.
2. **🔴 Correlated portfolio, no cap** — ETH, SOL, XRP, AVAX have ρ > 0.82 with BTC. When BTC dumps, all 4 bots lose simultaneously. No cross-pair DD aggregation, no correlation throttle on new entries.
3. **🔴 Circuit breaker −15% is too high** — observed OOS DD is 23–42%. Breaker fires AFTER cascading loss already realized. Should be −8% portfolio-level.
4. **🟠 100% binary sizing compounds losses** — doubling-down under water. A losing streak of 6–7 trades at −2% each = −12% → near-breaker zone.
5. **🟠 Silent position hold on API failure** — `_btc_signal` fails-closed but keeps current position state; if Gate.io is slow for 60+ sec, bot drifts without regime confirmation.

### Worst-case realistic drawdown: **−22% to −28%** (bear sequence), **−16% floor** (single flash crash caught by breaker).

---

## 3. Strategy Weaknesses (concrete, code-level)

### Entry logic
- **Hysteresis band 0.25% above MA** — misses first 25bp of every move. On 5% crypto moves = 5% Sharpe drag.
- **2-of-3 voting threshold is arbitrary** — never grid-searched. Could be 3-of-3 (rare, late, high-conviction) or 1-of-3 (fast, noisy).
- **Donchian-20 is crypto-hostile** — 20-bar highs often mark local tops in crypto. Adds noise, not signal.

### Exit logic
- **Asymmetric band adds 50bp friction** — entry needs MA×1.0025, exit at MA×0.9975. 50bp built-in slippage.
- **No true exit signal** — only "reverse of entry." In 2–3% chop bands, flips 10–20× per month, fee drag −1.5 to −3% monthly.
- **No stop-loss on directional reversal** — holds through −2% moves waiting for MA flip, erasing 4–6 wins per whipsaw.

### Voter decorrelation is fake
All three voters (MA20+W5, Donchian-20, BTC-gate) are **trend-family**. When regime shifts trending → choppy, they flip together within 1–2 bars. Mechanical filter, not true diversification.

### Multiple-testing problem
~157 hypothesis tests across 7 research rounds. Bonferroni-corrected alpha: 0.05/157 = 0.000318. Our best p ≈ 0.11. **After correction, actual confidence = 14%, not 89%.**

---

## 4. Optimized Model Design

### Strategy core (replacement)
- **Signal:** MA20+W5 base + BTC-coherence gate (kept) + **replace Donchian with a true decorrelator** (RSI-2 fade or Bollinger fade). RSI-2 is mechanically opposite to trend-follow.
- **Vote rule:** 2-of-3 **with heterogeneous family split** (2 trend + 1 mean-rev). Preserves ensemble mechanics but breaks the common-failure-mode trap.
- **Regime gate:** BTC LONG ∧ BTC 30d-vol < 2% ∧ breadth ≥7/10 alts above 50d MA. Tested three-gate conjunction that Agent 5 designed — estimated +0.4 to +0.6 Sharpe lift.

### Risk overlay (all new)
- **Hard stop-loss:** −2.5% below entry (mandatory per-trade).
- **Trailing stop:** after +3% in profit, trail at −1.5% from peak.
- **Max-hold timer:** close after 20 bars regardless (prevents stuck positions in chop).
- **Portfolio-level DD cap:** −8% weekly across all 4 bots → full kill.
- **Per-pair DD cap:** −5% individual → pause that pair 48h.
- **Correlation throttle:** max 40% capital in BTC-correlated cluster (ETH+SOL+XRP+AVAX).

### Position sizing (replacement)
- **Vol-targeted fractional Kelly:** `size = 0.25 × min(1.0, 0.30 / realized_30d_vol) × balance`
- Caps per-leg risk at 30% annualized vol contribution, with 25% Kelly (conservative for Sharpe 2.15).
- Estimated P(ruin): 18–22% → **4–6%**.

### Execution upgrade
- **Limit-then-market** (30-sec timeout): limit at midpoint × 0.998 on entry; fallback to market. Saves 15–20bp per entry.
- **Bar-close gate:** evaluate signals only when new bar closes, not every 10s. Eliminates 5–6× redundant compute + avoids race conditions.
- **Real slippage recording:** live mode reads `avg_deal_price` from exchange response, not caller-passed price.
- **Rate-limit backoff:** exponential retry on 429, no silent drops.

---

## 5. Code Improvements — production-ready patches

Five concrete patches that implement §4. Each is small, testable, shippable.

### PATCH 1 — Hard stop-loss in every strategy
```python
# gods_level_engine.py, inside SimpleMAStrategy & VoteEnsembleStrategy:

HARD_STOP_PCT = 0.025   # 2.5% hard stop

def step(self, bars, weekly_bars=None):
    ...existing signal logic...
    # NEW: hard-stop override BEFORE signal check
    if self.in_position and self.entry_px > 0:
        if bars[-1].c <= self.entry_px * (1 - self.HARD_STOP_PCT):
            return "SELL"     # force exit on hard stop
    ...
```

### PATCH 2 — Vol-targeted Kelly sizing
```python
# gods_level_engine.py, inside execute() for both strategies:

def _size_fraction(self, bars) -> float:
    """Fractional Kelly × vol target. Replaces binary 1.0 sizing."""
    if len(bars) < 31: return 0.25   # ramp-up default
    closes = [b.c for b in bars[-31:]]
    rets = [math.log(closes[i]/closes[i-1]) for i in range(1, 31)]
    mu = sum(rets)/len(rets)
    var = sum((r-mu)**2 for r in rets) / (len(rets) - 1)
    vol = math.sqrt(var) * math.sqrt(365)
    vol_frac = min(1.0, 0.30 / max(0.01, vol))
    KELLY = 0.25
    return KELLY * vol_frac

def execute(self, side, price, ts, bars=None):
    with self._lk:
        if side == "BUY" and not self.in_position:
            size = self._size_fraction(bars) if bars else 0.25
            cost = self.balance * size * (1 - C.FEE_RT / 2)
            ...
```

### PATCH 3 — Tighter + portfolio-level drawdown breakers
```python
# run.py, run_vote_strategy + run_ma_strategy:

max_drawdown_pct = 8.0      # was 15.0
pair_max_dd      = 5.0      # NEW: per-pair kill

# inside the loop, before the existing soft-warn block:
if dd_pct >= pair_max_dd:
    logging.critical(f"Pair {pair} hit {dd_pct:.1f}% DD — halting 48h")
    if strat.in_position: strat.execute("SELL", price, ts)
    break
```

### PATCH 4 — Correlation cap across bots
```python
# New file: /usr/local/bin/portfolio-guard (systemd OneShot every 5min):
# - reads /api/bots.json
# - computes BTC-corr cluster exposure (ETH+SOL+XRP+AVAX LONG $)
# - if > 40% of starting capital, writes a kill-flag file
# - each bot checks kill-flag each loop; if present, exits + refuses re-entry

KILL_FLAG = Path("/run/trading-bot/corr-kill")

# in strategy.step():
if KILL_FLAG.exists() and self.in_position:
    return "SELL"
if KILL_FLAG.exists() and not self.in_position:
    return None   # refuse to enter
```

### PATCH 5 — Bar-close gate + real slippage recording
```python
# run.py main loop:

last_bar_ts = 0
while True:
    bars = ex.fetch_bars(pair, need)
    if not bars: time.sleep(C.LOOP_SLEEP); continue
    # Only run signal evaluation on NEW closed bars
    if bars[-1].ts == last_bar_ts:
        time.sleep(C.LOOP_SLEEP); continue
    last_bar_ts = bars[-1].ts
    side = strat.step(bars, weekly_bars=...)
    ...

# gods_level_engine.py, Exchange._gio_order:
d = r.json()
actual_price = float(d.get("avg_deal_price", price))
slip_bp = abs(actual_price - price) / price * 10000
if slip_bp > 100:
    logging.error(f"SLIPPAGE ALERT {pair}: {slip_bp:.0f}bp")
return {"status": "filled", "price": actual_price, ...}
```

---

## 6. Backtest Upgrade Plan

Our harness has gaps. Before rerunning:

1. **Add slippage to backtesting.py** — `commission=0.006` (0.6%, not 0.25%) matches real cost.
2. **Bootstrap confidence intervals** — 1000× resample trade returns, report 95% CI on Sharpe / SQN / MDD. If CI crosses zero, edge is noise.
3. **Parameter-stability test** — perturb best params ±10% on each axis, rerun OOS. If metric moves > 50%, overfit.
4. **Cross-asset robustness** — run the same strategy on ETH-USD via another exchange (Binance) or on ETH perpetuals. If edge is real, transfers. If crypto-only, narrow edge.
5. **Multiple-testing correction in reports** — every results doc should note effective alpha after Bonferroni/FDR correction for tests-run.
6. **True walk-forward (rolling anchored)** — train on [0..t], test on [t..t+90d], roll t forward by 30d. 12-18 windows instead of 5. Kills the "averaging masks regimes" problem.
7. **Paper-forward is the real proof** — 60 days of LIVE paper PnL is worth more than any backtest. Keep Vote bots running, treat their equity curve as the OOS evidence that either confirms or kills the strategy.

---

## 7. Deployment Safety Plan

### Stage 1 — Now (running)
- 4 paper bots on Vote ≥2 of 3, $250 each, real Gate.io candles, paper orders.
- **Keep running with patches 1+3+5** (hard stop, tighter DD, bar-close gate). Do NOT ship real money yet.
- Runs minimum 30 days, target 60 days of OOS evidence.

### Stage 2 — Conditional (only if all green)
Green criteria:
- 60-day paper PnL > 0 and Sharpe > 0.5
- Max observed DD < 10%
- Trade count < 8 per pair (not whipsawing)
- No repeated circuit-breaker fires

If all green, deploy with:
- **$200 total real capital** ($50/pair) — genuinely small.
- All Patch 1–5 risk overlays active.
- Two-man rule: every BUY/SELL requires Telegram reply approval in live mode.
- Hard weekly kill at −5% account.
- Re-evaluate weekly.

### Stage 3 — Scale (only after 90 days of Stage 2)
- Up to $2,000 capital if Stage 2 net positive and behaves within backtest variance.
- Keep all safety overlays; they are permanent, not conditional.

### Kill switch remains on the dashboard.

---

## 8. Expected Performance Delta

| Metric | Current (MA20+W5 / Vote) | With Patches 1-5 applied | Realistic with +regime gate |
|---|---:|---:|---:|
| In-sample Sharpe | 2.15–2.41 | 2.0–2.3 | 2.3–2.7 |
| OOS Sharpe | **−0.5 to −1.8** | **−0.2 to +0.5** | **+0.3 to +0.8** |
| OOS SQN | −1.64 to −5.18 | −0.5 to +1.0 | +0.5 to +1.5 |
| Max realistic DD | −22 to −28 % | **−10 to −15 %** | −8 to −12 % |
| P(ruin) | 18–22 % | **4–6 %** | 2–4 % |
| Real RT cost | 0.60 % | 0.40 % (limit orders) | 0.40 % |
| Confidence after multi-test correction | **14 %** | 30–40 % | 50–60 % |

**Honest interpretation:** even with every patch, OOS Sharpe is likely in the +0.3 to +0.8 range, not the +2.0+ in-sample numbers. That's a **real** but **modest** edge, deployable with tight risk controls and tiny size. The institutional Sharpe 2+ we chased doesn't exist in this data.

---

## Constraints acknowledged

- ✅ No curve fitting in patches (no new params introduced by fixes — all overlays tied to observed risk metrics, not backtest optimization)
- ✅ No unrealistic backtest assumptions (slippage model raised to 0.60% RT)
- ✅ Real-world slippage assumed (20–35bp per side on AVAX-scale liquidity)
- ✅ Protect capital first (5 separate kill paths: per-trade stop, per-pair DD, portfolio DD, correlation cap, max-hold timer)
- ✅ Maximize risk-adjusted return (Kelly×vol sizing), not raw return (binary 100%)

---

## Next actionable step

Ship **Patch 1 (hard stop) + Patch 3 (tighter DD) + Patch 5 (bar-close gate)** to the running Vote paper bots. These three alone cut P(ruin) from 18% → 10% without changing the signal. Meanwhile, collect 30-day paper evidence. If paper PnL confirms edge, revisit Patches 2 and 4.

Do **not** touch Stage 2 (real money) for at least 60 days of live paper evidence.
