# BOOKING-AI-AGENT Audit & Deploy Log

## 2026-08-08 — Safe Postiz admin workflow deployed

### Outcome

- Status: **DEPLOYED AND VERIFIED**
- Production: <https://booking.6-empires.com>
- Pull request: <https://github.com/RolandGasparyan/BOOKING-AI-AGENT/pull/109>
- Merge commit: `eaff7fbb10c3b43e60e368fcb9b60ec2b74f761a`
- Deployment run: <https://github.com/RolandGasparyan/BOOKING-AI-AGENT/actions/runs/31230530621>

### Changes

- Added a Postiz Public API client that is structurally limited to `type=draft`.
- Added an explicit integration allowlist and fail-closed validation for missing,
  disabled, unsupported, partial, or mismatched provider responses.
- Added a separate `postiz_drafts` ledger through migration v13. The legacy
  `bookings.postiz_*` columns remain untouched.
- Added atomic claim, completion, `NEEDS_REVIEW`, and explicit administrator
  reconciliation states. Automatic retries are forbidden after ambiguous
  provider outcomes; an in-flight claim cannot be reconciled for five minutes.
- Added admin-only REST routes and Roland-only Telegram `/postiz` commands.
- Kept Postiz disconnected from public chat and automatic booking approval tasks.
- Limited eligible records to `CONFIRMED` Concert/Festival bookings.
- Built outbound copy from a strict public allowlist. Client identity, contact
  details, notes, venue, contract, deposit, and raw payload fields are excluded.
- Added Postiz repository secrets/variables to the immutable VPS deployment.
  Blank repository values now clear stale production values.
- Added a read-only production Postiz integration smoke gate.
- Restored pytest discovery in CI and pinned `pytest==9.0.3` in the hashed dev lock.

### Verification evidence

- Ruff: passed.
- Python compileall: passed.
- Bandit: passed.
- pip-audit for runtime and dev hashed locks: no known vulnerabilities.
- Focused pytest suite: `24 passed`.
- Integration suite: `122/122 passed`.
- HTTP/E2E suite: `124/124 passed`.
- Four independent review lenses completed with no remaining actionable findings.
- GitHub security/regression job: passed.
- Atomic production deployment job: passed.
- Production Postiz read-only smoke: `3 allowlisted integrations verified`.
- Public `/health`: HTTP 200 with the expected booking service response.
- Public UI: HTTP 200.
- Unauthenticated Postiz integrations route: HTTP 403.
- Unauthenticated Postiz draft mutation route: HTTP 403.
- nginx configuration: valid.
- Authenticated Telegram webhook: registered, zero pending updates.
- Shared environment backup created at
  `/opt/reincarnation_booking/backups/env-20260808T003621Z.bak`.

### Operational use

- Telegram: `/postiz` lists eligible confirmed public events.
- Telegram: `/postiz <booking-id-or-prefix>` creates one reviewable draft.
- REST: `GET /api/admin/postiz/integrations` lists sanitized allowlisted channels.
- REST: `POST /api/admin/bookings/{id}/postiz-draft` creates a draft.
- REST: `GET /api/admin/bookings/{id}/postiz-draft` reads the local ledger.
- REST: `POST /api/admin/bookings/{id}/postiz-draft/reconcile` resolves an
  ambiguous provider outcome only after an administrator verifies Postiz.

### Notes

- No production draft was created during deployment verification. Provider smoke
  verification was intentionally read-only.
- GitHub Actions emitted a non-blocking warning that older action revisions target
  Node.js 20 and are currently forced onto Node.js 24 by the runner.
- Graphify generated a local architecture graph with 614 nodes and 1,195 edges.
  It reported dangling/collapsed extraction edges as graph limitations, not
  confirmed application defects.

## 2026-08-08 — Final live hardening and provider truth gate

