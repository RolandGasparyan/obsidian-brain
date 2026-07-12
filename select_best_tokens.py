#!/usr/bin/env python3
"""
Rank Gate.io spot pairs by MA50+W10 quality score.

Composite score combines:
  • ROI (primary — weighted log-scaled so BONK-style outliers don't dominate)
  • Win rate (reliability signal)
  • Edge over buy-and-hold (strategy-fit signal)
  • Trade count penalty (fewer trades = less slippage drag in live)
  • Liquidity proxy (mean USDT-volume of recent bars — avoids thin pairs)

Outputs a ranked shortlist of "best profitable" tokens to actually trade.

Usage:
  python select_best_tokens.py
  python select_best_tokens.py --top 8 --interval 1d
  python select_best_tokens.py --pairs BTC_USDT ETH_USDT SOL_USDT
"""
import argparse
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from backtest_multi_token import (
    DEFAULT_PAIRS,
    backtest_one,
    fetch_gateio_bars,
)


UNIVERSE = [
    # Blue chips
    "BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT",
    # Large alts
    "XRP_USDT", "ADA_USDT", "AVAX_USDT", "DOT_USDT",
    "LINK_USDT", "TON_USDT", "NEAR_USDT", "TRX_USDT",
    # DeFi
    "UNI_USDT", "AAVE_USDT", "MKR_USDT",
    # Memecoins (profitable class)
    "DOGE_USDT", "SHIB_USDT", "PEPE_USDT",
    "FLOKI_USDT", "WIF_USDT", "BONK_USDT",
    # Layer-2 / other
    "ARB_USDT", "OP_USDT", "SUI_USDT",
    # Perpetual winners
    "INJ_USDT", "TIA_USDT",
]


def safe_log10(x):
    """log10 that handles negative / zero ROI gracefully."""
    if x <= -99.99:
        return -2.0
    # Map [-100, +inf] → log10(1 + x/100) + noise for signs
    if x >= 0:
        return math.log10(1 + x / 100)
    # negative ROI: mirror into negative log space
    return -math.log10(1 + abs(x) / 100)


def score_one(pair, results_for_pair, avg_volume):
    """
    Given the per-strategy results for one pair, compute a composite score
    for MA50_W10. Returns None if MA50_W10 wasn't run for this pair.
    """
    ma  = next((r for r in results_for_pair if r["name"] == "MA50_W10"), None)
    bh  = next((r for r in results_for_pair if r["name"] == "BUY_AND_HOLD"), None)
    if not ma or not bh:
        return None

    roi      = ma["roi"]         # compound %
    wr       = ma["wr"]          # %
    trades   = ma["trades"]
    bh_roi   = bh["roi"]
    edge     = roi - bh_roi

    # — normalized sub-scores (0..1 ish) —
    roi_term  = safe_log10(roi)                       # −2..~3.3 (19600% → ~2.3)
    wr_term   = max(0.0, (wr - 30.0) / 70.0)          # 30%→0, 100%→1
    edge_term = safe_log10(max(edge, -99.99))
    # trade count sweet spot ~8–25: outside is penalized
    if trades <= 0:
        trade_term = -1.0
    elif trades < 5:
        trade_term = -0.4
    elif trades <= 25:
        trade_term = 0.3
    else:
        # too many flips — slippage drag
        trade_term = max(-0.3, 0.3 - (trades - 25) * 0.02)

    # Liquidity gate: sub-$1M average daily volume = penalty
    if avg_volume >= 50_000_000:      # $50M+: blue chip
        liq_term = 0.6
    elif avg_volume >= 10_000_000:    # $10M+: solid
        liq_term = 0.3
    elif avg_volume >= 1_000_000:     # $1M+: tradeable
        liq_term = 0.0
    elif avg_volume >= 100_000:       # $100K+: risky
        liq_term = -0.4
    else:
        liq_term = -1.0

    composite = (
        1.2 * roi_term +
        0.6 * edge_term +
        0.8 * wr_term +
        0.5 * trade_term +
        0.7 * liq_term
    )

    return {
        "pair":      pair,
        "roi":       roi,
        "wr":        wr,
        "trades":    trades,
        "bh_roi":    bh_roi,
        "edge":      edge,
        "avg_vol":   avg_volume,
        "score":     composite,
        "avg_pct":   ma["avg_pct"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=UNIVERSE,
                    help="universe of Gate.io pairs to rank")
    ap.add_argument("--interval", default="1d", choices=["1d", "4h"])
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--top", type=int, default=8, help="how many to output")
    ap.add_argument("--balance", type=float, default=1000.0)
    args = ap.parse_args()

    print("═" * 96)
    print(f"  TOKEN SELECTION · {len(args.pairs)} pairs · {args.interval} · {args.limit} bars")
    print(f"  Scoring: ROI + edge + win-rate + trade-count + liquidity")
    print("═" * 96)

    ranked = []
    for i, pair in enumerate(args.pairs, 1):
        try:
            bars = fetch_gateio_bars(pair, args.interval, args.limit)
            if not bars or len(bars) < 60:
                print(f"  [{i:>2}/{len(args.pairs)}] {pair:<12} SKIP (only {len(bars)} bars)")
                continue
            # Liquidity proxy: avg USDT-value per bar over last 200 bars
            tail = bars[-200:] if len(bars) >= 200 else bars
            avg_usdt_vol = sum(b.c * b.v for b in tail) / len(tail)
            results = backtest_one(pair, bars, args.balance)
            row = score_one(pair, results, avg_usdt_vol)
            if row is None:
                print(f"  [{i:>2}/{len(args.pairs)}] {pair:<12} no MA50_W10 result")
                continue
            ranked.append(row)
            print(f"  [{i:>2}/{len(args.pairs)}] {pair:<12} ROI {row['roi']:>+9.1f}%  "
                  f"wr {row['wr']:>5.1f}%  vol ${row['avg_vol']/1e6:>7.1f}M  "
                  f"score {row['score']:>+6.2f}")
            time.sleep(0.25)
        except Exception as e:
            print(f"  [{i:>2}/{len(args.pairs)}] {pair:<12} ERR: {e}")

    ranked.sort(key=lambda r: -r["score"])

    print()
    print("═" * 96)
    print(f"  TOP {min(args.top, len(ranked))} — RECOMMENDED TRADING UNIVERSE")
    print("═" * 96)
    print(f"  {'#':>2}  {'PAIR':<12}  {'SCORE':>7}  {'ROI':>10}  {'B&H':>10}  {'EDGE':>10}  "
          f"{'WR':>5}  {'TRD':>3}  {'VOL($M)':>9}")
    print("─" * 96)
    for i, r in enumerate(ranked[:args.top], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"  {i:>2}  {r['pair']:<12}  {r['score']:>+6.2f}  {r['roi']:>+9.1f}%  "
              f"{r['bh_roi']:>+8.1f}%  {r['edge']:>+8.1f}%  {r['wr']:>4.0f}%  "
              f"{r['trades']:>3}  {r['avg_vol']/1e6:>8.1f}")
    print("═" * 96)

    if ranked:
        best = ranked[:args.top]
        pair_list = " ".join(r['pair'] for r in best)
        print()
        print("  Run the selected universe in the live engine config:")
        print(f"  PAIRS = {[r['pair'] for r in best]}")
        print()
        print("  Or re-backtest just the top set:")
        print(f"  python3 backtest_multi_token.py --pairs {pair_list}")


if __name__ == "__main__":
    main()
