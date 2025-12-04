"""Narrative search tools for Claude Self Reflect MCP server.

These tools provide hybrid search capabilities that combine traditional
chunk-based search with AI-generated narrative summaries for richer context.
"""

import os
import logging
import hashlib
import aiohttp
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastmcp import Context

logger = logging.getLogger(__name__)

# Configuration
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')
DASHSCOPE_EMBEDDING_URL = os.getenv(
    'DASHSCOPE_EMBEDDING_URL',
    'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/embeddings'
)
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-v3')


class NarrativeTools:
    """Handles narrative search operations for the MCP server."""

    def __init__(
        self,
        qdrant_url: str = QDRANT_URL,
        api_key: str = DASHSCOPE_API_KEY,
    ):
        self.qdrant_url = qdrant_url
        self.api_key = api_key

    def _get_narrative_collection_name(self, project: str) -> str:
        """Get the narratives collection name for a project."""
        project_hash = hashlib.md5(project.encode()).hexdigest()[:12]
        return f"narratives_{project_hash}"

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using DashScope."""
        if not self.api_key:
            raise Exception("DASHSCOPE_API_KEY not configured")

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        if len(text) > 8000:
            text = text[:8000]

        data = {
            "model": EMBEDDING_MODEL,
            "input": text,
            "encoding_format": "float"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                DASHSCOPE_EMBEDDING_URL,
                headers=headers,
                json=data
            ) as response:
                if response.status >= 400:
                    error = await response.text()
                    raise Exception(f"Embedding API error: {error}")

                result = await response.json()
                return result['data'][0]['embedding']

    async def _list_narrative_collections(self) -> List[str]:
        """List all narrative collections."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.qdrant_url}/collections") as response:
                if response.status >= 400:
                    return []
                result = await response.json()
                collections = result.get('result', {}).get('collections', [])
                return [
                    c['name'] for c in collections
                    if c['name'].startswith('narratives_')
                ]

    async def _search_narrative_collection(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int,
        min_score: float
    ) -> List[Dict[str, Any]]:
        """Search a single narrative collection."""
        search_request = {
            "vector": query_embedding,
            "limit": limit,
            "with_payload": True,
            "score_threshold": min_score
        }

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

    async def search_narratives(
        self,
        ctx: Context,
        query: str,
        project: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.3
    ) -> str:
        """
        Search AI-generated narratives for past conversations.

        Narratives provide high-level context about what was done, decisions made,
        and solutions implemented - perfect for understanding past work quickly.

        Args:
            query: Semantic search query (e.g., "authentication bug fix")
            project: Specific project or None for all
            limit: Maximum results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            XML-formatted narrative search results
        """
        await ctx.debug(f"Searching narratives for: {query}")

        try:
            # Get query embedding
            query_embedding = await self._get_embedding(query)

            # Get collections to search
            if project and project != 'all':
                collections = [self._get_narrative_collection_name(project)]
            else:
                collections = await self._list_narrative_collections()

            if not collections:
                return """<narrative_search>
<message>No narrative collections found. Use Batch Jobs to generate narratives.</message>
<hint>Go to Admin Panel > Batch Jobs to create narrative generation jobs.</hint>
</narrative_search>"""

            # Search all collections
            all_results = []
            for collection in collections:
                try:
                    results = await self._search_narrative_collection(
                        collection, query_embedding, limit, min_score
                    )
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Error searching {collection}: {e}")

            # Sort by score
            all_results.sort(key=lambda x: x['score'], reverse=True)
            all_results = all_results[:limit]

            if not all_results:
                return f"""<narrative_search>
<query>{query}</query>
<message>No matching narratives found</message>
<suggestion>Try broader search terms or generate narratives for more conversations</suggestion>
</narrative_search>"""

            # Format results
            output = f"""<narrative_search>
<query>{query}</query>
<results_count>{len(all_results)}</results_count>
<narratives>
"""
            for i, result in enumerate(all_results, 1):
                output += f"""  <narrative index="{i}">
    <score>{result['score']:.3f}</score>
    <conversation_id>{result.get('conversation_id', 'N/A')}</conversation_id>
    <project>{result.get('project', 'N/A')}</project>
    <summary>{result.get('summary', 'No summary')}</summary>
"""
                if result.get('problem'):
                    output += f"    <problem>{result['problem']}</problem>\n"
                if result.get('solution'):
                    output += f"    <solution>{result['solution']}</solution>\n"
                if result.get('decisions'):
                    decisions = result['decisions']
                    if isinstance(decisions, list):
                        output += f"    <decisions>{', '.join(decisions)}</decisions>\n"
                if result.get('files_modified'):
                    files = result['files_modified']
                    if isinstance(files, list):
                        output += f"    <files_modified>{', '.join(files)}</files_modified>\n"
                if result.get('key_insights'):
                    insights = result['key_insights']
                    if isinstance(insights, list):
                        output += f"    <key_insights>{', '.join(insights)}</key_insights>\n"
                if result.get('tags'):
                    tags = result['tags']
                    if isinstance(tags, list):
                        output += f"    <tags>{', '.join(tags)}</tags>\n"
                output += f"    <complexity>{result.get('complexity', 'N/A')}</complexity>\n"
                output += f"    <outcome>{result.get('outcome', 'N/A')}</outcome>\n"
                output += "  </narrative>\n"

            output += "</narratives>\n</narrative_search>"
            return output

        except Exception as e:
            logger.error(f"Narrative search failed: {e}", exc_info=True)
            return f"""<narrative_search>
<error>Search failed: {str(e)}</error>
</narrative_search>"""

    async def hybrid_search(
        self,
        ctx: Context,
        query: str,
        search_tools,  # Reference to SearchTools instance
        project: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.3,
        include_narratives: bool = True,
        include_chunks: bool = True
    ) -> str:
        """
        Perform hybrid search combining narratives and conversation chunks.

        This provides the best of both worlds:
        - Narratives: High-level context, decisions, solutions
        - Chunks: Specific code, detailed discussions

        Args:
            query: Semantic search query
            search_tools: SearchTools instance for chunk search
            project: Specific project or None for all
            limit: Maximum results per category
            min_score: Minimum similarity score
            include_narratives: Include narrative results
            include_chunks: Include chunk results

        Returns:
            XML-formatted combined search results
        """
        await ctx.debug(f"Hybrid search for: {query}")

        output = f"""<hybrid_search>
<query>{query}</query>
"""

        # Search narratives
        if include_narratives:
            try:
                narrative_results = await self.search_narratives(
                    ctx, query, project, limit, min_score
                )
                # Extract just the narratives section
                if "<narratives>" in narrative_results:
                    start = narrative_results.find("<narratives>")
                    end = narrative_results.find("</narratives>") + len("</narratives>")
                    output += narrative_results[start:end] + "\n"
                else:
                    output += "<narratives><message>No narratives found</message></narratives>\n"
            except Exception as e:
                output += f"<narratives><error>{str(e)}</error></narratives>\n"

        # Search chunks using existing search tools
        if include_chunks and search_tools:
            try:
                # Use the existing reflect_on_past search
                chunk_results = await search_tools.reflect_on_past(
                    ctx=ctx,
                    query=query,
                    limit=limit,
                    min_score=min_score,
                    project=project,
                    mode='full',
                    brief=False,
                    use_decay=-1,
                    response_format='xml',
                    include_raw=False
                )
                # Wrap in chunks tag
                output += "<chunks>\n"
                output += chunk_results
                output += "\n</chunks>\n"
            except Exception as e:
                output += f"<chunks><error>{str(e)}</error></chunks>\n"

        output += "</hybrid_search>"
        return output

    async def get_narrative_stats(
        self,
        ctx: Context,
        project: Optional[str] = None
    ) -> str:
        """
        Get statistics about stored narratives.

        Args:
            project: Specific project or None for all

        Returns:
            XML-formatted narrative statistics
        """
        await ctx.debug("Getting narrative stats")

        try:
            if project and project != 'all':
                collections = [self._get_narrative_collection_name(project)]
            else:
                collections = await self._list_narrative_collections()

            total = 0
            collection_stats = []

            for collection in collections:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{self.qdrant_url}/collections/{collection}"
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                count = result.get('result', {}).get('points_count', 0)
                                total += count
                                collection_stats.append({
                                    "name": collection,
                                    "count": count
                                })
                except Exception:
                    pass

            output = f"""<narrative_stats>
<total_narratives>{total}</total_narratives>
<collections_count>{len(collection_stats)}</collections_count>
<collections>
"""
            for cs in collection_stats:
                output += f"  <collection name=\"{cs['name']}\">{cs['count']}</collection>\n"
            output += """</collections>
</narrative_stats>"""
            return output

        except Exception as e:
            return f"<narrative_stats><error>{str(e)}</error></narrative_stats>"


# Singleton instance
narrative_tools = NarrativeTools()
