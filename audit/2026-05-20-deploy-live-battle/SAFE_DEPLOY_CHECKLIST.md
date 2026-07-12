# SAFE_DEPLOY_CHECKLIST.md

**Companion to:** `DEPLOY_LIVE_BATTLE_AUDIT.md`
**Use:** Before clicking `Run workflow` on `deploy-live-battle.yml`, walk through
this file top to bottom. **Every checkbox must be true. Stop at the first FAIL.**

This checklist is *stricter than* `canary/ARMING_CHECKLIST.md`. It assumes the
multi-account live battle is the operator-authorized path past Refusal #6, and
that the operator wants the deploy to fail closed at every layer that's easy to
get wrong.

---

## 0 · Pre-flight (run THESE before opening the workflow form)

Run from your Mac terminal. All commands are read-only.

```bash
# 0.1 — Verify GitHub origin HEAD matches what you expect
gh repo view RolandGasparyan/tradingguru-empire \
  --json defaultBranchRef --jq '.defaultBranchRef.name'
# Expect: main

git fetch origin main && git log --oneline origin/main -3
# Expect: latest 3 commits look right; bottom commit is one you recognize
```

```bash
# 0.2 — Verify strategy SHA256 lock is unchanged
ssh root@167.71.24.86 'sha256sum /root/canary/canary_strategy.py'
# Expect: 704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143
```

```bash
# 0.3 — Verify L99 halt state on VPS
ssh root@167.71.24.86 '
  if [ -f /root/.l99/protection_halt.json ]; then
    cat /root/.l99/protection_halt.json
  else
    echo "L99 halt file does not exist"
  fi
'
# Expect: either no file, or halted:false. If halted:true,
# decide explicitly whether you want this deploy to clear it.
```

```bash
# 0.4 — Verify current service status (knowing what you're replacing)
ssh root@167.71.24.86 '
  systemctl is-active canary-battle.service
  systemctl status canary-battle.service --no-pager | head -10
'
# Expect: active (running) — or inactive if you're cold-starting.
```

```bash
# 0.5 — Verify current arm artifact (knowing what'll be replaced)
ssh root@167.71.24.86 '
  if [ -f /root/canary/canary_arm.json ]; then
    cat /root/canary/canary_arm.json
  else
    echo "No active arm file"
  fi
'
# Note: armed_at timestamp + ack_time_cap_hours = window expiry.
# After deploy, armed_at = NOW, window resets to 720h.
```

```bash
# 0.6 — Verify the deploy script that will run
ssh root@167.71.24.86 '
  ls -la /root/tradingguru-empire/canary/setup_live_battle.sh
  head -50 /root/tradingguru-empire/canary/setup_live_battle.sh
'
# Expect: file exists, executable, last-modified recent. Read the top
# 50 lines to confirm no surprise changes since you last looked.
```

```bash
# 0.7 — Verify all 3 keyfile envelopes exist on VPS (NOT contents)
ssh root@167.71.24.86 '
  for f in /root/canary/.api_key_main /root/canary/.api_key_sub1 /root/canary/.api_key_sub2; do
    if [ -f "$f" ]; then
      echo "$f  $(stat -c %a "$f")  $(stat -c %s "$f") bytes  $(stat -c %y "$f")"
    else
      echo "$f  MISSING"
    fi
  done
'
# Expect: all 3 present, mode 600, size ≈ 97 bytes (32-char KEY + ":" + 64-char SECRET).
# A different size hints at a malformed key.
```

```bash
# 0.8 — Offline preflight (config + state I/O + logic, no Gate.io calls)
cd ~/path/to/local/tradingguru-empire
git fetch origin main && git checkout origin/main
python3 canary/check_agents.py --offline
# Expect: "RESULT: 11/14 passed · 0 failed · 3 skipped"
# Any FAIL → stop and diagnose. Do NOT click the deploy button.
```

```bash
# 0.9 — Live read-only Gate.io preflight (runs FROM the VPS, IP-whitelisted)
gh workflow run check-agents.yml \
  -R RolandGasparyan/tradingguru-empire \
  -f branch=main \
  -f offline=false
# Watch the run page Summary tab for the auth + balance result.
# Expect: ALL 3 accounts PASS, balance ≤ ceiling, ticker fetch OK for all 4 pairs.
```

---

## 1 · Decision gate (answer all honestly)

