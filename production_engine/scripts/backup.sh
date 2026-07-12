#!/bin/bash
# Backup script for trading engine

BACKUP_DIR="/opt/trading-engine/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

mkdir -p $BACKUP_DIR

# Create backup
tar -czf $BACKUP_FILE \
    /opt/trading-engine/data/config.json \
    /opt/trading-engine/data/config_versions \
    /opt/trading-engine/.env \
    2>/dev/null

# Keep only last 30 backups
cd $BACKUP_DIR
ls -t | tail -n +31 | xargs -r rm --

echo "✅ Backup created: $BACKUP_FILE"
