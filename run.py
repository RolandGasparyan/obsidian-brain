#!/usr/bin/env python3
"""
GODS LEVEL ENGINE — Launcher
Run: python run.py            (paper simulation)
     python run.py --live     (live trading, needs API keys)
     python run.py --loops N  (set simulation loops, default 500)
     python run.py --dryrun   (28-check system test)
"""

import sys, os, argparse, time, json, logging
sys.path.insert(0, os.path.dirname(__file__))

def parse_args():
    p = argparse.ArgumentParser(description="Gods Level Trading Engine")
    p.add_argument("--live",   action="store_true", help="Enable live trading")
    p.add_argument("--paper-real", action="store_true",
                   help="Paper orders, but fetch real candles from exchange (Stage 1 forward-test)")
    p.add_argument("--strategy", default="legacy",
                   choices=["legacy", "ma50", "ma100", "ma50w10", "ma50w20",
                            "ma20w5", "vote"],
                   help="legacy=9-agent voting · ma50/ma100=daily SMA trend follow · "
                        "ma50w10/ma50w20=daily MA50 + weekly MA filter · "
                        "ma20w5=param-sweep-winning MA · "
                        "vote=MA20+W5 + Donchian-20 + BTC-gate ensemble (current SHIP candidate)")
    p.add_argument("--interval", default="1m",
                   choices=["1m","5m","15m","1h","4h","1d"],
                   help="Candle interval for real-data fetches (default 1m for legacy, 1d for MA)")
    p.add_argument("--loops",  type=int, default=500, help="Simulation loops (default 500)")
    p.add_argument("--dryrun", action="store_true", help="Run 28-check diagnostic")
    p.add_argument("--pairs",  nargs="+", help="Override trading pairs")
    p.add_argument("--balance",type=float, default=1000.0, help="Starting balance USDT")
    p.add_argument("--votes",  type=int,   default=3, help="Min agent votes to enter (default 3)")
    p.add_argument("--csv-replay", metavar="PATH",
                   help="Replay a 1m BTC CSV through the MA strategy (offline forward-test)")
    return p.parse_args()


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║   ⚡  GODS LEVEL ENGINE  ⚡                                                   ║
║   Single Pair · 10 Agents · Micro Scalping · USDT Only · 24/7               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  RULES:                                                                      ║
║  1. Score all pairs → trade the SINGLE best one                              ║
║  2. All 10 agents scalp that one pair simultaneously                         ║
║  3. Pair losing? EXIT ALL → 100% USDT → pick next best pair                 ║
║  4. Zero tokens held between trades — always USDT                            ║
║                                                                              ║
║  ⚠  Paper mode by default. Never risk more than you can afford to lose.     ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


