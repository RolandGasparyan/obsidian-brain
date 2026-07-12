# OFI Final Verdict

**Strategy:** Order Flow Imbalance ("Agent Zeta", "TOP #1 Winning Setup")
**Decision:** **NO-GO for live deploy.**
**Date:** 2026-05-29
**Branch:** `claude/trading-guru-metaworld-B2WFx` (PR #75)

## Evidence

All four gates implemented in `orderflow_validate.py`. Reproduce with `python orderflow_validate.py`.

| Gate | Result |
|---|---|
| Fee sweep | Net-negative even at **0% fee**. Per-trade gross edge is roughly 10–30× below realistic round-trip taker fees on Gate.io spot. |
| A — Walk-forward (3 segments, fees on) | **0 / 3** segments net-positive. |
| B — Monte-Carlo permutation (300 shuffles) | Real result beats **0.0%** of shuffled-noise runs. Verdict: **indistinguishable from noise.** |
| C — Report internal consistency | **5 / 6** of the report's own arithmetic checks FAIL. |

### Gate C specifics — the report's own numbers do not tie out
- Headline trade count `31,978` vs body `4,005` — ~8× gap.
- Exit-table PnL sum `$144.96` vs stated total `$136.31`.
- PF implied by the stated grosses = `1.10`, not the stated `1.05`.
- Expectancy from stated WR × avg-win + (1−WR) × avg-loss = `+$0.0115/trade`, not the claimed `+$0.034/trade`.
- Stop-loss row implies `−$6.35` per SL trade vs stated avg loss of `−$0.33`.

## Sample limitation, honestly stated

The in-session backtest used 300 bars of real Binance 1m data (3 tokens × 100 bars). That is a small window. **However:**

- The fee-vs-edge math is sample-independent. The report's own per-trade edge of `+$0.034` is far smaller than any plausible round-trip fee on the position sizes implied by Kelly 0.375.
- The Monte-Carlo result is sample-independent for what it tests: the entry logic carries no information advantage over shuffled returns on this window.
- The report-consistency failures are arithmetic, not statistical.

A definitive large-sample re-run is a single command on the VPS where Gate.io is reachable:

```
python orderflow_validate.py --live      # 1000 1m bars/pair from Gate.io
```

## The unrun test that could change the verdict

Ledger reconciliation. The cloud engine at `34.139.162.200:8080` presumably has the raw 4,005 (or 31,978) trades. Export them and run:

```
python orderflow_validate.py --ledger trades.csv
```

This recomputes every metric from the raw trades, reconciles them against the report's headline claims, reproduces the exit-method table, and applies a fee sweep on the real notionals. If the engine's record is real, the numbers will tie out and the verdict can be revisited. Until then, the report is a claim, not evidence.

## What this verdict means

This document does not say "don't trade." It says: **do not deploy this specific strategy on this evidence.** The repo's own `CLAUDE.md` already records a different candidate with measured positive evidence — the MA50 + weekly SMA10 rule (`--strategy ma50w10`) returned +74.9% over 24 months on real BTC data and +3,427% across the 7.5-year regime-sample chain. If a strategy is going to risk real money, that one is the only one in this repo with measured edge after the same kind of scrutiny.

## Gate the deploy

`CLAUDE.md` already specifies the gate: live mode requires `CONFIRM LIVE TRADING` typed by the operator, after a regime re-test. Removing the halt files (`CANARY_HALT.json`, `protection_halt.json`) does not satisfy the gate — it bypasses it.

## Sign-off

Verification work is complete on `claude/trading-guru-metaworld-B2WFx`:

- `accounts.py` — paper-safe multi-account registry (main + 2 subs), 11 unit tests pass.
- `orderflow_validate.py` — fee sweep, walk-forward, Monte-Carlo, report-consistency audit, `--live` and `--ledger` modes.
- `tests/test_accounts.py` — 11/11 pass.

Companion PR #76 fixes four pre-existing compile errors on `main` (`gods_level_strategy_logic.py`, `setup2_sniper.py`, `trading_engine.py`, `factor_research_harness.py`).

The next step is the operator's, not the assistant's: export the ledger, or accept the verdict.