| Question | Answer | If NO |
|---|---|---|
| Did `check-agents.yml` non-offline run show 3/3 PASS in the last 30 min? | yes / no | Re-run §0.9 |
| Did I read the latest entries in `docs/9-refusals-log.md` in the last 24h? | yes / no | Read it |
| Have I memorized the 3 active kill paths (§5 of DEPLOY_LIVE_BATTLE_AUDIT)? | yes / no | Stop. Re-read |
| Do I accept the −22% to −28% worst-realistic DD on $1,979.52? | yes / no | Stop |
| Am I clear that clicking START clears `/root/.l99/protection_halt.json`? | yes / no | Stop |
| Am I clear that `paper_preflight_passed:true` is attested, not measured? | yes / no | Stop |
| Is there anyone on standby who can kill the service if I become unreachable? | yes / no | Note: at minimum, your phone should be reachable |
| Is the market in an obvious wild-tail event right now? | no | If yes, postpone |

If any answer in the **Answer** column is in the "stop" column, **do not click START.**

---

## 2 · Trigger the deploy

If — and only if — every checkbox in §0 and §1 is green:

🟢 https://github.com/RolandGasparyan/tradingguru-empire/actions/workflows/deploy-live-battle.yml

```
confirm:       START
issue_number:  (leave blank, defaults to 14)
```

Click **Run workflow**.

Expected duration: ~30 s.

---

## 3 · Post-deploy validation (within 90 s of click)

```bash
# 3.1 — Verify the run completed (replace RUN_ID with actual)
gh run view <RUN_ID> -R RolandGasparyan/tradingguru-empire
```

Open the workflow run page and read the **Summary** tab. Look for these exact strings:

| String | Meaning |
|---|---|
| `[1/7] Directories ready` | Step 1 of setup_live_battle.sh |
| `[2/7] API keys secured (chmod 0600)` | Step 2 |
| `lengths key/secret  MAIN=32/64  SUB1=32/64  SUB2=32/64` | All 3 keys correct length |
| `Written: /root/canary/canary_arm.json` | Arm artifact created |
| `[3/7] canary_arm.json created` | Step 3 |
| `L99 halt cleared` (only if L99 was engaged) | L99 was flipped to halted:false |
| `[4/7] L99 halt check done` | Step 4 |
| `[5/7] No paper-arena.json found (skipping backup)` OR `Demo data backed up` | Step 5 |
| `[6/7] No old canary.service running` | Step 6 (legacy cleanup) |
| `[7/7] executor+config synced, canary-battle.service started` | Step 7 |
| `=== LIVE BATTLE STARTED ===` | setup_live_battle.sh succeeded |
| `Active: active (running)` (in systemctl status block) | Service is running |
| `[MAIN] key_len=32 secret_len=64` + `  PASS  USDT free=$xxxx` | MAIN auth OK |
| `[SUB1] key_len=32 secret_len=64` + `  PASS  USDT free=$xxxx` | SUB1 auth OK |
| `[SUB2] key_len=32 secret_len=64` + `  PASS  USDT free=$xxxx` | SUB2 auth OK |
| `=== RESULT: ALL 3 ACCOUNTS AUTHENTICATED ===` | All 3 PASS |

**If you see `=== RESULT: AT LEAST ONE ACCOUNT FAILED AUTH ===`**:
The service is running with only the authenticated accounts. The failed
account's thread will FAIL-CLOSE every 30s. This is not catastrophic but you
should:
1. Run `permutation-check.yml` to confirm whether it's a key/secret swap or a
   genuinely invalid key
2. Re-write the failing account's key via `set-main-keys.yml` / `set-sub2-keys.yml`
3. Re-trigger `check-agents.yml` to confirm

---

## 4 · Post-deploy live verification (within 5 min of click)

```bash
# 4.1 — Watch live log for first cycles
ssh root@167.71.24.86 'tail -F /root/canary/runtime/battle.log'
```

Expected pattern (every 30s):

```
[YYYY-MM-DD HH:MM:SS,###][MAIN] balance OK $<usdt> USDT
[YYYY-MM-DD HH:MM:SS,###][SUB1] balance OK $<usdt> USDT
[YYYY-MM-DD HH:MM:SS,###][SUB2] balance OK $<usdt> USDT
[YYYY-MM-DD HH:MM:SS,###][BATTLE] Pairs ranked: [...]
```

