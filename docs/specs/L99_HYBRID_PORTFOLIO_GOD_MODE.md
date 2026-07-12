# L99 — CONTROLLED AGGRESSIVE + HYBRID PORTFOLIO GOD MODE

**Source:** Operator spec, 2026-05-01 (D7 day 1)
**Status:** Spec preserved verbatim · NOT implemented · candidate for [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) branch B.2.4
**Pre-req:** ANY engine in this spec requires a validated edge first; current state is 🛑 D6 NO-GO, no edge in microstructure data class.

---

## I. The original spec (verbatim)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L99 — CONTROLLED AGGRESSIVE + HYBRID PORTFOLIO GOD MODE
Spot-Optimized | Risk-Governed | Multi-Engine Architecture
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CORE PRINCIPLE:
Aggression without risk discipline = capital destruction.
Aggression inside structured portfolio = controlled alpha expansion.

This architecture combines:

1. ⚡ Controlled Aggressive Momentum Engine
2. 🧠 Institutional Core Engine
3. 🔬 Adaptive Acceleration Engine (optional)
4. 📊 Portfolio Risk Governor (Master Layer)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — CAPITAL STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Capital Allocation Model:

50% → Institutional Core Engine
35% → Controlled Aggressive Momentum
15% → Acceleration / Research Engine

Global Hard Rules:
Max total exposure: 8%
Max single position: 1.2%
Max total DD: 20%
Kill-switch at 25%

No engine may override master risk.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — ENGINE A: CONTROLLED AGGRESSIVE MOMENTUM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Purpose:
Capture volatility expansion bursts without degenerating into scalping chaos.

Universe:
Top 40 USDT spot pairs
24h volume ≥ 15M
Spread ≤ 0.10%
Volatility percentile ≥ 45%

Entry Conditions (ALL REQUIRED):

1. Breakout above 20-period range high
2. Volume ≥ 170% of 20-period avg
3. Delta acceleration positive spike
4. ATR expanding vs baseline
5. Fee-adjusted minimum move ≥ 0.8%

Stop:
1R hard stop

Take Profit:
2R primary
Trail at 1.5R

Cooldown:
2 consecutive losses → 6h cooldown
4 consecutive losses → disable until next regime shift

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — ENGINE B: INSTITUTIONAL CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Purpose: Stable +EV baseline.

Universe: Top 75 liquid pairs · 24h volume ≥ 10M · spread ≤ 0.15%

Entry: Multi-timeframe alignment (4H + 1H) · Breakout + continuation ·
       Volume ≥ 130% · Regime must be NORMAL or EXPANSION

