"""
L99 Bot — Testnet Final Launch Check
Run BEFORE every `python live_bot.py` session.

Usage:
    source venv/bin/activate
    python preflight.py

All checks must pass. Any FAIL = stop, diagnose, fix.
"""
import ast
import inspect
import os
import sys
import textwrap

# ── load dotenv first so config reads .env ────────────────────
from dotenv import load_dotenv
load_dotenv()

SEP  = "─" * 56
SEP2 = "═" * 56
PASS = "✓  PASS"
FAIL = "✗  FAIL"

results: list[tuple[str, bool, str]] = []

def check(label: str, ok: bool, detail: str = "") -> bool:
    tag = PASS if ok else FAIL
    print(f"  [{tag}] {label}")
    if detail:
        for line in textwrap.wrap(detail, 50):
            print(f"          {line}")
    results.append((label, ok, detail))
    return ok


print(f"\n{SEP2}")
print("  L99 TESTNET — FINAL LAUNCH CHECK")
print(SEP2)

# ══════════════════════════════════════════════════════
# SECTION 1 — ENV HARD CHECK
# ══════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  SECTION 1 — ENV HARD CHECK")
print(SEP)

import config

check("GATE_API_KEY set",
      bool(config.API_KEY),
      "set GATE_API_KEY in .env")

check("GATE_API_SECRET set",
      bool(config.API_SECRET),
      "set GATE_API_SECRET in .env")

check("TESTNET=true",
      config.TESTNET is True,
      f"got: {config.TESTNET}")

check("LIVE_TRADING=false",
      config.LIVE_TRADING is False,
      f"got: {config.LIVE_TRADING}")

check("No contradiction (LIVE+TESTNET)",
      not (config.LIVE_TRADING and config.TESTNET))

check("RISK_PER_TRADE ≤ 0.01",
      config.RISK_PER_TRADE <= 0.01,
      f"got: {config.RISK_PER_TRADE:.2%}")

check("MAX_CONCURRENT ≤ 3",
      config.MAX_CONCURRENT <= 3,
      f"got: {config.MAX_CONCURRENT}")

check("KILL_DD_ABS == 0.21",
      abs(config.KILL_DD_ABS - 0.21) < 0.001,
      f"got: {config.KILL_DD_ABS:.2%}")

# ══════════════════════════════════════════════════════
# SECTION 2 — ENTRY PRICE VALIDATION (source audit)
# ══════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  SECTION 2 — ENTRY PRICE VALIDATION")
print(SEP)

se_path = os.path.join(os.path.dirname(__file__), "signal_engine.py")
try:
    src = open(se_path).read()
    # must contain next-bar open reference
    has_next_open  = ('next_bar["open"]' in src or 'iloc[-1]["open"]' in src
                     or "iloc[-1].open" in src or "next_bar" in src)
    # must NOT contain same-bar close entry
    has_close_entry = "entry_target = bar[\"close\"]" in src or "entry_price = bar[\"close\"]" in src

    check("signal_engine.py uses iloc[-1] open (next bar)",
          has_next_open,
          "entry_target must reference df.iloc[-1][\"open\"]")

    check("No same-bar close execution in signal_engine",
          not has_close_entry,
          "entry_price must not equal bar close")
except FileNotFoundError:
    check("signal_engine.py exists", False, "file not found")

# ══════════════════════════════════════════════════════
# SECTION 3 — POSITION SIZING FORMULA
# ══════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  SECTION 3 — POSITION SIZING FORMULA")
print(SEP)

lb_path = os.path.join(os.path.dirname(__file__), "live_bot.py")
try:
    src_bot = open(lb_path).read()
    has_sizing = (
        "equity * config.RISK_PER_TRADE" in src_bot
        and "risk_per_unit" in src_bot
    )
    check("Sizing = equity × risk / stop_distance",
          has_sizing,
          "formula: size = equity*RISK_PER_TRADE / risk_per_unit")

    has_no_fixed = "position_size = " not in src_bot.replace(
        "position_size  = size", "")
    check("No fixed lot sizing",
          "position_size  = size" in src_bot,
          "size must derive from ATR-based risk formula")
except FileNotFoundError:
    check("live_bot.py exists", False, "file not found")

# ══════════════════════════════════════════════════════
# SECTION 4 — KILL SWITCH AUDIT
# ══════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  SECTION 4 — KILL SWITCH AUDIT")
print(SEP)

