#!/usr/bin/env bash
# install_hermes_ops.sh — Install hermes-agent on the DO VPS as Trading Guru ops brain.
# Run ON the DO VPS (167.71.24.86) as root.
# LLM provider = Manus Forge (OpenAI-compatible). Telegram = existing bot.
#
# Usage:
#   FORGE_KEY="<paste forge key>" \
#   TG_TOKEN="<telegram bot token>" \
#   TG_USER_ID="<your numeric telegram user id>" \
#   bash install_hermes_ops.sh
set -euo pipefail

FORGE_URL="${FORGE_URL:-https://forge.manus.ai/v1}"
FORGE_KEY="${FORGE_KEY:?Set FORGE_KEY env var}"
TG_TOKEN="${TG_TOKEN:?Set TG_TOKEN env var}"
TG_USER_ID="${TG_USER_ID:?Set TG_USER_ID env var}"
HERMES_MODEL="${HERMES_MODEL:-gemini-2.5-flash}"

echo "================= HERMES OPS INSTALL ================="
echo "Forge URL : $FORGE_URL"
echo "Model     : $HERMES_MODEL"
echo "TG user   : $TG_USER_ID"
echo "====================================================="

# 1) Install (installer brings its own uv + python 3.11, no sudo needed for that part)
if [ ! -d "$HOME/.hermes/hermes-agent" ]; then
  echo "[1/5] Installing hermes-agent ..."
  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash || {
    echo "Installer returned non-zero; continuing to configure if binary exists"; }
else
  echo "[1/5] hermes-agent already present, skipping install."
fi

export PATH="$HOME/.local/bin:$PATH"
HERMES="$(command -v hermes || echo "$HOME/.local/bin/hermes")"
echo "hermes binary: $HERMES"

# 2) Write config (.env + config.yaml) pointing at Manus Forge as custom OpenAI endpoint
echo "[2/5] Writing ~/.hermes config ..."
mkdir -p "$HOME/.hermes"
cat > "$HOME/.hermes/.env" <<EOF
OPENAI_BASE_URL=$FORGE_URL
OPENAI_API_KEY=$FORGE_KEY
TELEGRAM_BOT_TOKEN=$TG_TOKEN
TELEGRAM_ALLOWED_USERS=$TG_USER_ID
EOF
chmod 600 "$HOME/.hermes/.env"

# Set model + custom provider via CLI (best-effort; .env is the source of truth)
"$HERMES" config set model "$HERMES_MODEL" 2>/dev/null || true
"$HERMES" config set OPENAI_BASE_URL "$FORGE_URL" 2>/dev/null || true
"$HERMES" config set OPENAI_API_KEY "$FORGE_KEY" 2>/dev/null || true

# 3) Drop the Trading Guru battle-status skill
echo "[3/5] Installing trading-guru-status skill ..."
SKILL_DIR="$HOME/.hermes/skills/trading-guru-status"
mkdir -p "$SKILL_DIR"
cat > "$SKILL_DIR/SKILL.md" <<'SKILL'
# trading-guru-status

Use this skill whenever the user asks about the live Trading Guru champion battle,
the trading agents (TITAN, VELOCITY, SENTINEL), balances, PnL, who is winning,
crowns, coach assignments, or "how are the agents doing".

## How to get live data
Run this command and read its JSON/text output, then summarize for the user:

```bash
python3 /root/canary/tg_status.py
```

It prints: each agent's pair, session PnL, balance, round wins (crowns),
the current coach lineup, total team PnL, and the champion-battle service state.

If the command fails, check the service:
```bash
systemctl is-active champion-battle coach
tail -n 30 /root/canary/runtime/champion_battle.log
```

Always answer concisely: standings (🥇🥈🥉), total PnL, winner, and any concern
(e.g. a service is not active, or PnL is negative).
SKILL

# 4) Helper that hermes' skill calls — reads live champion state safely
echo "[4/5] Writing /root/canary/tg_status.py ..."
cat > /root/canary/tg_status.py <<'PY'
#!/usr/bin/env python3
"""Trading Guru live status — used by the hermes 'trading-guru-status' skill."""
import json, os, subprocess, pathlib
ROOT = pathlib.Path("/root/canary")
RUNTIME = ROOT / "runtime"

def svc(name):
    try:
        return subprocess.run(["systemctl","is-active",name],
                              capture_output=True,text=True,timeout=8).stdout.strip()
    except Exception as e:
        return f"err:{e}"

def load_state():
    for fn in ("champion_state.json","champion_battle_state.json"):
        p = RUNTIME / fn
        if p.exists():
            try: return json.loads(p.read_text())
            except Exception: pass
    return {}

def load_coach():
    for p in (ROOT/"coach_signals.json", RUNTIME/"coach_signals.json"):
        if p.exists():
            try: return json.loads(p.read_text())
            except Exception: pass
    return {}

state = load_state()
coach = load_coach()
out = {
    "services": {
        "champion-battle": svc("champion-battle"),
        "coach": svc("coach"),
    },
    "state": state,
    "coach_signals": coach,
}
print(json.dumps(out, indent=2, default=str)[:6000])
PY
chmod +x /root/canary/tg_status.py

# 5) Install gateway as systemd service
echo "[5/5] Installing hermes gateway service ..."
"$HERMES" gateway install 2>/dev/null || echo "gateway install returned non-zero (may need manual 'hermes gateway install')"
systemctl daemon-reload 2>/dev/null || true
"$HERMES" gateway start 2>/dev/null || systemctl start hermes-gateway 2>/dev/null || true
sleep 3
echo "--- gateway status ---"
"$HERMES" gateway status 2>/dev/null || systemctl is-active hermes-gateway || true

echo
echo "✅ DONE. Open Telegram, message your bot, and try: 'how are the agents doing?'"
echo "   Test status helper directly: python3 /root/canary/tg_status.py"
