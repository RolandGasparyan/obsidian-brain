#!/usr/bin/env python3
"""
shadow_round.py — Shadow Championship Round Runner v1.1 (with macro + bayesian + MC)

Per:
  governance/SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md            (spec #17)
  governance/PRODUCTION_READY_SHADOW_ENGINE_v1.md             (spec #18)
  governance/AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1.md (spec #19)
  governance/BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md  (spec #20 Parts I+II)

🛡 PAPER-SAFE:
    LIVE_ORDERS    = 0
    MARKET_DATA    = realtime (Gate.io PUBLIC REST, no API key)
    EXECUTION      = simulated_with_slippage_model + fee model
    CAPITAL        = virtual 10 USDT
    L99 halt       remains engaged (not consulted, not cleared)
    .api_key       not opened
    Canary SHA256  not touched

Run via:
    ./start_shadow_round.sh         # 90-min standard round
    ROUND_LENGTH_MIN=2 ./start_shadow_round.sh   # short round for testing

Outputs:
    runtime/shadow_round_YYYY-MM-DD-HHMM.jsonl       (per-trade log)
    runtime/shadow_round_summary_YYYY-MM-DD-HHMM.json (round summary)
    runtime/shadow_round.pid                         (pid file)

Spec consistency:
    RISK_PER_TRADE        = 0.25%       (Spec #14 / #17)
    MAX_EXPOSURE          = 1%
    MAX_CONCURRENT        = 1
    MAX_TRADES_PER_ROUND  = 6
    TP_PCT                = 1.0%
    SL_PCT                = 0.5%
    Phase 1 (0-30m)       cap 0.4%, max 2 trades
    Phase 2 (30-75m)      cap 0.6%, composite ≥ 85
    Phase 3 (75-90m)      composite ≥ 90 or defensive
    NO_PYRAMIDING
    NO_CAPITAL_MIGRATION
    FULL_EXIT_TO_USDT
    Auto-freeze: 3 consec losses | DD ≥ 2% | slip > 2× avg
"""

from __future__ import annotations

import json
import os
import signal
import statistics
import sys
import time
import urllib.request
import urllib.error
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Sibling modules (spec #19, #20).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from macro_layer import (
    compute_global_macro_score,
    apply_macro_to_risk,
    aggregate_macro_distribution,
    ARTICLE3_RISK_PER_TRADE_MAX_PCT,
)
from bayesian_regime import BayesianRegime, shannon_entropy
from monte_carlo import forward_stress, kelly_compression_required
from survival_metrics import compute_sovereign_survival_score

