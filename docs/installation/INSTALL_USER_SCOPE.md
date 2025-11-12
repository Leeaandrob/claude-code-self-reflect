# Guia de Instalação: Claude Self-Reflect no Claude Code (User Scope)

## 📋 Pré-requisitos

✅ **Seu sistema já tem:**
- Claude CLI instalado: `/home/leeaandrob/.nvm/versions/node/v22.16.0/bin/claude`
- claude-self-reflect v7.0.0 instalado globalmente
- Docker containers rodando (Qdrant, MCP server, watcher)

❌ **Falta:**
- Registrar MCP server no Claude Code (scope user)
- Configurar Voyage AI API key

---

## 🚀 Instalação Completa

### Passo 1: Configurar Voyage AI

```bash
# Navegar para o diretório de instalação global
cd /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect

# Editar o arquivo .env
nano .env
# OU
vim .env
# OU
code .env
```

**Modificar estas linhas:**

```bash
# Mudar de true para false
PREFER_LOCAL_EMBEDDINGS=false

# Adicionar sua API key
VOYAGE_KEY=pa-aagTOt95oqx9uuqCoUURCmj8dbA8OEVfPf25QBVuUKC
```

**Resultado esperado do .env:**

```bash
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_PORT=6333
QDRANT_MEMORY=4g

# Embedding Configuration
PREFER_LOCAL_EMBEDDINGS=false  # ← MUDADO PARA FALSE

# Voyage AI Configuration
VOYAGE_KEY=pa-aagTOt95oqx9uuqCoUURCmj8dbA8OEVfPf25QBVuUKC  # ← SUA API KEY

# Memory Decay Configuration
ENABLE_MEMORY_DECAY=true
DECAY_WEIGHT=0.3
DECAY_SCALE_DAYS=90

# ... resto do arquivo ...
```

Salvar e fechar o arquivo (Ctrl+O, Enter, Ctrl+X no nano).

### Passo 2: Reiniciar Docker Containers

```bash
# Parar containers atuais
docker stop claude-reflection-safe-watcher claude-reflection-mcp claude-reflection-qdrant

# Remover containers antigos
docker rm claude-reflection-safe-watcher claude-reflection-mcp claude-reflection-qdrant

# Iniciar novamente com nova configuração
cd /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect
docker compose --profile safe-watch up -d
```

**Verificar que containers estão rodando:**

```bash
docker ps | grep claude-reflection
```

Você deve ver 3 containers:
- `claude-reflection-qdrant`
- `claude-reflection-mcp`
- `claude-reflection-safe-watcher`

### Passo 3: Registrar MCP Server no Claude Code (User Scope)

```bash
# Adicionar MCP server com scope user (disponível em todos os projetos)
claude mcp add \
  --scope user \
  --transport stdio \
  claude-self-reflect \
  /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect/mcp-server/run-mcp.sh
```

**Ou de forma mais simples:**

```bash
claude mcp add \
  claude-self-reflect \
  /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect/mcp-server/run-mcp.sh \
  -s user
```

**Mensagem esperada:**
```
✅ MCP server "claude-self-reflect" added successfully (user scope)
⚠️  Please restart Claude Code for changes to take effect.
```

### Passo 4: Verificar Configuração

```bash
# Listar MCP servers registrados
claude mcp list
```

**Saída esperada:**
```
claude-self-reflect (user)
  Transport: stdio
  Command: /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect/mcp-server/run-mcp.sh
  Scope: user
```

**Verificar arquivo de configuração:**

```bash
cat ~/.claude.json | grep -A 10 "claude-self-reflect"
```

### Passo 5: Reiniciar Claude Code

**IMPORTANTE**: Claude Code **DEVE** ser reiniciado para reconhecer o novo MCP server.

```bash
# Fechar todas as instâncias do Claude Code
pkill -f claude

# OU, se estiver rodando em terminal:
# Ctrl+C para parar o processo

# Aguardar 2-3 segundos

# Iniciar Claude Code novamente
claude
```

### Passo 6: Testar Funcionamento

**Dentro do Claude Code:**

```
> list available mcp tools

> what tools do I have access to?
```

Você deve ver os 20+ tools do claude-self-reflect:
- `mcp__claude-self-reflect__reflect_on_past`
- `mcp__claude-self-reflect__store_reflection`
- `mcp__claude-self-reflect__get_recent_work`
- `mcp__claude-self-reflect__search_by_file`
- etc.

**Testar busca:**

```
> Search my past conversations about Docker

> Store a reflection: "Today I learned how to configure Voyage AI embeddings with Claude Self-Reflect"

> What did I work on in the last 7 days?
```

### Passo 7: Verificar Voyage AI Está Funcionando

```bash
# Ver logs do MCP server
docker compose logs mcp-server | grep -i voyage
```

**Saída esperada:**
```
INFO Using VOYAGE embeddings (1024 dimensions)
INFO Voyage client initialized
```

**Verificar no Qdrant:**

Abrir no navegador: http://localhost:6333/dashboard

Você deve ver coleções com nomes terminando em `_cloud_1024d` (Voyage) ao invés de `_local_384d` (FastEmbed).

---

## 🔍 Troubleshooting

### Problema 1: MCP Tools Não Aparecem

**Sintoma**: Claude Code não mostra os tools do claude-self-reflect

**Soluções:**

1. **Verificar se MCP está registrado:**
   ```bash
   claude mcp list | grep claude-self-reflect
   ```

2. **Verificar caminho do script:**
   ```bash
   ls -la /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect/mcp-server/run-mcp.sh
   ```

3. **Reiniciar Claude Code completamente:**
   ```bash
   pkill -f claude
   # Aguardar 5 segundos
   claude
   ```

