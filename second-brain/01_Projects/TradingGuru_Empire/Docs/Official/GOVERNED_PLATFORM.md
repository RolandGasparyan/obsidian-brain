# GOVERNED LIVE TRADING PLATFORM

> Canonical architecture overview for tradingguru-empire. Single-page index
> of how the layers, governance, telemetry, operational toolkit, and CI gates
> fit together. Every section links to the authoritative artifact — this doc
> never duplicates spec, only navigates to it.

## 1. The 4 layers

| Layer | What it does | Where it lives | Mutation policy |
|---|---|---|---|
| **L1 — Locked Strategy** | MA50W10 entry/exit signal logic | `canary/canary_strategy.py` | SHA256-locked at `704dd57…`; never edited via prompt. Lock change = decision PR + new hash. |
| **L1.5 — Constrained Executor** | Per-account threads, order placement, risk caps, killswitches | `canary/canary_executor.py` + `canary/canary_config.json` | Bounded edits only (bugfixes, telemetry, observability). Never relax caps via chat. |
| **L2 — Telemetry** | Publishes `terminal.json` + `live_battle.json` every 60s | `canary_executor.publish_status()` → `/var/www/.../battle/` | Additive only. Schema captured by `canary/tests/test_publish_shape.py`. |
| **L3 — Cinematic** | Renders the live battle for spectators | tradingguru.ai (separate codebase) | L3 cannot modify L1/L1.5. Reads JSON, never writes back. |

The boundary L3 → L1 is structural, not a comment. There is no code path from the frontend to the executor.

## 2. Governance authorities

| Authority | File | Enforces |
|---|---|---|
| **9-refusals log** | `docs/9-refusals-log.md` | Patterns refused historically: GODMODE, autonomous self-evolution, parameter mutation on locked strategy, multi-pair USDT rotation, Kelly-on-live, pyramiding, agent identity escalation |
| **Championship rules** | `docs/CHAMPIONSHIP_RULES.md` | Operator-authored doctrine; canonical operating contract |
| **Engineering doctrine** | this doc + chat-installed "Disciplined Engineering Agent" prompt | `NEVER` list: no SHA256-lock bypass, no live risk-cap mutation, no autonomous self-evolving live trading, no chat-prompt architecture rewrites |
| **Arming artifact** | `/root/canary/canary_arm.json` (operator-authored) | Executor refuses to start without it; requires `paper_preflight_passed=true` |
| **Refusal log** | `docs/9-refusals-log.md` (append-only) | Every refused pattern preserved; reviewable across sessions |

## 3. In-process safety caps

Defined in `canary/canary_config.json` and enforced in `canary_executor.py`:

| Cap | MAIN | SUB1 | SUB2 | Mutation policy |
|---|---|---|---|---|
| `max_capital_usd` | 1579.52 | 200 | 200 | Decision PR only |
| `balance_ceiling_usd` | 1650 | 220 | 220 | Decision PR only; **caught 4 wrong-wallet pastes this week** |
| `trade_size_pct` | 6% | 9% | 9% | Decision PR only |
| `max_daily_dd_usd` | 31.59 | 4 | 4 | Decision PR only |
| `max_trades_per_day` | 6 | 6 | 6 | Decision PR only |
| `max_hold_hours` | 46 | 46 | 46 | Decision PR only |
| `max_lifetime_hours` | 720 | 720 | 720 | Decision PR only |
| `cooldown_seconds` | 1800 | 1800 | 1800 | Decision PR only |
| Killswitch artifacts | `/root/.l99/protection_halt.json`, `runtime/CANARY_HALT.json` | (same) | (same) | Out-of-band manual override |

## 4. Operational toolkit

