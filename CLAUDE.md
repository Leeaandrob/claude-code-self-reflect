# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Self-Reflect is an MCP (Model Context Protocol) server that gives Claude perfect memory of all conversations through semantic search over vector embeddings. It's distributed as an npm package that installs a Python-based MCP server with Docker services.

**Key Architecture:**
- **MCP Server**: Python (FastMCP) at `mcp-server/src/server.py`
- **Vector DB**: Qdrant (Docker) for semantic search
- **Embeddings**: Local (FastEmbed 384d) or Cloud (Voyage 1024d)
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
docker compose --profile import up --abort-on-container-exit
```

### Quality Gates
```bash
# Pre-commit quality gate (runs automatically)
python scripts/quality-gate-staged.py

# AST-GREP pattern analysis
python scripts/quality/ast_grep_final_analyzer.py

# CodeRabbit review (use before PRs)
coderabbit --prompt-only

# Security scanning
python scripts/checks/check-pcre2-vulnerability.sh
```

### Release Process
```bash
# 1. Update version in package.json and mcp-server/pyproject.toml
# 2. Run quality gates
python scripts/quality-gate-staged.py
coderabbit --prompt-only

# 3. Test package build
npm pack --dry-run
node tests/test_npm_package_contents.py

# 4. Commit and push
git commit -am "chore: bump version to X.Y.Z"
git push

# 5. Create GitHub release (triggers npm publish via CI)
gh release create vX.Y.Z --title "vX.Y.Z - Description" --notes "Release notes"

# 6. Verify npm publication
npm view claude-self-reflect@latest version
```

## Architecture Deep Dive

### MCP Server Architecture (mcp-server/src/)
```
server.py (728 lines)
├── FastMCP initialization with 20+ tools
├── Lazy embedding manager (local/cloud switchable)
├── Connection pooling with circuit breaker
└── Modular tool registration:
    ├── search_tools.py - reflect_on_past, quick_search
    ├── temporal_tools.py - get_recent_work, get_timeline
    ├── reflection_tools.py - store_reflection, get_full_conversation
    └── mode_switch_tool.py - Runtime embedding mode switching
```

**Critical Design Patterns:**
- **Lazy Initialization**: Embeddings loaded on first use to avoid startup delays
- **Circuit Breaker**: Automatic failover for Qdrant connection issues
- **Async Throughout**: Full asyncio implementation (v4.0+)
- **Unified State**: Single JSON file for all import tracking (v5.0+)

### State Management (v5.0)
**Before v5.0**: Multiple JSON files (imported-files.json, project-files.json, etc.)
**After v5.0**: Single unified-state.json with atomic operations

```python
# Unified state structure
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

**Benefits**: 50% faster status checks, zero race conditions, automatic deduplication

### Collection Naming Convention (v4.0+)
Collections use prefixed naming to support mode switching:
- Local mode: `csr_{project}_local_384d`
- Cloud mode: `csr_{project}_cloud_1024d`

**CRITICAL**: Collections are NOT cross-compatible between modes due to different embedding dimensions.

### Import Pipeline Architecture
```
HOT/WARM/COLD Prioritization:
├── HOT (< 5 min): 2-second intervals
├── WARM (< 24 hrs): Normal priority, starvation prevention
└── COLD (> 24 hrs): Batch processed
```

**Services:**
- `streaming-watcher.py` - File system monitoring with intelligent priority queues
- `streaming-importer.py` - High-throughput async import (100 files/sec)
- `batch_watcher.py` - v7.0 AI narrative generation trigger
- `batch_monitor.py` - Anthropic Batch API polling

### v7.0 AI Narratives
Transforms raw conversation excerpts into rich problem-solution summaries:

```python
# Before: Raw excerpts (0.074 relevance score)
"User: Fix Docker issue\nAssistant: Container limited to 2GB..."

# After: AI narrative (0.691 relevance score - 9.3x improvement)
"""
PROBLEM: Docker memory investigation...
SOLUTION: Implemented resource constraints...
TOOLS: Docker, grep, Edit
CONCEPTS: container-memory, resource-limits
FILES: docker-compose.yaml
"""
```

**Implementation:**
- `docs/design/batch_import_all_projects.py` - Batch job creator
- `src/runtime/batch_watcher.py` - Auto-triggers when 10+ conversations
- `src/runtime/batch_monitor.py` - Polls Anthropic API for results
- Docker profile: `batch-automation` (requires ANTHROPIC_API_KEY)

