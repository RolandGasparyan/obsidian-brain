# Deploying the corrected site

**Status:** ready-to-deploy static site. No build step, no dependencies, no
fonts to download — Google Fonts is loaded from CDN, everything else is plain
HTML/CSS.

## Pages

| File              | Purpose                                                                |
|-------------------|------------------------------------------------------------------------|
| `index.html`      | Landing — hero, capital + alive-accounts status, live BTC/ETH/XRP/SOL  |
| `arena.html`      | Replay arena — cursor, event feed, boss moments, heatmap, cycle stats  |
| `agents.html`     | 3 agent slots (MAIN / SUB1 / SUB2) — capital, status, PnL, trades, DD  |
| `leaderboard.html`| Rankings table — sorted by session PnL, real account ids only          |
| `governance.html` | 3-layer architecture + 9-refusals discipline log                       |
| `about.html`      | What this is / isn't · sacred locks table                              |
| `404.html`        | Not-found page                                                         |
| `css/site.css`    | Single shared stylesheet                                               |
| `js/app.js`       | Live-data fetcher: Gate.io tickers + `/api/battle/*.json`              |

## Data sources

The site is a single static bundle. The only runtime dependencies are
read-only HTTP endpoints:

| Endpoint                                                    | Auth     | Used by                |
|-------------------------------------------------------------|----------|------------------------|
| `https://api.gateio.ws/api/v4/spot/tickers`                 | public   | landing-page tickers   |
| `/api/battle/terminal.json` (preferred)                     | none     | index · agents · LB    |
| `/api/battle/live_battle.json` (fallback if terminal missing)| none     | index · agents · LB    |
| `/api/battle/replay-index.json`                             | none     | arena cycle stats      |
| `/api/battle/replay-timeline.json`                          | none     | arena cursor           |
| `/api/battle/replay-events-recent.json`                     | none     | arena event feed       |
| `/api/battle/replay-bosses.json`                            | none     | arena boss moments     |
| `/api/battle/replay-heatmap.json`                           | none     | arena heatmap          |

`terminal.json` / `live_battle.json` are written by
`canary/canary_executor.publish_status()` every 60s on the VPS. If the
file is missing, the JS leaves every value as `—` (it never fabricates).

The Gate.io ticker call is a single public GET — same URL the canary
uses for read-only price fetches (see `arena_shadow_runner.py` and
`paper_battle/shadow_round.py`).

## What's been removed vs. the live site

| Element on live site                                | Status in this build |
|-----------------------------------------------------|----------------------|
| `$1,000,000 USDT — WINNER TAKES ALL` hero          | ❌ removed           |
| `FIRST AGENT TO HIT THE MILLION WINS THE POT`       | ❌ removed           |
| Any hardcoded PnL / win rate / cycle count          | ❌ replaced with `—` |
| Mocked agent rosters (names, personalities, stats)  | ❌ replaced with `—` |
| Mocked leaderboard rows (8 fictional placeholders)  | ❌ now 3 real slots  |
| Live-trading badging / "GO LIVE" CTAs               | ❌ removed           |

## What's kept

- Retro-pixel + CRT visual identity (Press Start 2P / VT323 / scanlines / amber glow / corner brackets)
- Strategy SHA256 lock (`704dd57…`) and 9-refusal discipline log
- The full Replay Arena structure (5 endpoints, polling cadence, empty-state copy)
- 3-layer architecture + 9-refusals discipline log

## What's new in this build

- `js/app.js` polls `/api/battle/*.json` and Gate.io public tickers
  every 10s.
- Landing page now shows live BTC/ETH/XRP/SOL last + 24h change, plus
  real aggregated capital and the alive-accounts count.
- Agents page renders 3 real account cards (MAIN / SUB1 / SUB2) with
  per-account PnL, trades-today, open positions and daily DD.
- Leaderboard renders the **60-minute championship** banner:
  current round id · round leader · overall leader · progress bar.
  Standings are ranked by `round_pnl_usd` for the current in-progress
  round (falls back to session PnL if the publisher predates the
  championship block). A completed-rounds history table shows the last
  12 rounds with per-account PnL deltas and a 🏆 next to each winner.
  All values come straight from `d.championship.*` in `terminal.json`,
  written by `build_rounds_view` in `canary_executor.py`.
- Arena renders the cursor timestamp, event feed, boss moments, heatmap
  and cycle stats from the actual replay endpoints.
- Every page shows a connection-status line so visitors know whether the
  numbers they see are live or whether telemetry has dropped (in which
  case every cell falls back to `—`).

## Option 1 — Apply locally on your Mac (no harness access required)

```bash
# 1. Clone the agent repo if you don't have it
cd ~/Desktop
[ -d agent ] || git clone git@github.com:RolandGasparyan/tradingguru-empire.git agent
cd agent && git pull --rebase origin main

# 2. Switch to the corrected-design branch (or merge PR #7 first)
git checkout claude/corrected-trading-guru-design-takyP || git checkout main

# 3. Copy the full site into the frontend repo's public/ directory
cp -r design/tradingguru-ai-corrected/full-site/* \
      ~/Desktop/ai-trading-championship/public/

# 4. Push the frontend change
cd ~/Desktop/ai-trading-championship
git checkout -b corrected-design
git add public/
git commit -m "corrected design: strip demo data, replace with — empty states"
git push -u origin corrected-design
```

Then open a PR on `ai-trading-championship` against `main`.

## Option 2 — Convert to React/JSX (when frontend access is granted)

When the next Claude session is granted access to
`RolandGasparyan/ai-trading-championship`, it can port these pages into the
existing React/Vite tree:

- `index.html` → `src/pages/LandingPage.jsx`
- `arena.html` → reuse existing `ArenaReplayPanel.jsx`, swap demo props for the empty-state copy here
- `agents.html` → `src/pages/AgentsPage.jsx`
- `leaderboard.html` → `src/pages/LeaderboardPage.jsx`
- `governance.html` → `src/pages/GovernancePage.jsx`
- `about.html` → `src/pages/AboutPage.jsx`

The visual tokens in `css/site.css` should land in
`src/styles/arena-overrides.css` (or whatever the design-tokens file is named).

## Option 3 — Serve as-is

This folder is a fully functional static site. Drop it into any static host
(Cloudflare Pages, Netlify, S3+CloudFront, nginx `/var/www/…`) and it will
render correctly with no build step.
