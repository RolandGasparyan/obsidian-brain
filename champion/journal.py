"""
champion.journal — unified trade journal + statistical viability gate.

Every closed trade from any engine writes one line to a shared JSONL.
The viability gate auto-pauses trading when our 50+ trade rolling
metrics drop below CHAMPION_MODE.md §VI minimum-viable thresholds:

    Win rate                  ≥ 48%
    Avg R per win             ≥ 2.0R
    EV per trade              ≥ +0.48R
    Profit factor             ≥ 1.3
    Max consecutive losses    ≤ 8
    Max drawdown              < 20%

Below ANY of these on the most recent 50 trades = FAIL → engine pause.
The doctrine says "If after 50+ live trades any column is BELOW
minimum → stop. Redesign. Retrain."

API:
    journal = TradeJournal(path)
    journal.record(closed_trade_dict)
    metrics = journal.compute_metrics(window=50)
    if not metrics.is_viable:
        log("VIABILITY GATE FAIL — pausing engine: %s", metrics.fail_reasons)
"""
from __future__ import annotations

import json
import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Deque, Dict, List, Optional


log = logging.getLogger("champion.journal")


# ── Champion §VI thresholds ──────────────────────────────────────────
@dataclass(frozen=True)
class ViabilityThresholds:
    win_rate_min:       float = 0.48
    avg_r_per_win_min:  float = 2.0
    ev_per_trade_min:   float = 0.48      # in R units
    profit_factor_min:  float = 1.3
    max_consec_losses:  int   = 8
    max_drawdown_max:   float = 0.20      # 20%
    min_trades:         int   = 50


@dataclass
class ViabilityMetrics:
    n_trades:        int
    n_wins:          int
    n_losses:        int
    win_rate:        float
    avg_r_per_win:   float
    avg_r_per_loss:  float
    ev_per_trade:    float
    profit_factor:   float
    max_consec_losses: int
    max_drawdown:    float
    is_viable:       bool
    fail_reasons:    List[str] = field(default_factory=list)


# ── trade record schema ─────────────────────────────────────────────
@dataclass
class JournalRecord:
    """One closed trade. Engines populate the relevant fields; missing
    ones are fine."""
    t_close_ns:     int
    engine:         str        # "godmode" | "aegis_alpha" | "quant_predator"
    pair:           str
    direction:      str        # "LONG" | "SHORT"
    entry_price:    float
    exit_price:     float
    units:          float
    pnl_usd:        float
    pnl_pct:        float      # signed, fraction of equity at entry
    pnl_R:          float      # signed, in R-units
    held_seconds:   int
    close_reason:   str
    score:          float = 0.0
    god_tier:       bool  = False
    risk_pct:       float = 0.0
    extra:          dict  = field(default_factory=dict)


