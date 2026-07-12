#!/bin/bash
# Production Trading Engine Deployment Script

set -e

echo "🚀 Deploying Trading Engine..."

# Create directories
sudo mkdir -p /opt/trading-engine
sudo chown -R trading:trading /opt/trading-engine

# Copy files
cp -r . /opt/trading-engine/

# Install dependencies
cd /opt/trading-engine
pip3 install --user -r requirements.txt

# Setup environment
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️ Please edit .env with your API keys!"
fi

# Create log directories
mkdir -p logs data/config_versions

# Setup systemd service
sudo cp config/trading-engine.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable trading-engine

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Edit /opt/trading-engine/.env with your API keys"
echo "2. sudo systemctl start trading-engine"
echo "3. sudo systemctl status trading-engine"
