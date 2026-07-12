# ROLLBACK_VALIDATION.md

**Companion to:** `DEPLOY_LIVE_BATTLE_AUDIT.md` (§11)
**Scope:** Verify which rollback / kill / halt paths are actually reachable
right now, which are stale, and what's missing.

If you can answer "yes" to every section here, you have an emergency stop
that you've actually exercised. If any section is "no", treat fixing that as
P0 before the next deploy.

---

## 1 · Reachability matrix

| Path | Active? | Targets | How to verify |
|---|:---:|---|---|
| `systemctl stop canary-battle.service` | ✅ active | All 3 account threads | `systemctl status canary-battle.service` |
| Write `runtime/CANARY_HALT.json` | ✅ active | In-process halt (executor next loop) | `ls -la /root/canary/runtime/CANARY_HALT.json` |
| Write `/root/.l99/protection_halt.json` | ✅ active | In-process halt (executor next loop) | `ls -la /root/.l99/protection_halt.json` |
| `halt-account.yml` workflow | ✅ active | Single account FAIL-CLOSED | Actions tab |
| `restore-account.yml` workflow | ✅ active | Restore halted account | Actions tab |
| `canary/kill.sh` | ⚠️ STALE | Targets `canary.service` (legacy, doesn't exist) | `bash -n /root/canary/kill.sh` then `grep canary.service /root/canary/kill.sh` |
| `canary/ROLLBACK.md` | ⚠️ STALE | References single-account era | `head -10 canary/ROLLBACK.md` |
| `canary/canary_killswitch.py` | ❌ not wired | Was a watchdog process | `grep -i 'NOT WIRED INTO ANY SERVICE' canary/canary_killswitch.py` |

---

## 2 · Active kill commands — exact copy-paste

### 2.1 — Soft halt (executor stays loaded; refuses to act on next loop)

```bash
ssh root@167.71.24.86 '
cat > /root/canary/runtime/CANARY_HALT.json <<EOF
{
  "halted": true,
  "reason": "OPERATOR_<your_reason_here>",
  "triggered_by": "operator_ssh",
  "ts": '"$(date +%s)"',
  "iso": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"
}
EOF
echo "✓ CANARY_HALT.json written"
ls -la /root/canary/runtime/CANARY_HALT.json
'
```

What happens: `canary_executor.check_halts()` at `canary_executor.py:87-93` reads this file every loop. On next 30s tick, the executor fail-closes all threads.

### 2.2 — Hard stop (service down, no auto-restart for 120s burst window)

```bash
ssh root@167.71.24.86 '
systemctl stop canary-battle.service
sleep 2
systemctl is-active canary-battle.service
'
# Expect: "inactive" or "failed"
```

What happens: systemd sends SIGTERM, then SIGKILL after 90s if not exited. All 3 account threads end. Open positions on Gate.io are NOT closed — the executor's exit logic only fires while alive.

### 2.3 — L99 hard halt (refuses next deploy attempt too)

```bash
ssh root@167.71.24.86 '
mkdir -p /root/.l99
cat > /root/.l99/protection_halt.json <<EOF
{
  "halted": true,
  "engaged_at": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",
  "reason": "OPERATOR_EMERGENCY_<your_reason>"
}
EOF
echo "✓ L99 halt re-engaged"
'
```

What happens:
- Executor will fail-close on next loop (reads this file too)
- BUT: a subsequent `deploy-live-battle.yml` run will *clear* `halted:true → false` per `setup_live_battle.sh:62-72`. This is the known governance tension flagged in `DEPLOY_LIVE_BATTLE_AUDIT.md §5`.
- To prevent the next deploy from re-arming: **also stop the workflow trigger** by toggling Issues off, or revoke SSH access, or remove the `deploy-live-battle-START` label permissions.

### 2.4 — Per-account halt (other 2 keep running)

GitHub UI: https://github.com/RolandGasparyan/tradingguru-empire/actions/workflows/halt-account.yml

→ Run workflow → pick `account: MAIN|SUB1|SUB2` → Run.

What happens: SSHes to VPS, renames `.api_key_<acct>` → `.halted-<ts>`. The
account's thread fails on next auth, sets thread_alive=false, other threads
continue.

CLI equivalent (skip the workflow):

```bash
ACC=sub2  # or main / sub1
ssh root@167.71.24.86 "
  TS=\$(date +%Y%m%d-%H%M%S)
  mv /root/canary/.api_key_$ACC /root/canary/.api_key_$ACC.halted-\$TS
  ls -la /root/canary/.api_key_$ACC.halted-\$TS
"
```

### 2.5 — Gate.io-side emergency (out-of-band)

```
1. Log into https://www.gate.io/
2. Account → API Management
3. For each account whose key you want to kill:
   → click "Delete" or "Disable" on the API key entry
4. Service threads will start failing INVALID_KEY on next auth check
5. Then run §2.2 to stop the service
6. Cancel open orders manually via Gate.io spot trading UI
7. (Optional) transfer balances out of sub-accounts to reduce exposure
```

This is the only stop path that works if SSH to the VPS is broken (VPS-down,
network outage, key revoked).

---

## 3 · What stale files report wrongly

### 3.1 — `canary/kill.sh`

```bash
# Targets legacy single-account service:
systemctl stop canary.service              # ← THIS UNIT DOES NOT EXIST
systemctl stop canary-killswitch.service   # ← THIS UNIT DOES NOT EXIST EITHER
```

Running it today:
- `systemctl stop canary.service` → "Unit canary.service not loaded."
- Does NOT stop `canary-battle.service` (the actual multi-account service).
- DOES write `runtime/CANARY_HALT.json` — that part still works.

**Effective behaviour today:** soft-halt only (the in-process check), not a
service stop. Do not rely on it.

### 3.2 — `canary/ROLLBACK.md`

Section A says "Canary loss approaching $2" — the multi-account battle's DD
caps are $31.59 (MAIN) and $4 (SUB1/SUB2 each), not $2. Section E says
"Position may still be on Gate.io" — true for both versions, but the recovery
steps reference a single sub-account at $100, not the current 3-account
$1,979.52 layout.

**Effective behaviour today:** advisory only. Use this file's §2 above.

### 3.3 — `canary/canary_killswitch.py`

The file's own docstring is unambiguous:

> ⚠️ This module dates from the single-account phase. … The current 3-account
> live battle does NOT run this watchdog.

It's import-able but no systemd unit references it.

**Effective behaviour today:** none. Safety in multi-account is inside the
executor process (`canary_executor.check_halts` + per-thread DD cap).

---

## 4 · Things that ARE missing — fix-it ladder

### P1 (do before next deploy)

| Gap | Suggested fix |
|---|---|
| `kill.sh` targets wrong service | Patch to target `canary-battle.service` OR delete the file and point operators at §2 of this doc |
| `ROLLBACK.md` describes the wrong era | Rewrite header to point at `docs/LIVE_BATTLE_MONITORING.md` for the current state; keep this file for historical context |
| No automated rollback on auth failure | Add a workflow that, if POST-DEPLOY AUTH CHECK reports `AT LEAST ONE ACCOUNT FAILED AUTH`, automatically re-engages L99 halt and stops the service. Requires explicit operator override to re-deploy |

### P2 (do before T+24h)

| Gap | Suggested fix |
|---|---|
| `paper_preflight_passed: true` is attested | Either run an actual paper preflight (replay the last 720h on `paper-arena.json`) and pass it the result, OR rename the field to `paper_preflight_attested` to be honest |
| No HEAD-SHA pin in arm file | Add `armed_against_sha: "<git rev-parse HEAD>"` to `canary_arm.json` and have `canary_executor` verify it matches the running code |
| `User=root` in systemd unit | Create dedicated `canary` user with read access to keyfiles and runtime dir; service runs as that user |

### P3 (later, doesn't block)

| Gap | Suggested fix |
|---|---|
| No `PrivateTmp=true` | Add to `canary-battle.service` `[Service]` block |
| No `ProtectHome=true` | Add to `canary-battle.service` `[Service]` block |
| No `CapabilityBoundingSet=` | Drop all capabilities (the bot only needs outbound HTTPS which doesn't need any caps) |
| No balance-vs-ceiling enforcement at deploy | Add `if balance > ceiling: FAIL-CLOSE` to `setup_live_battle.sh` post-deploy auth check |

---

## 5 · Validation procedure — run this once today

This is the "did the rollback chain actually work" test. Run it ONCE in
production, when the bot is on a flat session and you can afford a 30-second
pause.

```bash
# Step 1 — Soft-halt the running service via CANARY_HALT.json
ssh root@167.71.24.86 '
cat > /root/canary/runtime/CANARY_HALT.json <<EOF
{"halted": true, "reason": "VALIDATION_TEST", "ts": '"$(date +%s)"'}
EOF
echo "✓ halt file written"
'

# Step 2 — Watch the log for fail-close (within 30 sec)
ssh root@167.71.24.86 'tail -F /root/canary/runtime/battle.log' &
TAILPID=$!

# Expect to see (within next 30s):
#   FAIL-CLOSED: [MAIN] halt active: /root/canary/runtime/CANARY_HALT.json
#   FAIL-CLOSED: [SUB1] halt active: ...
#   FAIL-CLOSED: [SUB2] halt active: ...

# Step 3 — Stop the tail, clear the halt
sleep 60
kill $TAILPID 2>/dev/null
ssh root@167.71.24.86 'rm /root/canary/runtime/CANARY_HALT.json'

# Step 4 — Verify executor resumes on next loop
ssh root@167.71.24.86 'sleep 35; tail -20 /root/canary/runtime/battle.log'

# Expect: balance OK lines reappear on next cycle — service self-recovers
# because we never killed it; only its in-process loop saw the halt.
```

If you see the FAIL-CLOSED lines AND the resume — your soft-halt path is
proven working. Date this validation: `____-__-__`.

Repeat annually or after any executor code change.

---

## 6 · Summary

| Layer | Active? | Action |
|---|:---:|---|
| Soft halt (`runtime/CANARY_HALT.json`) | ✅ | Use §2.1 |
| Hard stop (`systemctl stop`) | ✅ | Use §2.2 |
| L99 hard halt | ⚠️ | Works in-process but is cleared by next deploy — see DEPLOY_LIVE_BATTLE_AUDIT §5 |
| Per-account halt (workflow) | ✅ | Use §2.4 |
| Gate.io-side disable | ✅ | Use §2.5 — works even when VPS is unreachable |
| Legacy `kill.sh` / `ROLLBACK.md` / `canary_killswitch.py` | ❌ | Don't rely on |

**Bottom line:** you have 4 working rollback paths. The legacy 3 are stale.
There is no automated rollback on auth-failure at deploy time (a P1 gap).

The single most important sentence in this file:

> When in doubt, do § 2.2 (`systemctl stop canary-battle.service`).
> The cost of an unnecessary stop is 0. The cost of a missed stop can be the daily DD cap.

---

*End of validation. No live actions taken. SHA256 lock unchanged. Strategy unchanged.*
