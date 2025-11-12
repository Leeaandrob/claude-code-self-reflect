"""Robust embedding model manager with proper cache handling."""

import os
import sys
import time
import logging
import shutil
from typing import Optional, List, Union
from pathlib import Path
import threading
import signal

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Manages embedding models with proper cache and lock handling."""

    def __init__(self):
        self.local_model = None
        self.voyage_client = None
        self.qwen_client = None
        self.model_type = None  # Default model type ('local', 'voyage', or 'qwen')

        # Configuration
        self.embedding_provider = os.getenv('EMBEDDING_PROVIDER', 'local').lower()
        self.prefer_local = os.getenv('PREFER_LOCAL_EMBEDDINGS', 'true').lower() == 'true'
        self.voyage_key = os.getenv('VOYAGE_KEY') or os.getenv('VOYAGE_KEY-2')
        self.dashscope_key = os.getenv('DASHSCOPE_API_KEY')
        self.dashscope_endpoint = os.getenv('DASHSCOPE_ENDPOINT', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        self.download_timeout = int(os.getenv('FASTEMBED_DOWNLOAD_TIMEOUT', '30'))

        # Set cache directory to our controlled location
        self.cache_dir = Path(__file__).parent.parent / '.fastembed-cache'
        
    def _clean_stale_locks(self):
        """Clean up any stale lock files from previous runs."""
        locks_dir = self.cache_dir / '.locks'
        if locks_dir.exists():
            logger.info(f"Cleaning stale locks in {locks_dir}")
            try:
                # Remove all lock files older than 5 minutes
                import time
                current_time = time.time()
                for lock_file in locks_dir.glob('**/*.lock'):
                    try:
                        age = current_time - lock_file.stat().st_mtime
                        if age > 300:  # 5 minutes
                            lock_file.unlink()
                            logger.debug(f"Removed stale lock: {lock_file.name}")
                    except Exception as e:
                        logger.debug(f"Could not remove lock {lock_file}: {e}")
            except Exception as e:
                logger.warning(f"Error cleaning locks: {e}")
        
    def initialize(self) -> bool:
        """Initialize embedding models based on configuration."""
        logger.info("Initializing embedding manager...")
        logger.info(f"Embedding provider: {self.embedding_provider}")

        # Clean up any stale locks first
        self._clean_stale_locks()

        local_success = False
        voyage_success = False
        qwen_success = False

        # Priority order based on EMBEDDING_PROVIDER
        if self.embedding_provider == 'qwen' and self.dashscope_key:
            # Qwen/DashScope mode
            logger.info("Qwen/DashScope mode requested")
            qwen_success = self._try_initialize_qwen()
            if qwen_success:
                self.model_type = 'qwen'
                logger.info("Using QWEN embeddings (text-embedding-v4, 2048 dimensions)")
            else:
                # Fallback to local if qwen fails
                logger.warning("Qwen initialization failed, falling back to local")
                local_success = self._try_initialize_local()
                if local_success:
                    self.model_type = 'local'

        elif self.embedding_provider == 'voyage' and self.voyage_key:
            # Voyage AI mode
            logger.info("Voyage AI mode requested")
            voyage_success = self._try_initialize_voyage()
            if voyage_success:
                self.model_type = 'voyage'
                logger.info("Using VOYAGE embeddings (1024 dimensions)")
            else:
                # Fallback to local if voyage fails
                logger.warning("Voyage initialization failed, falling back to local")
                local_success = self._try_initialize_local()
                if local_success:
                    self.model_type = 'local'

        else:
            # Local mode or auto-detect
            if self.embedding_provider not in ['local', 'qwen', 'voyage']:
                logger.warning(f"Unknown provider '{self.embedding_provider}', defaulting to local")

            local_success = self._try_initialize_local()
            if local_success:
                self.model_type = 'local'
                logger.info("Using LOCAL embeddings (384 dimensions)")
            else:
                logger.error("Failed to initialize local embedding model")
                return False

        logger.info(f"Embedding models available - Local: {local_success}, Voyage: {voyage_success}, Qwen: {qwen_success}")
        return True
    
    def _try_initialize_local(self) -> bool:
        """Try to initialize local FastEmbed model with timeout and optimizations."""
        return self.try_initialize_local()

    def try_initialize_local(self) -> bool:
        """Public method to initialize local FastEmbed model with timeout and optimizations."""
        try:
            logger.info(f"Attempting to load local model: {self.embedding_model}")
            
            # CRITICAL OPTIMIZATION: Set thread limits BEFORE loading model
            # This prevents ONNX Runtime and BLAS from over-subscribing CPU
            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['MKL_NUM_THREADS'] = '1' 
            os.environ['OPENBLAS_NUM_THREADS'] = '1'
            os.environ['NUMEXPR_NUM_THREADS'] = '1'
            logger.info("Set thread limits to prevent CPU over-subscription")
            
            # Ensure cache directory exists and is writable
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Set FASTEMBED_CACHE_PATH to our controlled directory
            os.environ['FASTEMBED_CACHE_PATH'] = str(self.cache_dir)
            logger.info(f"Using cache directory: {self.cache_dir}")
            
            # Also set HF_HOME to avoid any HuggingFace cache issues
            os.environ['HF_HOME'] = str(self.cache_dir / 'huggingface')
            
            model_cache = self.cache_dir / 'models--qdrant--all-MiniLM-L6-v2-onnx'
            
            if model_cache.exists():
                logger.info("Model cache found, loading from cache...")
            else:
                logger.info(f"Model cache not found, will download (timeout: {self.download_timeout}s)")
                logger.info("Note: First download may take 1-2 minutes")
                
            # Force alternative download if HuggingFace is problematic
            # This uses Qdrant's CDN which is more reliable
            if os.getenv('FASTEMBED_SKIP_HUGGINGFACE', 'true').lower() == 'true':
                os.environ['HF_HUB_OFFLINE'] = '1'
                logger.info("Using alternative download sources (Qdrant CDN)")
            
            # Use a thread with timeout for model initialization
            success = False
            error = None
            
            def init_model():
                nonlocal success, error
                try:
                    from fastembed import TextEmbedding
                    # Initialize with optimized settings
                    # Note: FastEmbed uses these environment variables internally
                    self.local_model = TextEmbedding(
                        model_name=self.embedding_model,
                        threads=1  # Single thread per worker to prevent over-subscription
                    )
                    success = True
                    logger.info(f"Successfully initialized local model: {self.embedding_model} with single-thread mode")
                except Exception as e:
                    error = e
                    logger.error(f"Failed to initialize local model: {e}")
            
            # SECURITY FIX: Use ThreadPoolExecutor with proper timeout handling
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

            # Create executor and manage lifecycle explicitly to avoid blocking on timeout
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(init_model)
            try:
                future.result(timeout=self.download_timeout)
                executor.shutdown(wait=True)
            except FuturesTimeoutError:
                logger.error(f"Model initialization timed out after {self.download_timeout}s")
                logger.info("Tip: Set FASTEMBED_SKIP_HUGGINGFACE=true to use alternative download sources")
                # Don't wait for the hung task
                executor.shutdown(wait=False)
                return False
            except Exception as e:
                logger.error(f"Model initialization failed: {e}")
                executor.shutdown(wait=True)
                return False
            
            return success
            
        except ImportError:
            logger.error("FastEmbed not installed. Install with: pip install fastembed")
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing local embeddings: {e}")
            return False
    
    def _try_initialize_qwen(self) -> bool:
        """Try to initialize Qwen/DashScope client."""
        return self.try_initialize_qwen()

    def try_initialize_qwen(self) -> bool:
        """Public method to initialize Qwen/DashScope client using OpenAI SDK."""
        try:
            logger.info("Attempting to initialize Qwen/DashScope via OpenAI SDK...")
            from openai import OpenAI

            # Initialize OpenAI client with DashScope endpoint
            self.qwen_client = OpenAI(
                api_key=self.dashscope_key,
                base_url=self.dashscope_endpoint
            )

            # Test the client with a simple embedding using text-embedding-v4
            response = self.qwen_client.embeddings.create(
                model="text-embedding-v4",
                input="test",
                dimensions=2048  # Default dimension for v4
            )

            if response.data and len(response.data) > 0:
                self.model_type = 'qwen'
                logger.info(f"Successfully initialized Qwen/DashScope (text-embedding-v4, 2048d)")
                return True
            else:
                logger.error("Qwen/DashScope test embedding returned no data")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Qwen/DashScope: {e}")
            return False

    def _try_initialize_voyage(self) -> bool:
        """Try to initialize Voyage AI client."""
        return self.try_initialize_voyage()

    def try_initialize_voyage(self) -> bool:
        """Public method to initialize Voyage AI client."""
        try:
            logger.info("Attempting to initialize Voyage AI...")
            import voyageai
            self.voyage_client = voyageai.Client(api_key=self.voyage_key)
            
            # Test the client with a simple embedding
            test_result = self.voyage_client.embed(
                texts=["test"],
                model="voyage-3",
                input_type="document"
            )
            
            if test_result and test_result.embeddings:
                self.model_type = 'voyage'
                logger.info("Successfully initialized Voyage AI")
                return True
            else:
                logger.error("Voyage AI test embedding failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize Voyage AI: {e}")
            return False
    
    def embed(self, texts: Union[str, List[str]], input_type: str = "document", force_type: str = None) -> Optional[List[List[float]]]:
        """Generate embeddings using the specified or default model."""
        # Determine which model to use
        use_type = force_type if force_type else self.model_type
        logger.debug(f"Embedding with: force_type={force_type}, self.model_type={self.model_type}, use_type={use_type}")

        if use_type == 'local' and not self.local_model:
            logger.error("Local model not initialized")
            return None
        elif use_type == 'voyage' and not self.voyage_client:
            logger.error("Voyage client not initialized")
            return None
        elif use_type == 'qwen' and not self.qwen_client:
            logger.error("Qwen client not initialized")
            return None

        # Ensure texts is a list
        if isinstance(texts, str):
            texts = [texts]

        try:
            if use_type == 'local':
                # FastEmbed returns a generator, convert to list
                embeddings = list(self.local_model.embed(texts))
                return [emb.tolist() for emb in embeddings]

            elif use_type == 'voyage':
                # Always use voyage-3 for consistency with collection dimensions (1024)
                result = self.voyage_client.embed(
                    texts=texts,
                    model="voyage-3",
                    input_type=input_type
                )
                return result.embeddings

            elif use_type == 'qwen':
                # Use OpenAI SDK with DashScope text-embedding-v4 (2048 dimensions)
                response = self.qwen_client.embeddings.create(
                    model="text-embedding-v4",
                    input=texts,
                    dimensions=2048
                )

                # Extract embeddings from response
                return [item.embedding for item in response.data]

        except Exception as e:
            logger.error(f"Error generating embeddings with {use_type}: {e}")
            return None
    
    def get_vector_dimension(self, force_type: str = None) -> int:
        """Get the dimension of embeddings for a specific type."""
        use_type = force_type if force_type else self.model_type
        if use_type == 'local':
            return 384  # all-MiniLM-L6-v2 dimension
        elif use_type == 'voyage':
            return 1024  # voyage-3 dimension
        elif use_type == 'qwen':
            return 2048  # text-embedding-v4 dimension
        return 0

    def get_model_info(self) -> dict:
        """Get information about the active model."""
        model_name = self.embedding_model
        if self.model_type == 'voyage':
            model_name = 'voyage-3'
        elif self.model_type == 'qwen':
            model_name = 'text-embedding-v4'

        return {
            'type': self.model_type,
            'model': model_name,
            'dimension': self.get_vector_dimension(),
            'embedding_provider': self.embedding_provider,
            'prefer_local': self.prefer_local,
            'has_voyage_key': bool(self.voyage_key),
            'has_qwen_key': bool(self.dashscope_key)
        }
    
    async def generate_embedding(self, text: str, force_type: str = None) -> Optional[List[float]]:
        """Generate embedding for a single text (async wrapper for compatibility)."""
        # Use the force_type if specified, otherwise use default
        result = self.embed(text, input_type="query", force_type=force_type)
        if result and len(result) > 0:
            return result[0]
        return None


# Global instance
_embedding_manager = None

def get_embedding_manager() -> EmbeddingManager:
    """Get or create the global embedding manager."""
    global _embedding_manager
    if _embedding_manager is None:
        _embedding_manager = EmbeddingManager()
        if not _embedding_manager.initialize():
            raise RuntimeError("Failed to initialize any embedding model")
    return _embedding_manager