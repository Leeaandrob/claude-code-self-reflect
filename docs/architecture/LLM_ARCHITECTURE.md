# Arquitetura de LLM: Claude Code + Claude Self-Reflect

## TL;DR - Resposta Rápida

**Pergunta**: Como está a camada de LLM? É bind ao Claude Code ou chamamos a API da Anthropic?

**Resposta**:
1. **Claude Code** → Chama API da Anthropic (ou Bedrock/Vertex)
2. **Claude Self-Reflect MCP Server** → **NÃO** chama LLM algum (exceto batch narratives v7.0)
3. **Separação clara**: Claude Code = Inteligência | MCP Server = Memória/Busca

---

## 1. Arquitetura Completa

### 1.1 Visão Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                        Usuário                                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code (CLI)                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MCP Client (stdio/http)                                 │  │
│  │  - Gerencia conexões com MCP servers                     │  │
│  │  - Passa resultados para o LLM                           │  │
│  │  - Renderiza respostas para o usuário                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LLM Backend (AQUI ESTÁ O CLAUDE!)                       │  │
│  │                                                           │  │
│  │  Opção 1: Anthropic API (Padrão)                        │  │
│  │  ├─ api.anthropic.com                                    │  │
│  │  ├─ Modelos: Sonnet 4.5, Haiku 4.5                      │  │
│  │  └─ Auth: ANTHROPIC_API_KEY                             │  │
│  │                                                           │  │
│  │  Opção 2: AWS Bedrock                                   │  │
│  │  ├─ bedrock-runtime.us-east-1.amazonaws.com             │  │
│  │  ├─ Modelos: claude-sonnet-4-5, claude-haiku-4-5       │  │
│  │  └─ Auth: AWS credentials                               │  │
│  │                                                           │  │
│  │  Opção 3: Google Vertex AI                              │  │
│  │  ├─ vertex-ai.googleapis.com                            │  │
│  │  └─ Auth: Google Cloud credentials                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────┬─────────────────────────────────────────────────────────┘
        │ stdio/http
        │ Invoca MCP tools quando necessário
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│           Claude Self-Reflect MCP Server (Python)               │
│                                                                 │
│  ❌ NÃO TEM LLM PRÓPRIO                                        │
│  ✅ Apenas processamento de dados:                             │
│                                                                 │
│  1. Embeddings:                                                │
│     ├─ Local: FastEmbed (all-MiniLM-L6-v2) 384d               │
│     └─ Cloud: Voyage AI (voyage-3) 1024d                      │
│                                                                 │
│  2. Busca Vetorial: Qdrant                                     │
│                                                                 │
│  3. Processamento: Python puro                                 │
│     ├─ Parsing de JSONL                                        │
│     ├─ Chunking de conversas                                   │
│     ├─ Extração de metadata                                    │
│     └─ Formatar resultados                                     │
│                                                                 │
│  🆕 EXCEÇÃO: v7.0 Batch Narratives                            │
│     └─ Anthropic Batch API (opcional, geração de narrativas)  │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Qdrant (Vector DB)                           │
│  - Armazena embeddings                                          │
│  - Busca por similaridade                                       │
│  - Sem LLM                                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Claude Code - Camada de LLM

### 2.1 Opções de Backend

O Claude Code suporta **3 opções** de backend para acessar modelos Claude:

#### Opção 1: Anthropic API (Padrão) ✅ MAIS COMUM

**Endpoint**: `https://api.anthropic.com/v1/messages`

**Configuração**:
```bash
# Automaticamente detectado se ANTHROPIC_API_KEY existe
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

**Modelos disponíveis**:
- `claude-sonnet-4-5-20250929` (principal)
- `claude-haiku-4-5-20251001` (rápido/barato)
- `claude-opus-4-20250514` (máxima qualidade, se disponível)

**Características**:
- ✅ Setup mais simples
- ✅ Acesso direto às features mais novas
- ✅ Melhor documentação
- ❌ Requer API key da Anthropic
- ❌ Dados trafegam pela internet pública

**Autenticação**:
```bash
# Via CLI
claude login

# Via env var
export ANTHROPIC_API_KEY="sk-ant-..."
```

#### Opção 2: AWS Bedrock 🏢 ENTERPRISE

**Endpoint**: `https://bedrock-runtime.{region}.amazonaws.com/model/{model-id}/invoke`

