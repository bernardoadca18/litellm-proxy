#!/bin/sh
# Entry point that neutralizes legacy environment variables
# These variables from old .env files should not affect the runtime

unset DATABASE_URL
unset DIRECT_URL
unset LITELLM_LOG
unset LITELLM_METRICS_PORT
unset PROMETHEUS_ENDPOINT
unset ENABLE_PROMETHEUS
unset ENABLE_OTEL
unset POSTGRES_USER
unset POSTGRES_PASSWORD
unset POSTGRES_DB
unset POSTGRES_PORT
unset REDIS_PASSWORD
unset GRAFANA_ADMIN_USER
unset GRAFANA_ADMIN_PASSWORD
unset MONITOR_INTERVAL
unset PGADMIN_DEFAULT_EMAIL
unset PGADMIN_DEFAULT_PASSWORD

# Set correct log level
export LITELLM_LOG_LEVEL=WARNING

# Execute litellm directly
exec litellm --config /app/config.yml --port 4000 --num_workers 1 --telemetry false
