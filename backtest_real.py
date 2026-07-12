#!/usr/bin/env python3
"""
Real-data backtest using pre-recorded 1-minute BTC/USD candles.

Data source: ff137/bitstamp-btcusd-minute-data (GitHub, public domain)
Location:    data/btcusd_1min_latest.csv   (~10 MB, 2025-01-07 → today)

Because outbound exchange APIs are blocked in this environment, we load
a CSV of real 1-minute BTC/USD candles, aggregate to the requested
timeframe, and walk the winning presets forward bar-by-bar.

Usage:
    python backtest_real.py                       # all presets, 15m
    python backtest_real.py --timeframe 5m
    python backtest_real.py --only momentum
    python backtest_real.py --bars 2000           # last N bars only
"""
import os, sys, csv, argparse, logging, time, importlib, urllib.request
from typing import List, Dict

sys.path.insert(0, os.path.dirname(__file__))
import gods_level_engine as eng

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "btcusd_1min_latest.csv")
CSV_URL  = ("https://raw.githubusercontent.com/ff137/bitstamp-btcusd-minute-data/"
            "main/data/updates/btcusd_bitstamp_1min_latest.csv")


def ensure_csv(path: str, url: str):
    if os.path.exists(path): return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"  Downloading {url} …")
    urllib.request.urlretrieve(url, path)
    print(f"  Saved to {path} ({os.path.getsize(path)/1e6:.1f} MB)")

TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}


def load_1m_bars(csv_path: str):
    from gods_level_engine import Bar
    bars = []
    with open(csv_path) as f:
        r = csv.DictReader(f)
        for row in r:
            bars.append(Bar(
                ts=int(row["timestamp"]),
                o=float(row["open"]),
                h=float(row["high"]),
                l=float(row["low"]),
                c=float(row["close"]),
                v=float(row["volume"]),
            ))
    return bars


def aggregate(bars_1m, minutes: int):
    """Roll 1m bars into N-minute bars by grouping on ts // (minutes*60)."""
    from gods_level_engine import Bar
    if minutes == 1:
        return bars_1m
    out, cur = [], []
    bucket = None
    for b in bars_1m:
        bk = b.ts // (minutes * 60)
        if bucket is None:
            bucket = bk
        if bk != bucket:
            if cur:
                out.append(Bar(
                    ts=cur[0].ts, o=cur[0].o,
                    h=max(x.h for x in cur),
                    l=min(x.l for x in cur),
                    c=cur[-1].c,
                    v=sum(x.v for x in cur),
                ))
            cur = [b]
            bucket = bk
        else:
            cur.append(b)
    if cur:
        out.append(Bar(
            ts=cur[0].ts, o=cur[0].o,
            h=max(x.h for x in cur),
            l=min(x.l for x in cur),
            c=cur[-1].c, v=sum(x.v for x in cur),
        ))
    return out


# Preset list mirrors the winners from compare_strategies.py,
# but adapted for single-pair (BTC) real-data walk-forward.
ALL9 = ["ScalpGod", "MomentumRider", "VWAPSniper", "StructureBreak",
        "RSIReversal", "EMAStack", "VolumeSurge", "MACDCross", "BBSqueeze"]

def preset(name, agents, min_votes=3, max_pos_pct=0.08, rr_min=1.0, hold_mult=60,
           stop_atr=0.70, stop_cap=0.0080, tp1_r=0.6, tp2_r=1.1, tp3_r=1.8,
           htf_filter=False, agent_weight=False):
    return {"name": name, "agents": agents, "min_votes": min_votes,
            "max_pos_pct": max_pos_pct, "rr_min": rr_min, "hold_mult": hold_mult,
            "stop_atr": stop_atr, "stop_cap": stop_cap,
            "tp1_r": tp1_r, "tp2_r": tp2_r, "tp3_r": tp3_r,
            "htf_filter": htf_filter, "agent_weight": agent_weight}


