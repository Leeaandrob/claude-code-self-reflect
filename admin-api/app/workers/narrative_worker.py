#!/usr/bin/env python3
"""
Narrative Worker - Automatic narrative generation for conversations.

This worker monitors the unified-state for conversations without narratives
and automatically generates them using DashScope Batch API.

Architecture:
1. Scan unified-state for conversations with status=completed and no has_narrative
2. Filter out non-existent files (orphaned entries from deleted projects)
3. Group into batches (configurable size, default 50)
4. Submit to DashScope Batch API
5. Poll until completion
6. Process results and store narratives in Qdrant
7. Update unified-state with has_narrative=true
8. Periodically clean up orphaned entries
"""

import os
import sys
import json
import asyncio
import logging
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.batch_service import batch_service, UNIFIED_STATE_FILE
from app.services.narrative_service import narrative_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
BATCH_SIZE = int(os.getenv('NARRATIVE_BATCH_SIZE', '50'))
CHECK_INTERVAL_SECONDS = int(os.getenv('NARRATIVE_CHECK_INTERVAL', '300'))  # 5 minutes
POLL_INTERVAL_SECONDS = int(os.getenv('NARRATIVE_POLL_INTERVAL', '60'))  # 1 minute
MIN_CONVERSATIONS_FOR_BATCH = int(os.getenv('NARRATIVE_MIN_BATCH', '5'))
MAX_CONCURRENT_BATCHES = int(os.getenv('NARRATIVE_MAX_CONCURRENT', '3'))
NARRATIVE_MODEL = os.getenv('NARRATIVE_MODEL', 'qwen-plus')
COOLDOWN_AFTER_BATCH_MINUTES = int(os.getenv('NARRATIVE_COOLDOWN', '10'))
# Cleanup orphaned entries every N cycles (default: every 12 cycles = 1 hour with 5min interval)
CLEANUP_INTERVAL_CYCLES = int(os.getenv('NARRATIVE_CLEANUP_INTERVAL', '12'))
# Enable newest-first ordering (prioritize recent conversations)
NEWEST_FIRST = os.getenv('NARRATIVE_NEWEST_FIRST', 'true').lower() == 'true'

# Track active batches
active_batches: Dict[str, Dict[str, Any]] = {}
# Track cleanup cycles
_cleanup_cycle_counter = 0


async def cleanup_orphaned_entries() -> Tuple[int, int]:
    """
    Remove entries from unified-state where the source file no longer exists.
    Returns tuple of (total_checked, removed_count).

    Note: This function is resilient to permission errors - it will log
    a warning but not crash the worker if it cannot write to the state file.
    """
    if not UNIFIED_STATE_FILE.exists():
        return 0, 0

    try:
        async with aiofiles.open(UNIFIED_STATE_FILE, 'r') as f:
            state = json.loads(await f.read())
    except Exception as e:
        logger.warning(f"Could not read unified state for cleanup: {e}")
        return 0, 0

    files_data = state.get('files', {})
    original_count = len(files_data)
    orphaned_paths = []

    for file_path in files_data.keys():
        if not Path(file_path).exists():
            orphaned_paths.append(file_path)

    if orphaned_paths:
        for path in orphaned_paths:
            del files_data[path]

        try:
            # Save updated state
            async with aiofiles.open(UNIFIED_STATE_FILE, 'w') as f:
                await f.write(json.dumps(state, indent=2))

            logger.info(
                f"Cleanup: removed {len(orphaned_paths)} orphaned entries "
                f"(files no longer exist)"
            )
        except PermissionError:
            logger.warning(
                f"Permission denied writing unified-state. "
                f"Found {len(orphaned_paths)} orphaned entries but cannot remove. "
                f"Run cleanup via admin API instead."
            )
            return original_count, 0
        except Exception as e:
            logger.warning(f"Could not save cleanup results: {e}")
            return original_count, 0

    return original_count, len(orphaned_paths)


