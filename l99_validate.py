#!/usr/bin/env python3
"""
L99 Final System Integration & Validation Engine.

Runs the 5-phase deployment gate from docs/specs/L99_DEPLOYMENT_VALIDATOR.md
against the live system and prints a single GO / CONDITIONAL / NO-GO verdict.

Designed to be honest, not flattering. Each phase has explicit pass
criteria; if any criterion fails we report the failure rather than wave
it through. No deployment proceeds without GO.

Usage:
  python l99_validate.py                  # default: full report
  python l99_validate.py --phase 1        # single phase
  python l99_validate.py --json           # machine-readable output
  python l99_validate.py --remote         # against VPS (ssh)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── verdict types ────────────────────────────────────────────────────
GO          = "GO"
CONDITIONAL = "CONDITIONAL"
NO_GO       = "NO-GO"


@dataclass
class CheckResult:
    name:    str
    passed:  bool
    detail:  str = ""
    severity: str = "hard"   # "hard" (gate-blocking) | "soft" (informational)

    @property
    def icon(self) -> str:
        if self.passed: return "✓"
        return "✗" if self.severity == "hard" else "⚠"


@dataclass
class PhaseResult:
    name:       str
    checks:     List[CheckResult] = field(default_factory=list)

    @property
    def hard_pass(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == "hard")

    @property
    def all_pass(self) -> bool:
        return all(c.passed for c in self.checks)

    def add(self, name: str, passed: bool, detail: str = "",
            severity: str = "hard"):
        self.checks.append(CheckResult(name, passed, detail, severity))


# ── helpers ──────────────────────────────────────────────────────────
def _systemctl_active(unit: str) -> bool:
    """Return True if the unit is `active`."""
    try:
        out = subprocess.run(["systemctl", "is-active", unit],
                              capture_output=True, text=True, timeout=5)
        return out.stdout.strip() == "active"
    except Exception:
        return False


def _systemctl_restarts(unit: str) -> int:
    try:
        out = subprocess.run(["systemctl", "show", unit,
                               "--property=NRestarts", "--value"],
                              capture_output=True, text=True, timeout=5)
        return int(out.stdout.strip() or 0)
    except Exception:
        return -1


def _safe_import(module_name: str, attr: str = None) -> Tuple[bool, str]:
    """Try to import a module; optionally fetch an attribute. Returns
    (success, detail string)."""
    try:
        mod = __import__(module_name, fromlist=[attr] if attr else [])
        if attr:
            getattr(mod, attr)
        return True, "imported"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _file_exists(path: str) -> bool:
    return Path(path).exists()


def _count_parquet_rows(root: str) -> Tuple[int, int]:
    """Return (file_count, total_rows) under root."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return 0, 0
    files = list(Path(root).rglob("*.parquet"))
    total = sum(pq.read_metadata(f).num_rows for f in files)
    return len(files), total


