#!/usr/bin/env python3
"""
Strategy comparison harness.

Runs the engine with different agent subsets + risk params on synthetic
candles and prints a side-by-side summary.

Usage:
    python compare_strategies.py --loops 2000
    python compare_strategies.py --only momentum --loops 5000
"""
import os, sys, argparse, logging, time, importlib

sys.path.insert(0, os.path.dirname(__file__))
import gods_level_engine as eng


def build_preset(name, agent_cls_names, min_votes, max_pos_pct, rr_min, hold_sec,
                 stop_atr=0.35, stop_cap=0.0040, tp1_r=0.8, tp2_r=1.4, tp3_r=2.2,
                 vol_mult=1.0):
    return {
        "name": name,
        "agent_cls_names": agent_cls_names,
        "min_votes": min_votes,
        "max_pos_pct": max_pos_pct,
        "rr_min": rr_min,
        "hold_sec": hold_sec,
        "stop_atr": stop_atr,
        "stop_cap": stop_cap,
        "tp1_r": tp1_r,
        "tp2_r": tp2_r,
        "tp3_r": tp3_r,
        "vol_mult": vol_mult,
    }


ALL9 = ["ScalpGod", "MomentumRider", "VWAPSniper", "StructureBreak",
        "RSIReversal", "EMAStack", "VolumeSurge", "MACDCross", "BBSqueeze"]


PRESETS = [
    # ── 1m baseline (shown for reference; fee-squeezed) ──────────
    build_preset("1m-BASELINE (all9, 3/9)",              ALL9,
                 min_votes=3, max_pos_pct=0.08, rr_min=1.0, hold_sec=900,
                 vol_mult=1.0),

    # ── 5m timeframe (vol ≈ √5 × 1m) ─────────────────────────────
    build_preset("5m-MICRO-SCALP (all9, 3/9)",           ALL9,
                 min_votes=3, max_pos_pct=0.08, rr_min=1.0, hold_sec=1800,
                 vol_mult=2.24),
    build_preset("5m-MOMENTUM",
                 ["MomentumRider", "MACDCross", "StructureBreak", "EMAStack", "VolumeSurge"],
                 min_votes=2, max_pos_pct=0.08, rr_min=1.2, hold_sec=2400,
                 vol_mult=2.24),
    build_preset("5m-MEAN-REVERSION",
                 ["RSIReversal", "VWAPSniper", "BBSqueeze"],
                 min_votes=2, max_pos_pct=0.06, rr_min=1.0, hold_sec=1500,
                 vol_mult=2.24),
    build_preset("5m-CONSERVATIVE (5/9, R:R>=1.5)",      ALL9,
                 min_votes=5, max_pos_pct=0.05, rr_min=1.5, hold_sec=1800,
                 vol_mult=2.24),
    build_preset("5m-WIDE-STOP (ATR×0.7, TP3=1.8R)",     ALL9,
                 min_votes=3, max_pos_pct=0.08, rr_min=1.0, hold_sec=1800,
                 stop_atr=0.70, stop_cap=0.0080,
                 tp1_r=0.6, tp2_r=1.1, tp3_r=1.8,
                 vol_mult=2.24),

    # ── 15m timeframe (vol ≈ √15 × 1m) ───────────────────────────
    build_preset("15m-MICRO-SCALP (all9, 3/9)",          ALL9,
                 min_votes=3, max_pos_pct=0.08, rr_min=1.0, hold_sec=5400,
                 vol_mult=3.87),
    build_preset("15m-MOMENTUM",
                 ["MomentumRider", "MACDCross", "StructureBreak", "EMAStack", "VolumeSurge"],
                 min_votes=2, max_pos_pct=0.08, rr_min=1.2, hold_sec=7200,
                 vol_mult=3.87),
    build_preset("15m-CONSERVATIVE (5/9, R:R>=1.5)",     ALL9,
                 min_votes=5, max_pos_pct=0.05, rr_min=1.5, hold_sec=5400,
                 vol_mult=3.87),
    build_preset("15m-WIDE-STOP (ATR×0.7, TP3=1.8R)",    ALL9,
                 min_votes=3, max_pos_pct=0.08, rr_min=1.0, hold_sec=5400,
                 stop_atr=0.70, stop_cap=0.0080,
                 tp1_r=0.6, tp2_r=1.1, tp3_r=1.8,
                 vol_mult=3.87),
]


