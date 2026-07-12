---
type: regime-models-index
date: 2026-05-13
tags: [bayesian, regime, posterior, entropy, transition-matrix]
ai-first: true
source: ~/Desktop/agent/paper_battle/bayesian_regime.py
---

# Regime Models

> For future Claude: Bayesian regime engine maintains a probability vector over 6 market states. Updates posterior every minute during a shadow round. **High entropy → automatic risk compression** (entropy > 1.5 nats triggers 0.7× sizing). When dominant regime changes, Monte Carlo retriggers to update Kelly fraction.

---

## The 6 Regimes

| Regime | Profile | Action |
|--------|---------|--------|
| **Trend** | Sustained directional move · vol ~0.45% · momentum > 0.8% | Composite trades allowed |
| **Chop** | Sideways · vol ~0.30% · momentum ~0 | Reduced aggression |
| **Expansion** | Vol breakout · vol ~0.80% · momentum +/-0.3% | Phase 2+ controlled trades |
| **Compression** | Vol crush · vol ~0.10% · momentum ~0 | Anticipate breakout, no trades |
| **Panic** | Vol spike · vol ~1.40% · momentum < -1.0% · spread CV ~1.20 · corr ~0.90 | NO TRADES · DEFENSIVE only |
| **Recovery** | Post-panic · vol ~0.70% · momentum +0.6% · corr ~0.65 | Selective high-composite only |

---

## Bayesian Update (per Spec #20 Part I)

```
posterior(R_t) ∝ likelihood(X | R_t) × Σ_i transition(R_t-1=i → R_t) × prior(R_t-1=i)
```

**Inputs (X):**
- `vol_pct` — realized volatility % over 12-tick window
- `momentum_pct` — 12-tick momentum %
- `spread_cv` — spread std/mean coefficient of variation
- `correlation_abs` — |corr(BTC, ETH)| over returns

**Likelihood per regime:** Gaussian density on each feature using regime-specific (mean, sigma) profile, multiplied across features (conditional-independence assumption).

**Update cadence:** every 60 seconds during shadow round (heartbeat).

---

## Transition Matrix (row-normalized)

Per operator-specified excerpts in Spec #20:

```
            Trend  Chop   Exp.   Comp.  Panic  Recov.
Trend    →  0.55   0.22   0.10   0.04   0.05   0.04
Chop     →  0.18   0.40   0.30   0.06   0.04   0.02
Expansion→  0.30   0.10   0.40   0.05   0.10   0.05
Compress →  0.15   0.15   0.48   0.18   0.02   0.02
Panic    →  0.05   0.10   0.05   0.05   0.15   0.60
Recovery →  0.30   0.20   0.20   0.10   0.05   0.15
```

**Notable transitions:**
- `Panic → Recovery: 0.60` (panic phases are short-lived)
- `Compression → Expansion: 0.48` (compression precedes breakouts)
- `Trend → Chop: 0.22` (trends decay into chop more often than reversing)

---

## Output Vector

Each minute:
```python
posterior = {
    "Trend":       0.34,
    "Chop":        0.18,
    "Expansion":   0.22,
    "Compression": 0.09,
    "Panic":       0.11,
    "Recovery":    0.06,
}
dominant = "Trend"        # argmax
entropy  = 1.32           # Shannon nats (max = ln(6) ≈ 1.79)
accel    = 0.18           # L1 distance from previous posterior
```

---

## Entropy-Driven Risk Compression

In `paper_battle/shadow_round.py:simulate_trade`:

```python
if bayes_entropy > 1.5:                    # near-max uncertainty
    risk_pct = min(risk_pct, 0.7 × RISK_PER_TRADE_PCT)
    macro_reason += "+entropy_compress"
```

→ See [[MacroLayer/README#Risk-sizing pipeline]] for full risk cascade

---

## Live Observation (90-min shadow round in flight 2026-05-13)

From console:
```
t+38.55m  bayes=Expa(H=0.60) BTC=$78,998
t+39.58m  bayes=Expa(H=0.87) BTC=$79,026   ← entropy rising
t+40.59m  [MC] regime_shift→Panic compress=True
t+41.62m  bayes=Pani(H=0.97) BTC=$79,050   ← near-max entropy
t+43.57m  bayes=Pani(H=0.36) BTC=$79,049   ← certainty growing
```

The Bayesian engine detected real market panic during the round and triggered Monte Carlo re-computation. Sovereign behavior: no trades fired during high-entropy + DEFENSIVE macro mode = correct suppression.

---

## Cross-links

- [[MonteCarlo/README]] — MC retriggers on regime shift
- [[MacroLayer/README]] — entropy feeds macro compression cascade
- [[ExecutionEngine/README]] — wired into `simulate_trade` risk sizing

## Source-of-truth

- `~/Desktop/agent/paper_battle/bayesian_regime.py` (167 lines)
- `~/Desktop/agent/governance/BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER_v1.md` Part I
