# Quant War Room — Manus-ready build

Pixel-art trading command center recreating the `tradingguru.ai/war-room`
look & feel, with a **TradingView Advanced Chart "remix" panel** skinned into
the retro UI. Vite + React, no backend.

## Run

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # → dist/  (static, drop anywhere)
npm run preview  # serve the production build
```

## What's animated

- **Starfield** — parallax drift + twinkle + planets (`components/Starfield.jsx`)
- **HUD** — live clock, uptime counter, animated XP bar, glowing balance, blinking LIVE dot (`components/HudBar.jsx`)
- **Ticker tape** — seamless marquee with a live random-walk on prices (`components/Ticker.jsx`)
- **Agent office** — canvas pixel scene: agents bob + 2-frame idle, SCAN/SYNC/WALL chips, animated yellow dashed data-links with travelling packets, scanning sweep line, perspective floor grid (`components/AgentOffice.jsx`)
- **TradingView panel** — real live chart, CRT scanline + neon bezel skin, BTC/ETH/SOL/BNB switcher (`components/TradingViewPanel.jsx`)
- Global CRT flicker overlay (`index.css`)

## Manus / dropping into another project

Everything is self-contained under `src/`. Copy `src/` + `index.html` +
`package.json` + `vite.config.js` into your Manus project, or copy the built
`dist/` folder for a zero-dependency static deploy.

## Editing the design

- Palette + every keyframe: `src/index.css` (`:root` vars at top).
- Pixel sprites & staff roster: `src/engine/sprites.js`.
- Render loop / animation logic: `src/components/AgentOffice.jsx`.
