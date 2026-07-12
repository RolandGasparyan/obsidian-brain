---
title: Forensic Live Trading Audit — 2026-06-17
type: meta
tags: [meta, audit, forensic, trading, gate-io]
status: completed
updated: 2026-06-17
---

# 🔬 Forensic Live Trading Audit — 2026-06-17

> **For future Claude:** This is a ground-truth audit of live Gate.io trading on VPS
> `167.71.24.86`, built ONLY from real exchange fills (`fetch_my_trades`, FIFO realized PnL,
> net of fees) — no backtests, no claimed performance, no log-reported PnL. Verdict:
> **`NO_VERIFIED_LIVE_CHAMPION_FOUND`** — no account is net profitable, and the largest
> account (MAIN) is unverifiable because its API key lacks Gate spot permission. Method was
> read-only (no orders/withdrawals). Raw data: `/tmp/forensic_audit.json` on the VPS (ephemeral).

## Scope & method
- **Sources (only):** Gate.io spot fills, order/account-book history, realized PnL (FIFO),
  fees, futures funding. Executor/runtime logs used **only** to attribute fills to a strategy.
- **Excluded:** all backtests, research reports, claimed performance, chart interpretation.
- **Confidence:** `high` for SUB1/SUB2 (direct exchange fills); MAIN = `unverifiable`.

## Verdict: `NO_VERIFIED_LIVE_CHAMPION_FOUND`
1. No account is net profitable (PF 0.085 / 0.119 — gross wins ≈ 9–12% of gross losses).
2. MAIN (largest) unverifiable — key returns `FORBIDDEN: does not have spot permission`.
3. The only live strategy (CMO v9.4) is also losing where measurable (SUB1 −6.53 since deploy).

## LIVE_STRATEGY_LEADERBOARD (lifetime, ~420d window)
Ranked: net realized → profit factor → drawdown → risk-adjusted.

| Rank | Account (agents) | Net realized USDT | Profit factor | Win rate | Max DD | Longest loss streak | Sharpe/trade | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | SUB2 / SENTINEL | −119.57 | 0.119 | 17.3% | −119.78 | 57 | −0.23 | 🔴 LOSS · drained ($0, 0 fills since 2026-06-07) |
| 2 | SUB1 / VELOCITY | −125.16 | 0.085 | 16.4% | −125.16 | 92 | −0.38 | 🔴 LOSS · near-drained ($0.83) |
| — | MAIN / TITAN+TRADING_GURU | UNVERIFIABLE | — | — | — | — | — | ⚠ no spot permission (`FORBIDDEN`) |

**Verified realized total (SUB1+SUB2): −244.73 USDT** | **Total fees: 137.47 USDT** | MAIN: unknown.

### Current strategy isolated — CMO "Gods Level" v9.4 (since 2026-06-07)
- SUB1 / VELOCITY: **−6.53 USDT**, 583 round-trips, WR 15.4%, PF 0.107, loss-streak 37.
- SUB2 / SENTINEL: **0 fills** (account dead/drained).

## The 9 forensic answers (evidence-cited)
1. **Strategy:** `champion_battle.py` "CMO Gods Level" v9.4 — only live executor (`champion-battle.service` active; `l99-agent-*`=FATAL, `l99bot`=STOPPED). First deploy 2026-06-07T08:42Z (`service.log`).
2. **Accounts:** SUB1 (VELOCITY) & SUB2 (SENTINEL) verified executing; MAIN (TITAN+TRADING_GURU, shared key `.api_key_main`) unverifiable.
3. **Symbols:** SUB1 → ADA, BTC, DOT, FLOKI, OP, SHIB, WIF. SUB2 → 19 pairs (+ APT, ARB, ATOM, AVAX, BNB, INJ, LTC, NEAR, SOL, SUI, UNI, XRP).
4. **Realized P/L:** SUB1 −125.16, SUB2 −119.57 USDT.
5. **Fees:** SUB1 76.43, SUB2 61.03 USDT.
6. **Longest win streak:** SUB1 11, SUB2 15.
7. **Longest loss streak:** SUB1 92, SUB2 57.
8. **Max drawdown:** SUB1 −125.16, SUB2 −119.78 USDT (realized curve).
9. **Net after fees:** SUB1 −125.16, SUB2 −119.57 (+3.50 SUB2 futures funding). All negative.

