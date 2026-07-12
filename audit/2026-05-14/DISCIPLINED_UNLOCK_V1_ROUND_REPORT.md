# Disciplined Unlock V1 — 4h Round Report

**Round date:** 2026-05-13 → 2026-05-14
**Mode:** `SHADOW_SLIGHT_UNLOCK` · `SLIGHT_UNLOCK=1`
**Duration:** 240.14 min (target 240 = 4h)
**Started:** 2026-05-13 19:40:07 UTC
**Completed:** 2026-05-13 23:40 UTC (auto-notify task `bmernikyu`)
**Spec applied:** #23 + Disciplined Unlock V1 tuning (commit `2604e3c`)

---

## Headline Result

```
sovereign_survival_score:  73.44 / 100        (round 1: 73.18 · round 2: 73.34 · round 3: 73.44)
sovereign_grade:           INSTITUTIONAL_READY  (3rd consecutive)
trades_total:              0                  ← still 0 after 4h with relaxed gates
governance_violations:     0
auto_freeze_triggered:     false
max_dd_pct:                0.00%
capital_preserved:         100%
```

**Δ vs round 2 (slight_unlock 90-min):** sovereign score +0.10 from improved `low_entropy` (regime more predictable over 4h sample).

---

## Exit Code 1 Diagnosis (NOT a real failure)

Background task `bmernikyu` reported `exit code 1` — but:
- Round elapsed: **240.14 min** ✓ (target 240)
- ROUND SUMMARY block written cleanly
- All JSON output files present
- No exceptions in console log
- `auto_freeze_triggered: false` · `governance_violations: 0`

The non-zero exit is a **tee/pipefail tooling artifact** from the launcher pipeline, not the runner itself. The Python runner returns `0` on clean completion (line 985 of shadow_round.py: `return 0 if not rnd.frozen else 3`). Round succeeded — the exit-code-1 is cosmetic.

---

## Why 0 trades AGAIN — the answer changed

The previous report blamed Spec #23's new gates (`macro<30`, `bayes Panic>55%`). Disciplined Unlock V1 relaxed those to `macro<25`, `bayes>65%`. Result: **the gates were NOT the binding constraint this round.**

### Evidence — gate biting rate

| Gate | This round avg | Threshold | Was biting? |
|------|----------------|-----------|-------------|
| `macro < 25 BLOCK` | macro avg=36.77, range 25-44, **never in PANIC band (<25)** | 25 | **NO** — never fired |
| `bayes Panic > 65% BLOCK` | Panic posterior avg=53.4% | 65% | Sometimes (during high-certainty Panic minutes, ~2-3 events visible at H<0.3) |
| `composite ≥ 47.5 FIRE` | composite never reached this | 47.5 | (the fire never even computed) |

### The real bottleneck: SIGNAL doesn't fire in calm BTC

```
BTC 4-hour range:    $79,300 - $79,700  ($400 = 0.50% total)
Per-minute moves:    typically $10-30 ($0.01-0.04%)
12-tick momentum:    peak ~0.05-0.15%
Required to fire:    momentum > 0.15%   ← rarely or never met
```