def run_dryrun():
    """Run 28-check diagnostic."""
    logging.disable(logging.CRITICAL)
    from gods_level_engine import (
        C, Sig, Vote, T, Exchange, ALL_AGENTS, Consensus,
        PairScorer, TM, GodsEngine, make_vote
    )

    print("="*72)
    print("  DRY RUN — 28 SYSTEM CHECKS")
    print("="*72)

    PASS = 0; FAIL = 0
    ex = Exchange(); con = Consensus()

    def ok(n, label, detail=""):
        nonlocal PASS; PASS += 1
        print(f"  ✅  [{n:02d}] {label:<38} {detail}")

    def fail(n, label, detail=""):
        nonlocal FAIL; FAIL += 1
        print(f"  ❌  [{n:02d}] {label:<38} {detail}")

    # Find best scenario
    best_count=0; best_seed=0; best_pair="BTC_USDT"; best_bars=None; best_votes=[]
    for seed in range(0, 5000, 50):
        for pair in C.PAIRS:
            bars   = ex.sim_bars(pair, 200, seed)
            agents = [A() for A in ALL_AGENTS]
            votes  = [ag.run(bars) for ag in agents]
            bv     = sum(1 for v in votes if v.signal in (Sig.BUY, Sig.STRONG_BUY))
            if bv > best_count:
                best_count=bv; best_seed=seed; best_pair=pair
                best_bars=bars; best_votes=votes
            if best_count >= 5: break
        if best_count >= 5: break

    # Section A
    bars200 = ex.sim_bars("BTC_USDT", 200, 99)
    bars_alt= ex.sim_bars("BTC_USDT", 200, 100)
    cl = T.closes(bars200); bb = T.bb(cl, 20, 2.0)
    ok(1, "Module import", "all classes loaded")
    (ok if len(bars200)==200 and all(b.h>=b.l for b in bars200) else fail)(
        2, "Bar simulation 200 candles", f"close={bars200[-1].c:.2f}")
    (ok if bars200[-1].c != bars_alt[-1].c else fail)(
        3, "Different seeds → different markets", f"{bars200[-1].c:.2f} ≠ {bars_alt[-1].c:.2f}")
    (ok if all([T.last(T.ema(cl,9)) and T.last(T.ema(cl,9))>0,
                0 < T.last(T.rsi(cl,7)) < 100,
                T.last(T.atr(bars200,14)) > 0,
                T.last(bb["u"]) > T.last(bb["m"]) > T.last(bb["l"])]) else fail)(
        4, "All indicators compute", f"EMA9={T.last(T.ema(cl,9)):.2f} RSI7={T.last(T.rsi(cl,7)):.1f}")

    # Section B
    scorer = PairScorer(ex)
    all_bars = {p: ex.sim_bars(p, 200, abs(hash(p))%9999) for p in C.PAIRS}
    ranks = sorted([scorer.score(p, all_bars[p]) for p in C.PAIRS], key=lambda r: r.score, reverse=True)
    top = ranks[0]
    (ok if len(ranks)==len(C.PAIRS) else fail)(
        5, f"Pair scorer scores all {len(C.PAIRS)} pairs", f"{len(ranks)}/{len(C.PAIRS)} scored")
    (ok if top.score == max(r.score for r in ranks) else fail)(
        6, "Best pair selected correctly", f"→{top.pair} score={top.score}")
    excl = scorer.best({p:b for p,b in all_bars.items() if p!=top.pair})
    (ok if excl.pair != top.pair else fail)(7, "Pair exclusion works", f"excluded {top.pair}")

    # Section C
    agents = [A() for A in ALL_AGENTS]
    vote_list = []
    ag_pass = 0
    for ag, v in zip(agents, best_votes):
        ok_v = (isinstance(v, Vote) and v.signal in (Sig.BUY,Sig.STRONG_BUY,Sig.HOLD)
                and 0<=v.conf<=1 and v.stop>0 and v.tp>0)
        if ok_v: ag_pass+=1; vote_list.append(v)
    (ok if ag_pass==9 else fail)(8, "All 9 agents run without error", f"9/9 OK")
    (ok if best_count>=3 else fail)(9, "Agents fire BUY signals in bull market",
        f"{best_count}/9 BUY on {best_pair}")

    # Section D
    decision = con.decide(vote_list)
    old_min = C.MIN_VOTES; C.MIN_VOTES = 99
    no_dec  = con.decide(vote_list); C.MIN_VOTES = old_min
    (ok if decision is not None else fail)(10, "Consensus aggregates votes",
        f"{decision.signal.value if decision else 'NONE'} conf={decision.conf:.2f}" if decision else "")
    (ok if no_dec is None else fail)(11, "Min votes guard blocks weak signals", "blocks correctly")

    # Section E — Trade lifecycle
    b = best_bars[-1]
    atr5 = T.last(T.atr(best_bars, 7)) or b.c*0.004
    v_t  = Vote("DR", Sig.BUY, 0.75, b.c-atr5*0.35, b.c+atr5*1.8, "dryrun")

    tm1 = TM(ex); t1 = tm1.open(best_pair, v_t, 80.0)
    (ok if t1 and not t1.closed and t1.entry>0 else fail)(
        12, "Trade opens correctly", f"entry={t1.entry:.4f}" if t1 else "NONE")
    (ok if t1 and t1.stop<t1.entry<t1.tp1<t1.tp2<t1.tp3 else fail)(
        13, "TP levels ordered: stop<entry<tp1<tp2<tp3", "✓")
    (ok if tm1.open(best_pair, v_t, 50.0) is None else fail)(
        14, "Double open blocked", "second open=None")
    r_hold = tm1.update(t1.entry * 1.0005) if t1 else "NONE"
    (ok if r_hold is None else fail)(15, "Holds correctly at +0.05%", "no exit")

    # TP3 direct
    tm2 = TM(ex); t2 = tm2.open(best_pair, v_t, 80.0)
    r_tp3 = tm2.update(t2.tp3 * 1.001) if t2 else "NONE"
    (ok if r_tp3 == "TP3_EXIT" else fail)(16, "TP3 exit triggers correctly", f"reason={r_tp3}")
    usdt_tp3 = tm2.close(t2.tp3*1.001, r_tp3) if t2 else 0
    c_tp3 = tm2.history[-1] if tm2.history else None
    (ok if c_tp3 and c_tp3.closed and c_tp3.pnl>0 and tm2.open_t is None else fail)(
        17, "TP3 → 100% USDT, zero tokens",
        f"pnl={c_tp3.pnl:+.4f} open=None" if c_tp3 else "FAILED")

    # Trail: after TP1 the stop/trail jumps to breakeven+fees; after TP2 it
    # stays at breakeven unless the peak-based trail is higher (ATR-dependent).
    tm3 = TM(ex); t3 = tm3.open(best_pair, v_t, 80.0)
    trail0 = t3.trail if t3 else 0
    if t3:
        tm3.update(t3.tp1 * 1.001); trail1 = t3.trail; tp1_hit = t3.tp1_hit
        tm3.update(t3.tp2 * 1.001); trail2 = t3.trail
        breakeven = t3.entry * (1 + C.FEE_RT * C.BREAKEVEN_BUFFER) if t3 else 0
    else:
        trail1 = trail2 = breakeven = 0; tp1_hit = False
    (ok if trail1 > trail0 and tp1_hit else fail)(
        18, "Trail jumps to breakeven after TP1", f"{trail0:.4f}→{trail1:.4f}")
    (ok if trail2 >= breakeven else fail)(
        19, "Trail stays at/above breakeven after TP2",
        f"{trail2:.4f} >= breakeven {breakeven:.4f}")

    # Stop loss
    tm4 = TM(ex); t4 = tm4.open(best_pair, v_t, 60.0)
    r_sl = tm4.update(t4.stop * 0.999) if t4 else "NONE"
    (ok if r_sl == "STOP_LOSS" else fail)(20, "Stop loss triggers correctly", f"reason={r_sl}")
    if t4: tm4.close(t4.stop*0.999, r_sl)
    c_sl = tm4.history[-1] if tm4.history else None
    (ok if c_sl and c_sl.closed and c_sl.pnl<0 and tm4.open_t is None else fail)(
        21, "Stop loss → 100% USDT, zero tokens",
        f"pnl={c_sl.pnl:+.4f} tokens=ZERO" if c_sl else "FAILED")

    # Time stop
    import time as _t
    tm5 = TM(ex); t5 = tm5.open(best_pair, v_t, 50.0)
    if t5: t5.t_open -= (C.MAX_HOLD_SEC + 5)
    r_ts = tm5.update(t5.entry * 1.0001) if t5 else "NONE"
    (ok if r_ts == "TIME_STOP" else fail)(22,
        f"Time stop fires at {C.MAX_HOLD_SEC//3600}h",
        f"reason={r_ts}")
    if t5: tm5.close(t5.entry, r_ts)

    # Emergency stop
    tm6 = TM(ex)
    v6  = Vote("EMRG", Sig.BUY, 0.5, b.c*0.97, b.c*1.03, "emergency")
    t6  = tm6.open(best_pair, v6, 100.0)
    crash6 = t6.entry * 0.984 if t6 else 0
    r_em   = tm6.update(crash6) if t6 else "NONE"
    (ok if r_em == "EMERGENCY_STOP" else fail)(
        23, "Emergency stop at -1.5% loss",
        f"reason={r_em} crash={crash6:.2f}" if t6 else "FAILED")
    if t6: tm6.close(crash6, r_em or "CLOSE")

    # Section F — Pair switch
    eg = GodsEngine()
    eg.pair_losses["ETH_USDT"] = 3
    sw1, rs1 = eg._need_switch("ETH_USDT")
    (ok if sw1 and "3" in rs1 else fail)(24, "Switch on 3 consecutive losses", f"reason: {rs1}")
    eg.pair_pnl["SOL_USDT"] = -C.BALANCE * 0.02
    sw2, rs2 = eg._need_switch("SOL_USDT")
    (ok if sw2 and "PnL" in rs2 else fail)(25, "Switch on PnL floor -1.5%", f"reason: {rs2}")
    eg.pair_losses["BTC_USDT"] = 1; eg.pair_pnl["BTC_USDT"] = -2.0
    sw3, _ = eg._need_switch("BTC_USDT")
    (ok if not sw3 else fail)(26, "No switch on 1 loss + small PnL", "pair held")

    # Section G — Sizing
    eg2 = GodsEngine(); eg2.active_pair="BTC_USDT"; eg2.balance=1000.0
    sz_hi=eg2._pos_size(1.00); sz_md=eg2._pos_size(0.60); sz_lo=eg2._pos_size(0.20)
    eg2.pair_losses["BTC_USDT"]=2; sz_half=eg2._pos_size(0.80)
    eg2.pair_losses["BTC_USDT"]=0; sz_full=eg2._pos_size(0.80)
    (ok if sz_hi>sz_md>sz_lo>0 else fail)(27, "Sizing scales with confidence",
        f"100%→${sz_hi:.2f} 60%→${sz_md:.2f} 20%→${sz_lo:.2f}")
    (ok if abs(sz_half-sz_full/2)<1.0 else fail)(28, "Size halved after 2 losses",
        f"normal=${sz_full:.2f} halved=${sz_half:.2f}")

    # Result
    total = PASS + FAIL
    bar   = "█"*PASS + "░"*FAIL
    print()
    print("─"*72)
    print(f"  DRY RUN: {PASS}/{total} PASSED  [{bar}]")
    if FAIL == 0:
        print("  🚀 ALL SYSTEMS GO — ENGINE READY")
    else:
        print(f"  ⚠  {FAIL} check(s) failed")
    print("─"*72)
    return FAIL == 0


