#!/usr/bin/env python3
"""
canary_executor.py — Multi-Account Live Battle · CMO_CHANDE v2 + SCALP_SHORT
DNA Championship Rules — LAB-PROVEN UPGRADE (200k+ paper trades analyzed)
  Lab Winner: Chande Momentum Oscillator + SCALP_SHORT = $1,103 PnL (12,472 trades)
  Runner-up:  CMO + MOMENTUM_SHORT = $952 PnL (12,329 trades)
  Mode: SPOT | Trade Size: $5 USDT | TP: 0.25% | SL: 0.15%
  Cooldown: 45s | Max Concurrent: 3 | Daily DD Cap: 5%
  Signal: CMO > 20 (tighter) + RSI > 52 + Volume surge confirmation
  SCALP_SHORT mode: aggressive entry on momentum, fast exit on reversal
  Proven Pairs: FLOKI WIF OP SHIB DOT ADA UNI ATOM BNB
  AVOID: XRP ETH BTC INJ (negative CMO backtest PnL)
3 accounts trade simultaneously:
  TITAN (MAIN) ~$1534 | VELOCITY (SUB1) ~$213 | SENTINEL (SUB2) ~$203
API keys: /root/canary/.api_key_main  .api_key_sub1  .api_key_sub2
"""
import json
import os
import sys
import time
import signal
import logging
import threading
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    import ccxt  # noqa: F401  required at runtime, optional for offline preflight (check_agents.py)
except ImportError:
    ccxt = None

ROOT         = Path("/root/canary")
RUNTIME      = ROOT / "runtime"
ARM_FILE     = ROOT / "canary_arm.json"
HALT_FILE    = RUNTIME / "CANARY_HALT.json"
L99_HALT     = Path("/root/.l99/protection_halt.json")
STATUS_FILE  = RUNTIME / "multi_battle_status.json"
FRONTEND_PUB = Path("/var/www/ai-trading-championship/dist/api/battle/live_battle.json")
TERMINAL_PUB = Path("/var/www/ai-trading-championship/dist/api/battle/terminal.json")

# agent_label is a CINEMATIC field only — surfaced via publish_status into
# terminal.json/live_battle.json so the frontend can render champion names
# (👑 TITAN / ⚡ VELOCITY / 🛡️ SENTINEL). It does NOT affect any trading
# logic, keyfile lookup, log filename, or governance check — those all
# continue to key off the canonical "id" (MAIN/SUB1/SUB2). Per
# docs/9-refusals-log.md: telemetry labels are explicitly allowed; live
# agent identity / strategy mutation is not.
ACCOUNTS = [
    {"id":"MAIN", "agent_label":"TITAN",    "api_key_file":ROOT/".api_key_main", "max_capital":1579.52,
     "balance_ceil":1650.0, "trade_size_pct":0.06, "max_daily_dd":31.59,
     "state_file":RUNTIME/"state_main.json", "log_file":RUNTIME/"trades_main.log"},
    {"id":"SUB1", "agent_label":"VELOCITY", "api_key_file":ROOT/".api_key_sub1", "max_capital":200.0,
     "balance_ceil":220.0,  "trade_size_pct":0.09, "max_daily_dd":4.0,
     "state_file":RUNTIME/"state_sub1.json", "log_file":RUNTIME/"trades_sub1.log"},
    {"id":"SUB2", "agent_label":"SENTINEL", "api_key_file":ROOT/".api_key_sub2", "max_capital":200.0,
     "balance_ceil":220.0,  "trade_size_pct":0.09, "max_daily_dd":4.0,
     "state_file":RUNTIME/"state_sub2.json", "log_file":RUNTIME/"trades_sub2.log"},
]

# CMO_CHANDE v2 proven pairs (sorted by Profit Factor from backtest)
# AVOID: XRP/USDT, ETH/USDT, BTC/USDT, INJ/USDT (negative CMO PnL)
# EDGE_v1.1 (2026-06-02): Restricted from 9 → top-3 PF pairs after Monte Carlo
# showed break-even WR is 60% (maker-maker fees); lower-PF pairs dilute basket WR.
# Full list preserved as ALL_PAIRS_FULL for reference / future re-enabling.
ALL_PAIRS_FULL      = ["FLOKI/USDT", "WIF/USDT", "OP/USDT", "SHIB/USDT",
                       "DOT/USDT", "ADA/USDT", "UNI/USDT", "ATOM/USDT", "BNB/USDT"]
ALL_PAIRS           = ["FLOKI/USDT", "WIF/USDT", "OP/USDT"]  # PF 4.43 / 3.12 / 2.37
MAX_LIFETIME_HOURS  = 720
POLL_INTERVAL_SEC   = 20       # faster polling (was 30s) for SCALP_SHORT mode
# CMO_CHANDE v2 parameters — LAB-PROVEN (200k+ paper trades)
# Lab result: CMO+SCALP_SHORT = $1,103 PnL | CMO+MOMENTUM_SHORT = $952 PnL
COOLDOWN_SEC        = 45       # 45s cooldown (tighter for SCALP_SHORT)
MAX_TRADES_PER_DAY  = 80       # more trades in SCALP_SHORT mode
MAX_HOLD_HOURS      = 0.083    # 5 min max hold (faster exit = SCALP_SHORT)
DAILY_CANDLE_LIMIT  = 50       # more candles for better CMO accuracy
CMO_PERIOD          = 14       # Chande Momentum Oscillator period
CMO_THRESHOLD       = 20       # CMO > 20 (tighter = higher quality signals)
CMO_MOMENTUM_THRESH = 35       # CMO > 35 = STRONG momentum (double position)
RSI_PERIOD          = 14       # RSI confirmation period
RSI_BUY_THRESHOLD   = 52       # RSI > 52 (slightly lower = more entries)
VOLUME_CANDLES      = 10       # candles for volume surge detection
VOLUME_SURGE_MULT   = 1.3      # volume must be 1.3x average (surge confirmation)
TP_PCT              = 0.0025   # 0.25% take profit (lab shows higher TP better)
SL_PCT              = 0.0015   # 0.15% stop loss (unchanged)
MAX_CONCURRENT_POS  = 3        # max open positions per account
TRADE_SIZE_USDT     = 15.0     # TIER_2 $15 per trade (was $5) — 2026-06-02
# Championship: 60-minute rounds. Anchored to arm.armed_at. Each round captures
# per-account session_pnl_at_round_start so we can derive round-by-round PnL
# deltas, rank champions, and crown the top earner of each round.
ROUND_INTERVAL_SEC  = 3600
ROUND_HISTORY_LIMIT = 48  # keep last 48 rounds (= 48h history)
LIVE_BANNER         = "MULTI-ACCOUNT LIVE BATTLE: CMO_CHANDE v2 SCALP_SHORT | v1.2 GHOST-CLEAR FIX | MAIN+SUB1+SUB2"

