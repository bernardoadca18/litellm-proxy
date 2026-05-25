#!/bin/bash

check_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    if curl -s -f "$url" | grep -q "$expected"; then
        echo "OK: $name is healthy"
        return 0
    else
        echo "FAIL: $name is unhealthy"
        return 1
    fi
}

check_service "LiteLLM" "http://localhost:4000/health" "ok"
check_service "Prometheus" "http://localhost:9090/-/healthy" "Prometheus"
check_service "Grafana" "http://localhost:3000/api/health" "ok"

docker exec litellm-postgres pg_isready -U litellm && echo "OK: PostgreSQL is healthy"
docker exec litellm-redis redis-cli -a "$REDIS_PASSWORD" ping | grep -q PONG && echo "OK: Redis is healthy"