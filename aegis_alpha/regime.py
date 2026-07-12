"""
aegis_alpha.regime — 4H macro regime classifier (PLAN B Part 3).

Three states:
    EXPANSION  — BTC 4H closes > EMA20 > EMA50, EMA20 slope positive,
                 ATR(14) expanding vs prior 20-period mean.
                 → All engines free to trade.
    NORMAL     — BTC trends positive but no expansion signature.
                 → 4H runs full size; 1H allowed but throttled.
    DEAD       — BTC EMA20 < EMA50 (downtrend) OR vol contracted to bottom
                 quartile of 90-day distribution (no opportunity).
                 → 4H runs (defensive); 1H DISABLED.

This is the gate the 1H runtime checks before every entry. The 4H
runtime is unaffected — it makes its own §3.2 BTC-uptrend gate
decision independently per the doctrine.

Lower-timeframe engines NEVER override macro regime. (PLAN B Part 3.)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from aegis_alpha.scanner import fetch_candles


log = logging.getLogger("aegis_alpha.regime")


class Regime(str, Enum):
    EXPANSION = "EXPANSION"
    NORMAL    = "NORMAL"
    DEAD      = "DEAD"


@dataclass
class RegimeReading:
    regime:        Regime
    btc_close:     float
    btc_ema20:     float
    btc_ema50:     float
    btc_ema20_slope: float    # % change of ema20 over last 10 bars
    atr_now:       float
    atr_baseline:  float
    atr_ratio:     float
    reasons:       List[str]


# ── helpers ──────────────────────────────────────────────────────────
def _ema(values: List[float], n: int) -> Optional[List[float]]:
    if len(values) < n: return None
    k = 2 / (n + 1)
    out = [None] * (n - 1) + [sum(values[:n]) / n]
    for v in values[n:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _atr(rows: List[List[str]], period: int = 14) -> Optional[float]:
    if len(rows) < period + 1: return None
    highs  = [float(r[3]) for r in rows]
    lows   = [float(r[4]) for r in rows]
    closes = [float(r[2]) for r in rows]
    trs = []
    for i in range(1, len(rows)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i]  - closes[i - 1]))
        trs.append(tr)
    last = trs[-period:]
    return sum(last) / len(last) if last else None


# ── classifier ───────────────────────────────────────────────────────
def classify_regime(pair: str = "BTC_USDT") -> Optional[RegimeReading]:
    """Pull BTC 4H candles and decide the macro regime.
    Returns None on data fetch failure."""
    try:
        rows = fetch_candles(pair, "4h", 100)
    except Exception as e:
        log.warning("regime fetch failed: %s", e)
        return None
    if len(rows) < 60:
        return None
    closes = [float(r[2]) for r in rows]
    ema20  = _ema(closes, 20)
    ema50  = _ema(closes, 50)
    if ema20 is None or ema50 is None:
        return None
    last_close   = closes[-1]
    last_ema20   = ema20[-1]
    last_ema50   = ema50[-1]
    # Slope: pct change of ema20 over last 10 bars
    if ema20[-11] is None or ema20[-11] == 0:
        ema20_slope = 0.0
    else:
        ema20_slope = (last_ema20 - ema20[-11]) / abs(ema20[-11])

    # ATR expansion vs 20-period prior mean
    atr_now = _atr(rows, 14) or 0.0
    prior_atrs: List[float] = []
    for i in range(20, 0, -1):
        slc = rows[:-i] if i > 0 else rows
        a   = _atr(slc, 14)
        if a is not None and a > 0:
            prior_atrs.append(a)
    atr_baseline = (sum(prior_atrs) / len(prior_atrs)) if prior_atrs else atr_now
    atr_ratio = (atr_now / atr_baseline) if atr_baseline > 0 else 1.0

    reasons: List[str] = []
    # DEAD checks first (downtrend OR contracted vol)
    if last_ema20 < last_ema50:
        reasons.append("EMA20<EMA50 (BTC downtrend)")
        return RegimeReading(Regime.DEAD, last_close, last_ema20, last_ema50,
                              ema20_slope, atr_now, atr_baseline, atr_ratio,
                              reasons)
    if atr_ratio < 0.70:
        reasons.append(f"ATR ratio {atr_ratio:.2f} < 0.70 (vol contracted)")
        return RegimeReading(Regime.DEAD, last_close, last_ema20, last_ema50,
                              ema20_slope, atr_now, atr_baseline, atr_ratio,
                              reasons)

    # EXPANSION = all three conditions
    expansion_ok = (last_close > last_ema20 > last_ema50
                    and ema20_slope > 0.005          # 0.5% positive over 10 bars
                    and atr_ratio > 1.20)
    if expansion_ok:
        reasons.append("close>EMA20>EMA50 + slope+ + ATR×1.2")
        return RegimeReading(Regime.EXPANSION, last_close, last_ema20, last_ema50,
                              ema20_slope, atr_now, atr_baseline, atr_ratio,
                              reasons)

    # Otherwise NORMAL
    reasons.append("uptrend present but no expansion signature")
    return RegimeReading(Regime.NORMAL, last_close, last_ema20, last_ema50,
                          ema20_slope, atr_now, atr_baseline, atr_ratio,
                          reasons)


def regime_allows_1h(reading: Optional[RegimeReading]) -> bool:
    """1H engine is allowed in EXPANSION or NORMAL; disabled in DEAD or
    if reading is None (fail-closed)."""
    if reading is None:
        return False
    return reading.regime in (Regime.EXPANSION, Regime.NORMAL)
