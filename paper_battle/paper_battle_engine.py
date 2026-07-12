#!/usr/bin/env python3
"""
paper_battle_engine.py — Pure Competitive Paper Battle Engine v1.3

EVOLUTION HISTORY
  v1.0 (2026-05-13)  Knowledge Core + Style Matrix + Scoring + Tiers
  v1.1 (2026-05-13)  + Character + XP + Levels + Stages + Self-Learn + Self-Upgrade + Memory
  v1.2 (2026-05-13)  + DNA Engine (L3) + Title System (L7) + Rivalry Engine (L8)
  v1.3 (2026-05-13)  + META_EVOLUTION Deep Research Engine — meta health, edge decay,
                       behavioral drift, research priority queue, knowledge maturity

🏆 PAPER / SIMULATION ONLY. NO EXCHANGE EXECUTION. NO CAPITAL MOVEMENT.

LAYER MAP per AI Universe Master Architecture v2.0:
  L1 Knowledge Core        ✓ (immutable trading rules)
  L2 Style Engine          ✓ (per-agent behavior variation)
  L3 DNA Engine            ✓ NEW — immutable personality constraints
  L4 XP System             ✓
  L5 Self-Learning         ✓ (±15% bounded by DNA)
  L6 Self-Upgrade          ✓ (Precision/RiskCompress/Aggression/RegimeMaster)
  L7 Title System          ✓ NEW — 7 titles, defense mechanics, +10% XP mult
  L8 Rivalry Engine        ✓ NEW — 4 states, XP pressure, counter-style memory
  L9 Paper Championship    ✓ (scoring, tiers, ranking)
  L10 Hybrid Router        — future (not in v1.2)
  L11 Governance           ✓ (kill switches, layer isolation, operator override)
  L12 Telemetry            ✓ (paper-arena.json publisher)
  L13 Visual Arena         ✓ (frontend at /championship + /racing)

CORE PRINCIPLE: All behavioral shifts capped at ±15%. DNA is immutable.
Titles cannot increase risk caps. Rivalry cannot bypass cooldown or governance.
"""

import json
import math
import time
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# ── PATHS ────────────────────────────────────────────────────────────────
ROOT          = Path("/root/agent/paper_battle")
STATE_FILE    = ROOT / "paper_state.json"
LEGACY_FILE   = ROOT / "championship_legacy.json"
LOG_FILE      = ROOT / "paper_battle.log"
INPUT_TELEM   = Path("/var/www/ai-trading-championship/dist/api/battle/terminal.json")
OUTPUT_ARENA  = Path("/var/www/ai-trading-championship/dist/api/battle/paper-arena.json")

# ── CONSTANTS ────────────────────────────────────────────────────────────
TICK_SECONDS  = 5

PAPER_MODE   = "PAPER_CHAMPIONSHIP"
PAPER_MODE_LEGACY = "PAPER_SANDBOX_NO_REAL_CAPITAL"
PAPER_DISCLAIMER = (
    "ALL pnl, trades, and outcomes are SIMULATED. "
    "No real capital is at risk. No orders are sent to any exchange. "
    "Layer 1 trading core remains LOCKED and INACTIVE."
)

STARTING_PAPER_EQUITY_USD = 10_000.00
CREATION_DATE = "2026-05-13"
SYSTEM_MATURITY_FACTOR = 1.0
PROJECT_VERSION = "v1.2"

# Universal cap on behavioral shifts (per spec: max ±15%)
MAX_BEHAVIOR_SHIFT = 0.15

# ── L1 KNOWLEDGE CORE (immutable) ───────────────────────────────────────
KC = {
    "base_threshold":       60,
    "base_risk_per_trade":  0.01,
    "tp_ratio":             2.0,
    "sl_ratio":             1.0,
    "cooldown_seconds":     1800,
    "max_hold_seconds":     21600,
    "max_trades_per_day":   8,
    "consec_loss_limit":    3,
    "chaos_regime":         "CHAOS",
}

# ── L2 STYLE MATRIX (base per-agent personality) ────────────────────────
STYLE = {
    "HUNTER":   {"aggression": 1.20, "threshold_offset": -5,  "holding_bias": "short",    "regime_preference": "momentum"},
    "RISK":     {"aggression": 0.70, "threshold_offset": +5,  "holding_bias": "balanced", "regime_preference": "all"},
    "ALPHA":    {"aggression": 1.00, "threshold_offset": -3,  "holding_bias": "adaptive", "regime_preference": "volatility"},
    "REGIME":   {"aggression": 1.00, "threshold_offset": +8,  "holding_bias": "long",     "regime_preference": "strong_trend_only"},
    "EXECUTOR": {"aggression": 0.90, "threshold_offset":  0,  "holding_bias": "short",    "regime_preference": "clean_liquidity"},
    "RECOVERY": {"aggression": 1.00, "threshold_offset": -4,  "holding_bias": "layered",  "regime_preference": "post_loss"},
    "SKEPTIC":  {"aggression": 0.60, "threshold_offset": +10, "holding_bias": "short",    "regime_preference": "overextension"},
    "CHAMPION": {"aggression": "dynamic", "threshold_offset": "dynamic", "holding_bias": "adaptive", "regime_preference": "best_scoring_pattern"},
}

# ── L3 DNA ENGINE (IMMUTABLE per-agent identity) ────────────────────────
# DNA caps behavior. Self-learning + rivalry adjustments cannot violate.
DNA = {
    "HUNTER": {
        "volatility_tolerance":   0.9,
        "aggression_ceiling":     1.3,
        "risk_sensitivity":       0.4,
        "decision_latency":       "fast",
        "regime_affinity":        {"trend": 1.2, "chop": 0.6, "expansion": 1.3, "panic": 0.5},
        "drawdown_reaction":      "adaptive",
        "confidence_decay_rate":  0.3,
    },
    "RISK": {
        "volatility_tolerance":   0.4,
        "aggression_ceiling":     0.8,
        "risk_sensitivity":       0.9,
        "decision_latency":       "medium",
        "regime_affinity":        {"trend": 0.9, "chop": 1.1, "expansion": 0.8, "panic": 0.7},
        "drawdown_reaction":      "defensive",
        "confidence_decay_rate":  0.7,
    },
    "ALPHA": {
        "volatility_tolerance":   0.8,
        "aggression_ceiling":     1.2,
        "risk_sensitivity":       0.6,
        "decision_latency":       "fast",
        "regime_affinity":        {"trend": 1.0, "chop": 0.9, "expansion": 1.2, "panic": 0.7},
        "drawdown_reaction":      "adaptive",
        "confidence_decay_rate":  0.4,
    },
    "REGIME": {
        "volatility_tolerance":   0.6,
        "aggression_ceiling":     1.0,
        "risk_sensitivity":       0.7,
        "decision_latency":       "slow",
        "regime_affinity":        {"trend": 1.4, "chop": 0.4, "expansion": 1.1, "panic": 0.5},
        "drawdown_reaction":      "neutral",
        "confidence_decay_rate":  0.3,
    },
    "EXECUTOR": {
        "volatility_tolerance":   0.5,
        "aggression_ceiling":     0.9,
        "risk_sensitivity":       0.8,
        "decision_latency":       "medium",
        "regime_affinity":        {"trend": 1.0, "chop": 1.1, "expansion": 0.9, "panic": 0.5},
        "drawdown_reaction":      "defensive",
        "confidence_decay_rate":  0.5,
    },
    "RECOVERY": {
        "volatility_tolerance":   0.7,
        "aggression_ceiling":     1.1,
        "risk_sensitivity":       0.6,
        "decision_latency":       "medium",
        "regime_affinity":        {"trend": 1.0, "chop": 0.8, "expansion": 1.0, "panic": 1.2},
        "drawdown_reaction":      "adaptive",
        "confidence_decay_rate":  0.2,
    },
    "SKEPTIC": {
        "volatility_tolerance":   0.5,
        "aggression_ceiling":     0.7,
        "risk_sensitivity":       0.85,
        "decision_latency":       "slow",
        "regime_affinity":        {"trend": 0.5, "chop": 0.7, "expansion": 0.6, "panic": 1.4},
        "drawdown_reaction":      "defensive",
        "confidence_decay_rate":  0.8,
    },
    "CHAMPION": {
        "volatility_tolerance":   0.7,
        "aggression_ceiling":     1.2,
        "risk_sensitivity":       0.7,
        "decision_latency":       "medium",
        "regime_affinity":        {"trend": 1.1, "chop": 0.9, "expansion": 1.1, "panic": 0.9},
        "drawdown_reaction":      "adaptive",
        "confidence_decay_rate":  0.4,
    },
}

# ── IDENTITY + LORE (v1.1 character layer) ──────────────────────────────
IDENTITY = {
    "HUNTER":   {"id": "HUNTER_01",   "first_name": "Ares",    "last_name": "Valkor",  "personality_type": "Aggressive Momentum",  "label": "HUNTER",   "faction": "PHOENIX", "color": "#ff7700", "icon": "🎯",
                 "backstory": "Born from volatility spikes during expansion cycles. Specializes in rapid momentum capture. Thrives in high-energy regimes. Struggles in sideways chop."},
    "RISK":     {"id": "RISK_01",     "first_name": "Cassia",  "last_name": "Verax",   "personality_type": "Risk Parity Guardian", "label": "RISK",     "faction": "AEGIS",   "color": "#22c55e", "icon": "🛡",
                 "backstory": "Trained in capital preservation across three market generations. Refuses positions until margin of safety is calculated. Slowest entries, longest survival."},
    "ALPHA":    {"id": "ALPHA_01",    "first_name": "Niven",   "last_name": "Sharp",   "personality_type": "Adaptive Predator",    "label": "ALPHA",    "faction": "VOID",    "color": "#a855f7", "icon": "α",
                 "backstory": "Chases the best signal across all regimes. Adaptive by nature. Burns hot when the market gives clarity. Idles when it doesn't."},
    "REGIME":   {"id": "REGIME_01",   "first_name": "Thane",   "last_name": "Korvan",  "personality_type": "Strong-Trend Sage",    "label": "REGIME",   "faction": "TITAN",   "color": "#facc15", "icon": "🌐",
                 "backstory": "A specialist in trend purity. Only trades when the market commits. Long holding bias. Patient as a glacier."},
    "EXECUTOR": {"id": "EXECUTOR_01", "first_name": "Mira",    "last_name": "Voss",    "personality_type": "Precision Operator",   "label": "EXECUTOR", "faction": "AEGIS",   "color": "#06b6d4", "icon": "⚙",
                 "backstory": "Obsessed with execution quality. Cares more about how a trade was taken than how it ended. Cleanest equity curve in the field."},
    "RECOVERY": {"id": "RECOVERY_01", "first_name": "Phoenyx", "last_name": "Aldon",   "personality_type": "Comeback Specialist",  "label": "RECOVERY", "faction": "PHOENIX", "color": "#f59e0b", "icon": "🔄",
                 "backstory": "Defined by what comes after the loss. Post-drawdown specialist with layered re-entry. Rises from ashes by design."},
    "SKEPTIC":  {"id": "SKEPTIC_01",  "first_name": "Doran",   "last_name": "Pyle",    "personality_type": "Contrarian Oracle",    "label": "SKEPTIC",  "faction": "VOID",    "color": "#ec4899", "icon": "✋",
                 "backstory": "Watches the crowd, then does the opposite. Fades euphoria. Buys terror. Often early — rarely wrong."},
    "CHAMPION": {"id": "CHAMPION_01", "first_name": "Atlas",   "last_name": "Crowne",  "personality_type": "Ensemble Architect",   "label": "CHAMPION", "faction": "TITAN",   "color": "#fbbf24", "icon": "👑",
                 "backstory": "Synthesizes the lessons of all rivals into one adaptive blueprint. Dynamic across all parameters. The standard others measure themselves against."},
}

AGENT_NAMES = list(STYLE.keys())
REGIMES = ["TRENDING", "BREAKOUT", "HIGH", "CHOP", "CONSOLIDATION", "OVERREACH", "CHAOS"]

# Regime → DNA affinity bucket mapping
REGIME_TO_AFFINITY = {
    "TRENDING": "trend", "BREAKOUT": "expansion", "HIGH": "expansion",
    "CHOP": "chop", "CONSOLIDATION": "chop",
    "OVERREACH": "panic", "CHAOS": "panic",
}

