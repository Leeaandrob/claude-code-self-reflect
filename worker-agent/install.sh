#!/bin/bash
#
# Claude Self-Reflect Worker Agent Installation Script
#
# This script installs the worker agent as a system service that:
# - Monitors and manages local Claude Self-Reflect Docker services
# - Reports status to a central admin panel
# - Allows remote control of services
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/your-repo/worker-agent/install.sh | bash
#
# Or with custom options:
#   ./install.sh --admin-url http://admin-server:8000/api --api-key your-key
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
INSTALL_DIR="/opt/claude-self-reflect"
ADMIN_API_URL="${ADMIN_API_URL:-}"
VOYAGE_KEY="${VOYAGE_KEY:-}"
DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-}"
CLAUDE_LOGS_PATH="${CLAUDE_LOGS_PATH:-$HOME/.claude/projects}"
HEARTBEAT_INTERVAL="${HEARTBEAT_INTERVAL:-30}"
AGENT_PORT="${AGENT_PORT:-8081}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --admin-url)
            ADMIN_API_URL="$2"
            shift 2
            ;;
        --voyage-key)
            VOYAGE_KEY="$2"
            shift 2
            ;;
        --dashscope-key)
            DASHSCOPE_API_KEY="$2"
            shift 2
            ;;
        --logs-path)
            CLAUDE_LOGS_PATH="$2"
            shift 2
            ;;
        --interval)
            HEARTBEAT_INTERVAL="$2"
            shift 2
            ;;
        --port)
            AGENT_PORT="$2"
            shift 2
            ;;
        --help)
            echo "Claude Self-Reflect Worker Agent Installer"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --admin-url URL       Admin API URL (required)"
            echo "  --voyage-key KEY      Voyage AI API key"
            echo "  --dashscope-key KEY   DashScope API key"
            echo "  --logs-path PATH      Claude logs path (default: ~/.claude/projects)"
            echo "  --interval SECONDS    Heartbeat interval (default: 30)"
            echo "  --port PORT           Agent API port (default: 8081)"
            echo "  --help                Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Claude Self-Reflect Worker Agent Installer             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${YELLOW}Warning: Running without root. Some features may not work.${NC}"
    INSTALL_DIR="$HOME/.claude-self-reflect/worker-agent"
fi

# Check requirements
echo -e "${BLUE}Checking requirements...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker found${NC}"

# Check Docker socket access
if ! docker ps &> /dev/null; then
    echo -e "${RED}Error: Cannot access Docker. Please add your user to the docker group:${NC}"
    echo "  sudo usermod -aG docker $USER"
    echo "Then log out and back in."
    exit 1
fi

echo -e "${GREEN}✓ Docker access OK${NC}"

# Prompt for admin URL if not provided
if [[ -z "$ADMIN_API_URL" ]]; then
    echo ""
    echo -e "${YELLOW}Enter the Admin API URL (e.g., http://admin-server:8000/api):${NC}"
    read -r ADMIN_API_URL

    if [[ -z "$ADMIN_API_URL" ]]; then
        echo -e "${RED}Admin API URL is required.${NC}"
        exit 1
    fi
fi

# Check API key
if [[ -z "$VOYAGE_KEY" ]] && [[ -z "$DASHSCOPE_API_KEY" ]]; then
    echo ""
    echo -e "${YELLOW}No embedding API key provided.${NC}"
    echo "Enter DASHSCOPE_API_KEY (or press Enter to skip):"
    read -r DASHSCOPE_API_KEY

    if [[ -z "$DASHSCOPE_API_KEY" ]]; then
        echo "Enter VOYAGE_KEY (or press Enter to skip):"
        read -r VOYAGE_KEY
    fi
fi

# Create installation directory
echo ""
echo -e "${BLUE}Creating installation directory: $INSTALL_DIR${NC}"
mkdir -p "$INSTALL_DIR"

# Download files
echo -e "${BLUE}Downloading worker agent files...${NC}"

cd "$INSTALL_DIR"

# Create docker-compose.yaml
cat > docker-compose.yaml << 'COMPOSE_EOF'
volumes:
  qdrant_data:
  config_data:

