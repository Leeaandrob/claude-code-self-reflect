# Batch Processing Tools

Operational tools for v7.0 AI-powered narrative generation via Anthropic Batch API.

## Files

### batch_import_all_projects.py (16KB)
**Purpose:** Create batch jobs for all projects
**Usage:** Generates batch requests for AI narrative generation
**Integration:** Used by `batch-automation` Docker profile

**Key Features:**
- Scans all projects for eligible conversations
- Creates batch job files in `~/.claude-self-reflect/batch_queue/`
- Submits to Anthropic Batch API
- Triggers when 10+ conversations detected

### recover_batch_results.py (8.9KB)
**Purpose:** Recover results from completed batch jobs
**Usage:** Poll Anthropic API and import narrative results
**Integration:** Used by `batch_monitor.py` service

**Key Features:**
- Polls batch job status
- Downloads completed results
- Imports enhanced narratives into Qdrant
- Updates conversation embeddings

### recover_all_batches.py (9.9KB)
**Purpose:** Bulk recovery for multiple batch jobs
**Usage:** Recover all pending/completed batches
**When to use:** After service interruptions or manual batch submission

### import_existing_batch.py (6.5KB)
**Purpose:** Import pre-existing batch results
**Usage:** Manual import of batch API responses
**When to use:** Debugging or manual batch processing

## Architecture

```
User Conversations (JSONL)
    ↓
[batch_watcher.py] → Detects 10+ conversations
    ↓
[batch_import_all_projects.py] → Creates batch job
    ↓
Anthropic Batch API (24h processing)
    ↓
[batch_monitor.py] → Polls for completion
    ↓
[recover_batch_results.py] → Imports narratives
    ↓
Qdrant (enhanced embeddings with 9.3x relevance)
```

## Related Services

- **src/runtime/batch_watcher.py** - Auto-trigger on conversation threshold
- **src/runtime/batch_monitor.py** - API polling daemon
- **Docker profile:** `batch-automation` (requires ANTHROPIC_API_KEY)

## AI Narrative Benefits

**Before:** Raw conversation excerpts (0.074 relevance score)
```
"User: Fix Docker issue\nAssistant: Container limited to 2GB..."
```

**After:** Rich problem-solution summaries (0.691 relevance - 9.3x improvement)
```
PROBLEM: Docker memory investigation for container limits
SOLUTION: Implemented resource constraints in docker-compose
TOOLS: Docker, grep, Edit
CONCEPTS: container-memory, resource-limits
FILES: docker-compose.yaml
```

## Requirements

- ANTHROPIC_API_KEY environment variable
- Qdrant collection with existing conversations
- 10+ conversations per project (auto-trigger threshold)

## Development Notes

**Moved from:** `docs/design/` (2025-11-12)
**Reason:** These are operational tools, not design documents
**Status:** Active in v7.0 production

---

*For design prototypes, see `docs/design/`*
*For evaluation tools, see `scripts/evaluation/`*