PRESETS = [
    # ── Progression ladder: each row adds one plugin to WIDE-STOP ──
    preset("0. WIDE-STOP baseline",                    ALL9),
    preset("1. + HTF filter",                          ALL9, htf_filter=True),
    preset("2. + HTF + Agent Weighting",               ALL9, htf_filter=True,
           agent_weight=True),

    # ── Agent weighting without HTF (to isolate effect) ──
    preset("A. WIDE-STOP + Agent Weighting only",      ALL9, agent_weight=True),

    # ── Other families with both plugins ──
    preset("B. CONSERVATIVE + HTF + Weighting",        ALL9,
           min_votes=5, max_pos_pct=0.05, rr_min=1.5,
           htf_filter=True, agent_weight=True),
    preset("C. MEAN-REVERSION + Weighting (no HTF)",
           ["RSIReversal", "VWAPSniper", "BBSqueeze"],
           min_votes=2, max_pos_pct=0.06, rr_min=1.0, hold_mult=50,
           agent_weight=True),
]


# Daily-timeframe presets — wider stops and TPs sized for 1d ATR (~4%).
# Use --tf 1d to run these. 30-bar hold cap = ~1 month max position.
PRESETS_1D = [
    preset("D1. SWING (all9, 3/9, ATR×0.5, TP3=2.0R)",
           ALL9, min_votes=3, max_pos_pct=0.10, rr_min=1.5, hold_mult=30,
           stop_atr=0.50, stop_cap=0.025, tp1_r=0.7, tp2_r=1.3, tp3_r=2.0),
    preset("D2. SWING + Agent Weighting",
           ALL9, min_votes=3, max_pos_pct=0.10, rr_min=1.5, hold_mult=30,
           stop_atr=0.50, stop_cap=0.025, tp1_r=0.7, tp2_r=1.3, tp3_r=2.0,
           agent_weight=True),
    preset("D3. WIDE SWING (ATR×0.7, TP3=2.5R)",
           ALL9, min_votes=3, max_pos_pct=0.10, rr_min=1.5, hold_mult=30,
           stop_atr=0.70, stop_cap=0.035, tp1_r=0.7, tp2_r=1.4, tp3_r=2.5),
    preset("D4. MOMENTUM SWING (5 agents, 2/5)",
           ["MomentumRider", "MACDCross", "StructureBreak", "EMAStack", "VolumeSurge"],
           min_votes=2, max_pos_pct=0.10, rr_min=1.5, hold_mult=30,
           stop_atr=0.50, stop_cap=0.025, tp1_r=0.7, tp2_r=1.3, tp3_r=2.0),
    preset("D5. CONSERVATIVE SWING (5/9, R:R>=2.0)",
           ALL9, min_votes=5, max_pos_pct=0.06, rr_min=2.0, hold_mult=30,
           stop_atr=0.50, stop_cap=0.025, tp1_r=0.7, tp2_r=1.3, tp3_r=2.0),
    preset("D6. MEAN-REV SWING (3 agents, 2/3)",
           ["RSIReversal", "VWAPSniper", "BBSqueeze"],
           min_votes=2, max_pos_pct=0.08, rr_min=1.0, hold_mult=20,
           stop_atr=0.70, stop_cap=0.030, tp1_r=0.7, tp2_r=1.2, tp3_r=1.8),
]


# Patch time.time() so TIME_STOP uses bar ts, not wall clock
_SIM_NOW = [0]
eng.time.time = lambda: _SIM_NOW[0]


