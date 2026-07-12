"""
l99.cli — central dispatcher for the unified L99 system.

Subcommands:
    status            — print engine activation + last snapshots
    scan-alpha        — run aegis_alpha scanner (one-shot)
    paper-alpha       — run aegis_alpha paper-shadow runtime
                          --once: single cycle and exit
                          (no flag): infinite loop on the configured
                          interval (default 4h)
    halt-all          — write a global kill flag every engine reads
    resume-all        — clear the kill flag
    btc-vol           — print current BTC 14d realized-vol percentile
    journal-stats     — Champion §VI viability metrics on rolling 50

Run: python -m l99 <subcommand> [options]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from l99.config import CONFIG, EngineId, EnginePaths, DATA_ROOT


KILL_FLAG = DATA_ROOT / "KILL_ALL"


def cmd_status(args):
    print(f"L99 STATUS  (starting equity ${CONFIG.starting_equity:,.0f})")
    print("=" * 70)
    print(f"  Killed:           {KILL_FLAG.exists()}")
    print(f"  Engine flags:     godmode={CONFIG.enable_godmode} "
          f"aegis={CONFIG.enable_aegis} predator={CONFIG.enable_predator}")
    print()
    for eid in EngineId:
        paths = EnginePaths.for_engine(eid)
        print(f"  ── {eid.value:<16} ──")
        if paths.snapshot.exists():
            try:
                blob = json.loads(paths.snapshot.read_text())
                age  = int(time.time() - paths.snapshot.stat().st_mtime)
                print(f"     last snapshot: {age}s ago")
                if "open_trades" in blob:
                    print(f"     open trades:   {blob['open_trades']}")
                if "closed_trades" in blob:
                    print(f"     closed trades: {blob['closed_trades']}")
                if "viability" in blob:
                    v = blob["viability"]
                    print(f"     viability:     "
                          f"{v.get('n_trades', 0)} trades, "
                          f"viable={v.get('is_viable')}")
            except Exception as e:
                print(f"     (snapshot unreadable: {e})")
        else:
            print(f"     no snapshot yet")


def cmd_scan_alpha(args):
    from aegis_alpha.scanner import run_scan
    print(f"L99 ▸ aegis-alpha scan (top {args.top})")
    scores = run_scan(args.top)
    qualified = sum(1 for s in scores if s.qualified)
    god = sum(1 for s in scores if s.god_tier)
    print(f"\nResults: {len(scores)} scanned · {qualified} qualified · {god} god-tier")
    for s in scores[:args.show]:
        flag = "🏆" if s.god_tier else "✅" if s.qualified else "·"
        print(f"  {flag} {s.pair:<14} score={s.total:.1f}  "
              f"24h_vol_M={s.snapshot_data.get('vol_24h_usd', 0)/1e6:.1f}  "
              f"ret24h={s.snapshot_data.get('ret_24h_pct', 0):+.2f}%")


def cmd_paper_alpha(args):
    from aegis_alpha.runtime import AlphaRuntime
    rt = AlphaRuntime(starting_equity=args.equity, top_n=args.top,
                      dry=args.once, timeframe=args.timeframe)
    if args.once:
        rt.run_cycle()
    else:
        rt.loop()


def cmd_halt_all(args):
    KILL_FLAG.parent.mkdir(parents=True, exist_ok=True)
    KILL_FLAG.touch()
    print(f"🛑 KILL FLAG written → {KILL_FLAG}")
    print("   Every running engine sees this and refuses new entries.")
    print("   Run `python -m l99 resume-all` to clear.")


def cmd_resume_all(args):
    if KILL_FLAG.exists():
        KILL_FLAG.unlink()
        print(f"✅ KILL FLAG cleared")
    else:
        print("(no kill flag set)")


def cmd_btc_vol(args):
    from l99.btc_vol import current_pctile
    pct = current_pctile(force_refresh=args.refresh)
    if pct is None:
        print("BTC vol pctile: unavailable")
    else:
        regime = ("HIGH (>80pct)" if pct >= 0.80 else
                  "LOW  (<20pct)" if pct <= 0.20 else
                  "NORMAL")
        print(f"BTC 14d realized vol percentile: {pct:.2%} → regime {regime}")


def cmd_journal_stats(args):
    from champion.journal import TradeJournal
    eid = EngineId(args.engine) if args.engine else None
    paths = EnginePaths.for_engine(eid) if eid else None
    if paths is None:
        print("usage: --engine godmode|aegis_alpha|quant_predator")
        return
    if not paths.journal.exists():
        print(f"no journal at {paths.journal}")
        return
    j = TradeJournal(paths.journal)
    m = j.compute_metrics(window=args.window, engine=eid.value)
    print(f"L99 ▸ journal stats · engine={eid.value} · window={args.window}")
    print("=" * 70)
    print(f"  Trades:           {m.n_trades} ({m.n_wins}W / {m.n_losses}L)")
    print(f"  Win rate:         {m.win_rate*100:.2f}%")
    print(f"  Avg R per win:    {m.avg_r_per_win:+.2f}")
    print(f"  Avg R per loss:   {m.avg_r_per_loss:+.2f}")
    print(f"  EV per trade:     {m.ev_per_trade:+.3f}R")
    print(f"  Profit factor:    {m.profit_factor:.2f}")
    print(f"  Max consec loss:  {m.max_consec_losses}")
    print(f"  Approx max DD:    {m.max_drawdown*100:.1f}%")
    print(f"  Champion VIABLE:  {'✅' if m.is_viable else '🛑'}")
    if not m.is_viable:
        for r in m.fail_reasons:
            print(f"     - {r}")


def main(argv=None):
    p  = argparse.ArgumentParser(prog="l99",
                                  description="L99 unified champion-mode CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status",      help="print engine activation + snapshots")

    sa = sub.add_parser("scan-alpha", help="aegis-alpha 4H scanner one-shot")
    sa.add_argument("--top",  type=int, default=CONFIG.spot_universe_top_n)
    sa.add_argument("--show", type=int, default=20)

    pa = sub.add_parser("paper-alpha", help="aegis-alpha paper-shadow runtime")
    pa.add_argument("--once",   action="store_true",
                     help="run one cycle and exit")
    pa.add_argument("--top",    type=int,   default=None,
                     help="universe size (defaults from config per timeframe)")
    pa.add_argument("--equity", type=float, default=CONFIG.starting_equity)
    pa.add_argument("--timeframe", default="4h", choices=["4h", "1h"],
                     help="Plan B: '1h' runs parallel 1H engine")

    re = sub.add_parser("regime", help="print current 4H macro regime")

    sub.add_parser("halt-all",   help="write global kill flag")
    sub.add_parser("resume-all", help="clear global kill flag")

    bv = sub.add_parser("btc-vol",     help="BTC 14d realized vol percentile")
    bv.add_argument("--refresh", action="store_true",
                     help="bypass cache (force fresh fetch)")

    js = sub.add_parser("journal-stats", help="Champion §VI viability metrics")
    js.add_argument("--engine", required=True,
                     choices=[e.value for e in EngineId])
    js.add_argument("--window", type=int, default=50)

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    def cmd_regime(args):
        from aegis_alpha.regime import classify_regime, regime_allows_1h
        r = classify_regime()
        if r is None:
            print("Regime classifier failed (data unavailable).")
            return
        print(f"4H REGIME · {r.regime.value}")
        print(f"   close   = {r.btc_close:,.2f}")
        print(f"   ema20   = {r.btc_ema20:,.2f}")
        print(f"   ema50   = {r.btc_ema50:,.2f}")
        print(f"   slope   = {r.btc_ema20_slope*100:+.2f}%/10bars")
        print(f"   atr_now = {r.atr_now:,.2f}  baseline {r.atr_baseline:,.2f}"
              f"  ratio {r.atr_ratio:.2f}")
        print(f"   1H allowed: {regime_allows_1h(r)}")
        for r_str in r.reasons:
            print(f"   reason: {r_str}")

    handlers = {
        "status":         cmd_status,
        "scan-alpha":     cmd_scan_alpha,
        "paper-alpha":    cmd_paper_alpha,
        "halt-all":       cmd_halt_all,
        "resume-all":     cmd_resume_all,
        "btc-vol":        cmd_btc_vol,
        "journal-stats":  cmd_journal_stats,
        "regime":         cmd_regime,
    }
    handlers[args.cmd](args)


if __name__ == "__main__":
    main()
