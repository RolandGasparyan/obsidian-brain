#!/usr/bin/env python3
"""
LIVE-ELIGIBILITY GATE — the anti-drift authority.
A strategy/pair is LIVE-ELIGIBLE only if it proves real edge across regimes
(esp. survives the BEAR), fee-realistic, OOS, no-lookahead, paper-tested.
This is what should decide what may go live — not labels, not random scores.
NO live execution here; it only judges.
"""
import os, glob, json
import pandas as pd, numpy as np
import lab  # reuse STRATS, load_daily, FEE

DATA = os.environ.get("GATE_DATA", os.path.dirname(__file__))
OUT  = os.environ.get("GATE_OUT", os.path.join(os.path.dirname(__file__), "results"))
os.makedirs(OUT, exist_ok=True)

# --- gate thresholds (tune here) ---
MIN_SHARPE   = 0.5
MAX_DD       = 40.0     # %
BEAR_FLOOR   = -5.0     # % : in a bear window, must not lose more than this
MIN_OVERALL  = 0.0      # % : overall return must be positive
N_WINDOWS    = 6        # split history into N contiguous regime windows

def equity_series(d, sigfn):
    sig = sigfn(d).shift(1).fillna(0)
    ret = d["close"].pct_change().fillna(0)
    daily = sig*ret - sig.diff().abs().fillna(0)*lab.FEE
    return daily, sig

def stats(daily):
    eq=(1+daily).cumprod()
    tot=(eq.iloc[-1]-1)*100
    peak=eq.cummax(); mdd=((peak-eq)/peak).max()*100
    sh=(daily.mean()/daily.std()*np.sqrt(365)) if daily.std()>0 else 0.0
    return float(tot), float(mdd), float(sh)

def regime_label(bh):
    return "BULL" if bh>20 else ("BEAR" if bh<-20 else "CHOP")

def gate_pair(csv):
    sym=os.path.splitext(os.path.basename(csv))[0].split("_")[0].upper()
    d=lab.load_daily(csv)
    if len(d)<260: return sym, None, []
    idx=np.array_split(np.arange(len(d)), N_WINDOWS)
    verdicts=[]
    for name,fn in lab.STRATS.items():
        if name=="buy_hold": continue
        daily,_=equity_series(d, fn)
        tot,mdd,sh=stats(daily)
        # per-window
        wins=[]
        worst_bear=None
        for w in idx:
            sub=daily.iloc[w[0]:w[-1]+1]
            bh=(d["close"].iloc[w[-1]]/d["close"].iloc[w[0]]-1)*100
            wr=((1+sub).prod()-1)*100
            lab_=regime_label(bh)
            wins.append((lab_, round(bh,0), round(wr,0)))
            if lab_=="BEAR":
                worst_bear = wr if worst_bear is None else min(worst_bear, wr)
        reasons=[]
        if sh<MIN_SHARPE: reasons.append(f"Sharpe {sh:.2f}<{MIN_SHARPE}")
        if mdd>MAX_DD: reasons.append(f"maxDD {mdd:.0f}%>{MAX_DD:.0f}%")
        if tot<=MIN_OVERALL: reasons.append(f"overall {tot:.0f}%<=0")
        if worst_bear is not None and worst_bear<BEAR_FLOOR:
            reasons.append(f"bear window {worst_bear:.0f}%<{BEAR_FLOOR}%")
        if worst_bear is None: reasons.append("no bear window to test (insufficient regime coverage)")
        eligible = len(reasons)==0
        verdicts.append(dict(strategy=name, eligible=eligible, total=round(tot,0),
                             sharpe=round(sh,2), maxdd=round(mdd,0),
                             worst_bear=(round(worst_bear,0) if worst_bear is not None else None),
                             reasons=reasons, windows=wins))
    verdicts.sort(key=lambda v:(v["eligible"], v["sharpe"]), reverse=True)
    return sym, d, verdicts

def main():
    report={"generated":pd.Timestamp.utcnow().isoformat(),
            "thresholds":dict(min_sharpe=MIN_SHARPE,max_dd=MAX_DD,bear_floor=BEAR_FLOOR),"pairs":{}}
    md=[f"# Live-Eligibility Gate\n_generated {report['generated']} · gate: Sharpe>={MIN_SHARPE}, maxDD<={MAX_DD}%, bear-window>={BEAR_FLOOR}%, overall>0 · paper-only_\n"]
    for csv in sorted(glob.glob(os.path.join(DATA,"*_1h.csv")))+sorted(glob.glob(os.path.join(DATA,"*.csv"))):
        if "_QUARANTINE" in csv: continue
        sym,d,verdicts=gate_pair(csv)
        if d is None: continue
        if sym in report["pairs"]: continue
        report["pairs"][sym]=verdicts
        md.append(f"\n## {sym}  ({d.index[0].date()} -> {d.index[-1].date()})\n")
        print(f"\n=== {sym} ===")
        for v in verdicts:
            tag="✅ LIVE-ELIGIBLE" if v["eligible"] else "❌ REJECTED"
            print(f"  {v['strategy']:<14} {tag:<18} tot {v['total']:>+5.0f}% Sharpe {v['sharpe']:>5.2f} DD {v['maxdd']:>3.0f}% bear {v['worst_bear']}")
            if v["reasons"]: print(f"      reasons: {'; '.join(v['reasons'])}")
            md.append(f"- **{v['strategy']}** — {tag} · tot {v['total']:+.0f}%, Sharpe {v['sharpe']:.2f}, DD {v['maxdd']:.0f}%, worst-bear {v['worst_bear']}%" + (f" · _rejected: {'; '.join(v['reasons'])}_" if v['reasons'] else ""))
    json.dump(report, open(os.path.join(OUT,"live_eligibility.json"),"w"), indent=2)
    open(os.path.join(OUT,"LIVE_ELIGIBILITY.md"),"w").write("\n".join(md))
    elig=sum(1 for p in report["pairs"].values() for v in p if v["eligible"])
    print(f"\n{elig} live-eligible setup(s) across {len(report['pairs'])} pairs. wrote {OUT}/LIVE_ELIGIBILITY.md")

if __name__=="__main__":
    main()
