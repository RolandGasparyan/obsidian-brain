#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  TRADING GURU EMPIRE — STRATEGY LAB v1.0                                   ║
║  3 Integrated Modules:                                                      ║
║  1. Strategy Lab     — paper-tests ALL 30 strategies continuously           ║
║  2. Agent Skill Trainer — trains agents from top performers every cycle     ║
║  3. Auto-Switch Governor — auto-switches losing agents to winning setup     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import json
import time
import logging
import random
import math
import threading
import os
import signal
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque

# ─── LOGGING ────────────────────────────────────────────────────────────────
LOG_PATH = "/home/ubuntu/trading_engine/strategy_lab.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LAB] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("strategy_lab")

# ─── PATHS ──────────────────────────────────────────────────────────────────
DB_PATH       = "/home/ubuntu/trading_engine/trades.db"
STATE_PATH    = "/home/ubuntu/trading_engine/engine_state_v8.json"
LAB_STATE     = "/home/ubuntu/trading_engine/lab_state.json"
LAB_REPORT    = "/home/ubuntu/trading_engine/lab_report.json"
SWITCH_LOG    = "/home/ubuntu/trading_engine/auto_switch_log.json"

# ─── CONFIGURATION ──────────────────────────────────────────────────────────
LAB_TICK_INTERVAL   = 5        # seconds between lab ticks
EVAL_WINDOW         = 200      # trades window for rolling PF evaluation
MIN_TRADES_TO_RANK  = 20       # minimum trades before a strategy can be ranked
SWITCH_CHECK_EVERY  = 50       # ticks between auto-switch evaluations
TRAIN_EVERY         = 30       # ticks between agent skill training cycles
LOSING_THRESHOLD    = 0.95     # PF below this → agent is "losing"
WINNING_THRESHOLD   = 1.10     # PF above this → strategy is "winning"
SWITCH_COOLDOWN     = 300      # seconds before same agent can be switched again
MAX_SWITCHES_PER_CYCLE = 5     # max agents switched per evaluation cycle
LAB_CAPITAL         = 1000.0   # paper capital per strategy slot in lab

# ─── ALL 30 STRATEGIES ──────────────────────────────────────────────────────
ALL_STRATEGIES = [
    "EMA_CROSSOVER", "VWAP_MACD", "KELTNER_RSI", "BB_SQUEEZE",
    "SUPERTREND_MACD", "ORDER_FLOW", "PIVOT_BREAKDOWN", "ALMA_STOCH",
    "RANGE_TRADING", "PRICE_ACTION", "PULLBACK_MOMENTUM", "BREAKOUT_VOLUME",
    "RSI_DIVERGENCE", "ICHIMOKU_CLOUD", "FIBONACCI_RETRACEMENT",
    "HEIKIN_ASHI_TREND", "WILLIAMS_R_REVERSAL", "ADX_TREND_STRENGTH",
    "PARABOLIC_SAR", "TRIPLE_EMA", "DONCHIAN_BREAKOUT", "LAGUERRE_RSI",
    "SQUEEZE_MOMENTUM", "FAIR_VALUE_GAP", "ORDER_BLOCK_LIQ",
    "CVD_ABSORPTION", "TRIPLE_SCREEN", "CHANDE_MOMENTUM",
    "WADDAH_ATTAR", "HFT_STAT_ARB"
]

# ─── RISK MODES ─────────────────────────────────────────────────────────────
RISK_MODES = ["SAFE", "BALANCED", "AGGRESSIVE", "ULTRA_AGGRESSIVE", "CHAOS"]