Stop: 1R   Take Profit: 2–2.5R

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — ENGINE C: ADAPTIVE ACCELERATION (OPTIONAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Purpose: Exploit high impulse regime only.

Active only when:
  BTC volatility percentile ≥ 70%
  Market breadth ≥ 65%
  Spread stable

Risk: 0.5R per trade · Max exposure: 2%
Disabled automatically if rolling 20 trades PF < 1.1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5 — MASTER REGIME ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Market Regimes: DEAD · NORMAL · EXPANSION · HIGH IMPULSE

Rules:
DEAD          → All engines disabled
NORMAL        → Institutional Core active
EXPANSION     → Core + Aggressive active
HIGH IMPULSE  → All engines allowed

Regime via: vol percentile · volume percentile · spread stability ·
            breadth score · BTC structural momentum

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6 — PORTFOLIO RISK GOVERNOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Max correlated exposure ≤ 4% per sector cluster
Max simultaneous trades ≤ 6
Daily loss ≥ 3R → trading paused 24h
Weekly loss ≥ 6R → reduce all engine risk by 50%
No compounding without passing rolling 50 gate.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7 — DRIFT PROTECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Disable engine if:
  Rolling IC < 0.02
  Win rate < 44%
  Profit factor < 1.15
  Spread anomalies increase

Auto-disable. Manual review required to re-enable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 8 — PERFORMANCE TARGET PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Win rate: 48–55%
Avg R/WIN: 2.0+
Profit factor: 1.3–1.7
Controlled volatility · higher growth than pure institutional ·
lower chaos than pure aggressive

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 9 — WHAT THIS MODE IS / IS NOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IS:    disciplined aggression · layered capital intelligence ·
       portfolio-structured alpha · risk-aware expansion ·
       spot-compatible momentum engine

IS NOT: scalping fantasy · leverage gambling · AI miracle edge ·
        unbounded compounding
```

---

## II. Why this spec is taken seriously

Unlike earlier vibe-pastes today, this spec has:

1. **Numerical thresholds** (8% max exposure, 1.2% max position, 25% kill-switch, 1R hard stops)
2. **Drift protection** (auto-disable on IC < 0.02, WR < 44%, PF < 1.15) — this matches the project's existing discipline framework
3. **Explicit "is NOT" disclaimers** — author understands the failure modes
4. **Layered governance** — engines cannot override master risk; performance gates required for compounding
5. **Regime-conditional activation** — engines disabled in DEAD regime
6. **Spot-compatible design** — no leverage, no futures, no scalping fantasy

This is a **legitimate Phase B candidate spec**, not a vision paste.

## III. The non-negotiable prerequisite

**The spec assumes the engines have edge.** That assumption is exactly what 5 convergent rigor levels (filter battery, signal-nature, Bayesian sweep, ensemble alignment, D6 binding) just disproved for our current data class.

| Engine | What it needs to work | Project state |
|---|---|:---:|
| **A: Aggressive Momentum** | Breakout + delta acceleration + ATR expansion ≥ 0.8% net of fees | 🛑 these features tested in 7-filter battery; Q5−Q1 < 30 bps |
| **B: Institutional Core** | Multi-TF alignment (4H+1H) producing positive expectancy | 🛑 MA50+W10 family failed; Vote ensemble paper -2.40% over 7d |
| **C: Adaptive Acceleration** | Same features as A under high-impulse regime | 🛑 same features tested; same null result |
| **Master Regime** | Vol/volume/spread/breadth percentile classifier | ✅ infrastructure exists (`regime_classifier.py`) |
| **Risk Governor** | Per-trade R sizing + portfolio caps | ✅ Patches 1+3+5 already implement most of this |

**Three of four engines depend on signals our rigor levels have proven null.** Implementing them on `main` would just be a more sophisticated way to deploy null edge.

## IV. What this spec gives us that's genuinely NEW

| Section | Already in project | New / spec adds |
|---|---|---|
| Capital allocation 50/35/15 | — | ✅ explicit allocation model |
| Max exposure / position caps | partial (Patch 1: per-trade hard stop) | ✅ portfolio-level 8% / 1.2% |
| Kill-switch 25% | — | ✅ explicit threshold |
| Engine cooldown (2 losses → 6h) | partial | ✅ structured cooldown rules |
| Multi-engine portfolio orchestration | — | ✅ this is the new piece |
| Master regime classifier | `regime_classifier.py` exists | partially in code, not wired |
| Drift auto-disable (IC/WR/PF gates) | manual review only | ✅ formal automated thresholds |
| Universe filters (volume/spread/vol percentile) | partially | ✅ explicit numbers |
| Sector cluster correlation cap | — | ✅ new portfolio-level rule |

**The most valuable new pieces are:** capital allocation model, portfolio-level risk governor, formal drift-disable automation, sector correlation cap.

## V. Honest validation gating

Before ANY engine in this spec deploys to a live bot:

1. **Edge proof required** — Engine A/B/C each need ≥1 signal class with Q5−Q1 magnitude > fee gate over the engine's holding horizon. Current state: NONE proven.
2. **4-gate validation** (`rsi2_validate.py`-style) for each engine: rolling walk-forward / Monte Carlo permutation / fee stress / bootstrap CI. ≥3 of 4 pass.
3. **Stage 1 paper validation** (60 days, ≥30 closed trades, PnL>0, DD<5%, Sharpe≥0.5) per engine before Stage 2 real-money.
4. **Stage 2 real $200** (90 days) per `CHAMPION_MODE.md` doctrine.

**Earliest credible deployment: ~70-100 days after edge is discovered.** Not before.

## VI. Mapping to PHASE_B_DECISION_TREE.md

Branch this spec **adds to the decision tree**:

```
🛑 NO-GO  (D6 confirmed)  →  branch B
                              ├─ B.2.1 ensemble                  (tested, null)
                              ├─ B.2.2 maker execution simulation (post-D7, needs L3 data)
                              ├─ B.2.3 on-chain B1 fallback        (post-D7, awaiting API keys)
                              └─ B.2.4 Hybrid Portfolio God Mode   (THIS SPEC, gated by signal-class edge)
```

**B.2.4 is conditional on B.2.3 finding edge.** Without an edge to feed into Engine A/B/C, the multi-engine orchestrator is just a more sophisticated way to lose money.

## VII. What I will NOT do for this spec

- ❌ Implement Engine A/B/C on `main` before edge proof
- ❌ Skip 4-gate validation
- ❌ Skip Stage 1 paper validation
- ❌ Bypass `CHAMPION_MODE.md` capital ladders
- ❌ Treat the spec's expected performance (WR 48-55%, PF 1.3-1.7) as anything but aspirational targets

## VIII. What I CAN do for this spec NOW (research only, ADR-compliant)

| Task | Output | Status |
|---|---|:---:|
| Save spec verbatim to repo | this file | ✅ done |
| Add B.2.4 branch to PHASE_B_DECISION_TREE | doc update | next |
| Sketch capital-allocation orchestrator scaffolding (NO LIVE WIRING) | `champion/portfolio_governor.py` skeleton | possible post-D7 |
| Implement drift-disable automation (auto-disable on IC/WR/PF thresholds) | extension of existing patches | possible post-D7 |
| Implement portfolio risk governor (correlation cap, simultaneous-trade limit) | extension of `gods_level_engine.py` | possible post-D7 |

Drift-disable automation and portfolio risk governor are the parts that work **without requiring an edge** — they're risk infrastructure. Those can be built and tested with synthetic data.

## IX. The honest order of operations

1. **D7 active** ✅ (today, May 1)
2. **B.2.3 on-chain B1 collection** ← gated on user supplying free API keys (CryptoQuant + Glassnode + Whale Alert)
3. **5-day passive collection** of B1 data
4. **7-filter battery on B1** (existing toolchain, schema-compatible)
5. **IF any cell survives** → 4-gate validate → Stage 1 paper deploy single-cell strategy
6. **IF Stage 1 clears** → consider implementing B.2.4 multi-engine orchestrator on top
7. **Stage 2 real $200** → ladder per `CHAMPION_MODE.md`

**Multi-engine orchestration is meaningful AFTER we have at least one validated engine.** Not before.

## X. Sources / linked docs

- Spec source: operator paste, 2026-05-01
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — overall branch structure
- [GODMODE_AUDIT.md](../../GODMODE_AUDIT.md) — Patches 1+3+5 risk overlay
- [CHAMPION_MODE.md](../../CHAMPION_MODE.md) — staged capital ladder
- [B1_RESEARCH.md](../../B1_RESEARCH.md) — on-chain prerequisite for any engine
- [wiki/findings/2026-04-30-d6-binding-no-go.md](../../wiki/findings/2026-04-30-d6-binding-no-go.md) — proof current data class is null

---

_Saved to repo as a research artifact 2026-05-01. NOT executable. Will become actionable only after Phase B B.2.3 (or another B-prime branch) produces a validated edge worth orchestrating._