RUNTIME.mkdir(parents=True, exist_ok=True)
# Bug fix: previously had both a FileHandler(battle.log) AND a StreamHandler(stdout),
# while the systemd unit ALSO redirects stdout to battle.log — every line was being
# written twice. Now: only stdout. systemd captures stdout → battle.log + journalctl.
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("BATTLE")
_shutdown = threading.Event()
# True iff shutdown was initiated by an external signal (SIGTERM/SIGINT —
# e.g. `systemctl stop`). False means shutdown was internal (all threads
# died, typically from a halt file). Used at end of main() to choose the
# exit code:
#   external signal  → exit 0 (operator chose to stop — systemd respects it)
#   internal/threads → exit 99 (Restart=on-failure fires → systemd retries,
#                               so the service auto-resumes once the halt
#                               artifact is cleared by the operator)
_signal_received = False

def _sig(s, f):
    global _signal_received
    log.info("Signal — shutting down")
    _signal_received = True
    _shutdown.set()
signal.signal(signal.SIGTERM, _sig)
signal.signal(signal.SIGINT,  _sig)

def fail_closed(r): log.error("FAIL-CLOSED: %s", r); sys.exit(1)

def check_arm():
    if not ARM_FILE.exists(): fail_closed(f"arm file missing: {ARM_FILE}")
    try: arm = json.loads(ARM_FILE.read_text())
    except Exception as e: fail_closed(f"arm unreadable: {e}")
    for k in ["armed_by","armed_at","ack_max_loss_usd","ack_time_cap_hours","paper_preflight_passed"]:
        if k not in arm: fail_closed(f"arm missing key: {k}")
    if arm["paper_preflight_passed"] is not True: fail_closed("paper preflight not passed")
    return arm

def check_halts():
    for hf in (L99_HALT, HALT_FILE):
        if hf.exists():
            try:
                c = json.loads(hf.read_text())
                if c.get("halted") is True: fail_closed(f"halt active: {hf}")
            except json.JSONDecodeError: fail_closed(f"halt unparseable: {hf}")

def check_clock(arm):
    at = datetime.fromisoformat(arm["armed_at"].replace("Z","+00:00"))
    elapsed = (datetime.now(timezone.utc)-at).total_seconds()/3600
    if elapsed > MAX_LIFETIME_HOURS: fail_closed(f"lifetime cap: {elapsed:.1f}h")

def load_creds(key_file):
    p = Path(key_file)
    if not p.exists(): fail_closed(f"key file missing: {p}")
    perms = oct(p.stat().st_mode)[-3:]
    if perms != "600": fail_closed(f"key file perms {perms} not 600: {p}")
    # Split first, THEN strip each side — protects against paste errors that
    # leave whitespace inside the key or secret (a single trailing space on
    # the API key produces INVALID_SIGNATURE at Gate.io with no other clue).
    raw = p.read_text().split(":")
    if len(raw) != 2: fail_closed(f"key file malformed (need KEY:SECRET): {p}")
    k, s = raw[0].strip(), raw[1].strip()
    if not k or not s: fail_closed(f"key file malformed (empty side): {p}")
    return k, s

def make_ex(account):
    if ccxt is None: fail_closed("ccxt not installed")
    k, s = load_creds(account["api_key_file"])
    return ccxt.gate({"apiKey":k,"secret":s,"enableRateLimit":True,"timeout":15000,
        "options":{"defaultType":"spot","createMarketBuyOrderRequiresPrice":False}})

def make_ex_public():
    """Unauthenticated ccxt for ticker / OHLCV. No key needed → not affected by bad API keys."""
    if ccxt is None: fail_closed("ccxt not installed")
    return ccxt.gate({"enableRateLimit":True,"timeout":15000,
        "options":{"defaultType":"spot"}})

def check_bal(ex, account):
    try: bal = ex.fetch_balance()
    except Exception as e: fail_closed(f"[{account['id']}] fetch_balance: {e}")
    free = float(bal.get("USDT",{}).get("free",0))
    if free > account["balance_ceil"]: fail_closed(f"[{account['id']}] balance ${free:.2f} > ceil ${account['balance_ceil']}")
    log.info("[%s] balance OK $%.2f USDT", account["id"], free)
    return free