def run_preset(preset, bars, tf_minutes, balance, htf_bars=None):
    importlib.reload(eng)
    from gods_level_engine import C, Sig, Exchange, ALL_AGENTS, Consensus, TM, htf_bullish
    # Re-patch time.time after reload
    eng.time.time = lambda: _SIM_NOW[0]

    logging.disable(logging.CRITICAL)

    C.MIN_VOTES     = preset["min_votes"]
    C.MAX_POS_PCT   = preset["max_pos_pct"]
    C.MAX_HOLD_SEC  = preset["hold_mult"] * tf_minutes * 60
    C.STOP_ATR_MULT = preset["stop_atr"]
    C.STOP_PCT_CAP  = preset["stop_cap"]
    C.TP1_R         = preset["tp1_r"]
    C.TP2_R         = preset["tp2_r"]
    C.TP3_R         = preset["tp3_r"]
    C.HTF_FILTER_ENABLED   = preset.get("htf_filter",    False)
    C.AGENT_WEIGHT_ENABLED = preset.get("agent_weight",  False)
    rr_min          = preset["rr_min"]

    # Per-agent rolling stats for Plugin #2
    agent_stats: Dict[str, List[bool]] = {}

    name_to_cls = {A.__name__: A for A in ALL_AGENTS}
    selected    = [name_to_cls[n]() for n in preset["agents"] if n in name_to_cls]

    tm  = TM(Exchange())
    con = Consensus()

    bal, sess_start = balance, balance
    pair_losses = 0
    LOOKBACK = 200
    entries  = 0
    diag = {"no_dec": 0, "bad_rr": 0, "bad_fee": 0, "bad_risk": 0, "small_sz": 0,
            "htf_veto": 0}

    def pos_sz(conf):
        b = bal * C.MAX_POS_PCT * conf
        b = min(b, bal * C.MAX_POS_PCT)
        b = max(b, bal * 0.01)
        if pair_losses >= 2: b *= 0.5
        return round(b, 2)

    for i in range(LOOKBACK, len(bars)):
        window = bars[max(0, i - LOOKBACK):i + 1]
        price  = bars[i].c
        _SIM_NOW[0] = bars[i].ts

        # Daily stop (realized only)
        rloss = -tm.session_pnl / sess_start if tm.session_pnl < 0 else 0.0
        if rloss >= C.DAILY_STOP:
            break

        if tm.open_t and not tm.open_t.closed:
            why = tm.update(price)
            if why:
                tm.close(price, why)
                t = tm.history[-1]
                bal += t.pnl
                pair_losses = (pair_losses + 1) if t.pnl < 0 else 0
                # Update per-agent rolling win rate (Plugin #2)
                TM.record_agent_outcome(agent_stats, t)
            continue

        votes    = [ag.run(window) for ag in selected]
        decision = con.decide(votes, agent_stats=agent_stats)
        if not decision: diag["no_dec"] += 1; continue

        # HTF regime filter (Plugin #1): only long when higher timeframe is bullish
        if C.HTF_FILTER_ENABLED and htf_bars is not None:
            cur_ts = bars[i].ts
            # latest HTF bar whose ts <= current trading bar
            htf_window = [b for b in htf_bars if b.ts <= cur_ts]
            if not htf_bullish(htf_window, C.HTF_EMA_PERIOD):
                diag["htf_veto"] += 1; continue

        sz = pos_sz(decision.conf)
        if sz < 5: diag["small_sz"] += 1; continue
        risk = price - decision.stop
        rew  = decision.tp - price
        if risk <= 0: diag["bad_risk"] += 1; continue
        if rew / risk < rr_min: diag["bad_rr"] += 1; continue
        if rew / price * 100 < C.FEE_RT * 100: diag["bad_fee"] += 1; continue

        t = tm.open("BTC_USDT", decision, sz, votes=votes)
        if t: entries += 1

    if tm.open_t and not tm.open_t.closed:
        tm.close(bars[-1].c, "END")
        t = tm.history[-1]
        bal += t.pnl
        TM.record_agent_outcome(agent_stats, t)

    trades = tm.history
    wins   = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    aw = sum(t.pnl for t in wins)   / len(wins)   if wins   else 0
    al = sum(t.pnl for t in losses) / len(losses) if losses else 0
    pf = abs(sum(t.pnl for t in wins) / sum(t.pnl for t in losses)) \
         if losses and sum(t.pnl for t in losses) != 0 else 0

    return {
        "name":     preset["name"],
        "trades":   len(trades),
        "wr":       tm.win_rate * 100,
        "pf":       pf,
        "pnl":      tm.session_pnl,
        "roi":      (bal - balance) / balance * 100,
        "end_bal":  bal,
        "entries":  entries,
        "avg_win":  aw,
        "avg_loss": al,
        "exits":    {w: sum(1 for t in trades if t.why == w)
                     for w in set(t.why for t in trades)} if trades else {},
        "diag":     diag,
    }


