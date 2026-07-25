# Audit & Deploy Log

## 2026-07-25 — RO-SUPREME-RUN

- Fast-forwarded the clean local checkout to `origin/main` at `699adaa`.
- Fixed Python 3.9 import-time failure in `utils/email_engine.py` by enabling postponed annotations.
- Tightened email exception handling to explicit SMTP/OS errors and made festival year calculation timezone-aware.
- Verification: `tests/e2e_test.py` passed 99/99; `tests/integration_test.py` passed 111/111; targeted Ruff check passed.
- Full-repository Ruff still reports pre-existing style/debt findings outside the touched module.
- Live booking health remained `200 OK`; no credentials or trading/deposit safety gates were changed.
- Committed as `b4b4973`, opened PR `#100`, and merged to `main` as `3b058de`.
- GitHub Actions run `30163064257` passed security/regression checks and atomic production deploy.
- Production verification: `reincarnation-booking.service` active, `https://booking.6-empires.com/health` returned `{"status":"ok","service":"REINCARNATION Booking v3"}`, release `3b058de1127417a905bd690835ec64164a7732dd` active.
- Shared environment remains restricted to `600 www-data:www-data`; no secret values were logged.
- Secret inventory verification: GitHub Actions secret names and both VPS env files were checked without exposing values. Obsidian Brain stores audit metadata only; no credentials were added.
- Active production provider material is present for Telegram, Meta Page, OpenAI/LLM, and Twilio voice. WhatsApp, Instagram direct token, Viber, Vapi, Postiz, SMTP password, and SerpAPI entries remain empty or unavailable on the booking VPS.
- Key storage policy remains enforced: secrets stay in GitHub Actions/VPS runtime stores, never in tracked Markdown or Obsidian logs.
- Fixed two additional Python 3.9 connector failures: postponed annotations in `scripts/connect_channels.py` and `scripts/hostinger_dns.py`.
- Hardened connector error handling, normalized URL suffix removal, and marked the Hostinger DNS helper executable. Targeted Ruff is clean.
- Verification: connector CLI smoke checks, E2E 99/99, integration 111/111, and GitHub Actions run `30163761071` all passed.
- PR `#101` merged as `85f3b08`; production release `85f3b080b930152f414c66c6185b280d39f2f082` is active and health is `200 OK`.
- Live read-only channel check: Telegram connected; WhatsApp, Viber, Instagram DM, and Postiz remain unconfigured; Meta Page token is present but expired and requires owner-side token rotation.
- No provider settings, webhooks, or secrets were changed during this check.
- Postiz removal deployed as `0076d85`; production shared env now has zero `POSTIZ_*` entries, with backup retained at `/opt/reincarnation_booking/shared/.env.pre-postiz-removal-20260725-160938`.
- Live smoke after removal: Armenian chat returned a reply, Vapi empty-transcript webhook returned `ok`, unsigned Twilio voice webhook correctly returned `403`, and admin stats keys are only `by_status,total`.
- Outbound call verification remains gated: no recipient/test phone variable exists in the protected production env, so no arbitrary real call was attempted. Inbound Vapi/Twilio voice security and TwiML paths remain verified.