Workflows the operator (or the assistant via labels on issue #14) can fire. All run on GitHub Actions, no chat-time auto-execution.

| Workflow | Trigger | Purpose | Bytes flow |
|---|---|---|---|
| `deploy-live-battle.yml` | label `deploy-live-battle-START` | Force-sync repo, write keyfiles from GitHub Secrets, restart service | GitHub Secrets → VPS keyfiles |
| `set-account-keys.yml` | manual `workflow_dispatch` form | Type 32-hex KEY + 64-hex SECRET in Actions UI, validates inline, writes one keyfile | Operator → VPS keyfile (never via chat) |
| `set-sub2-keys.yml` | manual `workflow_dispatch` form | Same as above but hardcoded SUB2 (no dropdown to misclick) | Same |
| `halt-account.yml` | label `halt-main`/`halt-sub1`/`halt-sub2` OR ack-string dispatch | Empty one keyfile, restart service. Targeted thread FAIL-CLOSED. | None (just deletes a file) |
| `restore-account.yml` | label `restore-main`/`restore-sub1`/`restore-sub2` | Walk `.halted-*` backups, restore the one matching the account's expected wallet size | VPS → VPS only |
| `status-report.yml` | label `status-check` | VPS diagnostic: service, keyfiles, auth, state, log tail | Read-only |
| `dashboard.yml` | label `dashboard` | Consolidated per-account view | Read-only |
| `permutation-check.yml` | label `permutation-check` | 3×3 KEY×SECRET matrix from VPS (finds swaps) | Read-only |
| `validate-secrets.yml` | label `validate-secrets` | Test GitHub Secrets from runner (IP-restricted, mostly FORBIDDEN — exists for completeness) | Read-only |
| `frontend-check.yml` | label `frontend-check` | Probe whether tradingguru.ai serves on-disk JSON byte-for-byte | Read-only |

Issue #14 is the operator-control issue. Labels are the API; comments are the result log.

## 5. CI gates (every PR)

Run on `push` to `main`/`Godmode` and on every PR by `.github/workflows/lint.yml` + `.github/workflows/test.yml`:

| Check | Behaviour | What it catches |
|---|---|---|
| `ruff` (critical) | Hard-fails on `E9,F63,F7,F82,F821,F811` (syntax, undefined names, redefinitions) | Real bugs only — style noise is informational |
| `bandit` | **PR #58 flips to hard-fail at medium+ severity/medium+ confidence** | Unhandled security findings. Suppressions require `# nosec BXXX` + justification. |
| `pip-audit` | **PR #55 added — hard-fail on any CVE in pinned manifest** | Known-CVE deps. Suppressions via `--ignore-vuln` + documented rationale. |
| `gitleaks` | **PR #57 added — hard-fail on any committed-secret pattern** | Accidentally committed API keys, JWT, SSH private keys. Suppressions via `.gitleaksignore` + reason block. |
| `test` (pytest) | Hard-fails on any test failure | Logic regressions, especially `test_publish_shape.py` (locks the L2 JSON contract) |

CI does not deploy. CI only gates merge.

## 6. Audit trail

| Artifact | Type | Purpose |
|---|---|---|
| `session-notes/2026-05-19-multi-account-live-launch.md` | append-only | First live launch + 19 PRs |
| `session-notes/2026-05-20-multi-account-api-recovery.md` | append-only | Credential paste-error recovery |
| `session-notes/2026-05-20-3-account-live-active.md` | append-only | 3-account battle finally live |
| `docs/9-refusals-log.md` | append-only | Every refused mutation pattern with verbatim quote |
| `AUDIT_REPORT_GODMODE.md` | snapshot | Security baseline (pip-audit + bandit findings logged) |
| Issue #14 comment thread | append-only | Every label-fired workflow's result |
| `.api_key_*.halted-<UTC>` files on VPS | append-only | Every halt operation's pre-state preserved for forensics |

## 7. Refused mutation patterns (verbatim from 9-refusals-log)

Patterns this platform refuses, every time, regardless of framing:

1. **GODMODE / SUPERPOWER / God-Level escalation** on `canary_strategy.py` — SHA256 lock; refusal #1
2. **Multi-pair USDT rotation** — refusal #3 (WR breakeven math fails)
3. **Self-evolving live trading** — refusal #4 (no proven edge, recovery-factor martingale risk)
4. **Parameter mutation on locked MA50W10** — refusal #5 (sizing %, DD cap, cooldown, max trades)
5. **GODMODE + SafeScaling + SelfEvolve mega-paste** — refusal #7
6. **New live agents** (HUNTER/RISK/EXECUTOR personalities) — paper-only until paper-port + decision PR
7. **Tripled trading cycles** / "trade more aggressively" via chat — refused
8. **Architecture rewrites via chat-paste master prompt** — refused
9. **Bloomberg + Twitch + LoL + F1 in one chat** — refused as scope explosion

The legitimate path for any of the above: paper-port flow → operator-authored decision PR under `docs/decisions/` → new SHA256 lock per strategy → separate deploy PR → manual operator approval.

## 8. Recovery playbook

| Symptom | Action | Workflow / label |
|---|---|---|
| One account's keyfile holds wrong credentials | `halt-<acct>` label | halt-account.yml |
| Halted account had correct creds in a backup | `restore-<acct>` label | restore-account.yml (auto-picks by wallet size) |
| Need to verify the live JSON feeds tradingguru.ai | `frontend-check` label | frontend-check.yml |
| Suspected swapped secrets across accounts | `permutation-check` label | permutation-check.yml |
| Whole-bot stop | SSH to VPS: `systemctl stop canary-battle.service` | Manual |
| Whole-bot disarm | Write `canary_arm.json` with `paper_preflight_passed: false` | Manual |
| Strategy compromise (hash mismatch) | L99 halt: write `/root/.l99/protection_halt.json` with `"halted": true` | Manual |

## 9. What this platform is NOT

- Not a research lab. New strategies go through paper-port flow first.
- Not a casino. Daily-DD caps are absolute, not advisory.
- Not autonomous. Every cap mutation, strategy swap, or live deploy requires operator action.
- Not "live evolving." The strategy is locked. The scoreboard is dynamic.
- Not under chat control. Chat ships PRs; chat does not directly modify the executor.

## 10. Where to look next

- New to the system: read `docs/CHAMPIONSHIP_RULES.md` first.
- Operating an incident: §8 above + issue #14.
- Auditing safety: §3 + `canary/canary_config.json`.
- Reviewing refusals: `docs/9-refusals-log.md`.
- CI gates: `.github/workflows/{lint,test}.yml`.
- Live status right now: fire `dashboard` label on issue #14.

---

This document is the index. Authority lives in the linked files.
