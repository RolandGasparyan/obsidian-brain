---
type: system-status
project: REINCARNATION Booking AI Agent
status: production
updated: 2026-08-01
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

## Verified channels

| Channel | Status | Verification |
|---|---|---|
| Web chat | Live | Armenian AI response and browser smoke test passed |
| Telegram | Live | `@reincarnation_ai_bot`, webhook connected, no pending updates or reported webhook error |
| WhatsApp Cloud | Live | Token, permissions, phone number, verify handshake, and signed webhook passed |
| Facebook Messenger | Live | Page token valid; `messages` and `messaging_postbacks` subscription active |
| Instagram | Live | `@reincarnationorchestra` linked to the Facebook Page; token and messaging permission valid |
| Viber | Disabled intentionally | Adapter and deployment path are ready, but no paid Viber bot account/token exists |
| TikTok | Not integrated | No messaging adapter or token; excluded from the active booking channels |

## Chat behavior

- Armenian is the default interface and assistant language.
- The assistant typing state shows a slowly rotating REINCARNATION logo.
- The localized typing label and animated dots remain visible for at least 900 ms.
- English and Russian interface translations remain available.
- Technical Rider and live availability/calendar functions are deployed.

## Operations

- Secrets stay in GitHub Actions/VPS environment configuration and are not stored in this note.
- The Viber status endpoint reports the real configuration state instead of claiming an inactive webhook is active.
- A future `VIBER_AUTH_TOKEN` secret will propagate automatically from GitHub Actions to the VPS.
- Viber remains off because new Viber bots require commercial approval and a paid contract.

## Last verification

- Date: 2026-08-01 (Asia/Yerevan)
- CI: compile, lint, static security, dependency audit, integration regression, and webhook security passed
- VPS: atomic deployment and health check passed
- Browser: Armenian chat response, typing animation, and zero console errors verified

