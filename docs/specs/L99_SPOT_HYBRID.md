# L99 Structural Spot Hybrid — God Mode ∞

**Source:** Operator spec, 2026-04-25
**Status:** Spec only. No code. Saved for D7+ planning conversation per ADR-003.
**Audit:** Annotated by Claude. Buildable / aspirational / reject sections clearly separated.

---

## I. The original spec (verbatim)

```
PRIMARY OBJECTIVE
  Grow USDT balance consistently. Always rotate back to USDT.
  No leverage. No overnight holds. No emotional holding.

  Round-trip fee ≈ 0.2%
  Minimum required net edge ≥ 0.35%
  Target expansion: 0.7% – 3%

INFRASTRUCTURE REALITY
  Exchange: Gate.io Spot · Latency: Retail-grade · Data: WebSocket
  order book + trades · No tick-level cancel visibility · No HFT fantasies.
  Trade only real structural expansion.

LAYER 1 — MARKET INTELLIGENCE
  [1] Volatility Scanner   rank USDT pairs by 5m ATR + 1m accel; top 3
  [2] Liquidity Filter      reject wide spread / thin depth / low volume
  [3] BTC Correlation       BTC unstable → reduce size 40%

LAYER 2 — MICROSTRUCTURE CORE
  [4] Depth Imbalance       DIR > 1.4 required
  [5] Delta Burst           30s delta > 1.5σ baseline
  [6] Absorption            confirm continuation; reject traps
  [7] Spread Stability      no widening spikes during entry

LAYER 3 — STRUCTURAL VALIDATION
  [8] Breakout Validator    local resistance break + volume
  [9] Volatility Expansion  compression → expansion only
  [10] Momentum Persistence reject single impulse spikes

LAYER 4 — ADAPTIVE INTELLIGENCE
  [11] Self-Learning Weights   rebalance every 50 trades; bounds [5%, 35%]
  [12] RL Edge Memory          store {regime, DIR, delta, spread, BTC, result}
                                low expectancy → raise threshold + reduce size
                                strong → allow compounding

LAYER 5 — CROSS-EXCHANGE CONFIRMATION
  [13] Cross-Exchange Liquidity Scanner
       monitor Binance / OKX / Bybit
       external impulse aligns → pre-activation
       divergence → block trade

LAYER 6 — EXECUTION ENGINE
  [14] Fee-Aware Edge        expected − 0.2% − slippage ≥ 0.35%, else reject
  [15] Maker Execution       post-only limit; cancel stale > 1000ms; no chasing

LAYER 7 — HYBRID LOGIC
  Initial mode SCALP (target 0.6–0.9%, stop −0.4%).
  On continuation: BE stop, target 1.5–3%, trail structure.
  Convert scalp → micro swing automatically.

LAYER 8 — ULTRA MICRO MODE
  Activated when: vol spike + cross-exchange alignment + tight spread.
  Logic: 10s delta accel + liquidity vacuum + aggression clustering.
  Target 0.4–0.8%. Max hold 90s. Max 2 attempts/session. Fail twice → disable.

LAYER 9 — RISK & EQUITY CONTROL
  [16] Risk Throttle      base 1%, 2L → 0.6%, 3L → cooldown, daily 4% → shutdown
  [17] Equity Drift       detect edge decay; reduce frequency
  [18] Compounding        +3% session → +15% size; cap 1.5%; revert on DD

FINAL GOD ARBITER
  Adaptive Composite = Dynamic Weights × Regime Expectancy
                      × Cross-Exchange Confidence × Edge × Risk
  Entry score ≥ 84, edge ≥ 0.35%
  Ultra mode score ≥ 92
  Otherwise HOLD USDT

CORE PHILOSOPHY
  Trade only expansion. Never chase. Never hope. Always rotate to USDT.
  System > Ego. Edge > Frequency. No clarity → no trade.
```

---

## II. Feasibility audit — layer by layer

### 🟢 Buildable on current Gate.io retail stack

| Layer | What's needed | Where it slots into the existing repo |
|---|---|---|
| L1.1 Vol Scanner | 5m ATR + 1m acceleration ranking | extend `aegis_alpha/scanner.py` (~50 LoC) |
| L1.2 Liquidity Filter | spread + 24h vol + book depth gates | new method on `MarketContext` |
| L1.3 BTC Correlation | BTC vol regime classifier | promote `VoteEnsembleStrategy._btc_signal()` to a shared context method |
| L2.4 Depth Imbalance | DIR ≥ 1.4 | already in `godmode/streams.py::MicrostructureStream` |
| L2.5 Delta Burst | STD Z-score ≥ 1.5σ | already in `MicrostructureStream` (uses `ctx.std_z()`) |
| L2.6 Absorption | bullish/bearish absorption + trap detection | currently stubbed `godmode/streams.py::AbsorptionStream` — implement |
| L2.7 Spread Stability | spread tick-over-tick variance | already in `godmode/streams.py::ExecutionQualityStream` |
| L3.8 Breakout Validator | local high break + volume confirmation | currently stubbed `StructuralBreakStream` — implement |
| L3.9 Volatility Expansion | compression → expansion logic | already in `VolatilityRegimeStream` |
| L3.10 Momentum Persistence | reject single-candle impulse | new method on `MarketContext` |
| L6.14 Fee-Aware Edge | net edge ≥ 0.35% (spot calibration per ADR-002) | already in `FeeEdgeStream` — needs threshold update from 0.12% → 0.35% |
| L6.15 Maker Execution | post-only with 1000ms cancel | new module `godmode/maker_executor.py` |
| L7 Hybrid Logic | per-trade state machine (scalp/micro-swing) | new module `godmode/trade_lifecycle.py` |
| L9.16 Risk Throttle | 1% / 0.6% / cooldown / 4% halt | already in `RiskThrottleStream`, mostly aligned with audit Patches 1+3 |
| L9.17 Equity Drift | rolling Sharpe / hit-rate decay detector | new module `godmode/drift_monitor.py` |
| L9.18 Compounding | dynamic sizing on session PnL | extend `RiskThrottleStream.allowed_risk()` |

