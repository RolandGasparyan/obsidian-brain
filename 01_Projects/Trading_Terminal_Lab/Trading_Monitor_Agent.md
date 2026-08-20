---
title: Trading Monitor Agent
type: project-doc
tags: [project, trading-terminal-lab, hermes, cron, telegram, monitor]
status: active
updated: 2026-08-20
---

# 🤖 Trading Monitor Agent

> Hermes Super Agent — hourly VPS health & trading engine status checker. Sends alerts to Telegram.

## Configuration

| Setting | Value |
|---------|-------|
| **Bot** | @Tradinglab6666_bot (Trading Lab) |
| **Chat ID** | 779433027 (Roland Gasparyan) |
| **Script** | `~/.hermes/scripts/trading-monitor.sh` |
| **Cron Job ID** | `24a35c6064f8` |
| **Schedule** | `0 * * * *` (every hour) |
| **Mode** | `no_agent` (script-only, no LLM) |

## What It Checks

1. **VPS1 Trading Engine** (34.139.162.200) — SSH + HTTP dashboard + API
2. **VPS2 Canary Real Money** (167.71.24.86) — SSH
3. **VPS Brain Sync** (165.227.164.26) — SSH
4. **6-empires.com** — domain availability
5. **Ollama** (localhost:11434) — local AI models
6. **Trading Terminal MCP** (localhost:8080) — local trading terminal
7. **Obsidian Brain** — vault file count

## Alert Types

- 🚨 **Critical** — VPS down, HTTP error, domain unreachable
- ✅ **All clear** — everything healthy

## Telegram Integration

- Bot sends messages via `curl` to Telegram Bot API
- No Hermes gateway required (script sends directly)
- To enable gateway: `hermes gateway run` (foreground) or `hermes gateway install` (service)

## Related

- [[Trading_Terminal_Lab_MOC]] — parent project
- [[Trading_Guru_Empire_MOC]] — trading ecosystem
