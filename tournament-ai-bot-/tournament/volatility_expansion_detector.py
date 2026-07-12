"""
volatility_expansion_detector.py
--------------------------------
v2: Phase-aware thresholds + per-pair rolling BB-width percentile.

Per-pair history: each pair gets its own ring buffer of BB widths. Percentile
is computed against that pair's distribution, not a global one. BTC's 0.8%
realized vol is not SOL's 4% realized vol.

Phase-aware: EARLY loosens everything (capital is replaceable), ENDGAME
tightens (capital is not).

Percentile lookup is O(log W) via sorted insert on a ring buffer. W=200
means ~8 comparisons per call.
"""
from __future__ import annotations

import bisect
from collections import deque
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Deque, Dict

import numpy as np


class VolState(str, Enum):
    EXPANDING = "EXPANDING"
    EXPANDED = "EXPANDED"
    COMPRESSED = "COMPRESSED"
    NEUTRAL = "NEUTRAL"


class PhaseHint(str, Enum):
    EARLY = "EARLY"
    MID = "MID"
    ENDGAME = "ENDGAME"


@dataclass
class VolatilityReading:
    state: VolState
    bb_width_percentile: float
    atr_ratio: float
    realized_vol_slope: float
    volume_confirmation: float
    score: float
    note: str
    pair_history_samples: int


@dataclass(frozen=True)
class _PhaseThresholds:
    compressed_pct_max: float
    expanded_atr_min: float
    expanded_pct_min: float
    expanding_atr_min: float
    expanding_pct_min: float
    expanding_vol_conf_min: float
    expanding_slope_min: float
    compressed_watch_bonus: float
    neutral_score_floor: float


_PHASE_THRESHOLDS: Dict[PhaseHint, _PhaseThresholds] = {
    # EARLY: loosened aggressively. Nascent expansion counts.
    PhaseHint.EARLY: _PhaseThresholds(
        compressed_pct_max=0.30,
        expanded_atr_min=1.9,
        expanded_pct_min=0.88,
        expanding_atr_min=1.03,
        expanding_pct_min=0.25,
        expanding_vol_conf_min=0.95,
        expanding_slope_min=-1e-7,
        compressed_watch_bonus=4.0,
        neutral_score_floor=22.0,
    ),
    PhaseHint.MID: _PhaseThresholds(
        compressed_pct_max=0.25,
        expanded_atr_min=1.6,
        expanded_pct_min=0.80,
        expanding_atr_min=1.10,
        expanding_pct_min=0.35,
        expanding_vol_conf_min=1.10,
        expanding_slope_min=0.0,
        compressed_watch_bonus=8.0,
        neutral_score_floor=30.0,
    ),
    PhaseHint.ENDGAME: _PhaseThresholds(
        compressed_pct_max=0.20,
        expanded_atr_min=1.5,
        expanded_pct_min=0.75,
        expanding_atr_min=1.20,
        expanding_pct_min=0.45,
        expanding_vol_conf_min=1.25,
        expanding_slope_min=5e-7,
        compressed_watch_bonus=15.0,
        neutral_score_floor=45.0,
    ),
}


class _PerPairHistory:
    """Ring buffer with sorted list for O(log W) percentile lookups."""
    __slots__ = ("_ring", "_sorted", "_maxlen")

    def __init__(self, maxlen: int = 200) -> None:
        self._ring: Deque[float] = deque(maxlen=maxlen)
        self._sorted: list[float] = []
        self._maxlen = maxlen

    def add(self, value: float) -> None:
        if len(self._ring) == self._maxlen:
            evicted = self._ring[0]
            idx = bisect.bisect_left(self._sorted, evicted)
            if idx < len(self._sorted) and self._sorted[idx] == evicted:
                self._sorted.pop(idx)
        self._ring.append(value)
        bisect.insort(self._sorted, value)

    def percentile_of(self, value: float) -> float:
        if not self._sorted:
            return 0.5
        idx = bisect.bisect_left(self._sorted, value)
        return idx / len(self._sorted)

    def __len__(self) -> int:
        return len(self._ring)


def _true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    prev_close = np.empty_like(close)
    prev_close[0] = close[0]
    prev_close[1:] = close[:-1]
    return np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])


def _rolling_mean_np(arr: np.ndarray, window: int) -> np.ndarray:
    if len(arr) < window:
        return np.full(len(arr), np.nan)
    cumsum = np.cumsum(np.insert(arr, 0, 0))
    out = np.full(len(arr), np.nan)
    out[window - 1:] = (cumsum[window:] - cumsum[:-window]) / window
    return out


def _rolling_std_np(arr: np.ndarray, window: int) -> np.ndarray:
    """Vectorized rolling std via cumulative sums. ~8x faster than Python loop."""
    if len(arr) < window:
        return np.full(len(arr), np.nan)
    c1 = np.cumsum(np.insert(arr, 0, 0))
    c2 = np.cumsum(np.insert(arr * arr, 0, 0))
    sums = c1[window:] - c1[:-window]
    sumsqs = c2[window:] - c2[:-window]
    means = sums / window
    var = sumsqs / window - means * means
    var = np.maximum(var, 0.0)
    out = np.full(len(arr), np.nan)
    out[window - 1:] = np.sqrt(var)
    return out


