# ops/

Operator-facing tools. Default posture is **VERIFY-ONLY**.

## Zone model

```
SAFE ZONE
---------
read-only
verify-only
telemetry only

GUARDED ZONE
------------
state mutation
requires explicit CONFIRM=YES
isolated from monitoring layer
```

## command-center.sh

Single entry point for the live battle host. Replaces the ad-hoc command list
the operator was pasting into the shell.

```
ops/command-center.sh <subcommand>
```

### SAFE ZONE (read-only)

| Subcommand       | What it does                                         |
| ---------------- | ---------------------------------------------------- |
| `status`         | Disclosure + live banner + service state             |
| `service`        | `systemctl status canary-battle.service`             |
| `tail`           | `tail -F` on `battle.log`                            |
| `champions`      | Last 50 MAIN / SUB1 / SUB2 lines                     |
| `pnl`            | Last 50 PnL / DD / Sharpe / balance lines            |
| `exec`           | Last 50 BUY / SELL / LONG / SHORT lines              |
| `failclosed`     | Last 20 FAIL-CLOSED events                           |
| `invalidkey`     | Last 20 INVALID_KEY events                           |
| `rollback-log`   | Last 20 ROLLBACK events                              |
| `governance`     | `cat /root/.l99/protection_halt.json`                |
| `halt-state`     | Show CANARY_HALT.json state (does not modify)        |
| `processes`      | `pgrep -a canary`                                    |
| `restart-policy` | Show `Restart=` from `systemctl show`                |
| `watch`          | Live dashboard refresh                               |
| `dashboard`      | `gh workflow run dashboard.yml`                      |
| `frontend`       | `gh workflow run frontend-check.yml`                 |
| `request`        | Interactively log a manual operator request          |
| `mode <NAME>`    | Switch runtime profile banner / env (see below)      |
| `l3`             | Print L3 championship layer config (cinematic)       |
| `leaderboard`    | Cinematic placeholder leaderboard (NOT live data)    |
| `battle`         | FINAL LIVE DEPLOY init: real SHA256 verify + governance + service + snapshot + hand-off to `watch` (FINAL LIVE ARENA overlay). Skip the watch loop with `BATTLE_SKIP_WATCH=1`. |
| `signals`        | Wider read-only signals view: UTC ts + grep on BUY/SELL/ENTRY/SIGNAL/EXECUTED/filled + `pgrep canary_executor.py`. Superset of `exec`. |

#### Runtime profiles (`mode`)

| Mode                 | Sets                                                         |
| -------------------- | ------------------------------------------------------------ |
| `SAFE`               | `SYSTEM_MODE=VERIFY_ONLY`, `WATCH_INTERVAL=10`, `TELEMETRY_LEVEL=NORMAL` |
| `AGGRESSIVE_MONITOR` | `SYSTEM_MODE=VERIFY_ONLY`, `WATCH_INTERVAL=1`, `TELEMETRY_LEVEL=HIGH`    |
| `SHADOW_ARENA`       | `VERIFY_ONLY` + `CHAMPIONSHIP_OVERLAY=1`, `LIVE_SCOREBOARD=1`, `TELEMETRY_LEVEL=MAX` |
| `OPS`                | `SYSTEM_MODE=OPERATOR`, `ENABLE_GUARDED_ZONE=1` (informational only — `CONFIRM=YES` is still the sole GUARDED ZONE gate) |
| `WARROOM`            | `SYSTEM_MODE=WARROOM`, `WATCH_INTERVAL=1`, `LIVE_WATCH=1`, `TELEMETRY_LEVEL=MAX` |
| `LIVE`               | `SYSTEM_MODE=LIVE`, `WATCH_INTERVAL=2`, `TELEMETRY_LEVEL=MAX`, `LIVE_BANNER=1` — operator-console live-watch posture. **Does NOT change** the trading state, SHA256 lock, or per-account caps. CONFIRM=YES still gates every GUARDED action. |

`mode` is pure SAFE ZONE — it only sets env vars and prints a banner. No
mode grants new execution power; the GUARDED ZONE is always gated by
`CONFIRM=YES`.

When invoked via `ops/command-center.sh mode SAFE`, the env exports only
live in the subshell. To set the operator's interactive shell profile,
source the script and call the function:

```
source ops/command-center.sh
switch_mode SAFE
```

#### L3 championship layer (`l3`, `leaderboard`)

