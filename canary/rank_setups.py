#!/usr/bin/env python3
"""Rank working strategy + pair combos from the paper trades DB.
Produces a JSON the Coach uses for smart dynamic rotation."""
import sqlite3, json, pathlib, sys

DB = "/home/ubuntu/trading_engine/trades.db"
OUT = "/home/ubuntu/canary/runtime/setup_rankings.json"
# Only pairs that are spot-tradable on Gate.io with our small size
TRADABLE = {"FLOKI","BOME","WIF","DOGE","OP","SHIB","DOT","ADA","UNI","ATOM",
            "LTC","SOL","BONK","XRP","AVAX","LINK","NEAR","SUI","SEI","INJ"}

def col_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in c.fetchall())

def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # discover columns
    c.execute("PRAGMA table_info(trades)")
    cols = [r[1] for r in c.fetchall()]
    strat_col = "strategy" if "strategy" in cols else ("strategy_name" if "strategy_name" in cols else None)
    asset_col = next((x for x in ("asset","symbol","pair","token") if x in cols), None)
    pnl_col = next((x for x in ("pnl_usd","pnl","profit_usd","profit") if x in cols), None)
    if not (strat_col and asset_col and pnl_col):
        print(f"Missing columns. cols={cols}", file=sys.stderr); sys.exit(1)

    q = f"""
    SELECT {strat_col} AS strat, {asset_col} AS asset,
           COUNT(*) AS n,
           SUM(CASE WHEN {pnl_col}>0 THEN 1 ELSE 0 END) AS wins,
           ROUND(SUM(CASE WHEN {pnl_col}>0 THEN {pnl_col} ELSE 0 END),4) AS gross_win,
           ROUND(SUM(CASE WHEN {pnl_col}<0 THEN -{pnl_col} ELSE 0 END),4) AS gross_loss,
           ROUND(SUM({pnl_col}),4) AS total_pnl
    FROM trades
    WHERE {pnl_col} IS NOT NULL AND {strat_col} IS NOT NULL AND {asset_col} IS NOT NULL
    GROUP BY strat, asset
    HAVING n >= 30
    """
    rows = []
    for strat, asset, n, wins, gw, gl, tot in c.execute(q):
        base = str(asset).replace("/USDT","").replace("_USDT","").replace("USDT","").upper().strip()
        if base not in TRADABLE:
            continue
        pf = (gw / gl) if gl and gl > 0 else (gw if gw > 0 else 0)
        wr = (wins / n) if n else 0
        # Score: reward profit factor + sample size + win rate, require positive PnL
        if tot is None or tot <= 0:
            continue
        score = round(pf * (0.5 + wr) * (1 + min(n, 2000) / 4000), 4)
        rows.append({
            "strategy": strat, "pair": f"{base}_USDT", "base": base,
            "trades": n, "win_rate": round(wr, 4), "profit_factor": round(pf, 3),
            "total_pnl": tot, "score": score,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    conn.close()

    pathlib.Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    out = {"generated_cols": {"strategy": strat_col, "asset": asset_col, "pnl": pnl_col},
           "count": len(rows), "rankings": rows[:40]}
    pathlib.Path(OUT).write_text(json.dumps(out, indent=2))
    print(f"Ranked {len(rows)} combos -> {OUT}\n")
    print(f"{'RANK':<5}{'STRATEGY':<22}{'PAIR':<12}{'N':>6}{'WR%':>7}{'PF':>8}{'PnL$':>10}{'SCORE':>8}")
    for i, r in enumerate(rows[:25], 1):
        print(f"{i:<5}{r['strategy'][:21]:<22}{r['pair']:<12}{r['trades']:>6}"
              f"{r['win_rate']*100:>6.1f}{r['profit_factor']:>8.2f}{r['total_pnl']:>10.2f}{r['score']:>8.2f}")

if __name__ == "__main__":
    main()
