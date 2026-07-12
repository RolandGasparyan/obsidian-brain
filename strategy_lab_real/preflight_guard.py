#!/usr/bin/env python3
"""
preflight_guard — drop-in PRE-TRADE gate for the live executor.
Import this and call is_allowed(...) BEFORE every order. It returns False for
anything the validation gate did not authorize (wrong pair, over-leverage,
forbidden/off-charter pair). FAIL-CLOSED: if authorized.json is missing or
unreadable, it REFUSES — so drift/theater can never slip through.

It only JUDGES. It never places, cancels, or modifies an order.
"""
import json, os

# Point this at the gate's output (regenerated every lab loop).
AUTHORIZED_JSON = os.environ.get(
    "AUTHORIZED_JSON",
    os.path.expanduser("~/tradingguru-empire/strategy_lab_real/results/authorized.json"),
)

def _norm(pair: str) -> str:
    return (pair or "").upper().split("/")[0].split("-")[0].strip()

def load_policy():
    try:
        with open(AUTHORIZED_JSON) as f:
            return json.load(f)
    except Exception:
        return None  # fail-closed

def is_allowed(strategy: str, pair: str, leverage: float = 1.0):
    """Return (allowed: bool, reason: str)."""
    pol = load_policy()
    if pol is None:
        return False, f"REFUSE: authorized.json unreadable at {AUTHORIZED_JSON} (fail-closed)"
    sym = _norm(pair)
    if any(fp in sym for fp in pol.get("forbidden_pairs", [])):
        return False, f"REFUSE: {sym} is a forbidden/off-charter pair"
    if float(leverage) > float(pol.get("max_leverage", 5)):
        return False, f"REFUSE: leverage {leverage:g}x > max {pol.get('max_leverage')}x"
    if not any(a["strategy"] == strategy and a["pair"] == sym for a in pol.get("authorized", [])):
        return False, f"REFUSE: {strategy} on {sym} is NOT gate-eligible (failed bull+bear validation)"
    return True, f"ALLOW: {strategy} on {sym} at {leverage:g}x"

if __name__ == "__main__":
    import sys
    s = os.environ.get("PF_STRATEGY",""); p = os.environ.get("PF_PAIR",""); l = float(os.environ.get("PF_LEVERAGE","1"))
    ok, why = is_allowed(s, p, l)
    print(("✅ " if ok else "❌ ") + why)
    sys.exit(0 if ok else 1)
