#!/bin/bash

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "Creating backup at $TIMESTAMP"

docker exec litellm-postgres pg_dump -U litellm litellm > "$BACKUP_DIR/postgres_$TIMESTAMP.sql"
docker exec litellm-redis redis-cli --pass "$REDIS_PASSWORD" SAVE

tar -czf "$BACKUP_DIR/full_backup_$TIMESTAMP.tar.gz" \
    -C ./config \
    .env \
    config.yml 2>/dev/null || true

echo "Backup complete: $BACKUP_DIR/full_backup_$TIMESTAMP.tar.gz"