def init_state(account):
    return {"account_id":account["id"],"positions":{},"trades_today":0,
            "current_date":"1970-01-01","session_pnl":0.0,
            "session_start":datetime.now(timezone.utc).isoformat(),
            "daily_dd_usd":0.0,"consec_api_fails":0,"last_exit_ts":{},
            # Championship 60-min rounds:
            # round_anchors[str(round_id)] = {"started_at": iso, "session_pnl_at_start": float}
            # When a new round begins (every 60 min from arm.armed_at), record the
            # account's current session_pnl. Round N's PnL = anchor[N+1] - anchor[N];
            # for the in-flight current round, end = current session_pnl.
            "round_anchors":{},"last_seen_round_id":0,
            # EDGE_v1.1 — rolling last-100 outcomes for live decision-gate WR.
            # Each entry is 1 for WIN, 0 for LOSS. PnL list parallels for avg-pnl.
            "rolling_outcomes":[],"rolling_pnls":[]}

def load_state(account):
    sf = Path(account["state_file"])
    if sf.exists():
        try:
            st = json.loads(sf.read_text())
            # Migrate older states that lack round-tracking fields
            st.setdefault("round_anchors", {})
            st.setdefault("last_seen_round_id", 0)
            # EDGE_v1.1 migration for pre-existing state files.
            st.setdefault("rolling_outcomes", [])
            st.setdefault("rolling_pnls", [])
            return st
        except Exception:
            pass
    return init_state(account)

def round_id_now(arm):
    """Current 60-min round number, 1-indexed from arm.armed_at."""
    at = datetime.fromisoformat(arm["armed_at"].replace("Z", "+00:00"))
    elapsed = (datetime.now(timezone.utc) - at).total_seconds()
    return int(elapsed // ROUND_INTERVAL_SEC) + 1

def round_started_at(arm, round_id):
    """ISO timestamp when round N began."""
    at = datetime.fromisoformat(arm["armed_at"].replace("Z", "+00:00"))
    return (at + (round_id - 1) * timedelta(seconds=ROUND_INTERVAL_SEC)).isoformat()

def maybe_anchor_round(state, arm):
    """If a new 60-min round has just begun, record session_pnl as that round's
    anchor (per-account starting point). Idempotent — only runs at boundary."""
    rid = round_id_now(arm)
    if rid > state.get("last_seen_round_id", 0):
        state["round_anchors"][str(rid)] = {
            "started_at": round_started_at(arm, rid),
            "session_pnl_at_start": float(state.get("session_pnl", 0.0)),
        }
        state["last_seen_round_id"] = rid

def build_rounds_view(states, arm):
    """For each completed + current round, compute per-champion PnL delta + crown
    the round winner. Returns list of round dicts (most recent first, capped to
    ROUND_HISTORY_LIMIT). Used by publish_status to write the championship
    scoreboard into terminal.json / live_battle.json."""
    rounds = []
    current_rid = round_id_now(arm)
    # Walk rounds from most recent downward
    for rid in range(current_rid, max(0, current_rid - ROUND_HISTORY_LIMIT), -1):
        per_champion = []
        for s in states:
            aid = s.get("account_id", "?")
            anchors = s.get("round_anchors", {})
            start_anchor = anchors.get(str(rid))
            if not start_anchor:
                # account hadn't existed yet during this round (e.g. dead at startup)
                per_champion.append({"account_id": aid, "round_pnl": None, "status": "no_data"})
                continue
            start_pnl = float(start_anchor.get("session_pnl_at_start", 0.0))
            if rid == current_rid:
                # Round in progress: end = current session_pnl
                end_pnl = float(s.get("session_pnl", 0.0))
                in_progress = True
            else:
                # Completed round: end = next round's start anchor (if recorded)
                next_anchor = anchors.get(str(rid + 1))
                end_pnl = float(next_anchor["session_pnl_at_start"]) if next_anchor else start_pnl
                in_progress = False
            per_champion.append({
                "account_id": aid,
                "round_pnl_usd": round(end_pnl - start_pnl, 6),
                "status": "in_progress" if in_progress else "completed",
            })
        # Crown the round winner — highest round_pnl_usd among accounts with data
        valid = [c for c in per_champion if c.get("round_pnl_usd") is not None]
        winner = max(valid, key=lambda c: c["round_pnl_usd"])["account_id"] if valid else None
        rounds.append({
            "round_id": rid,
            "started_at": round_started_at(arm, rid),
            "in_progress": (rid == current_rid),
            "winner_account_id": winner,
            "champions": per_champion,
        })
    return rounds

def save_state(account, state):
    """Persist state atomically. Writes to <state_file>.tmp first, fsyncs the
    bytes, then os.replace()s into place — so a SIGKILL / power-loss / OOM
    mid-write can never leave a half-written state file. os.replace is atomic
    on the same filesystem (POSIX rename semantics), so readers either see
    the previous good state or the new good state — never a torn write.

    Why this matters: state.positions tracks open Gate.io positions. A torn
    write that JSON-corrupts the file would make those positions invisible
    to the executor on next start, while the exchange still holds them."""
    sf = Path(account["state_file"])
    tmp = sf.with_suffix(sf.suffix + ".tmp")
    data = json.dumps(state, indent=2)
    # Use a low-level FD so we can fsync before the rename.
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp), str(sf))

def score_pairs(ex):
    scores = {}
    for pair in ALL_PAIRS:
        try:
            t = ex.fetch_ticker(pair)
            pct = float(t.get("percentage",0) or 0)
            vol = float(t.get("quoteVolume",0) or 1)
            scores[pair] = pct*0.4 + math.log10(max(vol,1))*0.6
        except Exception as e:
            log.warning("score %s: %s", pair, e); scores[pair]=-999
    ranked = sorted(scores, key=lambda p: scores[p], reverse=True)
    log.info("Pairs ranked: %s", [(p,round(scores[p],2)) for p in ranked])
    return ranked

