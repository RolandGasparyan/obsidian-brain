"""
aegis_alpha.executor — entry-confirmation gate per CHAMPION_MODE.md §3.2
+ paper-shadow trade orchestration.

What it does:
    1. Take a TokenScore from aegis_alpha.scanner
    2. Run the §3.2 entry checklist on the LATEST 4H candle
    3. If all gates pass → ask champion.PositionSizer for size
    4. Open a paper AlphaTrade
    5. On every new 4H candle, feed all open trades for state-machine update

Design:
    The executor owns a small portfolio of open AlphaTrades. It does NOT
    make signal decisions — those come from scanner. It does NOT decide
    risk per trade — that comes from PositionSizer. It exists to:
      - enforce §3.2 entry gates (volume, spread, BTC trend, no chase)
      - call sizer.compute_size() for dollar amounts
      - close open trades by feeding them new candles
      - log every entry / exit / partial to JSONL for the trade journal

Paper-shadow vs live:
    Paper-shadow (this commit): no exchange calls. The "fill" is the
    current ask price. Stops simulated against candle high/low. Useful
    to validate the §3.2 + §3.3 logic on real data without risk.

    Live (future commit): plug a Gate.io spot order client, replace
    paper_open_trade with real limit-then-market entry, attach
    server-side stop-loss.
"""
from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from aegis_alpha.scanner import TokenScore, factor_breakout
from aegis_alpha.trade   import (AlphaTrade, CloseReason,
                                  STANDARD_TP_LADDER, GOD_TIER_TP_LADDER)
from champion           import (CapitalStageTracker, PositionSizer,
                                 RiskLaws, TradeOutcome, SizeRecommendation)


log = logging.getLogger("aegis_alpha.executor")

NS_PER_HOUR = 3600 * 1_000_000_000


# ── entry confirmation per §3.2 ──────────────────────────────────────
@dataclass
class EntryConfirmation:
    pair:                       str
    score:                      float
    god_tier:                   bool
    breakout_level:             float
    breakout_candle_close:      float
    breakout_candle_volume:     float
    avg_volume_20p:             float
    spread_pct:                 float
    btc_uptrend:                bool
    distance_from_breakout_pct: float
    has_resistance_within_1_5pct: bool

    # Rule outcomes (filled in by check_entry)
    score_ok:        bool = False
    close_ok:        bool = False
    volume_ok:       bool = False
    no_resistance_ok: bool = False
    spread_ok:       bool = False
    btc_ok:          bool = False
    chase_ok:        bool = False     # < 2% from breakout

    @property
    def passes(self) -> bool:
        return all([self.score_ok, self.close_ok, self.volume_ok,
                    self.no_resistance_ok, self.spread_ok,
                    self.btc_ok, self.chase_ok])

    @property
    def fail_reasons(self) -> List[str]:
        out = []
        if not self.score_ok:         out.append("score < 72")
        if not self.close_ok:         out.append("4H not closed above breakout")
        if not self.volume_ok:        out.append("volume < 150% of 20p avg")
        if not self.no_resistance_ok: out.append("resistance within 1.5% above")
        if not self.spread_ok:        out.append("spread ≥ 0.10%")
        if not self.btc_ok:           out.append("BTC in active downtrend")
        if not self.chase_ok:         out.append(">2% past breakout, no pullback")
        return out