services:
  worker-agent:
    image: ghcr.io/leeaandrob/claude-self-reflect-worker:latest
    container_name: claude-reflect-worker-agent
    restart: unless-stopped
    depends_on:
      - qdrant
    ports:
      - "${AGENT_PORT:-8081}:8081"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - config_data:/config:ro
      - ${CLAUDE_LOGS_PATH}:/logs:ro
      - /etc/localtime:/etc/localtime:ro
    environment:
      - ADMIN_API_URL=${ADMIN_API_URL}
      - HEARTBEAT_INTERVAL=${HEARTBEAT_INTERVAL:-30}
      - QDRANT_URL=http://qdrant:6333
      - STATE_FILE=/config/unified-state.json
      - LOGS_DIR=/logs
      - AGENT_PORT=8081
      - VOYAGE_KEY=${VOYAGE_KEY:-}
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY:-}
    command: >
      --api-url ${ADMIN_API_URL}
      --qdrant-url http://qdrant:6333
      --state-file /config/unified-state.json
      --local-port 8081
      --interval ${HEARTBEAT_INTERVAL:-30}

  qdrant:
    image: qdrant/qdrant:v1.15.1
    container_name: claude-reflect-qdrant
    restart: unless-stopped
    ports:
      - "${QDRANT_PORT:-6333}:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO
    mem_limit: ${QDRANT_MEMORY:-4g}

  safe-watcher:
    image: ghcr.io/leeaandrob/claude-self-reflect-watcher:latest
    container_name: claude-reflect-watcher
    restart: unless-stopped
    depends_on:
      - qdrant
    volumes:
      - ${CLAUDE_LOGS_PATH}:/logs:ro
      - config_data:/config
    environment:
      - QDRANT_URL=http://qdrant:6333
      - STATE_FILE=/config/unified-state.json
      - LOGS_DIR=/logs
      - VOYAGE_KEY=${VOYAGE_KEY:-}
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY:-}
      - EMBEDDING_PROVIDER=cloud
      - PYTHONUNBUFFERED=1
    mem_limit: 2g

networks:
  default:
    name: claude-reflect-worker-network
COMPOSE_EOF

# Create .env file
cat > .env << ENV_EOF
# Claude Self-Reflect Worker Configuration
ADMIN_API_URL=${ADMIN_API_URL}
HEARTBEAT_INTERVAL=${HEARTBEAT_INTERVAL}
AGENT_PORT=${AGENT_PORT}
CLAUDE_LOGS_PATH=${CLAUDE_LOGS_PATH}

# Embedding API Keys (at least one required)
VOYAGE_KEY=${VOYAGE_KEY}
DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}

# Resource limits
QDRANT_MEMORY=4g
QDRANT_PORT=6333
ENV_EOF

echo -e "${GREEN}✓ Configuration created${NC}"

# Create systemd service (if running as root)
if [[ $EUID -eq 0 ]]; then
    echo -e "${BLUE}Creating systemd service...${NC}"

    cat > /etc/systemd/system/claude-reflect-worker.service << SERVICE_EOF
[Unit]
Description=Claude Self-Reflect Worker Agent
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    systemctl daemon-reload
    systemctl enable claude-reflect-worker.service
    echo -e "${GREEN}✓ Systemd service installed${NC}"
fi

# Start services
echo ""
echo -e "${BLUE}Starting services...${NC}"
docker compose pull 2>/dev/null || true
docker compose up -d

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Installation Complete!                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Installation directory: ${BLUE}${INSTALL_DIR}${NC}"
echo -e "Admin API URL: ${BLUE}${ADMIN_API_URL}${NC}"
echo -e "Agent API port: ${BLUE}${AGENT_PORT}${NC}"
echo ""
echo -e "${YELLOW}Commands:${NC}"
echo "  cd ${INSTALL_DIR}"
echo "  docker compose ps          # Check status"
echo "  docker compose logs -f     # View logs"
echo "  docker compose restart     # Restart services"
echo "  docker compose down        # Stop services"
echo ""

if [[ $EUID -eq 0 ]]; then
    echo -e "${YELLOW}Systemd commands:${NC}"
    echo "  systemctl status claude-reflect-worker"
    echo "  systemctl restart claude-reflect-worker"
    echo ""
fi

echo -e "${GREEN}The worker should now appear in your admin panel!${NC}"
