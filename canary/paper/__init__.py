"""canary.paper — OFFLINE replay lab for the MA50W10 strategy.

NOT a live trading path. NOT a paper-to-live bridge. Pure deterministic
playback of hand-crafted or recorded OHLCV frames against the locked
`canary_strategy.should_enter` / `should_exit` primitives. Used by tests
to verify strategy invariants without touching the exchange.
"""
