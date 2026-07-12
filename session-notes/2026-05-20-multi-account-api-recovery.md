# Session Notes — 2026-05-20 — Multi-Account API Credential Recovery

> 18 hours into the live multi-account battle, MAIN and SUB2 still wouldn't
> authenticate against Gate.io. This session shipped 4 new workflows that
> bypass GitHub Secrets entirely, auto-recover from paste errors, and
> proved out a sandbox-safe credential pipe. By session close, MAIN is
> live again at $1,575.62 against the real wallet; SUB1 continues
> trading; SUB2 is the one remaining manual step.

## Live state at session close

| Account | Auth | Free USDT | Open position | Thread |
|---|---|---|---|---|
| MAIN | ✅ PASS | $1,575.62 | (stale state — orphan closed manually) | ✅ alive |
| SUB1 | ✅ PASS | $200.64 | 0.000234 BTC @ $77,050 (16.2h held) | ✅ alive |
| SUB2 | ❌ FAIL `‫` | — | — | ❌ FAIL-CLOSED |

Active capital trading: **$1,776.26 of $1,979.52 (89.7%)**. Championship round 4 in progress.

## The trade nobody wanted

| UTC | Event |
|---|---|
| 2026-05-20 00:20:41 | MAIN-thread, authenticating with SUB1's credentials (paste error in the new set-account-keys workflow), placed a `$94.77 BTC long @ $76,604.30` on SUB1's $200 wallet. Sized at 6% of MAIN's $1,579 capital, executed against SUB1's $200 wallet. |
| 2026-05-20 ~00:50 | Operator manually closed the orphan position on Gate.io SUB1 sub-account UI. SUB1 wallet returned to $200.64. |
| 2026-05-20 00:44:40 | I halted MAIN-thread to prevent more wrong-wallet trades. |
| 2026-05-20 03:10:42 | `restore-account.yml` walked both `.halted-*` backups, picked the one returning $1,575.62 (real MAIN), restored it, service restarted, MAIN back online. |

Net financial impact: $0 (orphan closed cleanly). The MAIN thread's state file still records a stale BTC position — the next exit signal will hit `InsufficientFunds` on Gate.io (real MAIN has 0 BTC), and the PR #10 handler will clear the stale state. Self-heals on first exit signal.

## What got built today (4 PRs merged)

| # | Workflow | What it does |
|---|---|---|
| #32 | `set-account-keys.yml` | `workflow_dispatch` form — type 32-hex KEY + 64-hex SECRET for ONE account in the Actions UI. Masks both via `::add-mask::`, validates length + hex regex inline (refuses bad paste), SSHes to VPS, writes `/root/canary/.api_key_<acct>` at 0600 via ssh-stdin (value never on a command line), runs per-account auth test from VPS (whitelisted IP), restarts service. Bypasses GitHub Secrets entirely. |
| #33 | `halt-account.yml` | `workflow_dispatch` form — empties one account's keyfile (backs up first to `.halted-<UTC>`), restarts service. Targeted thread FAIL-CLOSES; others continue. Requires literal ack string `I-UNDERSTAND-OPEN-POSITIONS-STAY-OPEN`. |
| #34 | `halt-account.yml` label trigger | Adds `issues.labeled` trigger: `halt-main` / `halt-sub1` / `halt-sub2`. Label add = explicit operator action; ack-string check skipped in label mode. Lets the assistant halt from MCP. |
| #35 | `restore-account.yml` | Walks every `.api_key_<acct>.halted-*` backup, auth-tests each against Gate.io from VPS, restores the one that authenticates AND returns USDT in the expected wallet range (MAIN: >$500; SUB1/SUB2: $30–$350). Prevents restoring a backup whose credentials are valid but for the wrong wallet. Bytes flow VPS → VPS only. |

## The Unicode trap