**Configuração**:
```bash
# Habilitar Bedrock
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-east-1  # Obrigatório

# Autenticação AWS (qualquer método)
aws configure  # Opção 1: AWS CLI
# OU
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
# OU
export AWS_PROFILE="my-sso-profile"
aws sso login
```

**Modelos disponíveis**:
- `global.anthropic.claude-sonnet-4-5-20250929-v1:0` (principal)
- `us.anthropic.claude-haiku-4-5-20251001-v1:0` (rápido)

**Características**:
- ✅ Integrado ao ecossistema AWS
- ✅ Políticas IAM para controle de acesso
- ✅ VPC endpoints (tráfego privado)
- ✅ CloudWatch logging/monitoring
- ✅ Orçamento/billing consolidado AWS
- ❌ Setup mais complexo
- ❌ Requer conta AWS e permissões Bedrock
- ❌ Pode ter latência adicional

**Diferenças importantes**:
- `/login` e `/logout` desabilitados (usa AWS auth)
- Refresh automático de credenciais via SDK
- Suporte a SSO profiles

#### Opção 3: Google Vertex AI 🌐 ENTERPRISE

**Endpoint**: `https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/anthropic/models/{model}:streamRawPredict`

**Configuração**:
```bash
# Configurar Google Cloud
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="my-project-id"
export GOOGLE_CLOUD_REGION="us-central1"
```

**Modelos disponíveis**:
- `claude-3-5-sonnet@20250929`
- `claude-3-5-haiku@20251001`

**Características**:
- ✅ Integrado ao Google Cloud
- ✅ Identity & Access Management (IAM)
- ✅ Cloud Logging/Monitoring
- ✅ Vertex AI Workbench integration
- ❌ Setup mais complexo
- ❌ Requer conta Google Cloud
- ❌ Geograficamente limitado a regiões do GCP

### 2.2 Qual Backend o Claude Code Usa Por Padrão?

**Detecção Automática**:

```python
# Pseudo-código do Claude Code
if os.getenv("CLAUDE_CODE_USE_BEDROCK") == "1":
    backend = "aws_bedrock"
elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    backend = "vertex_ai"
elif os.getenv("ANTHROPIC_API_KEY"):
    backend = "anthropic_api"
else:
    raise "No LLM backend configured!"
```

**Ordem de prioridade**:
1. Bedrock (se `CLAUDE_CODE_USE_BEDROCK=1`)
2. Vertex AI (se `GOOGLE_APPLICATION_CREDENTIALS` existe)
3. Anthropic API (padrão)

### 2.3 Como o LLM Interage com MCP Tools?

```
┌─────────────────────────────────────────────────────────────────┐
│ User: "Search my past conversations about Docker"              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code                                  │
│                                                                 │
│  1. Envia prompt + contexto para LLM                           │
│     POST /v1/messages                                          │
│     {                                                          │
│       "model": "claude-sonnet-4-5-20250929",                  │
│       "messages": [{                                           │
│         "role": "user",                                        │
│         "content": "Search my past conversations about Docker" │
│       }],                                                      │
│       "tools": [                                               │
│         {                                                      │
│           "name": "mcp__claude-self-reflect__reflect_on_past", │
│           "description": "Search past conversations...",       │
│           "input_schema": {...}                               │
│         },                                                     │
│         ... mais 19 tools ...                                  │
│       ]                                                        │
│     }                                                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Anthropic API / Bedrock / Vertex AI                │
│                                                                 │
│  2. LLM processa e decide usar tool                            │
│     Response:                                                  │
│     {                                                          │
│       "stop_reason": "tool_use",                              │
│       "content": [{                                            │
│         "type": "tool_use",                                    │
│         "name": "mcp__claude-self-reflect__reflect_on_past",  │
│         "input": {                                             │
│           "query": "Docker",                                   │
│           "mode": "full"                                       │
│         }                                                      │
│       }]                                                       │
│     }                                                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code                                  │
│                                                                 │
│  3. Extrai tool_use e chama MCP server                        │
│     stdio → run-mcp.sh → python server.py                     │
│     Tool: reflect_on_past(query="Docker", mode="full")       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│           Claude Self-Reflect MCP Server                        │
│                                                                 │
│  4. Executa busca (SEM usar LLM)                               │
│     a. Gera embedding do query "Docker"                        │
│        - Local: FastEmbed                                      │
│        - Cloud: Voyage AI                                      │
│     b. Busca no Qdrant por similaridade                        │
│     c. Aplica memory decay                                     │
│     d. Formata resultados                                      │
│     e. Retorna JSON                                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code                                  │
│                                                                 │
│  5. Envia resultado de volta ao LLM                            │
│     POST /v1/messages                                          │
│     {                                                          │
│       "messages": [                                            │
│         ... original message ...,                              │
│         {                                                      │
│           "role": "assistant",                                 │
│           "content": [{ "type": "tool_use", ... }]            │
│         },                                                     │
│         {                                                      │
│           "role": "user",                                      │
│           "content": [{                                        │
│             "type": "tool_result",                            │
│             "tool_use_id": "...",                             │
│             "content": "[{...search results...}]"            │
│           }]                                                   │
│         }                                                      │
│       ]                                                        │
│     }                                                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Anthropic API / Bedrock / Vertex AI                │
│                                                                 │
│  6. LLM sintetiza resposta final                               │
│     Response:                                                  │
│     {                                                          │
│       "content": [{                                            │
│         "type": "text",                                        │
│         "text": "Found 3 conversations about Docker:\n        │
│                  1. Docker compose issues (2 weeks ago)...\n  │
│                  2. Container memory limits (1 month ago)..." │
│       }]                                                       │
│     }                                                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code                                  │
│  7. Renderiza resposta para o usuário                         │
└─────────────────────────────────────────────────────────────────┘
```