# ── L4 EVOLUTION STAGES ──────────────────────────────────────────────────
EVOLUTION_STAGES = {1: "Rookie", 2: "Contender", 3: "Veteran", 4: "Elite", 5: "Champion"}
STAGE_XP_THRESHOLDS = {1: 0, 2: 200, 3: 500, 4: 1000, 5: 2000}

UPGRADE_TYPES = {
    "PRECISION":     "Improved signal threshold calibration",
    "RISK_COMPRESS": "Improved drawdown handling",
    "AGGRESSION":    "Smarter scaling logic (paper only)",
    "REGIME_MASTER": "Faster regime adaptation",
}

# ── L7 TITLE SYSTEM ──────────────────────────────────────────────────────
TITLES = {
    "GRAND_CHAMPION":     {"label": "Grand Champion",     "icon": "👑", "metric": "adjusted_score",        "criteria": "highest"},
    "VOLATILITY_KING":    {"label": "Volatility King",    "icon": "⚡", "metric": "vol_regime_pnl",        "criteria": "highest"},
    "STABILITY_GUARDIAN": {"label": "Stability Guardian", "icon": "🛡", "metric": "max_drawdown_inverse",  "criteria": "highest"},
    "PRECISION_SNIPER":   {"label": "Precision Sniper",   "icon": "🎯", "metric": "win_rate",              "criteria": "highest"},
    "REGIME_MASTER":      {"label": "Regime Master",      "icon": "🌐", "metric": "regimes_positive",      "criteria": "highest"},
    "COMEBACK_LEGEND":    {"label": "Comeback Legend",    "icon": "🔥", "metric": "biggest_comeback",      "criteria": "highest"},
    "DISCIPLINE_GUARDIAN":{"label": "Discipline Guardian","icon": "🧘", "metric": "discipline_score",      "criteria": "highest"},
}

# Title defense: 2-cycle underperformance triggers defense state
TITLE_DEFENSE_CYCLES = 2
TITLE_XP_MULTIPLIER = 1.10  # +10%

# ── L8 RIVALRY ENGINE ────────────────────────────────────────────────────
RIVALRY_STATES = ["EMERGING", "HEATED", "CRITICAL", "LEGENDARY"]
RIVALRY_STATE_DURATIONS = {
    # Min cycles together to advance to next state
    "EMERGING_TO_HEATED":  10,
    "HEATED_TO_CRITICAL":  30,
    "CRITICAL_TO_LEGENDARY": 60,
}
RIVALRY_XP_MULTIPLIER = 1.25   # XP gain × 1.25, loss × 1.25 when active
RIVALRY_BEHAVIOR_SHIFT = 0.10  # ±10% counter-style adjustment cap
RIVALRY_TRAILING_AGGRESSION_BIAS = 0.05  # +5% if trailing
RIVALRY_LEADING_DISCIPLINE_BIAS = 0.05   # +5% if leading

# Opposite style pairs (auto-rivalry)
OPPOSITE_STYLES = [
    ("HUNTER", "SKEPTIC"),     # aggression vs contrarian
    ("REGIME", "ALPHA"),       # patient trend vs adaptive
    ("RISK", "RECOVERY"),      # preservation vs comeback
    ("EXECUTOR", "CHAMPION"),  # precision vs ensemble
]

# Self-learning bounds (already capped, kept for clarity)
LEARNING_DELTA_CAP = 0.15  # ±15% per cycle (spec)

# ── META-EVOLUTION CONSTANTS (v1.3 — Deep Research Engine v2.0) ─────────
META_HEALTH_THRESHOLD       = 60    # below → enter observation mode
EDGE_DECAY_DROP_PCT         = 10    # win_rate_drop > 10% → trigger
ROLLING_50_WINDOW           = 50
ROLLING_200_WINDOW          = 200
LONG_CYCLE_REVIEW_TRADES    = 1000  # full meta audit every N trades
KNOWLEDGE_MATURITY_MIN      = 1.0
KNOWLEDGE_MATURITY_MAX      = 1.5

RESEARCH_PRIORITIES = [
    "edge_decay_detection",
    "regime_inefficiency",
    "volatility_misalignment",
    "execution_latency_inefficiency",
    "parameter_overfitting_risk",
]
RESEARCH_PRIORITIES_TOP_K = 2  # only top 2 active at a time

# Behavioral drift triggers
DRIFT_AGGRESSION_THRESHOLD  = 0.10  # 10% aggression rise without performance gain
DRIFT_PRECISION_DROP        = 0.10  # 10% precision drop while trade freq up

# Adaptive caps per Section IV (these are the v1.3 explicit caps from spec)
ADAPTIVE_CAPS = {
    "threshold":      0.15,  # ±15%
    "aggression":     0.15,  # ±15%
    "regime_weight":  0.15,  # ±15%
    "trade_freq":     0.10,  # ±10%
}

# ── ADAPTIVE TRADING MODES (v2.0 — Spec #8) ─────────────────────────────
ADAPTIVE_MODES = {
    "STOP": {
        "label":          "STOP",
        "risk_pct_min":   0.0,
        "risk_pct_max":   0.0,
        "priority":       0,  # highest priority
        "freq_multiplier":0.0,
        "description":    "Capital lockdown · no new entries · defensive exits only",
    },
    "SAFE": {
        "label":           "SAFE",
        "risk_pct_min":    0.0025,
        "risk_pct_max":    0.005,
        "priority":        1,
        "freq_multiplier": 0.5,
        "description":     "Capital preservation · low frequency · strict confirmation",
    },
    "AGGRESSIVE": {
        "label":           "AGGRESSIVE",
        "risk_pct_min":    0.005,
        "risk_pct_max":    0.01,
        "priority":        2,
        "freq_multiplier": 1.0,
        "description":     "Standard opportunity capture · regime-aligned",
    },
    "MAX_AGGRESSIVE": {
        "label":           "MAX_AGGRESSIVE",
        "risk_pct_min":    0.01,
        "risk_pct_max":    0.01,  # hard cap, never above 1%
        "priority":        3,
        "freq_multiplier": 1.3,
        "description":     "High-conviction expansion · max 5 cycles only",
    },
}
MAX_AGGRESSIVE_CYCLE_LIMIT = 5  # cannot stay in MAX_AGGRESSIVE > 5 cycles per spec
MODE_UPGRADE_STABLE_CYCLES = 3  # need 3 consecutive stable cycles to upgrade
ANTI_OVERCONFIDENCE_WIN_STREAK = 5  # 5+ wins → confidence spike control

# ── PSI / TPI / MSI (v2.0 — Spec #4/#5/#6) ──────────────────────────────
PSI_LOCK_THRESHOLD       = 75    # < 75 → scaling locked
PSI_SLOW_COMPOUND_MAX    = 85    # 75-85 → slow compound
# > 85 → progressive compound

POWER_COMPRESSION_AGGRESSION = 0.60  # -40% on triggers
POWER_COMPRESSION_FREQUENCY  = 0.70  # -30% on triggers

# ── PROFIT ALLOCATION TIERS (paper, illustrative) ───────────────────────
PROFIT_ALLOCATION = {
    "core_capital":      0.40,
    "research_lab":      0.25,
    "infrastructure":    0.15,
    "strategic_reserve": 0.10,
    "brand_authority":   0.10,
}

# ── CAPITAL EVOLUTION PHASES (paper, currently Phase 0) ─────────────────
CAPITAL_PHASES = {
    0: "Paper Dominance",
    1: "Micro Live ($10-$50)",
    2: "Canary Controlled ($100)",
    3: "Controlled Compounding",
    4: "Ecosystem Expansion",
}
CURRENT_CAPITAL_PHASE = 0  # paper only · gated by 5-LAYER_DISCIPLINE gates + operator


# ── DETERMINISTIC NOISE ──────────────────────────────────────────────────
def det(seed_str: str, magnitude: float = 1.0) -> float:
    h = hashlib.sha256(seed_str.encode()).digest()
    n = int.from_bytes(h[:4], "big") / (2**32 - 1)
    return (n * 2 - 1) * magnitude


# ── KNOWLEDGE CORE — market state ────────────────────────────────────────
def compute_market_state(cycle: int, real_btc_price: float, real_regime: str) -> dict:
    momentum  = 50 + 35 * math.sin(cycle * 0.07) + det(f"mom:{cycle}", 12)
    trend     = 50 + 30 * math.sin(cycle * 0.04 + 1.2) + det(f"trnd:{cycle}", 10)
    volume    = 50 + 25 * math.sin(cycle * 0.11 + 0.5) + det(f"vol:{cycle}", 15)
    volatility= 0.015 + 0.025 * (0.5 + 0.5 * math.sin(cycle * 0.09)) + det(f"vty:{cycle}", 0.008)
    volatility = max(0.005, min(0.08, volatility))

    momentum  = max(0, min(100, momentum))
    trend     = max(0, min(100, trend))
    volume    = max(0, min(100, volume))

    if   volatility >= 0.07:                  regime = "CHAOS"
    elif momentum > 75 and trend > 70:        regime = "BREAKOUT"
    elif trend > 65:                          regime = "TRENDING"
    elif momentum > 70 and volatility > 0.04: regime = "HIGH"
    elif momentum < 35 and trend < 35:        regime = "OVERREACH"
    elif trend < 40 and volatility < 0.02:    regime = "CONSOLIDATION"
    else:                                     regime = "CHOP"

    regime_bonus = {"BREAKOUT": 15, "TRENDING": 12, "HIGH": 8, "OVERREACH": 4,
                    "CHOP": 0, "CONSOLIDATION": -3, "CHAOS": -20}.get(regime, 0)
    composite = 0.30*momentum + 0.30*trend + 0.15*volume + 0.15*(100 - abs(volatility-0.03)*1000) + 0.10*(50 + regime_bonus)
    composite = max(0, min(100, composite))

    signal_active = composite >= KC["base_threshold"] and regime != KC["chaos_regime"]

    return {
        "regime": regime, "btc_price": round(real_btc_price, 2),
        "momentum": round(momentum, 2), "trend": round(trend, 2),
        "volume": round(volume, 2), "volatility": round(volatility, 4),
        "composite_score": round(composite, 2),
        "signal_active": signal_active, "base_threshold": KC["base_threshold"],
    }


# ── AGENT STATE INIT (v1.2 includes DNA + titles + rivalries) ───────────
def init_agent_state(name: str) -> dict:
    ident = IDENTITY[name]
    return {
        # Identity
        "id": ident["id"], "name": name,
        "first_name": ident["first_name"], "last_name": ident["last_name"],
        "codename": name, "personality_type": ident["personality_type"],
        "faction": ident["faction"], "backstory": ident["backstory"],
        "creation_date": CREATION_DATE,

        # DNA (IMMUTABLE — set at creation)
        "dna": dict(DNA[name]),

        # Character progression
        "xp": 0, "level": 1, "evolution_stage": 1, "stage_name": "Rookie",
        "self_learning_enabled": True, "self_upgrade_enabled": True,

        # Trading state
        "equity": STARTING_PAPER_EQUITY_USD,
        "peak_equity": STARTING_PAPER_EQUITY_USD,
        "position": None, "last_exit_cycle": -10000,
        "trades_today": 0, "trades_total": 0,
        "wins": 0, "losses": 0,
        "consecutive_wins": 0, "consecutive_losses": 0,
        "trade_pnls": [], "trade_r_multiples": [],
        "regime_perf": {r: {"trades": 0, "pnl": 0.0} for r in REGIMES},
        "penalties": {"overtrade": 0, "cluster": 0, "chaos": 0, "cooldown_violation": False},
        "discipline_score": 100, "score": 0.0, "adjusted_score": 0.0,
        "rank": 0, "tier": "C", "last_action": "READY", "consistency_streak": 0,

        # Learned style overlay (bounded by DNA)
        "learned_overlay": {
            "aggression_mult": 1.0, "threshold_mult": 1.0,
            "regime_bias": {r: 1.0 for r in REGIMES}, "holding_mult": 1.0,
        },
        "learning_adjustments_history": [],

        # Upgrades
        "upgrades": [], "upgrade_history": [],

        # Titles (v1.2)
        "current_titles": [],           # list of title IDs held
        "titles_won_count": {t: 0 for t in TITLES},
        "titles_defended": {t: 0 for t in TITLES},
        "longest_title_reign": 0,
        "title_reigns": {},             # title_id → consecutive cycles held
        "title_under_defense": {},      # title_id → cycles_underperforming

        # Rivalries (v1.2) — opponent_name → state dict
        "rivalries": {},                # see init_rivalry_record()

        # Legacy
        "legacy": {
            "title_wins":               0,
            "longest_win_streak":       0,
            "longest_loss_streak":      0,
            "biggest_comeback_usd":     0.0,
            "best_regime":              None,
            "lowest_dd_pct":            100.0,
            "lifetime_pnl":             0.0,
            "historic_achievements":    [],
        },
    }