def _calc_cmo(closes: list, period: int = 14) -> float:
    """Chande Momentum Oscillator: (sum_up - sum_down) / (sum_up + sum_down) * 100"""
    if len(closes) < period + 1:
        return 0.0
    diffs = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    recent = diffs[-period:]
    sum_up   = sum(d for d in recent if d > 0)
    sum_down = sum(abs(d) for d in recent if d < 0)
    total = sum_up + sum_down
    if total == 0:
        return 0.0
    return (sum_up - sum_down) / total * 100.0

def _calc_rsi(closes: list, period: int = 14) -> float:
    """RSI for momentum confirmation"""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def _calc_volume_surge(candles: list, lookback: int = 10, mult: float = 1.3) -> bool:
    """Volume surge: current volume > mult * avg of last N candles.
    SCALP_SHORT mode: only enter when volume confirms momentum."""
    if len(candles) < lookback + 1:
        return True  # not enough data — allow trade
    volumes = [c[5] for c in candles]  # index 5 = volume
    avg_vol = sum(volumes[-(lookback+1):-1]) / lookback
    cur_vol = volumes[-1]
    if avg_vol <= 0:
        return True
    return cur_vol >= avg_vol * mult

def get_signal(ex, pair):
    """CMO_CHANDE v2 SCALP_SHORT signal — LAB-PROVEN #1 strategy.
    BUY when: CMO > threshold AND RSI confirms AND volume surge.
    STRONG BUY when: CMO > MOMENTUM_THRESH (double signal strength).
    SELL when: CMO < -threshold (momentum reversal = fast exit).
    EXIT: TP at +0.25%, SL at -0.15%, timeout at 5 min (SCALP_SHORT)."""
    try:
        candles = ex.fetch_ohlcv(pair, "1m", limit=DAILY_CANDLE_LIMIT)
        price   = float(ex.fetch_ticker(pair)["last"])
        if len(candles) < CMO_PERIOD + 5:
            return {"signal":"HOLD","price":price,"reason":"insufficient_data"}
        closes = [c[4] for c in candles]
        cmo = _calc_cmo(closes, CMO_PERIOD)
        rsi = _calc_rsi(closes, RSI_PERIOD)
        vol_surge = _calc_volume_surge(candles, VOLUME_CANDLES, VOLUME_SURGE_MULT)
        # STRONG BUY: CMO > 35 = maximum momentum (lab: highest avg PnL per trade)
        if cmo > CMO_MOMENTUM_THRESH and rsi > RSI_BUY_THRESHOLD:
            return {"signal":"BUY","price":price,"cmo":round(cmo,2),"rsi":round(rsi,2),
                    "strength":"STRONG","vol_surge":vol_surge}
        # BUY: CMO > 20 + RSI > 52 + volume surge (SCALP_SHORT entry)
        if cmo > CMO_THRESHOLD and rsi > RSI_BUY_THRESHOLD and vol_surge:
            return {"signal":"BUY","price":price,"cmo":round(cmo,2),"rsi":round(rsi,2),
                    "strength":"NORMAL","vol_surge":True}
        # SELL: strong negative CMO = momentum reversal / fast exit (SCALP_SHORT)
        if cmo < -CMO_THRESHOLD:
            return {"signal":"SELL","price":price,"cmo":round(cmo,2),"rsi":round(rsi,2)}
        return {"signal":"HOLD","price":price,"cmo":round(cmo,2),"rsi":round(rsi,2)}
    except Exception as e:
        log.warning("signal %s: %s", pair, e)
        return {"signal":"HOLD","price":None,"reason":str(e)}

def _base_fee(order, base_asset):
    """Sum any fees paid in BASE_ASSET from a ccxt order response.

    Handles both ccxt response shapes:
      - 'fee'  : single dict {cost, currency}
      - 'fees' : list of {cost, currency} dicts (Gate.io occasionally returns
                 this when a market order is split across multiple maker/taker
                 fills).

    Returns 0.0 when no base-asset fee is reported or the response is
    malformed. Tolerant by design — fee parsing must never raise into the
    caller, because the caller is on the BUY hot path.
    """
    total = 0.0
    fee = order.get("fee")
    if isinstance(fee, dict) and fee.get("currency") == base_asset:
        try:
            total += float(fee.get("cost") or 0)
        except (TypeError, ValueError):
            pass
    fees = order.get("fees") or []
    if isinstance(fees, list):
        for f in fees:
            if isinstance(f, dict) and f.get("currency") == base_asset:
                try:
                    total += float(f.get("cost") or 0)
                except (TypeError, ValueError):
                    pass
    return total


def buy(ex, pair, size_usdt, aid):
    """Market buy by cost. Returns {id, filled, avg} on success, None on failure.
    Refetches the order if filled/average are missing on the creation response so we
    record the ACTUAL base amount we hold — critical for SELL to not over-sell.

    Subtracts any base-currency fees so the recorded 'filled' matches the
    exchange-side free balance. Gate.io spot market-buys charge fees in the
    base asset (e.g. SOL fee on a SOL/USDT buy), which previously caused a
    recurring InsufficientFunds → actual-balance retry on every SELL. The
    SELL retry remains as defence-in-depth for any residual drift."""
    base_asset = pair.split("/")[0]
    try:
        o = ex.create_order(pair, "market", "buy", size_usdt)
        oid = o.get("id")
        filled = float(o.get("filled") or 0)
        avg = float(o.get("average") or 0)
        if filled <= 0 or avg <= 0:
            try:
                o2 = ex.fetch_order(oid, pair)
                filled = float(o2.get("filled") or filled)
                avg = float(o2.get("average") or avg)
                o = o2  # use refetched response for fee parsing
            except Exception:
                pass
        fee_in_base = _base_fee(o, base_asset)
        if fee_in_base > 0:
            filled = max(0.0, filled - fee_in_base)
        log.info("[%s] BUY %s $%.2f -> filled=%.8f @ $%.4f id=%s",
                 aid, pair, size_usdt, filled, avg, oid)
        if filled <= 0 or avg <= 0:
            log.error("[%s] BUY %s: filled/avg unresolvable after fetch_order — treating as failure",
                      aid, pair)
            return None
        return {"id": oid, "filled": filled, "avg": avg}
    except Exception as e:
        log.error("[%s] BUY FAIL %s: %s", aid, pair, e)
        return None