def run_preset(preset, n_loops, balance):
    # Reload engine for clean state
    importlib.reload(eng)
    from gods_level_engine import (
        C, Sig, T, Exchange, ALL_AGENTS, Consensus, PairScorer, TM
    )

    logging.disable(logging.CRITICAL)

    C.MIN_VOTES    = preset["min_votes"]
    C.MAX_POS_PCT  = preset["max_pos_pct"]
    C.MAX_HOLD_SEC = preset["hold_sec"]
    C.STOP_ATR_MULT = preset["stop_atr"]
    C.STOP_PCT_CAP  = preset["stop_cap"]
    C.TP1_R         = preset["tp1_r"]
    C.TP2_R         = preset["tp2_r"]
    C.TP3_R         = preset["tp3_r"]
    C.VOL_MULT      = preset["vol_mult"]
    rr_min         = preset["rr_min"]

    # Select agents
    name_to_cls = {A.__name__: A for A in ALL_AGENTS}
    selected    = [name_to_cls[n]() for n in preset["agent_cls_names"] if n in name_to_cls]

    ex     = Exchange()
    scorer = PairScorer(ex)
    tm     = TM(ex)
    con    = Consensus()

    bal, sess_start = balance, balance
    pair_losses, pair_pnl = {}, {}
    active_pair, active_score = None, 0
    switches = entries = 0
    diag = {"no_dec": 0, "bad_rr": 0, "bad_fee": 0, "bad_risk": 0, "small_sz": 0}

    # ── Walk-forward fix: ONE long continuous series per pair ──
    # Old design re-seeded per loop → discontinuous price jumps → stop/TP
    # changes became meaningless. Now: generate a single long random walk
    # per pair and slide a lookback window through it bar-by-bar.
    LOOKBACK       = C.CANDLES            # 200 bars visible to agents
    TOTAL_BARS     = LOOKBACK + n_loops   # enough history for n_loops walk-forward

    all_bars = {p: ex.sim_bars(p, TOTAL_BARS, abs(hash(p)) % 99991)
                for p in C.PAIRS}

    def window(pair, i):
        return all_bars[pair][max(0, i - LOOKBACK):i + 1]

    def pick(excl=None, i=LOOKBACK - 1):
        nonlocal active_pair, active_score
        ab = {p: window(p, i) for p in C.PAIRS}
        r  = scorer.best(ab, exclude=excl)
        active_pair, active_score = r.pair, r.score
        return r

    def pos_sz(conf):
        b = bal * C.MAX_POS_PCT * conf
        b = min(b, bal * C.MAX_POS_PCT)
        b = max(b, bal * 0.01)
        if pair_losses.get(active_pair, 0) >= 2: b *= 0.5
        return round(b, 2)

    def need_switch(pair):
        l = pair_losses.get(pair, 0)
        p = pair_pnl.get(pair, 0.0)
        if l >= C.PAIR_LOSSES_MAX: return True
        if p / sess_start <= C.PAIR_PNL_FLOOR: return True
        return False

    pick(i=LOOKBACK - 1)

    # Walk forward bar-by-bar
    for i in range(LOOKBACK, TOTAL_BARS):
        bars  = window(active_pair, i)
        price = all_bars[active_pair][i].c

        # Daily stop (realized only)
        realized_loss = -tm.session_pnl / sess_start if tm.session_pnl < 0 else 0.0
        if realized_loss >= C.DAILY_STOP:
            break

        # Manage open trade
        if tm.open_t and not tm.open_t.closed:
            why = tm.update(price)
            if why:
                tm.close(price, why)
                t = tm.history[-1]
                bal += t.pnl
                pair_pnl[active_pair]    = pair_pnl.get(active_pair, 0) + t.pnl
                pair_losses[active_pair] = (pair_losses.get(active_pair, 0) + 1) if t.pnl < 0 else 0
                if need_switch(active_pair):
                    pair_losses[active_pair] = 0
                    pair_pnl[active_pair]    = 0.0
                    pick(excl=active_pair, i=i)
                    switches += 1
            continue

        # Re-score every 25 bars
        if i > LOOKBACK and (i - LOOKBACK) % 25 == 0:
            ab = {p: window(p, i) for p in C.PAIRS}
            rb = scorer.best(ab)
            if rb.pair != active_pair and rb.score > active_score + 10:
                active_pair, active_score = rb.pair, rb.score
                continue

        votes    = [ag.run(bars) for ag in selected]
        decision = con.decide(votes)
        if not decision: diag["no_dec"] += 1; continue

        sz = pos_sz(decision.conf)
        if sz < 5: diag["small_sz"] += 1; continue
        risk = price - decision.stop
        rew  = decision.tp - price
        if risk <= 0: diag["bad_risk"] += 1; continue
        if rew / risk < rr_min: diag["bad_rr"] += 1; continue
        if rew / price * 100 < C.FEE_RT * 100: diag["bad_fee"] += 1; continue

        t = tm.open(active_pair, decision, sz)
        if t: entries += 1

    # Close dangling
    if tm.open_t and not tm.open_t.closed:
        price = all_bars[active_pair][-1].c
        tm.close(price, "END")
        t = tm.history[-1]
        bal += t.pnl

    trades = tm.history
    wins   = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    aw = sum(t.pnl for t in wins)   / len(wins)   if wins   else 0
    al = sum(t.pnl for t in losses) / len(losses) if losses else 0
    pf = abs(sum(t.pnl for t in wins) / sum(t.pnl for t in losses)) if losses and sum(t.pnl for t in losses) != 0 else 0

    return {
        "name":     preset["name"],
        "trades":   len(trades),
        "wins":     len(wins),
        "wr":       tm.win_rate * 100,
        "pnl":      tm.session_pnl,
        "roi":      (bal - balance) / balance * 100,
        "end_bal":  bal,
        "switches": switches,
        "entries":  entries,
        "avg_win":  aw,
        "avg_loss": al,
        "pf":       pf,
        "exits":    {w: sum(1 for t in trades if t.why == w) for w in set(t.why for t in trades)} if trades else {},
        "diag":     diag,
    }