def run_simulation(n_loops: int, balance: float, min_votes: int, extra_pairs=None):
    """Run paper simulation with live terminal output."""
    import importlib
    import gods_level_engine as eng
    importlib.reload(eng)
    from gods_level_engine import (
        C, Sig, Vote, T, Exchange, ALL_AGENTS, Consensus,
        PairScorer, TM, GodsEngine
    )

    if extra_pairs:
        C.PAIRS = extra_pairs
    C.BALANCE   = balance
    C.MIN_VOTES = min_votes

    logging.disable(logging.WARNING)

    ex      = Exchange()
    scorer  = PairScorer(ex)
    tm      = TM(ex)
    con     = Consensus()
    agents  = [A() for A in ALL_AGENTS]

    bal          = balance
    sess_start   = balance
    pair_losses: dict = {}
    pair_pnl:    dict = {}
    active_pair  = None
    active_score = 0
    bars_cache: dict = {}
    switches     = 0
    entries      = 0
    loop_n       = 0
    start_time   = time.time()

    def seed(pair, loop): return loop * 997 + abs(hash(pair)) % 997

    def pick(excl=None, off=0):
        nonlocal active_pair, active_score
        ab = {p: ex.sim_bars(p, C.CANDLES, seed(p, off)) for p in C.PAIRS}
        for p, b in ab.items(): bars_cache[p] = b
        r = scorer.best(ab, exclude=excl)
        active_pair  = r.pair
        active_score = r.score
        return r

    def pos_sz(conf):
        b = bal * C.MAX_POS_PCT * conf
        b = min(b, bal * C.MAX_POS_PCT)
        b = max(b, bal * 0.01)
        if pair_losses.get(active_pair, 0) >= 2: b *= 0.5
        return round(b, 2)

    def record(pair, pnl):
        pair_pnl[pair]    = pair_pnl.get(pair, 0.0) + pnl
        pair_losses[pair] = (pair_losses.get(pair, 0) + 1) if pnl < 0 else 0

    def need_switch(pair):
        l = pair_losses.get(pair, 0)
        p = pair_pnl.get(pair, 0.0)
        if l >= C.PAIR_LOSSES_MAX:   return True, f"{l} consecutive losses"
        if p/C.BALANCE <= C.PAIR_PNL_FLOOR: return True, f"pair PnL {p/C.BALANCE*100:.2f}%"
        return False, ""

    # Initial pair
    ps = pick(off=0)

    print(f"\n  Starting pair: {ps.pair} (score={ps.score})")
    print(f"  Balance: ${bal:.2f} | Min votes: {min_votes}/9 | Loops: {n_loops}")
    print(f"  Pairs: {', '.join(C.PAIRS)}")
    print()
    print("─"*72)
    print(f"  {'LOOP':>5}  {'EVENT':<10}  {'PAIR':<14}  {'DETAIL'}")
    print("─"*72)

    for loop in range(n_loops):
        loop_n = loop
        pair   = active_pair
        bars   = ex.sim_bars(pair, C.CANDLES, seed(pair, loop))
        bars_cache[pair] = bars
        price  = bars[-1].c

        # Daily stop — use realized PnL only, not in-flight balance
        realized_loss = -tm.session_pnl / sess_start if tm.session_pnl < 0 else 0.0
        if realized_loss >= C.DAILY_STOP:
            print(f"\n  🛑 DAILY STOP {realized_loss*100:.2f}% hit at loop {loop}")
            break

        # Manage open trade
        if tm.open_t and not tm.open_t.closed:
            why = tm.update(price)
            if why:
                usdt = tm.close(price, why)
                t    = tm.history[-1]
                bal  = bal - t.usdt_in + usdt
                record(pair, t.pnl)
                icon = "✅" if t.pnl > 0 else "❌"
                print(f"  {loop:>5}  {icon} CLOSED   {pair:<14}  "
                      f"pnl={t.pnl:+.4f}USDT ({t.pnl_pct:+.4f}%)  "
                      f"{why:<18}  bal=${bal:.4f}")
                sw, rs = need_switch(pair)
                if sw:
                    pair_losses[pair] = 0; pair_pnl[pair] = 0.0
                    ps2 = pick(excl=pair, off=loop+1)
                    switches += 1
                    print(f"  {loop:>5}  ⚡ SWITCH   {pair} → {active_pair:<12}  {rs}")
                    continue
            continue

        # Re-score pairs every 25 loops
        if loop > 0 and loop % 25 == 0:
            ps2 = scorer.best({p: ex.sim_bars(p, C.CANDLES, seed(p, loop)) for p in C.PAIRS})
            if ps2.pair != active_pair and ps2.score > active_score + 10:
                old = active_pair; active_pair = ps2.pair; active_score = ps2.score
                print(f"  {loop:>5}  🔄 UPGRADE  {old} → {active_pair:<12}  score→{ps2.score}")
                continue

        # Run agents
        votes    = [ag.run(bars) for ag in agents]
        buy_v    = sum(1 for v in votes if v.signal in (Sig.BUY, Sig.STRONG_BUY))
        decision = con.decide(votes)
        if not decision: continue

        sz   = pos_sz(decision.conf)
        if sz < 5: continue
        risk = price - decision.stop
        rew  = decision.tp - price
        if risk <= 0 or rew/risk < 1.0 or rew/price*100 < C.FEE_RT*100: continue

        t = tm.open(pair, decision, sz)
        if t:
            entries += 1
            print(f"  {loop:>5}  🎯 ENTERED  {pair:<14}  "
                  f"${sz:.2f}  {buy_v}/9 votes  conf={decision.conf:.2f}  "
                  f"@{price:.4f}  stop={decision.stop:.4f}  tp={decision.tp:.4f}")

        # Status every 100 loops
        if loop % 100 == 0 and loop > 0:
            elapsed = (time.time() - start_time) / 60
            print(f"\n  {'─'*68}")
            print(f"  CHECKPOINT L{loop} | Pair:{active_pair:<12} | "
                  f"Bal:${bal:.4f} | PnL:{tm.session_pnl:+.4f} | "
                  f"WR:{tm.win_rate*100:.0f}% | Trades:{len(tm.history)} | "
                  f"Switches:{switches} | {elapsed:.1f}min")
            print(f"  {'─'*68}\n")

    # Force close any open trade
    if tm.open_t and not tm.open_t.closed:
        bars  = bars_cache.get(active_pair, [])
        price = bars[-1].c if bars else 0.0
        if price > 0:
            usdt = tm.close(price, "SIM_END")
            t    = tm.history[-1]
            bal  = bal - t.usdt_in + usdt

    # Final report
    trades = tm.history
    pnl    = tm.session_pnl
    wr     = tm.win_rate * 100
    elapsed= (time.time() - start_time) / 60

    print()
    print("═"*72)
    print("  SIMULATION COMPLETE")
    print("═"*72)
    print(f"  Loops run:       {n_loops}")
    print(f"  Time elapsed:    {elapsed:.1f} min")
    print(f"  Entries:         {entries}")
    print(f"  Trades closed:   {len(trades)}")
    print(f"  Win rate:        {wr:.1f}%")
    print(f"  Pair switches:   {switches}")
    print(f"  Net PnL:         {pnl:+.4f} USDT")
    print(f"  Start balance:   ${balance:.2f}")
    print(f"  End balance:     ${bal:.4f} USDT")
    print(f"  ROI:             {(bal-balance)/balance*100:+.4f}%")

    if trades:
        wins   = [t for t in trades if t.pnl>0]
        losses = [t for t in trades if t.pnl<=0]
        aw = sum(t.pnl for t in wins)/len(wins)   if wins   else 0
        al = sum(t.pnl for t in losses)/len(losses) if losses else 0
        pf = abs(aw/al) if al!=0 else 0
        print(f"  Avg win:         ${aw:+.4f}")
        print(f"  Avg loss:        ${al:+.4f}")
        print(f"  Profit factor:   {pf:.2f}")
        pairs_used = sorted(set(t.pair for t in trades))
        print(f"  Pairs traded:    {', '.join(pairs_used)}")
        print()
        print("  PER-PAIR BREAKDOWN:")
        by_pair = {}
        for t in trades: by_pair.setdefault(t.pair, []).append(t)
        for p, pts in sorted(by_pair.items()):
            w  = sum(1 for t in pts if t.pnl>0)
            pp = sum(t.pnl for t in pts)
            print(f"    {p:<14} {len(pts):3d} trades | "
                  f"wr={w/len(pts)*100:.0f}% | pnl={pp:+.4f} USDT")

    # Exit types
    if trades:
        print()
        print("  EXIT TYPE BREAKDOWN:")
        exit_types = {}
        for t in trades: exit_types[t.why] = exit_types.get(t.why, 0)+1
        for why, cnt in sorted(exit_types.items(), key=lambda x:-x[1]):
            print(f"    {why:<22} {cnt:3d}×")

    print()
    print("  ✅ ALL FUNDS RETURNED TO USDT — ZERO TOKENS HELD")
    print("═"*72)

    # Save log
    log = {
        "mode": "paper_simulation",
        "loops": n_loops,
        "start_balance": balance,
        "end_balance": bal,
        "pnl": pnl,
        "roi_pct": (bal-balance)/balance*100,
        "trades": len(trades),
        "win_rate": wr,
        "switches": switches,
        "history": [
            {"pair": t.pair, "entry": t.entry, "exit": t.exit_px,
             "pnl": t.pnl, "pnl_pct": t.pnl_pct, "why": t.why}
            for t in trades
        ]
    }
    fname = f"sim_results_{int(time.time())}.json"
    fpath = os.path.join(os.path.dirname(__file__), fname)
    with open(fpath, "w") as f: json.dump(log, f, indent=2)
    print(f"\n  📝 Results saved: {fname}")


