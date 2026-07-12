# AI_ADAPTIVE_TRADING_MODE_ENGINE v1.0

**Operator-authored:** 2026-05-13 (spec #8)
**Status:** ACCEPTED · `determine_adaptive_mode()` implemented in engine v2.0

---

## Core mission

Agents automatically shift trading behavior based on: market regime · macro stability · volatility · liquidity · internal performance health · drawdown/risk signals.

**No emotional switching. No manual override needed. Pure intelligence-based transition.**

---

## Section I — Mode Definitions

### MODE 1 — SAFE

Risk/trade: 0.25% – 0.5% · Low frequency · No pyramiding · Strict confirmation · Wider stops · Stable position bias.

Activated when:
- MSI < 65
- Volatility spike
- 2 consecutive losses
- Regime transition probability > 60%
- DD > 3%

### MODE 2 — AGGRESSIVE

Risk/trade: 0.5% – 1% · Moderate frequency · Controlled pyramiding · Regime-aligned · Balanced confirmation.

Activated when:
- Macro stable
- Volatility normal
- Meta health > 75
- No drift flags
- Regime confidence > 70%

### MODE 3 — MAX_AGGRESSIVE

Risk/trade: up to 1% (never above cap) · Higher frequency (within limits) · Pyramiding enabled · Momentum bias · Faster rotation.

Activated when:
- MSI > 80
- Liquidity expansion confirmed
- Regime = strong trend
- Meta health > 85
- No risk alerts
- DD < 2%

**Limit: Cannot remain in MAX_AGGRESSIVE > 5 trading cycles.**

### MODE 4 — STOP

No new entries · Defensive exits only · Capital → preservation vault · Research mode.

Activated when:
- Systemic Risk > 75
- 3 consecutive losses
- DD > 5%
- Liquidity collapse
- Exchange instability
- Kill-switch triggered

**STOP overrides all modes.**

---

## Section II — Mode Transition Logic

**Priority:** STOP > SAFE > AGGRESSIVE > MAX_AGGRESSIVE

Rules:
- If STOP trigger → immediate STOP
- Else if SAFE conditions → SAFE
- Else if MAX_AGGRESSIVE conditions → MAX_AGGRESSIVE
- Else → AGGRESSIVE

**Downgrade faster than upgrade.** Upgrade requires 3 consecutive stable cycles. Downgrade requires 1 negative signal.

**Implementation:** `determine_adaptive_mode()` per agent per tick.

---

## Section III — Internal Health Check

Meta Health Score (MHS) drives forced modes:
- MHS < 70 → force SAFE
- MHS < 60 → force STOP

(Already implemented in `compute_meta_health()` — MHS < 60 = observation_mode.)

---

## Section IV — Regime-Based Mode Bias

| Regime | Favored mode |
|--------|--------------|
| Strong Trend | AGGRESSIVE / MAX_AGGRESSIVE |
| Chop | SAFE |
| Volatility Expansion | Controlled AGGRESSIVE only |
| Panic / Crisis | SAFE or STOP |
| Recovery | SAFE → AGGRESSIVE only |

---

## Section V — Anti-Overconfidence Lock

5+ consecutive wins triggers:
- Reduce size by 10%
- Increase confirmation strictness
- Limit pyramiding depth

**Prevent emotional over-scaling.**

**Implementation:** Constant `ANTI_OVERCONFIDENCE_WIN_STREAK = 5` in engine triggers force-SAFE mode.

---

## Section VI — Performance Feedback Loop

```
Performance ↑ → mode upgrade allowed (if conditions stable)
Performance ↓ → immediate downgrade
```

Transitions logged in agent's `learning_adjustments_history`.

---

## Section VII — Capital Protection Invariants

**Absolute limits (NEVER overridden by mode):**
- Risk/trade ≤ 1%
- Total exposure ≤ 5%
- Correlated exposure ≤ 2%

**Modes adjust behavior, never override risk caps.**

---

## Final purpose

Intelligent behavior shifts based on **environment + health**, not emotion/greed.

Ensures: Stability during instability · Expansion during opportunity · Defense during danger · Scaling only when earned.

---

## Cross-references

- `MASTER_ARCHITECTURE_v2.0.md`
- `paper_battle_engine.py` — `ADAPTIVE_MODES` dict + `determine_adaptive_mode()`
- `META_EVOLUTION_v2.md` — MHS source
