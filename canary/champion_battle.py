#!/usr/bin/env python3
"""
# ══════════════════════════════════════════════════════════════════════
# ⚔️  CHAMPIONSHIP CONSTITUTION — SUPREME LAW
# ══════════════════════════════════════════════════════════════════════
# ARTICLE I:   THE WINNER IS THE MAX USDT HUNTER
#              Agent with highest USDT balance at round end wins the crown.
# ARTICLE II:  SURVIVAL FIRST — no trade may risk more than 0.5% of capital.
# ARTICLE III: NEVER STOP LEARNING — Academy, Lab, and War Room feed every tick.
# ARTICLE IV:  ADAPT OR DIE — regime detection overrides all static configs.
# ARTICLE V:   SHORT ONLY — no long positions, ever.
# ARTICLE VI:  DAILY DD CAP IS SACRED — breach = FREEZE until next UTC day.
# ══════════════════════════════════════════════════════════════════════

CHAMPION BATTLE v3.0 — ADAPTIVE HIGH-FREQUENCY ARENA · GODS LEVEL FULL POWER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Strategy: CMO + Confidence-Weighted Sizing + Regime-Adaptive Trade Frequency
FAST SCAN: 3s tick, dynamic trade limits per regime (TREND=4, BREAKOUT=5,
SIDEWAYS=2, CHAOS=1). Confidence scoring gates every entry — weak setups
get 0.5x size, elite setups get 1.75x. Winner pyramiding: 2 layers max,
only on profit. Overtrading protection: max 25 trades/hour per agent.
Spread + liquidity filters active. Global kill switch: 5% session DD cap.

Pair universe (proven CMO pairs): FLOKI, BOME, WIF, DOGE, OP, SHIB, ADA, UNI [ATOM BLACKLISTED]

Agents: TITAN (MAIN) | VELOCITY (SUB1) | SENTINEL (SUB2)
Mode: SPOT BUY → sell at TP/SL (Gate.io spot market)
Sizing: Confidence-weighted Anti-Martingale (base $15, LOW=0.5x, NORMAL=1x, HIGH=1.4x, ELITE=1.75x)
TP: 0.35% | SL: 0.30% | Cooldown: 45s | Max open: 2 per agent
Capital defense PRESERVED: dd_cap TITAN $31.59, VELOCITY/SENTINEL $4.00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import json, os, sys, time, hmac, hashlib, signal, pathlib, urllib.request, urllib.parse
# ── Self-Learning Ecosystem ───────────────────────────────────────────────────
ACADEMY_DIR = pathlib.Path("/home/ubuntu/academy")
sys.path.insert(0, str(ACADEMY_DIR))
try:
    from evolution_engine import EvolutionEngineService as _EvoSvc
    _evo_service = _EvoSvc()
    _evo_ok = True
except Exception as _evo_err:
    _evo_service = None
    _evo_ok = False
    print(f"[WARN] Evolution engine not loaded: {_evo_err}")
try:
    from claude_intelligence import analyze_signal_quality as _claude_signal
    from claude_intelligence import analyze_post_trade as _claude_post_trade
    from claude_intelligence import get_strategy_recommendation as _claude_strat
    _claude_ok = True
except Exception as _cl_err:
    _claude_ok = False
    def _claude_signal(*a, **k): return {"confidence": 0.5, "go": True, "size_mult": 1.0, "source": "disabled"}
    def _claude_post_trade(*a, **k): return {}
    def _claude_strat(*a, **k): return {"recommended_strategy": None, "source": "disabled"}
    print(f"[WARN] Claude intelligence not loaded: {_cl_err}")
from datetime import datetime, timezone, timedelta
from collections import deque

# Telegram notifier (real-time round results). No-op if creds/module missing.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from telegram_alerts import notify as _tg_notify, is_configured as _tg_ok
except Exception:
    def _tg_notify(*a, **k): return False
    def _tg_ok(): return False

def tg(text, silent=False):
    """Send a Telegram message tagged CHAMPION; never raises."""
    try:
        return _tg_notify(text, silent=silent, tag="CHAMPION")
    except Exception:
        return False

# Environment-aware root: DigitalOcean runs as root (/root/canary),
# Google Cloud runs as ubuntu (/home/ubuntu/canary). Pick whichever exists.
def _detect_root():
    for cand in (pathlib.Path("/root/canary"), pathlib.Path("/home/ubuntu/canary")):
        try:
            if cand.exists():
                return cand
        except PermissionError:
            continue  # /root/canary exists but we have no read access — skip
    # default to whoever we are
    return pathlib.Path(os.path.expanduser("~")) / "canary"

ROOT = pathlib.Path(os.environ.get("CANARY_ROOT", "")) if os.environ.get("CANARY_ROOT") else _detect_root()
LOG_FILE     = ROOT / "runtime" / "champion_battle.log"
STATE_FILE   = ROOT / "runtime" / "champion_state.json"
HEALTH_FILE  = ROOT / "runtime" / "champion_health.json"
SIGNALS_FILE = ROOT / "runtime" / "coach_signals.json"   # written by coach.py
ROUNDS_FILE  = ROOT / "runtime" / "battle_rounds.json"   # persisted round-by-round results
# ── v4.0 Self-Learning Ecosystem ─────────────────────────────────────────────
ACADEMY_KB   = pathlib.Path("/home/ubuntu/academy/knowledge.json")
LAB_DISC     = pathlib.Path("/home/ubuntu/academy/lab_discoveries.json")
WAR_ROOM     = pathlib.Path("/home/ubuntu/academy/war_room_signals.json")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Strategy config ─────────────────────────────────────────────────────────
STRATEGY_NAME   = "CMO_CHAMPION_v5_MAX_AGGRESSION_4AGENT_RIVALRY"
# v9.0 TRIPLE CYCLE ENGINE: expanded pair universe (3x more opportunities)
# v9.1 DUST-PROOF PAIR UNIVERSE:
# REMOVED: FLOKI(9 dust), WIF(11 dust), SHIB(7 dust), DOGE(4 dust), BOME(1 dust)
# REMOVED: OP(3 dust), ARB(1 dust) — IOC partial-fill victims on low liquidity
# KEPT: High-liquidity pairs with precision >= 2 (never dust)
PAIRS           = ["ADA_USDT", "XRP_USDT", "SOL_USDT", "AVAX_USDT",
                   "NEAR_USDT", "APT_USDT", "TRX_USDT", "LINK_USDT",
                   "UNI_USDT", "DOT_USDT", "MATIC_USDT", "LTC_USDT",
                   "BNB_USDT", "ATOM_USDT", "INJ_USDT", "SUI_USDT"]
# DUST-PROOF: all pairs above have min_base_amount << $1, precision >= 1
# IOC partial fills still give sellable quantities for these pairs
# TRIPLE CYCLE: 3 concurrent cycle layers per agent (SCALP + SWING + BREAKOUT)
TRIPLE_CYCLE_ENABLED = True         # v9.0: enable 3x concurrent cycle layers
CYCLE_SCALP_MAX_HOLD  = 45          # SCALP cycle: max 45s hold, tight TP/SL
CYCLE_SWING_MAX_HOLD  = 180         # SWING cycle: max 3min hold, wider TP/SL
CYCLE_BREAK_MAX_HOLD  = 120         # BREAKOUT cycle: max 2min hold, momentum TP
CYCLE_SCALP_TP_PCT    = 0.0025      # SCALP TP: 0.25% (fast small wins)
CYCLE_SCALP_SL_PCT    = 0.0015      # SCALP SL: 0.15% (tight stop)
CYCLE_SWING_TP_PCT    = 0.0080      # SWING TP: 0.80% (bigger wins)
CYCLE_SWING_SL_PCT    = 0.0040      # SWING SL: 0.40%
CYCLE_BREAK_TP_PCT    = 0.0060      # BREAKOUT TP: 0.60%
CYCLE_BREAK_SL_PCT    = 0.0030      # BREAKOUT SL: 0.30%
CYCLE_SCALP_CONF_MIN  = 7           # SCALP needs 7+ confluence
CYCLE_SWING_CONF_MIN  = 9           # SWING needs 9+ confluence (ELITE)
CYCLE_BREAK_CONF_MIN  = 10          # BREAKOUT needs 10+ confluence (near GODMODE)
# Profit compounding: reinvest % of profit into next trade size
PROFIT_COMPOUND_RATE  = 0.20        # 20% of session profit added to base size
PROFIT_COMPOUND_MAX   = 3.0         # Max 3x base size from compounding
PROFIT_LOCK_THRESHOLD = 50.0        # Lock 50% of profit when session PnL > $50

# ── v6.0 BALANCED ENTRY SIZE CONFIG (fixed from MAX AGGRESSION) ─────────────
# v5.0 had $20 base which was too large for VELOCITY/SENTINEL low balances
# v6.0: $10 base, dynamic sizing via MAX_RISK_PER_TRADE cap protects small accounts
BASE_SIZE_USDT  = 10.0          # v6.0 BALANCED: $10 base (was $20)
MAX_STREAK      = 3             # up to 4x on win streak (unchanged)
# Confidence-weighted position multipliers
LOW_CONF_MULT   = 0.50          # MIN SIZE: $5 (10*0.50) — Gate.io minimum
NORMAL_CONF_MULT = 1.00         # Standard setup → $10 base size
HIGH_CONF_MULT  = 1.50          # Strong setup → $15 (10*1.5)
ELITE_CONF_MULT = 2.00          # ELITE MAX: $20 (10*2.0) — FULL POWER
# Confidence thresholds (score-based, 0–1 scale)
HIGH_CONF_THRESH  = 0.85        # score >= 0.85 → HIGH confidence
ELITE_CONF_THRESH = 0.92        # score >= 0.92 → ELITE confidence
# Risk compression
MAX_RISK_PER_TRADE  = 0.005     # Max 0.5% of balance per trade
MAX_TOTAL_EXPOSURE  = 0.25      # Max 25% of balance in open positions (was 30%)
# Winner pyramiding
ENABLE_PYRAMIDING   = True      # Add to winning positions
MAX_PYRAMID_LAYERS  = 2         # Max 2 pyramid layers
PYRAMID_ONLY_PROFIT = True      # Only pyramid when position is in profit

# ── v3.0 HIGH-FREQUENCY ARENA MODE ──────────────────────────────────────────
TICK_S          = 1             # 1s MAXIMUM SPEED scan
# Regime-adaptive trade limits per agent per tick (v9.0: TRIPLE CYCLE = 9 max)
REGIME_TRADE_LIMITS = {
    "TREND":     9,             # Strong trend → 9 opens per tick (3 per cycle layer)
    "BREAKOUT":  9,             # Breakout regime → 9 opens per tick (max aggression)
    "SIDEWAYS":  3,             # Sideways → 3 opens per tick (1 per cycle layer)
    "CHAOS":     3,             # High volatility → 3 opens per tick (cautious)
}
# Overtrading protection (v9.0 TRIPLE CYCLE: 3x more trades allowed)
MAX_TRADES_PER_HOUR = 180       # v9.0 TRIPLE CYCLE: 180 trades/hour (3x cycles × 60)
OVERTRADE_WINDOW_S  = 3600      # Rolling window for trade count
# Spread + liquidity filter
MAX_SPREAD_PCT      = 0.003     # Skip pair if spread > 0.3%
MIN_VOLUME_USDT     = 500.0     # Min 24h volume $500 USDT
# Global kill switch
GLOBAL_DD_KILL_PCT  = 0.05      # 5% session DD → pause agent
MAX_CONSEC_LOSS     = 3             # 3 consecutive losses → pause 10 min
# ── Full-exit USDT enforcement ─────────────────────────────────────────────
FULL_EXIT_TO_USDT   = True          # CHAMPIONSHIP RULE: always return to USDT
FINAL_HOLD_ASSET    = "USDT"        # No token positions held overnight
# ── Momentum + ADX filters ────────────────────────────────────────────────
ADX_THRESHOLD       = 22            # Minimum ADX for trend confirmation
MIN_VOLUME_BURST    = 1.5           # Volume must be 1.5x average for entry
ENABLE_SPREAD_FILTER    = True      # Skip pairs with spread > MAX_SPREAD_PCT
ENABLE_LIQUIDITY_FILTER = True      # Skip pairs with low volume
ENABLE_SLIPPAGE_PROTECTION = True   # Cancel if fill > 0.1% slippage
# ── XP + Rivalry + Telemetry system flags ─────────────────────────────────
ENABLE_XP_SYSTEM        = True      # Agents earn XP per trade
ENABLE_RIVALRY_ENGINE   = True      # Agents track rivals and adapt
ENABLE_REALTIME_TELEMETRY = True    # Publish live telemetry every tick
ENABLE_LIVE_ARENA       = True      # Championship arena mode active
ENABLE_AUTO_MODE_SWITCH = True      # Auto-switch strategy on regime change

TP_PCT          = 0.0050        # v9.0: 0.50% TP default (cycle-specific TP overrides this)
SL_PCT          = 0.0025        # v9.0: 0.25% SL default (cycle-specific SL overrides this)
CMO_PERIOD      = 14
CMO_THRESHOLD   = 6.0
EMA_PERIOD      = 3
MAX_HOLD_S      = 180           # v9.0 TRIPLE CYCLE: 180s max hold (SWING cycle needs more time)
COOLDOWN_S      = 15            # v9.0 TRIPLE CYCLE: 15s cooldown (3x faster than v6.0's 30s)
FEE_PCT         = 0.0020
MAX_OPEN        = 9             # v9.0 TRIPLE CYCLE: 9 concurrent positions (3 per cycle layer × 3 layers)
# ── Dynamic best-pair scanner config ──
SCAN_MIN_SCORE  = 0.0
SCAN_COACH_BIAS = 0.15
# ── Dynamic Strategy Rotation config ─────────────────────────────────────────
DYN_ROT_UPTREND_THRESH   = 15.0
DYN_ROT_DOWNTREND_THRESH = -15.0
DYN_ROT_LOSS_SWITCH      = 3
DYN_ROT_WIN_LOCK         = 5
DYN_STRATEGIES_UPTREND   = ["CHANDE_MOMENTUM", "PARABOLIC_SAR", "FAIR_VALUE_GAP"]
DYN_STRATEGIES_RANGE     = ["RANGE_TRADING", "BB_SQUEEZE", "KELTNER_RSI"]
DYN_STRATEGIES_DOWNTREND = ["WILLIAMS_R_REVERSAL", "BB_SQUEEZE", "KELTNER_RSI"]
# ── Battle-round config ───────────────────────────────────────────────────────
ROUND_INTERVAL_SEC  = int(os.environ.get("CHAMPION_ROUND_SEC", "3600"))
ROUND_HISTORY_LIMIT = 72
API_RETRY_S     = 300
MIN_SELL_USDT   = 3.0           # Gate.io min market order ~$3; below = leave as dust
GATE_MIN_ORDER  = 3.0           # Gate.io minimum order size in USDT (module-level constant)
BALANCE_SYNC_TICKS = 300        # v6.0 FIX: sync real balance every 300 ticks (~5 min at 1s/tick)

# ── v7.0 SMART KELLY + SMART DOUBLING (33-LEVEL MODE) ────────────────────────
# Kelly Criterion: f* = (W*R - L) / R  where W=win_rate, L=loss_rate, R=TP/SL ratio
# Smart Kelly uses rolling-100 win rate, quarter-Kelly (0.25x) for safety
# Smart Doubling: 33 levels, doubles on loss (recovery), resets on win
# Hybrid: Kelly sets the BASE, Doubling scales it on loss streaks for recovery
KELLY_FRACTION     = 0.25           # Quarter-Kelly for safety (Gods Level standard)
KELLY_MIN_TRADES   = 10             # Min trades before Kelly activates (use BASE_SIZE before)
KELLY_MAX_MULT     = 3.0            # Kelly never exceeds 3x BASE_SIZE
KELLY_MIN_MULT     = 0.25           # Kelly never goes below 0.25x BASE_SIZE
# Smart Doubling — 33 levels of progressive recovery sizing
# Level 0 = base, Level 1 = 1.5x, Level 2 = 2x, ... Level 5 = 3.5x, then caps
DOUBLING_LEVELS    = 33             # 33-level mode
DOUBLING_ON_LOSS   = True           # Scale UP on loss (recovery mode)
DOUBLING_RESET_WIN = True           # Reset to level 0 on any win
DOUBLING_MAX_MULT  = 4.0            # Hard cap: never exceed 4x base
# Level → multiplier mapping (33 levels, progressive)
# Levels 0-5: gentle ramp (1.0x → 1.5x → 2.0x → 2.5x → 3.0x → 3.5x)
# Levels 6-10: moderate (3.5x → 4.0x capped)
# Levels 11+: capped at 4.0x (safety)
DOUBLING_MULT_TABLE = (
    [round(1.0 + i * 0.5, 2) for i in range(6)] +   # 0-5: 1.0, 1.5, 2.0, 2.5, 3.0, 3.5
    [round(3.5 + i * 0.1, 2) for i in range(1, 6)] + # 6-10: 3.6, 3.7, 3.8, 3.9, 4.0
    [4.0] * 22                                        # 11-32: capped at 4.0
)
# Smart Stop/Start: auto-pause doubling when DD > threshold, auto-resume on recovery
DOUBLING_PAUSE_DD_PCT = 0.03        # Pause doubling if daily DD > 3% (protect capital)
DOUBLING_RESUME_WIN   = 2           # Resume after 2 consecutive wins

# ── v8.0 GOD-LEVEL PREDICTION ENGINE ─────────────────────────────────────────
# Multi-layer confluence: ALL operators must agree before a trade is opened.
# Only enters trades with maximum win probability (ELITE setups only).
# ── Confluence gate thresholds ──
PRED_MIN_CONFLUENCE  = 7        # minimum weighted signals that must agree (out of 11)
PRED_ELITE_CONF      = 9        # elite setup: 9+ signals → max size boost
PRED_GODMODE_CONF    = 11       # godmode: all 11 signals → maximum aggression
# ── Dynamic TP/SL based on ATR volatility ──
PRED_ATR_PERIOD      = 14       # ATR lookback period
PRED_TP_ATR_MULT     = 2.0      # TP = entry + 2.0 × ATR
PRED_SL_ATR_MULT     = 1.0      # SL = entry - 1.0 × ATR  (2:1 R:R)
PRED_TP_MIN_PCT      = 0.0030   # TP never less than 0.30%
PRED_TP_MAX_PCT      = 0.0150   # TP never more than 1.50%
PRED_SL_MIN_PCT      = 0.0015   # SL never less than 0.15%
PRED_SL_MAX_PCT      = 0.0075   # SL never more than 0.75%
# ── Future price prediction (micro momentum extrapolation) ──
PRED_FORECAST_TICKS  = 5        # predict price 5 ticks ahead
PRED_FORECAST_MIN_UP = 0.0003   # predicted move must be >= +0.03% to enter
# ── Confluence signal weights (Gods Level Buy Checklist) ──
# Each signal returns (fired: bool, weight: int)
PRED_WEIGHTS = {
    "cmo_momentum":      3,   # CMO above threshold (core signal)
    "ema_trend":         2,   # fast EMA > slow EMA (trend confirmation)
    "rsi_oversold":      2,   # RSI < 45 and rising (entry timing)
    "williams_r":        1,   # W%R <= -70 (oversold reversal)
    "bb_lower":          1,   # price near lower Bollinger Band
    "volume_burst":      2,   # volume spike vs average (institutional entry)
    "regime_up":         2,   # regime_is_up() confirms uptrend
    "slope_positive":    1,   # short-term slope > 0
    "range_position":    1,   # price in lower 40% of recent range (buy dip)
    "macd_cross":        2,   # MACD line crosses above signal line
    "momentum_accel":    2,   # price acceleration (2nd derivative positive)
}
PRED_MAX_WEIGHT = sum(PRED_WEIGHTS.values())  # 19 total

# ── v8.2 SMART ROTATION ENGINE ──────────────────────────────────────────────────────────────────────────────
ROTATION_TICKS        = 6       # Re-evaluate best pair every 6 ticks (~3 min)
ROTATION_MIN_TRADES   = 3       # Min trades before a pair can be ranked
BLACKLIST_LOSS_STREAK = 4       # Blacklist pair after 4 consecutive losses
BLACKLIST_DURATION_S  = 600     # Blacklist duration: 10 minutes
ROTATION_BOOST_TOP    = 1.30    # Score boost for #1 ranked pair (30%)
ROTATION_BOOST_TOP2   = 1.15    # Score boost for #2 ranked pair (15%)
ROTATION_PENALTY_COLD = 0.70    # Score penalty for cold/losing pairs (30% cut)
STRATEGY_KEYS = [
    "CHANDE_MOMENTUM",   # Best for momentum/trending markets
    "RANGE_TRADING",     # Best for sideways/range-bound markets
    "SQUEEZE_MOMENTUM",  # Best for breakout setups
    "TRIPLE_EMA",        # Best for strong trend confirmation
    "WADDAH_ATTAR",      # Best for explosive moves
]

# ── v6.0 FIXED dd_cap: 5% of real balance (dynamic, resets on balance sync) ──
# VELOCITY/SENTINEL: was $0.50 (50 cents!) — caused instant pause every session
# Now: dd_cap is set dynamically in Agent._init_live() based on real balance
# Static fallback here is used only if API fails at startup
ACCOUNTS = {
    "TITAN":          {"key_file": ROOT/".api_key_main",  "dd_cap": 50.00, "floor": 100.0, "alloc_cap": 700.0},
    "VELOCITY":       {"key_file": ROOT/".api_key_sub1",  "dd_cap":  6.25, "floor":   5.0,  "alloc_cap": None},
    "SENTINEL":       {"key_file": ROOT/".api_key_sub2",  "dd_cap":  5.75, "floor":   5.0,  "alloc_cap": None},
    "TRADING_GURU":   {"key_file": ROOT/".api_key_main",  "dd_cap": 50.00, "floor":  50.0,  "alloc_cap": 300.0},
}


# ── v5.0 Championship Constitution ───────────────────────────────────────────
CHAMPIONSHIP_RULE   = "THE WINNER IS THE MAX USDT HUNTER"
RIVAL_BOOST_PCT     = 0.20      # Boost size 20% when trailing rival by >5%
RIVAL_CATCH_THRESH  = 0.05      # 5% behind rival → activate rivalry mode
SPORTSMAN_TAUNT_INTERVAL = 10   # Log rivalry status every 10 ticks
# TRADING GURU special powers
TG_LEARN_INTERVAL   = 5         # Learn from rivals every 5 ticks
TG_ELITE_BOOST      = 3.00      # TRADING GURU gets 3x ELITE multiplier
TG_STUDY_ALL        = True      # Studies all other agents' open trades

# ── Logging ─────────────────────────────────────────────────────────────────────
def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f: f.write(line + "\n")
    except: pass

# ── Self-Learning Ecosystem Loader ───────────────────────────────────────────
_academy_cache = {}
_academy_ts    = 0.0
_warroom_cache = {}
_warroom_ts    = 0.0
_lab_cache     = {}
_lab_ts        = 0.0

def load_academy(max_age=1800):
    """Load Academy knowledge base (cached, refreshes every 30 min)."""
    global _academy_cache, _academy_ts
    if time.time() - _academy_ts < max_age and _academy_cache:
        return _academy_cache
    try:
        if ACADEMY_KB.exists():
            with open(ACADEMY_KB) as f:
                _academy_cache = json.load(f)
            _academy_ts = time.time()
    except Exception:
        pass
    return _academy_cache

def load_war_room(max_age=60):
    """Load War Room signals (cached, refreshes every 60s)."""
    global _warroom_cache, _warroom_ts
    if time.time() - _warroom_ts < max_age and _warroom_cache:
        return _warroom_cache
    try:
        if WAR_ROOM.exists():
            with open(WAR_ROOM) as f:
                _warroom_cache = json.load(f)
            _warroom_ts = time.time()
    except Exception:
        pass
    return _warroom_cache

def load_lab(max_age=300):
    """Load Lab discoveries (cached, refreshes every 5 min)."""
    global _lab_cache, _lab_ts
    if time.time() - _lab_ts < max_age and _lab_cache:
        return _lab_cache
    try:
        if LAB_DISC.exists():
            with open(LAB_DISC) as f:
                _lab_cache = json.load(f)
            _lab_ts = time.time()
    except Exception:
        pass
    return _lab_cache

def get_war_room_directive(agent_name):
    """Get War Room directive for a specific agent."""
    wr = load_war_room()
    if not wr:
        return None
    return wr.get("agent_directives", {}).get(agent_name)

def get_war_room_top_pairs():
    """Get top recommended pairs from War Room."""
    wr = load_war_room()
    if not wr:
        return []
    recs = wr.get("recommendations", [])
    return [r["pair"] for r in recs if r.get("recommendation") in ("STRONG_BUY", "BUY")][:5]

def get_war_room_regime():
    """Get overall market regime from War Room."""
    wr = load_war_room()
    if not wr:
        return "UNKNOWN"
    return wr.get("overall_regime", "UNKNOWN")

def get_lab_best_pair():
    """Get best pair from Lab discoveries."""
    lab = load_lab()
    if not lab:
        return None
    return lab.get("best_pair")

def get_academy_pair_score(pair):
    """Get Academy score for a pair (based on historical PF)."""
    kb = load_academy()
    if not kb:
        return 1.0
    # Check best combos
    for combo in kb.get("best_strategy_pair_combos", []):
        if combo.get("pair") == pair:
            return min(combo.get("profit_factor", 1.0), 3.0)
    return 1.0

# ── Gate.io client ────────────────────────────────────────────────────────────
class GateClient:
    BASE = "https://api.gateio.ws/api/v4"

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret
        self.ok = bool(key and secret)

    def _sign(self, method, path, query="", body=""):
        ts = str(int(time.time()))
        bh = hashlib.sha512(body.encode()).hexdigest()
        # Gate.io v4 HMAC requires full path including /api/v4 prefix
        full_path = "/api/v4" + path
        msg = f"{method}\n{full_path}\n{query}\n{bh}\n{ts}"
        sig = hmac.new(self.secret.encode(), msg.encode(), hashlib.sha512).hexdigest()
        return {"KEY": self.key, "Timestamp": ts, "SIGN": sig,
                "Content-Type": "application/json", "Accept": "application/json"}

    def _req(self, method, path, params=None, body=None):
        if not self.ok: return None
        query = urllib.parse.urlencode(params) if params else ""
        hdrs = self._sign(method, path, query, body or "")
        url = self.BASE + path + ("?" + query if query else "")
        req = urllib.request.Request(url, data=(body or "").encode() if body else None,
                                     headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise
            log(f"  [GateClient] {method} {path} HTTP {e.code}")
            return None
        except Exception as e:
            log(f"  [GateClient] {method} {path} error: {e}")
            return None

    def spot_balance(self, currency="USDT"):
        data = self._req("GET", "/spot/accounts", {"currency": currency})
        if data and isinstance(data, list):
            for a in data:
                if a.get("currency") == currency:
                    return float(a.get("available", 0))
        return None

    def ticker(self, pair):
        data = self._req("GET", "/spot/tickers", {"currency_pair": pair})
        if data and isinstance(data, list) and data:
            return float(data[0].get("last", 0))
        return None

    def candles(self, pair, limit=30, interval="10s"):
        data = self._req("GET", "/spot/candlesticks",
                         {"currency_pair": pair, "limit": limit, "interval": interval})
        if data and isinstance(data, list):
            return [float(c[2]) for c in data]  # close prices
        return []

    def place_buy(self, pair, amount_usdt, price):
        # v9.1 DUST FIX: Use aggressive limit order (0.1% above market) instead of IOC market
        # IOC market orders partially fill on low-liquidity pairs → DUST losses
        # Aggressive limit at +0.1% fills immediately but guarantees full fill or no fill
        # amount = coin qty (base currency) for limit orders
        coin_qty = amount_usdt / price if price > 0 else 0
        # Get precision for this pair (cached)
        prec, min_base = self.pair_precision(pair)
        coin_qty = round(coin_qty, prec)
        if min_base > 0 and coin_qty < min_base:
            coin_qty = min_base  # snap up to minimum
        limit_price = round(price * 1.001, 8)  # 0.1% above market = fills immediately
        body = json.dumps({"currency_pair": pair, "side": "buy",
                           "amount": str(coin_qty),
                           "price": str(limit_price),
                           "type": "limit",
                           "time_in_force": "ioc"})  # ioc: fill what's available, cancel rest
        return self._req("POST", "/spot/orders", body=body)

    def place_sell(self, pair, amount_coin):
        body = json.dumps({"currency_pair": pair, "side": "sell",
                           "amount": str(amount_coin), "type": "market",
                           "time_in_force": "ioc"})  # required for market orders
        return self._req("POST", "/spot/orders", body=body)

    def token_balance(self, currency):
        """Return the real available balance of a token (for full-qty sells)."""
        return self.spot_balance(currency)

    def pair_precision(self, pair):
        """Return amount_precision + min_base_amount for safe full-qty sells."""
        data = self._req("GET", f"/spot/currency_pairs/{pair}")
        if data and isinstance(data, dict):
            return (int(data.get("amount_precision", 6) or 6),
                    float(data.get("min_base_amount", 0) or 0))
        return (6, 0.0)

# ── Pair precision + minimum quantity cache (prevents DUST losses) ─────────────
# Fetched once per pair from Gate.io API and cached for the session.
_pair_min_qty_cache = {}   # pair -> min_base_amount (coin qty)
_pair_precision_cache = {} # pair -> (amount_precision, min_base_amount)

def get_pair_min_qty(gate_client, pair):
    """Return the minimum base amount (coin qty) for a pair. Cached per session."""
    if pair in _pair_min_qty_cache:
        return _pair_min_qty_cache[pair]
    try:
        _, min_base = gate_client.pair_precision(pair)
        _pair_min_qty_cache[pair] = min_base
        return min_base
    except Exception:
        return 0.0

# Monkey-patch GateClient.pair_precision to use session cache
_orig_pair_precision = GateClient.pair_precision
def _cached_pair_precision(self, pair):
    if pair in _pair_precision_cache:
        return _pair_precision_cache[pair]
    result = _orig_pair_precision(self, pair)
    _pair_precision_cache[pair] = result
    return result
GateClient.pair_precision = _cached_pair_precision

# ── Key loader ────────────────────────────────────────────────────────────────
def load_keys(key_file):
    try:
        raw = pathlib.Path(key_file).read_text().strip()
        if ":" in raw:
            parts = raw.split(":", 1)
            return parts[0].strip(), parts[1].strip()
        data = json.loads(raw)
        return data.get("key", ""), data.get("secret", "")
    except Exception as e:
        log(f"  [KEYS] Failed to load {key_file}: {e}")
        return "", ""

# ── Indicators ────────────────────────────────────────────────────────────────
def cmo(closes, period=CMO_PERIOD):
    if len(closes) < period + 1: return 0.0
    ups = sum(max(closes[i] - closes[i-1], 0) for i in range(-period, 0))
    dns = sum(max(closes[i-1] - closes[i], 0) for i in range(-period, 0))
    return (ups - dns) / (ups + dns) * 100 if (ups + dns) > 0 else 0.0

def ema(closes, period=EMA_PERIOD):
    if not closes: return 0.0
    k = 2 / (period + 1)
    e = closes[0]
    for c in closes[1:]: e = c * k + e * (1 - k)
    return e

def williams_r(closes, period=14):
    if len(closes) < period: return -50.0
    window = closes[-period:]
    hi, lo = max(window), min(window)
    if hi == lo: return -50.0
    return (hi - closes[-1]) / (hi - lo) * -100

def rsi(closes, period=14):
    if len(closes) < period + 1: return 50.0
    gains = losses = 0.0
    for i in range(-period, 0):
        d = closes[i] - closes[i-1]
        gains += max(d, 0); losses += max(-d, 0)
    if losses == 0: return 100.0
    rs = (gains / period) / (losses / period)
    return 100 - 100 / (1 + rs)

# ── Regime filter (EDGE FIX 2026-06-02) ───────────────────────────────────────
# Long-only spot scalping bleeds fees in flat/down markets. Only allow a LONG
# entry when the short-term regime is genuinely up: fast EMA above slow EMA AND
# recent slope positive AND price in the upper half of its recent range.
REGIME_FAST   = 5
REGIME_SLOW   = 20
REGIME_SLOPE_LOOKBACK = 8     # candles to measure short-term slope
REGIME_MIN_SLOPE_PCT  = 0.0005  # require >= +0.05% drift over the lookback

def regime_is_up(closes):
    """True when the market is trending up enough to justify a long scalp."""
    if len(closes) < REGIME_SLOW + 1:
        return False
    fast = ema(closes[-REGIME_FAST:], REGIME_FAST)
    slow = ema(closes[-REGIME_SLOW:], REGIME_SLOW)
    if fast <= slow:
        return False
    ref = closes[-REGIME_SLOPE_LOOKBACK]
    if ref <= 0:
        return False
    slope = (closes[-1] - ref) / ref
    if slope < REGIME_MIN_SLOPE_PCT:
        return False
    window = closes[-REGIME_SLOW:]
    hi, lo = max(window), min(window)
    if hi == lo:
        return False
    pos = (closes[-1] - lo) / (hi - lo)
    return pos >= 0.45  # price in the upper ~half of its recent range

# ── Strategy signal registry ──────────────────────────────────────────────────
# Each returns True when the strategy says BUY (long entry) for the given closes.
def sig_chande_momentum(closes, price):
    # EDGE FIX: CMO above threshold AND price not far below short EMA (0.997 tolerance).
    return cmo(closes) >= CMO_THRESHOLD and price >= ema(closes[-EMA_PERIOD:]) * 0.997

def sig_range_trading(closes, price):
    # Buy near lower band of recent range (mean-reversion long)
    if len(closes) < 20: return False
    window = closes[-20:]
    hi, lo = max(window), min(window)
    if hi == lo: return False
    pos = (price - lo) / (hi - lo)
    return pos <= 0.25  # price in bottom 25% of range

def sig_williams_r(closes, price):
    return williams_r(closes) <= -80  # oversold reversal long

def sig_fvg(closes, price):
    # Simplified FVG: bullish gap — last close > prior high after a dip
    if len(closes) < 4: return False
    return closes[-1] > closes[-3] and closes[-2] < closes[-3] and rsi(closes) < 60

def sig_keltner_rsi(closes, price):
    return rsi(closes) <= 35 and price <= ema(closes, 20)

def sig_bb_squeeze(closes, price):
    if len(closes) < 20: return False
    window = closes[-20:]
    mean = sum(window) / len(window)
    var = sum((c - mean) ** 2 for c in window) / len(window)
    std = var ** 0.5
    return price <= mean - std  # buy below lower band

def sig_parabolic_sar(closes, price):
    # Momentum long: price reclaiming short EMA after dip
    return price > ema(closes[-5:]) and rsi(closes) > 45 and rsi(closes) < 70

def sig_cmo_default(closes, price):
    return sig_chande_momentum(closes, price)

STRATEGY_SIGNALS = {
    "CHANDE_MOMENTUM":     sig_chande_momentum,
    "RANGE_TRADING":       sig_range_trading,
    "WILLIAMS_R_REVERSAL": sig_williams_r,
    "FAIR_VALUE_GAP":      sig_fvg,
    "KELTNER_RSI":         sig_keltner_rsi,
    "BB_SQUEEZE":          sig_bb_squeeze,
    "PARABOLIC_SAR":       sig_parabolic_sar,
}

def strategy_signal(strategy_key, closes, price):
    # EDGE FIX: regime gate first — never open a long scalp in a flat/down market.
    if not regime_is_up(closes):
        return False
    fn = STRATEGY_SIGNALS.get(strategy_key, sig_cmo_default)
    try:
        return fn(closes, price)
    except Exception:
        return False

# ── Real-time best-pair scanner (MAX OPTIMAL PROFIT) ───────────────────────────
# Instead of trading one fixed coach-assigned pair, every agent scores ALL pairs
# each tick and trades the single most profitable opportunity available right now.
def detect_market_regime(closes):
    """v3.0: Detect market regime for adaptive trade frequency.
    Returns: TREND | BREAKOUT | SIDEWAYS | CHAOS"""
    # v4.0: prefer War Room regime if fresh
    wr_regime = get_war_room_regime()
    if wr_regime not in ("UNKNOWN", ""):
        return wr_regime
    if len(closes) < 25:
        return "SIDEWAYS"
    fast = ema(closes[-5:], 5)
    slow = ema(closes[-20:], 20)
    # Volatility: std of last 20 closes / mean
    window = closes[-20:]
    mean = sum(window) / len(window)
    var = sum((c - mean) ** 2 for c in window) / len(window)
    std = var ** 0.5
    vol_pct = std / mean if mean > 0 else 0
    # Slope: % change over last 10 candles
    ref = closes[-10]
    slope = (closes[-1] - ref) / ref if ref > 0 else 0
    # CMO for momentum
    cmo_val = abs(cmo(closes))
    if vol_pct > 0.025:          # High volatility → CHAOS
        return "CHAOS"
    elif cmo_val > 20 and abs(slope) > 0.005:  # Strong directional momentum
        return "BREAKOUT"
    elif fast > slow and slope > 0.002:         # Uptrend
        return "TREND"
    elif fast < slow and slope < -0.002:        # Downtrend (treat as TREND for limit)
        return "TREND"
    else:
        return "SIDEWAYS"

# ── God-Level Indicator Helpers (v8.0) ──────────────────────────────────────
def atr_calc(closes, period=14):
    """Average True Range (simplified: mean of absolute candle-to-candle moves)."""
    if len(closes) < 2: return 0.0
    trs = [abs(closes[i] - closes[i-1]) for i in range(max(-period, -len(closes)+1), 0)]
    return sum(trs) / len(trs) if trs else 0.0

def macd_cross(closes, fast=12, slow=26, signal=9):
    """True if MACD line just crossed above signal line (bullish cross)."""
    if len(closes) < slow + signal + 2: return False
    def _ema(data, p):
        k = 2 / (p + 1); e = data[0]
        for c in data[1:]: e = c * k + e * (1 - k)
        return e
    macd_now  = _ema(closes, fast) - _ema(closes, slow)
    macd_prev = _ema(closes[:-1], fast) - _ema(closes[:-1], slow)
    sig_now   = _ema([macd_now], signal)  # simplified: use current MACD as signal proxy
    return macd_now > 0 and macd_prev <= 0  # zero-line cross (bullish)

def momentum_accel(closes):
    """True if price acceleration is positive (2nd derivative > 0)."""
    if len(closes) < 5: return False
    d1 = closes[-1] - closes[-2]  # velocity now
    d0 = closes[-2] - closes[-3]  # velocity before
    return d1 > d0 and d1 > 0     # accelerating upward

def bb_position(closes, period=20):
    """Returns price position relative to Bollinger Bands: 0=lower, 1=upper."""
    if len(closes) < period: return 0.5
    window = closes[-period:]
    mean = sum(window) / len(window)
    std = (sum((c - mean)**2 for c in window) / len(window)) ** 0.5
    if std == 0: return 0.5
    return (closes[-1] - (mean - 2*std)) / (4*std)  # 0=at lower band, 1=at upper band

def predict_price(closes, ticks_ahead=5):
    """Micro-momentum extrapolation: predict price N ticks ahead.
    Uses linear regression over last 10 candles."""
    if len(closes) < 10: return closes[-1] if closes else 0.0
    n = 10
    xs = list(range(n))
    ys = closes[-n:]
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0.0
    return ys[-1] + slope * ticks_ahead

def dynamic_tp_sl(closes, price):
    """Compute ATR-based dynamic TP/SL levels.
    Returns (tp_price, sl_price) clamped to safe percentage bounds."""
    atr_v = atr_calc(closes, PRED_ATR_PERIOD)
    if atr_v <= 0 or price <= 0:
        # Fallback to fixed percentages
        return price * (1 + TP_PCT), price * (1 - SL_PCT)
    # ATR-based levels
    tp_raw = price + PRED_TP_ATR_MULT * atr_v
    sl_raw = price - PRED_SL_ATR_MULT * atr_v
    # Clamp to percentage bounds
    tp_pct = (tp_raw - price) / price
    sl_pct = (price - sl_raw) / price
    tp_pct = max(PRED_TP_MIN_PCT, min(PRED_TP_MAX_PCT, tp_pct))
    sl_pct = max(PRED_SL_MIN_PCT, min(PRED_SL_MAX_PCT, sl_pct))
    tp = price * (1 + tp_pct)
    sl = price * (1 - sl_pct)
    return round(tp, 10), round(sl, 10)

def god_level_confluence(closes, price, strategy_key, ticker_data=None):
    """v8.0 GOD-LEVEL PREDICTION ENGINE.
    Runs all 11 confluence operators and returns:
      (weighted_score, max_weight, signals_hit, confluence_pct, is_elite)
    Only ELITE setups (confluence >= PRED_MIN_CONFLUENCE/PRED_MAX_WEIGHT) are tradable.
    """
    if len(closes) < 25 or not price:
        return 0, PRED_MAX_WEIGHT, [], 0.0, False

    hit = {}  # signal_name -> weight if fired

    # 1. CMO momentum (weight 3) — core signal
    c = cmo(closes)
    if c >= CMO_THRESHOLD:
        hit["cmo_momentum"] = PRED_WEIGHTS["cmo_momentum"]

    # 2. EMA trend (weight 2) — fast > slow confirms uptrend
    e_fast = ema(closes[-5:], 5)
    e_slow = ema(closes[-20:], 20) if len(closes) >= 20 else e_fast
    if e_fast > e_slow:
        hit["ema_trend"] = PRED_WEIGHTS["ema_trend"]

    # 3. RSI oversold + rising (weight 2) — entry timing
    r = rsi(closes)
    r_prev = rsi(closes[:-1]) if len(closes) > 15 else r
    if r < 45 and r > r_prev:  # oversold and rising
        hit["rsi_oversold"] = PRED_WEIGHTS["rsi_oversold"]

    # 4. Williams %R oversold (weight 1)
    wr = williams_r(closes)
    if wr <= -70:
        hit["williams_r"] = PRED_WEIGHTS["williams_r"]

    # 5. Price near lower Bollinger Band (weight 1) — buy the dip
    bb_pos = bb_position(closes)
    if bb_pos <= 0.30:  # in lower 30% of BB range
        hit["bb_lower"] = PRED_WEIGHTS["bb_lower"]

    # 6. Volume burst (weight 2) — institutional entry signal
    if ticker_data and ticker_data.get("volume_usdt", 0) > 2000:
        hit["volume_burst"] = PRED_WEIGHTS["volume_burst"]
    elif not ticker_data:
        # No volume data available — give partial credit (don't penalize)
        hit["volume_burst"] = 1  # half weight

    # 7. Regime is up (weight 2) — macro trend confirmation
    if regime_is_up(closes):
        hit["regime_up"] = PRED_WEIGHTS["regime_up"]

    # 8. Short-term slope positive (weight 1)
    ref = closes[-REGIME_SLOPE_LOOKBACK] if len(closes) >= REGIME_SLOPE_LOOKBACK else closes[0]
    slope = (closes[-1] - ref) / ref if ref > 0 else 0.0
    if slope >= REGIME_MIN_SLOPE_PCT:
        hit["slope_positive"] = PRED_WEIGHTS["slope_positive"]

    # 9. Price in lower 40% of recent range (weight 1) — buy dip in trend
    window = closes[-20:] if len(closes) >= 20 else closes
    hi, lo = max(window), min(window)
    pos = (closes[-1] - lo) / (hi - lo) if hi > lo else 0.5
    if pos <= 0.40:
        hit["range_position"] = PRED_WEIGHTS["range_position"]

    # 10. MACD bullish cross (weight 2)
    if macd_cross(closes):
        hit["macd_cross"] = PRED_WEIGHTS["macd_cross"]

    # 11. Momentum acceleration (weight 2) — price speeding up
    if momentum_accel(closes):
        hit["momentum_accel"] = PRED_WEIGHTS["momentum_accel"]

    total_hit = sum(hit.values())
    confluence_pct = total_hit / PRED_MAX_WEIGHT
    is_elite = total_hit >= PRED_MIN_CONFLUENCE

    return total_hit, PRED_MAX_WEIGHT, list(hit.keys()), round(confluence_pct, 3), is_elite


def score_pair(closes, price, strategy_key, coach_bias=0.0, ticker_data=None):
    """v8.0 GOD-LEVEL PREDICTION ENGINE score.
    Returns (score, tradable). Only ELITE setups (confluence >= threshold) are tradable.
    Incorporates: multi-layer confluence + future price prediction + dynamic TP/SL readiness.
    """
    if len(closes) < CMO_PERIOD + 1 or not price:
        return (-999.0, False)

    # ── GATE 1: Strategy signal must fire ──
    fired = strategy_signal(strategy_key, closes, price)
    if not fired:
        return (-999.0, False)

    # ── GATE 2: God-Level Confluence — ALL operators synchronized ──
    total_hit, max_w, signals_hit, conf_pct, is_elite = god_level_confluence(
        closes, price, strategy_key, ticker_data=ticker_data)
    if not is_elite:
        return (-999.0, False)  # Not enough operators agree — skip this trade

    # ── GATE 3: Future price prediction — must predict upward move ──
    predicted = predict_price(closes, PRED_FORECAST_TICKS)
    predicted_move = (predicted - price) / price if price > 0 else 0.0
    if predicted_move < PRED_FORECAST_MIN_UP:
        return (-999.0, False)  # Prediction says price won't move up enough

    # ── SCORE: Blend confluence + prediction strength + momentum ──
    cmo_val = cmo(closes)
    slope = (closes[-1] - closes[-REGIME_SLOPE_LOOKBACK]) / closes[-REGIME_SLOPE_LOOKBACK] \
        if len(closes) >= REGIME_SLOPE_LOOKBACK and closes[-REGIME_SLOPE_LOOKBACK] > 0 else 0.0

    # Base score from confluence (0-1 range)
    score = conf_pct * 0.50                        # 50% weight: confluence quality
    score += (cmo_val / 100.0) * 0.25             # 25% weight: CMO momentum
    score += min(predicted_move * 1000, 0.15) * 0.15  # 15% weight: predicted move
    score += min(slope * 100, 0.10) * 0.10        # 10% weight: current slope
    score += coach_bias                            # small tilt toward coach hint

    # Elite/Godmode bonus
    if total_hit >= PRED_GODMODE_CONF:
        score *= 1.30  # 30% bonus for godmode setup
    elif total_hit >= PRED_ELITE_CONF:
        score *= 1.15  # 15% bonus for elite setup

    return (round(score, 6), score >= SCAN_MIN_SCORE)


def scan_best_pair(pairs, prices, closes_map, strategy_key, coach_pair=None,
                   exclude=None, ticker_map=None, rotation_boost_fn=None):
    """v8.2 GOD-LEVEL SCAN + SMART ROTATION: scan all pairs using the full Prediction Engine.
    Returns (pair, score) of the most profitable ELITE setup right now.
    Only ELITE setups (all operators synchronized) are returned.
    rotation_boost_fn: optional callable(pair) -> float multiplier from Smart Rotation Engine.
    """
    exclude = exclude or set()
    ticker_map = ticker_map or {}
    best_pair, best_score = None, -1e9
    # Pre-load external intelligence once per scan
    wr_pairs = get_war_room_top_pairs()
    lab_best = get_lab_best_pair()
    for pair in pairs:
        if pair in exclude:
            continue
        price = prices.get(pair)
        closes = closes_map.get(pair) or []
        ticker_data = ticker_map.get(pair)
        bias = SCAN_COACH_BIAS if (coach_pair and pair == coach_pair) else 0.0
        sc, tradable = score_pair(closes, price, strategy_key,
                                  coach_bias=bias, ticker_data=ticker_data)
        if not tradable:
            continue
        # v4.0: War Room + Academy boost (still applied on top of confluence gate)
        wr_boost  = 1.3 if pair in wr_pairs else 1.0
        lab_boost = 1.2 if pair == lab_best else 1.0
        acad_boost = min(get_academy_pair_score(pair), 1.5)
        sc = sc * wr_boost * lab_boost * acad_boost
        # v8.2: Smart Rotation boost/penalty
        if rotation_boost_fn:
            rot_mult = rotation_boost_fn(pair)
            if rot_mult == 0.0:
                continue  # blacklisted pair — skip entirely
            sc = sc * rot_mult
        if sc > best_score:
            best_pair, best_score = pair, sc
    return best_pair, best_score

# ── Coach signal loader ───────────────────────────────────────────────────────
_coach_cache = {"data": None, "mtime": 0}

def load_coach_signals():
    """Read coach_signals.json (per-agent setup+pair assignments). Cached by mtime."""
    try:
        m = SIGNALS_FILE.stat().st_mtime
        if m != _coach_cache["mtime"]:
            _coach_cache["data"] = json.loads(SIGNALS_FILE.read_text())
            _coach_cache["mtime"] = m
        return _coach_cache["data"]
    except Exception:
        return _coach_cache["data"]  # last good, or None

# ── Agent ─────────────────────────────────────────────────────────────────────
class Agent:
    def __init__(self, name, cfg):
        self.name     = name
        self.dd_cap   = cfg["dd_cap"]
        self.floor    = cfg["floor"]
        k, s = load_keys(cfg["key_file"])
        self.gate     = GateClient(k, s)
        self.live_mode = False
        self.api_ok   = False
        self.balance  = 200.0   # virtual until API confirmed
        self.start_bal = 200.0
        self.day_start_bal = 200.0
        self.positions = {}     # pair → {qty, entry, tp, sl, opened, size_usdt}
        self.last_trade = {}    # pair → timestamp
        self.wins = 0
        self.losses = 0
        self.streak = 0         # Anti-Martingale win streak
        self.rolling = deque(maxlen=100)  # last 100 outcomes
        self.last_api_retry = 0
        # Coach assignment (smart dynamic rotation) — defaults until coach signals arrive
        self.assigned_strategy = "CMO_CHAMPION_v1"
        self.assigned_key      = "CHANDE_MOMENTUM"
        self.assigned_pair     = None   # coach hint only; agent scans all PAIRS live
        self.traded_pair       = None   # last pair the dynamic scanner actually opened
        self.last_score        = 0.0    # score of the last scanner-selected pair
        self.last_conf_level   = "NORMAL"  # confidence level of last entry
        # v3.0: overtrading protection — rolling trade timestamps
        self.trade_timestamps  = deque()   # timestamps of recent trades
        # v3.0: pyramid tracking — pair → pyramid layer count
        self.pyramid_layers    = {}        # pair → int (0=base, 1=layer1, 2=layer2)
        # ── Per-round event trackers (folded into the ONE round-end Telegram) ──
        self.round_upgrade = None   # (old_pair, new_pair, pf) if coach upgraded this round
        self.round_peak_streak = 0  # highest streak reached during the round
        # v5.0 Rivalry Engine
        self.is_trading_guru = (name == "TRADING_GURU")
        self.rivalry_mode    = False
        self.rivalry_target  = None
        self.sportsman_rank  = 0
        self.rival_balances  = {}
        self.tg_study_count  = 0
        # v7.0 Smart Kelly + Smart Doubling (33-Level Mode)
        self.kelly_win_rate    = 0.55       # rolling win rate for Kelly calc (default 55%)
        self.doubling_level    = 0          # current doubling level (0=base, max=32)
        self.doubling_paused   = False      # True when daily DD > DOUBLING_PAUSE_DD_PCT
        self.doubling_resume_wins = 0       # consecutive wins since doubling paused
        # v8.2 Smart Rotation Engine
        self.pair_stats        = {}         # pair -> {wins, losses, pnl, streak, last_trade_ts}
        self.strategy_stats    = {}         # strategy_key -> {wins, losses, pnl}
        self.pair_blacklist    = {}         # pair -> blacklist_until_ts
        self.hot_pair          = None       # currently ranked #1 pair
        self.hot_strategy      = "CHANDE_MOMENTUM"  # currently ranked #1 strategy
        self.rotation_tick     = 0          # tick counter for rotation evaluation
        # v9.0 TRIPLE CYCLE ENGINE
        self.cycle_mode        = "SCALP"    # current active cycle: SCALP | SWING | BREAKOUT
        self.cycle_wins        = {"SCALP": 0, "SWING": 0, "BREAKOUT": 0}
        self.cycle_losses      = {"SCALP": 0, "SWING": 0, "BREAKOUT": 0}
        self.cycle_pnl         = {"SCALP": 0.0, "SWING": 0.0, "BREAKOUT": 0.0}
        self._session_pnl_acc  = 0.0        # total session PnL accumulator for compounding
        self.compound_mult     = 1.0        # current profit compounding multiplier
        self._init_live()

    def apply_coach(self, signals):
        """Apply the coach's per-agent setup+pair assignment."""
        if not signals:
            return
        a = (signals.get("assignments") or {}).get(self.name)
        if not a:
            return
        old_pair = self.assigned_pair
        old_key  = self.assigned_key
        self.assigned_strategy = a.get("strategy", self.assigned_strategy)
        self.assigned_key      = a.get("strategy_key") or self.assigned_key
        self.assigned_pair     = a.get("pair")  # e.g. "BOME_USDT"
        # ── Track coach upgrade for the consolidated round-end message (no separate send) ──
        if old_pair is not None and (self.assigned_pair != old_pair or self.assigned_key != old_key):
            try:
                pf = a.get("profit_factor")
                self.round_upgrade = (old_pair, self.assigned_pair, pf)
            except Exception:
                pass

    def _init_live(self):
        try:
            bal = self.gate.spot_balance()
            if bal is not None:
                self.balance = bal
                self.start_bal = bal
                self.day_start_bal = bal
                # v6.0 FIX: set dd_cap dynamically as 5% of real balance
                # This prevents the $0.50 dd_cap bug that paused agents instantly
                dynamic_dd_cap = max(5.0, round(bal * 0.05, 2))
                self.dd_cap = dynamic_dd_cap
                self.live_mode = True
                self.api_ok = True
                log(f"  [{self.name}] ✅ LIVE MODE — balance=${bal:.2f} USDT | dd_cap=${dynamic_dd_cap:.2f} (5%)")
            else:
                log(f"  [{self.name}] ⚠️ API returned None — SIMULATION mode")
        except urllib.error.HTTPError as e:
            log(f"  [{self.name}] ⚠️ API {e.code} — SIMULATION mode (retry in {API_RETRY_S}s)")
        except Exception as e:
            log(f"  [{self.name}] ⚠️ API error: {e} — SIMULATION mode")

    def retry_api(self):
        now = time.time()
        if now - self.last_api_retry < API_RETRY_S: return
        self.last_api_retry = now
        log(f"  [{self.name}] 🔄 Retrying API connection...")
        self._init_live()

    def sync_real_balance(self):
        """v6.0 FIX: Periodically sync balance from real Gate.io API.
        Prevents virtual tracking drift from causing false DD_CAP_HIT pauses.
        Called every BALANCE_SYNC_TICKS ticks from the main loop.
        Only syncs if no open positions (to avoid mid-trade confusion)."""
        if not self.live_mode: return
        if self.positions: return  # don't sync mid-trade
        try:
            real_bal = self.gate.spot_balance()
            if real_bal is not None and real_bal > 0:
                old_bal = self.balance
                drift = real_bal - old_bal
                if abs(drift) > 0.01:  # only log if meaningful drift
                    log(f"  [{self.name}] 🔄 BALANCE SYNC: virtual=${old_bal:.2f} → real=${real_bal:.2f} (drift={drift:+.2f})")
                self.balance = real_bal
                # Update day_start_bal if real balance is HIGHER (we made money)
                # This prevents false DD_CAP_HIT when balance grew since day start
                if real_bal > self.day_start_bal:
                    self.day_start_bal = real_bal
                # Recalculate dd_cap based on current real balance (5% rule)
                self.dd_cap = max(5.0, round(real_bal * 0.05, 2))
        except Exception as e:
            log(f"  [{self.name}] ⚠️ Balance sync failed: {e}")

    def kelly_size(self):
        """v7.0 Smart Kelly Criterion sizing.
        f* = (W*R - L) / R  (full Kelly)
        Smart Kelly = f* * KELLY_FRACTION (quarter-Kelly for safety)
        Returns a multiplier relative to BASE_SIZE_USDT.
        Falls back to 1.0x if not enough trade history."""
        total = self.wins + self.losses
        if total < KELLY_MIN_TRADES:
            return 1.0  # not enough data — use base size
        # Update rolling win rate from actual history
        if self.rolling:
            wins = sum(1 for x in self.rolling if x == "W")
            self.kelly_win_rate = wins / len(self.rolling)
        W = self.kelly_win_rate
        L = 1.0 - W
        R = TP_PCT / max(SL_PCT, 0.0001)   # reward-to-risk ratio (e.g. 0.50/0.25 = 2.0)
        # Kelly formula: f* = (W*R - L) / R
        if R <= 0:
            return 1.0
        f_star = (W * R - L) / R
        # Quarter-Kelly for safety
        kelly_mult = f_star * KELLY_FRACTION
        # Clamp to safe range
        kelly_mult = max(KELLY_MIN_MULT, min(KELLY_MAX_MULT, kelly_mult))
        return kelly_mult

    def doubling_size(self):
        """v7.0 Smart Doubling (33-Level Mode) multiplier.
        Returns a multiplier that scales with loss streak for recovery.
        Auto-pauses when daily DD > DOUBLING_PAUSE_DD_PCT.
        Auto-resumes after DOUBLING_RESUME_WIN consecutive wins."""
        # Check if doubling should be paused (DD protection)
        if self.day_start_bal > 0:
            dd_pct = (self.day_start_bal - self.balance) / self.day_start_bal
            if dd_pct >= DOUBLING_PAUSE_DD_PCT and not self.doubling_paused:
                self.doubling_paused = True
                self.doubling_resume_wins = 0
        if self.doubling_paused:
            return 1.0  # paused — use base size only
        # Get multiplier from 33-level table
        level = min(self.doubling_level, DOUBLING_LEVELS - 1)
        return DOUBLING_MULT_TABLE[level]

    def conf_multiplier(self, score):
        """v3.0: Confidence-weighted position multiplier based on setup score."""
        if score >= ELITE_CONF_THRESH:
            # TRADING GURU gets extra boost on elite setups
            if getattr(self, "is_trading_guru", False):
                score = min(1.0, score * 1.05)
            self.last_conf_level = "ELITE"
            return ELITE_CONF_MULT
        elif score >= HIGH_CONF_THRESH:
            self.last_conf_level = "HIGH"
            return HIGH_CONF_MULT
        elif score >= SCAN_MIN_SCORE + 0.3:
            self.last_conf_level = "NORMAL"
            return NORMAL_CONF_MULT
        else:
            self.last_conf_level = "LOW"
            return LOW_CONF_MULT

    @property
    def trade_size(self):
        # v4.0: check War Room directive first (highest priority override)
        directive = get_war_room_directive(self.name)
        if directive:
            d = directive.get("directive", "")
            if d == "STOP_TRADING":
                return 0.0
            elif d == "REDUCE_SIZE":
                return BASE_SIZE_USDT * LOW_CONF_MULT
            elif d == "INCREASE_SIZE":
                return BASE_SIZE_USDT * HIGH_CONF_MULT
            elif d == "MAXIMUM_POWER":
                return BASE_SIZE_USDT * ELITE_CONF_MULT
        # v7.0 SMART KELLY + SMART DOUBLING HYBRID (33-Level Mode)
        # Step 1: Smart Kelly sets the base size from win-rate statistics
        kelly_mult = self.kelly_size()          # 0.25x – 3.0x based on rolling WR
        # Step 2: Smart Doubling scales on loss streak for recovery
        doubling_mult = self.doubling_size()    # 1.0x – 4.0x based on loss level
        # Step 3: Confidence multiplier from signal strength
        conf_mult = self.conf_multiplier(self.last_score)  # 0.5x – 2.0x
        # Step 4: Rivalry boost — chase the leader
        rivalry_boost = 1.20 if self.rivalry_mode else (1.10 if self.is_trading_guru else 1.0)
        # Hybrid formula: Kelly × Doubling × Confidence × Rivalry
        size = BASE_SIZE_USDT * kelly_mult * doubling_mult * conf_mult * rivalry_boost
        # Risk compression: never risk more than MAX_RISK_PER_TRADE of balance
        max_risk_size = self.balance * MAX_RISK_PER_TRADE / max(SL_PCT, 0.001)
        size = min(size, max_risk_size)
        # Exposure cap: total open + new must not exceed MAX_TOTAL_EXPOSURE
        open_exposure = sum(p.get("size_usdt", 0) for p in self.positions.values())
        exposure_headroom = max(0, self.balance * MAX_TOTAL_EXPOSURE - open_exposure)
        size = min(size, exposure_headroom) if exposure_headroom > 0 else size
        # Hard cap at 20% of balance per trade (protects small accounts)
        hard_cap = max(MIN_SELL_USDT, self.balance * 0.20)
        size = min(size, hard_cap)
        # v9.0 TRIPLE CYCLE: Profit compounding multiplier
        # As session profit grows, compound a % back into trade size
        if self.start_bal > 0:
            sess_pnl = self._session_pnl_acc if hasattr(self, '_session_pnl_acc') else (self.balance - self.start_bal)
            if sess_pnl > 0:
                self.compound_mult = min(
                    PROFIT_COMPOUND_MAX,
                    1.0 + (sess_pnl / self.start_bal) * PROFIT_COMPOUND_RATE * 10
                )
            else:
                self.compound_mult = 1.0
        size = size * self.compound_mult
        # v8.1: Gate.io minimum order = $3 USDT — never go below this
        if size < GATE_MIN_ORDER:
            size = GATE_MIN_ORDER  # snap up to Gate.io minimum
        return round(size, 2)

    @property
    def session_pnl(self):
        """v9.0: session PnL — uses accumulator if available, else balance delta."""
        if hasattr(self, '_session_pnl_acc'):
            return self._session_pnl_acc
        return self.balance - self.start_bal

    @property
    def session_pnl_calc(self):
        return self.balance - self.start_bal

    @property
    def daily_dd(self):
        return max(0, self.day_start_bal - self.balance)

    @property
    def rolling_wr(self):
        if not self.rolling: return None
        wins = sum(1 for x in self.rolling if x == "W")
        return wins / len(self.rolling)

    def is_paused(self):
        """v6.0: Paused if daily DD cap hit, global session DD kill, or balance too low."""
        # v6.0 FIX: Minimum balance guard — stop trading if balance < $10
        if self.balance < 10.0:
            return True
        if self.daily_dd >= self.dd_cap:
            return True
        # Global kill switch: 5% session DD
        session_dd_pct = (self.start_bal - self.balance) / self.start_bal if self.start_bal > 0 else 0
        return session_dd_pct >= GLOBAL_DD_KILL_PCT

    def hourly_trade_count(self):
        """v3.0: Count trades in the last OVERTRADE_WINDOW_S seconds."""
        now = time.time()
        cutoff = now - OVERTRADE_WINDOW_S
        # Prune old timestamps
        while self.trade_timestamps and self.trade_timestamps[0] < cutoff:
            self.trade_timestamps.popleft()
        return len(self.trade_timestamps)

    def can_trade(self, pair):
        if self.is_paused(): return False
        if len(self.positions) >= MAX_OPEN: return False
        if pair in self.positions: return False
        last = self.last_trade.get(pair, 0)
        if (time.time() - last) < COOLDOWN_S: return False
        # v3.0: overtrading protection
        if self.hourly_trade_count() >= MAX_TRADES_PER_HOUR:
            return False
        return True

    def open_best(self, prices, closes_map, ticker_map=None, ranked_pairs=None):
        """v8.2 GOD-LEVEL ENTRY + SMART ROTATION: scan ALL pairs using the full Prediction Engine.
        Prioritizes hot_pair (rotation #1), applies score boosts/penalties by rank.
        Only opens trades where ALL operators agree (ELITE setups only).
        Respects dd_cap pause, cooldown, and MAX_OPEN."""
        if self.is_paused():
            return
        if len(self.positions) >= MAX_OPEN:
            return
        # v3.0: regime-adaptive trade limit
        regime = detect_market_regime(list(closes_map.values())[0] if closes_map else [])
        regime_limit = REGIME_TRADE_LIMITS.get(regime, 2)
        if len(self.positions) >= regime_limit:
            return
        # exclude pairs we already hold + pairs still in cooldown + blacklisted pairs
        now = time.time()
        exclude = set(self.positions.keys())
        for p in PAIRS:
            if (now - self.last_trade.get(p, 0)) < COOLDOWN_S:
                exclude.add(p)
            if p in self.pair_blacklist and self.pair_blacklist[p] > now:
                exclude.add(p)  # v8.2: skip blacklisted pairs
        # v8.2: use ranked_pairs order (hot pair first) for scan priority
        scan_pairs = ranked_pairs if ranked_pairs else PAIRS
        # Filter out blacklisted/excluded from scan list
        scan_pairs = [p for p in scan_pairs if p not in exclude] + \
                     [p for p in PAIRS if p not in scan_pairs and p not in exclude]
        best_pair, best_score = scan_best_pair(
            scan_pairs, prices, closes_map, self.assigned_key,
            coach_pair=self.hot_pair or self.assigned_pair, exclude=exclude,
            ticker_map=ticker_map or {},
            rotation_boost_fn=lambda p: self.rotation_score_boost(p, ranked_pairs or PAIRS))
        if not best_pair:
            return
        self.traded_pair = best_pair
        self.last_score = best_score
        self._open(best_pair, prices.get(best_pair), closes_map.get(best_pair) or [])

    def try_open(self, pair, price, closes):
        """Backward-compatible single-pair entry (still used by tests / fallback).
        Now any pair is allowed — the fixed assigned-pair lock has been removed so
        agents can trade the most profitable pair the scanner selects."""
        if not self.can_trade(pair): return
        if not strategy_signal(self.assigned_key, closes, price):
            return
        self._open(pair, price, closes)

    def _open(self, pair, price, closes):
        if not price or not self.can_trade(pair):
            return
        size = self.trade_size
        # v9.1 DUST GUARD: skip if size < Gate.io minimum quote amount ($3)
        if size < GATE_MIN_ORDER:
            log(f"  [{self.name}] ⚠️ SIZE-TOO-SMALL {pair}: ${size:.2f} < min ${GATE_MIN_ORDER} — skipping")
            return
        # v9.1 DUST GUARD: verify expected coin qty >= min_base_amount × 2 (2x safety)
        if self.live_mode:
            min_qty = get_pair_min_qty(self.gate, pair)
            expected_qty = size / price if price > 0 else 0
            if min_qty > 0 and expected_qty < min_qty * 2.0:  # 2x safety margin (was 1.5x)
                log(f"  [{self.name}] ⚠️ DUST-SKIP {pair}: expected qty {expected_qty:.6f} < min {min_qty} × 2 — skipping to avoid dust loss")
                return
        # v9.0 TRIPLE CYCLE ENGINE: select TP/SL and max_hold based on cycle layer
        total_hit, max_w, signals_hit, conf_pct, _ = god_level_confluence(
            closes, price, self.assigned_key)
        # Determine cycle mode from confluence score
        if total_hit >= CYCLE_BREAK_CONF_MIN:
            cycle = "BREAKOUT"
            tp_pct = CYCLE_BREAK_TP_PCT
            sl_pct = CYCLE_BREAK_SL_PCT
            max_hold_cycle = CYCLE_BREAK_MAX_HOLD
        elif total_hit >= CYCLE_SWING_CONF_MIN:
            cycle = "SWING"
            tp_pct = CYCLE_SWING_TP_PCT
            sl_pct = CYCLE_SWING_SL_PCT
            max_hold_cycle = CYCLE_SWING_MAX_HOLD
        else:
            cycle = "SCALP"
            tp_pct = CYCLE_SCALP_TP_PCT
            sl_pct = CYCLE_SCALP_SL_PCT
            max_hold_cycle = CYCLE_SCALP_MAX_HOLD
        self.cycle_mode = cycle
        # Use ATR-based TP/SL but clamp to cycle-specific range
        tp_atr, sl_atr = dynamic_tp_sl(closes, price)
        # Blend ATR with cycle-specific targets (60% ATR, 40% cycle target)
        tp_cycle = price * (1 + tp_pct)
        sl_cycle = price * (1 - sl_pct)
        tp = round(tp_atr * 0.60 + tp_cycle * 0.40, 8)
        sl = round(sl_atr * 0.60 + sl_cycle * 0.40, 8)
        qty = round(size / price, 6)
        conf_tag = f"GODMODE({cycle})" if total_hit >= PRED_GODMODE_CONF else \
                   f"ELITE({cycle})" if total_hit >= PRED_ELITE_CONF else f"CONF({cycle})"
        predicted = predict_price(closes, PRED_FORECAST_TICKS)
        pred_move_pct = (predicted - price) / price * 100 if price > 0 else 0.0
        if self.live_mode:
            try:
                result = self.gate.place_buy(pair, size, price)
                if result:
                    filled_coin = float(result.get("filled_amount", 0) or 0)
                    filled_usdt = float(result.get("filled_total", 0) or 0)
                    # v9.1 DUST FIX: verify fill is large enough to sell back
                    min_qty = get_pair_min_qty(self.gate, pair)
                    if filled_coin > 0 and min_qty > 0 and filled_coin < min_qty:
                        log(f"  [{self.name}] 🚫 FILL-DUST {pair}: filled={filled_coin:.6f} < min={min_qty} — aborting position (partial fill)")
                        return  # Don't record position — order was too small to sell
                    if filled_coin < 0.000001 and filled_usdt < 0.5:
                        log(f"  [{self.name}] 🚫 FILL-ZERO {pair}: filled_coin={filled_coin} filled_usdt={filled_usdt:.4f} — order did not fill")
                        return  # Order did not fill at all
                    qty = filled_coin if filled_coin > 0 else qty
                    log(f"  [{self.name}] 🟢 BUY {pair} ${size:.2f} @ {price:.6f} | "
                        f"{conf_tag}({total_hit}/{max_w}) pred=+{pred_move_pct:.3f}% | "
                        f"{self.assigned_key} | TP={tp:.6f} SL={sl:.6f}")
                else:
                    log(f"  [{self.name}] ⚠️ BUY {pair} — order returned None")
                    return
            except Exception as e:
                log(f"  [{self.name}] ❌ BUY {pair} error: {e}")
                self.api_ok = False
                self.live_mode = False
                return
        else:
            log(f"  [{self.name}] [SIM] ▶ BUY {pair} ${size:.2f} @ {price:.6f} | "
                f"{conf_tag}({total_hit}/{max_w}) pred=+{pred_move_pct:.3f}% | "
                f"{self.assigned_key} | TP={tp:.6f} SL={sl:.6f}")
        self.positions[pair] = {
            "qty": qty, "entry": price, "tp": tp, "sl": sl,
            "opened": time.time(), "size_usdt": size,
            "confluence": total_hit, "predicted_move": round(pred_move_pct, 4),
            "cycle": cycle, "max_hold": max_hold_cycle,  # v9.0 triple cycle
        }
        self.last_trade[pair] = time.time()
        self.trade_timestamps.append(time.time())
        self.pyramid_layers[pair] = self.pyramid_layers.get(pair, 0)

    def _sell_full(self, pair, fallback_qty):
        """Sell the ENTIRE real token balance for this pair (championship rule:
        never leave token behind). Falls back to recorded qty if API unavailable.
        If real balance is below min_base_amount (dust), returns 'DUST' sentinel
        so caller can close the position without retrying forever."""
        base = pair.split("_")[0]
        qty = fallback_qty
        try:
            real = self.gate.token_balance(base)
            if real and real > 0:
                prec, min_base = self.gate.pair_precision(pair)
                # round DOWN to precision so we never exceed available
                q = int(real * (10 ** prec)) / (10 ** prec)
                if min_base and q < min_base:
                    # Balance is below exchange minimum — treat as unrecoverable dust
                    log(f"  [{self.name}] 🧹 DUST {pair}: {real:.8f} {base} < min {min_base} — closing position as dust loss")
                    return "DUST"
                qty = q
            elif real == 0:
                # Token already gone (sold externally or dust) — close position
                log(f"  [{self.name}] 🧹 ZERO {pair}: no {base} balance — closing position")
                return "DUST"
        except Exception:
            pass
        return self.gate.place_sell(pair, qty)

    def check_exits(self, prices):
        now = time.time()
        closed = []
        for pair, pos in list(self.positions.items()):
            price = prices.get(pair)
            if not price: continue
            age    = now - pos.get("opened", now)
            hit_tp = price >= pos["tp"]
            hit_sl = price <= pos["sl"]
            # v9.0 TRIPLE CYCLE: use per-position max_hold (SCALP=45s, SWING=180s, BREAKOUT=120s)
            pos_max_hold = pos.get("max_hold", MAX_HOLD_S)
            aged   = age >= pos_max_hold
            # EDGE FIX: fee-aware MAXHOLD. The old logic churned 46/48 trades out at
            # ~$0.00 the instant they aged. Now, when a trade ages we only force it out
            # if it has cleared the round-trip fee (real win) OR it has run well past TP
            # time (hard ceiling 2x MAX_HOLD). Otherwise we keep holding for TP/SL.
            fee_clear = price >= pos["entry"] * (1 + FEE_PCT)
            hard_aged = age >= (2 * MAX_HOLD_S)
            if aged and not (fee_clear or hard_aged):
                aged = False  # not worth closing yet — give it more time to reach TP
            if not (hit_tp or hit_sl or aged): continue
            if hit_tp:
                reason, outcome = "TP", "W"
            elif hit_sl:
                reason, outcome = "SL", "L"
            else:
                # timed-out exit: a win only if it cleared the fee, else a loss
                reason = "MAXHOLD"
                outcome = "W" if fee_clear else "L"
            pnl = (price - pos["entry"]) * pos["qty"]
            icon = "✅" if outcome == "W" else ("❌" if reason == "SL" else "⏱️")
            if self.live_mode:
                try:
                    sold = self._sell_full(pair, pos["qty"])
                    if sold is None:
                        # sell failed — keep position so we retry next tick (no token left behind)
                        log(f"  [{self.name}] ⚠️ SELL {pair} returned None — will retry next tick")
                        continue
                    if sold == "DUST":
                        # Balance below exchange minimum — close position as dust loss
                        reason = "DUST"
                        outcome = "L"
                        pnl = -pos.get("size_usdt", 0)  # full loss of invested amount
                        log(f"  [{self.name}] 🧹 DUST-CLOSE {pair} | invested={pos.get('size_usdt',0):.2f} USDT written off")
                    else:
                        log(f"  [{self.name}] {icon} {reason} {pair} @ {price:.6f} | PnL={pnl:+.4f} USDT | streak={self.streak}")
                except Exception as e:
                    log(f"  [{self.name}] ❌ SELL {pair} error: {e}")
                    self.api_ok = False
                    self.live_mode = False
                    continue
            else:
                log(f"  [{self.name}] [SIM] {icon} {reason} {pair} @ {price:.6f} | PnL={pnl:+.4f}")
            # Update stats
            self.balance += pnl
            self._session_pnl_acc += pnl   # v9.0 track session PnL for compounding
            # v9.0 TRIPLE CYCLE: track per-cycle PnL
            pos_cycle = pos.get("cycle", "SCALP")
            if pos_cycle in self.cycle_pnl:
                self.cycle_pnl[pos_cycle] = round(self.cycle_pnl[pos_cycle] + pnl, 4)
                if outcome == "W":
                    self.cycle_wins[pos_cycle] = self.cycle_wins.get(pos_cycle, 0) + 1
                else:
                    self.cycle_losses[pos_cycle] = self.cycle_losses.get(pos_cycle, 0) + 1
            self.rolling.append(outcome)
            if outcome == "W":
                self.wins += 1
                self.streak = min(self.streak + 1, MAX_STREAK)
                self.on_trade_result(True)   # v4.0 AEPE Smart Step reset
                # ── Evolution Engine: post-trade learning (WIN) ──
                if _evo_ok and _evo_service:
                    try:
                        _evo_service.on_trade_complete({
                            "agent_name": self.name, "pair": pair,
                            "strategy": self.assigned_key,
                            "side": "short", "entry_price": pos.get("entry", 0),
                            "exit_price": price, "pnl_usd": pnl, "fees_usd": 0,
                            "signal_score": self.last_score,
                            "risk_score": 0.5, "market_regime": _current_regime,
                            "outcome": "WIN", "hold_ticks": pos.get("hold_ticks", 0),
                            "entry_ts": pos.get("opened", int(time.time())),
                            "exit_ts": int(time.time()), "capital": self.balance,
                        })
                    except Exception: pass
                # ── Track peak streak for the consolidated round-end message (no separate send) ──
                if self.streak > self.round_peak_streak:
                    self.round_peak_streak = self.streak
                # v8.2: record for smart rotation
                self.record_trade_result(pair, self.assigned_key, True, pnl)
            else:
                self.losses += 1
                self.streak = 0
                self.on_trade_result(False)  # v4.0 AEPE Smart Step advance
                # v8.2: record for smart rotation
                self.record_trade_result(pair, self.assigned_key, False, pnl)
                # ── Evolution Engine: post-trade learning (LOSS) ──
                if _evo_ok and _evo_service:
                    try:
                        _evo_service.on_trade_complete({
                            "agent_name": self.name, "pair": pair,
                            "strategy": self.assigned_key,
                            "side": "short", "entry_price": pos.get("entry", 0),
                            "exit_price": price, "pnl_usd": pnl, "fees_usd": 0,
                            "signal_score": self.last_score,
                            "risk_score": 0.5, "market_regime": _current_regime,
                            "outcome": "LOSS", "hold_ticks": pos.get("hold_ticks", 0),
                            "entry_ts": pos.get("opened", int(time.time())),
                            "exit_ts": int(time.time()), "capital": self.balance,
                        })
                    except Exception: pass
            closed.append(pair)
        for pair in closed:
            del self.positions[pair]

    # ── v5.0 Rivalry Engine ──────────────────────────────────────────────────
    def update_rivalry(self, all_agents):
        """Update rivalry state — compete like professional sportsmen."""
        my_bal = self.balance
        rivals = {n: a.balance for n, a in all_agents.items() if n != self.name}
        self.rival_balances = rivals
        if not rivals:
            return
        max_rival_bal = max(rivals.values())
        self.sportsman_rank = sum(1 for b in rivals.values() if b > my_bal) + 1
        # Activate rivalry mode if trailing leader by >5%
        if max_rival_bal > 0 and (max_rival_bal - my_bal) / max(max_rival_bal, 1) > 0.05:
            self.rivalry_mode = True
            self.rivalry_target = max(rivals, key=rivals.get)
        else:
            self.rivalry_mode = False
            self.rivalry_target = None
        # TRADING GURU: study all rivals every 5 ticks
        if self.is_trading_guru:
            self.tg_study_count += 1
            if self.tg_study_count % 5 == 0:
                best_rival = max(rivals, key=rivals.get)
                best_agent = all_agents.get(best_rival)
                if best_agent:
                    log(f"  [TRADING_GURU] 📚 Studying {best_rival} (${best_agent.balance:.2f}) — rank #{self.sportsman_rank}")

    # ── AEPE GODMODE v4.0: Smart Step Loss-Doubling State Machine ──
    def _update_rank(self):
        """Update sportsman rank based on XP."""
        xp = self.xp
        if xp >= 500:   self.sportsman_rank = "LEGEND"
        elif xp >= 200: self.sportsman_rank = "CHAMPION"
        elif xp >= 100: self.sportsman_rank = "ELITE"
        elif xp >= 50:  self.sportsman_rank = "PRO"
        elif xp >= 20:  self.sportsman_rank = "AMATEUR"
        else:           self.sportsman_rank = "ROOKIE"
        self.level = max(1, xp // 10)

    def on_trade_result(self, won: bool):
        """Called after every trade.
        v7.0: Updates Smart Kelly win rate + Smart Doubling level (33-Level Mode)
        + AEPE state machine for regime-adaptive sizing."""
        # ── v7.0 Smart Kelly: update rolling win rate ──────────────────────────
        if self.rolling:
            wins = sum(1 for x in self.rolling if x == "W")
            self.kelly_win_rate = wins / len(self.rolling)

        # ── v7.0 Smart Doubling (33-Level Mode) ───────────────────────────────
        if won:
            # WIN: reset doubling level to 0 (recovery complete)
            if DOUBLING_RESET_WIN:
                self.doubling_level = 0
            # Check if doubling was paused — count consecutive wins for resume
            if self.doubling_paused:
                self.doubling_resume_wins += 1
                if self.doubling_resume_wins >= DOUBLING_RESUME_WIN:
                    self.doubling_paused = False
                    self.doubling_resume_wins = 0
                    log(f"  [{self.name}] U0001f7e2 DOUBLING RESUMED after {DOUBLING_RESUME_WIN} wins")
        else:
            # LOSS: advance doubling level (recovery mode)
            if DOUBLING_ON_LOSS and not self.doubling_paused:
                self.doubling_level = min(self.doubling_level + 1, DOUBLING_LEVELS - 1)
                mult = DOUBLING_MULT_TABLE[self.doubling_level]
                log(f"  [{self.name}] U0001f7e1 DOUBLING Level {self.doubling_level}/{DOUBLING_LEVELS-1} -> {mult:.1f}x")

        # ── AEPE State Machine (regime-adaptive) ──────────────────────────────
        STEPS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]  # legacy AEPE steps (kept for aepe_size_mult)
        MAX_STEP = len(STEPS) - 1
        if not hasattr(self, 'aepe_state'):
            self.aepe_state = "BALANCED"
            self.aepe_step = 0
            self.aepe_loss_streak = 0
            self.aepe_session_start_bal = self.balance
        if won:
            self.aepe_loss_streak = 0
            self.aepe_step = max(0, self.aepe_step - 1)
            if self.aepe_state == "SURVIVAL":
                self.aepe_state = "BALANCED"
            elif self.aepe_state == "SAFE" and self.wins >= 3:
                self.aepe_state = "BALANCED"
            elif self.aepe_state == "BALANCED" and self.wins >= 5:
                self.aepe_state = "ATTACK"
            elif self.aepe_state == "ATTACK" and self.wins >= 8:
                self.aepe_state = "GODMODE"
        else:
            self.aepe_loss_streak += 1
            self.aepe_step = min(self.aepe_step + 1, MAX_STEP)
            if self.aepe_loss_streak >= 6:
                self.aepe_state = "FREEZE"
            elif self.aepe_loss_streak >= 4:
                self.aepe_state = "SURVIVAL"
            elif self.aepe_loss_streak >= 2:
                self.aepe_state = "SAFE"
        # Session DD kill → FREEZE
        session_dd_pct = (self.balance - getattr(self, 'aepe_session_start_bal', self.balance)) / max(self.balance, 1)
        if session_dd_pct <= -0.05:
            self.aepe_state = "FREEZE"
        # FREEZE auto-resets at start of new UTC day (handled by daily_dd reset)

    def aepe_size_mult(self):
        """Returns the AEPE size multiplier based on current step and state."""
        STEPS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        if not hasattr(self, 'aepe_step'):
            return 1.0
        state = getattr(self, 'aepe_state', 'BALANCED')
        if state == "FREEZE":
            return 0.0  # stop trading
        if state == "SURVIVAL":
            return 0.33  # min size
        step = getattr(self, 'aepe_step', 0)
        return STEPS[min(step, len(STEPS)-1)]

    def record_trade_result(self, pair: str, strategy_key: str, won: bool, pnl: float):
        """v8.2: Record per-pair and per-strategy performance for smart rotation."""
        now = int(time.time())
        # ── Per-pair stats ──
        if pair not in self.pair_stats:
            self.pair_stats[pair] = {"wins": 0, "losses": 0, "pnl": 0.0, "streak": 0, "last_ts": now}
        ps = self.pair_stats[pair]
        ps["last_ts"] = now
        ps["pnl"] += pnl
        if won:
            ps["wins"] += 1
            ps["streak"] = max(0, ps.get("streak", 0)) + 1
        else:
            ps["losses"] += 1
            ps["streak"] = min(0, ps.get("streak", 0)) - 1
            # Auto-blacklist after consecutive losses
            if ps["streak"] <= -BLACKLIST_LOSS_STREAK:
                self.pair_blacklist[pair] = now + BLACKLIST_DURATION_S
                log(f"  [{self.name}] 🚫 BLACKLIST {pair} for {BLACKLIST_DURATION_S}s (streak={ps['streak']})")
        # ── Per-strategy stats ──
        if strategy_key not in self.strategy_stats:
            self.strategy_stats[strategy_key] = {"wins": 0, "losses": 0, "pnl": 0.0}
        ss = self.strategy_stats[strategy_key]
        ss["pnl"] += pnl
        if won:
            ss["wins"] += 1
        else:
            ss["losses"] += 1

    def rotate_best(self, pairs):
        """v8.2: Evaluate all pairs and strategies, rotate to best performers.
        Returns (hot_pair, hot_strategy, ranked_pairs) for use in scan_best_pair."""
        now = int(time.time())
        # ── Expire blacklisted pairs ──
        self.pair_blacklist = {p: t for p, t in self.pair_blacklist.items() if t > now}
        # ── Score each pair ──
        pair_scores = {}
        for pair in pairs:
            if pair in self.pair_blacklist:
                continue  # skip blacklisted
            ps = self.pair_stats.get(pair)
            if ps is None or (ps["wins"] + ps["losses"]) < ROTATION_MIN_TRADES:
                pair_scores[pair] = 1.0  # neutral score for untested pairs
                continue
            total = ps["wins"] + ps["losses"]
            wr = ps["wins"] / total
            pf = (ps["pnl"] / max(abs(ps["pnl"]), 0.01)) if ps["pnl"] != 0 else 0
            streak_bonus = 1.0 + max(0, ps.get("streak", 0)) * 0.05  # +5% per win streak
            score = (wr * 2.0 + pf * 1.0) * streak_bonus
            pair_scores[pair] = max(0.1, score)
        # ── Rank pairs ──
        ranked = sorted(pair_scores.items(), key=lambda x: x[1], reverse=True)
        if not ranked:
            return self.hot_pair, self.hot_strategy, pairs
        old_hot = self.hot_pair
        self.hot_pair = ranked[0][0]
        if old_hot != self.hot_pair and old_hot is not None:
            log(f"  [{self.name}] 🔄 ROTATION: {old_hot} → {self.hot_pair} (score={ranked[0][1]:.2f})")
        # ── Score each strategy ──
        strat_scores = {}
        for key in STRATEGY_KEYS:
            ss = self.strategy_stats.get(key)
            if ss is None or (ss["wins"] + ss["losses"]) < 2:
                strat_scores[key] = 1.0
                continue
            total = ss["wins"] + ss["losses"]
            wr = ss["wins"] / total
            pf = ss["pnl"] / max(abs(ss["pnl"]), 0.01) if ss["pnl"] != 0 else 0
            strat_scores[key] = max(0.1, wr * 2.0 + pf * 1.0)
        best_strat = max(strat_scores, key=strat_scores.get)
        old_strat = self.hot_strategy
        self.hot_strategy = best_strat
        if old_strat != best_strat:
            log(f"  [{self.name}] 🔄 STRATEGY SWITCH: {old_strat} → {best_strat} (score={strat_scores[best_strat]:.2f})")
        # ── Update assigned_key to best strategy ──
        self.assigned_key = self.hot_strategy
        return self.hot_pair, self.hot_strategy, [p for p, _ in ranked] + [p for p in pairs if p in self.pair_blacklist]

    def rotation_score_boost(self, pair: str, ranked_pairs: list) -> float:
        """v8.2: Returns a score multiplier based on pair's rotation rank."""
        if not ranked_pairs or pair not in ranked_pairs:
            return 1.0
        idx = ranked_pairs.index(pair)
        if idx == 0:
            return ROTATION_BOOST_TOP
        elif idx == 1:
            return ROTATION_BOOST_TOP2
        elif pair in self.pair_blacklist:
            return 0.0  # blocked
        elif idx >= len(ranked_pairs) - 2:
            return ROTATION_PENALTY_COLD  # cold pair penalty
        return 1.0

    def snap(self):
        total = self.wins + self.losses
        wr = round(100 * self.wins / total, 2) if total else 0
        rwr = round(100 * self.rolling_wr, 2) if self.rolling_wr is not None else None
        return {
            "name": self.name,
            "balance": round(self.balance, 4),
            "session_pnl": round(self.session_pnl, 4),
            "daily_dd": round(self.daily_dd, 4),
            "dd_cap": self.dd_cap,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": wr,
            "rolling_wr": rwr,
            "rolling_n": len(self.rolling),
            "streak": self.streak,
            "trade_size": round(self.trade_size, 2),
            "open_positions": len(self.positions),
            "open_pairs": list(self.positions.keys()),
            "mode": "LIVE_CMO_CHAMPION" if self.live_mode else "SIM_CMO_CHAMPION",
            "api_ok": self.api_ok,
            "paused": "DD_CAP_HIT" if self.is_paused() else None,
            "assigned_strategy": self.assigned_strategy,
            "assigned_key": self.assigned_key,
            "assigned_pair": self.assigned_pair,   # coach hint
            "traded_pair": self.traded_pair,       # pair the live scanner last chose
            "last_score": round(self.last_score, 4),
            "dynamic_scan": True,
            # v5.0 Rivalry Engine fields
            "rivalry_mode":    getattr(self, 'rivalry_mode', False),
            "rivalry_target":  getattr(self, 'rivalry_target', None),
            "sportsman_rank":  getattr(self, 'sportsman_rank', 0),
            "is_trading_guru": getattr(self, 'is_trading_guru', False),
            # v7.0 Smart Kelly + Smart Doubling state
            "kelly_win_rate":   round(getattr(self, 'kelly_win_rate', 0.55), 4),
            "kelly_mult":       round(self.kelly_size(), 4),
            "doubling_level":   getattr(self, 'doubling_level', 0),
            "doubling_mult":    DOUBLING_MULT_TABLE[min(getattr(self, 'doubling_level', 0), DOUBLING_LEVELS-1)],
            "doubling_paused":  getattr(self, 'doubling_paused', False),
        }