def run_paper_real(interval: str, balance: float, min_votes: int, extra_pairs=None):
    """Stage 1: fetch real candles from the exchange, run agents, paper-fill orders."""
    import importlib
    import gods_level_engine as eng
    importlib.reload(eng)
    from gods_level_engine import C, GodsEngine

    if extra_pairs: C.PAIRS = extra_pairs
    C.LIVE_MODE     = False           # stays False — orders are paper-filled
    C.USE_REAL_DATA = True
    C.INTERVAL      = interval
    C.BALANCE       = balance
    C.MIN_VOTES     = min_votes

    print("\n" + "="*72)
    print(f"  STAGE 1 — PAPER ORDERS · REAL {interval.upper()} CANDLES from {C.EXCHANGE.upper()}")
    print(f"  Balance=${balance:.2f} USDT | Pairs={len(C.PAIRS)} | MinVotes={min_votes}/9")
    print(f"  Ctrl-C to stop. No real money at risk.")
    print("="*72 + "\n")

    engine = GodsEngine()
    try:
        engine.start()
    except KeyboardInterrupt:
        engine.shutdown()


def _aggregate_to_weekly(daily_bars):
    """Roll a list of 1d Bar objects into 1w bars (Mon-anchored buckets)."""
    from gods_level_engine import Bar
    out, cur, bk = [], [], None
    for b in daily_bars:
        k = b.ts // (7 * 86400)
        if bk is None: bk = k
        if k != bk:
            if cur:
                out.append(Bar(cur[0].ts, cur[0].o,
                               max(x.h for x in cur), min(x.l for x in cur),
                               cur[-1].c, sum(x.v for x in cur)))
            cur = [b]; bk = k
        else:
            cur.append(b)
    if cur:
        out.append(Bar(cur[0].ts, cur[0].o,
                       max(x.h for x in cur), min(x.l for x in cur),
                       cur[-1].c, sum(x.v for x in cur)))
    return out


