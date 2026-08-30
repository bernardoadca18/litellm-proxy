# LiteLLM Proxy Gateway

**A lightweight, production-grade AI API gateway with multi-provider load balancing, key pooling, and optional observability stack.**

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-Proxy-8A2BE2)](https://github.com/BerriAI/litellm)

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Add your API keys to .env
# GEMINI_API_KEY_1=your-key
# OPENROUTER_API_KEY_1=your-key
# GROQ_API_KEY_1=your-key
# LITELLM_MASTER_KEY=your-secret-key

# 3. Start minimal runtime (LiteLLM only, ~200MB RAM)
make up

# 4. Test
make test
```

Your proxy is now live at `http://localhost:4000/v1`

## Architecture

```
                    ┌─────────────────────────┐
                    │   Your Applications     │
                    │   (OpenAI SDK)          │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │       LiteLLM           │
                    │  - 1 worker (default)   │
                    │  - simple-shuffle       │
                    │  - key pooling          │
                    │  - automatic cooldown   │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
    ┌───────────┐        ┌───────────┐        ┌───────────┐
    │  Gemini   │        │OpenRouter │        │   Groq    │
    │ N keys    │        │ N keys    │        │ N keys    │
    └───────────┘        └───────────┘        └───────────┘
                                │
                                ▼
                        ┌───────────┐
                        │  Ollama   │
                        │  (local)  │
                        └───────────┘
```

## Runtime Modes

### Core (Default) - Minimal RAM
```bash
make up
```
- LiteLLM only
- ~200MB RAM
- No database, no cache, no monitoring
- Recommended for most deployments

### With Redis Cache
```bash
make up-cache
```
- LiteLLM + Redis
- Use when you need response caching or multi-worker state

### With PostgreSQL
```bash
make up-database
```
- Adds PostgreSQL for persistence, teams, budgets
- Not needed for simple key pooling

### With Monitoring
```bash
make up-monitoring
```
- Prometheus + Grafana + exporters
- Optional observability stack

### Full Stack
```bash
make up-full
```

## Key Features

### Key Pooling
Distribute requests across multiple API keys for the same model:
- Each model can have N keys
- Automatic load balancing
- Rate limit survival through distribution

### Routing Strategy
- **simple-shuffle**: Random selection with equal weights
- Automatic cooldown on failures (60s default)
- Failover to next available key in group

### RAM Optimized
- 1 worker by default (I/O bound workload)
- No database required for core function
- Optional services via Docker Compose profiles

## Configured Models

| Model Alias | Provider | Keys |
|-------------|----------|------|
| `gemini-3.6-flash` | Google Gemini | 11 |
| `gemini-3.1-pro` | Google Gemini | 11 |
| `gemini-3.5-flash-lite` | Google Gemini | 11 |
| `groq-llama4-scout` | Groq | 4 |
| `groq-llama3.3-70b` | Groq | 4 |
| `openrouter-*` | OpenRouter | 11 each |
| `llama3.2-local` | Ollama | - |
| `qwen-local` | Ollama | - |

## Usage

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000/v1",
    api_key="your-LITELLM_MASTER_KEY"
)

response = client.chat.completions.create(
    model="gemini-3.6-flash",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### cURL

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer your-LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.6-flash",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Adding New Keys

1. Add to `.env`:
   ```
   GEMINI_API_KEY_12=your-new-key
   ```

2. Add to `config/litellm/config.yml` under the model group:
   ```yaml
   - model_name: gemini-3.6-flash
     litellm_params:
       model: gemini/gemini-3.6-flash
       api_key: "os.environ/GEMINI_API_KEY_12"
       rpm: 15
       timeout: 60
   ```

3. Recreate:
   ```bash
   docker compose up -d --force-recreate litellm
   ```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make up` | Start core services (minimal) |
| `make down` | Stop all services |
| `make logs` | View logs |
| `make health` | Check service health |
| `make validate` | Validate config |
| `make test` | Run smoke test |
| `make backup` | Backup config |
| `make up-monitoring` | Start monitoring stack |
| `make up-database` | Start with PostgreSQL |
| `make clean` | Remove all volumes |

## Resource Requirements

| Mode | RAM | Services |
|------|-----|----------|
| Core | ~200MB | LiteLLM |
| + Cache | +64MB | + Redis |
| + Database | +256MB | + PostgreSQL |
| + Monitoring | +512MB | + Prometheus/Grafana |

## Configuration

### Workers
- Default: 1 worker (recommended)
- Use 2+ only if benchmarks show necessity
- Set via `LITELLM_NUM_WORKERS` in `.env`

### Log Level
- `WARNING`: Production (default)
- `INFO`: Troubleshooting
- `DEBUG`: Development

### Routing
Configured in `config/litellm/config.yml`:
```yaml
router_settings:
  routing_strategy: "simple-shuffle"
  num_retries: 2
  cooldown_time: 60
  allowed_fails: 2
```

## Security

- Never commit `.env` to version control
- All secrets stay in environment variables
- Database and Redis not exposed on host ports
- Use `LITELLM_MASTER_KEY` for API authentication

## Troubleshooting

```bash
# Check health
make health

# View logs
make logs

# Validate config
make validate

# Test API
make test
```

## License

MIT License - Built on [LiteLLM](https://github.com/BerriAI/litellm)
