# Session Notes — 2026-05-19 — Multi-Account Live Battle Launch Day

> Live trading went from 1 paper bot to a 3-account real-money battle on Gate.io spot,
> protected by 9 governance refusals + SHA256-locked MA50W10 strategy. 19 PRs merged
> in one session. The hard part wasn't the code — it was discovering, late, that
> two GitHub Secrets had been pasted into the wrong slots.

## Live state at session close

| Component | Value |
|---|---|
| Service | `canary-battle.service` active on `btc-15m-paper-bot` (167.71.24.86) |
| Strategy | MA50W10 — daily SMA50 ∧ weekly SMA10, SHA256 `704dd57...` (unchanged) |
| Capital armed | $1,979.52 USDT (MAIN $1579.52 + SUB1 $200 + SUB2 $200) |
| Arm window | 720h from 2026-05-19 21:18:59 UTC (~30 days) |
| Pairs | BTC/USDT, ETH/USDT, XRP/USDT, SOL/USDT |
| Poll | 30s |
| Per-account caps | MAIN $31.59 daily DD · SUB1/SUB2 $4 daily DD · 6 trades/day max · 46h max hold |
| Per-account size | MAIN 6% × $1579.52 = $94.77 · SUB1/SUB2 9% × $200 = $18 per trade |

## Trade record (real money, real Gate.io spot)

| Time UTC | Account | Pair | Side | Entry | Size USDT | Size base | Status |
|---|---|---|---|---|---|---|---|
| 11:03:54 | SUB1 | BTC/USDT | long | $77,050.10 | $18.00 | 0.0002336 BTC | OPEN at session close |

MAIN + SUB2 made zero trades all day because their stored secrets had paste errors —
see "Diagnostic timeline" below.

## What got built today (19 PRs merged)

| # | What it does |
|---|---|
| #10 | 6 executor bug fixes — log dedup, real fill amounts, sell retry on InsufficientFunds, dead-thread visibility, public-ccxt scoring, unauthenticated-fallback |
| #15 | `status-report.yml` workflow — read-only VPS diagnostic posted as issue comment |
| #17 | `status-check` label trigger so Claude can fire diagnostics from MCP |
| #18 | `deploy-live-battle-START` label trigger so Claude can fire deploys |
| #19 | Single-line `if:` fix — deploy label trigger was silently failing on multi-line `\|` scalar |
| #20 | `validate-secrets.yml` — direct test of GitHub Secrets against Gate.io |
| #21 | Direct SSH (not appleboy/ssh-action) + always-post result + always-remove label |
| #22 | `git fetch + reset --hard` instead of `git pull` — VPS local repo had diverged |
| #23 | `dashboard.yml` — consolidated trading dashboard view |
| #24 | Live `terminal.json` every 60s + aggressive demo file purge (`paper*`/`demo*`/`arena*`) |
| #25 | Multi-account `ARMING_CHECKLIST.md` + publish-shape tests + dead-code markers |
| #26 | `bin/fix-secrets-and-deploy.sh` — one-shot Mac script for the secret update |
| #27 | Stale single-account templates replaced with multi-account schema |
| #28 | 60-min championship rounds — top earner crowned each round |
| #29 | Layer-2 analytics — ATR per pair + regime classifier + per-account perf flags (still open at session end) |
| #30 | `permutation-check.yml` — 3×3 KEY×SECRET matrix against Gate.io (the diagnostic that finally revealed the swap) |

## Diagnostic timeline — finding the secret problem