def run_ma_strategy(ma_period: int, interval: str, balance: float,
                    paper_real: bool, pair: str = "BTC_USDT",
                    weekly_ma_period: int = 0, live: bool = False,
                    max_drawdown_pct: float = 5.0):
    """Trend-follow loop using SimpleMAStrategy.

    Three execution modes, gated by the `paper_real` and `live` flags:
      * (default)             synthetic candles, paper orders
      * paper_real=True       real exchange candles, paper orders (Stage 1)
      * live=True             real candles AND real orders (Stage 2 — requires
                              LIVE_MODE, env-var API keys, CONFIRM prompt,
                              and a max-drawdown circuit breaker)

    weekly_ma_period > 0 enables the higher-timeframe weekly filter.
    Backtested compound (6 regimes 2018-2026) lifts +552% → +3,427% with W10.

    max_drawdown_pct: if live equity falls this far below the session peak,
    force a flat exit and stop. Default 15% — tighten for smaller capital.
    """
    import importlib, time
    import gods_level_engine as eng
    importlib.reload(eng)
    from gods_level_engine import C, Exchange, SimpleMAStrategy

    # ─────────────── LIVE-MODE GATE ───────────────
    if live:
        if not C.LIVE_MODE:
            print("\n❌ --live passed but LIVE_MODE=False in class C.")
            print("   Edit gods_level_engine.py: class C:  LIVE_MODE = True")
            return
        if not C.GIO_KEY or not C.GIO_SEC:
            print("\n❌ Live trading needs API keys in env vars.")
            print("   export GATEIO_API_KEY=...")
            print("   export GATEIO_SECRET=...")
            return
        print("\n" + "!"*72)
        print("  ⚠  LIVE TRADING MODE — real money will be used.")
        print(f"  Pair: {pair}   Capital: ${balance:.2f} USDT")
        print(f"  Max drawdown circuit breaker: {max_drawdown_pct:.1f}% below session peak")
        print(f"  Fees: {C.FEE_RT*100:.2f}% round-trip   Strategy: MA{ma_period}"
              f"{' + W' + str(weekly_ma_period) if weekly_ma_period else ''}")
        print("!"*72)
        confirm = input("\n  Type CONFIRM LIVE TRADING to proceed: ").strip()
        if confirm != "CONFIRM LIVE TRADING":
            print("  Cancelled — no orders placed.")
            return
        print("  Confirmed. Strategy starting in 3s… Ctrl-C to abort.")
        time.sleep(3)

    # ─────────────── MODE SETUP ───────────────
    C.USE_REAL_DATA = paper_real or live
    C.INTERVAL      = interval
    C.BALANCE       = balance
    # C.LIVE_MODE is only True if the user set it explicitly in class C
    # AND passed --live. Otherwise we force paper-fill behavior.
    if not live:
        C.LIVE_MODE = False

    ex    = Exchange()
    strat = SimpleMAStrategy(ex, pair, ma_period=ma_period, balance=balance,
                             weekly_ma_period=weekly_ma_period)

    # One-shot Telegram heartbeat so the user knows the bot came up
    try:
        from telegram_alerts import notify_startup
        _ma_name = f"MA{ma_period}" + (f"+W{weekly_ma_period}" if weekly_ma_period else "")
        notify_startup(pair, balance, _ma_name)
    except Exception:
        pass

    print("\n" + "="*72)
    if live:
        mode_tag = "🔴 LIVE · REAL ORDERS"
    elif paper_real:
        mode_tag = "🟡 PAPER · REAL CANDLES"
    else:
        mode_tag = "🟡 PAPER · SYNTHETIC CANDLES"
    suffix = f" + W{weekly_ma_period} weekly filter" if weekly_ma_period else ""
    print(f"  MA{ma_period}{suffix} TREND-FOLLOW · {mode_tag} · {interval} bars")
    print(f"  Pair={pair}  Balance=${balance:.2f}")
    if weekly_ma_period:
        base = pair.split('_')[0]
        print(f"  Rule: hold 100% {base} when daily close > SMA{ma_period}")
        print(f"        AND weekly close > weekly SMA{weekly_ma_period}, else USDT")
    else:
        base = pair.split('_')[0]
        print(f"  Rule: hold 100% {base} when close > SMA{ma_period}, else USDT")
    risk_tag = "LIVE money at risk." if live else "No real money at risk."
    print(f"  Ctrl-C to stop. {risk_tag}")
    print("="*72 + "\n")

    # Synthetic mode needs ONE continuous random walk, not a fresh seed
    # per loop — otherwise the MA strategy whipsaws on disconnected series.
    use_real_candles = paper_real or live
    sim_series = None
    sim_idx    = 0
    if not use_real_candles:
        warmup = max(ma_period + 50, weekly_ma_period * 7 + 50)
        sim_series = ex.sim_bars(pair, max(2000, warmup * 2),
                                 abs(hash(pair)) % 99991)
        sim_idx    = warmup

    # Session-peak equity used by the max-drawdown circuit breaker
    peak_equity    = balance
    dd_warned_soft = False   # one-shot Telegram warning at half threshold
    last_bar_ts    = 0       # Patch 5: bar-close gate — track the last bar
                             # we've already evaluated, skip duplicate work
                             # until a new closed bar arrives.

    try:
        loop = 0
        while True:
            loop += 1
            if use_real_candles:
                need = max(ma_period + 50, weekly_ma_period * 7 + 50)
                bars = ex.fetch_bars(pair, need)
                if not bars:
                    logging.warning(f"fetch_bars empty for {pair}, retrying in {C.LOOP_SLEEP}s")
                    time.sleep(C.LOOP_SLEEP); continue
            else:
                if sim_idx >= len(sim_series):
                    print("\n  ▶ synthetic series exhausted")
                    break
                bars   = sim_series[:sim_idx + 1]
                sim_idx += 1

            price = bars[-1].c
            ts    = bars[-1].ts

            # Patch 5: bar-close gate. Signal evaluation runs only when a
            # new closed bar arrives. DD breaker + status print still run
            # every loop (they read mark-to-market, not signals).
            new_bar = (ts != last_bar_ts)
            if new_bar:
                last_bar_ts = ts
                weekly_bars = _aggregate_to_weekly(bars) if weekly_ma_period > 0 else None
                side  = strat.step(bars, weekly_bars=weekly_bars)
                if side:
                    strat.execute(side, price, ts)

            # Max-drawdown circuit breaker — active in live AND paper-real.
            # Paper mode still honors the breaker so forward-test behavior
            # matches live, including the notification + flatten path.
            eq = strat.mark_to_market(price)
            if eq > peak_equity: peak_equity = eq
            if peak_equity > 0:
                dd_pct = (peak_equity - eq) / peak_equity * 100
                # Soft warning at half the hard threshold — gives the user
                # time to react before the automated stop
                soft_threshold = max_drawdown_pct / 2
                if dd_pct >= soft_threshold and not dd_warned_soft:
                    dd_warned_soft = True
                    try:
                        from telegram_alerts import notify_drawdown
                        notify_drawdown(pair, dd_pct, eq, peak_equity)
                    except Exception:
                        pass
                if dd_pct >= max_drawdown_pct:
                    logging.critical(
                        f"🛑 CIRCUIT BREAKER — equity drawdown {dd_pct:.2f}% "
                        f"≥ {max_drawdown_pct:.1f}% from peak ${peak_equity:.2f}. "
                        f"Flattening and stopping.")
                    try:
                        from telegram_alerts import notify_circuit_break
                        notify_circuit_break(pair, dd_pct, eq)
                    except Exception:
                        pass
                    if strat.in_position:
                        strat.execute("SELL", price, ts)
                    break

            if loop % 20 == 0:
                roi = (eq - balance) / balance * 100
                pos = "LONG" if strat.in_position else "USDT"
                dd  = (peak_equity - eq) / peak_equity * 100 if peak_equity > 0 else 0
                print(f"  loop {loop}  pos={pos}  px={price:.2f}  "
                      f"equity=${eq:.2f}  ROI={roi:+.2f}%  DD={dd:.2f}%  "
                      f"trades={len(strat.history)}")

            time.sleep(C.LOOP_SLEEP if use_real_candles else 0.0)
    except KeyboardInterrupt:
        # Final close + report
        if strat.in_position:
            bars = (ex.fetch_bars(pair, max(ma_period + 50, 200)) if use_real_candles
                    else ex.sim_bars(pair, 300, 99))
            if bars: strat.execute("SELL", bars[-1].c, bars[-1].ts)
        print("\n" + "="*72)
        print("  MA STRATEGY — STOPPED")
        print("="*72)
        print(f"  Trades: {len(strat.history)}  PnL: {strat.session_pnl:+.4f}  "
              f"Final: ${strat.balance:.2f}")
        print("="*72)


