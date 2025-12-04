# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Self-Reflect is an MCP (Model Context Protocol) server that gives Claude perfect memory of all conversations through semantic search over vector embeddings. It's distributed as an npm package that installs a Python-based MCP server with Docker services.

**Key Architecture:**
- **MCP Server**: Python (FastMCP) at `mcp-server/src/server.py`
- **Vector DB**: Qdrant (Docker) for semantic search
- **Embeddings**: Cloud only - Qwen/DashScope (2048d) or Voyage AI (1024d)
- **State Management**: Unified state file at `~/.claude-self-reflect/config/unified-state.json`
- **Distribution**: npm package with Python backend

## Build & Test Commands

### Development Setup
```bash
# Install Python dependencies (MCP server)
cd mcp-server
pip install -e .

# Install Node dependencies (installer/CLI)
npm install

# Start required services
docker compose up -d qdrant

# Test MCP server locally
cd mcp-server
python -m src.server
```

### Testing
```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test suites
pytest tests/test_unified_state.py -v
pytest tests/test_memory_decay.py -v
pytest tests/integration/ -v

# Test npm package build (CRITICAL before release)
npm pack --dry-run
node tests/test_npm_package_contents.py

# Test Docker builds
docker compose build --no-cache
docker compose --profile safe-watch up -d
```

### Quality Gates
```bash
# Pre-commit quality gate (runs automatically)
python scripts/quality-gate-staged.py

# AST-GREP pattern analysis
python scripts/quality/ast_grep_final_analyzer.py

# Security scanning
python scripts/checks/check-pcre2-vulnerability.sh
```

## Architecture Deep Dive

### MCP Server Architecture (mcp-server/src/)
```
server.py
├── FastMCP initialization with tools
├── Cloud embedding manager (Qwen/Voyage)
├── Connection pooling with circuit breaker
└── Modular tool registration:
    ├── search_tools.py - reflect_on_past, quick_search
    ├── temporal_tools.py - get_recent_work, get_timeline
    └── reflection_tools.py - store_reflection, get_full_conversation
```

**Critical Design Patterns:**
- **Lazy Initialization**: Embeddings loaded on first use to avoid startup delays
- **Circuit Breaker**: Automatic failover for Qdrant connection issues
- **Async Throughout**: Full asyncio implementation
- **Unified State**: Single JSON file for all import tracking

### State Management
Single unified-state.json with atomic operations:

```python
{
  "files": {
    "file_path_hash": {
      "path": "/full/path/to/file.jsonl",
      "hash": "sha256...",
      "imported_at": "2025-01-05T...",
      "project": "project-name",
      "message_count": 42
    }
  },
  "projects": {
    "project-name": {
      "file_count": 10,
      "message_count": 420,
      "last_updated": "2025-01-05T..."
    }
  }
}
```

### Collection Naming Convention
Collections use prefixed naming based on embedding provider:
- Qwen mode: `conv_{project_hash}_qwen_1024d` or `conv_{project_hash}_qwen_2048d`
- Voyage mode: `conv_{project_hash}_voyage_1024d`

### Import Pipeline Architecture
```
HOT/WARM/COLD Prioritization:
├── HOT (< 5 min): 2-second intervals
├── WARM (< 24 hrs): Normal priority, starvation prevention
└── COLD (> 24 hrs): Batch processed
```

**Services:**
- `streaming-watcher.py` - File system monitoring with intelligent priority queues

## Critical File Locations

### Configuration
- `.env` / `.env.template` - Environment configuration
- `docker-compose.yaml` - Service orchestration
- `mcp-server/pyproject.toml` - Python dependencies
- `package.json` - npm package manifest

### State & Data
- `~/.claude/projects/*/` - Source JSONL conversation files
- `~/.claude-self-reflect/config/unified-state.json` - Import state
- `~/.claude-self-reflect/logs/mcp-server.log` - MCP server logs

### Key Scripts
- `scripts/quality-gate-staged.py` - Pre-commit quality checks
- `installer/cli.js` - User-facing CLI (`claude-self-reflect setup`)

### Testing
- `tests/run_all_tests.py` - Master test runner
- `tests/test_unified_state.py` - State management tests
- `tests/integration/` - End-to-end integration tests

## Docker Services

### Active Services (3)
| Service | Dockerfile | Profile | Purpose |
|---------|------------|---------|---------|
| **qdrant** | (image) | default | Vector database |
| **safe-watcher** | Dockerfile.safe-watcher | safe-watch | Continuous import (**RECOMMENDED**) |
| **mcp-server** | Dockerfile.mcp-server | mcp | MCP server via Docker |

### Starting Services
```bash
# Start Qdrant (always needed)
docker compose up -d qdrant

# Start continuous import
docker compose --profile safe-watch up -d

# Check running services
docker compose ps
docker compose logs -f
```

## Common Development Patterns

### Adding a New MCP Tool
1. Create tool in appropriate file (`search_tools.py`, `temporal_tools.py`, etc.)
2. Define Pydantic model for parameters
3. Register with `@mcp.tool()` decorator
4. Add to tool registry in `server.py`
5. Restart Claude Code entirely (CRITICAL - MCP servers cache)

### Embedding Configuration
Cloud embeddings only - set one of these environment variables:
- `DASHSCOPE_API_KEY` - For Qwen/DashScope (2048d)
- `VOYAGE_KEY` - For Voyage AI (1024d)

### Working with Unified State
```python
from src.runtime.unified_state_manager import UnifiedStateManager

async with UnifiedStateManager() as state:
    await state.mark_imported(file_path, hash_value, project, message_count)
    is_imported = await state.is_imported(file_path, hash_value)
    stats = await state.get_import_stats()
```

## Security Considerations

1. **Quality Gates**: NEVER bypass with `--no-verify`
2. **Subprocess Safety**: Always use list form, never `shell=True` with user input
3. **Secrets**: Use environment variables, never commit keys
4. **Docker Security**: Run as non-root user (UID 1001)
5. **Path Validation**: Always normalize and validate file paths

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Status check | < 10ms | 6ms |
| Search latency | < 5ms | 3ms |
| Import speed | > 50/sec | 100/sec |
| Memory usage | < 100MB | 50MB |

## Troubleshooting Checklist

1. **MCP tools not working**: Restart Claude Code entirely (not just reload)
2. **Import showing 0%**: Test with MCP tools - if search works, ignore the 0%
3. **Collection not found**: Check collection naming matches embedding provider
4. **Embedding errors**: Check `~/.claude-self-reflect/logs/mcp-server.log`
5. **Docker issues**: Check `docker compose logs` for specific service

## Environment Variables

### Required (one of)
- `DASHSCOPE_API_KEY` - Qwen/DashScope API key
- `VOYAGE_KEY` - Voyage AI API key

### Optional
- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)
- `EMBEDDING_PROVIDER` - cloud (default)
- `ENABLE_MEMORY_DECAY` - Enable time-based decay (default: false)
- `DECAY_WEIGHT` - Decay factor (default: 0.3)
- `DECAY_SCALE_DAYS` - Decay scale in days (default: 90)
