# Decision — Stage 1 Micro Live Arm · 2026-05-14

**Author:** Roland Gasparyan
**Date:** 2026-05-14
**Purpose:** Authorize $10 USDT canary live test per Spec #14 + Spec #22 sovereign envelope

> 📋 **THIS IS A TEMPLATE.** Copy to `docs/decisions/2026-05-14-stage1-micro-arm.md` (drop the `.TEMPLATE` suffix), fill the bracketed sections, then sign at the bottom. Claude will refuse to proceed (step 6+ in MICRO_LIVE_OPERATOR_CHECKLIST.md) until the final file exists.

---

## 1 · Decision (verbatim — DO NOT EDIT)

> Authorize $10 USDT canary live test per Spec #14 micro parameters, with Spec #23 envelope tighter where stricter, and Spec #22 sovereign-grade abort conditions.

---

## 2 · Backtest evidence

Strategy: **MA50W10** (SHA256 `704dd5725a909fe3f6...` · canary/canary_strategy.py · 3-way parity verified)

Per `governance/MA_STRATEGY.md` (if present) or `canary/canary_config.json` `_meta.strategy_backtest_ref`:

- Returns:        **+3,427% over 7.5 years chained**
- Sharpe:         **2.81**
- Max DD:         **-23%**
- Avg trades/yr:  **~10**

Strategy is **binary**: 100% in OR 100% out. Canary scales down position size to $30 fixed (never martingales).

---

## 3 · Shadow validation summary (3 rounds completed pre-arm)

| Round | Date | Mode | Sovereign Score | Trades | Violations |
|-------|------|------|-----------------|--------|------------|
| R1 baseline | 2026-05-13 | SHADOW_CHAMPIONSHIP | 73.18 INSTITUTIONAL_READY | 0 | 0 |
| R2 slight_unlock | 2026-05-13 | SHADOW_SLIGHT_UNLOCK | 73.34 INSTITUTIONAL_READY | 0 | 0 |
| R3 disciplined unlock V1 | 2026-05-13 → 14 | SHADOW_SLIGHT_UNLOCK + V1 tuning | 73.44 INSTITUTIONAL_READY | 0 | 0 |

3-round trend: **+0.26 sovereign score** · capital preserved 100% · 0 governance violations across all rounds.

**Why advancing despite 0 trades:** shadow paper-mode cannot fire signal in calm BTC regime (4h range 0.5%, momentum < 0.15% threshold). Sovereign score **73.44 ≥ 55 MICRO_READY** threshold = passes Stage 1 progression gate. Real Gate.io execution will produce Realized_R on real market momentum.

---

## 4 · Authorized parameters (Spec #14 + Spec #23 envelope · tighter-wins)

```yaml
MODE:                MICRO_LIVE_SAFE
BASE_ASSET:          USDT
TEST_CAPITAL:        10 USDT (isolated sub-account)
RISK_PER_TRADE:      0.25%
MAX_RISK:            0.40%
MAX_EXPOSURE:        1%
MAX_CONCURRENT:      1
MAX_TRADES_PER_DAY:  3
MAX_LIFETIME_HOURS:  168 (7 days)
TP_PCT:              1.0%
SL_PCT:              0.5%
SESSION_DD_FREEZE:   1.5%
CONSEC_LOSS_FREEZE:  2
SCAN_TOP_PAIRS:      5
SCAN_INTERVAL:       10s
NO_PYRAMIDING:       true
NO_CAPITAL_MIGRATION:true
FULL_EXIT_TO_USDT:   true
NO_STRATEGY_MUTATION:true
```

These are the LIVE values. Article 3 hard caps (≤ 0.75% per trade) remain inviolable.

---

## 5 · Rationale

[OPERATOR · FILL THIS · WHY ARMING NOW · why these parameters · why this strategy · why this risk envelope]

---

## 6 · Rollback path

If anything goes wrong:

```bash
# 1. Stop service immediately
ssh root@167.71.24.86 'systemctl stop canary.service'

# 2. Re-engage L99 halt manually if cleared
ssh root@167.71.24.86 'echo "{\"halted\": true, \"reason\": \"OPERATOR_MANUAL_ROLLBACK_$(date -u +%Y-%m-%d)\", \"ts\": $(date +%s), \"engaged_by\": \"operator_manual\"}" > /root/.l99/protection_halt.json'

# 3. Verify all stopped
ssh root@167.71.24.86 'systemctl status canary.service && ss -tnp | grep -iE "gate|bybit"'

# 4. Investigate via journalctl + canary logs
ssh root@167.71.24.86 'journalctl -u canary.service --since "1 hour ago" --no-pager'
ssh root@167.71.24.86 'cat /root/canary/runtime/decisions.log /root/canary/runtime/trades.log'
```

Auto-rollback triggers (Failure Protocol Spec #14 Section VII):
- 3 consec losses → freeze + alert
- DD ≥ 2% ($0.20 from peak at $10) → freeze + alert
- Slippage anomaly > 0.1% deviation → freeze + investigate
- Regime misclassification (Bayesian Panic locked at >65% for sustained period) → freeze
- API instability (3 consec REST failures) → freeze

---

## 7 · Verbatim approval signature

I, **Roland Gasparyan**, authorize the Stage 1 micro live test on **2026-05-14** with the parameters listed in Section 4 above. Capital at risk is limited to **$10 USDT** in isolated sub-account. All other capital ($1,980.90 USDT main) remains in vault, untouched. Auto-halt triggers per LAW 3 (no live mutation) and Section VII Failure Protocol of Spec #14. I accept that AI cannot override my kill-switch authority (Constitution Article 6 + Capital Defense Grid Layer 9).

Signed: **Roland Gasparyan**
Date: **2026-05-14**
Location: **[OPERATOR · FILL]**

---

## 8 · Cross-references

- `governance/AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md` (Spec #14 · operational protocol)
- `governance/AGGRESSION_UNLOCK_MICRO_LIVE_SAFE_GATE_v1.md` (Spec #23 · envelope this inherits)
- `governance/MICRO_LIVE_OPERATOR_CHECKLIST.md` (this is step 3 of 9 in that checklist)
- `governance/AI_DISCIPLINE_CONSTITUTION.md` (Article 3 hard caps · Article 6 human override)
- `governance/CAPITAL_DEFENSE_GRID.md` (Layer 9 kill-switch sovereignty)
- `audit/2026-05-13/SLIGHT_UNLOCK_ROUND_REPORT.md` (R2 results)
- `audit/2026-05-14/DISCIPLINED_UNLOCK_V1_ROUND_REPORT.md` (R3 results + recommendation)
- `canary/canary_config.json` (live execution config · IMMUTABLE)
- `canary/ARMING_CHECKLIST.md` (technical arming procedure)
