---
type: macro-layer-index
date: 2026-05-13
tags: [macro, global-score, defensive, expansion, aggression-governor]
ai-first: true
source: ~/Desktop/agent/paper_battle/macro_layer.py
---

# Macro Layer

> For future Claude: Global Macro Score 0-100 derived from 4 components. Maps to 5 modes (PANIC/DEFENSIVE/NEUTRAL/EXPANSION/HIGH_OPPORTUNITY) → each mode sets `risk_multiplier`, `exposure_cap`, and `aggression_allowed`. Constitutional Article 3 caps are INVIOLABLE — macro can only DECREASE caps, never increase.

---

## What this layer is NOT

This is **NOT a trade generator.** It is a regulator that sits between Signal-Composite and Risk-Engine.

It adjusts:
- `risk_multiplier`
- `aggression_unlock`
- `exposure_cap_modifier`
- `phase_weighting`

Per Spec #19 Section VI: hard caps from Constitution Article 3 cannot be exceeded regardless of macro score.

---

## Global Macro Score Composition (per Spec #19)

```
GLOBAL_MACRO_SCORE = weighted_average(
    volatility_pressure       (weight 0.30),
    correlation_stress        (weight 0.25),
    spread_instability        (weight 0.25),
    volume_expansion          (weight 0.20),
)
```

| Component | Source | Normalization |
|-----------|--------|---------------|
| `volatility_pressure` | rolling stdev/mean of BTC ticks | calm 0.10% → 0, stress 0.80% → 100 |
| `correlation_stress` | abs Pearson(BTC, ETH) returns | healthy 0.40 → 0, lockstep 0.95 → 100 |
| `spread_instability` | spread std/mean coefficient of variation | stable 0.20 → 0, unstable 1.00 → 100 |
| `volume_expansion` | total quote_volume across 5 pairs | quiet $2B → 0, active $20B → 100 |

---

## The 5 Modes

| Score | Mode | Risk Mult | Exposure Cap | Aggression |
|-------|------|-----------|--------------|------------|
| < 25 | **PANIC** | 0.5 | 0.4% | DISABLED |
| 25-40 | **DEFENSIVE** | 0.6 | 0.5% | DISABLED |
| 40-70 | **NEUTRAL** | 1.0 | 1.0% | normal phase |
| 70-85 | **EXPANSION** | 1.1 | 1.0% | ALLOWED if composite ≥ threshold |
| > 85 | **HIGH_OPPORTUNITY** | 1.2 | 1.0% | UNLOCKED (phase dependent) |

---

## Phase × Macro Interaction

Per Spec #19 Section V:

| Phase | Macro effect |
|-------|--------------|
| Phase 1 (0-30m) | Macro CANNOT increase aggression. Compression-only. |
| Phase 2 (30-75m) | Macro may scale risk_mult up to 1.1× |
| Phase 3 (75-90m) leading (equity_change > 0.5%) | Macro IGNORED (defensive priority) |
| Phase 3 (75-90m) trailing | Macro may unlock controlled expansion |

---

## Risk-Sizing Pipeline (the cascade)

```
risk_pct_base  = min(RISK_PER_TRADE, phase_risk_cap)
       ↓
macro_adjusted = apply_macro_to_risk(base, mode, phase, equity_change)
       ↓
if mc_compress_active:    risk_pct ≤ 0.5 × RISK_PER_TRADE     (Spec #20 II)
       ↓
if bayes_entropy > 1.5:   risk_pct ≤ 0.7 × RISK_PER_TRADE     (Spec #20 I)
       ↓
risk_pct = min(risk_pct, ARTICLE3_RISK_PER_TRADE_MAX_PCT)     (immutable)
```

Each stage **only compresses**. Never increases.

Logged per trade as `risk_pct_pre_macro` + `risk_adjust_reason`.

---

## Live Observation (90-min round in flight 2026-05-13)

From console:
```
t+ 0.77m  macro=40/NEU bayes=Chop(H=0.98)     ← borderline NEUTRAL/DEFENSIVE
t+ 1.60m  macro=25/DEF bayes=Expa(H=0.26)     ← shifted DEFENSIVE
t+40.59m  macro=38/DEF bayes=Pani(H=0.97)     ← PANIC region
t+43.57m  macro=44/NEU bayes=Pani(H=0.36)     ← recovering to NEUTRAL
t+46.62m  macro=41/NEU bayes=Pani(H=0.66)     ← NEUTRAL with regime uncertainty
```

The macro layer correctly shifted to DEFENSIVE during low-volume / high-correlation periods, then back to NEUTRAL as conditions stabilized. NO TRADES fired throughout — correct behavior.

---

## Constitutional Article 3 Hard Caps

These cannot be overridden by macro under any conditions:

```python
ARTICLE3_RISK_PER_TRADE_MAX_PCT = 0.75
ARTICLE3_EXPOSURE_MAX_PCT       = 1.00
ARTICLE3_MAX_CONSEC_LOSS        = 3
ARTICLE3_MAX_DD_PCT             = 2.0
```

Macro can take risk DOWN to 0.5 × RISK_PER_TRADE during PANIC. Macro CANNOT take risk UP past 0.75% (Article 3) even in HIGH_OPPORTUNITY mode.

---

## Cross-links

- [[RegimeModels/README]] — Bayesian entropy feeds compression
- [[MonteCarlo/README]] — Kelly compression feeds same cascade
- [[ExecutionEngine/README]] — full risk-sizing pipeline lives in `simulate_trade`
- [[Governance/README]] — Constitution Article 3 (immutable)

## Source-of-truth

- `~/Desktop/agent/paper_battle/macro_layer.py` (247 lines)
- `~/Desktop/agent/governance/AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1.md`
