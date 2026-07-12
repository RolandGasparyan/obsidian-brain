#!/usr/bin/env python3
"""ops/scoring.py — L3 championship scorer.

Parses canary/runtime/battle.log and emits a real per-account leaderboard
across six categories (PnL, Sharpe, Stability, Survival, Execution,
Recovery), assigns titles, and prints a ranked championship.

SAFE ZONE: pure read-only against the log. No live execution, no order
path, no governance mutation. The L3 layer is a cinematic competition
overlay; the underlying strategy on every account is the same SHA256-
locked MA50W10.

Log line patterns recognised (permissive — both styles match):

  Account identifier (case-insensitive):
    [main] / [sub1] / [sub2]           (real canary_executor format)
    MAIN  / SUB1  / SUB2               (operator's token style)

  PnL:    "pnl=$0.4231" or "PnL +0.42" or "PnL: 0.42"
  Sharpe: "Sharpe 1.40" or "sharpe=1.4"
  DD:     "DD 0.10" or "maxdd=0.10"
  Exec:   tokens BUY / SELL / LONG / SHORT
  Failure: token FAIL-CLOSED

Scoring (each enabled category contributes 1..N points per account; top
account in the category gets N points where N = number of ranked
accounts):

  pnl       higher latest PnL = better
  sharpe    higher latest Sharpe = better
  survival  lower latest DD = better
  stability lower pstdev(PnL samples) = better
  execution higher exec / (exec + failclosed) = better
  recovery  fewer FAIL-CLOSED = better

Categories with no parseable data across all accounts are skipped.
"""
from __future__ import annotations

import argparse
import os
import re
import statistics
import sys
from typing import Callable, Optional


ACCOUNTS = ("main", "sub1", "sub2")

LABELS = {
    "main": os.environ.get("MAIN_LABEL", "TITAN"),
    "sub1": os.environ.get("SUB1_LABEL", "VELOCITY"),
    "sub2": os.environ.get("SUB2_LABEL", "SENTINEL"),
}

TITLES = {
    "pnl":      os.environ.get("TITLE_PNL_KING",  "MONEY EMPEROR"),
    "sharpe":   os.environ.get("TITLE_SHARPE",    "PRECISION KING"),
    "survival": os.environ.get("TITLE_SURVIVAL",  "SURVIVAL TITAN"),
    "speed":    os.environ.get("TITLE_SPEED",     "MOMENTUM HUNTER"),
}

ENABLED = {
    "pnl":       os.environ.get("SCORE_PNL",       "1") == "1",
    "sharpe":    os.environ.get("SCORE_SHARPE",    "1") == "1",
    "stability": os.environ.get("SCORE_STABILITY", "1") == "1",
    "survival":  os.environ.get("SCORE_SURVIVAL",  "1") == "1",
    "execution": os.environ.get("SCORE_EXECUTION", "1") == "1",
    "recovery":  os.environ.get("SCORE_RECOVERY",  "1") == "1",
}

STRATEGY_NAME = os.environ.get("STRATEGY_NAME", "MA50W10")

ROUND_MICRO  = os.environ.get("MICRO_ROUND_MIN",  "15")
ROUND_BATTLE = os.environ.get("BATTLE_ROUND_MIN", "60")
ROUND_WAR    = os.environ.get("WAR_ROUND_HOURS",  "6")

NUMBER = r"[+-]?\d+(?:\.\d+)?"

ACCT_BRACKET_RE = re.compile(r"\[(main|sub1|sub2)\]", re.IGNORECASE)
ACCT_TOKEN_RE   = re.compile(r"\b(MAIN|SUB1|SUB2)\b")
PNL_RE          = re.compile(
    rf"(?:\bpnl[=: ]\$?|PnL[=: ]\s*)({NUMBER})", re.IGNORECASE)
SHARPE_RE       = re.compile(rf"\bsharpe[=: ]\s*({NUMBER})", re.IGNORECASE)
DD_RE           = re.compile(
    rf"\b(?:maxdd|dd)[=: ]\s*({NUMBER})", re.IGNORECASE)
