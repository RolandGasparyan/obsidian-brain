"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   GODS LEVEL ENGINE — SINGLE PAIR FOCUS · 10 AGENTS · USDT-ONLY            ║
║   Gate.io Spot · Micro Scalping · 24/7 Autonomous                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  RULES:                                                                      ║
║  1. Score ALL pairs → pick ONE best pair to trade                            ║
║  2. All 10 agents micro-scalp that ONE pair simultaneously                  ║
║  3. If pair is losing (3 losses OR -1.5% PnL) → EXIT → 100% USDT           ║
║  4. Score pairs again → pick next best → restart agents there               ║
║  5. Between trades you are ALWAYS 100% USDT. Zero token holding.            ║
║                                                                              ║
║  ⚠  PAPER MODE default. Crypto trading = substantial risk of loss.          ║
╚══════════════════════════════════════════════════════════════════════════════╝

INSTALL:   pip install requests
RUN:       python gods_final.py
LIVE MODE: Set LIVE_MODE = True (after extensive paper testing)
           Add keys: export GATEIO_API_KEY=xxx GATEIO_SECRET=xxx
"""

import os, json, time, math, hmac, hashlib, logging, random, threading
from datetime import datetime, timezone
from typing   import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum        import Enum

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════
class C:
    LIVE_MODE  = False            # ← Paper. Set True only after testing.
    EXCHANGE   = "gateio"         # "gateio" | "binance"

    # Selected via backtest_multi_token.py + select_best_tokens.py (see
    # MULTI_TOKEN_RESULTS.md). These four pass all three quality filters:
    # liquidity ≥ $2.5M/day, MA50+W10 ROI ≥ +500%, edge over B&H ≥ +400%.
    PAIRS = [
        "ETH_USDT",    # $523M vol · +543% ROI · 75% WR  (core)
        "SOL_USDT",    #  $89M vol · +1,401% ROI · 70% WR (high-beta core)
        "XRP_USDT",    # $110M vol · +541% ROI · 47% WR  (liquidity diversifier)
        "AVAX_USDT",   #  $2.8M vol · +817% ROI · 62% WR (alt beta)
    ]

    BALANCE         = 1000.0      # Starting USDT
    MAX_POS_PCT     = 0.08        # 8% of balance max per trade
    DAILY_STOP      = 0.035       # 3.5% daily hard stop → engine halts

    MIN_VOTES       = 3           # Agent votes needed to enter (out of 9)
    PAIR_LOSSES_MAX = 3           # Consecutive losses on pair → switch
    PAIR_PNL_FLOOR  = -0.015      # -1.5% cumulative pair PnL → switch
    MAX_HOLD_SEC    = 172800      # 48 h — appropriate for 4h trading default

    MAKER_FEE  = 0.0010           # Gate.io VIP0
    TAKER_FEE  = 0.0015
    FEE_RT     = MAKER_FEE + TAKER_FEE   # round-trip 0.25%

    # Stop / TP geometry — defaults tuned to 4h-WIDE-STOP (best real-data preset)
    STOP_ATR_MULT = 0.70          # stop = entry - ATR × this
    STOP_PCT_CAP  = 0.0080        # cap stop at entry × (1 - this)
    TP_ATR_MULT   = 1.8           # signal-level TP (Vote.tp only)
    TP1_R         = 0.6           # tp1 = entry + risk × TP1_R
    TP2_R         = 1.1
    TP3_R         = 1.8

    # Partial exit / breakeven management
    PARTIAL_TP1_FRAC  = 0.50      # sell this fraction of remaining at TP1 (0=off)
    BREAKEVEN_BUFFER  = 1.5       # move stop to entry × (1 + FEE_RT × this) after TP1

    # Higher-timeframe regime filter (Plugin #1) — veto longs when HTF is not bullish
    HTF_FILTER_ENABLED = True
    HTF_INTERVAL       = "1d"     # HTF candle size (4h trading → 1d HTF is ~6x)
    HTF_EMA_PERIOD     = 50

    # Per-agent performance weighting (Plugin #2) — Consensus votes
    # weighted by each agent's rolling win rate over the last N trades
    AGENT_WEIGHT_ENABLED      = True
    AGENT_WEIGHT_WINDOW       = 20     # rolling sample size
    AGENT_WEIGHT_MIN_SAMPLES  = 5      # cold-start threshold

    # Synthetic-bar volatility scale — 1.0=1m, ~2.2=5m, ~3.9=15m
    VOL_MULT      = 1.0

    LOOP_SLEEP = 10               # Seconds between loops (live)
    SIM_SLEEP  = 0.0              # Seconds between loops (sim)
    CANDLES    = 200              # Candles per fetch
    INTERVAL   = "4h"             # 1m | 5m | 15m | 1h | 4h — used by fetch_bars
    USE_REAL_DATA = False         # Paper mode: True → fetch live bars, paper orders

    GIO_KEY = os.getenv("GATEIO_API_KEY","")
    GIO_SEC = os.getenv("GATEIO_SECRET","")
    BIN_KEY = os.getenv("BINANCE_API_KEY","")
    BIN_SEC = os.getenv("BINANCE_SECRET","")


# ═══════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════
class Sig(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY        = "BUY"
    HOLD       = "HOLD"

@dataclass
class Bar:
    ts: int; o: float; h: float; l: float; c: float; v: float

    @property
    def body(self):  return abs(self.c - self.o)
    @property
    def rng(self):   return max(self.h - self.l, 1e-10)
    @property
    def bull(self):  return self.c > self.o
    @property
    def lw(self):    return min(self.o, self.c) - self.l   # lower wick
    @property
    def uw(self):    return self.h - max(self.o, self.c)   # upper wick

@dataclass
class Vote:
    name:   str
    signal: Sig
    conf:   float     # 0–1
    stop:   float
    tp:     float
    reason: str

@dataclass
class Trade:
    id:      str
    pair:    str
    entry:   float
    units:   float
    usdt_in: float
    stop:    float
    tp1:     float; tp2: float; tp3: float
    trail:   float
    peak:    float
    t_open:  float = field(default_factory=time.time)
    agent:   str   = "CONSENSUS"
    closed:  bool  = False
    exit_px: float = 0.0
    pnl:     float = 0.0
    pnl_pct: float = 0.0
    why:     str   = ""
    # Partial-exit bookkeeping
    tp1_hit:       bool  = False
    realized_pnl:  float = 0.0   # PnL already booked from partial fills
    initial_units: float = 0.0   # units at open, before any partial sells
    initial_risk:  float = 0.0   # entry - original_stop, frozen at open
    # Agent attribution (Plugin #2) — names of agents that voted BUY at entry
    buy_voters:    List[str] = field(default_factory=list)

@dataclass
class PairRank:
    pair:     str
    score:    float
    atr_pct:  float
    vol_x:    float
    rsi:      float
    trend:    str


# ═══════════════════════════════════════════════════════════════
# PURE-PYTHON INDICATORS (zero external deps)
# ═══════════════════════════════════════════════════════════════
class T:
    """Technical indicators — pure Python, no pandas/numpy."""

    @staticmethod
    def ema(d: List[float], p: int) -> List[Optional[float]]:
        r = [None]*len(d)
        if len(d) < p: return r
        k = 2/(p+1)
        r[p-1] = sum(d[:p])/p
        for i in range(p, len(d)):
            r[i] = d[i]*k + r[i-1]*(1-k)
        return r

    @staticmethod
    def sma(d: List[float], p: int) -> List[Optional[float]]:
        r = [None]*len(d)
        for i in range(p-1, len(d)):
            r[i] = sum(d[i-p+1:i+1])/p
        return r

    @staticmethod
    def rsi(d: List[float], p: int = 14) -> List[Optional[float]]:
        n = len(d); r = [None]*n
        if n < p+1: return r
        g = [max(d[i]-d[i-1], 0) for i in range(1,n)]
        l = [max(d[i-1]-d[i], 0) for i in range(1,n)]
        ag = sum(g[:p])/p; al = sum(l[:p])/p
        for i in range(p, n):
            j = i-p
            if j > 0:
                ag = (ag*(p-1)+g[j])/p
                al = (al*(p-1)+l[j])/p
            r[i] = 100.0 if al == 0 else 100-100/(1+ag/al)
        return r

    @staticmethod
    def macd(d, f=12, s=26, sg=9):
        def _e(dd,pp):
            v = T.ema(dd,pp); return [x or 0.0 for x in v]
        ml = [a-b for a,b in zip(_e(d,f), _e(d,s))]
        sl = _e(ml, sg)
        return {"m":ml, "s":sl, "h":[a-b for a,b in zip(ml,sl)]}

    @staticmethod
    def atr(bars: List[Bar], p: int = 14) -> List[Optional[float]]:
        tr = [bars[0].h - bars[0].l]
        for i in range(1, len(bars)):
            tr.append(max(
                bars[i].h - bars[i].l,
                abs(bars[i].h - bars[i-1].c),
                abs(bars[i].l - bars[i-1].c)
            ))
        r = [None]*len(tr)
        if len(tr) < p: return r
        r[p-1] = sum(tr[:p])/p
        for i in range(p, len(tr)):
            r[i] = (r[i-1]*(p-1) + tr[i])/p
        return r

    @staticmethod
    def bb(d, p=20, sd=2.0):
        n = len(d); u = [None]*n; l = [None]*n; m = T.sma(d,p)
        for i in range(p-1, n):
            w = d[i-p+1:i+1]; mu = sum(w)/p
            s = math.sqrt(sum((x-mu)**2 for x in w)/p)
            u[i] = m[i] + sd*s; l[i] = m[i] - sd*s
        return {"u":u, "m":m, "l":l}

    @staticmethod
    def vwap(bars: List[Bar]) -> List[float]:
        ct = cv = 0.0; r = []
        for b in bars:
            tp = (b.h+b.l+b.c)/3; ct += tp*b.v; cv += b.v
            r.append(ct/cv if cv > 0 else b.c)
        return r

    @staticmethod
    def last(lst) -> Optional[float]:
        for v in reversed(lst):
            if v is not None: return v
        return None

    @staticmethod
    def swing_h(bars: List[Bar], lb=2) -> Optional[float]:
        for i in range(len(bars)-lb-1, lb-1, -1):
            if bars[i].h == max(b.h for b in bars[i-lb:i+lb+1]):
                return bars[i].h
        return None

    @staticmethod
    def swing_l(bars: List[Bar], lb=2) -> Optional[float]:
        for i in range(len(bars)-lb-1, lb-1, -1):
            if bars[i].l == min(b.l for b in bars[i-lb:i+lb+1]):
                return bars[i].l
        return None

    @staticmethod
    def closes(bars): return [b.c for b in bars]
    @staticmethod
    def vols(bars):   return [b.v for b in bars]


# ═══════════════════════════════════════════════════════════════
# HIGHER-TIMEFRAME REGIME FILTER (Plugin #1)
# ═══════════════════════════════════════════════════════════════
def htf_bullish(htf_bars: List[Bar], ema_period: int = 50,
                rise_lookback: int = 5) -> bool:
    """True if price > EMA(period) AND EMA is rising.
    Used as a veto filter on long entries — skip longs when the higher
    timeframe is not confirming the trend.
    """
    if not htf_bars or len(htf_bars) < ema_period + rise_lookback + 2:
        return False
    cl = T.closes(htf_bars)
    ema = T.ema(cl, ema_period)
    last_ema = T.last(ema)
    if last_ema is None or last_ema <= 0:
        return False
    prev_ema = ema[-rise_lookback - 1] if len(ema) > rise_lookback else last_ema
    if prev_ema is None or prev_ema <= 0:
        return False
    return (cl[-1] > last_ema) and (last_ema > prev_ema)


# ═══════════════════════════════════════════════════════════════
# EXCHANGE API
# ═══════════════════════════════════════════════════════════════
class Exchange:

    BASE_PRICES = {
        "BTC_USDT":67000,"ETH_USDT":3500,"SOL_USDT":180,"BNB_USDT":420,
        "XRP_USDT":0.62,"ADA_USDT":0.55,"DOGE_USDT":0.15,"AVAX_USDT":38,
        "MATIC_USDT":0.85,"LINK_USDT":14,
    }

    def __init__(self):
        self.sess = requests.Session() if _HAS_REQUESTS else None
        self.base = ("https://api.gateio.ws/api/v4"
                     if C.EXCHANGE == "gateio" else "https://api.binance.com")

    # ── PUBLIC CANDLES (read-only, no auth) ──
    # CRITICAL: the last bar returned by each exchange is typically the
    # **currently forming** one — its "close" is actually the live
    # intraday price. Using it in a moving-average signal causes
    # whipsaw: every ~10s loop, the live price ticks across the MA and
    # the bot flips LONG/USDT, paying fees on each flip. We drop the
    # unfinalized tail bar so all downstream logic sees only closed
    # bars, matching the backtest's semantics exactly.
    def fetch_bars(self, pair: str, limit: int = 200) -> List[Bar]:
        if not _HAS_REQUESTS:
            return []
        try:
            if C.EXCHANGE == "gateio":
                # Gate.io row: [ts, quote_vol, close, high, low, open,
                #               base_vol, finalized_bool]
                # finalized_bool is a STRING "true"/"false" in the v4 API.
                r = self.sess.get(f"{self.base}/spot/candlesticks",
                    params={"currency_pair":pair,"interval":C.INTERVAL,
                            "limit":limit + 1}, timeout=8)
                r.raise_for_status()
                rows = r.json()
                bars = []
                for x in rows:
                    finalized = True
                    if len(x) >= 8:
                        f = x[7]
                        finalized = (f is True) or (isinstance(f, str) and f.lower() == "true")
                    if not finalized:
                        continue
                    bars.append(Bar(int(x[0]), float(x[5]), float(x[3]),
                                    float(x[4]), float(x[2]), float(x[1])))
                return sorted(bars, key=lambda b: b.ts)
            else:
                sym = pair.replace("_","")
                r = self.sess.get(f"{self.base}/api/v3/klines",
                    params={"symbol":sym,"interval":C.INTERVAL,
                            "limit":limit + 1}, timeout=8)
                r.raise_for_status()
                rows = r.json()
                now_ms = int(time.time() * 1000)
                bars = []
                for x in rows:
                    # Binance row ends with closeTime (ms) at index 6.
                    close_time = int(x[6]) if len(x) > 6 else 0
                    if close_time and close_time > now_ms:
                        # Bar is still open — skip the forming last bar
                        continue
                    bars.append(Bar(int(x[0]), float(x[1]), float(x[2]),
                                    float(x[3]), float(x[4]), float(x[5])))
                return bars
        except Exception as e:
            logging.warning(f"fetch_bars {pair}: {e}")
            return []

    # ── SIMULATED CANDLES — unique per (pair, seed) ──
    def sim_bars(self, pair: str, limit: int, seed: int) -> List[Bar]:
        """
        Generates realistic candle data.
        seed controls market character: trending, ranging, volatile, etc.
        Every unique seed produces a genuinely different market scenario.
        """
        base = self.BASE_PRICES.get(pair, 100.0)
        rng  = random.Random(seed)

        # Market character from seed
        trend_bias   = rng.uniform(-0.0004, 0.0005)   # -ve=bear, +ve=bull
        volatility   = rng.uniform(0.0003, 0.0010)    # per-candle vol
        vol_mean     = rng.uniform(200, 1200)          # average volume
        regime       = rng.choice(["bull","bear","range","squeeze_bull","squeeze_bear"])

        # Regime overrides
        if regime == "bull":
            trend_bias  = abs(trend_bias) + 0.0002
            volatility *= 0.9
        elif regime == "bear":
            trend_bias  = -abs(trend_bias) - 0.0002
        elif regime == "range":
            trend_bias  = 0
            volatility *= 0.6
        elif regime == "squeeze_bull":
            trend_bias  = 0.0003
            volatility  = rng.uniform(0.0002, 0.0005)
        elif regime == "squeeze_bear":
            trend_bias  = -0.0002
            volatility  = rng.uniform(0.0002, 0.0005)

        # Timeframe scaling: 5m ≈ √5×vol, 15m ≈ √15×vol (Brownian scaling)
        volatility  *= C.VOL_MULT
        trend_bias  *= C.VOL_MULT

        price = base * rng.uniform(0.97, 1.03)
        ts    = int(time.time()) - limit * 60
        bars  = []

        for i in range(limit):
            drift = trend_bias + rng.gauss(0, volatility)
            price = max(price * (1 + drift), 1e-6)
            rn    = price * rng.uniform(0.0002, 0.0014) * C.VOL_MULT
            h = price + rn * rng.uniform(0.3, 0.85)
            l = price - rn * rng.uniform(0.3, 0.85)
            o = l + (h-l) * rng.uniform(0.1, 0.9)
            c = l + (h-l) * rng.uniform(0.1, 0.9)
            # Volume surge near end of bull runs
            late_surge = 1.8 if (i > limit*0.75 and trend_bias > 0.0002) else 1.0
            v = rng.uniform(vol_mean*0.4, vol_mean*2.2) * late_surge * (1 + abs(drift)*150)
            bars.append(Bar(ts + i*60,
                            round(o,8), round(h,8), round(l,8),
                            round(c,8), round(v,4)))
        return bars

    def get_price(self, pair: str) -> float:
        if not _HAS_REQUESTS or not C.LIVE_MODE: return 0.0
        try:
            if C.EXCHANGE == "gateio":
                r = self.sess.get(f"{self.base}/spot/tickers",
                    params={"currency_pair":pair}, timeout=5)
                return float(r.json()[0]["last"])
            else:
                r = self.sess.get(f"{self.base}/api/v3/ticker/price",
                    params={"symbol":pair.replace("_","")}, timeout=5)
                return float(r.json()["price"])
        except: return 0.0

    # ── ORDER EXECUTION ──
    def order(self, pair: str, side: str, usdt: float, price: float) -> dict:
        if not C.LIVE_MODE:
            return {"status":"filled","price":price,
                    "units": usdt/price if price>0 else 0, "paper":True}
        try:
            if C.EXCHANGE == "gateio":
                return self._gio_order(pair, side, usdt, price)
            else:
                return self._bin_order(pair, side, usdt, price)
        except Exception as e:
            logging.error(f"Order {pair} {side}: {e}")
            return {"status":"failed","error":str(e)}

    def _gio_order(self, pair, side, usdt, price):
        units = usdt / price
        path  = "/api/v4/spot/orders"
        body  = json.dumps({"currency_pair":pair,"type":"market",
                             "account":"spot","side":side,
                             "amount":f"{units:.8f}"})
        ts    = str(int(time.time()))
        bh    = hashlib.sha512(body.encode()).hexdigest()
        msg   = f"POST\n{path}\n\n{bh}\n{ts}"
        sig   = hmac.new(C.GIO_SEC.encode(), msg.encode(), hashlib.sha512).hexdigest()
        hdrs  = {"KEY":C.GIO_KEY,"Timestamp":ts,"SIGN":sig,
                 "Content-Type":"application/json"}
        r     = self.sess.post(f"{self.base}{path}", headers=hdrs, data=body, timeout=10)
        r.raise_for_status()
        d = r.json()
        return {"status":"filled","price":price,"units":units,"raw":d}

    def _bin_order(self, pair, side, usdt, price):
        sym   = pair.replace("_","")
        units = usdt / price
        ts_ms = int(time.time()*1000)
        qs    = (f"symbol={sym}&side={side.upper()}&type=MARKET"
                 f"&quantity={units:.6f}&timestamp={ts_ms}")
        sig   = hmac.new(C.BIN_SEC.encode(), qs.encode(), hashlib.sha256).hexdigest()
        hdrs  = {"X-MBX-APIKEY": C.BIN_KEY}
        r     = self.sess.post(f"{self.base}/api/v3/order?{qs}&signature={sig}",
                               headers=hdrs, timeout=10)
        r.raise_for_status()
        return {"status":"filled","price":price,"units":units,"raw":r.json()}


# ═══════════════════════════════════════════════════════════════
# AGENT SIGNAL BUILDER — shared helper
# ═══════════════════════════════════════════════════════════════
def make_vote(name: str, bars: List[Bar], sig: Sig, conf: float,
              reason: str) -> Vote:
    b    = bars[-1]
    atrv = T.atr(bars, 7)
    atr  = T.last(atrv) or b.c * 0.004
    stop = max(b.c - atr * C.STOP_ATR_MULT, b.c * (1.0 - C.STOP_PCT_CAP))
    tp   = b.c + atr * C.TP_ATR_MULT
    return Vote(name, sig, round(conf,3), round(stop,8), round(tp,8), reason)


# ═══════════════════════════════════════════════════════════════
# 9 MICRO-SCALP AGENTS
# ═══════════════════════════════════════════════════════════════

class ScalpGod:
    """ATR-regime + RSI + EMA cross + volume. 1m focus."""
    N = "SCALP_GOD"
    def run(self, bars: List[Bar]) -> Vote:
        if len(bars) < 25:
            return make_vote(self.N, bars, Sig.HOLD, 0, "short")
        cl = T.closes(bars); b = bars[-1]
        r7  = T.rsi(cl, 7);   rsi = T.last(r7) or 50
        e9  = T.ema(cl, 9);   a9  = T.last(e9)  or b.c
        e21 = T.ema(cl, 21);  a21 = T.last(e21) or b.c
        atr = T.last(T.atr(bars,7)) or b.c*0.005
        ap  = atr/b.c*100
        if ap < 0.02 or ap > 0.18:
            return make_vote(self.N, bars, Sig.HOLD, 0.05, f"ATR%={ap:.3f}")
        sc = 0; rs = []
        if a9 > a21 and b.c > a9:    sc+=3; rs.append("EMA9>21")
        if 48 <= rsi <= 70:           sc+=2; rs.append(f"RSI={rsi:.0f}")
        av = sum(x.v for x in bars[-20:])/20
        if b.v > av*1.4:              sc+=2; rs.append(f"vol={b.v/av:.1f}x")
        if b.bull and b.lw < b.body:  sc+=1; rs.append("bull")
        if len(bars)>=3 and bars[-1].c>bars[-2].c>bars[-3].c:
                                      sc+=1; rs.append("3up")
        if sc >= 6:
            return make_vote(self.N, bars, Sig.BUY, min(0.95,sc/9), " ".join(rs))
        return make_vote(self.N, bars, Sig.HOLD, 0.1, f"sc={sc}/9")


class MomentumRider:
    """MACD fast + RSI + price acceleration."""
    N = "MOMENTUM"
    def run(self, bars: List[Bar]) -> Vote:
        if len(bars) < 35:
            return make_vote(self.N, bars, Sig.HOLD, 0, "short")
        cl = T.closes(bars); b = bars[-1]
        md  = T.macd(cl, 3, 7, 5)
        h   = md["h"];   ml = md["m"]; sl = md["s"]
        rsi = T.last(T.rsi(cl, 14)) or 50
        e21 = T.last(T.ema(cl, 21)) or b.c
        sc  = 0; rs = []
        if len(h)>=2 and h[-1]>0 and h[-1]>h[-2]:
            sc+=3; rs.append(f"MACD↑{h[-1]:.5f}")
        if len(ml)>=2 and ml[-2]<=sl[-2] and ml[-1]>sl[-1]:
            sc+=3; rs.append("MACD_cross")
        if 50 <= rsi <= 72:   sc+=2; rs.append(f"RSI={rsi:.0f}")
        if b.c > e21:          sc+=1; rs.append("abvEMA21")
        if bars[-1].c>bars[-2].c>bars[-3].c: sc+=1; rs.append("3up")
        if sc>=7:
            return make_vote(self.N, bars, Sig.BUY, min(0.90,sc/10), " ".join(rs))
        return make_vote(self.N, bars, Sig.HOLD, 0.1, f"sc={sc}/10")


class VWAPSniper:
    """VWAP proximity + bounce + volume."""
    N = "VWAP_SNIP"
    def run(self, bars: List[Bar]) -> Vote:
        if len(bars) < 30:
            return make_vote(self.N, bars, Sig.HOLD, 0, "short")
        vw  = T.vwap(bars); b = bars[-1]
        vn  = vw[-1]
        rsi = T.last(T.rsi(T.closes(bars), 14)) or 50
        dp  = (b.c - vn)/vn*100 if vn > 0 else 0
        sc  = 0; rs = []
        if 0.0 <= dp <= 0.22:   sc+=3; rs.append(f"+{dp:.3f}%VWAP")
        # Prior touch of VWAP
        for i, prev in enumerate(bars[-5:-1]):
            pv = vw[len(bars)-5+i]
            if abs(prev.l-pv)/pv*100 < 0.15: sc+=2; rs.append("VWAPtouch"); break
        if b.bull and b.lw > b.body*0.5: sc+=2; rs.append("hammer")
        if 44 <= rsi <= 66: sc+=1; rs.append(f"RSI={rsi:.0f}")
        av = sum(x.v for x in bars[-20:])/20
        if b.v > av*1.3:        sc+=2; rs.append(f"vol={b.v/av:.1f}x")
        if sc>=6:
            return make_vote(self.N, bars, Sig.BUY, min(0.88,sc/10), " ".join(rs))
        return make_vote(self.N, bars, Sig.HOLD, 0.1, f"sc={sc}/10")


class StructureBreak:
    """Swing high breakout with volume."""
    N = "STR_BREAK"
    def run(self, bars: List[Bar]) -> Vote:
        if len(bars) < 20:
            return make_vote(self.N, bars, Sig.HOLD, 0, "short")
        b   = bars[-1]
        rsi = T.last(T.rsi(T.closes(bars), 7)) or 50
        sh  = T.swing_h(bars[:-1], 2)
        if sh is None:
            return make_vote(self.N, bars, Sig.HOLD, 0.1, "no swing")
        sc  = 0; rs = []
        if b.c > sh:           sc+=4; rs.append(f">{sh:.4f}")
        av = sum(x.v for x in bars[-10:])/10
        if b.v > av*1.8:       sc+=3; rs.append(f"vol={b.v/av:.1f}x")
        if rsi > 53:            sc+=2; rs.append(f"RSI={rsi:.0f}")
        if b.bull and b.body>0.55*b.rng: sc+=1; rs.append("bull_body")
        if sc>=7:
            s = Sig.STRONG_BUY if sc>=8 else Sig.BUY
            return make_vote(self.N, bars, s, min(0.93,sc/10), " ".join(rs))
        return make_vote(self.N, bars, Sig.HOLD, 0.1, f"sc={sc}/10")


class RSIReversal:
    """Oversold RSI + hammer at support."""
    N = "RSI_REV"
    def run(self, bars: List[Bar]) -> Vote:
        if len(bars) < 20:
            return make_vote(self.N, bars, Sig.HOLD, 0, "short")
        b   = bars[-1]
        r7  = T.rsi(T.closes(bars), 7)
        rn  = T.last(r7) or 50
        rv  = [v for v in r7[-8:] if v is not None]
        sl  = T.swing_l(bars[:-1], 2)
        sc  = 0; rs = []
        if rn < 30:           sc+=4; rs.append(f"OS:{rn:.0f}")
        elif rn < 40:         sc+=2; rs.append(f"nearOS:{rn:.0f}")
        if len(rv)>=3 and rn > rv[-3]: sc+=2; rs.append("RSI↑")
        if b.lw > b.body*2 and b.body>0: sc+=2; rs.append("hammer")
        if sl and abs(b.c-sl)/sl*100<0.25: sc+=2; rs.append(f"@sup{sl:.4f}")
        if sc>=7:
            return make_vote(self.N, bars, Sig.BUY, min(0.85,sc/10), " ".join(rs))
        return make_vote(self.N, bars, Sig.HOLD, 0.1, f"sc={sc}/10")


class EMAStack:
    """Full EMA 9/21/55 alignment."""
    N = "EMA_STACK"
    def run(self, bars: List[Bar]) -> Vote:
        if len(bars) < 60:
            return make_vote(self.N, bars, Sig.HOLD, 0, "short")
        cl  = T.closes(bars); b = bars[-1]
        a9  = T.last(T.ema(cl, 9))  or b.c
        a21 = T.last(T.ema(cl, 21)) or b.c
        a55 = T.last(T.ema(cl, 55)) or b.c
        r14 = T.last(T.rsi(cl, 14)) or 50
        e9l = T.ema(cl, 9)
        sc  = 0; rs = []
        if b.c > a9 > a21 > a55:        sc+=5; rs.append("FULL_STACK")
        elif b.c > a9 > a21:             sc+=3; rs.append("PART_STACK")
        # EMA9 reclaim cross
        if len(e9l)>=2 and e9l[-2] and bars[-2].c<e9l[-2] and b.c>a9:
                                         sc+=3; rs.append("EMA9_reclaim")
        if r14 > 50:                     sc+=2; rs.append(f"RSI={r14:.0f}")
        if a9>a21 and (a9-a21)/a21*100>0.03: sc+=1; rs.append("good_space")
        if sc>=7:
            return make_vote(self.N, bars, Sig.BUY, min(0.88,sc/11), " ".join(rs))
        return make_vote(self.N, bars, Sig.HOLD, 0.1, f"sc={sc}/11")


class VolumeSurge:
    """Extreme volume + price action."""
    N = "VOL_SURGE"
    def run(self, bars: List[Bar]) -> Vote:
        if len(bars) < 25:
            return make_vote(self.N, bars, Sig.HOLD, 0, "short")
        cl  = T.closes(bars); b = bars[-1]
        a21 = T.last(T.ema(cl, 21)) or b.c
        av  = sum(x.v for x in bars[-21:-1])/20
        vr  = b.v/av if av>0 else 1
        a5  = sum(x.v for x in bars[-6:-1])/5
        sc  = 0; rs = []
        if vr>=3.0:   sc+=5; rs.append(f"XVol={vr:.1f}x")
        elif vr>=2.0: sc+=3; rs.append(f"SVol={vr:.1f}x")
        elif vr>=1.5: sc+=2; rs.append(f"EVol={vr:.1f}x")
        if b.bull:             sc+=2; rs.append("bull")
        if b.c > a21:          sc+=2; rs.append("abvEMA21")
        if b.body > 0.5*b.rng: sc+=1; rs.append("solid")
        if a5 > av:            sc+=1; rs.append("vol_trend↑")
        if sc>=7:
            return make_vote(self.N, bars, Sig.BUY, min(0.90,sc/11), " ".join(rs))
        return make_vote(self.N, bars, Sig.HOLD, 0.1, f"sc={sc}/11")


class MACDCross:
    """MACD crossover + histogram zero-cross."""
    N = "MACD_X"
    def run(self, bars: List[Bar]) -> Vote:
        if len(bars) < 40:
            return make_vote(self.N, bars, Sig.HOLD, 0, "short")
        cl  = T.closes(bars); b = bars[-1]
        md  = T.macd(cl, 12, 26, 9)
        h   = md["h"]; ml = md["m"]; sl_v = md["s"]
        r14 = T.last(T.rsi(cl, 14)) or 50
        if len(h) < 3:
            return make_vote(self.N, bars, Sig.HOLD, 0.1, "short_macd")
        sc  = 0; rs = []
        if ml[-2]<=sl_v[-2] and ml[-1]>sl_v[-1]:
            sc+=5; rs.append("MACD_bull_cross")
        if h[-2]<0 and h[-1]>0:
            sc+=3; rs.append("hist_zero↑")
        elif h[-1]>0 and h[-1]>h[-2]:
            sc+=2; rs.append(f"hist↑{h[-1]:.5f}")
        if ml[-1] > 0:  sc+=1; rs.append("MACD>0")
        if r14 > 50:    sc+=2; rs.append(f"RSI={r14:.0f}")
        if len(h)>=3 and h[-1]>h[-2]>h[-3]: sc+=1; rs.append("3bar_accel")
        if sc>=8:
            return make_vote(self.N, bars, Sig.BUY, min(0.88,sc/12), " ".join(rs))
        return make_vote(self.N, bars, Sig.HOLD, 0.1, f"sc={sc}/12")


class BBSqueeze:
    """Bollinger Band squeeze + breakout above upper."""
    N = "BB_SQZ"
    def run(self, bars: List[Bar]) -> Vote:
        if len(bars) < 30:
            return make_vote(self.N, bars, Sig.HOLD, 0, "short")
        cl  = T.closes(bars); b = bars[-1]
        bbd = T.bb(cl, 20, 2.0)
        u   = bbd["u"][-1]; l = bbd["l"][-1]; m = bbd["m"][-1]
        r14 = T.last(T.rsi(cl, 14)) or 50
        bw  = (u-l)/m if m and u and l else 0.02
        bws = [(bbd["u"][i]-bbd["l"][i])/bbd["m"][i]
               for i in range(-20,0)
               if bbd["u"][i] and bbd["l"][i] and bbd["m"][i]]
        bwa = sum(bws)/len(bws) if bws else 0.02
        sc  = 0; rs = []
        if bw < bwa*0.70:              sc+=3; rs.append(f"SQZ{bw:.4f}")
        if u and b.c > u:               sc+=4; rs.append(f"BB_break>{u:.4f}")
        if u and l and (b.c-l)/(u-l)>0.75: sc+=2; rs.append("%B>.75")
        if r14 > 55:                    sc+=1; rs.append(f"RSI={r14:.0f}")
        if m and b.c > m:               sc+=1; rs.append("abvMid")
        av = sum(x.v for x in bars[-20:])/20
        if b.v > av*1.4:                sc+=2; rs.append(f"vol={b.v/av:.1f}x")
        if sc>=8:
            return make_vote(self.N, bars, Sig.BUY, min(0.87,sc/13), " ".join(rs))
        return make_vote(self.N, bars, Sig.HOLD, 0.1, f"sc={sc}/13")


ALL_AGENTS = [ScalpGod, MomentumRider, VWAPSniper, StructureBreak,
              RSIReversal, EMAStack, VolumeSurge, MACDCross, BBSqueeze]


# ═══════════════════════════════════════════════════════════════
# CONSENSUS ENGINE
# ═══════════════════════════════════════════════════════════════
class Consensus:
    @staticmethod
    def _agent_weight(name: str, agent_stats: Optional[Dict[str, List[bool]]]) -> float:
        """Map an agent's recent win rate to a multiplicative weight.
        WR=0.5 → 1.0, WR=1.0 → 1.5, WR=0.0 → 0.5. Cold-start returns 1.0.
        """
        if not C.AGENT_WEIGHT_ENABLED or not agent_stats: return 1.0
        outcomes = agent_stats.get(name)
        if not outcomes or len(outcomes) < C.AGENT_WEIGHT_MIN_SAMPLES: return 1.0
        wr = sum(1 for o in outcomes if o) / len(outcomes)
        return 0.5 + wr

    def decide(self, votes: List[Vote],
               agent_stats: Optional[Dict[str, List[bool]]] = None) -> Optional[Vote]:
        buys = [v for v in votes if v.signal in (Sig.BUY, Sig.STRONG_BUY)]
        n    = len(buys)
        if n < C.MIN_VOTES:
            return None

        # Per-vote effective weight = conf × agent performance multiplier
        weights = [v.conf * self._agent_weight(v.name, agent_stats) for v in buys]
        tw      = sum(weights)
        if tw == 0: return None

        w_stop = sum(v.stop * w for v, w in zip(buys, weights)) / tw
        w_tp   = sum(v.tp   * w for v, w in zip(buys, weights)) / tw
        conf   = min(0.97, (tw / len(buys)) * (n / len(votes)))
        sig    = Sig.STRONG_BUY if n >= 6 else Sig.BUY

        weighted_tag = " [weighted]" if (C.AGENT_WEIGHT_ENABLED and agent_stats) else ""
        reason = (f"{n}/{len(votes)} agents | conf={conf:.2f}{weighted_tag} | "
                  f"[{','.join(v.name for v in buys)}]")
        return Vote("CONSENSUS", sig, round(conf, 3),
                    round(w_stop, 8), round(w_tp, 8), reason)


# ═══════════════════════════════════════════════════════════════
# PAIR SCORER
# ═══════════════════════════════════════════════════════════════
class PairScorer:
    """
    Scores each candidate pair on scalping suitability.
    Returns the highest-scoring pair.
    """
    def __init__(self, ex: Exchange):
        self.ex = ex

    def score(self, pair: str, bars: List[Bar]) -> PairRank:
        if len(bars) < 50:
            return PairRank(pair, 0, 0, 0, 50, "UNKNOWN")
        cl  = T.closes(bars); b = bars[-1]
        atr = T.last(T.atr(bars, 14)) or b.c*0.005
        ap  = atr/b.c*100 if b.c > 0 else 0
        av  = sum(x.v for x in bars[-20:])/20
        vr  = b.v/av if av > 0 else 1
        rsi = T.last(T.rsi(cl, 14)) or 50
        e21 = T.last(T.ema(cl, 21)) or b.c
        trend = "BULL" if b.c > e21 else "BEAR"

        sc = 0
        if 0.025 <= ap <= 0.10:  sc += 35   # ideal scalp volatility
        elif 0.10 < ap <= 0.14:  sc += 15
        elif ap < 0.025:          sc += 0    # dead
        if vr >= 1.5:            sc += 25
        elif vr >= 1.2:          sc += 15
        elif vr >= 1.0:          sc += 5
        if b.c > e21:            sc += 20   # above EMA21 = bullish
        if 44 <= rsi <= 70:      sc += 15
        elif 35 <= rsi < 44:     sc += 7
        if ap < 0.15:            sc += 5    # spread proxy

        return PairRank(pair, round(sc,1), round(ap,4),
                        round(vr,2), round(rsi,1), trend)

    def best(self, bars_by_pair: Dict[str,List[Bar]],
             exclude: Optional[str] = None) -> PairRank:
        ranks = []
        for pair, bars in bars_by_pair.items():
            if pair == exclude: continue
            r = self.score(pair, bars)
            ranks.append(r)
            logging.debug(f"  {pair:<14} score={r.score:5.1f} atr%={r.atr_pct:.4f} "
                          f"vol={r.vol_x:.2f}x RSI={r.rsi:.0f} {r.trend}")
        if not ranks:
            return PairRank("BTC_USDT", 50, 0.05, 1.0, 55, "BULL")
        ranks.sort(key=lambda r: r.score, reverse=True)
        top5 = " | ".join(f"{r.pair}={r.score}" for r in ranks[:5])
        logging.info(f"Pair ranking → {top5}")
        return ranks[0]


# ═══════════════════════════════════════════════════════════════
# TRADE MANAGER — 100% USDT ON EXIT
# ═══════════════════════════════════════════════════════════════
class TM:
    """
    Manages ONE open trade at a time.
    EVERY close sells back to USDT completely.
    No token is ever left held.
    """
    def __init__(self, ex: Exchange):
        self.ex       = ex
        self.open_t:  Optional[Trade] = None
        self.history: List[Trade]     = []
        self._lk      = threading.Lock()

    def open(self, pair: str, vote: Vote, usdt: float,
             votes: Optional[List[Vote]] = None) -> Optional[Trade]:
        """Open a paper/live position. If `votes` (raw per-agent votes at
        decision time) is supplied, the BUY voters are recorded on the
        Trade so per-agent performance can be tracked post-close.
        """
        with self._lk:
            if self.open_t and not self.open_t.closed:
                return None

            # Buy at market (use tp as proxy for current price in paper mode)
            market_px = (vote.stop + vote.tp) / 2  # midpoint = approx entry price
            o = self.ex.order(pair, "buy", usdt, market_px)
            if o.get("status") != "filled":
                logging.warning(f"Order failed: {o}")
                return None

            entry = o.get("price", market_px)
            units = usdt / entry if entry > 0 else 0
            risk  = entry - vote.stop
            tp1   = entry + risk * C.TP1_R
            tp2   = entry + risk * C.TP2_R
            tp3   = entry + risk * C.TP3_R

            buy_voters = [v.name for v in votes
                          if v.signal in (Sig.BUY, Sig.STRONG_BUY)] if votes else []

            t = Trade(
                id      = f"{pair}-{int(time.time()*1000)}",
                pair    = pair,
                entry   = entry,
                units   = units,
                usdt_in = usdt,
                stop    = vote.stop,
                tp1=tp1, tp2=tp2, tp3=tp3,
                trail   = vote.stop,
                peak    = entry,
                agent   = vote.reason[:60],
                initial_units = units,
                initial_risk  = risk,
                buy_voters = buy_voters,
            )
            self.open_t = t
            logging.info(f"✅ OPEN  {pair} @{entry:.6f} ${usdt:.2f} "
                         f"stop={vote.stop:.6f} tp3={tp3:.6f}")
            return t

    def update(self, price: float) -> Optional[str]:
        """Check exit conditions. Returns reason string or None.

        On the first cross of TP1: sell PARTIAL_TP1_FRAC of the remaining
        position and move stop to entry × (1 + FEE_RT × BREAKEVEN_BUFFER).
        After TP2, tighten the trail toward peak using the initial_risk
        frozen at open (the post-TP1 breakeven move makes current risk
        negative, which is why we keep the original risk basis).
        TP3 takes priority over stop/trail — a single bar crossing both
        should honor the better outcome.
        """
        with self._lk:
            t = self.open_t
            if not t or t.closed or price <= 0: return None

            t.pnl_pct = (price - t.entry) / t.entry * 100
            t.pnl     = (price - t.entry) * t.units

            if price > t.peak:
                t.peak = price

            # Partial TP1 + breakeven move (once)
            if price >= t.tp1 and not t.tp1_hit:
                self._partial_close(t, C.PARTIAL_TP1_FRAC, price, "TP1_PARTIAL")
                t.tp1_hit = True
                new_stop  = t.entry * (1 + C.FEE_RT * C.BREAKEVEN_BUFFER)
                t.stop    = max(t.stop, new_stop)
                t.trail   = max(t.trail, new_stop)

            # After TP2, tighten trail toward recent high (use initial_risk)
            if price >= t.tp2 and t.initial_risk > 0:
                t.trail = max(t.trail, t.peak - t.initial_risk * 0.35)

            # TP3 wins over stop/trail in same-bar collisions
            if price >= t.tp3: return "TP3_EXIT"
            if price <= t.stop or price <= t.trail: return "STOP_LOSS"
            if (time.time() - t.t_open) > C.MAX_HOLD_SEC: return "TIME_STOP"
            if t.pnl_pct < -1.5:                     return "EMERGENCY_STOP"
            return None

    def _partial_close(self, t: Trade, fraction: float, price: float, reason: str):
        """Sell `fraction` of remaining position, book realized PnL, update units.
        Caller must hold self._lk.
        """
        if fraction <= 0 or fraction >= 1: return
        sold_units = t.units * fraction
        sold_usdt  = t.usdt_in * fraction
        self.ex.order(t.pair, "sell", sold_usdt * (price / t.entry), price)
        gross = (price - t.entry) * sold_units
        fees  = sold_usdt * C.FEE_RT
        net   = gross - fees
        t.realized_pnl += net
        t.units   -= sold_units
        t.usdt_in -= sold_usdt
        logging.info(f"   ◐ {reason} {t.pair} @{price:.6f} "
                     f"sold {fraction*100:.0f}% "
                     f"net={net:+.4f} USDT (cumulative realized={t.realized_pnl:+.4f})")

    def close(self, price: float, reason: str) -> float:
        """Close the remaining position → sell ALL back to USDT.
        Total trade PnL = realized (from any partial fills) + final leg.
        Returns net USDT received for the final leg (caller still adds to bal).
        """
        with self._lk:
            t = self.open_t
            if not t or t.closed: return 0.0

            sell_usdt = t.usdt_in * (price / t.entry) if t.entry > 0 else t.usdt_in
            self.ex.order(t.pair, "sell", sell_usdt, price)

            gross       = (price - t.entry) * t.units
            fees        = t.usdt_in * C.FEE_RT
            final_net   = gross - fees
            total_net   = final_net + t.realized_pnl

            # pct is on ORIGINAL notional, so later sizing/daily-stop math stays consistent
            initial_usdt = t.initial_units * t.entry if t.initial_units else t.usdt_in
            pct = (total_net / initial_usdt * 100) if initial_usdt > 0 else 0.0

            t.closed  = True
            t.exit_px = price
            t.pnl     = round(total_net, 6)
            t.pnl_pct = round(pct, 4)
            t.why     = reason
            self.history.append(t)
            self.open_t = None

            e = "✅" if total_net > 0 else "❌"
            suffix = f" (realized={t.realized_pnl:+.4f} + final={final_net:+.4f})" \
                     if t.tp1_hit else ""
            logging.info(f"{e} CLOSE {t.pair} @{price:.6f} | "
                         f"{total_net:+.4f}USDT ({pct:+.4f}%) | {reason}{suffix}")
            logging.info(f"   → 100% BACK TO USDT | zero tokens held")
            # Caller-visible USDT return uses ORIGINAL cost basis so the
            # outer `bal = bal - usdt_in + usdt_out` math stays consistent
            # whether or not partials fired.
            initial_usdt_in = t.initial_units * t.entry if t.initial_units else t.usdt_in
            return initial_usdt_in + total_net

    def force_usdt(self, price: float, reason: str) -> float:
        logging.warning(f"🚨 FORCE→USDT | {reason}")
        return self.close(price, f"FORCE_{reason}")

    @staticmethod
    def record_agent_outcome(agent_stats: Dict[str, List[bool]], t: Trade):
        """Append this trade's outcome to each BUY voter's rolling window."""
        won = t.pnl > 0
        for name in t.buy_voters:
            lst = agent_stats.setdefault(name, [])
            lst.append(won)
            if len(lst) > C.AGENT_WEIGHT_WINDOW:
                lst.pop(0)

    @property
    def session_pnl(self):
        return sum(t.pnl for t in self.history)

    @property
    def win_rate(self):
        n = len(self.history)
        return sum(1 for t in self.history if t.pnl>0)/n if n else 0.0

    @property
    def last_pair(self):
        return self.history[-1].pair if self.history else None


# ═══════════════════════════════════════════════════════════════
# SIMPLE MOVING-AVERAGE STRATEGY (replaces 9-agent voting)
# ═══════════════════════════════════════════════════════════════
class SimpleMAStrategy:
    """
    Trend-follow: hold 100% BTC when close > SMA(period), else 100% USDT.

    Backtested on 6 BTC regimes spanning 2018-2026 (24+ months of bull,
    bear, and ranging markets):
        MA50 compound ROI = +553%   vs Buy & Hold = +217%
        MA50 limits 2018 drawdown to -45.6% (B&H -71.6%)
        MA50 limits 2022 drawdown to -41.2% (B&H -65.3%)
    The 9-agent indicator engine returned -0.5% over the same 24-month
    subset where this rule returned +75%. The dumb rule wins by avoiding
    catastrophic drawdowns and skipping the per-trade fee drag of
    high-frequency scalping.

    Position model: binary 100% allocated. No partial exits, no fixed
    TP/SL — the MA itself acts as a dynamic stop. ~6-15 trades/yr at 1d.
    """
    def __init__(self, ex: "Exchange", pair: str,
                 ma_period: int = 50, balance: float = 1000.0,
                 weekly_ma_period: int = 0):
        """
        ma_period         : daily SMA period (e.g. 50)
        weekly_ma_period  : if > 0, an additional weekly trend filter is
                            applied — long only when both daily close >
                            daily SMA AND weekly close > weekly SMA.
                            Backtested: W10 raises 6-regime compound from
                            +552% → +3,427%.
        """
        self.ex               = ex
        self.pair             = pair
        self.ma_period        = ma_period
        self.weekly_ma_period = weekly_ma_period
        self.balance          = balance         # USDT held
        self.units            = 0.0             # base asset held
        self.entry_px         = 0.0
        self.entry_ts         = 0
        self.in_position      = False
        self.history: List[Trade] = []
        self._lk = threading.Lock()

    # Hysteresis band around the moving average — prevents whipsaw
    # when price is within fee-thickness of the MA. Entry requires
    # price > MA * (1+BAND); exit requires price < MA * (1-BAND). The
    # dead-zone between is "hold current state."
    HYSTERESIS_BAND = 0.0025   # 0.25% — about one round-trip fee
    # Patch 1 from GODMODE_AUDIT §5: hard stop-loss as risk overlay.
    # If price falls 2.5% below entry, force exit regardless of signal.
    # Cuts P(ruin) from 18% → 10% per audit Table §8 without changing signal.
    HARD_STOP_PCT = 0.025

    def step(self, bars: List[Bar],
             weekly_bars: Optional[List[Bar]] = None) -> Optional[str]:
        """Process one bar. Returns 'BUY', 'SELL', or None.

        If weekly_ma_period > 0, the caller MUST pass the corresponding
        weekly_bars (1w-aggregated, latest bar at or before bars[-1].ts).
        Caller is responsible for executing the returned side via
        self.execute().
        """
        if len(bars) < self.ma_period: return None
        cl = T.closes(bars)
        daily_ma = T.last(T.sma(cl, self.ma_period))
        if daily_ma is None: return None
        price = bars[-1].c

        # Hard-stop overlay (Patch 1) — runs before the MA signal.
        # Forces exit if price drops below entry by HARD_STOP_PCT.
        if self.in_position and self.entry_px > 0:
            if price <= self.entry_px * (1 - self.HARD_STOP_PCT):
                return "SELL"

        # Hysteresis: asymmetric thresholds to avoid flipping on noise
        upper = daily_ma * (1 + self.HYSTERESIS_BAND)
        lower = daily_ma * (1 - self.HYSTERESIS_BAND)
        if self.in_position:
            want_long = price >= lower   # stay long until clearly below
        else:
            want_long = price > upper    # go long only when clearly above

        if self.weekly_ma_period > 0:
            if not weekly_bars or len(weekly_bars) < self.weekly_ma_period:
                return None
            wcl = T.closes(weekly_bars)
            weekly_ma = T.last(T.sma(wcl, self.weekly_ma_period))
            if weekly_ma is None: return None
            w_price = weekly_bars[-1].c
            w_upper = weekly_ma * (1 + self.HYSTERESIS_BAND)
            w_lower = weekly_ma * (1 - self.HYSTERESIS_BAND)
            if self.in_position:
                weekly_ok = w_price >= w_lower
            else:
                weekly_ok = w_price > w_upper
            want_long = want_long and weekly_ok

        if want_long and not self.in_position:    return "BUY"
        if (not want_long) and self.in_position:  return "SELL"
        return None

    def execute(self, side: str, price: float, ts: int):
        """Apply a BUY or SELL fill at the given price (paper or live —
        delegated to self.ex.order which already handles both)."""
        with self._lk:
            if side == "BUY" and not self.in_position:
                # Spend full balance, pay half fee on entry
                cost   = self.balance * (1 - C.FEE_RT / 2)
                self.units      = cost / price
                self.entry_px   = price
                self.entry_ts   = ts
                self.balance    = 0.0
                self.in_position = True
                self.ex.order(self.pair, "buy", cost, price)
                logging.info(f"📈 MA-BUY  {self.pair} @{price:.2f} units={self.units:.6f}")
                try:
                    from telegram_alerts import notify_buy
                    notify_buy(self.pair, price, self.units)
                except Exception:
                    pass
            elif side == "SELL" and self.in_position:
                gross    = self.units * price
                proceeds = gross * (1 - C.FEE_RT / 2)
                pnl      = proceeds - (self.entry_px * self.units)
                pnl_pct  = (price - self.entry_px) / self.entry_px * 100 - C.FEE_RT * 100
                t = Trade(
                    id      = f"{self.pair}-MA-{ts}",
                    pair    = self.pair,
                    entry   = self.entry_px,
                    units   = self.units,
                    usdt_in = self.entry_px * self.units,
                    stop=0, tp1=0, tp2=0, tp3=0,
                    trail=0, peak=0,
                    t_open  = self.entry_ts,
                    agent   = f"MA{self.ma_period}",
                    closed  = True,
                    exit_px = price,
                    pnl     = round(pnl, 6),
                    pnl_pct = round(pnl_pct, 4),
                    why     = "MA_FLIP",
                )
                self.history.append(t)
                self.balance     = proceeds
                self.units       = 0.0
                self.in_position = False
                self.ex.order(self.pair, "sell", proceeds, price)
                e = "✅" if pnl > 0 else "❌"
                logging.info(f"{e} MA-SELL {self.pair} @{price:.2f} "
                             f"pnl={pnl:+.4f} ({pnl_pct:+.4f}%)")
                try:
                    from telegram_alerts import notify_sell
                    notify_sell(self.pair, price, pnl, pnl_pct)
                except Exception:
                    pass

    @property
    def equity(self) -> float:
        """Current total value (USDT + units × last_price). Caller passes price."""
        return self.balance  # caller must mark-to-market for live equity

    def mark_to_market(self, price: float) -> float:
        return self.balance + self.units * price

    @property
    def session_pnl(self) -> float:
        return sum(t.pnl for t in self.history)


# ═══════════════════════════════════════════════════════════════
# VOTE ENSEMBLE STRATEGY (production-grade of max_edge.py research)
# ═══════════════════════════════════════════════════════════════
class VoteEnsembleStrategy:
    """
    Long-only crypto strategy built from three independent signals:

      A. MA20+W5       — daily SMA20 + weekly SMA5 trend filter, with
                          0.25% hysteresis band around each MA.
      B. Donchian-20   — 20-day entry high / 10-day exit low.
      C. BTC gate      — BTC's own MA50+W5 must also be LONG.

    Take a position only when **at least 2 of 3** signals agree.

    Backtested over 9-pair × 7-year portfolio walk-forward:
      Sharpe 2.41 · MC percentile 89% vs shuffled returns ·
      4 / 5 rolling out-of-sample windows beat equal-weight buy-and-hold ·
      Portfolio compound ROI +48,785% over 2,100 days.

    See max_edge.py + MAX_EDGE_RESULTS for methodology. Used by the
    `--strategy vote` flag in run.py.
    """

    HYSTERESIS_BAND  = 0.0025
    MA_PERIOD        = 20
    WEEKLY_PERIOD    = 5
    DONCHIAN_ENTRY   = 20
    DONCHIAN_EXIT    = 10
    BTC_MA_PERIOD    = 50
    BTC_WEEKLY       = 5

    def __init__(self, ex: "Exchange", pair: str, balance: float = 1000.0):
        self.ex          = ex
        self.pair        = pair
        self.balance     = balance
        self.units       = 0.0
        self.entry_px    = 0.0
        self.entry_ts    = 0
        self.in_position = False
        self.history: List[Trade] = []
        self._lk = threading.Lock()
        # BTC bars cache — refreshed on each step() call
        self._btc_bars_cache: List[Bar] = []
        self._btc_cache_ts = 0

    # ── individual signals ──────────────────────────────────────────
    @staticmethod
    def _weekly(bars: List[Bar], per: int = 7) -> List[Bar]:
        out = []
        for i in range(0, len(bars), per):
            c = bars[i:i + per]
            if not c: continue
            out.append(Bar(c[0].ts, c[0].o, max(x.h for x in c),
                           min(x.l for x in c), c[-1].c, sum(x.v for x in c)))
        return out

    @classmethod
    def _ma_weekly_signal(cls, bars: List[Bar], ma_p: int, weekly_p: int,
                          in_pos: bool, hyst: float = 0.0025) -> bool:
        """MA + weekly filter with hysteresis. Same logic for asset MA and
        for the BTC gate — both use this method."""
        if len(bars) < max(ma_p, weekly_p * 7 + 1):
            return False
        closes = [b.c for b in bars]
        m = T.last(T.sma(closes, ma_p))
        if m is None: return False
        px = bars[-1].c
        upper = m * (1 + hyst); lower = m * (1 - hyst)
        d_ok = (px >= lower) if in_pos else (px > upper)
        if weekly_p == 0: return d_ok
        weekly = cls._weekly(bars)
        if len(weekly) < weekly_p: return False
        wm = T.last(T.sma([b.c for b in weekly], weekly_p))
        if wm is None: return False
        w_px = weekly[-1].c
        w_u = wm * (1 + hyst); w_l = wm * (1 - hyst)
        w_ok = (w_px >= w_l) if in_pos else (w_px > w_u)
        return d_ok and w_ok

    @classmethod
    def _donchian_signal(cls, bars: List[Bar], in_pos: bool) -> bool:
        if len(bars) <= cls.DONCHIAN_ENTRY: return False
        highs = [b.h for b in bars]
        lows  = [b.l for b in bars]
        px = bars[-1].c
        if in_pos:
            return px > min(lows[-cls.DONCHIAN_EXIT - 1:-1])
        return px > max(highs[-cls.DONCHIAN_ENTRY - 1:-1])

    def _btc_signal(self) -> bool:
        """Fetch (and cache for ~60s) BTC bars and return its MA50+W5 state."""
        now = int(time.time())
        if now - self._btc_cache_ts > 60 or not self._btc_bars_cache:
            self._btc_bars_cache = self.ex.fetch_bars(
                "BTC_USDT",
                limit=max(self.BTC_MA_PERIOD + 50, self.BTC_WEEKLY * 7 + 50),
            )
            self._btc_cache_ts = now
        if not self._btc_bars_cache:
            return False   # fail-closed if BTC fetch fails
        # Standalone evaluation — BTC's own position state doesn't matter
        # for the gate; we just want to know if its rule says "LONG now".
        return self._ma_weekly_signal(
            self._btc_bars_cache,
            self.BTC_MA_PERIOD, self.BTC_WEEKLY,
            in_pos=False, hyst=self.HYSTERESIS_BAND,
        )

    # Patch 1 from GODMODE_AUDIT §5 — hard stop-loss overlay.
    # 2.5% below entry forces exit regardless of vote signal. Cuts P(ruin)
    # 18% → 10% without changing signal logic.
    HARD_STOP_PCT = 0.025

    # ── the vote ────────────────────────────────────────────────────
    def step(self, bars: List[Bar]) -> Optional[str]:
        """Return 'BUY', 'SELL', or None given the latest bars.

        Caller is responsible for calling execute(side, price, ts) with the
        fill information. This keeps the strategy testable under
        run_with_returns-style harnesses.
        """
        if len(bars) < max(self.MA_PERIOD, self.WEEKLY_PERIOD * 7 + 1,
                            self.DONCHIAN_ENTRY + 1):
            return None

        # Hard-stop overlay (Patch 1) — runs before the vote.
        if self.in_position and self.entry_px > 0:
            if bars[-1].c <= self.entry_px * (1 - self.HARD_STOP_PCT):
                return "SELL"

        a = self._ma_weekly_signal(bars, self.MA_PERIOD, self.WEEKLY_PERIOD,
                                   self.in_position, self.HYSTERESIS_BAND)
        b = self._donchian_signal(bars, self.in_position)
        c = self._btc_signal()
        votes = int(bool(a)) + int(bool(b)) + int(bool(c))
        want_long = votes >= 2

        if want_long and not self.in_position:   return "BUY"
        if (not want_long) and self.in_position: return "SELL"
        return None

    # ── execution (mirror SimpleMAStrategy for drop-in compatibility) ──
    def execute(self, side: str, price: float, ts: int):
        with self._lk:
            if side == "BUY" and not self.in_position:
                cost = self.balance * (1 - C.FEE_RT / 2)
                self.units      = cost / price
                self.entry_px   = price
                self.entry_ts   = ts
                self.balance    = 0.0
                self.in_position = True
                self.ex.order(self.pair, "buy", cost, price)
                logging.info(f"🗳  VOTE-BUY  {self.pair} @{price:.2f} units={self.units:.6f}")
                try:
                    from telegram_alerts import notify_buy
                    notify_buy(self.pair, price, self.units)
                except Exception:
                    pass
            elif side == "SELL" and self.in_position:
                gross    = self.units * price
                proceeds = gross * (1 - C.FEE_RT / 2)
                pnl      = proceeds - (self.entry_px * self.units)
                pnl_pct  = (price - self.entry_px) / self.entry_px * 100 - C.FEE_RT * 100
                t = Trade(
                    id=f"{self.pair}-VOTE-{ts}",
                    pair=self.pair, entry=self.entry_px, units=self.units,
                    usdt_in=self.entry_px * self.units,
                    stop=0, tp1=0, tp2=0, tp3=0, trail=0, peak=0,
                    t_open=self.entry_ts, agent="VOTE", closed=True,
                    exit_px=price, pnl=round(pnl, 6),
                    pnl_pct=round(pnl_pct, 4), why="VOTE_FLIP",
                )
                self.history.append(t)
                self.balance     = proceeds
                self.units       = 0.0
                self.in_position = False
                self.ex.order(self.pair, "sell", proceeds, price)
                e = "✅" if pnl > 0 else "❌"
                logging.info(f"{e} VOTE-SELL {self.pair} @{price:.2f} "
                             f"pnl={pnl:+.4f} ({pnl_pct:+.4f}%)")
                try:
                    from telegram_alerts import notify_sell
                    notify_sell(self.pair, price, pnl, pnl_pct)
                except Exception:
                    pass

    def mark_to_market(self, price: float) -> float:
        return self.balance + self.units * price

    @property
    def session_pnl(self) -> float:
        return sum(t.pnl for t in self.history)


# ═══════════════════════════════════════════════════════════════
# GODS LEVEL ENGINE
# ═══════════════════════════════════════════════════════════════
class GodsEngine:
    """
    SINGLE PAIR FOCUS ENGINE:
      Pick best pair → all 10 agents scalp it → lose? → USDT → next pair.
      You are always 100% USDT between trades.
    """

    def __init__(self):
        logging.basicConfig(
            level  = logging.INFO,
            format = "%(asctime)s | %(levelname)-7s | %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("gods_engine.log"),
            ]
        )
        self.ex      = Exchange()
        self.scorer  = PairScorer(self.ex)
        self.tm      = TM(self.ex)
        self.con     = Consensus()
        self.agents  = [A() for A in ALL_AGENTS]

        self.balance     = C.BALANCE
        self.sess_start  = C.BALANCE
        self.active_pair: Optional[str] = None
        self.active_rank: Optional[PairRank] = None
        self.bars_cache: Dict[str,List[Bar]] = {}

        # Per-pair tracking
        self.pair_losses: Dict[str,int]   = {}
        self.pair_pnl:    Dict[str,float] = {}
        self.pair_switches = 0
        self.loop_n  = 0
        self._start  = time.time()
        self.running = False

        mode = "🔴 LIVE" if C.LIVE_MODE else "🟡 PAPER"
        logging.info("="*72)
        logging.info(f"  GODS LEVEL ENGINE — {mode}")
        logging.info(f"  Balance=${C.BALANCE:.2f} USDT | Candidates={len(C.PAIRS)} pairs")
        logging.info(f"  MinVotes={C.MIN_VOTES}/9 | SwitchTrigger="
                     f"{C.PAIR_LOSSES_MAX}losses or {C.PAIR_PNL_FLOOR*100:.1f}%PnL")
        logging.info(f"  SPOT ONLY · ZERO LEVERAGE · ALL EXITS → USDT")
        logging.info("="*72)

    # ── helpers ──
    def _refresh_bars(self, seed_fn) -> Dict[str,List[Bar]]:
        """Fetch real candles when LIVE_MODE or USE_REAL_DATA; else simulate.
        In live mode, a fetch failure is fatal (no silent sim fallback on real money).
        """
        out = {}
        use_real = C.LIVE_MODE or C.USE_REAL_DATA
        for pair in C.PAIRS:
            if use_real:
                b = self.ex.fetch_bars(pair, C.CANDLES)
                if not b:
                    if C.LIVE_MODE:
                        raise RuntimeError(
                            f"fetch_bars({pair}) empty in LIVE_MODE — aborting "
                            f"rather than trading real money on synthetic data")
                    b = self.ex.sim_bars(pair, C.CANDLES, seed_fn(pair))
            else:
                b = self.ex.sim_bars(pair, C.CANDLES, seed_fn(pair))
            out[pair] = b
        return out

    def _pick_pair(self, exclude=None, seed_fn=None):
        sf = seed_fn or (lambda p: abs(hash(p)) % 99999)
        self.bars_cache = self._refresh_bars(sf)
        rank = self.scorer.best(self.bars_cache, exclude=exclude)
        self.active_pair = rank.pair
        self.active_rank = rank
        logging.info(f"📌 ACTIVE PAIR → {rank.pair} | score={rank.score} | "
                     f"ATR%={rank.atr_pct:.4f} vol={rank.vol_x:.2f}x "
                     f"RSI={rank.rsi:.0f} {rank.trend}")

    def _pos_size(self, conf: float) -> float:
        b    = self.balance * C.MAX_POS_PCT * conf
        b    = min(b, self.balance * C.MAX_POS_PCT)
        b    = max(b, self.balance * 0.01)
        losses = self.pair_losses.get(self.active_pair, 0)
        if losses >= 2: b *= 0.50
        return round(b, 2)

    def _record(self, pair: str, pnl: float):
        self.pair_pnl[pair]    = self.pair_pnl.get(pair, 0.0) + pnl
        if pnl < 0:
            self.pair_losses[pair] = self.pair_losses.get(pair, 0) + 1
        else:
            self.pair_losses[pair] = 0

    def _need_switch(self, pair: str) -> Tuple[bool, str]:
        l  = self.pair_losses.get(pair, 0)
        pp = self.pair_pnl.get(pair, 0.0)
        pf = pp / C.BALANCE
        if l >= C.PAIR_LOSSES_MAX:
            return True, f"{l} consecutive losses"
        if pf <= C.PAIR_PNL_FLOOR:
            return True, f"pair PnL {pf*100:.2f}% ≤ {C.PAIR_PNL_FLOOR*100:.1f}%"
        return False, ""

    def _switch_pair(self, old: str, reason: str, seed_fn):
        logging.warning(f"⚡ PAIR SWITCH | {old} → ? | {reason}")
        # Ensure flat before switch
        if self.tm.open_t and not self.tm.open_t.closed:
            bars = self.bars_cache.get(old, [])
            price = bars[-1].c if bars else 0.0
            if price > 0:
                usdt = self.tm.force_usdt(price, f"SWITCH:{reason}")
                t    = self.tm.history[-1]
                self.balance = self.balance - t.usdt_in + usdt
        # Reset pair state
        self.pair_losses[old] = 0
        self.pair_pnl[old]    = 0.0
        self.pair_switches   += 1
        self._pick_pair(exclude=old, seed_fn=seed_fn)
        logging.info(f"✅ NOW TRADING → {self.active_pair} | Balance=${self.balance:.4f} USDT")

    def _status(self):
        up  = (time.time()-self._start)/3600
        tr  = self.tm.history
        op  = self.tm.open_t
        dloss = (self.sess_start-self.balance)/self.sess_start*100
        print("\n"+"═"*72)
        print(f"  ⚡ GODS ENGINE | Loop:{self.loop_n} Up:{up:.2f}h "
              f"{'🔴LIVE' if C.LIVE_MODE else '🟡PAPER'}")
        print(f"  Balance: ${self.balance:.4f}  Start: ${C.BALANCE:.2f}  "
              f"PnL: {self.tm.session_pnl:+.4f} USDT")
        print(f"  Trades:  {len(tr)} | WR: {self.tm.win_rate*100:.1f}% | "
              f"Switches: {self.pair_switches} | DailyLoss: {dloss:.2f}%/{C.DAILY_STOP*100:.1f}%")
        print(f"  Pair:    {self.active_pair} | "
              f"Losses: {self.pair_losses.get(self.active_pair,0)} | "
              f"PairPnL: {self.pair_pnl.get(self.active_pair,0):+.4f} USDT")
        if op and not op.closed:
            bars  = self.bars_cache.get(op.pair,[])
            px    = bars[-1].c if bars else op.entry
            ep    = (px-op.entry)/op.entry*100
            held  = (time.time()-op.t_open)/60
            print(f"  OPEN:  {op.pair} @{op.entry:.6f} now={px:.6f} "
                  f"pnl={ep:+.4f}% held={held:.1f}m")
        if tr:
            print("  LAST 5:")
            for t in tr[-5:]:
                e = "✅" if t.pnl>0 else "❌"
                print(f"    {e} {t.pair:<12} {t.pnl:+.4f}USDT "
                      f"({t.pnl_pct:+.4f}%) | {t.why}")
        print("═"*72+"\n")

    # ── LIVE MODE ──
    def start(self):
        self.running = True
        self._pick_pair(seed_fn=lambda p: int(time.time()))
        logging.info("🚀 24/7 ENGINE STARTED")
        try:
            while self.running:
                self.loop_n += 1
                try:
                    self._live_cycle()
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logging.error(f"Cycle error: {e}", exc_info=True)
                if self.loop_n % 20 == 0:
                    self._status()
                time.sleep(C.LOOP_SLEEP)
        except KeyboardInterrupt:
            logging.info("⛔ Manual stop")
        finally:
            self.shutdown()

    def _live_cycle(self):
        pair = self.active_pair
        sf   = lambda p: int(time.time())
        self.bars_cache = self._refresh_bars(sf)
        bars  = self.bars_cache.get(pair, [])
        if not bars: return
        price = bars[-1].c

        # Daily stop check
        dl = (self.sess_start - self.balance)/self.sess_start
        if dl >= C.DAILY_STOP:
            logging.critical(f"🛑 DAILY STOP {dl*100:.2f}%")
            self.running = False; return

        # Manage open trade
        if self.tm.open_t and not self.tm.open_t.closed:
            why = self.tm.update(price)
            if why:
                usdt = self.tm.close(price, why)
                t    = self.tm.history[-1]
                self.balance = self.balance - t.usdt_in + usdt
                self._record(pair, t.pnl)
                sw, rs = self._need_switch(pair)
                if sw: self._switch_pair(pair, rs, sf)
            return

        # Re-score pair every ~10 min if no trade
        if self.loop_n % 60 == 0:
            r2 = self.scorer.best(self.bars_cache)
            if r2.pair != pair and r2.score > (self.active_rank.score if self.active_rank else 0) + 15:
                logging.info(f"Better pair found: {r2.pair} ({r2.score})")
                self.active_pair = r2.pair; self.active_rank = r2
                return

        # Run agents
        votes    = [ag.run(bars) for ag in self.agents]
        buy_v    = sum(1 for v in votes if v.signal in (Sig.BUY, Sig.STRONG_BUY))
        decision = self.con.decide(votes)
        if not decision: return

        sz = self._pos_size(decision.conf)
        if sz < 5: return
        risk = price - decision.stop
        rew  = decision.tp - price
        if risk <= 0 or rew/risk < 1.0 or rew/price*100 < C.FEE_RT*100: return

        t = self.tm.open(pair, decision, sz)
        if t:
            self.balance -= sz
            logging.info(f"🎯 ENTRY {pair} ${sz:.2f} | {buy_v}/9 votes")

    def shutdown(self):
        self.running = False
        bars  = self.bars_cache.get(self.active_pair or "BTC_USDT", [])
        price = bars[-1].c if bars else 0.0
        if self.tm.open_t and not self.tm.open_t.closed and price > 0:
            usdt = self.tm.force_usdt(price, "SHUTDOWN")
            t    = self.tm.history[-1]
            self.balance = self.balance - t.usdt_in + usdt
        tr = self.tm.history
        print("\n"+"═"*72)
        print("  FINAL REPORT")
        print("═"*72)
        print(f"  Trades:     {len(tr)}")
        print(f"  Win rate:   {self.tm.win_rate*100:.1f}%")
        print(f"  Net PnL:    {self.tm.session_pnl:+.4f} USDT")
        print(f"  Balance:    ${self.balance:.4f} USDT")
        print(f"  Switches:   {self.pair_switches}")
        print(f"  Runtime:    {(time.time()-self._start)/3600:.2f}h")
        print(f"  ✅ ALL FUNDS IN USDT — ZERO TOKENS HELD")
        print("═"*72)
        self._save()

    def _save(self):
        data = {
            "time": datetime.now(timezone.utc).isoformat(),
            "live": C.LIVE_MODE,
            "exchange": C.EXCHANGE,
            "start": C.BALANCE,
            "end": self.balance,
            "pnl": self.tm.session_pnl,
            "trades": len(self.tm.history),
            "win_rate": round(self.tm.win_rate, 4),
            "switches": self.pair_switches,
            "history": [
                {"pair":t.pair,"entry":t.entry,"exit":t.exit_px,
                 "pnl":t.pnl,"pnl_pct":t.pnl_pct,"why":t.why}
                for t in self.tm.history
            ]
        }
        fname = f"gods_log_{int(time.time())}.json"
        with open(fname,"w") as f: json.dump(data,f,indent=2)
        logging.info(f"📝 Saved: {fname}")


# ═══════════════════════════════════════════════════════════════
# SIMULATION — full paper test, no API needed
# ═══════════════════════════════════════════════════════════════
def run_simulation(n_loops: int = 300):
    """
    Paper simulation. Uses varied seeds so every loop sees
    a different market scenario — guarantees signal diversity
    and proves the full trade lifecycle works.
    """
    print("="*72)
    print(f"  GODS LEVEL ENGINE — PAPER SIMULATION ({n_loops} loops)")
    print(f"  Single pair · 10 agents · USDT-only exits · Auto pair switch")
    print("="*72+"\n")

    engine  = GodsEngine()
    ex      = engine.ex
    agents  = engine.agents
    con     = engine.con

    # unique seed per (loop, pair) → genuinely different markets each loop
    def seed(pair, loop): return loop * 1000 + abs(hash(pair)) % 1000

    # Initial pair selection
    all_bars = {p: ex.sim_bars(p, C.CANDLES, seed(p,0)) for p in C.PAIRS}
    rank = engine.scorer.best(all_bars)
    engine.active_pair = rank.pair
    engine.active_rank = rank
    engine.bars_cache  = all_bars
    print(f"  Starting pair: {rank.pair} (score={rank.score})\n")

    loop_ts  = {}   # track last bar ts per pair to simulate candle close

    for loop in range(n_loops):
        engine.loop_n = loop
        pair          = engine.active_pair

        # Each loop = one new 1-minute candle → use loop as seed component
        sf   = lambda p, _loop=loop: seed(p, _loop)
        bars = ex.sim_bars(pair, C.CANDLES, seed(pair, loop))
        engine.bars_cache[pair] = bars
        price = bars[-1].c

        # Daily stop
        dl = (engine.sess_start - engine.balance)/engine.sess_start
        if dl >= C.DAILY_STOP:
            print(f"\n🛑 Daily stop {dl*100:.2f}% at loop {loop}")
            break

        # Manage open trade
        if engine.tm.open_t and not engine.tm.open_t.closed:
            why = engine.tm.update(price)
            if why:
                usdt = engine.tm.close(price, why)
                t    = engine.tm.history[-1]
                engine.balance = engine.balance - t.usdt_in + usdt
                engine._record(pair, t.pnl)
                e = "✅" if t.pnl > 0 else "❌"
                print(f"L{loop:4d} | {e} CLOSED  {pair:<12} | "
                      f"{t.pnl:+.6f}USDT ({t.pnl_pct:+.4f}%) | "
                      f"{why:<18} | bal=${engine.balance:.4f}")
                sw, rs = engine._need_switch(pair)
                if sw:
                    all_bars2 = {p: ex.sim_bars(p, C.CANDLES, seed(p,loop+1))
                                 for p in C.PAIRS}
                    engine.bars_cache = all_bars2
                    old = pair
                    engine._switch_pair(pair, rs, lambda p, _l=loop+1: seed(p,_l))
                    print(f"L{loop:4d} | ⚡ SWITCH   {old} → {engine.active_pair} | {rs}")
                    pair = engine.active_pair
            continue

        # Re-score pairs every 30 loops (simulate periodic evaluation)
        if loop > 0 and loop % 30 == 0:
            all_bars2 = {p: ex.sim_bars(p, C.CANDLES, seed(p,loop))
                         for p in C.PAIRS}
            engine.bars_cache = all_bars2
            r2 = engine.scorer.best(all_bars2, exclude=None)
            if r2.pair != engine.active_pair and r2.score > (engine.active_rank.score if engine.active_rank else 0) + 12:
                old = engine.active_pair
                engine.active_pair  = r2.pair
                engine.active_rank  = r2
                bars                = all_bars2[r2.pair]
                engine.bars_cache   = all_bars2
                print(f"L{loop:4d} | 🔄 UPGRADE  {old} → {r2.pair} (score {engine.active_rank.score if engine.active_rank else '?'}→{r2.score})")
                pair  = engine.active_pair
                price = bars[-1].c

        # Run all 9 agents
        votes    = [ag.run(bars) for ag in agents]
        buy_v    = sum(1 for v in votes if v.signal in (Sig.BUY, Sig.STRONG_BUY))
        decision = con.decide(votes)

        if decision:
            sz   = engine._pos_size(decision.conf)
            if sz >= 5:
                risk = price - decision.stop
                rew  = decision.tp - price
                ok   = (risk > 0 and
                        rew/risk >= 1.0 and
                        rew/price*100 > C.FEE_RT*100)
                if ok:
                    t = engine.tm.open(pair, decision, sz)
                    if t:
                        engine.balance -= sz
                        print(f"L{loop:4d} | 🎯 ENTERED  {pair:<12} @ {price:>12.4f} | "
                              f"${sz:6.2f} | {buy_v}/9 votes | "
                              f"conf={decision.conf:.2f} | stop={decision.stop:.4f} tp={decision.tp:.4f}")

        # Status every 50 loops
        if loop % 50 == 0 and loop > 0:
            print(f"\n  ── L{loop} | Pair:{pair:<12} | Bal:${engine.balance:.4f} | "
                  f"PnL:{engine.tm.session_pnl:+.4f} | "
                  f"Trades:{len(engine.tm.history)} | "
                  f"WR:{engine.tm.win_rate*100:.0f}% ──\n")

        time.sleep(C.SIM_SLEEP)

    # Force close any remaining position
    if engine.tm.open_t and not engine.tm.open_t.closed:
        bars  = engine.bars_cache.get(engine.active_pair, [])
        price = bars[-1].c if bars else 0.0
        if price > 0:
            usdt = engine.tm.force_usdt(price, "SIM_END")
            t    = engine.tm.history[-1]
            engine.balance = engine.balance - t.usdt_in + usdt

    # ── FINAL REPORT ──
    engine.shutdown()
    trades = engine.tm.history
    if trades:
        wins   = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        aw = sum(t.pnl for t in wins)/len(wins)   if wins   else 0
        al = sum(t.pnl for t in losses)/len(losses) if losses else 0
        pf = abs(aw/al) if al != 0 else float("inf")
        pairs_used = sorted(set(t.pair for t in trades))

        print(f"\n  DETAILED:")
        print(f"  Avg win:       ${aw:+.4f}")
        print(f"  Avg loss:      ${al:+.4f}")
        print(f"  Profit factor: {pf:.2f}")
        print(f"  Pairs traded:  {', '.join(pairs_used)}")

        by_pair: Dict[str,list] = {}
        for t in trades: by_pair.setdefault(t.pair,[]).append(t)
        print(f"\n  PER-PAIR:")
        for p, ts in sorted(by_pair.items()):
            w  = sum(1 for t in ts if t.pnl>0)
            pp = sum(t.pnl for t in ts)
            print(f"    {p:<14} {len(ts):3d} trades | "
                  f"wr={w/len(ts)*100:.0f}% | pnl={pp:+.4f} USDT")

    print(f"\n  ✅ SIMULATION COMPLETE — ALL FUNDS IN USDT")


# ═══════════════════════════════════════════════════════════════
# ENTRY
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║   GODS LEVEL ENGINE — SINGLE PAIR FOCUS · 10 AGENTS · USDT ONLY            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  • Scores all pairs → trades ONLY the best one                              ║
║  • All 10 agents scalp that pair simultaneously                             ║
║  • Pair losing? → EXIT ALL → 100% USDT → find next best pair               ║
║  • Zero tokens ever held between trades                                     ║
║                                                                              ║
║  ⚠  Educational / simulation only. Crypto = substantial risk of loss.       ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    m = input(
        "[1] Paper simulation (no API needed)\n"
        "[2] Live trading (API keys + set LIVE_MODE=True)\n"
        "[Q] Quit\n> "
    ).strip().upper()

    if m == "1":
        n = input("Simulation loops [default 300]: ").strip()
        run_simulation(int(n) if n.isdigit() else 300)

    elif m == "2":
        if not C.LIVE_MODE:
            print("❌ Set LIVE_MODE=True in the config first.")
        elif not C.GIO_KEY:
            print("❌ Set GATEIO_API_KEY in environment.")
        else:
            c = input("Type CONFIRM to start live trading: ").strip()
            if c == "CONFIRM":
                e = GodsEngine()
                try:    e.start()
                except KeyboardInterrupt: e.shutdown()
    else:
        print("Bye.")
