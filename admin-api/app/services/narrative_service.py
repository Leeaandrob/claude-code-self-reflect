"""Narrative storage and retrieval service using Qdrant."""
import os
import json
import hashlib
import logging
import aiohttp
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Qdrant configuration
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')
DASHSCOPE_EMBEDDING_URL = os.getenv(
    'DASHSCOPE_EMBEDDING_URL',
    'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/embeddings'
)
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-v3')
EMBEDDING_DIMENSION = 1024  # Qwen embedding dimension (1024d for consistency with conv collections)


class NarrativeService:
    """Service for storing and retrieving conversation narratives in Qdrant."""

    def __init__(self):
        self.qdrant_url = QDRANT_URL
        self.api_key = DASHSCOPE_API_KEY
        self.embedding_url = DASHSCOPE_EMBEDDING_URL

    def _get_collection_name(self, project: str) -> str:
        """Get the narratives collection name for a project."""
        project_hash = hashlib.md5(project.encode()).hexdigest()[:12]
        return f"narratives_{project_hash}"

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using DashScope."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # Truncate text if too long
        if len(text) > 8000:
            text = text[:8000]

        data = {
            "model": EMBEDDING_MODEL,
            "input": text,
            "encoding_format": "float",
            "dimensions": EMBEDDING_DIMENSION
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.embedding_url,
                headers=headers,
                json=data
            ) as response:
                if response.status >= 400:
                    error = await response.text()
                    raise Exception(f"Embedding API error: {error}")

                result = await response.json()
                return result['data'][0]['embedding']

    async def ensure_collection(self, project: str) -> str:
        """Ensure narratives collection exists for project."""
        collection_name = self._get_collection_name(project)

        # Check if collection exists
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.qdrant_url}/collections/{collection_name}"
            ) as response:
                if response.status == 200:
                    return collection_name

        # Create collection
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.qdrant_url}/collections/{collection_name}",
                json={
                    "vectors": {
                        "size": EMBEDDING_DIMENSION,
                        "distance": "Cosine"
                    }
                }
            ) as response:
                if response.status >= 400:
                    error = await response.text()
                    raise Exception(f"Failed to create collection: {error}")

        # Create payload indexes for efficient filtering
        indexes = ["conversation_id", "project", "outcome", "complexity"]
        for field in indexes:
            async with aiohttp.ClientSession() as session:
                await session.put(
                    f"{self.qdrant_url}/collections/{collection_name}/index",
                    json={
                        "field_name": field,
                        "field_schema": "keyword"
                    }
                )

        logger.info(f"Created narratives collection: {collection_name}")
        return collection_name

    async def store_narrative(
        self,
        conversation_id: str,
        project: str,
        narrative: Dict[str, Any],
        tokens_used: Optional[Dict] = None
    ) -> str:
        """Store a narrative in Qdrant."""
        collection_name = await self.ensure_collection(project)

        # Create searchable text from narrative
        searchable_text = self._create_searchable_text(narrative)

        # Get embedding
        embedding = await self._get_embedding(searchable_text)

        # Create point ID from conversation_id
        point_id = int(hashlib.md5(conversation_id.encode()).hexdigest()[:16], 16)

        # Prepare payload
        payload = {
            "conversation_id": conversation_id,
            "project": project,
            "summary": narrative.get("summary", ""),
            "problem": narrative.get("problem", ""),
            "solution": narrative.get("solution", ""),
            "decisions": narrative.get("decisions", []),
            "files_modified": narrative.get("files_modified", []),
            "key_insights": narrative.get("key_insights", []),
            "tags": narrative.get("tags", []),
            "complexity": narrative.get("complexity", "medium"),
            "outcome": narrative.get("outcome", "success"),
            "tokens_used": tokens_used or {},
            "created_at": datetime.now().isoformat(),
            "searchable_text": searchable_text
        }

        # Upsert point
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.qdrant_url}/collections/{collection_name}/points",
                json={
                    "points": [{
                        "id": point_id,
                        "vector": embedding,
                        "payload": payload
                    }]
                }
            ) as response:
                if response.status >= 400:
                    error = await response.text()
                    raise Exception(f"Failed to store narrative: {error}")

        logger.info(f"Stored narrative for conversation {conversation_id}")
        return str(point_id)

    def _create_searchable_text(self, narrative: Dict[str, Any]) -> str:
        """Create searchable text from narrative components."""
        parts = []

        if narrative.get("summary"):
            parts.append(f"Summary: {narrative['summary']}")

        if narrative.get("problem"):
            parts.append(f"Problem: {narrative['problem']}")

        if narrative.get("solution"):
            parts.append(f"Solution: {narrative['solution']}")

        if narrative.get("decisions"):
            parts.append(f"Decisions: {', '.join(narrative['decisions'])}")

        if narrative.get("files_modified"):
            parts.append(f"Files: {', '.join(narrative['files_modified'])}")

        if narrative.get("key_insights"):
            parts.append(f"Insights: {', '.join(narrative['key_insights'])}")

        if narrative.get("tags"):
            parts.append(f"Tags: {', '.join(narrative['tags'])}")

        return " | ".join(parts)

    async def search_narratives(
        self,
        query: str,
        project: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.3,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Search narratives by semantic similarity."""
        # Get query embedding
        query_embedding = await self._get_embedding(query)

        # Build search request
        search_request = {
            "vector": query_embedding,
            "limit": limit,
            "with_payload": True,
            "score_threshold": min_score
        }

        # Add filters if specified
        if filters or project:
            must_conditions = []

            if project:
                must_conditions.append({
                    "key": "project",
                    "match": {"value": project}
                })

            if filters:
                for key, value in filters.items():
                    must_conditions.append({
                        "key": key,
                        "match": {"value": value}
                    })

            if must_conditions:
                search_request["filter"] = {"must": must_conditions}

        # Search in all narrative collections or specific project
        results = []

        if project:
            collection_name = self._get_collection_name(project)
            results.extend(
                await self._search_collection(collection_name, search_request)
            )
        else:
            # Search all narrative collections
            collections = await self._list_narrative_collections()
            for collection_name in collections:
                try:
                    results.extend(
                        await self._search_collection(collection_name, search_request)
                    )
                except Exception as e:
                    logger.warning(f"Error searching {collection_name}: {e}")

        # Sort by score and limit
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]

    async def _search_collection(
        self,
        collection_name: str,
        search_request: Dict
    ) -> List[Dict[str, Any]]:
        """Search a single collection."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.qdrant_url}/collections/{collection_name}/points/search",
                json=search_request
            ) as response:
                if response.status >= 400:
                    return []

                result = await response.json()
                return [
                    {
                        "id": str(hit['id']),
                        "score": hit['score'],
                        "collection": collection_name,
                        **hit.get('payload', {})
                    }
                    for hit in result.get('result', [])
                ]

    async def _list_narrative_collections(self) -> List[str]:
        """List all narrative collections."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.qdrant_url}/collections"
            ) as response:
                if response.status >= 400:
                    return []

                result = await response.json()
                collections = result.get('result', {}).get('collections', [])
                return [
                    c['name'] for c in collections
                    if c['name'].startswith('narratives_')
                ]

    async def get_narrative(
        self,
        conversation_id: str,
        project: str
    ) -> Optional[Dict[str, Any]]:
        """Get narrative for a specific conversation."""
        collection_name = self._get_collection_name(project)
        point_id = int(hashlib.md5(conversation_id.encode()).hexdigest()[:16], 16)

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.qdrant_url}/collections/{collection_name}/points/{point_id}"
            ) as response:
                if response.status == 404:
                    return None
                if response.status >= 400:
                    return None

                result = await response.json()
                point = result.get('result')
                if point:
                    return point.get('payload')
                return None

    async def delete_narrative(
        self,
        conversation_id: str,
        project: str
    ) -> bool:
        """Delete a narrative."""
        collection_name = self._get_collection_name(project)
        point_id = int(hashlib.md5(conversation_id.encode()).hexdigest()[:16], 16)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.qdrant_url}/collections/{collection_name}/points/delete",
                json={"points": [point_id]}
            ) as response:
                return response.status < 400

    async def get_stats(self, project: Optional[str] = None) -> Dict[str, Any]:
        """Get narrative statistics."""
        if project:
            collections = [self._get_collection_name(project)]
        else:
            collections = await self._list_narrative_collections()

        stats = {
            "total_narratives": 0,
            "collections": [],
            "by_outcome": {},
            "by_complexity": {}
        }

        for collection_name in collections:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.qdrant_url}/collections/{collection_name}"
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            count = result.get('result', {}).get('points_count', 0)
                            stats['total_narratives'] += count
                            stats['collections'].append({
                                "name": collection_name,
                                "count": count
                            })
            except Exception as e:
                logger.warning(f"Error getting stats for {collection_name}: {e}")

        return stats


# Singleton instance
narrative_service = NarrativeService()
