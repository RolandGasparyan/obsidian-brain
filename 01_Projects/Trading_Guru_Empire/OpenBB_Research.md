---
title: OpenBB — research data platform
type: system
tags: [trading-guru-empire, data, research]
updated: 2026-06-08
---

# 📊 OpenBB — investment research data

[OpenBB-finance/OpenBB](https://github.com/OpenBB-finance/OpenBB) — open-source investment research platform. Installed (pip `openbb` 4.7.2 + all providers) at `~/tradingguru-empire/research/OpenBB` (Python 3.11 venv). **Data/research only — not an executor.**

## Verified working
Fetched live BTC-USD history via yfinance (keyless), 366 rows. ✅

## Use it
```bash
cd ~/tradingguru-empire/research/OpenBB && source .venv/bin/activate
python -c "from openbb import obb; print(obb.crypto.price.historical('BTC-USD', provider='yfinance').to_df().tail())"
```
Providers needing keys (FMP, Intrinio, Tiingo, FRED, Benzinga…) are configured via `obb.user.credentials` or `~/.openbb_platform/user_settings.json`. **You add those keys yourself** — I don't store credentials.

## Empire fit
- Pull live OHLCV / fundamentals / macro → feed [[Kronos_Forecasting|Kronos]] forecasts and [[Councils_28|council]] analysis.
- Complements [[Free_APIs_Reference]] (raw API list) with a unified Python SDK.

Related: [[Trading_Guru_Empire_MOC]] · [[Kronos_Forecasting]]
