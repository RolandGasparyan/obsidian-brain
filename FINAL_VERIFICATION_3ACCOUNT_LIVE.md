# Final Verification — Switch to Real Battle (3 Gate.io Accounts)

**Branch:** `claude/switch-real-battle-accounts-ylLGx`
**Base:** `main` @ `f7cd8fed27465a5ae0177d5a06c9be45857653b1`
**Generated:** 2026-05-19T16:54:58Z
**Scope:** Pre-deploy verification for MAIN + SUB1 + SUB2 live battle on Gate.io spot.

---

## Battle envelope

| Account | Capital (USDT) | Balance ceiling | Trade size | Max daily DD |
|---|---|---|---|---|
| MAIN | 1579.52 | 1650.00 | 6% (~$94.77) | $31.59 |
| SUB1 | 200.00 | 220.00 | 9% (~$18.00) | $4.00 |
| SUB2 | 200.00 | 220.00 | 9% (~$18.00) | $4.00 |
| **Total** | **1979.52** | — | — | — |

| Parameter | Value |
|---|---|
| Strategy | MA50W10 (daily SMA50 + weekly SMA10) |
| Pairs | BTC/USDT, ETH/USDT, XRP/USDT, SOL/USDT |
| Max trades / day / account | 6 |
| Max hold | 46h |
| Cooldown after exit | 1800s |
| Poll interval | 30s |
| Lifetime cap | 720h |
| Strategy SHA256 | `704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143` (matches sacred lock) |

---

## Sandbox preflight (offline)

`python3 canary/check_agents.py --offline`

```
RESULT: 11/14 passed · 0 failed · 3 skipped
```

| Category | Result |
|---|---|
| Config: file loadable | PASS |
| Config: 3 accounts (MAIN/SUB1/SUB2) | PASS |
| Config: capital/ceiling/size match executor | PASS |
| Config: pairs match executor | PASS |
| Config: per-account capitals sum to total_capital_usd | PASS |
| State I/O: MAIN init/save/load round-trip | PASS |
| State I/O: SUB1 init/save/load round-trip | PASS |
| State I/O: SUB2 init/save/load round-trip | PASS |
| Logic: score_pairs returns all configured pairs | PASS |
| Logic: get_signal=BUY when price above SMA | PASS |
| Logic: get_signal=SELL when price below SMA | PASS |
| Key files: MAIN/SUB1/SUB2 present + 0600 + parseable | SKIP — VPS-only |
| Syntax check (`python -m py_compile`) | PASS for `canary_executor.py`, `canary_killswitch.py`, `check_agents.py` |

The three SKIPs only run on the deploy host. They will be re-run live via `check-agents.yml`.

---

## File integrity (sha256, this branch)

```
67c18e198262b60f79bf1a992879466f4572e4fb05398626ccb80e0cdb45c85c  canary/canary_executor.py
7f56d85047f135f36bd47f6c3f5c001fac5a820ded513b10feb3f0017f8ec38b  canary/canary_config.json
839835923d50a5d9900714c4c7f77717d940299ccb7efac548619b4aeb583b86  canary/canary-battle.service
4bf240a44be8b6d4b279b4c640ed4eb4100e64b027e417d4ae4d94a0579accde  canary/setup_live_battle.sh
56fa9bc9a55511d4241ee664028908b04b75355b3cc87cf08334cc19c07d7c74  canary/check_agents.py
704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143  canary/canary_strategy.py  ← LOCKED
```

---

## Pre-deploy gates

