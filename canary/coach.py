#!/usr/bin/env python3
"""
TEAM COACH / COORDINATOR — Trading Guru Championship
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Central brain that makes all engines + agents work as ONE TEAM.

Every COACH_INTERVAL seconds the coach:
  1. Reads the historical setup rankings (rank_setups.py output, refreshed)
  2. Blends with LIVE paper-engine momentum (god_engine + main engine strategy_stats)
  3. Picks the TOP-N distinct (strategy, pair) combos — no two agents share a pair
  4. Broadcasts per-agent assignments to coach_signals.json

champion_battle.py reads coach_signals.json and trades the assigned setup+pair.
This turns 3 isolated bots into a coordinated, smart-rotating team.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import json, os, time, signal, subprocess, pathlib, sys
from datetime import datetime, timezone

# Telegram notifier (real-time learning/upgrade events). No-op if creds/module missing.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from telegram_alerts import notify as _tg_notify
except Exception:
    def _tg_notify(*a, **k): return False

def tg(text, silent=False):
    """Send a Telegram message tagged COACH; never raises."""
    try:
        return _tg_notify(text, silent=silent, tag="COACH")
    except Exception:
        return False

# Environment-aware root: DigitalOcean (/root) vs Google Cloud (/home/ubuntu)
def _detect_base():
    for base in (pathlib.Path("/root"), pathlib.Path("/home/ubuntu")):
        if (base / "canary").exists():
            return base
    return pathlib.Path(os.path.expanduser("~"))

_BASE         = pathlib.Path(os.environ["CANARY_BASE"]) if os.environ.get("CANARY_BASE") else _detect_base()
ROOT          = _BASE / "canary"
ENGINE_DIR    = _BASE / "trading_engine"
RUNTIME       = ROOT / "runtime"
RUNTIME.mkdir(parents=True, exist_ok=True)

RANKINGS_FILE = RUNTIME / "setup_rankings.json"
SIGNALS_FILE  = RUNTIME / "coach_signals.json"
LOG_FILE      = RUNTIME / "coach.log"
RANK_SCRIPT   = ROOT / "rank_setups.py"

GOD_STATE     = ENGINE_DIR / "god_engine_state.json"
MAIN_STATE    = ENGINE_DIR / "engine_state_v8.json"

# Team roster — agents that consume signals (ordered by capital / priority)
TEAM = ["TITAN", "VELOCITY", "SENTINEL"]

COACH_INTERVAL   = 30      # seconds between coaching cycles
RANK_REFRESH_S   = 600     # re-run rank_setups.py (DB scan) every 10 min
TOP_N            = 3       # distinct setups to assign (one per agent)
MIN_PF           = 1.2     # never assign a setup below this profit factor
MOMENTUM_WEIGHT  = 0.35    # how much live paper momentum tilts the blended score

# Map paper strategy KEY -> human name used in DB rankings (rank uses DB name)
STRAT_KEY_TO_NAME = {
    "CHANDE_MOMENTUM": "Chande Momentum Oscillator",
    "FAIR_VALUE_GAP": "ICT Fair Value Gap (FVG)",
    "SQUEEZE_MOMENTUM": "Squeeze Momentum (LazyBear)",
    "WILLIAMS_R_REVERSAL": "Williams %R Reversal",
    "PARABOLIC_SAR": "Parabolic SAR Flip",
    "KELTNER_RSI": "Keltner Channel + RSI",
    "BB_SQUEEZE": "Bollinger Band Squeeze",
    "FIBONACCI_RETRACEMENT": "Fibonacci Retracement",
    "CVD_ABSORPTION": "CVD Absorption Reversal",
    "RANGE_TRADING": "Range Trading S/R",
    "ORDER_FLOW": "Order Flow Imbalance",
    "HFT_STAT_ARB": "HFT Statistical Arbitrage",
    "RSI_DIVERGENCE": "RSI Divergence",
    "PRICE_ACTION": "Price Action Candlestick",
}
NAME_TO_KEY = {v: k for k, v in STRAT_KEY_TO_NAME.items()}

# ── FALLBACK RANKINGS ──────────────────────────────────────────────────────
# Used when no trades.db / paper-engine state is available (e.g. fresh
# DigitalOcean deploy). These are the PROVEN top setup+pair combos from the
# 355K+ trade backtest. Live DB rankings, when present, always override these.
FALLBACK_RANKINGS = [
    {"strategy": "Chande Momentum Oscillator", "pair": "BOME_USDT",
     "profit_factor": 68.5, "win_rate": 0.53, "score": 68.5},
    {"strategy": "Chande Momentum Oscillator", "pair": "FLOKI_USDT",
     "profit_factor": 10.7, "win_rate": 0.51, "score": 10.7},
    {"strategy": "Chande Momentum Oscillator", "pair": "WIF_USDT",
     "profit_factor": 6.6, "win_rate": 0.50, "score": 6.6},
    {"strategy": "Chande Momentum Oscillator", "pair": "DOGE_USDT",
     "profit_factor": 3.4, "win_rate": 0.49, "score": 3.4},
    # MAX-PROFIT (2026-06-03): full proven-CMO universe so the bench hint covers
    # every pair champion_battle.py now scans in real time.
    {"strategy": "Chande Momentum Oscillator", "pair": "OP_USDT",
     "profit_factor": 2.9, "win_rate": 0.49, "score": 2.9},
    {"strategy": "Chande Momentum Oscillator", "pair": "SHIB_USDT",
     "profit_factor": 2.7, "win_rate": 0.48, "score": 2.7},
    {"strategy": "Chande Momentum Oscillator", "pair": "ADA_USDT",
     "profit_factor": 2.5, "win_rate": 0.48, "score": 2.5},
    {"strategy": "Chande Momentum Oscillator", "pair": "UNI_USDT",
     "profit_factor": 2.3, "win_rate": 0.48, "score": 2.3},
    {"strategy": "Chande Momentum Oscillator", "pair": "ATOM_USDT",
     "profit_factor": 2.1, "win_rate": 0.47, "score": 2.1},
]


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def refresh_rankings():
    """Re-run the DB ranking scan (subprocess; keeps coach lightweight)."""
    try:
        subprocess.run(["python3", str(RANK_SCRIPT)], timeout=120,
                       capture_output=True)
        log("Rankings refreshed from trades DB.")
    except Exception as e:
        log(f"rank refresh failed: {e}")


def load_rankings():
    try:
        data = json.loads(RANKINGS_FILE.read_text())
        ranks = data.get("rankings", [])
        if ranks:
            return ranks
        log("rankings file empty -> using FALLBACK_RANKINGS")
        return list(FALLBACK_RANKINGS)
    except Exception as e:
        log(f"load rankings failed ({e}) -> using FALLBACK_RANKINGS")
        return list(FALLBACK_RANKINGS)


def load_live_momentum():
    """Read live paper strategy_stats to detect what's HOT right now.
    Returns {strategy_key: momentum_score in [-1, 1]}."""
    mom = {}
    for state_file in (GOD_STATE, MAIN_STATE):
        try:
            data = json.loads(state_file.read_text())
        except Exception:
            continue
        stats = data.get("strategy_stats") or {}
        # main engine stores per-agent; god engine stores per-strategy
        for key, s in stats.items():
            if not isinstance(s, dict):
                continue
            w = s.get("wins", 0) or 0
            l = s.get("losses", 0) or 0
            pnl = s.get("pnl", 0) or s.get("total_pnl", 0) or 0
            n = w + l
            if n < 3:
                continue
            wr = w / n
            # momentum: positive if winning + profitable lately
            score = (wr - 0.5) * 2  # [-1, 1] from win rate
            if pnl < 0:
                score -= 0.3
            mom[key] = max(-1.0, min(1.0, mom.get(key, 0) * 0.5 + score))
    return mom


def blend_and_select(rankings, momentum):
    """Blend historical score with live momentum, then pick TOP_N distinct pairs."""
    scored = []
    for r in rankings:
        if r.get("profit_factor", 0) < MIN_PF:
            continue
        key = NAME_TO_KEY.get(r["strategy"])
        mom = momentum.get(key, 0.0) if key else 0.0
        base = r.get("score", 0.0)
        blended = base * (1 + MOMENTUM_WEIGHT * mom)
        scored.append({**r, "strategy_key": key, "momentum": round(mom, 3),
                       "blended_score": round(blended, 4)})
    scored.sort(key=lambda x: x["blended_score"], reverse=True)

    # Greedy pick: distinct pairs so the team spreads risk across markets
    chosen, used_pairs, used_strats = [], set(), set()
    for s in scored:
        if s["pair"] in used_pairs:
            continue
        chosen.append(s)
        used_pairs.add(s["pair"])
        used_strats.add(s["strategy"])
        if len(chosen) >= TOP_N:
            break
    # Fallback: if fewer than TOP_N distinct pairs, allow reuse of best
    while len(chosen) < TOP_N and scored:
        chosen.append(scored[len(chosen) % len(scored)])
    return chosen, scored


def build_signals(chosen):
    assignments = {}
    for i, agent in enumerate(TEAM):
        setup = chosen[i % len(chosen)] if chosen else None
        if setup:
            assignments[agent] = {
                "strategy": setup["strategy"],
                "strategy_key": setup.get("strategy_key"),
                "pair": setup["pair"],
                "profit_factor": setup["profit_factor"],
                "win_rate": setup["win_rate"],
                "momentum": setup.get("momentum", 0),
                "blended_score": setup.get("blended_score"),
            }
    return {
        "version": "coach-v2",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "interval_s": COACH_INTERVAL,
        "team": TEAM,
        "assignments": assignments,
        "bench": [  # backup setups agents may rotate to if assigned pair stalls
            {"strategy": c["strategy"], "pair": c["pair"],
             "profit_factor": c["profit_factor"]}
            for c in chosen
        ],
    }


def build_signals_v2(chosen, all_scored):
    """v2 signals: keep per-agent hints + broadcast the FULL ranked pair list so
    champion_battle.py's real-time scanner has a complete pre-scored universe.
    The engine still does its own live scan; this is only a hint/bias source."""
    sig = build_signals(chosen)
    sig["version"] = "coach-v2"
    sig["ranked_pairs"] = [
        {"pair": s["pair"], "strategy": s["strategy"],
         "strategy_key": s.get("strategy_key"),
         "profit_factor": s.get("profit_factor"),
         "blended_score": s.get("blended_score"),
         "momentum": s.get("momentum", 0)}
        for s in all_scored
    ]
    return sig


def write_signals(signals):
    tmp = str(SIGNALS_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(signals, f, indent=2)
    os.replace(tmp, str(SIGNALS_FILE))


def main():
    log("=" * 66)
    log("TEAM COACH / COORDINATOR v1 — smart dynamic rotation online")
    log(f"Team: {TEAM} | TOP_N={TOP_N} | interval={COACH_INTERVAL}s | MIN_PF={MIN_PF}")
    log("=" * 66)

    stop = [False]
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__(0, True))
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__(0, True))

    if not RANKINGS_FILE.exists():
        refresh_rankings()

    last_refresh = time.time()
    cycle = 0
    prev_assign = {}   # agent -> (strategy_key, pair) from last cycle
    started_pinged = False
    while not stop[0]:
        cycle += 1
        try:
            did_refresh = False
            if time.time() - last_refresh >= RANK_REFRESH_S:
                refresh_rankings()
                last_refresh = time.time()
                did_refresh = True

            rankings = load_rankings()
            momentum = load_live_momentum()
            chosen, all_scored = blend_and_select(rankings, momentum)
            signals = build_signals_v2(chosen, all_scored)
            write_signals(signals)
            assigns = signals["assignments"]

            # Telegram sends removed from coach: ALL results now arrive in ONE
            # consolidated round-end message emitted by champion_battle.py.
            # The coach still writes coach_signals.json so the engine reads the
            # latest assignments (lineup + upgrades are summarized there).
            _ = (started_pinged, prev_assign, did_refresh, chosen)  # retained for log/state only

            if cycle % 4 == 1:  # log every 4th cycle (~2 min) to keep log small
                summary = " | ".join(
                    f"{a}->{v['strategy'][:14]}@{v['pair']}(PF{v['profit_factor']})"
                    for a, v in assigns.items()
                )
                log(f"Cycle {cycle}: {summary}")
        except Exception as e:
            log(f"[ERROR] cycle {cycle}: {e}")
        time.sleep(COACH_INTERVAL)

    log("Coach stopped.")


if __name__ == "__main__":
    main()
