#!/usr/bin/env python3
"""
GODS LEVEL ENGINE — Terminal Dashboard
Run alongside the engine to monitor live or simulation state.
Usage: python dashboard.py [--log gods_engine.log] [--results sim_results_*.json]
"""
import os, sys, json, time, glob, argparse
from datetime import datetime

def clear(): print("\033[H\033[J", end="")

def color(text, code): return f"\033[{code}m{text}\033[0m"
def green(t):  return color(t, "92")
def red(t):    return color(t, "91")
def yellow(t): return color(t, "93")
def cyan(t):   return color(t, "96")
def bold(t):   return color(t, "1")
def dim(t):    return color(t, "2")

def bar(val, max_val, width=20, fill="█", empty="░"):
    if max_val == 0: return empty * width
    filled = int(min(val/max_val, 1.0) * width)
    return fill * filled + empty * (width - filled)

def load_latest_results(pattern="sim_results_*.json"):
    files = sorted(glob.glob(pattern))
    if not files: return None
    try:
        with open(files[-1]) as f:
            return json.load(f)
    except:
        return None

def load_log_tail(logfile, n=30):
    if not os.path.exists(logfile): return []
    try:
        with open(logfile) as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[-n:]]
    except:
        return []

def render_dashboard(results, log_lines, refresh=0):
    clear()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Header
    print(bold(cyan("╔" + "═"*70 + "╗")))
    print(bold(cyan("║")) + bold(" ⚡  GODS LEVEL ENGINE — LIVE DASHBOARD") +
          " "*(31 - len(str(refresh))) + dim(f"[refresh #{refresh}]") + bold(cyan("  ║")))
    print(bold(cyan("║")) + f"  {now}" + " "*50 + bold(cyan("║")))
    print(bold(cyan("╚" + "═"*70 + "╝")))
    print()

    if results:
        mode = results.get("mode","unknown")
        pnl  = results.get("pnl", 0)
        start= results.get("start_balance", 1000)
        end  = results.get("end_balance", 1000)
        wr   = results.get("win_rate", 0)
        n_tr = results.get("trades", 0)
        sw   = results.get("switches", 0)
        roi  = results.get("roi_pct", 0)

        # Stats row
        pnl_c   = green(f"{pnl:+.4f}") if pnl >= 0 else red(f"{pnl:+.4f}")
        roi_c   = green(f"{roi:+.4f}%") if roi >= 0 else red(f"{roi:+.4f}%")
        wr_c    = green(f"{wr:.1f}%")   if wr >= 55 else (yellow(f"{wr:.1f}%") if wr >= 45 else red(f"{wr:.1f}%"))

        print(bold("  PERFORMANCE OVERVIEW"))
        print("  " + "─"*68)
        print(f"  Net PnL:      {pnl_c} USDT       ROI: {roi_c}")
        print(f"  Start Bal:    ${start:.2f} USDT")
        print(f"  End Bal:      {green(f'${end:.4f}') if end >= start else red(f'${end:.4f}')} USDT")
        print(f"  Trades:       {n_tr}  |  Win Rate: {wr_c}  |  Pair Switches: {sw}")
        print()

        # Balance bar
        bal_pct = end/start*100
        b_bar   = bar(end, start*1.1, 30)
        b_color = green if end >= start else red
        print(f"  Balance  [{b_color(b_bar)}] {b_color(f'{bal_pct:.1f}%')}")
        print(f"  Win Rate [{bar(wr,100,30,'▓','░')}] {wr_c}")
        print()

        # Per-pair table
        history = results.get("history", [])
        if history:
            by_pair = {}
            for t in history:
                by_pair.setdefault(t["pair"], []).append(t)

            print(bold("  PER-PAIR BREAKDOWN"))
            print("  " + "─"*68)
            print(f"  {'PAIR':<14} {'TRADES':>6} {'WIN%':>6} {'PNL USDT':>10} {'BAR'}")
            print("  " + "─"*68)
            for pair, trades in sorted(by_pair.items()):
                wins    = sum(1 for t in trades if t["pnl"] > 0)
                pair_pnl= sum(t["pnl"] for t in trades)
                pair_wr = wins/len(trades)*100
                pnl_c2  = green(f"{pair_pnl:+.4f}") if pair_pnl>=0 else red(f"{pair_pnl:+.4f}")
                wr_c2   = green(f"{pair_wr:.0f}%") if pair_wr>=55 else red(f"{pair_wr:.0f}%")
                pb      = bar(max(pair_pnl+2, 0), 4, 15)
                pb_c    = green(pb) if pair_pnl>=0 else red(pb)
                print(f"  {pair:<14} {len(trades):>6} {wr_c2:>14}  {pnl_c2:>18}  {pb_c}")
            print()

            # Exit type breakdown
            exit_types = {}
            for t in history: exit_types[t["why"]] = exit_types.get(t["why"], 0)+1
            print(bold("  EXIT TYPE BREAKDOWN"))
            print("  " + "─"*68)
            for why, cnt in sorted(exit_types.items(), key=lambda x:-x[1]):
                eb = bar(cnt, max(exit_types.values()), 20)
                print(f"  {why:<22}  {cnt:>3}×  [{eb}]")
            print()

    # Log tail
    if log_lines:
        print(bold("  RECENT LOG"))
        print("  " + "─"*68)
        for line in log_lines[-15:]:
            if "OPEN" in line or "ENTERED" in line:
                print("  " + cyan(line[:78]))
            elif "CLOSED" in line or "CLOSE" in line:
                if "+0." in line or "pnl=+" in line:
                    print("  " + green(line[:78]))
                else:
                    print("  " + red(line[:78]))
            elif "SWITCH" in line or "UPGRADE" in line:
                print("  " + yellow(line[:78]))
            elif "ERROR" in line or "HALT" in line or "STOP" in line:
                print("  " + red(line[:78]))
            else:
                print("  " + dim(line[:78]))
        print()

    print(bold(cyan("─"*72)))
    print(f"  {dim('Press Ctrl+C to exit  |  Auto-refresh every 3s  |  All funds in USDT ✅')}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--log",     default="gods_engine.log")
    p.add_argument("--results", default="sim_results_*.json")
    p.add_argument("--once",    action="store_true")
    args = p.parse_args()

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    refresh = 0
    try:
        while True:
            refresh += 1
            results  = load_latest_results(args.results)
            log_lines= load_log_tail(args.log)
            render_dashboard(results, log_lines, refresh)
            if args.once: break
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n  Dashboard closed.")
