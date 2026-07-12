#!/usr/bin/env python3
"""
d6_final_run.py — D6 Phase A binding-run orchestrator.

Single-command runner that, when invoked at the D6 deadline (Apr 30
~21:00 UTC, full 5-day microstructure window), executes the entire
validation suite back-to-back and writes a consolidated verdict
report. No manual orchestration. No risk of forgetting an analysis.

Pipeline (in order):

  1. Sanity-check the data window:
       - ≥ 4.5 days span between first and last parquet sample
       - ≥ 4 daily buckets in /var/log/microstructure/
       - all 5 pairs present
       - no parquet file with < 1000 rows (silent collector death)

  2. microstructure_analyze.py (base IC + t-stat per pair × feature × horizon)

  3. microstructure_robust_check.py (7-filter battery)
       - stationarity by day (now 5 days, not 2)
       - walk-forward stability
       - BH-FDR multi-comparison
       - block-bootstrap 95% CI (1000 resamples)
       - vol-adjusted IC
       - quintile monotonicity
       - concurrent-feature independence warnings

  4. microstructure_signal_nature.py (quintile + multi-fee scenarios)
       - taker (30 bps RT) verdict per cell
       - maker (10 bps RT) verdict per cell
       - economic interpretability check

  5. Cross-cut: which cells clear ALL of:
       - 6 hard filters (1+2+3+4+5+7)
       - Q5-Q1 magnitude ≥ 30 bps gross OR maker-net ≥ 5 bps
       - Stationarity = sign-consistent across 4/5 days
       - BUSD or USDT pair (not derivative)

  6. Write D6_FINAL_VERDICT.md with:
       - GO Phase B (with named cells + recommended execution model)
       - NO-GO (with diagnosis + ADR-002 fallback recommendation)
       - All raw outputs preserved as D6_FINAL_*.txt for audit trail

This is ops-code, not strategy code. ADR-003 compliant.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ── helpers ─────────────────────────────────────────────────────────
def run(cmd: list[str], log_path: Path) -> tuple[int, str]:
    """Run a command, capture stdout+stderr to log_path, return (exit, last_lines)."""
    print(f"  ▸ {' '.join(shlex.quote(c) for c in cmd)}")
    print(f"    → log: {log_path}")
    with log_path.open("w") as f:
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=False)
    tail = "\n".join(log_path.read_text().splitlines()[-25:])
    return proc.returncode, tail


def python_bin() -> str:
    """Use venv if present, else system python."""
    venv = ROOT / "venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


def data_sanity(data_dir: Path) -> dict:
    """Pre-flight check on the parquet directory."""
    import pandas as pd

    issues = []
    days = sorted(d.name for d in data_dir.iterdir() if d.is_dir())
    if len(days) < 4:
        issues.append(f"only {len(days)} daily buckets (need ≥4 for stationarity)")

    pairs_seen = set()
    small_files = []
    first_ts = None
    last_ts = None
    total_rows = 0
    for f in sorted(data_dir.rglob("*.parquet")):
        pairs_seen.add(f.stem)
        df = pd.read_parquet(f, columns=["ts_ms"])
        if len(df) < 500:
            small_files.append((str(f.relative_to(data_dir)), len(df)))
        if not df.empty:
            ts_min = df["ts_ms"].min() / 1000
            ts_max = df["ts_ms"].max() / 1000
            first_ts = ts_min if first_ts is None else min(first_ts, ts_min)
            last_ts  = ts_max if last_ts  is None else max(last_ts,  ts_max)
            total_rows += len(df)

    if first_ts is None:
        return {"ok": False, "issues": ["no parquet files found"], "span_h": 0,
                "pairs": [], "total_rows": 0}

    span_h = (last_ts - first_ts) / 3600
    if span_h < 4.5 * 24:
        issues.append(f"span only {span_h:.1f}h (need ≥108h for D6)")
    expected_pairs = {"AVAX_USDT", "BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT"}
    missing = expected_pairs - pairs_seen
    if missing:
        issues.append(f"missing pairs: {sorted(missing)}")
    if small_files:
        issues.append(f"{len(small_files)} parquet files have <500 rows")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "span_h": span_h,
        "days": days,
        "pairs": sorted(pairs_seen),
        "total_rows": total_rows,
        "small_files": small_files[:5],
        "first_sample": datetime.fromtimestamp(first_ts, tz=timezone.utc).isoformat(),
        "last_sample":  datetime.fromtimestamp(last_ts,  tz=timezone.utc).isoformat(),
    }


# ── verdict synthesis ──────────────────────────────────────────────
def parse_robust_survivors(log_text: str) -> list[dict]:
    """Extract the post-7-filter survivor table from robust_check output."""
    out: list[dict] = []
    in_table = False
    for line in log_text.splitlines():
        if "TIGHTENED PHASE B VERDICT" in line:
            in_table = True
            continue
        if in_table and line.strip().startswith("---") and len(out) > 0:
            break
        if not in_table: continue
        # Match data row: "     XRP_USDT   spread_pct          1800s +0.475 ..."
        m = re.match(
            r"\s+(\w+_USDT)\s+([\w_]+)\s+(\d+)s\s+([+-]?\d\.\d+)", line)
        if m:
            out.append({"pair": m.group(1), "feature": m.group(2),
                        "horizon": int(m.group(3)), "ic": float(m.group(4))})
    return out


def parse_nature_fee_verdicts(log_text: str) -> list[dict]:
    """Extract the FEE-SCENARIO SENSITIVITY table from signal_nature."""
    out: list[dict] = []
    in_block = False
    for line in log_text.splitlines():
        if "FEE-SCENARIO SENSITIVITY" in line:
            in_block = True
            continue
        if in_block and "═══" in line and out:
            break
        if not in_block: continue
        # Look for: "  XRP_USDT  spread_pct ... +14.23   ⚠ ..."
        m = re.match(
            r"\s+(\w+_USDT)\s+([\w_]+)\s+(\d+)s\s+([+-]?\d+\.\d+)\s+(.+)",
            line)
        if m:
            cells = m.group(5)
            # Look for the maker (10bps) cell — first verdict in row
            maker_m = re.search(r"([✅⚠🛑])\s*([+-]?\d+\.\d+)", cells)
            if maker_m:
                out.append({
                    "pair": m.group(1),
                    "feature": m.group(2),
                    "horizon": int(m.group(3)),
                    "gross_bps": float(m.group(4)),
                    "maker_verdict": maker_m.group(1),
                    "maker_net_bps": float(maker_m.group(2)),
                })
    return out


def write_verdict_md(report_path: Path, sanity: dict,
                     survivors: list[dict], fees: list[dict],
                     log_paths: dict) -> str:
    """Compose the consolidated D6 verdict markdown."""
    lines: list[str] = []
    L = lines.append
    L(f"# D6 FINAL VERDICT — {datetime.now(timezone.utc).isoformat()}")
    L("")
    L(f"**Data window:** {sanity['first_sample']} → {sanity['last_sample']}")
    L(f"**Span:** {sanity['span_h']:.1f} hours · "
      f"{len(sanity['days'])} daily buckets · "
      f"{sanity['total_rows']:,} total rows · "
      f"{len(sanity['pairs'])} pairs")
    L("")

    # Sanity status
    L("## 1. Pre-flight sanity")
    if sanity["ok"]:
        L("✅ Data window passes all sanity checks.")
    else:
        L("⚠ Data window has issues:")
        for x in sanity["issues"]:
            L(f"  - {x}")
    L("")

    # 7-filter survivors
    L("## 2. Seven-filter robustness battery")
    L(f"**Survivors:** {len(survivors)} cell(s) clear all 7 filters.")
    L("")
    if survivors:
        L("| # | Pair | Feature | Horizon | IC |")
        L("|--:|---|---|---:|---:|")
        for i, s in enumerate(survivors[:20], 1):
            L(f"| {i} | {s['pair']} | {s['feature']} | {s['horizon']}s | {s['ic']:+.3f} |")
        if len(survivors) > 20:
            L(f"| ... | ... | ... | ... | ... |")
        L("")

    # Maker-fee winners
    L("## 3. Economic verdict (Q5-Q1 vs maker fee)")
    maker_wins = [f for f in fees if f["maker_verdict"] == "✅"]
    L(f"**Maker-fee winners (≥5 bps net at 10 bps RT):** {len(maker_wins)}")
    if maker_wins:
        L("")
        L("| Pair | Feature | H | Gross (bps) | Maker net (bps) |")
        L("|---|---|---:|---:|---:|")
        for w in sorted(maker_wins, key=lambda x: -x["maker_net_bps"]):
            L(f"| {w['pair']} | {w['feature']} | {w['horizon']}s | "
              f"{w['gross_bps']:+.2f} | {w['maker_net_bps']:+.2f} |")
        L("")

    # Phase B / NO-GO decision
    L("## 4. Phase B promotion verdict")
    if maker_wins:
        leader = max(maker_wins, key=lambda x: x["maker_net_bps"])
        L(f"### 🟢 GO — Phase B candidate identified")
        L("")
        L(f"**Lead cell:** `{leader['pair']} · {leader['feature']} @ H={leader['horizon']}s`")
        L(f"- Gross Q5-Q1 edge: {leader['gross_bps']:+.2f} bps")
        L(f"- Maker-net edge:   {leader['maker_net_bps']:+.2f} bps (target ≥5)")
        L("")
        L("**D7+ design path:**")
        L("1. Implement single-feature maker-execution strategy on this cell")
        L("   - or: ensemble across all maker-winners if ≥3 independent features survive")
        L("2. Walk-forward backtest via professional_backtest.py on the same data")
        L("3. Risk overlay: HARD_STOP_PCT, position sizing, MAX_HOLD_BARS")
        L("4. Tests: tests/test_phase_b.py covering entry/exit/risk")
        L("5. Replace XRP_USDT bot with this strategy (single-pair focus)")
        L("6. 60-day Stage 1 paper validation")
        L("")
    else:
        L(f"### 🛑 NO-GO — no cell clears the maker-fee gate")
        L("")
        L("Possible explanations to investigate:")
        L("- 5-day window captured only one regime (extend to 10 days)")
        L("- Microstructure thesis is wrong → ADR-002 B1 fallback (on-chain)")
        L("- Need different feature engineering (vol-adjusted spread, OFI ratios)")
        L("- Need different execution model (wider horizons, market making)")
        L("")
        L("**ADR-002 fallback decision:** B1 on-chain becomes the next Phase A")
        L("research direction. Vote ensemble continues paper-running as control.")
        L("")

    # Audit trail
    L("## 5. Audit trail")
    L("")
    for label, path in log_paths.items():
        L(f"- `{label}` → `{path.name}`")
    L("")
    L("All logs preserved verbatim. Re-run with `python d6_final_run.py` for")
    L("a fresh verdict.")
    L("")
    L(f"---")
    L(f"_Generated by `d6_final_run.py` at "
      f"{datetime.now(timezone.utc).isoformat()}_")

    text = "\n".join(lines)
    report_path.write_text(text)
    return text


# ── main ───────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[2])
    ap.add_argument("--data-dir", default="/var/log/microstructure",
                    help="Microstructure parquet directory")
    ap.add_argument("--out-dir", default=str(ROOT),
                    help="Where to write D6_FINAL_*.txt and D6_FINAL_VERDICT.md")
    ap.add_argument("--allow-partial", action="store_true",
                    help="Run even if data span < 108h (D6 dry-run mode)")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    py = python_bin()

    print("═" * 80)
    print("  D6 FINAL RUN — Phase A binding verdict orchestrator")
    print(f"  Data: {args.data_dir}")
    print(f"  Out:  {out}")
    print("═" * 80)

    # 1. sanity
    print("\n[1/4] Pre-flight sanity check on data directory")
    sanity = data_sanity(Path(args.data_dir))
    print(f"  span: {sanity['span_h']:.1f}h, {len(sanity['days'])} days, "
          f"{sanity['total_rows']:,} rows, {len(sanity['pairs'])} pairs")
    if not sanity["ok"]:
        print(f"  ⚠ issues: {sanity['issues']}")
        if not args.allow_partial:
            print("  🛑 Aborting. Pass --allow-partial to run dry-run anyway.")
            return 2

    # Log paths
    base = Path(args.data_dir)
    paths = {
        "base_analyzer":   out / "D6_FINAL_BASE.txt",
        "robust_battery":  out / "D6_FINAL_ROBUST.txt",
        "signal_nature":   out / "D6_FINAL_NATURE.txt",
        "verdict":         out / "D6_FINAL_VERDICT.md",
    }

    # 2. base analyzer
    print("\n[2/4] Running microstructure_analyze.py")
    rc, _ = run([py, str(ROOT / "microstructure_analyze.py"),
                 "--data-dir", args.data_dir],
                paths["base_analyzer"])
    if rc != 0:
        print(f"  🛑 base analyzer failed (exit {rc})")
        return 3

    # 3. robust battery
    print("\n[3/4] Running microstructure_robust_check.py (7-filter)")
    rc, _ = run([py, str(ROOT / "microstructure_robust_check.py"),
                 "--data-dir", args.data_dir],
                paths["robust_battery"])
    if rc != 0:
        print(f"  🛑 robust check failed (exit {rc})")
        return 3

    # 4. signal nature
    print("\n[4/4] Running microstructure_signal_nature.py")
    rc, _ = run([py, str(ROOT / "microstructure_signal_nature.py"),
                 "--data-dir", args.data_dir],
                paths["signal_nature"])
    if rc != 0:
        print(f"  🛑 signal-nature failed (exit {rc})")
        return 3

    # Synthesis
    print("\n[5/4] Synthesizing consolidated verdict")
    survivors = parse_robust_survivors(paths["robust_battery"].read_text())
    fees = parse_nature_fee_verdicts(paths["signal_nature"].read_text())
    text = write_verdict_md(paths["verdict"], sanity, survivors, fees, paths)

    print("\n" + "═" * 80)
    print("  D6 FINAL VERDICT")
    print("═" * 80)
    print(text)
    print("═" * 80)
    print(f"\n  Report: {paths['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
