"""Cloud embedding model manager - Qwen/DashScope and Voyage AI only."""

import os
import logging
from typing import Optional, List, Union

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages cloud embedding models (Qwen/DashScope and Voyage AI)."""

    def __init__(self):
        self.voyage_client = None
        self.qwen_client = None
        self.model_type = None  # 'voyage' or 'qwen'

        # Configuration
        self.embedding_provider = os.getenv('EMBEDDING_PROVIDER', 'cloud').lower()
        self.voyage_key = os.getenv('VOYAGE_KEY') or os.getenv('VOYAGE_API_KEY')
        self.dashscope_key = os.getenv('DASHSCOPE_API_KEY')
        self.dashscope_endpoint = os.getenv('DASHSCOPE_ENDPOINT', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')

    def initialize(self) -> bool:
        """Initialize embedding models based on configuration."""
        logger.info("Initializing cloud embedding manager...")
        logger.info(f"Embedding provider: {self.embedding_provider}")

        qwen_success = False
        voyage_success = False

        # Priority: Qwen > Voyage (based on what's configured)
        if self.dashscope_key:
            qwen_success = self._try_initialize_qwen()
            if qwen_success:
                self.model_type = 'qwen'
                logger.info("Using QWEN embeddings (text-embedding-v4, 2048 dimensions)")
                return True

        if self.voyage_key:
            voyage_success = self._try_initialize_voyage()
            if voyage_success:
                self.model_type = 'voyage'
                logger.info("Using VOYAGE embeddings (voyage-3, 1024 dimensions)")
                return True

        # No cloud provider available
        logger.error("No cloud embedding provider configured. Set DASHSCOPE_API_KEY or VOYAGE_KEY.")
        return False

    def _try_initialize_qwen(self) -> bool:
        """Try to initialize Qwen/DashScope client."""
        return self.try_initialize_qwen()

    def try_initialize_qwen(self) -> bool:
        """Initialize Qwen/DashScope client using OpenAI SDK."""
        try:
            logger.info("Attempting to initialize Qwen/DashScope via OpenAI SDK...")
            from openai import OpenAI

            self.qwen_client = OpenAI(
                api_key=self.dashscope_key,
                base_url=self.dashscope_endpoint
            )

            # Test the client
            response = self.qwen_client.embeddings.create(
                model="text-embedding-v4",
                input="test",
                dimensions=2048
            )

            if response.data and len(response.data) > 0:
                self.model_type = 'qwen'
                logger.info("Successfully initialized Qwen/DashScope (text-embedding-v4, 2048d)")
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
        """Initialize Voyage AI client."""
        try:
            logger.info("Attempting to initialize Voyage AI...")
            import voyageai
            self.voyage_client = voyageai.Client(api_key=self.voyage_key)

            # Test the client
            test_result = self.voyage_client.embed(
                texts=["test"],
                model="voyage-3",
                input_type="document"
            )

            if test_result and test_result.embeddings:
                self.model_type = 'voyage'
                logger.info("Successfully initialized Voyage AI (voyage-3, 1024d)")
                return True
            else:
                logger.error("Voyage AI test embedding failed")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Voyage AI: {e}")
            return False

    def embed(self, texts: Union[str, List[str]], input_type: str = "document", force_type: str = None) -> Optional[List[List[float]]]:
        """Generate embeddings using cloud models."""
        use_type = force_type if force_type else self.model_type
        logger.debug(f"Embedding with: force_type={force_type}, self.model_type={self.model_type}, use_type={use_type}")

        if use_type == 'voyage' and not self.voyage_client:
            logger.error("Voyage client not initialized")
            return None
        elif use_type == 'qwen' and not self.qwen_client:
            logger.error("Qwen client not initialized")
            return None

        if isinstance(texts, str):
            texts = [texts]

        try:
            if use_type == 'voyage':
                result = self.voyage_client.embed(
                    texts=texts,
                    model="voyage-3",
                    input_type=input_type
                )
                return result.embeddings

            elif use_type == 'qwen':
                response = self.qwen_client.embeddings.create(
                    model="text-embedding-v4",
                    input=texts,
                    dimensions=2048
                )
                return [item.embedding for item in response.data]

        except Exception as e:
            logger.error(f"Error generating embeddings with {use_type}: {e}")
            return None

    def get_vector_dimension(self, force_type: str = None) -> int:
        """Get the dimension of embeddings for a specific type."""
        use_type = force_type if force_type else self.model_type
        if use_type == 'voyage':
            return 1024
        elif use_type == 'qwen':
            return 2048
        return 0

    def get_model_info(self) -> dict:
        """Get information about the active model."""
        model_name = 'voyage-3' if self.model_type == 'voyage' else 'text-embedding-v4'

        return {
            'type': self.model_type,
            'model': model_name,
            'dimension': self.get_vector_dimension(),
            'embedding_provider': self.embedding_provider,
            'has_voyage_key': bool(self.voyage_key),
            'has_qwen_key': bool(self.dashscope_key)
        }

    async def generate_embedding(self, text: str, force_type: str = None) -> Optional[List[float]]:
        """Generate embedding for a single text (async wrapper)."""
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
            raise RuntimeError("Failed to initialize cloud embedding model. Check DASHSCOPE_API_KEY or VOYAGE_KEY.")
    return _embedding_manager
