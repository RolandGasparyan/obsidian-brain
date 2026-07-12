#!/bin/bash
# Restore script for trading engine

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <backup_file>"
    echo "Example: ./restore.sh /opt/trading-engine/data/backups/backup_20260130.tar.gz"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️ This will restore from: $BACKUP_FILE"
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Stop service
sudo systemctl stop trading-engine

# Restore
tar -xzf $BACKUP_FILE -C /

# Restart service
sudo systemctl start trading-engine

echo "✅ Restore complete!"
