# L99 Governance Activation Protocol

## Status: PENDING — activate only after 50 verified testnet trades

---

## Preconditions (ALL required)

```sql
SELECT COUNT(*) FROM trades WHERE status = 'CLOSED';
-- Must return ≥ 50
```

```bash
python preflight.py
-- Must return 22/22 PASS
```

- No kill events in DB: `SELECT COUNT(*) FROM kill_events;` → 0
- No schema migration errors
- `GOVERNANCE_ENABLED=false` confirmed

---

## DB Migration (one-time)

```bash
psql -U l99_user -d l99 -f governance_migration.sql
```

Verify:
```bash
psql -U l99_user -d l99 -c "\d governance_events"
psql -U l99_user -d l99 -c "\d trades"
```

---

## Activation Sequence

**Step 1 — Enable flag**
```bash
# .env
GOVERNANCE_ENABLED=true
```

**Step 2 — Restart**
```bash
sudo supervisorctl restart l99bot
```

**Step 3 — Confirm log output**
```
Governance engine active
```

---

## First 24h Monitoring

```bash
tail -f ~/logs/l99_bot.log

psql -U l99_user -d l99 -c "
SELECT event_type, old_state, new_state, reason, timestamp
FROM governance_events
ORDER BY timestamp DESC LIMIT 20;"
```

Expected: no FROZEN events, only BASELINE entry.

---

## Governance Permitted Actions

| Action | Permitted |
|---|---|
| Allocation reduction | ✓ |
| Risk multiplier downgrade | ✓ |
| Entry freeze (degradation) | ✓ |
| Performance warnings to Telegram | ✓ |
| Strategy signal modification | ✗ |
| Kill-switch override | ✗ |
| Risk per trade increase | ✗ |
| Capital redistribution | ✗ |

---

## Rollback

```bash
# .env
GOVERNANCE_ENABLED=false

sudo supervisorctl restart l99bot
```

No schema rollback required.

---

## Deployment Tag

```bash
git tag v1.1-governance-enabled
git push origin v1.1-governance-enabled
```

## Safety Guarantees

- Governance is supervisory only
- Kill switch has supreme authority
- Risk per trade never increases automatically
- Stop distance never modified
- Signal logic untouched