# Sub-$5 base-asset residue left over after a SELL is dust (typical exchange
# fee remainder, partial-fill leftover, rounding crumb). Real trade sizes
# start at $18, so anything <$5 cannot be a held position — it's just drift.
# Swept back to USDT after each exit to keep the portfolio USDT-dominant.
DUST_NOTIONAL_USDT = 5.0


def sweep_dust(ex, pair, aid):
    """After a SELL, market-sell any sub-$5 base-asset residue back to USDT.

    Tidiness step, not a safety gate. Failures are logged and swallowed —
    leftover dust doesn't block the next trade cycle and we don't want a
    flaky cleanup call to take down a healthy thread.

    Only acts on amounts whose notional is below DUST_NOTIONAL_USDT. Larger
    residues (>=$5) are left alone — those would be real positions and a
    blind sweep could dump a position the executor expects to hold.
    """
    base_asset = pair.split("/")[0]
    try:
        bal = ex.fetch_balance()
    except Exception as e:
        log.warning("[%s] sweep_dust fetch_balance %s: %s", aid, pair, e)
        return
    free = float((bal.get(base_asset) or {}).get("free", 0) or 0)
    if free <= 0:
        return
    try:
        tkr = ex.fetch_ticker(pair)
        price = float(tkr.get("last") or 0)
    except Exception as e:
        log.warning("[%s] sweep_dust fetch_ticker %s: %s", aid, pair, e)
        return
    if price <= 0:
        return
    notional = free * price
    # Skip both the "nothing there" and the "too big to be dust" cases.
    if notional <= 0 or notional >= DUST_NOTIONAL_USDT:
        return
    try:
        amt = float(ex.amount_to_precision(pair, free))
        if amt <= 0:
            return
        o = ex.create_order(pair, "market", "sell", amt)
        log.info("[%s] DUST_SWEEP %s %.8f ~$%.4f id=%s",
                 aid, pair, amt, notional, o.get("id"))
    except Exception as e:
        log.warning("[%s] sweep_dust create_order %s: %s", aid, pair, e)


def sell(ex, pair, base_amt, aid):
    """Market sell. Respects exchange precision. If recorded base_amt exceeds actual
    on-exchange holdings (common when entry recorded an estimate, or fees ate dust),
    retries with the actual free balance so the position doesn't get stuck forever."""
    base_asset = pair.split("/")[0]
    try:
        amt = float(ex.amount_to_precision(pair, base_amt))
        if amt <= 0:
            log.error("[%s] SELL %s: %.10f rounds to 0 at pair precision", aid, pair, base_amt)
            return None
        o = ex.create_order(pair, "market", "sell", amt)
        log.info("[%s] SELL %s %.8f id=%s", aid, pair, amt, o.get("id"))
        return o
    except ccxt.InsufficientFunds as e:
        log.warning("[%s] SELL %s insufficient (recorded=%.8f) — retrying with actual free balance: %s",
                    aid, pair, base_amt, e)
        try:
            bal = ex.fetch_balance()
            actual = float(bal.get(base_asset, {}).get("free", 0))
            if actual <= 0:
                log.error("[%s] SELL %s: no %s held on exchange", aid, pair, base_asset)
                return None
            amt = float(ex.amount_to_precision(pair, actual))
            if amt <= 0:
                log.error("[%s] SELL %s: actual %s balance %.10f rounds to 0",
                          aid, pair, base_asset, actual)
                return None
            o = ex.create_order(pair, "market", "sell", amt)
            log.info("[%s] SELL %s %.8f (actual-balance retry) id=%s",
                     aid, pair, amt, o.get("id"))
            return o
        except Exception as e2:
            log.error("[%s] SELL FAIL (after retry) %s: %s", aid, pair, e2)
            return None
    except Exception as e:
        log.error("[%s] SELL FAIL %s: %s", aid, pair, e)
        return None

