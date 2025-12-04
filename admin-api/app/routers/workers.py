"""Workers API endpoints for managing remote agents."""
from fastapi import APIRouter, HTTPException
from typing import Dict
from datetime import datetime, timedelta
import logging
import httpx

from ..models.worker import WorkerHeartbeat, RegisteredWorker, DockerServiceInfo

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for workers (could be replaced with Redis/DB for persistence)
_workers: Dict[str, RegisteredWorker] = {}

# Worker is considered offline after this many seconds without heartbeat
OFFLINE_THRESHOLD_SECONDS = 60

# Timeout for forwarding commands to workers
WORKER_COMMAND_TIMEOUT = 30.0


def _update_online_status():
    """Update is_online status for all workers based on last heartbeat."""
    now = datetime.utcnow()
    threshold = timedelta(seconds=OFFLINE_THRESHOLD_SECONDS)

    for worker in _workers.values():
        # Handle timezone-aware datetimes
        last_hb = worker.last_heartbeat
        if last_hb.tzinfo is not None:
            last_hb = last_hb.replace(tzinfo=None)
        worker.is_online = (now - last_hb) < threshold


def _get_worker_url(worker: RegisteredWorker) -> str:
    """Get the base URL for a worker agent."""
    ip = worker.ip_address or worker.hostname
    return f"http://{ip}:{worker.agent_port}"


async def _forward_to_worker(worker_id: str, method: str, path: str) -> dict:
    """Forward a request to a worker agent."""
    if worker_id not in _workers:
        raise HTTPException(status_code=404, detail=f"Worker '{worker_id}' not found")

    worker = _workers[worker_id]
    _update_online_status()

    if not worker.is_online:
        raise HTTPException(
            status_code=503,
            detail=f"Worker '{worker_id}' is offline"
        )

    if not worker.ip_address:
        raise HTTPException(
            status_code=400,
            detail=f"Worker '{worker_id}' has no IP address"
        )

    url = f"{_get_worker_url(worker)}{path}"

    try:
        async with httpx.AsyncClient(timeout=WORKER_COMMAND_TIMEOUT) as client:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get('detail', response.text)
                )

            return response.json()

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to worker agent at {url}"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout connecting to worker agent"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error forwarding to worker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heartbeat")
async def receive_heartbeat(heartbeat: WorkerHeartbeat):
    """Receive heartbeat from a worker agent.

    Workers should call this endpoint every 30 seconds to report their status.
    """
    try:
        now = datetime.utcnow()

        # Update or create worker record
        worker = RegisteredWorker(
            worker_id=heartbeat.worker_id,
            hostname=heartbeat.hostname,
            ip_address=heartbeat.ip_address,
            platform=heartbeat.platform,
            last_heartbeat=now,
            is_online=True,
            services=heartbeat.services,
            docker_available=heartbeat.docker_available,
            cpu_percent=heartbeat.cpu_percent,
            memory_percent=heartbeat.memory_percent,
            total_files=heartbeat.total_files,
            imported_files=heartbeat.imported_files,
            total_messages=heartbeat.total_messages,
            qdrant_connected=heartbeat.qdrant_connected,
            qdrant_collections=heartbeat.qdrant_collections,
            qdrant_vectors=heartbeat.qdrant_vectors,
            embedding_mode=heartbeat.embedding_mode,
            agent_version=heartbeat.agent_version,
            agent_port=heartbeat.agent_port,
        )

        _workers[heartbeat.worker_id] = worker

        logger.info(f"Heartbeat received from worker: {heartbeat.worker_id} ({heartbeat.hostname})")

        return {
            "status": "ok",
            "worker_id": heartbeat.worker_id,
            "registered_at": now.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error processing heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_workers():
    """List all registered workers with their current status."""
    _update_online_status()

    workers_list = list(_workers.values())

    # Sort by online status (online first), then by hostname
    workers_list.sort(key=lambda w: (not w.is_online, w.hostname))

    # Calculate summary
    online_count = sum(1 for w in workers_list if w.is_online)
    total_services_running = sum(
        sum(1 for s in w.services if s.status == "running")
        for w in workers_list if w.is_online
    )
    total_vectors = sum(w.qdrant_vectors for w in workers_list if w.is_online)
    total_messages = sum(w.total_messages for w in workers_list if w.is_online)

    return {
        "workers": [w.model_dump() for w in workers_list],
        "summary": {
            "total_workers": len(workers_list),
            "online_workers": online_count,
            "offline_workers": len(workers_list) - online_count,
            "total_services_running": total_services_running,
            "total_vectors": total_vectors,
            "total_messages": total_messages,
        }
    }


@router.get("/{worker_id}")
async def get_worker(worker_id: str):
    """Get detailed information about a specific worker."""
    _update_online_status()

    if worker_id not in _workers:
        raise HTTPException(status_code=404, detail=f"Worker '{worker_id}' not found")

    return _workers[worker_id].model_dump()


@router.delete("/{worker_id}")
async def remove_worker(worker_id: str):
    """Remove a worker from the registry (e.g., when decommissioning)."""
    if worker_id not in _workers:
        raise HTTPException(status_code=404, detail=f"Worker '{worker_id}' not found")

    del _workers[worker_id]
    logger.info(f"Worker removed: {worker_id}")

    return {"status": "ok", "message": f"Worker '{worker_id}' removed"}


@router.get("/{worker_id}/status")
async def get_worker_live_status(worker_id: str):
    """Get live status directly from the worker agent."""
    return await _forward_to_worker(worker_id, "GET", "/status")


@router.get("/{worker_id}/services")
async def get_worker_services(worker_id: str):
    """Get live service list directly from the worker agent."""
    return await _forward_to_worker(worker_id, "GET", "/services")


@router.post("/{worker_id}/services/{service_name}/start")
async def start_service_on_worker(worker_id: str, service_name: str):
    """Start a service on a remote worker.

    This forwards the command directly to the worker agent's local API.
    """
    return await _forward_to_worker(worker_id, "POST", f"/services/{service_name}/start")


@router.post("/{worker_id}/services/{service_name}/stop")
async def stop_service_on_worker(worker_id: str, service_name: str):
    """Stop a service on a remote worker.

    This forwards the command directly to the worker agent's local API.
    """
    return await _forward_to_worker(worker_id, "POST", f"/services/{service_name}/stop")


@router.post("/{worker_id}/services/{service_name}/restart")
async def restart_service_on_worker(worker_id: str, service_name: str):
    """Restart a service on a remote worker.

    This forwards the command directly to the worker agent's local API.
    """
    return await _forward_to_worker(worker_id, "POST", f"/services/{service_name}/restart")


@router.get("/{worker_id}/services/{service_name}/logs")
async def get_service_logs_from_worker(worker_id: str, service_name: str, lines: int = 100):
    """Get service logs from a remote worker.

    This forwards the command directly to the worker agent's local API.
    """
    return await _forward_to_worker(worker_id, "GET", f"/services/{service_name}/logs?lines={lines}")