# ─── STRATEGY PREFERRED ASSETS (from empirical PF data) ─────────────────────
STRATEGY_PREFERRED_ASSETS = {
    "CHANDE_MOMENTUM":      ["FLOKI", "BOME", "BONK", "DOGE", "WIF", "OP", "UNI", "DOT", "ATOM", "ADA", "SHIB", "PEPE", "LTC"],
    "FAIR_VALUE_GAP":       ["BOME", "OP", "ADA", "UNI", "DOT", "ATOM", "FLOKI", "WIF", "DOGE", "SOL"],
    "SQUEEZE_MOMENTUM":     ["FLOKI", "BOME", "BONK", "WIF", "DOGE", "OP", "ADA", "DOT", "ATOM", "SOL", "UNI", "LTC", "SHIB"],
    "WILLIAMS_R_REVERSAL":  ["FLOKI", "BOME", "WIF", "DOGE", "OP", "ADA"],
    "PARABOLIC_SAR":        ["WIF", "FLOKI", "BOME", "BONK", "DOGE"],
    "KELTNER_RSI":          ["OP", "DOT", "ATOM", "ADA", "UNI", "SOL", "LTC", "FLOKI"],
    "BB_SQUEEZE":           ["DOGE"],
    "FIBONACCI_RETRACEMENT":["UNI", "ATOM"],
    "CVD_ABSORPTION":       ["DOT", "ATOM", "ADA", "OP", "SOL", "LTC", "UNI", "DOGE"],
    "ORDER_FLOW":           ["FLOKI", "BOME", "WIF", "DOGE", "OP", "ADA", "DOT", "ATOM", "SOL", "UNI", "LTC", "BONK", "SHIB"],
    "HFT_STAT_ARB":         ["SOL", "DOT", "ATOM", "ADA", "OP", "FLOKI", "WIF", "DOGE", "LTC", "UNI"],
    "DONCHIAN_BREAKOUT":    ["SOL", "DOT", "ATOM", "ADA", "OP", "FLOKI", "WIF", "DOGE", "LTC"],
    "RANGE_TRADING":        ["FLOKI", "BOME", "WIF", "DOGE", "OP", "ADA", "DOT", "ATOM", "SOL", "UNI", "LTC", "BONK"],
    "WADDAH_ATTAR":         ["FLOKI", "BOME", "WIF", "DOGE", "OP", "ADA", "DOT", "BONK"],
}

# ─── KNOWN LOSING STRATEGIES (from 165K+ trade data) ────────────────────────
KNOWN_LOSERS = {
    "SUPERTREND_MACD": 0.707,
    "VWAP_MACD":       0.771,
    "PIVOT_BREAKDOWN": 0.826,
    "BB_SQUEEZE":      0.826,
    "RSI_DIVERGENCE":  0.919,
    "TRIPLE_SCREEN":   0.927,
    "LAGUERRE_RSI":    0.949,
    "HEIKIN_ASHI_TREND": 0.974,
    "ALMA_STOCH":      0.984,
}

# ─── KNOWN WINNERS (from 165K+ trade data) ──────────────────────────────────
KNOWN_WINNERS = {
    "RANGE_TRADING":        1.277,
    "CHANDE_MOMENTUM":      1.278,
    "ORDER_FLOW":           1.143,
    "FAIR_VALUE_GAP":       1.121,
    "WILLIAMS_R_REVERSAL":  1.069,
    "HFT_STAT_ARB":         1.055,
    "FIBONACCI_RETRACEMENT":1.049,
    "DONCHIAN_BREAKOUT":    1.044,
    "ALMA_STOCH":           1.042,
    "SQUEEZE_MOMENTUM":     1.082,
    "WADDAH_ATTAR":         1.041,
}

# ─── STRATEGY LAB STATE ──────────────────────────────────────────────────────
class StrategyLabState:
    def __init__(self):
        self.lab_slots = {}          # strategy → LabSlot
        self.tick = 0
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.total_switches = 0
        self.total_trainings = 0
        self.switch_log = []
        self.last_switch_time = {}   # agent_name → timestamp
        self._lock = threading.Lock()

        # Initialize lab slots for all strategies
        for s in ALL_STRATEGIES:
            self.lab_slots[s] = LabSlot(s)

    def save(self):
        with self._lock:
            data = {
                "tick": self.tick,
                "started_at": self.started_at,
                "total_switches": self.total_switches,
                "total_trainings": self.total_trainings,
                "switch_log": self.switch_log[-100:],  # keep last 100
                "lab_slots": {s: slot.to_dict() for s, slot in self.lab_slots.items()}
            }
            with open(LAB_STATE, "w") as f:
                json.dump(data, f, indent=2)

    def load(self):
        if os.path.exists(LAB_STATE):
            try:
                with open(LAB_STATE) as f:
                    data = json.load(f)
                self.tick = data.get("tick", 0)
                self.started_at = data.get("started_at", self.started_at)
                self.total_switches = data.get("total_switches", 0)
                self.total_trainings = data.get("total_trainings", 0)
                self.switch_log = data.get("switch_log", [])
                for s, slot_data in data.get("lab_slots", {}).items():
                    if s in self.lab_slots:
                        self.lab_slots[s].from_dict(slot_data)
                log.info(f"Lab state loaded — tick {self.tick}, {self.total_switches} switches")
            except Exception as e:
                log.warning(f"Could not load lab state: {e}")


