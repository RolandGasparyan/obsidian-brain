"""
champion.sizer — Position Sizer per CHAMPION_MODE.md §4.1.

Combines:
  • CapitalStageTracker → base_risk / max_risk / min_risk envelope
  • Win-streak scaler   → 3W ×1.25 (next trade only), 5W ×1.5
  • Loss throttle       → 2L → min for 5 trades; 3L → 30min pause + min×10;
                          4L → 2h pause + min×20; 5L → STOP for the day
  • Volatility scaler   → BTC 14d realized vol percentile:
                          high(>80) ×0.7, low(<20) ×0.8, normal full
  • RiskLaws            → daily/weekly/peak/systemic halt + size scalers
  • God-tier bonus      → score ≥ 88 → up to 2× base (capped at max_risk)

Final: risk_pct = clip(base × all_scalers, min, max)
       risk_amount = equity × risk_pct
       position_units = risk_amount / |entry − stop|

The sizer is the SINGLE place where risk-per-trade is decided. Every
engine (godmode, aegis_alpha, quant-predator) must call .compute_size()
before any order; the returned SizeRecommendation is authoritative.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from champion.stage import CapitalStageTracker
from champion.risk  import RiskLaws, RiskState


NS_PER_SEC = 1_000_000_000


# ── trade outcome representation ─────────────────────────────────────
@dataclass
class TradeOutcome:
    """A closed-trade event. pnl_pct is signed fraction of equity at
    entry (e.g. +0.012 = +1.2%). pnl_R is in R units (+2.0 = 2R win,
    -1.0 = stop-loss hit). t_ns is exchange/local time in nanoseconds."""
    pnl_pct: float
    pnl_R:   float
    t_ns:    int


# ── what the sizer returns ──────────────────────────────────────────
@dataclass
class SizeRecommendation:
    blocked:          bool
    block_reason:     str
    risk_pct:         float          # final risk fraction of equity (0 if blocked)
    risk_amount:      float          # USD risked
    position_units:   float          # units of base asset
    notional_value:   float          # entry × position_units
    entry_price:      float
    stop_price:       float
    stop_distance_pct:float
    stage:            int
    state:            str            # RiskLaws state name
    scalers:          dict           # which scalers were applied
    god_tier:         bool
    raw_base_risk:    float          # base risk before scalers (audit)


# ── the sizer ───────────────────────────────────────────────────────
class PositionSizer:
    """Stateful: tracks recent trade outcomes for win-streak / loss-throttle
    state machine. Owns references to CapitalStageTracker + RiskLaws but
    does not mutate them — those receive ingestion separately."""

    # Win-streak scalers (§4.1)
    SCALER_3W = 1.25
    SCALER_5W = 1.50

    # Loss-throttle (§4.1)
    LOSS_2_THROTTLE_TRADES = 5     # next 5 trades at min risk
    LOSS_3_PAUSE_NS        = 30 * 60 * NS_PER_SEC
    LOSS_3_THROTTLE_TRADES = 10
    LOSS_4_PAUSE_NS        = 2 * 3600 * NS_PER_SEC
    LOSS_4_THROTTLE_TRADES = 20
    LOSS_5_DAILY_HALT      = True   # 5 in a row → STOP for day

    # Volatility scalers (BTC 14d realized vol percentile)
    HIGH_VOL_SCALER  = 0.70
    LOW_VOL_SCALER   = 0.80
    HIGH_VOL_PCTILE  = 0.80
    LOW_VOL_PCTILE   = 0.20

    # God-tier (§3.1)
    GOD_TIER_SIZE_MULT = 2.0    # capped at max_risk

    def __init__(self, tracker: CapitalStageTracker, risk: RiskLaws):
        self.tracker = tracker
        self.risk    = risk
        self._consec_wins:   int = 0
        self._consec_losses: int = 0
        self._win_streak_scaler_pending: float = 1.0   # used on next trade only
        self._throttle_remaining_trades: int   = 0     # min-risk floor for N trades
        self._pause_until_ns:           int    = 0
        self._daily_halt_until_day_key: str    = ""    # 5-loss daily stop
        self._recent_outcomes: Deque[TradeOutcome] = deque(maxlen=50)

    # ── ingestion ──────────────────────────────────────────────────
    def update_equity(self, equity: float, t_ns: int):
        self.tracker.update_equity(equity)
        self.risk.update_equity(equity, t_ns)

    def record_trade(self, outcome: TradeOutcome):
        """Update streak / throttle state from a closed trade."""
        self._recent_outcomes.append(outcome)
        self.risk.record_trade_close(outcome.pnl_pct, outcome.t_ns)

        if outcome.pnl_R > 0:
            self._consec_wins   += 1
            self._consec_losses  = 0
            # Win-streak scalers fire on the NEXT trade only
            if self._consec_wins == 5:
                self._win_streak_scaler_pending = self.SCALER_5W
            elif self._consec_wins == 3:
                self._win_streak_scaler_pending = self.SCALER_3W
            else:
                self._win_streak_scaler_pending = 1.0
            # Decrement throttle counter on a winner if active
            if self._throttle_remaining_trades > 0:
                self._throttle_remaining_trades -= 1
        else:
            self._consec_losses += 1
            self._consec_wins    = 0
            self._win_streak_scaler_pending = 1.0
            t_ns = outcome.t_ns
            if self._consec_losses == 2:
                self._throttle_remaining_trades = max(
                    self._throttle_remaining_trades, self.LOSS_2_THROTTLE_TRADES)
            elif self._consec_losses == 3:
                self._pause_until_ns = max(
                    self._pause_until_ns, t_ns + self.LOSS_3_PAUSE_NS)
                self._throttle_remaining_trades = max(
                    self._throttle_remaining_trades, self.LOSS_3_THROTTLE_TRADES)
            elif self._consec_losses == 4:
                self._pause_until_ns = max(
                    self._pause_until_ns, t_ns + self.LOSS_4_PAUSE_NS)
                self._throttle_remaining_trades = max(
                    self._throttle_remaining_trades, self.LOSS_4_THROTTLE_TRADES)
            elif self._consec_losses >= 5 and self.LOSS_5_DAILY_HALT:
                # Halt rest of UTC day
                self._daily_halt_until_day_key = time.strftime(
                    "%Y%m%d",
                    time.gmtime(t_ns / NS_PER_SEC + 86_400))

    # ── decision ──
    def compute_size(self, entry_price: float, stop_price: float,
                     t_ns: Optional[int] = None,
                     vol_percentile: Optional[float] = None,
                     god_tier: bool = False) -> SizeRecommendation:
        """The main API. Returns a SizeRecommendation. If `blocked`,
        DO NOT TRADE.  vol_percentile is the rolling BTC realized-vol
        percentile in [0, 1]; pass None to skip vol scaling."""
        if t_ns is None:
            t_ns = time.time_ns()
        equity   = self.tracker.equity
        rules    = self.tracker.rules
        scalers  = {}

        if entry_price <= 0 or stop_price <= 0 or entry_price == stop_price:
            return self._blocked("invalid entry/stop", entry_price, stop_price,
                                 equity, rules, scalers, god_tier, "INPUT")
        stop_dist_pct = abs(entry_price - stop_price) / entry_price
        scalers["stop_distance_pct"] = stop_dist_pct

        # 5-loss daily halt
        cur_day = time.strftime("%Y%m%d",
                                  time.gmtime(t_ns / NS_PER_SEC))
        if cur_day < self._daily_halt_until_day_key:
            return self._blocked(
                f"5-loss daily stop active until {self._daily_halt_until_day_key}",
                entry_price, stop_price, equity, rules, scalers, god_tier,
                "LOSS5_DAILY_HALT")

        # Loss-3/4 explicit pause
        if t_ns < self._pause_until_ns:
            return self._blocked(
                f"Loss-streak pause active ({(self._pause_until_ns - t_ns) / NS_PER_SEC / 60:.0f}min remaining)",
                entry_price, stop_price, equity, rules, scalers, god_tier,
                "LOSS_PAUSE")

        # RiskLaws layered checks (daily DD, weekly, peak, systemic)
        risk_dec = self.risk.decision(t_ns)
        if not risk_dec["allowed"]:
            return self._blocked(
                risk_dec["reason"], entry_price, stop_price, equity, rules,
                scalers, god_tier, risk_dec["state"].name)
        risk_law_scaler = risk_dec["size_scaler"]
        scalers["risk_law"] = risk_law_scaler
        risk_state = risk_dec["state"]

        # Compose scalers
        risk_pct = rules.base_risk
        scalers["base_risk"] = rules.base_risk

        # Win-streak (one-shot, applies once)
        ws_scaler = self._win_streak_scaler_pending
        scalers["win_streak"] = ws_scaler
        risk_pct *= ws_scaler

        # God-tier bonus
        if god_tier:
            risk_pct *= self.GOD_TIER_SIZE_MULT
            scalers["god_tier"] = self.GOD_TIER_SIZE_MULT

        # Volatility
        if vol_percentile is not None:
            if vol_percentile >= self.HIGH_VOL_PCTILE:
                risk_pct *= self.HIGH_VOL_SCALER
                scalers["vol"] = self.HIGH_VOL_SCALER
            elif vol_percentile <= self.LOW_VOL_PCTILE:
                risk_pct *= self.LOW_VOL_SCALER
                scalers["vol"] = self.LOW_VOL_SCALER
            else:
                scalers["vol"] = 1.0

        # RiskLaws scaler (e.g. 0.5 for −15% peak DD)
        risk_pct *= risk_law_scaler

        # Loss throttle floor — overrides upward scalers; min only
        if self._throttle_remaining_trades > 0:
            risk_pct = min(risk_pct, rules.min_risk)
            scalers["loss_throttle"] = "FLOOR_TO_MIN"

        # Clip to envelope
        clipped = max(rules.min_risk, min(rules.max_risk, risk_pct))
        if clipped != risk_pct:
            scalers["clip"] = (rules.min_risk, rules.max_risk)
        risk_pct = clipped

        # Translate to position
        risk_amount    = equity * risk_pct
        if stop_dist_pct <= 0:
            return self._blocked("stop_distance_pct == 0", entry_price,
                                 stop_price, equity, rules, scalers, god_tier,
                                 "INPUT")
        position_units = risk_amount / (stop_dist_pct * entry_price)
        notional_value = position_units * entry_price

        # Burn off the win-streak scaler — it was a one-shot
        self._win_streak_scaler_pending = 1.0

        return SizeRecommendation(
            blocked=False, block_reason="",
            risk_pct=risk_pct, risk_amount=risk_amount,
            position_units=position_units, notional_value=notional_value,
            entry_price=entry_price, stop_price=stop_price,
            stop_distance_pct=stop_dist_pct,
            stage=int(self.tracker.stage),
            state=risk_state.name,
            scalers=scalers, god_tier=god_tier,
            raw_base_risk=rules.base_risk,
        )

    def _blocked(self, reason, entry, stop, equity, rules,
                 scalers, god_tier, state) -> SizeRecommendation:
        return SizeRecommendation(
            blocked=True, block_reason=reason,
            risk_pct=0.0, risk_amount=0.0,
            position_units=0.0, notional_value=0.0,
            entry_price=entry, stop_price=stop,
            stop_distance_pct=(abs(entry - stop) / entry) if entry > 0 else 0.0,
            stage=int(self.tracker.stage),
            state=state,
            scalers=scalers, god_tier=god_tier,
            raw_base_risk=rules.base_risk,
        )

    # ── views for telemetry ─────────────────────────────────────────
    @property
    def consec_wins(self) -> int:   return self._consec_wins
    @property
    def consec_losses(self) -> int: return self._consec_losses
    @property
    def throttle_remaining(self) -> int: return self._throttle_remaining_trades

    def __repr__(self) -> str:
        return (f"<PositionSizer wins={self._consec_wins} "
                f"losses={self._consec_losses} "
                f"throttle={self._throttle_remaining_trades} "
                f"stage={self.tracker.stage.name}>")
