"""
l99.btc_vol — BTC 14-day realized volatility percentile feed.

Used by champion.PositionSizer's vol scaler (§4.1):
    high vol (>80th pctile of 90-day rolling) → ×0.7 size
    low vol  (<20th pctile)                   → ×0.8 size
    normal                                     → full size

Design:
    Pulls daily BTC closes from Gate.io (90-day window).
    Computes 14-day realized vol of log-returns (annualized).
    Compares the latest value to the percentile inside the 90-day series.
    Cached on disk for 6 hours to avoid hammering the public API.

API:
    from l99.btc_vol import current_pctile

    pct = current_pctile()         # 0.0..1.0, or None if data unavailable
    if pct is not None:
        sizer.compute_size(..., vol_percentile=pct)
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from pathlib import Path
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None

from l99.config import CONFIG, DATA_ROOT


log   = logging.getLogger("l99.btc_vol")
CACHE = DATA_ROOT / "btc_vol_pctile.json"


def _fetch_btc_closes(days: int = 90) -> List[float]:
    """Fetch the last `days` daily closes for BTC_USDT from Gate.io spot.
    Returns list ordered oldest → newest. Empty list on failure."""
    if requests is None:
        return []
    try:
        r = requests.get(
            "https://api.gateio.ws/api/v4/spot/candlesticks",
            params={"currency_pair": "BTC_USDT",
                     "interval": "1d", "limit": str(days)},
            timeout=10)
        r.raise_for_status()
        rows = r.json()
        # Gate row: [ts, vol_quote, close, high, low, open, vol_base]
        closes = [float(x[2]) for x in rows]
        return closes
    except Exception as e:
        log.warning("BTC closes fetch failed: %s", e)
        return []


def _annualized_realized_vol(log_rets: List[float]) -> float:
    """sqrt(var × 365) × 100 → annualized vol as fractional decimal."""
    if len(log_rets) < 2:
        return 0.0
    mu = sum(log_rets) / len(log_rets)
    var = sum((r - mu) ** 2 for r in log_rets) / max(1, len(log_rets) - 1)
    return math.sqrt(var * 365)


def _percentile_of(value: float, sample: List[float]) -> float:
    if not sample: return 0.5
    n_below = sum(1 for x in sample if x <= value)
    return n_below / len(sample)


def current_pctile(force_refresh: bool = False) -> Optional[float]:
    """0.0..1.0 percentile of the latest 14d realized vol vs the 90-day
    rolling distribution. None when data unavailable.

    Cached for CONFIG.btc_vol_refresh_s seconds on disk."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if not force_refresh and CACHE.exists():
        try:
            blob = json.loads(CACHE.read_text())
            age  = time.time() - blob.get("ts", 0)
            if age < CONFIG.btc_vol_refresh_s:
                return blob.get("pctile")
        except Exception:
            pass

    closes = _fetch_btc_closes(90)
    if len(closes) < 30:
        return None

    log_rets = [math.log(closes[i] / closes[i - 1])
                 for i in range(1, len(closes))]
    # Rolling 14d vol — slide the window through the series
    window = 14
    vols = []
    for i in range(window, len(log_rets) + 1):
        vols.append(_annualized_realized_vol(log_rets[i - window:i]))
    if not vols:
        return None
    current = vols[-1]
    pct = _percentile_of(current, vols)
    blob = {"ts": time.time(), "pctile": pct,
            "current_vol_ann": current, "n_samples": len(vols)}
    try:
        CACHE.write_text(json.dumps(blob))
    except Exception:
        pass
    return pct


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s")
    p = current_pctile(force_refresh=True)
    if p is None:
        print("BTC vol percentile unavailable")
    else:
        print(f"BTC 14d realized vol percentile: {p:.2%}")