def print_result(r):
    print(f"\n  {r['name']}")
    print(f"    Trades: {r['trades']:>4} | WR: {r['wr']:5.1f}% | "
          f"PF: {r['pf']:5.2f} | PnL: {r['pnl']:+8.2f}  ({r['roi']:+6.2f}%) | "
          f"End: ${r['end_bal']:.2f}")
    print(f"    Avg W: ${r['avg_win']:+.3f}  Avg L: ${r['avg_loss']:+.3f}")
    if r["exits"]:
        ex = ", ".join(f"{w}={c}" for w, c in sorted(r["exits"].items(), key=lambda x: -x[1]))
        print(f"    Exits: {ex}")
    d = r["diag"]
    print(f"    Filtered: no-consensus={d['no_dec']}  bad_rr={d['bad_rr']}  "
          f"bad_fee={d['bad_fee']}  small_sz={d['small_sz']}  "
          f"htf_veto={d.get('htf_veto', 0)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeframe", default="4h",
                    choices=list(TF_MINUTES.keys()))
    ap.add_argument("--htf",       default=None, choices=list(TF_MINUTES.keys()),
                    help="higher timeframe for regime filter (default: 4× trading TF)")
    ap.add_argument("--bars",      type=int, default=0, help="use last N bars (0 = all)")
    ap.add_argument("--balance",   type=float, default=1000.0)
    ap.add_argument("--only",      default=None)
    ap.add_argument("--csv",       default=CSV_PATH)
    args = ap.parse_args()

    ensure_csv(args.csv, CSV_URL)

    print("═" * 88)
    print(f"  REAL-DATA BACKTEST — BTC/USD from Bitstamp (via GitHub mirror)")
    print("═" * 88)

    print(f"  Loading {args.csv} …")
    bars_1m = load_1m_bars(args.csv)
    tf_min  = TF_MINUTES[args.timeframe]
    bars    = aggregate(bars_1m, tf_min)

    # Build HTF series (default: 4× the trading timeframe, clamped to supported set)
    htf_pref = args.htf or {"1m":"5m","5m":"15m","15m":"1h","1h":"4h","4h":"1d","1d":"1d"}[args.timeframe]
    htf_min  = TF_MINUTES[htf_pref]
    htf_bars = aggregate(bars_1m, htf_min)

    if args.bars:
        bars = bars[-args.bars:]
        cutoff_ts = bars[0].ts
        htf_bars  = [b for b in htf_bars if b.ts <= bars[-1].ts and b.ts >= cutoff_ts - htf_min*60*60]

    from datetime import datetime, timezone
    t0 = datetime.fromtimestamp(bars[0].ts,  tz=timezone.utc)
    t1 = datetime.fromtimestamp(bars[-1].ts, tz=timezone.utc)
    span_days = (bars[-1].ts - bars[0].ts) / 86400
    print(f"  Timeframe: {args.timeframe}  |  Bars: {len(bars)}  |  Span: {span_days:.1f} days")
    print(f"  HTF:       {htf_pref} ({len(htf_bars)} bars, used by Plugin #1 HTF filter)")
    print(f"  Range: {t0.date()} → {t1.date()}  |  ${bars[0].c:.0f} → ${bars[-1].c:.0f}")
    print(f"  Balance: ${args.balance:.2f}  |  Fees: {0.25}% round-trip")

    # Pick preset family by timeframe
    base_presets = PRESETS_1D if args.timeframe == "1d" else PRESETS
    presets = base_presets
    if args.only:
        presets = [p for p in base_presets if args.only.lower() in p["name"].lower()]
        if not presets:
            print(f"  No preset matches '{args.only}'"); return

    results = []
    for p in presets:
        t = time.time()
        r = run_preset(p, bars, tf_min, args.balance, htf_bars=htf_bars)
        r["_sec"] = time.time() - t
        results.append(r)
        print_result(r)
        print(f"    [{r['_sec']:.1f}s]")

    if len(results) > 1:
        print("\n" + "═" * 88)
        print(f"  FINAL — {args.timeframe} real BTC/USD data ({len(bars)} bars, {span_days:.0f}d)")
        print("═" * 88)
        print(f"  {'Strategy':<42} {'Trades':>6} {'WR%':>6} {'PF':>6} {'ROI%':>8} {'End$':>10}")
        print("  " + "─" * 86)
        for r in sorted(results, key=lambda x: -x["roi"]):
            print(f"  {r['name']:<42} {r['trades']:>6} {r['wr']:>6.1f} "
                  f"{r['pf']:>6.2f} {r['roi']:>8.3f} {r['end_bal']:>10.2f}")
        print("═" * 88)


if __name__ == "__main__":
    main()
