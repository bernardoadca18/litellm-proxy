<div align="center">

# LiteLLM Proxy Gateway

**Gateway de API de inteligência artificial auto-hospedado, pronto para produção, com balanceamento de carga entre múltiplos provedores, roteamento de fallback inteligente, suporte a modelos locais via Ollama e stack completa de observabilidade.**

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-Proxy-8A2BE2)](https://github.com/BerriAI/litellm)
[![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?logo=grafana&logoColor=white)](https://grafana.com/)
[![Nginx](https://img.shields.io/badge/Nginx-Reverse%20Proxy-009639?logo=nginx&logoColor=white)](https://nginx.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Models-black?logo=ollama)](https://ollama.com/)

[Read in English](README.md)

</div>

---

## Visao Geral

Este repositório contém um **deploy de proxy LiteLLM testado em producao** projetado para consolidar chaves de API de múltiplos provedores de IA em um único endpoint unificado, compatível com a interface da OpenAI. Ele elimina os gargalos de rate limit por meio de pooling inteligente de chaves e balanceamento de carga entre **10 contas Gemini**, **3 contas Groq** e **10 contas OpenRouter** — tudo exposto como uma única superfície de API compatível com qualquer SDK da OpenAI.

Além dos provedores em nuvem, integra nativamente **modelos Ollama em execucao local**, tornando-se um gateway de IA completo para cenários de inferência online e offline.

### Por que isso existe

Gerenciar dezenas de chaves de API distribuídas em múltiplos provedores é trabalhoso. Rate limits são atingidos de forma imprevisível. Failovers exigem intervencao manual. Os custos são invisíveis até a fatura chegar. Este proxy resolve tudo isso:

- **Um endpoint, qualquer modelo** — aponte suas aplicacoes para `http://localhost:4000/v1` e use qualquer modelo configurado com o SDK padrão da OpenAI
- **Rotacao de chaves transparente** — o LiteLLM distribui automaticamente as requisicoes entre todas as chaves configuradas para o mesmo modelo, maximizando o throughput
- **Fallbacks sem downtime** — se o Gemini 3.5 Flash atingir o rate limit, o tráfego cai automaticamente para o Gemini 2.5 Flash, depois para o Groq, depois para o OpenRouter
- **Observabilidade completa** — cada requisicao é registrada, cada métrica é coletada pelo Prometheus, cada dashboard está no Grafana

---

## Arquitetura

```
                          +-----------------------------------------------------+
                          |                  Suas Aplicacoes                    |
                          |   (OpenAI SDK, curl, qualquer cliente HTTP)         |
                          +----------------------+------------------------------+
                                                 |
                                          Porta 80 / 443
                                                 |
                          +----------------------v------------------------------+
                          |                   Nginx                             |
                          |    Rate limiting  .  SSL termination  .  Proxy      |
                          +----------------------+------------------------------+
                                                 |
                                          Porta 4000
                                                 |
                          +----------------------v------------------------------+
                          |               LiteLLM Proxy                         |
                          |                                                     |
                          |  +----------+  +----------+  +------------------+   |
                          |  |  Router  |  | Fallback |  |   Key Pooling    |   |
                          |  | (least-  |  |  Engine  |  |  (Round Robin)   |   |
                          |  |  busy)   |  |          |  |                  |   |
                          |  +----------+  +----------+  +------------------+   |
                          +--+-------------+-------------+----------------------+
                             |              |              |
               +-------------+--+   +------+------+  +---+----------+
               | Google Gemini  |   |    Groq     |  |  OpenRouter  |
               | (10 API keys)  |   | (3 API keys)|  | (10 API keys)|
               +----------------+   +-------------+  +--------------+
                                                              |
                                                    +---------+--------+
                                                    |  Ollama (Local)  |
                                                    |  192.168.100.11  |
                                                    +------------------+

       +------------------------------------------------------------------+
       |                    Infraestrutura de Suporte                     |
       |                                                                  |
       |  +-----------+  +--------------+  +----------+  +-----------+    |
       |  |PostgreSQL |  |    Redis     |  |Prometheus|  |  Grafana  |    |
       |  |(pgvector) |  |(Cache+Fila)  |  | (Metricas|  |(Dashboards|    |
       |  +-----------+  +--------------+  +----------+  +-----------+    |
       +------------------------------------------------------------------+
```

---

## Funcionalidades

### Capacidades Principais

- **API compatível com OpenAI** — substituto direto para qualquer chamada `openai.ChatCompletion.create()`; nenhuma alteracao de código é necessária nas suas aplicacoes
- **Balanceamento de carga multi-chave** — distribui requisicoes entre todas as chaves de API para o mesmo modelo usando estratégia least-busy, multiplicando os limites efetivos de rate
- **Roteamento de fallback hierárquico** — reprocessa automaticamente requisicoes com falha percorrendo uma cadeia de provedores configurada, sem nenhum código adicional no cliente
- **Inferência local** — roteia para o Ollama em cargas de trabalho sensíveis à privacidade, inferência sem custo ou cenários offline
- **Cache de requisicoes** — cache semântico baseado em Redis com TTL configurável reduz chamadas de API redundantes e custos

### Stack de Observabilidade

- **Métricas Prometheus** — coleta dados do LiteLLM, Redis, PostgreSQL, cAdvisor, Node Exporter e sondas Blackbox em um banco de dados de séries temporais unificado
- **Dashboards Grafana** — dashboards pré-provisionados para taxas de requisicao, distribuicoes de latência, taxas de erro e utilizacao de recursos
- **Alertas estruturados** — regras de alerta para downtime do proxy, altas taxas de erro, esgotamento de rate limit, falhas de Redis e PostgreSQL, e pressao de memória

### Ferramentas Operacionais

- **Rotacao automatizada de chaves** — `rotate-keys.sh` valida todas as chaves Gemini contra a API em producao, sinaliza chaves inválidas ou com rate limit esgotado e, opcionalmente, provisiona novas via `gcloud`
- **Scripts de backup** — dumps do PostgreSQL e snapshots do Redis com um único comando, arquivados com timestamp
- **Rotacao de logs** — rotacao automática por tamanho e retencao de 30 dias para todos os logs de container
- **Integracão com Watchtower** — atualizacão automática opcional das imagens de container do proxy LiteLLM em ciclos de 24 horas
- **Interface Makefile** — todas as operacoes comuns expostas como alvos `make` para uma experiência de desenvolvimento limpa

---

## Modelos Configurados

### Google Gemini (via Google AI Studio)

10 chaves de API são agrupadas por modelo, oferecendo até **10x os rate limits do plano gratuito** por grupo de modelos.

| Nome do Modelo | Modelo na API | RPM / chave | TPM / chave | Modo |
|---|---|---|---|---|
| `gemini-3.5-flash` | `gemini/gemini-3.5-flash` | 15 | 3.000.000 | Chat |
| `gemini-3.1-pro` | `gemini/gemini-3.1-pro` | 5 | 5.000.000 | Chat |
| `gemini-3.1-flash-lite` | `gemini/gemini-3.1-flash-lite` | 15 | 10.000.000 | Chat |
| `gemini-2.5-pro` | `gemini/gemini-2.5-pro` | 5 | 5.000.000 | Chat |
| `gemini-2.5-flash` | `gemini/gemini-2.5-flash` | 10 | 3.000.000 | Chat |
| `gemini-2.5-flash-lite` | `gemini/gemini-2.5-flash-lite` | 15 | 10.000.000 | Chat |
| `gemini-2.0-flash` | `gemini/gemini-2.0-flash` | 15 | 10.000.000 | Chat |
| `gemini-2.0-flash-lite` | `gemini/gemini-2.0-flash-lite` | 15 | 10.000.000 | Chat |

### Groq (Inferência de Alta Velocidade)

3 chaves de API agrupadas por modelo, aproveitando o hardware LPU da Groq para latência ultrabaixa.

| Nome do Modelo | Modelo na API | Modo |
|---|---|---|
| `groq-llama4-scout` | `meta-llama/llama-4-scout-17b-16e-instruct` | Chat |
| `groq-llama3.3-70b` | `llama-3.3-70b-versatile` | Chat |
| `groq-llama3.1-8b` | `llama-3.1-8b-instant` | Chat |
| `groq-qwen3-32b` | `qwen/qwen3-32b` | Chat |
| `groq-qwen3.6-27b` | `qwen/qwen3.6-27b` | Chat |
| `groq-gpt-oss-120b` | `openai/gpt-oss-120b` | Chat |
| `groq-gpt-oss-20b` | `openai/gpt-oss-20b` | Chat |

### OpenRouter (Modelos Gratuitos)

10 chaves de API agrupadas por modelo, com acesso a modelos abertos de última geracão sem custo.

| Nome do Modelo | Provedor | Modo |
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
| `openrouter-seedream-4.5` | ByteDance Seedream 4.5 | Geracao de Imagem |

### Ollama (Inferência Local)

Modelos privados em execucao em uma máquina local em `192.168.100.11:11434`. Nenhum dado sai da sua rede.

| Nome do Modelo | Modelo Ollama |
|---|---|
| `llama3.2-local` | `llama3.2` |
| `qwen-local` | `qwen3.5:9b` |
| `gemma-local` | `gemma4:e4b` |
| `phi4-mini-local` | `phi4-mini` |
| `gemma4-heretic-local` | `igorls/gemma-4-12B-it-heretic-GGUF` |
| `qwen3.5-abliterated-local` | `oroboroslabs/qwen3.5-abliterated-47-4` |
| `ollama-embed` | `mxbai-embed-large` (embeddings) |

---

## Logica de Roteamento de Fallback

Quando um modelo falha (rate limit, timeout ou erro), as requisicoes percorrem automaticamente uma cadeia de fallback predefinida. O roteador usa a estratégia `least-busy` e respeita um cooldown de 30 segundos em backends com falha antes de tentar novamente.

```
gemini-3.5-flash
  -> gemini-3.1-flash-lite
      -> gemini-2.5-flash
          -> gemini-2.0-flash
              -> groq-llama4-scout
                  -> groq-llama3.3-70b
                      -> openrouter-nemotron-ultra
                          -> openrouter-gpt-oss-120b

gemini-3.1-pro
  -> gemini-3.5-flash -> gemini-2.5-pro -> groq-llama4-scout -> groq-gpt-oss-120b -> openrouter-nemotron-super

gemini-2.5-pro
  -> gemini-3.1-pro -> groq-gpt-oss-120b -> openrouter-nemotron-ultra

groq-llama4-scout
  -> groq-llama3.3-70b -> groq-gpt-oss-120b -> openrouter-nemotron-ultra
```

Configuracao do roteador: `num_retries: 3`, `request_timeout: 90s`, `allowed_fails: 2`.

---

## Estrutura do Repositorio

```
.
+-- config/
|   +-- litellm/
|   |   +-- config.yml          # Definicoes de modelos, configuracoes do roteador, cadeias de fallback
|   +-- nginx/
|   |   +-- nginx.conf          # Proxy reverso com rate limiting (10 req/s, burst de 20)
|   +-- prometheus/
|       +-- prometheus.yml      # Configuracoes de scrape para todos os servicos + sonda blackbox
|       +-- alerts.yml          # Regras de alerta (downtime, erros, rate limits, memoria)
+-- scripts/
|   +-- backup.sh               # Dump do PostgreSQL + Redis SAVE + arquivo de configs
|   +-- healthcheck.sh          # Probe de saude para LiteLLM, Prometheus, Grafana, PG, Redis
|   +-- init-db.sql             # Inicializacao do schema PostgreSQL com pgvector + indices
|   +-- log-rotate.sh           # Rotacao de logs por tamanho + retencao de 30 dias
|   +-- rotate-keys.sh          # Validador de chaves Gemini com provisionamento opcional via gcloud
+-- docker-compose.yml          # Definicao completa dos servicos com limites de recursos e health checks
+-- makefile                    # Interface de comandos amigavel ao desenvolvedor
+-- test_api.py                 # Smoke test rapido via OpenAI SDK contra o proxy local
+-- .env.example                # Template para todas as variaveis de ambiente necessarias
+-- .gitignore                  # Exclui .env, bancos de dados, logs, backups e volumes
```

---

## Primeiros Passos

### Pre-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- Ao menos uma chave de API para qualquer provedor configurado
- (Opcional) [Ollama](https://ollama.com/) em execucao na sua rede local para suporte a modelos locais

### 1. Clonar e configurar

```bash
git clone <url-do-repositorio>
cd <nome-do-repositorio>

# Copiar o template de variaveis de ambiente
cp .env.example .env
```

### 2. Preencher suas chaves de API

Abra o arquivo `.env` e preencha com suas credenciais:

```bash
# --- Google Gemini (adicione quantas tiver, ate 10) ---
GEMINI_API_KEY_1=AIza...
GEMINI_API_KEY_2=AIza...

# --- Groq (ate 3 chaves) ---
GROQ_API_KEY_1=gsk_...

# --- OpenRouter (ate 10 chaves) ---
OPENROUTER_API_KEY_1=sk-or-v1-...

# --- Chave mestra do LiteLLM (gere um segredo aleatorio) ---
LITELLM_MASTER_KEY=sk-minha-chave-$(openssl rand -hex 16)

# --- Credenciais do banco de dados ---
POSTGRES_PASSWORD=senha-forte
REDIS_PASSWORD=senha-redis

DATABASE_URL=postgresql://litellm:senha-forte@postgres:5432/litellm

# --- Grafana ---
GRAFANA_ADMIN_PASSWORD=senha-grafana

# --- Ollama (aponte para o IP da sua maquina local) ---
OLLAMA_API_BASE=http://192.168.x.x:11434
```

> **Aviso de seguranca:** nunca commite o arquivo `.env` no controle de versao. Ele já está incluído no `.gitignore`.

### 3. Iniciar o stack principal

```bash
make up
```

Isso inicia o LiteLLM, o PostgreSQL e o Redis. Após aproximadamente 10 segundos, o proxy está no ar.

### 4. Verificar a saude dos servicos

```bash
make health
```

Saída esperada:

```
OK: LiteLLM   -> {"status": "healthy"}
OK: Prometheus -> Prometheus is Ready.
OK: Grafana    -> {"database": "ok"}
OK: PostgreSQL -> accepting connections
OK: Redis      -> PONG
```

### 5. Iniciar o stack de monitoramento (opcional)

```bash
docker compose --profile monitoring up -d
```

O Grafana estará disponível em [http://localhost:3000](http://localhost:3000).

---

## Uso

### Com o SDK Python da OpenAI

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000/v1",
    api_key="sua-LITELLM_MASTER_KEY"
)

response = client.chat.completions.create(
    model="gemini-2.5-flash",   # ou qualquer nome de modelo das tabelas acima
    messages=[
        {"role": "user", "content": "Olá!"}
    ]
)

print(response.choices[0].message.content)
```

### Smoke test rapido

```bash
python test_api.py
```

### Alternando entre modelos

Qualquer aplicacao apontando para este proxy pode alternar livremente entre provedores mudando apenas o parametro `model` — sem gerenciamento de chaves, sem SDK específico por provedor:

```python
# Modelo em nuvem com fallback automatico
model="gemini-3.5-flash"

# Inferência rapida via Groq
model="groq-llama4-scout"

# Inferência local e privada (nenhum dado sai da sua maquina)
model="llama3.2-local"

# Modelo de ponta gratuito via OpenRouter
model="openrouter-nemotron-ultra"

# Embeddings
model="ollama-embed"

# Geracao de imagem
model="openrouter-seedream-4.5"
```

---

## Comandos do Makefile

| Comando | Descricao |
|---|---|
| `make up` | Inicia todos os servicos principais e executa health checks |
| `make down` | Para todos os servicos |
| `make logs` | Exibe logs em tempo real (ultimas 100 linhas) |
| `make status` | Exibe o status dos containers |
| `make health` | Verifica os endpoints de saude de todos os servicos |
| `make backup` | Gera dump do PostgreSQL e snapshot do Redis |
| `make clean` | Remove todos os volumes Docker (operacao destrutiva) |
| `make rotate-keys` | Executa o script de validacao e rotacao de chaves Gemini |
| `make shell-litellm` | Abre um shell dentro do container LiteLLM |
| `make shell-postgres` | Abre uma sessao psql no container PostgreSQL |
| `make shell-redis` | Abre uma sessao redis-cli |

---

## Rotacao de Chaves de API

O script `rotate-keys.sh` gerencia a saude e o ciclo de vida das chaves de API do Gemini. Ele suporta tres modos:

```bash
# Executa uma unica passagem de validacao (verifica todas as 10 chaves, sinaliza falhas)
./scripts/rotate-keys.sh rotate

# Executa como daemon (re-verifica a cada 5 minutos por padrao)
./scripts/rotate-keys.sh monitor

# Coleta estatisticas de uso do Prometheus
./scripts/rotate-keys.sh stats
```

Ou via Make:

```bash
make rotate-keys
```

**O que ele faz:**

1. Envia um prompt de teste mínimo à API do Gemini para cada chave configurada
2. Classifica a resposta como `SAUDAVEL`, `RATE_LIMITED (429)` ou `INVALIDA (400/401/403)`
3. Se `GOOGLE_CLOUD_PROJECT` estiver definido, pode provisionar chaves de reposicao via `gcloud` e deletar as inválidas
4. Aciona um reload de configuracao ao vivo no proxy LiteLLM (ou reinicia o container como fallback)
5. Registra todas as acoes com timestamps em `./logs/rotate-keys.log`

---

## Monitoramento e Alertas

### Alvos de Scrape do Prometheus

| Job | Alvo | Intervalo |
|---|---|---|
| `litellm` | Endpoint de métricas LiteLLM (`:4001/metrics`) | 10s |
| `redis-exporter` | Redis Exporter (`:9121`) | 15s |
| `postgres-exporter` | PostgreSQL Exporter (`:9187`) | 15s |
| `cadvisor` | Métricas de container (`:8080`) | 15s |
| `node` | Métricas do sistema host (`:9100`) | 30s |
| `blackbox` | Sonda HTTP de saude (`/health/readiness`) | 15s |
| `prometheus` | Auto-monitoramento (`:9090`) | 30s |

### Regras de Alerta

| Alerta | Condicao | Severidade |
|---|---|---|
| `LiteLLMProxyDown` | Proxy inacessível por mais de 1 minuto | Crítica |
| `HighErrorRate` | Mais de 10% das requisicoes falhando em 5 minutos | Aviso |
| `RateLimitHigh` | Menos de 20% do rate limit restante | Aviso |
| `RedisDown` | Redis inacessível por mais de 1 minuto | Crítica |
| `PostgresDown` | PostgreSQL inacessível por mais de 1 minuto | Crítica |
| `HighMemoryUsage` | Mais de 90% de uso de memória por mais de 5 minutos | Aviso |
| `MultipleAPIFailures` | Mais de 5 falhas de API em 10 minutos para qualquer modelo | Aviso |

### Limites de Recursos

| Servico | Limite de Memória | Reserva de Memória | Limite de CPU |
|---|---|---|---|
| LiteLLM Proxy | 2 GB | — | 1,5 cores |
| PostgreSQL | 512 MB | 256 MB | — |
| Redis | 256 MB | — | — |
| Nginx | 128 MB | — | — |
| Prometheus | 512 MB | — | — |
| Grafana | 256 MB | — | — |
| Exporters (cada) | 64 MB | — | — |

---

## Arquitetura de Rede

O Docker Compose utiliza tres redes isoladas para aplicar o princípio de menor privilégio na comunicacao entre servicos:

```
+--- public ---------------------------------------------------------+
|  litellm (4000, 4001)  .  nginx (80, 443)  .  blackbox-exporter    |
+--------------------------------------------------------------------+

+--- private (interna -- sem acesso externo) -------------------------+
|  litellm  .  postgres  .  redis  .  cadvisor  .  node-exporter      |
|  redis-exporter  .  postgres-exporter  .  prometheus                |
+---------------------------------------------------------------------+

+--- monitoring -----------------------------------------------------+
|  prometheus  .  grafana  .  cadvisor  .  node-exporter             |
|  redis-exporter  .  postgres-exporter  .  blackbox-exporter        |
+--------------------------------------------------------------------+
```

- Os bancos de dados (`postgres`, `redis`) ficam apenas na rede `private` — nunca alcancáveis diretamente de fora do Docker
- O LiteLLM conecta `public` e `private`, atuando como único ponto de entrada
- Os servicos de monitoramento ficam isolados na rede `monitoring`, com acesso somente leitura à rede `private` para coleta de métricas

O Nginx aplica **rate limiting por IP** (`10 req/s`, burst de 20) e limitacao de conexoes (100 conexoes simultâneas por IP) na borda.

---

## Banco de Dados

O PostgreSQL 15 com a **extensao pgvector** é inicializado via `scripts/init-db.sql`, que cria:

- `litellm_organization` — entidades de organizacao
- `litellm_user` — usuários com controle de acesso baseado em funcao e chave estrangeira para a organizacao
- Índices compostos em `(organization_id)` e `(user_email)` para performance de consultas
- Triggers `BEFORE UPDATE` que mantêm os timestamps `updated_at` atualizados automaticamente

O Redis é configurado com:

- Persistência append-only (`appendfsync everysec`)
- Memória máxima de 256 MB com política de evicao `allkeys-lru`
- 1.000 clientes máximos, timeout de conexao de 300 segundos
- Autenticacao por senha obrigatória

---

## Perfis do Docker Compose

Os servicos são agrupados em perfis opcionais para manter o footprint padrão reduzido:

| Perfil | Servicos incluídos |
|---|---|
| _(padrao)_ | `litellm`, `postgres`, `redis` |
| `monitoring` | `prometheus`, `grafana`, `cadvisor`, `node-exporter`, `redis-exporter`, `postgres-exporter`, `blackbox-exporter` |
| `with-nginx` | `nginx` (proxy reverso + SSL termination) |
| `auto-update` | `watchtower` (atualizacoes automaticas de containers) |

Para iniciar múltiplos perfis:

```bash
docker compose --profile monitoring --profile with-nginx up -d
```

---

## Backup e Recuperacao

### Criar um backup

```bash
make backup
```

Isso gera:

- `backups/postgres_YYYYMMDD_HHMMSS.sql` — dump completo do PostgreSQL
- `backups/full_backup_YYYYMMDD_HHMMSS.tar.gz` — arquivo comprimido com configs e `.env`

### Restaurar o PostgreSQL

```bash
docker exec -i litellm-postgres psql -U litellm litellm < backups/postgres_YYYYMMDD_HHMMSS.sql
```

---

## Referencia de Configuracao

### Variaveis de Ambiente

| Variavel | Descricao | Padrao |
|---|---|---|
| `GEMINI_API_KEY_1..10` | Chaves de API do Google Gemini | — |
| `GROQ_API_KEY_1..3` | Chaves de API do Groq | — |
| `OPENROUTER_API_KEY_1..10` | Chaves de API do OpenRouter | — |
| `LITELLM_MASTER_KEY` | Chave de autenticacao do proxy | — |
| `LITELLM_LOG_LEVEL` | Verbosidade dos logs (`DEBUG`, `INFO`, `WARNING`) | `INFO` |
| `LITELLM_NUM_WORKERS` | Numero de workers Uvicorn | `4` |
| `LITELLM_REQUEST_TIMEOUT` | Timeout global de requisicao (segundos) | `60` |
| `LITELLM_NUM_RETRIES` | Tentativas de retry por requisicao | `3` |
| `LITELLM_CACHE_TTL` | TTL do cache Redis (segundos) | `3600` |
| `LITELLM_MAX_PARALLEL_REQUESTS` | Máximo de requisicoes simultâneas | `100` |
| `POSTGRES_USER` | Usuário do PostgreSQL | `litellm` |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL | — |
| `POSTGRES_DB` | Nome do banco de dados PostgreSQL | `litellm` |
| `REDIS_PASSWORD` | Senha do Redis | — |
| `DATABASE_URL` | String de conexao completa do PostgreSQL | — |
| `GRAFANA_ADMIN_USER` | Usuário administrador do Grafana | `admin` |
| `GRAFANA_ADMIN_PASSWORD` | Senha do administrador do Grafana | — |
| `OLLAMA_API_BASE` | URL do servidor Ollama | `http://192.168.100.11:11434` |
| `GOOGLE_CLOUD_PROJECT` | Projeto GCP (para provisionamento de chaves via `rotate-keys.sh`) | — |
| `MONITOR_INTERVAL` | Intervalo do daemon de rotacao de chaves (segundos) | `300` |

### Adicionando Novas Chaves de API

1. Adicione a nova chave ao `.env`: `GEMINI_API_KEY_11=AIza...`
2. Adicione uma nova entrada em `config/litellm/config.yml` no grupo de modelos desejado
3. Recarregue o proxy: `curl -X POST http://localhost:4000/reload` ou `docker compose restart litellm`

### Adicionando Novos Modelos

Adicione um novo bloco em `config/litellm/config.yml`:

```yaml
- model_name: meu-novo-modelo          # Nome que os clientes utilizarao
  litellm_params:
    model: provedor/id-do-modelo       # String de modelo do LiteLLM
    api_key: "os.environ/MINHA_CHAVE"
    rpm: 20
    timeout: 60
  model_info:
    mode: chat
    supports_function_calling: true
```

---

## Consideracoes de Seguranca

- Todos os segredos são armazenados no `.env`, que está no `.gitignore` — **nunca o commite**
- Os servicos de banco de dados e Redis não ficam expostos em portas do host — comunicam-se apenas nas redes internas do Docker
- O Nginx aplica rate limiting por IP para prevenir abuso do endpoint do proxy
- A `LITELLM_MASTER_KEY` atua como bearer token; rotacione-a periodicamente via `.env` e reinicializacao do container
- Para implantacoes em producao, descomente o redirecionamento HTTPS em `config/nginx/nginx.conf` e monte os certificados TLS em `config/nginx/ssl/`

---

## Contribuindo

Pull requests são bem-vindos. Para mudancas significativas, abra uma issue primeiro para discutir a modificacao proposta.

1. Faca um fork do repositório
2. Crie uma branch de funcionalidade: `git checkout -b feature/minha-melhoria`
3. Commite suas alteracoes: `git commit -m 'Adiciona minha melhoria'`
4. Envie para a branch: `git push origin feature/minha-melhoria`
5. Abra um pull request

---

## Licenca

Este projeto está licenciado sob a licenca MIT — consulte o arquivo [LICENSE](LICENSE) para mais detalhes.

---

<div align="center">

Construído sobre o [LiteLLM](https://github.com/BerriAI/litellm)  ·  Monitorado com [Prometheus](https://prometheus.io/) e [Grafana](https://grafana.com/)  ·  Proxy por [Nginx](https://nginx.org/)

</div>
