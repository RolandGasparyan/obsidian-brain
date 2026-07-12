## Summary

<!-- Describe the change in 1-2 sentences -->

## Type

- [ ] Bug fix
- [ ] Infrastructure / tooling
- [ ] Documentation
- [ ] Strategy change ← requires full stress re-run + tag

## Pre-Merge Checklist

- [ ] No parameter changes (`config.py` signal params untouched)
- [ ] No risk rule changes (`KILL_DD_ABS`, `KILL_CONSEC_LOSS`, `KILL_SHARPE_MIN`)
- [ ] No `LIVE_TRADING` flag changes
- [ ] Preflight still 22/22 (`python preflight.py`)
- [ ] CI pipeline green
- [ ] No secrets or credentials added
- [ ] Documentation updated if behaviour changed

## If strategy file touched (`signal_engine.py`, `risk_monitor.py`, `live_bot.py`, `config.py`)

- [ ] Separate feature branch used
- [ ] Stress test re-run completed
- [ ] Walk-forward validation completed
- [ ] Monte Carlo validation completed
- [ ] Tagged before merge (`git tag vX.Y-<milestone>`)
