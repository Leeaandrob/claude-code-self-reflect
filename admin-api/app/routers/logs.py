"""Logs viewer API endpoints."""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

CSR_HOME = Path.home() / '.claude-self-reflect'
LOGS_DIR = CSR_HOME / 'logs'

@router.get("/mcp")
async def get_mcp_logs(lines: int = 100):
    """Get MCP server logs."""
    try:
        log_file = LOGS_DIR / 'mcp-server.log'
        if not log_file.exists():
            return {"logs": "", "lines_count": 0}

        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            log_lines = [line.strip() for line in all_lines[-lines:]]
            log_text = '\n'.join(log_lines)
            return {
                "logs": log_text,
                "lines_count": len(log_lines),
                "total_lines": len(all_lines)
            }
    except Exception as e:
        logger.error(f"Error reading MCP logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/docker/{service}")
async def get_docker_logs(service: str, lines: int = 100):
    """Get Docker service logs."""
    try:
        import subprocess
        result = subprocess.run(
            ['docker', 'compose', 'logs', '--tail', str(lines), service],
            capture_output=True,
            text=True,
            check=True
        )
        log_lines = [line for line in result.stdout.split('\n') if line.strip()]
        log_text = '\n'.join(log_lines)
        return {
            "logs": log_text,
            "lines_count": len(log_lines),
            "service": service
        }
    except Exception as e:
        logger.error(f"Error reading Docker logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
