"""
canary_killswitch.py — Multi-account watchdog (P1 remediation, 2026-05-23).

Rewrites the legacy single-account watchdog for the 3-account live battle.
Runs as a SEPARATE systemd service (canary-watchdog.service) from canary_executor.py.

TRIGGER CONDITIONS (any → write CANARY_HALT.json → executor stops on next cycle):
  1. MAX DRAWDOWN BREACH   — any account's daily_dd_usd >= its max_daily_dd cap
  2. API FAILURE STORM     — any account's consec_api_fails >= MAX_API_FAILS
  3. ABNORMAL POSITION     — any account holds > MAX_OPEN_POSITIONS open positions
  4. CORRUPTED BALANCE     — state file for an account is stale > STATE_STALE_SEC
                             OR cannot be JSON-parsed (torn write / OOM)

All trigger events are logged with KILLSWITCH_TRIGGER prefix so grep/journalctl
can find them: grep KILLSWITCH_TRIGGER /root/canary/runtime/watchdog.log

POLL cycle: every POLL_SEC (30s). Safe to restart at any time — idempotent.
"""
import json
import sys
import time
import signal
import logging
from pathlib import Path
from datetime import datetime, timezone

# ── Paths (mirror canary_executor.py layout) ─────────────────────────────────
ROOT     = Path("/root/canary")
RUNTIME  = ROOT / "runtime"
ARM_FILE = ROOT / "canary_arm.json"
HALT_FILE = RUNTIME / "CANARY_HALT.json"
L99_HALT  = Path("/root/.l99/protection_halt.json")
WATCHDOG_LOG = RUNTIME / "watchdog.log"

# Per-account state files (multi-account layout)
ACCOUNT_STATE_FILES = {
    "MAIN": RUNTIME / "state_main.json",
    "SUB1": RUNTIME / "state_sub1.json",
    "SUB2": RUNTIME / "state_sub2.json",
}

# Per-account DD caps (must match ACCOUNTS in canary_executor.py)
ACCOUNT_DD_CAPS = {
    "MAIN": 31.59,
    "SUB1": 4.00,
    "SUB2": 4.00,
}

# ── Watchdog thresholds ───────────────────────────────────────────────────────
POLL_SEC           = 30     # watchdog loop interval
STATE_STALE_SEC    = 120    # state file age before declaring hung (2 * POLL_INTERVAL_SEC=30 + margin)
MAX_API_FAILS      = 5      # matches executor's per-thread exit threshold
MAX_OPEN_POSITIONS = 4      # executor trades up to 4 pairs; > 4 = impossible / corrupted
MAX_LIFETIME_HOURS = 720    # matches executor MAX_LIFETIME_HOURS

