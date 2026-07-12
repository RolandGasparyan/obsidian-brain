"""
champion — shared risk / sizing / journal infrastructure for ALL engines
(godmode, aegis_alpha, quant-predator).

Implements §4 (Capital Acceleration Model) and §5 (5-Layer Risk Protocol)
from CHAMPION_MODE.md. Every signal that any engine generates must pass
through PositionSizer before any order is placed.

The doctrine is enforced HERE, not in each engine separately. Engines
suggest direction; champion decides if and how big.

Public API:
    from champion import CapitalStageTracker, PositionSizer, RiskLaws

    tracker = CapitalStageTracker(starting_equity=3000.0)
    risk    = RiskLaws()
    sizer   = PositionSizer(tracker, risk)

    # On every fill / mark-to-market:
    sizer.update_equity(current_equity)

    # On every closed trade:
    sizer.record_trade(TradeOutcome(pnl_pct=0.012, pnl_R=2.0, t_ns=...))

    # Before placing any order:
    rec = sizer.compute_size(entry=67400.0, stop=67000.0,
                             vol_percentile=0.55, god_tier=False)
    if rec.blocked:
        log("Champion blocked entry: %s", rec.block_reason)
    else:
        place_order(units=rec.position_units, sl=rec.stop_price)
"""

from champion.stage  import CapitalStageTracker, Stage
from champion.sizer  import PositionSizer, SizeRecommendation, TradeOutcome
from champion.risk   import RiskLaws, RiskState

__all__ = [
    "CapitalStageTracker", "Stage",
    "PositionSizer", "SizeRecommendation", "TradeOutcome",
    "RiskLaws", "RiskState",
]

__version__ = "0.1.0"
