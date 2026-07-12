# AI_GLOBAL_MACRO_PREDICTION_LAYER v1.0

**Operator-authored:** 2026-05-13 (spec #6)
**Status:** ACCEPTED · MSI synthesized in engine v2.0 · real macro feed planned for future

---

## Mission

Integrate macroeconomic, geopolitical, liquidity, systemic risk signals into the AI ecosystem so capital decisions are: anticipatory, regime-aware, shock-resistant, institution-grade.

**This layer does NOT predict prices. It predicts environments.**

---

## Section I — Macro Intelligence Architecture

4 macro domains, each output 0-100:
1. Monetary Liquidity
2. Economic Momentum
3. Geopolitical Stress
4. Systemic Risk

```
Macro_State_Vector = {
  liquidity_score, growth_score, stress_score, systemic_risk_score
}
```

**Composite Macro Stability Index (MSI):**
```
MSI = (0.35 × liquidity) + (0.25 × growth)
    - (0.25 × stress) - (0.15 × systemic_risk)
```

Range: 0-100.

**Implementation:** `compute_msi()` in `paper_battle_engine.py` — currently synthesized from internal signals. Real macro feed planned for future deployment.

---

## Section II — Liquidity Engine

Inputs (planned): central bank balance sheet · interest rate direction · yield curve slope · USD strength · stablecoin supply growth · funding rate imbalance · risk-on/off flows.

Regimes: High Expansion · Neutral · Contraction · Liquidity Crisis.

Rules:
- Liquidity expanding + vol stable → Risk allowance +10%
- Liquidity contraction → Risk compression -20%
- Crisis probability > 70% → Emergency capital protection mode

---

## Section III — Economic Momentum Engine

Inputs (planned): PMI · employment · CPI deviation · GDP surprise · commodity trend.

Growth phases: Expansion · Slowdown · Recession Risk · Recovery.

If Recession Risk + Liquidity Contraction → Exposure cap -40%.
If Expansion + Liquidity Expansion → Controlled progressive scaling allowed.

---

## Section IV — Geopolitical Stress Detector

Monitors: conflict escalation · sanction probability · election risk · regulatory shock · black swan keyword frequency.

| Stress Index | Action |
|--------------|--------|
| > 75 | Freeze aggressive strategies · stablecoin dominance · min leverage |
| 50-75 | Reduce trend aggression 15% |

---

## Section V — Systemic Risk Model

Monitors: exchange insolvency · stablecoin depeg · correlation spike · volatility clustering · liquidity evaporation.

If Systemic Risk > 70 → emergency actions: halt new entries · exit weak positions · capital to vault · defensive allocation.

**No override allowed.**

---

## Section VI — Macro→Micro Translation Layer

Macro signals do NOT directly trade. They modify:
- Position size bias
- Strategy weighting
- Trade frequency ceiling
- Aggression coefficient
- Capital allocation routing

**Adjustment limits: max ±20%.** Core strategy logic unchanged.

---

## Section VII — Predictive Regime Shift Detection

Transition signals:
- Liquidity + Stress divergence
- Growth deceleration + Volatility spike
- Correlation breakdown
- Funding rate extremes

If 3+ signals align → **Pre-Transition Mode**:
- Reduce exposure 25%
- Increase confirmation strictness
- Expand stop discipline
- Pause pyramiding

**Anticipate regime shift before crash.**

---

## Section VIII — Macro Confidence Scoring

Macro Confidence Score (MCS): signal consistency · multi-source confirmation · historical accuracy · volatility coherence.

| MCS | Effect |
|-----|--------|
| < 60 | Macro adjustments reduced to 50% strength |
| > 85 | Macro bias fully applied (within limits) |

**Avoid overreacting to noise.**

---

## Section IX — Integration with Capital Civilization

```
Global Macro Layer → Predictive Regime Engine
→ Research Lab Validation → FUND_OS Allocation Adjustments
→ Live Execution Engine → Telemetry Feedback → Meta Health Audit
```

Macro intelligence **guides** capital, but never **overrides** governance.

---

## Section X — Safety Invariants

This layer **CANNOT**:
- Increase risk caps
- Override emergency halt
- Deploy unvalidated strategy
- Modify capital firewall
- Remove stop-loss discipline

**Macro influence is advisory, not authoritarian.**

---

## Final purpose

Move from reactive trading → macro-aware anticipatory capital governance. Environment intelligence, not price prediction.

---

## Cross-references

- `MASTER_ARCHITECTURE_v2.0.md`
- `paper_battle_engine.py` — `compute_msi()` (synthesized · real feed future)
- `SUPER_POWER_ENGINES.md` — predictive layer companion