def publish_status(states, ranked, threads_by_id=None, arm=None):
    """Write live snapshot. If threads_by_id is provided, mark each account's
    thread_alive so DEAD accounts (failed auth, etc.) are visible to the frontend
    instead of looking identical to LIVE accounts. If arm is provided, also
    publish the 60-minute championship rounds scoreboard.

    Publishes to THREE files every cycle:
      - STATUS_FILE              — /root/canary/runtime/multi_battle_status.json (internal)
      - FRONTEND_PUB             — /var/www/.../api/battle/live_battle.json (raw live data)
      - TERMINAL_PUB             — /var/www/.../api/battle/terminal.json (frontend-shaped,
                                   keeps the legacy fields the dashboard pages expect,
                                   PLUS the live multi-account battle data — so any page
                                   reading terminal.json now sees real updated state
                                   every 60s instead of the static startup snapshot).
    """
    try:
        if threads_by_id:
            for s in states:
                t = threads_by_id.get(s["account_id"])
                s["thread_alive"] = bool(t and t.is_alive())
        # Surface the cinematic agent_label on every state for the raw
        # live JSON. Pure telemetry enrichment — falls back to account_id
        # if the ACCOUNTS entry lacks a label. No trading logic reads
        # this field.
        _label_by_id = {a["id"]: a.get("agent_label", a["id"]) for a in ACCOUNTS}
        for s in states:
            s["agent_label"] = _label_by_id.get(s["account_id"], s["account_id"])
        ts = datetime.now(timezone.utc).isoformat()
        rounds_view = build_rounds_view(states, arm) if arm else []
        current_rid = round_id_now(arm) if arm else None

        # Internal / raw live data
        # schema_version: bump on any breaking change to terminal.json /
        # live_battle.json shape. Frontends pin to a min version; old
        # consumers see the bump and can re-fetch the schema doc.
        d = {"timestamp": ts, "schema_version": "2.0",
             "mode": "LIVE_MULTI_ACCOUNT", "banner": LIVE_BANNER,
             "pairs": ranked, "accounts": states,
             "rounds": rounds_view, "current_round_id": current_rid,
             "round_interval_sec": ROUND_INTERVAL_SEC}
        STATUS_FILE.write_text(json.dumps(d, indent=2))
        if FRONTEND_PUB.parent.exists():
            FRONTEND_PUB.write_text(json.dumps(d, indent=2))

        # Frontend-shaped terminal.json — legacy fields + live data so dashboard
        # pages reflect real trading state on every cycle.
        agg_pnl = sum(float(s.get("session_pnl", 0)) for s in states)
        agg_trades = sum(int(s.get("trades_today", 0)) for s in states)
        accounts_map = {}
        for acc in ACCOUNTS:
            sid = acc["id"]
            st = next((s for s in states if s.get("account_id") == sid), None) or {}
            positions = st.get("positions", {})
            # EDGE_v1.1 — surface rolling-100 WR + avg-pnl per account so the
            # decision gate for TIER_3 ($25) can be checked from the terminal API
            # without parsing battle.log.
            r_out = st.get("rolling_outcomes", []) or []
            r_pnl = st.get("rolling_pnls", []) or []
            r_n   = len(r_out)
            r_wr  = (sum(r_out) / r_n) if r_n > 0 else 0.0
            r_avg = (sum(r_pnl) / r_n) if r_n > 0 else 0.0
            accounts_map[sid] = {
                "agent_label": acc.get("agent_label", sid),
                "capital_usd": acc["max_capital"],
                "status": ("LIVE" if st.get("thread_alive", True) else "DEAD"),
                "trades_today": int(st.get("trades_today", 0)),
                "session_pnl_usd": float(st.get("session_pnl", 0)),
                "daily_dd_usd": float(st.get("daily_dd_usd", 0)),
                "open_positions": len(positions),
                "positions": positions,
                "rolling_window_n": r_n,
                "rolling_win_rate": round(r_wr, 4),
                "rolling_avg_pnl_usd": round(r_avg, 6),
            }
        # Championship — top earner of the current round, top earner overall
        current_round = next((r for r in rounds_view if r["in_progress"]), None)
        current_round_leader = current_round["winner_account_id"] if current_round else None
        overall_leader = None
        if accounts_map:
            overall_leader = max(
                (a for a in accounts_map.items() if a[1].get("status") == "LIVE"),
                key=lambda kv: kv[1].get("session_pnl_usd", 0.0),
                default=(None, None),
            )[0]

        terminal = {
            "schema_version": "2.0",
            "mode": "LIVE_REAL_CAPITAL",
            "disclaimer": "REAL capital. 3 Gate.io accounts live.",
            "real_capital_usd": sum(a["max_capital"] for a in ACCOUNTS),
            "layer1_locked": False,
            "layer1_l99_halted": False,
            "accounts": accounts_map,
            "pairs": ALL_PAIRS,
            "pairs_ranked": ranked,
            "strategy": "CMO_CHANDE",
            "agents": [],
            "bot": {"regime": "LIVE", "cycle": int(time.time())},
            "live": {
                "aggregate_session_pnl_usd": round(agg_pnl, 4),
                "aggregate_trades_today": agg_trades,
                "alive_accounts": sum(1 for a in accounts_map.values() if a["status"] == "LIVE"),
                "total_accounts": len(ACCOUNTS),
            },
            # Championship 60-min rounds scoreboard (Layer 2 → consumed by Layer 3)
            "championship": {
                "round_interval_sec": ROUND_INTERVAL_SEC,
                "current_round_id": current_rid,
                "current_round_leader": current_round_leader,
                "overall_leader": overall_leader,
                "rounds": rounds_view,
            },
            "timestamp": ts,
        }
        if TERMINAL_PUB.parent.exists():
            TERMINAL_PUB.write_text(json.dumps(terminal, indent=2))
    except Exception as e:
        log.warning("publish: %s", e)

