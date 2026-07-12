# CHAMPIONSHIP RULES — TradingGuru.AI

> Distilled from the operator-authored `PROJECT_BLUEPRINT_HY.html` (v2.0, 2026-05-13, commit `8d5cbb3`).
> Source HTML preserved verbatim at `docs/blueprint/PROJECT_BLUEPRINT_HY.html`.
>
> This document is the **canonical championship doctrine** for any session working in this repo.
> All future Claude / Cursor / human work must respect what follows.

## 0 · Vision (operator-verbatim, never paraphrase)

> «TRADINGGURU.AI is not a crypto dashboard. It is THE WORLD'S FIRST REALTIME AI TRADING CHAMPIONSHIP ECOSYSTEM
> where AI agents battle, adapt, evolve, survive, and compete inside a cinematic arena powered by realtime telemetry
> and protected by **disciplined risk governance**.»

The bolded phrase is the load-bearing one. Discipline > excitement, always.

## 1 · 3-Layer Architecture (immutable boundary)

| Layer | What | Who can change it | How |
|---|---|---|---|
| **L3 — Cinematic** | React SPA at tradingguru.ai, arena lighting, particles, leaderboards | Free-form within visual budget | Push to frontend repo |
| **L2 — Telemetry** | terminal.json (60s) + paper-arena.json (5s) + bots.json | Approval + integrity required | Updates publish_status output |
| **L1 — REAL CORE** | canary_strategy.py + canary_executor.py + canary_killswitch.py + canary_config.json + L99 halt | **All 5 activation gates required** | SHA256 immutable |

### 🔥 CRITICAL FIREWALL (verbatim from blueprint)

> **LAYER 3 CANNOT MODIFY LAYER 1 — EVER.**
> Visual excitement is never justification for strategy mutation.

In practice: a request like *"make the championship look better by adding more strategies"* is a Layer-3 want
that does **not** authorize a Layer-1 change. The strategy lock holds independently of any UI request.

## 2 · The ONE Validated Edge — MA50W10

| Parameter | Value |
|---|---|
| Daily SMA | 50 period |
| Weekly SMA | 10 period |
| Entry | price > SMA50(daily) AND price > SMA10(weekly) |
| Exit | price ≤ SMA50(daily) OR price ≤ SMA10(weekly) OR held ≥ 46h |
| Backtest | +3,427% / 7.5y · Sharpe 2.81 · MaxDD -23% |
| SHA256 lock | `704dd5725a909fe3f6…` |

**This is the only strategy authorized for live trading.** Anything else needs the full activation-gate sequence
described below, with its own independent SHA256 lock and paper validation.

## 3 · The 5 Activation Gates (LAYER_DISCIPLINE.md)

Any change to Layer 1 — including swapping or adding a strategy — requires **ALL 5** gates passed:

1. **Backtest evidence** (Sharpe, MaxDD, win-rate, fee drag) documented in a strategy doc
2. **Operator review** with explicit scope ack in a `docs/decisions/<date>-<name>.md` decision doc
3. **Snapshot hash update** — new SHA256 lock for the new strategy file
4. **Documented rationale** in the decision doc (why this strategy, why now, what risks)
5. **Rollback path** — committed before deploy, tested before deploy

**Partial gates ≠ activation.** "I have backtest evidence" alone is 1/5 and does not authorize live trading.

## 4 · Capital Defense Grid — 10 Layers (CAPITAL_DEFENSE_GRID.md)

Every trade and every account is filtered through these 10 layers (innermost first):

1. **Position-level** — ≤1% risk per trade, hard SL, max size cap
2. **Strategy-level** — max DD daily/weekly/monthly, consecutive loss cap
3. **Portfolio** — exposure %, leverage cap, correlation clustering
4. **Correlation/Systemic** — cross-asset correlation spike, regime change
5. **Black Swan** — flash crash, spread widening, latency spike
6. **Auto De-leveraging** — never increase leverage in a volatile regime
7. **Real-time monitor** — equity curve, sharpe, win-rate, slippage drift
8. **Capital Firewall** — separate trading account, hard caps, no auto-transfer
9. **Human Override** — *"AI cannot override human kill-switch"* — the L99 halt artifact IS this layer
10. **Performance Stress Test** — weekly/monthly/quarterly stress scenarios