# ── ENV CONFIG ──────────────────────────────────────────────────────────────


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _envf(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _envi(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


MODE                = _env("MODE", "SHADOW_CHAMPIONSHIP")
LIVE_ORDERS         = _envi("LIVE_ORDERS", 0)   # MUST be 0
ROUND_LENGTH_MIN    = _envi("ROUND_LENGTH_MIN", _envi("ROUND_LENGTH", 90))
VIRTUAL_CAPITAL     = _envf("VIRTUAL_CAPITAL", _envf("CAPITAL", 10.0))
RISK_PER_TRADE_PCT  = _envf("RISK_PER_TRADE", 0.25)
MAX_EXPOSURE_PCT    = _envf("MAX_EXPOSURE", 1.0)
MAX_CONCURRENT      = _envi("MAX_CONCURRENT", 1)
MAX_TRADES_PER_ROUND= _envi("MAX_TRADES_PER_ROUND", 6)
TP_PCT              = _envf("TP_PCT", 1.0)
SL_PCT              = _envf("SL_PCT", 0.5)
SCAN_INTERVAL_SEC   = _envi("SCAN_INTERVAL", 10)
SCAN_TOP_PAIRS      = _envi("SCAN_TOP_PAIRS", 5)
MAX_CONSEC_LOSS     = _envi("MAX_CONSEC_LOSS", 3)
DD_FREEZE_LEVEL_PCT = _envf("DD_FREEZE_LEVEL", 2.0)
INCLUDE_FEES        = _envi("INCLUDE_FEES", 1)
SPOT_FEE_TAKER_PCT  = _envf("SPOT_FEE_TAKER", 0.2)  # Gate.io spot taker
ENABLE_SLIPPAGE     = _envi("SLIPPAGE_MODEL", 1)

# ── SLIGHT UNLOCK MODE (per Spec #23 Section II) ────────────────────────────
# When SLIGHT_UNLOCK=1, applies the tighter risk envelope + slightly more
# permissive signal/composite thresholds + 2 new entry gates (macro<30 block,
# bayes Panic posterior >55% block). Still LIVE_ORDERS=0. Paper-safe.
SLIGHT_UNLOCK       = _envi("SLIGHT_UNLOCK", 0)

if SLIGHT_UNLOCK:
    # Tighter risk envelope (Spec #23 Section II).
    MAX_TRADES_PER_ROUND = min(MAX_TRADES_PER_ROUND, _envi("MAX_TRADES_TOTAL", 3))
    MAX_CONSEC_LOSS      = min(MAX_CONSEC_LOSS, _envi("AUTO_FREEZE_AFTER_CONSEC_LOSS", 2))
    DD_FREEZE_LEVEL_PCT  = min(DD_FREEZE_LEVEL_PCT, _envf("MAX_SESSION_DD", 1.5))
    # MAX_RISK ceiling (per spec — 0.40% absolute, never exceed)
    SLIGHT_UNLOCK_MAX_RISK_PCT = _envf("MAX_RISK", 0.40)

# Signal thresholds (defaults strict, slight_unlock loosens).
#
# DISCIPLINED UNLOCK V1 tuning (2026-05-13, operator-authored after 2× shadow rounds with 0 trades):
#   COMPOSITE_FIRE_THRESHOLD  50.0 → 47.5  (mildly more permissive entry)
#   MACRO_BLOCK_BELOW_SCORE   30.0 → 25.0  (block only on near-PANIC band, was clipping DEFENSIVE)
#   BAYES_PANIC_BLOCK_PCT     55.0 → 65.0  (block on near-certain Panic, not mid-uncertainty)
#
# UNCHANGED Spec #23 envelope (per operator "KEEP LOCKED"):
#   - MA50W10 core (not relevant here · Layer 1 SHA-locked anyway)
#   - DD caps · halt protections · rollback paths · sovereign freeze logic · live exec state
#   - Article 3 hard cap (RISK_PER_TRADE ≤ 0.75%)
#   - max_trades_per_round · max_consec_loss · session_dd_freeze
COMPOSITE_FIRE_THRESHOLD = 47.5 if SLIGHT_UNLOCK else 60.0
MOMENTUM_FIRE_THRESHOLD  = 0.15 if SLIGHT_UNLOCK else 0.20
MACRO_BLOCK_BELOW_SCORE  = 25.0  if SLIGHT_UNLOCK else 0.0   # 0 disables
BAYES_PANIC_BLOCK_PCT    = 65.0  if SLIGHT_UNLOCK else 100.0 # 100 disables

# Safety guard — refuse to run if LIVE_ORDERS != 0
if LIVE_ORDERS != 0:
    sys.stderr.write(
        "❌ REFUSED: shadow_round.py is paper-safe only. "
        "LIVE_ORDERS must be 0. See MICRO_LIVE_OPERATOR_CHECKLIST.md "
        "for the live-mode path.\n"
    )
    sys.exit(2)

# ── PATHS ────────────────────────────────────────────────────────────────────

# Detect server vs local layout.
_CANDIDATE_ROOTS = [Path("/root/agent"), Path(__file__).resolve().parents[1]]
ROOT = next((p for p in _CANDIDATE_ROOTS if p.exists()), _CANDIDATE_ROOTS[-1])
RUNTIME_DIR = ROOT / "runtime"
RUNTIME_DIR.mkdir(exist_ok=True, parents=True)

STAMP = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
TRADE_LOG_PATH    = RUNTIME_DIR / f"shadow_round_{STAMP}.jsonl"
ROUND_SUMMARY_PATH= RUNTIME_DIR / f"shadow_round_summary_{STAMP}.json"
PID_FILE          = RUNTIME_DIR / "shadow_round.pid"
LATEST_SUMMARY    = RUNTIME_DIR / "shadow_round_latest.json"

# ── PAIRS ────────────────────────────────────────────────────────────────────

# Top-5 USDT spot pairs by 24h volume (static — public knowledge, no API key).
PAIRS = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT", "XRP_USDT"][:SCAN_TOP_PAIRS]

# ── PHASE BOUNDARIES (proportional to ROUND_LENGTH_MIN) ──────────────────────

PHASE_1_END = ROUND_LENGTH_MIN * (30 / 90)
PHASE_2_END = ROUND_LENGTH_MIN * (75 / 90)
# Phase 3 runs from PHASE_2_END → ROUND_LENGTH_MIN

PHASE_1_RISK_CAP  = 0.4
PHASE_2_RISK_CAP  = 0.6
PHASE_1_MAX_TRADES= 2
PHASE_2_MIN_COMP  = 80 if SLIGHT_UNLOCK else 85   # Spec #23 Section II
PHASE_3_MIN_COMP  = 88 if SLIGHT_UNLOCK else 90   # Spec #23 Section II

# ── DATA STRUCTURES ─────────────────────────────────────────────────────────


@dataclass
class Tick:
    ts: float
    last: float
    bid: float
    ask: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread_pct(self) -> float:
        return ((self.ask - self.bid) / self.mid) * 100.0 if self.mid else 0.0


@dataclass
class Trade:
    pair: str
    side: str                  # "long" only in this micro safe mode
    signal_ts: float
    fill_ts: float
    modeled_entry: float
    actual_entry: float
    expected_exit: float
    actual_exit: float
    exit_ts: float
    spread_entry_pct: float
    spread_exit_pct: float
    slippage_entry_pct: float
    slippage_exit_pct: float
    fee_round_trip_pct: float
    risk_pct: float
    risk_pct_pre_macro: float
    risk_adjust_reason: str
    notional_usd: float
    realized_pnl_usd: float
    modeled_pnl_usd: float
    modeled_r: float
    realized_r: float
    composite_score: float
    regime: str
    phase: int
    exit_reason: str           # "tp" | "sl" | "phase_close" | "auto_freeze"
    execution_delay_ms: float
    # Spec #19 macro fields.
    global_macro_score: float
    macro_mode: str
    macro_risk_multiplier: float
    # Spec #20 Bayesian fields.
    bayesian_dominant_regime: str
    bayesian_entropy: float


# ── PRICE FEED (REST polling, no API key) ───────────────────────────────────


def fetch_tickers(pairs: list[str]) -> dict[str, Tick]:
    """Single batched call to Gate.io public spot tickers endpoint."""
    out: dict[str, Tick] = {}
    now = time.time()
    for pair in pairs:
        url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "shadow-round/1.0"})
            # URL is a static https:// literal built from a hardcoded
            # base (api.gateio.ws/api/v4/spot/tickers) with a pair
            # string from the trusted PAIRS constant. No user input,
            # no file:// scheme exposure. B310 risk is structural,
            # not exploitable here.
            with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
            if not data:
                continue
            row = data[0]
            last = float(row.get("last") or 0)
            bid = float(row.get("highest_bid") or last)
            ask = float(row.get("lowest_ask") or last)
            if last > 0 and bid > 0 and ask > 0:
                out[pair] = Tick(ts=now, last=last, bid=bid, ask=ask)
        except (urllib.error.URLError, ValueError, KeyError, TimeoutError):
            continue
    return out


