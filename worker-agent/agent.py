#!/usr/bin/env python3
"""
Claude Self-Reflect Worker Agent

This agent runs on each machine where Claude Self-Reflect is installed.
It manages local Docker services and reports status to the central admin API.

Features:
- Heartbeat reporting to admin API
- Local HTTP API for remote service control
- Docker container management (start/stop/restart)
- System metrics collection

Usage:
    python agent.py --api-url http://admin-server:8000/api

Requirements:
    pip install httpx psutil python-dotenv fastapi uvicorn pyyaml
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)

try:
    import psutil
except ImportError:
    print("ERROR: psutil not installed. Run: pip install psutil")
    sys.exit(1)

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    print("ERROR: fastapi/uvicorn not installed. Run: pip install fastapi uvicorn")
    sys.exit(1)

try:
    import yaml
except ImportError:
    yaml = None

from dotenv import load_dotenv

# Version
AGENT_VERSION = "2.0.0"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
agent_state = {
    'worker_id': None,
    'api_url': None,
    'started_at': None,
    'last_heartbeat': None,
    'compose_file': None,
    'services_dir': None,
}


def get_worker_id() -> str:
    """Generate a unique worker ID based on hostname."""
    hostname = socket.gethostname()
    unique_str = f"{hostname}-{platform.machine()}-{platform.system()}"
    worker_hash = hashlib.sha256(unique_str.encode()).hexdigest()[:8]
    return f"{hostname}-{worker_hash}"


def get_ip_address() -> Optional[str]:
    """Get the primary IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def run_docker_command(args: list, timeout: int = 30) -> tuple[bool, str, str]:
    """Run a docker command and return success, stdout, stderr."""
    try:
        result = subprocess.run(
            ['docker'] + args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def run_compose_command(args: list, compose_file: str = None, timeout: int = 60) -> tuple[bool, str, str]:
    """Run a docker compose command."""
    cmd = ['docker', 'compose']
    if compose_file:
        cmd.extend(['-f', compose_file])
    cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def check_docker() -> tuple[bool, Optional[str], list]:
    """Check if Docker is available and get service status."""
    services = []
    docker_version = None

    if not shutil.which('docker'):
        return False, None, []

    try:
        # Get Docker version
        success, stdout, _ = run_docker_command(['--version'], timeout=5)
        if success:
            docker_version = stdout.strip()

        # List containers (filter by claude-self-reflect related)
        success, stdout, _ = run_docker_command(
            ['ps', '-a', '--format', '{{json .}}'],
            timeout=10
        )

        if success:
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    container = json.loads(line)
                    name = container.get('Names', '')

                    # Filter for claude-self-reflect containers
                    keywords = ['qdrant', 'claude', 'mcp', 'watcher', 'reflect']
                    if any(kw in name.lower() for kw in keywords):
                        status = container.get('Status', '')
                        state = 'running' if 'Up' in status else 'stopped'

                        # Get container stats if running
                        memory_mb = None
                        cpu_percent = None
                        if state == 'running':
                            stats_success, stats_out, _ = run_docker_command(
                                ['stats', '--no-stream', '--format', '{{json .}}', container.get('ID', '')[:12]],
                                timeout=5
                            )
                            if stats_success and stats_out.strip():
                                try:
                                    stats = json.loads(stats_out.strip())
                                    mem_str = stats.get('MemUsage', '0MiB').split('/')[0].strip()
                                    if 'GiB' in mem_str:
                                        memory_mb = float(mem_str.replace('GiB', '')) * 1024
                                    elif 'MiB' in mem_str:
                                        memory_mb = float(mem_str.replace('MiB', ''))
                                    cpu_str = stats.get('CPUPerc', '0%').replace('%', '')
                                    cpu_percent = float(cpu_str)
                                except (json.JSONDecodeError, ValueError):
                                    pass

                        services.append({
                            'name': name,
                            'status': state,
                            'container_id': container.get('ID', '')[:12],
                            'image': container.get('Image', ''),
                            'uptime': status,
                            'ports': [p for p in container.get('Ports', '').split(', ') if p],
                            'memory_mb': memory_mb,
                            'cpu_percent': cpu_percent,
                        })
                except json.JSONDecodeError:
                    continue

        return True, docker_version, services

    except Exception as e:
        logger.error(f"Error checking Docker: {e}")
        return False, None, []


def get_system_metrics() -> dict:
    """Get system CPU and memory metrics."""
    return {
        'cpu_percent': psutil.cpu_percent(interval=0.5),
        'memory_percent': psutil.virtual_memory().percent,
        'memory_used_gb': psutil.virtual_memory().used / (1024**3),
        'memory_total_gb': psutil.virtual_memory().total / (1024**3),
        'disk_percent': psutil.disk_usage('/').percent
    }


def get_unified_state_stats(state_file: Path) -> dict:
    """Read import statistics from unified state file."""
    stats = {
        'total_files': 0,
        'imported_files': 0,
        'total_messages': 0
    }

    if not state_file.exists():
        return stats

    try:
        with open(state_file, 'r') as f:
            state = json.load(f)

        files = state.get('files', {})
        stats['imported_files'] = len(files)
        stats['total_messages'] = sum(
            f.get('message_count', 0) for f in files.values()
        )

        # Try to count total files in Claude logs
        logs_dir = os.getenv('LOGS_DIR', str(Path.home() / '.claude' / 'projects'))
        claude_logs = Path(logs_dir)
        if claude_logs.exists():
            stats['total_files'] = sum(1 for _ in claude_logs.rglob('*.jsonl'))

    except Exception as e:
        logger.error(f"Error reading unified state: {e}")

    return stats


async def check_qdrant(qdrant_url: str) -> dict:
    """Check Qdrant connection and get collection stats."""
    result = {
        'connected': False,
        'collections': 0,
        'vectors': 0
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{qdrant_url}/collections")
            if response.status_code == 200:
                data = response.json()
                collections = data.get('result', {}).get('collections', [])
                result['connected'] = True
                result['collections'] = len(collections)

                for coll in collections:
                    try:
                        coll_response = await client.get(
                            f"{qdrant_url}/collections/{coll['name']}"
                        )
                        if coll_response.status_code == 200:
                            coll_data = coll_response.json()
                            result['vectors'] += coll_data.get('result', {}).get('points_count', 0)
                    except Exception:
                        pass

    except Exception as e:
        logger.debug(f"Qdrant not reachable: {e}")

    return result


def detect_embedding_mode() -> Optional[str]:
    """Detect which embedding mode is configured."""
    if os.getenv('DASHSCOPE_API_KEY'):
        return 'qwen'
    elif os.getenv('VOYAGE_KEY'):
        return 'voyage'
    return 'cloud'


# ============================================================================
# Service Management Functions
# ============================================================================

def start_service(service_name: str) -> dict:
    """Start a Docker service/container."""
    # First try docker compose
    compose_file = agent_state.get('compose_file')
    if compose_file and Path(compose_file).exists():
        success, stdout, stderr = run_compose_command(
            ['up', '-d', service_name],
            compose_file=compose_file,
            timeout=120
        )
        if success:
            return {'status': 'ok', 'message': f'Service {service_name} started'}

    # Fallback to direct container start
    success, stdout, stderr = run_docker_command(['start', service_name], timeout=30)
    if success:
        return {'status': 'ok', 'message': f'Container {service_name} started'}

    return {'status': 'error', 'message': f'Failed to start {service_name}: {stderr}'}


def stop_service(service_name: str) -> dict:
    """Stop a Docker service/container."""
    # First try docker compose
    compose_file = agent_state.get('compose_file')
    if compose_file and Path(compose_file).exists():
        success, stdout, stderr = run_compose_command(
            ['stop', service_name],
            compose_file=compose_file,
            timeout=60
        )
        if success:
            return {'status': 'ok', 'message': f'Service {service_name} stopped'}

    # Fallback to direct container stop
    success, stdout, stderr = run_docker_command(['stop', service_name], timeout=30)
    if success:
        return {'status': 'ok', 'message': f'Container {service_name} stopped'}

    return {'status': 'error', 'message': f'Failed to stop {service_name}: {stderr}'}


def restart_service(service_name: str) -> dict:
    """Restart a Docker service/container."""
    compose_file = agent_state.get('compose_file')
    if compose_file and Path(compose_file).exists():
        success, stdout, stderr = run_compose_command(
            ['restart', service_name],
            compose_file=compose_file,
            timeout=120
        )
        if success:
            return {'status': 'ok', 'message': f'Service {service_name} restarted'}

    success, stdout, stderr = run_docker_command(['restart', service_name], timeout=60)
    if success:
        return {'status': 'ok', 'message': f'Container {service_name} restarted'}

    return {'status': 'error', 'message': f'Failed to restart {service_name}: {stderr}'}


def get_service_logs(service_name: str, lines: int = 100) -> dict:
    """Get logs from a Docker service/container."""
    success, stdout, stderr = run_docker_command(
        ['logs', '--tail', str(lines), service_name],
        timeout=30
    )
    if success:
        return {'status': 'ok', 'logs': stdout + stderr}
    return {'status': 'error', 'message': f'Failed to get logs: {stderr}'}


# ============================================================================
# FastAPI Local Server
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    agent_state['started_at'] = datetime.utcnow().isoformat()
    logger.info(f"Agent local API started on port {agent_state.get('local_port', 8081)}")
    yield
    logger.info("Agent shutting down")


app = FastAPI(
    title="Claude Self-Reflect Worker Agent",
    version=AGENT_VERSION,
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "worker_id": agent_state['worker_id'],
        "version": AGENT_VERSION,
        "uptime": agent_state['started_at']
    }


@app.get("/status")
async def status():
    """Get full agent status."""
    docker_available, docker_version, services = check_docker()
    metrics = get_system_metrics()
    state_file = Path(os.getenv('STATE_FILE', str(Path.home() / '.claude-self-reflect' / 'config' / 'unified-state.json')))
    import_stats = get_unified_state_stats(state_file)
    qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
    qdrant_stats = await check_qdrant(qdrant_url)

    return {
        "worker_id": agent_state['worker_id'],
        "hostname": socket.gethostname(),
        "ip_address": get_ip_address(),
        "platform": platform.system().lower(),
        "version": AGENT_VERSION,
        "docker_available": docker_available,
        "docker_version": docker_version,
        "services": services,
        "metrics": metrics,
        "import_stats": import_stats,
        "qdrant": qdrant_stats,
        "embedding_mode": detect_embedding_mode(),
        "last_heartbeat": agent_state.get('last_heartbeat'),
    }


@app.get("/services")
async def list_services():
    """List all managed Docker services."""
    docker_available, docker_version, services = check_docker()
    return {
        "docker_available": docker_available,
        "docker_version": docker_version,
        "services": services
    }


@app.post("/services/{service_name}/start")
async def api_start_service(service_name: str):
    """Start a service."""
    result = start_service(service_name)
    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])
    return result


