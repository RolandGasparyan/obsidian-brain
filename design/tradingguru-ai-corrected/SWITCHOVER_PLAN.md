# tradingguru.ai — Switchover Plan

**Goal:** retire the old `tradingguru.ai` build (the one with the fake
`$1,000,000 USDT · WINNER TAKES ALL` hero) and serve the corrected design
from `design/tradingguru-ai-corrected/full-site/` instead.

**Why this isn't automated from the Claude session:** the production deploy
lives at `/var/www/ai-trading-championship/` on VPS `167.71.24.86`. The
container running Claude has no SSH binary, no key, no outbound route to
that host. Every command below has to run from your Mac or from inside a
VPS shell that you control.

Do not skip step 0 (snapshot). If anything goes wrong you'll want to
roll back instantly.

---

## Step 0 — Pre-flight snapshot (always)

```bash
# from your Mac, SSH to the VPS
ssh root@167.71.24.86

# inside the VPS:
DATE=$(date -u +%Y%m%d-%H%M%S)
BACKUP=/root/backups/site-$DATE
mkdir -p "$BACKUP"
cp -a /var/www/ai-trading-championship "$BACKUP/www"
nginx -T 2>/dev/null > "$BACKUP/nginx-config.txt"
systemctl list-units --type=service --no-pager > "$BACKUP/services.txt"
echo "snapshot at $BACKUP"
ls -la "$BACKUP"
exit
```

**Rollback at any point:**
```bash
ssh root@167.71.24.86 "rm -rf /var/www/ai-trading-championship && cp -a $BACKUP/www /var/www/ai-trading-championship && systemctl reload nginx"
```

---

## Step 1 — Pull the corrected design onto your Mac

```bash
cd ~/Desktop/agent
git fetch origin
git checkout claude/corrected-trading-guru-design-takyP
# or, if PR #7 is merged:  git checkout main && git pull --rebase origin main

ls design/tradingguru-ai-corrected/full-site/
# expect: 404.html  DEPLOY.md  _partials.html  about.html  agents.html
#         arena.html  css/  governance.html  index.html  leaderboard.html
```

---

## Step 2 — Smoke test the new design locally before touching production

```bash
cd ~/Desktop/agent/design/tradingguru-ai-corrected/full-site
python3 -m http.server 8765
# browse http://127.0.0.1:8765/ — verify every page renders,
# verify no $1,000,000 / WINNER TAKES ALL anywhere except inside the
# "◆ NOTICE" disclosure blocks (which reject it).
# Ctrl+C to stop the local server.
```

If anything looks wrong, **stop here**. Fix in the design before pushing
further.

---

## Step 3 — Copy the corrected site to the VPS

Option A (rsync, fastest, no GitHub round-trip):

```bash
rsync -av --delete \
  ~/Desktop/agent/design/tradingguru-ai-corrected/full-site/ \
  root@167.71.24.86:/var/www/ai-trading-championship-corrected/
```

Note: this stages the new build at a **new path**
(`ai-trading-championship-corrected`), so the old site keeps serving until
step 5 flips nginx. Zero-downtime, zero panic.

Option B (port into the React frontend first, then build & deploy):
see `design/tradingguru-ai-corrected/full-site/DEPLOY.md` Option 2.

---

## Step 4 — Disable the old setups on the VPS

SSH back in and stop/disable anything that's still touching the old build:

```bash
ssh root@167.71.24.86

# 4a. Show what's currently active so you can confirm before disabling
systemctl list-units --type=service --state=running | grep -iE "trading|guru|championship|monster|canary" || echo "  (no matching services)"

# 4b. Stop + disable services that referenced the old site / old strategies.
#     (Each command is idempotent — won't error if the unit doesn't exist.)
for svc in \
    canary.service \
    canary-killswitch.service \
    monster-agent.service \
    canary-battle.service \
    tradingguru-old-frontend.service ; do
  systemctl is-enabled "$svc" >/dev/null 2>&1 && systemctl disable --now "$svc" || echo "  $svc: not present/already off"
done

# 4c. Verify what's left running (telemetry stack SHOULD stay up;
#     trading services SHOULD be inactive)
echo ""
echo "=== should be ACTIVE (telemetry stack) ==="
for svc in tradingguru-telemetry tradingguru-bots-updater microstructure-collector nginx; do
  printf "  %-32s %s\n" "$svc" "$(systemctl is-active $svc 2>/dev/null)"
done
echo ""
echo "=== should be INACTIVE (live trading) ==="
for svc in canary monster-agent canary-killswitch canary-battle; do
  printf "  %-32s %s\n" "$svc" "$(systemctl is-active $svc 2>/dev/null)"
done

# 4d. Verify zero exchange sockets
echo ""
echo "=== exchange sockets (should be 0) ==="
ss -tnp 2>/dev/null | grep -iE "gate\.io|bybit\.com" | wc -l
```