# ── SLIPPAGE & FEE MODEL ────────────────────────────────────────────────────


def simulate_slippage_pct(spread_pct: float, vol_5min_pct: float) -> float:
    """
    Slippage simulator per Spec #17 Section II.
        base = 0.05%
        vol_multiplier = realized 5-min vol scaling
        spread_impact  = half-spread crossed
    """
    if not ENABLE_SLIPPAGE:
        return 0.0
    base = 0.05
    vol_mult = max(0.0, vol_5min_pct) * 0.30   # 1% vol → +0.30% slip contribution
    spread_impact = spread_pct * 0.50          # half-spread crossed
    return base + vol_mult + spread_impact


def round_trip_fee_pct() -> float:
    return (SPOT_FEE_TAKER_PCT * 2.0) if INCLUDE_FEES else 0.0


# ── STRATEGY SIGNAL ─────────────────────────────────────────────────────────


def compute_signal(price_window: deque[float]) -> tuple[bool, float, str]:
    """
    Simple MA-breakout-with-momentum signal.
    Returns (fire, composite_score [0-100], regime_tag).
    Deterministic given window — not optimized for profit, optimized for
    validating the simulation pipeline.
    """
    if len(price_window) < 12:
        return False, 0.0, "INSUFFICIENT_DATA"

    prices = list(price_window)
    ma_short = statistics.fmean(prices[-6:])
    ma_long  = statistics.fmean(prices[-12:])
    last = prices[-1]

    # Realized 5-min volatility (% std-dev over last 12 ticks ≈ 2 min @ 10s scan).
    vol_pct = (statistics.pstdev(prices[-12:]) / ma_long * 100.0) if ma_long else 0.0

    momentum_pct = ((last - prices[-12]) / prices[-12] * 100.0) if prices[-12] else 0.0

    # Regime tagging.
    if vol_pct > 0.8:
        regime = "EXPANSION"
    elif vol_pct < 0.15:
        regime = "COMPRESSION"
    elif momentum_pct > 0.3:
        regime = "TREND_UP"
    elif momentum_pct < -0.3:
        regime = "TREND_DOWN"
    else:
        regime = "CHOP"

    # Composite score: only fire if MA-cross-up AND positive momentum AND non-chaos.
    if ma_short <= ma_long:
        return False, 0.0, regime
    if momentum_pct < MOMENTUM_FIRE_THRESHOLD:
        return False, 0.0, regime
    if regime in ("CHOP", "COMPRESSION", "INSUFFICIENT_DATA"):
        return False, 0.0, regime

    # Composite: weighted blend.
    trend_strength = min(100.0, momentum_pct * 25.0)
    vol_quality    = max(0.0, 100.0 - abs(vol_pct - 0.5) * 80.0)  # peak at ~0.5% vol
    cross_strength = min(100.0, ((ma_short - ma_long) / ma_long * 100.0) * 50.0)
    composite = 0.50 * trend_strength + 0.30 * cross_strength + 0.20 * vol_quality
    composite = max(0.0, min(100.0, composite))

    return (composite >= COMPOSITE_FIRE_THRESHOLD), composite, regime


# ── PHASE LOGIC ─────────────────────────────────────────────────────────────


def current_phase(elapsed_min: float) -> int:
    if elapsed_min < PHASE_1_END:
        return 1
    if elapsed_min < PHASE_2_END:
        return 2
    return 3


def phase_allows_trade(
    phase: int,
    composite: float,
    trades_in_phase_1: int,
    equity_change_pct: float,
    macro_score: float = 100.0,
    bayes_panic_pct: float = 0.0,
) -> tuple[bool, str]:
    # Spec #23 Section II — Slight Unlock entry gates (applied when SLIGHT_UNLOCK=1).
    # MACRO_BLOCK_BELOW_SCORE / BAYES_PANIC_BLOCK_PCT default to 0/100 outside
    # slight_unlock mode (disabled), so this is a no-op for legacy shadow runs.
    if macro_score < MACRO_BLOCK_BELOW_SCORE:
        return False, f"slight_unlock_macro<{MACRO_BLOCK_BELOW_SCORE:g}"
    if bayes_panic_pct > BAYES_PANIC_BLOCK_PCT:
        return False, f"slight_unlock_bayes_panic>{BAYES_PANIC_BLOCK_PCT:g}%"

    if phase == 1:
        if trades_in_phase_1 >= PHASE_1_MAX_TRADES:
            return False, "phase1_trade_cap"
        return True, "phase1_ok"
    if phase == 2:
        if composite < PHASE_2_MIN_COMP:
            return False, f"phase2_composite<{PHASE_2_MIN_COMP}"
        return True, "phase2_ok"
    # phase 3
    if equity_change_pct > 0.5:
        return False, "phase3_defensive_leading"
    if composite < PHASE_3_MIN_COMP:
        return False, f"phase3_composite<{PHASE_3_MIN_COMP}"
    return True, "phase3_ok"


def phase_risk_cap_pct(phase: int) -> float:
    if phase == 1:
        return PHASE_1_RISK_CAP
    if phase == 2:
        return PHASE_2_RISK_CAP
    return min(PHASE_1_RISK_CAP, RISK_PER_TRADE_PCT)  # phase 3 capped tight


