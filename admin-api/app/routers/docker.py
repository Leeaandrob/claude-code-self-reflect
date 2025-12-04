"""Docker services API endpoints."""
from fastapi import APIRouter, HTTPException
import subprocess
import json
import logging
import shutil

logger = logging.getLogger(__name__)
router = APIRouter()


def is_docker_available() -> bool:
    """Check if docker CLI is available."""
    return shutil.which('docker') is not None


@router.get("/services")
async def list_docker_services():
    """List Docker Compose services status."""
    # Check if docker is available
    if not is_docker_available():
        return {
            "services": [],
            "total": 0,
            "running": 0,
            "stopped": 0,
            "error": "Docker CLI not available. The admin-api is running inside a container without Docker access.",
            "hint": "To enable Docker management, mount the Docker socket: -v /var/run/docker.sock:/var/run/docker.sock"
        }

    try:
        result = subprocess.run(
            ['docker', 'compose', 'ps', '--format', 'json'],
            capture_output=True,
            text=True,
            check=True
        )
        services = []
        for line in result.stdout.strip().split('\n'):
            if line:
                service = json.loads(line)
                # Map Docker status to our simplified status
                state = service.get("State", "unknown").lower()
                if state == "running":
                    status = "running"
                elif state in ["exited", "dead"]:
                    status = "stopped"
                elif state == "restarting":
                    status = "starting"
                else:
                    status = "unknown"

                # Extract container image
                image = service.get("Image", "")

                # Extract ports
                ports_str = service.get("Ports", "")
                ports = []
                if ports_str:
                    # Parse ports like "0.0.0.0:6333->6333/tcp"
                    for port_mapping in ports_str.split(','):
                        port_mapping = port_mapping.strip()
                        if '->' in port_mapping:
                            external = port_mapping.split('->')[0].strip()
                            if ':' in external:
                                ports.append(external.split(':')[1])

                services.append({
                    "name": service.get("Service", ""),
                    "status": status,
                    "container_id": service.get("ID", ""),
                    "image": image,
                    "uptime": service.get("RunningFor", ""),
                    "ports": ports
                })

        return {
            "services": services,
            "total": len(services),
            "running": len([s for s in services if s["status"] == "running"]),
            "stopped": len([s for s in services if s["status"] == "stopped"])
        }
    except Exception as e:
        logger.error(f"Error listing Docker services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/services/{service_name}/start")
async def start_service(service_name: str):
    """Start a Docker Compose service."""
    if not is_docker_available():
        raise HTTPException(
            status_code=503,
            detail="Docker CLI not available. Cannot start services."
        )
    try:
        subprocess.run(
            ['docker', 'compose', 'start', service_name],
            capture_output=True,
            text=True,
            check=True
        )
        return {"message": f"Service {service_name} started"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr or str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/services/{service_name}/stop")
async def stop_service(service_name: str):
    """Stop a Docker Compose service."""
    if not is_docker_available():
        raise HTTPException(
            status_code=503,
            detail="Docker CLI not available. Cannot stop services."
        )
    try:
        subprocess.run(
            ['docker', 'compose', 'stop', service_name],
            capture_output=True,
            text=True,
            check=True
        )
        return {"message": f"Service {service_name} stopped"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr or str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
