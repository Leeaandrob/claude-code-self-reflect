"""Dashboard API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
import logging

from qdrant_client import AsyncQdrantClient

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
# Use STATE_FILE env var (set by docker-compose) or fallback to default
UNIFIED_STATE_FILE = Path(os.getenv('STATE_FILE', str(Path.home() / '.claude-self-reflect' / 'config' / 'unified-state.json')))

async def get_qdrant_client():
    """Get Qdrant client instance."""
    return AsyncQdrantClient(url=QDRANT_URL)

async def load_unified_state() -> Dict[str, Any]:
    """Load unified state from JSON file."""
    try:
        if UNIFIED_STATE_FILE.exists():
            with open(UNIFIED_STATE_FILE, 'r') as f:
                return json.load(f)
        return {"files": {}, "projects": {}}
    except Exception as e:
        logger.error(f"Error loading unified state: {e}")
        return {"files": {}, "projects": {}}

@router.get("/metrics")
async def get_dashboard_metrics():
    """Get all system metrics for dashboard."""
    try:
        # Load unified state
        state = await load_unified_state()

        # Get Qdrant stats
        qdrant_stats = {"status": "disconnected", "collections_count": 0, "total_vectors": 0}
        client = None
        try:
            client = AsyncQdrantClient(url=QDRANT_URL)
            collections = await client.get_collections()
            total_points = 0
            for coll in collections.collections:
                info = await client.get_collection(coll.name)
                total_points += info.points_count or 0

            qdrant_stats = {
                "status": "connected",
                "collections_count": len(collections.collections),
                "total_vectors": total_points
            }
        except Exception as e:
            logger.error(f"Qdrant connection error: {e}")
        finally:
            if client:
                await client.close()

        # Calculate import stats
        files = state.get("files", {})
        projects = state.get("projects", {})

        # If unified state is empty but Qdrant has data, use Qdrant stats
        if (not files or len(files) == 0) and qdrant_stats["total_vectors"] > 0:
            total_files = qdrant_stats["collections_count"]
            total_messages = qdrant_stats["total_vectors"]
            projects_count = 1  # legacy-imports
        else:
            total_files = len(files)
            total_messages = sum(f.get("message_count", 0) for f in files.values())
            projects_count = len(projects)

        # Detect embedding mode based on available API keys (same logic as settings.py)
        # Since v8.0.0, this system is cloud-only
        if os.getenv('DASHSCOPE_API_KEY'):
            embedding_mode = "qwen"
            embedding_model = "text-embedding-v4"
            embedding_dimension = 2048
        elif os.getenv('VOYAGE_KEY'):
            embedding_mode = "voyage"
            embedding_model = "voyage-3"
            embedding_dimension = 1024
        else:
            # Cloud-only mode but no API key configured
            embedding_mode = "cloud"
            embedding_model = "not configured"
            embedding_dimension = 0

        # Memory usage (simplified)
        import psutil
        memory = psutil.virtual_memory()

        return {
            "qdrant": qdrant_stats,
            "embedding": {
                "mode": embedding_mode,
                "model": embedding_model,
                "dimension": embedding_dimension
            },
            "import": {
                "total_files": total_files,
                "imported_files": total_files,
                "pending_files": 0,
                "total_messages": total_messages,
                "import_progress": 100.0 if total_files > 0 else 0.0
            },
            "memory": {
                "used": memory.used,
                "total": memory.total,
                "percentage": memory.percent
            },
            "projects_count": projects_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_system_stats():
    """Get detailed system statistics."""
    try:
        state = await load_unified_state()
        projects = state.get("projects", {})
        files = state.get("files", {})

        # Always use unified state data if available
        # Even if projects dict is empty, we may have files data
        if files and len(files) > 0:
            # Extract recent imports from files (only completed ones)
            recent_files = []
            for file_path, file_data in files.items():
                # Skip files that are not completed
                if file_data.get("status") != "completed":
                    continue

                # Extract project name from file path
                # Path format: /logs/-home-leeaandrob-Projects-Personal-project-name/file.jsonl
                project_name = ""

                if "/logs/" in file_path:
                    path_parts = file_path.split("/logs/")[1] if len(file_path.split("/logs/")) > 1 else ""
                    if "/" in path_parts:
                        dir_path = path_parts.rsplit("/", 1)[0]
                        if dir_path.startswith("-"):
                            parts = dir_path.split("-")
                            meta_folders = ["home", "projects", "personal", "paradigma", "researchmagic"]
                            last_meta_index = -1
                            for i, part in enumerate(parts):
                                if part.lower() in meta_folders:
                                    last_meta_index = i
                            if last_meta_index >= 0 and last_meta_index + 1 < len(parts):
                                project_name = "-".join(parts[last_meta_index + 1:])
                            else:
                                project_name = dir_path.lstrip("-")
                        else:
                            project_name = dir_path

                # Fallback: try collection (for newer format)
                if not project_name:
                    collection = file_data.get("collection", "")
                    if collection.startswith("csr_"):
                        project_part = collection[4:]
                        for suffix in ["_qwen_2048d", "_qwen_1024d", "_voyage_1024d", "_local_384d"]:
                            if suffix in project_part:
                                project_name = project_part.replace(suffix, "")
                                break

                # Get filename
                filename = file_path.split("/")[-1] if "/" in file_path else file_path

                # Estimate messages
                chunks = file_data.get("chunks", 0)
                estimated_messages = chunks * 50

                recent_files.append({
                    "path": filename,
                    "project": project_name,
                    "imported_at": file_data.get("imported_at") or datetime.now().isoformat(),
                    "message_count": estimated_messages
                })

            # Sort by imported_at descending (handle None values)
            recent_files.sort(key=lambda x: x["imported_at"] or "", reverse=True)

            # If we have recent files from unified state, use them
            return {
                "top_projects": [{
                    "name": "mixed-projects",
                    "message_count": sum(f["message_count"] for f in recent_files),
                    "file_count": len(recent_files)
                }],
                "recent_imports": recent_files[:10],
                "total_projects": len(set(f["project"] for f in recent_files if f["project"])),
                "total_files": len(files)
            }

        # Fallback to Qdrant only if no unified state data at all
        logger.info("Unified state empty, reading from Qdrant for stats")
        client = None
        try:
            client = AsyncQdrantClient(url=QDRANT_URL)
            collections = await client.get_collections()

            # Get collection stats
            collection_stats = []
            for coll in collections.collections:
                info = await client.get_collection(coll.name)
                points = info.points_count or 0
                if points > 0:
                    collection_stats.append({
                        "name": coll.name,
                        "points": points
                    })

            # Sort by points
            collection_stats.sort(key=lambda x: x["points"], reverse=True)

            top_projects = [{
                "name": "legacy-imports",
                "message_count": sum(c["points"] for c in collection_stats),
                "file_count": len(collection_stats)
            }]

            # Use current timestamp instead of "N/A"
            current_time = datetime.now().isoformat()
            recent_imports = [{
                "path": f"Collection: {c['name']}",
                "project": "legacy-imports",
                "imported_at": current_time,
                "message_count": c["points"]
            } for c in collection_stats[:10]]

            return {
                "top_projects": top_projects,
                "recent_imports": recent_imports,
                "total_projects": 1,
                "total_files": len(collection_stats)
            }
        finally:
            if client:
                await client.close()

        # Use unified state
        # Top projects by message count
        sorted_projects = sorted(
            projects.items(),
            key=lambda x: x[1].get("message_count", 0),
            reverse=True
        )[:5]

        top_projects = [
            {
                "name": name,
                "message_count": data.get("message_count", 0),
                "file_count": data.get("file_count", 0)
            }
            for name, data in sorted_projects
        ]

        # Recent activity (handle None values in imported_at)
        recent_imports = sorted(
            [
                {
                    "path": f.get("path", ""),
                    "project": f.get("project", ""),
                    "imported_at": f.get("imported_at", ""),
                    "message_count": f.get("message_count", 0)
                }
                for f in files.values()
            ],
            key=lambda x: x["imported_at"] or "",
            reverse=True
        )[:10]

        return {
            "top_projects": top_projects,
            "recent_imports": recent_imports,
            "total_projects": len(projects),
            "total_files": len(files)
        }
    except Exception as e:
        logger.error(f"Error fetching system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
