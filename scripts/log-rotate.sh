#!/bin/bash

LOG_DIR="./logs"
MAX_SIZE=100M
MAX_FILES=10

mkdir -p "$LOG_DIR"

for log in "$LOG_DIR"/*.log; do
    if [ -f "$log" ]; then
        size=$(stat -f%z "$log" 2>/dev/null || stat -c%s "$log" 2>/dev/null)
        if [ "$size" -gt "$(numfmt --from=iec $MAX_SIZE)" ]; then
            timestamp=$(date +%Y%m%d_%H%M%S)
            mv "$log" "$LOG_DIR/$(basename "$log" .log)_$timestamp.log"
            gzip "$LOG_DIR/$(basename "$log" .log)_$timestamp.log"
        fi
    fi
done

# Remove logs antigos
find "$LOG_DIR" -name "*.gz" -mtime +30 -delete