| Gate | Status |
|---|---|
| Strategy SHA256 unchanged from sacred lock | PASS |
| 3-account config in `canary_config.json` matches `canary_executor.ACCOUNTS` | PASS |
| Pair list consistent across config + executor | PASS |
| `setup_live_battle.sh` trims whitespace on all 3 key/secret pairs | PASS |
| `setup_live_battle.sh` chmods 0600 on all 3 key files | PASS |
| `canary-battle.service` runs `/root/canary/canary_executor.py` (multi-account) | PASS |
| `canary_arm.json` template requires `paper_preflight_passed: true` and pins capital + lifetime | PASS |
| `deploy-live-battle.yml` gated behind `confirm == 'START'` manual workflow_dispatch | PASS |
| GitHub secrets exist for `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `GATE_{MAIN,SUB1,SUB2}_API_{KEY,SECRET}` | OPERATOR-VERIFIED — cannot read secrets from sandbox |
| L99 halt file cleared on VPS | TO BE VERIFIED via SSH workflow |
| Live balances ≤ ceilings per account | TO BE VERIFIED via SSH workflow (read-only) |

---

## How to flip the switch (operator action)

**Step 1 — Live read-only preflight on the VPS** (no orders, no service changes):

```bash
gh workflow run check-agents.yml \
  -f branch=claude/switch-real-battle-accounts-ylLGx \
  -f offline=false
```

Or via UI: Actions → "Check Agents (VPS preflight)" → Run workflow → branch = `claude/switch-real-battle-accounts-ylLGx`, offline = `false`.

What it does:
- SSHes into the VPS using `SSH_PRIVATE_KEY`
- Pulls this branch on `/root/tradingguru-empire`
- Shows `systemctl is-active canary-battle.service`
- Sha256-compares source vs deployed `canary_executor.py` / `canary_config.json`
- Runs `python3 canary/check_agents.py` (full mode — talks to Gate.io read-only, checks balances ≤ ceilings, ticker fetch for all 4 pairs, arm file)
- Exit code 0 = green light

**Step 2 — Merge this branch to `main`** (after preflight is green).

**Step 3 — Deploy live trading** (this writes API keys + starts the systemd service):

```bash
gh workflow run deploy-live-battle.yml -f confirm=START
```

Or via UI: Actions → "Deploy Live Battle" → Run workflow → confirm = `START`.

What it does:
- SSHes into the VPS
- `git pull origin main` on `/root/tradingguru-empire`
- Exports the 6 `GATE_*` secrets and runs `setup_live_battle.sh`, which:
  1. Writes `/root/canary/.api_key_{main,sub1,sub2}` (0600)
  2. Writes `/root/canary/canary_arm.json` with `armed_at = now()`, 720h cap, `paper_preflight_passed: true`
  3. Clears `/root/.l99/protection_halt.json` if present
  4. Backs up `paper-arena.json`
  5. Syncs executor + config + service unit
  6. `systemctl restart canary-battle.service`

**Step 4 — Monitor first hour:**

```bash
ssh root@<VPS> 'tail -F /root/canary/runtime/battle.log'
ssh root@<VPS> 'watch -n 5 cat /root/canary/runtime/multi_battle_status.json'
```

---

## Stop sequence (kill switch)

If anything goes wrong:

```bash
ssh root@<VPS> 'systemctl stop canary-battle.service'
ssh root@<VPS> "echo '{\"halted\":true,\"reason\":\"operator_manual\"}' \
  > /root/canary/runtime/CANARY_HALT.json"
```

The executor's `check_halts()` will refuse to act on the next 30s cycle if the halt file exists.

---

## What this verification does NOT cover

- Live order submission — verifiable only after step 3.
- 24h paper preflight — not done; the operator-acknowledged arm template sets `paper_preflight_passed: true` as an attestation, not a measurement.
- VPS OS / dependency CVE scan — must be run with `pip-audit` inside `/root/canary/venv/` after deploy.
- End-to-end killswitch test — `canary_killswitch.py` exists but is not wired into `canary-battle.service`; the executor's internal halt-file check is the live safety mechanism. If you want the killswitch as a second process, that's a separate PR (add a `canary-killswitch.service` unit + adapt its `STATE_FILE` to read the three per-account state files).

These are known gaps. None of them block step 1 (read-only preflight). Steps 2-3 are operator-authorized live actions.
