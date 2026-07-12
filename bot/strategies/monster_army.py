import pandas as pd
import os

def add_signals(df):
    d = df.copy()

    ADX_THR   = float(os.getenv("ADX_THRESHOLD",   17))
    VOL_BURST = float(os.getenv("MIN_VOLUME_BURST", 1.1))
    BRK_WIN   = int(os.getenv("BREAKOUT_WINDOW",    5))

    # === EMA trend ===
    d["ema_fast"] = d["close"].ewm(span=9).mean()
    d["ema_slow"] = d["close"].ewm(span=21).mean()
    d["ema_200"]  = d["close"].ewm(span=200).mean()

    # === ATR ===
    high, low, close = d["high"], d["low"], d["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    d["atr14"] = tr.rolling(14).mean()

    # === ADX ===
    plus_dm  = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm   < minus_dm] = 0
    minus_dm[minus_dm < plus_dm]  = 0
    atr14    = d["atr14"]
    plus_di  = 100 * (plus_dm.rolling(14).mean()  / (atr14 + 1e-9))
    minus_di = 100 * (minus_dm.rolling(14).mean() / (atr14 + 1e-9))
    dx       = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    d["adx"] = dx.rolling(14).mean()

    # === Volume burst ===
    d["vol_ma"]    = d["volume"].rolling(20).mean()
    d["vol_burst"] = d["volume"] / (d["vol_ma"] + 1e-9)

    # === Breakout ===
    d["breakout_high"] = d["high"].rolling(BRK_WIN).max().shift(1)
    d["breakout"]      = d["close"] > d["breakout_high"]

    # === Momentum (ROC 10) ===
    d["momentum"] = d["close"].pct_change(10)

    # === RSI ===
    delta = d["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    d["rsi"] = 100 - (100 / (1 + gain / (loss + 1e-9)))

    # === RAW conditions ===
    entry_cond = (
        (d["ema_fast"] > d["ema_slow"]) &      # short-term uptrend
        (d["close"]    > d["ema_200"]) &       # above long-term trend
        (d["adx"]      > ADX_THR) &            # trend strength
        (d["vol_burst"]> VOL_BURST) &          # volume confirmation
        (d["breakout"])                &       # price breaking out
        (d["momentum"] > 0) &                  # positive momentum
        (d["rsi"].between(35, 65))             # RSI mid-range (not OB/OS)
    )
    exit_cond = (
        (d["ema_fast"] < d["ema_slow"]) |      # trend reversal
        (d["rsi"] > 72)                        # overbought
    )

    # === STATE MACHINE: track in_position to prevent signal overlap ===
    signals = [0] * len(d)
    in_pos  = False
    for i in range(len(d)):
        if not in_pos and entry_cond.iloc[i]:
            signals[i] = 1
            in_pos = True
        elif in_pos and exit_cond.iloc[i]:
            signals[i] = -1
            in_pos = False

    d["signal"] = signals
    return d
