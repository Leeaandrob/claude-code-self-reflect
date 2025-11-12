# 🧪 Testando o Admin Panel

## Pré-requisitos

✅ Python 3.11+
✅ Node.js 18+
✅ Docker (para Qdrant)
✅ Claude Self-Reflect já instalado

## Passo 1: Iniciar Qdrant

```bash
docker compose up -d qdrant
```

Aguarde alguns segundos para o Qdrant inicializar.

## Passo 2: Iniciar o Admin Panel

### Opção A: Script Automático (Recomendado)

```bash
./start-admin.sh
```

### Opção B: Manual

**Terminal 1 - Backend:**
```bash
cd admin-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

**Terminal 2 - Frontend:**
```bash
cd admin-panel
npm install
npm run dev
```

## Passo 3: Acessar o Dashboard

Abra seu navegador em: **http://localhost:5173**

Você deve ver:

### 📊 Dashboard

**Métricas (4 Cards):**
1. ✅ Qdrant Status - Badge verde "CONNECTED"
2. ✅ Total Vectors - Número de vetores nas coleções
3. ✅ Imported Files - Total de arquivos e mensagens
4. ✅ Memory Usage - Percentual e valores

**Embedding Configuration:**
- Mode: LOCAL ou CLOUD (badge colorido)
- Model: Nome do modelo
- Dimension: 384d ou 1024d

**Top Projects:**
- Top 5 projetos rankeados por mensagens
- Mostra #rank, nome, total de mensagens e arquivos

**Recent Imports:**
- Últimas 10 importações
- Mostra projeto, mensagens e tempo relativo

### 🔄 Auto-Refresh

O Dashboard atualiza automaticamente a cada 30 segundos!

## Passo 4: Testar a API

### Swagger UI

Acesse: **http://localhost:8000/docs**

Você verá todos os endpoints disponíveis. Teste alguns:

1. **GET /api/dashboard/metrics**
   - Clique em "Try it out"
   - Clique em "Execute"
   - Veja o JSON com todas as métricas

2. **GET /api/projects/**
   - Tente buscar a lista de projetos

3. **GET /api/collections/**
   - Veja suas coleções Qdrant

### cURL

```bash
# Métricas gerais
curl http://localhost:8000/api/dashboard/metrics | jq

# Lista de projetos
curl http://localhost:8000/api/projects/ | jq

# Status de importação
curl http://localhost:8000/api/imports/status | jq

# Coleções Qdrant
curl http://localhost:8000/api/collections/ | jq

# Config de embeddings
curl http://localhost:8000/api/settings/embedding | jq
```

## Passo 5: Navegar pelo Menu

Clique nos itens do menu lateral:

1. **Dashboard** (/) - ✅ Funcional
2. **Projects** (/projects) - Placeholder
3. **Imports** (/imports) - Placeholder
4. **Collections** (/collections) - Placeholder
5. **Batch Jobs** (/batch) - Placeholder
6. **Docker** (/docker) - Placeholder
7. **Logs** (/logs) - Placeholder
8. **Settings** (/settings) - Placeholder

## Passo 6: Verificar Logs

### API Logs
```bash
tail -f logs/api.log
```

### Frontend Logs
Os logs aparecem no terminal onde você rodou `npm run dev`

## Troubleshooting

### Erro: "Failed to fetch"

**Problema**: Frontend não consegue conectar na API

**Solução**:
1. Verifique se a API está rodando: `curl http://localhost:8000/health`
2. Verifique se não tem bloqueio de CORS
3. Reinicie a API: `./stop-admin.sh && ./start-admin.sh`

### Erro: "Qdrant connection failed"

**Problema**: API não consegue conectar no Qdrant

**Solução**:
1. Verifique se Qdrant está rodando: `docker compose ps qdrant`
2. Se não estiver: `docker compose up -d qdrant`
3. Aguarde 5 segundos e recarregue a página

### Dashboard mostra zeros

**Problema**: Nenhum dado foi importado ainda

**Solução**:
1. Execute uma importação: `docker compose --profile import up`
2. Ou use o watcher: `docker compose --profile safe-watch up -d`
3. Aguarde alguns minutos e recarregue

### Porta 8000 já está em uso

**Problema**: Outro serviço usando a porta

