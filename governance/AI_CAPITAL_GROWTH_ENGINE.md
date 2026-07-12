# AI_CAPITAL_GROWTH_ENGINE v1.0

**Operator-authored:** 2026-05-13 (spec #4)
**Status:** ACCEPTED · TPI formula + 5-phase classifier in engine v2.0

---

## Mission

Build a self-strengthening AI trading ecosystem where intelligence growth → capital growth → research growth → power growth. **Growth must be earned.**

---

## Section 1 — Power Definition Model

```
Power ≠ Trade Frequency · Power ≠ Aggression · Power ≠ Position Size

True Power Index (TPI) =
  Edge Quality × Stability Score × Risk Discipline ×
  Research Depth × Capital Efficiency
```

**Trade frequency is only a multiplier AFTER stability.**

If Stability < 75 → **Scaling prohibited.**

**Implementation:** `compute_tpi()` in `paper_battle_engine.py`. Computes per-agent TPI 0-100.

---

## Section 2 — Capital Evolution Phases

**Implementation:** `CAPITAL_PHASES` dict + `CURRENT_CAPITAL_PHASE = 0` constant.

### Phase 0 — Paper Dominance
Conditions: 500+ simulated trades · Sharpe > 1.8 · Max DD < 15% · Regime detection accuracy > 70%
Scaling: NONE. Goal: intelligence maturity.

### Phase 1 — Micro Live ($10-$50)
Conditions: Meta health > 80 · 30-day paper stability · No drift detected
Scaling: Risk/trade ≤ 0.5% · Max exposure ≤ 2%. Goal: execution validation.

### Phase 2 — Canary Controlled ($100)
Conditions: 30 live trades positive expectancy · No discipline violation · Kill-switch tested
Scaling: Risk/trade ≤ 1% · Max exposure ≤ 5%. Goal: capital discipline confirmation.

### Phase 3 — Controlled Compounding
Profit allocation: 40% capital · 30% research · 20% infrastructure · 10% reserve
**No 100% reinvestment.** No greed amplification.

### Phase 4 — Ecosystem Expansion
Only after 6 months stable live record + DD compression proven + research lab delivering validated improvements.
Actions: multi-agent routing · style diversification · cross-strategy allocation.

---

## Section 3 — Dynamic Trade Frequency Model

Increase allowed ONLY IF:
- Meta_Health_Score > 85
- Rolling_30D_Stability > 80
- Drawdown < 5%

```
New_Frequency = Base_Frequency × Stability_Modifier × Regime_Confidence
```

Max increase per cycle: **+20%**.
If DD spike > 3% → auto frequency reduction -30%.

**No exponential overtrading allowed.**

---

## Section 4 — Self-Learning Reinvest Loop

```
Performance ↑ → Research Budget ↑ → Hypothesis Testing ↑
→ Strategy Refinement ↑ → Edge Stability ↑
→ Allocation Confidence ↑ → Capital ↑

If Performance ↓ →
Allocation Compression → Research Focus Shift
→ Aggression Reduction → Stability Recovery Mode
```

**Loop closes on discipline, not greed.**

---

## Section 5 — Ecosystem Multiplier Model

```
Ecosystem Strength (ES) =
  Intelligence Depth × Agent Diversity ×
  Capital Allocation Efficiency × Governance Strength × Brand Authority
```

**Money alone does not increase ES. Research + Governance does.**

Allowed: research depth · predictive regime modeling · strategy diversity · risk compression mastery.
Forbidden: martingale · revenge trading · blind scaling · leverage escalation.

---

## Section 6 — Rich Avenue Expansion Model

Level 1 → Trading profits
Level 2 → AI infrastructure
Level 3 → Fund-grade governance
Level 4 → Public authority + brand
Level 5 → Intellectual property + licensing

**Reinvest must move capital upward in layers.** If reinvest only increases trade size → you remain trader. If reinvest builds systems → you become ecosystem architect.

---

## Section 7 — Automatic Power Compression Rule

**Implementation:** `check_power_compression()` in engine.

Triggers (any):
- 3 consecutive losses
- Regime mismatch spike
- Execution anomaly
- Liquidity instability
- Equity volatility surge

Response:
- Aggression × 0.60 (-40%)
- Frequency × 0.70 (-30%)
- Position size compressed
- Research priority shifted

**Capital preservation overrides growth.**

---

## Section 8 — Long-Term Domination Model

```
Year 1: Stability > Speed · Governance > Profit · Research > Expansion
Year 2: Multi-strategy allocation · Research-driven upgrades · Public authority layer
Year 3: Institutional fund architecture · Capital scaling · Licensing + ecosystem expansion
```

Sustainable exponential growth.

---

## Final principles

1. Intelligence first.
2. Discipline second.
3. Capital third.
4. Expansion last.
5. Never scale chaos.
6. Never override safety.
7. Power must be earned.

---

## Cross-references

- `MASTER_ARCHITECTURE_v2.0.md`
- `paper_battle_engine.py` — TPI + phase + power compression implementations
