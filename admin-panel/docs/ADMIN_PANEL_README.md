# Claude Self-Reflect - Admin Panel

## 📊 Visão Geral

Painel administrativo completo para gerenciar todo o sistema Claude Self-Reflect, construído com **React + TypeScript + Vite + Tailwind + shadcn/ui** no frontend e **FastAPI** no backend.

## 🏗️ Arquitetura

```
claude-self-reflect/
├── admin-panel/          # Frontend (React + Vite + TypeScript)
│   ├── src/
│   │   ├── components/   # Componentes UI
│   │   │   ├── ui/       # shadcn/ui components
│   │   │   ├── layout/   # Layout components
│   │   │   ├── dashboard/
│   │   │   ├── projects/
│   │   │   ├── imports/
│   │   │   ├── collections/
│   │   │   ├── settings/
│   │   │   ├── docker/
│   │   │   └── logs/
│   │   ├── pages/        # Page components
│   │   ├── services/     # API client
│   │   ├── hooks/        # Custom hooks
│   │   ├── types/        # TypeScript types
│   │   └── lib/          # Utilities
│   └── package.json
│
└── admin-api/            # Backend (FastAPI)
    ├── app/
    │   ├── routers/      # API endpoints
    │   │   ├── dashboard.py
    │   │   ├── projects.py
    │   │   ├── imports.py
    │   │   ├── collections.py
    │   │   ├── settings.py
    │   │   ├── docker.py
    │   │   ├── logs.py
    │   │   └── batch.py
    │   └── main.py
    └── requirements.txt
```

## ✨ Funcionalidades

### 1. Dashboard (/)
- **Métricas do Sistema** em tempo real
  - Status Qdrant (conexão, coleções, vetores)
  - Modo de Embeddings (local/cloud)
  - Estatísticas de Importação
  - Uso de Memória
- **Top 5 Projetos** por quantidade de mensagens
- **Atividade Recente** - últimas 10 importações
- Gráficos com Recharts

### 2. Projects (/projects)
- Lista todos os projetos com estatísticas
- Detalhes por projeto:
  - Número de arquivos
  - Total de mensagens
  - Última atualização
  - Coleções associadas (local/cloud)
- Filtros e busca
- Visualização de arquivos por projeto

### 3. Imports (/imports)
- Status geral de importação
- Lista de arquivos importados
- Filtro por projeto
- Progresso de importação
- Estatísticas:
  - Total de arquivos
  - Total de mensagens
  - Percentual de conclusão

### 4. Collections (/collections)
- Lista todas as coleções Qdrant
- Informações detalhadas:
  - Número de vetores
  - Número de pontos
  - Número de segmentos
  - Status (green/yellow/red)
  - Configuração (dimensão, distância)
- Inspeção de coleções individuais

### 5. Settings (/settings)
- **Configuração de Embeddings**
  - Switch entre Local (384d) e Cloud (1024d)
  - Informações do modelo
  - Status da API key
- **Variáveis de Ambiente**
- **Configurações Avançadas**
  - Memory decay
  - Decay weight
  - Decay scale

### 6. Docker (/docker)
- Lista de serviços Docker Compose
- Status de cada serviço:
  - ✅ running
  - ⏹️ stopped
  - 🔄 starting
  - ❌ error
- Controles:
  - Start/Stop serviços
  - Logs por serviço
- Informações:
  - Container ID
  - Uptime
  - Uso de memória/CPU
  - Profile associado

