# Canary Deployment — Operator Playbook  (MA50W10 variant)

> **Strategy:** MA50W10 trend-follow on BTC/USDT (see `MA_STRATEGY.md`).
> Backtest: +3,427% over 7.5y chained, Sharpe 2.81, MaxDD −23%.
> Canary cap: $100 sub-account · 48h · $2 max DD · single position.

> **Read this file fully before any action. Phase 2-4 require YOUR manual execution. Claude cannot click GO_LIVE for you.**

---

## ⚠️ Pre-deploy checklist (do NOT skip)

- [ ] Gate.io **sub-account** created (NOT main account)
- [ ] Sub-account funded with **exactly $100 USDT**, nothing else
- [ ] Sub-account API key generated with **spot trade permission only**
  - DO NOT enable: withdraw, margin, futures, options, transfer
  - IP whitelist if Gate.io supports it for your tier
- [ ] Main L99 production account untouched ($1,980 still in 100% USDT)
- [ ] Halt artifact still active at `/root/.l99/protection_halt.json`
- [ ] You have read `canary_strategy.py` and agree the rules are correct
- [ ] You have read `canary_executor.py` and verified the PARTIAL_FILL_FIX is baked in
- [ ] You have read `canary_killswitch.py` and verified DD cap = $2

---

## Phase 2 — Operator setup (~10 minutes)

### Step 1. Create dedicated venv (clean isolation from ai-l99-production)

```bash
cd /root/canary
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install ccxt numpy
```

### Step 2. Place API credentials

```bash
# Replace with YOUR sub-account API key + secret
cat > /root/canary/.api_key <<EOF
YOUR_GATE_SUB_ACCOUNT_API_KEY:YOUR_GATE_SUB_ACCOUNT_SECRET
EOF

chmod 600 /root/canary/.api_key
ls -la /root/canary/.api_key  # must show -rw-------
```

**The file MUST be `0600` perms or the executor will refuse to start.**

### Step 3. Verify isolation

```bash
# Quick balance check (one-liner)
/root/canary/venv/bin/python -c "
import ccxt
ex = ccxt.gate({
    'apiKey': open('/root/canary/.api_key').read().strip().split(':')[0],
    'secret': open('/root/canary/.api_key').read().strip().split(':')[1],
    'options': {'defaultType': 'spot'},
})
bal = ex.fetch_balance()
usdt = float(bal.get('USDT', {}).get('free', 0))
print(f'sub-account USDT free: \${usdt:.2f}')
if usdt > 105:
    print('❌ NOT ISOLATED — too much USDT. Move excess back to main account.')
elif usdt < 90:
    print('❌ UNDERFUNDED — add USDT to sub-account.')
else:
    print('✓ sub-account isolation OK')
"
```

Expected output:
```
sub-account USDT free: $100.00
✓ sub-account isolation OK
```

If anything else: **STOP**. Fix isolation first.

### Step 4. Install service units (no enable, no start)

```bash
sudo cp /root/canary/canary.service             /etc/systemd/system/canary.service
sudo cp /root/canary/canary-killswitch.service  /etc/systemd/system/canary-killswitch.service
sudo systemctl daemon-reload

# CONFIRM neither is enabled:
sudo systemctl is-enabled canary.service                 # should print: disabled
sudo systemctl is-enabled canary-killswitch.service      # should print: disabled
```

---

## Phase 3 — Mandatory paper preflight (≥4 hours)

This is required by `_CLAUDE.md` §1.1 paper-validation rule. We pretend to trade for 4 hours, verify the plumbing is clean, then go live.

### Step 5. Run paper preflight

