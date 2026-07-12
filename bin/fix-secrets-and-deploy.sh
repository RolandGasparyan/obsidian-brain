#!/usr/bin/env bash
# fix-secrets-and-deploy.sh
# One-shot script to fix the MAIN/SUB2 Gate.io secrets in GitHub repo secrets,
# fire the deploy, and watch the result land on issue #14.
#
# Usage (on your Mac, in a checkout of this repo):
#   bash bin/fix-secrets-and-deploy.sh
#
# Or run directly without cloning:
#   curl -fsSL https://raw.githubusercontent.com/RolandGasparyan/tradingguru-empire/main/bin/fix-secrets-and-deploy.sh | bash
#
# Requirements:
#   - gh CLI installed and authenticated (`gh auth status` works)
#   - Repo write access for RolandGasparyan/tradingguru-empire
#
# The script does NOT echo your secrets to the terminal. They're read via
# `read -rs` (silent prompt) and piped directly to `gh secret set`.

set -euo pipefail

REPO="RolandGasparyan/tradingguru-empire"
ISSUE=14

# Colors
red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
bold() { printf '\033[1m%s\033[0m\n' "$*"; }

bold "═══════════════════════════════════════════════════════════════════"
bold "  Fix MAIN/SUB2 Gate.io secrets + fire deploy"
bold "  Repo: $REPO"
bold "  Issue: #$ISSUE (live battle tracker)"
bold "═══════════════════════════════════════════════════════════════════"
echo

# 0. Sanity checks
if ! command -v gh >/dev/null 2>&1; then
  red "ERROR: gh CLI not installed. Install from https://cli.github.com/"
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  red "ERROR: gh CLI not authenticated. Run 'gh auth login' first."
  exit 1
fi

# Confirm we can talk to the repo
if ! gh repo view "$REPO" >/dev/null 2>&1; then
  red "ERROR: cannot access $REPO. Check your gh login and repo permissions."
  exit 1
fi
green "✓ gh CLI authenticated, repo accessible"
echo

# 1. Prompt for MAIN secret
yellow "STEP 1/4 — paste the correct MAIN Gate.io API secret"
yellow "         (the 64-char value from Gate.io > MAIN account > API Management)"
yellow "         (input is hidden — type/paste, then press Enter)"
printf "  GATE_MAIN_API_SECRET: "
read -rs MAIN_SECRET
echo
MAIN_SECRET="${MAIN_SECRET//[$'\t\r\n ']/}"  # strip whitespace
if [ ${#MAIN_SECRET} -lt 32 ]; then
  red "ERROR: secret looks too short (${#MAIN_SECRET} chars). Aborting."
  exit 1
fi
green "  ✓ MAIN secret captured (${#MAIN_SECRET} chars)"
echo

# 2. Prompt for SUB2 secret
yellow "STEP 2/4 — paste the correct SUB2 Gate.io API secret"
yellow "         (the 64-char value from Gate.io > SUB2 account > API Management)"
printf "  GATE_SUB2_API_SECRET: "
read -rs SUB2_SECRET
echo
SUB2_SECRET="${SUB2_SECRET//[$'\t\r\n ']/}"
if [ ${#SUB2_SECRET} -lt 32 ]; then
  red "ERROR: secret looks too short (${#SUB2_SECRET} chars). Aborting."
  exit 1
fi
green "  ✓ SUB2 secret captured (${#SUB2_SECRET} chars)"
echo

# Refuse to proceed if the two are identical (almost certainly a paste error)
if [ "$MAIN_SECRET" = "$SUB2_SECRET" ]; then
  red "ERROR: MAIN_SECRET and SUB2_SECRET are identical — that can't be right."
  red "       Different accounts have different secrets. Aborting."
  exit 1
fi

# 3. Set both secrets in GitHub Actions
yellow "STEP 3/4 — setting secrets in GitHub Actions"
printf '%s' "$MAIN_SECRET" | gh secret set GATE_MAIN_API_SECRET -R "$REPO" --body -
green "  ✓ GATE_MAIN_API_SECRET set"
printf '%s' "$SUB2_SECRET" | gh secret set GATE_SUB2_API_SECRET -R "$REPO" --body -
green "  ✓ GATE_SUB2_API_SECRET set"
# Clear from env (defense in depth)
unset MAIN_SECRET SUB2_SECRET
echo

# 4. Fire the deploy workflow + watch
yellow "STEP 4/4 — firing deploy-live-battle.yml + watching"
gh workflow run deploy-live-battle.yml -R "$REPO" -f confirm=START
echo "  (workflow dispatched)"
echo "  Sleeping 15s for the run to register…"
sleep 15

# Find the most recent run
RUN_ID=$(gh run list -R "$REPO" --workflow deploy-live-battle.yml --limit 1 \
         --json databaseId -q '.[0].databaseId')
if [ -z "$RUN_ID" ]; then
  red "Could not find a deploy run. Check https://github.com/$REPO/actions"
  exit 1
fi
green "  ✓ tracking run #$RUN_ID"

echo "  Streaming workflow status (Ctrl-C to detach; the deploy keeps running):"
gh run watch "$RUN_ID" -R "$REPO" --exit-status || true
echo

# 5. Pull the POST-DEPLOY AUTH CHECK section
bold "═══════════════════════════════════════════════════════════════════"
bold "  POST-DEPLOY AUTH CHECK results"
bold "═══════════════════════════════════════════════════════════════════"
gh run view "$RUN_ID" -R "$REPO" --log 2>/dev/null \
  | grep -E "POST-DEPLOY|key_len|PASS|FAIL|RESULT|state_|Started thread|balance OK|FAIL-CLOSED" \
  | head -40 || true
echo

bold "Done."
echo
echo "  Live battle status comments land on:"
echo "  https://github.com/$REPO/issues/$ISSUE"
echo
echo "  If all 3 accounts show PASS, the 24/7 3-account live battle is fully"
echo "  active. If MAIN or SUB2 still FAIL with INVALID_SIGNATURE, the secret"
echo "  values stored are still wrong — re-check the source values in Gate.io."
