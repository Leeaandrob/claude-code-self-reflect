# Claude Self-Reflect Worker Agent

A Docker-based agent that runs on each machine where Claude Self-Reflect is installed. It monitors local services, reports status to the central admin panel, and allows remote control of Docker services.

## Features

- **Heartbeat Reporting**: Sends status updates to the central admin API every 30 seconds
- **Service Monitoring**: Tracks Docker containers (Qdrant, MCP server, watcher)
- **Remote Control**: HTTP API for starting/stopping/restarting services remotely
- **System Metrics**: Reports CPU, memory, disk usage
- **Qdrant Stats**: Reports vector count and collection status
- **Import Progress**: Reports file import status from unified-state.json

## Quick Install

One-line installation on any machine with Docker:

```bash
curl -sSL https://raw.githubusercontent.com/your-repo/worker-agent/install.sh | \
  bash -s -- --admin-url http://your-admin-server:8000/api --dashscope-key YOUR_KEY
```

Or manually:

```bash
# Clone or download the worker-agent directory
cd worker-agent

# Create .env file
cat > .env << EOF
ADMIN_API_URL=http://your-admin-server:8000/api
DASHSCOPE_API_KEY=your-key
# or VOYAGE_KEY=your-key
CLAUDE_LOGS_PATH=$HOME/.claude/projects
EOF

# Start all services
docker compose up -d
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Worker Machine                             │
│                                                               │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │  Worker Agent   │───▶│    Qdrant       │                  │
│  │  (port 8081)    │    │  (port 6333)    │                  │
│  └────────┬────────┘    └─────────────────┘                  │
│           │                     ▲                             │
│           │                     │                             │
│           ▼                     │                             │
│  ┌─────────────────┐    ┌───────┴─────────┐                  │
│  │  Docker Socket  │    │  Safe Watcher   │                  │
│  │  (monitoring)   │    │  (imports)      │                  │
│  └─────────────────┘    └─────────────────┘                  │
│                                                               │
└───────────────────────────┬───────────────────────────────────┘
                            │ Heartbeats (every 30s)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                   Admin Server                                │
│                                                               │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │  Admin API      │───▶│  Admin Panel    │                  │
│  │  (port 8000)    │    │  (port 3000)    │                  │
│  └─────────────────┘    └─────────────────┘                  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Services

The worker stack includes:

| Service | Description | Port |
|---------|-------------|------|
| **worker-agent** | Agent that monitors and reports status | 8081 |
| **qdrant** | Vector database for semantic search | 6333 |
| **safe-watcher** | Continuous import service | - |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_API_URL` | `http://localhost:8000/api` | Central admin API URL |
| `HEARTBEAT_INTERVAL` | `30` | Seconds between heartbeats |
| `AGENT_PORT` | `8081` | Local agent API port |
| `QDRANT_PORT` | `6333` | Qdrant database port |
| `QDRANT_MEMORY` | `4g` | Qdrant memory limit |
| `CLAUDE_LOGS_PATH` | `~/.claude/projects` | Path to Claude conversation logs |
| `VOYAGE_KEY` | - | Voyage AI API key |
| `DASHSCOPE_API_KEY` | - | DashScope API key |

### Agent API Endpoints

The worker agent exposes a local HTTP API on port 8081:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Full agent status |
| `/services` | GET | List Docker services |
| `/services/{name}/start` | POST | Start a service |
| `/services/{name}/stop` | POST | Stop a service |
| `/services/{name}/restart` | POST | Restart a service |
| `/services/{name}/logs` | GET | Get service logs |

Example:

```bash
# Check agent health
curl http://localhost:8081/health

# Get full status
curl http://localhost:8081/status

# Restart Qdrant
curl -X POST http://localhost:8081/services/claude-reflect-qdrant/restart
```

## Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps

# Stop all services
docker compose down

# Update to latest version
docker compose pull
docker compose up -d
```

## Systemd Service (Optional)

The installer can create a systemd service for automatic startup:

```bash
# Check service status
systemctl status claude-reflect-worker

# Start/stop
systemctl start claude-reflect-worker
systemctl stop claude-reflect-worker

# Enable on boot
systemctl enable claude-reflect-worker
```

## Troubleshooting

### Agent not appearing in admin panel

1. Check if agent is running:
   ```bash
   docker compose ps
   curl http://localhost:8081/health
   ```

2. Check network connectivity to admin API:
   ```bash
   curl http://your-admin-server:8000/api/health
   ```

3. Check agent logs:
   ```bash
   docker compose logs worker-agent
   ```

### Docker socket permission denied

The agent container needs access to the Docker socket. Make sure:
- The socket is mounted: `-v /var/run/docker.sock:/var/run/docker.sock:ro`
- The user has permission to access Docker

### Qdrant not connecting

Check if Qdrant is running and healthy:
```bash
curl http://localhost:6333/collections
```

## Security Notes

- The agent mounts the Docker socket read-only for monitoring
- The agent API (port 8081) should be firewalled in production
- Use a VPN or private network between workers and admin server
- API keys are stored in the .env file - keep it secure