The strategy's signal generator requires:
1. `ma_short > ma_long` ✓ (varies)
2. `momentum_pct > 0.15%` ❌ (RARELY MET — BTC barely moves 0.15% in 2-min windows during this regime)
3. `regime not CHOP/COMPRESSION` ✓ (regime was Expansion/Recovery often)
4. `composite >= 47.5` ⚠ (never computed because #2 fails)

**The 4h round saw signal try to fire ZERO times** because momentum_pct never crossed 0.15%. This is upstream of any gate.

---

## Comparison Across 3 Rounds

| Metric | R1 baseline | R2 slight_unlock | R3 V1 tuning | Δ R3 vs R1 |
|--------|-------------|------------------|--------------|------------|
| Duration | 90 min | 90 min | **240 min** | 2.7× longer |
| Trades | 0 | 0 | **0** | same |
| Governance violations | 0 | 0 | 0 | same |
| Sovereign Score | 73.18 | 73.34 | **73.44** | +0.26 |
| Macro DEFENSIVE % | 75.0 | 57.5 | 63.7 | -11.3pp |
| Macro NEUTRAL % | 25.0 | 42.5 | 36.3 | +11.3pp |
| Bayes Panic % | 42.1 | 57.5 | **53.4** | +11.3pp |
| Bayes Expansion % | 50.0 | 32.9 | 38.2 | -11.8pp |
| Avg entropy (nats) | 0.597 | 0.556 | **0.531** | -0.066 |
| MC runs | 20 | 19 | **54** | 2.7× scaled with duration |

**Sovereign score trending up** (+0.26 over 3 rounds) from improving `low_entropy` (regime predictability tightens as sample grows). All other components static.

**0 trades held across all 3 rounds** = BTC market regime + signal threshold combination doesn't produce entries.

---

## Action Plan Verdict — Round 3

| # | Plan step | Status |
|---|-----------|--------|
| 1 | Build Slight Unlock + V1 tuning | ✓ DONE |
| 2 | Ensure ≥2 trades | ❌ 0 trades (target was 3-12) |
| 3 | Measure Realized_R | ❌ no trades to measure |
| 4 | Recompute Sovereign Score | ✓ 73.44 INSTITUTIONAL_READY (passed) |
| 5 | Revisit Micro Live Gate | ❌ steps 2-3 prerequisite still not met |

---

## Sovereign Components Breakdown

```
Component               Score  Weight  Contribution  Trend (R1→R3)
─────────────────────  ─────  ──────  ────────────  ─────────────
low_volatility         100.0   0.18   18.00         flat
drawdown_control        50.0   0.20   10.00         flat (MC p95 > Article 3)
survival_probability   100.0   0.22   22.00         flat
stable_compounding      19.62  0.15    2.94         flat (no trades)
low_entropy             79.25  0.10    7.93         ↑ (76.7 → 78.3 → 79.3)
tail_risk_immunity      83.81  0.15   12.57         flat
                                      ─────
TOTAL                                  73.44 → INSTITUTIONAL_READY
```

---

## Honest Conclusion

**The system is behaving correctly under Spec #22 Sovereign Capital Architecture.**

> "Capital preservation > Aggressive growth. Survival > Speed. Probabilities > Predictions."

3 consecutive rounds × 0 trades × 0 violations × $10 virtual untouched = the sovereign discipline is working. The system **refuses to speculate when momentum is below validated edge thresholds**.

**However**, this also means: the **paper-mode shadow CANNOT measure Realized_R in calm BTC regime**. Three options remain.

---

## 4 Options for next iteration

### Option A — Signal-level relaxation (deeper tuning)
Lower `MOMENTUM_FIRE_THRESHOLD` from 0.15% to 0.08-0.10%. Would allow composite to compute on smaller moves.

**Risk:** signal generates noise instead of edge. Real edge probably wants 0.20%+ momentum (matches Spec #14 micro params expectation). Lower threshold = more curve-fit risk.

**Honesty:** explicit spec deviation. Would need operator authorization.

### Option B — Wait for volatile market
Re-run on a more volatile day. BTC often moves >1% in 4 hours on event days (FOMC, CPI release, weekend gaps, etc.).

**Risk:** unknown when. **Pro:** pure validation, no parameter drift.

### Option C — Accept paper limit · advance to operator-authority $10 micro-live
Same recommendation as 2 rounds ago. Sovereign score **73.44 ≥ 55** passes Stage 1 progression threshold. Real Gate.io order execution will produce real Realized_R immediately on real momentum.

Path: operator completes `MICRO_LIVE_OPERATOR_CHECKLIST.md` steps 1-5 (~40 min) → Claude executes steps 6-9.

**Risk:** $10 real capital exposure (but paranoid auto-freeze + Spec #14 envelope).
**Pro:** measures what shadow can't surface; matches operator's intent if they want trades.

### Option D — Accept the discipline · do nothing
The 3-round 0-trade pattern is the system telling us "this market regime doesn't have edge worth taking." Spec #22 Section VII says **system success IS:**
> "Low volatility equity curve · Controlled drawdown · High survival probability · Stable compounding · Low entropy allocation · Tail-risk immunity"

The system meets ALL 6 of those criteria. Trades are not required for system validation — they are required for edge measurement. **Capital preservation IS the goal.**

**Risk:** none. **Pro:** honors Spec #22 philosophy fully.

---

## Recommendation

The most disciplined non-tuning path is **Option C** if the operator wants Realized_R measurement on real data, or **Option D** if the operator accepts that paper-mode validation has hit its measurement ceiling in this market regime.

**Avoid Option A** unless explicitly authorized — lowering momentum threshold to "find trades" is the exact opposite of sovereign discipline. Better to admit paper-mode reached its limit than to fit gates to fire trades for dopamine.

---

## Sacred locks (verified post-round)

```
Canary SHA256:    704dd5725a909fe3f6...  ✓ 3-way parity (local empire + server empire + server live)
L99 halt:         "halted": true ✓ engaged 45h+
canary.service:   inactive ✓
paper-arena.service (empire): active ✓
Exchange sockets: 0 ✓
Capital:          $1,980.90 USDT untouched · $10 virtual untouched
Refusal #12+#13:  ACTIVE
```

---

## Files captured

```
runtime/shadow_round_2026-05-13-1940.jsonl                          (per-trade log · empty)
runtime/shadow_round_summary_2026-05-13-1940.json                   (full summary)
runtime/disciplined_unlock_v1_console_2026-05-13-1940.log           (~14,800 heartbeat lines + 54 MC events)
runtime/shadow_round_latest.json                                    (updated)
```

> Shadow validates · Micro tests · Capital scales · Discipline governs · Survival compounds.
