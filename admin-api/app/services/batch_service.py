"""DashScope Batch API integration for narrative generation."""
import os
import json
import uuid
import asyncio
import logging
import aiohttp
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# In Docker, config is mounted at /config
# Outside Docker, use ~/.claude-self-reflect/config
CONFIG_PATH = Path(os.getenv('CONFIG_PATH', '/config'))
if not CONFIG_PATH.exists():
    CONFIG_PATH = Path.home() / '.claude-self-reflect' / 'config'

# Batch state directories - use /tmp in Docker, home dir outside
if Path('/config').exists():
    # Running in Docker
    BATCH_STATE_DIR = Path('/tmp/batch_state')
    BATCH_FILES_DIR = Path('/tmp/batch_files')
else:
    # Running outside Docker
    CSR_HOME = Path.home() / '.claude-self-reflect'
    BATCH_STATE_DIR = CSR_HOME / 'batch_state'
    BATCH_FILES_DIR = CSR_HOME / 'batch_files'

UNIFIED_STATE_FILE = CONFIG_PATH / 'unified-state.json'

# DashScope configuration
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')
DASHSCOPE_BASE_URL = os.getenv(
    'DASHSCOPE_BASE_URL',
    'https://dashscope-intl.aliyuncs.com/compatible-mode/v1'
)

# Default model for narrative generation
DEFAULT_NARRATIVE_MODEL = os.getenv('NARRATIVE_MODEL', 'qwen-plus')

# Narrative generation prompt template
NARRATIVE_PROMPT_TEMPLATE = """Analyze this conversation between a developer and Claude Code AI assistant. Generate a structured narrative that captures the essence of the work done.

<conversation>
{conversation_content}
</conversation>

Generate a JSON response with the following structure:
{{
  "summary": "A 2-3 sentence executive summary of what was accomplished",
  "problem": "The initial problem or objective (if any)",
  "solution": "The solution implemented (if any)",
  "decisions": ["List of key technical decisions made"],
  "files_modified": ["List of files created or modified"],
  "key_insights": ["Important learnings or patterns identified"],
  "tags": ["Relevant tags for semantic search"],
  "complexity": "low|medium|high",
  "outcome": "success|partial|failed|ongoing"
}}

Important:
- Be concise but comprehensive
- Focus on technical details and decisions
- Extract file paths mentioned in the conversation
- Identify patterns that could help future development
- Generate tags that would help find this conversation later

Respond ONLY with valid JSON, no additional text."""


