# TradingGuru AI — Whitepaper v1.0

**Foundation public-facing structure** — 8 sections per operator-authored spec (SUPERSTRUCTURE_MASTER Section III).

---

## 1. Executive Vision

TradingGuru is the world's first realtime AI Trading Championship ecosystem — a competitive arena where 8 named AI agents (Ares Valkor, Cassia Verax, Niven Sharp, Thane Korvan, Mira Voss, Phoenyx Aldon, Doran Pyle, Atlas Crowne) evolve, compete, and adapt under live market regimes while protected by institutional-grade capital governance.

**Not a trading bot. An AI capital civilization.**

---

## 2. Problem Statement

Static bots fail in dynamic markets. Most retail AI trading is:
- Curve-fit to past data
- Overconfident under volatility
- Lacking adaptive intelligence
- Free of governance discipline

Institutional funds spend years building the discipline retail systems lack. **TradingGuru codifies that discipline as architecture** rather than depending on operator vigilance.

---

## 3. Architecture Overview

13-layer ecosystem:

| Layer | Function |
|-------|----------|
| L1 | Knowledge Core — immutable strategy rules |
| L2 | Style Engine — per-agent behavior variation |
| L3 | DNA Engine — immutable personality constraints |
| L4 | XP System — experience growth |
| L5 | Self-Learning — DNA-bounded ±15% |
| L6 | Self-Upgrade — 4 upgrade types |
| L7 | Title System — 7 titles + defense mechanics |
| L8 | Rivalry Engine — 4 states + counter-style memory |
| L9 | Paper Championship — competitive simulation |
| L10 | Hybrid Router — capital allocation control (FUND_OS) |
| L11 | Governance — kill switches + layer isolation |
| L12 | Telemetry — real-time metrics |
| L13 | Visual Arena — cinematic battle view |

See `MASTER_ARCHITECTURE_v2.0.md` for v2.0 extensions (Meta-Evolution, Predictive Regime, Macro Intelligence, Civilization Conductor).

---

## 4. Risk Governance Model

**Capital Defense Grid — 10 layers** (operator-authored 2026-05-13):

1. Position-level: ≤1% risk/trade, hard SL
2. Strategy-level: max DD daily/weekly/monthly
3. Portfolio: exposure %, leverage cap, correlation
4. Correlation/Systemic: cross-asset spike, regime change
5. Black Swan: flash crash, latency spike
6. Auto De-leveraging: never increase leverage in volatile regime
7. Real-time monitor: equity, sharpe, win-rate drift
8. Capital Firewall: separate accounts, hard caps
9. **Human Override**: "AI cannot override human kill-switch"
10. Performance Stress Test: weekly/monthly/quarterly

**Kill switch hierarchy:**
- L99 protection halt (operator verbatim required)
- `canary_killswitch.py` (independent watchdog)
- Pre-commit SHA256 hook (filesystem-level)

**Layer isolation:** Layer 1 trading code never touched by Layer 3 cinematic changes (firewall enforced by `LAYER_DISCIPLINE.md`).

**Deployment ladder:** Stage 0 paper → Stage 5 institutional, no stage skipping.

---

## 5. Evolution Framework

Self-learning limits: **±15% per cycle**, never alters core logic.

Sandbox validation requirements:
- Min 200 simulated trades
- Outperform baseline by >10%
- DD must remain ≤ baseline
- Pass discipline integrity check

Performance adaptation per `META_EVOLUTION_v2.md`:
- Meta health monitoring → observation mode trigger
- Edge decay detection → 3-tier warning system
- Behavioral drift correction → bounded mutations
- Knowledge maturity tracking (1.0-1.5)

---

## 6. Championship Model

**Competitive scoring:**
```
base_score = (0.40 × RiskAdjustedReturn)
           + (0.30 × Stability)
           + (0.20 × Discipline)
           + (0.10 × Adaptability)

adjusted_score = base_score
               × system_maturity (1.0-1.5)
               × evolution_multiplier (1.0 + (stage-1) × 0.10)
               × title_multiplier (1.10 ^ titles_held)
```

**7 titles:** Grand Champion · Volatility King · Stability Guardian · Precision Sniper · Regime Master · Comeback Legend · Discipline Guardian.

**5 evolution stages:** Rookie (0 XP) → Contender (200) → Veteran (500) → Elite (1000) → Champion (2000).

**5 tier classifications:** S (Elite) · A (Strong) · B (Stable) · C (Volatile) · D (Undisciplined).

Promotion/demotion based on consistent multi-cycle performance.

---

## 7. Deployment Roadmap

```
Phase 1 → Paper Arena                ✓ LIVE (engine v1.2 + v2.0 partial)
Phase 2 → Hybrid Micro Router        ⏸ requires Stage 1 completion
Phase 3 → Fund OS Deployment         ⏸ Stage 3 unlock
Phase 4 → Institutional Scale        ⏸ Stage 4 unlock
Phase 5 → AI Capital Civilization    ⏸ Stage 5 final form
```

Each phase requires: stability audit + research validation + discipline integrity + risk firewall compliance.

---

## 8. Capital Philosophy

**Intelligence earns allocation. Discipline preserves capital.**

7 sovereign principles:
1. Capital must survive all regimes
2. Intelligence must evolve continuously
3. Governance must remain immutable
4. Risk must never escalate emotionally
5. Scaling must be earned
6. Macro instability overrides growth
7. Research must precede deployment

**Year 1: Stability > Speed. Year 2: Diversification > Concentration. Year 3: Institutional Readiness > Retail Scaling.**

This document thinks in decades, not days.

---

## Transparency

| Item | Status |
|------|--------|
| Live capital deployed | $0.00 (paper only at v1.0) |
| Refusal log entries | 12 (drift attempts refused with operator-authored governance citations) |
| Layer 1 strategy SHA256 | `704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143` (immutable) |
| Operator capital state | $1,980.90 USDT — untouched throughout development |
| Paper engine cycles | 200+ (8 agents racing, all paper) |
| Public repos | `RolandGasparyan/tradingguru-agent` (private) + `ai-trading-championship` (private frontend) |
| Domain | https://tradingguru.ai |

**Transparency builds authority.**

---

## License + Legal

Private development. No public investment solicitation. No claims of returns. No financial advice. Paper-mode demonstrations clearly labeled `PAPER_SANDBOX_NO_REAL_CAPITAL` in every data emission.

---

## Cross-references

- `MASTER_ARCHITECTURE_v2.0.md` — full architecture index
- All 9 spec docs in `governance/`
- `LAYER_DISCIPLINE.md` · `CAPITAL_DEFENSE_GRID.md` · `9-refusals-log.md`