def reset_demo_data():
    """Aggressive demo-data purge before live battle starts:
      1. Move any paper/demo source files out of the agent dir (backup, not delete)
      2. Move any paper/demo files served by the frontend api/battle/ dir to a
         backup subdir so they cannot be read by any page
      3. Write an initial LIVE_REAL_CAPITAL snapshot to terminal.json (publish_status
         overwrites this with live data every 60s afterward)
    """
    import glob
    ts = int(time.time())

    # Source-of-truth backups (paper arenas, demo state).
    for f in glob.glob("/root/agent/paper_battle/paper-arena.json"):
        bak = f + f".bak.{ts}"
        Path(f).rename(bak)
        log.info("Demo data backed up: %s -> %s", f, bak)

    # Cull any demo/paper artifacts that the frontend might serve from
    # /var/www/.../api/battle/. We move them to a `_demo_archive_<ts>/` subdir
    # so they're preserved but not served. Any filename containing 'paper',
    # 'demo', or 'arena' gets moved.
    battle_dir = TERMINAL_PUB.parent
    if battle_dir.exists():
        archive = battle_dir / f"_demo_archive_{ts}"
        moved = 0
        for child in battle_dir.iterdir():
            if not child.is_file():
                continue
            name_lower = child.name.lower()
            if any(tag in name_lower for tag in ("paper", "demo", "arena")):
                archive.mkdir(parents=True, exist_ok=True)
                target = archive / child.name
                try:
                    child.rename(target)
                    moved += 1
                    log.info("Archived demo file from frontend: %s -> %s", child, target)
                except OSError as e:
                    log.warning("Could not move %s: %s", child, e)
        if moved:
            log.info("Demo cleanup: archived %d file(s) to %s", moved, archive)

    # Initial LIVE snapshot to terminal.json. publish_status overwrites this
    # with live data every cycle, but this keeps the file LIVE-shaped even
    # before the first publish_status tick.
    fresh = {
        "mode": "LIVE_REAL_CAPITAL",
        "disclaimer": "REAL capital. 3 Gate.io accounts live.",
        "real_capital_usd": sum(a["max_capital"] for a in ACCOUNTS),
        "layer1_locked": False,
        "layer1_l99_halted": False,
        "accounts": {
            a["id"]: {"capital_usd": a["max_capital"], "status": "LIVE"}
            for a in ACCOUNTS
        },
        "pairs": ALL_PAIRS,
        "strategy": "MA50W10",
        "agents": [],
        "bot": {"regime": "LIVE", "cycle": 0},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if TERMINAL_PUB.parent.exists():
        TERMINAL_PUB.write_text(json.dumps(fresh, indent=2))
        log.info("terminal.json reset to LIVE_REAL_CAPITAL")

def run_account(account, arm):
    aid = account["id"]
    alog = logging.getLogger(aid)
    try:
        alog.info("START | capital=$%.2f | pairs=%s", account["max_capital"], ALL_PAIRS)
        ex = make_ex(account)
        check_bal(ex, account)
        state = load_state(account)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if state["current_date"] != today:
            state.update({"trades_today": 0, "daily_dd_usd": 0.0, "current_date": today})
            save_state(account, state)
        while not _shutdown.is_set():
            try:
                check_halts(); check_clock(arm)
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if state["current_date"] != today:
                    state.update({"trades_today": 0, "daily_dd_usd": 0.0, "current_date": today})
                # Championship: on each iteration, check if a new 60-min round has begun
                # and anchor this account's session_pnl as that round's starting point.
                maybe_anchor_round(state, arm)
                ranked = score_pairs(ex)
                for pair in ranked:
                    if _shutdown.is_set(): break
                    if time.time() - state["last_exit_ts"].get(pair, 0) < COOLDOWN_SEC: continue
                    sig = get_signal(ex, pair)
                    pos = state["positions"].get(pair)
                    # CMO_CHANDE: limit concurrent positions
                    if len(state["positions"]) >= MAX_CONCURRENT_POS and pos is None:
                        continue
                    if sig["signal"] == "BUY" and pos is None:
                        if state["trades_today"] >= MAX_TRADES_PER_DAY: continue
                        if state["daily_dd_usd"] >= account["max_daily_dd"]: continue
                        sz = TRADE_SIZE_USDT  # CMO_CHANDE: fixed $5 per trade
                        result = buy(ex, pair, sz, aid)
                        if result:
                            tp_price = result["avg"] * (1 + TP_PCT)
                            sl_price = result["avg"] * (1 - SL_PCT)
                            state["positions"][pair] = {
                                "side": "long",
                                "entry_price": result["avg"],
                                "size_usdt": sz,
                                "size_base": result["filled"],
                                "entry_ts": time.time(),
                                "order_id": result["id"],
                                "tp_price": tp_price,
                                "sl_price": sl_price,
                            }
                            state["trades_today"] += 1
                            alog.info("OPEN %s | entry=$%.6f | TP=$%.6f | SL=$%.6f | cmo=%.1f",
                                      pair, result["avg"], tp_price, sl_price,
                                      sig.get("cmo", 0))
                            save_state(account, state)
                    elif pos is not None:
                        p = sig.get("price") or pos["entry_price"]
                        hh = (time.time() - pos["entry_ts"]) / 3600
                        # CMO_CHANDE exits: TP, SL, or timeout (10 min)
                        hit_tp = p >= pos.get("tp_price", pos["entry_price"] * (1 + TP_PCT))
                        hit_sl = p <= pos.get("sl_price", pos["entry_price"] * (1 - SL_PCT))
                        if hit_tp or hit_sl or hh >= MAX_HOLD_HOURS:
                            reason = "TP" if hit_tp else ("SL" if hit_sl else "TIMEOUT")
                            o = sell(ex, pair, pos["size_base"], aid)
                            if o:
                                pnl = (p - pos["entry_price"]) * pos["size_base"]
                                state["session_pnl"] += pnl
                                state["daily_dd_usd"] += max(0, -pnl)
                                state["last_exit_ts"][pair] = time.time()
                                del state["positions"][pair]
                                outcome = "WIN" if pnl > 0 else "LOSS"
                                # EDGE_v1.1: track rolling last-100 outcomes for
                                # live decision-gate WR. Keep the lists capped at 100.
                                state.setdefault("rolling_outcomes", []).append(1 if pnl > 0 else 0)
                                state.setdefault("rolling_pnls", []).append(round(pnl, 6))
                                if len(state["rolling_outcomes"]) > 100:
                                    state["rolling_outcomes"] = state["rolling_outcomes"][-100:]
                                    state["rolling_pnls"] = state["rolling_pnls"][-100:]
                                alog.info("EXIT %s | %s | %s | entry=$%.6f exit=$%.6f pnl=$%.4f session=$%.4f",
                                          pair, outcome, reason, pos["entry_price"], p, pnl, state["session_pnl"])
                                save_state(account, state)
                                # Post-exit USDT-recovery audit + sub-$5 dust sweep.
                                # Both are best-effort and never block the loop.
                                try:
                                    _bal = ex.fetch_balance()
                                    _usdt = float((_bal.get("USDT") or {}).get("free", 0) or 0)
                                    _base_asset = pair.split("/")[0]
                                    _base = float((_bal.get(_base_asset) or {}).get("total", 0) or 0)
                                    alog.info("BALANCE_AFTER_EXIT %s usdt=$%.2f base=%s=%.8f",
                                              pair, _usdt, _base_asset, _base)
                                except Exception as _e:
                                    alog.warning("BALANCE_AFTER_EXIT %s log failed: %s", pair, _e)
                                sweep_dust(ex, pair, aid)
                            else:
                                # sell() failed — check if we actually hold any tokens.
                                # If balance=0, the position was already closed on exchange
                                # (e.g. exchange SL, manual close, or previous sell that
                                # returned None but still executed). Force-clear the ghost
                                # position so the bot can resume trading.
                                try:
                                    _base_asset = pair.split("/")[0]
                                    _chk_bal = ex.fetch_balance()
                                    _held = float((_chk_bal.get(_base_asset) or {}).get("free", 0) or 0)
                                    if _held <= 0:
                                        pnl = (p - pos["entry_price"]) * pos["size_base"]
                                        state["session_pnl"] += pnl
                                        state["daily_dd_usd"] += max(0, -pnl)
                                        state["last_exit_ts"][pair] = time.time()
                                        del state["positions"][pair]
                                        state.setdefault("rolling_outcomes", []).append(1 if pnl > 0 else 0)
                                        state.setdefault("rolling_pnls", []).append(round(pnl, 6))
                                        if len(state["rolling_outcomes"]) > 100:
                                            state["rolling_outcomes"] = state["rolling_outcomes"][-100:]
                                            state["rolling_pnls"] = state["rolling_pnls"][-100:]
                                        alog.warning("GHOST_CLEAR %s | %s | balance=0 on exchange — "
                                                     "force-cleared stuck position | pnl=$%.4f",
                                                     pair, reason, pnl)
                                        save_state(account, state)
                                    else:
                                        alog.error("SELL_STUCK %s | still holding %.8f %s — "
                                                   "will retry next tick", pair, _held, _base_asset)
                                except Exception as _ce:
                                    alog.error("SELL_STUCK %s | balance check failed: %s", pair, _ce)
                state["consec_api_fails"] = 0
            except Exception as e:
                alog.error("Loop error: %s", e)
                state["consec_api_fails"] = state.get("consec_api_fails", 0) + 1
                if state["consec_api_fails"] >= 5:
                    alog.error("[%s] 5 consecutive API failures — thread exiting (other accounts continue)", aid)
                    return
            _shutdown.wait(POLL_INTERVAL_SEC)
        alog.info("Shutdown clean.")
    except SystemExit:
        # fail_closed() during startup (e.g. check_bal) raised SystemExit in this
        # thread. The other account threads keep trading. Log it loudly so the operator
        # sees the death event instead of just noticing one less state file.
        alog.error("[%s] thread FAIL-CLOSED at startup — service stays up for other accounts", aid)
    except Exception:
        alog.exception("[%s] thread crashed unexpectedly", aid)

def main():
    log.info(LIVE_BANNER)
    log.info("MAIN=$1579.52 | SUB1=$200 | SUB2=$200 | Strategy=CMO_CHANDE | Pairs=%s", ALL_PAIRS)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    arm = check_arm()
    check_halts()
    check_clock(arm)
    reset_demo_data()
    log.info("Safety gates passed. Starting 3-account live battle...")
    threads_by_id = {}
    for acc in ACCOUNTS:
        t = threading.Thread(target=run_account, args=(acc, arm),
                             name=f"acct-{acc['id']}", daemon=True)
        t.start()
        threads_by_id[acc["id"]] = t
        log.info("Started thread: %s", acc["id"])
        time.sleep(3)
    # Use an UNAUTHENTICATED ccxt for status scoring — previously this borrowed MAIN's
    # auth instance, so if MAIN had a bad key the main thread's scoring also failed.
    ex_public = make_ex_public()
    while not _shutdown.is_set():
        try:
            states = [load_state(a) for a in ACCOUNTS]
            try:
                ranked = score_pairs(ex_public)
            except Exception as e:
                log.warning("Public scoring failed: %s", e)
                ranked = ALL_PAIRS
            alive = [aid for aid, t in threads_by_id.items() if t.is_alive()]
            if not alive:
                log.error("All account threads dead — exiting service so systemd can restart")
                _shutdown.set()
                break
            publish_status(states, ranked, threads_by_id, arm=arm)
        except Exception as e:
            log.warning("Status: %s", e)
        _shutdown.wait(60)
    for t in threads_by_id.values(): t.join(timeout=15)
    log.info("All accounts done.")
    # Exit code semantics — drives systemd's Restart=on-failure behaviour:
    #   • External signal received (operator `systemctl stop` / SIGTERM /
    #     SIGINT)        → exit 0  → systemd does NOT restart (intentional stop)
    #   • Internal shutdown (all threads dead, e.g. due to halt file)
    #                    → exit 99 → systemd restarts per the service unit's
    #                                Restart=on-failure + RestartSec=30
    #                                + StartLimitBurst=3 in 120s. While the
    #                                halt file is engaged each restart fails-
    #                                closes immediately; once the operator
    #                                clears the halt file, the next restart
    #                                resumes normally. After 3 burst restarts
    #                                in 120s without success, systemd gives
    #                                up — which is the intended defensive
    #                                ceiling.
    if not _signal_received:
        log.warning("Exiting with code 99 (halt-induced) — systemd will restart per Restart=on-failure")
        sys.exit(99)

if __name__=="__main__": main()
