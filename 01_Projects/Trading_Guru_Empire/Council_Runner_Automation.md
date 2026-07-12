---
title: Council Runner — battle-triggered automation
type: system
tags: [trading-guru-empire, automation, councils]
updated: 2026-06-08
---

# ⚙️ Council Runner — councils fire when a battle starts

Headless bridge: a battle start → council briefings via Gemini (no browser). Installed at `~/tradingguru-empire/council_runner/`.

## Flow
```
start_shadow_round.sh → runtime/shadow_round.pid
        → watch_battle.sh detects it
        → run_councils.mjs → Gemini → briefings/<time>.md
```

## Guardrails
- [!] **DRY_RUN=1 by default** — builds prompts, **$0 spend** until you flip it
- **MAX_USD_PER_DAY** hard cap (`state.json`)
- **STOP** kill-switch file
- Key from `.env` (never hard-coded)
- Briefings only — **never trades**

## Status (2026-06-08)
- Installed + watcher armed in DRY_RUN (no key) → end-to-end test PASSED
- Default councils: `intelligence,risk,strategy`
- Go live: `.env` → set `DRY_RUN=0` + paste valid Gemini key (US keyboard!)
- Reboot persistence: `com.tradingguru.councilwatch.plist` (launchd)

Related: [[Councils_28]] · [[Trading_Guru_Empire_MOC]]
