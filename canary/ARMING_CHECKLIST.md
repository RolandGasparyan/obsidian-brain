# Canary Arming Checklist — Multi-Account Live Battle

> Pre-arm checklist for the 3-account live battle (MAIN $1579.52 + SUB1 $200 + SUB2 $200).
> Tick every box BEFORE triggering `deploy-live-battle.yml`.

## ☐ Pre-arm gates

- [ ] Gate.io accounts: 1 MAIN + 2 sub-accounts (SUB1, SUB2) — each separate
- [ ] Account capital per `canary_config.json` (MAIN ~$1579.52, SUB1 ~$200, SUB2 ~$200)
- [ ] API keys per account: **Spot Trade enabled**, **no withdraw**, **no margin/futures**
- [ ] VPS IP (167.71.24.86) added to each key's IP whitelist on Gate.io
- [ ] L99 protection-halt artifact cleared (`/root/.l99/protection_halt.json` not active)
- [ ] You have read `canary_strategy.py` end to end and agree with MA50W10 rules
- [ ] You have read `canary_executor.py` and verified the per-account DD caps + size %

## ☐ GitHub Secrets

Confirm at https://github.com/RolandGasparyan/tradingguru-empire/settings/secrets/actions:

- [ ] `GATE_MAIN_API_KEY` + `GATE_MAIN_API_SECRET` set (32-char hex / 64-char hex)
- [ ] `GATE_SUB1_API_KEY` + `GATE_SUB1_API_SECRET` set (32-char hex / 64-char hex)
- [ ] `GATE_SUB2_API_KEY` + `GATE_SUB2_API_SECRET` set (32-char hex / 64-char hex)
- [ ] `SSH_HOST` + `SSH_USER` + `SSH_PRIVATE_KEY` set for VPS access

Verify quickly: add `validate-secrets` label to the tracker issue → workflow tests
each pair against Gate.io directly. **Note**: this runs from a GitHub Actions runner
IP, which is not whitelisted at Gate.io — so it returns `FORBIDDEN (IP not whitelisted)`
for all 3, which only tells us the keys *reach* Gate.io. Real auth verification
happens at deploy time on the VPS.

## ☐ Live deploy

- [ ] Fire deploy via label or workflow_dispatch:
  - Label: add `deploy-live-battle-START` to the tracker issue (#14 by default)
  - OR: `gh workflow run deploy-live-battle.yml -R RolandGasparyan/tradingguru-empire -f confirm=START`
- [ ] Within ~60s, a result comment lands on the tracker issue
- [ ] POST-DEPLOY AUTH CHECK must show **PASS** for all three accounts
- [ ] `=== RESULT: ALL 3 ACCOUNTS AUTHENTICATED ===`

## ☐ Live monitoring (first hour)

- [ ] Label tracker issue with `status-check` → confirm `state_main.json` +
      `state_sub1.json` + `state_sub2.json` all present
- [ ] Label tracker issue with `dashboard` → see full consolidated view
- [ ] Confirm `https://tradingguru.ai` (or your frontend) shows real updating
      data from `terminal.json` (no demo / paper labels)

## ☐ Continuous monitoring

The systemd unit `canary-battle.service` runs 24/7 with:
- `Restart=on-failure` + `RestartSec=30` (self-healing)
- `enabled` (auto-starts on boot)
- Arm window: 720h (30 days) before `canary_arm.json` expires
- Per-account daily DD caps enforced in-process

Re-deploy is a no-op rolling restart that re-loads any updated `GATE_*` secrets.

---

## STOP conditions (kill immediately, no debate)

Run on the VPS: `systemctl stop canary-battle.service`

🛑 Stop if any of:

- Any account hits its `max_daily_dd_usd` cap (MAIN $31.59, SUB1/SUB2 $4 each)
- Total open exposure exceeds expected (sum of `size_usdt` across all open positions)
- Service logs silent for > 2 minutes (check `journalctl -u canary-battle.service -f`)
- Gate.io shows balance > balance_ceiling per account (isolation breach)
- Any account holds position on a non-armed pair (only BTC/ETH/XRP/SOL allowed)
- Bot opens > 6 trades/day on any account (config cap should prevent this)
- Bot opens duplicate positions (cooldown should prevent this)
- You feel uncertain about anything

---

## Anti-checklist — STOP if you see yourself doing any of these

- ❌ Editing `canary_*.py` while service is running
- ❌ Raising `ack_max_loss_usd` to a number higher than the per-account daily DD
- ❌ Adding capital to any account during a live run
- ❌ Adding trading pairs beyond BTC/ETH/XRP/SOL
- ❌ Removing `Restart=on-failure` from the systemd unit
- ❌ Disabling Gate.io's IP whitelist on the keys
- ❌ Pasting a "GOD MODE" / `OVERRIDE_GOVERNANCE` config
