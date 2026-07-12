# Tournament AI Bot

Tournament-grade autonomous spot trading engine for Gate.io USDT markets.

## Structure

This repository contains the `tournament/` extension package for the Trading Guru
engine. Drop it into your `trading_guru/trading_guru/` directory.

## Modules

- `aggression_matrix.py` - Dynamic Aggression Control Matrix (pure logic)
- `aggression_scaler.py` - Velocity-tied aggression multiplier
- `brain.py` - Composition root, single entrypoint for fusion_brain
- `calibrate_volatility.py` - Offline detector calibration CLI
- `capital_phase_manager.py` - Early/Mid/Endgame phase directives
- `champion_momentum_engine.py` - Weighted composite scorer
- `edge_decay_detector.py` - Welch's t-test edge decay detection
- `loss_cluster_breaker.py` - Phase-aware loss cluster circuit breaker
- `performance_oracle.py` - Rolling stats + adaptive threshold
- `tournament_risk_controller.py` - Top-level entry veto
- `usdt_domination_core.py` - USDT ledger with rotation/growth tracking
- `volatility_expansion_detector.py` - Per-pair BB percentile + phase-aware thresholds

See `tournament/INTEGRATION.md` for wiring.

## Safety

- Spot only. No leverage. No margin. No futures.
- All trades end in USDT.
- Hard drawdown cap of 15% from starting capital.
- Deterministic aggression matrix with verified invariants.

## Status

Paper-mode qualification required before live trading.