def run_vote_strategy(interval: str, balance: float,
                      paper_real: bool, pair: str = "BTC_USDT",
                      live: bool = False,
                      max_drawdown_pct: float = 5.0):
    """Vote ≥2-of-3 ensemble loop (MA20+W5 + Donchian-20 + BTC-gate).

    Drop-in parallel to run_ma_strategy, but uses VoteEnsembleStrategy.
    Backtested portfolio Sharpe 2.41, rolling 4/5 on 9-pair 7-year set —
    the current ship candidate after max_edge validation.
    """
    from gods_level_engine import C, Exchange, VoteEnsembleStrategy

    if live:
        if not C.LIVE_MODE:
            print("\n  ⚠  LIVE flag passed but C.LIVE_MODE=False. "
                  "Set it manually in gods_level_engine.py first.")
            return
        if not (C.GIO_KEY and C.GIO_SEC):
            print("\n  ⚠  GATEIO_API_KEY / GATEIO_SECRET env vars required for --live.")
            return
        print("\n" + "!"*72)
        print("  ⚠  LIVE TRADING MODE — real money will be used.")
        print(f"  Pair: {pair}   Capital: ${balance:.2f} USDT")
        print(f"  Strategy: Vote ≥2 of 3  Max DD: {max_drawdown_pct:.1f}%")
        print("!"*72)
        confirm = input("\n  Type CONFIRM LIVE TRADING to proceed: ").strip()
        if confirm != "CONFIRM LIVE TRADING":
            print("  Cancelled — no orders placed.")
            return
        print("  Confirmed. Strategy starting in 3s… Ctrl-C to abort.")
        time.sleep(3)

    C.USE_REAL_DATA = paper_real or live
    C.INTERVAL      = interval
    C.BALANCE       = balance
    if not live:
        C.LIVE_MODE = False

    ex    = Exchange()
    strat = VoteEnsembleStrategy(ex, pair, balance=balance)

    try:
        from telegram_alerts import notify_startup
        notify_startup(pair, balance, "Vote≥2of3 (MA20+W5·Don20·BTC)")
    except Exception:
        pass

    print("\n" + "="*72)
    mode_tag = ("🔴 LIVE · REAL ORDERS"     if live       else
                "🟡 PAPER · REAL CANDLES"   if paper_real else
                "🟡 PAPER · SYNTHETIC")
    print(f"  VOTE ENSEMBLE · {mode_tag} · {interval} bars")
    print(f"  Pair={pair}  Balance=${balance:.2f}")
    print(f"  Rule: hold 100% {pair.split('_')[0]} when ≥2 of {{MA20+W5, Donchian-20, BTC-gate}} agree")
    print(f"  Circuit breaker: {max_drawdown_pct:.1f}% drawdown from session peak → flatten & stop")
    risk_tag = "LIVE money at risk." if live else "No real money at risk."
    print(f"  Ctrl-C to stop. {risk_tag}")
    print("="*72 + "\n")

    use_real = paper_real or live
    if not use_real:
        # Synthetic walk for local sim
        warmup     = 220
        sim_series = ex.sim_bars(pair, 2000, abs(hash(pair)) % 99991)
        sim_idx    = warmup
    else:
        sim_series = None
        sim_idx    = 0

    peak_equity    = balance
    dd_warned_soft = False
    last_bar_ts    = 0    # Patch 5: bar-close gate

    try:
        loop = 0
        while True:
            loop += 1
            if use_real:
                bars = ex.fetch_bars(pair, 250)
                if not bars:
                    logging.warning(f"fetch_bars empty for {pair}, retrying in {C.LOOP_SLEEP}s")
                    time.sleep(C.LOOP_SLEEP); continue
            else:
                if sim_idx >= len(sim_series):
                    print("\n  ▶ synthetic series exhausted"); break
                bars = sim_series[:sim_idx + 1]; sim_idx += 1

            price = bars[-1].c
            ts    = bars[-1].ts

            # Patch 5: only evaluate vote on a new closed bar.
            new_bar = (ts != last_bar_ts)
            if new_bar:
                last_bar_ts = ts
                side = strat.step(bars)
                if side:
                    strat.execute(side, price, ts)

            eq = strat.mark_to_market(price)
            if eq > peak_equity: peak_equity = eq
            if peak_equity > 0:
                dd_pct = (peak_equity - eq) / peak_equity * 100
                soft_threshold = max_drawdown_pct / 2
                if dd_pct >= soft_threshold and not dd_warned_soft:
                    dd_warned_soft = True
                    try:
                        from telegram_alerts import notify_drawdown
                        notify_drawdown(pair, dd_pct, eq, peak_equity)
                    except Exception: pass
                if dd_pct >= max_drawdown_pct:
                    logging.critical(
                        f"🛑 CIRCUIT BREAKER — dd {dd_pct:.2f}% ≥ {max_drawdown_pct:.1f}%. Flattening.")
                    try:
                        from telegram_alerts import notify_circuit_break
                        notify_circuit_break(pair, dd_pct, eq)
                    except Exception: pass
                    if strat.in_position:
                        strat.execute("SELL", price, ts)
                    break

            if loop % 20 == 0:
                roi = (eq - balance) / balance * 100
                pos = "LONG" if strat.in_position else "USDT"
                dd  = (peak_equity - eq) / peak_equity * 100 if peak_equity > 0 else 0
                print(f"  loop {loop}  pos={pos}  px={price:.2f}  "
                      f"equity=${eq:.2f}  ROI={roi:+.2f}%  DD={dd:.2f}%  "
                      f"trades={len(strat.history)}")

            time.sleep(C.LOOP_SLEEP if use_real else 0.0)
    except KeyboardInterrupt:
        if strat.in_position:
            bars = (ex.fetch_bars(pair, 200) if use_real
                    else ex.sim_bars(pair, 300, 99))
            if bars: strat.execute("SELL", bars[-1].c, bars[-1].ts)
        print("\n" + "="*72)
        print("  VOTE ENSEMBLE — STOPPED")
        print(f"  Trades: {len(strat.history)}  PnL: {strat.session_pnl:+.4f}  "
              f"Final: ${strat.balance:.2f}")
        print("="*72)


