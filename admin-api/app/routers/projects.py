"""Projects management API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import json
from pathlib import Path
import logging
import os
from qdrant_client import AsyncQdrantClient
import re

logger = logging.getLogger(__name__)
router = APIRouter()

# Use STATE_FILE env var (set by docker-compose) or fallback to default
UNIFIED_STATE_FILE = Path(os.getenv('STATE_FILE', str(Path.home() / '.claude-self-reflect' / 'config' / 'unified-state.json')))
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')

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

async def get_projects_from_qdrant() -> List[Dict[str, Any]]:
    """Extract project information from Qdrant collections.

    Supports both old (conv_*_voyage) and new (csr_{project}_*) naming conventions.
    """
    client = None
    try:
        client = AsyncQdrantClient(url=QDRANT_URL)
        collections = await client.get_collections()
        projects_map = {}

        for coll in collections.collections:
            name = coll.name
            info = await client.get_collection(name)
            points_count = info.points_count or 0

            # Extract project name from collection name
            project_name = None

            # New format: csr_{project}_local_384d or csr_{project}_cloud_1024d
            if name.startswith('csr_'):
                match = re.match(r'csr_(.+?)_(local|cloud)_\d+d', name)
                if match:
                    project_name = match.group(1)
                    mode = match.group(2)

            # Old format: conv_{hash}_voyage (extract from Qdrant payloads if possible)
            # For now, group all old collections as "legacy-imports"
            elif name.startswith('conv_') and name.endswith('_voyage'):
                project_name = "legacy-imports"

            if project_name and points_count > 0:
                if project_name not in projects_map:
                    projects_map[project_name] = {
                        "name": project_name,
                        "message_count": 0,
                        "collections": []
                    }
                projects_map[project_name]["message_count"] += points_count
                projects_map[project_name]["collections"].append({
                    "name": name,
                    "points": points_count
                })

        return list(projects_map.values())
    except Exception as e:
        logger.error(f"Error getting projects from Qdrant: {e}")
        return []
    finally:
        if client:
            await client.close()

@router.get("/")
async def list_projects():
    """List all projects with their statistics.

    Extracts projects from files data or falls back to Qdrant.
    """
    try:
        # Load unified state
        state = await load_unified_state()
        files = state.get("files", {})

        # Extract projects from files data
        if files and len(files) > 0:
            projects_map = {}

            for file_path, file_data in files.items():
                # Extract project name from file path
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

                # Fallback: try collection
                if not project_name:
                    collection = file_data.get("collection", "")
                    if collection.startswith("csr_"):
                        project_part = collection[4:]
                        for suffix in ["_qwen_2048d", "_qwen_1024d", "_voyage_1024d", "_local_384d"]:
                            if suffix in project_part:
                                project_name = project_part.replace(suffix, "")
                                break

                # Aggregate by project
                if project_name:
                    if project_name not in projects_map:
                        projects_map[project_name] = {
                            "file_count": 0,
                            "message_count": 0,
                            "last_updated": file_data.get("imported_at") or ""
                        }

                    projects_map[project_name]["file_count"] += 1
                    chunks = file_data.get("chunks", 0)
                    projects_map[project_name]["message_count"] += chunks * 50  # Estimate messages

                    # Update last_updated to most recent
                    current_time = file_data.get("imported_at") or ""
                    if current_time > projects_map[project_name]["last_updated"]:
                        projects_map[project_name]["last_updated"] = current_time

            # Convert to list
            project_list = [
                {
                    "name": name,
                    "file_count": data["file_count"],
                    "message_count": data["message_count"],
                    "last_updated": data["last_updated"],
                }
                for name, data in projects_map.items()
            ]

            return sorted(project_list, key=lambda x: x["message_count"], reverse=True)

        # Fallback to Qdrant if no files
        logger.info("No files in unified state, reading from Qdrant collections")
        qdrant_projects = await get_projects_from_qdrant()
        return sorted(qdrant_projects, key=lambda x: x["message_count"], reverse=True)

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_name}")
async def get_project_details(project_name: str):
    """Get detailed information about a specific project."""
    try:
        state = await load_unified_state()
        projects = state.get("projects", {})
        files = state.get("files", {})

        if project_name not in projects:
            raise HTTPException(status_code=404, detail="Project not found")

        project_data = projects[project_name]

        # Get files for this project
        project_files = [
            {
                "path": f.get("path", ""),
                "hash": f.get("hash", ""),
                "imported_at": f.get("imported_at", ""),
                "message_count": f.get("message_count", 0)
            }
            for f in files.values()
            if f.get("project") == project_name
        ]

        return {
            "name": project_name,
            "file_count": project_data.get("file_count", 0),
            "message_count": project_data.get("message_count", 0),
            "last_updated": project_data.get("last_updated", ""),
            "files": project_files
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