**Pontos importantes**:
- ✅ O LLM decide **quando** invocar tools
- ✅ O LLM decide **quais** tools invocar
- ✅ O LLM decide **como** interpretar resultados
- ❌ O MCP server **NÃO** tem acesso ao LLM
- ❌ O MCP server **NÃO** decide nada "inteligente"

---

## 3. Claude Self-Reflect - Sem LLM Próprio

### 3.1 O Que o MCP Server Faz (SEM LLM)

```python
# mcp-server/src/server.py

@mcp.tool()
async def reflect_on_past(query: str, mode: str = "full"):
    """Search past conversations - NO LLM NEEDED."""

    # 1. Gera embedding do query (matemática pura)
    if use_local:
        embedding = fastembed.embed(query)  # Modelo local
    else:
        embedding = voyage.embed(query)     # API Voyage

    # 2. Busca vetorial (algoritmo matemático)
    results = await qdrant.search(
        collection_name=collection,
        query_vector=embedding,
        limit=10
    )

    # 3. Aplica memory decay (fórmula matemática)
    for result in results:
        age_days = (now - result.timestamp).days
        decay_factor = exp(-age_days / 90)  # 90-day half-life
        result.score *= decay_factor

    # 4. Formata e retorna (string processing)
    return format_results(results)
```

**Nenhum LLM envolvido!** Apenas:
- ✅ Modelos de embedding (transformers matemáticos)
- ✅ Busca vetorial (cosine similarity)
- ✅ Processamento de strings
- ✅ Formatação de dados

### 3.2 Embeddings ≠ LLM

**Diferença crucial**:

| Aspecto | Embedding Model | LLM (Claude) |
|---------|----------------|--------------|
| **Propósito** | Converter texto → vetor numérico | Gerar texto inteligente |
| **Tamanho** | ~100MB (FastEmbed) | ~100GB+ (Claude) |
| **Output** | Array de floats [0.1, -0.5, ...] | Texto natural |
| **Raciocínio** | ❌ Não raciocina | ✅ Raciocina |
| **Custo** | Grátis (local) ou $0.0001/query | $0.003-$0.015/1K tokens |
| **Latência** | 10-50ms | 500-5000ms |

**Embedding models usados**:

```python
# Local (padrão) - 384 dimensões
model = "sentence-transformers/all-MiniLM-L6-v2"
# Gratuito, roda local, 100MB, 20ms

# Cloud (opcional) - 1024 dimensões
model = "voyage-3"
# Pago ($0.00012/1K tokens), API, melhor qualidade, 50ms
```

### 3.3 EXCEÇÃO: v7.0 Batch Narratives

**A ÚNICA parte que usa LLM da Anthropic**:

```python
# docs/design/batch_import_all_projects.py

def batch_generate_narratives(conversations: list):
    """Usa Anthropic Batch API para gerar narrativas."""

    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    # Cria batch job
    batch = client.batches.create(
        requests=[
            {
                "custom_id": f"conv-{i}",
                "params": {
                    "model": "claude-sonnet-4-5-20250929",
                    "messages": [{
                        "role": "user",
                        "content": f"Transform this conversation into a structured narrative:\n{conv}"
                    }]
                }
            }
            for i, conv in enumerate(conversations)
        ]
    )

    return batch.id
```

