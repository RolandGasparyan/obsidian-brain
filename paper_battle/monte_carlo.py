#!/usr/bin/env python3
"""
monte_carlo.py — Monte Carlo Forward Stress Overlay

Per governance/BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md (spec #20 Part II).

🛡 PAPER-SAFE. Pure forward simulation on edge parameters. No exchange writes.

Trigger schedule (set by caller):
    • round start
    • after 3 consecutive losses
    • on macro regime shift (dominant regime change)

API:
    result = forward_stress(
        win_prob=0.55,
        avg_modeled_r=2.0,
        avg_realized_r=0.95,
        slip_mean_pct=0.10,
        slip_std_pct=0.05,
        round_trip_fee_pct=0.40,
        risk_per_trade_pct=0.25,
        starting_capital=10.0,
        trades_per_path=20,
        n_paths=5000,
    )
"""

from __future__ import annotations

import math
import random
import statistics
from typing import Any


def _percentile(sorted_xs: list[float], p: float) -> float:
    if not sorted_xs:
        return 0.0
    k = (len(sorted_xs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_xs[int(k)]
    return sorted_xs[f] + (sorted_xs[c] - sorted_xs[f]) * (k - f)


def forward_stress(
    win_prob: float,
    avg_modeled_r: float,
    avg_realized_r: float,
    slip_mean_pct: float,
    slip_std_pct: float,
    round_trip_fee_pct: float,
    risk_per_trade_pct: float,
    starting_capital: float = 10.0,
    trades_per_path: int = 20,
    n_paths: int = 5000,
    ruin_floor_pct: float = 50.0,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Project forward distribution of capital paths under current edge parameters.

    Returns:
        expected_final_equity, p05_equity, p50_equity, p95_equity,
        max_dd_p95_pct, risk_of_ruin_pct, median_time_to_recovery,
        cagr_estimate_pct, kelly_optimal_fraction_pct
    """
    rng = random.Random(seed if seed is not None else 1337)
    win_prob = max(0.0, min(1.0, win_prob))

    # Effective realized-R distribution.
    # Wins are positive R, losses are -1 (full SL by definition).
    # Use observed avg_realized_r to scale the win-side R magnitude.
    if win_prob > 0 and avg_realized_r is not None:
        # avg_realized_r = win_prob * R_win + (1 - win_prob) * (-1)
        # → R_win = (avg_realized_r + (1 - win_prob)) / win_prob
        r_win_mean = (avg_realized_r + (1 - win_prob)) / win_prob if win_prob > 0 else 1.0
    else:
        r_win_mean = max(0.5, avg_realized_r or 0.5)
    r_win_mean = max(0.3, r_win_mean)  # floor at +0.3R
    r_win_std = max(0.2, r_win_mean * 0.30)

    ruin_threshold = starting_capital * (ruin_floor_pct / 100.0)

    final_equities: list[float] = []
    max_dd_pcts: list[float] = []
    ruin_count = 0
    recovery_times: list[int] = []

    for _ in range(n_paths):
        equity = starting_capital
        peak = starting_capital
        in_dd = False
        dd_start_trade = 0
        recovered_at: int | None = None

        ruined = False
        for trade_idx in range(trades_per_path):
            risk_usd = equity * (risk_per_trade_pct / 100.0)
            won = rng.random() < win_prob
            if won:
                r = rng.gauss(r_win_mean, r_win_std)
                r = max(0.1, r)
            else:
                r = -1.0
            # Apply slippage + fee as fractional R reduction.
            slip = rng.gauss(slip_mean_pct, slip_std_pct)
            slip = max(0.0, slip)
            cost_pct = slip * 2 + round_trip_fee_pct
            cost_r = cost_pct / 0.5  # SL = 0.5%, so cost_pct/SL = R-multiple of cost
            r -= cost_r
            equity += risk_usd * r

            if equity > peak:
                peak = equity
                if in_dd and recovered_at is None:
                    recovered_at = trade_idx - dd_start_trade
                in_dd = False
            else:
                if not in_dd:
                    in_dd = True
                    dd_start_trade = trade_idx

            if equity <= ruin_threshold:
                ruined = True
                break

        if ruined:
            ruin_count += 1
            final_equities.append(ruin_threshold)
        else:
            final_equities.append(equity)

        if peak > 0:
            max_dd_pcts.append(max(0.0, (peak - min(equity, peak)) / peak * 100.0))
        if recovered_at is not None:
            recovery_times.append(recovered_at)

    final_equities.sort()
    max_dd_pcts.sort()

    # Kelly-optimal fraction (Bernoulli with R-multiple):
    #   f* = (b*p - q) / b   where b = avg_R_win, p = win_prob, q = 1-p
    b = r_win_mean
    p = win_prob
    q = 1.0 - p
    kelly_pct = (b * p - q) / b * 100.0 if b > 0 else 0.0
    kelly_pct = max(0.0, kelly_pct)

    n_trades = trades_per_path
    expected_final = statistics.fmean(final_equities) if final_equities else starting_capital
    cagr_proxy = ((expected_final / starting_capital) ** (1 / max(1, n_trades / 252)) - 1.0) * 100.0 if expected_final > 0 else 0.0

    return {
        "n_paths":                  n_paths,
        "trades_per_path":          trades_per_path,
        "starting_capital":         starting_capital,
        "expected_final_equity":    round(expected_final, 4),
        "p05_equity":               round(_percentile(final_equities, 0.05), 4),
        "p50_equity":               round(_percentile(final_equities, 0.50), 4),
        "p95_equity":               round(_percentile(final_equities, 0.95), 4),
        "max_dd_p95_pct":           round(_percentile(max_dd_pcts, 0.95), 3) if max_dd_pcts else 0.0,
        "max_dd_median_pct":        round(_percentile(max_dd_pcts, 0.50), 3) if max_dd_pcts else 0.0,
        "risk_of_ruin_pct":         round(ruin_count / n_paths * 100.0, 3),
        "median_time_to_recovery":  round(_percentile(sorted(recovery_times), 0.50), 1) if recovery_times else None,
        "cagr_estimate_pct":        round(cagr_proxy, 2),
        "kelly_optimal_fraction_pct": round(kelly_pct, 3),
        "r_win_mean":               round(r_win_mean, 3),
        "win_prob":                 round(win_prob, 4),
    }


def kelly_compression_required(
    mc_result: dict[str, Any],
    constitutional_dd_pct: float = 2.0,
    max_ror_pct: float = 1.0,
) -> tuple[bool, str]:
    """
    Spec #20 Part II overlay logic:
        if projected_DD > tolerance OR ror > 1% → auto-compress
    Returns (should_compress, reason).
    """
    if mc_result.get("max_dd_p95_pct", 0) > constitutional_dd_pct:
        return True, f"p95_DD={mc_result['max_dd_p95_pct']:.2f}%>tol={constitutional_dd_pct}%"
    if mc_result.get("risk_of_ruin_pct", 0) > max_ror_pct:
        return True, f"RoR={mc_result['risk_of_ruin_pct']:.2f}%>max={max_ror_pct}%"
    return False, "within_tolerance"
