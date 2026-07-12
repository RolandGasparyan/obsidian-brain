# Tournament Package - Integration Guide

## Install

Drop the `tournament/` directory into `trading_guru/trading_guru/` so the import
path is `trading_guru.tournament`. No new dependencies beyond what the engine
already uses (`numpy`, stdlib).

```
trading_guru/
└── trading_guru/
    ├── config/
    ├── decision/
    ├── core/
    ├── execution_engine.py   # untouched
    ├── guardian.py           # untouched
    ├── sizer.py              # untouched
    ├── fusion_brain.py       # minor additions (below)
    └── tournament/           # <-- new
        ├── __init__.py
        ├── brain.py
        ├── usdt_domination_core.py
        ├── champion_momentum_engine.py
        ├── performance_oracle.py
        ├── capital_phase_manager.py
        ├── tournament_risk_controller.py
        ├── edge_decay_detector.py
        └── volatility_expansion_detector.py
```

## Wiring

### 1. `launch.py` — instantiate the brain once

```python
from trading_guru.tournament import TournamentBrain

# somewhere in your startup, after loading config:
tournament_brain = TournamentBrain(
    starting_usdt=config.starting_balance_usdt,
    base_score_threshold=62.0,       # tune after paper-trade calibration
    performance_window=200,
    edge_review_every=50,
)
# hand it to fusion_brain (or stash on app state)
fusion_brain.attach_tournament(tournament_brain)

# add to your existing 24h timer loop:
async def daily_phase_tick():
    while True:
        await asyncio.sleep(24 * 3600)
        tournament_brain.on_daily_tick()
```

### 2. `fusion_brain.py` — call the tournament brain inside evaluation

```python
from trading_guru.tournament import CandidateFeatures

class FusionBrain:
    def attach_tournament(self, brain):
        self._tb = brain

    async def evaluate_candidate(self, pair, ohlcv, signals):
        # existing signal computation...
        features = CandidateFeatures(
            pair=pair,
            roc_pct=signals.roc_5m,
            ema_stack_score=signals.ema_alignment,
            rsi=signals.rsi,
            rel_volume=signals.volume_ratio,
            regime_fit=signals.regime_confidence,
            taker_buy_ratio=signals.taker_buy_ratio,
            book_imbalance=signals.book_imbalance,
            cvd_slope_z=signals.cvd_z,
            ml_long_prob=signals.ml_prob,
            atr_pct=signals.atr_pct,
            proposed_rr=signals.rr,
        )
        decision = self._tb.evaluate_entry(
            features=features,
            ohlcv=ohlcv,
            open_positions=self.trade_manager.open_count(),
            realized_pnl_today_usdt=self.trade_manager.realized_today_usdt(),
        )
        log.info("fusion.tournament %s", decision.to_log_dict())
        return decision
```

### 3. `decision_pipeline.py` — add Gate 5 (Tournament)

Insert AFTER your existing 3c/3d gates, BEFORE sizing:

```python
brain_decision = await fusion.evaluate_candidate(pair, ohlcv, signals)
if not brain_decision.allow:
    return Reject(gate="G5_TOURNAMENT", reason=brain_decision.reason,
                  score=brain_decision.composite_score,
                  threshold=brain_decision.effective_threshold)

# pass the multiplier to sizer WITHOUT touching sizer code:
proposed_size *= brain_decision.recommended_risk_multiplier
```

### 4. `trade_manager.py` — callback hooks (read-only)

Since trade_manager is untouchable for strategy changes, wire via event bus
or a simple post-fill callback list:

```python
# wherever trade_manager finalizes a fill:
event = TradeEvent(
    trade_id=trade.id, pair=trade.pair, side=trade.side,
    entry_usdt=trade.entry_notional_usdt,
    exit_usdt=trade.exit_notional_usdt,
    realized_pnl_usdt=trade.realized_pnl_usdt,
    fees_usdt=trade.fees_usdt,
    opened_ts=trade.opened_ts, closed_ts=trade.closed_ts,
)
# fire-and-forget notification
for cb in trade_manager.on_fill_callbacks:
    cb(event)

# in launch.py:
trade_manager.on_fill_callbacks.append(tournament_brain.on_trade_closed)
trade_manager.on_deploy_callbacks.append(tournament_brain.on_trade_deployed)
```

## Dashboard / telemetry

`trading-ops` can poll `tournament_brain.telemetry()` via the existing FastAPI
control server. Suggested endpoint:

```python
@app.get("/tournament/telemetry")
async def tournament_telemetry():
    return tournament_brain.telemetry()
```

Returns equity, growth multiple, phase, expectancy, sharpe, rotation velocity,
edge decay status — everything the dashboard needs for the championship view.

## Mode config addition

In `config/modes.py`, add a `tournament` mode (or enable inside `spot_champion`):

```python
TOURNAMENT_MODE = ModeConfig(
    name="tournament",
    pairs=SPOT_KING_PAIRS,                # BTC/ETH/SOL/BNB
    use_tournament_brain=True,
    base_score_threshold=62.0,
    max_concurrent_trades=2,
    guardian_halt_drawdown=0.08,          # still active, below tournament hard cap
)
```

## Paper-trade qualification

Before flipping `./live_switch.sh YES` under tournament mode, run:

1. Minimum 50 paper trades (oracle's default edge-review trigger).
2. Verify `edge` in telemetry is `HEALTHY`.
3. Win rate ≥ 55%, expectancy_r ≥ 0.25, max_dd ≤ 6%.
4. Rotation velocity > 0 (edge per hour is positive).

Only then promote.

## What's NOT in this package (by design)

- No changes to `execution_engine`, `trade_manager`, `guardian`, `sizer`,
  `gate_client` — per your rules.
- No new WebSocket connections (reuses whatever `gate_client` already streams).
- No ML model training — `ml_long_prob` is an input, not produced here.
- No pair discovery — works with whatever `pair_scorer` feeds in.

## Known calibration TODOs

- `VolatilityExpansionDetector` thresholds (0.25 compressed, 0.8 expanded,
  slope/atr/volume cutoffs) need real-data tuning. Synthetic smoke test
  classifies aggressive synthetic expansion as NEUTRAL — intentional
  conservatism, but verify on BTC 1m bars across a few volatility regimes.
- `ChampionMomentumEngine` default weights are a starting point. After 200
  tournament-mode paper trades, consider fitting weights via logistic
  regression on outcome = win.
- `PerformanceOracle.threshold()` clamps delta to [-6, +15]. If you see the
  system stuck at the ceiling, loosen; if it flaps, tighten.
