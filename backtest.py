#!/usr/bin/env python3
"""
GODS LEVEL ENGINE — Real-Data Backtest

Fetches real 1-minute candles from Gate.io public API for all pairs,
then walks forward bar-by-bar running the full engine strategy
(10 agents, consensus, pair-scorer, trade manager).

Usage:
    python backtest.py                         # default: last 1000 bars per pair
    python backtest.py --bars 800 --votes 3
"""
import os, sys, time, json, argparse, logging
import requests

sys.path.insert(0, os.path.dirname(__file__))
import gods_level_engine as eng
from gods_level_engine import (
    C, Sig, Vote, Bar, T, ALL_AGENTS, Consensus, PairScorer, TM
)


# ── Patch time.time() inside engine so TIME_STOP uses simulated time ──
_SIM_NOW = [int(time.time())]
_real_time = time.time
def _sim_time():
    return _SIM_NOW[0]
eng.time.time = _sim_time


def fetch_bars(pair: str, limit: int = 1000, interval: str = "1m") -> list:
    """Fetch real candles from Gate.io public endpoint."""
    r = requests.get(
        "https://api.gateio.ws/api/v4/spot/candlesticks",
        params={"currency_pair": pair, "interval": interval, "limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json()
    bars = [
        Bar(int(x[0]), float(x[5]), float(x[3]),
            float(x[4]), float(x[2]), float(x[1]))
        for x in rows
    ]
    return sorted(bars, key=lambda b: b.ts)


def backtest(total_bars: int, lookback: int, balance: float, min_votes: int, pairs: list, interval: str = "1m"):
    logging.disable(logging.WARNING)
    C.MIN_VOTES = min_votes

    print("="*72)
    print("  GODS LEVEL ENGINE — REAL-DATA BACKTEST")
    print("="*72)
    print(f"  Pairs:      {', '.join(pairs)}")
    print(f"  Bars/pair:  {total_bars} ({interval})")
    print(f"  Lookback:   {lookback}")
    print(f"  Balance:    ${balance:.2f} USDT")
    print(f"  Min votes:  {min_votes}/9")

    # Fetch real data
    print(f"\n  Fetching real candles from Gate.io …")
    all_bars: dict = {}
    for p in pairs:
        try:
            bars = fetch_bars(p, limit=total_bars, interval=interval)
            if len(bars) < lookback + 50:
                print(f"    ⚠  {p:<12} only {len(bars)} bars — skipping")
                continue
            all_bars[p] = bars
            span_hr = (bars[-1].ts - bars[0].ts) / 3600
            print(f"    ✅ {p:<12} {len(bars)} bars | "
                  f"{span_hr:.1f}h | ${bars[0].c:.4f} → ${bars[-1].c:.4f}")
        except Exception as e:
            print(f"    ❌ {p:<12} {e}")

    if not all_bars:
        print("\n  No data fetched — abort.")
        return

    # Align all pairs on shortest length
    n = min(len(v) for v in all_bars.values())
    all_bars = {p: v[-n:] for p, v in all_bars.items()}

    ex     = eng.Exchange()
    scorer = PairScorer(ex)
    tm     = TM(ex)
    con    = Consensus()
    agents = [A() for A in ALL_AGENTS]

    bal, sess_start = balance, balance
    pair_losses: dict = {}
    pair_pnl:    dict = {}
    active_pair = active_score = None
    entries = switches = 0
    diag = {"no_decision":0, "tiny_size":0, "bad_risk":0, "bad_rr":0, "bad_fee":0, "agent_buys":0, "loops":0}

    def record(pair, pnl):
        pair_pnl[pair]    = pair_pnl.get(pair, 0.0) + pnl
        pair_losses[pair] = (pair_losses.get(pair, 0) + 1) if pnl < 0 else 0

    def need_switch(pair):
        l = pair_losses.get(pair, 0)
        p = pair_pnl.get(pair, 0.0)
        if l >= C.PAIR_LOSSES_MAX:      return True, f"{l} losses"
        if p/sess_start <= C.PAIR_PNL_FLOOR: return True, f"PnL {p/sess_start*100:.2f}%"
        return False, ""

    def pos_sz(conf):
        b = bal * C.MAX_POS_PCT * conf
        b = min(b, bal * C.MAX_POS_PCT)
        b = max(b, bal * 0.01)
        if pair_losses.get(active_pair, 0) >= 2: b *= 0.5
        return round(b, 2)

    # Initial pair pick using the first lookback window
    init_windows = {p: v[:lookback] for p, v in all_bars.items()}
    r0 = scorer.best(init_windows)
    active_pair, active_score = r0.pair, r0.score

    print(f"\n  Starting pair: {active_pair} (score={active_score})")
    print("─"*72)
    print(f"  {'BAR':>5}  {'EVENT':<10}  {'PAIR':<12}  {'DETAIL'}")
    print("─"*72)

    # Walk forward
    for i in range(lookback, n):
        price = all_bars[active_pair][i].c
        _SIM_NOW[0] = all_bars[active_pair][i].ts

        # Daily stop (realized PnL only)
        realized_loss = -tm.session_pnl / sess_start if tm.session_pnl < 0 else 0.0
        if realized_loss >= C.DAILY_STOP:
            print(f"\n  🛑 DAILY STOP {realized_loss*100:.2f}% hit at bar {i}")
            break

        # Manage open trade
        if tm.open_t and not tm.open_t.closed:
            why = tm.update(price)
            if why:
                usdt = tm.close(price, why)
                t = tm.history[-1]
                bal += t.pnl
                record(active_pair, t.pnl)
                icon = "✅" if t.pnl > 0 else "❌"
                print(f"  {i:>5}  {icon} CLOSED   {active_pair:<12}  "
                      f"pnl={t.pnl:+.4f} ({t.pnl_pct:+.3f}%)  "
                      f"{why:<16}  bal=${bal:.2f}")
                sw, rs = need_switch(active_pair)
                if sw:
                    old = active_pair
                    pair_losses[active_pair] = 0
                    pair_pnl[active_pair]    = 0.0
                    excl = {p: v[max(0,i-lookback):i] for p,v in all_bars.items()}
                    r2 = scorer.best(excl, exclude=old)
                    active_pair, active_score = r2.pair, r2.score
                    switches += 1
                    print(f"  {i:>5}  ⚡ SWITCH   {old} → {active_pair:<10}  {rs}")
            continue

        # Re-score every 25 bars
        if i > lookback and (i - lookback) % 25 == 0:
            wins = {p: v[max(0,i-lookback):i] for p,v in all_bars.items()}
            rbest = scorer.best(wins)
            if rbest.pair != active_pair and rbest.score > active_score + 10:
                old = active_pair
                active_pair, active_score = rbest.pair, rbest.score
                print(f"  {i:>5}  🔄 UPGRADE  {old} → {active_pair:<10}  score→{rbest.score}")
                continue

        # Run agents
        window = all_bars[active_pair][max(0,i-lookback):i+1]
        votes  = [ag.run(window) for ag in agents]
        buy_v  = sum(1 for v in votes if v.signal in (Sig.BUY, Sig.STRONG_BUY))
        diag["loops"] += 1
        diag["agent_buys"] += buy_v
        decision = con.decide(votes)
        if not decision: diag["no_decision"] += 1; continue

        sz = pos_sz(decision.conf)
        if sz < 5: diag["tiny_size"] += 1; continue
        risk = price - decision.stop
        rew  = decision.tp - price
        if risk <= 0: diag["bad_risk"] += 1; continue
        if rew/risk < 1.0: diag["bad_rr"] += 1; continue
        if rew/price*100 < C.FEE_RT*100: diag["bad_fee"] += 1; continue

        t = tm.open(active_pair, decision, sz)
        if t:
            entries += 1
            print(f"  {i:>5}  🎯 ENTERED  {active_pair:<12}  "
                  f"${sz:.2f}  {buy_v}/9 votes  conf={decision.conf:.2f}  "
                  f"@{price:.4f}  stop={decision.stop:.4f}  tp={decision.tp:.4f}")

    # Force close any dangling trade
    if tm.open_t and not tm.open_t.closed:
        price = all_bars[active_pair][-1].c
        tm.close(price, "BACKTEST_END")
        t = tm.history[-1]
        bal += t.pnl
        record(active_pair, t.pnl)

    # ── Report ──
    trades = tm.history
    pnl    = tm.session_pnl
    wr     = tm.win_rate * 100

    print("\n" + "═"*72)
    print("  BACKTEST COMPLETE")
    print("═"*72)
    print(f"  Bars walked:     {n - lookback}")
    print(f"  Span:            {(all_bars[active_pair][-1].ts - all_bars[active_pair][lookback].ts)/3600:.1f}h")
    print(f"  Entries:         {entries}")
    print(f"  Trades closed:   {len(trades)}")
    print(f"  Win rate:        {wr:.1f}%")
    print(f"  Pair switches:   {switches}")
    print(f"  Net PnL:         {pnl:+.4f} USDT")
    print(f"  Start balance:   ${balance:.2f}")
    print(f"  End balance:     ${bal:.4f}")
    print(f"  ROI:             {(bal-balance)/balance*100:+.4f}%")

    if trades:
        wins_t  = [t for t in trades if t.pnl > 0]
        losses  = [t for t in trades if t.pnl <= 0]
        aw = sum(t.pnl for t in wins_t)/len(wins_t) if wins_t else 0
        al = sum(t.pnl for t in losses)/len(losses) if losses else 0
        pf = abs(sum(t.pnl for t in wins_t) / sum(t.pnl for t in losses)) if losses and sum(t.pnl for t in losses) != 0 else 0
        print(f"  Avg win:         ${aw:+.4f}")
        print(f"  Avg loss:        ${al:+.4f}")
        print(f"  Profit factor:   {pf:.2f}")

        print("\n  PER-PAIR:")
        by_p: dict = {}
        for t in trades: by_p.setdefault(t.pair, []).append(t)
        for p, pts in sorted(by_p.items()):
            w  = sum(1 for t in pts if t.pnl > 0)
            pp = sum(t.pnl for t in pts)
            print(f"    {p:<12} {len(pts):3d} trades | wr={w/len(pts)*100:3.0f}% | pnl={pp:+.4f}")

        print("\n  EXIT TYPES:")
        et: dict = {}
        for t in trades: et[t.why] = et.get(t.why, 0) + 1
        for why, cnt in sorted(et.items(), key=lambda x: -x[1]):
            print(f"    {why:<20} {cnt:3d}×")

    print("\n  DIAGNOSTICS:")
    print(f"    Loops evaluated:   {diag['loops']}")
    print(f"    Total BUY votes:   {diag['agent_buys']} (avg {diag['agent_buys']/max(1,diag['loops']):.2f}/loop)")
    print(f"    No consensus:      {diag['no_decision']}")
    print(f"    Size too small:    {diag['tiny_size']}")
    print(f"    Risk ≤ 0:          {diag['bad_risk']}")
    print(f"    R:R < 1:           {diag['bad_rr']}")
    print(f"    Reward < fees:     {diag['bad_fee']}")

    print("\n  ✅ ALL FUNDS IN USDT — ZERO TOKENS HELD")
    print("═"*72)

    # Save
    log = {
        "mode":          "real_data_backtest",
        "pairs":         pairs,
        "bars_per_pair": n,
        "lookback":      lookback,
        "min_votes":     min_votes,
        "start_balance": balance,
        "end_balance":   bal,
        "pnl":           pnl,
        "roi_pct":       (bal-balance)/balance*100,
        "trades":        len(trades),
        "win_rate":      wr,
        "switches":      switches,
        "history": [
            {"pair": t.pair, "entry": t.entry, "exit": t.exit_px,
             "pnl": t.pnl, "pnl_pct": t.pnl_pct, "why": t.why}
            for t in trades
        ],
    }
    fname = f"backtest_results_{int(_real_time())}.json"
    fpath = os.path.join(os.path.dirname(__file__), fname)
    with open(fpath, "w") as f: json.dump(log, f, indent=2)
    print(f"\n  📝 Results saved: {fname}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars",    type=int, default=1000)
    ap.add_argument("--lookback",type=int, default=200)
    ap.add_argument("--balance", type=float, default=1000.0)
    ap.add_argument("--votes",   type=int, default=3)
    ap.add_argument("--pairs",   nargs="+", default=None)
    ap.add_argument("--interval",default="1m", help="1m | 5m | 15m | 1h")
    args = ap.parse_args()
    backtest(args.bars, args.lookback, args.balance, args.votes,
             args.pairs or C.PAIRS, args.interval)
