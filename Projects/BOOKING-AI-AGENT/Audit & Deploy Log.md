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
- Before the user-authorized test, no recipient/test phone variable existed in the protected production env; inbound Vapi/Twilio voice security and TwiML paths were already verified.
- User-authorized Twilio conversational test call completed successfully (`completed`, 44 seconds). The recipient is stored only in protected VPS env as `VOICE_TEST_RECIPIENT`; the number is not in GitHub, source, or Obsidian. Backup created before the env update.

## 2026-07-26 — Postiz removal cleanup

- Removed the active Postiz publishing path from the booking app: approval tasks no longer invoke Postiz, admin stats no longer probe Postiz health, the channel connector no longer advertises a Postiz setup step, and the setup script no longer seeds `POSTIZ_API_KEY`.
- Deleted `utils/postiz_publisher.py` from the writable project copy and removed the user-visible Postiz references from `README.md` and the E2E bootstrap harness.
- Verified that the remaining Postiz mentions are limited to historical SQLite migration columns kept for legacy database compatibility.
- Syntax check passed for the edited Python files with `python3 -m py_compile api/app.py scripts/connect_channels.py tests/e2e_test.py`.
- Cleaned the lockfiles by removing the stray `httpx2` / `httpcore2` dependency entries and their comment residue so the install manifest matches the codebase again.

## 2026-07-26 — Legacy migration cleanup

- Removed the last Postiz-era schema migration entries from `migrations/runner.py` and renumbered the remaining migrations so fresh databases no longer carry any Postiz column setup.
- Updated the integration test to assert the new terminal migration version and keep the schema-migration audit aligned with the current manifest.
- Verification: `python3 -m py_compile migrations/runner.py tests/integration_test.py` passed; direct Postiz / `httpx2` / `httpcore2` searches in the touched project files returned no matches.

## 2026-07-26 — Final verification pass

- Confirmed the chat and voice code paths keep Armenian as the default language for ambiguous or English input, while Russian remains routed to Russian.
- Confirmed the public integrations still present in code are Telegram, Meta/Facebook, WhatsApp, Viber, Vapi, Twilio voice, outbound calls, and outbound WhatsApp; no Postiz publishing path remains.
- Performed syntax sanity checks on `api/app.py`, `scripts/connect_channels.py`, `tests/e2e_test.py`, `tests/integration_test.py`, and `migrations/runner.py`; all passed.
- A temporary dependency-install verification environment was still blocked by package-index disclosure policy, so live runtime chat/voice execution could not be completed from this turn.

## 2026-07-26 — Twilio voice correction

- Fixed the Twilio voice webhook so Armenian calls now speak the actual Armenian reply text instead of an English explanatory notice.
- Kept the fallback TTS voice selection conservative because Twilio’s configured voice catalog does not expose a dedicated Armenian voice in this codebase.
- Re-ran `python3 -m py_compile api/app.py` after the fix; syntax remained clean.

## 2026-07-26 — Launch attempt

- Created a local commit for the remaining Booking AI Agent fixes on `codex/channel-connector-verification`.
- GitHub CLI authentication is still stale in this environment, so `gh`-driven PR flow could not proceed.
- A direct `git push` attempt to `origin` timed out after 60 seconds in this session, so the branch is not yet published upstream from here.

## 2026-07-26 — Twilio voice polish

- Tightened the Twilio voice closing line so Armenian calls now end with the Armenian goodbye text instead of an English fallback sentence.
- Kept the existing conservative TTS fallback behavior intact, because the configured Twilio voice catalog still does not expose a dedicated Armenian voice.

## 2026-07-26 — VPS publish and proxy correction

- Published the current Booking AI Agent release to the VPS and verified the live HTTPS health route returned `ok`.
- Re-aligned the VPS app bind address and nginx upstream to the host bridge address `172.17.0.1:5000` so the public reverse proxy can reach the app again.
- Confirmed the live service is running under systemd and the public `/health` route succeeds through the reverse proxy after reload.
