#!/usr/bin/env python3
"""
Quick edge backtest: replays real Gate.io 10s candles for the 3 battle pairs and
compares OLD params (TP 0.35 / SL 0.18 / hold 90s / CMO>=15) vs NEW EDGE params
(TP 0.22 / SL 0.30 / hold 240s, fee-aware / CMO>=8). Spot, long-only, fee 0.20% RT.
"""
import urllib.request, json, time

PAIRS = ["FLOKI_USDT", "BOME_USDT", "WIF_USDT"]
FEE = 0.0020  # round-trip taker
TICK = 10     # candle interval seconds

def klines(pair, limit=1000, interval="10s"):
    url = (f"https://api.gateio.ws/api/v4/spot/candlesticks"
           f"?currency_pair={pair}&limit={limit}&interval={interval}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    # gate candle: [t, volume, close, high, low, open, ...]
    return [(float(c[2]), float(c[3]), float(c[4])) for c in data]  # (close, high, low)

def cmo(closes, period=14):
    if len(closes) < period + 1: return 0.0
    ups = sum(max(closes[i]-closes[i-1],0) for i in range(-period,0))
    dns = sum(max(closes[i-1]-closes[i],0) for i in range(-period,0))
    return (ups-dns)/(ups+dns)*100 if (ups+dns)>0 else 0.0

def ema(closes, period=3):
    if not closes: return 0.0
    k=2/(period+1); e=closes[0]
    for c in closes[1:]: e=c*k+e*(1-k)
    return e

def ema_p(closes, period):
    if not closes: return 0.0
    k=2/(period+1); e=closes[0]
    for c in closes[1:]: e=c*k+e*(1-k)
    return e

def regime_up(closes):
    if len(closes) < 21: return False
    fast=ema_p(closes[-5:],5); slow=ema_p(closes[-20:],20)
    if fast<=slow: return False
    ref=closes[-8]
    if ref<=0 or (closes[-1]-ref)/ref < 0.0005: return False
    w=closes[-20:]; hi,lo=max(w),min(w)
    if hi==lo: return False
    return (closes[-1]-lo)/(hi-lo) >= 0.45

def backtest(rows, tp_pct, sl_pct, hold_s, cmo_thr, ema_tol, fee_aware, use_regime=False):
    closes=[r[0] for r in rows]
    n=len(rows)
    hold_ticks=max(1,hold_s//TICK)
    i=20; pos=None; trades=[]; cooldown=0
    while i < n-1:
        c,h,l=rows[i]
        if pos is None:
            if cooldown>0: cooldown-=1; i+=1; continue
            window=closes[max(0,i-30):i+1]
            if len(window)<15: i+=1; continue
            ok = cmo(window)>=cmo_thr and c>=ema(window[-3:])*ema_tol
            if use_regime and ok:
                ok = regime_up(window)
            if ok:
                pos={"entry":c,"tp":c*(1+tp_pct),"sl":c*(1-sl_pct),"open_i":i}
            i+=1; continue
        # in position: check next bars
        age=i-pos["open_i"]
        hit_tp = h>=pos["tp"]
        hit_sl = l<=pos["sl"]
        aged = age>=hold_ticks
        fee_clear = c>=pos["entry"]*(1+FEE)
        hard=age>=2*hold_ticks
        if fee_aware and aged and not (fee_clear or hard):
            aged=False
        if hit_tp:
            ret=tp_pct-FEE; trades.append(ret); pos=None; cooldown=max(1,75//TICK)
        elif hit_sl:
            ret=-sl_pct-FEE; trades.append(ret); pos=None; cooldown=max(1,75//TICK)
        elif aged:
            ret=(c/pos["entry"]-1)-FEE; trades.append(ret); pos=None; cooldown=max(1,75//TICK)
        i+=1
    return trades

def summarize(name, all_trades, notional=15.0):
    n=len(all_trades)
    if n==0:
        print(f"  {name:5s}: 0 trades"); return
    wins=sum(1 for t in all_trades if t>0)
    pnl=sum(t*notional for t in all_trades)
    gw=sum(t for t in all_trades if t>0); gl=-sum(t for t in all_trades if t<0)
    pf=(gw/gl) if gl>0 else float('inf')
    print(f"  {name:5s}: trades={n:3d}  win%={100*wins/n:5.1f}  PF={pf:4.2f}  "
          f"netPnL=${pnl:+7.3f} (on ${notional}/trade)")

def main():
    old_all=[]; new_all=[]
    for p in PAIRS:
        try:
            rows=klines(p)
        except Exception as e:
            print("fetch fail",p,e); continue
        old=backtest(rows, 0.0035, 0.0018, 90,  15.0, 0.999, fee_aware=False)
        new=backtest(rows, 0.0022, 0.0030, 240, 8.0,  0.997, fee_aware=True, use_regime=True)
        old_all+=old; new_all+=new
        print(f"{p}:")
        summarize("OLD", old); summarize("NEW", new)
        time.sleep(0.3)
    print("\n=== COMBINED (3 pairs, last ~1000x10s candles ≈ 2.8h each) ===")
    summarize("OLD", old_all); summarize("NEW", new_all)

if __name__=="__main__":
    main()