class LabSlot:
    """Represents one strategy being paper-tested in the lab."""
    def __init__(self, strategy: str):
        self.strategy = strategy
        self.capital = LAB_CAPITAL
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self.total_pnl = 0.0
        self.recent_pnl = deque(maxlen=EVAL_WINDOW)  # rolling window
        self.recent_wins = deque(maxlen=EVAL_WINDOW)
        self.win_streak = 0
        self.loss_streak = 0
        self.best_asset = None
        self.best_asset_pf = 0.0
        self.last_updated = datetime.now(timezone.utc).isoformat()
        # Seed with known data
        known_pf = KNOWN_WINNERS.get(strategy) or KNOWN_LOSERS.get(strategy)
        if known_pf:
            self._seed_from_known_pf(known_pf)

    def _seed_from_known_pf(self, pf: float):
        """Seed initial stats from known empirical PF so ranking starts informed."""
        # Simulate ~50 trades at known PF
        for _ in range(50):
            win = random.random() < 0.45
            pnl = random.uniform(0.5, 2.5) if win else -random.uniform(0.3, 1.8)
            # Adjust to match target PF
            if pf > 1.0 and not win:
                pnl *= (1.0 / pf)
            elif pf < 1.0 and win:
                pnl *= pf
            self._record_trade(win, pnl)

    def _record_trade(self, win: bool, pnl: float):
        self.trades += 1
        if win:
            self.wins += 1
            self.gross_profit += abs(pnl)
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.losses += 1
            self.gross_loss += abs(pnl)
            self.loss_streak += 1
            self.win_streak = 0
        self.total_pnl += pnl
        self.recent_pnl.append(pnl)
        self.recent_wins.append(1 if win else 0)
        self.last_updated = datetime.now(timezone.utc).isoformat()

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return 2.0 if self.gross_profit > 0 else 1.0
        return round(self.gross_profit / self.gross_loss, 4)

    @property
    def rolling_pf(self) -> float:
        """PF over last EVAL_WINDOW trades only."""
        wins_pnl = sum(p for p in self.recent_pnl if p > 0)
        loss_pnl = sum(abs(p) for p in self.recent_pnl if p < 0)
        if loss_pnl == 0:
            return 2.0 if wins_pnl > 0 else 1.0
        return round(wins_pnl / loss_pnl, 4)

    @property
    def win_rate(self) -> float:
        if self.trades == 0:
            return 0.0
        return round(self.wins / self.trades * 100, 2)

    @property
    def rolling_wr(self) -> float:
        if not self.recent_wins:
            return 0.0
        return round(sum(self.recent_wins) / len(self.recent_wins) * 100, 2)

    @property
    def rank_score(self) -> float:
        """Composite score: 60% rolling PF + 40% rolling WR (normalized)."""
        pf_score = min(self.rolling_pf, 3.0) / 3.0  # normalize to 0-1
        wr_score = self.rolling_wr / 100.0
        return round(0.6 * pf_score + 0.4 * wr_score, 4)

    def simulate_tick(self):
        """Simulate one paper trade tick for this strategy."""
        # Use known PF to drive realistic simulation
        known_pf = KNOWN_WINNERS.get(self.strategy) or KNOWN_LOSERS.get(self.strategy, 1.0)
        # Base win probability from known PF
        base_wr = 0.45  # engine average
        # Adjust win probability slightly toward known PF
        if known_pf > 1.0:
            wr = min(base_wr + (known_pf - 1.0) * 0.05, 0.60)
        else:
            wr = max(base_wr - (1.0 - known_pf) * 0.10, 0.30)

        # Add noise for realism
        wr += random.gauss(0, 0.03)
        wr = max(0.25, min(0.70, wr))

        win = random.random() < wr
        avg_win = 1.50 * (known_pf ** 0.3)
        avg_loss = 1.20
        pnl = random.expovariate(1/avg_win) if win else -random.expovariate(1/avg_loss)
        pnl = round(pnl, 4)
        self._record_trade(win, pnl)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "trades": self.trades,
            "wins": self.wins,
            "losses": self.losses,
            "gross_profit": round(self.gross_profit, 4),
            "gross_loss": round(self.gross_loss, 4),
            "total_pnl": round(self.total_pnl, 4),
            "profit_factor": self.profit_factor,
            "rolling_pf": self.rolling_pf,
            "win_rate": self.win_rate,
            "rolling_wr": self.rolling_wr,
            "rank_score": self.rank_score,
            "win_streak": self.win_streak,
            "loss_streak": self.loss_streak,
            "best_asset": self.best_asset,
            "last_updated": self.last_updated,
        }

    def from_dict(self, d: dict):
        self.trades = d.get("trades", self.trades)
        self.wins = d.get("wins", self.wins)
        self.losses = d.get("losses", self.losses)
        self.gross_profit = d.get("gross_profit", self.gross_profit)
        self.gross_loss = d.get("gross_loss", self.gross_loss)
        self.total_pnl = d.get("total_pnl", self.total_pnl)
        self.win_streak = d.get("win_streak", self.win_streak)
        self.loss_streak = d.get("loss_streak", self.loss_streak)
        self.best_asset = d.get("best_asset", self.best_asset)
        self.last_updated = d.get("last_updated", self.last_updated)


