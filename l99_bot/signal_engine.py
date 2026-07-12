"""
L99 Bot — Signal Engine
Generates entry signals from live 4H OHLCV data.

Stage 0 fix applied:
  Signal confirmed at bar[i] CLOSE.
  Entry order placed at bar[i+1] OPEN (next candle).
  No look-ahead bias.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import ccxt
import numpy as np
import pandas as pd
import ta

import config

logger = logging.getLogger("l99.signal")


@dataclass
class Signal:
    symbol:          str
    signal_time:     datetime   # time of bar close that triggered
    entry_target:    float      # next open — limit order price
    stop_price:      float
    target_price:    float
    atr:             float
    adx:             float
    volume_ratio:    float
    breakout_level:  float


def _build_exchange() -> ccxt.Exchange:
    klass = getattr(ccxt, config.EXCHANGE_ID)
    ex = klass({
        "apiKey":    config.API_KEY,
        "secret":    config.API_SECRET,
        "enableRateLimit": True,
        "options":   {"defaultType": "spot"},
    })
    if config.TESTNET:
        if hasattr(ex, "set_sandbox_mode"):
            try:
                ex.set_sandbox_mode(True)
            except Exception:
                pass
        logger.info("TESTNET flag active — Gate.io has no spot testnet; connecting to live API")
    return ex


_exchange: ccxt.Exchange | None = None


def get_exchange() -> ccxt.Exchange:
    global _exchange
    if _exchange is None:
        _exchange = _build_exchange()
    return _exchange


# ── OHLCV fetch ───────────────────────────────────────────────

def fetch_ohlcv(symbol: str, limit: int = 250) -> pd.DataFrame:
    ex   = get_exchange()
    raw  = ex.fetch_ohlcv(symbol, config.TIMEFRAME, limit=limit)
    df   = pd.DataFrame(raw, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df.set_index("ts", inplace=True)
    return df.astype(float)


# ── Indicator computation ─────────────────────────────────────

def _indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema21"]  = ta.trend.EMAIndicator(df["close"], config.EMA_FAST).ema_indicator()
    df["ema50"]  = ta.trend.EMAIndicator(df["close"], config.EMA_MID).ema_indicator()
    df["ema200"] = ta.trend.EMAIndicator(df["close"], config.EMA_SLOW).ema_indicator()
    df["adx"]    = ta.trend.ADXIndicator(
        df["high"], df["low"], df["close"], config.ADX_PERIOD
    ).adx()
    df["atr"] = ta.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], config.ATR_PERIOD
    ).average_true_range()
    df["vol_ma"]    = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]
    df["breakout_level"] = df["high"].shift(1).rolling(config.BREAKOUT_WINDOW).max()
    return df


# ── Signal check on the LAST COMPLETED bar ───────────────────
# bar[-2] = last closed bar (bar[-1] is the live/forming bar)

def check_signal(symbol: str) -> Signal | None:
    try:
        df = fetch_ohlcv(symbol, limit=250)
    except Exception as e:
        logger.warning("OHLCV fetch failed for %s: %s", symbol, e)
        return None

    if len(df) < 210:
        logger.warning("Insufficient candles for %s: %d (need ≥210)", symbol, len(df))
        return None

    try:
        df = _indicators(df)
    except Exception as e:
        logger.warning("Indicator computation failed for %s: %s", symbol, e)
        return None

    # Last completed bar = iloc[-2]; iloc[-1] is forming
    bar  = df.iloc[-2]
    next_bar = df.iloc[-1]   # we want its open as entry target

    if any(pd.isna([bar["ema21"], bar["ema50"], bar["ema200"],
                    bar["adx"], bar["atr"], bar["breakout_level"]])):
        return None

    trend_ok  = bar["ema21"] > bar["ema50"] > bar["ema200"]
    adx_ok    = bar["adx"]   > config.ADX_THRESHOLD
    vol_ok    = bar["vol_ratio"] > config.VOLUME_MULT
    break_ok  = bar["close"] > bar["breakout_level"]

    if not (trend_ok and adx_ok and vol_ok and break_ok):
        return None

    # Entry target = next candle open (look-ahead-free execution)
    entry_target = next_bar["open"]
    atr          = bar["atr"]
    stop_price   = entry_target - config.ATR_STOP_MULT * atr
    risk_per_unit = entry_target - stop_price
    target_price = entry_target + config.RR_RATIO * risk_per_unit

    sig = Signal(
        symbol         = symbol,
        signal_time    = df.index[-2].to_pydatetime(),
        entry_target   = round(entry_target, 8),
        stop_price     = round(stop_price,   8),
        target_price   = round(target_price, 8),
        atr            = round(atr,          8),
        adx            = round(float(bar["adx"]), 4),
        volume_ratio   = round(float(bar["vol_ratio"]), 4),
        breakout_level = round(float(bar["breakout_level"]), 8),
    )
    logger.info("Signal: %s  entry=%.4f  stop=%.4f  tp=%.4f",
                symbol, sig.entry_target, sig.stop_price, sig.target_price)
    return sig


def scan_all() -> list[Signal]:
    signals = []
    for symbol in config.COINS:
        sig = check_signal(symbol)
        if sig:
            signals.append(sig)
    return signals