- Removed the reintroduced Postiz application, admin, ledger, and test paths by reverting the three Postiz commits; retained only immutable legacy migration compatibility.
- Added complete GitHub Actions-to-VPS synchronization for channel, TTS, email webhook, and Google Calendar configuration without logging secret values.
- Isolated concurrent E2E databases and added deployment-configuration regression checks.
- Merged PR `#110` and deployed release `425e39723e75e67c4a7d76f37f252caedb30d163`; quality and atomic deployment jobs passed.
- Live chat verification passed for Armenian, English, and Russian. Armenian output was natural and script-correct; AIMLAPI TTS returned a valid HTTPS audio asset.
- A user-authorized Twilio call to the protected test recipient completed successfully in production with a 16-second duration. The active caller ID is owned by the configured Twilio account.
- A real WhatsApp outbound probe exposed provider error `63007`. The official Twilio Senders API returned no registered WhatsApp sender; the configured sandbox-style sender is therefore not production-ready.
- Hardened channel verification to query the official Twilio Senders API and report Twilio Voice independently from Twilio WhatsApp.
- Changed outbound WhatsApp API behavior so immediate provider rejection returns `502`; success now states provider acceptance and no longer claims delivery.
- Added `tests/test_verify_channels.py`; final local gates passed: integration `112/112`, E2E `110/110`, Ruff, Bandit, and pip-audit with no known vulnerabilities.
- Merged PR `#111` as `33c20e87ca8b33af531245319e254e75aa68b822`. GitHub Actions run `31236202361` passed and atomically deployed that exact release.
- Post-deploy evidence: `reincarnation-booking.service` is active and `https://booking.6-empires.com/health` returns `ok`.
- Production-ready providers: web chat/API, LLM, Telegram, Facebook Page, Instagram, Twilio Voice, SMTP, and Google Calendar.
- External provider blockers remain explicit: WhatsApp Cloud references inaccessible object `507303355806859`; Twilio has no registered WhatsApp sender; Viber has no auth token; Vapi has no API key, assistant ID, or phone-number ID.
- No provider credentials were generated, guessed, copied into source control, or written to this log.

## 2026-08-08 — Final outbound-call truth fix and clean launch

- Fixed outbound Twilio and Vapi calls so the API waits for immediate provider acceptance instead of returning success before the provider request runs.
- Provider rejection and malformed provider success responses now fail closed with HTTP `502`; successful responses include the provider call ID.
- Removed the unsafe fallback that reused `TWILIO_WA_NUMBER` as a voice caller ID. Voice calls now require the owned `TWILIO_PHONE_NUMBER`.
- Added regression coverage for missing Twilio voice configuration, missing provider IDs, provider rejection, provider acceptance, and Vapi rejection without placing real calls.
- Local verification passed: Ruff, Bandit, compileall, pip-audit with no known vulnerabilities, integration `112/112`, and E2E `115/115`.
- Merged PR `#112`; GitHub Actions run `31237355302` passed and atomically deployed release `84f2a4ee41050368717a7eb5798fe0accb31790b`.
- Corrected `prod_healthcheck.sh` to detect the active Docker nginx proxy when the legacy host `nginx.service` is intentionally inactive, and to validate the running container configuration and loaded booking vhost.
- Merged PR `#113`; GitHub Actions run `31237612709` passed and atomically deployed final release `d1f680ca3d06ec5d40f8f13e7eac59b1b9ad0af4`.
- Final VPS health evidence: `26 passed`, `0 warnings`, `0 failed`; service active and enabled, database integrity passed, public HTTPS returned `200`, HTTP redirected to HTTPS, TLS valid, and no service errors were logged in the last hour.
- Final public live-chat smoke passed in Armenian, English, and Russian. Each response stayed in the user's language; Armenian output was natural and script-correct.
- Final read-only provider verification: web/API, LLM, Telegram, Facebook Page, Instagram, Twilio Voice, SMTP, and Google Calendar passed.
- External account blockers remain explicit: WhatsApp Cloud object `507303355806859` is inaccessible, Twilio has no registered WhatsApp sender, Viber credentials are absent, and Vapi credentials are absent.
- No new real call or outbound platform message was sent during this final verification, and no provider credential was generated, guessed, exposed, or committed.