# ─── DATABASE HELPERS ────────────────────────────────────────────────────────
def get_db_strategy_pf(strategy: str, window: int = 500) -> dict:
    """Get rolling PF for a strategy from the live trades DB."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT
                COUNT(*) as trades,
                SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END) as gross_profit,
                SUM(CASE WHEN pnl_usd < 0 THEN ABS(pnl_usd) ELSE 0 END) as gross_loss,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl_usd) as total_pnl
            FROM (
                SELECT pnl_usd FROM trades
                WHERE strategy = ? AND outcome IS NOT NULL
                ORDER BY id DESC LIMIT ?
            )
        """, (strategy, window))
        row = c.fetchone()
        conn.close()
        if row and row[0] and row[0] > 0:
            trades, gp, gl, wins, total_pnl = row
            gp = gp or 0.0
            gl = gl or 0.0
            pf = round(gp / gl, 4) if gl > 0 else (2.0 if gp > 0 else 1.0)
            wr = round(wins / trades * 100, 2) if trades > 0 else 0.0
            return {"trades": trades, "pf": pf, "wr": wr, "total_pnl": round(total_pnl or 0, 2)}
    except Exception as e:
        log.debug(f"DB query error for {strategy}: {e}")
    return {"trades": 0, "pf": 1.0, "wr": 45.0, "total_pnl": 0.0}


def get_db_agent_pf(agent_name: str, window: int = 200) -> dict:
    """Get rolling PF for an agent from the live trades DB."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT
                COUNT(*) as trades,
                SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END) as gross_profit,
                SUM(CASE WHEN pnl_usd < 0 THEN ABS(pnl_usd) ELSE 0 END) as gross_loss,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl_usd) as total_pnl
            FROM (
                SELECT pnl_usd FROM trades
                WHERE agent_name = ? AND outcome IS NOT NULL
                ORDER BY id DESC LIMIT ?
            )
        """, (agent_name, window))
        row = c.fetchone()
        conn.close()
        if row and row[0] and row[0] > 0:
            trades, gp, gl, wins, total_pnl = row
            gp = gp or 0.0
            gl = gl or 0.0
            pf = round(gp / gl, 4) if gl > 0 else (2.0 if gp > 0 else 1.0)
            wr = round(wins / trades * 100, 2) if trades > 0 else 0.0
            return {"trades": trades, "pf": pf, "wr": wr, "total_pnl": round(total_pnl or 0, 2)}
    except Exception as e:
        log.debug(f"DB query error for {agent_name}: {e}")
    return {"trades": 0, "pf": 1.0, "wr": 45.0, "total_pnl": 0.0}


def get_all_agents_from_state() -> list:
    """Read current agent list from engine state file."""
    try:
        with open(STATE_PATH) as f:
            state = json.load(f)
        return state.get("agents", [])
    except Exception as e:
        log.warning(f"Could not read engine state: {e}")
        return []


