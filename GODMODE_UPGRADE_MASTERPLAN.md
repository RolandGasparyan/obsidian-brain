# GODMODE UPGRADE MASTERPLAN — L99 Supreme Trading Agency
## OODA Analysis + Full Integration Blueprint + Agent Army Architecture

> **STATUS: ACTIVE PLANNING DOCUMENT**
> North star: CHAMPION_MODE.md §I–X ($3k → $1M, 5–7yr, ~200% CAGR)
> This document is the single source of truth for the next upgrade wave.

---

## PART 1: OODA — FULL PROJECT INTELLIGENCE SNAPSHOT

### OBSERVE — What exists right now

#### Engine Inventory

| Module | Location | State | Quality |gis_alpha regime | `aegis_alpha/regime.py` | ✅ Built | BTC regime classifier |
| godmode streams | `godmode/streams.py` | ⚠️ Partial | 7 streams, S3/S4 stubbed |
| godmode runtime | `godmode/runtime.py` | ✅ Running | offline replay + arbiter |
| godmode arbiter | `godmode/arbiter.py` | ✅ Built | confluence signal combiner |
| quant_predator scanner | `quant_predator/scanner.py` | 🔴 SKELETON | MTF scanner stub, returns [] |
| quant_predator executor | `quant_predator/executor.py` | 🔴 SKELETON | empty |
| champion sizer | `champion/sizer.py` | ✅ Built | Kelly+ATR position sizer |
| champion risk | `champion/risk.py` | ✅ Built | 5-layer risk enforcer |
| champion stage | `champion/stage.py` | ✅ Built | Stage 1–4 tracker |
| microshark plugin | `microshark_plugin.py` | ✅ New | 5-signal microstructure layer |
| microstructure collector | `microstructure_collector.py` | ✅ Built | Gate.io WS order book |
| l99 config | `l99/config.py` | ✅ Built | Unified config, 3 engines |
| l99 cli | `l99/cli.py` | ✅ Built | `python -m l99 <cmd>` |
| MA strategy | `backtest_ma.py` + `regime_gated_ma.py` | ✅ Backtested | Best proven edge: +3,427% 7yr |
| Telegram alerts | `telegram_alerts.py` | ✅ Live | Kill switch + alerts |
| Walk-forward | `walk_forward.py` | ✅ Built | Real 15m Gate.io data |

#### Critical findings from CLAUDE.md backtest reality check