The L3 layer is a **cinematic competition overlay** for display purposes
only. It does **not** grant per-account strategy variants, alter execution,
or change governance. The underlying strategy on every account is the same
SHA256-locked `MA50W10`.

- `l3` — prints the L3 config (rounds, score categories, titles). Exports
  the env vars listed below into the current subshell. To persist into the
  interactive shell, source the script and call `enable_l3_battle`.
- `leaderboard` — runs `ops/scoring.py` against `${BATTLE_LOG}`, parses
  per-account PnL / Sharpe / DD / executions / failures, computes scores
  across all enabled categories, prints a ranked leaderboard with title
  assignments, and brackets it with the cinematic disclosure. If `python3`
  is missing or the scorer fails, falls back to a clearly-labelled
  cinematic placeholder. The underlying strategy on every account remains
  the same SHA256-locked `MA50W10` — the leaderboard is presentation only.

#### Scoring (ops/scoring.py)

Stdlib-only Python module that parses `battle.log` and ranks accounts.
Recognises both the real `canary_executor.py` log format
(`[asctime][main|sub1|sub2] ... pnl=$0.42 ...`) and the operator's
`MAIN ... PnL +0.42 ...` token style.

| Category    | Metric                                  | Direction |
| ----------- | --------------------------------------- | --------- |
| `pnl`       | latest PnL sample                       | higher    |
| `sharpe`    | latest Sharpe sample                    | higher    |
| `survival`  | latest DD sample                        | lower     |
| `stability` | population stdev of all PnL samples     | lower     |
| `execution` | exec / (exec + fail-closed)             | higher    |
| `recovery`  | 1 / (1 + fail-closed count)             | higher    |

Each enabled category contributes 1..N points (top = N, bottom = 1).
Categories with no data across all accounts are skipped. `SCORE_*=0`
disables a category. Tie-break on final ranking is latest PnL desc.

Run standalone:

```
python3 ops/scoring.py --battle-log /path/to/battle.log
```

| Env var              | Default          |
| -------------------- | ---------------- |
| `ENABLE_L3_BATTLE`   | `1`              |
| `SCORE_PNL`          | `1`              |
| `SCORE_SHARPE`       | `1`              |
| `SCORE_STABILITY`    | `1`              |
| `SCORE_SURVIVAL`     | `1`              |
| `SCORE_EXECUTION`    | `1`              |
| `SCORE_RECOVERY`     | `1`              |
| `TITLE_PNL_KING`     | `MONEY EMPEROR`  |
| `TITLE_SHARPE`       | `PRECISION KING` |
| `TITLE_SURVIVAL`     | `SURVIVAL TITAN` |
| `TITLE_SPEED`        | `MOMENTUM HUNTER`|
| `MICRO_ROUND_MIN`    | `15`             |
| `BATTLE_ROUND_MIN`   | `60`             |
| `WAR_ROUND_HOURS`    | `6`              |

### GUARDED ZONE (require `CONFIRM=YES`)

| Subcommand | What it does                                          |
| ---------- | ----------------------------------------------------- |
| `halt`     | Write soft-halt file `CANARY_HALT.json`               |
| `unhalt`   | Remove soft-halt file                                 |
| `stop`     | `systemctl stop canary-battle.service`                |
| `start`    | `systemctl start canary-battle.service`               |
| `rollback` | Invoke `canary/rollback_deploy.sh MANUAL_ABORT`       |
| `battle-restart` | `systemctl restart canary-battle.service` (no interactive prompt — gated by `CONFIRM=YES` only) |

Example:

```
CONFIRM=YES ops/command-center.sh halt
CONFIRM=YES ops/command-center.sh battle-restart
```

### `battle` and `battle-restart`

`battle` is the disciplined replacement for ad-hoc "FINAL LIVE DEPLOY" /
"AGGRESSIVE BATTLE START" paste scripts:

| | Old pattern (paste-script) | `battle` subcommand |
| --- | --- | --- |
| SHA256 check | prints a truncated prefix | actually runs `sha256sum` and compares to the full lock |
| Mismatch handling | (no check, so none) | prints `MISMATCH — drift detected; DO NOT deploy`, continues in observe-only mode |
| Service restart | `read -p` y/n prompt mid-flow | NOT in `battle` — a separate GUARDED subcommand `battle-restart` |
| Restart gating | a keypress | `CONFIRM=YES` env var (explicit, scriptable, refuses with exit 2 otherwise) |
| Watch loop | inline `watch` invocation | hands off to existing `cmd_watch` |

