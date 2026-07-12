# L99 Bot — VPS Deploy Guide

## Requirements

- Ubuntu 22.04 LTS
- PostgreSQL 14+
- Python 3.10+
- Supervisor

---

## Step 1 — System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git \
                    postgresql postgresql-contrib supervisor
```

## Step 2 — PostgreSQL

```bash
sudo -u postgres psql -c "CREATE DATABASE l99;"
sudo -u postgres psql -c "CREATE USER l99_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE l99 TO l99_user;"
sudo systemctl restart postgresql
```

If auth fails, set `md5` in `/etc/postgresql/*/main/pg_hba.conf` for local connections.

## Step 3 — Clone

```bash
cd ~
git clone https://github.com/RolandGasparyan/ai-trading-championship.git
cd ai-trading-championship/l99_bot
```

## Step 4 — Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 5 — Configure .env

```bash
cp .env.example .env
nano .env
chmod 600 .env
```

Required values:

```
TESTNET=true
LIVE_TRADING=false
RISK_PER_TRADE=0.01
MAX_CONCURRENT=3
KILL_DD_THRESHOLD=0.21

BINANCE_API_KEY=<testnet key>
BINANCE_API_SECRET=<testnet secret>

DB_NAME=l99
DB_USER=l99_user
DB_PASS=your_password
DB_HOST=localhost
DB_PORT=5432

TG_TOKEN=<bot token>
TG_CHAT_ID=<chat id>
```

> NOTE: env var is `DB_PASS` (not `DB_PASSWORD`)

## Step 6 — Initialize DB

```bash
mkdir -p ~/logs
python db.py
```

Verify:

```bash
psql -U l99_user -d l99 -c "\d trades"
```

## Step 7 — Preflight (MANDATORY)

```bash
python preflight.py
```

Must return `22/22 checks passed`. If not — stop and diagnose.

## Step 8 — Supervisor

```bash
sudo cp ~/ai-trading-championship/supervisor.conf /etc/supervisor/conf.d/l99bot.conf
# Edit YOUR_USER in the conf file
sudo nano /etc/supervisor/conf.d/l99bot.conf

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start l99bot
sudo supervisorctl status l99bot
```

## Step 9 — Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw enable
```

## Step 10 — Verify

```bash
tail -n 20 /var/log/l99bot.out.log
psql -U l99_user -d l99 -c "SELECT COUNT(*) FROM trades;"
```

Confirm Telegram startup message received.

---

## Safe Restart

```bash
cd ~/ai-trading-championship/l99_bot
source venv/bin/activate
python preflight.py                    # must pass 22/22
sudo supervisorctl restart l99bot
```

---

## LIVE Mode (only after pilot approval)

Do NOT flip `LIVE_TRADING=true` until:

- 50+ clean testnet trades
- No execution anomaly
- No DB mismatch
- No API instability

`preflight.py` is testnet-gated — do not run it in live mode. Use manual config check:

```bash
python -c "import config; print(config.TESTNET, config.LIVE_TRADING)"
```