## Critical File Locations

### Configuration
- `.env` / `.env.template` - Environment configuration
- `docker-compose.yaml` - Service orchestration (8 profiles)
- `mcp-server/pyproject.toml` - Python dependencies
- `package.json` - npm package manifest

### State & Data
- `~/.claude/projects/*/` - Source JSONL conversation files
- `~/.claude-self-reflect/config/unified-state.json` - Import state (v5.0+)
- `~/.claude-self-reflect/batch_queue/` - v7.0 batch job queue
- `~/.claude-self-reflect/logs/mcp-server.log` - MCP server logs

### Key Scripts
- `scripts/migrate-to-unified-state.py` - v5.0 migration
- `scripts/quality-gate-staged.py` - Pre-commit quality checks
- `scripts/unified_state_manager.py` - State management API
- `installer/cli.js` - User-facing CLI (`claude-self-reflect setup`)

### Testing
- `tests/run_all_tests.py` - Master test runner
- `tests/test_unified_state.py` - State management tests
- `tests/test_npm_package_contents.py` - Package validation
- `tests/integration/` - End-to-end integration tests

## Common Development Patterns

### Adding a New MCP Tool
1. Create tool in appropriate file (`search_tools.py`, `temporal_tools.py`, etc.)
2. Define Pydantic model for parameters
3. Register with `@mcp.tool()` decorator
4. Add to tool registry in `server.py`
5. Test with `mcp-server/src/status.py`
6. Restart Claude Code entirely (CRITICAL - MCP servers cache)

### Modifying Embedding Logic
```python
# Embeddings are managed by embedding_manager.py
# Supports runtime mode switching (no restart needed)

# To switch modes:
switch_embedding_mode(mode="local")   # 384d FastEmbed
switch_embedding_mode(mode="cloud")   # 1024d Voyage
```

**CRITICAL**: Changing modes requires rebuilding collections (different dimensions).

### Updating Quality Gates
When quality gate blocks commits with false positives:

```python
# Edit scripts/quality-gate-staged.py
CRITICAL_PATTERNS = {
    # Make pattern more specific:
    # Before: r'subprocess.run\('
    # After: r'subprocess.run\([^,]*,\s*shell=True'
}

# Test the fix
python scripts/quality-gate-staged.py

# NEVER use --no-verify to bypass
```

### Working with Unified State
```python
from src.runtime.unified_state_manager import UnifiedStateManager

async with UnifiedStateManager() as state:
    # All operations are atomic with file locking
    await state.mark_imported(file_path, hash_value, project, message_count)
    is_imported = await state.is_imported(file_path, hash_value)
    stats = await state.get_import_stats()
```

## Docker Profiles

The docker-compose.yaml defines 8 profiles:
- `import` - One-time import
- `watch` - DEPRECATED (use safe-watch)
- `safe-watch` - Production file watcher
- `async` - Async importer (performance testing)
- `mcp` - MCP server via Docker
- `batch-automation` - v7.0 AI narratives (requires ANTHROPIC_API_KEY)

```bash
# Start services with specific profile
docker compose --profile safe-watch up -d
docker compose --profile batch-automation up -d

# Check running services
docker compose ps
docker compose logs -f
```

## Breaking Changes & Migration

### v3.x → v4.0
- Collection naming changed (add `csr_` prefix + dimension suffix)
- SHA-256 + UUID for conversation IDs (was MD5)
- Qdrant authentication required
- Run: `python scripts/migrate-collections.py`

### v4.x → v5.0
- Unified state file (was multiple JSON files)
- Atomic operations with file locking
- Run: `python scripts/migrate-to-unified-state.py`

### v6.x → v7.0
- AI-powered narratives (opt-in, requires ANTHROPIC_API_KEY)
- Batch automation services
- No migration needed (backward compatible)

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
3. **Collection not found**: Check collection naming matches mode (local vs cloud)
4. **Embedding errors**: Check `~/.claude-self-reflect/logs/mcp-server.log`
5. **Docker issues**: Check `docker compose logs` for specific service

## Additional Resources

- **MCP Reference**: `docs/development/MCP_REFERENCE.md`
- **Architecture Details**: `docs/architecture/`
- **Release History**: `CHANGELOG.md`
- **Security**: `SECURITY.md`
- **Contributing**: `CONTRIBUTING.md`
