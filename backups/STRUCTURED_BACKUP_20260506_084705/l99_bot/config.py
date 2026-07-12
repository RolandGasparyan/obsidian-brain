"""
L99 Bot — Configuration
All runtime parameters in one place. Edit here only.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Exchange (Gate.io native) ──────────────────────────────────
EXCHANGE_ID      = "gateio"
API_KEY          = os.getenv("GATE_API_KEY", "")
API_SECRET       = os.getenv("GATE_API_SECRET", "")
GATE_BASE_URL    = "https://api.gateio.ws/api/v4"
TESTNET          = os.getenv("TESTNET",       "true").lower()  == "true"
LIVE_TRADING     = os.getenv("LIVE_TRADING",  "false").lower() == "true"

# ── Universe ───────────────────────────────────────────────────
COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
         "AVAX/USDT", "LINK/USDT", "ADA/USDT", "XRP/USDT"]
TIMEFRAME        = "4h"

# ── Signal parameters (SACRED — do not touch) ─────────────────
EMA_FAST         = 21
EMA_MID          = 50
EMA_SLOW         = 200
ADX_PERIOD       = 14
ADX_THRESHOLD    = 30
ATR_PERIOD       = 14
BREAKOUT_WINDOW  = 20
VOLUME_MULT      = 2.0

# ── Regime filter ─────────────────────────────────────────────
# Option B: no global BTC gate — per-coin EMA200 IS the regime filter.
# Entry requires close > EMA21 > EMA50 > EMA200 on every coin independently.

# ── Risk (env-overridable for stage transitions) ──────────────
RISK_PER_TRADE   = float(os.getenv("RISK_PER_TRADE",  "0.01"))   # 1% default
MAX_CONCURRENT   = int(os.getenv("MAX_CONCURRENT",    "3"))
ATR_STOP_MULT    = 1.5
RR_RATIO         = 2.5          # 2.5R TP

# ── Costs ─────────────────────────────────────────────────────
FEE_RATE         = 0.0014
SLIPPAGE_EST     = 0.001        # conservative next-open slip

# ── Kill switch thresholds ────────────────────────────────────
KILL_CONSEC_LOSS = 5
KILL_DD_ABS      = float(os.getenv("KILL_DD_THRESHOLD", "0.21"))  # 21% default
KILL_SHARPE_MIN  = 0.8
KILL_SLIP_MAX    = 0.0025

# ── Database ──────────────────────────────────────────────────
DB_NAME          = os.getenv("DB_NAME",     "l99")
DB_USER          = os.getenv("DB_USER",     "l99_user")
DB_PASS          = os.getenv("DB_PASS",     "")
DB_HOST          = os.getenv("DB_HOST",     "localhost")
DB_PORT          = int(os.getenv("DB_PORT", "5432"))

# ── Governance (disabled until v1.1-governance-enabled tag) ──
GOVERNANCE_ENABLED    = os.getenv("GOVERNANCE_ENABLED", "false").lower() == "true"
GOVERNANCE_MIN_TRADES = 50

# ── Redundancy (disabled until v1.2-redundancy tag) ──────────
REDUNDANCY_ENABLED    = os.getenv("REDUNDANCY_ENABLED", "false").lower() == "true"
CAPITAL_PRIMARY_PCT   = float(os.getenv("CAPITAL_PRIMARY_PCT",   "1.0"))

# ── Loop timing ───────────────────────────────────────────────
POLL_SECONDS     = 30
CANDLE_CLOSE_LAG = 5
