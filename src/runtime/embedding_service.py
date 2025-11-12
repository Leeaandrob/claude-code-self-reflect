"""
Embedding service abstraction to handle both local and cloud embeddings.
Reduces complexity by separating embedding concerns from import logic.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider."""
        pass

    @abstractmethod
    def get_collection_suffix(self) -> str:
        """Get the suffix for collection naming."""
        pass


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using FastEmbed."""

    def __init__(self):
        self.model = None
        self.dimension = 384
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the FastEmbed model."""
        try:
            from fastembed import TextEmbedding
            # CRITICAL: Use the correct model that matches the rest of the system
            # This must be sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
            self.model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
            logger.info("Initialized local FastEmbed model: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)")
        except ImportError as e:
            logger.error("FastEmbed not installed. Install with: pip install fastembed")
            raise
        except Exception as e:
            logger.exception(f"Failed to initialize FastEmbed: {e}")
            raise

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using FastEmbed."""
        if not self.model:
            raise RuntimeError("FastEmbed model not initialized")

        try:
            embeddings = list(self.model.embed(texts))
            return [list(emb) for emb in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate local embeddings: {e}")
            raise

    def get_dimension(self) -> int:
        """Get embedding dimension (384 for FastEmbed)."""
        return self.dimension

    def get_collection_suffix(self) -> str:
        """Get collection suffix for local embeddings."""
        return "local_384d"


class CloudEmbeddingProvider(EmbeddingProvider):
    """Cloud embedding provider using Voyage AI."""

    def __init__(self, api_key: str):
        # Don't store API key directly, use it only for client initialization
        self.client = None
        self.dimension = 1024
        self._initialize_client(api_key)

    def _initialize_client(self, api_key: str):
        """Initialize the Voyage AI client."""
        try:
            import voyageai
            self.client = voyageai.Client(api_key=api_key)
            logger.info("Initialized Voyage AI client (1024 dimensions)")
        except ImportError as e:
            logger.error("voyageai not installed. Install with: pip install voyageai")
            raise
        except Exception as e:
            logger.exception(f"Failed to initialize Voyage AI: {e}")
            raise

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Voyage AI."""
        if not self.client:
            raise RuntimeError("Voyage AI client not initialized")

        try:
            result = self.client.embed(texts, model="voyage-2")
            return result.embeddings
        except Exception as e:
            logger.error(f"Failed to generate cloud embeddings: {e}")
            raise

    def get_dimension(self) -> int:
        """Get embedding dimension (1024 for Voyage)."""
        return self.dimension

    def get_collection_suffix(self) -> str:
        """Get collection suffix for cloud embeddings."""
        return "cloud_1024d"


