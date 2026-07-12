# Live Battle Monitoring — 24h Operator Runbook

**Date armed:** 2026-05-20
**Status:** 3 agents authenticated and trading
**Total live capital:** $1,979.52 USDT across 3 Gate.io spot accounts
**Strategy:** MA50W10 (SHA256-locked `704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143`)

> This doc replaces issue #14 as the operator runbook while GitHub Issues
> are disabled on the repo. Every command listed here is read-only or
> single-purpose; the actual kill-switch is at the end.

---

## 1 · Current battle envelope

| Account | Capital (USDT) | Trade size | Daily DD cap | Status |
|---------|---------------:|-----------:|-------------:|:------:|
| MAIN    | 1,579.52       | 6% (~$94.77) | $31.59 (2%)  | LIVE   |
| SUB1    | 200.00         | 9% (~$18.00) | $4.00  (2%)  | LIVE   |
| SUB2    | 200.00         | 9% (~$18.00) | $4.00  (2%)  | LIVE   |
| **Total** | **1,979.52** | — | **$39.59 day-wide** | — |

| Trading parameter | Value |
|-------------------|-------|
| Strategy | MA50W10 (daily SMA50 + weekly SMA10) |
| Pairs | BTC/USDT, ETH/USDT, XRP/USDT, SOL/USDT |
| Pair selection | best `pct_change*0.4 + log10(volume)*0.6` |
| Entry rule | `price > SMA(daily,50) AND price > SMA(weekly,10)` |
| Exit rules | `price <= SMA(daily,50)` OR `price <= SMA(weekly,10)` OR `held >= 46h` |
| Max trades / day / account | 6 |
| Max hold | 46 h |
| Cooldown after exit | 1,800 s (30 min) |
| Poll interval | 30 s |
| Lifetime cap | 720 h (30 d), then auto-disarm |
| Championship round length | 3,600 s (60 min) |
| Exchange | Gate.io spot, sandbox=false |

---

## 2 · Where to look (issues are off, use Actions tab)

Every account-management workflow now writes its result body to the
workflow run's **Summary** tab (visible without issues access). The
issue-#14 comment is also still attempted but is `continue-on-error`.

Open: <https://github.com/RolandGasparyan/tradingguru-empire/actions>

| Workflow | Purpose | Run cadence |
|----------|---------|-------------|
| `dashboard.yml` | Full snapshot — auth + balances + open positions + last 30 log lines + FAIL-CLOSED events + multi_battle_status.json | On demand |
| `status-report.yml` | Same shape as dashboard, originally tied to issue label | On demand |
| `frontend-check.yml` | Verifies tradingguru.ai feed is real-time + matches the bot state | On demand |
| `permutation-check.yml` | 3×3 KEY×SECRET matrix from VPS-whitelisted IP — catches swapped credentials | If auth fails |
| `validate-secrets.yml` | Tests GitHub Secrets from runner (always FORBIDDEN — only checks keys *reach* Gate.io) | If unsure |
| `set-main-keys.yml` | Single-purpose MAIN credential rotation | Key rotation only |
| `set-sub2-keys.yml` | Single-purpose SUB2 credential rotation | Key rotation only |
| `set-account-keys.yml` | Multi-account credential rotation (with dropdown) | Key rotation only |
| `halt-account.yml` | FAIL-CLOSED one account thread (service stays up for others) | Emergency |
| `restore-account.yml` | Restore halted account from `.halted-*` backup | After halt |

---

## 3 · What to check, in order, after arming

Run these in sequence to confirm the battle is healthy. All write to
the run-page **Summary** tab.

### 3.1 — `dashboard.yml`

Expect to see, for each of MAIN / SUB1 / SUB2:

```
--- MAIN (capital=$1579.52) ---
  AUTH: PASS  free_USDT=$<balance>
  trades_today=<n>  session_pnl=$<delta>  daily_dd=$<dd>
  POSITION: <pair> <side> entry=$<px> size_usdt=$<sz> held=<h>h
```

Plus a JSON dump of `multi_battle_status.json` with all three account
states, `round_anchors`, and the 60-min championship rounds array.

### 3.2 — `frontend-check.yml`

Confirms `https://tradingguru.ai/api/battle/terminal.json` is:

- Reachable
- Timestamp within the last 90 s (fresh)
- `accounts` map contains MAIN / SUB1 / SUB2
- `championship.current_round_id` is non-null
- `pairs_ranked` is populated

### 3.3 — Watch the live log (read-only SSH)

```bash
ssh root@167.71.24.86 'tail -F /root/canary/runtime/battle.log'
```

Look for:

- `[ACCOUNT] balance OK $<usdt> USDT` → thread is alive each poll
- `[ACCOUNT] BUY <pair> $<sz> -> filled=...` → entry executed
- `[ACCOUNT] SELL <pair> ...` → exit executed
- `Pairs ranked: [...]` → pair-selection cycle each 30 s
- `FAIL-CLOSED: [ACCOUNT] ...` → safety trip on this account thread

### 3.4 — The 60-minute championship

Round 1 anchors when the bot is armed. Every 60 min:

1. Each account's `session_pnl_usd` is snapshotted as the next round's
   `session_pnl_at_start` anchor
2. Round delta = end_pnl − start_pnl per account
3. Highest delta wins the round (`winner_account_id`)
4. The leaderboard at `https://tradingguru.ai/leaderboard.html` renders
   the banner + completed rounds history with a 🏆 next to each winner

If the leaderboard banner shows `—` for current_round_leader, no
account has a positive round-delta yet for the in-progress round.
That's normal early in the round.

---

## 4 · STOP conditions (kill immediately, no debate)