async def get_conversations_without_narrative(limit: int = 500) -> List[Dict[str, Any]]:
    """Get conversations that need narrative generation.

    Only returns conversations where:
    - status=completed
    - has_narrative is not set
    - chunks > 0
    - THE FILE ACTUALLY EXISTS on disk
    """
    if not UNIFIED_STATE_FILE.exists():
        logger.warning("Unified state file not found")
        return []

    async with aiofiles.open(UNIFIED_STATE_FILE, 'r') as f:
        state = json.loads(await f.read())

    files_data = state.get('files', {})
    conversations = []
    skipped_missing = 0
    skipped_has_narrative = 0
    skipped_not_completed = 0
    skipped_empty = 0

    for file_path, file_info in files_data.items():
        # Skip if already has narrative
        if file_info.get('has_narrative'):
            skipped_has_narrative += 1
            continue

        # Only process completed imports
        if file_info.get('status') != 'completed':
            skipped_not_completed += 1
            continue

        # Skip files with 0 chunks (empty conversations)
        if file_info.get('chunks', 0) == 0:
            skipped_empty += 1
            continue

        # CRITICAL FIX: Verify file exists before adding to list
        if not Path(file_path).exists():
            skipped_missing += 1
            continue

        # Extract project from collection name
        collection = file_info.get('collection', '')
        project = ''
        if collection.startswith('conv_'):
            parts = collection.split('_')
            if len(parts) >= 2:
                project = parts[1]

        # Get conversation ID from file path
        conv_id = Path(file_path).stem

        conversations.append({
            'id': conv_id,
            'path': file_path,
            'project': project,
            'collection': collection,
            'chunks': file_info.get('chunks', 0),
            'imported_at': file_info.get('imported_at', '')
        })

    # Sort by import date - NEWEST FIRST to prioritize recent conversations
    # This ensures new conversations get narratives quickly while backfill happens gradually
    conversations.sort(key=lambda x: x['imported_at'] or '', reverse=NEWEST_FIRST)

    logger.info(
        f"Conversations stats: "
        f"valid={len(conversations)}, "
        f"has_narrative={skipped_has_narrative}, "
        f"missing_file={skipped_missing}, "
        f"not_completed={skipped_not_completed}, "
        f"empty={skipped_empty}"
    )

    return conversations[:limit]


async def update_unified_state_narrative(conversation_ids: List[str], success: bool = True):
    """Update unified-state to mark conversations as having narratives."""
    if not UNIFIED_STATE_FILE.exists():
        return

    async with aiofiles.open(UNIFIED_STATE_FILE, 'r') as f:
        state = json.loads(await f.read())

    files_data = state.get('files', {})
    updated_count = 0

    for file_path, file_info in files_data.items():
        conv_id = Path(file_path).stem
        if conv_id in conversation_ids:
            file_info['has_narrative'] = success
            file_info['narrative_generated_at'] = datetime.now().isoformat()
            updated_count += 1

    # Save state
    async with aiofiles.open(UNIFIED_STATE_FILE, 'w') as f:
        await f.write(json.dumps(state, indent=2))

    logger.info(f"Updated {updated_count} conversations in unified-state")


async def process_batch_results(batch_id: str) -> int:
    """Process completed batch results and store narratives."""
    try:
        # Get batch info
        job = await batch_service.get_job(batch_id)
        project = job.get('project', 'unknown')
        conversation_ids = job.get('conversations', [])

        # Get results from DashScope
        results = await batch_service.get_batch_results(batch_id)

        stored_count = 0
        successful_ids = []
        failed_ids = []

        for result in results:
            conv_id = result.get('conversation_id')
            narrative = result.get('narrative')
            error = result.get('error')

            if error:
                logger.warning(f"Narrative generation failed for {conv_id}: {error}")
                failed_ids.append(conv_id)
                continue

            if narrative:
                try:
                    # Determine project from conversation
                    conv_project = project
                    if not conv_project or conv_project == 'unknown':
                        # Try to get from the conversations list in job
                        conv_project = 'default'

                    await narrative_service.store_narrative(
                        conversation_id=conv_id,
                        project=conv_project,
                        narrative=narrative,
                        tokens_used=result.get('tokens_used')
                    )
                    stored_count += 1
                    successful_ids.append(conv_id)
                except Exception as e:
                    logger.error(f"Failed to store narrative for {conv_id}: {e}")
                    failed_ids.append(conv_id)

        # Update unified-state
        if successful_ids:
            await update_unified_state_narrative(successful_ids, success=True)

        logger.info(
            f"Batch {batch_id}: stored {stored_count} narratives, "
            f"{len(failed_ids)} failed"
        )

        return stored_count

    except Exception as e:
        logger.error(f"Error processing batch results: {e}")
        return 0


