# Session Note — Isolation Migration

**Date:** 2026-05-13
**Trigger:** Operator verbatim:
> "es agenti amen inchy arandzin stexci vor erbeq chxarnenq urish projectneri mech,
>  stexcir arandzin folder yev amen inch togh menak aydtegh lini"

**Translation:** "Create everything for this agent separately so we never mix it
with other projects, create a separate folder and let everything live only there."

---

## What was done

### Server side (167.71.24.86)

1. **Stopped paper bot permanently** — `monster-agent.service` stopped + disabled.
   CPU consumed: 1h 17min 10s before shutdown.
2. **Created `/root/agent/`** as unified home with 8 subdirs.
3. **Migrated `/root/canary/`** → `/root/agent/canary/` (excl venv, 144KB).
   SHA256 lock verified: `704dd5725a909fe3f6…` unchanged.
4. **Migrated `/root/ai-l99-production/strategy_lab/`** → `/root/agent/bot/` + `DISABLED.md` marker.
5. **Migrated docs:**
   - `MA_STRATEGY.md` (the only validated edge)
   - 11 wiki decision notes (consolidated from 2 source paths)
   - Created `9-refusals-log.md` (session firewall record)
6. **Migrated governance:**
   - `LAYER_DISCIPLINE.md` (immutable Layer 1/2/3 rules)
   - `BRANCH_LOCK.md` (multi-session coordination)
   - 3 GODMODE refused proposals (read-only ref)
7. **Backed up** monster-agent.service unit → `/root/agent/backups/`

### Local side (~/Desktop/agent/)

1. Created `~/Desktop/agent/` with 5 subdirs (chmod 700).
2. Wrote `README.md` with full hands-off zones list.
3. Pulled all docs + governance from server via scp.
4. Wrote `server-mirror/STATE.md` (snapshot reference).
5. Wrote `frontend-pointers/README.md` (where Layer 3 UI lives, NOT copied).
6. Wrote this session note.

---

## What was NOT touched

Per layer discipline:

- `/root/ai-l99-production/` (L99 master — separate concern)
- `/root/.l99/` (system-wide halt state)
- `/var/www/ai-trading-championship/` (production frontend)
- All capital and exchange connections (none anyway — halt engaged)
- `canary_strategy.py` content (SHA256 verified pre+post migrate)
- L99 halt file (still pinned 26h+)

---

## Verification (post-migration)

- ✅ Canary SHA256: `704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143`
- ✅ L99 halt: still engaged (`halted: true`)
- ✅ monster-agent: inactive, disabled, no python process running
- ✅ No live exchange sockets
- ✅ Telemetry services unaffected
- ✅ Capital: $1,980.90 USDT untouched

---

## Repo separation rule (now enforced by folder structure)

Per memory.md `repo_separation.md`:
> "trading work goes ONLY to ai-trading-championship; never touch reincarnation-smm from a trading session"

Updated interpretation (this session's enhancement):
> Trading agent code/state/docs live ONLY in:
>   - Server: /root/agent/
>   - Local:  ~/Desktop/agent/
> Frontend (Layer 3) lives in its own repo at /var/www/ on server,
>   ~/Desktop/ai-trading-championship/ on local.
> Never touched: REINCARNATION SMM, any other Desktop project.

---

## Operator's next-touch points

If the operator returns to a trading session, they can:

```bash
# Local
cd ~/Desktop/agent
cat README.md
ls docs/  governance/

# Server
ssh root@167.71.24.86 'cat /root/agent/README.md'
ssh root@167.71.24.86 'sha256sum /root/agent/canary/canary_strategy.py'
```

Everything is one folder. No more chaos across 11 desktop directories.
