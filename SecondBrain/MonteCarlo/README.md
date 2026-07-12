---
type: monte-carlo-index
date: 2026-05-13
tags: [monte-carlo, forward-stress, kelly, risk-of-ruin]
ai-first: true
source: ~/Desktop/agent/paper_battle/monte_carlo.py
---

# Monte Carlo Overlay

> For future Claude: Forward stress simulator. Runs 2,000-5,000 capital paths × 20 trades each at trigger events to project p05/p95/max_DD/RoR/Kelly. If `p95_DD > Article 3 cap` OR `RoR > 1%` → activates `mc_compress_active` flag which scales next trades' risk by 0.5×. Bounded invocations (not per-tick) to keep CPU stable.

---

## What it computes

Per `forward_stress(...)` in `paper_battle/monte_carlo.py`:

| Output | Meaning |
|--------|---------|
| `expected_final_equity` | Mean of N path final values |
| `p05_equity` | 5th percentile worst-case equity |
| `p50_equity` | Median final equity |
| `p95_equity` | 95th percentile best-case equity |
| `max_dd_p95_pct` | 95th percentile drawdown across paths |
| `max_dd_median_pct` | Median drawdown |
| `risk_of_ruin_pct` | % of paths that fell below 50% starting capital |
| `median_time_to_recovery` | Median trades to recover from DD |
| `cagr_estimate_pct` | Compound annual proxy |
| `kelly_optimal_fraction_pct` | (b·p − q) / b · 100 |
| `r_win_mean` | Implied win-side R magnitude |
| `win_prob` | Input win probability |

---

## Trigger Schedule

Per Spec #20 Part II:

1. **Round start** — establish baseline projection
2. **Regime shift** (Bayesian dominant regime change) — re-project under new conditions
3. **3 consecutive losses** — emergency reassessment

→ NOT per-tick (would be expensive)

---

## Simulation Mechanics

For each of N paths × 20 trades:

```
risk_usd = equity × (risk_per_trade_pct / 100)

won = bernoulli(win_prob)
if won:
    r = gauss(r_win_mean, r_win_mean × 0.30)
    r = max(0.1, r)
else:
    r = -1.0

slip   = gauss(slip_mean_pct, slip_std_pct)
cost   = (slip × 2 + round_trip_fee_pct) / SL_PCT     # cost in R-multiples
r     -= cost

equity += risk_usd × r

if equity ≤ ruin_threshold (50% of starting):
    ruined; break
```

Track per-path: peak, max_dd, recovery time. Aggregate at end.

---

## Kelly Compression Overlay

```python
def kelly_compression_required(mc, constitutional_dd_pct=2.0, max_ror_pct=1.0):
    if mc["max_dd_p95_pct"] > constitutional_dd_pct:
        return True, f"p95_DD={mc['max_dd_p95_pct']:.2f}%>tol={constitutional_dd_pct}%"
    if mc["risk_of_ruin_pct"] > max_ror_pct:
        return True, f"RoR={mc['risk_of_ruin_pct']:.2f}%>max={max_ror_pct}%"
    return False, "within_tolerance"
```

When `should_compress == True`:
```python
shadow_round.mc_compress_active = True
# in simulate_trade:
if mc_compress_active:
    risk_pct = min(risk_pct, RISK_PER_TRADE_PCT * 0.5)
```

→ See [[MacroLayer/README#Risk-sizing pipeline]] for full cascade

---

## Live Observation (90-min round in flight 2026-05-13)

From console:
```
[MC] round_start:    p05=9.7571 max_dd_p95=3.69% RoR=0.000% kelly=39.13% compress=True
                                              ↑ exceeds 2% tolerance → compression activated

[MC] regime_shift→Expansion:    compress=True (still)
[MC] regime_shift→Panic:        compress=True (still)
```

The model correctly identifies that with current parameters (TP 1% / SL 0.5% / 0.4% RT fees / 0.10% slip × 2) the projected p95 DD exceeds the Article 3 2% cap → compression flag stays active for the round. Sovereign behavior.

---

## Why Article 3 hard cap matters

Even if Kelly says 39.13% optimal fraction, the system **cannot** allocate that much because:

1. Spec #14 forces RISK_PER_TRADE = 0.25%
2. Article 3 absolute max = 0.75%
3. `min(macro_adjusted, Article 3)` enforced in `macro_layer.apply_macro_to_risk`

The Kelly value is informational. The deployed risk is sovereign-bounded.

---

## Cross-links

- [[RegimeModels/README]] — Bayesian shifts trigger MC
- [[MacroLayer/README]] — MC compression feeds risk cascade
- [[ExecutionEngine/README#Trigger schedule]] — when MC fires in the runner
- [[Architecture/README#Five Sovereign Layers]] — Layer 2 component

## Source-of-truth

- `~/Desktop/agent/paper_battle/monte_carlo.py` (189 lines)
- `~/Desktop/agent/governance/BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md` Part II