def run_ma_csv_replay(csv_path: str, ma_period: int, weekly_ma_period: int,
                      balance: float, pair: str = "BTC_USDT"):
    """Offline forward-test: feed a real 1m BTC CSV through SimpleMAStrategy
    one daily bar at a time. Uses the same engine code path that live would.
    """
    import csv as csvmod, importlib, os
    import gods_level_engine as eng
    importlib.reload(eng)
    from gods_level_engine import C, Bar, Exchange, SimpleMAStrategy
    from datetime import datetime, timezone

    C.LIVE_MODE     = False
    C.USE_REAL_DATA = False
    C.BALANCE       = balance

    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}"); return

    # Load 1m → aggregate to 1d
    bars_1m = []
    with open(csv_path) as f:
        r = csvmod.DictReader(f)
        for row in r:
            bars_1m.append(Bar(int(row["timestamp"]),
                float(row["open"]), float(row["high"]), float(row["low"]),
                float(row["close"]), float(row["volume"])))

    def agg(bars, minutes):
        if minutes == 1: return bars
        out, cur, bk = [], [], None
        for b in bars:
            k = b.ts // (minutes * 60)
            if bk is None: bk = k
            if k != bk:
                if cur:
                    out.append(Bar(cur[0].ts, cur[0].o,
                                   max(x.h for x in cur), min(x.l for x in cur),
                                   cur[-1].c, sum(x.v for x in cur)))
                cur = [b]; bk = k
            else:
                cur.append(b)
        if cur:
            out.append(Bar(cur[0].ts, cur[0].o,
                           max(x.h for x in cur), min(x.l for x in cur),
                           cur[-1].c, sum(x.v for x in cur)))
        return out

    bars_1d = agg(bars_1m, 1440)
    bars_1w = agg(bars_1m, 10080)

    ex    = Exchange()
    strat = SimpleMAStrategy(ex, pair, ma_period=ma_period, balance=balance,
                             weekly_ma_period=weekly_ma_period)

    t0 = datetime.fromtimestamp(bars_1d[0].ts,  tz=timezone.utc)
    t1 = datetime.fromtimestamp(bars_1d[-1].ts, tz=timezone.utc)
    span = (bars_1d[-1].ts - bars_1d[0].ts) / 86400
    suffix = f" + W{weekly_ma_period}" if weekly_ma_period else ""
    print("\n" + "="*72)
    print(f"  CSV REPLAY FORWARD-TEST · MA{ma_period}{suffix} · {os.path.basename(csv_path)}")
    print(f"  Range: {t0.date()} → {t1.date()} ({span:.0f} days, {len(bars_1d)} daily bars)")
    print(f"  Balance=${balance:.2f}  Price: ${bars_1d[0].c:,.0f} → ${bars_1d[-1].c:,.0f}")
    print("="*72 + "\n")

    warmup = max(ma_period + 1, weekly_ma_period * 7 + 1) if weekly_ma_period else ma_period + 1
    events = 0
    for i in range(warmup, len(bars_1d)):
        daily_window = bars_1d[:i + 1]
        # Weekly bars whose ts <= current daily bar's ts
        cur_ts = bars_1d[i].ts
        w_window = [b for b in bars_1w if b.ts <= cur_ts] if weekly_ma_period else None

        side = strat.step(daily_window, weekly_bars=w_window)
        if side:
            strat.execute(side, bars_1d[i].c, bars_1d[i].ts)
            events += 1
            dt = datetime.fromtimestamp(bars_1d[i].ts, tz=timezone.utc).date()
            eq = strat.mark_to_market(bars_1d[i].c)
            icon = "📈" if side == "BUY" else "📉"
            print(f"  {dt}  {icon} {side:<4} @${bars_1d[i].c:>9,.0f}  "
                  f"equity=${eq:>8,.2f}  trades={len(strat.history)}")

    # Close dangling
    if strat.in_position:
        strat.execute("SELL", bars_1d[-1].c, bars_1d[-1].ts)

    equity_final = strat.balance
    roi = (equity_final - balance) / balance * 100
    wins = sum(1 for t in strat.history if t.pnl > 0)
    wr   = wins / len(strat.history) * 100 if strat.history else 0

    print("\n" + "="*72)
    print("  CSV REPLAY COMPLETE")
    print("="*72)
    print(f"  Starting balance : ${balance:,.2f}")
    print(f"  Ending balance   : ${equity_final:,.2f}")
    print(f"  ROI              : {roi:+.2f}%")
    print(f"  Trades           : {len(strat.history)}  (WR {wr:.0f}%)")
    print(f"  Net PnL          : {strat.session_pnl:+.4f} USDT")
    print("="*72)


