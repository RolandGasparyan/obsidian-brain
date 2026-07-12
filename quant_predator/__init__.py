"""
quant_predator — multi-timeframe momentum engine (engine 3 of L99).

CHAMPION_MODE.md §2.2:
    What it does: Multi-timeframe momentum domination scanner
    Signal type:  Weekly/daily trend + 4H entry trigger
    Trades:       BTC, ETH, top 20 alts in trending regimes only
    Hold time:    2–14 days (position trades)
    Sizing:       1.5–2.0% risk per trade (via champion sizer)
    Fee target:   ≥ 1.0% net edge (justified by hold duration)

Status: SKELETON. Public scanner + executor stubs that import champion
sizer correctly. Real signal logic ships in a follow-up commit when we
have ≥ 60 days of paper-shadow evidence from godmode + aegis_alpha.

Public API (placeholder):
    from quant_predator.scanner  import scan_predator_universe
    from quant_predator.executor import PredatorExecutor
"""

__version__ = "0.0.1-skeleton"
