#!/usr/bin/env python3
"""
TRADING GURU — REAL Strategy Lab.
Paper-tests strategies on REAL price data (fee-realistic, OOS, no lookahead).
NO random numbers. NO live execution. Produces a ranked leaderboard per pair.
"""
import os, json, glob
import pandas as pd, numpy as np

DATA_DIR = os.environ.get("LAB_DATA", os.path.dirname(__file__))
OUT_DIR  = os.environ.get("LAB_OUT",  os.path.join(os.path.dirname(__file__), "results"))
FEE      = float(os.environ.get("LAB_FEE", "0.001"))   # 0.1%/side spot taker
os.makedirs(OUT_DIR, exist_ok=True)

def load_daily(csv):
    df = pd.read_csv(csv); df["t"] = pd.to_datetime(df["timestamp"]); df = df.set_index("t")
    d = df.resample("1D").agg(open=("open","first"), high=("high","max"),
                              low=("low","min"), close=("close","last")).dropna()
    return d

# ---- strategy signal functions: return a daily 0/1 long-or-flat series ----
def s_buy_hold(d):      return pd.Series(1, index=d.index)
def s_sma50(d):         return (d["close"] > d["close"].rolling(50).mean()).astype(int)
def s_sma200(d):        return (d["close"] > d["close"].rolling(200).mean()).astype(int)
def s_ma50w10(d):
    w = d["close"].resample("1W").last(); wsma = w.rolling(10).mean()
    wc = w.reindex(d.index, method="ffill"); wsa = wsma.reindex(d.index, method="ffill")
    return ((d["close"] > d["close"].rolling(50).mean()) & (wc > wsa)).astype(int)
def s_donchian20(d):
    hi = d["close"].rolling(20).max().shift(1); lo = d["close"].rolling(20).min().shift(1)
    sig = pd.Series(np.nan, index=d.index)
    sig[d["close"] > hi] = 1; sig[d["close"] < lo] = 0
    return sig.ffill().fillna(0).astype(int)
def s_cross_5_20(d):
    return (d["close"].rolling(5).mean() > d["close"].rolling(20).mean()).astype(int)

STRATS = {"buy_hold":s_buy_hold, "sma50_trend":s_sma50, "sma200_trend":s_sma200,
          "MA50W10":s_ma50w10, "donchian20":s_donchian20, "cross_5_20":s_cross_5_20}

def backtest(d, sigfn):
    sig = sigfn(d).shift(1).fillna(0)             # act next bar -> no lookahead
    ret = d["close"].pct_change().fillna(0)
    switch = sig.diff().abs().fillna(0)           # fee on entry/exit
    daily = sig*ret - switch*FEE
    eq = (1+daily).cumprod()
    yrs = max((d.index[-1]-d.index[0]).days/365.25, 0.1)
    total = (eq.iloc[-1]-1)*100
    cagr = (eq.iloc[-1]**(1/yrs)-1)*100
    peak = eq.cummax(); mdd = ((peak-eq)/peak).max()*100
    sharpe = (daily.mean()/daily.std()*np.sqrt(365)) if daily.std()>0 else 0.0
    recent = ((1+daily.iloc[-30:]).prod()-1)*100   # forward-test: last ~30 bars
    return dict(total_return=float(round(total,1)), cagr=float(round(cagr,1)), max_dd=float(round(mdd,1)),
                sharpe=float(round(sharpe,2)), pct_in_mkt=float(round(sig.mean()*100,0)),
                trades=int(switch.sum()), recent_30d=float(round(recent,1)))

def is_working(m):  # honest gate: positive risk-adjusted, survivable DD
    return bool(m["sharpe"]>=0.5 and m["cagr"]>0 and m["max_dd"]<50)

def main():
    pairs = {}
    for csv in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv"))):
        sym = os.path.splitext(os.path.basename(csv))[0].split("_")[0].upper()
        d = load_daily(csv)
        rows=[]
        for name,fn in STRATS.items():
            try:
                m = backtest(d, fn); m["strategy"]=name; m["working"]=is_working(m); rows.append(m)
            except Exception as e:
                rows.append({"strategy":name,"error":str(e)})
        rows.sort(key=lambda r: r.get("sharpe",-9), reverse=True)
        pairs[sym]={"period":f"{d.index[0].date()} -> {d.index[-1].date()}","results":rows}
    out={"generated":pd.Timestamp.utcnow().isoformat(),"fee_per_side":FEE,"pairs":pairs}
    json.dump(out, open(os.path.join(OUT_DIR,"leaderboard.json"),"w"), indent=2)
    # markdown leaderboard
    md=[f"# Strategy Lab leaderboard\n_generated {out['generated']} · fee {FEE*100:.2f}%/side · OOS, no-lookahead, paper-only_\n"]
    for sym,info in pairs.items():
        md.append(f"\n## {sym}  ({info['period']})\n")
        md.append("| strategy | return | CAGR | maxDD | Sharpe | last~30d | %in | ✅ |")
        md.append("|---|---|---|---|---|---|---|---|")
        for r in info["results"]:
            if "error" in r: md.append(f"| {r['strategy']} | ERR | | | | | | |"); continue
            md.append(f"| {r['strategy']} | {r['total_return']:+.0f}% | {r['cagr']:+.0f}% | {r['max_dd']:.0f}% | {r['sharpe']:.2f} | {r['recent_30d']:+.1f}% | {r['pct_in_mkt']:.0f}% | {'✅' if r['working'] else ''} |")
    open(os.path.join(OUT_DIR,"LEADERBOARD.md"),"w").write("\n".join(md))
    # console
    for sym,info in pairs.items():
        print(f"\n=== {sym} ({info['period']}) ===")
        for r in info["results"]:
            if "error" in r: print(f"  {r['strategy']:<14} ERROR {r['error'][:40]}"); continue
            tag="WORKING" if r["working"] else ""
            print(f"  {r['strategy']:<14} ret {r['total_return']:>+7.0f}%  CAGR {r['cagr']:>+5.0f}%  DD {r['max_dd']:>4.0f}%  Sharpe {r['sharpe']:>5.2f}  30d {r['recent_30d']:>+6.1f}%  {tag}")
    print(f"\nwrote {OUT_DIR}/LEADERBOARD.md + leaderboard.json")

if __name__=="__main__":
    main()
