# 2026-05-03 — Stage 2 transition spec (4-gate criteria + tooling)

**Type:** decision
**Status:** decided · live deployment requires explicit operator action with CONFIRM LIVE TRADING input
**Linked log entry:** [[log#2026-05-03-stage2-transition-spec]]
**Linked decision:** [[decisions/2026-05-03-pivot-to-ma50w10]]

## Context

Per [[decisions/2026-05-03-pivot-to-ma50w10]], MA50+W10 paper-real Stage 1 started 2026-05-03 and runs until 2026-06-03 (30-day window). The decision at June 3 is whether to promote to Stage 2 real-money OR continue paper-real OR resurrect B.2.3.

To make the June 3 decision fast and disciplined (not improvised under time pressure), define the gate criteria + build the tooling NOW. This decision specifies BOTH the criteria and the read-only diagnostic that scores against them. Per CLAUDE.md safety rule, the actual flip-to-live operation remains a separate explicit step gated by typing `CONFIRM LIVE TRADING`.

## The 4 gates (per-bot, independent, ALL must pass)

| # | Gate | Threshold | Source |
|---|---|---|---|
| 1 | Continuous uptime | ≥ 30 calendar days running without crash-loop | systemd `ActiveEnterTimestamp` |
| 2 | Net P&L | ≥ +2% over the window | `scripts/equity_report.py` (parses MA-BUY/MA-SELL log events) |
| 3 | Max drawdown | ≥ −3% (no drawdown deeper than 3% from a running peak of cumulative-return) | `equity_report.py` |
| 4 | Closed trades | ≥ 5 (sample size for any meaningful inference) | `equity_report.py` |

**Why these specific numbers:**

- **30 days uptime.** Below this, results dominated by single regime. Above this, opportunity cost of delay grows.
- **+2% net P&L.** Beats Gate.io USDT yield (~0.5% APY ⇒ ~0.04%/30d) by 50× — meaningful signal not just noise. Below 2% means the strategy is barely-better-than-cash with execution risk added.
- **−3% max DD.** Position sizing assumption: $250 max per bot, daily candles → typical realised vol ~5% per trade. A −3% portfolio DD means strategy correctly flattens to USDT before larger drawdowns; consistent with `MA_STRATEGY.md`'s key feature (cuts catastrophic-bear losses).
- **≥ 5 closed trades.** Below this, P&L is dominated by 1-2 lucky/unlucky moves; statistically meaningless. 5 is the floor, not a target.

These are HARD gates. Failing any one ⇒ NOT a Stage 2 candidate. Operator may NOT promote despite a "feels good" reading.

## Tooling

| File | Purpose |
|---|---|
| `scripts/equity_report.py` | Reads `/var/log/trading-bot-*.log`, reconstructs equity curve from MA-BUY/MA-SELL events, computes metrics. Outputs human table or JSON. **Read-only.** |
| `tests/test_equity_report.py` | 18 unit tests on synthetic logs verifying parser correctness + metric computation. Pass before any commit. |
| `systemd/equity-report.service` + `.timer` | Runs equity_report.py daily at 00:05 UTC, writes results to `/var/log/equity-report.log` and `/var/log/equity-report-latest.json` |
| `scripts/stage2_promote_check.sh` | **Read-only diagnostic** — discovers all `trading-bot-*.service`s, calls equity_report for each, applies the 4 gates, prints PASS/FAIL table. Does NOT promote. |
| `systemd/trading-bot-live-ma50w10.service.template` | Pre-built unit for live deployment. **Filename ends in `.template`** specifically so a careless `cp systemd/* /etc/systemd/system/` does NOT enable it. The promotion script (TBD) will strip the suffix before installing. |

## Promotion procedure (for the June 3 decision)

This is a SPEC, not a script-yet. The actual `scripts/champion_promote.sh` is TBD and will be built closer to June 3 once we know the 30-day picture. Reason: writing a "click here to flip to live" script while we're still 30 days out tempts premature use. The procedure below is what the script will eventually wrap.

```
1. Operator runs scripts/stage2_promote_check.sh
   → table shows all bots, their metrics, and pass/fail per gate

2. If trading-bot-ma50w10 shows 4/4 PASS:
   → Operator does manual eyes-on:
       a. Pull last 30-day chart from journalctl, plot equity curve
       b. Check: monotonic-ish growth, not a single lucky trade
       c. Check: max DD recovered (not still in drawdown)
       d. Check: vote bots' state for context (correlation? regime?)
       e. Check: production-monitor alerts in last 24h

3. If eyes-on passes:
   → Pre-flight on VPS:
       - Gate.io API key has TRADING enabled, WITHDRAW disabled
       - Account has ≥$300 USDT (incl. slippage buffer)
       - /etc/default/gate-api-keys exists, mode 600, owner root
       - Current BTC price within ±5% of paper-bot's last decision price

4. Run scripts/champion_promote.sh (TBD):
   → Demands typing CONFIRM LIVE TRADING (per CLAUDE.md hard safety rule)
   → systemctl stop trading-bot-ma50w10 (paper)
   → cp systemd/trading-bot-live-ma50w10.service.template
        /etc/systemd/system/trading-bot-live-ma50w10.service
   → systemctl daemon-reload
   → systemctl enable --now trading-bot-live-ma50w10
   → Tail first 60s of journalctl for first BUY/SELL
   → Telegram alert with first live-trade details

5. T+1 hour:
   → Operator verifies first live order placed correctly via Gate.io UI
   → Verifies Telegram alert received
   → Sets calendar alarm for +24h post-promotion review

6. T+24 hour:
   → Run stage2_promote_check.sh (NOW reading live bot's log)
   → Confirm: realised P&L tracks paper-bot's expectation
              within slippage tolerance (±0.3%)

7. T+60 days (Stage 2 complete):
   → Track record meets L99 definition per CHAMPION_MODE.md
   → Separate ADR for any further scaling decisions
```

## Reversibility (Stage 2 → Stage 1 demote)

If anything looks wrong after promotion — slippage worse than expected, unexpected drawdown, system instability — `scripts/champion_demote.sh` (TBD) provides an instant rollback:

```bash
systemctl disable --now trading-bot-live-ma50w10
systemctl start trading-bot-ma50w10   # resume paper
```

A position held by the live bot at demote time stays open (no force-close); operator decides manually whether to flatten via Gate.io UI or hold to next strategy signal. This is intentional: forced market sells in the middle of a panic = exactly the wrong execution.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Auto-promote when 4 gates pass on June 3 | CLAUDE.md hard rule: "Never run live trading. Live mode needs CONFIRM LIVE TRADING typed by the user." Auto-promote would bypass this. |
| Lower the +2% gate to +0% (just "non-negative") | Strategy that's barely above zero is worse than holding USDT (which earns ~0.5% APY without execution risk). Below +2% is a fail. |
| Wait until 60 days of paper before Stage 2 | Doubles the L99 timeline without meaningful information gain over 30 days for a daily-candle strategy. The 30-day window already captures multiple SMA crossovers in normal regimes. |
| Build the actual promotion script NOW, not just the spec | Premature. Tempts misuse before 30-day data exists. Also, the precise script depends on details we'll learn from observing the bot for 30 days (e.g., what does Gate.io's API return on the actual order? slippage characteristics?). |
| **Spec + read-only diagnostic + LIVE template now; promotion script TBD** ← chosen | Operator has all the prep work; risky bits (the actual flip) are deferred to closer to the date when we have data. |

## Consequences

**Enabled:**
- June 3 decision is fast: run one bash command, read PASS/FAIL table, decide.
- 4-gate criteria precisely defined NOW means no improvisation under time pressure.
- LIVE template + spec exist; promotion script can be written in ~30 min in early June (we'll have full 30-day data then to inform precise wording).
- `equity_report.py` runs daily as of install — operator gets cumulative trend data, not just point-in-time.

**Costs:**
- Adds 5 files to repo (~700 lines including tests).
- Daily systemd timer fires 30 times before it's needed (cheap — ~50ms per invocation).
- Maintenance: when ma20w5 paper bot is added (today), and any future bots, no changes needed — `discover_bot_logs()` finds them automatically.

## Re-evaluation triggers

Re-open this decision IF:

- A bot crashes / restarts often enough that the "continuous uptime" gate would unfairly fail it (then we'd need an "uptime ≥ 95% of 30d" criterion instead)
- Closed-trades count is < 5 across ALL bots at June 3 (then we extend Stage 1 by 30 days, not 60 — minimum-viable-sample logic)
- A new validated strategy is added that needs different gate thresholds (then a per-strategy override table)
- Gate.io changes their fee structure (the +2% gate was implicit on current fee tier)

## ADR linkage

- ADR-001 — D-day discipline. 30-day paper validation gate. **Codified here.**
- ADR-002 — Phase B direction. Microstructure deferred behind ma50w10 candidate. Unchanged.
- ADR-003 — D7 freeze. Expired 2026-05-01. Strategy code (ma50w10, ma20w5) already exists; no new strategy code in this decision.
- `feedback_drift_pattern.md` (memory) — `/godmode` cue, this decision is a legitimate acceleration (defines criteria + builds tooling) WITHOUT bending the 30-day or 60-day requirements. Honored.
- CLAUDE.md "Never run live trading. Live mode needs CONFIRM LIVE TRADING typed by the user." — codified here as Step 4 of promotion.

## Related

- [[decisions/2026-05-03-pivot-to-ma50w10]] — what this transition will execute
- [[findings/2026-05-03-ma50w10-deployed]] — Stage 1 deployment confirmation
- [scripts/equity_report.py](../../scripts/equity_report.py) — the reporting tool
- [scripts/stage2_promote_check.sh](../../scripts/stage2_promote_check.sh) — the gate-eval tool
- [systemd/trading-bot-live-ma50w10.service.template](../../systemd/trading-bot-live-ma50w10.service.template) — pre-built live unit
- [CHAMPION_MODE.md](../../CHAMPION_MODE.md) — L99 / 60-day track record definition
