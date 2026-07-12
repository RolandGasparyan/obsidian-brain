---
title: Kronos — K-line forecasting model
type: system
tags: [trading-guru-empire, ml, forecasting, research]
updated: 2026-06-08
---

# 🔮 Kronos — financial K-line foundation model

[shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos) — first open-source foundation model for financial candlesticks (decoder-only transformer, MIT, AAAI 2026). **Forecasts** future OHLCV from history; **does not trade**. Installed at `~/tradingguru-empire/research/Kronos` (Python 3.11 venv).

## What it does
- Tokenizes OHLCV K-lines → predicts future candles (open/high/low/close/volume/amount)
- Pretrained weights on HuggingFace (`NeoQuasar/Kronos-*`): mini 4.1M · small 24.7M · base 102M
- Probabilistic sampling (T, top_p, sample_count) → forecast distributions
- Can be fine-tuned on your own data (Qlib pipeline)

## Run a forecast
```bash
cd ~/tradingguru-empire/research/Kronos
source .venv/bin/activate
python examples/prediction_example.py   # downloads Kronos-small + tokenizer from HF, plots forecast
```

```python
from model import Kronos, KronosTokenizer, KronosPredictor
tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
mdl = Kronos.from_pretrained("NeoQuasar/Kronos-small")
pred = KronosPredictor(mdl, tok, max_context=512)
# pred.predict(df=ohlcv_df, x_timestamp=..., y_timestamp=..., pred_len=120)
```

## Empire fit (research / signal, not execution)
- Feed it your `data/btc_1h.csv` / `eth_1h.csv` (29,784 bars each) → forecast next bars
- Use forecasts as an input *signal* for the [[Councils_28|councils]] / strategy research — **never** auto-execute. Author's own README: this is a demo, not a production trading system.
- Pairs with [[Free_APIs_Reference]] (live OHLCV) and [[OpenAlice_Paper]] (paper sim).

> [!note] Forecasts ≠ trades
> Kronos outputs predicted candles. Turning a forecast into an order is a separate, deliberate decision — keep `LIVE_ORDERS=0`.

Related: [[Trading_Guru_Empire_MOC]]
