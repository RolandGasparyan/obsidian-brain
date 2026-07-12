# UNCRISHABLE Trading Engine

24/7 Production-Grade AI Trading System with 8 AI GODS competing for maximum profit.

## Features

- **8 AI GODS** competing in real-time
- **Auto-Withdraw** profits to cold wallet
- **4-Hour Capital Rebalancing** (winners get more)
- **99.9% Uptime** with auto-restart
- **Config Persistence** - never lose settings
- **Health Monitoring** with Telegram alerts

## Quick Start

### 1. Server Setup (DigitalOcean $12/month)

```bash
ssh root@YOUR_SERVER_IP
apt update && apt upgrade -y
apt install -y python3.11 python3-pip git
useradd -m -s /bin/bash trading
```

### 2. Upload & Deploy

```bash
# On your local machine
scp trading-engine-production.tar.gz trading@SERVER_IP:~

# On server
ssh trading@SERVER_IP
sudo mkdir -p /opt/trading-engine
sudo chown trading:trading /opt/trading-engine
cd /opt/trading-engine
tar -xzf ~/trading-engine-production.tar.gz
./scripts/deploy.sh
```

### 3. Configure

```bash
nano /opt/trading-engine/.env
# Add your Gate.io API keys
# Add Telegram bot token (optional)
```

### 4. Start

```bash
sudo systemctl start trading-engine
sudo systemctl status trading-engine
```

## Commands

```bash
# Start/Stop/Restart
sudo systemctl start trading-engine
sudo systemctl stop trading-engine
sudo systemctl restart trading-engine

# View Logs
tail -f /opt/trading-engine/logs/engine.log

# Check Status
sudo systemctl status trading-engine
```

## Configuration

Edit `/opt/trading-engine/data/config.json`:

```json
{
  "starting_balance": 692.0,
  "trading_mode": "FUTURES",
  "direction": "SHORTS_ONLY",
  "max_leverage": 10,
  "withdraw_threshold": 100
}
```

## 8 AI GODS

1. **DeepSeek R1** - Quant God (15x, Scalping)
2. **GPT-5** - Macro God (12x, Momentum)
3. **Claude Opus** - Contrarian God (10x, Mean Reversion)
4. **Llama 3.3** - Speed God (10x, HFT Scalping)
5. **Gemini Flash** - Multi-Modal God (11x, Momentum)
6. **Mistral Large** - Risk God (10x, Mean Reversion)
7. **Qwen 72B** - Pattern God (12x, Breakout)
8. **Grok xAI** - News God (13x, News Trading)

## Auto-Withdraw

Profits automatically sent to cold wallet after reaching threshold:
- Default threshold: $100
- Chain: TRC20 (low fees)
- Wallet: Configure in .env

## Monitoring

- Health checks every 60 seconds
- Auto-restart on failure
- Telegram alerts for:
  - Trade executions
  - Profit milestones
  - Withdrawals
  - Errors

## Cost

- VPS: $12/month (DigitalOcean 4GB)
- 99.9% uptime guaranteed
- No Replit crashes
- Config never lost