class QwenEmbeddingProvider(EmbeddingProvider):
    """Qwen/DashScope embedding provider using OpenAI SDK."""

    def __init__(self, api_key: str, endpoint: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"):
        self.client = None
        self.dimension = 2048
        self.max_chars = 6000  # Conservative limit (~2000 tokens, well under 8192 limit)
        self._initialize_client(api_key, endpoint)

    def _initialize_client(self, api_key: str, endpoint: str):
        """Initialize the OpenAI client with DashScope endpoint."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key, base_url=endpoint)
            logger.info("Initialized Qwen/DashScope client via OpenAI SDK (2048 dimensions)")
        except ImportError as e:
            logger.error("openai not installed. Install with: pip install openai")
            raise
        except Exception as e:
            logger.exception(f"Failed to initialize Qwen/DashScope: {e}")
            raise

    def _chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into smaller pieces if it exceeds max_chars.
        Tries to split on sentence boundaries to maintain context.
        """
        if len(text) <= self.max_chars:
            return [text]

        chunks = []
        current_chunk = ""

        # Split on sentence boundaries (., !, ?, \n)
        sentences = text.replace('!', '.').replace('?', '.').split('.')

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If adding this sentence would exceed limit, save current chunk
            if len(current_chunk) + len(sentence) + 2 > self.max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + '.'
            else:
                current_chunk += sentence + '.'

        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text[:self.max_chars]]

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Qwen via OpenAI SDK with automatic chunking and batching.

        Optimized for Qwen API limits:
        - Batch size: 10 texts per request (API limit)
        - RPM: 1,800 requests/minute = 30 req/sec
        - Theoretical max: 300 texts/sec (30 req/sec × 10 texts/batch)
        """
        if not self.client:
            raise RuntimeError("Qwen client not initialized")

        try:
            import numpy as np
            all_embeddings = []
            BATCH_SIZE = 10  # Qwen API batch limit

            # Process texts in batches for efficiency
            for i in range(0, len(texts), BATCH_SIZE):
                batch_texts = texts[i:i + BATCH_SIZE]
                batch_results = []

                for text in batch_texts:
                    # Skip empty texts
                    if not text or not text.strip():
                        logger.warning("Skipping empty text for embedding")
                        batch_results.append([0.0] * self.dimension)
                        continue

                    # Chunk if text is too long
                    chunks = self._chunk_text(text)

                    if len(chunks) > 1:
                        logger.debug(f"Text split into {len(chunks)} chunks (length: {len(text)} chars)")

                        # For multi-chunk texts, process chunks separately and average
                        chunk_embeddings = []
                        for chunk in chunks:
                            response = self.client.embeddings.create(
                                model="text-embedding-v4",
                                input=[chunk],
                                dimensions=2048
                            )
                            chunk_embeddings.append(response.data[0].embedding)

                        # Average embeddings if multiple chunks
                        avg_embedding = np.mean(chunk_embeddings, axis=0).tolist()
                        batch_results.append(avg_embedding)
                    else:
                        # Single chunk - add to batch for processing
                        batch_results.append(chunks[0])

                # Now process all single-chunk texts in the batch together
                single_chunk_texts = [
                    text for text, result in zip(batch_texts, batch_results)
                    if isinstance(result, str)  # These are the chunked texts waiting for embedding
                ]

                if single_chunk_texts:
                    # Batch API call for all single-chunk texts (up to 10 at once)
                    response = self.client.embeddings.create(
                        model="text-embedding-v4",
                        input=single_chunk_texts,
                        dimensions=2048
                    )

                    # Replace string placeholders with actual embeddings
                    embed_idx = 0
                    for j, result in enumerate(batch_results):
                        if isinstance(result, str):
                            batch_results[j] = response.data[embed_idx].embedding
                            embed_idx += 1

                all_embeddings.extend(batch_results)

            return all_embeddings

        except Exception as e:
            logger.error(f"Failed to generate Qwen embeddings: {e}")
            raise

    def get_dimension(self) -> int:
        """Get embedding dimension (2048 for Qwen v4)."""
        return self.dimension

    def get_collection_suffix(self) -> str:
        """Get collection suffix for Qwen embeddings."""
        return "qwen_2048d"


class EmbeddingService:
    """
    Service to manage embedding generation with automatic provider selection.
    Reduces complexity by encapsulating embedding logic.
    """

    def __init__(self, prefer_local: bool = True, voyage_api_key: Optional[str] = None, qwen_api_key: Optional[str] = None, qwen_endpoint: Optional[str] = None, embedding_provider: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            prefer_local: Whether to prefer local embeddings when available
            voyage_api_key: API key for Voyage AI (if using cloud embeddings)
            qwen_api_key: API key for Qwen/DashScope
            qwen_endpoint: Endpoint URL for DashScope
            embedding_provider: Explicit provider selection ('local', 'voyage', 'qwen')
        """
        self.prefer_local = prefer_local
        self.voyage_api_key = voyage_api_key
        self.qwen_api_key = qwen_api_key
        self.qwen_endpoint = qwen_endpoint or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        self.embedding_provider = embedding_provider
        self.provider = None
        self._initialize_provider()

    def _initialize_provider(self):
        """Initialize the appropriate embedding provider."""
        # Priority 1: Explicit provider selection
        if self.embedding_provider == 'qwen' and self.qwen_api_key:
            try:
                self.provider = QwenEmbeddingProvider(self.qwen_api_key, self.qwen_endpoint)
                logger.info("Using Qwen embedding provider (text-embedding-v4)")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize Qwen provider: {e}, falling back...")

        elif self.embedding_provider == 'voyage' and self.voyage_api_key:
            try:
                self.provider = CloudEmbeddingProvider(self.voyage_api_key)
                logger.info("Using Voyage AI embedding provider")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize Voyage provider: {e}, falling back...")

        elif self.embedding_provider == 'local':
            try:
                self.provider = LocalEmbeddingProvider()
                logger.info("Using local embedding provider (FastEmbed)")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize local provider: {e}")
                raise RuntimeError("Local provider requested but failed to initialize")

        # Priority 2: Auto-detect based on prefer_local flag (legacy behavior)
        if self.prefer_local or not self.voyage_api_key:
            try:
                self.provider = LocalEmbeddingProvider()
                logger.info("Using local embedding provider (FastEmbed)")
            except Exception as e:
                logger.warning(f"Failed to initialize local provider: {e}")
                if self.voyage_api_key:
                    self._fallback_to_cloud()
                else:
                    raise RuntimeError("No embedding provider available")
        else:
            try:
                self.provider = CloudEmbeddingProvider(self.voyage_api_key)
                logger.info("Using cloud embedding provider (Voyage AI)")
            except Exception as e:
                logger.warning(f"Failed to initialize cloud provider: {e}")
                self._fallback_to_local()

    def _fallback_to_cloud(self):
        """Fallback to cloud provider."""
        if not self.voyage_api_key:
            raise RuntimeError("No Voyage API key available for cloud fallback")
        try:
            self.provider = CloudEmbeddingProvider(self.voyage_api_key)
            logger.info("Fallback to cloud embedding provider")
            # Clear the key after use
            self.voyage_api_key = None
        except Exception as e:
            raise RuntimeError(f"Failed to initialize any embedding provider: {e}")

    def _fallback_to_local(self):
        """Fallback to local provider."""
        try:
            self.provider = LocalEmbeddingProvider()
            logger.info("Fallback to local embedding provider")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize any embedding provider: {e}")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using the configured provider.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not self.provider:
            raise RuntimeError("No embedding provider initialized")

        # Filter out empty texts
        non_empty_texts = [t for t in texts if t and t.strip()]
        if not non_empty_texts:
            return []

        return self.provider.generate_embeddings(non_empty_texts)

    def get_dimension(self) -> int:
        """Get the dimension of embeddings."""
        if not self.provider:
            raise RuntimeError("No embedding provider initialized")
        return self.provider.get_dimension()

    def get_collection_suffix(self) -> str:
        """Get the collection suffix for current provider."""
        if not self.provider:
            raise RuntimeError("No embedding provider initialized")
        return self.provider.get_collection_suffix()

    def get_provider_name(self) -> str:
        """Get the name of the current provider."""
        if isinstance(self.provider, LocalEmbeddingProvider):
            return "FastEmbed (Local)"
        elif isinstance(self.provider, CloudEmbeddingProvider):
            return "Voyage AI (Cloud)"
        elif isinstance(self.provider, QwenEmbeddingProvider):
            return "Qwen (DashScope)"
        else:
            return "Unknown"


