# PROFITABLE TRADING SETUP BACKUP
## Date: January 27, 2026
## Platform: Gate.io Futures - SHORTS ONLY

---

## CURRENT TRADING CONFIGURATION

### Trading Pairs
```
ETH/USDT:USDT  (Ethereum)
AVAX/USDT:USDT (Avalanche)
```

### Position Settings
```
POSITION_SIZE_USD = $200
LEVERAGE = 50x
EXPOSURE = $10,000 per trade
CYCLE_SPEED = 0.11s (TRIPLED - 545 cycles/min)
DIRECTION = SHORTS ONLY
```

### Consensus Requirements
```
REQUIRED_CONSENSUS = 6/8 votes OR 60% weighted votes
TOTAL_MODEL_WEIGHT = 9.7
```

---

## 8 AI MODELS WITH WEIGHTS

| Model     | Weight | Role                      |
|-----------|--------|---------------------------|
| DeepSeek  | 1.5x   | Quant Architect           |
| Grok      | 1.4x   | Real-Time News Sniper     |
| GPT5      | 1.3x   | Macro Strategist          |
| Claude    | 1.2x   | Contrarian Psychologist   |
| Mistral   | 1.2x   | Risk Quantifier           |
| Gemini    | 1.1x   | Multi-Modal Analyst       |
| Llama     | 1.0x   | High-Speed Scalper        |
| Qwen      | 1.0x   | Pattern Hunter            |

---

## GODS LEVEL RSI LOGIC

```
RSI < 40  = OVERSOLD    -> NO SHORT (wait for bounce)
RSI 40-60 = NEUTRAL     -> CAUTIOUS (low probability)
RSI > 65  = OVERBOUGHT  -> SHORT OPPORTUNITY
RSI > 75  = EXTREME     -> HIGH PROBABILITY SHORT
```

---

## SCORING SYSTEM (100 points max)

| Metric           | Weight | Description                    |
|------------------|--------|--------------------------------|
| PnL              | 30%    | Total profit/loss              |
| Win Rate         | 20%    | Winning trades percentage      |
| Discipline       | 25%    | NO TRADE decisions quality     |
| Drawdown         | 15%    | Maximum drawdown control       |
| Reasoning        | 10%    | Quality of analysis            |

---

## RACE HISTORY (Jan 26, 2026)

```
Total Cycles: 90
Total Trades: 0 (market was oversold)
Correct NO TRADE decisions: 126 per model
Discipline Score: 13.75/25 (35% accuracy)
All models tied at 43.75 points
```

---

## KEY FILES

| File                       | Purpose                        |
|----------------------------|--------------------------------|
| run_championship.py        | Main trading engine            |
| GODS_LEVEL_PROMPTS.py      | AI model prompts & weights     |
| gate_executor.py           | Gate.io API integration        |
| ai_race_scoring_engine.py  | Scoring calculations           |
| leaderboard.json           | Current standings              |
| race_results.json          | Detailed race results          |

---

## SHELL COMMANDS

```bash
# START LIVE TRADING
python3 run_championship.py --mode live

# RUN 24/7 IN BACKGROUND
nohup python3 run_championship.py --mode live > logs/gods_race.log 2>&1 &

# WATCH LIVE OUTPUT
tail -f logs/gods_race.log

# STOP TRADING
pkill -f "run_championship"

# CHECK GATE.IO POSITIONS
python3 -c "from gate_executor import GateExecutor; print(GateExecutor().get_positions())"
```

---

## RESTORE INSTRUCTIONS

1. Ensure Gate.io API keys are set:
   - GATE_API_KEY
   - GATE_API_SECRET

2. Start the application workflow first

3. Run the championship:
   ```bash
   python3 run_championship.py --mode live
   ```

---

## NOTES

- AIs correctly vote NO TRADE when RSI < 40 (oversold)
- System waits for overbought conditions (RSI > 65) to SHORT
- All 8 models vote independently with weighted consensus
- LONGS are automatically closed at startup (SHORTS ONLY mode)