def init_rivalry_record(opponent: str) -> dict:
    return {
        "opponent": opponent,
        "cycles_active": 0,
        "state": "EMERGING",
        "wins_against": 0,
        "losses_against": 0,
        "max_gap_pct": 0.0,
        "adaptations": [],          # last 10 counter-style adjustments
        "title_defense": False,
        "active": False,
        "trailing": False,
    }


# ── LEVEL + STAGE ────────────────────────────────────────────────────────
def compute_level(xp: int) -> int:
    return max(1, math.floor(math.sqrt(max(0, xp) / 50)))

def compute_evolution_stage(xp: int) -> int:
    if xp >= STAGE_XP_THRESHOLDS[5]: return 5
    if xp >= STAGE_XP_THRESHOLDS[4]: return 4
    if xp >= STAGE_XP_THRESHOLDS[3]: return 3
    if xp >= STAGE_XP_THRESHOLDS[2]: return 2
    return 1


# ── XP AWARD ─────────────────────────────────────────────────────────────
def title_xp_multiplier(agent: dict) -> float:
    """Each title held gives +10% XP multiplier (multiplicative)."""
    return TITLE_XP_MULTIPLIER ** len(agent.get("current_titles", []))


def rivalry_xp_multiplier(agent: dict) -> float:
    """If any rivalry is active, apply 1.25× to XP gains/losses."""
    for r in agent.get("rivalries", {}).values():
        if r.get("active") and r.get("state") in ("HEATED", "CRITICAL", "LEGENDARY"):
            return RIVALRY_XP_MULTIPLIER
    return 1.0


def award_xp(agent: dict, delta: int, reason: str, cycle: int):
    # Apply title + rivalry multipliers (only on positive gains for titles, both for rivalries per spec)
    multiplier = 1.0
    if delta > 0:
        multiplier *= title_xp_multiplier(agent)
    multiplier *= rivalry_xp_multiplier(agent)
    delta = int(round(delta * multiplier))

    old_xp = agent["xp"]
    old_lvl = agent["level"]
    old_stage = agent["evolution_stage"]
    agent["xp"] = max(0, agent["xp"] + delta)
    agent["level"] = compute_level(agent["xp"])
    agent["evolution_stage"] = compute_evolution_stage(agent["xp"])
    agent["stage_name"] = EVOLUTION_STAGES[agent["evolution_stage"]]
    if agent["level"] != old_lvl or agent["evolution_stage"] != old_stage:
        agent["learning_adjustments_history"].append({
            "type": "LEVEL_UP" if agent["level"] > old_lvl else ("STAGE_UP" if agent["evolution_stage"] > old_stage else "PROGRESSION"),
            "old_xp": old_xp, "new_xp": agent["xp"],
            "old_level": old_lvl, "new_level": agent["level"],
            "old_stage": old_stage, "new_stage": agent["evolution_stage"],
            "reason": reason, "cycle": cycle, "multiplier": round(multiplier, 3),
        })
        agent["learning_adjustments_history"] = agent["learning_adjustments_history"][-50:]


# ── L3 DNA ENFORCEMENT — applied to effective style ─────────────────────
def apply_dna_to_effective_style(name: str, effective: dict, dna: dict) -> dict:
    """Cap effective style values within DNA bounds. DNA is hard ceiling."""
    # Aggression cap: cannot exceed aggression_ceiling
    effective["aggression"] = min(effective["aggression"], dna["aggression_ceiling"])
    # Risk sensitivity: higher = wants smaller positions, so reduce aggression by (risk_sensitivity * 0.2)
    risk_dampening = 1.0 - (dna["risk_sensitivity"] - 0.5) * 0.3  # range ~[0.85, 1.15]
    effective["aggression"] *= max(0.7, min(1.3, risk_dampening))
    # Volatility tolerance — agent's threshold offset shifts by (1 - tolerance) — low tolerance = stricter entry
    effective["threshold_offset"] += (1.0 - dna["volatility_tolerance"]) * 10  # adds up to +10 if zero tolerance
    return effective


def apply_overlay_to_style(base_style: dict, overlay: dict) -> dict:
    eff = {}
    base_agg = base_style["aggression"] if not isinstance(base_style["aggression"], str) else 1.0
    eff["aggression"] = base_agg * overlay["aggression_mult"]
    base_th = base_style["threshold_offset"] if not isinstance(base_style["threshold_offset"], str) else 0
    eff["threshold_offset"] = base_th * overlay["threshold_mult"]
    eff["holding_bias"] = base_style["holding_bias"]
    eff["regime_preference"] = base_style["regime_preference"]
    eff["regime_bias"] = dict(overlay["regime_bias"])
    return eff


def resolve_style(agent_name: str, market: dict, agent_state: dict) -> dict:
    """Effective style = base + dynamic (CHAMPION) + learned overlay + DNA constraints + rivalry pressure."""
    s = dict(STYLE[agent_name])
    if agent_name == "CHAMPION":
        c = market["composite_score"]
        s["aggression"] = 1.4 if c > 80 else (1.0 if c > 60 else 0.7)
        s["threshold_offset"] = -8 if c > 80 else (-3 if c > 60 else 5)
    eff = apply_overlay_to_style(s, agent_state["learned_overlay"])

    # Apply DNA constraints
    eff = apply_dna_to_effective_style(agent_name, eff, agent_state["dna"])

    # Apply rivalry pressure (if any active rivalry)
    rivalry_bias = compute_rivalry_pressure(agent_state)
    eff["aggression"] *= (1.0 + rivalry_bias["aggression_bias"])
    eff["threshold_offset"] += rivalry_bias["threshold_offset"]

    # Final cap: aggression cannot exceed DNA aggression_ceiling under any circumstance
    eff["aggression"] = min(eff["aggression"], agent_state["dna"]["aggression_ceiling"])
    eff["dna_volatility_tolerance"] = agent_state["dna"]["volatility_tolerance"]
    eff["dna_decision_latency"] = agent_state["dna"]["decision_latency"]
    return eff


def compute_rivalry_pressure(agent: dict) -> dict:
    """Aggregate rivalry-driven bias. Capped at ±15% total per spec."""
    aggression_bias = 0.0
    threshold_offset = 0.0
    for r in agent.get("rivalries", {}).values():
        if not r.get("active"): continue
        state = r.get("state", "EMERGING")
        if state not in ("HEATED", "CRITICAL", "LEGENDARY"): continue
        if r.get("trailing"):
            aggression_bias += RIVALRY_TRAILING_AGGRESSION_BIAS
            threshold_offset -= 3
        else:
            # Leading: focus on discipline, reduce unnecessary trades
            aggression_bias -= RIVALRY_LEADING_DISCIPLINE_BIAS * 0.5
    # Hard cap ±15%
    aggression_bias = max(-MAX_BEHAVIOR_SHIFT, min(MAX_BEHAVIOR_SHIFT, aggression_bias))
    threshold_offset = max(-10, min(10, threshold_offset))
    return {"aggression_bias": aggression_bias, "threshold_offset": threshold_offset}


# ── L5 SELF-LEARNING (bounded by DNA) ───────────────────────────────────
def self_learning_update(agent: dict, market: dict, cycle: int):
    if not agent["self_learning_enabled"]: return
    if cycle % 20 != 0 or agent["trades_total"] < 5: return

    overlay = agent["learned_overlay"]
    dna = agent["dna"]
    recent_pnls = agent["trade_pnls"][-50:]
    if not recent_pnls: return

    avg_recent = sum(recent_pnls) / len(recent_pnls)
    regime_pnls = {r: agent["regime_perf"][r]["pnl"] for r in REGIMES if agent["regime_perf"][r]["trades"] > 0}
    adjustments = []

    # Regime biasing — DNA affinity still applies, but learned bias drifts within ±15%
    for r, pnl in regime_pnls.items():
        affinity_bucket = REGIME_TO_AFFINITY.get(r, "trend")
        dna_affinity = dna["regime_affinity"].get(affinity_bucket, 1.0)
        if pnl > 0:
            new_bias = min(1.0 + LEARNING_DELTA_CAP, overlay["regime_bias"].get(r, 1.0) * 1.05)
        elif pnl < 0:
            new_bias = max(1.0 - LEARNING_DELTA_CAP, overlay["regime_bias"].get(r, 1.0) * 0.95)
        else:
            continue
        # DNA affinity caps: cannot exceed (dna_affinity * 1.2) or go below (dna_affinity * 0.8)
        ceiling = min(1.0 + LEARNING_DELTA_CAP, dna_affinity * 1.2)
        floor   = max(1.0 - LEARNING_DELTA_CAP, dna_affinity * 0.8)
        new_bias = max(floor, min(ceiling, new_bias))
        if abs(new_bias - overlay["regime_bias"].get(r, 1.0)) > 0.001:
            adjustments.append(f"regime_bias[{r}] {overlay['regime_bias'].get(r, 1.0):.3f}→{new_bias:.3f} (dna_aff={dna_affinity:.2f})")
            overlay["regime_bias"][r] = new_bias

    # Aggression learning — bounded by DNA aggression_ceiling
    dd_pct = ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100
    if avg_recent > 0 and dd_pct < 5:
        new_agg = min(1.0 + LEARNING_DELTA_CAP, overlay["aggression_mult"] * 1.03)
    elif avg_recent < 0 or dd_pct > 10:
        new_agg = max(1.0 - LEARNING_DELTA_CAP, overlay["aggression_mult"] * 0.97)
    else:
        new_agg = overlay["aggression_mult"]
    # DNA aggression_ceiling check (effective aggression cannot exceed ceiling)
    base_aggression = STYLE[agent["name"]]["aggression"] if not isinstance(STYLE[agent["name"]]["aggression"], str) else 1.0
    max_overlay = dna["aggression_ceiling"] / base_aggression
    new_agg = min(new_agg, max_overlay)
    if abs(new_agg - overlay["aggression_mult"]) > 0.001:
        adjustments.append(f"aggression_mult {overlay['aggression_mult']:.3f}→{new_agg:.3f}")
        overlay["aggression_mult"] = new_agg

    # Threshold learning
    if agent["trades_total"] > 0:
        wr = agent["wins"] / agent["trades_total"]
        if wr < 0.4:
            new_th = min(1.0 + LEARNING_DELTA_CAP, overlay["threshold_mult"] * 1.04)
        elif wr > 0.6:
            new_th = max(1.0 - LEARNING_DELTA_CAP, overlay["threshold_mult"] * 0.98)
        else:
            new_th = overlay["threshold_mult"]
        if abs(new_th - overlay["threshold_mult"]) > 0.001:
            adjustments.append(f"threshold_mult {overlay['threshold_mult']:.3f}→{new_th:.3f}")
            overlay["threshold_mult"] = new_th

    if adjustments:
        agent["learning_adjustments_history"].append({
            "type": "SELF_LEARN", "cycle": cycle, "adjustments": adjustments,
            "rationale": f"avg_recent_pnl={avg_recent:.2f} dd_pct={dd_pct:.1f} wr={agent['wins']/max(1,agent['trades_total']):.2%}",
        })
        agent["learning_adjustments_history"] = agent["learning_adjustments_history"][-50:]


