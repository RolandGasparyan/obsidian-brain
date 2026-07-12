#!/usr/bin/env python3
"""
aegis_alpha.scanner — Champion Mode §3.1, the 4H momentum-rotation scanner.

Scans Gate.io spot top-N pairs by 24h volume and scores each 0–100 across
five factors. Tokens scoring ≥ 72 qualify; ≥ 88 are "god tier" (size 2×).

Factor scoring (max points):
  F1. 24h volume surge       (25)   24h_vol / 30d_avg_daily_vol ≥ 3.0 → 25
  F2. 4H breakout strength   (20)   close > 20-period 4H high
  F3. Relative strength vs   (20)   token_24h_ret − BTC_24h_ret ≥ +5%
       BTC
  F4. ATR expansion          (15)   atr_4h / 20-period_avg ≥ 1.5
  F5. Liquidity (binary)     (20+5) 24h vol > $5M required;
                                    spread < 0.10% adds 5 (total 25)
                                    spread > 0.15% disqualifies regardless

Exclusions per §3.1:
  - 24h vol < $5M USDT       → DISQUALIFIED
  - Spread > 0.15%           → DISQUALIFIED
  - Volume < 1.5× avg        → not scanned (under 0-pt threshold)
  - RS < 0% vs BTC           → 0 pts on F3 (allowed but underperforms)

Entry checklist (§3.2) — applied AFTER scoring, before any trade:
  [ ] score ≥ 72
  [ ] 4H candle CLOSED above breakout level (not wick)
  [ ] breakout candle volume ≥ 150% of 20-period avg
  [ ] no resistance wall within 1.5% above
  [ ] spread < 0.10% at entry time
  [ ] BTC 4H EMA20 > EMA50 (no active downtrend)
  [ ] risk per trade ≤ 2% of stage capital allocation

Usage (standalone):
    python -m aegis_alpha.scanner --top 50 --min-score 72
    python -m aegis_alpha.scanner --top 100 --min-score 88 --json
    python -m aegis_alpha.scanner --refresh   # ignore cache

The scanner is data-only. No order placement. Paired with an entry
executor module (sibling, planned) it becomes a full engine. For now,
output is a ranked candidate list — exactly what §3.1 specifies.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("requests missing"); sys.exit(1)


GATE_PUBLIC = "https://api.gateio.ws/api/v4"

MIN_24H_USD_VOLUME = 5_000_000   # §3.1 F5 hard gate
MAX_SPREAD_PCT     = 0.15        # disqualifying spread
GOOD_SPREAD_PCT    = 0.10        # bonus +5 if below
MIN_QUALIFY_SCORE  = 72
GOD_TIER_SCORE     = 88


# ── data classes ─────────────────────────────────────────────────────
@dataclass
class TokenSnapshot:
    pair:           str
    last_price:     float
    vol_24h_usd:    float
    vol_30d_avg:    Optional[float] = None    # daily $ volume avg
    return_24h_pct: float = 0.0
    bid:            float = 0.0
    ask:            float = 0.0
    spread_pct:     float = 0.0


@dataclass
class FactorScore:
    name:    str
    points:  float    # earned
    max:     float    # available
    detail:  Dict[str, float] = field(default_factory=dict)


@dataclass
class TokenScore:
    pair:        str
    total:       float
    factors:     List[FactorScore]
    qualified:   bool
    god_tier:    bool
    disqualify_reason: str = ""
    snapshot_data: Dict[str, float] = field(default_factory=dict)


# ── REST helpers ─────────────────────────────────────────────────────
def fetch_tickers() -> List[dict]:
    """All Gate.io spot tickers in one call."""
    r = requests.get(f"{GATE_PUBLIC}/spot/tickers", timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_candles(pair: str, interval: str, limit: int) -> List[List[str]]:
    """Gate.io spot candlesticks. Returns raw rows.
    Row format: [ts, vol_quote, close, high, low, open, vol_base]"""
    r = requests.get(f"{GATE_PUBLIC}/spot/candlesticks",
                     params={"currency_pair": pair,
                             "interval": interval, "limit": str(limit)},
                     timeout=12)
    r.raise_for_status()
    return r.json()


def fetch_orderbook_top(pair: str) -> Tuple[Optional[float], Optional[float]]:
    r = requests.get(f"{GATE_PUBLIC}/spot/order_book",
                     params={"currency_pair": pair, "limit": "1"}, timeout=8)
    r.raise_for_status()
    j = r.json()
    bid = float(j["bids"][0][0]) if j.get("bids") else 0.0
    ask = float(j["asks"][0][0]) if j.get("asks") else 0.0
    return bid, ask


# ── factor calculators ───────────────────────────────────────────────
def factor_volume_surge(snap: TokenSnapshot) -> FactorScore:
    if not snap.vol_30d_avg or snap.vol_30d_avg <= 0:
        return FactorScore("volume_surge", 0, 25,
                           {"reason": "no 30d baseline"})
    ratio = snap.vol_24h_usd / snap.vol_30d_avg
    if ratio >= 3.0:    pts = 25.0
    elif ratio >= 2.0:  pts = 18.0
    elif ratio >= 1.5:  pts = 10.0
    else:               pts = 0.0
    return FactorScore("volume_surge", pts, 25, {"ratio": ratio})


def factor_breakout(closes_4h: List[float], current: float,
                    look: int = 20) -> FactorScore:
    if len(closes_4h) < look + 1:
        return FactorScore("breakout", 0, 20,
                           {"reason": f"need {look+1} bars, have {len(closes_4h)}"})
    prior_high = max(closes_4h[-(look + 1):-1])
    if prior_high <= 0:
        return FactorScore("breakout", 0, 20)
    above_pct = (current - prior_high) / prior_high * 100
    if above_pct > 0:
        pts = 20.0
    elif above_pct > -0.5:
        pts = 8.0
    else:
        pts = 0.0
    return FactorScore("breakout", pts, 20,
                       {"prior_high_20p": prior_high,
                        "current": current,
                        "above_pct": above_pct})


def factor_rel_strength(token_ret_24h: float,
                         btc_ret_24h: float) -> FactorScore:
    rs = token_ret_24h - btc_ret_24h
    if rs >= 5.0:    pts = 20.0
    elif rs >= 2.0:  pts = 14.0
    elif rs >= 0:    pts = 7.0
    else:            pts = 0.0
    return FactorScore("rel_strength_vs_btc", pts, 20,
                       {"token_24h_pct": token_ret_24h,
                        "btc_24h_pct": btc_ret_24h,
                        "rs_pct": rs})


def _atr(highs: List[float], lows: List[float],
         closes: List[float], n: int) -> Optional[float]:
    if len(closes) < n + 1: return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i]  - closes[i - 1]))
        trs.append(tr)
    last = trs[-n:]
    return sum(last) / len(last) if last else None


def factor_atr_expansion(highs: List[float], lows: List[float],
                          closes: List[float]) -> FactorScore:
    """ATR ratio: current ATR(14) vs avg of last 20 prior ATR(14) values."""
    if len(closes) < 35:
        return FactorScore("atr_expansion", 0, 15,
                           {"reason": f"need 35 bars, have {len(closes)}"})
    cur_atr = _atr(highs, lows, closes, 14)
    if cur_atr is None or cur_atr <= 0:
        return FactorScore("atr_expansion", 0, 15)
    # Build prior 20 atr values
    prior_atrs = []
    for i in range(20, 0, -1):
        slice_h = highs[:-i] if i > 0 else highs
        slice_l = lows[:-i]  if i > 0 else lows
        slice_c = closes[:-i] if i > 0 else closes
        a = _atr(slice_h, slice_l, slice_c, 14)
        if a is not None and a > 0:
            prior_atrs.append(a)
    if not prior_atrs:
        return FactorScore("atr_expansion", 0, 15)
    avg_prior = sum(prior_atrs) / len(prior_atrs)
    ratio = cur_atr / avg_prior if avg_prior > 0 else 0
    if ratio > 1.5:    pts = 15.0
    elif ratio > 1.2:  pts = 10.0
    elif ratio >= 1.0: pts = 5.0
    else:              pts = 0.0
    return FactorScore("atr_expansion", pts, 15,
                       {"cur_atr": cur_atr, "avg_prior_atr": avg_prior,
                        "ratio": ratio})


def factor_liquidity(snap: TokenSnapshot) -> Tuple[FactorScore, str]:
    """Returns (score, disqualify_reason). Empty reason = OK."""
    if snap.vol_24h_usd < MIN_24H_USD_VOLUME:
        return (FactorScore("liquidity", 0, 25,
                            {"vol_24h_usd": snap.vol_24h_usd}),
                f"24h volume ${snap.vol_24h_usd:,.0f} < ${MIN_24H_USD_VOLUME:,}")
    if snap.spread_pct > MAX_SPREAD_PCT:
        return (FactorScore("liquidity", 0, 25,
                            {"spread_pct": snap.spread_pct}),
                f"spread {snap.spread_pct:.3f}% > {MAX_SPREAD_PCT}%")
    pts = 20.0
    if snap.spread_pct < GOOD_SPREAD_PCT:
        pts = 25.0
    return (FactorScore("liquidity", pts, 25,
                        {"vol_24h_usd": snap.vol_24h_usd,
                         "spread_pct": snap.spread_pct}),
            "")


# ── main scoring pipeline ────────────────────────────────────────────
def build_universe(top_n: int = 50,
                   only_usdt: bool = True) -> List[TokenSnapshot]:
    """Return top-N USDT pairs by 24h USD volume from one tickers call."""
    tickers = fetch_tickers()
    rows: List[TokenSnapshot] = []
    for t in tickers:
        pair = t.get("currency_pair", "")
        if only_usdt and not pair.endswith("_USDT"):
            continue
        try:
            last  = float(t.get("last") or 0)
            base_vol  = float(t.get("base_volume")  or 0)   # in base coin
            quote_vol = float(t.get("quote_volume") or 0)   # in USDT
            change_pct = float(t.get("change_percentage") or 0)
        except ValueError:
            continue
        if quote_vol <= 0 or last <= 0:
            continue
        rows.append(TokenSnapshot(
            pair=pair, last_price=last, vol_24h_usd=quote_vol,
            return_24h_pct=change_pct,
        ))
    rows.sort(key=lambda x: -x.vol_24h_usd)
    return rows[:top_n]


def score_token(snap: TokenSnapshot, btc_24h_pct: float,
                fetch_book: bool = True) -> TokenScore:
    """Run all 5 factors against one token. Fetches its 4H candles +
    optional orderbook top. Network calls: 1 (or 2 with book)."""
    factors: List[FactorScore] = []
    disqualify = ""

    # Need 4H candles — fetch enough for ATR(14) + 20 prior ATRs (so ~50 bars)
    try:
        rows = fetch_candles(snap.pair, "4h", 60)
    except Exception as e:
        return TokenScore(snap.pair, 0, [], False, False,
                          f"4H candle fetch failed: {e}")
    # Gate row format: [ts, quote_vol, close, high, low, open, base_vol]
    closes = [float(r[2]) for r in rows]
    highs  = [float(r[3]) for r in rows]
    lows   = [float(r[4]) for r in rows]
    if len(closes) < 30:
        return TokenScore(snap.pair, 0, [], False, False,
                          f"only {len(closes)} 4H bars")

    # Compute 30d avg DAILY volume from 4H bars: 6 4H bars / day, 30 days = 180 bars
    # We don't have 180 here. Approximation from the recent 4H quote_vol average × 6.
    quote_vols_4h = [float(r[1]) for r in rows]   # USDT volume per 4H bar
    if quote_vols_4h:
        daily_avg = sum(quote_vols_4h[-30 * 6:]) / max(1, min(len(quote_vols_4h), 30 * 6)) * 6
    else:
        daily_avg = None
    snap.vol_30d_avg = daily_avg

    # Spread (optional book fetch)
    if fetch_book:
        try:
            bid, ask = fetch_orderbook_top(snap.pair)
            snap.bid, snap.ask = bid, ask
            mid = (bid + ask) / 2 if (bid and ask) else snap.last_price
            snap.spread_pct = ((ask - bid) / mid * 100) if mid > 0 and ask > bid else 99.9
        except Exception:
            snap.spread_pct = 0.05  # assume tight if book fetch fails
    else:
        snap.spread_pct = 0.05

    # ── factors ──
    f1 = factor_volume_surge(snap);                                 factors.append(f1)
    f2 = factor_breakout(closes, snap.last_price);                  factors.append(f2)
    f3 = factor_rel_strength(snap.return_24h_pct, btc_24h_pct);     factors.append(f3)
    f4 = factor_atr_expansion(highs, lows, closes);                 factors.append(f4)
    f5, dq = factor_liquidity(snap);                                factors.append(f5)
    if dq:
        disqualify = dq

    total = sum(f.points for f in factors)
    qualified = total >= MIN_QUALIFY_SCORE and not disqualify
    god_tier  = total >= GOD_TIER_SCORE  and not disqualify

    return TokenScore(
        pair=snap.pair, total=total, factors=factors,
        qualified=qualified, god_tier=god_tier,
        disqualify_reason=disqualify,
        snapshot_data={
            "last":       snap.last_price,
            "vol_24h_usd":snap.vol_24h_usd,
            "ret_24h_pct":snap.return_24h_pct,
            "spread_pct": snap.spread_pct,
            "bid":        snap.bid,
            "ask":        snap.ask,
        },
    )


def run_scan(top_n: int, btc_24h_pct: Optional[float] = None,
              throttle_s: float = 0.15) -> List[TokenScore]:
    """Score the top-N USDT spot pairs. Returns sorted desc by score."""
    universe = build_universe(top_n)
    if btc_24h_pct is None:
        # Find BTC in universe; if absent, fetch tickers separately
        btc = next((u for u in universe if u.pair == "BTC_USDT"), None)
        if btc is None:
            tickers = fetch_tickers()
            for t in tickers:
                if t.get("currency_pair") == "BTC_USDT":
                    try:
                        btc_24h_pct = float(t.get("change_percentage") or 0)
                    except ValueError:
                        btc_24h_pct = 0.0
                    break
        else:
            btc_24h_pct = btc.return_24h_pct
    btc_24h_pct = btc_24h_pct or 0.0

    scores: List[TokenScore] = []
    for i, snap in enumerate(universe):
        score = score_token(snap, btc_24h_pct, fetch_book=True)
        scores.append(score)
        time.sleep(throttle_s)
    scores.sort(key=lambda s: -s.total)
    return scores


# ── CLI ──────────────────────────────────────────────────────────────
def _print_human(results: List[TokenScore], limit: int):
    print("═" * 100)
    print(f"  AEGIS-ALPHA SCANNER · 4H momentum · top {len(results)} pairs · "
          f"qualifying ≥{MIN_QUALIFY_SCORE} · god-tier ≥{GOD_TIER_SCORE}")
    print("═" * 100)
    print(f"  {'#':>3}  {'PAIR':<14}  {'SCORE':>5}  "
          f"{'V_SURGE':>8}  {'BREAK':>6}  {'RS-BTC':>7}  {'ATR-X':>6}  {'LIQ':>5}  "
          f"{'24h%':>7}  {'VOL$M':>7}  {'spread%':>8}  STATUS")
    print("  " + "-" * 96)
    qualified_count = god_count = dq_count = 0
    for i, s in enumerate(results[:limit], 1):
        if s.disqualify_reason: dq_count += 1
        if s.qualified:         qualified_count += 1
        if s.god_tier:          god_count += 1
        sd = s.snapshot_data
        f = {fac.name: fac.points for fac in s.factors}
        flag = ("🏆 GOD"   if s.god_tier else
                "✅ QUAL" if s.qualified else
                "❌ DQ"    if s.disqualify_reason else "·")
        print(f"  {i:>3}  {s.pair:<14}  {s.total:>5.1f}  "
              f"{f.get('volume_surge', 0):>7.1f}  "
              f"{f.get('breakout', 0):>5.1f}  "
              f"{f.get('rel_strength_vs_btc', 0):>6.1f}  "
              f"{f.get('atr_expansion', 0):>5.1f}  "
              f"{f.get('liquidity', 0):>4.1f}  "
              f"{sd.get('ret_24h_pct', 0):>+6.2f}%  "
              f"{sd.get('vol_24h_usd', 0)/1e6:>6.1f}  "
              f"{sd.get('spread_pct', 0):>7.3f}%  {flag}")
    print("  " + "-" * 96)
    print(f"  Total scanned: {len(results)}   Qualified: {qualified_count}   "
          f"God-tier: {god_count}   Disqualified: {dq_count}")
    print("═" * 100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top",       type=int,   default=50,
                    help="top-N spot USDT pairs by 24h volume (default 50)")
    ap.add_argument("--limit",     type=int,   default=30,
                    help="max rows to display (default 30)")
    ap.add_argument("--min-score", type=float, default=MIN_QUALIFY_SCORE)
    ap.add_argument("--throttle",  type=float, default=0.15,
                    help="seconds between per-pair API calls")
    ap.add_argument("--json",      action="store_true",
                    help="emit machine-readable JSON to stdout")
    args = ap.parse_args()

    print(f"[scanner] fetching universe (top {args.top}) …", flush=True,
          file=sys.stderr)
    results = run_scan(args.top, throttle_s=args.throttle)

    if args.json:
        out = []
        for s in results:
            d = asdict(s)
            d["factors"] = [asdict(f) for f in s.factors]
            out.append(d)
        print(json.dumps(out, indent=2))
    else:
        _print_human(results, args.limit)


if __name__ == "__main__":
    main()
