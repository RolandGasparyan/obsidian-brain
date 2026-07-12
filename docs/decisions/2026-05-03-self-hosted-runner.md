# 2026-05-03 — Self-hosted GitHub Actions runner on VPS for research scripts

**Type:** decision
**Status:** decided · runner registration pending operator
**Linked log entry:** [[log#2026-05-03-self-hosted-runner]]
**Linked finding:** [[findings/2026-05-03-b21-ensemble-shipped]]

## Context

`phase_b_ensemble.py` (B.2.1 multi-feature ensemble) needs to run against the live microstructure parquet at `/var/log/microstructure` on the VPS. The Claude Code session has no SSH or network access to the VPS by design (correct sandbox isolation). Operator was asked which path to take:

| Option | What |
|---|---|
| Manual SSH + paste output | Operator runs ad-hoc, pastes back |
| **GitHub Actions self-hosted runner** ← chosen | Workflow dispatched from GitHub UI / CLI, runs on VPS, posts result to Telegram + artifact |
| Pull data locally | Pull ~50–200 MB parquet to dev machine, run there |

Operator chose option B.

## Choice

**Adopt a self-hosted GitHub Actions runner on the VPS, restricted to manual `workflow_dispatch` only, gated by a custom label `vps-trading`.**

Concrete deliverables (this commit):

- `.github/workflows/phase-b-ensemble.yml` — manual-dispatch workflow with configurable inputs (pair, horizon, features, agreement, bootstrap days/trials)
- This decision page (incl. setup instructions for the operator)
- `wiki/log.md` and `wiki/index.md` updates

Concrete deliverables (operator, on VPS — see § "Setup steps" below):

- Register a self-hosted runner with labels `self-hosted,vps-trading`
- Install as systemd service so it survives reboots
- Verify by triggering the workflow once

## Workflow design rationale

| Decision | Why |
|---|---|
| `workflow_dispatch` only — NO `on: push` or `on: pull_request` | Research scripts shouldn't auto-fire on every commit. Bootstrap takes 10–30 min; auto-fire would burn VPS CPU on every push. Manual = explicit operator intent. |
| Runner labels `[self-hosted, vps-trading]` | Don't grab unrelated self-hosted runners if the org adds more later. The custom label pins this workflow to the trading VPS. |
| `concurrency: phase-b-ensemble` | Two parallel runs would compete for `/var/log/microstructure` read locks and double the runner CPU load. Serialise. |
| `permissions: contents: read` (default-deny) | Workflow doesn't write to the repo. Minimal token scope reduces blast radius if the runner is compromised. |
| `timeout-minutes: 90` | Bootstrap can take 10–30 min; allow buffer without leaving a hung job indefinitely. |
| Telegram notify with `--data-urlencode` and `ok:true` parse | Per CLAUDE.md hard rule #4 — verify delivery, not just notify-call success. The exact bug pattern that bit production-monitor on 2026-04-30 (`EnvironmentFile=-…` silent no-op) is mitigated here by parsing Telegram's response for `"ok":true`. |
| Artifact retention 30 days | Long enough for follow-up audit, short enough to not clutter Actions storage. |
| `if: always()` on artifact + Telegram steps | Get the output and notification even when the script fails. Failed bootstrap with no notification = exact silent-failure bug from 2026-04-30. |

## Security trade-offs (real, not theoretical)

A self-hosted runner on a production VPS is a **non-trivial security exposure**. Documented honestly:

| Risk | Mitigation in this design |
|---|---|
| PR from fork could run code as the runner user | `workflow_dispatch` only; no `on: pull_request`. GitHub default for self-hosted runners also requires explicit allow for fork PRs (`workflow.permissions.actions=read` on the repo level). |
| Anyone with push to a feature branch could craft a malicious workflow file | True, but limited to repo-write actors (operator + Claude). Workflow file changes show in `git log`. Telegram notifies on every run. Mitigation: review `.github/workflows/*.yml` changes carefully in PR review (same as code review). |
| Runner user has access to `/var/log/microstructure`, `/etc/default/trading-bot-telegram`, bot configs | True; the workflow needs this access to do its job. **Mitigation: register the runner under a dedicated user (`gha-runner`) with read access to `/var/log/microstructure` and `/etc/default/trading-bot-telegram`, but NOT to bot API keys, NOT in `sudoers`, NOT able to write to `/etc/systemd/`.** |
| Runner could be used to mine crypto / exfil data | True for any self-hosted runner. Mitigation: monitor runner CPU via `production_monitor.py` (already alerts on bot CPU spikes — extend to include runner user). |
| GitHub Actions token leak | The workflow uses default `GITHUB_TOKEN` with `permissions: contents: read` only. No write scope. |

**This decision does NOT extend the runner to run live trading code.** Phase B.2.1 ensemble is a backtest on static parquet — no order placement, no API key use, no balance changes. Future workflows that need live-trading scope must be a separate decision with its own ADR.

## Setup steps (operator, one-time, on VPS)

**Automated path (recommended).** All 6 steps are wrapped in `scripts/setup_vps_runner.sh` — idempotent, safe to re-run.

```bash
# 1. SSH to VPS
ssh root@167.71.24.86

# 2. Pull the latest branch with the script
cd /var/www/ai-trading-championship
git fetch origin claude/integrate-recommendations-XVgTr
git checkout claude/integrate-recommendations-XVgTr
git pull origin claude/integrate-recommendations-XVgTr

# 3. Get a registration token from GitHub (5-minute expiry):
#    https://github.com/RolandGasparyan/ai-trading-championship/settings/actions/runners/new
#    Click "Linux", copy the value passed to --token in the displayed config.sh command

# 4. Run the setup script
sudo RUNNER_TOKEN=<paste-token-here> bash scripts/setup_vps_runner.sh

# 5. (Script auto-verifies.) Confirm in GitHub UI:
#    https://github.com/RolandGasparyan/ai-trading-championship/settings/actions/runners
#    → "vps-trading-prod" should show "Idle"
```

What the script does, in order, idempotent at each step:

1. Create `gha-runner` user (skip if exists)
2. Grant runner read-only access to `/var/log/microstructure` (ACL preferred, `chmod o+rX` fallback) and `/etc/default/trading-bot-telegram` (mode 640, group ownership)
3. Download `actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz` (skip if `run.sh` already extracted)
4. Register runner with GitHub via `config.sh` (skip if `.runner` file exists)
5. Install + start systemd service `actions.runner.…vps-trading-prod.service`
6. Verify via `journalctl` that the runner reached "Listening for Jobs" (or warn if not yet visible — sometimes takes a few seconds)

**Reversibility:** `sudo REMOVAL_TOKEN=<token> bash scripts/teardown_vps_runner.sh`
(get removal token from same Settings → Actions → Runners page → click runner → Remove → "Configured" tab)

## Triggering a run

Once the runner is registered:

```bash
# From dev machine via gh CLI (recommended):
gh workflow run phase-b-ensemble.yml --ref claude/integrate-recommendations-XVgTr

# With custom inputs:
gh workflow run phase-b-ensemble.yml --ref claude/integrate-recommendations-XVgTr \
  -f pair=BTC_USDT \
  -f bootstrap_days=30 \
  -f bootstrap_trials=50

# OR from GitHub UI: Actions tab → Phase B.2.1 Ensemble → Run workflow
```

**Note on workflow visibility:** GitHub only shows `workflow_dispatch` workflows in the UI if the file exists on the **default branch** (`main`). Until merged to main, trigger via `gh workflow run --ref` pointing to the feature branch. Once merged, both UI and CLI work.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| A. Operator runs `python phase_b_ensemble.py` manually, pastes output | Works for one-shot; doesn't scale to repeated bootstraps with different parameters; no audit trail |
| B. systemd timer wrapper (mirroring `d6-autotrigger.timer`) | Would auto-fire on schedule, not on operator intent; less flexible for parameter sweeps |
| C. Pull data to dev machine, run locally | 50–200 MB parquet pull every iteration; data goes stale immediately; operator's dev machine becomes part of the production-data surface |
| D. **Self-hosted runner with workflow_dispatch** ← chosen | Auditable (Actions log + artifact + Telegram); parameter-flexible; one-time setup; reusable for B.2.2/B.2.3 by adding more workflow files |
| E. GitHub-hosted runner (Ubuntu) | Cannot reach `/var/log/microstructure`; would require uploading data to GitHub or a cloud bucket — defeats the purpose |

## Consequences

**Enabled:**
- B.2.1 ensemble can be run on real VPS data on demand without operator typing 4 SSH commands every time
- Output captured as 30-day artifact + Telegram-delivered verdict
- Pattern reusable for future research scripts (B.2.2 maker simulator, B.2.3 on-chain collector) — copy the workflow file and adjust the `python ...` line
- ADR-003 lesson honored: Telegram notify with response-parse, not fire-and-forget

**Costs:**
- Runner agent on VPS uses ~50 MB RAM idle, ~0% CPU when not running jobs
- One-time ~30 min operator setup (user creation, runner registration, systemd service)
- Security exposure: documented above; mitigated by dedicated `gha-runner` user with restricted access
- Adds `.github/workflows/phase-b-ensemble.yml` to the repo (74 lines)

## Reversibility

100%. To remove:

```bash
# On VPS:
sudo systemctl stop actions.runner.RolandGasparyan-ai-trading-championship.vps-trading-prod.service
cd /home/gha-runner/actions-runner
sudo ./svc.sh uninstall
sudo -u gha-runner ./config.sh remove --token <REMOVAL_TOKEN_FROM_GITHUB_UI>
sudo userdel -r gha-runner

# In repo:
git rm .github/workflows/phase-b-ensemble.yml
```

Removing the workflow file alone disables the workflow without removing the runner; removing the runner alone leaves the workflow file dormant. Either is partial reversibility.

## Re-evaluation triggers

Re-open this decision IF:

- A new workflow needs **write** access to the repo (current: `contents: read`)
- A new workflow needs to place orders / move funds (current: backtest only)
- Production-monitor detects unexpected runner CPU usage outside scheduled job windows
- GitHub announces a security CVE on the self-hosted runner agent (subscribe to https://github.com/actions/runner/releases for advisories)
- Operator wants to add a runner on a second VPS for redundancy (would need new `vps-trading-2` label and concurrency strategy)

## ADR linkage

- ADR-002 — Phase B direction. This workflow is the execution surface for B.2.1.
- ADR-003 — D7 freeze. Freeze expired 2026-05-01. New strategy code (`phase_b_ensemble.py`) goes through 4-gate validation; this workflow is part of how that validation is run.
- `feedback_drift_pattern.md` (memory) — operator picked option A explicitly with full understanding of the trade-offs documented above; not a drift-cue acceptance.
- `repo_separation.md` (memory) — workflow runs on the trading VPS only; not on dev machine.

## Related

- [[findings/2026-05-03-b21-ensemble-shipped]] — what this workflow runs
- [[decisions/2026-05-03-ruflo-dev-tool-only]] — same session, contrasting scope discipline
- [[findings/2026-04-30-d6-binding-no-go]] — the 2026-04-30 silent-Telegram-failure bug that informed the `ok:true` parse
- [PHASE_B_DECISION_TREE.md § B.2.1](../../PHASE_B_DECISION_TREE.md)
- GitHub Actions self-hosted runner docs: https://docs.github.com/en/actions/hosting-your-own-runners