### 7. Logs (/logs)
- **MCP Server Logs** (`~/.claude-self-reflect/logs/mcp-server.log`)
- **Docker Service Logs** por serviço
- Filtros:
  - Nível (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Serviço
  - Período de tempo
- Busca em tempo real
- Auto-refresh configurável
- Download de logs

### 8. Batch Jobs (/batch) - v7.0 AI Narratives
- Lista de jobs batch (narrativas AI)
- Status por job:
  - 📋 queued
  - ⚙️ processing
  - ✅ completed
  - ❌ failed
- Detalhes:
  - Número de conversas
  - Projeto
  - Data de criação/atualização
  - Link para resultado (quando concluído)
- Monitoramento de progresso

## 🚀 Como Usar

### Backend (FastAPI)

```bash
cd admin-api

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor
python -m app.main

# API estará disponível em http://localhost:8000
# Documentação automática: http://localhost:8000/docs
```

### Frontend (React + Vite)

```bash
cd admin-panel

# Instalar dependências
npm install

# Desenvolvimento
npm run dev

# Build para produção
npm run build

# Preview da build
npm run preview

# Painel estará disponível em http://localhost:5173
```

### Variáveis de Ambiente

Criar arquivo `.env` no admin-api:

```env
# Qdrant
QDRANT_URL=http://localhost:6333

# Embeddings
PREFER_LOCAL_EMBEDDINGS=true
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VOYAGE_API_KEY=your_key_here  # Se usar cloud

# Paths
CSR_HOME=/home/user/.claude-self-reflect
CLAUDE_LOGS_PATH=/home/user/.claude/projects

# Memory Decay
ENABLE_MEMORY_DECAY=false
DECAY_WEIGHT=0.3
DECAY_SCALE_DAYS=90
```

Criar arquivo `.env` no admin-panel:

```env
VITE_API_URL=http://localhost:8000/api
```

## 📡 API Endpoints

### Dashboard
- `GET /api/dashboard/metrics` - Métricas gerais do sistema
- `GET /api/dashboard/stats` - Estatísticas detalhadas

### Projects
- `GET /api/projects/` - Lista todos os projetos
- `GET /api/projects/{project_name}` - Detalhes de um projeto

### Imports
- `GET /api/imports/status` - Status geral de importação
- `GET /api/imports/files` - Lista de arquivos importados

### Collections
- `GET /api/collections/` - Lista todas as coleções
- `GET /api/collections/{collection_name}` - Informações de uma coleção

### Settings
- `GET /api/settings/embedding` - Configuração de embeddings
- `POST /api/settings/embedding/mode` - Atualiza modo de embedding

### Docker
- `GET /api/docker/services` - Lista serviços Docker
- `POST /api/docker/services/{service}/start` - Inicia serviço
- `POST /api/docker/services/{service}/stop` - Para serviço

### Logs
- `GET /api/logs/mcp?lines=100` - Logs do MCP server
- `GET /api/logs/docker/{service}?lines=100` - Logs de um serviço

### Batch Jobs
- `GET /api/batch/jobs?limit=50` - Lista jobs batch
- `GET /api/batch/jobs/{job_id}` - Detalhes de um job

## 🎨 Componentes UI (shadcn/ui)

Componentes já implementados:
- ✅ Card (Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter)
- ✅ Button (variants: default, destructive, outline, secondary, ghost, link)
- ✅ Badge (variants: default, secondary, destructive, outline, success, warning, info)

Próximos a implementar:
- [ ] Table
- [ ] Dialog
- [ ] Tabs
- [ ] Alert
- [ ] Progress
- [ ] Skeleton
- [ ] Chart (via Recharts)

## 🔧 Utilities

### lib/utils.ts
- `cn()` - Merge classes com Tailwind
- `formatBytes()` - Formata bytes para KB/MB/GB
- `formatDuration()` - Formata segundos para tempo legível
- `formatRelativeTime()` - Tempo relativo (2h ago, 3d ago)

### types/index.ts
Todas as interfaces TypeScript para:
- Project
- ImportStats
- FileImportStatus
- Collection
- DockerService
- BatchJob
- SystemMetrics
- LogEntry
- EmbeddingConfig

## 🛡️ Segurança

- ✅ CORS configurado para localhost (dev)
- ✅ API endpoints protegidos contra injeção
- ✅ Subprocess com lista de argumentos (não shell=True)
- ✅ Validação de paths
- ✅ Sanitização de inputs
- ⚠️ Produção: adicionar autenticação/autorização

## 📊 Performance

- ✅ Lazy loading de componentes
- ✅ React Router para SPA
- ✅ API assíncrona (async/await)
- ✅ Connection pooling (Qdrant)
- ✅ Caching de estado (unified-state.json)

## 🐳 Docker Support

### Dockerfile para API (futuro)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yaml para admin panel

```yaml
services:
  admin-api:
    build: ./admin-api
    ports:
      - "8000:8000"
    environment:
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - qdrant

  admin-frontend:
    build: ./admin-panel
    ports:
      - "3000:80"
    depends_on:
      - admin-api
```

## 📝 Próximos Passos

### Alta Prioridade
1. [ ] Implementar páginas faltantes (Dashboard, Projects, etc.)
2. [ ] Adicionar componentes shadcn/ui restantes
3. [ ] Implementar hooks personalizados (useProjects, useMetrics)
4. [ ] Adicionar testes (Vitest + React Testing Library)
5. [ ] Adicionar autenticação

### Média Prioridade
6. [ ] WebSocket para logs em tempo real
7. [ ] Gráficos interativos (Recharts)
8. [ ] Dark mode toggle
9. [ ] Export de relatórios (PDF/CSV)
10. [ ] Notificações push

### Baixa Prioridade
11. [ ] Internacionalização (i18n)
12. [ ] PWA support
13. [ ] Mobile responsive otimizado
14. [ ] Documentação Storybook

## 🤝 Integração com Claude Self-Reflect

O admin panel se integra perfeitamente com o sistema existente:

- ✅ Lê `unified-state.json` para estatísticas
- ✅ Conecta ao Qdrant existente (porta 6333)
- ✅ Monitora serviços Docker do docker-compose.yaml
- ✅ Acessa logs em `~/.claude-self-reflect/logs/`
- ✅ Gerencia batch jobs em `~/.claude-self-reflect/batch_state/`
- ✅ Sem modificação do código existente necessária

## 📚 Tecnologias

**Frontend:**
- React 18
- TypeScript 5
- Vite 6
- Tailwind CSS 3
- shadcn/ui
- React Router 6
- Recharts (gráficos)
- Lucide React (ícones)

**Backend:**
- FastAPI
- Pydantic v2
- Qdrant Client
- Python 3.11+
- Uvicorn (ASGI server)

## 🎯 Benefícios

1. **Visibilidade Total** - Veja tudo que está acontecendo no sistema
2. **Controle Centralizado** - Gerencie tudo em uma interface
3. **Debugging Facilitado** - Logs em tempo real e métricas detalhadas
4. **Produtividade** - Não precisa mais usar CLI para tudo
5. **Monitoramento** - Acompanhe saúde do sistema 24/7

---

**Desenvolvido para Claude Self-Reflect v7.0.0**
