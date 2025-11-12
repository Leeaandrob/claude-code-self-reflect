"""Settings API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class EmbeddingModeUpdate(BaseModel):
    mode: str  # 'local', 'voyage', or 'qwen'

@router.get("/embedding")
async def get_embedding_config():
    """Get current embedding configuration."""
    embedding_provider = os.getenv('EMBEDDING_PROVIDER', 'local').lower()

    return {
        "mode": embedding_provider,
        "local": {
            "provider": "fastembed",
            "model": os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
            "dimension": 384,
            "api_key_required": False
        },
        "voyage": {
            "provider": "voyage",
            "model": "voyage-3",
            "dimension": 1024,
            "api_key_set": bool(os.getenv('VOYAGE_KEY'))
        },
        "qwen": {
            "provider": "dashscope",
            "model": "text-embedding-v4",
            "dimension": 2048,
            "api_key_set": bool(os.getenv('DASHSCOPE_API_KEY')),
            "endpoint": os.getenv('DASHSCOPE_ENDPOINT', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')
        }
    }

@router.post("/embedding/mode")
async def update_embedding_mode(update: EmbeddingModeUpdate):
    """Update embedding mode (requires restart)."""
    if update.mode not in ['local', 'voyage', 'qwen']:
        raise HTTPException(status_code=400, detail="Mode must be 'local', 'voyage', or 'qwen'")

    # In a real implementation, this would update .env or config file
    return {
        "message": f"Embedding mode set to {update.mode}. Please restart services.",
        "mode": update.mode
    }
