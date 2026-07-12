# FUND_OS_ULTRA v2.0 — Ultra Institutional Capital System

**Operator-authored:** 2026-05-13 (extracted from spec #3 + #7)
**Status:** ACCEPTED · documented · NOT ARMED (paper-only, no live capital)
**Layer:** L10 (Hybrid Router) — gated behind operator authority

---

## Mission

Deploy capital safely with institutional governance.

---

## Layer 1 — Capital Segregation

```
Master Account
  ├── Strategy Sub-Accounts (one per strategy)
  ├── Research Sandbox Account
  ├── Canary Account ($100 cap)
  └── Long-Term Preservation Vault
```

**Rules:**
- No cross-account auto-transfer
- Each account has independent kill-switch
- Master account read-only by Claude (operator-only write)

---

## Layer 2 — Multi-Strategy Capital Router

```
allocation_score =
  (0.4 × stability_score)
+ (0.3 × regime_alignment_score)
+ (0.2 × discipline_score)
+ (0.1 × research_confidence_score)
```

Capital distributed proportionally.

---

## Layer 3 — Dynamic Exposure Control

Absolute caps:
- Max risk per trade ≤ 1%
- Max total exposure ≤ 5%
- Max correlated exposure ≤ 2%

Emergency compression: **-50% risk reduction instantly** on trigger.

---

## Layer 4 — Real-Time Risk Monitor

Continuously tracks:
- Equity volatility
- Consecutive loss clustering
- Liquidity anomalies
- Spread explosion
- Execution latency

If anomaly detected → **immediate freeze**.

---

## Layer 5 — Deployment Ladder

```
Stage 0 → Paper only            ✓ CURRENT
Stage 1 → $10 micro             ⏸ requires LAYER_DISCIPLINE 5/5
Stage 2 → $100 canary           ⏸ requires Stage 1 success
Stage 3 → Controlled scale      ⏸ requires Stage 2 success
Stage 4 → Multi-agent live      ⏸ requires Stage 3 success
Stage 5 → Institutional AUM     ⏸ requires Stage 4 fund-grade proof
```

Each stage requires validation audit.

---

## Fund Principle

**Capital must earn the right to scale.**

---

## Implementation status

| Component | Status |
|-----------|--------|
| Capital segregation | DOCUMENTED — accounts not provisioned (no live capital) |
| Router formula | DOCUMENTED — would activate Stage 1+ |
| Dynamic exposure caps | ENFORCED in `canary_config.json` ($100/$30/$2/48h) |
| Real-time risk monitor | Partial (`canary_killswitch.py` implements Layer 5/7) |
| Deployment ladder | Stage 0 — paper engine v1.2 running |

---

## To activate Layer 1+ (operator actions)

1. Provision Gate.io sub-account ($10-50 USDT funded)
2. Place trade-only API key at `/root/canary/.api_key` chmod 600
3. Author `wiki/decisions/2026-05-XX-stage1-arm.md` decision doc
4. Sign `/root/canary/canary_arm.json`
5. Verbatim clear L99 halt
6. Claude verifies 5 LAYER_DISCIPLINE gates + Capital Defense Layer 8/9

Steps 1-5 are **operator-only authority artifacts**. Claude cannot generate them.

---

## Cross-references

- `MASTER_ARCHITECTURE_v2.0.md`
- `LAYER_DISCIPLINE.md` — 5-gate strategic lock
- `CAPITAL_DEFENSE_GRID.md` — Layer 8 capital firewall + Layer 9 human override
- `canary/ARMING_CHECKLIST.md` — operator authorization sequence
