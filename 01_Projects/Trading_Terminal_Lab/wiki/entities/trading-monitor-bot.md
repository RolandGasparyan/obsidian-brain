---
title: Trading Monitor Bot
created: 2026-08-20
updated: 2026-08-20
type: entity
tags: [telegram, automation, cron, hermes, monitoring]
sources: [Trading_Monitor_Agent.md]
confidence: high
---

# Trading Monitor Bot

Telegram bot @Tradinglab6666_bot that sends hourly VPS health and trading engine status alerts.

## Overview

A `no_agent` cron job (ID: `24a35c6064f8`) that runs `~/.hermes/scripts/trading-monitor.sh` every hour. The script checks:

1. VPS1 Trading Engine (34.139.162.200) — SSH + HTTP
2. VPS2 Canary Real Money (167.71.24.86) — SSH
3. VPS Brain Sync (165.227.164.26) — SSH
4. 6-empires.com — domain availability
5. Ollama (localhost:11434) — local AI
6. Trading Terminal MCP (localhost:8080)
7. Obsidian Brain vault — file count

## Configuration

- **Bot Token:** configured in `~/.hermes/.env`
- **Chat ID:** 779433027 (Roland Gasparyan)
- **Schedule:** `0 * * * *` (every hour)
- **Delivery:** script sends via `curl` to Telegram Bot API directly

## Related

- [[hermes-agent]] — platform hosting the cron job
- [[trading-engine]] — engine being monitored