# Factory function for convenience
def create_embedding_service(
    prefer_local: Optional[bool] = None,
    voyage_api_key: Optional[str] = None,
    qwen_api_key: Optional[str] = None,
    qwen_endpoint: Optional[str] = None,
    embedding_provider: Optional[str] = None
) -> EmbeddingService:
    """
    Create an embedding service with environment variable defaults.

    Args:
        prefer_local: Override for PREFER_LOCAL_EMBEDDINGS env var
        voyage_api_key: Override for VOYAGE_KEY env var
        qwen_api_key: Override for DASHSCOPE_API_KEY env var
        qwen_endpoint: Override for DASHSCOPE_ENDPOINT env var
        embedding_provider: Override for EMBEDDING_PROVIDER env var

    Returns:
        Configured EmbeddingService instance
    """
    if embedding_provider is None:
        embedding_provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()

    if prefer_local is None:
        prefer_local = os.getenv("PREFER_LOCAL_EMBEDDINGS", "true").lower() == "true"

    if voyage_api_key is None:
        voyage_api_key = os.getenv("VOYAGE_KEY")

    if qwen_api_key is None:
        qwen_api_key = os.getenv("DASHSCOPE_API_KEY")

    if qwen_endpoint is None:
        qwen_endpoint = os.getenv("DASHSCOPE_ENDPOINT", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")

    return EmbeddingService(prefer_local, voyage_api_key, qwen_api_key, qwen_endpoint, embedding_provider)