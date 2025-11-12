"""Docker services API endpoints."""
from fastapi import APIRouter, HTTPException
import subprocess
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/services")
async def list_docker_services():
    """List Docker Compose services status."""
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
    try:
        subprocess.run(
            ['docker', 'compose', 'start', service_name],
            check=True
        )
        return {"message": f"Service {service_name} started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/services/{service_name}/stop")
async def stop_service(service_name: str):
    """Stop a Docker Compose service."""
    try:
        subprocess.run(
            ['docker', 'compose', 'stop', service_name],
            check=True
        )
        return {"message": f"Service {service_name} stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
