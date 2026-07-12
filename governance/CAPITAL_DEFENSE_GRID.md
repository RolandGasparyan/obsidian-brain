# Capital Defense Grid v1.0

**Operator-authored:** 2026-05-13
**Status:** ACCEPTED · integrated into v1.0+ governance stack
**Relationship to existing docs:**
- **Strengthens** `LAYER_DISCIPLINE.md` (adds operational risk layers below the 5-gate strategy lock)
- **Strengthens** `9-refusals-log.md` rationale base (Layer 9 = explicit AI-override-prohibition on human kill-switch)
- **Complements** ADR-004 (paper battle architecture has zero capital risk by design — this doctrine governs the future LIVE pathway)

---

## System purpose

> Protect capital at all costs.
> Prevent catastrophic loss.
> Preserve long-term survival.
> Enable controlled scaling.

---

## Defense Philosophy

| Rule | Statement |
|------|-----------|
| 1 | Survival > Profit |
| 2 | Capital preservation first |
| 3 | Drawdown containment |
| 4 | Controlled exposure |
| 5 | Automatic intervention before disaster |

---

## 10-Layer Defense Stack

### Layer 1 — Position-Level Defense
- Fixed % risk per trade (≤ 0.5–1%)
- Hard stop-loss required
- Max position size cap
- Volatility-adjusted sizing
- No averaging down without predefined logic
- No martingale logic
- Slippage tolerance threshold
- Max holding duration (if strategy requires)

**Auto-trigger:** position loss > predefined threshold → immediate exit.

### Layer 2 — Strategy-Level Defense
- Max daily drawdown
- Max weekly drawdown
- Max monthly drawdown
- Max consecutive losing trades
- Equity curve slope monitoring
- Performance deviation tracking

**Auto-trigger:** drawdown exceeds historical tolerance → reduce size 50%. Second breach → halt strategy.

### Layer 3 — Portfolio Defense Grid
- Max total portfolio exposure %
- Sector / asset-class allocation cap
- Leverage cap
- Margin utilization ceiling
- Correlation clustering detection
- Beta exposure monitoring

**Auto-trigger:** portfolio volatility spike > threshold → reduce exposure or close weakest positions first.

### Layer 4 — Correlation & Systemic Risk Shield
Monitors: cross-asset correlation spike, market regime change, volatility regime shift, liquidity contraction, macro event risk window.

**Auto-trigger:** systemic instability → reduce exposure, defensive allocation, pause new entries.

### Layer 5 — Black Swan Containment Protocol
Emergency triggers: flash crash detection, spread widening anomaly, broker execution delay, API latency spike, news shock detection, extreme gap risk.

**Auto-actions:** close high-risk positions, remove leverage, freeze new entries, move to cash allocation.

### Layer 6 — Auto De-Leveraging Engine
When volatility increases: position size auto-adjust, leverage auto-reduce, risk-per-trade auto-scale-down, exposure compression activated. **Never increase leverage in volatile regime.**

### Layer 7 — Real-Time Risk Monitor
Tracks: equity curve stability, Sharpe deviation, win-rate drift, slippage drift, liquidity shifts, execution latency.

**Auto-action:** anomaly > tolerance → alert / reduce size / full halt.

### Layer 8 — Capital Firewall Structure
- Separate trading account
- Hard capital cap
- No auto-transfer
- Withdrawal protection
- Periodic profit extraction
- Compartmentalized capital pools

**Never expose total capital.**

### Layer 9 — Human Override Grid 🛑

> **AI cannot override human kill-switch.**

Human retains:
- Instant kill-switch
- Exposure override
- Strategy pause
- Leverage restriction authority

**Note:** L99 protection halt at `/root/.l99/protection_halt.json` IS the human kill-switch under this doctrine. Engaged by operator verbatim "stop all trades" 2026-05-12 06:51 UTC. **Per Layer 9, Claude cannot clear it** — only operator can, via explicit verbatim plus a decision doc that satisfies the 5-gate requirement in `LAYER_DISCIPLINE.md`.

