#!/bin/bash

# Script para parar o Admin Panel

echo "🛑 Parando Claude Self-Reflect Admin Panel..."
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

STOPPED_SOMETHING=false

# Para Frontend
if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}→${NC} Parando Frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
        sleep 1
        # Force kill se necessário
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            kill -9 $FRONTEND_PID 2>/dev/null
        fi
        echo -e "${GREEN}✓${NC} Frontend parado"
        STOPPED_SOMETHING=true
    fi
    rm -f logs/frontend.pid
fi

# Para API
if [ -f "logs/api.pid" ]; then
    API_PID=$(cat logs/api.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}→${NC} Parando API (PID: $API_PID)..."
        kill $API_PID 2>/dev/null
        sleep 1
        # Force kill se necessário
        if ps -p $API_PID > /dev/null 2>&1; then
            kill -9 $API_PID 2>/dev/null
        fi
        echo -e "${GREEN}✓${NC} API parada"
        STOPPED_SOMETHING=true
    fi
    rm -f logs/api.pid logs/api.port
fi

# Limpar processos órfãos
echo -e "${YELLOW}→${NC} Verificando processos órfãos..."

# API
if pkill -f "uvicorn app.main" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Processos uvicorn órfãos removidos"
    STOPPED_SOMETHING=true
fi

# Frontend
if pkill -f "vite.*admin-panel" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Processos Vite órfãos removidos"
    STOPPED_SOMETHING=true
fi

echo ""

if [ "$STOPPED_SOMETHING" = true ]; then
    echo -e "${GREEN}✓ Admin Panel parado com sucesso!${NC}"
else
    echo -e "${YELLOW}ℹ Nenhum serviço estava rodando${NC}"
fi

echo ""