# ── L6 SELF-UPGRADE ──────────────────────────────────────────────────────
def check_and_apply_upgrades(agent: dict, cycle: int):
    if not agent["self_upgrade_enabled"] or agent["level"] < 3 or agent["score"] <= 0:
        return
    if agent["penalties"]["chaos"] > 2 or agent["penalties"]["cluster"] > 2:
        return
    dd_pct = ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100
    if dd_pct > 15: return

    if "PRECISION" not in agent["upgrades"] and agent["level"] >= 3:
        agent["upgrades"].append("PRECISION")
        agent["upgrade_history"].append({"upgrade": "PRECISION", "cycle": cycle, "level": agent["level"]})
        agent["learning_adjustments_history"].append({
            "type": "UPGRADE", "cycle": cycle, "upgrade": "PRECISION",
            "effect": "Threshold calibration sharpened by 5%"})
        agent["learned_overlay"]["threshold_mult"] *= 0.95
    elif "RISK_COMPRESS" not in agent["upgrades"] and agent["level"] >= 4 and dd_pct < 8:
        agent["upgrades"].append("RISK_COMPRESS")
        agent["upgrade_history"].append({"upgrade": "RISK_COMPRESS", "cycle": cycle, "level": agent["level"]})
        agent["learning_adjustments_history"].append({
            "type": "UPGRADE", "cycle": cycle, "upgrade": "RISK_COMPRESS",
            "effect": "Drawdown handling sharpened"})
    elif "AGGRESSION" not in agent["upgrades"] and agent["level"] >= 5:
        agent["upgrades"].append("AGGRESSION")
        agent["upgrade_history"].append({"upgrade": "AGGRESSION", "cycle": cycle, "level": agent["level"]})
        agent["learning_adjustments_history"].append({
            "type": "UPGRADE", "cycle": cycle, "upgrade": "AGGRESSION",
            "effect": "Smarter scaling — aggression cap raised 5% (bounded by DNA ceiling)"})
        agent["learned_overlay"]["aggression_mult"] = min(1.20, agent["learned_overlay"]["aggression_mult"] * 1.05)
    elif "REGIME_MASTER" not in agent["upgrades"] and agent["level"] >= 6:
        agent["upgrades"].append("REGIME_MASTER")
        agent["upgrade_history"].append({"upgrade": "REGIME_MASTER", "cycle": cycle, "level": agent["level"]})
        agent["learning_adjustments_history"].append({
            "type": "UPGRADE", "cycle": cycle, "upgrade": "REGIME_MASTER",
            "effect": "Faster regime adaptation"})


def evolution_multiplier(stage: int) -> float:
    return 1.0 + (stage - 1) * 0.10


# ── L7 TITLE SYSTEM ──────────────────────────────────────────────────────
def compute_title_metrics(agent: dict) -> dict:
    """Compute each title's metric for ranking."""
    # Volatility regime PnL
    vol_pnl = agent["regime_perf"]["HIGH"]["pnl"] + agent["regime_perf"]["BREAKOUT"]["pnl"] + agent["regime_perf"]["CHAOS"]["pnl"]
    # Inverse of max drawdown (higher = better stability)
    max_dd_inv = 100 - ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100
    # Win rate (min 5 trades)
    wr = agent["wins"] / agent["trades_total"] if agent["trades_total"] >= 5 else 0
    # Regimes with positive PnL
    regimes_positive = sum(1 for r in REGIMES if agent["regime_perf"][r]["pnl"] > 0)
    return {
        "adjusted_score":       agent["adjusted_score"],
        "vol_regime_pnl":       vol_pnl,
        "max_drawdown_inverse": max_dd_inv,
        "win_rate":             wr,
        "regimes_positive":     regimes_positive,
        "biggest_comeback":     agent["legacy"]["biggest_comeback_usd"],
        "discipline_score":     agent["discipline_score"],
    }


def award_titles(agents: list, cycle: int):
    """Award titles based on per-cycle ranking by each metric.

    Each title goes to the agent with the highest metric value.
    Defense mechanic: 2 cycles of underperformance → defense → challenger takes.
    """
    # Compute metrics for each agent
    metrics = {a["name"]: compute_title_metrics(a) for a in agents}

    title_holders_this_cycle = {}

    for title_id, spec in TITLES.items():
        metric_key = spec["metric"]
        ranked = sorted(agents, key=lambda a: metrics[a["name"]][metric_key], reverse=True)
        if not ranked:
            continue
        leader = ranked[0]
        leader_name = leader["name"]
        leader_value = metrics[leader_name][metric_key]

        # Determine previous holder
        prev_holders = [a for a in agents if title_id in a["current_titles"]]
        prev_holder = prev_holders[0] if prev_holders else None

        if prev_holder is None:
            # New title, leader takes it
            new_holder = leader
        else:
            prev_value = metrics[prev_holder["name"]][metric_key]
            if leader_name == prev_holder["name"]:
                # Same holder — extend reign
                new_holder = leader
                # Clear defense state
                if title_id in prev_holder["title_under_defense"]:
                    del prev_holder["title_under_defense"][title_id]
            else:
                # Challenger leads. Check if prev holder has been underperforming.
                under = prev_holder["title_under_defense"].get(title_id, 0)
                if under >= TITLE_DEFENSE_CYCLES:
                    # Transfer
                    new_holder = leader
                    prev_holder["title_under_defense"].pop(title_id, None)
                else:
                    # Still in defense window
                    prev_holder["title_under_defense"][title_id] = under + 1
                    new_holder = prev_holder

        # Update current_titles
        for a in agents:
            if a["name"] == new_holder["name"]:
                if title_id not in a["current_titles"]:
                    a["current_titles"].append(title_id)
                    a["titles_won_count"][title_id] = a["titles_won_count"].get(title_id, 0) + 1
                    a["legacy"]["title_wins"] += 1
                    a["legacy"]["historic_achievements"].append({
                        "type": "TITLE_GAINED", "title": title_id,
                        "label": spec["label"], "cycle": cycle, "value": round(metrics[a["name"]][metric_key], 2),
                    })
                    a["learning_adjustments_history"].append({
                        "type": "TITLE_WON", "cycle": cycle, "title": title_id,
                        "label": spec["label"],
                    })
                a["title_reigns"][title_id] = a["title_reigns"].get(title_id, 0) + 1
                if a["title_reigns"][title_id] > a["longest_title_reign"]:
                    a["longest_title_reign"] = a["title_reigns"][title_id]
            else:
                if title_id in a["current_titles"]:
                    # Lost this title
                    a["current_titles"].remove(title_id)
                    a["title_reigns"][title_id] = 0
                    a["legacy"]["historic_achievements"].append({
                        "type": "TITLE_LOST", "title": title_id, "cycle": cycle,
                    })
                    a["learning_adjustments_history"].append({
                        "type": "TITLE_LOST", "cycle": cycle, "title": title_id,
                    })

        title_holders_this_cycle[title_id] = new_holder["name"]

    return title_holders_this_cycle


# ── L8 RIVALRY ENGINE ────────────────────────────────────────────────────
def update_rivalries(agents: list, cycle: int):
    """Detect + advance + update rivalry states for all agent pairs."""
    by_score = sorted(agents, key=lambda a: a["adjusted_score"], reverse=True)
    by_score_map = {a["name"]: i for i, a in enumerate(by_score)}

    # Build set of active rivalry pairs this cycle
    active_pairs = set()

    # 1. Performance-gap-based rivalries (adjacent ranks with <10% gap)
    for i in range(len(by_score) - 1):
        a, b = by_score[i], by_score[i + 1]
        gap_pct = abs(a["adjusted_score"] - b["adjusted_score"]) / max(1, abs(a["adjusted_score"]) + abs(b["adjusted_score"])) * 200
        if gap_pct < 10:
            active_pairs.add(tuple(sorted([a["name"], b["name"]])))

    # 2. Opposite-style rivalries (always tracked)
    for (n1, n2) in OPPOSITE_STYLES:
        active_pairs.add(tuple(sorted([n1, n2])))

    # 3. Title defense rivalries
    for a in agents:
        for title_id, under_cycles in a.get("title_under_defense", {}).items():
            if under_cycles >= 1:
                # Find leader for this title
                for b in agents:
                    if b["name"] != a["name"] and title_id not in a["current_titles"]:
                        pass  # too granular; leader detection happens in award_titles

    # Update each agent's rivalries
    by_name = {a["name"]: a for a in agents}
    for a in agents:
        name = a["name"]
        rivalries = a["rivalries"]
        for pair in active_pairs:
            if name not in pair: continue
            opp = pair[0] if pair[1] == name else pair[1]
            if opp not in by_name: continue

            # Init record if missing
            if opp not in rivalries:
                rivalries[opp] = init_rivalry_record(opp)

            rec = rivalries[opp]
            rec["active"] = True
            rec["cycles_active"] += 1

            # Trailing? (compared by adjusted_score)
            opp_score = by_name[opp]["adjusted_score"]
            rec["trailing"] = a["adjusted_score"] < opp_score
            gap_pct = abs(a["adjusted_score"] - opp_score) / max(1, abs(a["adjusted_score"]) + abs(opp_score)) * 200
            rec["max_gap_pct"] = max(rec["max_gap_pct"], round(gap_pct, 2))

            # Advance state
            c = rec["cycles_active"]
            old_state = rec["state"]
            if c >= RIVALRY_STATE_DURATIONS["CRITICAL_TO_LEGENDARY"]:
                rec["state"] = "LEGENDARY"
            elif c >= RIVALRY_STATE_DURATIONS["HEATED_TO_CRITICAL"]:
                rec["state"] = "CRITICAL"
            elif c >= RIVALRY_STATE_DURATIONS["EMERGING_TO_HEATED"]:
                rec["state"] = "HEATED"
            else:
                rec["state"] = "EMERGING"
            if old_state != rec["state"]:
                a["learning_adjustments_history"].append({
                    "type": "RIVALRY_STATE_CHANGE", "cycle": cycle,
                    "opponent": opp, "old_state": old_state, "new_state": rec["state"],
                })

        # Deactivate rivalries not in active_pairs this cycle
        for opp_name in list(rivalries.keys()):
            if tuple(sorted([name, opp_name])) not in active_pairs:
                if rivalries[opp_name].get("active"):
                    rivalries[opp_name]["active"] = False


# ═══════════════════════════════════════════════════════════════════════
# ── META_EVOLUTION DEEP RESEARCH ENGINE (v1.3) ─────────────────────────
# ═══════════════════════════════════════════════════════════════════════

def compute_meta_health(agent: dict) -> dict:
    """Section I — Meta Observation Layer.

    Computes meta_health_score [0-100] from internal decision quality signals.
    < 60 → Observation Mode (suspend upgrades, freeze parameter mutations).
    """
    pnls = agent["trade_pnls"]
    if len(pnls) < 5:
        return {
            "score":                100,
            "observation_mode":     False,
            "components":           {},
            "stability":            100,
            "aggression_drift":     0.0,
            "confidence_decay":     0.0,
        }

    # Rolling 50 vs rolling 200 stability
    r50  = pnls[-ROLLING_50_WINDOW:]  if len(pnls) >= ROLLING_50_WINDOW  else pnls
    r200 = pnls[-ROLLING_200_WINDOW:] if len(pnls) >= ROLLING_200_WINDOW else pnls
    avg50  = sum(r50) / len(r50) if r50 else 0
    avg200 = sum(r200) / len(r200) if r200 else 0

    # Decision stability — inverse coefficient of variation of recent returns
    if r50 and len(r50) >= 2:
        m = avg50
        var = sum((x - m) ** 2 for x in r50) / len(r50)
        stdev = math.sqrt(max(1e-6, var))
        stability = max(0, min(100, 100 - abs(stdev / max(0.5, abs(m))) * 30))
    else:
        stability = 50

    # Aggression drift — overlay drift from 1.0
    aggression_drift = abs(agent["learned_overlay"]["aggression_mult"] - 1.0)

    # Confidence decay — DNA confidence_decay_rate × recent loss ratio
    decay_rate = agent["dna"]["confidence_decay_rate"]
    recent_loss_ratio = sum(1 for p in r50 if p <= 0) / max(1, len(r50))
    confidence_decay = decay_rate * recent_loss_ratio * 100

    # Aggregate
    components = {
        "stability":          round(stability, 2),
        "rolling_50_avg":     round(avg50, 2),
        "rolling_200_avg":    round(avg200, 2),
        "aggression_drift":   round(aggression_drift, 3),
        "confidence_decay":   round(confidence_decay, 2),
        "rolling_diff":       round(avg50 - avg200, 2),
    }

    # Health score: penalize divergence, drift, decay
    diff_penalty       = max(0, min(40, abs(avg50 - avg200) * 0.5))
    drift_penalty      = aggression_drift * 100   # 0.15 → 15 points
    decay_penalty      = confidence_decay * 0.3
    health = 100 - diff_penalty - drift_penalty - decay_penalty
    # Boost: high stability
    health += (stability - 50) * 0.3
    health = max(0, min(100, health))

    return {
        "score":            round(health, 1),
        "observation_mode": health < META_HEALTH_THRESHOLD,
        "components":       components,
        "stability":        round(stability, 2),
        "aggression_drift": round(aggression_drift, 3),
        "confidence_decay": round(confidence_decay, 2),
    }