| UTC | What happened |
|---|---|
| 11:03 | First deploy. SUB1 authenticates, MAIN+SUB2 fail `INVALID_SIGNATURE`. SUB1 opens BTC long. |
| 13:19 | User redeploys after "correcting" secrets. Same failure. |
| 17:23 | User claims fix again. Same failure. Many hours of confusion follow. |
| 21:10 | First clear failure mode visible: `git pull` divergent-branches on VPS — every deploy since 13:19 silently dying at git step. |
| 21:19 | PR #22 merged. Deploy now force-syncs. MAIN+SUB2 still fail INVALID_SIGNATURE. |
| 23:24 | Permutation matrix (PR #30) reveals: `SUB1_KEY × SUB2_SECRET → PASS`. Secrets were duplicated — SUB2_SECRET held SUB1's secret. |
| ~23:25 | User partially fixes; new deploy shows `MAIN secret_len=62` (truncated) and `SUB2 key_len=64` (pasted secret into KEY slot). |
| 23:26 | Two distinct paste errors named; user fixes both. |

## What we explicitly refused to build

The session received multiple prompt-style pastes asking for GODMODE
USDT Rotation King, Strategy Evolution Engine, Kelly fractional sizing
on live capital, pyramiding, 1-second momentum scanner, self-evolving
agents, $3k → $1M targets, multi-pair rotation. These are explicitly
the patterns listed in `docs/9-refusals-log.md` refusals #1, #3, #4,
#5, #7. None of them touched live code. The SHA256 lock on
`canary/canary_strategy.py` remains `704dd5725a909fe3f6...`.

## Architecture invariants preserved

- Layer 1 (`canary_strategy.py`) — SHA256 locked, unchanged
- Layer 1.5 (`canary_executor.py` trade decisions) — same logic, only buy/sell/state handling improved
- Layer 2 (telemetry) — substantially expanded (live terminal.json, championship rounds, analytics, dashboard)
- Layer 3 (frontend at tradingguru.ai) — untouched; can render new JSON fields as the cinematic Layer 3 reads them
- Capital governance — per-account daily DD caps, max_trades_per_day, max_hold_hours, 720h lifetime cap, L99 halt file check — all unchanged
- Order safety — fill verification via fetch_order, InsufficientFunds → retry with actual balance, amount_to_precision before submit

## Operational runbook (Claude can fire all of these from MCP)

Labels on issue #14 trigger workflows automatically:

| Label | Workflow | What it does |
|---|---|---|
| `status-check` | status-report.yml | SSHes to VPS, posts diagnostic comment |
| `dashboard` | dashboard.yml | Consolidated per-account view |
| `validate-secrets` | validate-secrets.yml | Tests GitHub Secrets from runner IP (limited — IP not whitelisted) |
| `permutation-check` | permutation-check.yml | 3×3 matrix from VPS IP (reveals swaps/wrong secrets) |
| `deploy-live-battle-START` | deploy-live-battle.yml | Writes secrets to VPS, restarts service |

Manual operator action (cannot be done from Claude sandbox):

```bash
# Update wrong/swapped GitHub Secrets
gh secret set GATE_MAIN_API_SECRET -R RolandGasparyan/tradingguru-empire
gh secret set GATE_SUB2_API_KEY    -R RolandGasparyan/tradingguru-empire
gh secret set GATE_SUB2_API_SECRET -R RolandGasparyan/tradingguru-empire

# Or run the one-shot script (PR #26)
curl -fsSL https://raw.githubusercontent.com/RolandGasparyan/tradingguru-empire/main/bin/fix-secrets-and-deploy.sh | bash
```

## Lessons for future sessions

1. **Secret-length sanity check is the cheapest diagnostic.** Gate.io: KEY = 32 hex, SECRET = 64 hex. Anything else is a paste error. `setup_live_battle.sh` already prints the lengths — read them.
2. **VPS-side credential test ≠ runner-side credential test.** Gate.io API keys can be IP-locked; runner IP isn't whitelisted, so `validate-secrets.yml` from the runner always returns FORBIDDEN. Only the VPS-side check is authoritative.
3. **`git pull` on a long-running mirror repo is unsafe.** Force-sync (`git fetch + reset --hard origin/main`) is the right pattern for an authoritative one-way deploy mirror.
4. **`appleboy/ssh-action` failed silently on `issues.labeled` triggers.** Direct `ssh` command with `-o StrictHostKeyChecking=no` and `if: always()` on cleanup steps gave visible failure modes.
5. **9-refusals-log existed for exactly this session's drift pressure.** Multiple prompt-style pastes asked for the literal patterns the architect had already rejected. The log + SHA256 lock held.