```bash
# 4.2 — Verify multi_battle_status.json is updating
ssh root@167.71.24.86 'watch -n 5 "stat -c \"%y  %s\" /root/canary/runtime/multi_battle_status.json"'
```

Modification time should advance every ~60s.

```bash
# 4.3 — Verify frontend telemetry is fresh
gh workflow run frontend-check.yml -R RolandGasparyan/tradingguru-empire
```

Watch the run for: timestamp delta < 90s, all 3 accounts in `accounts` map,
`championship.current_round_id` non-null.

---

## 5 · 24-hour checkpoints (only-you actions)

| When | Run | Look for |
|---|---|---|
| T+1h | `dashboard.yml` | All 3 LIVE · current_round_id incremented · no FAIL-CLOSED |
| T+6h | `dashboard.yml` + `frontend-check.yml` | session_pnl values appearing · trades_today > 0 OR honest zero · daily_dd << cap |
| T+24h | `dashboard.yml` | Aggregate session_pnl direction visible · daily_dd reset for the new day |
| T+168h (1 wk) | `dashboard.yml` | Total session_pnl shows MA50W10 is or isn't profitable OOS · re-evaluate |
| T+720h (30 d) | None — arm expires automatically | Bot refuses to act. Re-arm via deploy-live-battle.yml if continuing |

---

## 6 · Forbidden actions during a live run

Per `canary/ARMING_CHECKLIST.md` anti-checklist + this audit's findings:

- ❌ Edit `canary/canary_*.py` while service is running. Use a deploy.
- ❌ Raise `ack_max_loss_usd`. The per-account daily DD caps are the real safety; this field is documentation.
- ❌ Add capital to any account during live run. Triggers isolation-breach STOP per ceiling check.
- ❌ Add trading pairs beyond BTC/ETH/XRP/SOL. Strategy lock includes the pair list at config level.
- ❌ Remove `Restart=on-failure` from the systemd unit (already enforced — the unit is in git).
- ❌ Disable Gate.io's IP whitelist on the keys.
- ❌ Paste any "GOD MODE" / `OVERRIDE_GOVERNANCE` config — Refusals #1, #5, #7, #9, #13 apply.
- ❌ Run `LIVE_ORDERS=1 ./start_championship_round.sh` — Refusal #13.
- ❌ Mutate `canary_strategy.py` — pre-commit SHA256 hook will refuse the commit, but don't even try.

---

## 7 · Stop conditions — if any are true, kill now

Run one of the kill paths in DEPLOY_LIVE_BATTLE_AUDIT.md §11 immediately:

- 🛑 Any account's `session_pnl_usd` <= `-(0.9 * max_daily_dd)` — close to cap
- 🛑 Aggregate exposure across all open positions exceeds expected sum (`0.06*$1579.52 + 2*0.09*$200` = $130.77 max single-cycle exposure)
- 🛑 `battle.log` silent for > 2 minutes
- 🛑 Any account's Gate.io balance > `balance_ceiling_usd` (MAIN $1650 / SUB1 $220 / SUB2 $220) — isolation breach
- 🛑 Any position on a non-armed pair (only BTC/ETH/XRP/SOL allowed)
- 🛑 > 6 trades/day on any single account (config cap should prevent — if it fires, the cap is broken)
- 🛑 Duplicate positions on the same pair within `< COOLDOWN_SEC` (cooldown should prevent — if it fires, cooldown is broken)
- 🛑 Anomaly in `multi_battle_status.json` (account_id mismatch, unexpected fields, malformed JSON)
- 🛑 Operator feels uncertain about anything

---

## 8 · Audit-this-checklist meta-rule

This checklist is **a tool, not a guarantee.** The real safety chain is:

1. Operator authority (you)
2. SHA256-locked strategy (refuses to be mutated)
3. Per-account daily DD caps (enforced in-process by executor)
4. Per-account IP whitelist (enforced by Gate.io)
5. Kill switch (you)

Any of those failing alone is recoverable. Two failing together is a crisis.
This checklist exists to prevent operator-side mistakes that would compound
with a Layer-1 surprise.

If you find a check that's wrong or missing, edit this file and open a PR —
the checklist itself is design-time, just like `LAYER_DISCIPLINE.md` and
`9-refusals-log.md`.

---

*End of checklist. No live actions in this file. No mutations to canary_strategy.py, canary_config.json, or SHA256 lock.*
