# Stage 1 forward-test runbook

**Deployment:** VPS `167.71.24.86` · **Mode:** paper-real · **Strategy:** MA50+W10 on 1d bars

## Overview

Four independent systemd services run the MA50+W10 strategy against real
Gate.io candles with fake money — one service per pair:

| Pair | Service | Paper capital | Log |
|---|---|---:|---|
| `ETH_USDT`  | `trading-bot@ETH_USDT.service`  | $250 | `/var/log/trading-bot-ETH_USDT.log` |
| `SOL_USDT`  | `trading-bot@SOL_USDT.service`  | $250 | `/var/log/trading-bot-SOL_USDT.log` |
| `XRP_USDT`  | `trading-bot@XRP_USDT.service`  | $250 | `/var/log/trading-bot-XRP_USDT.log` |
| `AVAX_USDT` | `trading-bot@AVAX_USDT.service` | $250 | `/var/log/trading-bot-AVAX_USDT.log` |

Each bot polls Gate.io every 10 s, recomputes the MA50+W10 signal from
live daily candles, and flips between LONG and USDT as the signal
dictates. **No real money is at risk in this stage.**

The service unit template is `/etc/systemd/system/trading-bot@.service`.
It enforces per-bot caps of 256 MB RAM and 40% CPU, auto-restarts on
failure after 15 s, and has `RuntimeMaxSec=7d` so the forward-test
stops itself after one week.

## Quick status

```bash
ssh root@167.71.24.86 bot-status
```

Returns a coloured table: pair · state · restarts · memory · position ·
last observed price · equity · ROI.

## JSON status endpoint

Refreshed every minute by a root cron entry (`/etc/cron.d/bot-status-json`),
served as a static file by nginx:

```
GET http://167.71.24.86/api/bots.json
```

Example payload:

```json
{
  "generated_at": "2026-04-24T14:13:00Z",
  "bots": [
    { "pair": "ETH_USDT", "state": "active", "restarts": 0,
      "pos": "LONG", "price": 2314.60, "equity": 249.93,
      "roi_pct": -0.03, "trades": 1 }
  ]
}
```

This is the hook for wiring the frontend (or any external monitor) to
bot state without giving read access to the VPS.

## Trade history

```bash
ssh root@167.71.24.86 bot-trades              # all four pairs
ssh root@167.71.24.86 bot-trades ETH_USDT     # just one
```

Every entry is a line like:

```
2026-04-24 14:13:35,071 | INFO | 📈 MA-BUY  ETH_USDT @2312.35 units=0.107980
2026-04-27 09:05:02,411 | INFO | ✅ MA-SELL ETH_USDT @2401.77 pnl=+9.65 (+3.86%)
```

## Stream live logs

```bash
ssh root@167.71.24.86 'tail -f /var/log/trading-bot-ETH_USDT.log'

# all four at once
ssh root@167.71.24.86 'tail -f /var/log/trading-bot-*.log'
```

## Start / stop / restart

```bash
# one pair
ssh root@167.71.24.86 'systemctl restart trading-bot@ETH_USDT'

# all four
ssh root@167.71.24.86 'for p in ETH_USDT SOL_USDT XRP_USDT AVAX_USDT; do \
    systemctl restart trading-bot@$p; done'
```

## What "healthy" looks like — red-flag checklist

| Signal | Healthy | Red flag → investigate |
|---|---|---|
| `restarts` in `bot-status` | `0` | `> 3` within a day — bot is crashlooping |
| Memory per bot | 20–40 MB | Near 256 MB — leak, systemd will OOM-kill |
| Trade count after 7 days | **1–6 per pair** | `> 15` — strategy is whipsawing, not the 6–15/yr backtest profile |
| Drawdown (DD in status line) | `< 15%` | `≥ 15%` — approaches the live-mode circuit breaker threshold |
| Fetch errors in log | rare/none | repeated `fetch_bars empty` — Gate.io rate-limiting or network issue |

## Stage-1 exit criteria (after 7 days)

Promote to Stage 2 (live small-capital trading) only if **all** of these
hold on every pair:

1. Bot stayed `active` the entire week, `restarts` ≤ 3
2. Total trade count in the range `1–6` per pair
3. Observed pnl matches the backtest expectation within an order of
   magnitude (trend-following in bull regime, flat-to-small-negative in
   chop/bear)
4. No `Traceback` or `ERROR` entries in any log
5. The bot's position matches the manually-computed MA50+W10 signal
   (cross-check by running `select_best_tokens.py` or computing
   `price > SMA50(daily) AND weekly_close > SMA10(weekly)`)

If any one of these fails, do **not** flip `LIVE_MODE = True`. Diagnose
and patch first.

## Rotating / purging logs

Configured in `/etc/logrotate.d/trading-bot`: daily rotation, gzip
compression, 14-day retention, 20 MB per-file cap. Logs never need to
be touched manually during a 7-day run.

To wipe and restart clean (e.g. after a strategy change):

```bash
ssh root@167.71.24.86 'for p in ETH_USDT SOL_USDT XRP_USDT AVAX_USDT; do \
    > /var/log/trading-bot-$p.log; \
    systemctl restart trading-bot@$p; \
  done'
```