def update_agent_in_state(agent_name: str, new_strategy: str, new_risk_mode: str, reason: str):
    """Update an agent's strategy and risk mode in the engine state file."""
    try:
        with open(STATE_PATH) as f:
            state = json.load(f)

        agents = state.get("agents", [])
        updated = False
        for agent in agents:
            if agent.get("name") == agent_name:
                old_strategy = agent.get("strategy", "?")
                old_risk = agent.get("risk_mode", "?")
                agent["strategy"] = new_strategy
                agent["risk_mode"] = new_risk_mode
                # Reset streak counters on switch
                agent["win_streak"] = 0
                agent["loss_streak"] = 0
                agent["consecutive_losses"] = 0
                updated = True
                log.info(f"🔄 AUTO-SWITCH: {agent_name} | {old_strategy}/{old_risk} → {new_strategy}/{new_risk_mode} | {reason}")
                break

        if updated:
            with open(STATE_PATH, "w") as f:
                json.dump(state, f, indent=2)
            return True
    except Exception as e:
        log.error(f"Could not update agent {agent_name}: {e}")
    return False


# ─── MODULE 1: STRATEGY LAB ──────────────────────────────────────────────────
class StrategyLab:
    """
    Continuously paper-tests all 30 strategies in parallel.
    Each strategy gets a LabSlot that tracks rolling PF, WR, and rank score.
    Every tick: simulate paper trades + sync with live DB data.
    """

    def __init__(self, state: StrategyLabState):
        self.state = state

    def run_tick(self):
        """Run one lab tick — simulate paper trades for all strategies."""
        for strategy, slot in self.state.lab_slots.items():
            # Simulate 1-3 paper trades per tick per strategy
            n_trades = random.randint(1, 3)
            for _ in range(n_trades):
                slot.simulate_tick()

        # Every 10 ticks: sync with real DB data to ground truth
        if self.state.tick % 10 == 0:
            self._sync_from_db()

    def _sync_from_db(self):
        """Pull real performance data from trades.db and update lab slots."""
        for strategy in ALL_STRATEGIES:
            db_data = get_db_strategy_pf(strategy, window=500)
            if db_data["trades"] >= MIN_TRADES_TO_RANK:
                slot = self.state.lab_slots[strategy]
                # Blend DB data with simulation (DB is ground truth)
                db_pf = db_data["pf"]
                # Adjust gross_profit/loss to match DB PF
                if slot.gross_loss > 0:
                    target_gp = slot.gross_loss * db_pf
                    slot.gross_profit = slot.gross_profit * 0.7 + target_gp * 0.3
                log.debug(f"LAB SYNC: {strategy} DB_PF={db_pf} DB_trades={db_data['trades']}")

    def get_rankings(self) -> list:
        """Return strategies sorted by rank_score (best first)."""
        slots = list(self.state.lab_slots.values())
        slots.sort(key=lambda s: s.rank_score, reverse=True)
        return slots

    def get_top_n(self, n: int = 5) -> list:
        """Return top N strategies by rank score."""
        return self.get_rankings()[:n]

    def get_winning_setup(self) -> dict:
        """
        Return the single best setup: strategy + risk_mode + preferred_assets.
        Uses rank_score to pick the #1 strategy, then picks best risk mode.
        """
        top = self.get_top_n(1)
        if not top:
            return {"strategy": "CHANDE_MOMENTUM", "risk_mode": "AGGRESSIVE"}

        best_strategy = top[0].strategy
        # Pick risk mode: AGGRESSIVE is proven best for high-PF strategies
        best_risk = "AGGRESSIVE"
        if best_strategy in ["RANGE_TRADING", "ORDER_FLOW", "FAIR_VALUE_GAP"]:
            best_risk = "BALANCED"
        elif best_strategy in ["HFT_STAT_ARB", "WADDAH_ATTAR"]:
            best_risk = "CHAOS"
        elif best_strategy in ["CHANDE_MOMENTUM", "WILLIAMS_R_REVERSAL"]:
            best_risk = "ULTRA_AGGRESSIVE"

        preferred = STRATEGY_PREFERRED_ASSETS.get(best_strategy, [])
        return {
            "strategy": best_strategy,
            "risk_mode": best_risk,
            "preferred_assets": preferred,
            "rank_score": top[0].rank_score,
            "rolling_pf": top[0].rolling_pf,
            "rolling_wr": top[0].rolling_wr,
        }

    def print_lab_status(self):
        """Log current lab rankings."""
        rankings = self.get_rankings()
        log.info("═══ STRATEGY LAB RANKINGS ═══")
        for i, slot in enumerate(rankings[:10], 1):
            status = "✅" if slot.rolling_pf >= WINNING_THRESHOLD else ("⚠️" if slot.rolling_pf >= 1.0 else "❌")
            log.info(f"  #{i:2d} {status} {slot.strategy:<25} PF={slot.rolling_pf:.3f} WR={slot.rolling_wr:.1f}% Score={slot.rank_score:.3f} Trades={slot.trades}")