```
# SAFE — verify + governance + service state + snapshot + watch
ops/command-center.sh battle

# Verify + status only (skip the watch loop, useful for cron / final report)
BATTLE_SKIP_WATCH=1 ops/command-center.sh battle

# GUARDED — explicit service restart
CONFIRM=YES ops/command-center.sh battle-restart
```

`battle-restart` validates that `SERVICE_NAME == canary-battle.service`
before acting (defends against `SERVICE_NAME` mis-pointing), prints a
`DANGER-ZONE EXECUTION` banner, restarts, and prints the post-restart
`is-active` state.

Without `CONFIRM=YES`, GUARDED ZONE subcommands refuse with exit 2 and a
clear "REFUSED" banner. They are operator-driven only — there is no
automation path that can trigger them from the monitoring layer.

### GUARDED ZONE input validation

Before any state mutation, the script validates:

| Check | Applies to | Refusal |
| ----- | ---------- | ------- |
| `CONFIRM=YES` env | all | exit 2, prints REFUSED banner |
| Target is regular file (not symlink, not dir) | `halt`, `unhalt` | exit 1 |
| Basename matches `CANARY_HALT.json` | `halt`, `unhalt` | exit 1 |
| Runtime dir exists (no auto-create) | `halt` | exit 1 |
| Rollback script is regular non-symlink executable | `rollback` | exit 1 |
| Rollback basename is `rollback_deploy.sh` | `rollback` | exit 1 |
| Rollback path resolves under `CANARY_REPO_DIR` | `rollback` | exit 1 |

Every successful GUARDED ZONE action prints a `DANGER-ZONE EXECUTION` banner
with action / target / host / user / time before the side effect, so the
post-incident transcript shows exactly what ran and who ran it.

### Source-guard

`main` runs only when the file is executed directly. Sourcing the file
(`source ops/command-center.sh`) loads the helpers without executing
any subcommand — useful for tests, won't trigger side effects.

### Configuration

All host paths are overridable via env so the script can be tested off-host
without touching production:

| Variable                 | Default                                           |
| ------------------------ | ------------------------------------------------- |
| `CANARY_RUNTIME_DIR`     | `/root/canary/runtime`                            |
| `CANARY_REPO_DIR`        | `/root/tradingguru-empire`                        |
| `PROTECTION_HALT`        | `/root/.l99/protection_halt.json`                 |
| `OPERATOR_REQUESTS_DIR`  | `/root/canary/operator_requests`                  |
| `BATTLE_LOG`             | `${CANARY_RUNTIME_DIR}/battle.log`                |
| `CANARY_HALT_FILE`       | `${CANARY_RUNTIME_DIR}/CANARY_HALT.json`          |
| `SERVICE_NAME`           | `canary-battle.service`                           |
| `ROLLBACK_SCRIPT`        | `${CANARY_REPO_DIR}/canary/rollback_deploy.sh`    |

### Governance posture

- Cinematic labels (`TITAN`, `VELOCITY`, `SENTINEL`) are display-only.
- All three live accounts execute the **same** SHA256-locked `MA50W10`
  strategy. This script does not select per-account strategy variants.
- NO-DRIFT LAW: this script does **not** mutate strategy, bypass governance,
  or grant autonomous evolution. GUARDED ZONE actions are explicit operator
  actions, logged via `request` where applicable.
- `research/` contains isolated frameworks (e.g. `research/tradingagents/`)
  that are **not** wired into live execution. See
  `governance/ADR-005-tradingagents-integration.md` for the integration
  policy.

### Lint / verification

```
shellcheck -x ops/command-center.sh      # clean on default ruleset
bash -n ops/command-center.sh            # syntax OK
```

## Mac operator bundle

`command-center.sh` is designed to run **on the VPS**. The Mac operator
bundle gives you two thin layers on top:

```
ops/mac-control.sh   →  SSH dispatcher: forwards subcommands to the VPS
ops/mac-local.sh     →  offline tools: SHA256 verify, frontend, ticker, strix
```

Neither script mutates strategy, governance, or capital. The GUARDED ZONE
on the VPS still requires `CONFIRM=YES`; `mac-control.sh` also enforces
the same gate locally before it opens an SSH session.

### One-time setup (Mac)