async def poll_batch_until_complete(batch_id: str, max_wait_hours: int = 24) -> bool:
    """Poll a batch job until it completes or fails."""
    start_time = datetime.now()
    max_wait = timedelta(hours=max_wait_hours)

    while datetime.now() - start_time < max_wait:
        try:
            job = await batch_service.poll_and_update_status(batch_id)
            status = job.get('status', '')

            logger.info(
                f"Batch {batch_id}: status={status}, "
                f"progress={job.get('progress', 0)}%"
            )

            if status == 'completed':
                return True
            elif status == 'failed':
                logger.error(f"Batch {batch_id} failed: {job.get('error')}")
                return False

            # Wait before next poll
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

        except Exception as e:
            logger.error(f"Error polling batch {batch_id}: {e}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS * 2)

    logger.error(f"Batch {batch_id} timed out after {max_wait_hours} hours")
    return False


async def create_and_process_batch(conversations: List[Dict[str, Any]]) -> Optional[str]:
    """Create a batch job and wait for completion."""
    conversation_ids = [c['id'] for c in conversations]

    # Determine project (use first conversation's project or 'mixed')
    projects = set(c['project'] for c in conversations if c['project'])
    project = list(projects)[0] if len(projects) == 1 else 'mixed'

    logger.info(
        f"Creating batch for {len(conversation_ids)} conversations, "
        f"project={project}, model={NARRATIVE_MODEL}"
    )

    try:
        # Submit batch
        job = await batch_service.submit_batch(
            conversation_ids=conversation_ids,
            project=project,
            model=NARRATIVE_MODEL
        )

        batch_id = job.get('batch_id')
        if not batch_id:
            logger.error("Failed to get batch_id from job submission")
            return None

        logger.info(f"Created batch {batch_id}")

        # Track active batch
        active_batches[batch_id] = {
            'created_at': datetime.now().isoformat(),
            'conversations': len(conversation_ids),
            'project': project
        }

        # Poll until complete
        success = await poll_batch_until_complete(batch_id)

        if success:
            # Process results
            stored = await process_batch_results(batch_id)
            logger.info(f"Batch {batch_id} completed: {stored} narratives stored")
        else:
            logger.error(f"Batch {batch_id} did not complete successfully")

        # Remove from active batches
        active_batches.pop(batch_id, None)

        return batch_id

    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        return None


async def run_worker_cycle():
    """Run one cycle of the worker."""
    # Check if we have room for more batches
    if len(active_batches) >= MAX_CONCURRENT_BATCHES:
        logger.info(
            f"Max concurrent batches reached ({MAX_CONCURRENT_BATCHES}), "
            f"waiting..."
        )
        return

    # Get conversations without narratives
    conversations = await get_conversations_without_narrative(limit=BATCH_SIZE)

    if len(conversations) < MIN_CONVERSATIONS_FOR_BATCH:
        logger.info(
            f"Not enough conversations for batch "
            f"({len(conversations)} < {MIN_CONVERSATIONS_FOR_BATCH})"
        )
        return

    # Take up to BATCH_SIZE conversations
    batch_conversations = conversations[:BATCH_SIZE]

    # Create and process batch
    await create_and_process_batch(batch_conversations)


async def worker_loop():
    """Main worker loop."""
    global _cleanup_cycle_counter

    logger.info("=" * 60)
    logger.info("Narrative Worker Starting")
    logger.info("=" * 60)
    logger.info(f"Configuration:")
    logger.info(f"  BATCH_SIZE: {BATCH_SIZE}")
    logger.info(f"  CHECK_INTERVAL: {CHECK_INTERVAL_SECONDS}s")
    logger.info(f"  POLL_INTERVAL: {POLL_INTERVAL_SECONDS}s")
    logger.info(f"  MIN_CONVERSATIONS: {MIN_CONVERSATIONS_FOR_BATCH}")
    logger.info(f"  MAX_CONCURRENT: {MAX_CONCURRENT_BATCHES}")
    logger.info(f"  MODEL: {NARRATIVE_MODEL}")
    logger.info(f"  COOLDOWN: {COOLDOWN_AFTER_BATCH_MINUTES}min")
    logger.info(f"  CLEANUP_INTERVAL: every {CLEANUP_INTERVAL_CYCLES} cycles")
    logger.info(f"  NEWEST_FIRST: {NEWEST_FIRST}")
    logger.info("=" * 60)

    # Run initial cleanup on startup
    logger.info("Running initial cleanup of orphaned entries...")
    total, removed = await cleanup_orphaned_entries()
    logger.info(f"Initial cleanup: {removed}/{total} orphaned entries removed")

    while True:
        try:
            # Periodic cleanup of orphaned entries
            _cleanup_cycle_counter += 1
            if _cleanup_cycle_counter >= CLEANUP_INTERVAL_CYCLES:
                _cleanup_cycle_counter = 0
                logger.info("Running periodic cleanup of orphaned entries...")
                await cleanup_orphaned_entries()

            await run_worker_cycle()
        except Exception as e:
            logger.error(f"Error in worker cycle: {e}")

        # Wait before next check
        logger.info(f"Waiting {CHECK_INTERVAL_SECONDS}s before next check...")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def main():
    """Entry point."""
    # Check required environment
    if not os.getenv('DASHSCOPE_API_KEY'):
        logger.error("DASHSCOPE_API_KEY is required")
        sys.exit(1)

    await worker_loop()


if __name__ == '__main__':
    asyncio.run(main())
