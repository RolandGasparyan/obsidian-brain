#!/usr/bin/env python3
"""
L99 Supreme Regime Detection — Phase A v3 layer.

Implements the 4-layer regime classifier as described in the
operator's `/L99-regime` spec. Maps to the features the
microstructure_collector already produces, plus a small Gate.io REST
poll for 1m OHLC candles (Layer 1 needs ATR which the trade tape can
approximate but candles are canonical).

Design contract:

  • Pure scorer. NO trading logic. NO order placement.
  • Consumed by the collector each snapshot. Adds two new parquet
    columns: regime_score (0-100) and regime_label.
  • Layer 4 (cross-exchange Binance/OKX alignment) STUBBED with
    constant 1.0 (neutral). Adding it later is one new WS task each.

Layers:

  Layer 1  Volatility expansion
      A. atr5m_ratio   = current 5m ATR / 20-period 5m ATR baseline
      B. range_accel   = avg(last 3 1m ranges) / avg(prior 10 1m ranges)

  Layer 2  Order-flow intensity
      C. delta_strength = |delta_30s| / 1.5 σ baseline
      D. delta_accel    = 1.0 if last two delta-magnitudes are
                          both increasing, 0.0 otherwise

  Layer 3  Liquidity stability
      E. spread_stability = 1.0 - clip(|spread - session_avg| / session_avg, 0, 1)
      F. depth_density    = clip((bid10+ask10) / session_avg, 0, 1.5)

  Layer 4  Cross-exchange alignment  [STUB — constant 1.0 until WS added]

Output:

  regime_score = 100 × Layer1 × Layer2 × Layer3 × Layer4    (each ∈ [0, 1.something])
  Clipped to [0, 100].

  regime_label:
    0 - 40   DEAD
    40 - 65  NEUTRAL
    65 - 85  EXPANSION
    85 - 100 HIGH_IMPULSE

Used by:
  microstructure_collector.py   (per-snapshot scorer)
  microstructure_analyze.py     (regime-conditional IC test)
"""
from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None


# ── per-pair OHLC cache for Layer 1 ──────────────────────────────────
@dataclass
class OHLCBars:
    """Rolling cache of 1m candles fetched from Gate.io REST. Refreshed
    by the collector every 30 s. ATR-on-bars is more robust than
    tick-derived ATR for short windows."""
    bars_1m: List[Tuple[int, float, float, float, float]] = field(default_factory=list)
    # each row = (ts_s, open, high, low, close)
    last_refresh_ms: int = 0


def fetch_1m_bars(pair: str, limit: int = 50) -> List[Tuple[int, float, float, float, float]]:
    """Pull last `limit` 1-minute candlesticks from Gate.io spot REST.
    Returns list of (ts_s, open, high, low, close), oldest first.
    Returns [] on any error (caller treats as 'not enough data')."""
    if requests is None:
        return []
    try:
        r = requests.get(
            "https://api.gateio.ws/api/v4/spot/candlesticks",
            params={"currency_pair": pair, "interval": "1m", "limit": limit},
            timeout=5,
        )
        r.raise_for_status()
        rows = r.json()
        # Gate.io row: [ts, quote_vol, close, high, low, open, base_vol, finalized]
        out = []
        for x in rows:
            try:
                ts = int(x[0])
                op = float(x[5]); hi = float(x[3]); lo = float(x[4]); cl = float(x[2])
                # only finalized bars for ATR
                if len(x) >= 8:
                    f = x[7]
                    finalized = (f is True) or (isinstance(f, str) and f.lower() == "true")
                    if not finalized:
                        continue
                out.append((ts, op, hi, lo, cl))
            except (IndexError, ValueError):
                continue
        out.sort(key=lambda r: r[0])
        return out
    except Exception:
        return []


def atr_from_bars(bars: List[Tuple[int, float, float, float, float]], n: int) -> float:
    """Simple ATR over the last n bars. Returns 0.0 if insufficient."""
    if len(bars) < n + 1:
        return 0.0
    trs = []
    for i in range(len(bars) - n, len(bars)):
        if i == 0: continue
        h, l = bars[i][2], bars[i][3]
        prev_close = bars[i - 1][4]
        tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


