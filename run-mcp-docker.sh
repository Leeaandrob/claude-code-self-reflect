#!/bin/bash
# Run MCP server via Docker container (stdio mode for Claude Code)
# This uses the same Docker container as the import service

# Ensure MCP container is running
if ! docker compose ps mcp-server | grep -q "Up"; then
    echo "[ERROR] MCP container not running. Start with:" >&2
    echo "  docker compose --profile mcp up -d" >&2
    exit 1
fi

# Run MCP server in stdio mode via Docker exec
# The -i flag keeps stdin open for MCP protocol
exec docker compose exec -T mcp-server python -m src
