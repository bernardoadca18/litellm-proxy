#!/bin/bash
# ============================================================
# rotate-keys.sh - Gerenciamento de chaves API do Gemini
# ============================================================

set -euo pipefail

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuracoes
LITELLM_URL="${LITELLM_URL:-http://localhost:4000}"
CONFIG_FILE="${CONFIG_FILE:-./config/litellm/config.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
LOG_FILE="${LOG_FILE:-./logs/rotate-keys.log}"
HEALTH_CHECK_MODEL="${HEALTH_CHECK_MODEL:-gemini-3.5-flash}"
HEALTH_CHECK_PROMPT="${HEALTH_CHECK_PROMPT:-Say 'OK' in one word}"

mkdir -p "$BACKUP_DIR" "$(dirname "$LOG_FILE")"

log() {
    local level=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

test_key() {
    local key_name=$1
    local api_key=$2
    
    log "INFO" "Testing key: $key_name"
    
    response=$(curl -s -w "\n%{http_code}" \
        -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$api_key" \
        -H "Content-Type: application/json" \
        -d "{
            \"contents\": [{
                \"parts\": [{\"text\": \"$HEALTH_CHECK_PROMPT\"}]
            }],
            \"generationConfig\": {
                \"maxOutputTokens\": 5,
                \"temperature\": 0
            }
        }" 2>/dev/null || true)
    
    local http_code=$(echo "$response" | tail -n1)
    
    case $http_code in
        200)
            log "INFO" "Key $key_name is HEALTHY"
            return 0
            ;;
        429)
            log "WARN" "Key $key_name: RATE LIMITED (429)"
            return 1
            ;;
        403|400|401)
            log "ERROR" "Key $key_name: INVALID (HTTP $http_code)"
            return 2
            ;;
        *)
            log "ERROR" "Key $key_name: UNKNOWN ERROR (HTTP $http_code)"
            return 1
            ;;
    esac
}

generate_new_key() {
    local project_id=$1
    local key_name="litellm-key-$(date +%Y%m%d-%H%M%S)"
    
    if ! command -v gcloud &> /dev/null; then
        log "ERROR" "gcloud CLI not found. Cannot generate new keys."
        return 1
    fi
    
    log "INFO" "Generating new API key: $key_name"
    
    new_key=$(gcloud alpha services api-keys create \
        --project="$project_id" \
        --display-name="$key_name" \
        --format="value(keyString)" 2>/dev/null)
    
    if [ -n "$new_key" ]; then
        log "INFO" "New key generated successfully"
        echo "$new_key"
        return 0
    else
        log "ERROR" "Failed to generate new key"
        return 1
    fi
}

delete_old_key() {
    local key_string=$1
    local project_id=$2
    
    key_id=$(gcloud alpha services api-keys list \
        --project="$project_id" \
        --filter="keyString:$key_string" \
        --format="value(uid)" 2>/dev/null)
    
    if [ -n "$key_id" ]; then
        log "INFO" "Deleting old key: $key_id"
        gcloud alpha services api-keys delete "$key_id" --project="$project_id" -q 2>/dev/null || true
    fi
}

rotate_keys() {
    log "INFO" "========== Starting API Key Rotation =========="
    
    backup_file="$BACKUP_DIR/config_$(date +%Y%m%d_%H%M%S).yml"
    cp "$CONFIG_FILE" "$backup_file"
    log "INFO" "Backup saved to $backup_file"
    
    source .env 2>/dev/null || {
        log "ERROR" "Could not load .env file"
        exit 1
    }
    
    declare -A key_status
    
    for i in {1..5}; do
        key_var="GEMINI_API_KEY_$i"
        key_value="${!key_var}"
        
        if [ -z "$key_value" ]; then
            log "WARN" "Key $key_var is empty, skipping"
            continue
        fi
        
        test_key "$key_var" "$key_value"
        status=$?
        key_status["$key_var"]=$status
        
        if [ $status -eq 2 ]; then
            log "ERROR" "Key $key_var is PERMANENTLY invalid"
            
            if [ -n "${GOOGLE_CLOUD_PROJECT:-}" ]; then
                log "INFO" "Attempting to generate new key for $key_var"
                new_key=$(generate_new_key "$GOOGLE_CLOUD_PROJECT")
                if [ -n "$new_key" ]; then
                    sed -i "s/^$key_var=.*/$key_var=\"$new_key\"/" .env
                    log "INFO" "Updated $key_var in .env"
                    delete_old_key "$key_value" "$GOOGLE_CLOUD_PROJECT"
                fi
            fi
        fi
    done
    
    log "INFO" "Reloading LiteLLM configuration"
    
    if curl -s -X POST "$LITELLM_URL/reload" > /dev/null 2>&1; then
        log "INFO" "LiteLLM reloaded via API"
    else
        log "WARN" "API reload failed, restarting container"
        docker-compose restart litellm 2>/dev/null || true
    fi
    
    log "INFO" "========== Rotation Summary =========="
    for key in "${!key_status[@]}"; do
        case ${key_status[$key]} in
            0) echo "OK: $key - Healthy" ;;
            1) echo "WARN: $key - Rate limited" ;;
            2) echo "FAIL: $key - Invalid" ;;
        esac
    done
    
    log "INFO" "Rotation complete"
}

monitor() {
    local interval="${MONITOR_INTERVAL:-300}"
    
    log "INFO" "Starting monitoring mode (interval: ${interval}s)"
    
    while true; do
        rotate_keys
        sleep "$interval"
    done
}

stats() {
    log "INFO" "Collecting usage statistics"
    
    if curl -s "http://localhost:9090/api/v1/query" -G \
        --data-urlencode 'query=sum(rate(litellm_requests_total[24h])) by (api_key)' > /tmp/stats.json 2>/dev/null; then
        log "INFO" "Usage statistics saved to /tmp/stats.json"
        cat /tmp/stats.json | jq '.' 2>/dev/null || cat /tmp/stats.json
    else
        log "WARN" "Prometheus not available"
    fi
}

case "${1:-rotate}" in
    rotate)
        rotate_keys
        ;;
    monitor)
        monitor
        ;;
    stats)
        stats
        ;;
    *)
        echo "Usage: $0 {rotate|monitor|stats}"
        echo ""
        echo "Commands:"
        echo "  rotate   - Single rotation pass (default)"
        echo "  monitor  - Run continuously as daemon"
        echo "  stats    - Show usage statistics"
        exit 1
        ;;
esac