@app.post("/services/{service_name}/stop")
async def api_stop_service(service_name: str):
    """Stop a service."""
    result = stop_service(service_name)
    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])
    return result


@app.post("/services/{service_name}/restart")
async def api_restart_service(service_name: str):
    """Restart a service."""
    result = restart_service(service_name)
    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])
    return result


@app.get("/services/{service_name}/logs")
async def api_get_logs(service_name: str, lines: int = 100):
    """Get service logs."""
    result = get_service_logs(service_name, lines)
    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])
    return result


# ============================================================================
# Heartbeat Loop
# ============================================================================

async def send_heartbeat(
    api_url: str,
    worker_id: str,
    state_file: Path,
    qdrant_url: str,
    local_port: int
) -> bool:
    """Send heartbeat to admin API."""
    docker_available, docker_version, services = check_docker()
    metrics = get_system_metrics()
    import_stats = get_unified_state_stats(state_file)
    qdrant_stats = await check_qdrant(qdrant_url)

    heartbeat = {
        'worker_id': worker_id,
        'hostname': socket.gethostname(),
        'ip_address': get_ip_address(),
        'platform': platform.system().lower(),
        'platform_version': platform.release(),
        'python_version': platform.python_version(),

        'services': services,
        'docker_available': docker_available,
        'docker_version': docker_version,

        'cpu_percent': metrics['cpu_percent'],
        'memory_percent': metrics['memory_percent'],
        'memory_used_gb': metrics['memory_used_gb'],
        'memory_total_gb': metrics['memory_total_gb'],
        'disk_percent': metrics['disk_percent'],

        'total_files': import_stats['total_files'],
        'imported_files': import_stats['imported_files'],
        'total_messages': import_stats['total_messages'],

        'qdrant_connected': qdrant_stats['connected'],
        'qdrant_collections': qdrant_stats['collections'],
        'qdrant_vectors': qdrant_stats['vectors'],

        'embedding_mode': detect_embedding_mode(),
        'agent_version': AGENT_VERSION,
        'agent_port': local_port,  # Tell admin which port to use for commands
        'started_at': agent_state['started_at'],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{api_url}/workers/heartbeat",
                json=heartbeat
            )

            if response.status_code == 200:
                agent_state['last_heartbeat'] = datetime.utcnow().isoformat()
                logger.debug("Heartbeat sent successfully")
                return True
            else:
                logger.warning(f"Heartbeat failed: {response.status_code} - {response.text}")
                return False

    except httpx.ConnectError:
        logger.error(f"Cannot connect to admin API at {api_url}")
        return False
    except Exception as e:
        logger.error(f"Error sending heartbeat: {e}")
        return False