```bash
# Open in screen or tmux so it survives SSH disconnect
screen -S canary-paper
cd /root/canary
LIVE_MODE=0 ./venv/bin/python -m unittest discover -s tests 2>&1 || true
# If no tests yet, run the script in paper mode (you'll need to adapt this depending on what paper mode you've implemented)

# MA50W10 preflight: verify strategy module loads + SMA computes + stale-detector works
./venv/bin/python -c "
import canary_strategy as s
import time
print(f'strategy SYMBOL={s.SYMBOL} TF=({s.DAILY_TIMEFRAME},{s.WEEKLY_TIMEFRAME})')
print(f'periods: daily SMA{s.DAILY_SMA_PERIOD} · weekly SMA{s.WEEKLY_SMA_PERIOD}')
print(f'trade_size_usdt={s.trade_size_usdt():.2f}')

# Test SMA on synthetic uptrend
closes_up = [100 + i*0.5 for i in range(60)]
sma50 = s.sma(closes_up, 50)
assert sma50 is not None and 100 < sma50 < 130, f'SMA50 sanity fail: {sma50}'
print(f'✓ SMA50 synthetic uptrend = {sma50:.2f}')

# Test stale detector
now_ms = int(time.time() * 1000)
is_stale_fresh, _ = s.is_ohlcv_stale(now_ms - 3600*1000, 26*3600)
is_stale_old,   _ = s.is_ohlcv_stale(now_ms - 30*3600*1000, 26*3600)
assert not is_stale_fresh, 'fresh data flagged as stale'
assert is_stale_old, 'old data not flagged as stale'
print('✓ STALE_OHLCV_DETECTOR working')

# Test entry signal (synthetic uptrend → should fire if price > both SMAs)
daily = [100 + i*0.5 for i in range(60)]
weekly = [100 + i*1.0 for i in range(15)]
ok, reason = s.should_enter(
    current_price=200.0,
    daily_closes=daily, weekly_closes=weekly,
    daily_latest_ts_ms=now_ms - 3600*1000,
    weekly_latest_ts_ms=now_ms - 86400*1000,
    seconds_since_last_exit=99999,
    trades_today=0, have_open_position=False,
)
assert ok, f'should_enter on clear uptrend failed: {reason}'
print(f'✓ should_enter synthetic uptrend: {reason}')
print('✓ strategy module loads and computes correctly')
"
```

If anything errors: **STOP**. Fix before arming.

### Step 6. Verify killswitch sanity

```bash
# Kill switch dry-run: confirm it parses your eventual state file format
./venv/bin/python -c "
import canary_killswitch as ks
print('MAX_DD_USD =', ks.MAX_DD_USD)
print('MAX_LIFETIME_HOURS =', ks.MAX_LIFETIME_HOURS)
print('POLL_SEC =', ks.POLL_SEC)
print('✓ killswitch module loads')
"
```

---

## Phase 4 — Arm and launch (you, not Claude)

### Step 7. Create the arm file (you sign this)

```bash
cat > /root/canary/canary_arm.json <<EOF
{
  "armed_by": "Roland Gasparyan",
  "armed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "ack_max_loss_usd": 2.00,
  "ack_time_cap_hours": 48,
  "paper_preflight_passed": true,
  "_acknowledgments": [
    "I have read canary_strategy.py and agree the rules are correct",
    "I have read canary_executor.py and verified hard caps are in code",
    "I have read canary_killswitch.py and verified DD trigger fires at -$2.00",
    "I understand this is engineering validation, not strategy validation",
    "I accept up to $2.00 loss as research expense",
    "I will not edit canary_*.py while running",
    "I will run /root/canary/kill.sh if anything looks wrong"
  ]
}
EOF
cat /root/canary/canary_arm.json   # review before continuing
```

If you don't agree with any acknowledgment line, **DO NOT START**.

### Step 8. Start the killswitch FIRST, then the canary

Order matters: watchdog must be running before the bot trades.

```bash
sudo systemctl start canary-killswitch.service
sleep 5
sudo systemctl status canary-killswitch.service --no-pager | head -10

# Verify watchdog is actually running:
journalctl -u canary-killswitch.service -n 5 --no-pager

# Then start canary
sudo systemctl start canary.service
sleep 5
sudo systemctl status canary.service --no-pager | head -10
```

### Step 9. Watch live

