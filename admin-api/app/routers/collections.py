"""Qdrant collections API endpoints."""
from fastapi import APIRouter, HTTPException
from qdrant_client import AsyncQdrantClient
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')

@router.get("/")
async def list_collections():
    """List all Qdrant collections."""
    client = None
    try:
        client = AsyncQdrantClient(url=QDRANT_URL)
        collections = await client.get_collections()
        result = []
        for coll in collections.collections:
            info = await client.get_collection(coll.name)
            result.append({
                "name": coll.name,
                "vectors_count": info.vectors_count or 0,
                "points_count": info.points_count or 0,
                "segments_count": info.segments_count or 0,
                "status": info.status,
                "config": {
                    "params": {
                        "vectors": {
                            "size": info.config.params.vectors.size,
                            "distance": info.config.params.vectors.distance.value
                        }
                    }
                }
            })
        return result
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if client:
            await client.close()

@router.get("/{collection_name}")
async def get_collection_info(collection_name: str):
    """Get detailed information about a collection."""
    client = None
    try:
        client = AsyncQdrantClient(url=QDRANT_URL)
        info = await client.get_collection(collection_name)
        return {
            "name": collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "segments_count": info.segments_count,
            "status": info.status,
            "config": info.config.dict()
        }
    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if client:
            await client.close()