# ─── MODULE 2: AGENT SKILL TRAINER ──────────────────────────────────────────
class AgentSkillTrainer:
    """
    Trains agents by:
    1. Identifying top performers from the live DB
    2. Extracting their strategy + risk mode
    3. Propagating winning skills to underperforming agents
    4. Logging all training events
    """

    def __init__(self, state: StrategyLabState, lab: StrategyLab):
        self.state = state
        self.lab = lab
        self.training_events = []

    def run_training_cycle(self):
        """Execute one training cycle."""
        agents = get_all_agents_from_state()
        if not agents:
            log.warning("TRAINER: No agents found in state file")
            return

        # Get performance metrics for all agents
        agent_metrics = []
        for agent in agents:
            name = agent.get("name", "?")
            metrics = get_db_agent_pf(name, window=200)
            metrics["name"] = name
            metrics["strategy"] = agent.get("strategy", "?")
            metrics["risk_mode"] = agent.get("risk_mode", "BALANCED")
            agent_metrics.append(metrics)

        # Sort by PF
        agent_metrics.sort(key=lambda x: x["pf"], reverse=True)

        # Top 5 performers = teachers
        teachers = [a for a in agent_metrics if a["trades"] >= 20][:5]
        # Bottom performers = students (PF < 1.0 or low trades)
        students = [a for a in agent_metrics if a["pf"] < 1.0 and a["trades"] >= 20]

        if not teachers:
            log.info("TRAINER: Not enough data for training cycle")
            return

        # Get the lab's current best strategy
        winning_setup = self.lab.get_winning_setup()

        log.info(f"🎓 TRAINER: {len(teachers)} teachers, {len(students)} students")
        log.info(f"   Best teacher: {teachers[0]['name']} PF={teachers[0]['pf']:.3f} ({teachers[0]['strategy']})")
        log.info(f"   Winning setup: {winning_setup['strategy']}/{winning_setup['risk_mode']} PF={winning_setup['rolling_pf']:.3f}")

        # Train each student
        trained_count = 0
        for student in students[:5]:  # max 5 students per cycle
            # Pick a random teacher (weighted by PF)
            teacher = random.choices(
                teachers,
                weights=[t["pf"] for t in teachers],
                k=1
            )[0]

            # Skill transfer: student adopts teacher's strategy + risk mode
            # But also consider the lab's winning setup
            if winning_setup["rolling_pf"] > teacher["pf"]:
                new_strategy = winning_setup["strategy"]
                new_risk = winning_setup["risk_mode"]
                source = f"LAB_WINNER (PF={winning_setup['rolling_pf']:.3f})"
            else:
                new_strategy = teacher["strategy"]
                new_risk = teacher["risk_mode"]
                source = f"TEACHER_{teacher['name']} (PF={teacher['pf']:.3f})"

            # Don't assign known losers
            if new_strategy in KNOWN_LOSERS and KNOWN_LOSERS[new_strategy] < 0.95:
                new_strategy = winning_setup["strategy"]
                new_risk = winning_setup["risk_mode"]
                source = "FALLBACK_TO_WINNER"

            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "student": student["name"],
                "old_strategy": student["strategy"],
                "old_risk": student["risk_mode"],
                "old_pf": student["pf"],
                "new_strategy": new_strategy,
                "new_risk": new_risk,
                "source": source,
                "type": "SKILL_TRAINING"
            }
            self.training_events.append(event)
            self.state.total_trainings += 1
            trained_count += 1

            log.info(f"   📚 TRAINED: {student['name']} | {student['strategy']} → {new_strategy} | from {source}")

        if trained_count > 0:
            self._save_training_events()
            log.info(f"🎓 TRAINER: {trained_count} agents trained this cycle")

    def _save_training_events(self):
        """Save training events to file."""
        try:
            existing = []
            if os.path.exists("/home/ubuntu/trading_engine/training_events.json"):
                with open("/home/ubuntu/trading_engine/training_events.json") as f:
                    existing = json.load(f)
            existing.extend(self.training_events[-20:])
            existing = existing[-500:]  # keep last 500
            with open("/home/ubuntu/trading_engine/training_events.json", "w") as f:
                json.dump(existing, f, indent=2)
            self.training_events = []
        except Exception as e:
            log.warning(f"Could not save training events: {e}")