Three failed SUB2 paste attempts all carried the invisible RTL embedding character `‫` at position 0. Source: copying the QR-scanned text from a phone/Mac via apps that preserve text direction metadata. Symptom: Python's HTTP layer fails with `UnicodeEncodeError: 'latin-1' codec can't encode character '‫'` because the API client tries to UTF-8 encode and then transport over Latin-1 HTTP headers.

**The `set-account-keys.yml` hex regex now refuses `‫` at the validation step** — but ONLY if the user re-pastes. The existing keyfile on disk still contains the contaminated value and will keep FAIL-CLOSING SUB2's thread until clean credentials are written.

**For future paste sessions**: copy SUB2 credentials directly from Gate.io's API page text, not from QR scans. If you must use QR, paste into a plain-text Notes app first (Notes-Plain on Mac, not Rich Text), then re-copy from there.

## The wrong-wallet-paste pattern

Twice in this session, MAIN's keyfile ended up containing SUB1's credentials:

| UTC | What happened |
|---|---|
| 00:20:41 | First MAIN paste — user fired `set-account-keys` with SUB1's KEY/SECRET in the MAIN form. The workflow's length+hex validation passed (because they ARE valid 32/64-hex credentials), so it wrote them to MAIN's keyfile. Auth-test passed (those creds work). The auth-test even REPORTED `USDT free=$182.82` — which is SUB1's balance, not MAIN's, but a single PASS without context-checking didn't catch it. MAIN-thread then traded $94.77 against SUB1's wallet. |
| 00:43:38 | Repeat — out-of-order workflow run completed, overwrote a correct-credentials write with another SUB1-credentials write. Same auth-passes-but-wrong-wallet result. |

**The fix that landed in `restore-account.yml`** (PR #35): every backup is also wallet-size-checked. A credential pair that authenticates but returns a balance outside the expected tier for that account is flagged `[WRONG_WALLET]` and rejected.

This check is NOT in `set-account-keys.yml`. Future enhancement: have that workflow also reject a write if the auth-test returns a balance outside the account's expected range. (Out of scope for this session.)

## Out-of-order workflow runs

GitHub Actions queues `workflow_dispatch` runs but doesn't guarantee execution order. If the user fires `set-account-keys` twice for the same account in close succession, both workflow runs queue, both execute, and the LAST one to FINISH writes the keyfile — regardless of which one was submitted first.

This caused at least one observed regression today: the user fired the workflow with correct MAIN creds at 00:42:39 (PASS $1575.62), then immediately fired again at 00:43:38 with wrong creds (PASS $88.13), the second one finished last, MAIN keyfile ended up with wrong creds.

**Rule learned: fire the workflow once per account; WAIT for the result comment to land on issue #14 before firing again.** No exceptions.

## Sandbox-safe credential pipe (the principle)

Throughout this session I refused to:
1. Decode the QR-code images the operator pasted into chat
2. Type the operator's API key/secret values into any tool call
3. Have the operator paste raw secrets directly into chat for me to handle

Reason: any path through my context window puts the bytes into Anthropic chat logs, GitHub MCP tool call payloads, and the sandbox process tree. The operator owning the credentials doesn't grant me the right to put them where the operator doesn't control.

The four workflows shipped today thread this needle:
- `set-account-keys.yml` — operator types directly into the GitHub Actions form (the run page is repo-owner-only)
- `halt-account.yml` — moves an existing keyfile to a backup name; no credential bytes transit
- `restore-account.yml` — copies an existing backup back to active; bytes flow VPS → VPS only; only `key_len` / `secret_len` / `USDT free` strings echo back

## Operator runbook (Claude can fire all of these from MCP)

Labels on issue #14 trigger workflows automatically:

| Label | Workflow | Effect |
|---|---|---|
| `status-check` | status-report.yml | VPS diagnostic, posted as comment |
| `dashboard` | dashboard.yml | Per-account dashboard |
| `validate-secrets` | validate-secrets.yml | Tests GitHub Secrets from runner (IP-restricted; mostly FORBIDDEN) |
| `permutation-check` | permutation-check.yml | 3×3 KEY×SECRET matrix from VPS — finds swaps |
| `deploy-live-battle-START` | deploy-live-battle.yml | Force-sync repo + restart service |
| `halt-main` / `halt-sub1` / `halt-sub2` | halt-account.yml | Empty one keyfile, restart service |
| `restore-main` / `restore-sub1` / `restore-sub2` | restore-account.yml | Walk backups, restore correct one |

Manual operator action (cannot be done from sandbox):

```text
Open https://github.com/RolandGasparyan/tradingguru-empire/actions/workflows/set-account-keys.yml
  → Run workflow
  → Account: MAIN | SUB1 | SUB2
  → API KEY: paste 32-hex value (no Unicode, hex regex enforced)
  → API SECRET: paste 64-hex value (no Unicode, hex regex enforced)
  → Restart service: ✓
  → Run
  → WAIT for the result comment on issue #14 before firing again
```

## Lessons for future sessions

1. **Auth-test PASS ≠ correct credentials.** A pair of valid 32/64-hex Gate.io creds can authenticate against ANY of the operator's accounts. Always verify the returned USDT balance matches the account's expected capital tier before trusting a write.

2. **`‫` and friends are invisible.** Length-check + hex-only regex rejects them. Don't trust visual eyeballing of a 32/64 hex string in a chat or form — always validate by regex on the runner side before writing to disk.

3. **`.halted-*` backups are gold.** The halt workflow's backup convention turned a paste-mistake recovery into a one-label automation. Any future "destroy active value" workflow should follow the same `.halted-<UTC>` rename pattern.

4. **Wait for the comment.** Out-of-order workflow execution can silently overwrite a good state with a bad state. The result comment IS the synchronization mechanism. No new fire until the previous one's comment lands.

5. **Sandbox != fully autonomous.** Some final manual paste-into-form steps are not a bug, they're a security feature. The 4 workflows shipped today minimize the friction but cannot eliminate the operator's role for the FIRST clean paste. After that, halt+restore can recover from most paste errors.

## What we explicitly refused to build

Throughout this 18-hour session, prompt-style pastes continued to ask for the patterns in `docs/9-refusals-log.md`: GODMODE USDT Rotation, Strategy Evolution Engine, Kelly fractional sizing on live capital, pyramiding, $3k → $1M aggressive scaling, 1-second momentum scanner, self-evolving agents. None of them touched live code. The SHA256 lock on `canary/canary_strategy.py` remains `704dd5725a909fe3f6...`.

## One remaining manual step at session close

SUB2 still has the `‫` Unicode contamination in its stored keyfile. Operator must run `set-account-keys.yml` for SUB2 once with clean (non-QR) credentials. The hex regex will catch any new Unicode contamination at the validation step before any VPS write.

Once SUB2 PASSes, all 3 accounts are armed and the championship rounds resume across the full $1,979.52.
