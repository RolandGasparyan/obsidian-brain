import pandas as pd

def add_indicators(df):
    # EMA 20
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()

    # EMA 50
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    # RSI 14
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    return df