**Por que isso é diferente**:
- ❌ **NÃO** é o MCP server que chama
- ✅ É um **script separado** (`batch_import_all_projects.py`)
- ✅ Roda **offline** (não em tempo real)
- ✅ Usa **Batch API** (50% mais barato)
- ✅ **Opcional** (requer ANTHROPIC_API_KEY)

**Propósito**:
- Gerar narrativas ricas de conversas antigas
- Melhorar qualidade de busca (0.074 → 0.691 score)
- Extrair metadata (tools, files, concepts)

---

## 4. Comparação: API Direta vs Claude Code

### 4.1 Chamando Anthropic API Diretamente

```python
import anthropic

client = anthropic.Anthropic(api_key="sk-ant-...")

# Chamada manual
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": "Search my past conversations about Docker"
    }]
)

print(response.content[0].text)
# Output: "I don't have access to your past conversations.
#          I'm starting fresh with no memory of previous chats."
```

**Problema**: Claude não tem memória!

### 4.2 Via Claude Code + MCP

```bash
# Claude Code CLI
claude

> Search my past conversations about Docker

# Claude Code automaticamente:
# 1. Detecta intenção de buscar memória
# 2. Invoca mcp__claude-self-reflect__reflect_on_past("Docker")
# 3. MCP server busca no Qdrant
# 4. LLM sintetiza resultados
# Output: "Found 3 conversations about Docker:
#          1. Docker compose issues (2 weeks ago)...
#          2. Container memory (1 month ago)..."
```

**Benefício**: Claude TEM memória via MCP!

### 4.3 Diferenças Chave

| Aspecto | API Direta | Claude Code + MCP |
|---------|-----------|-------------------|
| **Memória** | ❌ Nenhuma | ✅ Ilimitada (Qdrant) |
| **Tools** | ⚠️ Manual (via tool calling) | ✅ Automático (MCP) |
| **Contexto** | Apenas conversa atual | Histórico completo |
| **Setup** | API key | CLI + MCP server |
| **Custo** | Apenas API | API + infraestrutura |
| **Latência** | ~500ms | ~700ms (+ MCP call) |

---

## 5. Fluxo Completo de Dados

### 5.1 Write Path (Indexação)

```
Conversa no Claude Code
        │
        ▼
~/.claude/projects/{project}/{timestamp}.jsonl
        │
        ▼
Watcher detecta novo arquivo
        │
        ▼
streaming-watcher.py (Python)
├─ Parse JSONL
├─ Chunk messages
├─ Generate embeddings (FastEmbed ou Voyage)
└─ Upload para Qdrant
        │
        ▼
Qdrant Vector Database
└─ Armazena {embedding, metadata, payload}
```

**Nenhum LLM envolvido** (exceto v7.0 narratives opcionais)

### 5.2 Read Path (Busca)

```
User: "Search Docker issues"
        │
        ▼
Claude Code CLI
├─ Parse comando
└─ Send to LLM (Anthropic/Bedrock/Vertex)
        │
        ▼
LLM decide usar tool
└─ tool_use: reflect_on_past("Docker")
        │
        ▼
Claude Code invoca MCP server
└─ stdio → run-mcp.sh → python server.py
        │
        ▼
MCP Server (NO LLM)
├─ Generate embedding("Docker")
├─ Search Qdrant
├─ Apply memory decay
└─ Format results
        │
        ▼
Return results to Claude Code
        │
        ▼
Claude Code → LLM
└─ Synthesize response with results
        │
        ▼
Render to user
```

**LLM usado apenas 2x**:
1. Decidir invocar tool
2. Sintetizar resposta final

---

## 6. Custos e Performance

### 6.1 Custos por Componente

#### Claude Code (LLM)

| Backend | Modelo | Input | Output | Batch (50% off) |
|---------|--------|-------|--------|----------------|
| **Anthropic API** | Sonnet 4.5 | $3/MTok | $15/MTok | $1.50/MTok |
| **Anthropic API** | Haiku 4.5 | $0.80/MTok | $4/MTok | $0.40/MTok |
| **AWS Bedrock** | Sonnet 4.5 | $3/MTok | $15/MTok | ❌ N/A |
| **AWS Bedrock** | Haiku 4.5 | $0.80/MTok | $4/MTok | ❌ N/A |
| **Vertex AI** | Sonnet 3.5 | $3/MTok | $15/MTok | ❌ N/A |

