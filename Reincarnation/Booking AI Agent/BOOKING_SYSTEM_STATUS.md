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
| WhatsApp (WAHA) | Live | `booking` session WORKING as `+37495776665`; outbound live message accepted |
| WhatsApp (Twilio) | Live | `whatsapp:+14155238886` sender ONLINE |
| WhatsApp Cloud | Disabled | No Cloud API credentials; WAHA/Twilio are the active WhatsApp transports |
| Facebook Messenger | Live API connection | Page token valid for Reincarnation Orchestra |
| Instagram | Live API connection | Instagram/Page token valid for Reincarnation Orchestra |
| Vapi voice | Live API connection | Configured assistant found; `+37495776665` attached |
| Email | Live | Loopback SSH relay accepted a live message from `bookings@reincarnation.am` to `info@reincarnation.am` |
| Viber | Not configured | No commercial Viber bot/token exists; adapter stays disabled |
| Google Calendar | Not configured | No Calendar ID/service-account credentials; adapter stays disabled |
| TikTok | Not integrated | No supported direct-message adapter or token |

## Chat and pricing behavior

- Armenian is the default interface and assistant language.
- Armenian replies are guarded against accidental Latin, Cyrillic, or Greek prose leakage.
- The bot does not ask the customer for a budget.
- Once event type, duration, and country are known, the bot states the official applicable fee.
- The Armenian 60-minute private-event live test returned 6,300,000 AMD.
- Russian declined city forms such as `В Москве` route to international USD pricing.
- Technical Rider and live availability/calendar functions are deployed.

## Voice behavior

- Voice calls use Armenian speech and `hy-AM` recognition.
- AIMLAPI Speech is attempted first.
- When AIMLAPI Speech has no credits or fails, the server generates Armenian WAV audio with the pinned local Piper model.
- Generated audio is exposed only through short-lived signed cache URLs.

## Last verification

- Date: 2026-08-19 (Asia/Yerevan)
- CI: compile, Ruff, Bandit, dependency audit, integration, E2E and webhook security passed
- Regression totals: integration 123/123; E2E 136/136
- VPS: atomic deployment, systemd, nginx, HTTPS, TLS, DB integrity and disk checks passed
- Live delivery: Twilio call, WhatsApp message, Telegram message and email accepted by their configured providers
- Secrets remain in GitHub Actions/VPS environment configuration and are not stored in this note
