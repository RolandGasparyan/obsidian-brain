---
type: execution-engine-index
date: 2026-05-13
tags: [shadow-round, execution, slippage, fees, phases]
ai-first: true
source: ~/Desktop/agent/paper_battle/shadow_round.py
---

# Execution Engine

> For future Claude: `shadow_round.py` v1.1 is the active execution simulator. Polls Gate.io public REST every 10s for 5 USDT pairs. Simulates entries with slippage + spread cross + 0.4% RT fees. Runs in 3 phases over 90-minute rounds. **LIVE_ORDERS=0 is enforced at three layers** (bash wrapper, Python env guard, runtime sys.exit). Cannot become live without operator clearing Refusal #12.

---

## How to invoke

```bash
# Standard 90-min round
~/Desktop/agent/start_shadow_round.sh

# Short test
ROUND_LENGTH_MIN=10 ~/Desktop/agent/start_shadow_round.sh

# Stop mid-round
~/Desktop/agent/stop_shadow_round.sh
```

Output paths:
- `~/Desktop/agent/runtime/shadow_round_YYYY-MM-DD-HHMM.jsonl` (per-trade log)
- `~/Desktop/agent/runtime/shadow_round_summary_YYYY-MM-DD-HHMM.json` (round summary)
- `~/Desktop/agent/runtime/shadow_round_latest.json` (always latest summary)
- `~/Desktop/agent/runtime/shadow_round.pid` (while running)

---

## Architecture

```
                  ┌─ start_shadow_round.sh (bash wrapper)
                  │   LIVE_ORDERS=0 forced + hard guard
                  ▼
                  ┌─ shadow_round.py (Python orchestrator)
                  │   Python guard: if LIVE_ORDERS != 0: sys.exit(2)
                  ▼
   ┌──────────────┴─────────────────┐
   │  every 10s scan tick           │
   │  fetch_tickers(5 pairs)        │
   │  update price + spread windows │
   ▼                                │
   ┌─ every 60s heartbeat ─┐        │
   │  recompute_macro      │ ◄──── macro_layer.py     [Spec #19]
   │  recompute_bayes      │ ◄──── bayesian_regime.py [Spec #20 I]
   │  if regime_shift:     │
   │    recompute_mc       │ ◄──── monte_carlo.py     [Spec #20 II]
   └──────────────────────┘        │
                                   │
   ┌─ on signal fire ──────────────┘
   │  simulate_trade
   │    risk_pct_base    = min(RISK_PER_TRADE, phase_cap)
   │    apply_macro      (Spec #19)
   │    apply_mc_compress (Spec #20 II)
   │    apply_entropy_compress (Spec #20 I)
   │    apply_Article3_hard_cap (Constitution)
   │  →  Trade record with full provenance
   ▼
   ┌─ at round end
   │  compute_round_summary
   │  compute_sovereign_survival_score (Spec #22)
   │  write JSON to runtime/
   └─
```

---

## Default Parameters (Spec #14 micro-test)

```yaml
BASE_ASSET:          USDT
VIRTUAL_CAPITAL:     10
RISK_PER_TRADE:      0.25%
MAX_EXPOSURE:        1%
MAX_CONCURRENT:      1
MAX_TRADES_PER_ROUND: 6
TP_PCT:              1.0%
SL_PCT:              0.5%
SCAN_INTERVAL:       10s
ROUND_LENGTH:        90 min
PAIRS:               BTC_USDT · ETH_USDT · SOL_USDT · BNB_USDT · XRP_USDT
LIVE_ORDERS:         0 (MUST)
```

---

## 3-Phase Round Structure

| Phase | Time | Risk Cap | Constraints |
|-------|------|----------|-------------|
| Phase 1 | 0-30m | ≤ 0.4% | Max 2 trades |
| Phase 2 | 30-75m | ≤ 0.6% | Composite ≥ 85 required |
| Phase 3 | 75-90m | ≤ 0.4% | Leading → defensive, Trailing → composite ≥ 90 |

---

## Slippage Model

```python
def simulate_slippage_pct(spread_pct, vol_5min_pct):
    base = 0.05
    vol_mult = max(0.0, vol_5min_pct) * 0.30      # 1% vol → +0.30% slip
    spread_impact = spread_pct * 0.50              # half-spread crossed
    return base + vol_mult + spread_impact
```

Plus exit slippage applied symmetrically. Plus 0.4% round-trip Gate.io taker fee (0.2% × 2).

→ At 0.10% slip each way + 0.40% fee = **0.60% total round-trip cost** vs **1.0% TP** = effectively half the modeled R captured. This is why edge_preservation hovers at ~50% in current parametrization — see [[../README#Cross-Reference Index]] for tuning options.

---

## Auto-Freeze Triggers

```python
def check_auto_freeze(self, last_slippage):
    if consec_losses >= 3:                           return FROZEN
    if max_dd_pct >= 2.0:                            return FROZEN  # Article 3
    if last_slip > 2.0 * avg_slip:                   return FROZEN  # spike
```

---

## Hard Safety Guards (3 layers)

```
LAYER A · Bash wrapper:
    start_shadow_round.sh line 13:  export LIVE_ORDERS=0
    start_shadow_round.sh line 30:  if [[ "${LIVE_ORDERS}" != "0" ]]: exit 2

LAYER B · Python env init:
    shadow_round.py line 96:        LIVE_ORDERS = _envi("LIVE_ORDERS", 0)

LAYER C · Python runtime guard:
    shadow_round.py line 113-119:
        if LIVE_ORDERS != 0:
            sys.stderr.write("❌ REFUSED: paper-safe only. See MICRO_LIVE_OPERATOR_CHECKLIST")
            sys.exit(2)
```

To switch to live: **all 3 layers must change** AND operator must complete steps 1-5 from `MICRO_LIVE_OPERATOR_CHECKLIST.md` AND a new `start_championship_live.sh` script must be built (does not exist yet — see Spec #16).

---

## Live Observation (90-min round in flight 2026-05-13)

```
PID:        41772
Elapsed:    ~63 min (of 90 min)
Memory:     30,576 KB stable
Trades:     0 (correct — DEFENSIVE/PANIC mode suppression)
Capital:    $10.0000 virtual untouched
Heartbeats: ~63 (one per minute)
MC runs:    3 (round_start + 2× regime shifts)
```

→ See [[DeploymentLogs/README]] for full session

---

## Cross-links

- [[MacroLayer/README]] — risk multiplier source
- [[RegimeModels/README]] — Bayesian entropy source
- [[MonteCarlo/README]] — Kelly compression source
- [[Governance/README#Pre-Commit Hook]] — last line of defense
- [[CapitalDefense/README#MICRO_LIVE_OPERATOR_CHECKLIST]] — operator steps to unlock live

## Source-of-truth

- `~/Desktop/agent/paper_battle/shadow_round.py` (935 lines, v1.1)
- `~/Desktop/agent/start_shadow_round.sh` (3 KB wrapper)
- `~/Desktop/agent/stop_shadow_round.sh` (0.9 KB stopper)
- `~/Desktop/agent/governance/SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md`
- `~/Desktop/agent/governance/PRODUCTION_READY_SHADOW_ENGINE_v1.md`