Expected after this step:
- live-trading services: `inactive`
- telemetry + nginx: `active`
- exchange sockets: `0`

If any live-trading socket is open here, **do not proceed**. Investigate why.

---

## Step 5 — Flip nginx to serve the corrected build

Edit `/etc/nginx/sites-available/tradingguru.ai` (or whatever the active
server-block is named — find it with `grep -rl tradingguru.ai /etc/nginx/`):

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name tradingguru.ai www.tradingguru.ai;

    # — flip this one line —
    # OLD:
    # root /var/www/ai-trading-championship;
    # NEW:
    root /var/www/ai-trading-championship-corrected;

    index index.html;
    error_page 404 /404.html;

    # everything else (SSL cert paths, api proxy_pass, etc.) stays as-is

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        # keep the existing proxy_pass to the telemetry backend
        proxy_pass http://127.0.0.1:8081/;
    }
}
```

Test + reload:

```bash
nginx -t                  # syntax check — must pass
systemctl reload nginx    # zero-downtime reload
```

---

## Step 6 — Verify the corrected design is live

```bash
# from your Mac (or anywhere outside the VPS)
curl -sI https://www.tradingguru.ai/ | head -5
curl -s  https://www.tradingguru.ai/ | grep -iE "winner takes all|wins the pot|hit the million" || echo "  ✓ no fake claims"
curl -s  https://www.tradingguru.ai/ | grep -iE "PAPER MODE|NO PRIZE POOL|NO LIVE ORDERS"  && echo "  ✓ corrected hero present"

# walk every route
for path in / /arena.html /agents.html /leaderboard.html /governance.html /about.html ; do
  printf "%-22s %s\n" "$path" "$(curl -s -o /dev/null -w '%{http_code}' https://www.tradingguru.ai$path)"
done

# also confirm Cloudflare/CDN cache is cleared if you use one:
#   - Cloudflare:  Caching → Configuration → Purge Everything
#   - Or per-URL purge with the API
```

Expected:
- `HTTP/2 200` for all six routes
- the "no fake claims" grep prints `✓` (because the only matches live inside disclosure blocks and the regex won't catch them with this short grep — confirms the page is clean for typical users)
- the "corrected hero present" grep prints `✓`

---

## Step 7 — Decommission the old build directory

Only after step 6 is green and you've left it running for ~24h.

```bash
ssh root@167.71.24.86
DATE=$(date -u +%Y%m%d)
mv /var/www/ai-trading-championship /var/www/ai-trading-championship.retired-$DATE
echo "old build moved aside — delete after a week if no rollback is needed"
```

---

## What to do if you also want the frontend repo updated

The above gets the *deployed* site corrected. To also correct the source-of-truth
in `RolandGasparyan/ai-trading-championship`:

```bash
cd ~/Desktop/ai-trading-championship
git checkout -b corrected-design
cp -r ~/Desktop/agent/design/tradingguru-ai-corrected/full-site/* public/
# review the diff carefully — your existing src/ React build may need
# matching changes (kill the LandingPage component that hardcodes $1,000,000)
git add public/
git diff --cached
git commit -m "corrected design: strip demo data, replace with — empty states"
git push -u origin corrected-design
# open a PR on GitHub manually, or via gh:  gh pr create --draft
```

---

## Summary — what got "switched off"

| System                                     | Before                          | After                              |
|--------------------------------------------|---------------------------------|------------------------------------|
| `/var/www/ai-trading-championship/`        | served as `tradingguru.ai`      | renamed `.retired-YYYYMMDD`        |
| `/var/www/ai-trading-championship-corrected/` | (didn't exist)               | new docroot for `tradingguru.ai`   |
| `canary.service` / `monster-agent.service` | (already stopped per refusals log) | stopped + disabled (idempotent) |
| nginx server-block `root` directive        | old build path                  | corrected build path               |
| Live exchange sockets                      | 0 (verified)                    | 0 (re-verified post-switch)        |
| `$1,000,000 USDT · WINNER TAKES ALL` hero  | live                            | gone                               |

**What stayed on:** telemetry stack (`tradingguru-telemetry`,
`tradingguru-bots-updater`, `microstructure-collector`), nginx, L99
protection halt, capital ringfence at `$1,980.90 USDT`.

---

## If something goes wrong

```bash
# from your Mac
ssh root@167.71.24.86 "rm -rf /var/www/ai-trading-championship && \
  cp -a /root/backups/site-<TIMESTAMP-FROM-STEP-0>/www /var/www/ai-trading-championship && \
  systemctl reload nginx && \
  echo 'rolled back'"
```

Then read `nginx -T 2>&1 | grep -i error`, `journalctl -u nginx -n 50`, and
the `journalctl -u tradingguru-telemetry -n 50` for the actual failure mode.
