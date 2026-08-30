#!/bin/bash
set -euo pipefail

echo "=== LiteLLM Health Check ==="

if curl -sf http://localhost:4000/health/readiness >/dev/null 2>&1; then
    echo "OK: LiteLLM is healthy"
    exit 0
else
    echo "FAIL: LiteLLM is unhealthy"
    exit 1
fi