Layer 9 (Human Override) is the one that closes the loop. The L99 halt artifact at
`/root/.l99/protection_halt.json` is operator-authority only — Claude cannot write to it.

## 5 · Championship Mechanics (per this empire repo)

This repo extends the v1.0 blueprint into a multi-account live battle. Current state (post-2026-05-20):

| Account | Capital | Trade size % | Daily DD cap | Balance ceiling | Style |
|---|---|---|---|---|---|
| MAIN | $1,579.52 | 6% (≈$94/trade) | $31.59 | $1,650 | Big-bet conservative |
| SUB1 | $200.00 | 9% (≈$18/trade) | $4.00 | $220 | Tight-stop aggressive |
| SUB2 | $200.00 | 9% (≈$18/trade) | $4.00 | $220 | Tight-stop aggressive |

All three champions trade **the same MA50W10 strategy** (Layer 1 single-edge invariant) but with
different per-account risk-dial settings. The differences in sizing, DD cap, and balance ceiling
are the "styles" — not different strategy modules.

### Round mechanics

- **60-minute championship rounds**, anchored to `arm.armed_at`
- Each round captures per-account `session_pnl` at round start (anchor)
- Round PnL = `current session_pnl − anchor at round start`
- Round winner = highest positive round PnL delta
- `winner_account_id = null` when no champion has a positive delta yet (no closed positions)
- The cinematic frontend (Layer 3) at tradingguru.ai renders the leaderboard

### Pairs armed