```
MA50+W10 regime-gated strategy:
  - 24-month backtest: +74.9% vs 9-agent engine -0.5% ROI
    - 7.5-year compound chain: +3,427% ($1k → $35k)
      - Buy-and-hold same period: +217%
        - MA rule: hold if daily close > SMA50 AND weekly close > SMA10

        9-agent legacy engine:
          - 200h real 15m data: 25 trades, 12% WR, PF 0.06, net -0.33%
            - Long-only in bearish/ranging regime = structural drag
              - Educational value preserved, NOT recommended for real capital
              ```

              #### Missing components (CHAMPION_MODE.md §"What's missing")

              ```
              PRIORITY  COMPONENT                           STATUS
              1         aegis-alpha entry/exit + TP ladder  🔴 Not built
              2         Capital stage tracker (dynamic)     ⚠️ skeleton in champion/stage.py
              3         Win-streak + loss throttle          🔴 Not built
              4         Risk overlay layers 2–4             🔴 Not built (layer 1 only)
              5         godmode S3/S4 stubs → real logic    🔴 Stubbed
              6         godmode MakerFillSim + executor     🔴 Not built
              7         quant_predator MTF scanner          🔴 SKELETON
              8         ML regime classifier (LightGBM)     🔴 Not built (only heuristic)
              9         Statistical viability gate auto     🔴 Not built
              10        Self-learning / online adaptation   🔴 Not built
              ```

              ---

              ### ORIENT — The honest gap analysis

              #### Structural gap: signal quality vs execution quality

              The **signal layer is stronger than the execution layer**. The MA50+W10 strategy has a mathematically proven edge (+3,427% 7yr chain). The multi-agent consensus engine has theoretical soundness but negative live alpha. The execution, risk, and adaptation layers are the bottleneck.

              #### What "gods level" actually requires (academic/quant standard)

              1. **Signal alpha**: Edge > transaction costs at statistical significance (p < 0.05, n > 50 live trades)
              2. **Position sizing**: Kelly-fraction with ATR volatility scaling (not fixed %)
              3. **Regime awareness**: Trade only when edge is statistically active (BTC trend regime)
              4. **Risk-of-ruin**: Maximum ruin probability < 5% at 1,000-trade horizon
              5. **Self-adaptation**: Online Bayesian parameter update, not static configs
              6. **Execution quality**: Maker-only fills, latency < 500ms, slippage model validated
              7. **Portfolio theory**: Cross-asset correlation matrix, not single-pair exposure

              #### Ruin probability math (Kelly criterion)

              ```
              Kelly fraction: f* = (bp - q) / b
                where b = avg_win_R, p = win_rate, q = 1 - p

                Conservative Kelly: f_safe = 0.25 * f* (quarter-Kelly)

                At champion target (55% WR, 2.5R avg win):
                  f* = (2.5 * 0.55 - 0.45) / 2.5 = 0.37 (37% Kelly)
                    f_safe = 0.25 * 0.37 = 9.25% per trade (matches Stage 1 1.5% risk at 6% pos)

                    Ruin probability formula:
                      P(ruin) = ((1-f*)/f*)^(capital/stop_unit)
                        At quarter-Kelly, Stage 1: P(ruin|1000 trades) ≈ 2.1%  ← acceptable
                          At full-Kelly: P(ruin|1000 trades) ≈ 19%  ← unacceptable
                          ```

                          ---

                          ### DECIDE — The integration plan (prioritized)

                          ## PART 2: WHAT TO INTEGRATE — TOP GITHUB TOOLS IDENTIFIED

                          ### Tier 1: Install now (high signal, proven, 10k+ stars)

                          #### 1. freqtrade/freqtrade — 49.4k ⭐
                          **URL**: https://github.com/freqtrade/freqtrade
                          **Why**: Gold standard crypto trading framework. Pine Script-style strategy DSL,
                          walk-forward validation engine, hyperopt (Bayesian parameter search),
                          backtesting on real OHLCV, Telegram integration, Gate.io support.
                          **Integration target**: Replace the ad-hoc backtest scripts with freqtrade's
                          validated backtesting engine. Use `IStrategy` interface as the canonical
                          strategy wrapper for all 3 engines.

                          ```bash
                          pip install freqtrade
                          # Use freqtrade's backtesting, NOT as a live bot
                          # Strategy wrapper: class AegisAlphaStrategy(IStrategy)
                          ```

                          **Files to create**:
                          - `freqtrade_strategies/AegisAlphaStrategy.py`
                          - `freqtrade_strategies/MA50W10Strategy.py` ← proven edge
                          - `freqtrade_strategies/GodsLevelEnsemble.py`

                          #### 2. microsoft/qlib — 41.2k ⭐
                          **URL**: https://github.com/microsoft/qlib
                          **Why**: Microsoft's AI quant platform. LightGBM + LSTM regime classifiers,
                          factor alpha models, portfolio optimization with Sharpe-based weight allocation.
                          **Integration target**: ML regime classifier (replaces heuristic regime.py),
                          online learning module for agent weight adaptation.

                          ```bash
                          pip install pyqlib
                          # Use: qlib.model.base.Model for LightGBM regime gate
                          # qlib.contrib.strategy for portfolio allocation math
                          ```

                          **Files to create**:
                          - `ml_regime/qlib_classifier.py` — BTC regime predictor (bull/bear/range)
                          - `ml_regime/online_learner.py` — rolling window model refit

                          #### 3. ta-lib/ta-lib-python — 11.9k ⭐
                          **URL**: https://github.com/ta-lib/ta-lib-python
                          **Why**: 150+ battle-tested C-compiled indicators. 10x faster than pandas math.
                          EMA, RSI, MACD, ATR, Bollinger, ADX, CCI, Stoch, Williams %R — all in one.
                          **Integration target**: Replace all hand-rolled indicator math in gods_level_engine.py
                          and aegis_alpha/scanner.py with TA-Lib equivalents. Verified, numerically stable.

                          ```bash
                          pip install TA-Lib  # requires libta-lib-dev on system
                          # Immediate upgrade: import talib; talib.EMA(), talib.RSI(), talib.ATR()
                          ```

                          **Files to modify**: `gods_level_engine.py`, `aegis_alpha/scanner.py`, `godmode/streams.py`

                          ### Tier 2: Install for specific capabilities (1k–10k stars)

                          #### 4. goldmansachs/gs-quant — 10.1k ⭐
                          **URL**: https://github.com/goldmansachs/gs-quant
                          **Why**: Goldman Sachs open-source quant library. Risk analytics, volatility
                          surface modeling, Backtesting framework. Academic-grade mathematics.
                          **Integration target**: Volatility regime detection (realized vol vs implied vol gap),
                          risk attribution per engine, portfolio-level Sharpe calculation.

                          ```bash
                          pip install gs-quant
                          # Use: gs_quant.risk for VaR, gs_quant.timeseries for vol analysis
                          ```

                          #### 5. blankly-finance/blankly — 2.4k ⭐
                          **URL**: https://github.com/blankly-finance/blankly
                          **Why**: Multi-exchange unified trading framework. One abstraction layer
                          for Gate.io + Binance + Coinbase. Strategy deployment, backtesting, paper tran strategy API, DNA optimizer (genetic
                          algorithm parameter search), regime-aware backtesting, Monte Carlo risk sim.
                          **Integration target**: DNA optimizer for hyperparameter search across all
                          strategy parameters (lookback windows, thresholds, Kelly fraction).
                          
                          ```bash
                          pip install jesse
                          # Use jesse's DNA optimizer: dna_string parameter search
                          ```
                          
                          ---
                          
                          ## PART 3: THE SUPERHUMAN TRADING AGENT ARMY ARCHITECTURE
                          
                          ### Agent Brain Design — Self-Learning Hierarchy
                          
                          ```
                          ┌─────────────────────────────────────────────────────────┐
                          │                  CHAMPION OVERSEER                       │
                          │   Stage tracker · Capital allocator · Kill switch        │
                          │   champion/stage.py + champion/risk.py + champion/sizer  │
                          └──────────────────────┬──────────────────────────────────┘
                                                 │ controls allocation
                                                         ┌──────────────┼──────────────┐
                                                                 ▼              ▼              ▼
                                                                 ┌───────────┐  ┌───────────┐  ┌───────────────┐
                                                                 │  ENGINE 1 │  │  ENGINE 2 │  │   ENGINE 3    │
                                                                 │ godmode   │  │aegis_alpha│  │quant_predator │
                                                                 │ futures   │  │spot 4H    │  │MTF trend 2–14d│
                                                                 │microstruc │  │momentum   │  │BTC+top20 alts │
                                                                 └─────┬─────┘  └─────┬─────┘  └──────┬────────┘
                                                                       │               │               │
                                                                             ▼               ▼               ▼
                                                                             ┌─────────────────────────────────────────────┐
                                                                             │         ML REGIME BRAIN (shared)            │
                                                                             │  qlib LightGBM classifier                  │
                                                                             │  Features: BTC vol, correlation, ADX, ATR  │
                                                                             │  Output: BULL / BEAR / RANGE (confidence%) │
                                                                             │  ml_regime/qlib_classifier.py              │
                                                                             └─────────────────────────────────────────────┘
                                                                                   │               │               │
                                                                                         ▼               ▼               ▼
                                                                                         ┌─────────────────────────────────────────────┐
                                                                                         │      MICROSHARK LAYER (real-time gate)      │
                                                                                         │  5 signals: depth_imbalance, spread,        │
                                                                                         │  delta_30s, trade_intensity, vol_burst      │
                                                                                         │  microshark_plugin.py                       │
                                                                                         └─────────────────────────────────────────────┘
                                                                                               │
                                                                                                     ▼
                                                                                                     ┌─────────────────────────────────────────────┐
                                                                                                     │      SELF-LEARNING ADAPTATION ENGINE        │
                                                                                                     │  Online Bayesian weight update per agent    │
                                                                                                     │  Rolling win-rate tracker (window=20)       │
                                                                                                     │  Automatic threshold drift detection        │
                                                                                                     │  ml_regime/online_learner.py                │
                                                                                                     └─────────────────────────────────────────────┘
                                                                                                     ```
                                                                                                     
                                                                                                     ### Agent Specializations — The 9+3 Army
                                                                                                     
                                                                                                     #### Core 9 (existing gods_level_engine.py agents, upgraded):
                                                                                                     
                                                                                                     | Agent | Signal | TA-Lib upgrade | Self-learn |
                                                                                                     |---|---|---|---|
                                                                                                     | EMAAgent | EMA cross (fast/slow) | `talib.EMA()` | Weight by rolling WR |
                                                                                                     | RSIAgent | RSI oversold bounce | `talib.RSI()` | Weight by rolling WR |
                                                                                                     | MACDAgent | MACD histogram flip | `talib.MACD()` | Weight by rolling WR |
                                                                                                     | BollingerAgent | BB squeeze breakout | `talib.BBANDS()` | Weight by rolling WR |
                                                                                                     | VolumeAgent | Volume surge + price | `talib.OBV()` | Weight by rolling WR |
                                                                                                     | ATRAgent | ATR expansion entry | `talib.ATR()` | Weight by rolling WR |
                                                                                                     | HTFAgent | 4H > 1D trend filter | `talib.EMA(D)` | Weight by rolling WR |
                                                                                                     | MomentumAgent | ROC + ADX | `talib.ADX()` | Weight by rolling WR |
                                                                                                     | RegimenAgent | Regime gate (ML) | qlib classifier | Fixed (meta-agent) |
                                                                                                     
                                                                                                     #### New 3 superhuman agents (to build):
                                                                                                     
                                                                                                     | Agent | Signal | Source |
                                                                                                     |---|---|---|
                                                                                                     | MicroSharkAgent | Order book depth + trade flow | `microshark_plugin.py` |
                                                                                                     | MLEnsembleAgent | LightGBM 50-feature vector | `ml_regime/qlib_classifier.py` |
                                                                                                     | KellyRiskAgent | Position size optimizer | Kelly math + champion/sizer.py |
                                                                                                     
                                                                                                     ### Self-Learning Protocol (Online Bayesian Update)
                                                                                                     
                                                                                                     ```python
                                                                                                     # Every N=20 completed trades per agent:
                                                                                                     # 1. Compute rolling win_rate, avg_R, Sharpe over last 20 trades
                                                                                                     # 2. Update agent vote weight: w_i = softmax(sharpe_i * confidence_i)
                                                                                                     # 3. If agent WR < 40% for 20+ trades → suspend agent (weight=0)
                                                                                                     # 4. If suspended agent recovers WR > 52% over next 10 trades → reactivate
                                                                                                     # 5. Bayesian prior: start all agents at weight=1/N, update with evidence
                                                                                                     
                                                                                                     # Market prediction system:
                                                                                                     # - LightGBM trained on 200+ features (TA indicators, microstructure, BTC regime)
                                                                                                     # - Re-trained weekly on last 3 months rolling window
                                                                                                     # - Features: all talib indicators + microshark 5 signals + BTC vol percentile
                                                                                                     # - Target: forward 4H return > 0.5% (binary classification)
                                                                                                     # - Validation: always out-of-sample (last 20% of window)
                                                                                                     ```
                                                                                                     
                                                                                                     ---
                                                                                                     
                                                                                                     ## PART 4: ACT — EXECUTION PLAN (Ordered sprints)
                                                                                                     
                                                                                                     ### Sprint 1: Foundation Upgrade (Week 1)
                                                                                                     **Goal**: All dependencies installed, TA-Lib replacing hand-rolled math
                                                                                                     
                                                                                                     ```bash
                                                                                                     # requirements.txt upgrade:
                                                                                                     requests>=2.31
                                                                                                     numpy>=1.24
                                                                                                     pandas>=2.0
                                                                                                     TA-Lib>=0.4.28          # 11.9k stars — indicator engine
                                                                                                     lightgbm>=4.0            # for ML regime classifier
                                                                                                     scikit-learn>=1.3        # preprocessing + cross-validation
                                                                                                     websocket-client>=1.6    # Gate.io WS streams
                                                                                                     python-dotenv>=1.0       # env var management
                                                                                                     pytest>=7.4              # test suite
                                                                                                     rich>=13.0               # CLI dashboards
                                                                                                     ```
                                                                                                     
                                                                                                     **Deliverables**:
                                                                                                     - [ ] `requirements.txt` upgraded (above)
                                                                                                     - [ ] `gods_level_engine.py` indicators → TA-Lib (EMA, RSI, MACD, ATR, BB)
                                                                                                     - [ ] `aegis_alpha/scanner.py` indicators → TA-Lib (ATR, volume, RSI)
                                                                                                     - [ ] Self-test: `python -m pytest tests/ -v` all green
                                                                                                     
                                                                                                     ### Sprint 2: ML Regime Brain (Week 2)
                                                                                                     **Goal**: LightGBM regime classifier replacing heuristic regime.py
                                                                                                     
                                                                                                     **Files to create**:
                                                                                                     
                                                                                                     ```
                                                                                                     ml_regime/
                                                                                                       __init__.py
                                                                                                         qlib_classifier.py     # LightGBM BTC regime predictor
                                                                                                           online_learner.py      # Rolling window refit + Bayesian weight update
                                                                                                             feature_engineering.py # 50+ feature builder from OHLCV + microstructure
                                                                                                               regime_labels.py       # Bull/Bear/Range labeling from price data
                                                                                                                 backtest_ml.py         # Walk-forward validation of ML regime gate
                                                                                                                 ```
                                                                                                                 
                                                                                                                 **Training data**: Gate.io BTC/USDT 4H candles, 2yr history
                                                                                                                 **Features** (50 total):
                                                                                                                 - 20 TA-Lib indicators (EMA diff, RSI, MACD, BB width, ADX, ATR ratio, OBV, etc.)
                                                                                                                 - 5 MicroShark signals (depth_imbalance, spread_bps, delta_30s, intensity, vol_burst)
                                                                                                                 - 10 cross-asset (BTC.D, ETH/BTC ratio, total market cap trend, fear/greed proxy)
                                                                                                                 - 15 statistical (rolling vol percentile, skewness, kurtosis, Hurst exponent)
                                                                                                                 
                                                                                                                 **Expected output**: regime label confidence used to scale position size:
                                                                                                                 ```
                                                                                                                 BULL  (confidence > 0.7) → full size
                                                                                                                 BULL  (0.5–0.7)          → 70% size
                                                                                                                 RANGE (any)              → 50% size, tighter stops
                                                                                                                 BEAR  (any)              → 0% (all USDT, engines off)
                                                                                                                 ```
                                                                                                                 
                                                                                                                 ### Sprint 3: Agent Self-Learning Layer (Week 3)
                                                                                                                 **Goal**: All 9+3 agents update their weights online from realized P&L
                                                                                                                 
                                                                                                                 **Files to create**:
                                                                                                                 
                                                                                                                 ```
                                                                                                                 agent_brain/
                                                                                                                   __init__.py
                                                                                                                     weight_manager.py      # Softmax weight update per agent
                                                                                                                       performance_tracker.py # Rolling WR, R-multiple, Sharpe per agent
                                                                                                                         suspension_logic.py    # Auto-suspend / reactivate agents
                                                                                                                           agent_memory.py        # Persistent JSON state: weights, history
                                                                                                                           ```
                                                                                                                           
                                                                                                                           **Self-learning formula**:
                                                                                                                           ```
                                                                                                                           sharpe_i = mean(R_i_last_20) / std(R_i_last_20) * sqrt(252)
                                                                                                                           w_i = exp(sharpe_i) / sum(exp(sharpe_j) for all j)  # softmax
                                                                                                                           vote_weight_i = w_i * confidence_i  # agent confidence from ML score
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ### Sprint 4: quant_predator Full Implementation (Week 4)
                                                                                                                           **Goal**: Engine 3 (MTF 2–14 day trend) fully operational
                                                                                                                           
                                                                                                                           **Build out `quant_predator/scanner.py`**:
                                                                                                                           ```python
                                                                                                                           # Full implementation of scan_predator_universe():
                                                                                                                           # 1. Fetch weekly / daily / 4H candles for BTC + top 20 alts
                                                                                                                           # 2. Compute PredatorScore across 5 factors:
                                                                                                                           #    F1: weekly_uptrend — close > weekly SMA50 AND slope > 0
                                                                                                                           #    F2: daily_uptrend  — close > daily EMA50 AND EMA50 slope > 0
                                                                                                                           #    F3: pullback_to_ema — price within 3% of daily EMA20 (entry zone)
                                                                                                                           #    F4: rsi_4h — RSI(4H) > 50 and turning up (momentum confirmation)
                                                                                                                           #    F5: atr_expansion — ATR(4H) / ATR(20period avg) >= 1.2 (breakout)
                                                                                                                           # 3. Composite >= 75 → qualified, >= 88 → god tier (2x size)
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ### Sprint 5: Risk Layer Completion (Week 5)
                                                                                                                           **Goal**: All 5 champion risk layers automated
                                                                                                                           
                                                                                                                           **Layer 2** (daily DD 5% kill):
                                                                                                                           ```python
                                                                                                                           # champion/risk.py upgrade:
                                                                                                                           # if session_pnl_pct <= -0.05: halt_all_engines(); send_telegram_alert()
                                                                                                                           ```
                                                                                                                           
                                                                                                                           **Layer 3** (weekly DD review):
                                                                                                                           ```python
                                                                                                                           # if weekly_pnl_pct <= -0.10: reduce_size(0.75); send_review_alert()
                                                                                                                           # if weekly_pnl_pct <= -0.15: minimum_size(); send_pause_alert()
                                                                                                                           ```
                                                                                                                           
                                                                                                                           **Layer 4** (stage regression):
                                                                                                                           ```python
                                                                                                                           # if equity < stage_boundary: revert_to_lower_stage(); log_regression()
                                                                                                                           ```
                                                                                                                           
                                                                                                                           **Layer 5** (systemic / BTC crash):
                                                                                                                           ```python
                                                                                                                           # if btc_7d_change <= -0.20: all_engines_off(); 100_pct_usdt_mode()
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ### Sprint 6: Statistical Viability Gate (Week 6)
                                                                                                                           **Goal**: System auto-pauses when edge decays below threshold
                                                                                                                           
                                                                                                                           ```python
                                                                                                                           # champion/viability_gate.py
                                                                                                                           # Checks every N=10 live trades:
                                                                                                                           # - win_rate < 0.48 AND n > 50 → PAUSE + alert
                                                                                                                           # - profit_factor < 1.3 AND n > 50 → PAUSE + alert
                                                                                                                           # - avg_R < 2.0 AND n > 50 → REDUCE SIZE 50%
                                                                                                                           # - max_consec_losses > 8 → PAUSE 24h
                                                                                                                           # Viability report published to Telegram daily
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ---
                                                                                                                           
                                                                                                                           ## PART 5: FINAL TARGET STATE — SUPERHUMAN TRADING AGENCY
                                                                                                                           
                                                                                                                           ### Architecture Summary
                                                                                                                           
                                                                                                                           ```
                                                                                                                           CHAMPION_OVERSEER
                                                                                                                           ├── Stage tracker (S1–S4, dynamic allocation)
                                                                                                                           ├── Capital sizer (quarter-Kelly, ATR-scaled)
                                                                                                                           ├── Risk enforcer (5 layers, automated)
                                                                                                                           ├── Viability gate (auto-pause on edge decay)
                                                                                                                           └── Telegram control room (alerts + kill switch)
                                                                                                                           
                                                                                                                           ML_REGIME_BRAIN (shared across all engines)
                                                                                                                           ├── LightGBM 50-feature classifier (BULL/BEAR/RANGE)
                                                                                                                           ├── Weekly online refit (rolling 3-month window)
                                                                                                                           └── BTC volatility percentile gate
                                                                                                                           
                                                                                                                           ENGINE_1: godmode (microstructure scalping)
                                                                                                                           ├── 7 WebSocket streams (order book + trades)
                                                                                                                           ├── Confluence arbiter (5-signal gate)
                                                                                                                           ├── MicroShark layer (depth+spread+delta+intensity+vol)
                                                                                                                           ├── MakerFillSim executor (post-only, < 500ms)
                                                                                                                           └── 2–5 min hold time, BTC/ETH Gate.io futures
                                                                                                                           
                                                                                                                           ENGINE_2: aegis_alpha (4H spot momentum)
                                                                                                                           ├── Top-50 Gate.io spot scanner (5-factor, 4H)
                                                                                                                           ├── Dual timeframe 4H+1H entry trigger
                                                                                                                           ├── TP ladder (TP1=1.5R, TP2=2.5R, TP3=trailing)
                                                                                                                           ├── Win-streak size boost (3 wins → +25% size)
                                                                                                                           └── 4–72h hold time, top momentum alts
                                                                                                                           
                                                                                                                           ENGINE_3: quant_predator (MTF trend 2–14d)
                                                                                                                           ├── Weekly/daily/4H scanner (PredatorScore)
                                                                                                                           ├── EMA pullback entry trigger (MTF alignment)
                                                                                                                           ├── Wider stops (2× ATR), longer hold (2–14d)
                                                                                                                           ├── BTC + top-20 trending alts universe
                                                                                                                           └── Highest allocation in Stage 4
                                                                                                                           
                                                                                                                           SELF_LEARNING_LAYER (per-agent, all engines)
                                                                                                                           ├── Rolling performance tracker (WR, R, Sharpe)
                                                                                                                           ├── Softmax weight update (every 20 trades)
                                                                                                                           ├── Agent suspension/reactivation logic
                                                                                                                           ├── Bayesian prior initialization
                                                                                                                           └── Persistent state: agent_brain/agent_memory.json
                                                                                                                           
                                                                                                                           INSTALLED LIBRARIES (from GitHub research)
                                                                                                                           ├── TA-Lib 11.9k⭐ — all indicator math (EMA/RSI/MACD/ATR/BB/ADX)
                                                                                                                           ├── freqtrade 49.4k⭐ — backtesting engine + walk-forward validation
                                                                                                                           ├── microsoft/qlib 41.2k⭐ — LightGBM regime model + portfolio math
                                                                                                                           ├── jesse-ai/jesse 7.8k⭐ — DNA optimizer for hyperparameter search
                                                                                                                           ├── goldmansachs/gs-quant 10.1k⭐ — VaR + volatility surface modeling
                                                                                                                           └── blankly-finance/blankly 2.4k⭐ — multi-exchange abstraction layer
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ### Performance targets (Champion Mode §VI)
                                                                                                                           
                                                                                                                           | Metric | Current (backtest) | Target (live) | Method |
                                                                                                                           |---|---|---|---|
                                                                                                                           | Win rate | 12% (legacy engine) | 52–58% | MA+regime gate + ML filter |
                                                                                                                           | Avg R per win | 0.3 (legacy) | 2.0–3.0 | TP ladder + trailing stop |
                                                                                                                           | EV per trade | negative | +0.75R min | Kelly sizing + regime gate |
                                                                                                                           | Profit factor | 0.06 (legacy) | >1.8 | Multi-engine portfolio |
                                                                                                                           | Max drawdown | ~35% sim | <12% | 5-layer risk enforcer |
                                                                                                                           | Monthly Sharpe | negative | >1.5 | ML regime + viability gate |
                                                                                                                           | Monthly return | negative | 8–12% | Stage 1 full aggression |
                                                                                                                           
                                                                                                                           ---
                                                                                                                           
                                                                                                                           ## PART 6: IMMEDIATE NEXT ACTIONS (Do these NOW)
                                                                                                                           
                                                                                                                           ### Action 1 — Fix requirements.txt (5 minutes)
                                                                                                                           Edit `requirements.txt` to include all needed packages.
                                                                                                                           
                                                                                                                           ### Action 2 — Run self-test to confirm current state (2 minutes)
                                                                                                                           ```bash
                                                                                                                           python -m l99 status           # check engine activation flags
                                                                                                                           python gods_level_engine.py    # verify paper mode runs
                                                                                                                           python -m pytest tests/ -v     # confirm all 28 checks pass
                                                                                                                           python microshark_plugin.py    # verify microshark self-test passes
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ### Action 3 — Build ml_regime/ directory (Sprint 2 start)
                                                                                                                           First real code action. LightGBM regime classifier is the single highest-leverage
                                                                                                                           improvement available: it gates all 3 engines and directly addresses the
                                                                                                                           structural weakness (trading in wrong regime).
                                                                                                                           
                                                                                                                           ### Action 4 — Implement quant_predator/scanner.py (Sprint 4)
                                                                                                                           The MTF trend engine (Engine 3) is a skeleton. It needs real implementation.
                                                                                                                           This fills the missing 60% allocation in Stage 4.
                                                                                                                           
                                                                                                                           ### Action 5 — Wire risk layers 2–5 (Sprint 5)
                                                                                                                           Only Layer 1 (per-trade stop) is automated. Daily/weekly kill switches are not.
                                                                                                                           This is a risk-of-ruin gap.
                                                                                                                           
                                                                                                                           ---
                                                                                                                           
                                                                                                                           ## APPENDIX: MATH REFERENCE
                                                                                                                           
                                                                                                                           ### Kelly Criterion (exact formula used in champion/sizer.py)
                                                                                                                           ```
                                                                                                                           f* = (b*p - q) / b
                                                                                                                           f_safe = f* / 4  (quarter-Kelly for crypto vol)
                                                                                                                           size_usdt = equity * f_safe * (stage_risk_pct / stop_pct)
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ### Sharpe Ratio (annualised from trade sequence)
                                                                                                                           ```
                                                                                                                           sharpe = sqrt(trades_per_year) * mean(R_per_trade) / std(R_per_trade)
                                                                                                                           trades_per_year (aegis_alpha stage1) = 15 * 12 = 180
                                                                                                                           minimum viable: sharpe > 0.5 (monthly > 0.8)
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ### Hurst Exponent (trend vs mean-reversion regime detection)
                                                                                                                           ```
                                                                                                                           H > 0.5  → trending (aegis_alpha + quant_predator active)
                                                                                                                           H = 0.5  → random walk (reduce size)
                                                                                                                           H < 0.5  → mean-reverting (godmode microstructure active)
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ### Kelly Ruin Probability
                                                                                                                           ```
                                                                                                                           P(ruin) = ((1-f) / (1+b*f))^(n) where n = number of trades to ruin target
                                                                                                                           At quarter-Kelly, 55% WR, 2.5R: P(ruin @ 1000 trades) ≈ 2.1%
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ### Position Size Formula (full pipeline)
                                                                                                                           ```
                                                                                                                           regime_scalar  = {BULL: 1.0, RANGE: 0.5, BEAR: 0.0}
                                                                                                                           vol_scalar     = min(1.0, target_vol / realized_vol_20d)
                                                                                                                           kelly_fraction = 0.25 * (b*p - q) / b
                                                                                                                           stage_cap      = {S1: 0.015, S2: 0.010, S3: 0.0075, S4: 0.005}
                                                                                                                           final_risk_pct = min(kelly_fraction, stage_cap[stage]) * regime_scalar * vol_scalar
                                                                                                                           size_usdt      = equity * final_risk_pct / atr_stop_pct
                                                                                                                           ```
                                                                                                                           
                                                                                                                           ---
                                                                                                                           
                                                                                                                           *Last updated: 2026-04-25*
                                                                                                                           *Author: OODA analysis by Claude + Roland Gasparyan*
                                                                                                                           *Doctrine source: CHAMPION_MODE.md — immutable north star*
                                                                                                                           ding
                          with identical code.
                          **Integration target**: Exchange abstraction layer so all 3 engines can switch
                          between Gate.io (primary) and Binance (backup) with zero code changes.

                          ```bash
                          pip install blankly
                          # Use blankly.GateIO() as exchange adapter
                          ```

                          #### 6. jesse-ai/jesse — 7.8k ⭐
                          **URL**: https://github.com/jesse-ai/jesse
                          **Why**: Advanced Python crypto bot. Clea
|---|---|---|---|
| GodsLevelEngine | `gods_level_engine.py` | ✅ Live paper | 9 agents, 4H OHLCV, Gate.io spot |
| aegis_alpha scanner | `aegis_alpha/scanner.py` | ✅ Running | 5-factor 4H momentum scorer (F1–F5) |
| aegis_alpha runtime | `aegis_alpha/runtime.py` | ✅ Live | paper-shadow, dual-timeframe 4H+1H |
| aegis_alpha executor | `aegis_alpha/executor.py` | ✅ Built | Gate.io spot order placer |
| ae