def check_entry(score: TokenScore,
                candles_4h: List[List[float]],
                btc_ema20: float, btc_ema50: float,
                avg_resistance_above: Optional[float] = None,
                ) -> EntryConfirmation:
    """Apply CHAMPION_MODE.md §3.2 confirmation checklist.

    candles_4h rows: [ts, quote_vol, close, high, low, open, base_vol]
    avg_resistance_above: nearest resistance level above current price,
                          or None if unknown (treats as no resistance).
    """
    if len(candles_4h) < 21:
        # Not enough history for the breakout level + avg-volume window
        return EntryConfirmation(
            pair=score.pair, score=score.total, god_tier=score.god_tier,
            breakout_level=0.0, breakout_candle_close=0.0,
            breakout_candle_volume=0.0, avg_volume_20p=0.0,
            spread_pct=0.0, btc_uptrend=False,
            distance_from_breakout_pct=0.0,
            has_resistance_within_1_5pct=False,
        )

    closes = [float(r[2]) for r in candles_4h]
    vols   = [float(r[1]) for r in candles_4h]   # quote (USDT) volume per bar
    breakout_level = max(closes[-21:-1])         # 20-period high BEFORE current
    last_close     = closes[-1]
    last_vol       = vols[-1]
    avg_vol_20     = sum(vols[-21:-1]) / 20

    score_ok  = score.total >= 72
    close_ok  = last_close > breakout_level
    volume_ok = last_vol >= 1.5 * avg_vol_20

    distance_pct = ((last_close - breakout_level) / breakout_level * 100
                    if breakout_level > 0 else 0)
    chase_ok = distance_pct <= 2.0

    has_resistance = (avg_resistance_above is not None and
                       last_close > 0 and
                       (avg_resistance_above - last_close) / last_close < 0.015)
    no_resistance_ok = not has_resistance

    spread_pct = score.snapshot_data.get("spread_pct", 0.0)
    spread_ok  = spread_pct < 0.10

    btc_uptrend = btc_ema20 > btc_ema50
    btc_ok      = btc_uptrend

    return EntryConfirmation(
        pair=score.pair, score=score.total, god_tier=score.god_tier,
        breakout_level=breakout_level,
        breakout_candle_close=last_close, breakout_candle_volume=last_vol,
        avg_volume_20p=avg_vol_20,
        spread_pct=spread_pct, btc_uptrend=btc_uptrend,
        distance_from_breakout_pct=distance_pct,
        has_resistance_within_1_5pct=has_resistance,
        score_ok=score_ok, close_ok=close_ok, volume_ok=volume_ok,
        no_resistance_ok=no_resistance_ok, spread_ok=spread_ok,
        btc_ok=btc_ok, chase_ok=chase_ok,
    )


# ── stop placement per §3.2 ──────────────────────────────────────────
STOP_ATR_BUFFER = 0.2          # stop = breakout_low - 0.2× ATR_4H
HARD_MAX_STOP_PCT = 0.02       # never wider than 2% from entry (Stage 1)


def compute_stop(entry_price: float,
                 breakout_candle_low: float,
                 atr_4h: float) -> float:
    """Stop = below breakout candle low minus 0.2× ATR_4H, capped at 2%
    from entry. Returns the stop PRICE (not distance)."""
    raw_stop = breakout_candle_low - STOP_ATR_BUFFER * atr_4h
    hard_floor = entry_price * (1 - HARD_MAX_STOP_PCT)
    # The stop must be the closer of {raw_stop, hard_floor} — i.e. the
    # higher value (closer to entry, smaller risk).
    return max(raw_stop, hard_floor)


