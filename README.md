# AI Trading Championship

Research and production trading systems.

---

## L99 Testnet Bot

A momentum-based crypto trading bot validated through institutional-grade backtesting.

- **Strategy:** Momentum King Portfolio (4H EMA stack + ADX + Volume breakout)
- **Mode:** TESTNET only — no live capital until pilot validation complete
- **Risk:** 1% per trade | **Max concurrent:** 3 | **Kill DD:** 21%

```bash
cd l99_bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill credentials
python db.py
python preflight.py    # must pass 22/22
python live_bot.py
```

See [docs/DEPLOY_GUIDE.md](docs/DEPLOY_GUIDE.md) for full VPS deployment.

---

## GODS LEVEL ENGINE — Single Pair Focus · 10 Agents · USDT Only

### Quick Start
    pip install requests
    python run.py

### Rules
- Scores ALL pairs → trades the #1 best pair only
- All 10 agents micro-scalp that pair simultaneously
- Pair losing? → EXIT ALL → 100% USDT → select next best pair
- Always 100% USDT between trades — zero token holding

### Live Mode
    export GATEIO_API_KEY=your_key
    export GATEIO_SECRET=your_secret
    python run.py --live
