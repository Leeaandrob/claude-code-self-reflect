"""Import status API endpoints."""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import logging
import os
from qdrant_client import AsyncQdrantClient

logger = logging.getLogger(__name__)
router = APIRouter()

CSR_HOME = Path.home() / '.claude-self-reflect'
UNIFIED_STATE_FILE = CSR_HOME / 'config' / 'unified-state.json'
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
CLAUDE_LOGS_PATH = Path(os.getenv('CLAUDE_LOGS_PATH', Path.home() / '.claude' / 'projects'))

@router.get("/status")
async def get_import_status():
    """Get overall import status with real-time progress.

    Compares files in CLAUDE_LOGS_PATH with imported files in unified state.
    """
    try:
        # Count total JSONL files in Claude logs directory
        total_files = 0
        total_files_size = 0
        if CLAUDE_LOGS_PATH.exists():
            for project_dir in CLAUDE_LOGS_PATH.iterdir():
                if project_dir.is_dir():
                    jsonl_files = list(project_dir.glob("*.jsonl"))
                    total_files += len(jsonl_files)
                    total_files_size += sum(f.stat().st_size for f in jsonl_files)

        # Get imported files from unified state
        imported_files = 0
        imported_messages = 0
        if UNIFIED_STATE_FILE.exists():
            with open(UNIFIED_STATE_FILE, 'r') as f:
                state = json.load(f)
            files = state.get("files", {})
            imported_files = len(files)
            # Calculate messages from chunks (chunks × 50 = estimated messages)
            for file_data in files.values():
                chunks = file_data.get("chunks", 0)
                imported_messages += chunks * 50

        # Calculate progress
        progress = (imported_files / total_files * 100.0) if total_files > 0 else 0.0

        return {
            "total_files": total_files,
            "imported_files": imported_files,
            "pending_files": total_files - imported_files,
            "total_messages": imported_messages,
            "progress": round(progress, 2),
            "total_size_mb": round(total_files_size / (1024 * 1024), 2)
        }

        # Fallback to Qdrant if unified state is empty
        logger.info("Unified state empty, reading from Qdrant collections")
        client = None
        try:
            client = AsyncQdrantClient(url=QDRANT_URL)
            collections = await client.get_collections()
            total_points = 0
            collection_count = 0

            for coll in collections.collections:
                info = await client.get_collection(coll.name)
                points = info.points_count or 0
                if points > 0:
                    total_points += points
                    collection_count += 1

            return {
                "total_files": collection_count,
                "imported_files": collection_count,
                "total_messages": total_points,
                "progress": 100.0 if collection_count > 0 else 0.0,
                "note": "Data read from Qdrant collections (legacy format)"
            }
        finally:
            if client:
                await client.close()

    except Exception as e:
        logger.error(f"Error getting import status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files")
async def list_imported_files(project: str = None, limit: int = 100):
    """List imported files with optional project filter."""
    try:
        if UNIFIED_STATE_FILE.exists():
            with open(UNIFIED_STATE_FILE, 'r') as f:
                state = json.load(f)
            files = state.get("files", {})

            result = []
            for file_path, file_data in files.items():
                # Extract project name from file path
                # Path format: /logs/-home-leeaandrob-Projects-Personal-project-name/file.jsonl
                project_name = ""

                if "/logs/" in file_path:
                    # Split by /logs/ and take the directory part
                    path_parts = file_path.split("/logs/")[1] if len(file_path.split("/logs/")) > 1 else ""
                    if "/" in path_parts:
                        # Get directory name (before the filename)
                        dir_path = path_parts.rsplit("/", 1)[0]

                        # Clean up: remove leading dash and extract meaningful project name
                        # Example: -home-leeaandrob-Projects-Personal-nutribot-ai-nutribot-hybrid-backend
                        # becomes: nutribot-ai-nutribot-hybrid-backend
                        if dir_path.startswith("-"):
                            parts = dir_path.split("-")
                            # Find last occurrence of meta folders
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

                # Fallback: try to extract from collection (for newer format)
                if not project_name:
                    collection = file_data.get("collection", "")
                    if collection.startswith("csr_"):
                        # Remove prefix and suffix
                        project_part = collection[4:]  # Remove "csr_"
                        # Remove embedding suffix
                        for suffix in ["_qwen_2048d", "_qwen_1024d", "_voyage_1024d", "_local_384d"]:
                            if suffix in project_part:
                                project_name = project_part.replace(suffix, "")
                                break

                # Get chunks (approximate messages count)
                chunks = file_data.get("chunks", 0)
                # Estimate messages: chunks * 50 (MAX_CHUNK_SIZE default)
                estimated_messages = chunks * 50

                # Extract filename from path
                filename = file_path.split("/")[-1] if "/" in file_path else file_path

                file_info = {
                    "path": filename,
                    "full_path": file_path,
                    "project": project_name,
                    "imported_at": file_data.get("imported_at") or "",
                    "message_count": estimated_messages,
                    "chunks": chunks,
                    "collection": file_data.get("collection", ""),
                    "status": file_data.get("status", "unknown")
                }

                # Apply project filter if specified
                if not project or project_name == project:
                    result.append(file_info)

            # Sort by imported_at descending (handle None values)
            result.sort(key=lambda x: x["imported_at"] or "", reverse=True)

            return result[:limit]
        return []
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