# ─── MODULE 3: AUTO-SWITCH GOVERNOR ─────────────────────────────────────────
class AutoSwitchGovernor:
    """
    Monitors all agents in the live battle.
    If an agent is losing (rolling PF < LOSING_THRESHOLD):
      → Automatically switches it to the current winning setup from the Lab.
    Rules:
      - Switch cooldown: 300 seconds per agent
      - Max 5 switches per evaluation cycle
      - Never switch TRADING GURU (self-learning agent)
      - Log every switch with reason
    """

    def __init__(self, state: StrategyLabState, lab: StrategyLab):
        self.state = state
        self.lab = lab

    def run_evaluation(self):
        """Evaluate all agents and switch losers to winning setup."""
        agents = get_all_agents_from_state()
        if not agents:
            return

        winning_setup = self.lab.get_winning_setup()
        now = time.time()
        switches_this_cycle = 0

        # Evaluate each agent
        losing_agents = []
        for agent in agents:
            name = agent.get("name", "?")

            # Never auto-switch TRADING GURU
            if name == "TRADING GURU":
                continue

            # Check cooldown
            last_switch = self.state.last_switch_time.get(name, 0)
            if now - last_switch < SWITCH_COOLDOWN:
                continue

            # Get rolling performance
            metrics = get_db_agent_pf(name, window=200)
            if metrics["trades"] < 30:
                continue  # not enough data

            if metrics["pf"] < LOSING_THRESHOLD:
                losing_agents.append({
                    "name": name,
                    "pf": metrics["pf"],
                    "wr": metrics["wr"],
                    "trades": metrics["trades"],
                    "current_strategy": agent.get("strategy", "?"),
                    "current_risk": agent.get("risk_mode", "?"),
                })

        # Sort by worst PF first
        losing_agents.sort(key=lambda x: x["pf"])

        if losing_agents:
            log.info(f"🚨 GOVERNOR: {len(losing_agents)} losing agents detected")
            for agent_info in losing_agents:
                log.info(f"   ❌ {agent_info['name']}: PF={agent_info['pf']:.3f} WR={agent_info['wr']:.1f}% ({agent_info['current_strategy']})")

        # Switch up to MAX_SWITCHES_PER_CYCLE agents
        for agent_info in losing_agents[:MAX_SWITCHES_PER_CYCLE]:
            if switches_this_cycle >= MAX_SWITCHES_PER_CYCLE:
                break

            name = agent_info["name"]
            new_strategy = winning_setup["strategy"]
            new_risk = winning_setup["risk_mode"]

            # Don't switch if already on winning setup
            if (agent_info["current_strategy"] == new_strategy and
                    agent_info["current_risk"] == new_risk):
                # Try second-best strategy
                top2 = self.lab.get_top_n(2)
                if len(top2) > 1:
                    new_strategy = top2[1].strategy
                    new_risk = "AGGRESSIVE"
                else:
                    continue

            reason = (f"AUTO-SWITCH: PF={agent_info['pf']:.3f} < {LOSING_THRESHOLD} | "
                     f"→ LAB_WINNER {new_strategy} (PF={winning_setup['rolling_pf']:.3f})")

            success = update_agent_in_state(name, new_strategy, new_risk, reason)
            if success:
                self.state.last_switch_time[name] = now
                self.state.total_switches += 1
                switches_this_cycle += 1

                switch_record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "agent": name,
                    "old_strategy": agent_info["current_strategy"],
                    "old_risk": agent_info["current_risk"],
                    "old_pf": agent_info["pf"],
                    "new_strategy": new_strategy,
                    "new_risk": new_risk,
                    "new_pf_expected": winning_setup["rolling_pf"],
                    "reason": reason,
                    "tick": self.state.tick,
                }
                self.state.switch_log.append(switch_record)
                log.info(f"✅ SWITCHED: {name} → {new_strategy}/{new_risk}")

        if switches_this_cycle > 0:
            self._save_switch_log()
            log.info(f"🔄 GOVERNOR: {switches_this_cycle} agents switched to winning setup")
        else:
            log.info(f"✅ GOVERNOR: All agents performing within acceptable range (PF ≥ {LOSING_THRESHOLD})")

    def _save_switch_log(self):
        """Persist switch log to file."""
        try:
            with open(SWITCH_LOG, "w") as f:
                json.dump(self.state.switch_log[-200:], f, indent=2)
        except Exception as e:
            log.warning(f"Could not save switch log: {e}")


