"""
L99 Governance — Capital Allocator
Computes per-asset allocation weights based on rolling Sharpe.
Rebalances every 20 closed trades. Never modifies signal logic.

Weight formula: weight_i = Sharpe_i / Σ(Sharpe_all)
Constraints:
  - Max weight per asset:  35%
  - Min weight per asset:  5%
  - Sharpe < 1.2 → cap at 10%
  - Sharpe < 1.0 → asset disabled (weight = 0)
"""
import logging
from dataclasses import dataclass, field

import config

logger = logging.getLogger("l99.governance.allocator")

_MAX_WEIGHT   = 0.35
_MIN_WEIGHT   = 0.05
_CAP_WEAK     = 0.10    # cap when Sharpe < 1.2
_DISABLE_BELOW = 1.0   # disable asset when Sharpe < this


@dataclass
class AllocationResult:
    weights:          dict[str, float]   # symbol → weight (0.0–1.0)
    disabled_assets:  list[str]
    trade_count:      int
    reason:           str


def compute_weights(
    per_asset_metrics: dict[str, dict],
    trade_count: int,
) -> AllocationResult:
    coins = config.COINS

    if trade_count < 20:
        equal = 1.0 / len(coins)
        return AllocationResult(
            weights={c: equal for c in coins},
            disabled_assets=[],
            trade_count=trade_count,
            reason=f"equal weight — insufficient trades ({trade_count}/20)"
        )

    raw_sharpes: dict[str, float] = {}
    disabled: list[str] = []

    for coin in coins:
        m = per_asset_metrics.get(coin, {})
        sharpe = m.get("sharpe", 0.0)
        count  = m.get("count", 0)

        if count < 5 or sharpe < _DISABLE_BELOW:
            disabled.append(coin)
            raw_sharpes[coin] = 0.0
        else:
            raw_sharpes[coin] = max(0.0, sharpe)

    active_sharpes = {c: s for c, s in raw_sharpes.items() if s > 0}
    if not active_sharpes:
        equal = 1.0 / len(coins)
        return AllocationResult(
            weights={c: equal for c in coins},
            disabled_assets=coins.copy(),
            trade_count=trade_count,
            reason="all assets below Sharpe floor — equal weight fallback"
        )

    total_sharpe = sum(active_sharpes.values())
    raw_weights  = {c: s / total_sharpe for c, s in active_sharpes.items()}

    # Apply constraints
    weights: dict[str, float] = {}
    for coin in coins:
        if coin in disabled:
            weights[coin] = 0.0
            continue
        sharpe = raw_sharpes[coin]
        w = raw_weights.get(coin, 0.0)
        if sharpe < 1.2:
            w = min(w, _CAP_WEAK)
        w = min(w, _MAX_WEIGHT)
        w = max(w, _MIN_WEIGHT)
        weights[coin] = w

    # Renormalize active assets to sum to 1.0
    active_total = sum(w for c, w in weights.items() if c not in disabled)
    if active_total > 0:
        weights = {
            c: (w / active_total if c not in disabled else 0.0)
            for c, w in weights.items()
        }

    logger.info("Allocation rebalanced: %s", {c: f"{w:.1%}" for c, w in weights.items()})
    return AllocationResult(
        weights=weights,
        disabled_assets=disabled,
        trade_count=trade_count,
        reason="performance-weighted allocation"
    )
