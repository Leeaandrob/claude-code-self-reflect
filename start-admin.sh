#!/bin/bash

# Script para iniciar o Admin Panel completo (usando uv e pnpm)

echo "🚀 Iniciando Claude Self-Reflect Admin Panel..."
echo ""

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verifica se uv está instalado
if ! command -v uv &> /dev/null; then
    echo -e "${RED}✗${NC} uv não encontrado. Instale com: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Verifica se pnpm está instalado
if ! command -v pnpm &> /dev/null; then
    echo -e "${RED}✗${NC} pnpm não encontrado. Instale com: curl -fsSL https://get.pnpm.io/install.sh | sh -"
    exit 1
fi

# Criar diretório de logs se não existir
mkdir -p logs

# Função para parar serviços existentes
stop_existing_services() {
    echo -e "${BLUE}[0/4]${NC} Verificando serviços em execução..."

    # Parar API se estiver rodando
    if [ -f "logs/api.pid" ]; then
        API_PID=$(cat logs/api.pid)
        if ps -p $API_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}→${NC} Parando API existente (PID: $API_PID)..."
            kill $API_PID 2>/dev/null
            sleep 1
            # Force kill se ainda estiver rodando
            if ps -p $API_PID > /dev/null 2>&1; then
                kill -9 $API_PID 2>/dev/null
            fi
            rm -f logs/api.pid logs/api.port
        fi
    fi

    # Parar Frontend se estiver rodando
    if [ -f "logs/frontend.pid" ]; then
        FRONTEND_PID=$(cat logs/frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}→${NC} Parando Frontend existente (PID: $FRONTEND_PID)..."
            kill $FRONTEND_PID 2>/dev/null
            sleep 1
            if ps -p $FRONTEND_PID > /dev/null 2>&1; then
                kill -9 $FRONTEND_PID 2>/dev/null
            fi
            rm -f logs/frontend.pid
        fi
    fi

    # Limpar processos órfãos
    pkill -f "uvicorn app.main" 2>/dev/null
    pkill -f "vite.*admin-panel" 2>/dev/null

    echo -e "${GREEN}✓${NC} Pronto para iniciar novos serviços"
    echo ""
}

# Parar serviços existentes primeiro
stop_existing_services

# Verifica se Qdrant está rodando
echo -e "${BLUE}[1/4]${NC} Verificando Qdrant..."
if ! docker compose ps qdrant | grep -q "Up"; then
    echo -e "${BLUE}→${NC} Iniciando Qdrant..."
    docker compose up -d qdrant
    sleep 3
else
    echo -e "${GREEN}✓${NC} Qdrant já está rodando"
fi

# Inicia API Backend com uv
echo ""
echo -e "${BLUE}[2/4]${NC} Iniciando Backend API (uv)..."
cd admin-api

# Sincroniza dependências com uv
echo -e "${BLUE}→${NC} Sincronizando dependências com uv..."
uv sync --quiet

# Limpar log antigo
> ../logs/api.log

echo -e "${BLUE}→${NC} Iniciando servidor FastAPI em background..."
nohup uv run python -m app.main > ../logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > ../logs/api.pid

# Aguardar API iniciar e detectar porta
echo -e "${BLUE}→${NC} Aguardando API inicializar..."
sleep 4

if ps -p $API_PID > /dev/null; then
    # Detectar porta usada pela API - pegar apenas números da última linha
    API_PORT=$(grep "Starting API server on" ../logs/api.log | tail -1 | sed -n 's/.*:\([0-9]\+\)$/\1/p')

    if [ -z "$API_PORT" ] || [ "$API_PORT" = "" ]; then
        API_PORT=8000
    fi

    echo $API_PORT > ../logs/api.port

    if [ "$API_PORT" != "8000" ]; then
        echo -e "${GREEN}✓${NC} API rodando (PID: $API_PID, Porta: $API_PORT - porta 8000 em uso)"
    else
        echo -e "${GREEN}✓${NC} API rodando (PID: $API_PID, Porta: $API_PORT)"
    fi
else
    echo -e "${RED}✗${NC} Falha ao iniciar API"
    cat ../logs/api.log | tail -20
    exit 1
fi

cd ..

# Inicia Frontend com pnpm
echo ""
echo -e "${BLUE}[3/4]${NC} Iniciando Frontend (pnpm)..."
cd admin-panel

# Instala dependências se necessário
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}→${NC} Instalando dependências com pnpm..."
    pnpm install
fi

# Gerar config.js com porta dinâmica da API
if [ -f "../logs/api.port" ]; then
    DETECTED_API_PORT=$(cat ../logs/api.port)
else
    DETECTED_API_PORT=8000
fi

echo -e "${BLUE}→${NC} Configurando API URL (porta $DETECTED_API_PORT)..."
cat > public/config.js << EOF
// Runtime configuration for API URL
// This file is generated dynamically by start-admin.sh
// Uses window.location.hostname to work with both localhost and network IPs
window.ADMIN_CONFIG = {
  API_URL: 'http://' + window.location.hostname + ':${DETECTED_API_PORT}/api'
}
EOF

# Limpar log antigo
> ../logs/frontend.log

echo -e "${BLUE}→${NC} Iniciando Vite dev server..."
pnpm dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../logs/frontend.pid

cd ..

# Aguarda inicialização
echo ""
echo -e "${BLUE}[4/4]${NC} Aguardando inicialização completa..."
sleep 3

# Verificar se frontend ainda está rodando
if ! ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${RED}✗${NC} Frontend falhou ao iniciar"
    cat logs/frontend.log | tail -20
    exit 1
fi

# Resumo
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Admin Panel iniciado com sucesso!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Ler porta da API do arquivo
if [ -f "logs/api.port" ]; then
    API_PORT=$(cat logs/api.port)
else
    API_PORT=8000
fi

echo "📊 Frontend:  http://localhost:5173"
echo "🔌 API:       http://localhost:$API_PORT"
echo "📚 API Docs:  http://localhost:$API_PORT/docs"
echo ""

if [ "$API_PORT" != "8000" ]; then
    echo -e "${BLUE}ℹ${NC} Nota: API usando porta $API_PORT (porta 8000 estava em uso)"
    echo ""
fi

echo "PIDs dos processos:"
echo "  • API:      $API_PID (logs/api.pid)"
echo "  • Frontend: $FRONTEND_PID (logs/frontend.pid)"
echo ""

echo "Gerenciadores:"
echo "  • Python:     uv (https://docs.astral.sh/uv/)"
echo "  • Frontend:   pnpm (https://pnpm.io/)"
echo ""
echo "Para parar os serviços:"
echo "  ./stop-admin.sh"
echo ""
echo "Logs em tempo real:"
echo "  API:      tail -f logs/api.log"
echo "  Frontend: tail -f logs/frontend.log"
echo ""