class BatchService:
    """Service for managing DashScope Batch API operations."""

    def __init__(self):
        self.api_key = DASHSCOPE_API_KEY
        self.base_url = DASHSCOPE_BASE_URL
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        BATCH_STATE_DIR.mkdir(parents=True, exist_ok=True)
        BATCH_FILES_DIR.mkdir(parents=True, exist_ok=True)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """Make HTTP request to DashScope API."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }

        if not files:
            headers['Content-Type'] = 'application/json'

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                headers=headers,
                json=data if not files else None,
                data=files,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                result = await response.json()
                if response.status >= 400:
                    logger.error(f"DashScope API error: {result}")
                    raise Exception(f"DashScope API error: {result.get('error', {}).get('message', 'Unknown error')}")
                return result

    async def upload_file(self, file_path: Path) -> str:
        """Upload a JSONL file to DashScope for batch processing."""
        url = f"{self.base_url}/files"
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }

        async with aiofiles.open(file_path, 'rb') as f:
            file_content = await f.read()

        form_data = aiohttp.FormData()
        form_data.add_field(
            'file',
            file_content,
            filename=file_path.name,
            content_type='application/jsonl'
        )
        form_data.add_field('purpose', 'batch')

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=form_data) as response:
                result = await response.json()
                if response.status >= 400:
                    raise Exception(f"File upload failed: {result}")
                return result['id']

    async def create_batch_job(
        self,
        input_file_id: str,
        model: str = DEFAULT_NARRATIVE_MODEL,
        completion_window: str = "24h"
    ) -> Dict[str, Any]:
        """Create a batch job in DashScope."""
        data = {
            "input_file_id": input_file_id,
            "endpoint": "/v1/chat/completions",
            "completion_window": completion_window,
            "metadata": {
                "model": model,
                "created_by": "claude-self-reflect"
            }
        }

        return await self._make_request('POST', '/batches', data=data)

    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get the status of a batch job."""
        return await self._make_request('GET', f'/batches/{batch_id}')

    async def cancel_batch(self, batch_id: str) -> Dict[str, Any]:
        """Cancel a running batch job."""
        return await self._make_request('POST', f'/batches/{batch_id}/cancel')

    async def get_file_content(self, file_id: str) -> str:
        """Download file content from DashScope."""
        url = f"{self.base_url}/files/{file_id}/content"
        headers = {'Authorization': f'Bearer {self.api_key}'}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status >= 400:
                    raise Exception(f"Failed to download file: {response.status}")
                return await response.text()

    def _load_conversation(self, file_path: str) -> Optional[str]:
        """Load conversation content from JSONL file."""
        try:
            messages = []
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        msg = json.loads(line)
                        role = msg.get('type', msg.get('role', 'unknown'))
                        content = msg.get('message', msg.get('content', ''))
                        if isinstance(content, dict):
                            content = content.get('content', str(content))
                        messages.append(f"[{role}]: {content}")

            return "\n\n".join(messages)
        except Exception as e:
            logger.error(f"Error loading conversation {file_path}: {e}")
            return None

    async def prepare_batch_file(
        self,
        conversation_ids: List[str],
        project: Optional[str] = None,
        model: str = DEFAULT_NARRATIVE_MODEL
    ) -> Path:
        """Prepare a JSONL file for batch processing."""
        batch_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_file = BATCH_FILES_DIR / f"batch_{timestamp}_{batch_id}.jsonl"

        # Load unified state to get file paths
        if not UNIFIED_STATE_FILE.exists():
            raise Exception("Unified state file not found")

        async with aiofiles.open(UNIFIED_STATE_FILE, 'r') as f:
            state = json.loads(await f.read())

        files_data = state.get('files', {})

        # Build conversation map
        # Note: In unified-state.json, the KEY is the file path (not a hash)
        # and the VALUE contains metadata (chunks, status, etc)
        conversation_map = {}
        for file_path, file_info in files_data.items():
            # Skip non-completed files
            if file_info.get('status') != 'completed':
                continue
            # Extract conversation ID from path (the UUID)
            conv_id = Path(file_path).stem
            conversation_map[conv_id] = file_path

        # Prepare batch requests
        requests = []
        for conv_id in conversation_ids:
            file_path = conversation_map.get(conv_id)
            if not file_path or not Path(file_path).exists():
                logger.warning(f"Conversation file not found: {conv_id}")
                continue

            conversation_content = self._load_conversation(file_path)
            if not conversation_content:
                continue

            # Truncate if too long (max ~100k tokens for context)
            if len(conversation_content) > 400000:
                conversation_content = conversation_content[:400000] + "\n\n[TRUNCATED]"

            request = {
                "custom_id": conv_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a technical analyst that generates structured JSON summaries of development conversations. Always respond with valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": NARRATIVE_PROMPT_TEMPLATE.format(
                                conversation_content=conversation_content
                            )
                        }
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                }
            }
            requests.append(request)

        if not requests:
            raise Exception("No valid conversations found for batch processing")

        # Write batch file
        async with aiofiles.open(batch_file, 'w') as f:
            for request in requests:
                await f.write(json.dumps(request) + '\n')

        logger.info(f"Created batch file with {len(requests)} requests: {batch_file}")
        return batch_file

    async def submit_batch(
        self,
        conversation_ids: List[str],
        project: Optional[str] = None,
        model: str = DEFAULT_NARRATIVE_MODEL
    ) -> Dict[str, Any]:
        """Submit a batch job for narrative generation."""
        # Prepare the batch file
        batch_file = await self.prepare_batch_file(conversation_ids, project, model)

        # Upload file to DashScope
        file_id = await self.upload_file(batch_file)
        logger.info(f"Uploaded batch file, got file_id: {file_id}")

        # Create batch job
        batch_response = await self.create_batch_job(file_id, model)
        batch_id = batch_response.get('id')

        # Save local state
        state = {
            "batch_id": batch_id,
            "dashscope_file_id": file_id,
            "local_batch_file": str(batch_file),
            "status": "submitted",
            "model": model,
            "project": project,
            "conversations": conversation_ids,
            "conversations_count": len(conversation_ids),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        state_file = BATCH_STATE_DIR / f"{batch_id}.json"
        async with aiofiles.open(state_file, 'w') as f:
            await f.write(json.dumps(state, indent=2))

        return state

    async def poll_and_update_status(self, batch_id: str) -> Dict[str, Any]:
        """Poll DashScope for batch status and update local state."""
        state_file = BATCH_STATE_DIR / f"{batch_id}.json"
        if not state_file.exists():
            raise Exception(f"Batch job not found: {batch_id}")

        async with aiofiles.open(state_file, 'r') as f:
            state = json.loads(await f.read())

        # Get status from DashScope
        try:
            batch_status = await self.get_batch_status(batch_id)
        except Exception as e:
            logger.error(f"Error polling batch status: {e}")
            state['error'] = str(e)
            state['updated_at'] = datetime.now().isoformat()
            async with aiofiles.open(state_file, 'w') as f:
                await f.write(json.dumps(state, indent=2))
            return state

        # Map DashScope status to our status
        dashscope_status = batch_status.get('status', 'unknown')
        status_map = {
            'validating': 'pending',
            'in_progress': 'in_progress',
            'completed': 'completed',
            'failed': 'failed',
            'expired': 'failed',
            'cancelled': 'failed'
        }

        state['status'] = status_map.get(dashscope_status, dashscope_status)
        state['dashscope_status'] = batch_status
        state['updated_at'] = datetime.now().isoformat()

        # Calculate progress
        request_counts = batch_status.get('request_counts', {})
        total = request_counts.get('total', 0)
        completed = request_counts.get('completed', 0)
        if total > 0:
            state['progress'] = int((completed / total) * 100)
            state['completed_count'] = completed
            state['failed_count'] = request_counts.get('failed', 0)

        # If completed, store output file info
        if state['status'] == 'completed':
            state['completed_at'] = datetime.now().isoformat()
            state['output_file_id'] = batch_status.get('output_file_id')
            state['error_file_id'] = batch_status.get('error_file_id')

        # Save updated state
        async with aiofiles.open(state_file, 'w') as f:
            await f.write(json.dumps(state, indent=2))

        return state

    async def get_batch_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """Download and parse batch results."""
        state_file = BATCH_STATE_DIR / f"{batch_id}.json"
        if not state_file.exists():
            raise Exception(f"Batch job not found: {batch_id}")

        async with aiofiles.open(state_file, 'r') as f:
            state = json.loads(await f.read())

        if state.get('status') != 'completed':
            raise Exception(f"Batch job not completed: {state.get('status')}")

        output_file_id = state.get('output_file_id')
        if not output_file_id:
            raise Exception("No output file available")

        # Download results
        content = await self.get_file_content(output_file_id)

        results = []
        for line in content.strip().split('\n'):
            if line:
                try:
                    result = json.loads(line)
                    custom_id = result.get('custom_id')
                    response = result.get('response', {})

                    # Extract narrative from response
                    if response.get('status_code') == 200:
                        body = response.get('body', {})
                        choices = body.get('choices', [])
                        if choices:
                            content = choices[0].get('message', {}).get('content', '{}')
                            try:
                                narrative = json.loads(content)
                            except json.JSONDecodeError:
                                narrative = {"raw_content": content}

                            results.append({
                                "conversation_id": custom_id,
                                "narrative": narrative,
                                "tokens_used": body.get('usage', {})
                            })
                    else:
                        results.append({
                            "conversation_id": custom_id,
                            "error": response.get('error', 'Unknown error')
                        })
                except Exception as e:
                    logger.error(f"Error parsing result line: {e}")

        return results

    async def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all batch jobs from local state."""
        jobs = []

        if not BATCH_STATE_DIR.exists():
            return jobs

        for state_file in BATCH_STATE_DIR.glob('*.json'):
            try:
                async with aiofiles.open(state_file, 'r') as f:
                    state = json.loads(await f.read())
                    jobs.append({
                        "id": state.get("batch_id", ""),
                        "status": state.get("status", ""),
                        "model": state.get("model", ""),
                        "project": state.get("project", ""),
                        "conversations_count": state.get("conversations_count", 0),
                        "progress": state.get("progress", 0),
                        "completed_count": state.get("completed_count", 0),
                        "failed_count": state.get("failed_count", 0),
                        "created_at": state.get("created_at", ""),
                        "updated_at": state.get("updated_at", ""),
                        "completed_at": state.get("completed_at", ""),
                        "error": state.get("error", "")
                    })
            except Exception as e:
                logger.warning(f"Error reading state file {state_file}: {e}")

        return sorted(jobs, key=lambda x: x["created_at"], reverse=True)[:limit]

    async def get_job(self, batch_id: str) -> Dict[str, Any]:
        """Get detailed batch job information."""
        state_file = BATCH_STATE_DIR / f"{batch_id}.json"
        if not state_file.exists():
            raise Exception(f"Batch job not found: {batch_id}")

        async with aiofiles.open(state_file, 'r') as f:
            return json.loads(await f.read())

    async def get_conversations_without_narrative(
        self,
        project: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get conversations that don't have narratives yet."""
        if not UNIFIED_STATE_FILE.exists():
            return []

        async with aiofiles.open(UNIFIED_STATE_FILE, 'r') as f:
            state = json.loads(await f.read())

        files_data = state.get('files', {})
        conversations = []

        for file_path_key, file_info in files_data.items():
            # Skip if already has narrative
            if file_info.get('has_narrative'):
                continue

            # Skip non-completed files
            if file_info.get('status') != 'completed':
                continue

            # Extract project from collection name (conv_{hash}_qwen_1024d)
            collection = file_info.get('collection', '')
            file_project = collection.split('_')[1] if collection.startswith('conv_') else ''

            # Filter by project if specified
            if project and file_project != project:
                continue

            # The key is the file path (Docker format: /logs/...)
            # Convert to conversation ID from the filename
            file_path = Path(file_path_key)
            conv_id = file_path.stem  # UUID without .jsonl

            conversations.append({
                "id": conv_id,
                "path": file_path_key,
                "project": file_project,
                "collection": collection,
                "chunks": file_info.get('chunks', 0),
                "imported_at": file_info.get('imported_at', '')
            })

        # Sort by import date (newest first)
        conversations.sort(key=lambda x: x['imported_at'], reverse=True)
        return conversations[:limit]


# Singleton instance
batch_service = BatchService()