**Solução**:
1. Identifique: `lsof -i :8000`
2. Mate o processo: `kill -9 <PID>`
3. Ou mude a porta em `admin-api/app/main.py`

### Erro ao instalar dependências Python

**Problema**: Dependência faltando

**Solução**:
```bash
cd admin-api
pip install --upgrade pip
pip install -r requirements.txt
```

### Erro ao instalar dependências Node

**Problema**: npm install falhou

**Solução**:
```bash
cd admin-panel
rm -rf node_modules package-lock.json
npm install
```

## Parar os Serviços

### Opção A: Script

```bash
./stop-admin.sh
```

### Opção B: Manual

1. Pressione `Ctrl+C` nos terminais
2. Mate processos pendentes:
   ```bash
   pkill -f "uvicorn app.main"
   pkill -f "vite"
   ```

## Testes Básicos

### 1. Dashboard Loads
- [ ] Página carrega sem erros
- [ ] 4 cards de métricas aparecem
- [ ] Badge do Qdrant está verde
- [ ] Top Projects mostra dados
- [ ] Recent Imports mostra dados

### 2. API Funciona
- [ ] `/api/dashboard/metrics` retorna JSON
- [ ] `/api/projects/` retorna array
- [ ] `/api/collections/` retorna coleções
- [ ] `/docs` mostra Swagger UI

### 3. Navegação
- [ ] Menu lateral funciona
- [ ] Todas as rotas carregam
- [ ] URL muda ao navegar
- [ ] Active state do menu funciona

### 4. Auto-Refresh
- [ ] Dashboard atualiza sozinho após 30s
- [ ] Console não mostra erros

## Checklist de Funcionalidades

### Backend
- [x] FastAPI rodando
- [x] 8 routers funcionais
- [x] CORS configurado
- [x] Swagger UI acessível
- [x] Conexão com Qdrant
- [x] Leitura de unified-state.json
- [x] Health check endpoint

### Frontend
- [x] Vite dev server
- [x] React Router
- [x] Layout com sidebar
- [x] Dashboard funcional
- [x] API client
- [x] TypeScript types
- [x] Tailwind CSS
- [x] shadcn/ui components

## Próximos Passos Após Testar

1. **Funciona?** 🎉
   - Parabéns! Você tem um admin panel funcional
   - Comece a usar para monitorar seu sistema
   - Implemente as páginas faltantes conforme necessário

2. **Não funciona?** 🔧
   - Revise os logs (api.log)
   - Verifique as soluções de troubleshooting acima
   - Teste cada componente isoladamente

3. **Quer melhorar?** 🚀
   - Implemente as páginas pendentes
   - Adicione mais componentes shadcn/ui
   - Crie gráficos com Recharts
   - Adicione autenticação
   - Implemente WebSocket para logs em tempo real

## Recursos de Ajuda

- **Logs da API**: `tail -f logs/api.log`
- **Swagger UI**: http://localhost:8000/docs
- **Browser DevTools**: F12 → Console/Network
- **Documentação**: `ADMIN_PANEL_README.md`
- **Summary**: `ADMIN_PANEL_SUMMARY.md`

## Exemplo de Teste Completo

```bash
# 1. Limpar ambiente
./stop-admin.sh
docker compose down
docker compose up -d qdrant

# 2. Aguardar Qdrant
sleep 5

# 3. Iniciar admin panel
./start-admin.sh

# 4. Aguardar inicialização
sleep 10

# 5. Testar API
curl http://localhost:8000/health
# Deve retornar: {"status":"healthy"}

curl http://localhost:8000/api/dashboard/metrics | jq '.qdrant.status'
# Deve retornar: "connected"

# 6. Abrir browser
xdg-open http://localhost:5173  # Linux
# ou
open http://localhost:5173      # macOS

# 7. Verificar que dashboard carrega
# 8. Clicar em todos os itens do menu
# 9. Voltar para Dashboard
# 10. Aguardar 30s e ver auto-refresh

# 11. Parar tudo
./stop-admin.sh
```

## Feedback

Se tudo funcionou: 🎉 **SUCESSO!**

Se algo não funcionou:
1. Anote o erro específico
2. Verifique os logs
3. Consulte o troubleshooting
4. Revise a documentação

---

**Boa sorte testando!** 🚀
