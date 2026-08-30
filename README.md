# LiteLLM Proxy Gateway

**Minimal AI API gateway with multi-provider load balancing and key pooling.**

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Add your API keys to .env
# GEMINI_API_KEY_1=your-key
# OPENROUTER_API_KEY_1=your-key
# GROQ_API_KEY_1=your-key
# LITELLM_MASTER_KEY=your-secret-key

# 3. Start proxy
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
                    │  - 1 worker             │
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

## Requirements

- Docker with Docker Compose
- ~300MB RAM (idle)

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

2. Add to `config/providers.yml`:
   ```yaml
   gemini:
     keys:
       - GEMINI_API_KEY_12
   ```

3. Regenerate config and restart:
   ```bash
   make generate-config
   make up
   ```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make up` | Start proxy |
| `make down` | Stop proxy |
| `make logs` | View logs |
| `make health` | Check health |
| `make generate-config` | Generate config from providers.yml |
| `make validate` | Validate config |
| `make doctor` | Run diagnostics |
| `make test` | Run smoke test |
| `make clean` | Remove containers and volumes |

## Configuration

### providers.yml (Source of Truth)

`config/providers.yml` defines providers, keys, and models. The actual `config/litellm/config.yml` is generated from it.

```yaml
providers:
  gemini:
    keys:
      - GEMINI_API_KEY_1
      - GEMINI_API_KEY_2
    models:
      - name: gemini-3.6-flash
        model: gemini/gemini-3.6-flash
        rpm: 15
        timeout: 60
```

### Routing

Configured in `config/providers.yml`:
```yaml
router:
  routing_strategy: simple-shuffle
  num_retries: 2
  cooldown_time: 60
  allowed_fails: 2
```

## Security

- Never commit `.env` to version control
- All secrets stay in environment variables
- Use `LITELLM_MASTER_KEY` for API authentication

## Troubleshooting

```bash
# Run diagnostics
make doctor

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