async def heartbeat_loop(
    api_url: str,
    interval: int,
    state_file: Path,
    qdrant_url: str,
    local_port: int
):
    """Run the heartbeat loop."""
    worker_id = agent_state['worker_id']
    consecutive_failures = 0
    max_failures = 5

    while True:
        try:
            success = await send_heartbeat(
                api_url, worker_id, state_file, qdrant_url, local_port
            )

            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    logger.warning(f"Failed to send heartbeat {max_failures} times")
                    consecutive_failures = 0

        except Exception as e:
            logger.error(f"Unexpected error in heartbeat loop: {e}")

        await asyncio.sleep(interval)


async def run_agent(
    api_url: str,
    interval: int,
    state_file: Path,
    qdrant_url: str,
    local_port: int,
    compose_file: str = None
):
    """Run both the heartbeat loop and local API server."""
    worker_id = get_worker_id()
    agent_state['worker_id'] = worker_id
    agent_state['api_url'] = api_url
    agent_state['local_port'] = local_port
    agent_state['compose_file'] = compose_file

    logger.info(f"Starting Claude Self-Reflect Worker Agent v{AGENT_VERSION}")
    logger.info(f"Worker ID: {worker_id}")
    logger.info(f"Admin API URL: {api_url}")
    logger.info(f"Local API port: {local_port}")
    logger.info(f"Heartbeat interval: {interval}s")
    logger.info(f"State file: {state_file}")
    logger.info(f"Qdrant URL: {qdrant_url}")
    if compose_file:
        logger.info(f"Compose file: {compose_file}")

    # Create uvicorn config
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=local_port,
        log_level="warning"
    )
    server = uvicorn.Server(config)

    # Run both tasks concurrently
    await asyncio.gather(
        server.serve(),
        heartbeat_loop(api_url, interval, state_file, qdrant_url, local_port)
    )


