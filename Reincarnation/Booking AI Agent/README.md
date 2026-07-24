# REINCARNATION Booking AI Agent

Secure omni-channel booking intake and approval system for REINCARNATION Band.
It supports web chat, Telegram, Facebook/Instagram, WhatsApp, voice providers,
and inbound email while keeping final booking confirmation behind two mandatory
gates: a verified deposit of at least 50% and Roland's explicit approval.

## Security model

- Telegram uses Telegram's secret-token header.
- Meta and WhatsApp Cloud use HMAC-SHA256 verification.
- Twilio voice and WhatsApp use Twilio signature verification.
- Vapi, inbound email, and admin routes require separate strong secrets.
- Provider event IDs are hashed and claimed atomically to prevent replay.
- Booking creation uses an immediate SQLite transaction to prevent concurrent
  double-booking.
- Booking details, admin data, outbound calls/messages, deposits, and the
  festival scout are admin-authenticated.
- Production binds to loopback behind Nginx, disables interactive API docs,
  applies request limits/security headers, and rejects unsafe configuration.
- Festival outreach and social publishing are disabled until explicitly
  enabled.

See [SECURITY.md](SECURITY.md) for disclosure guidance and the production
checklist.

## Local setup

Requires Python 3.11 or newer.

```bash
git clone https://github.com/RolandGasparyan/BOOKING-AI-AGENT.git
cd BOOKING-AI-AGENT
./scripts/setup.sh
```

If `python3` is older than 3.11, select a newer interpreter explicitly with
`PYTHON_BIN=python3.11 ./scripts/setup.sh`.

The setup script creates a private `.env`, installs the hash-verified lock file,
initializes the database, runs both regression suites, and performs a
loopback-only health check. It never pulls, updates, or executes remote shell
content.

For manual setup:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-bootstrap.lock
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements.lock
install -m 600 .env.template .env
PYTHONPATH=. .venv/bin/python -m uvicorn api.app:app --host 127.0.0.1 --port 5000
```

Set `ENVIRONMENT=development` for local work. Production intentionally refuses
to start with placeholder, short, wildcard, non-HTTPS, or externally bound
security settings.

## Configuration

Generate a different value for every application-managed secret:

```bash
openssl rand -hex 32
```

At minimum, production requires:

- `WEBHOOK_SECRET` — admin API secret sent as `X-Webhook-Secret`.
- `WEBHOOK_URL` — public HTTPS origin.
- `ALLOWED_HOSTS` and `ALLOWED_ORIGINS` — explicit production values.

When a channel is enabled, also configure its provider credentials and its
matching verification secret. Leave unused optional channels blank; blank
webhook secrets fail closed. Never reuse `WEBHOOK_SECRET` as a provider secret.

The main optional controls are:

- `FESTIVAL_SCOUT_ENABLED=false`
- `FESTIVAL_OUTREACH_ENABLED=false`
- `POSTIZ_AUTO_PUBLISH_ENABLED=false`
- `SESSION_MAX_COUNT=500`
- `SESSION_TTL_SECONDS=3600`
- `MAX_REQUEST_BYTES=1048576`

`META_GRAPH_API_VERSION` makes provider-version upgrades explicit. Test an
upgrade before changing it.

## Verification

```bash
.venv/bin/python tests/integration_test.py
.venv/bin/python tests/e2e_test.py
.venv/bin/python -m compileall -q api core adapters dashboard migrations workers utils tests
```

CI additionally runs Ruff, Bandit, and `pip-audit`. Production and CI install
from hash-verified lock files. Update a lock file whenever its corresponding
input file changes:

```bash
uv pip compile requirements.txt --python-version 3.11 --generate-hashes -o requirements.lock
uv pip compile requirements-dev.txt --python-version 3.11 --generate-hashes -o requirements-dev.lock
uv pip compile requirements-bootstrap.txt --python-version 3.11 --generate-hashes -o requirements-bootstrap.lock
```

## API routes

| Purpose | Route | Authentication |
| --- | --- | --- |
| Web chat | `POST /api/chat/incoming` | Public, rate-limited by Nginx |
| Availability | `GET /api/booking/availability` | Public, rate-limited |
| Booking submit | `POST /api/booking/submit` | Public, validated/rate-limited |
| Booking detail | `GET /api/booking/{id}` | Admin secret |
| Telegram | `POST /api/webhook/telegram` | Telegram secret header |
| Meta FB/IG | `POST /api/webhook/meta` | Meta HMAC |
| WhatsApp Cloud | `POST /api/webhook/whatsapp` | Meta HMAC |
| Twilio WhatsApp | `POST /api/webhook/twilio/whatsapp` | Twilio signature |
| Viber | `POST /api/webhook/viber` | Viber HMAC |
| Twilio voice | `POST /api/webhook/twilio/voice` | Twilio signature |
| Vapi | `POST /api/webhook/vapi` | Vapi webhook secret |
| Inbound email | `POST /api/webhook/email` | Email webhook secret |
| Admin | `/api/admin/*` | Admin secret |

Register and verify configured channels from the server:

```bash
PYTHONPATH=. .venv/bin/python scripts/connect_channels.py --check
PYTHONPATH=. .venv/bin/python scripts/connect_channels.py
```

The connector does not print verification-token values. Read them directly
from the protected server `.env` when a provider dashboard asks for one.

Armenian (`hy`) is the system fallback for chat and booking communications.
Explicit English and Russian messages are still answered in their detected
language. Browser voice chat uses Armenian (`hy-AM`) by default. Twilio speech
recognition accepts Armenian (`hy-AM`), but Twilio `<Say>` does
not currently provide Armenian text-to-speech. Spoken Armenian phone replies
therefore require a separately configured voice provider that explicitly lists
Armenian TTS support. The application must not claim Armenian phone speech is
active when only Twilio `<Say>` is configured.

## Production deployment

The GitHub Actions workflow runs the full quality gate before deploying `main`.
It requires `SSH_HOST`, `SSH_PORT`, `SSH_USER`, `SSH_PRIVATE_KEY`, and a pinned
`SSH_KNOWN_HOSTS` value. The deploy user needs narrowly scoped passwordless
`sudo` for the included service/Nginx installation and restart commands.

Production configuration lives only at:

```text
/opt/reincarnation_booking/shared/.env
```

The workflow uses immutable releases, hash-verified dependencies, a SQLite
online backup, migrations as `www-data`, an atomic symlink switch, a database
readiness check, and rollback on a failed service health check. The manual
equivalent is `deploy/deploy.sh` and must be run as root from a trusted checkout.

Do not commit `.env`, database files, private keys, provider payloads, or
production logs.

## Architecture

- `api/` — FastAPI gateway, validation, authentication, routes.
- `core/` — booking rules, SQLite ledger, LLM/session core, security helpers.
- `adapters/` — provider payload parsing, signature checks, outbound delivery.
- `dashboard/` — Telegram admin approval flow.
- `workers/` — bounded background jobs and opt-in festival scouting.
- `migrations/` — versioned schema upgrades.
- `static/` — dependency-free web client.
- `deploy/`, `nginx/` — hardened production service and reverse proxy.

## Operational notes

- Run one application worker. The scheduler and in-memory conversation sessions
  are process-local, and SQLite is intended for a single application instance.
- A booking reaches `CONFIRMED` only after both financial and approval gates.
- `AWAITING_DEPOSIT` means approval is complete but payment is still missing;
  `AWAITING_APPROVAL` means the deposit is verified but approval is still missing.
- Recording a deposit requires the contract total; zero, non-finite, duplicate,
  and below-50% deposits are rejected.
- API documentation is available only outside production at `/docs`.