def run_live():
    """Start 24/7 live trading engine."""
    import importlib
    import gods_level_engine as eng
    importlib.reload(eng)
    from gods_level_engine import C, GodsEngine

    if not C.LIVE_MODE:
        print("\n❌ LIVE_MODE is False in gods_level_engine.py")
        print("   Edit the file: set LIVE_MODE = True in class C")
        return

    if not C.GIO_KEY and not C.BIN_KEY:
        print("\n❌ No API keys found.")
        print("   Run: export GATEIO_API_KEY=your_key")
        print("        export GATEIO_SECRET=your_secret")
        return

    print("\n" + "!"*72)
    print("  ⚠  LIVE TRADING MODE")
    print("  Real money will be used. Losses are permanent.")
    print("!"*72)
    confirm = input("\n  Type CONFIRM LIVE TRADING to proceed: ").strip()
    if confirm != "CONFIRM LIVE TRADING":
        print("  Cancelled.")
        return

    engine = GodsEngine()
    try:
        engine.start()
    except KeyboardInterrupt:
        engine.shutdown()


# ── MAIN ──
if __name__ == "__main__":
    print_banner()
    args = parse_args()

    # Configure logging so MA strategy trade events (📈 MA-BUY, ✅ MA-SELL)
    # reach stdout. GodsEngine configures logging in its __init__, but the
    # MA path skips GodsEngine entirely — without this, logging.info(...)
    # calls inside SimpleMAStrategy go to a silent root logger.
    import logging as _log
    if not _log.getLogger().handlers:
        _log.basicConfig(
            level  = _log.INFO,
            format = "%(asctime)s | %(levelname)-7s | %(message)s",
            handlers=[_log.StreamHandler()],
        )

    # Vote ensemble (MA20+W5 + Donchian + BTC-gate) short-circuits first
    if args.strategy == "vote":
        pair = args.pairs[0] if args.pairs else "BTC_USDT"
        vote_interval = args.interval if args.interval != "1m" else "1d"
        run_vote_strategy(
            interval    = vote_interval,
            balance     = args.balance,
            paper_real  = args.paper_real,
            live        = args.live,
            pair        = pair,
        )

    # MA strategy short-circuits the legacy dispatch
    elif args.strategy.startswith("ma"):
        # Parse ma50, ma100, ma50w10, ma50w20, ma20w5
        ma_map = {"ma50": (50, 0), "ma100": (100, 0),
                  "ma50w10": (50, 10), "ma50w20": (50, 20),
                  "ma20w5": (20, 5)}
        ma_period, weekly_ma = ma_map[args.strategy]
        pair = args.pairs[0] if args.pairs else "BTC_USDT"

        # --csv-replay wins over other modes if supplied
        if args.csv_replay:
            run_ma_csv_replay(
                csv_path         = args.csv_replay,
                ma_period        = ma_period,
                weekly_ma_period = weekly_ma,
                balance          = args.balance,
                pair             = pair,
            )
        else:
            # Default to 1d candles for MA unless user overrode --interval
            ma_interval = args.interval if args.interval != "1m" else "1d"
            run_ma_strategy(
                ma_period        = ma_period,
                weekly_ma_period = weekly_ma,
                interval         = ma_interval,
                balance          = args.balance,
                paper_real       = args.paper_real,
                live             = args.live,
                pair             = pair,
            )

    elif args.dryrun:
        ok = run_dryrun()
        sys.exit(0 if ok else 1)

    elif args.live:
        run_live()

    elif args.paper_real:
        run_paper_real(
            interval    = args.interval,
            balance     = args.balance,
            min_votes   = args.votes,
            extra_pairs = args.pairs,
        )

    else:
        print(f"  Mode:    🟡 PAPER SIMULATION (synthetic, legacy 9-agent engine)")
        print(f"  Loops:   {args.loops}")
        print(f"  Balance: ${args.balance:.2f} USDT")
        print(f"  Votes:   {args.votes}/9 minimum to enter")
        print(f"  Tip:     '--strategy ma50' is the recommended profitable strategy")
        print()
        run_simulation(
            n_loops   = args.loops,
            balance   = args.balance,
            min_votes = args.votes,
            extra_pairs = args.pairs
        )
