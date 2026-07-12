#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
# tradingguru.ai — switchover helper
# Companion to design/tradingguru-ai-corrected/SWITCHOVER_PLAN.md
#
# RUNS ON THE VPS, not from a Claude session.
# Copy this file to root@167.71.24.86 first, then `bash switchover.sh <step>`.
#
# Steps:
#   0  snapshot — back up /var/www/ai-trading-championship + nginx config
#   4  disable  — stop+disable any live-trading services still around
#   6  verify   — curl each route and grep for fake claims / corrected hero
#   7  retire   — rename the old docroot aside (run only after ~24h soak)
#   rollback    — restore from the most recent /root/backups/site-* snapshot
#
# Step 5 (nginx server-block edit) is NOT automated — it requires reading
# your specific config; SWITCHOVER_PLAN.md step 5 has the exact diff.
#
# Safe by default: every command is idempotent; nothing destructive runs
# without an explicit confirmation prompt.
# ─────────────────────────────────────────────────────────────────────────

set -euo pipefail

OLD_DOCROOT="/var/www/ai-trading-championship"
NEW_DOCROOT="/var/www/ai-trading-championship-corrected"
BACKUP_BASE="/root/backups"
DOMAIN="www.tradingguru.ai"

step="${1:-help}"

confirm() {
  read -r -p "$1 [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]]
}

case "$step" in

  0|snapshot)
    DATE=$(date -u +%Y%m%d-%H%M%S)
    BACKUP="$BACKUP_BASE/site-$DATE"
    echo "→ snapshotting current site + config to $BACKUP"
    mkdir -p "$BACKUP"
    if [ -d "$OLD_DOCROOT" ]; then
      cp -a "$OLD_DOCROOT" "$BACKUP/www"
      echo "  ✓ docroot copied"
    else
      echo "  ! $OLD_DOCROOT does not exist — nothing to back up"
    fi
    nginx -T 2>/dev/null > "$BACKUP/nginx-config.txt" && echo "  ✓ nginx -T captured"
    systemctl list-units --type=service --no-pager > "$BACKUP/services.txt"
    echo "$BACKUP" > "$BACKUP_BASE/.latest"
    echo "✓ snapshot complete at $BACKUP"
    ;;

  4|disable)
    echo "→ disabling live-trading services (if present)"
    SERVICES=(canary.service canary-killswitch.service monster-agent.service canary-battle.service tradingguru-old-frontend.service)
    for svc in "${SERVICES[@]}"; do
      if systemctl list-unit-files "$svc" >/dev/null 2>&1; then
        if [ "$(systemctl is-active "$svc" 2>/dev/null || echo inactive)" != "inactive" ]; then
          echo "  $svc → stopping + disabling"
          systemctl disable --now "$svc"
        else
          echo "  $svc → already inactive"
        fi
      else
        echo "  $svc → not installed"
      fi
    done

    echo ""
    echo "═══ should be ACTIVE (telemetry stack) ═══"
    for svc in tradingguru-telemetry tradingguru-bots-updater microstructure-collector nginx; do
      printf "  %-32s %s\n" "$svc" "$(systemctl is-active "$svc" 2>/dev/null || echo absent)"
    done
    echo ""
    echo "═══ should be INACTIVE (live trading) ═══"
    for svc in canary monster-agent canary-killswitch canary-battle; do
      printf "  %-32s %s\n" "$svc" "$(systemctl is-active "$svc" 2>/dev/null || echo absent)"
    done
    echo ""
    SOCK=$(ss -tnp 2>/dev/null | grep -iE 'gate\.io|bybit\.com' | wc -l)
    if [ "$SOCK" = "0" ]; then
      echo "  ✓ exchange sockets: 0 (clean)"
    else
      echo "  ✗ exchange sockets: $SOCK — INVESTIGATE before continuing"
      exit 1
    fi
    ;;

  6|verify)
    echo "→ verifying corrected design is live at https://$DOMAIN"
    for path in / /arena.html /agents.html /leaderboard.html /governance.html /about.html; do
      code=$(curl -sk -o /dev/null -w '%{http_code}' "https://$DOMAIN$path")
      printf "  %-22s %s\n" "$path" "$code"
    done
    echo ""
    echo "→ checking the home route for fake claims (excluding disclosure blocks)"
    HOME_HTML=$(curl -sk "https://$DOMAIN/")
    if echo "$HOME_HTML" | grep -qiE 'WINNER TAKES ALL|WINS THE POT'; then
      # only flag if it's NOT inside a "no ... " or "removed" sentence
      ROGUE=$(echo "$HOME_HTML" | grep -i -E 'WINNER TAKES ALL|WINS THE POT' | grep -ivE 'no .*winner|removed|notice|disclosure|reject' || true)
      if [ -n "$ROGUE" ]; then
        echo "  ✗ ROGUE fake claim found:"
        echo "$ROGUE" | sed 's/^/      /'
        exit 1
      else
        echo "  ✓ matches found, all inside disclosure blocks"
      fi
    else
      echo "  ✓ no matches at all"
    fi

    if echo "$HOME_HTML" | grep -qiE 'PAPER MODE|NO PRIZE POOL|NO LIVE ORDERS'; then
      echo "  ✓ corrected hero copy present"
    else
      echo "  ✗ corrected hero copy MISSING — wrong build is serving"
      exit 1
    fi
    ;;

  7|retire)
    if ! [ -d "$OLD_DOCROOT" ]; then
      echo "  $OLD_DOCROOT already gone — nothing to retire"
      exit 0
    fi
    if ! [ -d "$NEW_DOCROOT" ]; then
      echo "  ✗ $NEW_DOCROOT not present — refusing to retire the old build"
      exit 1
    fi
    DATE=$(date -u +%Y%m%d)
    TARGET="${OLD_DOCROOT}.retired-${DATE}"
    if confirm "Move $OLD_DOCROOT → $TARGET ?"; then
      mv "$OLD_DOCROOT" "$TARGET"
      echo "✓ retired: $TARGET"
      echo "  delete after at least 7 days if no rollback needed"
    else
      echo "  aborted"
    fi
    ;;

  rollback)
    LATEST_FILE="$BACKUP_BASE/.latest"
    if ! [ -f "$LATEST_FILE" ]; then
      echo "  ✗ no snapshot pointer at $LATEST_FILE — run step 0 first or pass path"
      exit 1
    fi
    BACKUP=$(cat "$LATEST_FILE")
    if ! [ -d "$BACKUP/www" ]; then
      echo "  ✗ $BACKUP/www does not exist"
      exit 1
    fi
    if confirm "Restore $OLD_DOCROOT from $BACKUP/www and reload nginx?"; then
      rm -rf "$OLD_DOCROOT"
      cp -a "$BACKUP/www" "$OLD_DOCROOT"
      systemctl reload nginx
      echo "✓ rolled back from $BACKUP"
    else
      echo "  aborted"
    fi
    ;;

  help|*)
    sed -n '2,30p' "$0"
    exit 0
    ;;
esac
