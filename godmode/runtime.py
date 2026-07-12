"""
godmode.runtime — paper-shadow runtime that wires all 7 streams +
Confluence Arbiter to a replay tick stream (or a live collector, once
we add an adapter).

Current mode: OFFLINE REPLAY — consumes recorded JSONL files via
`godmode.replay.replay_stream`. Runs all streams, logs every arbiter
decision (including HOLDs), and writes a summary at the end.

No real orders. No paper-fill simulation (that comes with the full
MakerExecutor integration — for v1 we just record decisions).

Usage:
    python -m godmode.runtime --contract BTC_USDT
    python -m godmode.runtime --contract BTC_USDT --limit 100000

Outputs:
    godmode/data/shadow_decisions.jsonl   — one line per non-HOLD decision
    godmode/data/shadow_summary.json       — run stats

NOT for live trading. This validates the pipeline wiring on recorded
data. Live execution happens in a future module after agents produce
meaningful hit-rates in replay.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from collections import Counter
from pathlib import Path

from godmode.context  import MarketContext
from godmode.replay   import replay_stream
from godmode.arbiter  import ConfluenceArbiter
from godmode.streams  import (
    MicrostructureStream,
    VolatilityRegimeStream,
    AbsorptionStream,
    StructuralBreakStream,
    FeeEdgeStream,
    ExecutionQualityStream,
    RiskThrottleStream,
)
from champion import CapitalStageTracker, PositionSizer, RiskLaws

log = logging.getLogger("godmode.runtime")

DATA_ROOT = Path(__file__).resolve().parent / "data"


# ── stop placement (CHAMPION_MODE.md §3.2 + futures spec) ────────────
# 2-5 minute holds need tight stops or fees swallow R:R. Use 0.7× ATR(1m)
# clamped to [0.05%, 0.30%] of price. The /godsmode spec calls for
# "0.7× ATR" — this matches.
STOP_ATR_MULT       = 0.7
STOP_DIST_MIN_FRAC  = 0.0005   # 0.05%
STOP_DIST_MAX_FRAC  = 0.0030   # 0.30%


def compute_stop_price(side: str, entry: float, atr_1m, mid: float) -> float:
    """Return a stop price for a given side ('BUY' = long, 'SELL' = short).
    Falls back to MIN distance if ATR isn't available yet."""
    if entry <= 0 or mid is None or mid <= 0:
        return entry
    raw = STOP_ATR_MULT * (atr_1m or 0.0)
    floor = mid * STOP_DIST_MIN_FRAC
    cap   = mid * STOP_DIST_MAX_FRAC
    dist  = max(floor, min(cap, raw))
    return entry - dist if side == "BUY" else entry + dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", default="BTC_USDT")
    ap.add_argument("--data",     default=str(DATA_ROOT),
                    help="godmode data root")
    ap.add_argument("--limit",    type=int, default=0,
                    help="stop after N ticks (0 = all)")
    ap.add_argument("--score-every", type=int, default=100,
                    help="run arbiter every N ticks (default 100 ≈ 500ms)")
    ap.add_argument("--starting-equity", type=float, default=3_000.0,
                    help="paper-shadow starting equity for sizer (default $3k)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)-5s | %(message)s")

    ctx      = MarketContext(args.contract)
    streams  = [
        MicrostructureStream(),     # s1
        VolatilityRegimeStream(),   # s2
        AbsorptionStream(),         # s3 stub
        StructuralBreakStream(),    # s4 stub
        FeeEdgeStream(),            # s5
        ExecutionQualityStream(),   # s6 stub
        RiskThrottleStream(),       # s7
    ]
    arbiter  = ConfluenceArbiter()

    # Champion: doctrine-compliant sizing for every ENTER decision.
    # Paper-shadow → equity is just held at starting_equity (we don't
    # track P&L of hypothetical fills here; that comes when the
    # MakerExecutor lands).
    tracker  = CapitalStageTracker(starting_equity=args.starting_equity)
    risk_laws = RiskLaws()
    risk_laws.update_equity(args.starting_equity, time.time_ns())
    sizer    = PositionSizer(tracker, risk_laws)

    decisions_path = DATA_ROOT / "shadow_decisions.jsonl"
    summary_path   = DATA_ROOT / "shadow_summary.json"
    dec_fh = open(decisions_path, "w", buffering=1)

    action_counts = Counter()
    score_hist    = []
    tick_n        = 0
    non_hold      = 0
    first_t = last_t = 0
    t0 = time.time()
    # Per-stream diagnostic: max magnitude, mean confidence, veto count
    diag = {s.__class__.__name__: {"max_mag": 0.0, "mean_conf_sum": 0.0,
                                     "veto": 0, "calls": 0}
            for s in streams}

    try:
        for tick in replay_stream(args.data, args.contract):
            tick_n += 1
            if first_t == 0: first_t = tick.t_ns
            last_t = tick.t_ns

            ctx.ingest(tick)
            for s in streams:
                s.update(ctx)

            # Only score at cadence — signals don't change on every tick
            if tick_n % args.score_every != 0:
                continue

            # Call score() exactly once per stream per decision
            outputs = {}
            for s in streams:
                out = s.score()
                outputs[out.name] = out
                d = diag[s.__class__.__name__]
                d["calls"] += 1
                d["mean_conf_sum"] += out.confidence
                if out.magnitude > d["max_mag"]:
                    d["max_mag"] = out.magnitude
                if out.veto:
                    d["veto"] += 1
            decision = arbiter.vote(outputs)
            action_counts[decision.action] += 1
            score_hist.append(decision.final_score)

            if decision.action != "HOLD":
                non_hold += 1
                # Champion sizing — doctrine-compliant per-trade sizing
                mid = ctx.mid()
                atr = ctx.atr_1m(14)
                # Best ask for BUY, best bid for SELL — that's where post-only
                # entries would be expected to fill at-or-better.
                bb, ba = ctx.best_quote()
                if decision.action == "BUY":
                    entry = ba if ba else mid
                else:
                    entry = bb if bb else mid
                stop = compute_stop_price(decision.action, entry, atr, mid)
                rec = sizer.compute_size(
                    entry_price=entry, stop_price=stop, t_ns=tick.t_ns,
                    vol_percentile=None,    # TODO: feed BTC 14d vol pctile
                    god_tier=decision.aggressive,
                )
                # Feed BTC price to RiskLaws so systemic kill works.
                if mid: risk_laws.update_btc_price(mid, tick.t_ns)

                dec_fh.write(json.dumps({
                    "t_ns":         tick.t_ns,
                    "action":       decision.action,
                    "final_score":  round(decision.final_score, 2),
                    "net_edge_pct": round(decision.net_edge_pct * 100, 4),
                    "aggressive":   decision.aggressive,
                    "vetoes":       decision.vetoes,
                    "mid":          mid,
                    "dir_10":       ctx.dir_10(),
                    "std_z":        ctx.std_z(),
                    "entry":        entry,
                    "stop":         stop,
                    "stop_dist_pct": round(rec.stop_distance_pct * 100, 4),
                    "sizer_blocked": rec.blocked,
                    "block_reason": rec.block_reason,
                    "risk_pct":     round(rec.risk_pct * 100, 4),
                    "risk_amount":  round(rec.risk_amount, 4),
                    "position_units": round(rec.position_units, 8),
                    "notional":     round(rec.notional_value, 2),
                    "stage":        rec.stage,
                    "state":        rec.state,
                    "scalers":      rec.scalers,
                }, separators=(",", ":")) + "\n")

            if args.limit and tick_n >= args.limit:
                break
    finally:
        dec_fh.close()

    dur_s = (last_t - first_t) / 1e9 if first_t else 0
    wall = time.time() - t0
    # normalize diag
    for name, d in diag.items():
        d["mean_conf"] = round(d["mean_conf_sum"] / max(1, d["calls"]), 3)
        d.pop("mean_conf_sum", None)
        d["max_mag"] = round(d["max_mag"], 2)

    summary = {
        "contract":       args.contract,
        "ticks":          tick_n,
        "score_calls":    sum(action_counts.values()),
        "data_duration_s": round(dur_s, 1),
        "wall_duration_s": round(wall, 2),
        "speedup":        round(dur_s / max(wall, 1e-6), 1),
        "actions":        dict(action_counts),
        "non_hold":       non_hold,
        "non_hold_pct":   round(non_hold / max(1, sum(action_counts.values())) * 100, 2),
        "score_p50":      sorted(score_hist)[len(score_hist) // 2] if score_hist else 0,
        "score_p95":      sorted(score_hist)[int(len(score_hist) * 0.95)] if score_hist else 0,
        "score_max":      max(score_hist) if score_hist else 0,
        "per_stream":     diag,
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("═" * 72)
    print(f"  Shadow runtime complete — {args.contract}")
    print(f"  Ticks processed:      {tick_n:,}")
    print(f"  Arbiter decisions:    {sum(action_counts.values()):,}")
    print(f"  Data duration:        {dur_s:.1f}s   wall: {wall:.2f}s"
          f"   speedup: {summary['speedup']}×")
    print(f"  Actions:              BUY={action_counts['BUY']}  "
          f"SELL={action_counts['SELL']}  HOLD={action_counts['HOLD']}")
    print(f"  Non-HOLD rate:        {summary['non_hold_pct']}%")
    print(f"  Score p50 / p95 / max: "
          f"{summary['score_p50']:.1f} / {summary['score_p95']:.1f} / "
          f"{summary['score_max']:.1f}")
    print(f"  Decisions file:       {decisions_path}")
    print(f"  Summary:              {summary_path}")
    print()
    print(f"  Per-stream diagnostics:")
    for name, d in diag.items():
        print(f"    {name:<28} max_mag={d['max_mag']:>6.1f}  "
              f"mean_conf={d['mean_conf']:.2f}  "
              f"vetoes={d['veto']:>3}/{d['calls']}")
    print("═" * 72)


if __name__ == "__main__":
    main()
