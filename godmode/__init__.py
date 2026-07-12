"""
GODMODE Futures — Gate.io USDT Perpetual microstructure bot.

Parallel track to the spot paper bots (SimpleMAStrategy / VoteEnsembleStrategy).
See GODMODE_FUTURES_ARCH.md in the repo root for the full architecture.

Modules:
    collector   — Module 1: WebSocket L2 book + trade-tape collector (this commit)
    replay      — Module 2: offline tick replay engine (next deliverable)
    agents      — Modules 3a-3d: the four signal agents
    arbiter     — Module 4: confluence arbiter
    executor    — Module 5: maker-biased post-only executor
    risk        — Module 6-7: fee-aware edge + risk throttle
"""

__version__ = "0.1.0-collector"
