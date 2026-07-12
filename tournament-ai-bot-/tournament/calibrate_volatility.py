"""
calibrate_volatility.py
-----------------------
Offline calibration harness for VolatilityExpansionDetector.

Usage:
    python -m tournament.calibrate_volatility path/to/btc_1m.csv
    python -m tournament.calibrate_volatility path/to/btc_1m.csv --phase EARLY
    python -m tournament.calibrate_volatility path/to/btc_1m.csv --pair BTC_USDT --lookahead 10 --r-multiple 1.2

Input format: CSV with columns (case-insensitive, extra columns ignored):
    timestamp, open, high, low, close, volume

Or a pandas DataFrame passed programmatically via run_calibration(df, ...).

What it computes per bar:
    - ATR ratio (current_atr / median_atr_over_lookback)
    - BB width percentile (rank of current BB width vs rolling window)
    - Realized volatility slope (linear regression slope of rvol over N bars)

What it outputs:
    - Distribution of classifications (COMPRESSION / EXPANDING / EXPANDED / NEUTRAL)
      per phase (EARLY / MID / ENDGAME)
    - Hit rate analysis: P(future return > 1.2R in next 10 bars | classification)
    - Lift vs baseline: hit_rate(EXPANDING) / hit_rate(baseline)
    - Summary table printed to stdout, optional CSV dump

Design:
    Runs the actual VolatilityExpansionDetector.read() call, so what you see
    is what production will see. No simulation of the logic — same code path.
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from .volatility_expansion_detector import (
    PhaseHint, VolatilityExpansionDetector, VolState,
)


# ---- data loading ----

def load_csv(path: str) -> Dict[str, np.ndarray]:
    """Load OHLCV from CSV. Column order: timestamp,open,high,low,close,volume.
    Flexible: accepts any of these header spellings (case-insensitive).
    Returns dict of numpy arrays."""
    with open(path) as f:
        reader = csv.reader(f)
        header = next(reader)
        cols = {name.lower().strip(): i for i, name in enumerate(header)}

        # resolve column indices with common aliases
        def resolve(*names: str) -> int:
            for n in names:
                if n in cols:
                    return cols[n]
            raise ValueError(f"CSV missing any of: {names}. Found: {list(cols)}")

        ts_idx = resolve("timestamp", "time", "ts", "date", "datetime")
        o_idx = resolve("open")
        h_idx = resolve("high")
        l_idx = resolve("low")
        c_idx = resolve("close")
        v_idx = resolve("volume", "vol")

        ts, o, h, l, c, v = [], [], [], [], [], []
        for row in reader:
            if not row or len(row) <= max(ts_idx, o_idx, h_idx, l_idx, c_idx, v_idx):
                continue
            try:
                ts.append(float(row[ts_idx]) if row[ts_idx].replace(".", "").isdigit()
                          else row[ts_idx])
                o.append(float(row[o_idx]))
                h.append(float(row[h_idx]))
                l.append(float(row[l_idx]))
                c.append(float(row[c_idx]))
                v.append(float(row[v_idx]))
            except (ValueError, IndexError):
                continue

    return {
        "timestamp": np.asarray(ts),
        "open": np.asarray(o, dtype=np.float64),
        "high": np.asarray(h, dtype=np.float64),
        "low": np.asarray(l, dtype=np.float64),
        "close": np.asarray(c, dtype=np.float64),
        "volume": np.asarray(v, dtype=np.float64),
    }


def load_dataframe(df) -> Dict[str, np.ndarray]:
    """Accept a pandas DataFrame with OHLCV columns."""
    cols = {c.lower(): c for c in df.columns}
    def col(*names):
        for n in names:
            if n in cols:
                return df[cols[n]].to_numpy(dtype=np.float64)
        raise ValueError(f"DataFrame missing any of: {names}")
    return {
        "timestamp": df.index.to_numpy() if df.index.name else np.arange(len(df)),
        "open": col("open"),
        "high": col("high"),
        "low": col("low"),
        "close": col("close"),
        "volume": col("volume", "vol"),
    }


# ---- core calibration ----

@dataclass
class BarReading:
    idx: int
    state: VolState
    score: float
    atr_ratio: float
    bb_percentile: float
    rvol_slope: float
    future_return: float          # 10-bar future log return
    future_r_multiples: float     # future return / (ATR/price) = R multiples
    hit: bool                     # True if future_r_multiples >= r_threshold


@dataclass
class PhaseReport:
    phase: str
    total_bars: int
    classification_counts: Dict[str, int]
    hit_rates: Dict[str, float]       # P(hit | state)
    lift_vs_baseline: Dict[str, float]
    expected_ev: Dict[str, float]     # mean R-multiples conditional on state
    baseline_hit_rate: float


def compute_future_r_multiples(
    close: np.ndarray, atr: np.ndarray, lookahead: int,
) -> np.ndarray:
    """For each bar t, compute (close[t+lookahead] / close[t] - 1) / (atr[t]/close[t])
    which is the forward return expressed in ATR units (R multiples)."""
    n = len(close)
    out = np.full(n, np.nan)
    for t in range(n - lookahead):
        if close[t] <= 0 or np.isnan(atr[t]) or atr[t] <= 0:
            continue
        ret = close[t + lookahead] / close[t] - 1.0
        r_unit = atr[t] / close[t]
        out[t] = ret / r_unit
    return out


def _compute_atr_series(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                       window: int = 14) -> np.ndarray:
    prev_close = np.empty_like(close)
    prev_close[0] = close[0]
    prev_close[1:] = close[:-1]
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    out = np.full(len(close), np.nan)
    if len(close) < window:
        return out
    cumsum = np.cumsum(np.insert(tr, 0, 0))
    out[window - 1:] = (cumsum[window:] - cumsum[:-window]) / window
    return out


def run_calibration(
    ohlcv: Dict[str, np.ndarray],
    pair: str = "BACKTEST",
    phase: PhaseHint = PhaseHint.EARLY,
    lookahead: int = 10,
    r_multiple: float = 1.2,
    warmup_bars: int = 200,
    step: int = 1,
    verbose: bool = False,
) -> PhaseReport:
    """Run the detector across every bar, collect classifications and outcomes."""
    high = ohlcv["high"]
    low = ohlcv["low"]
    close = ohlcv["close"]
    volume = ohlcv["volume"]
    n = len(close)

    if n < warmup_bars + lookahead + 50:
        raise ValueError(f"need at least {warmup_bars + lookahead + 50} bars, got {n}")

    # Precompute ATR series (used for R-multiple normalization)
    atr = _compute_atr_series(high, low, close, window=14)

    # Precompute future R multiples
    future_r = compute_future_r_multiples(close, atr, lookahead)

    # Walk forward through bars, calling the real detector each time
    # Fresh detector per pair so per-pair history builds from scratch (realistic)
    det = VolatilityExpansionDetector()

    readings: List[BarReading] = []
    for t in range(warmup_bars, n - lookahead, step):
        r = det.read(
            pair=pair,
            high=high[: t + 1],
            low=low[: t + 1],
            close=close[: t + 1],
            volume=volume[: t + 1],
            phase=phase,
        )
        fr = future_r[t]
        if np.isnan(fr):
            continue
        readings.append(BarReading(
            idx=t,
            state=r.state,
            score=r.score,
            atr_ratio=r.atr_ratio,
            bb_percentile=r.bb_width_percentile,
            rvol_slope=r.realized_vol_slope,
            future_return=close[t + lookahead] / close[t] - 1.0,
            future_r_multiples=float(fr),
            hit=float(fr) >= r_multiple,
        ))
        if verbose and len(readings) % 1000 == 0:
            print(f"  processed {len(readings)} bars...", file=sys.stderr)

    return _summarize(readings, phase.value, r_multiple, lookahead)


def _summarize(
    readings: List[BarReading], phase: str, r_threshold: float, lookahead: int,
) -> PhaseReport:
    if not readings:
        raise ValueError("no valid readings generated")

    total = len(readings)
    counts: Dict[str, int] = {s.value: 0 for s in VolState}
    hits_by_state: Dict[str, int] = {s.value: 0 for s in VolState}
    r_sum_by_state: Dict[str, float] = {s.value: 0.0 for s in VolState}

    for r in readings:
        counts[r.state.value] += 1
        if r.hit:
            hits_by_state[r.state.value] += 1
        r_sum_by_state[r.state.value] += r.future_r_multiples

    # baseline: unconditional hit rate
    total_hits = sum(hits_by_state.values())
    baseline_hit = total_hits / total

    hit_rates = {}
    lift = {}
    expected_ev = {}
    for state in VolState:
        k = state.value
        n_state = counts[k]
        if n_state > 0:
            hit_rates[k] = hits_by_state[k] / n_state
            lift[k] = hit_rates[k] / baseline_hit if baseline_hit > 0 else 0.0
            expected_ev[k] = r_sum_by_state[k] / n_state
        else:
            hit_rates[k] = 0.0
            lift[k] = 0.0
            expected_ev[k] = 0.0

    return PhaseReport(
        phase=phase,
        total_bars=total,
        classification_counts=counts,
        hit_rates=hit_rates,
        lift_vs_baseline=lift,
        expected_ev=expected_ev,
        baseline_hit_rate=baseline_hit,
    )


# ---- reporting ----

def print_report(report: PhaseReport, r_threshold: float, lookahead: int) -> None:
    total = report.total_bars

    print(f"\n=== VOLATILITY CALIBRATION REPORT ===")
    print(f"phase: {report.phase}")
    print(f"bars analyzed: {total:,}")
    print(f"lookahead: {lookahead} bars")
    print(f"R threshold: {r_threshold}R")
    print(f"baseline hit rate: {report.baseline_hit_rate:.2%}")
    print()

    # Header
    hdr = f"{'state':<12} {'bars':>8} {'%':>8} {'hit_rate':>12} {'lift':>8} {'mean_R':>10}"
    print(hdr)
    print("-" * len(hdr))

    # Display order: EXPANDING first (most actionable), then others
    for state in [VolState.EXPANDING, VolState.COMPRESSED, VolState.EXPANDED, VolState.NEUTRAL]:
        k = state.value
        count = report.classification_counts[k]
        pct = count / total if total > 0 else 0.0
        hit = report.hit_rates[k]
        lift = report.lift_vs_baseline[k]
        ev = report.expected_ev[k]
        print(f"{k:<12} {count:>8,} {pct:>7.2%} {hit:>11.2%} "
              f"{lift:>7.2f}x {ev:>+9.3f}R")

    print()
    print("interpretation:")
    expanding_lift = report.lift_vs_baseline[VolState.EXPANDING.value]
    expanding_count = report.classification_counts[VolState.EXPANDING.value]
    expanding_ev = report.expected_ev[VolState.EXPANDING.value]

    if expanding_count == 0:
        print("  ! EXPANDING never fired - thresholds too strict for this data")
    elif expanding_lift >= 1.5:
        print(f"  EXPANDING predictive edge confirmed: {expanding_lift:.2f}x baseline")
        print(f"  EV per EXPANDING signal: {expanding_ev:+.3f}R over {lookahead} bars")
    elif expanding_lift >= 1.1:
        print(f"  EXPANDING has mild edge ({expanding_lift:.2f}x baseline)")
        print(f"  Consider tightening thresholds or testing other phases")
    else:
        print(f"  ! EXPANDING has NO detectable edge ({expanding_lift:.2f}x baseline)")
        print(f"  Thresholds need recalibration OR this pair/timeframe lacks")
        print(f"  exploitable expansion patterns at {r_threshold}R / {lookahead} bars")

    # warn on low sample
    if expanding_count < 30:
        print(f"  ! very low EXPANDING sample ({expanding_count}), results unreliable")


def write_csv(report: PhaseReport, output_path: str) -> None:
    with open(output_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["phase", "state", "bars", "pct", "hit_rate", "lift_vs_baseline", "mean_R"])
        total = report.total_bars
        for state in VolState:
            k = state.value
            count = report.classification_counts[k]
            w.writerow([
                report.phase, k, count, count / total if total else 0,
                report.hit_rates[k], report.lift_vs_baseline[k],
                report.expected_ev[k],
            ])
    print(f"  wrote CSV: {output_path}")


# ---- CLI ----

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Offline volatility calibration for Trading Guru")
    p.add_argument("input_csv", help="Path to 1m OHLCV CSV")
    p.add_argument("--pair", default="BACKTEST", help="Pair identifier (for per-pair history)")
    p.add_argument("--phase", choices=["EARLY", "MID", "ENDGAME", "ALL"], default="ALL",
                   help="Phase hint to test (default: ALL three)")
    p.add_argument("--lookahead", type=int, default=10, help="Future bars to check")
    p.add_argument("--r-multiple", type=float, default=1.2, help="Hit threshold in R")
    p.add_argument("--warmup", type=int, default=200, help="Warmup bars to skip")
    p.add_argument("--step", type=int, default=1, help="Bar step (>1 for speed)")
    p.add_argument("--output-csv", default=None, help="Dump summary to CSV")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)

    print(f"loading {args.input_csv}...", file=sys.stderr)
    ohlcv = load_csv(args.input_csv)
    n = len(ohlcv["close"])
    print(f"  {n:,} bars loaded", file=sys.stderr)

    phases = (
        [PhaseHint.EARLY, PhaseHint.MID, PhaseHint.ENDGAME]
        if args.phase == "ALL"
        else [PhaseHint[args.phase]]
    )

    all_reports = []
    for ph in phases:
        print(f"\nrunning {ph.value}...", file=sys.stderr)
        report = run_calibration(
            ohlcv=ohlcv,
            pair=args.pair,
            phase=ph,
            lookahead=args.lookahead,
            r_multiple=args.r_multiple,
            warmup_bars=args.warmup,
            step=args.step,
            verbose=args.verbose,
        )
        print_report(report, args.r_multiple, args.lookahead)
        all_reports.append(report)

    if args.output_csv:
        # concatenate reports into single CSV
        with open(args.output_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["phase", "state", "bars", "pct", "hit_rate", "lift_vs_baseline", "mean_R"])
            for rep in all_reports:
                total = rep.total_bars
                for state in VolState:
                    k = state.value
                    count = rep.classification_counts[k]
                    w.writerow([
                        rep.phase, k, count,
                        round(count / total if total else 0, 6),
                        round(rep.hit_rates[k], 6),
                        round(rep.lift_vs_baseline[k], 6),
                        round(rep.expected_ev[k], 6),
                    ])
        print(f"\nwrote {args.output_csv}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
