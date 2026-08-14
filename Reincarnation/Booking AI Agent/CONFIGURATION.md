# Configuration Reference — Working Production Setup

Every setting the live system actually uses, taken from the files in this
repository. **No secret values appear here** — only names, formats and rules.
Real secrets live only in `/opt/reincarnation_booking/shared/.env` on the
droplet (mode `0600`, owned by `www-data`) and in GitHub Actions secrets.

---

## 1. Where things live on the server

| Path | What |
|------|------|
| `/opt/reincarnation_booking/current` | Symlink → the live release |
| `/opt/reincarnation_booking/releases/<timestamp>-<pid>` | Individual releases |
| `/opt/reincarnation_booking/shared/.env` | Secrets, `0600`, `www-data` |
| `/opt/reincarnation_booking/shared/data/` | SQLite database (`reincarnation.db`) |
| `/opt/reincarnation_booking/backups/` | Pre-migration DB snapshots |
| `/var/log/reincarnation/` | `booking.log`, `booking.error.log` |
| `/etc/systemd/system/reincarnation-booking.service` | Unit file |
| `/etc/nginx/sites-available/reincarnation-booking` | vhost |

Deploys are atomic: a new release directory is built and tested, the symlink is
swapped, then the service restarts. If the health check fails, the previous
release is restored automatically.

---

## 2. Runtime validation rules (production)

`api/app.py` → `_validate_runtime_config()` refuses to start when the config is
weak. These rules are enforced only when `ENVIRONMENT=production`:

- **`WEBHOOK_SECRET` is always required.**
- Every secret that is set must be **at least 24 characters** and must not start
  with `CHANGE_ME`.
- **`WEBHOOK_URL` must use HTTPS.**
- Conditional requirements — enabling a channel makes its secrets mandatory:

| If you set… | …then these become required |
|-------------|------------------------------|
| `TELEGRAM_BOT_TOKEN` | `TELEGRAM_WEBHOOK_SECRET`, plus `TELEGRAM_ADMIN_CHAT_ID` as a positive integer |
| `META_PAGE_ACCESS_TOKEN` or `META_IG_ACCESS_TOKEN` | `META_APP_SECRET`, `META_VERIFY_TOKEN`, plus `META_IG_ACCOUNT_ID` for Instagram replies |
| `WA_PHONE_NUMBER_ID` or `WA_ACCESS_TOKEN` | `WA_APP_SECRET`, `WA_VERIFY_TOKEN` |
| `VIBER_AUTH_TOKEN` | `VIBER_AUTH_TOKEN` itself must meet the length rule |
| `VAPI_API_KEY` or `VAPI_PHONE_NUMBER_ID` | `VAPI_WEBHOOK_SECRET` |
| `TWILIO_ACCOUNT_SID` | `TWILIO_AUTH_TOKEN` |

Leaving a channel's variables blank cleanly disables that channel — the app
starts fine and the tests confirm unconfigured channels return `503` rather
than crashing.

Generate secrets with:

```bash
openssl rand -hex 32
```

Use an **independent** value for each one.

---

## 3. Environment variables

### Server

| Variable | Working value | Notes |
|----------|---------------|-------|
| `PORT` | `5000` | uvicorn port |
| `HOST` | `127.0.0.1` | Overridden by the unit file to `172.17.0.1` |
| `ENVIRONMENT` | `production` | Turns on the validation rules above |
| `WEBHOOK_URL` | `https://booking.6-empires.com` | Must be HTTPS |
| `WEBHOOK_SECRET` | *(secret)* | **Required.** Admin API + festival scout auth |
| `ALLOWED_HOSTS` | `booking.6-empires.com` | Host header allowlist |
| `ALLOWED_ORIGINS` | `https://booking.6-empires.com` | CORS |
| `MAX_REQUEST_BYTES` | `1048576` | 1 MB request cap |
| `SESSION_MAX_COUNT` | `500` | In-memory chat sessions |
| `SESSION_TTL_SECONDS` | `3600` | Session lifetime |

### LLM

`core/llm_core.py` speaks plain OpenAI-compatible `/chat/completions` with a
Bearer token, so **any** compatible provider is a configuration change — no code
change. `OPENAI_API_KEY` is simply "the key for whatever `LLM_BASE_URL` points
at", regardless of provider.

| Variable | Value | Notes |
|----------|-------|-------|
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Must be HTTPS (or loopback), no credentials or fragment in the URL — enforced at startup |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Verify against https://console.groq.com/docs/models — Groq retires models |
| `LLM_TIMEOUT` | `30` | Seconds |
| `OPENAI_API_KEY` | *(secret)* | Blank → deterministic canned fallback |

**Armenian quality caveat.** This app is Armenian-first. After each reply,
`_needs_armenian_rewrite()` checks for Latin prose; if found it asks the model
to rewrite in Armenian, and if the rewrite is still Latin it discards the reply
and serves a canned Armenian fallback. A model with weak Armenian therefore
degrades the chat quietly — into canned responses — rather than failing loudly.
Test real Armenian conversations after any model change.

