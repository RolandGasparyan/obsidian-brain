def detect_state(df):
    """
    Simple state detection using close prices
    """

    if len(df) < 2:
        return "UNKNOWN"

    last_close = df["close"].iloc[-1]
    prev_close = df["close"].iloc[-2]

    if last_close > prev_close:
        return "UPTREND"
    elif last_close < prev_close:
        return "DOWNTREND"
    else:
        return "RANGE"
