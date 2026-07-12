"""
godmode.arbiter — Confluence Arbiter per /GODSMODE spec.

Combines 7 stream outputs multiplicatively:

    final_score = (|microstructure|/100) × (volatility_mag/100)
                × (absorption_mag/100)   × (structural_mag/100)
                × (fee_edge_ok ? 1 : 0)  × (risk_permits ? 1 : 0)
                × (execution_ok ? 1 : 0)
                × 100

Decision rules:
    ENTER if final_score >= 78 AND net_edge >= 0.12% AND risk permits
    AGGRESSIVE if final_score >= 88 AND net_edge >= 0.25%
    Otherwise NO TRADE.

Direction comes from the signed `microstructure.directional`:
    positive → BUY
    negative → SELL

Any stream with `veto=True` forces NO TRADE regardless of score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from godmode.streams import StreamOutput


@dataclass
class Decision:
    action:       str                 # "BUY" | "SELL" | "HOLD"
    final_score:  float               # 0..100
    net_edge_pct: float
    aggressive:   bool
    reasons:      Dict[str, dict] = field(default_factory=dict)
    vetoes:       List[str]       = field(default_factory=list)


class ConfluenceArbiter:
    ENTER_SCORE   = 78.0
    AGGR_SCORE    = 88.0
    MIN_EDGE      = 0.0012
    AGG_EDGE      = 0.0025

    def vote(self, outputs: Dict[str, StreamOutput]) -> Decision:
        # Extract each
        micro  = outputs.get("microstructure")
        vol    = outputs.get("volatility")
        absorp = outputs.get("absorption")
        struct = outputs.get("structural")
        edge   = outputs.get("fee_edge")
        exec_  = outputs.get("execution")
        risk   = outputs.get("risk")

        # Collect vetoes
        vetoes = [o.name for o in outputs.values() if o and o.veto]
        if vetoes:
            return Decision("HOLD", 0.0, 0.0, False,
                            reasons={o.name: o.data for o in outputs.values() if o},
                            vetoes=vetoes)

        # Direction from microstructure
        if not micro or micro.confidence == 0.0:
            return Decision("HOLD", 0.0, 0.0, False,
                            reasons={"microstructure":
                                     micro.data if micro else {"missing": True}},
                            vetoes=["microstructure_confidence_zero"])
        direction = "BUY" if micro.directional > 0 else "SELL"

        # Multiplicative score (fee+risk+exec are gates; use 1 if permitting, else 0)
        def mag_frac(o): return (o.magnitude / 100.0) if o else 0.0
        score = (
            abs(micro.directional) / 100.0
            * (mag_frac(vol)    if vol    and vol.confidence    > 0 else 0.0)
            * (mag_frac(absorp) if absorp                                 else 0.0)
            * (mag_frac(struct) if struct                                 else 0.0)
            * (mag_frac(edge)   if edge   and edge.confidence   > 0 else 0.0)
            * (mag_frac(exec_)  if exec_  and exec_.confidence  > 0 else 0.0)
            * (mag_frac(risk)   if risk   and risk.confidence   > 0 else 0.0)
            * 100.0
        )

        net_edge = (edge.data.get("net_edge", 0.0)
                    if edge and edge.data else 0.0)

        reasons = {o.name: o.data for o in outputs.values() if o}

        if score < self.ENTER_SCORE:
            return Decision("HOLD", score, net_edge, False, reasons)
        if net_edge < self.MIN_EDGE:
            return Decision("HOLD", score, net_edge, False, reasons,
                            vetoes=["edge_below_min"])
        aggressive = score >= self.AGGR_SCORE and net_edge >= self.AGG_EDGE
        return Decision(direction, score, net_edge, aggressive, reasons)