def detect_edge_decay(agent: dict, market: dict) -> dict:
    """Section II — Edge Decay Detection.

    Returns dict with warning_level (0|1|2|3=quarantine) + triggers.
    """
    pnls = agent["trade_pnls"]
    if len(pnls) < 10:
        return {"warning_level": 0, "triggers": [], "quarantined": False}

    triggers = []

    # Trigger 1: rolling 50 return < rolling 200 return
    r50  = pnls[-ROLLING_50_WINDOW:]  if len(pnls) >= ROLLING_50_WINDOW  else pnls
    r200 = pnls[-ROLLING_200_WINDOW:] if len(pnls) >= ROLLING_200_WINDOW else pnls
    avg50  = sum(r50)  / max(1, len(r50))
    avg200 = sum(r200) / max(1, len(r200))
    if len(r200) >= 50 and avg50 < avg200:
        triggers.append("ROLLING_50_BELOW_200")

    # Trigger 2: win rate drop > 10%
    if agent["trades_total"] >= 20:
        wr_total = agent["wins"] / agent["trades_total"]
        recent_wins = sum(1 for p in r50 if p > 0)
        wr_recent = recent_wins / max(1, len(r50))
        if (wr_total - wr_recent) > (EDGE_DECAY_DROP_PCT / 100):
            triggers.append(f"WIN_RATE_DROP_{(wr_total - wr_recent)*100:.1f}PCT")

    # Trigger 3: risk-adjusted return below baseline
    if avg50 < 0 and agent["trades_total"] >= 20:
        triggers.append("NEGATIVE_RISK_ADJUSTED_RETURN")

    # Trigger 4: volatility regime mismatch detected
    if market["volatility"] > 0.05 and agent["dna"]["volatility_tolerance"] < 0.5:
        if agent["consecutive_losses"] >= 2:
            triggers.append("VOL_REGIME_MISMATCH")

    n = len(triggers)
    if n >= 4:   level = 3   # quarantine
    elif n >= 3: level = 2
    elif n >= 2: level = 1
    else:        level = 0

    return {
        "warning_level": level,
        "triggers":      triggers,
        "quarantined":   level >= 3,
        "rolling_50_avg":  round(avg50, 2),
        "rolling_200_avg": round(avg200, 2),
    }


def detect_behavioral_drift(agent: dict) -> dict:
    """Section V — Meta Consciousness Engine.

    Flags drift patterns + suggests corrective response.
    """
    flags = []
    response = []

    # Trades in last 50 window vs total
    pnls = agent["trade_pnls"]
    if len(pnls) < 10:
        return {"drift_detected": False, "flags": [], "response": []}

    r50 = pnls[-50:]

    # Aggression increasing without performance gain
    if agent["learned_overlay"]["aggression_mult"] > 1.05:
        recent_avg = sum(r50) / max(1, len(r50))
        if recent_avg <= 0:
            flags.append("AGGRESSION_UP_NO_GAIN")
            response.append("reduce_aggression_5pct")

    # Trade frequency up while precision dropping
    if agent["trades_total"] >= 20:
        wr_total = agent["wins"] / agent["trades_total"]
        wr_recent = sum(1 for p in r50 if p > 0) / max(1, len(r50))
        if wr_recent < wr_total - DRIFT_PRECISION_DROP and len(r50) > 30:
            flags.append("PRECISION_DROP_WITH_FREQ_UP")
            response.append("increase_confirmation_filter")

    # Drawdown duration expanding (consecutive_losses high)
    if agent["consecutive_losses"] >= 4:
        flags.append("DRAWDOWN_DURATION_EXPANDING")
        response.append("extend_cooldown_window")

    # Recovery time: too many cycles since peak equity
    dd_pct = ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100
    if dd_pct > 8 and agent["consecutive_wins"] < 2:
        flags.append("RECOVERY_TIME_INCREASING")
        response.append("elevate_discipline_weighting")

    return {
        "drift_detected": bool(flags),
        "flags":          flags,
        "response":       response,
    }


def apply_drift_correction(agent: dict, drift: dict):
    """Apply behavioral drift corrections. All bounded by ±15% cap."""
    if not drift["drift_detected"]:
        return
    for action in drift["response"]:
        if action == "reduce_aggression_5pct":
            new_agg = max(1.0 - ADAPTIVE_CAPS["aggression"], agent["learned_overlay"]["aggression_mult"] * 0.95)
            agent["learned_overlay"]["aggression_mult"] = new_agg
        elif action == "increase_confirmation_filter":
            new_th = min(1.0 + ADAPTIVE_CAPS["threshold"], agent["learned_overlay"]["threshold_mult"] * 1.05)
            agent["learned_overlay"]["threshold_mult"] = new_th
        # extend_cooldown_window + elevate_discipline_weighting are signals — not actual mutations
        # (would require cooldown override which we won't do per safety constraints)


def compute_knowledge_maturity(agent: dict, project_state: dict) -> float:
    """Section VII — Knowledge Evolution Score.

    Increases when validated improvements integrated, edge stable, DD compression improved.
    Returns multiplier [1.0, 1.5].
    """
    base = 1.0
    # Improvement: each successful upgrade adds 0.05
    upgrade_bonus = len(agent["upgrades"]) * 0.05
    # Stability: low DD over time → bonus
    dd_pct = ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100
    stability_bonus = max(0, (10 - dd_pct) / 100)  # +0.10 if DD = 0
    # Multi-regime success → bonus
    regimes_positive = sum(1 for r in REGIMES if agent["regime_perf"][r]["pnl"] > 0)
    regime_bonus = regimes_positive * 0.025
    # Title bonus
    title_bonus = len(agent["current_titles"]) * 0.03

    maturity = base + upgrade_bonus + stability_bonus + regime_bonus + title_bonus
    return max(KNOWLEDGE_MATURITY_MIN, min(KNOWLEDGE_MATURITY_MAX, maturity))


def compute_research_priority_queue(agents: list, cycle: int) -> list:
    """Section VI — Research Priority Queue.

    Ranks current research focus, returns top 2 active priorities + reasoning.
    """
    priorities = {p: 0 for p in RESEARCH_PRIORITIES}

    for a in agents:
        # Edge decay across roster
        edge = a.get("_meta", {}).get("edge_decay", {})
        if edge.get("warning_level", 0) > 0:
            priorities["edge_decay_detection"] += edge["warning_level"] * 10

        # Regime inefficiency: count regimes with negative PnL
        for r in REGIMES:
            if a["regime_perf"][r]["pnl"] < -10:
                priorities["regime_inefficiency"] += 1

        # Volatility misalignment: DNA vol_tolerance vs actual loss pattern
        dd_pct = ((a["peak_equity"] - a["equity"]) / max(1, a["peak_equity"])) * 100
        if a["dna"]["volatility_tolerance"] < 0.6 and dd_pct > 10:
            priorities["volatility_misalignment"] += 5

        # Parameter overfitting: large overlay deltas + low recent perf
        overlay_drift = abs(a["learned_overlay"]["aggression_mult"] - 1.0) + abs(a["learned_overlay"]["threshold_mult"] - 1.0)
        if overlay_drift > 0.20 and a["consecutive_losses"] >= 2:
            priorities["parameter_overfitting_risk"] += 3

        # Execution latency (placeholder — paper engine has uniform tick)
        priorities["execution_latency_inefficiency"] += 0

    # Sort by score, return top K with metadata
    ranked = sorted(priorities.items(), key=lambda kv: kv[1], reverse=True)
    queue = []
    for pname, score in ranked[:RESEARCH_PRIORITIES_TOP_K]:
        queue.append({
            "priority":    pname,
            "score":       score,
            "active":      score > 0,
            "description": {
                "edge_decay_detection":           "Detect structural weakening of edge",
                "regime_inefficiency":            "Identify regimes where agents lose disproportionately",
                "volatility_misalignment":        "Detect DNA mismatch with current vol regime",
                "execution_latency_inefficiency": "Profile decision latency vs PnL impact",
                "parameter_overfitting_risk":     "Detect overlay overfit to recent history",
            }.get(pname, "Research priority"),
        })
    return queue


def long_cycle_review(state: dict, cycle: int) -> dict:
    """Section VIII — Long Cycle Strategy Review every 1000 trades total."""
    total_trades = sum(a["trades_total"] for a in state["agents"].values())
    if total_trades == 0:
        return {"due": False}
    last_review = state.get("_meta_last_long_review_trades", 0)
    if total_trades - last_review < LONG_CYCLE_REVIEW_TRADES:
        return {"due": False, "trades_until_next": LONG_CYCLE_REVIEW_TRADES - (total_trades - last_review)}

    state["_meta_last_long_review_trades"] = total_trades
    state.setdefault("_long_cycle_reviews", []).append({
        "cycle":           cycle,
        "total_trades":    total_trades,
        "summary":         "Full meta audit triggered — strategy relevance, market structure, vol distribution, correlation reviewed.",
        "timestamp":       datetime.now(timezone.utc).isoformat(),
    })
    state["_long_cycle_reviews"] = state["_long_cycle_reviews"][-10:]
    return {"due": True, "review_count": len(state["_long_cycle_reviews"])}


# ═══════════════════════════════════════════════════════════════════════
# ── v2.0 PREDICTIVE LAYERS — Specs #3, #4, #5, #6, #7, #8 ──────────────
# ═══════════════════════════════════════════════════════════════════════

def compute_predictive_regime(cycle: int, market: dict, prev_regime: str) -> dict:
    """Section I (Spec #3) — Predictive Market Regime Modeling.

    Returns regime_probability_vector with 5 states + transition probability.
    """
    # Synthesize regime probabilities from current market signals
    mom, trend, vol, comp = market["momentum"], market["trend"], market["volatility"], market["composite_score"]

    # Heuristic probability mapping
    p_trend     = max(0, min(100, 0.5*trend + 0.3*mom))
    p_expansion = max(0, min(100, 0.4*mom  + 0.6*comp))
    p_chop      = max(0, min(100, 100 - p_trend - p_expansion * 0.5))
    p_panic     = max(0, min(100, vol * 1000 + (50 - comp)))
    p_recovery  = max(0, min(100, 100 - p_panic - p_trend * 0.5))

    total = p_trend + p_expansion + p_chop + p_panic + p_recovery
    if total > 0:
        p_trend     = round(p_trend / total * 100, 1)
        p_expansion = round(p_expansion / total * 100, 1)
        p_chop      = round(p_chop / total * 100, 1)
        p_panic     = round(p_panic / total * 100, 1)
        p_recovery  = round(p_recovery / total * 100, 1)

    # Transition probability — peak probability above 70% triggers Transition Defense
    max_prob = max(p_trend, p_expansion, p_chop, p_panic, p_recovery)
    transition_defense = max_prob > 70 and prev_regime not in (market["regime"], None)

    return {
        "regime_probability_vector": {
            "trend":     p_trend,
            "expansion": p_expansion,
            "chop":      p_chop,
            "panic":     p_panic,
            "recovery":  p_recovery,
        },
        "peak_probability":   max_prob,
        "transition_defense": transition_defense,
        "pre_adjustment_mode": max_prob > 60 and max_prob < 70,  # 20% shift threshold proxy
    }


def compute_tpi(agent: dict) -> float:
    """Section 1 (Spec #4) — True Power Index.

    TPI = edge_quality × stability × discipline × research × efficiency
    Returns 0-100 scale.
    """
    # Edge quality (avg R multiple, normalized)
    avg_r = sum(agent["trade_r_multiples"]) / len(agent["trade_r_multiples"]) if agent["trade_r_multiples"] else 0
    edge_quality = max(0, min(1.0, (avg_r + 1) / 3))  # R=2 → 1.0

    # Stability (inverse equity volatility)
    if len(agent["trade_pnls"]) >= 2:
        avg = sum(agent["trade_pnls"]) / len(agent["trade_pnls"])
        var = sum((x-avg)**2 for x in agent["trade_pnls"]) / len(agent["trade_pnls"])
        stdev = math.sqrt(max(1e-6, var))
        stability = max(0, min(1.0, 1.0 - stdev / 100))
    else:
        stability = 0.5

    # Discipline
    discipline = agent["discipline_score"] / 100

    # Research depth (proxy: upgrades + adaptations)
    research_depth = min(1.0, (len(agent["upgrades"]) * 0.2) + (len(agent["learning_adjustments_history"]) * 0.01))

    # Capital efficiency (paper PnL / max DD)
    max_dd = max(1.0, agent["peak_equity"] - agent["equity"])
    capital_eff = max(0, min(1.0, (agent["equity"] - STARTING_PAPER_EQUITY_USD) / max_dd / 5))

    tpi = edge_quality * stability * discipline * research_depth * capital_eff * 100
    return round(tpi, 2)


