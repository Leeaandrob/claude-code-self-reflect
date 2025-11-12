"""Batch jobs API endpoints (v7.0 narratives)."""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

CSR_HOME = Path.home() / '.claude-self-reflect'
BATCH_STATE_DIR = CSR_HOME / 'batch_state'

@router.get("/jobs")
async def list_batch_jobs(limit: int = 50):
    """List batch jobs with their status."""
    try:
        if not BATCH_STATE_DIR.exists():
            return []
        
        jobs = []
        for state_file in BATCH_STATE_DIR.glob('*.json'):
            try:
                with open(state_file, 'r') as f:
                    job_data = json.load(f)
                    jobs.append({
                        "id": job_data.get("batch_id", ""),
                        "status": job_data.get("status", ""),
                        "created_at": job_data.get("created_at", ""),
                        "updated_at": job_data.get("updated_at", ""),
                        "conversations_count": len(job_data.get("conversations", [])),
                        "project": job_data.get("project", "")
                    })
            except Exception as e:
                logger.warning(f"Error reading batch state {state_file}: {e}")
        
        return sorted(jobs, key=lambda x: x["created_at"], reverse=True)[:limit]
    except Exception as e:
        logger.error(f"Error listing batch jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_batch_job(job_id: str):
    """Get detailed batch job information."""
    try:
        state_file = BATCH_STATE_DIR / f"{job_id}.json"
        if not state_file.exists():
            raise HTTPException(status_code=404, detail="Job not found")
        
        with open(state_file, 'r') as f:
            return json.load(f)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
