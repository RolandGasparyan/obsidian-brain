# Setup Guide — Production Checks & Obsidian Sync

Two scripts, both safe to re-run, both tested.

---

## 1. Check production health

**Where:** on the droplet — DigitalOcean → Droplets → `empire-booking-prod` → **Web Console**
(or `ssh root@165.227.95.37`).

```bash
bash /opt/reincarnation_booking/current/scripts/prod_healthcheck.sh
```

If the release predates this script, fetch it first:

```bash
cd /opt/reincarnation_booking/current && git pull 2>/dev/null || true
bash scripts/prod_healthcheck.sh
```

### What it verifies

| # | Check | Why it matters |
|---|-------|----------------|
| 1 | Live release symlink | Confirms which release is actually serving |
| 2 | systemd service active + enabled | Service runs now and survives reboot |
| 3 | `/health` via `172.17.0.1:5000` | App is up **and** the database is reachable |
| 4 | Served UI carries the mobile fixes | Greps the live HTML for `#calClose`, `send-btn-label`, `min-width:0`, the 380px breakpoint — proves the responsive fixes are really deployed, not just merged |
| 5 | nginx active, config valid, vhost enabled | Reverse proxy is healthy |
| 6 | `https://booking.6-empires.com/health` | The public entrypoint works end to end |
| 7 | TLS certificate expiry | Warns under 21 days, fails when expired |
| 8 | Database present, integrity, backups | Data is intact and backed up |
| 9 | Disk and memory | Catches a filling disk before it breaks a deploy |
| 10 | Errors in the last hour of logs | Surfaces runtime problems |

Exit code is `0` when everything passes, `1` when any check fails. It makes no
changes to the server.

---

## 2. Verify every channel against its real provider

**Where:** on the droplet.

```bash
cd /opt/reincarnation_booking/current
sudo -u www-data .venv/bin/python scripts/verify_channels.py
```

Add `--json` for machine-readable output.

`current/.env` is a symlink to `shared/.env` and the script reads it directly.
Do **not** pass the secrets on the command line — a pattern like
`env $(grep -v '^#' .env | xargs) python ...` puts every credential into the
process table, where `ps aux` exposes them to any user on the box.

Where the health check answers "is the app up", this answers "is each platform
actually connected". It asks each provider directly:

| Channel | What is verified |
|---------|------------------|
| Web chat + API | `/health` returns ok, the UI serves HTML |
| LLM | Credentials accepted **and `LLM_MODEL` is in the provider's model list** (production target: aimlapi) |
| Telegram | `getMe` accepts the token, a webhook is registered, it points at us, and Telegram's last delivery did not fail |
| Facebook Page / Instagram | Each access token resolves to a real account |
| WhatsApp Cloud | The phone number ID resolves; reports number, verified name and quality rating |
| WAHA WhatsApp | The local API accepts its key and the linked session reports `WORKING` |
| Twilio | Account is active, `TWILIO_PHONE_NUMBER` is genuinely owned, `TWILIO_WA_NUMBER` carries the `whatsapp:` prefix |
| Twilio Verify | Verification Service resolves from `TWILIO_VERIFY_SERVICE_SID`; OTP start/check can be exercised against the live service |
| Viber | Token accepted, webhook registered and pointing at us |
| Vapi | Assistant and phone number IDs exist on the account |
| Email | Real SMTP connect + STARTTLS + login |
| Google Calendar | Service-account JSON parses and the module reports configured |

A channel with no credentials is reported **not configured** (`➖`), not failed —
that is a valid state. Exit code is `0` unless a *configured* channel fails.

**It sends nothing.** No messages, no calls, no emails — every probe is a
read-only lookup.

The LLM model check is the one to watch after switching providers: aimlapi and
Groq both retire or rename models over time, and a wrong `LLM_MODEL` fails here
loudly instead of silently degrading the chat into canned fallbacks.

---

## 3. Sync the docs into Obsidian (on your Mac)

**Where:** on your Mac, in Terminal.

```bash
git clone https://github.com/RolandGasparyan/BOOKING-AI-AGENT.git
cd BOOKING-AI-AGENT
bash scripts/sync_obsidian_mac.sh
```

The vault is auto-detected from Obsidian's own config
(`~/Library/Application Support/obsidian/obsidian.json`, most recently opened
vault). To choose one explicitly:

```bash
bash scripts/sync_obsidian_mac.sh ~/Documents/MyVault
```

### What it does

Pulls the latest docs from GitHub and writes them to:

```
<your vault>/Reincarnation/Booking AI Agent/
├── Dashboard.md          ← generated, links everything, shows synced commit
├── PROJECT_SUMMARY.md
├── ARCHITECTURE.md
├── DEPLOYMENT_LOG.md
├── QUICK_REFERENCE.md
├── OBSIDIAN_IMPORT.md
├── README.md
└── SECURITY.md
```

It only writes inside that one folder, never deletes anything outside it, and
falls back to the local checkout if the clone fails (private repo or no
network). Re-run it any time to refresh — that is the intended workflow.

---

## Reference

| What | Value |
|------|-------|
| Production site | https://booking.6-empires.com |
| Temporary live site + provider callbacks | https://booking.165-227-95-37.sslip.io |
| Droplet | `empire-booking-prod` · 165.227.95.37 · NYC1 · Ubuntu 24.04 LTS |
| App root on server | `/opt/reincarnation_booking` |
| App (internal) | `http://172.17.0.1:5000` |
| systemd unit | `reincarnation-booking` |
| Repository | https://github.com/RolandGasparyan/BOOKING-AI-AGENT |

### Common server commands

```bash
systemctl status reincarnation-booking          # service state
journalctl -u reincarnation-booking -f          # live logs
journalctl -u reincarnation-booking -p err -n 50 # recent errors
nginx -t && systemctl reload nginx              # validate + reload nginx
readlink -f /opt/reincarnation_booking/current  # which release is live
```

Deploys run automatically from GitHub Actions on every push to `main`, with a
health check and automatic rollback if it fails.