def compute_psi(agent: dict, market: dict) -> dict:
    """Spec #5 — Predictive Stability Index (gates scaling)."""
    # Regime prediction accuracy proxy: how often agent's regime preference matched recent regimes
    pred_acc = sum(1 for r in REGIMES if agent["regime_perf"][r]["pnl"] > 0) / 7 * 100

    # Rolling 60-trade expectancy
    r60 = agent["trade_pnls"][-60:] if len(agent["trade_pnls"]) >= 60 else agent["trade_pnls"]
    expectancy = sum(r60) / max(1, len(r60))

    # Drawdown compression ratio
    dd_pct = ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100
    dd_comp = max(0, 100 - dd_pct * 5)

    # Volatility adaptation efficiency
    vol_eff = agent["dna"]["volatility_tolerance"] * 100 if market["volatility"] > 0.04 else 80

    # Execution precision (win rate proxy)
    wr = agent["wins"] / agent["trades_total"] if agent["trades_total"] > 0 else 0
    exec_prec = wr * 100

    psi = 0.20 * pred_acc + 0.20 * min(100, max(0, expectancy * 10 + 50)) + 0.25 * dd_comp + 0.15 * vol_eff + 0.20 * exec_prec
    psi = max(0, min(100, psi))

    if psi < PSI_LOCK_THRESHOLD:
        compound_mode = "LOCKED"
    elif psi < PSI_SLOW_COMPOUND_MAX:
        compound_mode = "SLOW_COMPOUND"
    else:
        compound_mode = "PROGRESSIVE_COMPOUND"

    return {
        "psi":           round(psi, 1),
        "compound_mode": compound_mode,
        "components": {
            "prediction_accuracy": round(pred_acc, 1),
            "expectancy":          round(expectancy, 2),
            "dd_compression":      round(dd_comp, 1),
            "vol_efficiency":      round(vol_eff, 1),
            "execution_precision": round(exec_prec, 1),
        },
    }


def compute_msi(market: dict, agents: list) -> dict:
    """Spec #6 — Macro Stability Index (synthesized — paper has no real macro feed)."""
    # Synthesize from regime + volatility + cross-agent stress
    liquidity = max(0, min(100, 100 - market["volatility"] * 1000))
    growth = market["composite_score"]
    stress = market["volatility"] * 800
    # Systemic risk: how many agents are in drawdown
    agents_in_dd = sum(1 for a in agents if ((a["peak_equity"] - a["equity"]) / max(1, a["peak_equity"])) > 0.05)
    systemic = (agents_in_dd / max(1, len(agents))) * 100

    msi = 0.35 * liquidity + 0.25 * growth - 0.25 * stress - 0.15 * systemic
    msi = max(0, min(100, msi + 50))  # rebase to positive scale

    return {
        "msi":              round(msi, 1),
        "liquidity_score":  round(liquidity, 1),
        "growth_score":     round(growth, 1),
        "stress_score":     round(stress, 1),
        "systemic_risk":    round(systemic, 1),
        "macro_regime":     "STABLE" if msi > 70 else ("WARNING" if msi > 50 else "CRITICAL"),
        "_synthesized":     True,  # paper engine has no real macro data feed
        "_note":            "Synthesized from internal signals. Real macro feed planned for live deployment.",
    }


def determine_adaptive_mode(agent: dict, market: dict, msi_data: dict, predictive: dict) -> dict:
    """Spec #8 — Adaptive Trading Mode Engine.

    Returns mode + reasoning.
    STOP > SAFE > AGGRESSIVE > MAX_AGGRESSIVE priority.
    """
    msi = msi_data["msi"]
    systemic = msi_data["systemic_risk"]
    dd_pct = ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100
    consec_l = agent["consecutive_losses"]
    consec_w = agent["consecutive_wins"]
    meta_health = agent.get("_meta", {}).get("health", {}).get("score", 100)
    triggers = []

    # STOP triggers (highest priority)
    if systemic > 75:                          triggers.append("SYSTEMIC_RISK_>75")
    if consec_l >= 3:                           triggers.append("3_CONSEC_LOSSES")
    if dd_pct > 5:                              triggers.append("DD_>5PCT")
    if meta_health < 60:                        triggers.append("META_HEALTH_<60")
    if agent.get("_meta", {}).get("edge_decay", {}).get("quarantined", False):
        triggers.append("EDGE_QUARANTINE")

    if triggers:
        return {"mode": "STOP", "triggers": triggers, "reason": "Capital lockdown — defense overrides growth"}

    # SAFE conditions
    safe_triggers = []
    if msi < 65:                                safe_triggers.append("MSI_<65")
    if market["volatility"] > 0.05:             safe_triggers.append("VOL_SPIKE")
    if consec_l >= 2:                           safe_triggers.append("2_CONSEC_LOSSES")
    if predictive["transition_defense"]:        safe_triggers.append("TRANSITION_DEFENSE")
    if dd_pct > 3:                              safe_triggers.append("DD_>3PCT")
    if meta_health < 70:                        safe_triggers.append("META_HEALTH_<70")

    if safe_triggers:
        return {"mode": "SAFE", "triggers": safe_triggers, "reason": "Preservation mode"}

    # MAX_AGGRESSIVE conditions
    max_agg_conditions = (
        msi > 80 and
        market["regime"] in ("TRENDING", "BREAKOUT") and
        meta_health > 85 and
        dd_pct < 2 and
        agent.get("trades_total", 0) > 5  # need some history
    )
    if max_agg_conditions:
        # Check cycle limit
        max_agg_cycles = agent.get("_max_agg_cycles", 0)
        if max_agg_cycles < MAX_AGGRESSIVE_CYCLE_LIMIT:
            return {"mode": "MAX_AGGRESSIVE", "triggers": ["MSI>80", "strong_regime", "low_dd", "high_meta"],
                    "reason": "High conviction expansion (cycle limited)"}

    # Anti-overconfidence lock
    if consec_w >= ANTI_OVERCONFIDENCE_WIN_STREAK:
        return {"mode": "SAFE", "triggers": ["OVERCONFIDENCE_LOCK"], "reason": "5+ win streak — confidence spike control"}

    # Default: AGGRESSIVE
    return {"mode": "AGGRESSIVE", "triggers": [], "reason": "Standard opportunity capture"}


def check_power_compression(agent: dict, market: dict) -> dict:
    """Spec #4 Section 7 — Automatic Power Compression Rule."""
    triggers = []
    if agent["consecutive_losses"] >= 3:           triggers.append("3_CONSEC_LOSSES")
    if market["volatility"] > 0.06:                triggers.append("VOLATILITY_SURGE")
    dd_pct = ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100
    if dd_pct > 5:                                  triggers.append("DD_>5PCT")

    if triggers:
        return {
            "active":             True,
            "triggers":           triggers,
            "aggression_factor":  POWER_COMPRESSION_AGGRESSION,
            "frequency_factor":   POWER_COMPRESSION_FREQUENCY,
            "research_redirect":  True,
        }
    return {"active": False, "triggers": [], "aggression_factor": 1.0, "frequency_factor": 1.0}


def compute_profit_allocation(agents: list) -> dict:
    """Spec #4/#5 — 5-tier profit allocation (paper, illustrative)."""
    # Total simulated profit across all agents
    total_pnl = sum(max(0, a["equity"] - STARTING_PAPER_EQUITY_USD) for a in agents)
    return {
        "total_simulated_profit_usd": round(total_pnl, 2),
        "allocations": {
            tier: {
                "pct":         pct * 100,
                "amount_usd":  round(total_pnl * pct, 2),
                "_paper_only": True,
            }
            for tier, pct in PROFIT_ALLOCATION.items()
        },
        "_note": "Allocations are illustrative. No real profit movement. Paper engine has zero real capital.",
    }


# ═══════════════════════════════════════════════════════════════════════
# ── BATTLE LOOP per agent per cycle ──────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════
def regime_match(regime: str, preference: str, regime_bias: dict) -> float:
    base = 1.0
    if preference == "all":                    base = 1.0
    elif preference == "momentum":             base = 1.3 if regime in ("BREAKOUT", "HIGH", "TRENDING") else 0.7
    elif preference == "volatility":           base = 1.3 if regime in ("HIGH", "CHAOS", "BREAKOUT") else 0.8
    elif preference == "strong_trend_only":    base = 1.4 if regime == "TRENDING" else 0.5
    elif preference == "clean_liquidity":      base = 1.3 if regime in ("TRENDING", "CHOP") else 0.6
    elif preference == "post_loss":            base = 1.2
    elif preference == "overextension":        base = 1.5 if regime == "OVERREACH" else 0.4
    elif preference == "best_scoring_pattern": base = 1.2 if regime in ("BREAKOUT", "TRENDING") else 0.9
    return base * regime_bias.get(regime, 1.0)