## Redeploying strategy changes

```bash
# locally: commit + push
git commit -am "tweak strategy"
git push origin main

# VPS: pull + restart bots
ssh root@167.71.24.86 '
  cd /var/www/ai-trading-championship && \
  GIT_SSH_COMMAND="ssh -i /root/.ssh/github_deploy_ai_trading -o IdentitiesOnly=yes" \
    git pull --ff-only origin main && \
  for p in ETH_USDT SOL_USDT XRP_USDT AVAX_USDT; do \
    systemctl restart trading-bot@$p; \
  done
'
```

## Telegram alerts

One-time setup:

```bash
# 1. In Telegram, message @BotFather → /newbot → name your bot → copy
#    the token (looks like "7123456789:AAH…")
# 2. Send any message to your new bot (this creates the chat)
# 3. Find your chat id:
curl "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq '.result[0].message.chat.id'
# 4. Add the env vars to the trading-bot unit so every restart picks
#    them up:
ssh root@167.71.24.86
systemctl edit trading-bot@.service
# In the opened editor, paste:
#   [Service]
#   Environment=TELEGRAM_BOT_TOKEN=7123456789:AAH...
#   Environment=TELEGRAM_CHAT_ID=123456789
systemctl daemon-reload
for p in ETH_USDT SOL_USDT XRP_USDT AVAX_USDT; do
  systemctl restart trading-bot@$p
done
# 5. Smoke-test:
cd /var/www/ai-trading-championship && venv/bin/python telegram_alerts.py
```

Event types the bots push:

| Event | When |
|---|---|
| 🚀 *Bot online* | bot starts / restarts |
| 📈 *MA-BUY* | strategy enters LONG |
| ✅ *MA-SELL* (or ❌) | strategy exits LONG |
| ⚠️ *DRAWDOWN* | equity −7.5% from peak (one-shot) |
| 🛑 *CIRCUIT BREAKER* | equity −15% from peak → flatten & stop |

Missing env vars = no-op (bot runs fine, just silent).

## Kill switch

The four paper bots can be stopped / started / restarted from the
`/dashboard` page via an HTTP control plane.

- Service: `bot-control.service` (Python stdlib HTTP server, port 5055)
- Endpoint: `POST /api/control/{stop-all, start-all, restart-all}`
  and `POST /api/control/{stop, start, restart}/<pair>`
- Auth: `X-Control-Token` header matching `/etc/trading-bot-control.token`

To use:

```bash
# 1. Grab the token (run once, paste into the browser)
ssh root@167.71.24.86 'cat /etc/trading-bot-control.token'

# 2. Open http://167.71.24.86/dashboard → KILL SWITCH panel
# 3. Click 🔑 set token → paste → Save
# 4. Use STOP ALL · RESTART ALL · START ALL · STATUS as needed
```

CLI equivalents (useful from scripts):

```bash
TOKEN=$(ssh root@167.71.24.86 cat /etc/trading-bot-control.token)
curl -X POST -H "X-Control-Token: $TOKEN" http://167.71.24.86/api/control/stop-all
curl -X POST -H "X-Control-Token: $TOKEN" http://167.71.24.86/api/control/restart/ETH_USDT
curl       -H "X-Control-Token: $TOKEN" http://167.71.24.86/api/control/status
```

## Domain + HTTPS

Setup staged for `tradingguru.ai` (Hostinger DNS):

1. In the Hostinger DNS panel: set the `@` A record to `167.71.24.86`
   (TTL 300). Optional: `www` CNAME → `tradingguru.ai`.
2. Once `dig tradingguru.ai @1.1.1.1` returns `167.71.24.86`:
   ```
   ssh root@167.71.24.86 /usr/local/bin/issue-cert
   ```
   This runs certbot webroot issuance and swaps in the pre-staged
   HTTPS nginx config (`ai-trading-championship.https.ready`).
3. Auto-renewal is handled by the `certbot.timer` systemd unit.

## File map on VPS

```
/etc/systemd/system/trading-bot@.service   template unit
/etc/logrotate.d/trading-bot               log rotation rules
/etc/cron.d/bot-status-json                refreshes /api/bots.json every minute

/usr/local/bin/bot-status                  terminal dashboard
/usr/local/bin/bot-trades                  grep trades from logs
/usr/local/bin/bot-status-json             JSON generator for the API endpoint
/usr/local/bin/redeploy-trading            git pull + npm build for the frontend

/var/log/trading-bot-*.log                 one log per pair, 14 days retained
/var/www/ai-trading-championship/          repo checkout
  ├ dist/                                  frontend build served by nginx
  │ └ api/bots.json                        status snapshot, refreshed each minute
  └ venv/                                  Python 3.12 venv with `requests`
```

## Stopping Stage 1 early

```bash
ssh root@167.71.24.86 '
  for p in ETH_USDT SOL_USDT XRP_USDT AVAX_USDT; do \
    systemctl stop trading-bot@$p; \
    systemctl disable trading-bot@$p; \
  done
'
```

The template unit itself stays in place so re-enabling is one command
per pair. Nothing is lost.
