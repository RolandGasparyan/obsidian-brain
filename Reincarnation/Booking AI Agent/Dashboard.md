---
tags: [booking-ai-agent, reincarnation, production]
updated: 2026-08-01
commit: 806eb2b
---

# 🎯 Booking AI Agent — Dashboard

> Synchronized from the production repository and live verification record.
> Last sync: **2026-08-01** (booking repository commit `806eb2b`)

## 📚 Documentation

- [[PROJECT_SUMMARY]] — status, overview, quick start
- [[ARCHITECTURE]] — system design, components, event flows
- [[DEPLOYMENT_LOG]] — deployment history and fixes
- [[QUICK_REFERENCE]] — CSS fixes, debugging, emergency procedures
- [[OBSIDIAN_IMPORT]] — vault structure and note templates
- [[README]] — repository readme
- [[SECURITY]] — security policy
- [[BOOKING_SYSTEM_STATUS]] — current production and connected-channel source of truth

## 🔗 Live services

| What | Where |
|------|-------|
| Production site | https://booking.6-empires.com |
| Droplet | empire-cpu · 64.227.6.197 · NYC1 · Ubuntu 22.04 |
| App (internal) | http://172.17.0.1:5000 |
| Repository | https://github.com/RolandGasparyan/BOOKING-AI-AGENT |

## 📡 Connected channels

| Channel | Status |
|---|---|
| Web chat | 🟢 Live |
| Telegram | 🟢 Live |
| WhatsApp Cloud | 🟢 Live |
| Facebook Messenger | 🟢 Live |
| Instagram | 🟢 Live |
| Viber | ⏸ Disabled intentionally — no commercial bot token |
| TikTok | ⚪ Not integrated |

## 🩺 Check production health

Open the droplet's **Web Console** on DigitalOcean and run:

```bash
bash /opt/reincarnation_booking/current/scripts/prod_healthcheck.sh
```

It verifies the systemd service, the `/health` endpoint, the served UI
(including that the mobile layout fixes are really live), nginx, public
HTTPS, the TLS certificate, the database and disk.

## 🔄 Refresh this vault

```bash
bash scripts/sync_obsidian_mac.sh
```
