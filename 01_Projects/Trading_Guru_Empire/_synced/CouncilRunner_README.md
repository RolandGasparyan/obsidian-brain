# Council Runner — councils fire when a battle starts

Headless bridge between your **shadow battles** and the **Trading Guru Empire
councils** (the 28 teams from The Delegation). No browser, no 24/7 spend — it
only runs when a battle actually starts.

## How it works

```
start_shadow_round.sh  →  writes runtime/shadow_round.pid
                                  │
                 watch_battle.sh detects the new pid (rising edge)
                                  │
                 run_councils.mjs  →  Gemini API  →  briefings/<time>.md
```

It watches the **existing** PID file your battle already creates — it does not
modify any of your battle scripts.

## Guardrails (read this)

- **DRY_RUN=1 by default** — builds the council prompts and writes them to
  `briefings/`, but makes **zero API calls and spends $0**. Flip to `0` to go live.
- **MAX_USD_PER_DAY** — hard daily cap, tracked in `state.json`. The runner skips
  councils once the cap is hit.
- **STOP kill-switch** — `touch council_runner/STOP` and the watcher exits and the
  runner aborts.
- **Key in `.env`** — read at runtime, never committed, never hard-coded.
- Councils produce **briefings only** — never trade orders. Nothing here places trades.

## Setup

```bash
cd council_runner
cp .env.example .env
#   → paste your Gemini key, choose COUNCILS, set MAX_USD_PER_DAY
#   → leave DRY_RUN=1 for the first battle to confirm it fires safely

# test the wiring without a battle:
DRY_RUN=1 /opt/homebrew/bin/node run_councils.mjs   # writes a dry-run briefing

# run the watcher (foreground):
./watch_battle.sh
```

### Run it 24/7 (survives reboot)

```bash
cp com.tradingguru.councilwatch.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tradingguru.councilwatch.plist
# stop: launchctl unload ~/Library/LaunchAgents/com.tradingguru.councilwatch.plist
```

The watcher idles cheaply (just polling a file) and only calls Gemini when a
battle starts — so "24/7" costs nothing until a round actually launches.

## Going live (when you're ready)

1. `.env`: set `DRY_RUN=0`, confirm `GEMINI_API_KEY` is a clean `AIza…`/valid key,
   set a comfortable `MAX_USD_PER_DAY`.
2. Start a battle as usual (`start_shadow_round.sh`).
3. Read the briefing in `council_runner/briefings/`.

Tune which councils run via `COUNCILS=` (default `intelligence,risk,strategy`).
All 14 unique councils are available; add more = more spend per battle.
