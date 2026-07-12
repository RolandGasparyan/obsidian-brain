#!/usr/bin/env bash
# ============================================================
# quarantine_theater.sh — find the "theater" (fake-scoring + grade-vocab +
# broken lab + nested dup) and MOVE it (never delete) into _QUARANTINE_<ts>/.
#
#   DEFAULT = DRY-RUN: only lists what it would move. Changes nothing.
#   APPLY=1 = actually move the SAFE/inert items (docs, inactive fake lab,
#             nested dup). Code that may be imported by running engines is
#             only REPORTED, never auto-moved.
#
# HARD PROTECTED (never touched): the live bot, keys, running engines, venvs.
#   Review the quarantine folder, then YOU delete it. Nothing is deleted here.
# ============================================================
set -uo pipefail
BASE="${BASE:-$HOME/tradingguru-empire}"
APPLY="${APPLY:-0}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
QDIR="$BASE/_QUARANTINE_$TS"
MAN="$BASE/QUARANTINE_PLAN_$TS.txt"
cd "$BASE" || { echo "no $BASE"; exit 1; }

# never touch these (live money, keys, running engines, real tools, data, vcs)
PROTECT='(^|/)(canary|realmode|paper_battle|replay_engine|intelligence|arena_shadow_runner|strategy_lab_real|research|data|\.venv|node_modules|\.git|backups|\.api_key|\.env)'

moved=0; reported=0
log(){ echo "$*" | tee -a "$MAN"; }
do_move(){  # $1 = path (relative)
  local p="$1"
  if [ "$APPLY" = "1" ]; then
    mkdir -p "$QDIR/$(dirname "$p")"
    git mv "$p" "$QDIR/$p" 2>/dev/null || mv "$p" "$QDIR/$p"
    log "  MOVED  -> _QUARANTINE/$p"; moved=$((moved+1))
  else
    log "  WOULD MOVE  $p"; moved=$((moved+1))
  fi
}

log "=== Quarantine plan ($([ "$APPLY" = 1 ] && echo APPLY || echo DRY-RUN)) $TS ==="
log ""

log "## A. Nested duplicate repo folder (safe to quarantine)"
if [ -d "Trading Guru Empire" ]; then do_move "Trading Guru Empire"; else log "  (none)"; fi
log ""

log "## B. Fake / broken Strategy Lab (service is inactive)"
for f in strategy_lab.py strategy-lab.service; do
  [ -e "$f" ] && do_move "$f"
done
log ""

log "## C. Grade-theater MARKDOWN docs (inert — safe to quarantine)"
grep -rliE 'godmode|obliteratus|institutional_ready|sovereign_grade' --include=*.md . 2>/dev/null \
  | sed 's|^\./||' | grep -vE "$PROTECT" | grep -v '_QUARANTINE' | while read -r f; do do_move "$f"; done
log ""

log "## D. Random-scoring CODE (REPORT ONLY — may be imported by running engines)"
log "   Review each; move manually only after confirming nothing live imports it."
grep -rliE 'random\.(uniform|random|gauss|randint)' --include=*.py . 2>/dev/null \
  | sed 's|^\./||' | grep -vE "$PROTECT" | grep -v '_QUARANTINE' | while read -r f; do
    log "  REVIEW  $f"; done
log ""

log "=== summary: $([ "$APPLY" = 1 ] && echo moved || echo would-move) items in A-C; D is report-only ==="
log "Protected (untouched): live canary bot, API keys, running engines, venvs, data, .git."
log "Plan written to: $MAN"
[ "$APPLY" = "1" ] && log "Quarantine folder: $QDIR  (review, then YOU delete it)."