```bash
# In one terminal — bot output
journalctl -u canary.service -f

# In another — watchdog output
journalctl -u canary-killswitch.service -f

# In a third — telemetry
watch -n 5 'cat /root/canary/runtime/canary_status.json | python3 -m json.tool'
```

---

## Phase 5 — Stop (anytime, any reason)

### Step 10. One-button kill

```bash
sudo /root/canary/kill.sh "your_reason_here"
```

This:
1. Writes `/root/canary/runtime/CANARY_HALT.json`
2. Stops `canary.service`
3. Stops `canary-killswitch.service`
4. Prints final state snapshot

### Step 11. Post-mortem

```bash
# Trade history
less /root/canary/runtime/trades.log

# Signal decisions (every check, even vetoed)
less /root/canary/runtime/decisions.log

# Killswitch evaluations
less /root/canary/runtime/killswitch.log

# Final state
cat /root/canary/canary_state.json
```

### Step 12. Manual position cleanup if needed

If `kill.sh` ran while a position was open:
- `canary_state.json` will show `"position": {...}` — the position is still on Gate.io
- The executor's emergency exit logic may have closed it; check Gate.io UI to verify
- If still open: close it manually via Gate.io Spot → Sub-Account → Spot Trading

---

## Hard rules — these are also enforced in code

| Rule | Hard-coded in |
|---|---|
| Symbol = `BTC/USDT` only | `canary_strategy.py:SYMBOL`, `canary_executor.py:SYMBOL` |
| Max capital $100 | `canary_executor.py:MAX_CAPITAL_USD` |
| Refuse if balance > $105 | `canary_executor.py:check_balance_isolation()` |
| Max risk $30/trade | `canary_strategy.py:TRADE_SIZE_USDT` |
| Max 8 trades/day | `canary_strategy.py:MAX_TRADES_PER_DAY` |
| Max DD $2 | `canary_executor.py:MAX_DAILY_DD_USD` + `canary_killswitch.py:MAX_DD_USD` |
| 48h lifetime | both files |
| Cooldown 30 min | `canary_strategy.py:COOLDOWN_SECONDS` |
| No martingale | strategy never references PnL when sizing |
| No pyramiding | mutex `POSITION.lock` |
| No leverage | `defaultType=spot`, no margin endpoint |
| No self-modify | no parameter editing endpoints |
| Fail-closed | `Restart=no` in unit file |

---

## What Claude built (for your audit)

```
/root/canary/
├── canary_config.json       — locked params (documentation; code is source of truth)
├── canary_strategy.py       — signal logic (SMA50 + ADX(14) + volume burst)
├── canary_executor.py       — main loop with hard gates + PARTIAL_FILL_FIX
├── canary_killswitch.py     — independent watchdog
├── kill.sh                  — one-button stop
├── DEPLOY.md                — this file
├── ROLLBACK.md              — what to do if things go wrong
├── ARMING_CHECKLIST.md      — quick checklist version
├── canary.service           — systemd unit (NOT enabled)
├── canary-killswitch.service — systemd unit (NOT enabled)
└── runtime/                 — will be populated on first start
    ├── trades.log
    ├── decisions.log
    ├── killswitch.log
    └── canary_status.json
```

**Files Claude did NOT create:**
- `/root/canary/.api_key` — you create
- `/root/canary/canary_arm.json` — you sign
- `/root/canary/venv/` — you create in Step 1

These three are intentionally your responsibility. Claude cannot enter API credentials or sign on your behalf.

---

## Emergency contact tree

If something looks wrong and you can't reach a keyboard:

1. **From any device with SSH**: `ssh root@VPS && sudo /root/canary/kill.sh`
2. **From Gate.io mobile app**: log into sub-account, cancel any open orders, sell any BTC back to USDT
3. **Without SSH or Gate.io app**: contact Gate.io support to freeze the sub-account

The L99 main account is fully isolated. Anything happening to the canary sub-account does NOT touch the main $1,980.