4. **Verificar logs do MCP:**
   ```bash
   tail -f ~/.claude-self-reflect/logs/mcp-server.log
   ```

### Problema 2: Voyage API Key Não Funciona

**Sintoma**: Logs mostram "Using local embeddings" ou erro de autenticação

**Soluções:**

1. **Verificar .env:**
   ```bash
   cat /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect/.env | grep VOYAGE
   ```

   Deve mostrar:
   ```
   PREFER_LOCAL_EMBEDDINGS=false
   VOYAGE_KEY=pa-aagTOt95oqx9uuqCoUURCmj8dbA8OEVfPf25QBVuUKC
   ```

2. **Reiniciar containers com nova configuração:**
   ```bash
   docker compose down
   docker compose --profile safe-watch up -d
   ```

3. **Testar API key manualmente:**
   ```bash
   docker compose exec mcp-server python -c "
   import os
   os.environ['VOYAGE_KEY'] = 'pa-aagTOt95oqx9uuqCoUURCmj8dbA8OEVfPf25QBVuUKC'
   import voyageai
   client = voyageai.Client()
   result = client.embed(['test'], model='voyage-3')
   print('✅ Voyage AI funcionando!', len(result.embeddings[0]), 'dimensions')
   "
   ```

### Problema 3: Containers Não Estão Rodando

**Sintoma**: `docker ps` não mostra containers claude-reflection

**Soluções:**

1. **Verificar se Docker está rodando:**
   ```bash
   docker info
   ```

2. **Verificar logs de erro:**
   ```bash
   cd /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect
   docker compose logs
   ```

3. **Rebuild containers:**
   ```bash
   docker compose down -v  # Remove volumes também
   docker compose build --no-cache
   docker compose --profile safe-watch up -d
   ```

### Problema 4: Permission Denied no Script

**Sintoma**: Erro "Permission denied" ao executar run-mcp.sh

**Solução:**
```bash
chmod +x /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect/mcp-server/run-mcp.sh
```

---

## 📊 Verificação Final de Sucesso

Execute todos estes comandos para confirmar instalação completa:

```bash
echo "=== 1. Claude CLI Instalado ==="
which claude

echo -e "\n=== 2. MCP Server Registrado ==="
claude mcp list | grep claude-self-reflect

echo -e "\n=== 3. Docker Containers Rodando ==="
docker ps | grep claude-reflection

echo -e "\n=== 4. Voyage AI Configurado ==="
cat /home/leeaandrob/.nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect/.env | grep -E "PREFER_LOCAL|VOYAGE_KEY"

echo -e "\n=== 5. Qdrant Acessível ==="
curl -s http://localhost:6333/collections | jq -r '.result.collections[].name' | grep claude-self-reflect

echo -e "\n=== 6. MCP Server Logs ==="
tail -5 ~/.claude-self-reflect/logs/mcp-server.log
```

**Resultado esperado:**
- ✅ Claude CLI path mostrado
- ✅ MCP server listado com scope "user"
- ✅ 3 containers rodando
- ✅ `PREFER_LOCAL_EMBEDDINGS=false` e `VOYAGE_KEY` configurado
- ✅ Coleções Qdrant com sufixo `_cloud_1024d`
- ✅ Logs sem erros

---

## 🎯 Testando no Claude Code

Depois de reiniciar o Claude Code, teste:

### Teste 1: Listar Tools
```
> What MCP tools do I have access to?
```

Deve listar 20+ tools do claude-self-reflect.

### Teste 2: Busca Básica
```
> Search my past conversations about Python
```

Deve retornar conversas relevantes (se você tiver histórico).

### Teste 3: Armazenar Reflexão
```
> Store a reflection: "Successfully configured Claude Self-Reflect with Voyage AI embeddings (1024d) for better search quality"
```

Deve confirmar que a reflexão foi armazenada.

### Teste 4: Trabalho Recente
```
> What did I work on in the last week?
```

Deve mostrar atividade agrupada por projeto.

### Teste 5: Busca por Arquivo
```
> Search conversations about server.py
```

Deve encontrar conversas que mencionaram esse arquivo.

---

## 📚 Recursos Adicionais

### Documentação
- **MCP Reference**: `docs/development/MCP_REFERENCE.md`
- **Architecture**: `docs/architecture/LLM_ARCHITECTURE.md`
- **Integration**: `docs/integration/CLAUDE_CODE_INTEGRATION_ANALYSIS.md`

### Comandos Úteis

```bash
# Ver status de indexação
docker compose exec mcp-server python /app/mcp-server/src/status.py

# Ver logs em tempo real
docker compose logs -f

# Reimportar conversas
docker compose run --rm importer

# Parar tudo
docker compose down

# Iniciar tudo
docker compose --profile safe-watch up -d
```

### Links

- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Voyage AI Dashboard**: https://dash.voyageai.com/
- **GitHub Issues**: https://github.com/ramakay/claude-self-reflect/issues

---

## 🎉 Próximos Passos

Agora que está instalado e configurado:

1. **Use naturalmente**: Apenas converse normalmente no Claude Code
2. **Conversas são indexadas automaticamente**: O watcher monitora `~/.claude/projects/`
3. **Busque quando precisar**: "How did we solve X?" ou "What did we discuss about Y?"
4. **Explore features avançadas**:
   - `search_by_concept("authentication")`
   - `search_by_file("docker-compose.yaml")`
   - `get_timeline(start_date, end_date)`

5. **(Opcional) Habilitar v7.0 Narratives**:
   ```bash
   # Adicionar ANTHROPIC_API_KEY ao .env
   # Iniciar batch automation
   docker compose --profile batch-automation up -d
   ```

---

**Instalação criada por**: Claude Code
**Data**: 2025-01-05
**Versão do projeto**: 7.0.0
**Scope**: user (disponível em todos os projetos)
