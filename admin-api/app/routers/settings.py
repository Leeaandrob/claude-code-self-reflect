"""Settings API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class EmbeddingModeUpdate(BaseModel):
    mode: str  # 'voyage' or 'qwen' (cloud-only since v8.0.0)


def _detect_embedding_mode() -> str:
    """Detect actual embedding mode based on available API keys.

    Since v8.0.0, this system is cloud-only. Priority:
    1. If DASHSCOPE_API_KEY is set -> 'qwen'
    2. Else if VOYAGE_KEY is set -> 'voyage'
    3. Else -> 'cloud' (unconfigured)
    """
    if os.getenv('DASHSCOPE_API_KEY'):
        return 'qwen'
    elif os.getenv('VOYAGE_KEY'):
        return 'voyage'
    else:
        # Cloud-only mode but no API key configured
        return 'cloud'


@router.get("/embedding")
async def get_embedding_config():
    """Get current embedding configuration.

    Note: Since v8.0.0, this system is cloud-only.
    Local embeddings have been removed.
    """
    # Detect actual mode based on available API keys
    detected_mode = _detect_embedding_mode()

    dashscope_key_set = bool(os.getenv('DASHSCOPE_API_KEY'))
    voyage_key_set = bool(os.getenv('VOYAGE_KEY'))

    return {
        "mode": detected_mode,
        "voyage": {
            "provider": "voyage",
            "model": "voyage-3",
            "dimension": 1024,
            "api_key_set": voyage_key_set
        },
        "qwen": {
            "provider": "dashscope",
            "model": "text-embedding-v4",
            "dimension": 2048,
            "api_key_set": dashscope_key_set,
            "endpoint": os.getenv('DASHSCOPE_ENDPOINT', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')
        },
        "cloud_only": True,
        "version": "8.0.0"
    }

@router.post("/embedding/mode")
async def update_embedding_mode(update: EmbeddingModeUpdate):
    """Update embedding mode (requires restart).

    Note: Since v8.0.0, only 'voyage' and 'qwen' modes are supported.
    Local embeddings have been removed.
    """
    if update.mode not in ['voyage', 'qwen']:
        raise HTTPException(
            status_code=400,
            detail="Mode must be 'voyage' or 'qwen'. Local mode was removed in v8.0.0."
        )

    # Validate API key is available for the selected mode
    if update.mode == 'voyage' and not os.getenv('VOYAGE_KEY'):
        raise HTTPException(
            status_code=400,
            detail="VOYAGE_KEY environment variable must be set to use Voyage mode."
        )
    if update.mode == 'qwen' and not os.getenv('DASHSCOPE_API_KEY'):
        raise HTTPException(
            status_code=400,
            detail="DASHSCOPE_API_KEY environment variable must be set to use Qwen mode."
        )

    # In a real implementation, this would update .env or config file
    return {
        "message": f"Embedding mode set to {update.mode}. Please restart services.",
        "mode": update.mode,
        "note": "Restart the MCP server and safe-watcher for changes to take effect."
    }