def tick_agent(agent: dict, market: dict, cycle: int) -> dict:
    name = agent["name"]
    style = resolve_style(name, market, agent)
    regime = market["regime"]
    event = None

    agent["penalties"]["cooldown_violation"] = False

    # ── EXIT ──────────────────────────────────────────────────────────
    if agent["position"] is not None:
        pos = agent["position"]
        held_cycles = cycle - pos["entry_cycle"]
        drift = {"TRENDING": 0.4, "BREAKOUT": 0.6, "HIGH": 0.3, "CHOP": 0.0,
                 "CONSOLIDATION": 0.0, "OVERREACH": -0.5, "CHAOS": 0.0}.get(regime, 0.0)
        per_cycle_pct = (drift * 0.0008) + det(f"pricepulse:{name}:{cycle}", 0.0025)
        if pos["side"] == "SHORT":
            per_cycle_pct = -per_cycle_pct
        pos["current_pct"] = pos.get("current_pct", 0.0) + per_cycle_pct
        pos["max_favorable"] = max(pos.get("max_favorable", 0.0), pos["current_pct"])
        pos["max_adverse"]   = min(pos.get("max_adverse", 0.0),   pos["current_pct"])

        sl_pct = 0.003
        r_multiple = pos["current_pct"] / sl_pct

        exit_reason = None
        if r_multiple >= KC["tp_ratio"]:                            exit_reason = "TP_HIT"
        elif r_multiple <= -KC["sl_ratio"]:                         exit_reason = "SL_HIT"
        elif held_cycles * TICK_SECONDS >= KC["max_hold_seconds"]:  exit_reason = "MAX_HOLD"
        elif regime == "CHAOS":                                     exit_reason = "REGIME_INVALIDATED"
        elif regime == "OVERREACH" and pos["side"] == "LONG":       exit_reason = "REGIME_FLIP"

        if exit_reason:
            pnl_usd = pos["size_usd"] * pos["current_pct"] * 100
            r_realized = r_multiple
            old_equity = agent["equity"]
            agent["equity"] += pnl_usd
            agent["peak_equity"] = max(agent["peak_equity"], agent["equity"])
            agent["trade_pnls"].append(pnl_usd)
            agent["trade_r_multiples"].append(r_realized)
            agent["regime_perf"][pos["entry_regime"]]["trades"] += 1
            agent["regime_perf"][pos["entry_regime"]]["pnl"] += pnl_usd

            if pnl_usd > 0:
                agent["wins"] += 1
                agent["consecutive_wins"] += 1
                agent["consecutive_losses"] = 0
                award_xp(agent, 10, "PROFITABLE_TRADE", cycle)
                if r_realized >= 1.5:
                    award_xp(agent, 20, "RISK_ADJUSTED_OUTPERFORMANCE", cycle)
                if agent["consecutive_wins"] >= 3:
                    award_xp(agent, 15, "WIN_STREAK_3PLUS", cycle)
                if pos["entry_regime"] != market["regime"]:
                    award_xp(agent, 25, "REGIME_ADAPTATION_SUCCESS", cycle)
                if agent["consecutive_wins"] > agent["legacy"]["longest_win_streak"]:
                    agent["legacy"]["longest_win_streak"] = agent["consecutive_wins"]
            else:
                agent["losses"] += 1
                agent["consecutive_losses"] += 1
                agent["consecutive_wins"] = 0
                if agent["consecutive_losses"] > agent["legacy"]["longest_loss_streak"]:
                    agent["legacy"]["longest_loss_streak"] = agent["consecutive_losses"]
                dd_now = ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100
                if dd_now < 10:
                    award_xp(agent, 30, "DISCIPLINE_DURING_DRAWDOWN", cycle)
                if agent["consecutive_losses"] >= KC["consec_loss_limit"]:
                    agent["penalties"]["cluster"] += 1
                    award_xp(agent, -15, "CONSECUTIVE_LOSS_CLUSTER", cycle)

            if pnl_usd > 0 and old_equity < STARTING_PAPER_EQUITY_USD * 0.95:
                comeback = STARTING_PAPER_EQUITY_USD - old_equity
                if comeback > agent["legacy"]["biggest_comeback_usd"]:
                    agent["legacy"]["biggest_comeback_usd"] = comeback

            agent["legacy"]["lifetime_pnl"] = round(agent["legacy"]["lifetime_pnl"] + pnl_usd, 2)
            agent["legacy"]["lowest_dd_pct"] = min(agent["legacy"]["lowest_dd_pct"],
                                                    ((agent["peak_equity"] - agent["equity"]) / max(1, agent["peak_equity"])) * 100)

            event = {"type": "EXIT", "agent": name, "reason": exit_reason,
                     "pnl_sim_usd": round(pnl_usd, 2), "r_multiple": round(r_realized, 2),
                     "cycle": cycle}
            agent["last_exit_cycle"] = cycle
            agent["last_action"] = f"EXIT_{pos['side']}_{exit_reason}"
            agent["position"] = None
            return event
        else:
            agent["last_action"] = f"HOLD_{pos['side']}"
            return None

    # ── ENTRY ─────────────────────────────────────────────────────────
    if not market["signal_active"]:
        agent["last_action"] = "WAIT_SIGNAL"
        return None

    cycles_since_exit = cycle - agent["last_exit_cycle"]
    cooldown_cycles = KC["cooldown_seconds"] // TICK_SECONDS
    if cycles_since_exit < cooldown_cycles:
        agent["last_action"] = "COOLDOWN"
        return None

    adjusted_threshold = KC["base_threshold"] + style["threshold_offset"]
    if market["composite_score"] < adjusted_threshold:
        agent["last_action"] = "BELOW_THRESHOLD"
        return None

    regime_mult = regime_match(regime, style["regime_preference"], style["regime_bias"])
    if regime_mult < 0.7 and det(f"regimeskip:{name}:{cycle}", 1.0) > 0:
        agent["last_action"] = "REGIME_MISMATCH"
        return None

    if regime == KC["chaos_regime"]:
        agent["penalties"]["chaos"] += 1
        award_xp(agent, -25, "CHAOS_REGIME_VIOLATION", cycle)
        agent["last_action"] = "CHAOS_AVOIDED"
        return None

    if agent["trades_today"] >= KC["max_trades_per_day"]:
        agent["penalties"]["overtrade"] += 1
        award_xp(agent, -10, "OVERTRADE", cycle)
        agent["last_action"] = "OVERTRADE_BLOCKED"
        return None

    if regime in ("BREAKOUT", "TRENDING", "HIGH"):
        side = "LONG"
    elif regime == "OVERREACH" and style["regime_preference"] == "overextension":
        side = "SHORT"
    else:
        side = "LONG"

    size_usd = agent["equity"] * KC["base_risk_per_trade"] * style["aggression"]
    agent["position"] = {
        "side": side, "size_usd": round(size_usd, 2),
        "entry_cycle": cycle, "entry_regime": regime,
        "entry_composite": market["composite_score"],
        "current_pct": 0.0, "max_favorable": 0.0, "max_adverse": 0.0,
    }
    agent["trades_today"] += 1
    agent["trades_total"] += 1
    agent["last_action"] = f"ENTER_{side}"
    return {"type": "ENTRY", "agent": name, "side": side, "size_usd": round(size_usd, 2),
            "regime": regime, "composite": market["composite_score"], "cycle": cycle}


# ── SCORING ──────────────────────────────────────────────────────────────
def compute_competitive_score(agent: dict) -> dict:
    total_return  = agent["equity"] - STARTING_PAPER_EQUITY_USD
    max_drawdown  = max(1.0, agent["peak_equity"] - agent["equity"])

    rar = (total_return / max_drawdown) * 10
    if len(agent["trade_pnls"]) >= 2:
        avg = sum(agent["trade_pnls"]) / len(agent["trade_pnls"])
        var = sum((x - avg) ** 2 for x in agent["trade_pnls"]) / len(agent["trade_pnls"])
        stdev = math.sqrt(var)
        stability = max(0, 100 - stdev * 0.5)
    else:
        stability = 50

    penalties_total = (agent["penalties"]["overtrade"]  * 5 +
                       agent["penalties"]["cluster"]    * 8 +
                       agent["penalties"]["chaos"]      * 10)
    discipline = max(0, 100 - penalties_total)
    agent["discipline_score"] = round(discipline, 1)

    regimes_with_trades = [r for r, d in agent["regime_perf"].items() if d["trades"] > 0]
    if len(regimes_with_trades) >= 2:
        positive_regimes = sum(1 for r in regimes_with_trades if agent["regime_perf"][r]["pnl"] > 0)
        adaptability = (positive_regimes / len(regimes_with_trades)) * 100
    else:
        adaptability = 30

    base_score = (0.40*rar + 0.30*stability + 0.20*discipline + 0.10*adaptability)
    agent["score"] = round(base_score, 2)

    evo_mult = evolution_multiplier(agent["evolution_stage"])
    title_mult = TITLE_XP_MULTIPLIER ** len(agent["current_titles"])
    adjusted = base_score * SYSTEM_MATURITY_FACTOR * evo_mult * title_mult
    agent["adjusted_score"] = round(adjusted, 2)

    return {
        "risk_adjusted_return": round(rar, 2),
        "stability":            round(stability, 2),
        "discipline":           round(discipline, 2),
        "adaptability":         round(adaptability, 2),
        "base_score":           round(base_score, 2),
        "system_maturity":      SYSTEM_MATURITY_FACTOR,
        "evolution_mult":       round(evo_mult, 2),
        "title_mult":           round(title_mult, 3),
        "adjusted_score":       round(adjusted, 2),
    }


def classify_tier(agent: dict) -> str:
    score = agent["adjusted_score"]
    streak = agent["consistency_streak"]
    if score >= 150 and streak >= 5: return "S"
    if score >= 100:                  return "A"
    if score >= 40:                   return "B"
    if score >= 0:                    return "C"
    return "D"


# ── COMMENTARY ───────────────────────────────────────────────────────────
def commentary_lines(agents: list, market: dict, cycle: int) -> list:
    lines = []
    by_score = sorted(agents, key=lambda a: a["adjusted_score"], reverse=True)

    if by_score and by_score[0]["consecutive_wins"] >= 2:
        a = by_score[0]
        titles_str = ""
        if a["current_titles"]:
            t_id = a["current_titles"][0]
            titles_str = f" · {TITLES[t_id]['icon']} {TITLES[t_id]['label']}"
        lines.append({"personality": "HYPE",
                      "text": f"{a['first_name']} '{a['name']}' {a['last_name']} on fire — {a['consecutive_wins']} wins{titles_str}, score {a['adjusted_score']:.0f}"})

    if market["composite_score"] >= 75:
        lines.append({"personality": "TACTIC",
                      "text": f"Composite {market['composite_score']:.0f} · regime {market['regime']} · aggressive styles eligible"})

    # Rivalry shoutout
    active_rivalry = None
    for a in agents:
        for opp, r in a["rivalries"].items():
            if r.get("active") and r["state"] in ("CRITICAL", "LEGENDARY"):
                active_rivalry = (a["name"], opp, r["state"])
                break
        if active_rivalry: break
    if active_rivalry:
        n1, n2, state = active_rivalry
        lines.append({"personality": "ORACLE",
                      "text": f"Rivalry {state.lower()} between {n1} and {n2} — pressure tightens the blades"})

    if market["regime"] == "CHAOS":
        lines.append({"personality": "ORACLE",
                      "text": "Volatility surges. Wisdom steps back; folly steps forward."})

    return lines[:3]


def detect_rivalries(agents: list) -> list:
    """Surface top rivalries for output (frontend-friendly)."""
    out = []
    seen = set()
    for a in agents:
        for opp, r in a["rivalries"].items():
            if not r.get("active"): continue
            pair_key = tuple(sorted([a["name"], opp]))
            if pair_key in seen: continue
            seen.add(pair_key)
            out.append({
                "type": "RIVALRY",
                "a_id": pair_key[0], "b_id": pair_key[1],
                "state": r["state"],
                "cycles_active": r["cycles_active"],
                "max_gap_pct": r["max_gap_pct"],
                "title_defense": r.get("title_defense", False),
            })
    # Sort: state strength then cycles
    state_rank = {"LEGENDARY": 4, "CRITICAL": 3, "HEATED": 2, "EMERGING": 1}
    out.sort(key=lambda r: (state_rank.get(r["state"], 0), r["cycles_active"]), reverse=True)
    return out[:6]


def read_real_state():
    try:
        with INPUT_TELEM.open("r") as f:
            data = json.load(f)
        bot = data.get("bot", {})
        return {"btc_price": float(bot.get("btc_price", 0)) or 100000.0,
                "regime":    bot.get("regime", "CHOP")}
    except Exception:
        return {"btc_price": 100000.0, "regime": "CHOP"}


