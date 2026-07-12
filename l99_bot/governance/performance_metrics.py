"""
L99 Governance — Performance Metrics
Computes rolling portfolio and per-asset metrics from DB trade history.
Pure read layer — no state changes.
"""
import logging
from collections import defaultdict

import numpy as np

import db

logger = logging.getLogger("l99.governance.metrics")

_WINDOW = 30   # default rolling window (trades)


def _sharpe(pnls: list[float]) -> float:
    arr = np.array(pnls)
    std = arr.std()
    if std == 0 or len(arr) < 2:
        return 0.0
    return float((arr.mean() / std) * np.sqrt(len(arr)))


def _profit_factor(pnls: list[float]) -> float:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss   = abs(sum(p for p in pnls if p < 0))
    return gross_profit / gross_loss if gross_loss > 0 else float("inf")


def _win_rate(pnls: list[float]) -> float:
    if not pnls:
        return 0.0
    return sum(1 for p in pnls if p > 0) / len(pnls)


def _consec_losses(pnls: list[float]) -> int:
    count = 0
    for p in reversed(pnls):
        if p < 0:
            count += 1
        else:
            break
    return count


def fetch_portfolio_metrics(n: int = _WINDOW) -> dict:
    trades = db.fetch_last_n_trades(n)
    if not trades:
        return {"count": 0, "sharpe": 0.0, "profit_factor": 0.0,
                "win_rate": 0.0, "consec_losses": 0}

    pnls = [float(t["pnl"]) for t in trades]
    return {
        "count":          len(pnls),
        "sharpe":         _sharpe(pnls),
        "profit_factor":  _profit_factor(pnls),
        "win_rate":       _win_rate(pnls),
        "consec_losses":  _consec_losses(pnls),
        "avg_r":          float(np.mean([float(t["R_multiple"]) for t in trades])),
    }


def fetch_per_asset_metrics(n_per_asset: int = _WINDOW) -> dict[str, dict]:
    trades = db.fetch_last_n_trades(n_per_asset * 10)   # over-fetch then group
    by_symbol: dict[str, list] = defaultdict(list)
    for t in trades:
        by_symbol[t["symbol"]].append(float(t["pnl"]))

    result: dict[str, dict] = {}
    for symbol, pnls in by_symbol.items():
        recent = pnls[:n_per_asset]
        result[symbol] = {
            "count":         len(recent),
            "sharpe":        _sharpe(recent),
            "profit_factor": _profit_factor(recent),
            "win_rate":      _win_rate(recent),
        }
    return result
