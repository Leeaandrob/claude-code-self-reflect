"""Claude Self-Reflect Admin API Server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logging.info(f"Loaded environment from {env_path}")

from .routers import dashboard, projects, imports, collections, settings, docker, logs, batch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Claude Self-Reflect Admin API",
    description="Administrative API for managing Claude Self-Reflect system",
    version="1.0.0"
)

# CORS configuration - Allow any localhost or LAN IP for development
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(imports.router, prefix="/api/imports", tags=["Imports"])
app.include_router(collections.router, prefix="/api/collections", tags=["Collections"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(docker.router, prefix="/api/docker", tags=["Docker"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(batch.router, prefix="/api/batch", tags=["Batch Jobs"])

@app.get("/")
async def root():
    return {
        "name": "Claude Self-Reflect Admin API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    import socket

    def find_free_port(start_port=8000, max_tries=10):
        """Find an available port starting from start_port."""
        for port in range(start_port, start_port + max_tries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("0.0.0.0", port))
                    return port
            except OSError:
                continue
        raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + max_tries}")

    # Find available port
    port = find_free_port(8000)
    if port != 8000:
        logger.warning(f"Port 8000 in use, using port {port} instead")

    logger.info(f"Starting API server on http://0.0.0.0:{port}")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