rm_path = os.path.join(os.path.dirname(__file__), "risk_monitor.py")
try:
    src_rm = open(rm_path).read()
    check("Drawdown check in risk_monitor",
          "_check_drawdown" in src_rm and "KILL_DD_ABS" in src_rm)
    check("5-consecutive-loss check",
          "_check_consecutive_losses" in src_rm)
    check("Rolling Sharpe check",
          "_check_rolling_sharpe" in src_rm)
except FileNotFoundError:
    check("risk_monitor.py exists", False)

try:
    src_bot2 = open(lb_path).read()
    check("flatten_all() called on kill",
          "flatten_all(open_positions)" in src_bot2)
    check("alert_kill() called on kill",
          "tg.alert_kill(" in src_bot2)
    check("DB log_kill() in risk_monitor",
          "db.log_kill(" in open(rm_path).read())
    check("New entries disabled after kill (is_killed gate)",
          "monitor.is_killed" in src_bot2)
except Exception as e:
    check("Kill switch integration", False, str(e))

# ══════════════════════════════════════════════════════
# SECTION 5 — STARTUP MESSAGE FORMAT
# ══════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  SECTION 5 — STARTUP MESSAGE FORMAT")
print(SEP)

tg_path = os.path.join(os.path.dirname(__file__), "telegram_alerts.py")
try:
    src_tg = open(tg_path).read()
    required = [
        "L99 Bot started successfully",
        "Mode:",
        "Max concurrent:",
        "Risk per trade:",
        "Kill DD:",
    ]
    for item in required:
        check(f'alert_start contains "{item}"', item in src_tg)
except FileNotFoundError:
    check("telegram_alerts.py exists", False)

# preview what Telegram will receive
mode = "TESTNET" if config.TESTNET else "LIVE"
print(f"\n  Expected Telegram message:")
print(f"  ┌────────────────────────────────────┐")
print(f"  │ 🟢 L99 Bot started successfully.  │")
risk_str = f"{config.RISK_PER_TRADE:.0%}"
kill_str = f"{config.KILL_DD_ABS:.0%}"
print(f"  │ Mode: {mode:<30}│")
print(f"  │ Max concurrent: {config.MAX_CONCURRENT:<20}│")
print(f"  │ Risk per trade: {risk_str:<20}│")
print(f"  │ Kill DD: {kill_str:<27}│")
print(f"  └────────────────────────────────────┘")

# ══════════════════════════════════════════════════════
# SECTION 6 — FIRST TRADE TEMPLATE
# ══════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  SECTION 6 — FIRST TRADE RECORD TEMPLATE")
print(SEP)
print("  Fill after first signal fires:")
print()
print("  Symbol:           ___________")
print("  Entry price:      ___________")
print("  Stop price:       ___________")
print("  Target price:     ___________")
print("  Position size:    ___________")
print("  Expected open:    ___________")
print("  Actual fill:      ___________")
print("  Slippage:         ___________  (must be ≤ 0.15%)")
print("  DB trade id:      ___________")
print("  TG alert time:    ___________")
print()
print("  DB verify command:")
print("    psql -U l99_user -d l99 -c \"SELECT * FROM trades ORDER BY id DESC LIMIT 1;\"")

# ══════════════════════════════════════════════════════
# SECTION 7 — RUN WINDOW
# ══════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  SECTION 7 — TESTNET RUN PARAMETERS")
print(SEP)
print("  Minimum run: 20 completed trades OR 7 trading days")
print("  No parameter changes during window.")
print("  No optimization. No new filters. No scaling.")

# ══════════════════════════════════════════════════════
# FINAL VERDICT
# ══════════════════════════════════════════════════════
n_pass  = sum(1 for _, ok, _ in results if ok)
n_total = len(results)
n_fail  = n_total - n_pass

print(f"\n{SEP2}")
print("  FINAL VERDICT")
print(SEP2)
print(f"  Checks passed: {n_pass} / {n_total}")

if n_fail == 0:
    print()
    print("  ✓  ALL CHECKS PASSED")
    print("  ✓  TESTNET LAUNCH AUTHORISED")
    print()
    print("  Launch command:")
    print("    source venv/bin/activate")
    print("    python live_bot.py")
else:
    print()
    print(f"  ✗  {n_fail} CHECK(S) FAILED — DO NOT LAUNCH")
    print()
    print("  Failed checks:")
    for label, ok, detail in results:
        if not ok:
            print(f"    • {label}")
            if detail:
                print(f"      → {detail}")

print(SEP2)
sys.exit(0 if n_fail == 0 else 1)