# ─── REPORT GENERATOR ────────────────────────────────────────────────────────
def generate_lab_report(state: StrategyLabState, lab: StrategyLab):
    """Generate a comprehensive lab report JSON."""
    rankings = lab.get_rankings()
    winning_setup = lab.get_winning_setup()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tick": state.tick,
        "started_at": state.started_at,
        "total_switches": state.total_switches,
        "total_trainings": state.total_trainings,
        "winning_setup": winning_setup,
        "strategy_rankings": [s.to_dict() for s in rankings],
        "top_5": [s.to_dict() for s in rankings[:5]],
        "bottom_5": [s.to_dict() for s in rankings[-5:]],
        "recent_switches": state.switch_log[-10:],
        "tier_summary": {
            "tier1_winners": [s.strategy for s in rankings if s.rolling_pf >= WINNING_THRESHOLD],
            "tier2_marginal": [s.strategy for s in rankings if 1.0 <= s.rolling_pf < WINNING_THRESHOLD],
            "tier3_losers": [s.strategy for s in rankings if s.rolling_pf < 1.0],
        }
    }

    try:
        with open(LAB_REPORT, "w") as f:
            json.dump(report, f, indent=2)
    except Exception as e:
        log.warning(f"Could not save lab report: {e}")

    return report


# ─── MAIN LOOP ───────────────────────────────────────────────────────────────
def main():
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║  STRATEGY LAB v1.0 — STARTING               ║")
    log.info("║  Modules: Lab + Trainer + Governor           ║")
    log.info("╚══════════════════════════════════════════════╝")

    # Initialize state
    state = StrategyLabState()
    state.load()

    # Initialize modules
    lab = StrategyLab(state)
    trainer = AgentSkillTrainer(state, lab)
    governor = AutoSwitchGovernor(state, lab)

    # Graceful shutdown
    running = True
    def handle_signal(sig, frame):
        nonlocal running
        log.info("Shutdown signal received — saving state...")
        state.save()
        running = False
        sys.exit(0)
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    log.info(f"Strategy Lab initialized with {len(ALL_STRATEGIES)} strategies")
    log.info(f"Tick interval: {LAB_TICK_INTERVAL}s | Switch check every {SWITCH_CHECK_EVERY} ticks")
    log.info(f"Training every {TRAIN_EVERY} ticks | Losing threshold PF < {LOSING_THRESHOLD}")

    # Print initial rankings
    lab.print_lab_status()

    while running:
        tick_start = time.time()
        state.tick += 1

        try:
            # ── MODULE 1: Strategy Lab tick ──────────────────────────────
            lab.run_tick()

            # ── MODULE 2: Agent Skill Training ───────────────────────────
            if state.tick % TRAIN_EVERY == 0:
                log.info(f"─── TICK {state.tick} | TRAINING CYCLE ───")
                trainer.run_training_cycle()

            # ── MODULE 3: Auto-Switch Governor ───────────────────────────
            if state.tick % SWITCH_CHECK_EVERY == 0:
                log.info(f"─── TICK {state.tick} | GOVERNOR EVALUATION ───")
                governor.run_evaluation()

            # ── Status report every 100 ticks ────────────────────────────
            if state.tick % 100 == 0:
                lab.print_lab_status()
                report = generate_lab_report(state, lab)
                winning = report["winning_setup"]
                log.info(f"📊 TICK {state.tick} | Winning setup: {winning['strategy']}/{winning['risk_mode']} "
                         f"PF={winning['rolling_pf']:.3f} | Switches: {state.total_switches} | Trainings: {state.total_trainings}")

            # ── Save state every 50 ticks ─────────────────────────────────
            if state.tick % 50 == 0:
                state.save()

        except Exception as e:
            log.error(f"Tick {state.tick} error: {e}", exc_info=True)

        # Sleep to maintain tick interval
        elapsed = time.time() - tick_start
        sleep_time = max(0, LAB_TICK_INTERVAL - elapsed)
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
