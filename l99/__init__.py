"""
l99 — top-level governance + central CLI for the unified Champion-Mode
trading system.

The three engines:
    /godmode       — Gate.io USDT-margined futures, microstructure
                     (2-5 minute holds), maker-biased, post-only
    /aegis-alpha   — Gate.io spot, 4H momentum rotation
                     (4-72 hour holds), top-50 USDT pairs
    /quant-predator— BTC + top-20 alts MTF momentum
                     (2-14 day position trades)

All three route every order through champion.PositionSizer. Risk
discipline is enforced once, applied everywhere.

Public API:
    from l99 import CONFIG, EngineId

    # Read shared config
    CONFIG.starting_equity      # e.g. 3000.0
    CONFIG.allocation(stage=1)  # {"godmode": 0.40, "aegis": 0.40, ...}

    # Spawn an engine via CLI:
    #   python -m l99 status
    #   python -m l99 scan-alpha --top 50
    #   python -m l99 paper-alpha --dry
    #   python -m l99 halt-all
"""

from l99.config import CONFIG, EngineId, EnginePaths, FeeTier

__all__ = ["CONFIG", "EngineId", "EnginePaths", "FeeTier"]
__version__ = "1.0.0-L99"