EXEC_RE         = re.compile(r"\b(BUY|SELL|LONG|SHORT)\b")
FAIL_RE         = re.compile(r"\bFAIL-CLOSED\b")


class AccountStats:
    __slots__ = ("pnl", "sharpe", "dd", "executions", "failures")

    def __init__(self) -> None:
        self.pnl: list[float] = []
        self.sharpe: list[float] = []
        self.dd: list[float] = []
        self.executions = 0
        self.failures = 0

    @property
    def latest_pnl(self) -> Optional[float]:
        return self.pnl[-1] if self.pnl else None

    @property
    def latest_sharpe(self) -> Optional[float]:
        return self.sharpe[-1] if self.sharpe else None

    @property
    def latest_dd(self) -> Optional[float]:
        return self.dd[-1] if self.dd else None

    @property
    def stability(self) -> Optional[float]:
        if len(self.pnl) < 2:
            return None
        return statistics.pstdev(self.pnl)

    @property
    def execution_rate(self) -> Optional[float]:
        total = self.executions + self.failures
        if total == 0:
            return None
        return self.executions / total

    @property
    def recovery(self) -> float:
        return 1.0 / (1.0 + self.failures)


def identify_account(line: str) -> Optional[str]:
    m = ACCT_BRACKET_RE.search(line)
    if m:
        return m.group(1).lower()
    m = ACCT_TOKEN_RE.search(line)
    if m:
        return m.group(1).lower()
    return None


def parse_log(path: str) -> tuple[dict[str, AccountStats], int]:
    stats = {a: AccountStats() for a in ACCOUNTS}
    if not os.path.isfile(path):
        return stats, 0
    parsed_lines = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            acct = identify_account(line)
            if acct is None or acct not in stats:
                continue
            s = stats[acct]
            had_signal = False
            m = PNL_RE.search(line)
            if m:
                s.pnl.append(float(m.group(1))); had_signal = True
            m = SHARPE_RE.search(line)
            if m:
                s.sharpe.append(float(m.group(1))); had_signal = True
            m = DD_RE.search(line)
            if m:
                s.dd.append(float(m.group(1))); had_signal = True
            if EXEC_RE.search(line):
                s.executions += 1; had_signal = True
            if FAIL_RE.search(line):
                s.failures += 1; had_signal = True
            if had_signal:
                parsed_lines += 1
    return stats, parsed_lines


def rank_category(
    stats: dict[str, AccountStats],
    metric: Callable[[AccountStats], Optional[float]],
    higher_is_better: bool,
) -> dict[str, int]:
    """Return {account: points}. Top-ranked account gets len(ranked) points,
    next gets len(ranked)-1, etc. Accounts with no data get 0."""
    values = []
    for a, s in stats.items():
        v = metric(s)
        if v is None:
            continue
        values.append((a, v))
    if not values:
        return {a: 0 for a in stats}
    values.sort(key=lambda x: x[1], reverse=higher_is_better)
    points = {a: 0 for a in stats}
    n = len(values)
    for i, (a, _) in enumerate(values):
        points[a] = n - i
    return points


CATEGORY_DEFS = [
    ("pnl",       lambda s: s.latest_pnl,    True),
    ("sharpe",    lambda s: s.latest_sharpe, True),
    ("survival",  lambda s: s.latest_dd,     False),
    ("stability", lambda s: s.stability,     False),
    ("execution", lambda s: s.execution_rate, True),
    ("recovery",  lambda s: s.recovery,      True),
]


def fmt_num(v: Optional[float], fmt: str = "{:+.2f}", missing: str = "—") -> str:
    return missing if v is None else fmt.format(v)


def fmt_pct(v: Optional[float], missing: str = "—") -> str:
    return missing if v is None else f"{v * 100:5.1f}%"


def hr() -> None:
    print("=" * 50)


