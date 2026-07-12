import ccxt
import pandas as pd

exchange = ccxt.gateio()

SYMBOL = "BTC/USDT"
TIMEFRAME = "15m"

def get_latest_data(limit=100):
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=limit)

    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp","open","high","low","close","volume"]
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    return df

