#!/usr/bin/env python3
"""
PAPER SHADOW-EXECUTOR — the validated edge (MA50W10 / BTC), zero real money.

Runs daily on REAL BTC prices and builds a genuine FORWARD (out-of-sample)
track record anchored to a fixed go-live INCEPTION date. Unlike a re-backtest,
the equity curve only counts from the day we went live, so what you see is the
real performance you WOULD have had since switching it on — the honest bridge
to ever trusting real money.

NO orders. NO keys. NO live execution. Judges only.

Inputs  : a BTC OHLC csv (env SHADOW_DATA or lab_data/BTC.csv, fallback *_1h.csv)
State   : shadow_state.json   (stores inception + last mark; never re-anchored)
Outputs : PAPER_SHADOW.md, shadow_track.csv (one row per UTC date), shadow_state.json
Alerts  : optional Telegram on a position flip (TG_BOT_TOKEN/TG_CHAT_ID env)
"""
import os, json, time, urllib.parse, urllib.request
import pandas as pd, numpy as np
import lab

DATA = os.environ.get("SHADOW_DATA", os.path.join(os.path.dirname(__file__), "lab_data"))
OUT  = os.environ.get("SHADOW_OUT",  os.path.join(os.path.dirname(__file__), "results"))
PAIR = os.environ.get("SHADOW_PAIR", "BTC")
os.makedirs(OUT, exist_ok=True)
STATE = os.path.join(OUT, "shadow_state.json")
TRACK = os.path.join(OUT, "shadow_track.csv")

# ---- locate data ----
csv = os.path.join(DATA, f"{PAIR}.csv")
if not os.path.exists(csv):
    csv = os.path.join(DATA, f"{PAIR.lower()}_1h.csv")
if not os.path.exists(csv):
    raise SystemExit(f"shadow: no data for {PAIR} at {DATA}")

d = lab.load_daily(csv)
sig = lab.s_ma50w10(d)                       # signal computed on FULL history (valid MAs)
today = d.index[-1]

# ---- inception: fixed on first run, never moved ----
st = {}
try: st = json.load(open(STATE))
except Exception: pass
if "inception" not in st:
    st["inception"] = str(today.date())      # go-live = today
inception = pd.Timestamp(st["inception"])

# ---- forward slice from inception ----
mask = d.index >= inception
ds  = d[mask]
sg  = sig[mask]
if len(ds) < 2:
    # day-0: anchor + a zero-baseline report/track row so the dashboard renders now
    pos_now = "IN_BTC" if int(sig.iloc[-1]) == 1 else "IN_CASH"
    last_px = float(d["close"].iloc[-1])
    rep0 = {"generated": pd.Timestamp.now("UTC").isoformat(), "strategy": "MA50W10", "pair": PAIR,
            "inception": st["inception"], "days_live": 0, "current_state": pos_now,
            "last_action": st["inception"], "paper_return_pct": 0.0, "buy_hold_pct": 0.0,
            "max_dd_pct": 0.0, "sharpe": 0.0, "closed_trades": 0, "win_rate_pct": 0.0,
            "last_close": last_px}
    json.dump(rep0, open(os.path.join(OUT, "shadow_report.json"), "w"), indent=2)
    open(TRACK, "w").write("date,pos,paper_return_pct,buy_hold_pct,close,closed_trades,win_rate_pct\n"
                           f"{today.date()},{pos_now},0.00,0.00,{last_px:.2f},0,0.0\n")
    st.update({"last_state": pos_now, "updated": time.time()})
    json.dump(st, open(STATE, "w"), indent=2)
    print(f"shadow inception set {st['inception']} | pos {pos_now} | day-0 report written, curve from tomorrow")
    raise SystemExit(0)

sig_eff = sg.shift(1).fillna(0)
ret = ds["close"].pct_change().fillna(0)
switch = sig_eff.diff().abs().fillna(0)
daily = sig_eff*ret - switch*lab.FEE
eq = (1+daily).cumprod()

# ---- realized closed trades since inception ----
trades = []
entry_px = None; entry_dt = None
flips = sg[sg.diff() != 0]
for dt, s in sg.items():
    s = int(s)
    if s == 1 and entry_px is None:
        entry_px, entry_dt = float(ds["close"].loc[dt]), dt
    elif s == 0 and entry_px is not None:
        xpx = float(ds["close"].loc[dt])
        trades.append((entry_dt.date(), dt.date(), (xpx/entry_px-1)*100 - 2*lab.FEE*100))
        entry_px = None