# ── Per-pair rolling state for Layers 2-3 baselines ───────────────────
@dataclass
class RegimeState:
    """Holds rolling baselines used by L99 Layers 2-3."""
    pair: str
    # Layer 2D: last few delta-magnitudes for acceleration check
    recent_deltas: Deque[float] = field(default_factory=lambda: deque(maxlen=4))
    # Layer 2C: rolling 10-minute baseline of |delta_30s| for σ
    delta_baseline: Deque[float] = field(default_factory=lambda: deque(maxlen=600))
    # Layer 3E: rolling session spread average (use last 10 min)
    spread_baseline: Deque[float] = field(default_factory=lambda: deque(maxlen=600))
    # Layer 3F: rolling top-10 notional baseline
    depth_baseline: Deque[float] = field(default_factory=lambda: deque(maxlen=600))
    # Layer 1 cache
    ohlc: OHLCBars = field(default_factory=OHLCBars)

    def update_baselines(self, *, abs_delta: float, spread_pct: float,
                         depth_total: float):
        if not math.isnan(abs_delta):
            self.delta_baseline.append(abs_delta)
            self.recent_deltas.append(abs_delta)
        if not math.isnan(spread_pct) and spread_pct > 0:
            self.spread_baseline.append(spread_pct)
        if not math.isnan(depth_total) and depth_total > 0:
            self.depth_baseline.append(depth_total)


# ── Scorer ────────────────────────────────────────────────────────────
@dataclass
class RegimeScore:
    score:               float          # 0..100
    label:               str            # DEAD | NEUTRAL | EXPANSION | HIGH_IMPULSE
    layer1:              float          # 0..1.x volatility expansion
    layer2:              float          # 0..1.x order-flow intensity
    layer3:              float          # 0..1.x liquidity stability
    layer4:              float          # 0..1.x cross-exchange alignment (stub)
    atr5m_ratio:         float
    range_accel:         float
    delta_strength:      float
    delta_accel:         float
    spread_stability:    float
    depth_density:       float


def _label(score: float) -> str:
    if score < 40:  return "DEAD"
    if score < 65:  return "NEUTRAL"
    if score < 85:  return "EXPANSION"
    return "HIGH_IMPULSE"


