# FINAL VERIFY AUDIT — `Godmode` branch

**Branch:** `Godmode`
**Base:** `main` @ `e6c6854`
**Scope:** Sandbox-executable work only. SSH-dependent and test-coverage-dependent steps are flagged below and **not** completed.
**Generated:** 2026-05-19
**Auditor:** Claude Code, sandbox session

---

## Executive verdict: **NO-GO**

Live deploy from `Godmode` to production is **not authorized by the data**. The merge/tag/deploy actions specified in the source prompt would be ceremony, not engineering. See § "Final Deploy Gate (honest)" below.

A live MA50W10 bot is currently running on `main` @ `e6c6854` on droplet `btc-15m-paper-bot` (164.71.24.86). Nothing on `Godmode` displaces it, and nothing in this audit produces evidence to displace it.

---

## 1. Repo audit — completed

| Item | Result |
|---|---|
| `main` HEAD | `e6c6854` "fix(canary): sync executor + config to /root/canary/ on setup (#3)" |
| Duplicate squash commit on main | `e6024c0` (race during PR #3 merge — harmless, identical tree) |
| `Godmode` branch | **Created in this audit** (didn't exist before). Based on `main`. |
| Open PRs | #4 — DRAFT paper-port harness, scaffolds only, will not auto-merge |
| Stale branches | `claude/check-all-wk6vA` (PR #2 merged), `claude/fix-setup-deploy` (PR #3 merged), `RolandGasparyan-patch-1` — all candidates for cleanup |
| Conflicts | None detected |

---

## 2. Dependency & security audit — completed

### 2.1 Dependency manifest

**No `requirements.txt`, `pyproject.toml`, `package.json`, `Pipfile`, or `setup.py` existed on the repo before this audit.** Dependencies have been installed ad-hoc on the VPS. This commit adds the first `requirements.txt`.

### 2.2 ruff lint (whole tree)

```
Found 156 errors total. Critical categories (F821, F811, E9, F63, F7, F82): 0.
  102  E701  multiple-statements-on-one-line-colon       stylistic
   20  E702  multiple-statements-on-one-line-semicolon   stylistic
   14  E402  module-import-not-at-top-of-file            mostly intentional (sys.path manipulation)
   10  F841  unused-variable                             cleanup candidate
    9  E722  bare-except                                 should be tightened to specific exceptions
    1  E741  ambiguous-variable-name                     cleanup candidate
```

No NameError / undefined-name / syntax errors. Codebase compiles.

### 2.3 bandit security scan (codebase)

```
Total lines scanned: 8,898
By severity:
  High    : 0
  Medium  : 3
  Low     : 35
```

**3 actionable Medium findings** (all `B310: urllib.urlopen — audit permitted schemes`):

| File | Line | Risk |
|---|---|---|
| `arena_shadow_runner.py` | 112 | `urllib.urlopen` over a URL string — should validate scheme is `https://` only before opening |
| `paper_battle/shadow_round.py` | 251 | same |
| `paper_battle/shadow_round.py` | 872 | same |

All three fetch `https://api.gateio.ws/api/v4/spot/tickers` with a hardcoded URL, so real risk is low. Fix: validate scheme explicitly, or `# nosec B310` with a comment justifying the static URL.

### 2.4 CVE scan (pip-audit)

`pip-audit` cannot scan this repo — no manifest existed prior to this commit. As a proxy, the **sandbox's** Python environment was scanned:

```
Found 18 known vulnerabilities in 6 packages (sandbox env, NOT the VPS):
  cryptography 41.0.7  →  fix: 42.0.0+ (multiple CVEs incl. CVE-2023-50782, CVE-2024-0727)
  pip          24.0    →  fix: 25.3+
  pyjwt        2.7.0   →  fix: 2.12.0
  setuptools   68.1.2  →  fix: 70.0.0+
  urllib3      2.6.3   →  fix: 2.7.0
  wheel        0.42.0  →  fix: 0.46.2
```

**Important: the above is the sandbox env, not the VPS.** I cannot scan the VPS from here. After the new `requirements.txt` is installed on the VPS, run `pip-audit` there and address findings.

### 2.5 Node.js audit

Not applicable. No `package.json`, no Node code in this repo.

### 2.6 semgrep

Not installed in sandbox. The ruff `S*` checks cover the most common semgrep rules (S110 bare-except, S307 eval, etc.).

---

## 3. Updates & upgrades — **partially refused as written**

| Sub-step | Status |
|---|---|
| Pin in requirements.txt | ✅ done (this commit) |
| Pin in package.json | N/A (no Node code) |
| Update Python to 3.12+ | ❌ **Refused.** Live bot is currently running Python 3 on the VPS (whatever's there). I cannot SSH from this sandbox to change it. Switching Python under a running trading process is risky and outside this PR's scope. |
| Regenerate lockfiles | Deferred — `requirements.txt` is the first manifest; a follow-up commit can produce `requirements.lock` via `pip-compile` once dependency set is stable. |
| Rebuild Docker images --no-cache | ❌ **Refused.** No `Dockerfile` in this repo. The deploy doesn't use containers — it runs directly under systemd as `canary-battle.service`. Inventing a Docker layer just to "rebuild" it would be theater. |

---

## 4. High-star plugins — added to requirements.txt with honesty

`requirements.txt` (this commit) categorizes the prompt's wishlist into three buckets:

| Bucket | Packages | Why |
|---|---|---|
| **Actually used** | `ccxt`, `numpy`, `ruff`, `bandit` | Imported in current code or wired into CI |
| **Dev / CI** | `pytest`, `pytest-asyncio`, `hypothesis`, `black`, `mypy`, `pip-audit` | Standard quality tooling |
| **Wishlisted, commented out** | `vectorbt`, `backtrader`, `pandas-ta`, `finta`, `python-binance`, `websockets`, `pydantic`, `fastapi`, `uvicorn`, `loguru`, `rich`, `structlog`, `APScheduler`, `celery`, `redis`, `prometheus_client`, `sentry-sdk`, `tenacity` | Adding these without using them just bloats install + threat surface. Uncomment when code actually imports them. |

`TA-Lib` deliberately omitted — requires native C library, must be installed manually on the deploy host if anyone wires it in.

`freqtrade` is not a library, it's a full bot. Including it in this repo would be a fork war.

`grafana` is not a Python package.

---

## 5. Godmode feature verify — **refused as written**

Prompt asked to confirm modules: `signal_engine`, `risk_manager`, `position_sizer`, `execution_router`, `paper_trade_layer`, `championship_scoreboard`, `telemetry`, `alerting`, `kill_switch`.

**None of these modules exist in the repo.** The actual file structure:

| Prompt module | Reality |
|---|---|
| signal_engine | inline in `canary/canary_executor.get_signal()`; also `bot/agent.py` and `paper_battle/shadow_round.py` have their own |
| risk_manager | inline in `canary/canary_executor.run_account()` (daily DD cap, trades-per-day cap) |
| position_sizer | inline: `sz = round(account["max_capital"] * account["trade_size_pct"], 2)` |
| execution_router | `canary/canary_executor.{buy,sell}()` — direct ccxt calls |
| paper_trade_layer | `paper_battle/shadow_round.py` + `paper_battle/paper_battle_engine.py` |
| championship_scoreboard | `canary/canary_executor.publish_status()` writes to `/var/www/.../battle/live_battle.json` |
| telemetry | logs to `battle.log` via stdlib logging |
| alerting | none — no email/webhook/discord |
| kill_switch | `canary/canary_killswitch.py` exists (230 lines) but is not currently imported by `canary_executor.py`; killswitch logic lives in the L99-halt file check |

Building those 9 modules cleanly is a multi-week refactor. I will not pretend they're done.

### Test coverage ≥ 85% — **refused**

There are **zero pytest tests** in this repo. Achieving 85% line coverage requires writing ~thousands of lines of new test code against a ~3,000-line bot. That is not a "Final Verify" step. The new `test.yml` workflow runs:

1. `python -m compileall .` (syntax)
2. `canary/check_agents.py --offline` (config/state/logic preflight)
3. `pytest` only if test files exist (currently zero)

This is honest scaffolding. Don't claim 85% coverage that doesn't exist.

---

## 6. DigitalOcean droplet prep — **CANNOT EXECUTE FROM SANDBOX**

| Sub-step | Status |
|---|---|
| `ssh root@... apt update && apt upgrade -y` | ❌ No SSH from this sandbox. Confirmed earlier in session. |
| Verify systemd `btc-15m-paper-bot.service` | ❌ Need SSH. (Note: the actual service unit is named `canary-battle.service`, not `btc-15m-paper-bot.service` as the prompt says.) |
| ufw / fail2ban / unattended-upgrades | ❌ Need SSH. |
| Verify `.env` not committed | ✅ Sandbox-checkable — confirmed: no `.env` in repo, `.gitignore` excludes secrets, `/root/canary/.api_key_*` files only exist on the VPS (perms 0600) |
| Cron / healthcheck / log rotation | ❌ Need SSH. |

**Honest path:** You SSH in and run these yourself. I can hand you a one-liner script if useful.

---

## 7. CI/CD — completed (with the deploy workflow deliberately stubbed)

Created on this branch:

| File | Purpose | Live risk |
|---|---|---|
| `.github/workflows/lint.yml` | ruff + bandit on every push/PR | Zero — no SSH, no deploy |
| `.github/workflows/test.yml` | compileall + check_agents.py + pytest-if-exists | Zero — no SSH, no deploy |

**Not created: `deploy-godmode.yml`.** The existing `.github/workflows/deploy-live-battle.yml` already does SSH-deploy of the MA50W10 build to the VPS. Creating a parallel `deploy-godmode.yml` that does the same thing under a different name would be dishonest naming — there is no "Godmode" build to deploy. When/if a real Godmode build exists, it can either reuse the existing workflow or get its own with explicit, non-fictional inputs.

---

## 8. Final Deploy Gate — **NO-GO on every line**

| Criterion | Status | Why |
|---|---|---|
| ☐ All tests green | **FAIL** | No tests exist (this audit added the first lint/test scaffolds, both currently passing the trivial cases) |
| ☐ No HIGH/CRITICAL CVEs | **UNKNOWN** | No VPS scan possible from sandbox. Sandbox env has 18 CVEs in 6 packages; assume the VPS env has a similar profile until you scan it. |
| ☐ Secrets rotated | **PASS** | `SSH_PRIVATE_KEY` rotated ~90 min ago after the earlier accidental disclosure. Gate.io API keys were already in GitHub Secrets and used in this morning's deploy. |
| ☐ Kill switch tested | **FAIL** | `canary/canary_killswitch.py` exists but has never been exercised end-to-end. The current "kill" path is `systemctl stop canary-battle.service` (which was accidentally invoked earlier today). |
| ☐ Paper-trade dry run 24h clean | **FAIL** | Last 3 paper rounds had **0 trades each**. Live bot has been running ~2 hours, not 24. |
| ☐ Rollback plan documented | **FAIL** | No `docs/rollback.md`. The rollback is currently "`systemctl stop`, restore `canary_arm.json.bak.*`, restart" — known to me, not written down. |

**Score: 1/6 PASS. NO-GO.**

---

## 9. Deploy — **NOT PERFORMED**

The prompt says "On GO: merge Godmode → main via PR, tag v-godmode-final, trigger deploy workflow." There is no GO. There is also nothing meaningful in `Godmode` to merge or tag at this point — this branch only contains:

- Audit artifacts (this file, `requirements.txt`)
- Two CI workflows (`lint.yml`, `test.yml`)

None of which constitute a "Godmode build" worth tagging `v-godmode-final`. Tagging this would be vanity, not engineering.

---

## Remediation plan (concrete, in priority order)

Each item is real work, not magic:

1. **Confirm the live MA50W10 bot is running.** (Still pending operator confirmation in chat — SSH in, `systemctl is-active canary-battle.service`.) Until confirmed, everything else is moot.
2. **Install `requirements.txt` on the VPS** in a fresh venv and `pip-audit` it. Address any HIGH/CRITICAL CVEs.
3. **Fix the 3 bandit B310 findings** in `arena_shadow_runner.py` and `paper_battle/shadow_round.py` (constant URL check or `# nosec B310` with justification).
4. **Write `docs/rollback.md`** with the literal commands to take the bot down and restore prior state.
5. **End-to-end exercise the kill switch.** Today. Verify `canary/canary_killswitch.py` actually halts the executor when triggered. (Currently it's import-able but not wired into `canary_executor.py` as far as I can see.)
6. **Build a real test suite** under `tests/`. Start with the pure functions: `agg_params`, `mq_to_size`, `score_pairs` (mockable), `get_signal` (mockable). Target 60% on `canary/canary_executor.py` first; the rest later.
7. **Wait out the 720h live envelope** the bot is armed for, with logging and review at 24h / 168h / 720h. Then evaluate whether to redeploy.
8. **Separately**, on PR #4: upload the strategy-lab files, run paper replays, compare against the lab's `paper_state/`. **Do not flip live to those strategies until paper port fidelity is verified.**

---

## What I refused, and why

| Step | Refused | Reason |
|---|---|---|
| 3 — Python 3.12+ on VPS, Docker rebuild | Yes | No SSH from sandbox; no Dockerfile in repo |
| 5 — 9 module verify + 85% coverage | Yes | Modules don't exist; tests don't exist; one-session fabrication is dishonest |
| 6 — apt upgrade, ufw, fail2ban, cron | Yes | No SSH from sandbox |
| 9 — merge Godmode → main, tag v-godmode-final, deploy | Yes | Nothing to merge; tagging vapor is vanity; NO-GO on every gate criterion |

What you asked for and got: the parts of the work that are honest, real, and don't endanger the running bot. Branch is `Godmode`, PR is opened as draft. Decide from there.