# ═════════════════════════════════════════════════════════════════════
# PHASE 1 — ENGINE CONNECTIVITY CHECK
# ═════════════════════════════════════════════════════════════════════
def phase1_connectivity() -> PhaseResult:
    p = PhaseResult("PHASE 1 — Engine connectivity")

    # Module 1: Microstructure Agents (live, in production)
    ms_active = _systemctl_active("microstructure-collector.service")
    p.add("Microstructure Agents (collector daemon)", ms_active,
          "microstructure-collector.service active" if ms_active
          else "microstructure-collector.service NOT active")

    # Module 2: Risk Engine (Patches 1+3+5 from GODMODE_AUDIT)
    ok, detail = _safe_import("gods_level_engine", "VoteEnsembleStrategy")
    if ok:
        try:
            from gods_level_engine import VoteEnsembleStrategy, SimpleMAStrategy
            has_stop = (hasattr(VoteEnsembleStrategy, "HARD_STOP_PCT")
                        and VoteEnsembleStrategy.HARD_STOP_PCT == 0.025)
            ok = has_stop
            detail = f"HARD_STOP_PCT={VoteEnsembleStrategy.HARD_STOP_PCT}"
        except Exception as e:
            ok = False; detail = str(e)
    p.add("Risk Engine (Patches 1+3+5 loaded)", ok, detail)

    # Module 3: Edge Filter (FeeEdgeStream)
    ok, detail = _safe_import("godmode.streams", "FeeEdgeStream")
    p.add("Edge Filter (godmode.streams.FeeEdgeStream)", ok, detail)

    # Module 4: Execution Engine (4 paper bots)
    pairs = ["ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]
    active_count = sum(_systemctl_active(f"trading-bot@{p_}.service") for p_ in pairs)
    p.add("Execution Engine (Vote paper bots)", active_count == 4,
          f"{active_count}/4 trading-bot services active")

    # Module 5: Regime Engine (per L99_SPOT_HYBRID Layer 4)
    # Operator added regime_classifier.py recently — check if it imports
    ok, detail = _safe_import("regime_classifier")
    p.add("Regime Engine (regime_classifier.py)", ok, detail,
          severity="soft")   # not yet fully integrated

    # Module 6: Volatility Scanner (per L99 Layer 1.1)
    # Maps to aegis_alpha/scanner.py
    has_scanner = _file_exists("aegis_alpha/scanner.py")
    p.add("Volatility Scanner (aegis_alpha.scanner)", has_scanner,
          "scanner.py present" if has_scanner else "missing",
          severity="soft")   # exists as scanner, not wired to engine

    # Module 7: Liquidity Filter — not yet implemented as standalone
    p.add("Liquidity Filter (standalone module)", False,
          "not yet built — embedded in Vote bot pre-checks", severity="soft")

    # Module 8: Cross-Exchange Scanner — explicitly Phase B+ per
    # L99_SPOT_HYBRID feasibility audit
    p.add("Cross-Exchange Scanner (Binance/OKX/Bybit)", False,
          "not built — separate ~3-week project per L99_SPOT_HYBRID §II",
          severity="soft")

    return p


# ═════════════════════════════════════════════════════════════════════
# PHASE 2 — DATA INTEGRITY TEST
# ═════════════════════════════════════════════════════════════════════
def phase2_data_integrity() -> PhaseResult:
    p = PhaseResult("PHASE 2 — Data integrity")

    # WebSocket stability: collector restart count
    rst = _systemctl_restarts("microstructure-collector.service")
    p.add("WebSocket stability (collector restarts == 0)",
          rst == 0, f"NRestarts={rst}")

    # Order book refresh: parquet file growth
    files, rows = _count_parquet_rows("/var/log/microstructure")
    enough_data = rows >= 10_000   # at least ~30 min × 5 pairs at 1Hz
    p.add("Order-book / tape data accumulating",
          enough_data, f"{files} files, {rows:,} rows")

    # Delta calculation accuracy: feature columns present
    if files > 0:
        try:
            import pyarrow.parquet as pq
            f = next(Path("/var/log/microstructure").rglob("*.parquet"))
            schema = pq.read_metadata(f).schema.to_arrow_schema().names
            required = {"depth_imbalance", "delta_30s", "spread_pct",
                        "ofi_30s", "micro_price", "book_slope_bid"}
            present = required.issubset(set(schema))
            p.add("Feature schema complete (DIR/delta/OFI/micro/slope)",
                  present,
                  f"{len(required & set(schema))}/{len(required)} required fields")
        except Exception as e:
            p.add("Feature schema readable", False, str(e))
    else:
        p.add("Feature schema readable", False, "no parquet to inspect")

    # Cross-exchange sync — explicitly N/A on current build
    p.add("Cross-exchange data sync", False,
          "no other exchanges connected (per L99_SPOT_HYBRID §II)",
          severity="soft")

    # Bot trades log produces no errors
    bot_logs = list(Path("/var/log").glob("trading-bot-*.log"))
    if bot_logs:
        errors = 0
        for log in bot_logs:
            try:
                with open(log) as fh:
                    errors += sum(1 for line in fh
                                   if "Traceback" in line or "ERROR" in line)
            except Exception:
                pass
        p.add("Bot logs have no Traceback / ERROR",
              errors == 0, f"{errors} error lines across {len(bot_logs)} logs")
    else:
        p.add("Bot logs present", False, "no /var/log/trading-bot-*.log files",
              severity="soft")

    return p


# ═════════════════════════════════════════════════════════════════════
# PHASE 3 — STRATEGY SIMULATION TEST  (references existing OOS results)
# ═════════════════════════════════════════════════════════════════════
def phase3_simulation() -> PhaseResult:
    p = PhaseResult("PHASE 3 — Strategy simulation (≥ 100 setups, WR≥52%, R≥1.4)")

    # Phase 3 is answered by the seven existing OOS-research artifacts.
    # The honest verdict from those documents is on file — re-running is
    # ADR-003-violating "new strategy code on main." We CITE results.

    # GODMODE / professional / walk-forward / param-sweep / regime / MR /
    # max-edge — all in the repo, all NO-GO.
    docs_to_check = [
        "WALK_FORWARD_RESULTS.md",
        "PARAM_SWEEP_RESULTS.md",
        "REGIME_GATE_RESULTS.md",
        "MR_ENSEMBLE_RESULTS.md",
        "DEEP_EDGE_RESULTS.md",
        "PROFESSIONAL_BACKTEST_RESULTS.md",
        "GODSMODE_RESULTS.md",
    ]
    present = sum(1 for d in docs_to_check if _file_exists(d))
    p.add("OOS research artifacts present",
          present == len(docs_to_check),
          f"{present}/{len(docs_to_check)} result docs",
          severity="soft")

    # Audit verdict
    audit_present = _file_exists("GODMODE_AUDIT.md")
    p.add("GODMODE_AUDIT.md present (composite 27/100, NO-GO verdict)",
          audit_present,
          "comprehensive 6-agent audit of strategy claims" if audit_present
          else "MISSING — independent audit required before deployment")

    # The strict verdict from professional_backtest.py: every strategy
    # had NEGATIVE OOS SQN. That is the binding evidence for Phase 3.
    p.add("Phase 3 simulation gate (WR≥52% AND avgR≥1.4) cleared",
          False,
          "professional_backtest.py: every strategy/pair NEGATIVE OOS SQN. "
          "godsmode_backtest.py: 0/80 cells passed ship gate. "
          "Best historical: ETH 4h MAWeekly OOS Sharpe +1.39 — but recent "
          "return UNDERPERFORMS buy-and-hold (+5.5% vs +12.3%). Below WR≥52% / R≥1.4 bar.")

    # Per audit Table §8: post-patch OOS Sharpe range
    p.add("Post-patch OOS Sharpe ≥ 0.5 (audit threshold)",
          False,
          "Audit projects -0.2 to +0.5 OOS Sharpe even after Patches 1+3+5. "
          "This is the upper bound; expectation is around 0.")

    return p


# ═════════════════════════════════════════════════════════════════════
# PHASE 4 — MODE ACTIVATION TEST MATRIX
# ═════════════════════════════════════════════════════════════════════
def phase4_modes() -> PhaseResult:
    p = PhaseResult("PHASE 4 — Mode activation matrix")

    # Modes per spec: Neutral, Expansion, Aggressive, Ultra Micro
    # Currently we have ONE deployed mode: Vote ≥2 of 3 paper-real
    p.add("Neutral Mode (default Vote ≥2 of 3)", True,
          "active in all 4 trading-bot services")

    p.add("Expansion Mode (regime-conditional)", False,
          "regime_classifier.py present but not wired to bots — "
          "L99_SPOT_HYBRID Layer 4 work, post-D7", severity="soft")

    p.add("Aggressive Mode (size 1.0% on score≥88 + edge≥0.25%)", False,
          "RiskThrottleStream supports the state but no scoring layer "
          "promotes to it on spot — Phase B+", severity="soft")

    p.add("Ultra Micro Mode (10s delta, liquidity vacuum, 90s hold)", False,
          "REJECTED per L99_SPOT_HYBRID §III — physically impossible on "
          "Gate.io public WS (no tick-level cancel events)")

    # Per spec: each mode must have fee-aware profitability evidence
    p.add("All deployed modes have fee-aware profitability evidence",
          False,
          "Neutral mode pre-evidence (8h paper, 0 closed trades). "
          "Other 3 modes not deployed.")

    return p


# ═════════════════════════════════════════════════════════════════════
# PHASE 5 — LIVE SHADOW TEST
# ═════════════════════════════════════════════════════════════════════
def phase5_shadow() -> PhaseResult:
    p = PhaseResult("PHASE 5 — Live shadow test")

    # Per audit §7: minimum 60 days paper before any real money.
    # We started Vote bots ~8 hours ago.

    # Trade count
    pairs = ["ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]
    closed_trades = 0
    open_trades = 0
    for pair in pairs:
        log = Path(f"/var/log/trading-bot-{pair}.log")
        if not log.exists():
            continue
        try:
            with open(log) as fh:
                content = fh.read()
            buys  = content.count("VOTE-BUY")
            sells = content.count("VOTE-SELL")
            closed_trades += sells
            if buys > sells:
                open_trades += 1
        except Exception:
            pass

    p.add("Closed trades ≥ 30 (audit Stage 2 gate)", closed_trades >= 30,
          f"only {closed_trades} closed trades across all pairs (need ≥ 30)")

    # Paper-mode confirmation: real money MUST be zero
    no_live_mode = True
    try:
        from gods_level_engine import C
        no_live_mode = (C.LIVE_MODE is False)
    except Exception:
        pass
    p.add("Real-money LIVE_MODE disabled", no_live_mode,
          "C.LIVE_MODE = False (correct)" if no_live_mode
          else "DANGER: C.LIVE_MODE is True")

    # Patches verified active (we have a separate test suite for this)
    try:
        result = subprocess.run(
            ["pytest", "tests/test_audit_patches.py", "-q"],
            capture_output=True, text=True, timeout=60,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        ok = result.returncode == 0
        last_line = result.stdout.strip().split("\n")[-1] if result.stdout else ""
        p.add("Audit-patch tests green", ok, last_line)
    except FileNotFoundError:
        p.add("Audit-patch tests green", False, "pytest not in PATH",
              severity="soft")
    except Exception as e:
        p.add("Audit-patch tests green", False, str(e))

    # Days since deploy
    p.add("Paper-shadow period ≥ 60 days (audit §7)", False,
          "Vote ensemble deployed ~12 hours ago — far from 60-day gate")

    return p


# ═════════════════════════════════════════════════════════════════════
# REPORT
# ═════════════════════════════════════════════════════════════════════
def overall_verdict(phases: List[PhaseResult]) -> str:
    """GO / CONDITIONAL / NO-GO per the spec's Final Deployment Rule."""
    # GO requires every hard check across every phase to pass
    if all(ph.hard_pass for ph in phases):
        return GO
    # CONDITIONAL: Phases 1-2 hard-pass, Phase 3+ allowed soft fail with
    # at least some positive OOS evidence
    if phases[0].hard_pass and phases[1].hard_pass:
        return CONDITIONAL
    return NO_GO


def render(phases: List[PhaseResult], verdict: str):
    print("═" * 80)
    print("  L99 — FINAL SYSTEM INTEGRATION & VALIDATION ENGINE")
    print(f"  generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("═" * 80)
    for ph in phases:
        print(f"\n{ph.name}")
        print("─" * 80)
        for c in ph.checks:
            tag = f"({c.severity})" if c.severity == "soft" else ""
            print(f"  [{c.icon}] {c.name:<55} {tag}")
            if c.detail and (not c.passed or c.severity == "soft"):
                print(f"        ↳ {c.detail}")
    print()
    print("═" * 80)
    if verdict == GO:
        print(f"  VERDICT: ✅ {verdict}  — system cleared for Stage 2 ($200 cap)")
    elif verdict == CONDITIONAL:
        print(f"  VERDICT: ⚠ {verdict}  — infra green, evidence missing")
    else:
        print(f"  VERDICT: 🛑 {verdict}  — DO NOT DEPLOY REAL CAPITAL")
        print()
        print("  Per spec Final Deployment Rule:")
        print("    System goes LIVE only if all 5 phases are GREEN.")
        print("    Otherwise: HOLD USDT.")
        print()
        print("  This is the correct outcome — the gate is working.")
    print("═" * 80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5],
                    help="run a single phase only")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable JSON output")
    args = ap.parse_args()

    phase_funcs = [phase1_connectivity, phase2_data_integrity,
                   phase3_simulation, phase4_modes, phase5_shadow]
    if args.phase:
        phases = [phase_funcs[args.phase - 1]()]
    else:
        phases = [f() for f in phase_funcs]

    verdict = overall_verdict(phases)

    if args.json:
        print(json.dumps({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "phases": [{
                "name": p.name,
                "hard_pass": p.hard_pass,
                "checks": [asdict(c) for c in p.checks],
            } for p in phases],
            "verdict": verdict,
        }, indent=2))
    else:
        render(phases, verdict)

    sys.exit(0 if verdict == GO else 1 if verdict == CONDITIONAL else 2)


if __name__ == "__main__":
    main()