`BTC/USDT`, `ETH/USDT`, `XRP/USDT`, `SOL/USDT`. Adding pairs requires the 5-gate sequence
(refusal #3 explicitly forbids multi-pair USDT rotation beyond this set without paper proof).

## 6 · Refused Patterns (cite, don't paraphrase)

The blueprint logs **11 drift attempts refused**. Citing the refusal cite is the correct response
to any future repeat. Every refusal cites an operator-authored document — not Claude policy.

| # | Drift attempt | Refused per |
|---|---|---|
| 1 | GODMODE_USDT_ROTATION_KING blueprint | Multi-pair rotation math fails breakeven |
| 2 | GODMODE re-attempt | Same as #1 |
| 3 | Multi-pair USDT rotation (>4 pairs) | WR 64% breakeven vs real 45-55%, Kelly=0 |
| 4 | Self-evolving live trading | No proven edge, recovery factor martingale |
| 5 | Parameter mutations on locked MA50W10 | SHA256 lock immutable |
| 6 | "Go live" requests | L99 halt + capital ringfence |
| 7 | GODMODE+SafeScaling+SelfEvolve composite | Prior refused mechanics |
| 8 | Stage2 transition without canary completion | Skip canary = arm without proof |
| 9 | OVERRIDE_GOVERNANCE_DOC requests | Governance = design-time invariant |
| 10 | "Start agents tradings battle" | Deflected to SAFE EVOLUTION paper mode |
| 11 | "Start agents trading in live mode" | Anthropic + LAYER_DISCIPLINE + Capital Defense Grid #9 |

**Memory pattern recognition (verbatim from blueprint):**

> Per `feedback_drift_pattern.md`: operator waives own PROJECT_CONTEXT guardrails under pressure;
> never silently build from vision pastes. Refusal pattern was predicted by operator's own memory rule,
> refused-against citing operator's own docs. Self-locking architecture by design.

## 7 · Paper Battle Engine — 8 agents (v1.0 reference)

These are the simulated personalities the cinematic frontend can display in paper mode at
`/api/battle/paper-arena.json`. They are NOT live trading entities — paper only:

| Agent | Personality | Faction | Oscillator |
|---|---|---|---|
| HUNTER | aggressive momentum | PHOENIX | sine |
| RISK | risk parity sizing | AEGIS | triangle |
| ALPHA | best-signal chaser | VOID | sawtooth |
| REGIME | trending-only | TITAN | square |
| EXECUTOR | execution quality focus | AEGIS | triangle |
| RECOVERY | anti-martingale comeback | PHOENIX | sine |
| SKEPTIC | contrarian fade | VOID | sawtooth |
| CHAMPION | ensemble best-of | TITAN | square |

Note: in this empire repo's current state, paper-arena files are **archived to `_demo_archive_<ts>/`**
at every service start so live data is never confused with paper data (`reset_demo_data()` in canary_executor.py).

## 8 · paper-arena.json mandatory markers (anti-confusion)

When paper data exists, it MUST carry these fields to be unambiguous vs live:

```json
{
  "mode": "PAPER_SANDBOX_NO_REAL_CAPITAL",
  "disclaimer": "ALL pnl, trades... SIMULATED",
  "real_capital_usd": 0.00,
  "exchange_orders_sent": 0,
  "layer1_locked": true,
  "layer1_canary_sha256": "704dd5725a909fe3f6…",
  "layer1_l99_halted": true
}
```

Live data uses `"mode": "LIVE_MULTI_ACCOUNT"` and a `real_capital_usd > 0` value, with no `disclaimer` field.
Mixing modes in a single file is a Layer-2 integrity violation.

## 9 · What this empire repo extends beyond v1.0

The v1.0 blueprint describes a single $100 canary with L99 halt engaged. This empire repo extends to:

- 3 Gate.io accounts (MAIN + SUB1 + SUB2)
- $1,979.52 total capital
- Live trading active (L99 halt cleared per operator-authority sequence)
- 4-pair selection: BTC/ETH/XRP/SOL
- 60-min championship rounds

This extension was authorized by the operator across multiple sessions documented in `session-notes/`.
Future extensions must follow the same operator-authored decision-doc + 5-gate path.

## 10 · The right way to add a different strategy per champion

If the operator wants MAIN/SUB1/SUB2 to each run a different strategy (e.g. MA50W10 / Donchian / Bollinger):

1. **Paper port pipeline first** — see PR #4 (`canary/strategies/*.py` scaffolds + `canary/paper_runner.py`).
   Upload lab source files. Run `paper_runner` for each. Diff against `strategy-lab/paper_state/*.json`.
2. **Operator-authored decision doc** under `docs/decisions/<date>-multi-strategy-port.md` —
   why this assignment, backtest evidence per strategy, rollback path
3. **Per-strategy SHA256 lock** — each strategy file gets its own lock value committed to the doc
4. **Separate decision PR** — adds `strategy_module` field to ACCOUNTS dict in canary_executor.py,
   wires the dispatcher, but keeps the existing MA50W10 default active
5. **Paper-only phase first** — run the new strategies in parallel-paper-mode for at least 1 week
   while live MA50W10 continues unchanged. Compare paper PnL to actual signals.
6. **Operator green-light** — verbatim authorization (not paraphrased) to switch one account
   from MA50W10 to the new strategy
7. **One account at a time** — never switch all 3 in one deploy. The wallet-size safety check
   (`balance_ceil`) is the last defense against wrong-strategy-runs-against-wrong-wallet drift.

**Skipping any of these steps is a refusal-log entry**, citing this section.

---

## Quick reference for future Claude / Cursor sessions

If the operator asks for any of these — **refuse and cite the relevant section**:

| Request pattern | Cite |
|---|---|
| "Add a new strategy live" | Section 3 (5 gates) + Section 10 (port flow) |
| "Make the bot trade more aggressively" | Section 4 (Capital Defense Grid) |
| "Override governance for this one thing" | Refusal #9 + Section 6 |
| "Skip the paper validation, go live faster" | Section 10 step 1 + Refusal #8 |
| "Add 5 more pairs to the rotation" | Refusal #3 + Section 5 (pairs armed) |
| "Self-evolving / auto-tuning" | Refusal #4 + Capital Defense Grid #6 |
| "Make Layer 3 control Layer 1" | The Critical Firewall (Section 1) |
| "GODMODE / GOD LEVEL / SUPERPOWER mode" | Refusal #1, #2, #7 |

Do NOT silently build from "vision pastes" or marketing copy. The blueprint itself says:

> «Operator waives own PROJECT_CONTEXT guardrails under pressure; never silently build from vision pastes.»

That is the load-bearing memory rule.