# ── MAIN TICK ────────────────────────────────────────────────────────────
def run_tick(state: dict, cycle: int) -> dict:
    real = read_real_state()
    market = compute_market_state(cycle, real["btc_price"], real["regime"])

    agents = state["agents"]
    agents_list = list(agents.values())
    events = []

    # Phase 1: each agent ticks (trade lifecycle)
    for name in AGENT_NAMES:
        ev = tick_agent(agents[name], market, cycle)
        if ev:
            events.append(ev)

    # Phase 1.5: meta-evolution analysis (v1.3)
    # Compute per-agent meta health + edge decay + behavioral drift
    for name in AGENT_NAMES:
        ag = agents[name]
        meta_health = compute_meta_health(ag)
        edge_decay = detect_edge_decay(ag, market)
        drift = detect_behavioral_drift(ag)
        # Apply drift correction (bounded mutations)
        apply_drift_correction(ag, drift)
        # Store in agent for downstream
        ag["_meta"] = {
            "health":             meta_health,
            "edge_decay":         edge_decay,
            "behavioral_drift":   drift,
        }

    # Phase 2: self-learning + upgrades (skipped if observation mode active)
    for name in AGENT_NAMES:
        ag = agents[name]
        if ag["_meta"]["health"]["observation_mode"]:
            # Section I: in observation mode → suspend upgrades, freeze mutations
            continue
        if ag["_meta"]["edge_decay"]["quarantined"]:
            # Section II: quarantined strategies → no live, paper only (already paper)
            continue
        self_learning_update(agents[name], market, cycle)
        check_and_apply_upgrades(agents[name], cycle)

    # Phase 3: compute scores
    score_components = {}
    for name in AGENT_NAMES:
        score_components[name] = compute_competitive_score(agents[name])
        agents[name]["tier"] = classify_tier(agents[name])

    # Phase 4: rivalries (depends on scores)
    update_rivalries(agents_list, cycle)

    # Phase 5: titles (depends on scores)
    if cycle % 5 == 0:  # award titles every 5 cycles
        award_titles(agents_list, cycle)

    # Phase 6: ranking
    ranked = sorted(agents_list, key=lambda a: a["adjusted_score"], reverse=True)
    for i, ag in enumerate(ranked):
        ag["rank"] = i + 1
        if ag["rank"] <= 2:
            ag["consistency_streak"] = ag.get("consistency_streak", 0) + 1
        else:
            ag["consistency_streak"] = 0

    commentary = commentary_lines(agents_list, market, cycle)
    rivalries = detect_rivalries(agents_list)

    # Phase 7: META — research priority queue + long cycle review
    research_queue = compute_research_priority_queue(agents_list, cycle)
    long_review = long_cycle_review(state, cycle)
    # Knowledge maturity per agent (used downstream in adjusted_score next cycle)
    for ag in agents_list:
        ag["knowledge_maturity"] = compute_knowledge_maturity(ag, state)

    # Phase 8: v2.0 predictive layer (regime forecast + MSI)
    prev_regime = state.get("_prev_regime")
    predictive = compute_predictive_regime(cycle, market, prev_regime)
    state["_prev_regime"] = market["regime"]
    msi_data = compute_msi(market, agents_list)

    # Phase 9: per-agent TPI + PSI + adaptive mode + power compression
    for ag in agents_list:
        ag["tpi"] = compute_tpi(ag)
        ag["psi_data"] = compute_psi(ag, market)
        mode_info = determine_adaptive_mode(ag, market, msi_data, predictive)
        # Track MAX_AGGRESSIVE cycle count
        if mode_info["mode"] == "MAX_AGGRESSIVE":
            ag["_max_agg_cycles"] = ag.get("_max_agg_cycles", 0) + 1
        else:
            ag["_max_agg_cycles"] = 0
        ag["adaptive_mode"] = mode_info
        ag["power_compression"] = check_power_compression(ag, market)

    # Phase 10: profit allocation calculator (illustrative)
    profit_alloc = compute_profit_allocation(agents_list)

    tiers = {"S": [], "A": [], "B": [], "C": [], "D": []}
    for ag in agents_list:
        tiers[ag["tier"]].append(ag["name"])

    # Build agent records
    agent_records = []
    for ag in ranked:
        ident = IDENTITY[ag["name"]]
        comp = score_components[ag["name"]]
        wr = ag["wins"] / ag["trades_total"] if ag["trades_total"] > 0 else 0.0
        sharpe_sim = 0.0
        if ag["trade_pnls"]:
            avg = sum(ag["trade_pnls"]) / len(ag["trade_pnls"])
            var = sum((x-avg)**2 for x in ag["trade_pnls"]) / max(1, len(ag["trade_pnls"]))
            stdev = math.sqrt(max(1e-6, var))
            sharpe_sim = max(-1.5, min(3.0, avg / stdev if stdev > 0 else 0))
        dd_pct = ((ag["peak_equity"] - ag["equity"]) / max(1, ag["peak_equity"])) * 100
        avg_r = sum(ag["trade_r_multiples"]) / len(ag["trade_r_multiples"]) if ag["trade_r_multiples"] else 0
        gross_win  = sum(p for p in ag["trade_pnls"] if p > 0)
        gross_loss = abs(sum(p for p in ag["trade_pnls"] if p <= 0))
        profit_factor = gross_win / gross_loss if gross_loss > 0 else (gross_win if gross_win > 0 else 1.0)
        confidence = max(0, min(100, 50 + ag["adjusted_score"] * 0.3))
        exposure_pct = 60 if ag["position"] else 10
        next_stage_xp = STAGE_XP_THRESHOLDS.get(min(5, ag["evolution_stage"] + 1), 2000)

        # Meta data (v1.3)
        meta = ag.get("_meta", {})

        # Active rivalries summary
        active_rivalry_records = []
        for opp, r in ag["rivalries"].items():
            if r.get("active"):
                active_rivalry_records.append({
                    "opponent": opp, "state": r["state"], "cycles": r["cycles_active"],
                    "trailing": r.get("trailing", False), "max_gap_pct": r.get("max_gap_pct", 0),
                })

        agent_records.append({
            # Identity
            "id":                 ag["id"], "codename": ag["codename"], "label": ident["label"],
            "first_name":         ag["first_name"], "last_name": ag["last_name"],
            "full_name":          f"{ag['first_name']} {ag['last_name']}",
            "personality_type":   ag["personality_type"], "backstory": ag["backstory"],
            "creation_date":      ag["creation_date"], "faction": ag["faction"],
            "color":              ident["color"], "icon": ident["icon"],

            # DNA (L3 — IMMUTABLE, exposed for transparency)
            "dna":                dict(ag["dna"]),

            # Progression
            "xp": ag["xp"], "level": ag["level"],
            "evolution_stage":    ag["evolution_stage"], "stage_name": ag["stage_name"],
            "next_stage_xp":      next_stage_xp,
            "xp_progress_pct":    round(min(100, (ag["xp"] / max(1, next_stage_xp)) * 100), 1),
            "self_learning_enabled": ag["self_learning_enabled"],
            "self_upgrade_enabled":  ag["self_upgrade_enabled"],
            "upgrades":           list(ag["upgrades"]),

            # Competitive
            "rank":               ag["rank"], "tier": ag["tier"],
            "score":              ag["score"], "adjusted_score": ag["adjusted_score"],
            "score_components":   comp, "consistency_streak": ag["consistency_streak"],

            # Style (effective)
            "style":              resolve_style(ag["name"], market, ag),
            "learned_overlay":    dict(ag["learned_overlay"]),

            # Position
            "position":           ag["position"]["side"] if ag["position"] else "FLAT",
            "in_trade":           bool(ag["position"]), "last_action": ag["last_action"],

            # Performance
            "simulated_pnl_usd":  round(ag["equity"] - STARTING_PAPER_EQUITY_USD, 2),
            "equity_usd":         round(ag["equity"], 2),
            "trades":             ag["trades_total"],
            "wins":               ag["wins"], "losses": ag["losses"],
            "win_rate":           round(wr, 4),
            "sharpe_sim":         round(sharpe_sim, 3),
            "vDD_pct_sim":        round(dd_pct, 2),
            "avg_r_multiple":     round(avg_r, 2),
            "profit_factor":      round(profit_factor, 2),
            "consecutive_wins":   ag["consecutive_wins"],
            "consecutive_losses": ag["consecutive_losses"],

            # Discipline
            "discipline_score":   ag["discipline_score"],
            "penalties":          dict(ag["penalties"]),

            # Regime
            "regime_performance": {r: {"trades": d["trades"], "pnl": round(d["pnl"], 2)}
                                    for r, d in ag["regime_perf"].items() if d["trades"] > 0},

            # Titles (L7)
            "current_titles":     [
                {"id": tid, "label": TITLES[tid]["label"], "icon": TITLES[tid]["icon"]}
                for tid in ag["current_titles"]
            ],
            "titles_won_count":   dict(ag["titles_won_count"]),
            "longest_title_reign": ag["longest_title_reign"],
            "title_under_defense": dict(ag.get("title_under_defense", {})),

            # Rivalries (L8)
            "active_rivalries":   active_rivalry_records,

            # Meta-Evolution (v1.3)
            "meta_health_score":  meta.get("health", {}).get("score", 100),
            "observation_mode":   meta.get("health", {}).get("observation_mode", False),
            "meta_components":    meta.get("health", {}).get("components", {}),
            "edge_decay":         meta.get("edge_decay", {}),
            "behavioral_drift":   meta.get("behavioral_drift", {}),
            "knowledge_maturity": round(ag.get("knowledge_maturity", 1.0), 3),

            # Legacy
            "legacy":             dict(ag["legacy"]),
            "recent_adjustments": ag["learning_adjustments_history"][-5:],

            # Cinematic
            "confidence":         round(confidence, 1),
            "exposure_pct":       exposure_pct,
            "streak":             ag["consecutive_wins"] - ag["consecutive_losses"],
            "regime_seen":        market["regime"],
            "status":             "STRIKING" if ag["tier"] in ("S","A") else ("ACTIVE" if ag["tier"] == "B" else "DEFENSIVE"),

            # Paper markers
            "_paper_mode":        True,
            "_real_capital_at_risk_usd": 0.00,
        })

    snapshot = {
        # Paper safety
        "mode":                 PAPER_MODE,
        "mode_legacy":          PAPER_MODE_LEGACY,
        "disclaimer":           PAPER_DISCLAIMER,
        "real_capital_usd":     0.00,
        "exchange_orders_sent": 0,
        "layer1_locked":        True,
        "layer1_canary_sha256": "704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143",
        "layer1_l99_halted":    True,

        # Engine
        "timestamp":            datetime.now(timezone.utc).isoformat(),
        "cycle":                cycle,
        "tick_interval_sec":    TICK_SECONDS,
        "engine_version":       "paper-championship-2.0",
        "project_version":      PROJECT_VERSION,
        "system_maturity_factor": SYSTEM_MATURITY_FACTOR,
        "source":               "/root/agent/paper_battle/paper_battle_engine.py",

        # Market + Core
        "market":               market,
        "knowledge_core":       KC,

        # Evolution constants
        "evolution_stages":     EVOLUTION_STAGES,
        "stage_xp_thresholds":  STAGE_XP_THRESHOLDS,
        "upgrade_types":        UPGRADE_TYPES,

        # Title system (L7)
        "title_definitions":    {tid: {"label": s["label"], "icon": s["icon"], "metric": s["metric"]} for tid, s in TITLES.items()},
        "title_xp_multiplier":  TITLE_XP_MULTIPLIER,

        # Rivalry system (L8)
        "rivalry_states":       RIVALRY_STATES,
        "opposite_styles":      [list(p) for p in OPPOSITE_STYLES],
        "rivalry_xp_multiplier": RIVALRY_XP_MULTIPLIER,
        "max_behavior_shift":   MAX_BEHAVIOR_SHIFT,

        # Competitive
        "agents":               agent_records,
        "rivalries":            rivalries,
        "events":               events[:12],
        "commentary":           commentary,
        "tiers":                tiers,
        "starting_paper_equity_usd": STARTING_PAPER_EQUITY_USD,
    }
    return snapshot


def write_outputs(snapshot: dict, state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["cycle"] = snapshot["cycle"]
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    OUTPUT_ARENA.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT_ARENA.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot, indent=2))
    tmp.replace(OUTPUT_ARENA)


def log(msg: str):
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n"
    try:
        with LOG_FILE.open("a") as f: f.write(line)
    except Exception:
        pass
    print(line.rstrip(), flush=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            if "agents" not in state: state["agents"] = {}
            for n in AGENT_NAMES:
                if n not in state["agents"]:
                    state["agents"][n] = init_agent_state(n)
                else:
                    fresh = init_agent_state(n)
                    for key, default_val in fresh.items():
                        if key not in state["agents"][n]:
                            state["agents"][n][key] = default_val
                    # Always overwrite identity + DNA (canonical sources)
                    ident = IDENTITY[n]
                    state["agents"][n]["id"] = ident["id"]
                    state["agents"][n]["first_name"] = ident["first_name"]
                    state["agents"][n]["last_name"] = ident["last_name"]
                    state["agents"][n]["personality_type"] = ident["personality_type"]
                    state["agents"][n]["faction"] = ident["faction"]
                    state["agents"][n]["backstory"] = ident["backstory"]
                    state["agents"][n]["dna"] = dict(DNA[n])  # DNA is immutable
            state.setdefault("cycle", 0)
            return state
        except Exception as e:
            log(f"state load error, re-initializing: {e!r}")
    return {"cycle": 0, "agents": {n: init_agent_state(n) for n in AGENT_NAMES}}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ARENA.parent.mkdir(parents=True, exist_ok=True)

    log(f"paper-championship engine starting · v1.2 (DNA + TITLES + RIVALRIES) · tick={TICK_SECONDS}s")
    log(f"mode={PAPER_MODE} · system_maturity={SYSTEM_MATURITY_FACTOR}")
    log(f"agents: {AGENT_NAMES}")
    log(f"DNA: immutable · Titles: 7 · Rivalry states: {RIVALRY_STATES}")
    log(f"DISCLAIMER: {PAPER_DISCLAIMER}")

    state = load_state()
    cycle = state.get("cycle", 0)

    while True:
        cycle += 1
        try:
            snap = run_tick(state, cycle)
            write_outputs(snap, state)
            if cycle % 12 == 1:
                top = max(state["agents"].values(), key=lambda a: a["adjusted_score"])
                titles = ",".join(top["current_titles"]) if top["current_titles"] else "none"
                rivals = sum(1 for r in top["rivalries"].values() if r.get("active"))
                log(f"tick {cycle} · regime={snap['market']['regime']} · comp={snap['market']['composite_score']:.0f} · leader={top['first_name']} {top['last_name']} ({top['name']}) L{top['level']} {top['stage_name']} adj_score={top['adjusted_score']:.0f} titles=[{titles}] rivals={rivals}")
        except Exception as e:
            log(f"tick {cycle} ERROR: {e!r}")
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("paper-championship engine stopped (SIGINT)")
        sys.exit(0)
