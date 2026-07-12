# AI_GLOBAL_MACRO_PREDICTION_LAYER + Production Shadow Engine Integration v1.0

**Operator-authored:** 2026-05-13 (spec #19 in v2.0 dump)
**Status:** ACCEPTED · documented · **IMPLEMENTED** in `paper_battle/macro_layer.py`
**Significance:** Adds strategic pressure gauge layer to shadow runner. Adjusts aggression / risk compression / exposure — never overrides hard caps.

---

## Why this spec is different

This layer **does NOT generate trades**. It is a regulator that sits between Signal-Composite and Risk-Engine, modulating:
- `risk_multiplier`
- `aggression_unlock`
- `exposure_cap_modifier`
- `phase_weighting`

The constitution still wins: hard caps from `AI_DISCIPLINE_CONSTITUTION` Article 3 cannot be exceeded regardless of macro score.

---

## Section I — Global Macro Score Model

**Output range:** 0–100

**Inputs (read-only public data, no API key):**

| Signal | Source | Implementation |
|--------|--------|----------------|
| BTC Volatility Percentile | rolling stdev/mean of BTC ticks | ✓ from shadow round windows |
| Correlation Spike Index | Pearson(BTC, ETH) over rolling window | ✓ from shadow round windows |
| Stablecoin Flow Proxy | hard from public REST | ⚠ approximated via BTC dominance proxy |
| Funding Rate Imbalance | Gate.io futures public funding rate | ⏳ optional (requires extra REST call) |
| Volume Expansion Ratio | current vs avg 24h volume | ✓ from ticker quote_volume |
| Spread Instability Index | std/mean of spread over window | ✓ from shadow round windows |

Each normalized to 0–100 scale.

**Composite formula:**
```
GLOBAL_MACRO_SCORE = weighted_average(
    volatility_pressure       (weight 0.30),
    correlation_stress        (weight 0.25),
    spread_instability        (weight 0.25),
    volume_expansion          (weight 0.20)
)
```

---

## Section II — Macro Regime Classification

| Score | Mode | Risk Mult | Exposure Cap | Aggression |
|-------|------|-----------|--------------|------------|
| < 40 | DEFENSIVE | 0.6 | 0.5% | DISABLED |
| 40–70 | NEUTRAL | 1.0 | 1.0% | Normal phase logic |
| 70–85 | EXPANSION | 1.1 | 1.0% | Allowed if composite ≥ threshold |
| > 85 | HIGH_OPPORTUNITY | 1.2 | 1.0% | Unlocked (phase dependent) |

---

## Section III — Phase × Macro Interaction (Section V verbatim)

| Phase | Macro effect |
|-------|--------------|
| Phase 1 (0-30) | Macro **cannot** increase aggression. Compression-only. |
| Phase 2 (30-75) | Macro may expand risk_mult up to 1.1× |
| Phase 3 (75-90) leading | Macro **ignored** (defensive priority) |
| Phase 3 (75-90) trailing | Macro may unlock controlled expansion |

---

## Section IV — Hard Safety Constraints (Section VI verbatim)

Regardless of macro score, these caps are **inviolable**:

```
risk_per_trade        ≤  0.75%
max_exposure          ≤  1%
max_consecutive_losses=  3
max_drawdown          ≤  2%
```

→ Same constraints as Constitution Article 3.

**Implementation note:** `macro_layer.py` applies `min(constitutional_cap, macro_adjusted_cap)` — never the max.

---

## Section V — Logging Extension

Each JSONL trade row now includes:
```json
{
  "global_macro_score": 72,
  "macro_mode": "EXPANSION",
  "macro_risk_multiplier": 1.1,
  ...
}
```

Round summary includes:
```json
{
  "avg_macro_score": 68,
  "macro_regime_distribution": {
    "DEFENSIVE": 10,
    "NEUTRAL": 50,
    "EXPANSION": 40,
    "HIGH_OPPORTUNITY": 0
  }
}
```

---

## Section VI — Panic Interaction (Section VIII verbatim)

If Macro detects **Panic regime** (score < 25):
- Risk multiplier → 0.5
- Aggression disabled
- Only composite ≥ 90 trades allowed
- If DD rising → freeze triggered

---

## Implementation Status

**File:** `paper_battle/macro_layer.py` (added in commit following this doc)

Public API:
```python
from macro_layer import compute_global_macro_score, macro_mode_for

result = compute_global_macro_score(price_windows, spread_history, tickers)
# returns {"score": float, "mode": str, "risk_multiplier": float,
#          "exposure_cap_pct": float, "aggression_allowed": bool, "inputs": {...}}
```

Wired into `shadow_round.py`:
- Computed once per heartbeat (every ~60s) — not per tick
- Result applied to risk sizing in `simulate_trade`
- Result logged in every JSONL row
- Distribution aggregated in round summary

---

## Final declaration (verbatim)

> Macro layer adds intelligence, not recklessness.
> Prediction guides risk. Discipline remains supreme.
> Shadow validates structure. Live remains locked.

---

## Cross-references

- `SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md` (spec #17) — base protocol
- `PRODUCTION_READY_SHADOW_ENGINE_v1.md` (spec #18) — production bar
- `BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md` (spec #20) — companion advanced layer
- `AI_DISCIPLINE_CONSTITUTION.md` Article 3 — hard caps this layer respects
- `MASTER_ARCHITECTURE_v2.0.md` — index
