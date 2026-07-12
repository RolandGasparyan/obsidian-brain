"""
aegis_alpha — momentum-rotation engine on Gate.io spot top 50.

Implements §3 of CHAMPION_MODE.md:
  - 4H scanner with 5-factor scoring (volume / breakout / RS / ATR / liquidity)
  - 72/100 qualifying threshold, 88/100 god-tier
  - Entry/exit logic in scanner module's siblings (planned)

Hold time: 4–72 hours. Stage 1 risk 1.0–2.0% per trade. Returns to USDT
on every exit, per the doctrine's STATE A / STATE B machine.
"""

__version__ = "0.1.0-scanner"