def compute_regime(state: RegimeState,
                   *,
                   delta_30s: float,
                   spread_pct: float,
                   bid10_notional: float,
                   ask10_notional: float) -> RegimeScore:
    """Compute L99 score from current snapshot + accumulated baselines.

    All inputs are the same fields the collector already snapshots. ATR
    is computed from cached OHLC (refreshed by caller). Layer 4 is
    constant 1.0 until cross-exchange WS is added.
    """
    state.update_baselines(
        abs_delta   = abs(delta_30s) if not math.isnan(delta_30s) else 0.0,
        spread_pct  = spread_pct,
        depth_total = (bid10_notional or 0) + (ask10_notional or 0),
    )

    # ── Layer 1: volatility expansion ─────────────────────────────────
    bars = state.ohlc.bars_1m
    atr5m_now = atr_from_bars(bars[-5:], 5) if len(bars) >= 6 else 0.0
    atr5m_baseline = atr_from_bars(bars[-25:-5], 20) if len(bars) >= 26 else 0.0
    atr5m_ratio = (atr5m_now / atr5m_baseline) if atr5m_baseline > 0 else 1.0
    # range_accel: last 3 1m ranges vs prior 10
    if len(bars) >= 13:
        last3 = sum(b[2] - b[3] for b in bars[-3:]) / 3
        prior10 = sum(b[2] - b[3] for b in bars[-13:-3]) / 10
        range_accel = last3 / prior10 if prior10 > 0 else 1.0
    else:
        range_accel = 1.0

    layer1_a = max(0.0, min(2.0, atr5m_ratio))     # cap at 2.0
    layer1_b = max(0.0, min(2.0, range_accel))
    # Layer 1 contribution: average of A and B, then scaled
    # 1.0 = baseline normal, 1.4+ = expansion, 1.7+ = high impulse
    layer1 = (layer1_a + layer1_b) / 2

    # ── Layer 2: order-flow intensity ─────────────────────────────────
    if len(state.delta_baseline) >= 30:
        # std-dev of |delta| over rolling baseline
        mu = sum(state.delta_baseline) / len(state.delta_baseline)
        var = sum((x - mu) ** 2 for x in state.delta_baseline) / max(1, len(state.delta_baseline) - 1)
        sigma = math.sqrt(var) if var > 0 else 1.0
        cur_abs = abs(delta_30s) if not math.isnan(delta_30s) else 0.0
        # 1.5σ → strength = 1.0 (neutral); 3.0σ → strength = 2.0
        delta_strength = max(0.0, min(2.0, (cur_abs - mu) / max(1e-6, 1.5 * sigma) + 1.0))
    else:
        delta_strength = 1.0

    # delta_accel: 1.0 if last 2 deltas show monotonic increase in magnitude
    delta_accel = 0.0
    if len(state.recent_deltas) >= 3:
        rd = list(state.recent_deltas)
        if rd[-1] > rd[-2] > rd[-3]:
            delta_accel = 1.5
        elif rd[-1] > rd[-2]:
            delta_accel = 1.0
        else:
            delta_accel = 0.7

    layer2 = (delta_strength * 0.6 + delta_accel * 0.4)

    # ── Layer 3: liquidity stability ──────────────────────────────────
    if len(state.spread_baseline) >= 10:
        sess_avg_spread = sum(state.spread_baseline) / len(state.spread_baseline)
        if sess_avg_spread > 0 and not math.isnan(spread_pct):
            dev = abs(spread_pct - sess_avg_spread) / sess_avg_spread
            spread_stability = max(0.0, 1.0 - min(dev, 1.0))
        else:
            spread_stability = 1.0
    else:
        spread_stability = 1.0

    if len(state.depth_baseline) >= 10:
        sess_avg_depth = sum(state.depth_baseline) / len(state.depth_baseline)
        cur_depth = (bid10_notional or 0) + (ask10_notional or 0)
        if sess_avg_depth > 0:
            depth_density = max(0.0, min(1.5, cur_depth / sess_avg_depth))
        else:
            depth_density = 1.0
    else:
        depth_density = 1.0

    layer3 = (spread_stability * 0.5 + depth_density * 0.5)

    # ── Layer 4: cross-exchange alignment (STUB) ──────────────────────
    # Until Binance/OKX WS is added, this stays at neutral 1.0.
    # When added, will pull BTC/ETH last-trade impulse from each venue
    # and check sign-alignment with our pair's delta_30s.
    layer4 = 1.0

    # ── Composite ─────────────────────────────────────────────────────
    raw = layer1 * layer2 * layer3 * layer4
    # raw ranges roughly 0..6 in extreme expansion; 1.0 is "all neutral"
    # Scale: raw=1.0 → score 50; raw=2.0 → ~75; raw=3.0 → ~85
    score = max(0.0, min(100.0, 50.0 * raw))

    return RegimeScore(
        score=score, label=_label(score),
        layer1=layer1, layer2=layer2, layer3=layer3, layer4=layer4,
        atr5m_ratio=atr5m_ratio, range_accel=range_accel,
        delta_strength=delta_strength, delta_accel=delta_accel,
        spread_stability=spread_stability, depth_density=depth_density,
    )


# ── Async helper to refresh OHLC (called from collector) ──────────────
async def refresh_ohlc(state: RegimeState, log: logging.Logger,
                       interval_s: int = 30):
    """Periodic 1m-candle refresh. Call this as a background task per pair.
    Implementation note: we use synchronous requests inside an asyncio
    task because the call is short and infrequent (every 30 s).
    """
    import asyncio
    while True:
        try:
            bars = fetch_1m_bars(state.pair, limit=50)
            if bars:
                state.ohlc.bars_1m = bars
                state.ohlc.last_refresh_ms = int(time.time() * 1000)
        except Exception as e:
            log.warning(f"{state.pair} OHLC refresh: {e}")
        await asyncio.sleep(interval_s)