**Custo médio de query com MCP**:
```
User query: "Search Docker" (~10 tokens)
LLM decision: (~100 tokens)
Tool result: (~500 tokens)
LLM synthesis: (~200 tokens)

Total: 10 input + 200 output = ~$0.003
```

#### Claude Self-Reflect (MCP Server)

| Componente | Custo |
|-----------|-------|
| **Local embeddings** | $0 (FastEmbed) |
| **Cloud embeddings** | $0.00012/1K tokens (Voyage) |
| **Qdrant** | $0 (self-hosted Docker) |
| **Python processing** | $0 (compute negligível) |

**Custo médio de busca**:
```
Query: "Search Docker" (~2 tokens)
Embedding: $0.00000024 (Voyage) ou $0 (local)
Qdrant: $0
Total: ~$0
```

#### v7.0 Narratives (Opcional)

| Operação | Custo |
|----------|-------|
| **Narrative generation** | $0.012/conversation (Batch API) |
| **Standard API** | $0.025/conversation |
| **Savings** | 50% |

**ROI**: Melhoria de 9.3x na qualidade de busca por $0.012/conv

### 6.2 Performance

| Operação | Latência | Onde |
|----------|----------|------|
| **LLM call** | 500-5000ms | Anthropic/Bedrock/Vertex |
| **Embedding** | 10-50ms | Local ou Voyage |
| **Qdrant search** | 3-15ms | Docker local |
| **Total MCP call** | 20-100ms | Soma embedding + search |
| **Full query** | 700-5200ms | LLM + MCP |

**Gargalo**: LLM (10-100x mais lento que MCP)

---

## 7. Configuração Recomendada

### 7.1 Para Desenvolvedores Individuais

```bash
# LLM: Anthropic API (simples)
export ANTHROPIC_API_KEY="sk-ant-..."

# Embeddings: Local (grátis, privado)
export PREFER_LOCAL_EMBEDDINGS=true

# MCP: stdio (baixa latência)
claude mcp add claude-self-reflect \
  /path/to/run-mcp.sh

# Narratives: Desabilitado (economizar)
# (sem ANTHROPIC_API_KEY em .env do projeto)
```

**Custo mensal estimado**: $5-20 (apenas LLM queries)

### 7.2 Para Times (Enterprise)

```bash
# LLM: AWS Bedrock (controle, billing)
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-east-1
aws sso login --profile work

# Embeddings: Voyage (melhor qualidade)
export PREFER_LOCAL_EMBEDDINGS=false
export VOYAGE_KEY="pa-..."

# MCP: stdio (por enquanto, HTTP futuro)
claude mcp add claude-self-reflect \
  /path/to/run-mcp.sh

# Narratives: Habilitado (ROI positivo)
export ANTHROPIC_API_KEY="sk-ant-..."
docker compose --profile batch-automation up -d
```

**Custo mensal estimado**:
- LLM (Bedrock): $50-500/user
- Embeddings (Voyage): $1-10/user
- Narratives: $10-50/user
- **Total**: $61-560/user/mês

### 7.3 Para Research/Academia

