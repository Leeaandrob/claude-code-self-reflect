"""Worker model for tracking remote agent status."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ServiceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    ERROR = "error"
    UNKNOWN = "unknown"


class DockerServiceInfo(BaseModel):
    """Info about a Docker service on a worker."""
    name: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    container_id: Optional[str] = None
    image: Optional[str] = None
    uptime: Optional[str] = None
    ports: List[str] = Field(default_factory=list)
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None


class WorkerHeartbeat(BaseModel):
    """Heartbeat data sent by worker agents."""
    worker_id: str = Field(..., description="Unique worker identifier (hostname or custom ID)")
    hostname: str = Field(..., description="Machine hostname")
    ip_address: Optional[str] = Field(None, description="Worker IP address")
    platform: str = Field(..., description="OS platform (linux, darwin, windows)")
    platform_version: Optional[str] = None
    python_version: Optional[str] = None

    # Docker services status
    services: List[DockerServiceInfo] = Field(default_factory=list)
    docker_available: bool = False
    docker_version: Optional[str] = None

    # System metrics
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_used_gb: Optional[float] = None
    memory_total_gb: Optional[float] = None
    disk_percent: Optional[float] = None

    # Import stats (from unified-state)
    total_files: int = 0
    imported_files: int = 0
    total_messages: int = 0

    # Qdrant connection
    qdrant_connected: bool = False
    qdrant_collections: int = 0
    qdrant_vectors: int = 0

    # Embedding mode
    embedding_mode: Optional[str] = None  # 'voyage', 'qwen', 'cloud'

    # Agent info
    agent_version: str = "1.0.0"
    agent_port: int = 8081  # Port where agent API is listening
    started_at: Optional[datetime] = None


class RegisteredWorker(BaseModel):
    """A registered worker with last heartbeat info."""
    worker_id: str
    hostname: str
    ip_address: Optional[str] = None
    platform: str

    # Last known status
    last_heartbeat: datetime
    is_online: bool = True  # Considered offline if no heartbeat for 60s

    # Last known services
    services: List[DockerServiceInfo] = Field(default_factory=list)
    docker_available: bool = False

    # Last known metrics
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None

    # Import stats
    total_files: int = 0
    imported_files: int = 0
    total_messages: int = 0

    # Qdrant
    qdrant_connected: bool = False
    qdrant_collections: int = 0
    qdrant_vectors: int = 0

    embedding_mode: Optional[str] = None
    agent_version: str = "1.0.0"
    agent_port: int = 8081  # Port where agent API is listening