# ── journal ──────────────────────────────────────────────────────────
class TradeJournal:
    """Append-only JSONL journal with on-the-fly viability metrics.

    Thread-safe via a single lock. Engines call .record(rec) on every
    closed trade. The viability check is computed on demand to avoid
    blocking the trading loop."""

    def __init__(self, path: Path,
                 thresholds: ViabilityThresholds = ViabilityThresholds(),
                 mem_window: int = 200):
        self.path = path
        self.thresholds = thresholds
        self._lock = threading.Lock()
        # In-memory ring of recent trades for fast metric recomputation
        self._recent: Deque[JournalRecord] = deque(maxlen=mem_window)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(path, "a", buffering=1)
        self._load_recent()

    def _load_recent(self):
        """Re-hydrate the in-memory ring from the tail of the file
        (so a restart doesn't reset rolling metrics)."""
        if not self.path.exists():
            return
        try:
            lines = self.path.read_text().splitlines()[-self._recent.maxlen:]
            for line in lines:
                try:
                    j = json.loads(line)
                    self._recent.append(JournalRecord(**j))
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            log.warning("journal hydrate failed: %s", e)

    # ── recording ────────────────────────────────────────────────────
    def record(self, rec: JournalRecord):
        with self._lock:
            self._recent.append(rec)
            self._fh.write(json.dumps(asdict(rec), separators=(",", ":")))
            self._fh.write("\n")

    def close(self):
        with self._lock:
            if self._fh is not None:
                self._fh.close()
                self._fh = None

    # ── metrics ──────────────────────────────────────────────────────
    def compute_metrics(self, window: int = 50,
                        engine: Optional[str] = None) -> ViabilityMetrics:
        """Compute Champion §VI metrics on the last `window` trades.
        Optionally filter by engine name."""
        with self._lock:
            trades = list(self._recent)

        if engine:
            trades = [t for t in trades if t.engine == engine]
        trades = trades[-window:]

        n = len(trades)
        if n == 0:
            return ViabilityMetrics(
                n_trades=0, n_wins=0, n_losses=0,
                win_rate=0.0, avg_r_per_win=0.0, avg_r_per_loss=0.0,
                ev_per_trade=0.0, profit_factor=0.0,
                max_consec_losses=0, max_drawdown=0.0,
                is_viable=False,
                fail_reasons=["no trades"],
            )

        wins   = [t for t in trades if t.pnl_R > 0]
        losses = [t for t in trades if t.pnl_R <= 0]
        nw, nl = len(wins), len(losses)
        win_rate = nw / n
        avg_w_r  = (sum(t.pnl_R for t in wins) / nw) if nw else 0.0
        avg_l_r  = (sum(t.pnl_R for t in losses) / nl) if nl else 0.0

        ev_R = sum(t.pnl_R for t in trades) / n
        gross_win  = sum(t.pnl_R for t in wins)
        gross_loss = abs(sum(t.pnl_R for t in losses))
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

        # Max consecutive losses
        max_streak = 0
        cur_streak = 0
        for t in trades:
            if t.pnl_R <= 0:
                cur_streak += 1
                if cur_streak > max_streak: max_streak = cur_streak
            else:
                cur_streak = 0

        # Max drawdown on cumulative R-curve
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in trades:
            cum += t.pnl_R
            if cum > peak: peak = cum
            dd = peak - cum
            if dd > max_dd: max_dd = dd
        # Convert max_dd from R into approximate fraction-of-equity using
        # an assumed 1.5% risk per trade (Stage 1 baseline) — purely
        # diagnostic; the hard kill is risk_laws.peak_dd anyway.
        approx_dd_pct = max_dd * 0.015

        # Viability gate
        th = self.thresholds
        fail = []
        if n < th.min_trades:
            fail.append(f"only {n} trades < min {th.min_trades}")
        if win_rate < th.win_rate_min:
            fail.append(f"win_rate {win_rate*100:.1f}% < {th.win_rate_min*100:.0f}%")
        if avg_w_r < th.avg_r_per_win_min:
            fail.append(f"avg_R_win {avg_w_r:.2f} < {th.avg_r_per_win_min}")
        if ev_R < th.ev_per_trade_min:
            fail.append(f"EV {ev_R:+.2f}R < {th.ev_per_trade_min}")
        if profit_factor < th.profit_factor_min:
            fail.append(f"PF {profit_factor:.2f} < {th.profit_factor_min}")
        if max_streak > th.max_consec_losses:
            fail.append(f"max_streak {max_streak} > {th.max_consec_losses}")
        if approx_dd_pct > th.max_drawdown_max:
            fail.append(f"approx_dd {approx_dd_pct*100:.1f}% > {th.max_drawdown_max*100:.0f}%")

        return ViabilityMetrics(
            n_trades=n, n_wins=nw, n_losses=nl,
            win_rate=win_rate, avg_r_per_win=avg_w_r, avg_r_per_loss=avg_l_r,
            ev_per_trade=ev_R, profit_factor=profit_factor,
            max_consec_losses=max_streak, max_drawdown=approx_dd_pct,
            is_viable=(len(fail) == 0),
            fail_reasons=fail,
        )
