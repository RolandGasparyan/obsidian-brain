#!/usr/bin/env bash
# start_shadow_round.sh — paper-safe shadow round launcher
# Per governance/SHADOW_ROUND_EXECUTION_PROTOCOL_v1.md (spec #17, 2026-05-13).
#
# 🛡 LIVE_ORDERS forced to 0. Refuses to launch if any env overrides this.

set -euo pipefail

# ── Mode (immutable for this script) ─────────────────────────────────────
export MODE="SHADOW_CHAMPIONSHIP"
export LIVE_ORDERS=0
export META_LEARNING="ROUND_END_ONLY"
export PHASE_STRUCTURE=1

# ── Defaults (overridable via env) ───────────────────────────────────────
export ROUND_LENGTH_MIN="${ROUND_LENGTH_MIN:-${ROUND_LENGTH:-90}}"
export VIRTUAL_CAPITAL="${VIRTUAL_CAPITAL:-${CAPITAL:-10}}"
export BASE_ASSET="${BASE_ASSET:-USDT}"
export RISK_PER_TRADE="${RISK_PER_TRADE:-0.25}"
export MAX_EXPOSURE="${MAX_EXPOSURE:-1}"
export MAX_CONCURRENT="${MAX_CONCURRENT:-1}"
export MAX_TRADES_PER_ROUND="${MAX_TRADES_PER_ROUND:-6}"
export TP_PCT="${TP_PCT:-1.0}"
export SL_PCT="${SL_PCT:-0.5}"
export SCAN_INTERVAL="${SCAN_INTERVAL:-10}"
export SCAN_TOP_PAIRS="${SCAN_TOP_PAIRS:-5}"
export MAX_CONSEC_LOSS="${MAX_CONSEC_LOSS:-3}"
export DD_FREEZE_LEVEL="${DD_FREEZE_LEVEL:-2}"
export NO_PYRAMIDING=1
export NO_CAPITAL_MIGRATION=1
export FULL_EXIT_TO_USDT=1
export INCLUDE_FEES="${INCLUDE_FEES:-1}"
export SLIPPAGE_MODEL="${SLIPPAGE_MODEL:-1}"
export SPOT_FEE_TAKER="${SPOT_FEE_TAKER:-0.2}"

# ── Hard guard against accidental live ───────────────────────────────────
if [[ "${LIVE_ORDERS}" != "0" ]]; then
  echo "❌ REFUSED: start_shadow_round.sh requires LIVE_ORDERS=0" >&2
  echo "   For live-micro see MICRO_LIVE_OPERATOR_CHECKLIST.md" >&2
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
echo "🧠 Shadow Championship Mode Initialized"
echo "⏱ Round Length        : ${ROUND_LENGTH_MIN} min"
echo "💰 Virtual Capital    : ${VIRTUAL_CAPITAL} ${BASE_ASSET}"
echo "📊 Real Market Data   : Gate.io public REST (no API key)"
echo "❌ Live Orders        : Disabled (LIVE_ORDERS=${LIVE_ORDERS})"
echo "🛡 Discipline         : RISK/trade=${RISK_PER_TRADE}% · MAX_EXP=${MAX_EXPOSURE}% · TP=${TP_PCT}% · SL=${SL_PCT}%"
echo "🔬 Simulation         : slippage_model=${SLIPPAGE_MODEL} · include_fees=${INCLUDE_FEES}"
echo "📁 Output Dir         : ${SCRIPT_DIR}/runtime/"
echo

exec python3 "${RUNNER}"
