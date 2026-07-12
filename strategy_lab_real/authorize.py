#!/usr/bin/env python3
"""Generate authorized.json — the SINGLE SOURCE OF TRUTH for what may deploy.
Derived ONLY from the gate's live_eligibility.json. Anything not here is refused.
Paper/analysis authority — does not execute anything."""
import json, os, pandas as pd
OUT = os.environ.get("AUTH_OUT", os.path.join(os.path.dirname(__file__), "results"))
MAX_LEVERAGE = float(os.environ.get("MAX_LEVERAGE", "5"))
FORBIDDEN_PAIRS = ["FLOKI","WIF","OP","SHIB","PEPE","DOGE","BONK","ADA","ATOM","UNI"]  # memecoins/off-charter

elig = json.load(open(os.path.join(OUT, "live_eligibility.json")))
authorized = [{"pair":p, "strategy":v["strategy"], "sharpe":v["sharpe"], "maxdd":v["maxdd"]}
              for p, vs in elig["pairs"].items() for v in vs if v["eligible"]]
policy = {"generated": pd.Timestamp.now("UTC").isoformat(),
          "max_leverage": MAX_LEVERAGE,
          "forbidden_pairs": FORBIDDEN_PAIRS,
          "authorized": authorized,
          "note": "ONLY these strategy/pair combos may be deployed, at <= max_leverage. "
                  "Everything else is REFUSED. Regenerated each gate run. Paper authority."}
json.dump(policy, open(os.path.join(OUT, "authorized.json"), "w"), indent=2)
print(f"authorized: {len(authorized)} setup(s) -> " + ", ".join(f"{a['strategy']}/{a['pair']}" for a in authorized))
