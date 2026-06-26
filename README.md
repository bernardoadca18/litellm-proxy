<div align="center">

# LiteLLM Proxy Gateway

**A production-grade, self-hosted AI API gateway with multi-provider load balancing, intelligent fallback routing, local model support via Ollama, and a full observability stack.**

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-Proxy-8A2BE2)](https://github.com/BerriAI/litellm)
[![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?logo=grafana&logoColor=white)](https://grafana.com/)
[![Nginx](https://img.shields.io/badge/Nginx-Reverse%20Proxy-009639?logo=nginx&logoColor=white)](https://nginx.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Models-black?logo=ollama)](https://ollama.com/)

[Ler em Português](README.pt-br.md)

</div>

---

## Overview

This repository contains a **battle-tested, production-ready LiteLLM proxy deployment** designed to consolidate multiple AI provider API keys under a single, unified OpenAI-compatible endpoint. It eliminates rate-limit bottlenecks through intelligent key pooling and load balancing across **10 Gemini accounts**, **3 Groq accounts**, and **10 OpenRouter accounts** — all exposed as a single API surface compatible with any OpenAI SDK.

Beyond cloud providers, it seamlessly integrates **locally-running Ollama models**, making it a complete AI gateway for both online and offline inference use cases.

### Why this exists

Managing dozens of API keys across multiple providers is painful. Rate limits get hit unpredictably. Failovers require manual intervention. Costs are invisible until the bill arrives. This proxy solves all of that:

- **One endpoint, any model** — point your apps at `http://localhost:4000/v1` and use any configured model with the standard OpenAI SDK
- **Transparent key rotation** — LiteLLM automatically distributes requests across all configured keys for the same model, maximizing throughput
- **Zero-downtime fallbacks** — if Gemini 3.5 Flash hits a rate limit, traffic automatically cascades to Gemini 2.5 Flash, then Groq, then OpenRouter
- **Full observability** — every request is logged, every metric is scraped by Prometheus, every dashboard is in Grafana

---

## Architecture

```
                          ┌─────────────────────────────────────────────────────┐
                          │                  Your Applications                  │
                          │   (OpenAI SDK, curl, any HTTP client)               │
                          └──────────────────────┬──────────────────────────────┘
                                                 │
                                          Port 80 / 443
                                                 │
                          ┌──────────────────────▼──────────────────────────────┐
                          │                   Nginx                             │
                          │    Rate limiting · SSL termination · Reverse proxy  │
                          └──────────────────────┬──────────────────────────────┘
                                                 │
                                          Port 4000
                                                 │
                          ┌──────────────────────▼──────────────────────────────┐
                          │               LiteLLM Proxy                         │
                          │                                                     │
                          │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
                          │  │  Router  │  │ Fallback │  │   Key Pooling    │   │
                          │  │ (least-  │  │  Engine  │  │  (Round Robin)   │   │
                          │  │  busy)   │  │          │  │                  │   │
                          │  └──────────┘  └──────────┘  └──────────────────┘   │
                          └──┬──────────────┬──────────────┬────────────────────┘
                             │              │              │
               ┌─────────────▼──┐   ┌──────▼──────┐  ┌───▼──────────┐
               │ Google Gemini  │   │    Groq     │  │  OpenRouter  │
               │ (10 API keys)  │   │ (3 API keys)│  │ (10 API keys)│
               └────────────────┘   └─────────────┘  └──────────────┘
                                                              │
                                                    ┌─────────▼────────┐
                                                    │  Ollama (Local)  │
                                                    │  192.168.100.11  │
                                                    └──────────────────┘
                                                    
       ┌──────────────────────────────────────────────────────────────────┐
       │                    Supporting Infrastructure                     │
       │                                                                  │
       │  ┌───────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────┐    │
       │  │PostgreSQL │  │    Redis     │  │Prometheus│  │  Grafana  │    │
       │  │(pgvector) │  │(Cache+Queue) │  │(Metrics) │  │(Dashboards│    │
       │  └───────────┘  └──────────────┘  └──────────┘  └───────────┘    │
       └──────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Capabilities
- **OpenAI-compatible API** — drop-in replacement for any `openai.ChatCompletion.create()` call; no code changes needed in your applications
- **Multi-key load balancing** — distributes requests across all API keys for the same model using a least-busy strategy, multiplying effective rate limits
- **Hierarchical fallback routing** — automatically retries failed requests down a configured provider chain without any client-side code
- **Local model inference** — routes to Ollama for privacy-sensitive workloads, zero-cost inference, or offline scenarios
- **Request caching** — Redis-backed semantic caching with configurable TTL reduces redundant API calls and costs

### Observability Stack
- **Prometheus metrics** — scrapes LiteLLM, Redis, PostgreSQL, cAdvisor, Node Exporter, and Blackbox probes on a unified time-series database
- **Grafana dashboards** — pre-provisioned dashboards for request rates, latency distributions, error rates, and resource utilization
- **Structured alerting** — alerting rules for proxy downtime, high error rates, rate limit exhaustion, Redis and PostgreSQL failures, and memory pressure

### Operational Tooling
- **Automated key rotation** — `rotate-keys.sh` validates all Gemini keys against the live API, flags invalid/rate-limited keys, and optionally provisions new ones via `gcloud`
- **Backup scripts** — one-command PostgreSQL dumps and Redis snapshots with timestamped archives
- **Log rotation** — automatic size-based rotation and 30-day retention for all container logs
- **Watchtower integration** — optional automatic container image updates for the LiteLLM proxy on a 24-hour poll cycle
- **Makefile interface** — all common operations exposed as `make` targets for a clean developer experience

---

## Configured Models

### Google Gemini (via Google AI Studio)
10 API keys are pooled per model, giving you up to **10× the free-tier rate limits** per model group.

| Model Name | API Model | RPM / key | TPM / key | Mode |
|---|---|---|---|---|
| `gemini-3.5-flash` | `gemini/gemini-3.5-flash` | 15 | 3,000,000 | Chat |
| `gemini-3.1-pro` | `gemini/gemini-3.1-pro` | 5 | 5,000,000 | Chat |
| `gemini-3.1-flash-lite` | `gemini/gemini-3.1-flash-lite` | 15 | 10,000,000 | Chat |
| `gemini-2.5-pro` | `gemini/gemini-2.5-pro` | 5 | 5,000,000 | Chat |
| `gemini-2.5-flash` | `gemini/gemini-2.5-flash` | 10 | 3,000,000 | Chat |
| `gemini-2.5-flash-lite` | `gemini/gemini-2.5-flash-lite` | 15 | 10,000,000 | Chat |
| `gemini-2.0-flash` | `gemini/gemini-2.0-flash` | 15 | 10,000,000 | Chat |
| `gemini-2.0-flash-lite` | `gemini/gemini-2.0-flash-lite` | 15 | 10,000,000 | Chat |

### Groq (High-Speed Inference)
3 API keys pooled per model, leveraging Groq's LPU hardware for ultra-low latency.

| Model Name | API Model | Mode |
|---|---|---|
| `groq-llama4-scout` | `meta-llama/llama-4-scout-17b-16e-instruct` | Chat |
| `groq-llama3.3-70b` | `llama-3.3-70b-versatile` | Chat |
| `groq-llama3.1-8b` | `llama-3.1-8b-instant` | Chat |
| `groq-qwen3-32b` | `qwen/qwen3-32b` | Chat |
| `groq-qwen3.6-27b` | `qwen/qwen3.6-27b` | Chat |
| `groq-gpt-oss-120b` | `openai/gpt-oss-120b` | Chat |
| `groq-gpt-oss-20b` | `openai/gpt-oss-20b` | Chat |

### OpenRouter (Free Tier Models)
10 API keys pooled per model, accessing state-of-the-art open models at zero cost.

| Model Name | Provider | Mode |
|---|---|---|
| `openrouter-nemotron-ultra` | NVIDIA Nemotron 3 Ultra | Chat |
| `openrouter-nemotron-super` | NVIDIA Nemotron 3 Super | Chat |
| `openrouter-gpt-oss-120b` | OpenAI GPT-OSS 120B | Chat |
| `openrouter-gpt-oss-20b` | OpenAI GPT-OSS 20B | Chat |
| `openrouter-gemma4-31b` | Google Gemma 4 31B | Chat |
| `openrouter-gemma4-26b` | Google Gemma 4 26B (MoE) | Chat |
| `openrouter-north-mini-code` | Cohere North Mini Code | Chat |
| `openrouter-owl-alpha` | OpenRouter Owl Alpha | Chat |
| `openrouter-laguna-m1` | Poolside Laguna M.1 | Chat |
| `openrouter-laguna-xs2` | Poolside Laguna XS.2 | Chat |
| `openrouter-nemotron-nano-9b` | NVIDIA Nemotron Nano 9B v2 | Chat |
| `openrouter-nemotron-nano-30b` | NVIDIA Nemotron 3 Nano 30B | Chat |
| `openrouter-nemotron-omni` | NVIDIA Nemotron 3 Nano Omni | Chat |
| `openrouter-nemotron-12b-vl` | NVIDIA Nemotron Nano 12B VL | Chat |
| `openrouter-embed-vl` | NVIDIA LLaMA Nemotron Embed VL 1B v2 | Embedding |
| `openrouter-seedream-4.5` | ByteDance Seedream 4.5 | Image Generation |

### Ollama (Local Inference)
Private models running on a local machine at `192.168.100.11:11434`. No data leaves your network.

| Model Name | Ollama Model |
|---|---|
| `llama3.2-local` | `llama3.2` |
| `qwen-local` | `qwen3.5:9b` |
| `gemma-local` | `gemma4:e4b` |
| `phi4-mini-local` | `phi4-mini` |
| `gemma4-heretic-local` | `igorls/gemma-4-12B-it-heretic-GGUF` |
| `qwen3.5-abliterated-local` | `oroboroslabs/qwen3.5-abliterated-47-4` |
| `ollama-embed` | `mxbai-embed-large` (embeddings) |

---

## Fallback Routing Logic

When a model fails (rate limit, timeout, or error), requests automatically cascade through a predefined fallback chain. The router uses a `least-busy` strategy and respects a 30-second cooldown on failed backends before retrying them.

```
gemini-3.5-flash
  └─► gemini-3.1-flash-lite
      └─► gemini-2.5-flash
          └─► gemini-2.0-flash
              └─► groq-llama4-scout
                  └─► groq-llama3.3-70b
                      └─► openrouter-nemotron-ultra
                          └─► openrouter-gpt-oss-120b

gemini-3.1-pro
  └─► gemini-3.5-flash ─► gemini-2.5-pro ─► groq-llama4-scout ─► groq-gpt-oss-120b ─► openrouter-nemotron-super

gemini-2.5-pro
  └─► gemini-3.1-pro ─► groq-gpt-oss-120b ─► openrouter-nemotron-ultra

groq-llama4-scout
  └─► groq-llama3.3-70b ─► groq-gpt-oss-120b ─► openrouter-nemotron-ultra
```

Router configuration: `num_retries: 3`, `request_timeout: 90s`, `allowed_fails: 2`.

---

## Repository Structure

```
.
├── config/
│   ├── litellm/
│   │   └── config.yml          # All model definitions, router settings, fallback chains
│   ├── nginx/
│   │   └── nginx.conf          # Reverse proxy with rate limiting (10 req/s burst 20)
│   └── prometheus/
│       ├── prometheus.yml      # Scrape configs for all services + blackbox probe
│       └── alerts.yml          # Alerting rules (downtime, errors, rate limits, memory)
├── scripts/
│   ├── backup.sh               # PostgreSQL dump + Redis SAVE + config archive
│   ├── healthcheck.sh          # Health probe for LiteLLM, Prometheus, Grafana, PG, Redis
│   ├── init-db.sql             # PostgreSQL schema initialization with pgvector + indexes
│   ├── log-rotate.sh           # Size-based log rotation + 30-day retention
│   └── rotate-keys.sh          # Gemini API key validator with optional gcloud provisioning
├── docker-compose.yml          # Full service definition with resource limits + health checks
├── makefile                    # Developer-friendly command interface
├── test_api.py                 # Quick smoke test via OpenAI SDK against local proxy
├── .env.example                # Template for all required environment variables
└── .gitignore                  # Excludes .env, databases, logs, backups, volumes
```

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- At least one API key for any configured provider
- (Optional) [Ollama](https://ollama.com/) running on your local network for local model support

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd <repo-name>

# Copy the environment template
cp .env.example .env
```

### 2. Fill in your API keys

Open `.env` and populate it with your credentials:

```bash
# --- Google Gemini (add as many as you have, up to 10) ---
GEMINI_API_KEY_1=AIza...
GEMINI_API_KEY_2=AIza...

# --- Groq (up to 3 keys) ---
GROQ_API_KEY_1=gsk_...

# --- OpenRouter (up to 10 keys) ---
OPENROUTER_API_KEY_1=sk-or-v1-...

# --- LiteLLM master key (generate a random secret) ---
LITELLM_MASTER_KEY=sk-my-secret-key-$(openssl rand -hex 16)

# --- Database credentials ---
POSTGRES_PASSWORD=your-strong-password
REDIS_PASSWORD=your-redis-password
DATABASE_URL=postgresql://litellm:your-strong-password@postgres:5432/litellm

# --- Grafana ---
GRAFANA_ADMIN_PASSWORD=your-grafana-password

# --- Ollama (optional, point to your local machine's IP) ---
OLLAMA_API_BASE=http://192.168.x.x:11434
```

> **Security note:** Never commit `.env` to version control. It is already in `.gitignore`.

### 3. Start the core stack

```bash
make up
```

This starts LiteLLM, PostgreSQL, and Redis. After ~10 seconds, the proxy is live.

### 4. Verify health

```bash
make health
```

Expected output:
```
OK: LiteLLM → {"status": "healthy"}
OK: Prometheus → Prometheus is Ready.
OK: Grafana → {"database": "ok"}
OK: PostgreSQL → accepting connections
OK: Redis → PONG
```

### 5. Start the monitoring stack (optional)

```bash
docker compose --profile monitoring up -d
```

Grafana will be available at [http://localhost:3000](http://localhost:3000).

---

## Usage

### With the OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000/v1",
    api_key="your-LITELLM_MASTER_KEY"
)

response = client.chat.completions.create(
    model="gemini-2.5-flash",   # or any model name from the tables above
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### Quick smoke test

```bash
python test_api.py
```

### Switching models

Any application pointing at this proxy can freely switch between providers by changing only the `model` parameter — no API key management, no provider-specific SDK:

```python
# Cloud model with automatic fallback
model="gemini-3.5-flash"

# Fast Groq inference
model="groq-llama4-scout"

# Local private inference (no data leaves your machine)
model="llama3.2-local"

# Free frontier model via OpenRouter
model="openrouter-nemotron-ultra"

# Embeddings
model="ollama-embed"

# Image generation
model="openrouter-seedream-4.5"
```

---

## Makefile Commands

| Command | Description |
|---|---|
| `make up` | Start all core services and run health checks |
| `make down` | Stop all services |
| `make logs` | Tail live logs (last 100 lines) |
| `make status` | Show container status |
| `make health` | Check health endpoints for all services |
| `make backup` | Dump PostgreSQL and save Redis snapshot |
| `make clean` | Remove all Docker volumes (destructive) |
| `make rotate-keys` | Run the Gemini API key validation and rotation script |
| `make shell-litellm` | Open a shell inside the LiteLLM container |
| `make shell-postgres` | Open a psql session in the PostgreSQL container |
| `make shell-redis` | Open a redis-cli session |

---

## API Key Rotation

The `rotate-keys.sh` script manages the health and lifecycle of Gemini API keys. It supports three modes:

```bash
# Run a single validation pass (checks all 10 keys, flags failures)
./scripts/rotate-keys.sh rotate

# Run as a daemon (re-checks every 5 minutes by default)
./scripts/rotate-keys.sh monitor

# Pull usage statistics from Prometheus
./scripts/rotate-keys.sh stats
```

Or via Make:

```bash
make rotate-keys
```

**What it does:**
1. Sends a minimal test prompt to the Gemini API for each configured key
2. Classifies the response as `HEALTHY`, `RATE_LIMITED (429)`, or `INVALID (400/401/403)`
3. If `GOOGLE_CLOUD_PROJECT` is set, it can provision replacement keys via `gcloud` and delete invalidated ones
4. Triggers a live config reload on the LiteLLM proxy (or restarts the container as fallback)
5. Logs all actions with timestamps to `./logs/rotate-keys.log`

---

## Monitoring & Alerting

### Prometheus Scrape Targets

| Job | Target | Interval |
|---|---|---|
| `litellm` | LiteLLM metrics endpoint (`:4001/metrics`) | 10s |
| `redis-exporter` | Redis Exporter (`:9121`) | 15s |
| `postgres-exporter` | PostgreSQL Exporter (`:9187`) | 15s |
| `cadvisor` | Container metrics (`:8080`) | 15s |
| `node` | Host system metrics (`:9100`) | 30s |
| `blackbox` | HTTP health probe (`/health/readiness`) | 15s |
| `prometheus` | Self-monitoring (`:9090`) | 30s |

### Alert Rules

| Alert | Condition | Severity |
|---|---|---|
| `LiteLLMProxyDown` | Proxy unreachable for > 1 minute | Critical |
| `HighErrorRate` | > 10% of requests failing over 5m | Warning |
| `RateLimitHigh` | < 20% of rate limit remaining | Warning |
| `RedisDown` | Redis unreachable for > 1 minute | Critical |
| `PostgresDown` | PostgreSQL unreachable for > 1 minute | Critical |
| `HighMemoryUsage` | > 90% memory usage for > 5 minutes | Warning |
| `MultipleAPIFailures` | > 5 API failures in 10m for any model | Warning |

### Resource Limits

| Service | Memory Limit | Memory Reservation | CPU Limit |
|---|---|---|---|
| LiteLLM Proxy | 2 GB | — | 1.5 cores |
| PostgreSQL | 512 MB | 256 MB | — |
| Redis | 256 MB | — | — |
| Nginx | 128 MB | — | — |
| Prometheus | 512 MB | — | — |
| Grafana | 256 MB | — | — |
| Exporters (each) | 64 MB | — | — |

---

## Network Architecture

The Docker Compose setup uses three isolated networks to enforce least-privilege communication:

```
┌─── public ─────────────────────────────────────────────────────┐
│  litellm (4000, 4001)  ·  nginx (80, 443)  ·  blackbox-exporter│
└────────────────────────────────────────────────────────────────┘

┌─── private (internal — no external access) ─────────────────────┐
│  litellm  ·  postgres  ·  redis  ·  cadvisor  ·  node-exporter  │
│  redis-exporter  ·  postgres-exporter  ·  prometheus             │
└─────────────────────────────────────────────────────────────────┘

┌─── monitoring ──────────────────────────────────────────────────┐
│  prometheus  ·  grafana  ·  cadvisor  ·  node-exporter           │
│  redis-exporter  ·  postgres-exporter  ·  blackbox-exporter      │
└─────────────────────────────────────────────────────────────────┘
```

- Databases (`postgres`, `redis`) are on the `private` network only — never directly reachable from outside Docker
- LiteLLM bridges `public` and `private`, acting as the single ingress point
- Monitoring services are isolated to the `monitoring` network, with read-only access to the `private` network for metric scraping

Nginx applies **per-IP rate limiting** (`10 req/s`, burst of 20) and connection limiting (100 concurrent connections per IP) at the edge.

---

## Database

PostgreSQL 15 with the **pgvector extension** is initialized via `scripts/init-db.sql`, which creates:

- `litellm_organization` — organization entities
- `litellm_user` — users with role-based access and foreign key to organization
- Composite indexes on `(organization_id)` and `(user_email)` for query performance
- `BEFORE UPDATE` triggers maintaining `updated_at` timestamps automatically

Redis is configured with:
- Append-only persistence (`appendfsync everysec`)
- 256 MB max memory with `allkeys-lru` eviction policy
- 1000 max clients, 300-second connection timeout
- Password authentication required

---

## Docker Compose Profiles

Services are grouped into optional profiles to keep the default footprint small:

| Profile | Services included |
|---|---|
| _(default)_ | `litellm`, `postgres`, `redis` |
| `monitoring` | `prometheus`, `grafana`, `cadvisor`, `node-exporter`, `redis-exporter`, `postgres-exporter`, `blackbox-exporter` |
| `with-nginx` | `nginx` (reverse proxy + SSL termination) |
| `auto-update` | `watchtower` (automatic container updates) |

Start multiple profiles:
```bash
docker compose --profile monitoring --profile with-nginx up -d
```

---

## Backup & Recovery

### Create a backup

```bash
make backup
```

This produces:
- `backups/postgres_YYYYMMDD_HHMMSS.sql` — full PostgreSQL dump
- `backups/full_backup_YYYYMMDD_HHMMSS.tar.gz` — compressed archive of configs and `.env`

### Restore PostgreSQL

```bash
docker exec -i litellm-postgres psql -U litellm litellm < backups/postgres_YYYYMMDD_HHMMSS.sql
```

---

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY_1..10` | Google Gemini API keys | — |
| `GROQ_API_KEY_1..3` | Groq API keys | — |
| `OPENROUTER_API_KEY_1..10` | OpenRouter API keys | — |
| `LITELLM_MASTER_KEY` | Proxy authentication key | — |
| `LITELLM_LOG_LEVEL` | Log verbosity (`DEBUG`, `INFO`, `WARNING`) | `INFO` |
| `LITELLM_NUM_WORKERS` | Uvicorn worker count | `4` |
| `LITELLM_REQUEST_TIMEOUT` | Global request timeout (seconds) | `60` |
| `LITELLM_NUM_RETRIES` | Retry attempts per request | `3` |
| `LITELLM_CACHE_TTL` | Redis cache TTL (seconds) | `3600` |
| `LITELLM_MAX_PARALLEL_REQUESTS` | Max concurrent requests | `100` |
| `POSTGRES_USER` | PostgreSQL user | `litellm` |
| `POSTGRES_PASSWORD` | PostgreSQL password | — |
| `POSTGRES_DB` | PostgreSQL database name | `litellm` |
| `REDIS_PASSWORD` | Redis password | — |
| `DATABASE_URL` | Full PostgreSQL connection string | — |
| `GRAFANA_ADMIN_USER` | Grafana admin username | `admin` |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password | — |
| `OLLAMA_API_BASE` | Ollama server URL | `http://192.168.100.11:11434` |
| `GOOGLE_CLOUD_PROJECT` | GCP project (for `rotate-keys.sh` key provisioning) | — |
| `MONITOR_INTERVAL` | Key rotation daemon interval (seconds) | `300` |

### Adding New API Keys

1. Add the new key to `.env`: `GEMINI_API_KEY_11=AIza...`
2. Add a new entry in `config/litellm/config.yml` under the desired model group
3. Reload the proxy: `curl -X POST http://localhost:4000/reload` or `docker compose restart litellm`

### Adding New Models

Add a new block to `config/litellm/config.yml`:

```yaml
- model_name: my-new-model          # Name clients will use
  litellm_params:
    model: provider/model-id        # LiteLLM model string
    api_key: "os.environ/MY_KEY"
    rpm: 20
    timeout: 60
  model_info:
    mode: chat
    supports_function_calling: true
```

---

## Security Considerations

- All secrets are stored in `.env` which is gitignored — **never commit it**
- Database and Redis services are not exposed on host ports — they communicate only on internal Docker networks
- Nginx enforces IP-based rate limiting to prevent abuse of the proxy endpoint
- The `LITELLM_MASTER_KEY` acts as a bearer token; rotate it periodically via `.env` and a container restart
- For production deployments, uncomment the HTTPS redirect in `config/nginx/nginx.conf` and mount TLS certificates at `config/nginx/ssl/`

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss the proposed modification.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-improvement`
3. Commit your changes: `git commit -m 'Add my improvement'`
4. Push to the branch: `git push origin feature/my-improvement`
5. Open a pull request

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built on top of [LiteLLM](https://github.com/BerriAI/litellm) · Monitored with [Prometheus](https://prometheus.io/) & [Grafana](https://grafana.com/) · Proxied by [Nginx](https://nginx.org/)

</div>
