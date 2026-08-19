---
type: system-status
project: REINCARNATION Booking AI Agent
status: production
updated: 2026-08-19
tags: [reincarnation, booking-ai, production, vps, github, obsidian]
---

# REINCARNATION Booking AI Agent — Current Status

## Production

- Live URL: https://booking.6-empires.com/
- Health URL: https://booking.6-empires.com/health
- GitHub: https://github.com/RolandGasparyan/BOOKING-AI-AGENT
- Branch: `main`
- Live release: `2379caacfbfa1c3baca9f89535e32d610fb30e14`
- Verified deploy run: https://github.com/RolandGasparyan/BOOKING-AI-AGENT/actions/runs/32240314957
- Deployment: GitHub Actions atomic release to the booking VPS
- Service: `REINCARNATION Booking v3`
- DNS: `booking.6-empires.com` points to `165.227.95.37`
- TLS: valid Let's Encrypt certificate
- Official booking email: `bookings@reincarnation.am`
- Official general email: `info@reincarnation.am`

## Verified channels

| Channel | Status | Verification |
|---|---|---|
| Web chat | Live | Production health, UI, Armenian pricing reply and session API passed |
| LLM | Live | AIMLAPI model endpoint reachable; configured model is available |
| Armenian voice | Live | Twilio outbound call accepted; AIMLAPI Speech falls back to local Armenian Piper audio |
| Twilio Verify | Live | Verification Service exists; six-digit SMS channel configured |
| Telegram | Live | `@reincarnation_ai_bot`, webhook connected, no pending updates; live message accepted |
| WhatsApp (WAHA) | Live, deploy-pinned | `booking` session WORKING as `+37495776665`; every production deploy now fails and rolls back if the live session is unavailable |
| WhatsApp (Twilio) | Live | `whatsapp:+14155238886` sender ONLINE |
| WhatsApp Cloud | Disabled | No Cloud API credentials; WAHA/Twilio are the active WhatsApp transports |
| Facebook Messenger | Live API connection | Page token valid for Reincarnation Orchestra |
| Instagram | Live API connection | Instagram/Page token valid for Reincarnation Orchestra |
| Vapi voice | Live API connection | Configured assistant found; `+37495776665` attached |
| Email | Live | Loopback SSH relay accepted a live message from `bookings@reincarnation.am` to `info@reincarnation.am` |
| Festival outreach | Verified, sending gated | Production dry-run found 9 leads and 2 verified contacts; proposal preview, SMTP relay, deduplication and safety gates passed. Automatic external email remains controlled by `FESTIVAL_OUTREACH_ENABLED` |
| Viber | Commercial application sent | Official onboarding request sent on 2026-08-19 from `bookings@reincarnation.am` to Viber partner Infosintez (covers Armenia); adapter, live HTTPS webhook and automatic registration are ready for the approved token |
| Google Calendar | Live | Dedicated `REINCARNATION Booking` calendar; service-account token exchange, live read and create→delete write probe passed from production |
| TikTok | Not integrated | No supported direct-message adapter or token |

## Confirmed performance calendar

The dedicated `REINCARNATION Booking` Google Calendar contains these confirmed
all-day performance dates for 2026:

| Date | Performance | Location |
|---|---|---|
| 2026-08-22 | REINCARNATION — Jermuk | Jermuk, Armenia |
| 2026-10-24 | REINCARNATION — Los Angeles | Peacock Theater, Los Angeles, CA, USA |
| 2026-11-19 | REINCARNATION — Moscow | Moscow, Russia |

Each event uses a deterministic event ID, so re-running the calendar sync
updates the existing event instead of creating a duplicate.

## Chat and pricing behavior

- Armenian is the default interface and assistant language.
- Armenian replies are guarded against accidental Latin, Cyrillic, or Greek prose leakage.
- The bot does not ask the customer for a budget.
- Once event type, duration, and country are known, the bot states the official applicable fee.
- The Armenian 60-minute private-event live test returned 6,300,000 AMD.
- Russian declined city forms such as `В Москве` route to international USD pricing.
- Երևանի հանրային 40-րոպեանոց set-ը և 40-րոպեանոց մասնավոր միջոցառումը հստակ տարանջատված են՝ համապատասխանաբար 5,500,000 և 5,000,000 ՀՀ դրամից։
- Technical Rider 2026-ը վերակառուցված 8-էջանոց PDF է՝ Audio/F.O.H., Backline, Stage Plot, input channels և տեխնիկական կոնտակտներով։
- General Permissions-ը համադրված է պաշտոնական գների, 50% կանխավճարի, չեղարկման կանոնի և ընթացիկ կայքի/կոնտակտների հետ։
- Technical Rider-ի ներբեռնումը և live availability/calendar գործառույթները միացված են։

## Voice behavior

- Voice calls use Armenian speech and `hy-AM` recognition.
- AIMLAPI Speech is attempted first.
- When AIMLAPI Speech has no credits or fails, the server generates Armenian WAV audio with the pinned local Piper model.
- Generated audio is exposed only through short-lived signed cache URLs.

## Last verification

- Date: 2026-08-19 (Asia/Yerevan)
- Release: `2379caacfbfa1c3baca9f89535e32d610fb30e14`
- CI: compile, Ruff, Bandit, dependency audit, integration, E2E and webhook security passed
- Regression totals: integration 148/148; E2E 140/140; production health 27/27
- VPS: atomic deployment, systemd, nginx, HTTPS, TLS, DB integrity and disk checks passed
- Live delivery: Twilio call, WhatsApp message, Telegram message and email accepted by their configured providers; Google Calendar live read/write/delete passed
- Secrets remain in GitHub Actions/VPS environment configuration and are not stored in this note
