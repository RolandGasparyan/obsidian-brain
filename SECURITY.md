# Security Policy

## Reporting Vulnerabilities

Do NOT open a public GitHub issue for security vulnerabilities.

Report privately via GitHub Security Advisories:
Settings → Security → Advisories → Report a vulnerability

## What NOT to commit

- API keys (`BINANCE_API_KEY`, `BINANCE_API_SECRET`)
- Telegram tokens (`TG_TOKEN`, `TG_CHAT_ID`)
- Database credentials (`DB_PASS`)
- Any `.env` file (only `.env.example` is tracked)

The `.gitignore` enforces `.env` exclusion. If a secret is accidentally committed, rotate it immediately and contact the repo owner.

## Scope

- `l99_bot/` — trading bot (high sensitivity: exchange API credentials)
- `docs/` — documentation only
- CI secrets must be set via GitHub repository secrets, never hardcoded
