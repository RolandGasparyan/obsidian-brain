# DEPLOY_LIVE_BATTLE_AUDIT.md

**Scope:** Section-by-section audit of `.github/workflows/deploy-live-battle.yml` and
`canary/setup_live_battle.sh` against the project's own governance stack.
**Audited HEAD:** `2c2cbb7` (post PR #47)
**Date:** 2026-05-20
**Auditor:** Claude sandbox session (read-only against the repo; no VPS access)

This audit does not claim live trading is armed, does not verify Gate.io
balances, and does not override operator authority. It surfaces findings,
risks, and the specific lines the operator should be aware of before each
deploy.

---

## 1 · Governance references

| Doc | Path | Used by this audit |
|---|---|---|
| Layer discipline | `governance/LAYER_DISCIPLINE.md` | L1 / L2 / L3 boundary rules |
| Refusal log | `docs/9-refusals-log.md` | 13 refusals, especially #5 (param mutation), #6 (go-live), #9 (override governance), #13 (LIVE_ORDERS=1) |
| Arming checklist | `canary/ARMING_CHECKLIST.md` | pre-arm gates, STOP conditions, anti-checklist |
| Strategy lock | `canary/canary_strategy.py` (SHA256 `704dd5725a909fe3f6…`) | the only L99-validated edge |
| Sacred locks | `README.md` table | capital · L99 halt · sockets · paper bot status |
| GODMODE audit | `governance/refused_proposals/GODMODE_AUDIT.md` | composite 27/100 · 92% overfit · OOS Sharpe −0.5 to −1.8 |

---

## 2 · Workflow trigger gates

`.github/workflows/deploy-live-battle.yml:1-24`

```yaml
on:
  workflow_dispatch:
    inputs:
      confirm:        # MUST be 'START' exactly
      issue_number:   # default '14'
  issues:
    types: [labeled] # auto-fires on label 'deploy-live-battle-START'
jobs:
  deploy:
    if: (workflow_dispatch && confirm=='START') ||
        (issues && label.name=='deploy-live-battle-START')
```

| Finding | Risk | Evidence |
|---|---|---|
| ✅ Manual confirmation required | LOW | `confirm=='START'` exact match — `Start`, `start`, or empty all fail |
| ✅ Label-trigger requires distinctive name | LOW | `deploy-live-battle-START` is hard to apply by accident |
| ⚠️ No `environments:` gate | MED | Could add a `environments: production` block with required reviewers for an extra approval step. Currently any repo-write user can fire it |
| ⚠️ Auto-fire on label | MED | Anyone with `issues: write` can add the label. If issues are enabled and any collaborator is added, they can fire deploys. Recommend: bind label-fire to specific assignee or issue author check |
| 🔴 No L99 halt pre-check | HIGH | Workflow does not refuse to start if `/root/.l99/protection_halt.json` is engaged. The deploy script *clears* the halt rather than refusing. See § 5 |

---

## 3 · SSH key setup

`.github/workflows/deploy-live-battle.yml:41-46`

```yaml
- name: Set up SSH key
  run: |
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    printf '%s\n' "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_ed25519
    chmod 600 ~/.ssh/id_ed25519
```

| Finding | Risk | Evidence |
|---|---|---|
| ✅ Key file mode 0600 | LOW | Standard SSH requirement |
| ✅ ~/.ssh dir mode 0700 | LOW | Standard SSH requirement |
| ✅ No key-echo in log | LOW | `printf` redirected to file, GitHub's secret masking would catch it otherwise |
| ⚠️ `printf '%s\n'` may add trailing newline | LOW | Generally fine; some keys are sensitive to trailing whitespace. Not an issue in practice |
| 🔴 No `ssh-add` / agent forwarding controls | LOW | Acceptable — direct ssh -i is the simpler pattern |

---

## 4 · git pull sequence (force-reset)

`.github/workflows/deploy-live-battle.yml:52-61` (inside `/tmp/deploy.sh`)

```bash
cd /root/tradingguru-empire
git fetch origin main
git reset --hard origin/main
git log --oneline -3
```

| Finding | Risk | Evidence |
|---|---|---|
| ✅ Force-reset is documented as intentional | LOW | Inline comment explains: "the VPS local repo has diverged from origin in the past, causing the entire deploy to fail at this step with no fallback" |
| 🔴 Destructive — discards any VPS-local commits | MED | `reset --hard` deletes uncommitted edits and any commits not on origin. Justification accepted, but any forensic / debug work done on the VPS must be committed and pushed BEFORE next deploy or it's lost |
| ⚠️ No verification of expected HEAD | MED | After reset, only `git log --oneline -3` is printed. No assertion that HEAD matches a known-good SHA. Recommend: pin SHA in arm artifact and compare |
| ⚠️ `cd` to hardcoded `/root/tradingguru-empire` | LOW | If the repo isn't there, deploy fails immediately. Acceptable. |

---

## 5 · L99 halt clearing logic (FLAG: governance tension)

`canary/setup_live_battle.sh:62-72`

```bash
if [ -f /root/.l99/protection_halt.json ]; then
  python3 - /root/.l99/protection_halt.json <<'PY'
import json, sys
f = sys.argv[1]
d = json.load(open(f))
d["halted"] = False
json.dump(d, open(f, "w"))
print("L99 halt cleared")
PY
fi
```

| Finding | Risk | Evidence |
|---|---|---|
| 🔴 **L99 halt is silently cleared on every deploy** | **HIGH** | The L99 halt is the project's documented "human override safety layer." `setup_live_battle.sh` flips `halted:true → halted:false` whenever the operator clicks deploy. The operator's intent to halt is overwritten without a confirmation prompt |
| 🔴 **No record of who/when cleared** | MED | Other fields in the halt file are preserved, but no audit trail is written. Recommend: write `cleared_by`, `cleared_at`, `cleared_by_workflow_run_id` into the file |
| ⚠️ **`canary_executor.check_halts()` reads `halted` boolean** | LOW | `canary_executor.py:87-93` — once `halted` is `false`, the executor proceeds. The clearing IS effective |
| ⚠️ The L99 file is preserved (not deleted) | LOW | Could be a feature (keeps history) or a bug (the executor only reads `halted` flag, not the history) |
| **Recommendation** | — | Either (a) require an explicit `confirm_clear_l99: YES` input on the workflow, or (b) refuse to deploy if `halted:true` is present and require operator to manually `rm /root/.l99/protection_halt.json` first |

**Governance tension cited explicitly:**

- `README.md` "What's protected forever" treats L99 as a human-override.
- `docs/9-refusals-log.md` Refusal #6 ("'Go live' requests refused per L99 halt engaged").
- Current behaviour: clicking the deploy clears L99 → past refusal #6 is bypassable by the same workflow.

This is a deliberate design decision (the multi-account live battle IS the
operator-authorized path past refusal #6, per `FINAL_VERIFICATION_3ACCOUNT_LIVE.md`),
but the clearing should be **explicit** in the deploy flow, not silent in
`setup_live_battle.sh`.

---

## 6 · Secret handling and 0600 permissions

`canary/setup_live_battle.sh:21-41`

```bash
trim() { local v="$1"; v="${v#"${v%%[![:space:]]*}"}"; v="${v%"${v##*[![:space:]]}"}"; printf '%s' "$v"; }
for acc in MAIN SUB1 SUB2; do
  key_var="GATE_${acc}_API_KEY"
  sec_var="GATE_${acc}_API_SECRET"
  if [ -z "${!key_var}" ] || [ -z "${!sec_var}" ]; then
    echo "ERROR: ${key_var} and ${sec_var} must be set"
    exit 1
  fi
done
MAIN_K=$(trim "$GATE_MAIN_API_KEY"); MAIN_S=$(trim "$GATE_MAIN_API_SECRET")
…
printf "%s:%s" "$MAIN_K" "$MAIN_S" > /root/canary/.api_key_main
printf "%s:%s" "$SUB1_K" "$SUB1_S" > /root/canary/.api_key_sub1
printf "%s:%s" "$SUB2_K" "$SUB2_S" > /root/canary/.api_key_sub2
chmod 0600 /root/canary/.api_key_main /root/canary/.api_key_sub1 /root/canary/.api_key_sub2
```

| Finding | Risk | Evidence |
|---|---|---|
| ✅ All 6 env vars required (no fallback) | LOW | The `if -z` check exits 1 if any are missing |
| ✅ Whitespace trimmed before concat | LOW | Past INVALID_SIGNATURE incidents caused by trailing space documented in inline comment |
| ✅ Files written via `printf` (no shell expansion) | LOW | No `echo $VAR` which could mangle special chars |
| ✅ Files chmod'd 0600 immediately | LOW | All three at once after write |
| ✅ Files owned by `root` (service user) | LOW | Implicit — running as root |
| ⚠️ No KEY/SECRET length validation | MED | `setup_live_battle.sh` does NOT verify 32-hex KEY + 64-hex SECRET. Only the single-purpose `set-*-keys.yml` workflows validate (PR #44 / pre-existing #37). A wrong-length value flows through here silently and the auth check downstream catches it |
| ⚠️ Env vars passed via `SendEnv` AND inline on command | LOW | `deploy-live-battle.yml:119-121` does both. Belt+suspenders, but the inline `KEY='$VAR'` form ends up in the SSH command line briefly (visible via `ps` on the VPS in the SSH server process). Practical exposure is minimal — VPS is single-tenant root |
| ✅ Service unit ReadWritePaths excludes `/root/canary/.api_key_*` | LOW | The keyfiles are written by `setup_live_battle.sh` (root, outside the service). The running service can READ them (since they're in `/root/canary/` which is the WorkingDirectory) but the `ReadWritePaths=/root/canary/runtime` restriction means the service can't accidentally rewrite them |

---

## 7 · `canary_arm.json` lifecycle

`canary/setup_live_battle.sh:43-60`

```bash
NOW=$(date -u +%Y-%m-%dT%H:%M:%S+00:00)
python3 - "$NOW" <<'PY'
d = {
    "armed_by": "Roland Gasparyan",
    "armed_at": sys.argv[1],
    "ack_max_loss_usd": 4.00,
    "ack_time_cap_hours": 720,
    "paper_preflight_passed": True,
    "accounts_armed": ["MAIN", "SUB1", "SUB2"],
    "pairs_armed": ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT"],
    "total_capital_usd": 1979.52,
}
…
PY
```

| Finding | Risk | Evidence |
|---|---|---|
| ✅ Created fresh every deploy | LOW | Prevents stale arm files from previous incidents |
| ✅ `armed_at` is wall-clock UTC at deploy time | LOW | `canary_executor.check_clock()` enforces 720h from this |
| ✅ Required fields validated by executor | LOW | `canary_executor.py:82-84` — refuses to start if any of `armed_by`, `armed_at`, `ack_max_loss_usd`, `ack_time_cap_hours`, `paper_preflight_passed` missing |
| 🔴 **`paper_preflight_passed: true` is hardcoded, not measured** | **HIGH** | The flag is set unconditionally. There is no actual paper preflight that the deploy validates. `canary_executor.py:84` enforces the flag must be `true` to start — but the flag is set true regardless of any preflight. This is an attestation, not a measurement |
| 🔴 `ack_max_loss_usd: 4.00` is inconsistent with daily DD caps | MED | MAIN daily DD cap is `$31.59` (per `canary_config.json` + executor), SUB1/SUB2 are `$4` each. The arm artifact's `ack_max_loss_usd:4.00` is the SMALLEST daily DD cap. The executor does not appear to enforce `ack_max_loss_usd` directly — it uses per-account `max_daily_dd_usd` from `ACCOUNTS`. The arm field is documentation, not enforcement |
| ⚠️ `ack_time_cap_hours: 720` extends arm window 30 days per deploy | MED | Every `confirm=START` deploys a fresh 30-day arm. There is no cumulative cap. A bug-driven re-deploy loop could permanently extend the arm window |
| ⚠️ `total_capital_usd: 1979.52` is hardcoded | LOW | Matches `canary_config.json` declared total. No cross-check between this file and balance ceilings is enforced |

---

## 8 · Systemd service safety

`canary/canary-battle.service`

```ini
[Service]
Type=simple
User=root
WorkingDirectory=/root/canary
ExecStart=/root/canary/venv/bin/python3 /root/canary/canary_executor.py
Restart=on-failure
RestartSec=30
StartLimitInterval=120
StartLimitBurst=3
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:/root/canary/runtime/battle.log
StandardError=append:/root/canary/runtime/battle.stderr.log
NoNewPrivileges=true
ProtectSystem=full
ReadWritePaths=/root/canary/runtime
ReadWritePaths=/var/www/ai-trading-championship/dist/api/battle
ReadOnlyPaths=/root/.l99
```

| Finding | Risk | Evidence |
|---|---|---|
| ✅ `NoNewPrivileges=true` | LOW | Process can't acquire new privileges |
| ✅ `ProtectSystem=full` | LOW | /usr, /boot, /efi read-only |
| ✅ `ReadWritePaths` strictly limited | LOW | Only runtime dir + frontend api/battle dir |
| ✅ `ReadOnlyPaths=/root/.l99` | LOW | Service can read L99 halt but cannot write to it. Halt-flipping is only possible from outside the service (i.e. `setup_live_battle.sh` or manual operator action) |
| ✅ `Restart=on-failure` + burst limit | LOW | 3 restarts in 120s, then systemd gives up — avoids fast crashloop |
| 🔴 **`User=root`** | MED | Service runs as root. Justified by need to write to `/var/www/...` and read `/root/canary/.api_key_*`, but reducing to a dedicated `canary` user would be a hardening win |
| ⚠️ No `PrivateTmp=true` | LOW | `/tmp` is shared. Not currently a concrete risk but standard hardening |
| ⚠️ No `ProtectHome=true` | LOW | Service can read user homedirs |
| ⚠️ No `CapabilityBoundingSet=` | LOW | Could drop everything except `CAP_NET_BIND_SERVICE` (not even needed for outbound HTTPS) |
| ⚠️ No `LimitNOFILE=` | LOW | Defaults are typically fine for a low-frequency trading bot |
| ✅ stdout/stderr split | LOW | Easier forensic review than merged log |
| ✅ `Type=simple` matches Python's blocking main loop | LOW | Correct for the design |

---

## 9 · Post-deploy auth check

`.github/workflows/deploy-live-battle.yml:66-96` (inline Python)

```python
for acc in ["main", "sub1", "sub2"]:
    kf = Path(f"/root/canary/.api_key_{acc}")
    if not kf.exists():
        print(f"[{acc.upper()}] keyfile MISSING")
        all_ok = False
        continue
    raw = kf.read_text().strip().split(":", 1)
    if len(raw) != 2:
        print(f"[{acc.upper()}] keyfile malformed")
        all_ok = False
        continue
    k, s = raw[0].strip(), raw[1].strip()
    print(f"[{acc.upper()}] key_len={len(k)} secret_len={len(s)}")
    ex = ccxt.gate(...)
    try:
        bal = ex.fetch_balance()
        usdt = float(bal.get("USDT", {}).get("free", 0))
        print(f"  PASS  USDT free=${usdt:.2f}")
    except Exception as e:
        all_ok = False
        print(f"  FAIL  {type(e).__name__}: {e}")
```

| Finding | Risk | Evidence |
|---|---|---|
| ✅ All 3 accounts checked individually | LOW | No early break on first failure |
| ✅ Catches both INVALID_KEY and INVALID_SIGNATURE | LOW | Generic `except Exception` |
| ✅ Reports USDT balance on success | LOW | Useful for ceiling-vs-actual sanity |
| 🔴 **Auth failure does NOT roll back the deploy** | **HIGH** | The script merely sets `all_ok=False` and continues. The service has already been restarted by step [7/7] of `setup_live_battle.sh`. A failed auth here means one or more account threads will FAIL-CLOSE on their next loop. The deploy reports `=== RESULT: AT LEAST ONE ACCOUNT FAILED AUTH ===` but service stays running with whatever accounts authenticated successfully |
| ✅ Per-account FAIL-CLOSED is by design | LOW | `canary_executor.py:fail_closed()` exits only the failing thread; service stays up for healthy accounts |
| ⚠️ No balance-vs-ceiling check | MED | A balance ABOVE ceiling implies isolation breach (operator manually transferred funds in). Auth check reports the balance but doesn't compare to `balance_ceil` |
| ⚠️ No IP-whitelist verification | MED | A successfully-fetching balance proves IP is whitelisted, but a `INVALID_KEY` error could mean key was deleted OR IP changed OR key rotated. Better diagnostic would distinguish these |

---

## 10 · Replay logging integrity

| Finding | Risk | Evidence |
|---|---|---|
| ✅ `canary_executor.publish_status` writes 3 files atomically | LOW | `STATUS_FILE` (internal) · `FRONTEND_PUB` (raw) · `TERMINAL_PUB` (frontend-shaped) |
| ✅ Test suite verifies the published shape | LOW | `canary/tests/test_publish_shape.py` — 6 tests on `publish_status` output |
| ✅ Replay endpoints `/api/battle/replay-*.json` consumed by the corrected design | LOW | PR #41 wires arena.html to these |
| ⚠️ No assertion that `frontend-check.yml` was run after deploy | MED | The deploy doesn't fail if `terminal.json` isn't updating. Recommend chaining `frontend-check.yml` as a follow-up |

---

## 11 · Emergency re-halt procedures

| Procedure | Available | Notes |
|---|---|---|
| In-band halt (executor self-stop) | ✅ | Write `halted:true` to `/root/canary/runtime/CANARY_HALT.json` OR `/root/.l99/protection_halt.json`. `canary_executor.check_halts()` fail-closes on next loop |
| systemd stop | ✅ | `systemctl stop canary-battle.service` |
| Single-account halt | ✅ | `halt-account.yml` workflow renames `.api_key_<acct>` → `.halted-<ts>`, thread fail-closes |
| `kill.sh` | ⚠️ STALE | `canary/kill.sh` targets `canary.service` (legacy single-account name), not `canary-battle.service`. Will fail with "Unit canary.service not loaded" |
| `ROLLBACK.md` | ⚠️ STALE | References single-account era (canary.service, $2 DD, single position). Not applicable to multi-account battle |
| `canary_killswitch.py` | ❌ NOT WIRED | Its own docstring (`canary_killswitch.py:1-30`) declares it legacy and not installed as a service |

**Action:** Treat `kill.sh`, `ROLLBACK.md`, and `canary_killswitch.py` as advisory
historical docs. Active kill paths are:

```bash
# Hard stop (recommended)
ssh root@167.71.24.86 'systemctl stop canary-battle.service'

# Soft halt — service stays up but executor refuses to act
ssh root@167.71.24.86 'cat > /root/canary/runtime/CANARY_HALT.json <<EOF
{"halted": true, "reason": "OPERATOR_<reason>", "ts": '"$(date +%s)"'}
EOF'

# Hard halt + re-engage L99 (refuses next deploy clearing too — until file is unset)
ssh root@167.71.24.86 'cat > /root/.l99/protection_halt.json <<EOF
{"halted": true, "engaged_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
 "reason": "OPERATOR_EMERGENCY_<reason>"}
EOF
systemctl stop canary-battle.service'
```

---

## 12 · Go/no-go decision conditions

### GO conditions (all must hold)

- [ ] Strategy SHA256 still `704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143`
- [ ] `canary/canary_config.json` accounts list matches `canary_executor.ACCOUNTS`
- [ ] Sum of `accounts.*.max_capital_usd` == `total_capital_usd`
- [ ] All 6 `GATE_*` GitHub Secrets exist (verify via secrets settings page)
- [ ] All 3 Gate.io API keys have IP `167.71.24.86` whitelisted
- [ ] All 3 Gate.io API keys have Spot Trade ON, Withdraw OFF, Margin/Futures OFF
- [ ] `canary/check_agents.py --offline` returns 0 fails locally
- [ ] Operator has read `ARMING_CHECKLIST.md` §STOP-conditions list in the last 24h
- [ ] Operator has tested `systemctl stop canary-battle.service` in a non-production context at least once
- [ ] Operator accepts the −22% to −28% worst-realistic DD per `GODMODE_AUDIT.md`

### NO-GO conditions (any one stops the deploy)

- [ ] Any FAIL in `canary/check_agents.py` non-offline mode (run via `check-agents.yml` workflow against live Gate.io)
- [ ] Any `balance_*` exceeds `balance_ceiling_*` on Gate.io (isolation breach)
- [ ] Operator is uncertain about anything
- [ ] Network or Gate.io is reporting issues
- [ ] Strategy SHA256 has changed (would mean L1 mutation — Refusal #5)
- [ ] Any `OVERRIDE_GOVERNANCE` config or `LIVE_ORDERS=1` flag has been proposed (Refusals #9, #13)

---

## 13 · Summary findings table

| Severity | Count | Examples |
|:---:|:---:|---|
| 🔴 HIGH | 4 | L99 silently cleared · `paper_preflight_passed` attested not measured · auth failure doesn't roll back · `kill.sh` + `ROLLBACK.md` stale |
| ⚠️ MED | 8 | No HEAD pin · no balance/ceiling check · `ack_max_loss_usd` mismatch · service runs as root · etc. |
| ⚠️ LOW | many | various hardening opportunities |
| ✅ PASS | many | core safety (0600 keys · SHA256 lock · systemd hardening basics · 3-account isolation) |

The deploy workflow is **functional and operator-authorized** but **not minimum-friction-safe**. Each HIGH finding above has a concrete fix path; none of the fixes require mutating Layer 1 or changing the strategy. See `SAFE_DEPLOY_CHECKLIST.md` for the operator-side mitigations and `ROLLBACK_VALIDATION.md` for the kill-path inventory.

---

*End of audit. No live actions taken. SHA256 lock unchanged. Strategy unchanged. canary_config.json unchanged.*