**Estimated effort: 1–2 weeks of focused work**, post-D7, conditional on Phase A signal.

### 🟡 Aspirational — requires data we don't have yet

| Layer | Why it's blocked | Realistic timeline |
|---|---|---|
| **L4.11 Self-Learning Weights** | Needs ≥ 50 labeled trade outcomes to compute meaningful weight updates. Current Vote bots have produced ~4 trades. | 30–60 days of paper-forward minimum |
| **L4.12 RL Edge Memory** | RL state→action→reward needs 1,000+ samples for stable Q-value estimates. Even after 60 days at 6–15 trades/year/pair × 4 pairs = 24–60 trades. | **6–12 months** of paper data, OR augment with backtest-replay of historical regimes |
| **L5.13 Cross-Exchange Liquidity** | New WebSocket clients × 3 venues (Binance, OKX, Bybit). Each has different message format, rate limits, RTT distribution. Synchronization to a common clock requires careful engineering. | ~1 week per exchange = 3 weeks of pure infrastructure |

These are real, valuable additions — but they are **separate projects**, not Phase B. They build on top of a working Phase B.

### 🛑 Reject as currently specified

**L8 Ultra Micro Mode.** The spec opens with *"No HFT fantasies"* and explicitly states *"No tick-level cancel visibility."* Layer 8 then asks for:

- 10-second delta acceleration  → needs cancel-rate visibility we don't have
- Liquidity vacuum detection    → needs tick-level cancel deltas (proven impossible on Gate.io public WS earlier in this thread)
- 90-second max hold            → fee math fails: 0.20% RT + slippage on 0.4–0.8% target = 0.10–0.40% net edge, fails Layer 14's own ≥ 0.35% gate ~half the time

This is the same trap as the original God-Mode spec. Building it would re-introduce the audit's main critique: chasing fantasy performance on infrastructure that physically can't deliver it.

**Honest reframing:** if the operator wants a high-conviction "ultra mode," it should be the SAME 18-agent system with a higher composite-score threshold (already in spec: ≥ 92 for ultra). A separate engine with shorter holds is not the right shape on this stack.

---

## III. The 3-month sequencing (post-D7, conditional on Phase A)

```
D7  (May 1)    Phase A analyzer verdict. Pick α/β/γ from ADR-002 table.
D8–D14         Build Phase B chosen architecture.
                One of α/β/γ — NOT the full 18-agent L99-Spot-Hybrid yet.

D15–D45        30-day paper-forward of Phase B.
                Patches 1+3+5 active. Vote bots run alongside as control.

D45+           IF Phase B paper PnL > 0 AND ≥ 50 labeled trades collected:
                Start L4.11 Self-Learning Weights (refresh existing weights;
                does NOT yet train RL memory).

D60+           IF still positive AND ≥ 100 labeled trades:
                Add L1.1 Vol Scanner + L1.2 Liquidity Filter
                (rotation across top-N pairs).

D90+           IF still positive AND ≥ 500 labeled trades:
                Start L5 Cross-Exchange Confirmation (Binance first,
                others if first one shows divergence value).

D120+          IF cross-exchange shows additive edge AND total ≥ 1,000 trades:
                Start L4.12 RL Edge Memory (SQLite-backed, daily
                expectancy regression by regime).

NEVER on this stack: L8 Ultra Micro as separately specified.
                The score-≥92 path within the main system is the
                honest version. Latency physics doesn't change.
```

Every step is gated by paper PnL evidence. Skipping a gate is how every
retail algo trader audited in GODMODE_AUDIT.md blew up.

---

## IV. What this changes about ADR-001 / ADR-003

**Nothing.** ADR-003's hard rule still applies — no new strategy code on
`main` for 5 days. This document is reference material for the D7+
conversation. ADR-002's decision table still gates Phase B selection.
ADR-001's fallback to B1 (on-chain) still triggers if the analyzer
finds no signal.

The honest readout: this spec is the **destination architecture**, not the
**next step**. The next step is the same as before — wait for D6.

---

## V. Action items

- [x] Spec saved to `docs/specs/L99_SPOT_HYBRID.md` (this file)
- [ ] D6 (Apr 30): Phase A analyzer run — gate decides whether L99-Spot-Hybrid
       work begins at all
- [ ] D7+: if green-lit, port the buildable subset (sec II) into `godmode/`
       in priority order: L2 (already done) → L3 (impl stubs) → L9 (already
       partial) → L1 → L6 → L7 → L4-skeleton → L5 → L4-RL
- [ ] If analyzer kills the thesis, this spec gets the same archive treatment
       as the original God-Mode spec — kept for record, not built