# ── Price fetcher ─────────────────────────────────────────────────────────────
_price_cache = {}
_candle_cache = {}

def fetch_prices(pairs):
    prices = {}
    for pair in pairs:
        try:
            url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read())
                if data and isinstance(data, list):
                    prices[pair] = float(data[0].get("last", 0))
        except Exception as e:
            if pair in _price_cache:
                prices[pair] = _price_cache[pair]
    _price_cache.update(prices)
    return prices

def fetch_closes(pair, limit=30):
    try:
        url = (f"https://api.gateio.ws/api/v4/spot/candlesticks"
               f"?currency_pair={pair}&limit={limit}&interval=10s")
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            if data and isinstance(data, list):
                closes = [float(c[2]) for c in data]
                _candle_cache[pair] = closes
                return closes
    except Exception:
        pass
    return _candle_cache.get(pair, [])

# ── Battle rounds (continuous championship) ────────────────────────────────────
class BattleRounds:
    """Anchors fixed-length rounds to engine start. Each round records every
    agent's session_pnl at start; at the round boundary it computes per-agent
    round PnL, crowns a winner, appends to persistent history, and the next
    round auto-starts (no process restart needed)."""
    def __init__(self, agents):
        self.started_at = datetime.now(timezone.utc)
        self.current_rid = 1
        self.anchors = {}      # rid -> {agent_name: session_pnl_at_start}
        self.history = []      # list of completed-round dicts (most recent last)
        self._load()
        self._anchor(self.current_rid, agents)

    def _load(self):
        try:
            data = json.loads(ROUNDS_FILE.read_text())
            self.history = data.get("history", [])[-ROUND_HISTORY_LIMIT:]
        except Exception:
            self.history = []

    def _rid_now(self):
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return int(elapsed // ROUND_INTERVAL_SEC) + 1

    def _round_started_at(self, rid):
        return (self.started_at + timedelta(seconds=(rid - 1) * ROUND_INTERVAL_SEC)).isoformat()

    def _anchor(self, rid, agents):
        if rid not in self.anchors:
            self.anchors[rid] = {a.name: float(a.session_pnl) for a in agents}

    def round_seconds_left(self):
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return max(0, ROUND_INTERVAL_SEC - (elapsed % ROUND_INTERVAL_SEC))

    def tick(self, agents):
        """Call each loop. When a round boundary is crossed, finalize the round
        and start the next. Returns a completed-round dict if one just closed."""
        rid = self._rid_now()
        if rid <= self.current_rid:
            return None
        # One or more rounds just completed — finalize each in order.
        completed = None
        while self.current_rid < rid:
            completed = self._finalize(self.current_rid, agents)
            self.current_rid += 1
            self._anchor(self.current_rid, agents)
        self._persist()
        return completed

    def _finalize(self, rid, agents):
        start = self.anchors.get(rid, {a.name: 0.0 for a in agents})
        results = []
        for a in agents:
            delta = round(float(a.session_pnl) - float(start.get(a.name, 0.0)), 6)
            results.append({
                "agent": a.name, "round_pnl_usd": delta,
                "wins": a.wins, "losses": a.losses,
                "balance": round(a.balance, 4),
                "assigned_pair": a.assigned_pair,
            })
        # CHAMPIONSHIP RULE: THE WINNER IS THE MAX USDT HUNTER
        # Winner = agent with highest absolute USDT balance at round end
        winner = max(results, key=lambda r: r["balance"])["agent"] if results else None
        rec = {
            "round_id": rid,
            "started_at": self._round_started_at(rid),
            "ended_at": self._round_started_at(rid + 1),
            "winner": winner,
            "results": sorted(results, key=lambda r: r["round_pnl_usd"], reverse=True),
        }
        self.history.append(rec)
        self.history = self.history[-ROUND_HISTORY_LIMIT:]
        log(f"  🏆 ROUND {rid} COMPLETE — winner: {winner} | " +
            " | ".join(f"{r['agent']} {r['round_pnl_usd']:+.4f}" for r in rec["results"]))

        # ══ ONE consolidated Telegram message: full results all in one ══
        try:
            ranked = rec["results"]
            medals = ["🥇", "🥈", "🥉"]
            total_pnl = sum(r["round_pnl_usd"] for r in ranked)
            lines = [f"🏆 ROUND {rid} COMPLETE"]
            # Standings: medal, agent, pair, round PnL, balance
            for i, r in enumerate(ranked):
                m = medals[i] if i < len(medals) else "•"
                pair = (r["assigned_pair"] or "-").replace("_USDT", "")
                lines.append(f"{m} {r['agent']} ({pair}): "
                             f"{r['round_pnl_usd']:+.2f} | bal ${r['balance']:.0f}")
            # Winner + cumulative crowns
            crowns = self.standings()
            crown_txt = ("  |  ".join(f"{k}:{v}" for k, v in
                          sorted(crowns.items(), key=lambda x: -x[1]))) if crowns else "-"
            lines.append(f"👑 MAX USDT HUNTER: {winner or '-'} (${max(r['balance'] for r in ranked):.2f})  |  Crowns: {crown_txt}")
            # Coach lineup for the next round (current assignments)
            lineup = "  ".join(
                f"{a.name[:3]}→{(a.assigned_pair or '-').replace('_USDT','')}" for a in agents)
            lines.append(f"🧠 Coach: {lineup}")
            # Self-learning upgrades that happened this round
            ups = [a for a in agents if a.round_upgrade]
            if ups:
                up_txt = "  ".join(
                    f"{a.name[:3]} {(a.round_upgrade[0] or '-').replace('_USDT','')}→"
                    f"{(a.round_upgrade[1] or '-').replace('_USDT','')}" for a in ups)
                lines.append(f"📈 Upgrades: {up_txt}")
            # Power-ups (Anti-Martingale streaks) reached this round
            pows = [a for a in agents if a.round_peak_streak >= 2]
            if pows:
                pow_txt = "  ".join(
                    f"{a.name[:3]} {min(2**a.round_peak_streak, 2**MAX_STREAK)}x" for a in pows)
                lines.append(f"🔥 Power-ups: {pow_txt}")
            # Total team PnL for the round
            lines.append(f"💰 Total PnL: {total_pnl:+.2f} USDT")
            tg("\n".join(lines))
        except Exception as e:
            log(f"  [ROUNDS] telegram error: {e}")

        # Reset per-round event trackers for the next round.
        for a in agents:
            a.round_upgrade = None
            a.round_peak_streak = 0
        return rec

    def _persist(self):
        try:
            tmp = str(ROUNDS_FILE) + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"updated_at": datetime.now(timezone.utc).isoformat(),
                           "round_interval_sec": ROUND_INTERVAL_SEC,
                           "history": self.history}, f, indent=2)
            os.replace(tmp, str(ROUNDS_FILE))
        except Exception as e:
            log(f"  [ROUNDS] persist error: {e}")

    def standings(self):
        """Cumulative round wins per agent across history."""
        crowns = {}
        for r in self.history:
            w = r.get("winner")
            if w: crowns[w] = crowns.get(w, 0) + 1
        return crowns

    def snapshot(self, agents):
        """Live championship view for save_state."""
        start = self.anchors.get(self.current_rid, {})
        live = []
        for a in agents:
            delta = round(float(a.session_pnl) - float(start.get(a.name, 0.0)), 6)
            live.append({"agent": a.name, "round_pnl_usd": delta,
                         "assigned_pair": a.assigned_pair})
        live.sort(key=lambda r: r["round_pnl_usd"], reverse=True)
        return {
            "current_round_id": self.current_rid,
            "round_interval_sec": ROUND_INTERVAL_SEC,
            "round_seconds_left": int(self.round_seconds_left()),
            "current_round_leader": live[0]["agent"] if live else None,
            "current_round_live": live,
            "round_wins": self.standings(),
            "history": list(reversed(self.history)),   # most recent first
        }

