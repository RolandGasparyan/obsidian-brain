"""
GODS LEVEL ENGINE — Configuration Override
Edit this file to change settings without touching the core engine.
"""
import os

# ── SAFETY ──────────────────────────────────────────────────────────
LIVE_MODE    = False          # ← KEEP FALSE until fully tested

# ── EXCHANGE ─────────────────────────────────────────────────────────
EXCHANGE     = "gateio"       # "gateio" | "binance"

# ── PAIRS TO SCORE (engine picks the best one) ───────────────────────
# Curated shortlist — see MULTI_TOKEN_RESULTS.md for the backtest evidence.
#   ETH_USDT   $523M vol · +543% MA50+W10 ROI · 75% WR
#   SOL_USDT   $ 89M vol · +1,401% ROI · 70% WR
#   XRP_USDT   $110M vol · +541% ROI · 47% WR
#   AVAX_USDT  $  2.8M vol · +817% ROI · 62% WR
PAIRS = [
    "ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT",
]

# ── CAPITAL & RISK ───────────────────────────────────────────────────
BALANCE          = 1000.0     # Starting USDT
MAX_POS_PCT      = 0.08       # Max 8% of balance per trade
DAILY_STOP       = 0.035      # 3.5% daily loss → halt engine

# ── SIGNAL QUALITY ──────────────────────────────────────────────────
MIN_VOTES        = 3          # Agents needed to vote BUY (out of 9)

# ── PAIR SWITCHING ──────────────────────────────────────────────────
PAIR_LOSSES_MAX  = 3          # Consecutive losses before switching pair
PAIR_PNL_FLOOR   = -0.015     # -1.5% cumulative pair PnL → switch

# ── TRADE TIMING ────────────────────────────────────────────────────
MAX_HOLD_SEC     = 900        # 15 min max hold per trade

# ── FEES (Gate.io VIP0 default) ─────────────────────────────────────
MAKER_FEE        = 0.0010     # 0.10%
TAKER_FEE        = 0.0015     # 0.15%

# ── API KEYS ────────────────────────────────────────────────────────
GIO_KEY  = os.getenv("GATEIO_API_KEY", "")
GIO_SEC  = os.getenv("GATEIO_SECRET", "")
BIN_KEY  = os.getenv("BINANCE_API_KEY", "")
BIN_SEC  = os.getenv("BINANCE_SECRET", "")