### Layer 10 — Performance Stress Test Loop
- Weekly: compare live vs expected variance, stress-test with volatility spike simulation
- Monthly: drawdown resilience check, risk-adjusted return review
- Quarterly: full portfolio stress simulation, black swan scenario modeling, liquidity crisis test

---

## Escalation Matrix

| Level | Trigger | Action |
|-------|---------|--------|
| 1 | Warning | Reduce size 25% |
| 2 | Breach | Reduce size 50% |
| 3 | Critical | Halt strategy |
| 4 | Systemic | Liquidate to defensive allocation |

---

## Defense Doctrine

> Capital is ammunition.
> Protect ammunition.
> Win long-term war.

---

## Integration with current governance

| Existing doc | How Capital Defense Grid relates |
|---|---|
| `LAYER_DISCIPLINE.md` (5-gate Layer 1 lock) | Strategic / design-time lock. Capital Defense Grid is the operational / runtime lock. Both required. |
| `9-refusals-log.md` | Each refusal can now also cite specific Capital Defense Grid layer (esp. Layer 9). |
| `canary_config.json` caps ($100/$30/$2/48h) | Maps to Layer 1 (position-level) + Layer 8 (capital firewall) |
| `canary_killswitch.py` | Implements Layer 5 + Layer 7 auto-triggers |
| `/root/.l99/protection_halt.json` | **IS** the Layer 9 human override artifact |
| `_archive_2026-05-13/` cleanup | Reduces attack surface — consistent with Layer 8 compartmentalization |
| Paper engine + paper-arena.json | Inherently complies — zero capital, zero leverage, zero orders |

---

## Status of each layer in current production

| Layer | Current implementation status |
|-------|-------------------------------|
| 1 — Position-level | DEFINED in `canary_config.json` ($30/trade cap, 1 concurrent position max) · NOT ACTIVE (canary inactive) |
| 2 — Strategy-level | DEFINED ($2 loss / 48h timeout per ARMING_CHECKLIST) · NOT ACTIVE |
| 3 — Portfolio | N/A (single-strategy single-asset for canary phase) |
| 4 — Correlation/Systemic | N/A (single-asset BTC/USDT) |
| 5 — Black Swan | PARTIAL (killswitch logic in `canary_killswitch.py`, STALE_OHLCV_DETECTOR patch applied) |
| 6 — Auto De-leveraging | N/A (canary is unleveraged spot) |
| 7 — Real-time monitor | PARTIAL (terminal.json publishes, no auto-halt logic yet) |
| 8 — Capital firewall | DEFINED (Gate.io sub-account requirement in arming protocol) · NOT YET PROVISIONED |
| 9 — Human override | **ACTIVE** (`/root/.l99/protection_halt.json` engaged 30h+) |
| 10 — Stress test loop | NOT YET SCHEDULED (weekly/monthly cron jobs to define in v1.1) |

---

## What this changes about current refusals (clarification)

The Capital Defense Grid **does not** remove any operator-authored discipline. It **adds** doctrine. Specifically:

- Refusal #11 (live mode trading after this session's empire-build marathon) is now also citable to **Capital Defense Grid Layer 9** — AI cannot override the human kill-switch (L99 halt). Only the operator clearing it via explicit verbatim + decision doc allows progression.
- Future canary arming must satisfy: (a) LAYER_DISCIPLINE.md 5 gates AND (b) Capital Defense Grid Layer 8 (Gate.io sub-account provisioning) AND (c) Layer 9 (operator clears halt explicitly) AND (d) Layer 10 (stress test loop scheduled).

---

## Cross-references

- `governance/LAYER_DISCIPLINE.md` — strategic/design-time discipline
- `governance/BRANCH_LOCK.md` — multi-session coordination
- `governance/ADR-004-paper-battle-architecture.md` — paper-mode architecture (zero capital, by design)
- `docs/9-refusals-log.md` — refusal record
- `canary/ARMING_CHECKLIST.md` — operator authorization sequence
- `canary/canary_killswitch.py` — automated safety circuit
- `/root/.l99/protection_halt.json` — Layer 9 human override artifact (currently engaged)
