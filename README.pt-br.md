# LiteLLM Proxy Gateway

**Gateway de IA mínimo com balanceamento de carga multi-provider e pooling de chaves.**

## Início Rápido

```bash
# 1. Copiar template de ambiente
cp .env.example .env

# 2. Adicionar suas chaves API ao .env
# GEMINI_API_KEY_1=sua-chave
# OPENROUTER_API_KEY_1=sua-chave
# GROQ_API_KEY_1=sua-chave
# LITELLM_MASTER_KEY=sua-chave-secreta

# 3. Iniciar proxy
make up

# 4. Testar
make test
```

Seu proxy está disponível em `http://localhost:4000/v1`

## Arquitetura

```
                    ┌─────────────────────────┐
                    │   Suas Aplicações       │
                    │   (OpenAI SDK)          │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │       LiteLLM           │
                    │  - 1 worker             │
                    │  - simple-shuffle       │
                    │  - key pooling          │
                    │  - cooldown automático  │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
    ┌───────────┐        ┌───────────┐        ┌───────────┐
    │  Gemini   │        │OpenRouter │        │   Groq    │
    │ N chaves  │        │ N chaves  │        │ N chaves  │
    └───────────┘        └───────────┘        └───────────┘
                                │
                                ▼
                        ┌───────────┐
                        │  Ollama   │
                        │  (local)  │
                        └───────────┘
```

## Requisitos

- Docker com Docker Compose
- ~260MB RAM (idle)

## Funcionalidades

### Key Pooling
Distribui requisições entre múltiplas chaves API para o mesmo modelo:
- Cada modelo pode ter N chaves
- Balanceamento de carga automático
- Sobrevivência a rate limits através de distribuição

### Estratégia de Roteamento
- **simple-shuffle**: Seleção aleatória com pesos iguais
- Cooldown automático em falhas (60s padrão)
- Failover para próxima chave disponível no grupo

## Modelos Configurados

| Alias do Modelo | Provider | Chaves |
|-----------------|----------|--------|
| `gemini-3.6-flash` | Google Gemini | 11 |
| `gemini-3.1-pro` | Google Gemini | 11 |
| `gemini-3.5-flash-lite` | Google Gemini | 11 |
| `groq-llama4-scout` | Groq | 4 |
| `groq-llama3.3-70b` | Groq | 4 |
| `openrouter-*` | OpenRouter | 11 cada |
| `llama3.2-local` | Ollama | - |
| `qwen-local` | Ollama | - |

## Uso

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000/v1",
    api_key="seu-LITELLM_MASTER_KEY"
)

response = client.chat.completions.create(
    model="gemini-3.6-flash",
    messages=[{"role": "user", "content": "Olá!"}]
)

print(response.choices[0].message.content)
```

### cURL

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer seu-LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.6-flash",
    "messages": [{"role": "user", "content": "Olá!"}]
  }'
```

## Adicionando Novas Chaves

1. Adicionar ao `.env`:
   ```
   GEMINI_API_KEY_12=sua-nova-chave
   ```

2. Reiniciar:
   ```bash
   make restart
   ```

**Não é necessário editar `providers.yml`** - as chaves são descobertas automaticamente por prefixo.

## Comandos do Makefile

| Comando | Descrição |
|---------|-------------|
| `make up` | Iniciar proxy |
| `make down` | Parar proxy |
| `make restart` | Reiniciar proxy |
| `make logs` | Ver logs |
| `make health` | Verificar saúde |
| `make generate-config` | Gerar config do providers.yml |
| `make validate` | Validar config |
| `make doctor` | Rodar diagnósticos |
| `make test` | Rodar smoke test |
| `make clean` | Remover containers e volumes |

## Configuração

### providers.yml (Fonte da Verdade)

`config/providers.yml` define providers, chaves e modelos. O `config/litellm/config.yml` é gerado a partir dele.

```yaml
providers:
  gemini:
    key_prefix: GEMINI_API_KEY_
    models:
      - name: gemini-3.6-flash
        model: gemini/gemini-3.6-flash
        mode: chat
        rpm: 15
        timeout: 60
```

### Roteamento

Configurado em `config/providers.yml`:
```yaml
router:
  routing_strategy: simple-shuffle
  num_retries: 2
  cooldown_time: 60
  allowed_fails: 2
```

## Segurança

- Nunca commite `.env` no controle de versão
- Todos os secrets ficam em variáveis de ambiente
- Use `LITELLM_MASTER_KEY` para autenticação da API

## Troubleshooting

```bash
# Rodar diagnósticos
make doctor

# Verificar saúde
make health

# Ver logs
make logs

# Validar config
make validate

# Testar API
make test
```

## Licença

MIT License - Construído sobre [LiteLLM](https://github.com/BerriAI/litellm)
