"""
aegis_alpha.runtime — paper-shadow runtime that wires
scanner + executor + champion sizer + journal into one loop.

Cycle:
    every 4h:
        1. run scanner.run_scan(top_N)
        2. for each qualifying TokenScore (≥72):
              build EntryConfirmation, try_open() through executor
        3. for each open trade: feed latest 4H candle into
              executor.on_candle() → state machine fires exits
        4. closed trades go through journal + viability check
        5. write live snapshot for the dashboard

No real orders. Every "fill" is at the current ask price (BUY) or bid
(SELL). All P&L is paper. Stops are simulated by feeding candle highs/lows.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None

from aegis_alpha.executor import (AlphaExecutor, EntryConfirmation,
                                   check_entry, compute_stop)
from aegis_alpha.scanner  import TokenScore, fetch_candles, run_scan
from aegis_alpha.regime   import (Regime, RegimeReading, classify_regime,
                                   regime_allows_1h)
from aegis_alpha.global_exposure import (can_open, register_open,
                                          unregister_open, current_exposure)
from champion             import (CapitalStageTracker, PositionSizer,
                                   RiskLaws, TradeOutcome)
from champion.journal     import (JournalRecord, TradeJournal,
                                   ViabilityThresholds)
from l99.config           import CONFIG, EngineId, EnginePaths, DATA_ROOT
from l99.btc_vol          import current_pctile


log = logging.getLogger("aegis_alpha.runtime")


# ── BTC EMA helpers (for the §3.2 BTC-uptrend gate) ──────────────────
def _ema(values: List[float], n: int) -> Optional[float]:
    if len(values) < n: return None
    k = 2 / (n + 1)
    ema = sum(values[:n]) / n
    for v in values[n:]:
        ema = v * k + ema * (1 - k)
    return ema


def _fetch_btc_emas() -> tuple:
    """Returns (ema20_4h, ema50_4h) on BTC_USDT spot. (None, None) on failure."""
    try:
        rows = fetch_candles("BTC_USDT", "4h", 80)
        closes = [float(r[2]) for r in rows]
        return _ema(closes, 20), _ema(closes, 50)
    except Exception as e:
        log.warning("BTC EMA fetch failed: %s", e)
        return None, None


# ── _atr_4h helper ───────────────────────────────────────────────────
def _atr_from_candles(rows, period: int = 14) -> Optional[float]:
    if len(rows) < period + 1: return None
    highs  = [float(r[3]) for r in rows]
    lows   = [float(r[4]) for r in rows]
    closes = [float(r[2]) for r in rows]
    trs = []
    for i in range(1, len(rows)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i]  - closes[i - 1]))
        trs.append(tr)
    last = trs[-period:]
    return sum(last) / len(last) if last else None


# ── runtime ──────────────────────────────────────────────────────────
class AlphaRuntime:
    """One-shot or loop runtime for the spot momentum engine.

    Plan B: parameterized by timeframe ('4h' or '1h'). The 1H engine
    additionally gates on the 4H macro regime (DEAD → no entries) and
    shares a global exposure cap with the 4H engine via
    aegis_alpha.global_exposure. Both engines write to SEPARATE
    journals and §VI viability is evaluated per-engine.
    """

    def __init__(self,
                 starting_equity: float = None,
                 top_n: int = None,
                 dry: bool = False,
                 timeframe: str = "4h"):
        if timeframe not in ("4h", "1h"):
            raise ValueError(f"timeframe must be '4h' or '1h', got {timeframe}")
        self.timeframe       = timeframe
        self.engine_id_str   = f"aegis_alpha_{timeframe}"
        self.starting_equity = starting_equity or CONFIG.starting_equity
        # Default top_n by timeframe (Plan B Part 1)
        if top_n is not None:
            self.top_n = top_n
        elif timeframe == "1h":
            self.top_n = CONFIG.spot_universe_top_n_1h
        else:
            self.top_n = CONFIG.spot_universe_top_n_4h
        self.dry             = dry

        self.tracker  = CapitalStageTracker(starting_equity=self.starting_equity)
        self.risk     = RiskLaws()
        self.risk.update_equity(self.starting_equity, time.time_ns())
        self.sizer    = PositionSizer(self.tracker, self.risk)

        # Each timeframe gets its OWN journal (Plan B Part 5).
        # Engine snapshots also live in per-timeframe subdirs.
        base = DATA_ROOT / self.engine_id_str
        base.mkdir(parents=True, exist_ok=True)
        self.journal_path  = base / "journal.jsonl"
        self.decisions_path = base / "decisions.jsonl"
        self.snapshot_path = base / "snapshot.json"
        self.journal  = TradeJournal(self.journal_path)
        self.executor = AlphaExecutor(self.sizer, journal_path=self.decisions_path)

        self._cycle_n = 0

    # ── one-cycle (scan → confirm → open → manage) ─────────────────
    def run_cycle(self):
        self._cycle_n += 1
        t_ns = time.time_ns()
        log.info("[%s] cycle #%d starting", self.engine_id_str, self._cycle_n)

        # PLAN B Part 3: 1H engine is gated by the 4H macro regime.
        regime_reading: Optional[RegimeReading] = None
        regime_disabled = False
        if self.timeframe == "1h":
            regime_reading = classify_regime()
            if not regime_allows_1h(regime_reading):
                regime_disabled = True
                rname = regime_reading.regime.value if regime_reading else "UNKNOWN"
                log.info("[%s] 4H regime=%s — 1H engine DISABLED, "
                         "managing existing trades only",
                         self.engine_id_str, rname)

        # 1) Scanner
        log.info("[%s] scanning top %d spot pairs …",
                 self.engine_id_str, self.top_n)
        scores = run_scan(self.top_n)
        log.info("[%s] scan complete · qualified=%d · god_tier=%d",
                 self.engine_id_str,
                 sum(1 for s in scores if s.qualified),
                 sum(1 for s in scores if s.god_tier))

        # BTC trend gate (independent of regime classifier — §3.2 BTC-uptrend)
        btc_ema20, btc_ema50 = _fetch_btc_emas()
        if btc_ema20 is None or btc_ema50 is None:
            log.warning("[%s] BTC EMA unavailable; skipping entries this cycle",
                        self.engine_id_str)
            btc_ema20 = btc_ema50 = 1.0   # fail-closed via the gate
        # BTC vol percentile for size scaler
        vol_pct = current_pctile()

        # 2) Try entries on qualified tokens (skip if regime says DEAD for 1H)
        opens_attempted = 0
        opens_succeeded = 0
        opens_blocked_by_exposure = 0
        if regime_disabled:
            log.info("[%s] entry attempts skipped due to DEAD regime",
                     self.engine_id_str)
        else:
            for s in scores:
                if not s.qualified: continue
                if s.disqualify_reason: continue
                opens_attempted += 1
                try:
                    rows = fetch_candles(s.pair, self.timeframe, 30)
                except Exception as e:
                    log.warning("[%s] candle fetch failed for %s: %s",
                                self.engine_id_str, s.pair, e)
                    continue
                if len(rows) < 21:
                    continue
                confirm = check_entry(s, rows, btc_ema20, btc_ema50)
                if not confirm.passes:
                    log.info("[%s] %-12s NO-ENTRY: %s",
                             self.engine_id_str, s.pair,
                             ", ".join(confirm.fail_reasons[:2]))
                    continue
                entry_price  = float(rows[-1][2])
                atr_4h       = _atr_from_candles(rows) or 0.0
                breakout_low = float(rows[-1][4])

                # PLAN B Part 4: pre-flight global exposure check.
                # Use the strategy's base risk (post-vol/scaler) as
                # estimate. Worst case we'll be off by the pending
                # win-streak scaler — sizer will still cap at
                # stage.max_risk so this is a conservative pre-check.
                pre_check = can_open(self.engine_id_str,
                                       self.tracker.base_risk_pct)
                if not pre_check.allowed:
                    opens_blocked_by_exposure += 1
                    log.info("[%s] %-12s NO-ENTRY (exposure cap): %s",
                             self.engine_id_str, s.pair, pre_check.reason)
                    continue

                trade = self.executor.try_open(
                    confirm, s,
                    entry_price=entry_price, atr_4h=atr_4h,
                    breakout_candle_low=breakout_low,
                    t_ns=t_ns, vol_percentile=vol_pct)
                if trade is not None:
                    # Register the trade's actual sized risk for the cap
                    register_open(self.engine_id_str,
                                   trade_id=f"{self.engine_id_str}:{trade.pair}:{t_ns}",
                                   risk_pct=trade.risk_amount_usd /
                                            max(1.0, self.tracker.equity))
                    opens_succeeded += 1
                    log.info("[%s] OPEN %s entry=%.4f stop=%.4f units=%.4f",
                             self.engine_id_str, trade.pair, trade.entry_price,
                             trade.initial_stop_price, trade.units_total)
                time.sleep(0.15)

        # 3) Manage open trades — feed timeframe-correct candle to each.
        # IMPORTANT: trades opened in this engine use the engine's TF;
        # we fetch the same TF for management so state machine math is
        # internally consistent.
        closed_trade_ids = []
        for trade in list(self.executor.open_trades):
            try:
                rows = fetch_candles(trade.pair, self.timeframe, 20)
            except Exception:
                continue
            if not rows: continue
            last_row = rows[-1]
            high   = float(last_row[3])
            low    = float(last_row[4])
            close  = float(last_row[2])
            volume = float(last_row[1])
            atr    = _atr_from_candles(rows) or trade.atr_4h_at_entry
            was_open = not trade.closed
            self.executor.on_candle(
                pair=trade.pair, ts_ns=t_ns,
                high=high, low=low, close=close, volume=volume,
                atr_4h=atr,
            )
            # If this trade closed during on_candle, unregister exposure.
            if was_open and trade.closed:
                tid = f"{self.engine_id_str}:{trade.pair}:{trade.open_t_ns}"
                unregister_open(tid)
                closed_trade_ids.append(tid)

        # 4) Journal closed trades — engine label includes timeframe so
        # §VI viability is computed per-timeframe (Plan B Part 5).
        for trade in self.executor.closed_trades[-(opens_succeeded + 5):]:
            if getattr(trade, "_journaled", False): continue
            rec = JournalRecord(
                t_close_ns   = trade.closed_t_ns or t_ns,
                engine       = self.engine_id_str,
                pair         = trade.pair,
                direction    = "LONG",
                entry_price  = trade.entry_price,
                exit_price   = trade.last_price,
                units        = trade.units_total,
                pnl_usd      = trade.realized_R * trade.risk_amount_usd,
                pnl_pct      = (trade.realized_R * trade.risk_amount_usd /
                                max(1.0, self.tracker.equity)),
                pnl_R        = trade.realized_R,
                held_seconds = (trade.closed_t_ns - trade.open_t_ns) // 1_000_000_000
                                if trade.closed_t_ns else 0,
                close_reason = trade.close_reason,
                score        = trade.score,
                god_tier     = trade.god_tier,
            )
            self.journal.record(rec)
            trade._journaled = True

        # 5) Viability check + snapshot
        metrics = self.journal.compute_metrics(window=50, engine=self.engine_id_str)
        exposure_snap = current_exposure()
        self._write_snapshot({
            "engine":          self.engine_id_str,
            "timeframe":       self.timeframe,
            "cycle":           self._cycle_n,
            "ts":              t_ns,
            "open_trades":     self.executor.open_count(),
            "closed_trades":   self.executor.closed_count(),
            "opens_attempted": opens_attempted,
            "opens_succeeded": opens_succeeded,
            "opens_blocked_by_exposure": opens_blocked_by_exposure,
            "stage":           int(self.tracker.stage),
            "equity":          self.tracker.equity,
            "btc_vol_pctile":  vol_pct,
            "regime":          (regime_reading.regime.value
                                  if regime_reading else None),
            "regime_disabled": regime_disabled,
            "global_exposure": exposure_snap,
            "viability":       {
                "n_trades":   metrics.n_trades,
                "win_rate":   metrics.win_rate,
                "ev_per_trade": metrics.ev_per_trade,
                "is_viable":  metrics.is_viable,
                "fail_reasons": metrics.fail_reasons,
            },
        })
        if (metrics.n_trades >= 50 and not metrics.is_viable):
            log.warning("[aegis] VIABILITY GATE FAIL — %s",
                        ", ".join(metrics.fail_reasons))
            self._tg_alert(
                f"⚠️ aegis VIABILITY FAIL after {metrics.n_trades} trades\n"
                + "\n".join(metrics.fail_reasons))

        # Telegram cycle summary (silent heartbeat)
        n_qualified = sum(1 for s in scores if s.qualified)
        n_god       = sum(1 for s in scores if s.god_tier)
        regime_tag  = (f" regime={regime_reading.regime.value}"
                        if regime_reading else "")
        self._tg_alert(
            f"{self.engine_id_str} cycle #{self._cycle_n}{regime_tag}\n"
            f"scanned={len(scores)} qual={n_qualified} god={n_god}\n"
            f"opens: tried={opens_attempted} ok={opens_succeeded} "
            f"blocked_exp={opens_blocked_by_exposure}\n"
            f"open={self.executor.open_count()} closed={self.executor.closed_count()}\n"
            f"stage={int(self.tracker.stage)} eq=${self.tracker.equity:,.2f}",
            silent=True, tag=self.engine_id_str)

        log.info("[%s] cycle #%d done · open=%d · closed=%d · "
                 "blocked_by_exposure=%d",
                 self.engine_id_str, self._cycle_n,
                 self.executor.open_count(), self.executor.closed_count(),
                 opens_blocked_by_exposure)

    def loop(self, interval_s: int = None):
        if interval_s is None:
            interval_s = (CONFIG.alpha_1h_scan_interval_s
                          if self.timeframe == "1h"
                          else CONFIG.alpha_scan_interval_s)
        log.info("[%s] loop running (every %ds), Ctrl-C to stop",
                 self.engine_id_str, interval_s)
        try:
            while True:
                self.run_cycle()
                if self.dry:
                    return
                time.sleep(interval_s)
        except KeyboardInterrupt:
            log.info("[%s] interrupted; flushing journal", self.engine_id_str)
            self.journal.close()
            self.executor.close()

    def _write_snapshot(self, blob: dict):
        try:
            tmp = self.snapshot_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(blob, indent=2, default=str))
            tmp.replace(self.snapshot_path)
        except Exception as e:
            log.warning("[aegis] snapshot write failed: %s", e)

    def _tg_alert(self, body: str, silent: bool = False, tag: str = "aegis"):
        """Best-effort Telegram. No-op if not configured."""
        try:
            from telegram_alerts import notify
            notify(body, silent=silent, tag=tag)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once",   action="store_true",
                    help="run a single cycle and exit (for cron / testing)")
    ap.add_argument("--top",    type=int, default=None,
                    help="universe size; defaults from config per timeframe")
    ap.add_argument("--equity", type=float, default=CONFIG.starting_equity)
    ap.add_argument("--timeframe", default="4h", choices=["4h", "1h"],
                    help="aegis timeframe (Plan B: '1h' enables parallel engine)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    rt = AlphaRuntime(starting_equity=args.equity, top_n=args.top,
                       dry=args.once, timeframe=args.timeframe)
    if args.once:
        rt.run_cycle()
    else:
        rt.loop()


if __name__ == "__main__":
    main()
