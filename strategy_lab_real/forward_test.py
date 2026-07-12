#!/usr/bin/env python3
"""
Paper FORWARD-TEST tracker for the one validated setup: MA50W10 on BTC.
Reads fresh BTC data, runs the strategy day-by-day in paper, and reports the
LIVE state it would be in right now (in-BTC or in-cash) + performance.
This is what the live bot SHOULD do (BTC-only MA50W10) — with zero real money.
"""
import os, json
import pandas as pd, numpy as np
import lab

DATA = os.environ.get("FWD_DATA", os.path.join(os.path.dirname(__file__), "lab_data"))
OUT  = os.environ.get("FWD_OUT",  os.path.join(os.path.dirname(__file__), "results"))
PAIR = os.environ.get("FWD_PAIR", "BTC")
os.makedirs(OUT, exist_ok=True)

csv = os.path.join(DATA, f"{PAIR}.csv")
if not os.path.exists(csv):
    csv = os.path.join(DATA, f"{PAIR.lower()}_1h.csv")
d = lab.load_daily(csv)

sig = lab.s_ma50w10(d)
sig_eff = sig.shift(1).fillna(0)
ret = d["close"].pct_change().fillna(0)
daily = sig_eff*ret - sig_eff.diff().abs().fillna(0)*lab.FEE
eq = (1+daily).cumprod()

in_mkt = bool(sig.iloc[-1] == 1)
# last position change
chg = sig[sig.diff() != 0]
last_change = chg.index[-1].date() if len(chg) else d.index[0].date()
tot = (eq.iloc[-1]-1)*100
r30 = ((1+daily.iloc[-30:]).prod()-1)*100
peak = eq.cummax(); mdd = ((peak-eq)/peak).max()*100
bh = (d["close"].iloc[-1]/d["close"].iloc[0]-1)*100
sharpe = (daily.mean()/daily.std()*np.sqrt(365)) if daily.std()>0 else 0.0

state = "🟢 IN BTC (long)" if in_mkt else "⚪️ IN CASH (USDT)"
report = {
    "generated": pd.Timestamp.now("UTC").isoformat(), "pair": PAIR, "strategy": "MA50W10",
    "window": f"{d.index[0].date()} -> {d.index[-1].date()}",
    "current_state": "IN_BTC" if in_mkt else "IN_CASH",
    "since_signal_changed": str(last_change),
    "paper_return_pct": round(tot,1), "last30d_pct": round(r30,1),
    "max_dd_pct": round(mdd,1), "sharpe": round(sharpe,2), "buy_hold_pct": round(bh,1),
    "last_close": float(d["close"].iloc[-1]),
}
json.dump(report, open(os.path.join(OUT,"forward_test.json"),"w"), indent=2)
md = f"""# Paper Forward-Test — MA50W10 / {PAIR}
_generated {report['generated']} · paper-only, no real money · window {report['window']}_

## RIGHT NOW
- **State:** {state}  (since {last_change})
- Last close: {report['last_close']:,.0f}

## Paper performance (this window)
| metric | MA50W10 | buy&hold |
|---|---|---|
| return | {tot:+.0f}% | {bh:+.0f}% |
| last ~30d | {r30:+.1f}% | — |
| max drawdown | {mdd:.0f}% | — |
| Sharpe | {sharpe:.2f} | — |

> This is the validated setup running in paper. Watch it here before risking real money.
> When you trust it, re-arm the live bot **BTC-only** behind the preflight guard.
"""
open(os.path.join(OUT,"FORWARD_TEST.md"),"w").write(md)
print(f"MA50W10/{PAIR}: {state} since {last_change} | paper {tot:+.0f}% (vs BH {bh:+.0f}%) | 30d {r30:+.1f}% | DD {mdd:.0f}% | Sharpe {sharpe:.2f}")
