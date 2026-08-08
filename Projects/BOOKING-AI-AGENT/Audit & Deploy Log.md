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
