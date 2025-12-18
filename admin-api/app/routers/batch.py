"""Batch jobs API endpoints for narrative generation."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from pathlib import Path
import logging
import json
import asyncio
import aiofiles
from datetime import datetime

from ..services.batch_service import batch_service, UNIFIED_STATE_FILE
from ..services.narrative_service import narrative_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Backfill state tracking
_backfill_state = {
    "running": False,
    "started_at": None,
    "batches_submitted": 0,
    "batches_completed": 0,
    "narratives_generated": 0,
    "errors": 0,
    "last_error": None
}


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


# =============================================================================
# BACKFILL MANAGEMENT ENDPOINTS
# =============================================================================


class BackfillRequest(BaseModel):
    """Request model for starting a backfill."""
    batch_size: int = Field(50, ge=5, le=100, description="Conversations per batch")
    max_batches: int = Field(10, ge=1, le=50, description="Maximum batches to submit")
    model: str = Field("qwen-plus", description="Model to use")
    delay_between_batches: int = Field(60, ge=10, le=600, description="Seconds between batches")


@router.get("/backfill/stats")
async def get_backfill_stats():
    """Get statistics about conversations pending narrative generation.

    This is the first step before starting a backfill - understand the scale.
    """
    try:
        if not UNIFIED_STATE_FILE.exists():
            return {"error": "Unified state file not found"}

        async with aiofiles.open(UNIFIED_STATE_FILE, 'r') as f:
            state = json.loads(await f.read())

        files_data = state.get('files', {})

        # Count categories
        total = len(files_data)
        with_narrative = 0
        pending_exists = 0
        pending_missing = 0
        not_completed = 0
        empty = 0

        for file_path, info in files_data.items():
            if info.get('has_narrative'):
                with_narrative += 1
            elif info.get('status') != 'completed':
                not_completed += 1
            elif info.get('chunks', 0) == 0:
                empty += 1
            elif Path(file_path).exists():
                pending_exists += 1
            else:
                pending_missing += 1

        # Estimate costs (rough)
        avg_tokens_per_conv = 15000  # Average input tokens
        avg_output_tokens = 500  # Average output tokens
        qwen_plus_input_price = 0.000075  # per 1k tokens (batch)
        qwen_plus_output_price = 0.0003  # per 1k tokens (batch)

        cost_per_conv = (
            (avg_tokens_per_conv / 1000) * qwen_plus_input_price +
            (avg_output_tokens / 1000) * qwen_plus_output_price
        )
        estimated_cost = pending_exists * cost_per_conv

        # Estimate time (50 per batch, ~30 min per batch with DashScope)
        batches_needed = (pending_exists + 49) // 50
        estimated_hours = (batches_needed * 30) / 60

        return {
            "summary": {
                "total_conversations": total,
                "with_narrative": with_narrative,
                "pending_valid": pending_exists,
                "pending_missing_file": pending_missing,
                "not_completed": not_completed,
                "empty_conversations": empty
            },
            "backfill": {
                "conversations_to_process": pending_exists,
                "batches_needed": batches_needed,
                "estimated_hours": round(estimated_hours, 1),
                "estimated_cost_usd": round(estimated_cost, 2)
            },
            "cleanup": {
                "orphaned_entries": pending_missing,
                "recommendation": "Run cleanup first" if pending_missing > 100 else "OK"
            },
            "worker_status": _backfill_state
        }
    except Exception as e:
        logger.error(f"Error getting backfill stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backfill/cleanup")
async def cleanup_orphaned_entries():
    """Remove entries from unified-state where files no longer exist.

    Run this before backfill to clean up stale entries from deleted projects.
    """
    try:
        if not UNIFIED_STATE_FILE.exists():
            return {"error": "Unified state file not found"}

        async with aiofiles.open(UNIFIED_STATE_FILE, 'r') as f:
            state = json.loads(await f.read())

        files_data = state.get('files', {})
        original_count = len(files_data)
        orphaned = []

        for file_path in list(files_data.keys()):
            if not Path(file_path).exists():
                orphaned.append(file_path)
                del files_data[file_path]

        if orphaned:
            # Save updated state
            async with aiofiles.open(UNIFIED_STATE_FILE, 'w') as f:
                await f.write(json.dumps(state, indent=2))

        return {
            "success": True,
            "original_count": original_count,
            "removed_count": len(orphaned),
            "remaining_count": len(files_data),
            "sample_removed": orphaned[:5] if orphaned else []
        }
    except Exception as e:
        logger.error(f"Error cleaning orphaned entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backfill/start")
async def start_backfill(
    request: BackfillRequest,
    background_tasks: BackgroundTasks
):
    """Start a managed backfill process in the background.

    This submits batches with delays to avoid overwhelming the API.
    """
    global _backfill_state

    if _backfill_state["running"]:
        raise HTTPException(
            status_code=409,
            detail="Backfill already running. Check /backfill/status"
        )

    # Get pending conversations
    conversations = await batch_service.get_conversations_without_narrative(
        limit=request.batch_size * request.max_batches,
        validate_existence=True
    )

    if not conversations:
        return {
            "success": False,
            "message": "No conversations pending narrative generation"
        }

    # Calculate batches
    total_conversations = len(conversations)
    batches_to_submit = min(
        request.max_batches,
        (total_conversations + request.batch_size - 1) // request.batch_size
    )

    # Reset state
    _backfill_state = {
        "running": True,
        "started_at": datetime.now().isoformat(),
        "total_conversations": total_conversations,
        "batch_size": request.batch_size,
        "batches_to_submit": batches_to_submit,
        "batches_submitted": 0,
        "batches_completed": 0,
        "narratives_generated": 0,
        "errors": 0,
        "last_error": None,
        "model": request.model,
        "delay_between_batches": request.delay_between_batches
    }

    # Start background backfill
    background_tasks.add_task(
        run_backfill_batches,
        conversations,
        request.batch_size,
        batches_to_submit,
        request.model,
        request.delay_between_batches
    )

    return {
        "success": True,
        "message": f"Backfill started: {batches_to_submit} batches with {total_conversations} conversations",
        "status": _backfill_state
    }


@router.get("/backfill/status")
async def get_backfill_status():
    """Get current backfill status."""
    return _backfill_state


@router.post("/backfill/stop")
async def stop_backfill():
    """Stop the running backfill (completes current batch, stops after)."""
    global _backfill_state

    if not _backfill_state["running"]:
        return {"success": False, "message": "No backfill running"}

    _backfill_state["running"] = False
    return {
        "success": True,
        "message": "Backfill will stop after current batch completes",
        "status": _backfill_state
    }


async def run_backfill_batches(
    conversations: List[dict],
    batch_size: int,
    max_batches: int,
    model: str,
    delay_seconds: int
):
    """Background task to run backfill batches."""
    global _backfill_state

    try:
        for batch_num in range(max_batches):
            if not _backfill_state["running"]:
                logger.info("Backfill stopped by user")
                break

            start_idx = batch_num * batch_size
            end_idx = start_idx + batch_size
            batch_conversations = conversations[start_idx:end_idx]

            if not batch_conversations:
                break

            try:
                # Submit batch
                conversation_ids = [c['id'] for c in batch_conversations]
                job = await batch_service.submit_batch(
                    conversation_ids=conversation_ids,
                    project="backfill",
                    model=model
                )

                _backfill_state["batches_submitted"] += 1
                batch_id = job.get('batch_id')

                logger.info(
                    f"Backfill batch {batch_num + 1}/{max_batches} submitted: "
                    f"{len(conversation_ids)} conversations, job_id={batch_id}"
                )

                # Poll until complete
                for _ in range(1000):  # Max ~8 hours of polling
                    if not _backfill_state["running"]:
                        break

                    status_job = await batch_service.poll_and_update_status(batch_id)
                    status = status_job.get('status', '')

                    if status == 'completed':
                        _backfill_state["batches_completed"] += 1
                        _backfill_state["narratives_generated"] += status_job.get(
                            'completed_count', len(conversation_ids)
                        )
                        break
                    elif status == 'failed':
                        _backfill_state["errors"] += 1
                        _backfill_state["last_error"] = status_job.get('error')
                        break

                    await asyncio.sleep(30)

                # Delay before next batch
                if batch_num < max_batches - 1:
                    await asyncio.sleep(delay_seconds)

            except Exception as e:
                _backfill_state["errors"] += 1
                _backfill_state["last_error"] = str(e)
                logger.error(f"Backfill batch error: {e}")
                await asyncio.sleep(delay_seconds)

    finally:
        _backfill_state["running"] = False
        _backfill_state["finished_at"] = datetime.now().isoformat()
        logger.info(f"Backfill finished: {_backfill_state}")
