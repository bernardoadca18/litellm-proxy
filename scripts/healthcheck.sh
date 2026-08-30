#!/bin/bash
set -euo pipefail

ERRORS=0

check_litellm() {
    if curl -sf http://localhost:4000/health/readiness >/dev/null 2>&1; then
        echo "OK: LiteLLM is healthy"
    else
        echo "FAIL: LiteLLM is unhealthy"
        ERRORS=$((ERRORS + 1))
    fi
}

check_redis() {
    if docker ps --format '{{.Names}}' | grep -q 'litellm-redis'; then
        if docker exec litellm-redis redis-cli -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; then
            echo "OK: Redis is healthy"
        else
            echo "FAIL: Redis is unhealthy"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "SKIP: Redis not running (optional)"
    fi
}

check_postgres() {
    if docker ps --format '{{.Names}}' | grep -q 'litellm-postgres'; then
        if docker exec litellm-postgres pg_isready -U "${POSTGRES_USER:-litellm}" -d "${POSTGRES_DB:-litellm}" >/dev/null 2>&1; then
            echo "OK: PostgreSQL is healthy"
        else
            echo "FAIL: PostgreSQL is unhealthy"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "SKIP: PostgreSQL not running (optional)"
    fi
}

check_prometheus() {
    if docker ps --format '{{.Names}}' | grep -q 'litellm-prometheus'; then
        if curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1; then
            echo "OK: Prometheus is healthy"
        else
            echo "FAIL: Prometheus is unhealthy"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "SKIP: Prometheus not running (optional)"
    fi
}

check_grafana() {
    if docker ps --format '{{.Names}}' | grep -q 'litellm-grafana'; then
        if curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then
            echo "OK: Grafana is healthy"
        else
            echo "FAIL: Grafana is unhealthy"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "SKIP: Grafana not running (optional)"
    fi
}

echo "=== Core Services ==="
check_litellm

echo ""
echo "=== Optional Services ==="
check_redis
check_postgres

echo ""
echo "=== Monitoring Services ==="
check_prometheus
check_grafana

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "FAILED: $ERRORS service(s) unhealthy"
    exit 1
else
    echo ""
    echo "All checked services are healthy"
fi