## 2026-08-08 — Final production health pipeline stabilization

- Fixed an intermittent `prod_healthcheck.sh` false negative caused by `grep -q` closing the Docker nginx configuration pipe early while `pipefail` was active.
- Kept the nginx vhost validation strict while allowing the producer to finish normally; three consecutive pre-deploy live runs passed `26/26` with zero warnings and failures.
- Merged PR `#114`; GitHub Actions run `31238059747` passed and atomically deployed release `b5f7d092f44fa5ca24d89a18c92bed0797e6cc63`.
- Three consecutive checks of the installed production script passed `26/26`; public health, service, database integrity, Docker nginx configuration, booking vhost, HTTPS, redirect, TLS, disk, memory, and recent logs passed.
- Final public chat smoke passed in Armenian, English, and Russian, with every response staying in the user's language.
- Read-only Meta discovery confirmed the configured WhatsApp token is accepted, but WABA enumeration requires the missing `business_management` permission and no phone number was discoverable under the accessible Roland business.
- Read-only provider verification remained `8 working`, `2 failed`, `2 not configured`: WhatsApp Cloud has an inaccessible phone object, Twilio has no registered WhatsApp sender, and Viber/Vapi credentials are absent.
- No provider credential was generated, guessed, printed, committed, or added to this log. No real outbound message or call was placed.

## 2026-08-08 — Provider onboarding security hardening and production release

- Inspected Meta Business Portfolio `458729864550170` through the authenticated browser session. Three approved Reincarnation Orchestra WhatsApp Business Accounts exist: `2207138373371879`, `1755403032553350`, and `1034074986034025`.
- Read-only inspection confirmed that all three WABAs have zero phone numbers. The business verification remains in progress and no payment method is present.
- Hardened `scripts/connect_meta_channels.py` with a read-only `--check` mode, explicit `business_management` permission diagnostics, owned/client WABA discovery, optional explicit WABA IDs, safe env-key insertion, and UTF-8/context-managed env access.
- Removed the unsafe behavior that persisted a temporary Meta user token as `WA_ACCESS_TOKEN`. Apply mode now requires `META_SYSTEM_USER_TOKEN` or `WA_SYSTEM_USER_TOKEN` and fails closed without one.
- Added a focused regression suite proving that temporary user tokens are not persisted or used to subscribe a WABA. Added the suite to GitHub Actions.
- Local evidence passed: focused onboarding tests `2/2`, integration `112/112`, E2E `115/115`, targeted Ruff, Bandit, compileall, and pip-audit with no known vulnerabilities.
- Merged PR `#115` as `578631d87e47bd1b066bd8fd65cecf068433c77c`. GitHub Actions run `31238957555` passed and atomically deployed that exact release.
- Three consecutive post-deploy production health checks passed `26/26` with zero warnings and zero failures. The service is active and enabled; public HTTPS, TLS, Docker nginx, database integrity, backups, disk, memory, and recent logs passed.
- Final read-only channel verification remains truthful: 8 working (web/API, LLM, Telegram, Facebook, Instagram, Twilio Voice, SMTP, Google Calendar), 2 failed (WhatsApp Cloud stale/inaccessible phone object and unregistered Twilio WhatsApp sender), and 2 not configured (Viber and Vapi).
- Meta phone onboarding is prepared in the browser with display name `Reincarnation Orchestra` and category `Entertainment`; the next step creates/updates the business profile and proceeds to phone verification, so it was not submitted without action-time authorization and OTP access.
- Twilio, Viber, and Vapi browser sessions are at their login/registration gates. No provider token was generated, guessed, scraped from repositories, printed, committed, or copied into this log. No real outbound message or call was sent.