# ── ROUND ORCHESTRATION ────────────────────────────────────────────────────


class ShadowRound:
    def __init__(self) -> None:
        self.start_ts = time.time()
        self.virtual_capital_start = VIRTUAL_CAPITAL
        self.virtual_capital = VIRTUAL_CAPITAL
        self.peak_equity = VIRTUAL_CAPITAL
        self.trades: list[Trade] = []
        self.windows: dict[str, deque[float]] = {p: deque(maxlen=30) for p in PAIRS}
        self.spread_history: deque[float] = deque(maxlen=60)
        self.trades_in_phase_1 = 0
        self.consec_losses = 0
        self.frozen = False
        self.freeze_reason: str | None = None
        self.slippage_history: list[float] = []
        self.tick_count = 0

        # Spec #19 — macro layer state.
        self.macro_observations: list[dict[str, Any]] = []
        self.current_macro: dict[str, Any] = {
            "score": 50.0, "mode": "NEUTRAL", "risk_multiplier": 1.0,
            "exposure_cap_pct": 1.0, "aggression_allowed": False,
            "inputs": {},
        }
        self.last_macro_recompute = 0.0
        self.last_raw_tickers: dict[str, dict[str, Any]] = {}

        # Spec #20 Part I — Bayesian regime engine.
        self.bayes = BayesianRegime()
        self.bayes_dominant = "Chop"
        self.bayes_entropy = 0.0
        self.bayes_accel = 0.0
        self.bayes_posterior: dict[str, float] = {}   # full vector (for Spec #23 Panic gate)
        self.last_bayes_recompute = 0.0

        # Spec #20 Part II — Monte Carlo overlay state.
        self.mc_results: list[dict[str, Any]] = []
        self.mc_compress_active = False
        self.mc_compress_reason: str | None = None

    @property
    def elapsed_min(self) -> float:
        return (time.time() - self.start_ts) / 60.0

    @property
    def equity_change_pct(self) -> float:
        return ((self.virtual_capital - self.virtual_capital_start)
                / self.virtual_capital_start * 100.0)

    @property
    def max_dd_pct(self) -> float:
        if not self.peak_equity:
            return 0.0
        return ((self.peak_equity - self.virtual_capital) / self.peak_equity * 100.0)

    def update_peak(self) -> None:
        if self.virtual_capital > self.peak_equity:
            self.peak_equity = self.virtual_capital

    def check_auto_freeze(self, last_slippage: float | None) -> None:
        if self.frozen:
            return
        if self.consec_losses >= MAX_CONSEC_LOSS:
            self.frozen = True
            self.freeze_reason = f"consec_losses>={MAX_CONSEC_LOSS}"
            return
        if self.max_dd_pct >= DD_FREEZE_LEVEL_PCT:
            self.frozen = True
            self.freeze_reason = f"dd>={DD_FREEZE_LEVEL_PCT}%"
            return
        if last_slippage is not None and self.slippage_history:
            avg = statistics.fmean(self.slippage_history)
            if avg > 0 and last_slippage > 2.0 * avg:
                self.frozen = True
                self.freeze_reason = f"slip_spike_{last_slippage:.3f}_vs_avg_{avg:.3f}"

    def simulate_trade(
        self, pair: str, tick: Tick, composite: float, regime: str, phase: int
    ) -> Trade:
        # Sizing — base from phase cap.
        risk_pct_base = min(RISK_PER_TRADE_PCT, phase_risk_cap_pct(phase))
        risk_pct_pre_macro = risk_pct_base

        # Apply macro layer (Spec #19 Section V).
        risk_pct, macro_reason = apply_macro_to_risk(
            base_risk_pct=risk_pct_base,
            macro=self.current_macro,
            phase=phase,
            equity_change_pct=self.equity_change_pct,
        )

        # Apply Monte Carlo Kelly compression if active (Spec #20 Part II).
        if self.mc_compress_active:
            risk_pct = min(risk_pct, RISK_PER_TRADE_PCT * 0.5)
            macro_reason += "+mc_compress"

        # Apply Bayesian entropy compression (high uncertainty → less aggression).
        if self.bayes_entropy > 1.5:  # close to max entropy ≈ 1.79
            risk_pct = min(risk_pct, RISK_PER_TRADE_PCT * 0.7)
            macro_reason += "+entropy_compress"

        # Constitutional hard cap (never exceed Article 3).
        risk_pct = min(risk_pct, ARTICLE3_RISK_PER_TRADE_MAX_PCT)

        risk_usd = self.virtual_capital * (risk_pct / 100.0)
        exposure_cap = min(MAX_EXPOSURE_PCT, self.current_macro["exposure_cap_pct"])
        notional_usd = risk_usd / (SL_PCT / 100.0)
        notional_usd = min(notional_usd,
                           self.virtual_capital * (exposure_cap / 100.0) * 100.0)

        # Modeled entry/exit using mid.
        modeled_entry = tick.mid
        modeled_exit_tp = modeled_entry * (1.0 + TP_PCT / 100.0)

        # Simulated entry (cross half spread + slip).
        prices = list(self.windows[pair])
        ma_long = statistics.fmean(prices[-12:]) if len(prices) >= 12 else modeled_entry
        vol_pct = (statistics.pstdev(prices[-12:]) / ma_long * 100.0) if len(prices) >= 12 and ma_long else 0.0
        slip_entry_pct = simulate_slippage_pct(tick.spread_pct, vol_pct)
        actual_entry = modeled_entry * (1.0 + (tick.spread_pct / 2.0 + slip_entry_pct) / 100.0)

        # Forward-step price window until TP or SL hit, with realistic stochastic walk
        # using the existing window's drift + std-dev.
        if len(prices) >= 6:
            drift_per_tick = (prices[-1] - prices[-6]) / 5.0
            step_std = statistics.pstdev(
                [prices[i] - prices[i-1] for i in range(1, len(prices))]
            ) or abs(drift_per_tick) or modeled_entry * 0.0005
        else:
            drift_per_tick = 0.0
            step_std = modeled_entry * 0.0005

        # Simulate up to 60 ticks of forward walk (~10 min @ 10s).
        import random
        rng = random.Random(int(tick.ts * 1000) + len(self.trades))
        px = actual_entry
        ticks_held = 0
        exit_reason = "phase_close"
        actual_exit = px
        tp_price = actual_entry * (1.0 + TP_PCT / 100.0)
        sl_price = actual_entry * (1.0 - SL_PCT / 100.0)

        for _ in range(60):
            step = drift_per_tick + rng.gauss(0, step_std)
            px += step
            ticks_held += 1
            if px >= tp_price:
                exit_reason = "tp"
                actual_exit = tp_price
                break
            if px <= sl_price:
                exit_reason = "sl"
                actual_exit = sl_price
                break
        else:
            actual_exit = px

        # Exit slippage.
        slip_exit_pct = simulate_slippage_pct(tick.spread_pct, vol_pct)
        actual_exit_after_slip = actual_exit * (1.0 - slip_exit_pct / 100.0)

        # PnL.
        units = notional_usd / actual_entry
        gross_pnl = (actual_exit_after_slip - actual_entry) * units
        fees_usd = notional_usd * (round_trip_fee_pct() / 100.0)
        realized_pnl = gross_pnl - fees_usd
        modeled_pnl = (modeled_exit_tp - modeled_entry) * (notional_usd / modeled_entry) if exit_reason == "tp" else 0.0

        # R-multiples.
        modeled_r = TP_PCT / SL_PCT if exit_reason in ("tp", "phase_close") else -1.0
        realized_r = (realized_pnl / risk_usd) if risk_usd else 0.0

        fill_ts = tick.ts + 0.15  # simulated 150ms request→fill
        exit_ts = fill_ts + ticks_held * SCAN_INTERVAL_SEC

        return Trade(
            pair=pair,
            side="long",
            signal_ts=tick.ts,
            fill_ts=fill_ts,
            modeled_entry=round(modeled_entry, 6),
            actual_entry=round(actual_entry, 6),
            expected_exit=round(modeled_exit_tp, 6),
            actual_exit=round(actual_exit_after_slip, 6),
            exit_ts=exit_ts,
            spread_entry_pct=round(tick.spread_pct, 5),
            spread_exit_pct=round(tick.spread_pct, 5),
            slippage_entry_pct=round(slip_entry_pct, 5),
            slippage_exit_pct=round(slip_exit_pct, 5),
            fee_round_trip_pct=round(round_trip_fee_pct(), 4),
            risk_pct=round(risk_pct, 5),
            risk_pct_pre_macro=round(risk_pct_pre_macro, 5),
            risk_adjust_reason=macro_reason,
            notional_usd=round(notional_usd, 4),
            realized_pnl_usd=round(realized_pnl, 6),
            modeled_pnl_usd=round(modeled_pnl, 6),
            modeled_r=round(modeled_r, 4),
            realized_r=round(realized_r, 4),
            composite_score=round(composite, 2),
            regime=regime,
            phase=phase,
            exit_reason=exit_reason,
            execution_delay_ms=150.0,
            global_macro_score=self.current_macro["score"],
            macro_mode=self.current_macro["mode"],
            macro_risk_multiplier=self.current_macro["risk_multiplier"],
            bayesian_dominant_regime=self.bayes_dominant,
            bayesian_entropy=round(self.bayes_entropy, 4),
        )

    def recompute_macro_and_bayes(self, raw_tickers: dict[str, dict[str, Any]]) -> bool:
        """
        Refresh macro score + Bayesian regime posterior.
        Returns True if dominant regime changed (caller may want to retrigger MC).
        """
        # Macro (Spec #19).
        macro = compute_global_macro_score(
            price_windows=self.windows,
            spread_history=list(self.spread_history),
            raw_tickers=raw_tickers,
        )
        self.current_macro = macro
        self.macro_observations.append(macro)
        self.last_macro_recompute = time.time()

        # Bayesian features (Spec #20 Part I).
        btc = list(self.windows.get("BTC_USDT", []))
        eth = list(self.windows.get("ETH_USDT", []))
        if len(btc) >= 12:
            ma = statistics.fmean(btc)
            vol_pct = (statistics.pstdev(btc[-12:]) / ma * 100.0) if ma else 0.0
            momentum_pct = ((btc[-1] - btc[-12]) / btc[-12] * 100.0) if btc[-12] else 0.0
        else:
            vol_pct, momentum_pct = 0.3, 0.0
        spreads = list(self.spread_history)
        sp_cv = (statistics.pstdev(spreads) / statistics.fmean(spreads)) if (len(spreads) >= 6 and statistics.fmean(spreads) > 0) else 0.5
        if len(btc) >= 8 and len(eth) >= 8:
            btc_rets = [btc[i] - btc[i-1] for i in range(1, len(btc))]
            eth_rets = [eth[i] - eth[i-1] for i in range(1, len(eth))]
            from macro_layer import _pearson as _p  # safe to reuse
            corr_abs = abs(_p(btc_rets, eth_rets))
        else:
            corr_abs = 0.5

        features = {
            "vol_pct": vol_pct,
            "momentum_pct": momentum_pct,
            "spread_cv": sp_cv,
            "correlation_abs": corr_abs,
        }
        prev_dominant = self.bayes_dominant
        posterior, dominant, entropy, accel = self.bayes.update(features)
        self.bayes_dominant = dominant
        self.bayes_entropy = entropy
        self.bayes_accel = accel
        self.bayes_posterior = posterior   # full vector for Spec #23 Panic gate
        self.last_bayes_recompute = time.time()
        return dominant != prev_dominant

    def recompute_monte_carlo(self, reason: str) -> None:
        """Run Monte Carlo forward stress (Spec #20 Part II). Bounded invocations."""
        # Estimate edge params from current trades (or seed from spec defaults).
        if self.trades:
            wins = sum(1 for t in self.trades if t.realized_pnl_usd > 0)
            wp = wins / len(self.trades)
            avg_mod_r = statistics.fmean([t.modeled_r for t in self.trades])
            avg_real_r = statistics.fmean([t.realized_r for t in self.trades])
            slip_mean = statistics.fmean([t.slippage_entry_pct for t in self.trades])
            slip_std = statistics.pstdev([t.slippage_entry_pct for t in self.trades]) if len(self.trades) > 1 else 0.02
        else:
            # Seed from prior knowledge (Spec #14 expectation).
            wp = 0.50
            avg_mod_r = TP_PCT / SL_PCT
            avg_real_r = avg_mod_r * 0.9
            slip_mean = 0.10
            slip_std = 0.05

        mc = forward_stress(
            win_prob=wp,
            avg_modeled_r=avg_mod_r,
            avg_realized_r=avg_real_r,
            slip_mean_pct=slip_mean,
            slip_std_pct=slip_std,
            round_trip_fee_pct=round_trip_fee_pct(),
            risk_per_trade_pct=RISK_PER_TRADE_PCT,
            starting_capital=self.virtual_capital,
            trades_per_path=20,
            n_paths=2000,   # smaller per-trigger for performance
        )
        mc["trigger_reason"] = reason
        mc["triggered_at_elapsed_min"] = round(self.elapsed_min, 3)
        self.mc_results.append(mc)

        should_compress, comp_reason = kelly_compression_required(
            mc,
            constitutional_dd_pct=DD_FREEZE_LEVEL_PCT,
            max_ror_pct=1.0,
        )
        self.mc_compress_active = should_compress
        self.mc_compress_reason = comp_reason if should_compress else None

    def write_trade(self, trade: Trade) -> None:
        with TRADE_LOG_PATH.open("a") as f:
            f.write(json.dumps(asdict(trade)) + "\n")

    def round_summary(self) -> dict[str, Any]:
        n = len(self.trades)
        wins = sum(1 for t in self.trades if t.realized_pnl_usd > 0)
        avg_modeled_r = statistics.fmean([t.modeled_r for t in self.trades]) if n else 0.0
        avg_realized_r = statistics.fmean([t.realized_r for t in self.trades]) if n else 0.0
        avg_slip_in = statistics.fmean([t.slippage_entry_pct for t in self.trades]) if n else 0.0
        avg_spread = statistics.fmean([t.spread_entry_pct for t in self.trades]) if n else 0.0
        edge_preservation = (avg_realized_r / avg_modeled_r * 100.0) if avg_modeled_r else 0.0
        execution_stability = self.compute_execution_stability()
        # Spec #19 — macro distribution.
        macro_dist = aggregate_macro_distribution(self.macro_observations)
        avg_macro_score = (
            statistics.fmean([o["score"] for o in self.macro_observations])
            if self.macro_observations else 0.0
        )
        # Spec #20 Part I — Bayesian regime distribution + entropy stats.
        bayes_dist = self.bayes.regime_distribution()
        avg_entropy = (
            statistics.fmean([shannon_entropy(p) for p in self.bayes.history])
            if self.bayes.history else 0.0
        )
        # Spec #20 Part II — MC summary.
        latest_mc = self.mc_results[-1] if self.mc_results else None
        return {
            "mode": MODE,
            "slight_unlock": bool(SLIGHT_UNLOCK),
            "live_orders": LIVE_ORDERS,
            "round_started_utc": datetime.fromtimestamp(self.start_ts, timezone.utc).isoformat(),
            "round_length_min": ROUND_LENGTH_MIN,
            "round_elapsed_min": round(self.elapsed_min, 2),
            "virtual_capital_start_usdt": self.virtual_capital_start,
            "virtual_capital_end_usdt": round(self.virtual_capital, 6),
            "net_pnl_usdt": round(self.virtual_capital - self.virtual_capital_start, 6),
            "trades_total": n,
            "trades_win": wins,
            "win_rate_pct": round(wins / n * 100.0, 2) if n else 0.0,
            "avg_modeled_r": round(avg_modeled_r, 4),
            "avg_realized_r": round(avg_realized_r, 4),
            "edge_preservation_pct": round(edge_preservation, 2),
            "edge_preservation_pass": edge_preservation >= 90.0,
            "avg_slippage_entry_pct": round(avg_slip_in, 5),
            "avg_spread_pct": round(avg_spread, 5),
            "max_dd_pct": round(self.max_dd_pct, 3),
            "execution_stability_score": round(execution_stability, 2),
            "execution_stability_pass": execution_stability >= 80.0,
            "auto_freeze_triggered": self.frozen,
            "freeze_reason": self.freeze_reason,
            "governance_violations": 0,  # by construction (caps enforced pre-trade)
            "shadow_pass": (
                (edge_preservation >= 90.0)
                and (execution_stability >= 80.0)
                and (not self.frozen)
                and (n >= 1)
            ),
            # Spec #19 macro layer.
            "avg_macro_score": round(avg_macro_score, 2),
            "macro_regime_distribution_pct": macro_dist,
            "macro_observation_count": len(self.macro_observations),
            # Spec #20 Part I — Bayesian regime.
            "bayesian_regime_distribution_pct": bayes_dist,
            "avg_regime_entropy_nats": round(avg_entropy, 4),
            "bayes_update_count": len(self.bayes.history),
            # Spec #20 Part II — Monte Carlo overlay.
            "monte_carlo_runs": len(self.mc_results),
            "monte_carlo_latest": latest_mc,
            "monte_carlo_compress_active_at_end": self.mc_compress_active,
            "monte_carlo_compress_reason": self.mc_compress_reason,
            "spec_refs": [
                "AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1",
                "REAL_EXECUTION_LIVE_TRANSITION_MASTER_v1",
                "SHADOW_ROUND_EXECUTION_PROTOCOL_v1",
                "PRODUCTION_READY_SHADOW_ENGINE_v1",
                "AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1",
                "BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1",
                "META_CIVILIZATION_LOOP_v1",
                "SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER_v1",
            ],
        }

    def compute_execution_stability(self) -> float:
        if len(self.slippage_history) < 2:
            return 100.0
        avg = statistics.fmean(self.slippage_history)
        std = statistics.pstdev(self.slippage_history)
        if avg <= 0:
            return 100.0
        # Coefficient of variation → 0% noise = 100, 100% noise = 0.
        cv = std / avg
        return max(0.0, min(100.0, 100.0 - cv * 100.0))

    def write_summary(self) -> dict[str, Any]:
        summary = self.round_summary()
        # Spec #22 Section VII — synthesize Sovereign Survival Score on top of components.
        sss = compute_sovereign_survival_score(summary)
        summary["sovereign_survival_score"] = sss["sovereign_survival_score"]
        summary["sovereign_grade"]          = sss["sovereign_grade"]
        summary["sovereign_components"]     = sss["components"]
        ROUND_SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
        LATEST_SUMMARY.write_text(json.dumps(summary, indent=2))
        return summary


