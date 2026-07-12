def generate_signal(df):
    last = df.iloc[-1]

    # Trend condition
    if last["ema20"] > last["ema50"] and last["rsi"] > 55:
        return "BUY"

    elif last["ema20"] < last["ema50"] and last["rsi"] < 45:
        return "SELL"

    else:
        return "HOLD"
