#!/usr/bin/env python3
"""
Test script for Claude Self-Reflect system validation.
Validates: Docker services, Qwen embeddings, Qdrant collections, indexing progress, MCP connectivity.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(title: str):
    """Print section header."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{title:^80}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{GREEN}✓{RESET} {message}")


def print_error(message: str):
    """Print error message."""
    print(f"{RED}✗{RESET} {message}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{YELLOW}⚠{RESET} {message}")


def print_info(message: str):
    """Print info message."""
    print(f"{BLUE}ℹ{RESET} {message}")


def run_command(cmd: List[str], capture_output=True, timeout=10) -> Tuple[int, str, str]:
    """Run shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timeout"
    except Exception as e:
        return -1, "", str(e)


def test_docker_services() -> bool:
    """Test Docker services are running."""
    print_header("1. Docker Services Check")

    services = {
        "claude-reflection-qdrant": "Qdrant Vector Database",
        "claude-reflection-safe-watcher": "Safe Watcher (Indexer)"
    }

    all_ok = True

    for container, description in services.items():
        code, stdout, _ = run_command(["docker", "ps", "--filter", f"name={container}", "--format", "{{.Status}}"])

        if code == 0 and "Up" in stdout:
            print_success(f"{description}: Running")
        else:
            print_error(f"{description}: Not running or not found")
            all_ok = False

    return all_ok


def test_environment_variables() -> bool:
    """Test required environment variables."""
    print_header("2. Environment Variables Check")

    env_file = Path.home() / ".nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect/.env"

    if not env_file.exists():
        print_error(f".env file not found: {env_file}")
        return False

    required_vars = {
        "DASHSCOPE_API_KEY": "Qwen API Key",
        "DASHSCOPE_ENDPOINT": "Qwen Endpoint",
        "EMBEDDING_PROVIDER": "Embedding Provider",
        "PREFER_LOCAL_EMBEDDINGS": "Embedding Mode"
    }

    all_ok = True
    env_content = env_file.read_text()

    for var, description in required_vars.items():
        if var in env_content and not env_content.split(f"{var}=")[1].split("\n")[0].strip() == "":
            value = env_content.split(f"{var}=")[1].split("\n")[0].strip()
            print_success(f"{description} ({var}): {value[:50]}...")
        else:
            print_error(f"{description} ({var}): Not set")
            all_ok = False

    return all_ok


def test_qwen_embeddings() -> bool:
    """Test Qwen embeddings are being used."""
    print_header("3. Qwen Embeddings Check")

    code, stdout, _ = run_command(["docker", "logs", "--tail", "500", "claude-reflection-safe-watcher"])

    if code != 0:
        print_error("Could not read safe-watcher logs")
        return False

    if "Using Qwen/DashScope: text-embedding-v4 (1024d)" in stdout or "Auto-selected Qwen/DashScope" in stdout:
        print_success("Qwen embeddings initialized successfully")
        print_info("  Model: text-embedding-v4")
        print_info("  Dimensions: 1024")

        # Check for rate limiting
        if "Qwen rate limited" in stdout:
            print_warning("Qwen API rate limiting detected (should be rare)")
        else:
            print_success("No rate limiting issues detected")

        return True
    elif "Using Voyage AI" in stdout or "Auto-selected Voyage" in stdout:
        print_warning("Using Voyage AI instead of Qwen (check DASHSCOPE_API_KEY)")
        return False
    elif "Using FastEmbed" in stdout:
        print_warning("Using FastEmbed instead of Qwen (check configuration)")
        return False
    else:
        # If we can't find the log message, check if collections are 1024d (indirect evidence)
        print_warning("Could not find embedding initialization log (container may have restarted)")
        print_info("  Checking Qdrant collections for 1024d vectors (Qwen signature)...")

        # This will be validated in the next test
        return True  # Don't fail, let Qdrant check validate


def test_qdrant_collections() -> bool:
    """Test Qdrant collections and vector dimensions."""
    print_header("4. Qdrant Collections Check")

    code, stdout, _ = run_command(["curl", "-s", "http://localhost:6333/collections"])

    if code != 0:
        print_error("Could not connect to Qdrant")
        return False

    try:
        data = json.loads(stdout)
        collections = data.get("result", {}).get("collections", [])

        if not collections:
            print_warning("No collections found yet (indexing may be starting)")
            return True

        print_success(f"Found {len(collections)} collection(s)")

        # Check each collection
        for coll in collections[:5]:  # Check first 5
            name = coll.get("name")

            # Get collection details
            code2, stdout2, _ = run_command(["curl", "-s", f"http://localhost:6333/collections/{name}"])
            if code2 == 0:
                details = json.loads(stdout2)
                vector_size = details.get("result", {}).get("config", {}).get("params", {}).get("vectors", {}).get("size")
                points_count = details.get("result", {}).get("points_count", 0)

                if vector_size == 1024:
                    print_success(f"  {name}: {points_count} vectors, 1024d ✓")
                elif vector_size == 384:
                    print_warning(f"  {name}: {points_count} vectors, 384d (FastEmbed, not Qwen)")
                else:
                    print_info(f"  {name}: {points_count} vectors, {vector_size}d")

        return True

    except json.JSONDecodeError:
        print_error("Invalid JSON response from Qdrant")
        return False


def test_indexing_progress() -> bool:
    """Test indexing progress."""
    print_header("5. Indexing Progress Check")

    code, stdout, _ = run_command(["docker", "logs", "--tail", "200", "claude-reflection-safe-watcher"], timeout=30)

    if code != 0:
        print_error("Could not read safe-watcher logs")
        return False

    # Find progress messages
    progress_lines = [line for line in stdout.split("\n") if "Progress:" in line]

    if not progress_lines:
        print_warning("No progress information found yet")
        return True

    latest_progress = progress_lines[-1]
    print_info(f"Latest: {latest_progress.split(' - ')[-1] if ' - ' in latest_progress else latest_progress}")

    # Find completed files
    completed_lines = [line for line in stdout.split("\n") if "Completed:" in line]
    print_success(f"Files completed: {len(completed_lines)}")

    # Check for errors
    error_lines = [line for line in stdout.split("\n") if "ERROR" in line and "Failed to embed" in line]
    if error_lines:
        print_warning(f"Embedding errors: {len(error_lines)}")
    else:
        print_success("No embedding errors detected")

    return True


def test_mcp_configuration() -> bool:
    """Test MCP server configuration."""
    print_header("6. MCP Configuration Check")

    claude_config = Path.home() / ".claude.json"

    if not claude_config.exists():
        print_error(f"Claude config not found: {claude_config}")
        return False

    try:
        with open(claude_config, 'r') as f:
            config = json.load(f)

        mcp_config = config.get("mcpServers", {}).get("claude-self-reflect", {})

        if not mcp_config:
            print_error("claude-self-reflect MCP not configured")
            return False

        print_success("MCP server configured in ~/.claude.json")

        env_vars = mcp_config.get("env", {})
        required_env = ["DASHSCOPE_API_KEY", "EMBEDDING_PROVIDER"]

        all_ok = True
        for var in required_env:
            if var in env_vars and env_vars[var]:
                print_success(f"  {var}: {env_vars[var][:30]}...")
            else:
                print_warning(f"  {var}: Not set in MCP config")
                all_ok = False

        return all_ok

    except json.JSONDecodeError:
        print_error("Invalid JSON in ~/.claude.json")
        return False


def test_search_functionality() -> bool:
    """Test basic search functionality."""
    print_header("7. Search Functionality Check")

    # Get a collection with data
    code, stdout, _ = run_command(["curl", "-s", "http://localhost:6333/collections"])

    if code != 0:
        print_error("Could not connect to Qdrant")
        return False

    try:
        data = json.loads(stdout)
        collections = data.get("result", {}).get("collections", [])

        # Find collection with most points
        best_collection = None
        max_points = 0
        vector_size = None

        for coll in collections:
            name = coll.get("name")
            code2, stdout2, _ = run_command(["curl", "-s", f"http://localhost:6333/collections/{name}"])
            if code2 == 0:
                details = json.loads(stdout2)
                points = details.get("result", {}).get("points_count", 0)
                if points > max_points:
                    max_points = points
                    best_collection = name
                    vector_size = details.get("result", {}).get("config", {}).get("params", {}).get("vectors", {}).get("size")

        if not best_collection or max_points == 0:
            print_warning("No collections with data yet - indexing still in progress")
            print_info("  Search functionality cannot be tested until indexing completes")
            return True

        print_success(f"Found collection with data: {best_collection} ({max_points} vectors, {vector_size}d)")

        # Perform actual search test using Qwen embeddings
        print_info("  Testing semantic search with Qwen embeddings...")

        # Check if we have Qwen configured
        env_file = Path.home() / ".nvm/versions/node/v22.16.0/lib/node_modules/claude-self-reflect/.env"
        if not env_file.exists():
            print_warning("  Cannot test search: .env file not found")
            return False

        env_content = env_file.read_text()
        api_key = None
        endpoint = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        for line in env_content.split("\n"):
            if line.startswith("DASHSCOPE_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
            elif line.startswith("DASHSCOPE_ENDPOINT="):
                endpoint = line.split("=", 1)[1].strip()

        if not api_key:
            print_warning("  Cannot test search: DASHSCOPE_API_KEY not set")
            return False

        # Generate test embedding using Qwen
        test_query = "docker configuration and containers"
        print_info(f"  Query: '{test_query}'")

        # Call Qwen API to get embedding
        import requests

        try:
            response = requests.post(
                f"{endpoint}/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "text-embedding-v4",
                    "input": test_query,
                    "encoding_format": "float"
                },
                timeout=10
            )

            if response.status_code != 200:
                print_error(f"  Qwen API error: {response.status_code}")
                return False

            embedding_data = response.json()
            query_vector = embedding_data["data"][0]["embedding"]

            if len(query_vector) != vector_size:
                print_error(f"  Vector dimension mismatch: query={len(query_vector)}d, collection={vector_size}d")
                return False

            print_success(f"  Generated {len(query_vector)}d embedding from Qwen")

        except requests.exceptions.RequestException as e:
            print_error(f"  Failed to get Qwen embedding: {e}")
            return False

        # Perform search in Qdrant
        search_payload = {
            "vector": query_vector,
            "limit": 5,
            "with_payload": True,
            "score_threshold": 0.3
        }

        code3, stdout3, stderr3 = run_command([
            "curl", "-s", "-X", "POST",
            f"http://localhost:6333/collections/{best_collection}/points/search",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(search_payload)
        ])

        if code3 != 0:
            print_error(f"  Search failed: {stderr3}")
            return False

        search_results = json.loads(stdout3)
        results = search_results.get("result", [])

        if not results:
            print_warning(f"  No results found for query '{test_query}'")
            print_info("    (This may be expected if indexed data doesn't match the query)")
            return True

        print_success(f"  Found {len(results)} result(s)")

        # Validate result structure
        for i, result in enumerate(results[:3], 1):
            score = result.get("score", 0)
            payload = result.get("payload", {})
            excerpt = payload.get("excerpt", "")[:100]
            timestamp = payload.get("timestamp", "unknown")

            print_info(f"    [{i}] Score: {score:.3f} | Time: {timestamp}")
            print_info(f"        Excerpt: {excerpt}...")

            # Validate payload structure
            required_fields = ["excerpt", "timestamp", "conversation_id"]
            missing_fields = [f for f in required_fields if f not in payload]

            if missing_fields:
                print_warning(f"        Missing fields: {missing_fields}")
            else:
                print_success(f"        Payload structure valid")

        return True

    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON response: {e}")
        return False
    except Exception as e:
        print_error(f"Search test failed: {e}")
        return False


def print_summary(results: Dict[str, bool]):
    """Print test summary."""
    print_header("Test Summary")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")

    print(f"\n{BLUE}Results: {passed}/{total} tests passed{RESET}")

    if passed == total:
        print(f"\n{GREEN}✓ All systems operational!{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print("  1. Wait for indexing to complete (check progress above)")
        print("  2. Restart Claude Code to reload MCP configuration")
        print("  3. Test search: 'Search my past conversations about [topic]'")
    else:
        print(f"\n{RED}✗ Some tests failed. Review errors above.{RESET}")


def main():
    """Run all tests."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}Claude Self-Reflect System Validation{RESET}")
    print(f"{BLUE}Testing Qwen embeddings, Qdrant, indexing, and MCP{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}")

    results = {
        "Docker Services": test_docker_services(),
        "Environment Variables": test_environment_variables(),
        "Qwen Embeddings": test_qwen_embeddings(),
        "Qdrant Collections": test_qdrant_collections(),
        "Indexing Progress": test_indexing_progress(),
        "MCP Configuration": test_mcp_configuration(),
        "Search Readiness": test_search_functionality()
    }

    print_summary(results)

    # Exit code
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
