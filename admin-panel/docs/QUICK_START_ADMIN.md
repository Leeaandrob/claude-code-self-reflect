# 🚀 Quick Start - Admin Panel (uv + pnpm)

## Pré-requisitos

### Instalar uv (Python)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Instalar pnpm (Node.js)
```bash
curl -fsSL https://get.pnpm.io/install.sh | sh -
# ou
npm install -g pnpm
```

### Outros
- Docker (para Qdrant)
- Claude Self-Reflect já instalado

---

## Método 1: Script Automático ⚡ (Recomendado)

```bash
# Inicia tudo automaticamente
./start-admin.sh

# Acesse: http://localhost:5173
```

O script faz tudo para você:
1. ✅ Verifica se uv e pnpm estão instalados
2. ✅ Inicia Qdrant se necessário
3. ✅ Sincroniza dependências Python com uv
4. ✅ Inicia API em background
5. ✅ Instala dependências frontend com pnpm
6. ✅ Inicia Vite dev server

---

## Método 2: Manual

### Passo 1: Backend (uv)

```bash
cd admin-api

# Sincronizar dependências (cria .venv automaticamente)
uv sync

# Iniciar servidor
uv run python -m app.main
```

A API estará em: **http://localhost:8000**

### Passo 2: Frontend (pnpm)

Em outro terminal:

```bash
cd admin-panel

# Instalar dependências
pnpm install

# Iniciar dev server
pnpm dev
```

O painel estará em: **http://localhost:5173**

### Passo 3: Qdrant

Certifique-se que está rodando:

```bash
docker compose up -d qdrant
```

---

## Parar os Serviços

```bash
./stop-admin.sh
```

Ou manualmente: `Ctrl+C` nos terminais

---

## ✅ Verificação

Após iniciar, você deve ver:

### Dashboard (http://localhost:5173)
- ✅ 4 cards de métricas
- ✅ Qdrant Status (verde = conectado)
- ✅ Top 5 projetos
- ✅ Atividade recente
- ✅ Auto-refresh a cada 30s

### API Docs (http://localhost:8000/docs)
- ✅ Swagger UI interativo
- ✅ 8 grupos de endpoints
- ✅ Teste direto na interface

---

## 🔧 Comandos Úteis

### Backend (uv)
```bash
# Adicionar dependência
uv add fastapi

# Adicionar dev dependency
uv add --dev pytest

# Rodar comando
uv run python -m pytest

# Ver dependências
uv pip list
```

### Frontend (pnpm)
```bash
# Adicionar dependência
pnpm add react-query

# Adicionar dev dependency
pnpm add -D vitest

# Rodar script
pnpm build
pnpm preview

# Ver dependências
pnpm list
```

---

## 🐛 Troubleshooting

### "uv: command not found"
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # ou ~/.zshrc
```

### "pnpm: command not found"
```bash
npm install -g pnpm
# ou
curl -fsSL https://get.pnpm.io/install.sh | sh -
```

### API não inicia
```bash
cd admin-api
uv sync  # Resincronizar dependências
uv run python -m app.main
```

### Frontend não carrega
```bash
cd admin-panel
rm -rf node_modules pnpm-lock.yaml
pnpm install
pnpm dev
```

### Qdrant não conecta
```bash
docker compose ps qdrant
# Se não estiver "Up":
docker compose up -d qdrant
```

---

## 📊 Próximos Passos

1. ✅ Explore o Dashboard
2. ✅ Teste a API em `/docs`
3. ✅ Veja seus projetos
4. ✅ Monitore importações
5. ✅ Configure embeddings

---

## 🎯 Por que uv e pnpm?

### uv (Python)
- ⚡ **10-100x mais rápido** que pip
- 🔒 **Lockfile nativo** (uv.lock)
- 📦 **Gestão de ambientes virtuais** automática
- 🎯 **Resolução de dependências** deterministíca
- 💾 **Cache global** compartilhado

### pnpm (Node.js)
- ⚡ **3x mais rápido** que npm
- 💾 **Economia de espaço** (hard links)
- 🔒 **Lockfile confiável** (pnpm-lock.yaml)
- 🎯 **Isolamento estrito** de dependências
- 📦 **Monorepo nativo**

---

**Desenvolvido para Claude Self-Reflect v7.0.0**
*Admin Panel v1.0.0 - Powered by uv & pnpm*