Alternatives, same three variables:

| Provider | `LLM_BASE_URL` | Notes |
|----------|----------------|-------|
| Groq | `https://api.groq.com/openai/v1` | Very fast, free tier |
| aimlapi | `https://api.aimlapi.com/v1` | Previous production backend, `gpt-4o-mini` |
| Ollama | `http://127.0.0.1:11434/v1` | Self-hosted; tried and abandoned — a CPU-only VPS cannot answer in real time |

### Armenian phone text-to-speech

Twilio handles Armenian speech recognition with `hy-AM`, while AIMLAPI creates
the Armenian MP3 played inside the TwiML `<Gather>` loop. The production API key
must allow the **Chat**, **Audio**, and **Speech** endpoint categories.

| Variable | Default | Notes |
|----------|---------|-------|
| `TTS_API_KEY` | falls back to `OPENAI_API_KEY` | AIMLAPI key with Speech permission |
| `TTS_BASE_URL` | `https://api.aimlapi.com/v1` | `/tts` is appended automatically |
| `TTS_MODEL` | `openai/gpt-4o-mini-tts` | Armenian-capable speech model |
| `TTS_VOICE` | `nova` | AIMLAPI/OpenAI voice name; tuned for a softer conversational response |
| `TTS_SPEED` | `0.88` | Allowed range 0.25–4.0; slightly slower for clearer Armenian |
| `TTS_STYLE` | natural Armenian booking-manager prompt | AIMLAPI speaking style; use an empty value to omit it |

### Changing the LLM provider from GitHub (recommended)

Set these in the repository once and every deploy applies them to the droplet
automatically — no SSH, and the key lives in GitHub's encrypted secret store
instead of being typed on a server:

| Where | Name | Value |
|-------|------|-------|
| Settings → Secrets → Actions | `LLM_API_KEY` | the provider key |
| Settings → Variables → Actions | `LLM_BASE_URL` | e.g. `https://api.groq.com/openai/v1` |
| Settings → Variables → Actions | `LLM_MODEL` | e.g. `llama-3.3-70b-versatile` |

`GROQ_API_KEY` and `OPENAI_API_KEY` are accepted as fallback secret names.

The deploy's *Apply LLM settings from repository secrets* step then merges just
those keys into `shared/.env` via `scripts/merge_env.py`, leaving every other
secret untouched. If none of the three are set, the step does nothing at all.

Safety, because `shared/.env` is **not** covered by the release rollback:

- the previous `.env` is snapshotted to `backups/env-<timestamp>.bak` first,
- the merge is written to a temp file and only renamed into place after it
  parses and still contains every key the original had,
- the rename is atomic, so an interrupted deploy cannot leave a half-written file,
- values travel base64-encoded inside the remote script, never on a command
  line where `ps` would expose them,
- mode `0600` and `www-data` ownership are reapplied afterwards.

Rotating a key is then: update the GitHub secret, re-run the deploy.

### Changing the LLM provider directly on the server

Still supported, and the right tool when you want to change something the
workflow does not manage. The deploy never overwrites an existing
`/opt/reincarnation_booking/shared/.env`:

```bash
sudo nano /opt/reincarnation_booking/shared/.env    # set the three LLM_* / key lines
sudo systemctl restart reincarnation-booking
bash /opt/reincarnation_booking/current/scripts/prod_healthcheck.sh
```

Keep the file at mode `0600`, owned by `www-data`. Never put a key in the
repository — `.env.template` carries names and example values only.

### Channels

| Group | Variables |
|-------|-----------|
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET` |
| Email (SMTP) | `SMTP_HOST` (`smtp.gmail.com`), `SMTP_PORT` (`587`), `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_WEBHOOK_SECRET` |
| Meta (FB/IG) | `META_APP_SECRET`, `META_PAGE_ACCESS_TOKEN`, `META_IG_ACCESS_TOKEN`, `META_IG_ACCOUNT_ID`, `META_VERIFY_TOKEN`, `META_GRAPH_API_VERSION` (`v21.0`) |
| WhatsApp Cloud | `WA_PHONE_NUMBER_ID`, `WA_ACCESS_TOKEN`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN` |
| Viber | `VIBER_AUTH_TOKEN`, `VIBER_BOT_NAME` |
| Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WA_NUMBER` (`whatsapp:+1…`), `TWILIO_PHONE_NUMBER` (plain E.164, voice-capable), `TWILIO_VERIFY_SERVICE_SID`, `TWILIO_VERIFY_DEFAULT_CHANNEL` |
| Vapi.ai | `VAPI_API_KEY`, `VAPI_PHONE_NUMBER_ID`, `VAPI_ASSISTANT_ID`, `VAPI_WEBHOOK_SECRET` |

Note the two different Twilio number formats — `TWILIO_WA_NUMBER` needs the
`whatsapp:` prefix, `TWILIO_PHONE_NUMBER` must not have it.

### Integrations

| Group | Variables | Default |
|-------|-----------|---------|
| Festival scout | `FESTIVAL_SCOUT_ENABLED`, `FESTIVAL_SCOUT_INTERVAL_HOURS`, `FESTIVAL_OUTREACH_ENABLED`, `SERPAPI_KEY` | disabled, `72` hours |
| Google Calendar | `GOOGLE_CALENDAR_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON` | unset → sync is a safe no-op |

Google Calendar degrades cleanly: unconfigured or malformed service-account JSON
is caught and logged rather than crashing, and an invalid `event_date` is
rejected before any network call.

---

## 4. systemd unit

`deploy/reincarnation-booking.service`

**Binding:** uvicorn listens on **`172.17.0.1:5000`** — the Docker bridge
gateway, not localhost. That is why the unit orders itself `After=docker.service`
(`docker0` must exist first) and why health checks target that address.

```ini
ExecStart=/opt/reincarnation_booking/current/.venv/bin/python -m uvicorn api.app:app \
    --host 172.17.0.1 --port 5000 --workers 1 \
    --log-level info --access-log \
    --log-config /opt/reincarnation_booking/current/deploy/logging.json