def render(stats: dict[str, AccountStats], parsed_lines: int) -> int:
    """Render the leaderboard. Returns process exit code."""
    hr()
    print("Cinematic competition layer only.")
    print(f"All accounts execute the same SHA256-locked {STRATEGY_NAME} strategy.")
    hr()
    print()
    print("🏆 L3 CHAMPIONSHIP LEADERBOARD")
    print(f"Rounds: micro={ROUND_MICRO}m  battle={ROUND_BATTLE}m  war={ROUND_WAR}h")
    print()

    if parsed_lines == 0:
        print("(no scoring signals parsed from battle.log yet)")
        print("(once trades emit PnL/Sharpe/DD/BUY/SELL/FAIL-CLOSED lines,")
        print(" this leaderboard will show real per-account scores)")
        print()
        hr()
        print("Cinematic competition layer only.")
        print("All accounts execute the same")
        print(f"SHA256-locked {STRATEGY_NAME} strategy.")
        hr()
        return 0

    # Compute per-category points
    cat_points: dict[str, dict[str, int]] = {}
    for name, metric, higher in CATEGORY_DEFS:
        if not ENABLED.get(name, True):
            continue
        cat_points[name] = rank_category(stats, metric, higher)

    # Per-account row
    header = f"{'ACCOUNT':<10} {'PnL':>8} {'Sharpe':>7} {'DD':>6} " \
             f"{'Stab':>6} {'Exec':>7} {'Recov':>6} {'TOTAL':>6}"
    print(header)
    print("-" * len(header))

    totals: dict[str, int] = {a: 0 for a in stats}
    for a in ACCOUNTS:
        s = stats[a]
        row_total = sum(cat_points.get(c, {}).get(a, 0) for c in cat_points)
        totals[a] = row_total
        print(
            f"{LABELS[a]:<10} "
            f"{fmt_num(s.latest_pnl):>8} "
            f"{fmt_num(s.latest_sharpe, '{:.2f}'):>7} "
            f"{fmt_num(s.latest_dd, '{:.2f}'):>6} "
            f"{fmt_num(s.stability, '{:.3f}'):>6} "
            f"{fmt_pct(s.execution_rate):>7} "
            f"{s.recovery:>6.3f} "
            f"{row_total:>6}"
        )
    print()

    # Title assignments
    def top_of(category: str) -> Optional[str]:
        points = cat_points.get(category)
        if not points:
            return None
        # Top is the account with the highest points in this category, but
        # only if any account actually scored > 0 (data existed).
        best_a, best_p = max(points.items(), key=lambda kv: kv[1])
        return LABELS[best_a] if best_p > 0 else None

    print("TITLES")
    print(f"  {TITLES['pnl']:<16} {top_of('pnl')      or '—'}")
    print(f"  {TITLES['sharpe']:<16} {top_of('sharpe') or '—'}")
    print(f"  {TITLES['survival']:<16} {top_of('survival') or '—'}")
    # "Speed" maps to execution rate as a stand-in until a dedicated latency
    # signal is available in the log.
    print(f"  {TITLES['speed']:<16} {top_of('execution') or '—'}")
    print()

    # Final championship — sort by total points; tie-break by latest PnL desc.
    ranking = sorted(
        ACCOUNTS,
        key=lambda a: (totals[a], stats[a].latest_pnl or 0.0),
        reverse=True,
    )
    print("🏆 FINAL CHAMPIONSHIP")
    for i, a in enumerate(ranking, start=1):
        print(f"  {i}. {LABELS[a]:<10} {totals[a]:>4} pts")
    print()
    hr()
    print("Cinematic competition layer only.")
    print("All accounts execute the same")
    print(f"SHA256-locked {STRATEGY_NAME} strategy.")
    hr()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="L3 championship scorer (SAFE ZONE, read-only)")
    ap.add_argument(
        "--battle-log",
        default=os.environ.get("BATTLE_LOG", "/root/canary/runtime/battle.log"),
        help="path to battle.log",
    )
    args = ap.parse_args()

    if not os.path.isfile(args.battle_log):
        hr()
        print("Cinematic competition layer only.")
        print(f"All accounts execute the same SHA256-locked {STRATEGY_NAME} strategy.")
        hr()
        print()
        print(f"(no battle log at {args.battle_log})")
        print()
        hr()
        return 0

    stats, parsed = parse_log(args.battle_log)
    return render(stats, parsed)


if __name__ == "__main__":
    sys.exit(main())
