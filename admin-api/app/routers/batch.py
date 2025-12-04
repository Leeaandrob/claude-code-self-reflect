"""Batch jobs API endpoints for narrative generation."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from ..services.batch_service import batch_service
from ..services.narrative_service import narrative_service

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateBatchRequest(BaseModel):
    """Request model for creating a batch job."""
    conversation_ids: List[str] = Field(..., description="List of conversation IDs to process")
    project: Optional[str] = Field(None, description="Project filter")
    model: str = Field("qwen-plus", description="Model to use for narrative generation")


class BatchJobResponse(BaseModel):
    """Response model for batch job."""
    id: str
    status: str
    model: Optional[str] = None
    project: Optional[str] = None
    conversations_count: int = 0
    progress: int = 0
    completed_count: int = 0
    failed_count: int = 0
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


@router.get("/jobs")
async def list_batch_jobs(limit: int = 50) -> List[BatchJobResponse]:
    """List all batch jobs with their status."""
    try:
        jobs = await batch_service.list_jobs(limit)
        return [BatchJobResponse(**job) for job in jobs]
    except Exception as e:
        logger.error(f"Error listing batch jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_batch_job(job_id: str):
    """Get detailed batch job information."""
    try:
        job = await batch_service.get_job(job_id)
        return job
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Job not found")
        logger.error(f"Error getting batch job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs")
async def create_batch_job(
    request: CreateBatchRequest,
    background_tasks: BackgroundTasks
):
    """Create a new batch job for narrative generation."""
    try:
        if not request.conversation_ids:
            raise HTTPException(status_code=400, detail="No conversation IDs provided")

        if len(request.conversation_ids) > 50000:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50,000 conversations per batch"
            )

        # Submit batch job
        job = await batch_service.submit_batch(
            conversation_ids=request.conversation_ids,
            project=request.project,
            model=request.model
        )

        # Schedule background polling
        background_tasks.add_task(poll_batch_status, job['batch_id'])

        return {
            "success": True,
            "job": job,
            "message": f"Batch job created with {len(request.conversation_ids)} conversations"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating batch job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/refresh")
async def refresh_batch_status(job_id: str, background_tasks: BackgroundTasks):
    """Manually refresh batch job status from DashScope."""
    try:
        job = await batch_service.poll_and_update_status(job_id)

        # If still in progress, schedule another poll
        if job.get('status') in ['pending', 'in_progress', 'submitted']:
            background_tasks.add_task(poll_batch_status, job_id)

        return job
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Job not found")
        logger.error(f"Error refreshing batch status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
async def cancel_batch_job(job_id: str):
    """Cancel a running batch job."""
    try:
        result = await batch_service.cancel_batch(job_id)
        return {"success": True, "result": result}
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Job not found")
        logger.error(f"Error cancelling batch job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/results")
async def get_batch_results(job_id: str):
    """Get the results of a completed batch job."""
    try:
        results = await batch_service.get_batch_results(job_id)
        return {
            "success": True,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Job not found")
        if "not completed" in str(e).lower():
            raise HTTPException(status_code=400, detail="Job not completed yet")
        logger.error(f"Error getting batch results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/pending")
async def get_pending_conversations(
    project: Optional[str] = None,
    limit: int = 100
):
    """Get conversations that don't have narratives yet."""
    try:
        conversations = await batch_service.get_conversations_without_narrative(
            project=project,
            limit=limit
        )
        return {
            "count": len(conversations),
            "conversations": conversations
        }
    except Exception as e:
        logger.error(f"Error getting pending conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/process")
async def process_batch_results(job_id: str):
    """Process completed batch results and store narratives in Qdrant."""
    try:
        # Get job details
        job = await batch_service.get_job(job_id)
        if job.get('status') != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Job not completed: {job.get('status')}"
            )

        # Get results
        results = await batch_service.get_batch_results(job_id)
        project = job.get('project', 'unknown')

        # Store narratives
        stored_count = 0
        errors = []

        for result in results:
            conv_id = result.get('conversation_id')
            narrative = result.get('narrative')
            error = result.get('error')

            if error:
                errors.append({"conversation_id": conv_id, "error": error})
                continue

            if narrative:
                try:
                    await narrative_service.store_narrative(
                        conversation_id=conv_id,
                        project=project,
                        narrative=narrative,
                        tokens_used=result.get('tokens_used')
                    )
                    stored_count += 1
                except Exception as e:
                    errors.append({
                        "conversation_id": conv_id,
                        "error": str(e)
                    })

        return {
            "success": True,
            "stored_count": stored_count,
            "error_count": len(errors),
            "errors": errors[:10]  # Limit error details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing batch results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/narratives/search")
async def search_narratives(
    query: str,
    project: Optional[str] = None,
    limit: int = 10,
    min_score: float = 0.3
):
    """Search narratives by semantic similarity."""
    try:
        results = await narrative_service.search_narratives(
            query=query,
            project=project,
            limit=limit,
            min_score=min_score
        )
        return {
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error searching narratives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/narratives/stats")
async def get_narrative_stats(project: Optional[str] = None):
    """Get narrative storage statistics."""
    try:
        stats = await narrative_service.get_stats(project)
        return stats
    except Exception as e:
        logger.error(f"Error getting narrative stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_available_models():
    """List available models for narrative generation."""
    return {
        "models": [
            {
                "id": "qwen-max",
                "name": "Qwen Max",
                "description": "Best performance, highest cost. Good for complex narratives.",
                "price_input": "$0.11/1M tokens (batch)",
                "price_output": "$0.44/1M tokens (batch)"
            },
            {
                "id": "qwen-plus",
                "name": "Qwen Plus",
                "description": "Balanced performance and cost. Recommended for most use cases.",
                "price_input": "$0.075/1M tokens (batch)",
                "price_output": "$0.30/1M tokens (batch)"
            },
            {
                "id": "qwen-turbo",
                "name": "Qwen Turbo",
                "description": "Fastest and cheapest. Good for simple summaries.",
                "price_input": "~$0.02/1M tokens (batch)",
                "price_output": "~$0.08/1M tokens (batch)"
            }
        ],
        "default": "qwen-plus",
        "note": "Batch API pricing is 50% off standard API pricing"
    }


async def poll_batch_status(job_id: str, max_retries: int = 100):
    """Background task to poll batch status until completion."""
    import asyncio

    for _ in range(max_retries):
        try:
            job = await batch_service.poll_and_update_status(job_id)
            status = job.get('status', '')

            if status in ['completed', 'failed']:
                logger.info(f"Batch job {job_id} finished with status: {status}")
                break

            # Wait before next poll (increasing interval)
            await asyncio.sleep(30)  # Poll every 30 seconds
        except Exception as e:
            logger.error(f"Error polling batch {job_id}: {e}")
            await asyncio.sleep(60)  # Wait longer on error