```

| Setting | Value |
|---------|-------|
| User / Group | `www-data` |
| Restart | `always`, `RestartSec=5`, burst 5 per 60 s |
| EnvironmentFile | `/opt/reincarnation_booking/shared/.env` |
| Writable paths | `shared/data`, `/var/log/reincarnation` only |
| Logs | `booking.log`, `booking.error.log` |

Hardening in force: `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`,
`PrivateDevices`, `NoNewPrivileges`, empty `CapabilityBoundingSet`,
`RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6`, `UMask=0077`, plus the
kernel/cgroup/clock/hostname protections.

---

## 5. nginx

`nginx/reincarnation-booking.conf` — vhost `booking.6-empires.com`, port 80
redirects to 443, TLS from Let's Encrypt (TLSv1.2/1.3, HSTS two years).

Security headers: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
`Referrer-Policy: strict-origin-when-cross-origin`, and a `Permissions-Policy`
that denies camera/geolocation/payment while allowing **`microphone=(self)`** —
that last one is what makes the browser voice input work.

### Rate limits

| Zone | Rate | Applied to | Burst |
|------|------|-----------|-------|
| `chat_api` | 60 r/min | `/api/chat/` | 20 |
| `booking_api` | 30 r/min | `/api/booking/`, `/api/admin/`, `/api/festival/`, `/api/calls/` | 10 / 10 / 5 / 5 |
| `webhook_api` | 300 r/min | `/api/webhook/` | 100 |

### Notable locations

- `/static/` is served straight from disk by nginx (`alias` into the current
  release, `expires 7d`, gzip) — it does not hit the app.
- `/api/webhook/` sets `proxy_buffering off` and forwards
  `X-Hub-Signature-256`, which HMAC verification depends on.
- `/api/admin/` has a commented-out IP allowlist. It is currently protected by
  `WEBHOOK_SECRET` alone; uncomment `allow`/`deny` to add network-level
  restriction.

Timeouts: connect 10 s, send/read 60 s, body 10 s, `client_max_body_size 1m`.

---

## 6. Deployment (GitHub Actions)

`.github/workflows/main.yml` — runs on pull requests and on pushes to `main`
and the active `claude/*` branch.

**Job `quality`** (every run): compile, `ruff`, `bandit`, `pip-audit`,
`tests/integration_test.py`, `tests/e2e_test.py`.

**Job `deploy`** (only `push` to `main`, needs `quality`, environment
`production`): rsyncs the release, builds a release-local venv from the hashed
lockfiles, re-runs both suites **on the server**, backs up and migrates the
database, swaps the symlink, restarts, health-checks, and rolls back on failure.

Repository secrets/variables it reads: `SSH_HOST` (production: `165.227.95.37`),
`SSH_PORT` (`22`), `SSH_USER` (`root`), plus the deploy key.

Dependencies are installed with `--require-hashes` from `requirements*.lock`, so
a tampered package fails the build.

---

## 7. Health check

```bash
bash /opt/reincarnation_booking/current/scripts/prod_healthcheck.sh
```

The app's own `/health` returns `{"status":"ok"}` when the database is
reachable and **`503` when it is not** — so a 503 means "app up, database
down", which the script reports distinctly.

Because nginx routes by `Host`, checking the app directly needs the header:

```bash
curl -H "Host: booking.6-empires.com" http://172.17.0.1:5000/health
```

---

## 8. Quick facts

| What | Value |
|------|-------|
| Production site | https://booking.6-empires.com |
| Provider callback health | https://booking.165-227-95-37.sslip.io/health |
| Droplet | `empire-booking-prod` · 165.227.95.37 · NYC1 · Ubuntu 24.04 LTS |
| App bind address | `172.17.0.1:5000` (Docker gateway) |
| systemd unit | `reincarnation-booking` |
| Service user | `www-data` |
| Database | SQLite at `shared/data/reincarnation.db` |
| Languages | Armenian, English, Russian |
| Test coverage | integration 111, e2e 99 |