def print_result(r):
    print(f"\n  {r['name']}")
    print(f"    Trades: {r['trades']:>4} | WR: {r['wr']:5.1f}% | "
          f"PF: {r['pf']:5.2f} | PnL: {r['pnl']:+8.2f}  ({r['roi']:+6.2f}%) | "
          f"End: ${r['end_bal']:.2f}")
    print(f"    Entries attempted: {r['entries']:>3} | Pair switches: {r['switches']:>2} | "
          f"Avg W: ${r['avg_win']:+.3f}  Avg L: ${r['avg_loss']:+.3f}")
    if r["exits"]:
        ex_str = ", ".join(f"{w}={c}" for w, c in sorted(r["exits"].items(), key=lambda x: -x[1]))
        print(f"    Exits: {ex_str}")
    d = r["diag"]
    print(f"    Filtered: no-consensus={d['no_dec']}  bad_rr={d['bad_rr']}  "
          f"bad_fee={d['bad_fee']}  small_sz={d['small_sz']}")


def print_table(results):
    print("\n" + "═" * 88)
    print("  FINAL COMPARISON")
    print("═" * 88)
    print(f"  {'Strategy':<42} {'Trades':>6} {'WR%':>6} {'PF':>6} {'ROI%':>8} {'End$':>10}")
    print("  " + "─" * 86)
    for r in sorted(results, key=lambda x: -x["roi"]):
        print(f"  {r['name']:<42} {r['trades']:>6} {r['wr']:>6.1f} "
              f"{r['pf']:>6.2f} {r['roi']:>8.3f} {r['end_bal']:>10.2f}")
    print("═" * 88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loops",   type=int,   default=2000)
    ap.add_argument("--balance", type=float, default=1000.0)
    ap.add_argument("--only",    type=str,   default=None,
                    help="Substring filter for preset name (e.g. 'momentum')")
    args = ap.parse_args()

    print("═" * 88)
    print(f"  STRATEGY COMPARISON — {args.loops} loops/preset, ${args.balance} start")
    print("═" * 88)

    presets = PRESETS
    if args.only:
        presets = [p for p in PRESETS if args.only.lower() in p["name"].lower()]
        if not presets:
            print(f"  No preset matches '{args.only}'"); return

    results = []
    for p in presets:
        t0 = time.time()
        r  = run_preset(p, args.loops, args.balance)
        r["_sec"] = time.time() - t0
        results.append(r)
        print_result(r)
        print(f"    [{r['_sec']:.1f}s]")

    if len(results) > 1:
        print_table(results)


if __name__ == "__main__":
    main()
