import ccxt
import pandas as pd

def fetch_full_history(pair, timeframe="1d", limit=500):
    exchange = ccxt.kucoin({"enableRateLimit": True})
    ohlcv = exchange.fetch_ohlcv(pair, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df