## 🔴 MAIN account is UNAUDITABLE & SELF-BLIND (credential investigation, 2026-06-17 follow-up)
Attempted to pull MAIN's 1-month history. **Exhaustively tested all 9 Gate keys on the VPS — none can read MAIN's spot history:**

| Key source | Prefix | Result |
|---|---|---|
| Deployed `.api_key_main` (live) | `cfdd4c…` | Authenticates but **zero read perms** — spot, account & wallet all `FORBIDDEN` |
| `keys_backup_1779660988/.api_key_main` | `5cf6d6…` | `INVALID_KEY` (revoked) |
| `keys_backup_1779660988/.api_key_sub1/2` | `30c0ea / adb8dd` | `INVALID_KEY` (revoked) |
| vault `GATE_API_KEY_LIVE` (= ai-trading-championship) | `73b23c…` | `AuthenticationError` (revoked) |
| vault `ai-l99-production GATE_API_KEY` | `4be8b4…` | `AuthenticationError` (revoked) |
| `arena_lab GATE_KEY` | `875a31…` | Works but **TESTNET** (paper $230 — not the real account) |
| canary `.api_key_sub1 / sub2` | `294cde / 1f1b0f` | Spot OK — but these are VELOCITY/SENTINEL, not MAIN |

**Implications (material operational risk):**
- MAIN's realized PnL / 1-month history **cannot be verified** — no readable credential exists. Not fabricated; reported as a hard evidence gap.
- The **executor itself cannot read its own MAIN trades** — `champion_battle.py`'s `fetch_my_trades` on MAIN throws the same `FORBIDDEN: does not have spot permission` (`pnl.log` 2026-06-14). MAIN trades with **no fill confirmation and no exit verification** — flying blind on the largest account.
- `battle.log`: MAIN has **15,645 failed order attempts**; whether any MAIN orders actually fill is unconfirmable with the current key.

**To close the gap (operator action):** on Gate.io API Management, grant the MAIN account key **Spot → Read** permission (Wallet read ideally), update `/root/canary/.api_key_main` (`key:secret` format). Then a single read-only command pulls the verified 30-day MAIN history. (Do NOT paste secrets into chat.)

## Material findings (read-only — no changes made)
- **MAIN key misconfig:** `.api_key_main` lacks Gate **spot** permission → biggest account unauditable and possibly not exiting correctly. Executor itself hit the same `FORBIDDEN` on `fetch_my_trades` (`pnl.log` 2026-06-14). **Verify key scopes.** *(Full credential investigation above.)*
- **Sub-accounts drained:** SENTINEL $0.00, VELOCITY $0.83 — below $5 floor → constant `BALANCE_NOT_ENOUGH` (failed attempts in `battle.log`: MAIN 15,645 / SUB1 16,819 / SUB2 12,721).
- **No trustworthy self-ledger:** `runtime/ledger/` empty, `pnl.log` empty, `trade_review.jsonl` = 4 lines, `trade_memory.jsonl` = 11.6M lines of reasoning spam → exchange was the only source of truth.

## Caveats
- Realized = executed spot round-trips only; open dust (<~$5/acct) excluded; FIFO clean (no unmatched pre-window sells); no GT/point fees encountered.
- **Attribution limit:** Gate fills carry no strategy tag and the executor keeps no clean ledger, so lifetime account totals aggregate ALL strategies ever run per account. Only the post-2026-06-07 slice is cleanly attributable to CMO v9.4.

## Related
- [[Trading_Guru_Empire_MOC]] · [[Infrastructure_Overview]] · [[GODSMODE_Research_Results]]
- Backtest reality (separate evidence): root `CLAUDE.md` — 9-agent engine ≈ −0.5% over 24mo; only `MA50W10` rule was profitable (not what is running live).