wins = [t for t in trades if t[2] > 0]
win_rate = (len(wins)/len(trades)*100) if trades else 0.0

# ---- metrics ----
in_mkt   = int(sig.iloc[-1]) == 1
pos_now  = "IN_BTC" if in_mkt else "IN_CASH"
tot      = (eq.iloc[-1]-1)*100
bh       = (ds["close"].iloc[-1]/ds["close"].iloc[0]-1)*100
peak     = eq.cummax(); mdd = ((peak-eq)/peak).max()*100
sharpe   = (daily.mean()/daily.std()*np.sqrt(365)) if daily.std()>0 else 0.0
chg      = sg[sg.diff() != 0]
last_act = chg.index[-1].date() if len(chg) else ds.index[0].date()
days     = (today.date() - inception.date()).days
last_px  = float(ds["close"].iloc[-1])

report = {
    "generated": pd.Timestamp.now("UTC").isoformat(), "strategy": "MA50W10", "pair": PAIR,
    "inception": str(inception.date()), "days_live": days,
    "current_state": pos_now, "last_action": str(last_act),
    "paper_return_pct": round(tot,2), "buy_hold_pct": round(bh,2),
    "max_dd_pct": round(mdd,2), "sharpe": round(sharpe,2),
    "closed_trades": len(trades), "win_rate_pct": round(win_rate,1),
    "last_close": last_px,
}

# ---- write daily track row (idempotent per UTC date) ----
row_date = str(today.date())
prev_rows = []
if os.path.exists(TRACK):
    prev_rows = [l for l in open(TRACK).read().splitlines() if l and not l.startswith(row_date+",")]
header = "date,pos,paper_return_pct,buy_hold_pct,close,closed_trades,win_rate_pct"
body = [r for r in prev_rows if r != header]
body.append(f"{row_date},{pos_now},{tot:.2f},{bh:.2f},{last_px:.2f},{len(trades)},{win_rate:.1f}")
open(TRACK, "w").write(header + "\n" + "\n".join(body) + "\n")

# ---- markdown card ----
state_emoji = "🟢 IN BTC (long)" if in_mkt else "⚪️ IN CASH (USDT)"
md = f"""# 📒 Paper Shadow — MA50W10 / {PAIR}  (the validated edge, zero money)
_generated {report['generated']} · forward track since **{report['inception']}** ({days} days live)_

## RIGHT NOW
- **Position:** {state_emoji}  (last change {last_act})
- Last close: {last_px:,.0f}

## Forward track record (since go-live, out-of-sample)
| metric | MA50W10 | buy & hold |
|---|---|---|
| return | **{tot:+.2f}%** | {bh:+.2f}% |
| max drawdown | {mdd:.2f}% | — |
| Sharpe (ann.) | {sharpe:.2f} | — |
| closed trades | {len(trades)} | — |
| win rate | {win_rate:.0f}% | — |

> Honest forward record — counts only from {report['inception']}, no hindsight.
> Fund real money only after this proves itself live-shadow. Live bot stays guarded.
"""
open(os.path.join(OUT, "PAPER_SHADOW.md"), "w").write(md)

# ---- optional Telegram on flip ----
prev_state = st.get("last_state")
if prev_state and prev_state != pos_now:
    arrow = "🟢 BUY CASH→BTC" if pos_now == "IN_BTC" else "⚪️ EXIT BTC→CASH"
    msg = f"[SHADOW] {arrow} | MA50W10/{PAIR} | close {last_px:,.0f} | fwd {tot:+.2f}% ({days}d)"
    tok, chat = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
    if tok and chat:
        try:
            url = f"https://api.telegram.org/bot{tok}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
            urllib.request.urlopen(url, data=data, timeout=10); print("  telegram: sent")
        except Exception as e: print(f"  telegram: failed ({e})")

st.update({"last_state": pos_now, "updated": time.time()})
json.dump(st, open(STATE, "w"), indent=2)
json.dump(report, open(os.path.join(OUT, "shadow_report.json"), "w"), indent=2)
print(f"SHADOW MA50W10/{PAIR}: {pos_now} | fwd {tot:+.2f}% (BH {bh:+.2f}%) | {days}d | "
      f"{len(trades)} trades {win_rate:.0f}% win | DD {mdd:.1f}% | inception {report['inception']}")