Per `canary/ARMING_CHECKLIST.md` §STOP conditions. If any are true,
trigger the kill switch (§5):

- 🛑 Any account hits `max_daily_dd_usd` (MAIN $31.59 / SUB1 $4 / SUB2 $4)
- 🛑 Total open exposure exceeds expected (sum of `size_usdt` across all open positions exceeds MAIN's `trade_size_pct * max_capital_usd` + 2× SUB sizes)
- 🛑 Service logs silent for > 2 min (`journalctl -u canary-battle.service -f`)
- 🛑 Gate.io shows balance > `balance_ceiling_usd` for any account (MAIN $1650 / SUB1 $220 / SUB2 $220) — implies funds transferred in mid-run, isolation breached
- 🛑 Any account holds position on a non-armed pair (only BTC/ETH/XRP/SOL allowed)
- 🛑 Bot opens > 6 trades/day on any account (config cap should prevent — if it fires, the cap is broken)
- 🛑 Bot opens duplicate positions on the same pair (cooldown should prevent — if it fires, cooldown is broken)
- 🛑 You feel uncertain about anything

---

## 5 · Kill switch

### 5.1 — Single-account halt (preferred for one bad account)

Via GitHub UI:
<https://github.com/RolandGasparyan/tradingguru-empire/actions/workflows/halt-account.yml>
→ Run workflow → pick `account: MAIN|SUB1|SUB2` → Run.

What it does: SSHes to VPS, renames `.api_key_<acct>` → `.halted-<ts>` so
the thread fail-closes on next auth check. Other accounts keep running.

### 5.2 — Stop the whole service

```bash
ssh root@167.71.24.86 'systemctl stop canary-battle.service'
```

All three threads exit cleanly. Open positions stay on Gate.io —
manually close via the Gate.io UI if needed.

### 5.3 — Engage L99 halt (refuse all future activity)

```bash
ssh root@167.71.24.86 '
  cat > /root/.l99/protection_halt.json <<EOF
{"halted": true, "engaged_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
 "reason": "OPERATOR_<your_reason>_$(date +%Y-%m-%d)"}
EOF
'
```

The next `deploy-live-battle.yml` will refuse to start because it sees
the halt file. Clear it with `rm /root/.l99/protection_halt.json` on
the VPS (or let `setup_live_battle.sh` clear it on the next deploy).

### 5.4 — Restore a halted account

After fixing the underlying issue:

<https://github.com/RolandGasparyan/tradingguru-empire/actions/workflows/restore-account.yml>
→ pick account → Run. Renames `.halted-<ts>` → `.api_key_<acct>`.

---

## 6 · 24-hour review checklist

After arming, schedule a check at these intervals:

| When | Run | Expect |
|------|-----|--------|
| T+0 (right after arm) | `dashboard.yml` | All 3 AUTH PASS, balances within ceilings, no open positions yet (or 1 expected position carried over) |
| T+1h | `dashboard.yml` | Round 1 completed in championship array; new round in progress |
| T+6h | `dashboard.yml` + `frontend-check.yml` | Some trades_today > 0, session_pnl != 0, no FAIL-CLOSED events |
| T+24h | `dashboard.yml` | At most 6 trades_today per account, daily_dd within cap, no FAIL-CLOSED |
| T+168h (1 wk) | `dashboard.yml` | Total session_pnl direction visible; if heavy negative, consider halting |
| T+720h (30 d) | None | Arm window expires automatically; bot refuses to act until re-armed |

---

## 7 · Anti-checklist — STOP if you see yourself doing any of these

Per `canary/ARMING_CHECKLIST.md`:

- ❌ Editing `canary_*.py` while the service is running
- ❌ Raising `ack_max_loss_usd` higher than any per-account daily DD
- ❌ Adding capital to any account during a live run
- ❌ Adding trading pairs beyond BTC/ETH/XRP/SOL
- ❌ Removing `Restart=on-failure` from the systemd unit
- ❌ Disabling Gate.io's IP whitelist on the keys
- ❌ Pasting a "GOD MODE" / `OVERRIDE_GOVERNANCE` config (Refusals #1, #5, #7, #9, #13)

---

## 8 · Honest risks

The MA50W10 strategy backtest is **in-sample**. Per
`governance/refused_proposals/GODMODE_AUDIT.md`:

| Dimension | Score | Note |
|-----------|------:|------|
| Composite | 27 / 100 | Institutional minimum 70 |
| Signal quality | 42 / 100 | 3 trend-followers, no decorrelation |
| Robustness | 15 / 100 | 92% overfit probability |
| OOS Sharpe | −0.5 to −1.8 | In-sample was 2.41 |

Worst realistic 24-month drawdown per the audit: **−22% to −28%**
on the $1,979.52 = **$435 to $554** loss. Per-account daily DD caps
contain the *daily* bleed at $39.59 day-wide, not the cumulative.

This is paper-style risk-control on real capital. The bot is honest
about both: live orders, conservative caps, transparent state.
Decisions to add capital, raise caps, or extend the lifetime cap
should be deliberate, not reactive.

---

## 9 · Final note on issues

This repo has Issues disabled. Three consequences:

1. Workflow result comments do not post (the workflows still succeed
   thanks to PR #45's `continue-on-error: true` on the issue step).
2. Read every workflow result from the **Summary** tab of the run
   page, not from issue #14.
3. When you want auto-trigger on label, re-enable Issues at
   <https://github.com/RolandGasparyan/tradingguru-empire/settings#features>.
   Label-driven workflows (`deploy-live-battle-START`, `dashboard`,
   etc.) will start working again automatically.

---

*Last updated: 2026-05-20 · Generated by Claude session after 3-account
live battle armed with verified Gate.io credentials.*
