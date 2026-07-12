# SHADOW_ROUND_EXECUTION_PROTOCOL v1.0

**Operator-authored:** 2026-05-13 (spec #17 in v2.0 dump)
**Status:** ACCEPTED · documented · **PAPER-SAFE — buildable + runnable without Refusal #12 clearance**
**Significance:** The bridge between paper-mode (v1.2) and live-micro. Real market data + simulated execution + no real orders.

---

## Why this spec is different

Specs #14, #15, #16 all converge on live capital. **Spec #17 explicitly disables live orders** (`LIVE_ORDERS=DISABLED`) and replaces them with a slippage simulation model on real market data. This makes it the **first runnable step** in the adaptive-championship sequence — no operator artifacts required, no L99 clearance needed.

This is also the **safest validation** of Spec #15's measurement framework before live data flows.

---

## Mode Definition

```
MODE: SHADOW_CHAMPIONSHIP
LIVE_ORDERS: 0 (disabled)
MARKET_DATA: realtime (Gate.io public WS)
EXECUTION: simulated_with_slippage_model
ROUND_LENGTH: 90 minutes
PHASE_STRUCTURE: active
META_LEARNING: round_end_only
```

---

## Section I — Shadow Config

```yaml
BASE_ASSET: USDT
VIRTUAL_CAPITAL: 10

RISK_PER_TRADE: 0.25%
MAX_EXPOSURE: 1%
MAX_CONCURRENT: 1
MAX_TRADES_PER_ROUND: 6

TP_PCT: 1.0%
SL_PCT: 0.5%

NO_PYRAMIDING: 1
NO_CAPITAL_MIGRATION: 1
FULL_EXIT_TO_USDT: 1
```

---

## Section II — Execution Simulation Model

```
entry_price = best_bid_or_ask  +  slippage_model_output
slippage_model:
    base = 0.05%
    vol_multiplier = f(realized_volatility_5min)
    spread_impact = f(current_spread)

exit_simulation:
    + spot_fee_round_trip (Gate.io ~0.2% taker)
    + spread_at_exit
    + slippage_exit
    + execution_delay (50-300ms simulated)

realized_R = (exit_px - entry_px) / risk_size  − all_costs
```

---

## Section III — Phase Logic (Active)

| Phase | Time | Risk cap | Constraints |
|-------|------|----------|-------------|
| Phase 1 | 0–30 min | ≤ 0.4% | Max 2 trades |
| Phase 2 | 30–75 min | ≤ 0.6% | Composite score ≥ 85 required |
| Phase 3 | 75–90 min | — | Leading → defensive · Trailing → composite ≥ 90 only |

---

## Section IV — Data Logging

**Per-trade row:**
- Regime classification
- Composite score
- Simulated slippage
- Modeled R
- Realized R
- Execution delay
- Spread entry / exit
- DD state
- Aggression level

**Round summary:**
- Net USDT
- Expectancy
- Sharpe (shadow)
- Max DD
- Execution stability score
- Regime performance map

Output paths:
- `runtime/shadow_round_YYYY-MM-DD-HHMM.jsonl` (per-trade)
- `runtime/shadow_round_summary_YYYY-MM-DD-HHMM.json` (round summary)

---

## Section V — Shadow Success Criteria

Minimum 1 full 90-min round.

**PASS if:**
- ✅ Modeled vs Realized R deviation < 10%
- ✅ Zero governance breaches
- ✅ Phase switching logic correct
- ✅ Drawdown compression triggers correctly
- ✅ Aggression switching follows spec
- ✅ Execution model produces stable variance

PASS → eligible for micro-live progression (still requires operator steps 1-5).
FAIL → adjust slippage model / phase logic in sandbox.

---

## Section VI — Shadow Run Command

The spec's run command:

```bash
export MODE="SHADOW_CHAMPIONSHIP"
export LIVE_ORDERS=0
export ROUND_LENGTH=90
export META_LEARNING="ROUND_END_ONLY"

./start_shadow_round.sh
```

**Status:** Script `start_shadow_round.sh` does not currently exist. Python-equivalent runner can be built as `paper_battle/shadow_round.py` and wired to existing `paper-arena.service` or run as standalone `shadow-round.service`.

---

## Implementation Plan (paper-safe, no Refusal #12 required)

| Component | Implementation path |
|-----------|--------------------|
| `shadow_round.py` runner | New file: `paper_battle/shadow_round.py` |
| Real-time market data | Reuse existing Gate.io public WS subscriber (already paper-engine-wired) |
| Slippage simulator | New function in `shadow_round.py`: `simulate_slippage(side, vol, spread)` |
| Phase logic | Wrap existing `compute_predictive_regime()` + `determine_adaptive_mode()` |
| Round-end summary | New function: `compute_round_summary()` |
| 90-min timer | Standard `asyncio.sleep(90*60)` or systemd timer |
| Per-trade JSONL log | Append to `runtime/shadow_round_*.jsonl` |
| Round JSON summary | Write to `runtime/shadow_round_summary_*.json` |
| Frontend exposure | Extend `paper-arena.json` with `shadow_round` block (still classifier-clean — no live capital touched) |
| Systemd service | `shadow-round.service` (analog of `paper-arena.service`) |

**Estimated build time:** ~45-60 min from green light.

**Safety:** Zero exchange API writes. Read-only public WS. No `.api_key` consumed. L99 halt remains engaged. Canary SHA256 untouched. Capital $1,980.90 USDT untouched.

---

## Cross-references

- `AI_SOVEREIGN_EMPIRE_CORE_WITH_MICRO_TEST_v1.md` (spec #14) — parameters mirror micro-test
- `REAL_EXECUTION_LIVE_TRANSITION_MASTER_v1.md` (spec #15) — measurement schema this populates
- `ADAPTIVE_EVOLVING_CHAMPIONSHIP_ENGINE_v1.md` (spec #16) — same round/phase structure, LIVE version
- `MICRO_LIVE_OPERATOR_CHECKLIST.md` — operator artifacts needed BEFORE live equivalent
- `MASTER_ARCHITECTURE_v2.0.md` — index