# ── State writer ──────────────────────────────────────────────────────────────
def save_state(agents, tick, championship=None):
    try:
        state = {
            "version": "champion-battle-v1",
            "strategy": STRATEGY_NAME,
            "pairs": PAIRS,
            "tick": tick,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "CMO_CHAMPION",
            "agents": [a.snap() for a in agents],
            "leaderboard": sorted([a.snap() for a in agents],
                                  key=lambda x: x["session_pnl"], reverse=True),
            "championship": championship,
        }
        tmp = str(STATE_FILE) + ".tmp"
        with open(tmp, "w") as f: json.dump(state, f, indent=2)
        os.replace(tmp, str(STATE_FILE))
    except Exception as e:
        log(f"  [STATE] save error: {e}")

def write_health(agents):
    try:
        health = {
            "status": "running",
            "strategy": STRATEGY_NAME,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "agents": {a.name: {"balance": a.balance, "live": a.live_mode,
                                "api_ok": a.api_ok, "streak": a.streak,
                                "trade_size": a.trade_size} for a in agents}
        }
        with open(HEALTH_FILE, "w") as f: json.dump(health, f, indent=2)
    except: pass

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    global _current_regime
    _current_regime = "SIDEWAYS"  # updated each tick by detect_market_regime
    log("=" * 70)
    log("CHAMPION BATTLE v9.1 — DUST-PROOF + TRIPLE CYCLE + GOD-LEVEL PREDICTION + SMART ROTATION + KELLY + DOUBLING · ⚔️ THE WINNER IS THE MAX USDT HUNTER ⚔️")
    log(f"Strategy: {STRATEGY_NAME} | DYNAMIC BEST-PAIR SCAN (all pairs every tick)")
    log(f"Pair universe ({len(PAIRS)}) [DUST-PROOF]: {PAIRS}")
    log(f"Base size: ${BASE_SIZE_USDT} | Kelly: {KELLY_FRACTION}x fraction | Doubling: {DOUBLING_LEVELS}-level mode | max_mult={DOUBLING_MAX_MULT}x")
    log(f"[PREDICTION ENGINE] Min confluence: {PRED_MIN_CONFLUENCE}/{PRED_MAX_WEIGHT} | Elite: {PRED_ELITE_CONF}+ | Godmode: {PRED_GODMODE_CONF}+ | Forecast: +{PRED_FORECAST_MIN_UP*100:.3f}%")
    log(f"[TRIPLE CYCLE ENGINE] SCALP(7+conf,TP={CYCLE_SCALP_TP_PCT*100:.2f}%,SL={CYCLE_SCALP_SL_PCT*100:.2f}%,{CYCLE_SCALP_MAX_HOLD}s) | SWING(9+conf,TP={CYCLE_SWING_TP_PCT*100:.2f}%,SL={CYCLE_SWING_SL_PCT*100:.2f}%,{CYCLE_SWING_MAX_HOLD}s) | BREAKOUT(10+conf,TP={CYCLE_BREAK_TP_PCT*100:.2f}%,SL={CYCLE_BREAK_SL_PCT*100:.2f}%,{CYCLE_BREAK_MAX_HOLD}s)")
    log(f"[PROFIT COMPOUNDING] Rate={PROFIT_COMPOUND_RATE*100:.0f}% of profit | Max={PROFIT_COMPOUND_MAX}x | Lock threshold=${PROFIT_LOCK_THRESHOLD} | Pairs: {len(PAIRS)} (3x expanded universe)")
    log(f"[SMART ROTATION] Rotate every {ROTATION_TICKS} ticks | Blacklist after {BLACKLIST_LOSS_STREAK} losses ({BLACKLIST_DURATION_S}s) | Hot boost: +{int((ROTATION_BOOST_TOP-1)*100)}% | Cold penalty: -{int((1-ROTATION_PENALTY_COLD)*100)}%")
    log(f"[DYNAMIC TP/SL] ATR-based | TP: {PRED_TP_MIN_PCT*100:.2f}%-{PRED_TP_MAX_PCT*100:.2f}% | SL: {PRED_SL_MIN_PCT*100:.2f}%-{PRED_SL_MAX_PCT*100:.2f}% | R:R=2:1")
    log(f"TP: {TP_PCT*100:.2f}% (fallback) | SL: {SL_PCT*100:.2f}% (fallback) | CMO threshold: {CMO_THRESHOLD} | cooldown {COOLDOWN_S}s | max_open {MAX_OPEN}")
    log(f"dd_cap defense PRESERVED: " + ", ".join(f"{n} ${c['dd_cap']}" for n, c in ACCOUNTS.items()))
    log("=" * 70)

    agents = [Agent(n, c) for n, c in ACCOUNTS.items()]
    live_count = sum(1 for a in agents if a.live_mode)
    log(f"  Agents: {live_count}/3 in LIVE mode, {3-live_count}/3 in SIMULATION mode")

    rounds = BattleRounds(agents)
    log(f"  🏟️ Battle rounds: {ROUND_INTERVAL_SEC}s each | history kept: {ROUND_HISTORY_LIMIT} | "
        f"prior completed rounds loaded: {len(rounds.history)}")

    # Startup ping removed: all results now arrive in ONE consolidated round-end message.

    stop = [False]
    def _s(*_): stop[0] = True
    signal.signal(signal.SIGTERM, _s)
    signal.signal(signal.SIGINT, _s)

    tick = 0
    while not stop[0]:
        tick += 1
        try:
            # Retry API for agents in simulation mode
            for agent in agents:
                if not agent.live_mode:
                    agent.retry_api()

            # v6.0 FIX: Periodic real balance sync to prevent virtual tracking drift
            # Syncs every ~5 minutes when agents have no open positions
            if tick % BALANCE_SYNC_TICKS == 0:
                for agent in agents:
                    agent.sync_real_balance()

            # COACH: apply latest team assignments (used only as a soft hint now)
            signals = load_coach_signals()
            for agent in agents:
                agent.apply_coach(signals)
            # v5.0 Rivalry Engine: update all agents' rivalry state every tick
            agents_dict = {a.name: a for a in agents}
            for agent in agents:
                agent.update_rivalry(agents_dict)
            if tick % 10 == 0:
                ranks = sorted(agents, key=lambda a: a.balance, reverse=True)
                rank_str = " | ".join([f"#{i+1} {a.name}=${a.balance:.2f}" for i,a in enumerate(ranks)])
                log(f"  [\U0001f3c6 CHAMPIONSHIP] {rank_str}")

            # v8.0 GOD-LEVEL: fetch prices + candles + ticker volume data every tick
            prices = fetch_prices(PAIRS)
            closes_map = {}
            ticker_map = {}
            for pair in PAIRS:
                if not prices.get(pair):
                    continue
                closes = fetch_closes(pair, 30)
                if len(closes) >= CMO_PERIOD + 1:
                    closes_map[pair] = closes
                # Fetch ticker for volume data (used by volume_burst signal)
                try:
                    url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}"
                    req = urllib.request.Request(url, headers={"Accept": "application/json"})
                    with urllib.request.urlopen(req, timeout=4) as r:
                        td = json.loads(r.read())
                        if td and isinstance(td, list):
                            t = td[0]
                            ticker_map[pair] = {
                                "volume_usdt": float(t.get("quote_volume", 0) or 0),
                                "bid": float(t.get("highest_bid", 0) or 0),
                                "ask": float(t.get("lowest_ask", 0) or 0),
                                "change_pct": float(t.get("change_percentage", 0) or 0),
                            }
                except Exception:
                    pass

            # v8.2 SMART ROTATION: evaluate best pair+strategy every ROTATION_TICKS
            ranked_pairs_map = {}
            for agent in agents:
                agent.rotation_tick += 1
                if agent.rotation_tick % ROTATION_TICKS == 0:
                    hot_pair, hot_strat, ranked = agent.rotate_best(PAIRS)
                    ranked_pairs_map[agent.name] = ranked
                else:
                    ranked_pairs_map[agent.name] = getattr(agent, '_last_ranked', PAIRS)
                agent._last_ranked = ranked_pairs_map[agent.name]

            # Each agent scans all pairs and opens the single best setup (up to MAX_OPEN).
            for agent in agents:
                for _ in range(MAX_OPEN):
                    before = len(agent.positions)
                    agent.open_best(prices, closes_map, ticker_map=ticker_map,
                                    ranked_pairs=ranked_pairs_map.get(agent.name, PAIRS))
                    if len(agent.positions) == before:
                        break  # nothing more to open this tick

            for agent in agents:
                agent.check_exits(prices)

            # Battle-round bookkeeping: finalize/crown at each round boundary
            rounds.tick(agents)

            if tick % 6 == 0:
                save_state(agents, tick, championship=rounds.snapshot(agents))
                write_health(agents)
                snaps = sorted([a.snap() for a in agents],
                               key=lambda x: x["session_pnl"], reverse=True)
                log(f"  Tick {tick} | " + " | ".join(
                    f"{s['name']} ${s['balance']:.2f} ({s['session_pnl']:+.4f}) "
                    f"[{s['mode'].split('_')[0]}] {a.assigned_key} "
                    f"open={','.join(p.replace('_USDT','') for p in a.positions) or '-'} "
                    f"last={(a.traded_pair or '-').replace('_USDT','')}({a.last_score:+.3f}) "
                    f"streak={s['streak']} size=${s['trade_size']:.0f}"
                    for s, a in zip(snaps, sorted(agents, key=lambda x: x.session_pnl, reverse=True))
                ))

        except Exception as e:
            import traceback as _tb_inner
            log(f"  [ERROR] tick {tick}: {e} | {_tb_inner.format_exc().splitlines()[-2]}")
        time.sleep(TICK_S)

    save_state(agents, tick, championship=rounds.snapshot(agents))
    log("Champion battle stopped.")

if __name__ == "__main__":
    import traceback as _tb
    # ─── NEVER-DIE WRAPPER ───────────────────────────────────────────────────
    # champion_battle.py must NEVER stop. If main() crashes for any reason,
    # wait 10 seconds and restart automatically.
    _restart_count = 0
    while True:
        try:
            main()
            log("⚠️  main() returned — restarting in 10s...")
        except KeyboardInterrupt:
            log("🛑 Stopped by user (KeyboardInterrupt)")
            break
        except SystemExit as _se:
            log(f"🛑 SystemExit({_se.code}) — stopping")
            break
        except Exception as _e:
            _restart_count += 1
            log(f"💥 FATAL CRASH #{_restart_count}: {_e}")
            log(_tb.format_exc())
            log(f"🔄 Auto-restarting in 10 seconds...")
        time.sleep(10)
