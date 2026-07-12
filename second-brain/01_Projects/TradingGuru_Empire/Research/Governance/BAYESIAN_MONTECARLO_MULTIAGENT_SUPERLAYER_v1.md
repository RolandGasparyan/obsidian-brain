# BAYESIAN_MONTECARLO_MULTIAGENT_SUPERLAYER v1.0

**Operator-authored:** 2026-05-13 (spec #20 in v2.0 dump)
**Status:** ACCEPTED · documented · **PARTS I + II IMPLEMENTED** · Part III deferred (multi-agent allocator)
**Significance:** Advanced predictive + stress + allocation intelligence layer. Probabilistic regime anticipation + forward stress validation + dynamic capital orchestration.

---

## Three Parts

| Part | Subject | Status |
|------|---------|--------|
| **I** | Bayesian Regime Transition Model | ✓ implemented in `paper_battle/bayesian_regime.py` |
| **II** | Monte Carlo Forward Stress Overlay | ✓ implemented in `paper_battle/monte_carlo.py` |
| **III** | Multi-Agent Macro-Weighted Allocation Matrix | ⏳ DEFERRED — requires multi-agent signal wiring |

Parts I + II are paper-safe and self-contained. Part III requires extending shadow runner from single-strategy to 8-agent simulation (the 8 named characters from paper_battle_engine.py v1.2: Ares Valkor, Cassia Verax, Niven Sharp, Thane Korvan, Mira Voss, Phoenyx Aldon, Doran Pyle, Atlas Crowne). That is a larger architectural change — design decision needed first.

---

## Part I — Bayesian Regime Transition Model

### Regime set
```
R = {Trend, Chop, Expansion, Compression, Panic, Recovery}
```

### Update rule
```
posterior(R_t) ∝ likelihood(X | R_t) × Σ_i transition(R_t-1=i → R_t) × prior(R_t-1=i)
```

### Inputs (X)
- Volatility percentile
- ADX slope (approximated by momentum-decay rate)
- Momentum decay rate
- Correlation cluster change
- Volume expansion/contraction
- Spread instability index
- Funding imbalance (deferred — requires futures REST call)

### Transition matrix (operator-specified excerpts)
```
T[Trend → Chop]            = 0.22
T[Trend → Panic]           = 0.05
T[Chop → Expansion]        = 0.30
T[Compression → Expansion] = 0.48
T[Panic → Recovery]        = 0.60
```

Full 6×6 matrix codified in `bayesian_regime.py` with row-normalization.

### Output
```
REGIME_PROB_VECTOR = {
    "Trend":       0.34,
    "Chop":        0.18,
    "Expansion":   0.22,
    "Compression": 0.09,
    "Panic":       0.11,
    "Recovery":    0.06
}
dominant_regime = argmax(REGIME_PROB_VECTOR)
entropy = Shannon(REGIME_PROB_VECTOR)   # high entropy → reduce aggression
```

### Integration with shadow_round
- Computed once per heartbeat (every minute)
- `dominant_regime` logged per trade
- `entropy` used by macro layer to compress risk when uncertainty is high (>1.6 nats)

---

## Part II — Monte Carlo Forward Stress Overlay

### Inputs
- Rolling win probability
- Average R-multiple
- Slippage mean + variance
- Fee impact
- Regime volatility factor
- Current drawdown
- Risk per trade

### Simulation
- N = 5,000–10,000 capital paths (configurable, default 5000)
- Each path simulates 20 forward trades
- Per trade: sample win/loss from Bernoulli(p) · sample R from realized R distribution · apply slippage/fee
- Apply risk compression rules (DD-aware)

### Outputs
```python
{
    "expected_final_equity":     10.27,
    "p05_equity":                 9.42,    # 5th percentile worst-case
    "p95_equity":                11.18,    # 95th percentile best-case
    "max_dd_distribution_p95":    0.0234,  # 2.34%
    "risk_of_ruin_pct":           0.18,    # %
    "median_time_to_recovery":   12,
    "cagr_estimate_pct":         11.4,
}
```

### Overlay logic
```
if projected_DD > constitutional_tolerance OR risk_of_ruin > 1%:
    auto_compress_kelly_factor
    reduce_risk_multiplier
    disable_aggressive_mode
```

### Trigger schedule
- At round start
- After 3 consecutive losses
- When macro regime shifts (dominant_regime change)

→ Bounded invocations (not per-tick), keeps CPU bounded.

---

## Part III — Multi-Agent Macro-Weighted Allocation Matrix (DEFERRED)

### Agent set (8, from `paper_battle_engine.py` v1.2)
```
A = {Ares Valkor, Cassia Verax, Niven Sharp, Thane Korvan,
     Mira Voss, Phoenyx Aldon, Doran Pyle, Atlas Crowne}
```

Spec uses generic role names (HUNTER, RISK, ALPHA, REGIME, EXECUTOR, RECOVERY, SKEPTIC, CHAMPION) — to be mapped onto the 8 named characters via their DNA traits.

### Allocation formula

**Step 1** — Regime Weighting
```
Agent_Regime_Score_i = Σ (Regime_Prob_r × Agent_Performance_in_Regime_i,r)
```

**Step 2** — Stability adjustment
```
if agent.dd_rising:           weight *= 0.7
if agent.exec_stability < 80: weight *= 0.6
```

**Step 3** — Macro overlay
```
if GLOBAL_MACRO_SCORE < 40: bias toward {RISK, RECOVERY, SKEPTIC}
if GLOBAL_MACRO_SCORE > 70: bias toward {HUNTER, ALPHA, REGIME}
```

**Step 4** — Normalize
```
Final_Weight_i = Agent_Regime_Score_i / Σ(all agents)
```

### Constraints
- Single agent cap ≤ 40%
- Min allocation ≥ 5%
- Total exposure ≤ constitutional limit (1% in micro)

### Why deferred
Current `shadow_round.py` is single-strategy. To wire Part III properly:
1. Each of the 8 agents needs its own per-tick signal generator
2. Per-regime historical performance needs persistent storage
3. Stability metrics need rolling tracking per agent
4. Allocator runs each tick or each minute to set per-agent risk weighting
5. Total scope: ~400-600 lines new code + state file design

**Recommendation:** Design discussion with operator on whether to:
- (a) reuse existing `paper_battle_engine.py` agent definitions and shadow them in parallel
- (b) define 8 lightweight signal variants inline in shadow runner
- (c) replace single-strategy shadow with multi-agent shadow as v2 of shadow runner

---

## Part V — Hard Safety Guarantees (verbatim)

This superlayer **CANNOT**:
- Override stop-loss
- Override exposure caps
- Override drawdown compression
- Increase leverage ceiling
- Remove governance firewall

It **can ONLY**:
- Adjust weighting
- Compress risk
- Unlock controlled expansion (within constitutional bounds)
- Reallocate internal capital share

---

## Part VI — Advanced Metrics Exposed

Added to shadow round summary:
- Regime Entropy Index
- Macro Pressure Index (from spec #19)
- Monte Carlo Ruin Probability
- (deferred) Agent Allocation Heatmap
- (deferred) Capital Concentration Risk Score
- Regime Transition Acceleration

---

## Final declaration (verbatim)

> This is not indicator stacking.
> This is:
>   Probabilistic regime anticipation
>   + Forward stress validation
>   + Dynamic capital orchestration
>
> Discipline remains supreme. Prediction guides risk. Simulation validates survival. Allocation optimizes structure.
> **Shadow first. Micro later. Scale earned.**

---

## Cross-references

- `SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md` (spec #17) — base protocol
- `PRODUCTION_READY_SHADOW_ENGINE_v1.md` (spec #18) — production bar
- `AI_GLOBAL_MACRO_PREDICTION_LAYER_INTEGRATION_v1.md` (spec #19) — companion macro layer
- `AI_DISCIPLINE_CONSTITUTION.md` Article 3 — hard caps inviolable
- `paper_battle/paper_battle_engine.py` — 8 named agents available for Part III wiring
- `MASTER_ARCHITECTURE_v2.0.md` — index
