"""
canary_strategy.py — MA50W10 trend-follow for engineering canary.

STRATEGY: MA50+W10 (the only L99-validated edge in this repo)
  Backtest: +3,427% over 7.5y chained, Sharpe 2.81, MaxDD -23% (see MA_STRATEGY.md)
  Single asset, binary position, daily-timeframe with weekly filter.

ENTRY RULES (all must be true):
  1. current_btc_price > SMA(daily_closes, 50)         ← daily trend filter
  2. current_btc_price > SMA(weekly_closes, 10)        ← weekly trend filter
  3. no open position
  4. cooldown elapsed: ≥ 1800 sec since last exit
  5. trades_today < 8                                  ← hard daily cap

EXIT RULES (any one triggers):
  1. current_btc_price ≤ SMA(daily_closes, 50)         ← daily flip down
  2. current_btc_price ≤ SMA(weekly_closes, 10)        ← weekly flip down
  3. hold time ≥ 46h                                   ← exit before 48h auto-halt
  (NO fixed TP/SL — exits driven by MA flips per MA_STRATEGY.md)

SIZING:
  Fixed 30 USDT per trade. Scaled-down version of the binary 100% rule
  for the canary's $100 sub-account. Pure binary on a full account would
  be ~100% allocation — we cap at $30 (3 layers × $30 max per session).
  Does NOT scale with PnL, wins, or losses.

DEVIATIONS FROM BACKTESTED MA50W10 (noted for transparency):
  - Backtest decides at daily close (00:00 UTC). Canary polls every 30s and
    treats current_price as proxy for "close-so-far". This makes the bot
    responsive within the 48h canary window. Pure daily-close behavior
    would mean only 1-2 evaluations in 48h.
  - Backtest is binary (100% in or out). Canary uses fixed $30 size.
  - Backtest has no daily-DD cap. Canary adds a $2 hard cap for safety.
  - Backtest expects ≈10 trades/year. Canary may complete 0-2 trades in 48h.
    Zero-trade outcome is a VALID plumbing test (validates no-trade path).
"""
from typing import List, Optional, Tuple

# ── Locked constants ──────────────────────────────────────────────────────
SYMBOL              = "BTC/USDT"
DAILY_TIMEFRAME     = "1d"
WEEKLY_TIMEFRAME    = "1w"
DAILY_SMA_PERIOD    = 50
WEEKLY_SMA_PERIOD   = 10
MAX_HOLD_SECONDS    = 46 * 3600     # exit at 46h to leave buffer for 48h auto-halt
COOLDOWN_SECONDS    = 1800
MAX_TRADES_PER_DAY  = 8
TRADE_SIZE_USDT     = 30.0

# Stale OHLCV thresholds (per STALE_OHLCV_DETECTOR patch)
MAX_DAILY_CANDLE_AGE_SEC  = 26 * 3600   # 26h — accounts for daily-close lag at session start
MAX_WEEKLY_CANDLE_AGE_SEC = 8 * 86400   # 8 days — accounts for weekly-close lag