```bash
# Clone the repo
git clone https://github.com/RolandGasparyan/tradingguru-empire.git ~/tradingguru-empire
cd ~/tradingguru-empire

# Confirm the strategy SHA256 lock is intact locally
ops/mac-local.sh verify

# Optional: pre-set SSH config so 'btc-15m-paper-bot' resolves
# (~/.ssh/config)
#   Host btc-15m-paper-bot
#     HostName 167.71.24.86
#     User root
#     IdentityFile ~/.ssh/id_ed25519
#     ConnectTimeout 10

# Optional: persistent env for mac-control.sh
mkdir -p ~/.tradingguru-empire
cat > ~/.tradingguru-empire/mac-control.env <<'ENV'
VPS_HOST=btc-15m-paper-bot
VPS_USER=root
SSH_OPTS="-o ConnectTimeout=10"
REPO_DIR_VPS=/root/tradingguru-empire
ENV

# Verify SSH + remote console reachability
ops/mac-control.sh doctor
```

### mac-control.sh (SSH dispatcher)

Forwards SAFE subcommands directly. GUARDED subcommands require
`CONFIRM=YES` on the Mac AND the same env is forwarded to the VPS so the
remote `command-center.sh` enforces its own gate (defence in depth).

```bash
# SAFE — read-only
ops/mac-control.sh status
ops/mac-control.sh tail
ops/mac-control.sh leaderboard
ops/mac-control.sh pnl
ops/mac-control.sh governance
ops/mac-control.sh battle           # aggressive-monitoring init + watch

# Mac-only
ops/mac-control.sh doctor      # check config + ssh + remote ops/
ops/mac-control.sh final       # championship aggregated report

# GUARDED — must confirm
CONFIRM=YES ops/mac-control.sh halt
CONFIRM=YES ops/mac-control.sh unhalt
CONFIRM=YES ops/mac-control.sh battle-restart
```

### mac-local.sh (offline tools)

Runs without the VPS — useful when on the road or when the host is down.

```bash
ops/mac-local.sh verify        # canary_strategy.py SHA256 vs lock
ops/mac-local.sh frontend      # open tradingguru.ai
ops/mac-local.sh ticker BTC_USDT
ops/mac-local.sh strix         # security audit loop (bin/strix-watch.sh)
ops/mac-local.sh sync          # git pull origin main --ff-only
ops/mac-local.sh refusals      # print docs/9-refusals-log.md
ops/mac-local.sh adrs          # list ADRs + refused_proposals
```

### `final` — championship report

`mac-control.sh final` is the end-of-championship aggregator. It is fully
read-only and combines:

| Section          | Source                                            |
| ---------------- | ------------------------------------------------- |
| Strategy (local) | `shasum -a 256 canary/canary_strategy.py`         |
| Strategy (VPS)   | `sha256sum` over the same file on the VPS         |
| Leaderboard      | `ops/command-center.sh leaderboard` (real scoring)|
| Governance       | `/root/.l99/protection_halt.json`                 |
| Soft halt        | `CANARY_HALT.json`                                |
| Service          | `systemctl status canary-battle.service`          |
| PnL events       | last 50 PnL / DD / Sharpe lines from `battle.log` |
| Fail-closed      | last 20 `FAIL-CLOSED` events                      |
| Restart policy   | `systemctl show ... Restart=`                     |

Both SHA256 readings are compared to the lock:
`704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143`.
Mismatch on either side does NOT mutate anything — it prints a clear
`MISMATCH` line so the operator can decide.

### Mac-side exit codes

| Exit | Meaning                                                          |
| ---- | ---------------------------------------------------------------- |
| 64   | unknown subcommand / drifted SHA256 (local verify)               |
| 65   | GUARDED subcommand invoked without `CONFIRM=YES`                 |
| 66   | required local file missing (strategy, strix-watch.sh, …)        |
| 70   | required tool missing (`shasum`/`sha256sum`/`curl`) or SSH down  |
| 71   | empty / failing network response, or remote `command-center.sh` missing |

### Governance posture (Mac side)

- The Mac scripts inherit every refusal in `docs/9-refusals-log.md`.
- No autonomous mutation, no strategy evolution, no governance bypass —
  the Mac layer is a remote terminal and a verifier, nothing more.
- Cinematic labels (TITAN / VELOCITY / SENTINEL) remain display-only.
- The SHA256 lock applies on BOTH sides: any drift fails verification.
