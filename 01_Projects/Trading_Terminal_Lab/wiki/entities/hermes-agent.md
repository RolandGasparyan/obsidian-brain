---
title: Hermes Agent
created: 2026-08-20
updated: 2026-08-20
type: entity
tags: [hermes, ai-agent, automation, telegram, cron]
sources: [Trading_Terminal_Lab_Codebase.md]
confidence: high
---

# Hermes Agent

AI assistant by Nous Research, running on macOS desktop. The platform that hosts [[trading-terminal-lab]].

## Overview

Hermes Agent is a desktop AI assistant with:
- **Terminal** — executes shell commands locally (backend: local)
- **Browser** — web automation via Browser Use
- **File tools** — read/write/patch files
- **Memory** — persistent cross-session memory
- **Cron jobs** — scheduled tasks with Telegram delivery
- **Skills** — 100+ specialized skill files
- **Delegation** — subagent spawning for parallel work

## Trading Terminal Lab Integration

- **Project:** `Trading Terminal Lab` (p_de393953) — Hermes project anchored to `~/Projects/trading-terminal-mcp/`
- **Cron Job:** `24a35c6064f8` — Trading Monitor (hourly VPS health → Telegram)
- **Telegram Bot:** @Tradinglab6666_bot — sends alerts to chat 779433027

## Local AI Models (Ollama)

4 models configured at localhost:11434:
- `qwen2.5-coder:latest` (default)
- `mistral:latest`
- `minicpm-v:8b`
- `glm-5.2:cloud`

## Related

- [[trading-monitor-bot]] — Telegram bot for monitoring
- [[mcp-server]] — MCP server consumed by Hermes
- [[trading-engine]] — engine accessible via MCP
