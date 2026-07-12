# One-paste switchover from your Mac

If you'd rather not click in the GitHub UI, this single block does the
entire switchover via SSH from your Mac's Terminal. **No editing
required** — copy, paste, hit return.

Prereqs (one-time):
- You can already `ssh root@167.71.24.86` without password (key auth)
- `~/Desktop/agent` is your local clone of `tradingguru-empire`

```bash
# ── ONE-PASTE SWITCHOVER ─────────────────────────────────────────────
set -e
LOCAL_REPO=~/Desktop/agent
VPS=root@167.71.24.86
NEW_DOCROOT=/var/www/ai-trading-championship-corrected
OLD_DOCROOT=/var/www/ai-trading-championship

# 1. pull the corrected design onto Mac
cd "$LOCAL_REPO"
git fetch origin
git checkout claude/corrected-trading-guru-design-takyP
git pull --rebase origin claude/corrected-trading-guru-design-takyP

# 2. push the helper + new build to the VPS
scp design/tradingguru-ai-corrected/switchover.sh $VPS:/root/switchover.sh
ssh $VPS "chmod +x /root/switchover.sh"
rsync -av --delete design/tradingguru-ai-corrected/full-site/ \
      $VPS:$NEW_DOCROOT/

# 3. drive the switchover on the VPS
ssh $VPS bash <<'REMOTE'
set -e
echo "═══ STEP 0 — snapshot ═══"
bash /root/switchover.sh 0

echo ""
echo "═══ STEP 4 — disable old live-trading services ═══"
bash /root/switchover.sh 4

echo ""
echo "═══ STEP 5 — flip nginx server-block root ═══"
CONF=$(grep -rl 'tradingguru\.ai' /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null | head -1)
[ -n "$CONF" ] || { echo "✗ nginx config not found"; exit 1; }
echo "  config: $CONF"
cp -a "$CONF" "$CONF.bak.$(date -u +%Y%m%d-%H%M%S)"

OLD='root /var/www/ai-trading-championship;'
NEW='root /var/www/ai-trading-championship-corrected;'
if ! grep -qF "$OLD" "$CONF"; then
  echo "✗ expected line '$OLD' not found in $CONF — aborting"
  echo "   inspect manually and re-run after fixing"
  exit 1
fi
sed -i.bak "s|$OLD|$NEW|" "$CONF"
nginx -t
systemctl reload nginx
echo "  ✓ nginx reloaded"

echo ""
echo "═══ STEP 6 — verify ═══"
sleep 2
bash /root/switchover.sh 6
REMOTE

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✓ Switchover complete."
echo "  Live site: https://www.tradingguru.ai"
echo "  Run after 24h:  ssh $VPS 'bash /root/switchover.sh 7'"
echo "  Emergency rollback:  ssh $VPS 'bash /root/switchover.sh rollback'"
echo "════════════════════════════════════════════════════════"
```

## What it does, step by step

1. Pulls latest from this branch onto your Mac.
2. Copies `switchover.sh` to the VPS as `/root/switchover.sh`.
3. Rsyncs the corrected build to `/var/www/ai-trading-championship-corrected/`.
4. SSHes to the VPS and:
   - **Step 0** — backs up the current site + nginx config to `/root/backups/site-<TIMESTAMP>/`
   - **Step 4** — stops and disables any live-trading services still active
   - **Step 5** — finds the nginx server-block for `tradingguru.ai`, replaces the docroot line in-place (the only change is `ai-trading-championship` → `ai-trading-championship-corrected`), tests config, reloads
   - **Step 6** — curls every route, greps for fake claims, confirms corrected hero is live

Every step is idempotent. If the nginx line doesn't match the expected
pattern, the script aborts before touching anything — no half-applied
state.

## If anything goes sideways

```bash
ssh root@167.71.24.86 'bash /root/switchover.sh rollback'
```

Restores the most recent snapshot, reloads nginx, done.

## After 24 hours (optional, retires the old docroot)

```bash
ssh root@167.71.24.86 'bash /root/switchover.sh 7'
```

Renames `/var/www/ai-trading-championship` to
`/var/www/ai-trading-championship.retired-YYYYMMDD`. Safe to delete after
a week if no rollback is needed.