class VolatilityExpansionDetector:
    def __init__(
        self,
        bb_window: int = 20,
        atr_window: int = 14,
        history_per_pair: int = 200,
        slope_window: int = 10,
    ) -> None:
        self._bb_window = bb_window
        self._atr_window = atr_window
        self._slope_window = slope_window
        self._history_size = history_per_pair
        self._histories: Dict[str, _PerPairHistory] = {}
        self._lock = RLock()

    def _history_for(self, pair: str) -> _PerPairHistory:
        with self._lock:
            h = self._histories.get(pair)
            if h is None:
                h = _PerPairHistory(maxlen=self._history_size)
                self._histories[pair] = h
            return h

    def read(
        self,
        pair: str,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
        phase: PhaseHint = PhaseHint.MID,
    ) -> VolatilityReading:
        thr = _PHASE_THRESHOLDS[phase]
        n = min(len(high), len(low), len(close), len(volume))
        if n < self._bb_window + self._atr_window:
            return VolatilityReading(
                VolState.NEUTRAL, 0.5, 0.0, 0.0, 0.0, 0.0,
                f"insufficient_bars({n})", 0,
            )

        high = np.asarray(high[-n:], dtype=np.float64)
        low = np.asarray(low[-n:], dtype=np.float64)
        close = np.asarray(close[-n:], dtype=np.float64)
        volume = np.asarray(volume[-n:], dtype=np.float64)

        sma = _rolling_mean_np(close, self._bb_window)
        std = _rolling_std_np(close, self._bb_window)
        with np.errstate(divide="ignore", invalid="ignore"):
            bb_width = np.where(sma > 0, 2.0 * std / sma, np.nan)
        current_bb = bb_width[-1]
        if np.isnan(current_bb):
            return VolatilityReading(
                VolState.NEUTRAL, 0.5, 0.0, 0.0, 0.0, 0.0, "bb_nan", 0,
            )

        history = self._history_for(pair)
        bb_pct = history.percentile_of(float(current_bb))
        history.add(float(current_bb))
        hist_samples = len(history)

        # Cold-start fallback: use recent bars from this OHLCV as pseudo-history
        if hist_samples < 30:
            recent = bb_width[~np.isnan(bb_width)][-100:]
            if len(recent) >= 10:
                bb_pct = float((recent < current_bb).sum()) / len(recent)

        tr = _true_range(high, low, close)
        atr_series = _rolling_mean_np(tr, self._atr_window)
        current_atr = atr_series[-1]
        atr_slice = atr_series[~np.isnan(atr_series)]
        median_atr = float(np.median(atr_slice[-100:])) if len(atr_slice) >= 10 else 0.0
        atr_ratio = current_atr / median_atr if median_atr > 0 else 1.0

        rets = np.diff(np.log(close))
        rvol = _rolling_std_np(rets, self._bb_window)
        slope_slice = rvol[-self._slope_window:]
        slope_slice = slope_slice[~np.isnan(slope_slice)]
        if len(slope_slice) >= 2:
            xs = np.arange(len(slope_slice), dtype=np.float64)
            x_mean = xs.mean()
            y_mean = slope_slice.mean()
            num = ((xs - x_mean) * (slope_slice - y_mean)).sum()
            den = ((xs - x_mean) ** 2).sum()
            slope = float(num / den) if den > 0 else 0.0
        else:
            slope = 0.0

        vol_median = float(np.median(volume[-100:]))
        vol_recent = float(np.mean(volume[-self._slope_window:]))
        vol_conf = vol_recent / vol_median if vol_median > 0 else 1.0

        state = self._classify(bb_pct, atr_ratio, slope, vol_conf, thr)
        score = self._score_state(state, atr_ratio, vol_conf, slope, bb_pct, thr)

        note = f"phase={phase.value} pct={bb_pct:.2f} atr={atr_ratio:.2f} slope={slope:.2e}"
        return VolatilityReading(
            state=state,
            bb_width_percentile=round(bb_pct, 3),
            atr_ratio=round(atr_ratio, 3),
            realized_vol_slope=float(slope),
            volume_confirmation=round(vol_conf, 3),
            score=round(score, 2),
            note=note,
            pair_history_samples=hist_samples,
        )

    @staticmethod
    def _classify(
        bb_pct: float, atr_ratio: float, slope: float, vol_conf: float,
        thr: _PhaseThresholds,
    ) -> VolState:
        if atr_ratio > thr.expanded_atr_min and bb_pct > thr.expanded_pct_min:
            return VolState.EXPANDED
        if bb_pct < thr.compressed_pct_max and abs(slope) < 1e-6:
            return VolState.COMPRESSED
        if (
            slope >= thr.expanding_slope_min
            and atr_ratio >= thr.expanding_atr_min
            and vol_conf >= thr.expanding_vol_conf_min
            and bb_pct >= thr.expanding_pct_min
        ):
            return VolState.EXPANDING
        return VolState.NEUTRAL

    @staticmethod
    def _score_state(
        state: VolState, atr_ratio: float, vol_conf: float, slope: float,
        bb_pct: float, thr: _PhaseThresholds,
    ) -> float:
        if state == VolState.EXPANDING:
            s = 55.0
            s += min(20.0, 20.0 * max(0.0, (atr_ratio - thr.expanding_atr_min) / 0.5))
            s += min(15.0, 15.0 * max(0.0, vol_conf - 1.0))
            s += min(10.0, 10.0 * max(0.0, slope) * 1000.0)
            return min(100.0, s)
        if state == VolState.COMPRESSED:
            return 40.0
        if state == VolState.EXPANDED:
            return 12.0
        # NEUTRAL with positive slope/volume gets partial credit
        s = 25.0
        if slope > 0:
            s += 10.0
        if vol_conf > 1.0:
            s += 8.0
        if bb_pct > 0.5:
            s += 5.0
        return min(60.0, s)

    def compressed_watch_bonus(self, phase: PhaseHint) -> float:
        return _PHASE_THRESHOLDS[phase].compressed_watch_bonus

    def neutral_floor(self, phase: PhaseHint) -> float:
        return _PHASE_THRESHOLDS[phase].neutral_score_floor