```bash
# LLM: Anthropic API (melhor modelo)
export ANTHROPIC_API_KEY="sk-ant-..."

# Embeddings: Local (sem custo, reproduzível)
export PREFER_LOCAL_EMBEDDINGS=true

# MCP: stdio
claude mcp add claude-self-reflect \
  /path/to/run-mcp.sh

# Narratives: Habilitado para experimentos
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Custo mensal estimado**: $10-50 (uso moderado)

---

## 8. Perguntas Frequentes

### Q1: O MCP server precisa de API key da Anthropic?

**R**: **NÃO**, o MCP server NÃO usa LLM da Anthropic para buscas normais.

**Exceção**: v7.0 batch narratives (opcional) usa Batch API para gerar narrativas.

### Q2: Qual modelo de embedding o Claude Code usa?

**R**: O **Claude Code** não usa embeddings. O **Claude Self-Reflect MCP Server** usa:
- Local: `sentence-transformers/all-MiniLM-L6-v2` (384d, grátis)
- Cloud: `voyage-3` (1024d, $0.00012/1K tokens)

### Q3: Posso usar Claude Self-Reflect sem internet?

**R**: **SIM**, se usar:
- Local embeddings (`PREFER_LOCAL_EMBEDDINGS=true`)
- Qdrant local (Docker)

**Mas ainda precisa de internet para**:
- Claude Code chamar LLM (Anthropic/Bedrock/Vertex)

### Q4: O MCP server roda o modelo Claude localmente?

**R**: **NÃO**. O MCP server:
- ❌ NÃO tem modelo Claude
- ❌ NÃO faz inferência de LLM
- ✅ Apenas busca vetorial + formatação

O modelo Claude roda em:
- ☁️ Anthropic API (cloud)
- ☁️ AWS Bedrock (cloud)
- ☁️ Google Vertex AI (cloud)

**Não há opção de rodar Claude localmente** (modelo é proprietário)

### Q5: Qual a diferença entre FastEmbed e Voyage?

| Aspecto | FastEmbed | Voyage |
|---------|-----------|--------|
| **Onde roda** | Local | Cloud API |
| **Custo** | Grátis | $0.00012/1K tokens |
| **Dimensões** | 384 | 1024 |
| **Qualidade** | Boa | Melhor |
| **Latência** | 10-20ms | 40-60ms |
| **Privacidade** | 100% local | Envia texto para API |
| **Setup** | Zero config | API key |

**Recomendação**:
- **FastEmbed**: Default (grátis, privado, bom suficiente)
- **Voyage**: Se precisa de máxima qualidade e pode pagar

### Q6: Bedrock é mais barato que API direta?

**R**: **Mesmo preço** para modelos Claude:
- API direta: $3/MTok input, $15/MTok output
- Bedrock: $3/MTok input, $15/MTok output

**Mas Bedrock oferece**:
- ✅ Billing consolidado AWS
- ✅ VPC privado (sem tráfego público)
- ✅ IAM policies granulares
- ✅ CloudWatch integration

**Trade-off**: Complexidade de setup vs benefícios enterprise

### Q7: v7.0 narratives compensa o custo?

**R**: **Depende do uso**:

**Custo**:
- $0.012/conversation via Batch API
- 1000 conversas = $12

**Benefício**:
- Search quality: 0.074 → 0.691 (9.3x melhor)
- Token compression: 82% redução
- Metadata: tools, files, concepts

**ROI positivo se**:
- Você faz muitas buscas
- Qualidade de busca é crítica
- Tem orçamento para melhorias

**Pular se**:
- Orçamento apertado
- Poucas conversas (<100)
- Busca básica funciona bem

---

## 9. Conclusão

### Resumo da Arquitetura de LLM

**Claude Code**:
- ✅ **TEM** LLM (Claude via API/Bedrock/Vertex)
- ✅ **DECIDE** quando usar MCP tools
- ✅ **SINTETIZA** respostas finais
- 💰 **CUSTO**: $0.003-0.015/query

**Claude Self-Reflect MCP Server**:
- ❌ **NÃO TEM** LLM próprio
- ✅ **BUSCA** vetorial via embeddings
- ✅ **FORMATA** resultados
- 💰 **CUSTO**: ~$0/query (local) ou ~$0.0001/query (Voyage)

**Exceção v7.0**:
- ⚠️ **USA** Anthropic Batch API
- ✅ **GERA** narrativas offline
- ✅ **OPCIONAL** (requer API key)
- 💰 **CUSTO**: $0.012/conversation

### Diagrama Mental Simples

```
┌─────────────────────┐
│  Você faz pergunta  │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────┐
│  Claude Code                 │
│  (Tem LLM - Pago)           │
│  ├─ Raciocina               │
│  ├─ Decide invocar tools    │
│  └─ Sintetiza resposta      │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Claude Self-Reflect         │
│  (Sem LLM - Grátis)         │
│  ├─ Busca vetorial          │
│  ├─ Formata dados           │
│  └─ Retorna resultados      │
└──────────────────────────────┘
```

### Recomendação Final

**Para maioria dos usuários**:
```bash
LLM: Anthropic API (simples)
Embeddings: Local (grátis)
Narratives: Desabilitado (economizar)
```

**Para empresas**:
```bash
LLM: AWS Bedrock (controle)
Embeddings: Voyage (qualidade)
Narratives: Habilitado (ROI)
```

**Princípio chave**:
- LLM = Inteligência (caro, Claude Code)
- MCP = Memória (barato, Self-Reflect)
- Separação = Eficiência

---

**Documento atualizado**: 2025-01-05
**Versão**: 1.0
