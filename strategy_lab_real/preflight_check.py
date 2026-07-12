#!/usr/bin/env python3
"""Deployment pre-flight guard — the SINGLE DOOR to any deployment.
Given a proposed (strategy, pair, leverage), returns ALLOW or REFUSE by
checking against authorized.json (gate-eligible only) + leverage cap +
forbidden pairs. Exit 0 = allow, 1 = refuse. Judges only; executes nothing.

  PF_STRATEGY=sma50_trend PF_PAIR=BTC PF_LEVERAGE=3 python3 preflight_check.py
"""
import json, os, sys
OUT = os.environ.get("AUTH_OUT", os.path.join(os.path.dirname(__file__), "results"))
pol = json.load(open(os.path.join(OUT, "authorized.json")))
strat = os.environ.get("PF_STRATEGY", "")
pair  = os.environ.get("PF_PAIR", "").upper()
lev   = float(os.environ.get("PF_LEVERAGE", "1"))

reasons = []
if not any(a["pair"] == pair and a["strategy"] == strat for a in pol["authorized"]):
    reasons.append(f"'{strat}' on {pair} is NOT gate-eligible (failed bull+bear validation)")
if lev > pol["max_leverage"]:
    reasons.append(f"leverage {lev:g}x exceeds max {pol['max_leverage']:g}x")
if any(fp in pair for fp in pol["forbidden_pairs"]):
    reasons.append(f"{pair} is a forbidden/off-charter pair")

allow = len(reasons) == 0
print(("✅ ALLOW" if allow else "❌ REFUSE") + f"  {strat or '?'} / {pair or '?'} / {lev:g}x")
for r in reasons:
    print("   - " + r)
sys.exit(0 if allow else 1)
