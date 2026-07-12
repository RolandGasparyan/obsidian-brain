#!/usr/bin/env bash
# start_slight_unlock_shadow.sh — Spec #23 Slight Unlock Shadow Mode
#
# Per governance/AGGRESSION_UNLOCK_MICRO_LIVE_SAFE_GATE_v1.md (spec #23, 2026-05-13).
#
# 🛡 Still PAPER-SAFE. LIVE_ORDERS=0 forced. This validates the Spec #23
# Section II envelope under simulated execution BEFORE any live consideration.
#
# Differences from default shadow round:
#   - Phase 2 composite gate: 80 (was 85)
#   - Phase 3 composite gate: 88 (was 90)
#   - Max trades per round:    3 (was 6)
#   - Max consec loss:         2 (was 3)
#   - Session DD freeze:       1.5% (was 2.0%)
#   - Default round length:    240 min / 4h (DISCIPLINED UNLOCK V1)
#
# DISCIPLINED UNLOCK V1 tuning (2026-05-13, post-2-rounds-zero-trades):
#   - Signal fire threshold:   47.5 (was 50)   ← mildly more permissive
#   - Momentum threshold:      0.15% (unchanged from prior slight_unlock)
#   - Macro block:             < 25 (was < 30) ← block only near-PANIC band
#   - Bayes Panic block:       > 65% (was > 55%) ← block only near-certain Panic
#
# UNCHANGED per operator "KEEP LOCKED": MA50W10 core · DD caps · halt protections ·
# rollback paths · sovereign freeze logic · live execution state (still LIVE_ORDERS=0).

set -euo pipefail

# ── Slight Unlock activator ──────────────────────────────────────────────
export SLIGHT_UNLOCK=1

# ── Mode (still paper) ───────────────────────────────────────────────────
export MODE="SHADOW_SLIGHT_UNLOCK"
export LIVE_ORDERS=0
export META_LEARNING="ROUND_END_ONLY"
export PHASE_STRUCTURE=1

# ── Spec #23 Section II params ──────────────────────────────────────────
export ROUND_LENGTH_MIN="${ROUND_LENGTH_MIN:-${ROUND_LENGTH:-240}}"  # 4h default (Disciplined Unlock V1)
export VIRTUAL_CAPITAL="${VIRTUAL_CAPITAL:-${CAPITAL:-10}}"
export BASE_ASSET="${BASE_ASSET:-USDT}"
export RISK_PER_TRADE="${BASE_RISK:-0.25}"
export MAX_RISK="${MAX_RISK:-0.40}"
export MAX_EXPOSURE="${MAX_EXPOSURE:-1}"
export MAX_CONCURRENT="${MAX_CONCURRENT:-1}"
export MAX_TRADES_TOTAL="${MAX_TRADES_TOTAL:-3}"
export MAX_TRADES_PER_ROUND="$MAX_TRADES_TOTAL"
export MAX_SESSION_DD="${MAX_SESSION_DD:-1.5}"
export DD_FREEZE_LEVEL="$MAX_SESSION_DD"
export AUTO_FREEZE_AFTER_CONSEC_LOSS="${AUTO_FREEZE_AFTER_CONSEC_LOSS:-2}"
export MAX_CONSEC_LOSS="$AUTO_FREEZE_AFTER_CONSEC_LOSS"
export TP_PCT="${TP_PCT:-1.0}"
export SL_PCT="${SL_PCT:-0.5}"
export SCAN_INTERVAL="${SCAN_INTERVAL:-10}"
export SCAN_TOP_PAIRS="${SCAN_TOP_PAIRS:-5}"
export NO_PYRAMIDING=1
export NO_CAPITAL_MIGRATION=1
export FULL_EXIT_TO_USDT=1
export INCLUDE_FEES=1
export SLIPPAGE_MODEL=1
export SPOT_FEE_TAKER="${SPOT_FEE_TAKER:-0.2}"

# ── Hard guard against accidental live ───────────────────────────────────
if [[ "${LIVE_ORDERS}" != "0" ]]; then
  echo "❌ REFUSED: slight_unlock shadow requires LIVE_ORDERS=0" >&2
  echo "   For live-micro see MICRO_LIVE_OPERATOR_CHECKLIST.md (5 operator steps)" >&2
  exit 2
fi

# ── Locate repo + runner ────────────────────────────────────────────────
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
RUNNER="${SCRIPT_DIR}/paper_battle/shadow_round.py"

if [[ ! -f "${RUNNER}" ]]; then
  echo "❌ runner not found: ${RUNNER}" >&2
  exit 1
fi

# ── Banner ───────────────────────────────────────────────────────────────
echo "🧠 Slight Unlock Shadow Mode Initialized (Spec #23 Section II)"
echo "🔓 Slight Unlock        : ENABLED (tighter envelope · slightly permissive signal)"
echo "⏱  Round Length        : ${ROUND_LENGTH_MIN} min"
echo "💰 Virtual Capital     : ${VIRTUAL_CAPITAL} ${BASE_ASSET}"
echo "📊 Real Market Data    : Gate.io public REST (no API key)"
echo "❌ Live Orders         : Disabled (LIVE_ORDERS=${LIVE_ORDERS})"
echo "🛡  Risk Envelope       : RISK/trade=${RISK_PER_TRADE}% · MAX_RISK=${MAX_RISK}% · "
echo "                         max_trades=${MAX_TRADES_TOTAL} · max_consec_loss=${AUTO_FREEZE_AFTER_CONSEC_LOSS} · "
echo "                         session_dd≤${MAX_SESSION_DD}%"
echo "🚪 New Entry Gates     : macro_score<30 BLOCK · bayes_panic>55% BLOCK"
echo "📁 Output Dir          : ${SCRIPT_DIR}/runtime/"
echo

exec python3 "${RUNNER}"
