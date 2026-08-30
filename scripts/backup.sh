#!/bin/bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ERRORS=0

mkdir -p "$BACKUP_DIR"

echo "Creating backup at $TIMESTAMP"

if docker ps --format '{{.Names}}' | grep -q 'litellm-postgres'; then
    if docker exec litellm-postgres pg_dump -U "${POSTGRES_USER:-litellm}" "${POSTGRES_DB:-litellm}" > "$BACKUP_DIR/postgres_$TIMESTAMP.sql" 2>/dev/null; then
        echo "OK: PostgreSQL backup created"
    else
        echo "ERROR: PostgreSQL backup failed"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "SKIP: PostgreSQL not running"
fi

if docker ps --format '{{.Names}}' | grep -q 'litellm-redis'; then
    if docker exec litellm-redis redis-cli -a "${REDIS_PASSWORD}" SAVE >/dev/null 2>&1; then
        docker cp litellm-redis:/data/dump.rdb "$BACKUP_DIR/redis_$TIMESTAMP.rdb" 2>/dev/null && \
            echo "OK: Redis backup created" || {
            echo "ERROR: Redis backup failed"
            ERRORS=$((ERRORS + 1))
        }
    else
        echo "ERROR: Redis SAVE failed"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "SKIP: Redis not running"
fi

CONFIG_BACKUP="$BACKUP_DIR/config_$TIMESTAMP.tar.gz"
if tar -czf "$CONFIG_BACKUP" \
    -C "$(dirname "$0")/.." \
    config/litellm/config.yml \
    .env 2>/dev/null; then
    echo "OK: Config backup created"
else
    echo "WARN: Config backup had issues (some files may not exist)"
fi

if [ $ERRORS -gt 0 ]; then
    echo "ERROR: Backup completed with $ERRORS error(s)"
    exit 1
else
    echo "OK: Backup complete: $BACKUP_DIR"
fi
