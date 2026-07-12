#!/usr/bin/env bash
# Strategy Lab — VPS runner (light: pandas venv, NO OpenBB, reads lab_data CSVs).
# Real backtests, paper-only. NO live execution, no API keys, no orders.
set -uo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
export LAB_DATA="$DIR/lab_data"
export LAB_OUT="$DIR/results"
mkdir -p "$LAB_OUT"
PY="$DIR/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
# refresh fresh DAILY data (ccxt public OHLCV) so the forward record keeps advancing
echo "$(date -u +%FT%TZ) strategy-lab (vps) fetch fresh data"
FETCH_PAIRS=BTC,ETH LAB_DATA="$LAB_DATA" "$PY" "$DIR/fetch_btc.py" || echo "fetch skipped"
echo "$(date -u +%FT%TZ) strategy-lab (vps) backtest"
"$PY" "$DIR/lab.py"
# anti-drift gate on the LONG history (bull+bear), separate from the 1y lab_data
echo "$(date -u +%FT%TZ) live-eligibility gate"
GATE_DATA="$DIR/gate_data" GATE_OUT="$LAB_OUT" "$PY" "$DIR/validation_gate.py" || echo "gate skipped"
# regenerate the single source of truth (authorized.json) from the gate
AUTH_OUT="$LAB_OUT" "$PY" "$DIR/authorize.py" || echo "authorize skipped"
# paper forward-test of the validated setup (MA50W10/BTC)
FWD_DATA="$LAB_DATA" FWD_OUT="$LAB_OUT" FWD_PAIR=BTC "$PY" "$DIR/forward_test.py" || echo "forward-test skipped"
# alert ONLY when the validated setup flips state (CASH<->BTC)
# Telegram creds (optional) come from .tg_env — YOU fill it; never stored in code.
[ -f "$DIR/.tg_env" ] && . "$DIR/.tg_env" || true
FWD_OUT="$LAB_OUT" "$PY" "$DIR/signal_alert.py" || echo "alert skipped"
# paper shadow-executor: forward (out-of-sample) track record of the validated edge
SHADOW_DATA="$LAB_DATA" SHADOW_OUT="$LAB_OUT" SHADOW_PAIR=BTC "$PY" "$DIR/shadow_executor.py" || echo "shadow skipped"
# rebuild the static dashboard (served by tge-dashboard.service)
DASH_DIR="$DIR/dashboard" LAB_OUT="$LAB_OUT" "$PY" "$DIR/build_dashboard.py" || echo "dashboard skipped"
exit 0
