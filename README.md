# Claude Self-Reflect
<div align="center">
<img src="https://repobeats.axiom.co/api/embed/e45aa7276c6b2d1fbc46a9a3324e2231718787bb.svg" alt="Repobeats analytics image" />
</div>
<div align="center">

[![npm version](https://badge.fury.io/js/claude-self-reflect.svg)](https://www.npmjs.com/package/claude-self-reflect)
[![npm downloads](https://img.shields.io/npm/dm/claude-self-reflect.svg)](https://www.npmjs.com/package/claude-self-reflect)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-6B4FBB)](https://github.com/anthropics/claude-code)
[![MCP Protocol](https://img.shields.io/badge/MCP-Enabled-FF6B6B)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

[![GitHub stars](https://img.shields.io/github/stars/ramakay/claude-self-reflect.svg?style=social)](https://github.com/ramakay/claude-self-reflect/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/ramakay/claude-self-reflect.svg)](https://github.com/ramakay/claude-self-reflect/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/ramakay/claude-self-reflect/pulls)

</div>

**Claude forgets everything. This fixes that.**

Give Claude perfect memory of all your conversations. Search past discussions instantly. Never lose context again.

**Cloud Embeddings** • **20x Faster** • **Production Ready**

## Why This Exists

Claude starts fresh every conversation. You've solved complex bugs, designed architectures, made critical decisions - all forgotten. Until now.

## Table of Contents

- [Quick Install](#quick-install)
- [Performance](#performance)
- [Real Examples](#real-examples)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)
- [Contributors](#contributors)

## Quick Install

```bash
# Install and run automatic setup
npm install -g claude-self-reflect
claude-self-reflect setup
```

### Cloud Embeddings Setup

Claude Self-Reflect uses cloud embeddings for high-quality semantic search. You need one of these API keys:

**Option 1: Qwen/DashScope (Recommended - 2048 dimensions)**
```bash
# Get your key at https://dashscope.console.aliyun.com/
claude-self-reflect setup --dashscope-key=YOUR_KEY
```

**Option 2: Voyage AI (1024 dimensions)**
```bash
# Get your key at https://www.voyageai.com/
claude-self-reflect setup --voyage-key=YOUR_KEY
```

> **Note**: Cloud embeddings provide better search accuracy with 1024-2048 dimensional vectors.

## Performance

| Metric | Value |
|--------|-------|
| **Status Check** | 6ms |
| **Search Latency** | 3ms |
| **Import Speed** | 100/sec |
| **Memory Usage** | 50MB |

### Competitive Comparison

| Feature | Claude Self-Reflect | MemGPT | LangChain Memory |
|---------|---------------------|---------|------------------|
| **Cloud embeddings** | Qwen/Voyage | OpenAI | OpenAI |
| **Real-time indexing** | Yes (2-sec) | Manual | No |
| **Search speed** | <3ms | ~50ms | ~100ms |
| **Setup time** | 5 min | 30+ min | 20+ min |
| **Docker based** | Yes | Python | Python |

## Real Examples

```
You: "How did we fix that 100% CPU usage bug?"
Claude: "Found it - we fixed the circular reference causing 100% CPU usage
        in the server modularization. Also fixed store_reflection dimension
        mismatch by creating separate collections per embedding type."

You: "What about that Docker memory issue?"
Claude: "The container was limited to 2GB but only using 266MB. We found
        the issue only happened with MAX_QUEUE_SIZE=1000 outside Docker.
        With proper Docker limits, memory stays stable at 341MB."

You: "Have we worked with JWT authentication?"
Claude: "Found conversations about JWT patterns including User.authenticate
        methods, TokenHandler classes, and concepts like token rotation,
        PKCE, and social login integration."
```

## Key Features

### MCP Tools Available to Claude

**Search & Memory:**
- `csr_reflect_on_past` - Search past conversations using semantic similarity
- `csr_quick_check` - Fast existence check (count + top match)
- `csr_search_insights` - Aggregated insights from search results
- `csr_get_more` - Paginate through additional results
- `csr_search_by_file` - Find conversations about specific files
- `csr_search_by_concept` - Search by development concepts
- `store_reflection` - Store important insights for future reference
- `get_full_conversation` - Retrieve complete conversation files

**Temporal Queries:**
- `get_recent_work` - "What did we work on last?" with session grouping
- `search_by_recency` - Time-constrained search like "docker issues last week"
- `get_timeline` - Activity timeline with statistics

**System:**
- `get_embedding_mode` - Check current embedding configuration
- `reload_code` - Hot reload Python code changes (development)

### Project-Scoped Search

Searches are **project-aware by default**. Claude automatically searches within your current project:

```
# In ~/projects/MyApp
You: "What authentication method did we use?"
Claude: [Searches ONLY MyApp conversations]

# To search everywhere
You: "Search all projects for WebSocket implementations"
Claude: [Searches across ALL your projects]
```

### Memory Decay

Recent conversations matter more. Old ones fade naturally.
- **90-day half-life**: Recent memories stay strong
- **Graceful aging**: Old information fades naturally
- **Configurable**: Adjust decay rate via environment variables

### HOT/WARM/COLD Prioritization

The safe-watcher service uses intelligent prioritization:
- **HOT** (< 5 minutes): 2-second intervals for near real-time import
- **WARM** (< 24 hours): Normal priority with starvation prevention
- **COLD** (> 24 hours): Batch processed to prevent blocking

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Self-Reflect                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Qdrant    │  │safe-watcher │  │    MCP Server       │  │
│  │  (Vector)   │◄─┤  (Import)   │  │  (Semantic Search)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         ▲                                    │              │
│         │         ┌──────────────────────────┘              │
│         │         ▼                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Cloud Embeddings                        │   │
│  │         Qwen (2048d) or Voyage (1024d)              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Docker Services

| Service | Purpose | Profile |
|---------|---------|---------|
| **qdrant** | Vector database | default |
| **safe-watcher** | Continuous import | safe-watch |
| **mcp-server** | MCP server | mcp |

### Components
- **Vector Database**: Qdrant for semantic search
- **MCP Server**: Python-based using FastMCP
- **Embeddings**: Cloud (Qwen/DashScope or Voyage AI)
- **Import Pipeline**: Docker-based with HOT/WARM/COLD prioritization

## Requirements

### Minimum Requirements
- **Docker Desktop** (macOS/Windows) or **Docker Engine** (Linux)
- **Node.js** 18+ (for the setup wizard)
- **Claude Code** CLI
- **4GB RAM** available for Docker
- **2GB disk space** for vector database

### API Keys (one required)
- **DASHSCOPE_API_KEY** - For Qwen embeddings (2048d)
- **VOYAGE_KEY** - For Voyage AI embeddings (1024d)

### Operating Systems
- macOS 11+ (Intel & Apple Silicon)
- Windows 10/11 with WSL2
- Linux (Ubuntu 20.04+, Debian 11+)

## Environment Variables

### Required (one of)
```bash
DASHSCOPE_API_KEY=xxx    # For Qwen (2048d)
VOYAGE_KEY=xxx           # For Voyage (1024d)
```

### Optional
```bash
QDRANT_URL=http://localhost:6333
EMBEDDING_PROVIDER=cloud
ENABLE_MEMORY_DECAY=false
DECAY_WEIGHT=0.3
DECAY_SCALE_DAYS=90
```

## Keeping Up to Date

```bash
npm update -g claude-self-reflect
```

Updates are automatic and preserve your data.

## Troubleshooting

### Common Issues

**1. "No collections created" after import**
```bash
# Run diagnostics
claude-self-reflect doctor

# Re-run setup to fix paths
claude-self-reflect setup
```

**2. MCP server shows "ERROR" but it's actually INFO**

This is not an actual error - Claude Code displays all stderr output as errors. The INFO message confirms successful startup.

**3. Docker volume mount issues**
```bash
# Ensure Docker has file sharing permissions
# macOS: Docker Desktop → Settings → Resources → File Sharing
# Add: /Users/YOUR_USERNAME/.claude

# Restart Docker and re-run setup
docker compose down
claude-self-reflect setup
```

**4. Qdrant not accessible**
```bash
# Start services
docker compose up -d qdrant
docker compose --profile safe-watch up -d

# Check if running
docker compose ps

# View logs
docker compose logs qdrant
```

### Diagnostic Tools

```bash
# Run comprehensive diagnostics
claude-self-reflect doctor

# View service logs
docker compose logs -f

# Check specific service
docker compose logs safe-watcher
```

### Getting Help

1. [GitHub Issues](https://github.com/ramakay/claude-self-reflect/issues)
2. [Troubleshooting Guide](docs/troubleshooting.md)

## Uninstall

```bash
# Remove MCP server
claude mcp remove claude-self-reflect

# Stop Docker containers
docker compose down

# Uninstall npm package
npm uninstall -g claude-self-reflect
```

## Contributors

Special thanks to our contributors:
- **[@TheGordon](https://github.com/TheGordon)** - Fixed timestamp parsing (#10)
- **[@akamalov](https://github.com/akamalov)** - Ubuntu WSL insights
- **[@kylesnowschwartz](https://github.com/kylesnowschwartz)** - Security review (#6)

---

Built with care by [ramakay](https://github.com/ramakay) for the Claude community.