# ── orchestrator ─────────────────────────────────────────────────────
class AlphaExecutor:
    """Owns the open-trade portfolio and the journal. NOT thread-safe."""

    def __init__(self, sizer: PositionSizer,
                 journal_path: Optional[Path] = None):
        self.sizer = sizer
        self.open_trades:   List[AlphaTrade] = []
        self.closed_trades: List[AlphaTrade] = []
        self.journal_path = journal_path
        self._jfh = None
        if journal_path:
            journal_path.parent.mkdir(parents=True, exist_ok=True)
            self._jfh = open(journal_path, "a", buffering=1)

    # ── entry path ───────────────────────────────────────────────────
    def try_open(self,
                 confirm: EntryConfirmation,
                 score: TokenScore,
                 entry_price: float,
                 atr_4h: float,
                 breakout_candle_low: float,
                 t_ns: int,
                 vol_percentile: Optional[float] = None,
                 ) -> Optional[AlphaTrade]:
        """Returns the new AlphaTrade if confirmation + sizer allow.
        Returns None and logs if any gate blocks."""
        if not confirm.passes:
            self._journal({
                "kind": "ENTRY_REJECTED", "t_ns": t_ns,
                "pair": score.pair, "reasons": confirm.fail_reasons,
                "confirm": _confirm_to_dict(confirm),
            })
            return None

        # Don't open a second concurrent trade on the same pair (Stage 1)
        if any(t.pair == score.pair for t in self.open_trades):
            self._journal({"kind": "ENTRY_REJECTED", "t_ns": t_ns,
                           "pair": score.pair, "reasons": ["already_open"]})
            return None

        stop_price = compute_stop(entry_price, breakout_candle_low, atr_4h)
        rec = self.sizer.compute_size(
            entry_price=entry_price, stop_price=stop_price, t_ns=t_ns,
            vol_percentile=vol_percentile, god_tier=score.god_tier,
        )
        if rec.blocked:
            self._journal({
                "kind": "ENTRY_BLOCKED_BY_SIZER", "t_ns": t_ns,
                "pair": score.pair,
                "reason": rec.block_reason,
                "state":  rec.state,
                "stage":  rec.stage,
            })
            return None

        trade = AlphaTrade(
            pair=score.pair, score=score.total, god_tier=score.god_tier,
            open_t_ns=t_ns,
            entry_price=entry_price,
            initial_stop_price=stop_price,
            breakout_level=confirm.breakout_level,
            units_total=rec.position_units,
            notional_usd=rec.notional_value,
            entry_volume=confirm.breakout_candle_volume,
            risk_amount_usd=rec.risk_amount,
            atr_4h_at_entry=atr_4h,
        )
        self.open_trades.append(trade)
        self._journal({
            "kind": "ENTRY_OPEN", "t_ns": t_ns,
            "pair": trade.pair, "score": trade.score, "god_tier": trade.god_tier,
            "entry": trade.entry_price, "stop": trade.initial_stop_price,
            "units": trade.units_total, "notional": trade.notional_usd,
            "risk_amount": trade.risk_amount_usd,
            "R_value": trade.R_value,
            "atr_4h": atr_4h,
            "rec_scalers": rec.scalers,
            "stage": rec.stage,
        })
        return trade

    # ── manage path ──────────────────────────────────────────────────
    def on_candle(self, pair: str, ts_ns: int,
                  high: float, low: float, close: float, volume: float,
                  atr_4h: float, btc_drop_1h_pct: float = 0.0):
        """Feed one 4H candle to every open trade for `pair`. Closes
        any trades whose state machine fires an exit, journals events,
        and tells the sizer about closed trade outcomes."""
        for trade in list(self.open_trades):
            if trade.pair != pair: continue
            events = trade.on_candle(
                candle_high=high, candle_low=low, candle_close=close,
                candle_volume=volume, atr_4h_now=atr_4h,
                t_ns=ts_ns, btc_drop_1h_pct=btc_drop_1h_pct,
            )
            for reason, price, units in events:
                self._journal({
                    "kind": "EXIT_PARTIAL" if not trade.closed else "EXIT_FINAL",
                    "t_ns": ts_ns, "pair": pair,
                    "reason": reason.value, "price": price, "units": units,
                    "realized_R_so_far": trade.realized_R,
                })
            if trade.closed:
                self.open_trades.remove(trade)
                self.closed_trades.append(trade)
                # Tell champion the outcome → updates streaks/throttles
                pnl_R   = trade.realized_R
                pnl_pct = pnl_R * (trade.risk_amount_usd /
                                   max(1.0, self.sizer.tracker.equity))
                self.sizer.record_trade(TradeOutcome(
                    pnl_pct=pnl_pct, pnl_R=pnl_R, t_ns=ts_ns))
                self._journal({
                    "kind": "TRADE_CLOSED", "t_ns": ts_ns, "pair": pair,
                    "score": trade.score, "god_tier": trade.god_tier,
                    "close_reason": trade.close_reason,
                    "realized_R": trade.realized_R,
                    "pnl_pct_of_equity": pnl_pct,
                })

    # ── views ────────────────────────────────────────────────────────
    def open_count(self) -> int:    return len(self.open_trades)
    def closed_count(self) -> int:  return len(self.closed_trades)

    def stats(self) -> dict:
        n = len(self.closed_trades)
        wins = sum(1 for t in self.closed_trades if t.realized_R > 0)
        total_R = sum(t.realized_R for t in self.closed_trades)
        return {
            "closed":   n,
            "wins":     wins,
            "losses":   n - wins,
            "win_rate": (wins / n) if n else 0.0,
            "total_R":  total_R,
            "avg_R":    (total_R / n) if n else 0.0,
            "open":     self.open_count(),
            "open_pairs": [t.pair for t in self.open_trades],
        }

    # ── housekeeping ────────────────────────────────────────────────
    def close(self):
        if self._jfh is not None:
            self._jfh.close()
            self._jfh = None

    def _journal(self, record: dict):
        if self._jfh is not None:
            self._jfh.write(json.dumps(record, separators=(",", ":")) + "\n")


def _confirm_to_dict(c: EntryConfirmation) -> dict:
    return {
        "score":              c.score,
        "god_tier":           c.god_tier,
        "breakout_level":     c.breakout_level,
        "spread_pct":         c.spread_pct,
        "btc_uptrend":        c.btc_uptrend,
        "distance_pct":       c.distance_from_breakout_pct,
        "score_ok":           c.score_ok,
        "close_ok":           c.close_ok,
        "volume_ok":          c.volume_ok,
        "no_resistance_ok":   c.no_resistance_ok,
        "spread_ok":          c.spread_ok,
        "btc_ok":             c.btc_ok,
        "chase_ok":           c.chase_ok,
    }
