"""
L99 Governance — Confidence-Based Position Scaler
Dynamic size adjustment ONLY when statistically justified.
Never emotional. Never based on single-signal strength.

Multiplier tiers:
  0.75x — rolling drawdown > 5%  (forced reduction)
  1.00x — base risk (default)
  1.25x — all confidence gates pass (cap: 1.5% absolute)

Hard cap: 1.5% risk per trade, regardless of multiplier.
Reverts to base immediately on 2 consecutive losses.
"""
import logging
from dataclasses import dataclass, field

import numpy as np

import config
import db

logger = logging.getLogger("l99.governance.scaler")

_BASE_MULTIPLIER  = 1.00
_SCALE_MULTIPLIER = 1.25
_REDUCE_MULTIPLIER = 0.75
_MAX_RISK_ABS     = 0.015   # 1.5% hard cap


@dataclass
class ScalingDecision:
    multiplier:        float
    effective_risk_pct: float
    reason:            str
    conditions_met:    list[str] = field(default_factory=list)
    conditions_failed: list[str] = field(default_factory=list)


def evaluate(
    consecutive_losses:    int,
    current_drawdown:      float,    # negative fraction, e.g. -0.04 = -4%
    governance_is_normal:  bool = True,
) -> ScalingDecision:
    """
    Computes size multiplier from DB trade history + live risk state.
    Caller provides consecutive_losses and current_drawdown from RiskMonitor.
    """
    # ── Forced reduction: rolling DD > 5% ────────────────────────
    if abs(current_drawdown) > 0.05:
        return _decision(
            _REDUCE_MULTIPLIER, [], [],
            f"forced reduction — rolling DD {current_drawdown:.2%} > 5%"
        )

    # ── Immediate revert on 2 consecutive losses ──────────────────
    if consecutive_losses >= 2:
        return _decision(
            _BASE_MULTIPLIER, [], [],
            f"base risk — {consecutive_losses} consecutive losses"
        )

    # ── Governance downgrade gate ─────────────────────────────────
    met: list[str]    = []
    failed: list[str] = []

    _gate(governance_is_normal,
          "governance NORMAL", "governance in downgrade mode", met, failed)

    # ── Statistical gates (last 20 trades) ───────────────────────
    trades = db.fetch_last_n_trades(20)
    if len(trades) < 20:
        return _decision(_BASE_MULTIPLIER, [], [],
                         f"insufficient history ({len(trades)}/20 trades)")

    pnls     = [float(t["pnl"])        for t in trades]
    slippages = [abs(float(t["slippage"])) for t in trades]

    win_rate = sum(1 for p in pnls if p > 0) / len(pnls)
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss   = abs(sum(p for p in pnls if p < 0))
    pf           = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    arr    = np.array(pnls)
    std    = arr.std()
    sharpe = float((arr.mean() / std) * np.sqrt(len(arr))) if std > 0 else 0.0

    _gate(win_rate >= 0.55, f"win_rate {win_rate:.1%}",   "win_rate < 55%",   met, failed)
    _gate(pf >= 1.5,        f"PF {pf:.2f}",               "PF < 1.5",         met, failed)
    _gate(sharpe >= 1.6,    f"Sharpe {sharpe:.3f}",        "Sharpe < 1.6",     met, failed)

    # ── 10-trade drawdown gate (< 3%) ────────────────────────────
    recent_pnls = pnls[:10]
    dd_10 = _max_drawdown(recent_pnls)
    _gate(dd_10 < 0.03, f"10-trade DD {dd_10:.2%}", "10-trade DD ≥ 3%", met, failed)

    # ── Execution quality gates ───────────────────────────────────
    avg_slip = np.mean(slippages) if slippages else 0.0
    _gate(avg_slip < 0.001, f"avg slippage {avg_slip:.4%}", "avg slippage ≥ 0.1%", met, failed)

    avg_latency = _fetch_avg_latency()
    _gate(avg_latency < 1000, f"avg latency {avg_latency:.0f}ms", "latency ≥ 1000ms", met, failed)

    # ── Decision ─────────────────────────────────────────────────
    if not failed:
        return _decision(_SCALE_MULTIPLIER, met, failed,
                         "all confidence gates passed — scaling to 1.25x")

    return _decision(_BASE_MULTIPLIER, met, failed,
                     f"base risk — {len(failed)} gate(s) failed")


def _max_drawdown(pnls: list[float]) -> float:
    if not pnls:
        return 0.0
    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdown = (peak - cumulative) / (np.abs(peak) + 1e-9)
    return float(drawdown.max())


def _fetch_avg_latency() -> float:
    try:
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT AVG(latency_ms) FROM execution_metrics "
                    "WHERE timestamp > NOW() - INTERVAL '1 hour'"
                )
                row = cur.fetchone()
        return float(row[0]) if row and row[0] else 0.0
    except Exception:
        return 0.0   # table may not exist yet — assume OK


def _decision(multiplier: float, met: list, failed: list, reason: str) -> ScalingDecision:
    effective = min(config.RISK_PER_TRADE * multiplier, _MAX_RISK_ABS)
    logger.debug("Scaler: %.2fx → risk=%.3f%%  %s", multiplier, effective * 100, reason)
    return ScalingDecision(
        multiplier=multiplier, effective_risk_pct=effective,
        reason=reason, conditions_met=met, conditions_failed=failed,
    )


def _gate(condition: bool, actual: str, failure: str,
          met: list, failed: list) -> None:
    if condition:
        met.append(f"✓ {actual}")
    else:
        failed.append(f"✗ {failure}")