# ── Logging ───────────────────────────────────────────────────────────────────
RUNTIME.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][WATCHDOG] %(message)s",
    handlers=[
        logging.FileHandler(str(WATCHDOG_LOG), mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("watchdog")


# ── Core halt machinery ───────────────────────────────────────────────────────

def trigger_halt(reason: str, account_id: str = "SYSTEM") -> None:
    """
    Write CANARY_HALT.json and exit. Executor reads this file on every loop
    iteration via check_halts() and will stop within POLL_INTERVAL_SEC (30s).

    All activations are logged with KILLSWITCH_TRIGGER so they are
    grep-findable: grep KILLSWITCH_TRIGGER /root/canary/runtime/watchdog.log
    """
    payload = {
        "halted": True,
        "reason": reason,
        "account_id": account_id,
        "triggered_by": "canary_killswitch_v2_multi_account",
        "ts": time.time(),
        "iso": datetime.now(timezone.utc).isoformat(),
    }
    try:
        HALT_FILE.write_text(json.dumps(payload, indent=2))
    except OSError as e:
        log.error("KILLSWITCH_TRIGGER: failed to write halt file: %s", e)
        # Still log and exit — executor will catch state stale next cycle
    log.error("KILLSWITCH_TRIGGER account=%s reason=%s", account_id, reason)
    log.error("KILLSWITCH_TRIGGER halt written to %s", HALT_FILE)
    log.error("KILLSWITCH_TRIGGER executor will stop within %ds", POLL_SEC)
    sys.exit(0)


def is_already_halted() -> bool:
    """Return True if halt is already engaged (avoid duplicate triggers)."""
    if HALT_FILE.exists():
        try:
            c = json.loads(HALT_FILE.read_text())
            if c.get("halted") is True:
                log.info("Halt already active: %s — watchdog idle", c.get("reason"))
                return True
        except Exception:
            pass
    return False


# ── Per-account check functions ───────────────────────────────────────────────

def load_account_state(account_id: str) -> dict | None:
    """
    Load and validate per-account state file.
    Returns None (with log) if missing, stale, or unparseable.
    Stale = file mtime > STATE_STALE_SEC old (executor writes every loop tick).
    """
    sf = ACCOUNT_STATE_FILES[account_id]
    if not sf.exists():
        log.warning("[%s] state file missing — executor not started yet?", account_id)
        return None
    age = time.time() - sf.stat().st_mtime
    if age > STATE_STALE_SEC:
        trigger_halt(
            f"state_stale: age={age:.0f}s > {STATE_STALE_SEC}s (executor may be hung or crashed)",
            account_id=account_id,
        )
    try:
        state = json.loads(sf.read_text())
        return state
    except Exception as e:
        trigger_halt(f"state_corrupted: {e}", account_id=account_id)
        return None


def check_drawdown(account_id: str, state: dict) -> None:
    """
    TRIGGER 1: MAX DRAWDOWN BREACH
    Fires if daily_dd_usd has reached or exceeded the per-account cap.
    The executor already enforces this inline but this is the external
    safety net if the in-process check is bypassed (e.g. state file written
    by a bug or external tool with a spoofed low value).
    """
    dd = float(state.get("daily_dd_usd", 0.0))
    cap = ACCOUNT_DD_CAPS.get(account_id, 999.0)
    if dd >= cap:
        trigger_halt(
            f"max_drawdown_breach: daily_dd_usd=${dd:.2f} >= cap=${cap:.2f}",
            account_id=account_id,
        )


def check_api_failure_storm(account_id: str, state: dict) -> None:
    """
    TRIGGER 2: API FAILURE STORM
    Fires if consec_api_fails has reached the threshold.
    The executor thread already exits at this point, but this watchdog
    ensures a HALT file is written so the service restart doesn't
    immediately re-enter the failure loop.
    """
    fails = int(state.get("consec_api_fails", 0))
    if fails >= MAX_API_FAILS:
        trigger_halt(
            f"api_failure_storm: consec_api_fails={fails} >= threshold={MAX_API_FAILS}",
            account_id=account_id,
        )


def check_position_state(account_id: str, state: dict) -> None:
    """
    TRIGGER 3: ABNORMAL POSITION STATE
    Fires if the number of open positions exceeds the number of tradeable
    pairs. This is structurally impossible in correct operation and indicates
    either a bug, a corrupted state file, or a manual injection.
    """
    positions = state.get("positions", {})
    if not isinstance(positions, dict):
        trigger_halt(
            f"abnormal_position_state: positions field is {type(positions).__name__}, expected dict",
            account_id=account_id,
        )
    n = len(positions)
    if n > MAX_OPEN_POSITIONS:
        trigger_halt(
            f"abnormal_position_state: {n} open positions > max {MAX_OPEN_POSITIONS}",
            account_id=account_id,
        )
    # Check each position has required fields (corrupted entry detection)
    required = {"side", "entry_price", "size_usdt", "size_base", "entry_ts"}
    for pair, pos in positions.items():
        if not isinstance(pos, dict):
            trigger_halt(
                f"abnormal_position_state: position[{pair}] is {type(pos).__name__}, expected dict",
                account_id=account_id,
            )
        missing = required - pos.keys()
        if missing:
            trigger_halt(
                f"abnormal_position_state: position[{pair}] missing fields: {missing}",
                account_id=account_id,
            )


def check_balance_state(account_id: str, state: dict) -> None:
    """
    TRIGGER 4: CORRUPTED BALANCE STATE
    Fires if session_pnl is non-finite (NaN/Inf) or daily_dd_usd is negative
    (impossible in correct operation — drawdown is always >= 0).
    A negative daily_dd_usd would mask real losses from TRIGGER 1.
    """
    try:
        pnl = float(state.get("session_pnl", 0.0))
        dd  = float(state.get("daily_dd_usd", 0.0))
    except (TypeError, ValueError) as e:
        trigger_halt(f"corrupted_balance_state: could not parse pnl/dd: {e}", account_id=account_id)
        return

    import math
    if not math.isfinite(pnl):
        trigger_halt(
            f"corrupted_balance_state: session_pnl is non-finite: {pnl}",
            account_id=account_id,
        )
    if not math.isfinite(dd):
        trigger_halt(
            f"corrupted_balance_state: daily_dd_usd is non-finite: {dd}",
            account_id=account_id,
        )
    if dd < 0:
        trigger_halt(
            f"corrupted_balance_state: daily_dd_usd=${dd:.4f} is negative (should be >= 0)",
            account_id=account_id,
        )


# ── System-level checks ───────────────────────────────────────────────────────

def check_l99_halt() -> None:
    """Propagate L99 protection halt if active."""
    if L99_HALT.exists():
        try:
            c = json.loads(L99_HALT.read_text())
            if c.get("halted") is True:
                trigger_halt(
                    f"l99_halt_propagated: {c.get('reason', 'unknown')}",
                    account_id="SYSTEM",
                )
        except Exception:
            pass


def check_lifetime(arm: dict) -> None:
    """Halt if the 720h lifetime cap is exceeded."""
    try:
        armed_at = datetime.fromisoformat(arm["armed_at"].replace("Z", "+00:00"))
        elapsed_h = (datetime.now(timezone.utc) - armed_at).total_seconds() / 3600.0
        if elapsed_h > MAX_LIFETIME_HOURS:
            trigger_halt(
                f"lifetime_exceeded: {elapsed_h:.2f}h > {MAX_LIFETIME_HOURS}h",
                account_id="SYSTEM",
            )
    except Exception as e:
        log.warning("check_lifetime parse error: %s", e)


# ── Main watchdog loop ────────────────────────────────────────────────────────

_shutdown = False


def _sig(s, f) -> None:
    global _shutdown
    log.warning("Signal %d received — watchdog clean exit", s)
    _shutdown = True


signal.signal(signal.SIGTERM, _sig)
signal.signal(signal.SIGINT, _sig)


def main() -> None:
    log.info("=" * 70)
    log.info("CANARY WATCHDOG v2 (multi-account) STARTING")
    log.info("Accounts: %s", list(ACCOUNT_STATE_FILES.keys()))
    log.info("DD caps: %s", ACCOUNT_DD_CAPS)
    log.info("Poll: %ds | Stale threshold: %ds | API fail threshold: %d",
             POLL_SEC, STATE_STALE_SEC, MAX_API_FAILS)
    log.info("=" * 70)

    arm: dict | None = None
    if ARM_FILE.exists():
        try:
            arm = json.loads(ARM_FILE.read_text())
            log.info("Armed at: %s", arm.get("armed_at"))
        except Exception as e:
            log.warning("arm file unreadable: %s — lifetime check disabled", e)
    else:
        log.warning("arm file missing — lifetime check disabled until arming")

    while not _shutdown:
        # Skip all checks if halt is already engaged
        if is_already_halted():
            time.sleep(POLL_SEC)
            continue

        # System-level checks
        check_l99_halt()
        if arm:
            check_lifetime(arm)

        # Per-account checks
        all_ok = True
        for account_id in ACCOUNT_STATE_FILES:
            state = load_account_state(account_id)
            if state is None:
                # load_account_state already triggered halt if stale/corrupted
                # If just missing (not yet started), skip silently
                all_ok = False
                continue
            check_drawdown(account_id, state)
            check_api_failure_storm(account_id, state)
            check_position_state(account_id, state)
            check_balance_state(account_id, state)

        if all_ok:
            # Summary log — visible in watchdog.log on each clean pass
            summary_parts = []
            for account_id in ACCOUNT_STATE_FILES:
                sf = ACCOUNT_STATE_FILES[account_id]
                if sf.exists():
                    try:
                        st = json.loads(sf.read_text())
                        pnl = float(st.get("session_pnl", 0))
                        dd  = float(st.get("daily_dd_usd", 0))
                        n   = len(st.get("positions", {}))
                        summary_parts.append(
                            f"{account_id}(pnl={pnl:+.2f} dd={dd:.2f} pos={n})"
                        )
                    except Exception:
                        pass
            log.info("OK | %s", " | ".join(summary_parts))

        time.sleep(POLL_SEC)

    log.info("Watchdog exit clean.")


if __name__ == "__main__":
    main()