def main():
    parser = argparse.ArgumentParser(
        description='Claude Self-Reflect Worker Agent'
    )
    parser.add_argument(
        '--api-url',
        default=os.getenv('ADMIN_API_URL', 'http://localhost:8000/api'),
        help='Admin API URL (default: http://localhost:8000/api)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=int(os.getenv('HEARTBEAT_INTERVAL', '30')),
        help='Heartbeat interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--state-file',
        type=Path,
        default=Path(os.getenv(
            'STATE_FILE',
            str(Path.home() / '.claude-self-reflect' / 'config' / 'unified-state.json')
        )),
        help='Path to unified state file'
    )
    parser.add_argument(
        '--qdrant-url',
        default=os.getenv('QDRANT_URL', 'http://localhost:6333'),
        help='Qdrant URL (default: http://localhost:6333)'
    )
    parser.add_argument(
        '--local-port',
        type=int,
        default=int(os.getenv('AGENT_PORT', '8081')),
        help='Local API port for receiving commands (default: 8081)'
    )
    parser.add_argument(
        '--compose-file',
        type=Path,
        default=os.getenv('COMPOSE_FILE'),
        help='Docker compose file for service management'
    )
    parser.add_argument(
        '--env-file',
        type=Path,
        default=None,
        help='Path to .env file to load'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Load env file
    if args.env_file:
        load_dotenv(args.env_file)
    else:
        for env_path in [
            Path.cwd() / '.env',
            Path('/config/.env'),
            Path.home() / '.claude-self-reflect' / '.env'
        ]:
            if env_path.exists():
                load_dotenv(env_path)
                break

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        asyncio.run(run_agent(
            api_url=args.api_url,
            interval=args.interval,
            state_file=args.state_file,
            qdrant_url=args.qdrant_url,
            local_port=args.local_port,
            compose_file=str(args.compose_file) if args.compose_file else None
        ))
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
        sys.exit(0)


if __name__ == '__main__':
    main()