# ── SMA ────────────────────────────────────────────────────────────────────
def sma(values: List[float], period: int) -> Optional[float]:
    """Simple moving average; returns None if not enough data."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


# ── Stale OHLCV check (PATCH 2: STALE_OHLCV_DETECTOR) ─────────────────────
def is_ohlcv_stale(latest_candle_ts_ms: int, max_age_sec: int, now_ms: Optional[int] = None) -> Tuple[bool, str]:
    """
    Returns (is_stale, reason). reason is logged.
    `latest_candle_ts_ms` is candles[-1][0] from ccxt (millisecond epoch).
    """
    import time
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    age_sec = (now_ms - latest_candle_ts_ms) / 1000.0
    if age_sec > max_age_sec:
        return (True, f"stale_ohlcv age={age_sec:.0f}s > {max_age_sec}s")
    if age_sec < -60:   # future timestamp → clock drift
        return (True, f"future_ohlcv age={age_sec:.0f}s (clock drift?)")
    return (False, f"fresh age={age_sec:.0f}s")


# ── Signal API ─────────────────────────────────────────────────────────────
def should_enter(
    current_price: float,
    daily_closes: List[float],
    weekly_closes: List[float],
    daily_latest_ts_ms: int,
    weekly_latest_ts_ms: int,
    *,
    seconds_since_last_exit: int,
    trades_today: int,
    have_open_position: bool,
) -> Tuple[bool, str]:
    """
    Returns (signal, reason). reason is always logged.
    Implements MA50+W10 long-entry rule with stale-data guard.
    """
    if have_open_position:
        return (False, "veto:have_open_position")
    if trades_today >= MAX_TRADES_PER_DAY:
        return (False, f"veto:trades_today={trades_today}≥{MAX_TRADES_PER_DAY}")
    if seconds_since_last_exit < COOLDOWN_SECONDS:
        return (False, f"veto:cooldown={seconds_since_last_exit}<{COOLDOWN_SECONDS}s")

    # Stale-data guard (PATCH 2)
    daily_stale, daily_reason = is_ohlcv_stale(daily_latest_ts_ms, MAX_DAILY_CANDLE_AGE_SEC)
    if daily_stale:
        return (False, f"veto:{daily_reason}")
    weekly_stale, weekly_reason = is_ohlcv_stale(weekly_latest_ts_ms, MAX_WEEKLY_CANDLE_AGE_SEC)
    if weekly_stale:
        return (False, f"veto:{weekly_reason}")

    daily_sma50 = sma(daily_closes, DAILY_SMA_PERIOD)
    if daily_sma50 is None:
        return (False, f"veto:daily_sma50_unavailable need={DAILY_SMA_PERIOD} have={len(daily_closes)}")

    weekly_sma10 = sma(weekly_closes, WEEKLY_SMA_PERIOD)
    if weekly_sma10 is None:
        return (False, f"veto:weekly_sma10_unavailable need={WEEKLY_SMA_PERIOD} have={len(weekly_closes)}")

    if current_price <= daily_sma50:
        return (False, f"veto:daily_trend price={current_price:.2f}≤SMA50={daily_sma50:.2f}")
    if current_price <= weekly_sma10:
        return (False, f"veto:weekly_trend price={current_price:.2f}≤W_SMA10={weekly_sma10:.2f}")

    return (True, f"enter price={current_price:.2f} > SMA50={daily_sma50:.2f} AND > W_SMA10={weekly_sma10:.2f}")


def should_exit(
    current_price: float,
    daily_closes: List[float],
    weekly_closes: List[float],
    daily_latest_ts_ms: int,
    weekly_latest_ts_ms: int,
    *,
    seconds_held: int,
) -> Tuple[bool, str]:
    """
    Returns (should_exit, reason).
    MA50W10 exit triggers (no fixed TP/SL — let MA flip drive exit):
      1. daily flip: price ≤ daily SMA50
      2. weekly flip: price ≤ weekly SMA10
      3. timeout: held ≥ 46h (leaves 2h buffer before 48h auto-halt)
    """
    if seconds_held >= MAX_HOLD_SECONDS:
        return (True, f"exit:timeout held={seconds_held}s ≥ {MAX_HOLD_SECONDS}s")

    daily_stale, daily_reason = is_ohlcv_stale(daily_latest_ts_ms, MAX_DAILY_CANDLE_AGE_SEC)
    if daily_stale:
        # If we can't see fresh data on a held position, exit conservatively
        return (True, f"exit:defensive:{daily_reason}")
    weekly_stale, weekly_reason = is_ohlcv_stale(weekly_latest_ts_ms, MAX_WEEKLY_CANDLE_AGE_SEC)
    if weekly_stale:
        return (True, f"exit:defensive:{weekly_reason}")

    daily_sma50 = sma(daily_closes, DAILY_SMA_PERIOD)
    weekly_sma10 = sma(weekly_closes, WEEKLY_SMA_PERIOD)

    if daily_sma50 is None or weekly_sma10 is None:
        # MA unavailable on a held position → exit defensively
        return (True, "exit:defensive:ma_unavailable")

    if current_price <= daily_sma50:
        return (True, f"exit:daily_flip price={current_price:.2f}≤SMA50={daily_sma50:.2f}")
    if current_price <= weekly_sma10:
        return (True, f"exit:weekly_flip price={current_price:.2f}≤W_SMA10={weekly_sma10:.2f}")

    return (False, f"hold price={current_price:.2f} > SMA50={daily_sma50:.2f} AND > W_SMA10={weekly_sma10:.2f} held={seconds_held}s")


def trade_size_usdt() -> float:
    """Fixed $30. Does NOT vary with PnL/wins/losses. (No martingale, no recovery sizing.)"""
    return TRADE_SIZE_USDT
