# L99 Testnet Execution Protocol

## Status: LOCKED — NO MODIFICATIONS PERMITTED

---

## Pre-Launch (every session)

```bash
cd ~/ai-trading-championship/l99_bot
source venv/bin/activate
python preflight.py
```

Must return `22/22 checks passed`. If not — STOP.

---

## Start

```bash
sudo supervisorctl restart l99bot
sudo supervisorctl status l99bot
```

Expected: `l99bot   RUNNING`

---

## Verify Mode

```bash
python -c "import config; print('TESTNET=',config.TESTNET,'LIVE=',config.LIVE_TRADING)"
```

Expected: `TESTNET= True LIVE= False`

---

## First Trade Validation (manual)

On first execution verify:

1. Entry price = next candle open (not signal candle close)
2. Stop distance = 1.5 × ATR
3. Position size = equity × 0.01 / stop_distance
4. Trade logged in DB: `SELECT * FROM trades ORDER BY id DESC LIMIT 1;`
5. Telegram entry alert received
6. Open positions ≤ 3
7. No duplicate orders on same symbol

Any anomaly → immediate halt + diagnose.

---

## Burn-In Requirements

- Minimum 50 completed trades before any evaluation
- No parameter changes during burn-in
- No optimization
- No scaling

---

## Absolute Rules

- No parameter tuning
- No risk increase
- No LIVE_TRADING flip
- Preflight required before any restart
- Any unexpected behavior → stop + diagnose