# ── MAIN LOOP ───────────────────────────────────────────────────────────────


_STOP = False


def _handle_stop(*_: object) -> None:
    global _STOP
    _STOP = True


def run() -> int:
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    PID_FILE.write_text(str(os.getpid()))
    print("🧠 Shadow Championship Round v1.1 — started")
    print(f"   mode               : {MODE}")
    print(f"   slight_unlock      : {SLIGHT_UNLOCK}  (Spec #23 Section II envelope)")
    print(f"   live_orders        : {LIVE_ORDERS} (must be 0)")
    print(f"   virtual_capital    : {VIRTUAL_CAPITAL} USDT")
    print(f"   round_length_min   : {ROUND_LENGTH_MIN}")
    print(f"   thresholds         : phase2_comp≥{PHASE_2_MIN_COMP} · phase3_comp≥{PHASE_3_MIN_COMP} · "
          f"fire≥{COMPOSITE_FIRE_THRESHOLD} · mom≥{MOMENTUM_FIRE_THRESHOLD}%")
    print(f"   slight_unlock_gates: macro<{MACRO_BLOCK_BELOW_SCORE:g} block · "
          f"bayes_panic>{BAYES_PANIC_BLOCK_PCT:g}% block")
    print(f"   risk_envelope      : max_trades={MAX_TRADES_PER_ROUND} · "
          f"max_consec_loss={MAX_CONSEC_LOSS} · session_dd≤{DD_FREEZE_LEVEL_PCT}%")
    print(f"   pairs              : {PAIRS}")
    print(f"   scan_interval_sec  : {SCAN_INTERVAL_SEC}")
    print(f"   trade_log          : {TRADE_LOG_PATH}")
    print(f"   summary            : {ROUND_SUMMARY_PATH}")
    print(f"   pid                : {os.getpid()}")
    print()

    rnd = ShadowRound()
    open_trade: Trade | None = None  # MAX_CONCURRENT = 1
    next_tick_at = time.time()
    last_heartbeat_recompute = 0.0

    # Spec #20 Part II — initial Monte Carlo at round start.
    rnd.recompute_monte_carlo(reason="round_start")
    mc0 = rnd.mc_results[-1]
    print(f"  [MC] round_start: p05={mc0['p05_equity']:.4f} "
          f"max_dd_p95={mc0['max_dd_p95_pct']:.2f}% "
          f"RoR={mc0['risk_of_ruin_pct']:.3f}% "
          f"kelly={mc0['kelly_optimal_fraction_pct']:.3f}% "
          f"compress={rnd.mc_compress_active} ({rnd.mc_compress_reason})")

    try:
        while not _STOP and rnd.elapsed_min < ROUND_LENGTH_MIN and not rnd.frozen:
            # Pace ticks.
            now = time.time()
            if now < next_tick_at:
                time.sleep(max(0.1, next_tick_at - now))
            next_tick_at = time.time() + SCAN_INTERVAL_SEC

            ticks = fetch_tickers(PAIRS)
            if not ticks:
                continue
            rnd.tick_count += 1

            # Update price + spread windows.
            for pair, t in ticks.items():
                rnd.windows[pair].append(t.last)
                rnd.spread_history.append(t.spread_pct)

            # Recompute macro + bayes every ~60s (Spec #19 + #20 cadence).
            if time.time() - last_heartbeat_recompute >= 60:
                # Fetch full ticker dicts for macro volume input.
                # URL is a static https:// literal to a known Gate.io
                # public endpoint, with a constant User-Agent header.
                # No user input feeds the URL, no file:// scheme path
                # is reachable. B310 risk is structural, not exploitable.
                try:
                    with urllib.request.urlopen(  # nosec B310
                        urllib.request.Request(
                            "https://api.gateio.ws/api/v4/spot/tickers",
                            headers={"User-Agent": "shadow-round/1.1"},
                        ),
                        timeout=5,
                    ) as resp:
                        all_tickers_raw = json.loads(resp.read().decode("utf-8"))
                    raw_tickers = {row["currency_pair"]: row for row in all_tickers_raw if row.get("currency_pair") in PAIRS}
                except Exception:
                    raw_tickers = {}
                regime_shifted = rnd.recompute_macro_and_bayes(raw_tickers)
                last_heartbeat_recompute = time.time()
                if regime_shifted:
                    rnd.recompute_monte_carlo(reason=f"regime_shift→{rnd.bayes_dominant}")
                    print(f"  [MC] regime_shift→{rnd.bayes_dominant} "
                          f"RoR={rnd.mc_results[-1]['risk_of_ruin_pct']:.3f}% "
                          f"compress={rnd.mc_compress_active}")

            phase = current_phase(rnd.elapsed_min)

            # Skip new entries if already in a trade (MAX_CONCURRENT=1) — but the
            # synthetic walk inside simulate_trade exits in-place, so open_trade
            # always resolves within one tick. Kept here for future async exits.
            if open_trade is not None:
                open_trade = None

            if len(rnd.trades) >= MAX_TRADES_PER_ROUND:
                continue

            # Scan pairs for signal.
            best_pair: str | None = None
            best_composite = 0.0
            best_regime = ""
            for pair, t in ticks.items():
                fire, composite, regime = compute_signal(rnd.windows[pair])
                if fire and composite > best_composite:
                    best_pair, best_composite, best_regime = pair, composite, regime

            if best_pair is None:
                _heartbeat(rnd, ticks)
                continue

            allowed, reason = phase_allows_trade(
                phase=phase,
                composite=best_composite,
                trades_in_phase_1=rnd.trades_in_phase_1,
                equity_change_pct=rnd.equity_change_pct,
                macro_score=rnd.current_macro["score"],
                bayes_panic_pct=(rnd.bayes_posterior.get("Panic", 0.0) * 100.0
                                 if rnd.bayes_posterior else 0.0),
            )
            if not allowed:
                _heartbeat(rnd, ticks, note=f"signal blocked: {reason}")
                continue

            trade = rnd.simulate_trade(best_pair, ticks[best_pair],
                                       best_composite, best_regime, phase)
            rnd.trades.append(trade)
            rnd.virtual_capital += trade.realized_pnl_usd
            rnd.update_peak()
            rnd.slippage_history.append(trade.slippage_entry_pct)
            if trade.realized_pnl_usd <= 0:
                rnd.consec_losses += 1
                # Spec #20 Part II — MC re-trigger after 3 consec losses.
                if rnd.consec_losses == 3 and not rnd.frozen:
                    rnd.recompute_monte_carlo(reason="3_consec_losses")
                    print(f"  [MC] consec_loss_trigger: "
                          f"RoR={rnd.mc_results[-1]['risk_of_ruin_pct']:.3f}% "
                          f"compress={rnd.mc_compress_active}")
            else:
                rnd.consec_losses = 0
            if phase == 1:
                rnd.trades_in_phase_1 += 1
            rnd.write_trade(trade)
            rnd.check_auto_freeze(trade.slippage_entry_pct)

            print(
                f"  [t+{rnd.elapsed_min:5.2f}m φ{phase}] "
                f"{trade.pair} {trade.exit_reason:>4s} "
                f"R={trade.realized_r:+.2f} "
                f"pnl={trade.realized_pnl_usd:+.4f} "
                f"comp={trade.composite_score:5.1f} "
                f"regime={trade.regime} "
                f"slip={trade.slippage_entry_pct:.3f}% "
                f"cap={rnd.virtual_capital:.4f}"
            )
    finally:
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except OSError:
                pass

        summary = rnd.write_summary()
        print()
        print("─" * 60)
        print("ROUND SUMMARY")
        print("─" * 60)
        for k, v in summary.items():
            if isinstance(v, list):
                continue
            print(f"  {k:<32s} {v}")
        print("─" * 60)
        print(f"  trade_log : {TRADE_LOG_PATH}")
        print(f"  summary   : {ROUND_SUMMARY_PATH}")
        print(f"  latest    : {LATEST_SUMMARY}")
        print(f"  pass      : {summary['shadow_pass']}")

    return 0 if not rnd.frozen else 3


def _heartbeat(rnd: ShadowRound, ticks: dict[str, Tick], note: str = "") -> None:
    if rnd.tick_count % 6 != 0:  # one heartbeat per minute @ 10s scan
        return
    extra = f" — {note}" if note else ""
    btc = ticks.get("BTC_USDT")
    btc_str = f"BTC=${btc.last:,.2f}" if btc else "BTC=?"
    macro = rnd.current_macro
    print(f"  ♥ t+{rnd.elapsed_min:5.2f}m φ{current_phase(rnd.elapsed_min)} "
          f"trades={len(rnd.trades)} cap={rnd.virtual_capital:.4f} "
          f"dd={rnd.max_dd_pct:.2f}% macro={macro['score']:.0f}/{macro['mode'][:3]} "
          f"bayes={rnd.bayes_dominant[:4]}(H={rnd.bayes_entropy:.2f}) "
          f"{btc_str}{extra}")


if __name__ == "__main__":
    sys.exit(run())
